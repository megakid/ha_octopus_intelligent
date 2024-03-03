"""Support for Octopus Intelligent Tariff in the UK."""
from datetime import timedelta, datetime, timezone
from typing import Any, override
import asyncio
import logging

import homeassistant.util.dt as dt_util

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .graphql_client import OctopusEnergyGraphQLClient
from .graphql_util import validate_octopus_account
from .persistent_data import PersistentData, PersistentDataStore
from .util import *

_LOGGER = logging.getLogger(__name__)

class OctopusIntelligentSystem(DataUpdateCoordinator):
    def __init__(self, hass, *, api_key, account_id, off_peak_start, off_peak_end):
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="Octopus Intelligent",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=300),
        )
        self._hass = hass
        self._api_key = api_key
        self._account_id = account_id

        self._off_peak_start = off_peak_start
        self._off_peak_end = off_peak_end
        
        self.client = OctopusEnergyGraphQLClient(self._api_key)
        self._persistent_data = PersistentData()
        self._store = PersistentDataStore(self._persistent_data, hass, account_id)

    @property
    def account_id(self):
        return self._account_id

    @override
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.

        Returns:
            dict: The data received from the Octopus API, for example:
            {
                'completedDispatches': [{
                    'chargeKwh': '-0.58',
                    'startDtUtc': '2024-02-25 02:00:00+00:00',
                    'endDtUtc': '2024-02-25 02:30:00+00:00',
                    'meta': {'location': 'AT_HOME', 'source': None},
                }, {
                    'chargeKwh': '-0.58',
                    'startDtUtc': '2024-02-25 03:30:00+00:00',
                    'endDtUtc': '2024-02-25 04:00:00+00:00',
                    'meta': {'location': 'AT_HOME', 'source': None},
                }],
                'plannedDispatches': [{
                    'chargeKwh': '-0.67',
                    'startDtUtc': '2024-02-25 23:30:00+00:00',
                    'endDtUtc': '2024-02-26 00:00:00+00:00',
                    'meta': {'location': None, 'source': 'smart-charge'},
                }, {
                    'chargeKwh': '-1.12',
                    'startDtUtc': '2024-02-26 03:00:00+00:00',
                    'endDtUtc': '2024-02-26 04:00:00+00:00',
                    'meta': {'location': None, 'source': 'smart-charge'},
                }],
                'vehicleChargingPreferences': {
                    'weekdayTargetSoc': 80,
                    'weekdayTargetTime': '08:00',
                    'weekendTargetSoc': 80,
                    'weekendTargetTime': '08:00',
                },
                'registeredKrakenflexDevice': { ... },
            }
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(90):
                data = await self.client.async_get_combined_state(self._account_id)
                self._update_planned_dispatch_sources(data)
                return data
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Octopus GraphQL API: {err}")

    def _update_planned_dispatch_sources(self, data):
        """Workaround for issue #35: missing dispatch sources in Octopus API response."""
        dispatches = (data or {}).get("plannedDispatches", [])
        all_sources = [disp.get("meta", {}).get("source", "") for disp in dispatches]
        good_sources: set[str] = {src for src in all_sources if src}
        if good_sources:
            if len(good_sources) > 1:
                _LOGGER.warning(
                    "Unexpected mix of planned dispatch sources: %s", good_sources
                )
                # We don't expect to see a mix of non-None sources like 'bump-charge'
                # and 'smart-charge' in the same planned dispatch list, but if that
                # happens, play safe and avoid assuming the wrong source.
                self._persistent_data.last_seen_planned_dispatch_source = ""
            else:
                self._persistent_data.last_seen_planned_dispatch_source = next(
                    iter(good_sources)
                )

        # Fill in any missing (None) source attribute in the planned dispatch list.
        if any(not src for src in all_sources):
            source = self._persistent_data.last_seen_planned_dispatch_source
            _LOGGER.debug(
                "Missing planned dispatch source in Octopus API response%s",
                f", assuming '{source}'" if source else "",
            )
            if source:
                for dispatch in dispatches:
                    meta = dispatch.get("meta", {})
                    if meta:
                        meta["source"] = meta.get("source") or source

    def is_smart_charging_enabled(self):
        return not self.data.get('registeredKrakenflexDevice', {}).get('suspended', False)
    async def async_suspend_smart_charging(self):
        await self.client.async_suspend_smart_charging(self._account_id)
    async def async_resume_smart_charging(self):
        await self.client.async_resume_smart_charging(self._account_id)

    def is_boost_charging_now(self):
        return self.is_charging_now('bump-charge')

    def is_off_peak_charging_now(self, minutes_offset: int = 0):
        return self.is_charging_now('smart-charge', minutes_offset=minutes_offset)

    def next_offpeak_start_utc(self, minutes_offset: int = 0):
        offpeak_range = self.next_offpeak_range_utc(minutes_offset=minutes_offset)
        return offpeak_range["start"] if offpeak_range is not None else None

    def next_offpeak_end_utc(self, minutes_offset: int = 0):
        offpeak_range = self.next_offpeak_range_utc(minutes_offset=minutes_offset)
        return offpeak_range["end"] if offpeak_range is not None else None

    def next_offpeak_range_utc(self, minutes_offset: int = 0):
        utcnow = dt_util.utcnow() + timedelta(minutes=minutes_offset)
        localdate = dt_util.start_of_local_day(dt_util.as_local(utcnow))
        fixed_start_b1 = dt_util.as_utc(localdate - timedelta(days=1) + self._off_peak_start)
        fixed_end_b1 = dt_util.as_utc(localdate - timedelta(days=1) + self._off_peak_end)
        fixed_start_0 = dt_util.as_utc(localdate + self._off_peak_start)
        fixed_end_0 = dt_util.as_utc(localdate + self._off_peak_end)
        fixed_start_a1 = dt_util.as_utc(localdate + timedelta(days=1) + self._off_peak_start)
        fixed_end_a1 = dt_util.as_utc(localdate + timedelta(days=1) + self._off_peak_end)
        #fixed_start_a2 = dt_util.as_utc(localdate + timedelta(days=2) + self._off_peak_start)
        fixed_end_a2 = dt_util.as_utc(localdate + timedelta(days=2) + self._off_peak_end)

        if fixed_start_b1 > fixed_end_b1:
            all_offpeak_ranges = [
                {"start": fixed_start_b1, "end": fixed_end_0},
                {"start": fixed_start_0, "end": fixed_end_a1},
                {"start": fixed_start_a1, "end": fixed_end_a2}
            ]
        else:
            all_offpeak_ranges = [
                {"start": fixed_start_b1, "end": fixed_end_b1},
                {"start": fixed_start_0, "end": fixed_end_0},
                {"start": fixed_start_a1, "end": fixed_end_a1},
            ]

        for state in self.data.get('plannedDispatches', []):
            if state.get('meta', {}).get('source', '') == 'smart-charge':
                startUtc = datetime.strptime(state.get('startDtUtc'), '%Y-%m-%d %H:%M:%S%z').astimezone(timezone.utc)
                endUtc = datetime.strptime(state.get('endDtUtc'), '%Y-%m-%d %H:%M:%S%z').astimezone(timezone.utc)
                all_offpeak_ranges.append({"start": startUtc, "end": endUtc})

        # merge overlapping ones:
        offpeak_ranges = merge_and_sort_time_ranges(all_offpeak_ranges)

        for offpeak_range in offpeak_ranges:
            startUtc = offpeak_range["start"]
            endUtc = offpeak_range["end"]
            if startUtc <= utcnow <= endUtc or utcnow <= startUtc:
                return offpeak_range
        return None


    def is_charging_now(self, source = None, minutes_offset: int = 0):
        utcnow = dt_util.utcnow() + timedelta(minutes=minutes_offset)
        for state in self.data.get('plannedDispatches', []):
            if source is None or state.get('meta', {}).get('source', '') == source:
                startUtc = datetime.strptime(state.get('startDtUtc'), '%Y-%m-%d %H:%M:%S%z').astimezone(timezone.utc)
                endUtc = datetime.strptime(state.get('endDtUtc'), '%Y-%m-%d %H:%M:%S%z').astimezone(timezone.utc)
                if startUtc <= utcnow <= endUtc:
                    return True
        return False

    def is_off_peak_time_now(self, minutes_offset: int = 0):
        now = dt_util.now() + timedelta(minutes=minutes_offset)
        offpeak_start_mins = self._off_peak_start.seconds // 60
        offpeak_end_mins = self._off_peak_end.seconds // 60
        now_mins = now.hour * 60 + now.minute
        if (offpeak_end_mins < offpeak_start_mins):
            return now_mins >= offpeak_start_mins or now_mins <= offpeak_end_mins
        else:
            return offpeak_start_mins <= now_mins <= offpeak_end_mins

    def is_off_peak_now(self, minutes_offset: int = 0):
        return self.is_off_peak_time_now(minutes_offset) or self.is_charging_now('smart-charge', minutes_offset)

    def get_target_soc(self):
        return self.data.get('vehicleChargingPreferences', {}).get('weekdayTargetSoc', None)
    def get_target_time(self):
        return self.data.get('vehicleChargingPreferences', {}).get('weekdayTargetTime', None)

    async def async_set_target_soc(self, target_soc: int):
        target_time_str = self.get_target_time()
        if target_time_str is None:
            _LOGGER.warn("Octopus Intelligent System could not set target SOC because data is not available yet")
            return
        target_time = to_hours_after_midnight(target_time_str)
        await self.client.async_set_charge_preferences(self._account_id, target_time, target_soc)
        await self.async_refresh()

    async def async_set_target_time(self, target_time: str):
        target_soc = self.get_target_soc()
        if (target_soc is None):
            _LOGGER.warn("Octopus Intelligent System could not set target time because data is not available yet")
            return
        target_time = to_hours_after_midnight(target_time)
        await self.client.async_set_charge_preferences(self._account_id, target_time, target_soc)
        await self.async_refresh()

    async def async_start_boost_charge(self):
        await self.client.async_trigger_boost_charge(self._account_id)
    async def async_cancel_boost_charge(self):
        await self.client.async_cancel_boost_charge(self._account_id)

    async def async_remove_entry(self):
        """Called when the integration (config entry) is removed from Home Assistant."""
        await self._store.remove()

    async def start(self):
        _LOGGER.debug("Starting OctopusIntelligentSystem")
        await validate_octopus_account(self.client, self._account_id)

        await self._store.load()

    async def stop(self):
        _LOGGER.debug("Stopping OctopusIntelligentSystem")
