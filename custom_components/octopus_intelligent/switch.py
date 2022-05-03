from gc import callbacks
from homeassistant.components.switch import (
    SwitchEntity,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .const import DOMAIN, OCTOPUS_SYSTEM
from homeassistant.core import callback
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([
      OctopusIntelligentBumpChargeSwitch(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM]), 
      OctopusIntelligentSmartChargeSwitch(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM])], 
    True)

class OctopusIntelligentBumpChargeSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, octopus_system) -> None:
        """Initialize the switch."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_bump_charge"
        self._name = "Octopus Bump Charge"
        self._octopus_system = octopus_system
        self._is_on = octopus_system.is_boost_charging_now()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_on = self._octopus_system.is_boost_charging_now()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._octopus_system.async_start_boost_charge()
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._octopus_system.async_cancel_boost_charge()
        self._is_on = False
        self.async_write_ha_state()

    @property
    def is_on(self):
        """Return the name of the device."""
        return self._is_on

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

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
        return "mdi:car-electric-outline"
    # @property
    # def extra_state_attributes(self):
    #     """Attributes of the sensor."""
    #     return self._attributes

    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return BinarySensorDeviceClass.RUNNING.value


class OctopusIntelligentSmartChargeSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, octopus_system) -> None:
        """Initialize the switch."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_smart_charging"
        self._name = "Octopus Smart Charging"
        self._octopus_system = octopus_system
        self._is_on = octopus_system.is_smart_charging_enabled()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._is_on = self._octopus_system.is_smart_charging_enabled()
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        await self._octopus_system.async_resume_smart_charging()
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        await self._octopus_system.async_suspend_smart_charging()
        self._is_on = False
        self.async_write_ha_state()

    @property
    def is_on(self):
        """Return the name of the device."""
        return self._is_on

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

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
        return "mdi:flash-auto"
    # @property
    # def extra_state_attributes(self):
    #     """Attributes of the sensor."""
    #     return self._attributes

    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return BinarySensorDeviceClass.RUNNING.value

    