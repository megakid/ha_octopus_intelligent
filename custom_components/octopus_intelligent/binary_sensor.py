from gc import callbacks
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.event import (
    async_track_utc_time_change
)
from .const import DOMAIN, OCTOPUS_SYSTEM
from homeassistant.core import callback
from homeassistant.util import slugify
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([
        OctopusIntelligentSlot(
            hass, 
            hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM],
            "Octopus Intelligent Slot",
            True,
            0),
        OctopusIntelligentSlot(
            hass, 
            hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM],
            "Octopus Intelligent Slot (next 1 hour)",
            False,
            60),
        OctopusIntelligentSlot(
            hass, 
            hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM],
            "Octopus Intelligent Slot (next 2 hours)",
            False,
            120),
        OctopusIntelligentSlot(
            hass, 
            hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM],
            "Octopus Intelligent Slot (next 3 hours)",
            False,
            180)
    ], True)


class OctopusIntelligentSlot(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, hass, octopus_system, name : str, store_attributes : bool = False, look_ahead_mins : int = 0) -> None:
        """Initialize the binary sensor."""
        super().__init__(octopus_system)
        self._name = name
        self._unique_id = slugify(name)
        self._octopus_system = octopus_system
        self._store_attributes = store_attributes
        self._look_ahead_mins = look_ahead_mins
        self._timer = async_track_utc_time_change(
            hass, self.timer_update, minute=range(0, 60, 30), second=1)
        
        self._attributes = {}
        self._is_on = self._is_off_peak()

    def _is_off_peak(self):
        mins_looked = 0
        while (mins_looked <= self._look_ahead_mins):
            if not self._octopus_system.is_off_peak_now(mins_looked):
                return False
            mins_looked += 30
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_on = self._is_off_peak()
        if (self._store_attributes):
            self._attributes = self.coordinator.data
        self.async_write_ha_state()

    @callback
    async def timer_update(self, time):
        """Refresh state when timer is fired."""
        self._is_on = self._is_off_peak()
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
    def is_on(self) -> bool:
        """Return the status of the binary sensor."""
        return self._is_on

    @property
    def extra_state_attributes(self):
        """Attributes of the sensor."""
        return self._attributes
        
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
        return "mdi:home-lightning-bolt-outline"

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._timer()

