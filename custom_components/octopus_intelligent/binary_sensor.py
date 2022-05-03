from gc import callbacks
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .const import DOMAIN, OCTOPUS_SYSTEM
from homeassistant.core import callback
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([OctopusIntelligentSlot(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM])], True)


class OctopusIntelligentSlot(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, octopus_system) -> None:
        """Initialize the binary sensor."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_slot"
        self._name = "Octopus Intelligent Slot"
        self._octopus_system = octopus_system
        
        self._attributes = {}
        self._is_on = self._octopus_system.is_off_peak_time() or self._octopus_system.is_off_peak_charging_now()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_on = self._octopus_system.is_off_peak_time() or self._octopus_system.is_off_peak_charging_now()
        self._attributes = self.coordinator.data
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
    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return BinarySensorDeviceClass.RUNNING.value

    