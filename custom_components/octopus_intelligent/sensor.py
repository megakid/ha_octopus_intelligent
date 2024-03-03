from gc import callbacks
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_utc_time_change
)
from .const import DOMAIN, OCTOPUS_SYSTEM
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.util import slugify
import homeassistant.util.dt as dt_util

import logging
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    async_add_entities([
        OctopusIntelligentNextOffpeakTime(
            hass, 
            hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM]),
        OctopusIntelligentOffpeakEndTime(
            hass, 
            hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM]),
    ], False)  # False: data was already fetched by __init__.py async_setup_entry()


class OctopusIntelligentNextOffpeakTime(CoordinatorEntity, SensorEntity):
    def __init__(self, hass, octopus_system) -> None:
        """Initialize the sensor."""
        super().__init__(octopus_system)
        self._name = "Octopus Intelligent Next Offpeak Start"
        self._unique_id = slugify(self._name)
        self._octopus_system = octopus_system
        self._timer = async_track_utc_time_change(
            hass, self.timer_update, minute=range(0, 60, 30), second=1)
        
        self._attributes = {}
        self._native_value = None
        self._set_native_value(log_on_error=False)

    def _set_native_value(self, log_on_error = True):
        try:
            self._native_value = self._octopus_system.next_offpeak_start_utc()
            return True
        except:
            if log_on_error:
                _LOGGER.exception("Could not set native_value")
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._set_native_value():
            self.async_write_ha_state()

    @callback
    async def timer_update(self, time):
        """Refresh state when timer is fired."""
        if self._set_native_value():
            self.async_write_ha_state()
    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def native_value(self) -> bool:
        """Return the value of the sensor."""
        return self._native_value

    @property
    def extra_state_attributes(self):
        """Attributes of the sensor."""
        return self._attributes
        
    @property
    def device_class(self):
        """Device class of sensor"""
        return SensorDeviceClass.TIMESTAMP

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("AccountID", self._octopus_system.account_id),
            },
            "name": "Octopus Intelligent Tariff",
            "manufacturer": "Octopus",
        }        
    @property
    def icon(self):
        """Icon of the entity."""
        return "mdi:home-clock-outline"

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._timer()


class OctopusIntelligentOffpeakEndTime(CoordinatorEntity, SensorEntity):
    def __init__(self, hass, octopus_system) -> None:
        """Initialize the sensor."""
        super().__init__(octopus_system)
        self._name = "Octopus Intelligent Offpeak End"
        self._unique_id = slugify(self._name)
        self._octopus_system = octopus_system
        self._timer = async_track_utc_time_change(
            hass, self.timer_update, minute=range(0, 60, 30), second=1)
        
        self._attributes = {}
        self._native_value = None
        self._set_native_value(log_on_error=False)

    def _set_native_value(self, log_on_error = True):
        utcnow = dt_util.utcnow()
        offpeak_range = self._octopus_system.next_offpeak_range_utc()
        # Only update if we're in an offpeak window now
        if offpeak_range["start"] <= utcnow:
            try:
                self._native_value = offpeak_range["end"]
                return True
            except:
                if log_on_error:
                    _LOGGER.exception("Could not set native_value")
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._set_native_value():
            self.async_write_ha_state()

    @callback
    async def timer_update(self, time):
        """Refresh state when timer is fired."""
        if self._set_native_value():
            self.async_write_ha_state()

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def native_value(self) -> bool:
        """Return the value of the sensor."""
        return self._native_value

    @property
    def extra_state_attributes(self):
        """Attributes of the sensor."""
        return self._attributes
        
    @property
    def device_class(self):
        """Device class of sensor"""
        return SensorDeviceClass.TIMESTAMP

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("AccountID", self._octopus_system.account_id),
            },
            "name": "Octopus Intelligent Tariff",
            "manufacturer": "Octopus",
        }        
    @property
    def icon(self):
        """Icon of the entity."""
        return "mdi:timelapse"

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._timer()

