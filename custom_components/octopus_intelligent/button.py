from homeassistant.components.button import (
    ButtonEntity,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .const import DOMAIN, OCTOPUS_SYSTEM
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([
      StartBoostCharge(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM]),
      CancelBoostCharge(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM])], 
    True)



class StartBoostCharge(CoordinatorEntity,ButtonEntity):
    """Representation of a boost charge button."""

    def __init__(self, octopus_system) -> None:
        """Initialize the button."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_start_bump_charge"
        self._name = "Start Bump Charge"
        self._octopus_system = octopus_system

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    async def async_press(self, **kwargs):
        """Send the command."""
        _LOGGER.debug("Start boost charge: %s", self.name)
        await self._octopus_system.async_start_boost_charge()

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("AccountID", self._octopus_system.account_id),
            },
            "name": "Octopus Intelligent Tariff",
            "manufacturer": "Octopus",
        }

class CancelBoostCharge(CoordinatorEntity,ButtonEntity):
    """Representation of a cancel boost charge button."""

    def __init__(self, octopus_system) -> None:
        """Initialize the button."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_cancel_bump_charge"
        self._name = "Cancel Bump Charge"
        self._octopus_system = octopus_system


    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    async def async_press(self, **kwargs):
        """Send the command."""
        _LOGGER.debug("Cancel boost charge: %s", self.name)
        await self._octopus_system.async_cancel_boost_charge()

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("AccountID", self._octopus_system.account_id),
            },
            "name": "Octopus Intelligent Tariff",
            "manufacturer": "Octopus",
        }
