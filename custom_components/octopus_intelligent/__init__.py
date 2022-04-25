"""Support for Octopus Intelligent Tariff in the UK."""
from datetime import timedelta
import datetime
import logging
import async_timeout


import homeassistant.util.dt as dt_util

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.core import HomeAssistant

from .const import(
    DOMAIN,
    OCTOPUS_SYSTEM,

    CONF_ACCOUNT_ID,
    CONF_OFFPEAK_START,
    CONF_OFFPEAK_END
)
from .graphql_client import OctopusEnergyGraphQLClient
from .util import to_timedelta, to_hours_after_midnight

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["button", "binary_sensor", "select"]
#PLATFORMS = ("button", "sensor", "binary_sensor")


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Octopus Intelligent System integration."""

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    _LOGGER.debug("Setting up Octopus Intelligent System component")

    octopus_system = OctopusIntelligentSystem(
        hass,
        api_key=entry.data[CONF_API_KEY],
        account_id=entry.data[CONF_ACCOUNT_ID],
        off_peak_start=to_timedelta(entry.data[CONF_OFFPEAK_START]),
        off_peak_end=to_timedelta(entry.data[CONF_OFFPEAK_END])
    )

    try:
        await hass.async_add_executor_job(octopus_system.start)
    except Exception as ex:
        _LOGGER.error("Got error when setting up Octopus Intelligent Integration: %s", ex)
        return False
    # except AccessDeniedError as ex:
    #     _LOGGER.error("Got Access Denied Error when setting up Gardena Smart System: %s", ex)
    #     return False
    # except InvalidClientError as ex:
    #     _LOGGER.error("Got Invalid Client Error when setting up Gardena Smart System: %s", ex)
    #     return False
    # except MissingTokenError as ex:
    #     _LOGGER.error("Got Missing Token Error when setting up Gardena Smart System: %s", ex)
    #     return False

    if entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry.entry_id] = {}

    hass.data[DOMAIN][entry.entry_id][OCTOPUS_SYSTEM] = octopus_system

    await octopus_system.async_config_entry_first_refresh()        

    #hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lambda event: octopus_system.stop())

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component))

    _LOGGER.debug("Octopus Intelligent System component setup finished")
    return True


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

    @property
    def account_id(self):
        return self._account_id

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(30):
                return await self.client.async_get_combined_state(self._account_id)
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Octopus GraphQL API: {err}")

    def is_charging_now(self):
        utcnow = dt_util.utcnow()
        for state in self.data.get('plannedDispatches', []):
            startUtc = datetime.strptime(state.get('startDtUtc'), '%Y-%m-%dT%H:%M:%S.%f%z')
            endUtc = datetime.strptime(state.get('endDtUtc'), '%Y-%m-%dT%H:%M:%S.%f%z')
            if startUtc <= utcnow <= endUtc:
                return True
        return False

    def is_off_peak_time(self):
        now = dt_util.now()
        offpeak_start_mins = self._off_peak_start.seconds // 60
        offpeak_end_mins = self._off_peak_end.seconds // 60
        now_mins = now.hour * 60 + now.minute
        if (offpeak_end_mins < offpeak_start_mins):
            return now_mins >= offpeak_start_mins or now_mins <= offpeak_end_mins
        else:
            return now_mins >= offpeak_start_mins and now_mins <= offpeak_end_mins

    def get_target_soc(self):
        return self.data.get('vehicleChargingPreferences', {}).get('weekdayTargetSoc', None)
    def get_target_time(self):
        return self.data.get('vehicleChargingPreferences', {}).get('weekdayTargetTime', None)

    async def async_set_target_soc(self, target_soc: int):
        target_time_str = self.get_target_time()
        if target_time_str is None:
            _LOGGER.warn("Octopus Intelligent System could not set target SOC because data is available yet")
            return
        target_time = to_hours_after_midnight(target_time_str)
        await self.client.async_set_charge_preferences(self._account_id, target_time, target_soc)
        await self.async_refresh()

    async def async_set_target_time(self, target_time: str):
        target_soc = self.get_target_soc()
        if (target_soc is None):
            _LOGGER.warn("Octopus Intelligent System could not set target time because data is available yet")
            return
        target_time = to_hours_after_midnight(target_time)
        await self.client.async_set_charge_preferences(self._account_id, target_time, target_soc)
        await self.async_refresh()

    async def async_start_boost_charge(self):
        await self.client.async_trigger_boost_charge(self._account_id)
    async def async_cancel_boost_charge(self):
        await self.client.async_cancel_boost_charge(self._account_id)

    async def start(self):
        _LOGGER.debug("Starting OctopusIntelligentSystem")
        try:
            accounts = await self.client.async_get_accounts()
            if (self._account_id not in accounts):
                _LOGGER.error(f"Account {self._account_id} not found in accounts {accounts}")
                raise Exception(f"Account {self._account_id} not found in accounts {accounts}")
        except Exception as ex:
            _LOGGER.error(f"Authentication failed : {ex.message}. You may need to check your token or create a new app in the gardena api and use the new token.")

    # async def stop(self):
    #     _LOGGER.debug("Stopping OctopusIntelligentSystem")
    #     # self.smart_system.quit()
