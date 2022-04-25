from gc import callbacks
from homeassistant.const import (
    PERCENTAGE,
)
from homeassistant.components.select import (
    SelectEntity,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .const import DOMAIN, OCTOPUS_SYSTEM, INTELLIGENT_SOC_OPTIONS, INTELLIGENT_CHARGE_TIMES
from homeassistant.core import callback
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    async_add_entities([
      OctopusIntelligentTargetSoc(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM]),
      OctopusIntelligentTargetTime(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM])], 
    True)


class OctopusIntelligentTargetSoc(CoordinatorEntity, SelectEntity):
    def __init__(self, octopus_system) -> None:
        """Initialize the select."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_target_soc"
        self._name = "Target State of Charge"
        self._octopus_system = octopus_system
        self._available = False

        self._current_option = None
        self._options = list(map(lambda x: f"{x}%", INTELLIGENT_SOC_OPTIONS))
#        self._attributes = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._available = True
        targetSoc = self._octopus_system.get_target_soc()
        self._current_option = f"{targetSoc}%"
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
    def current_option(self) -> str:
        """Return the current value."""
        return self._current_option

    @property
    def options(self) -> list:
        """Return the list of values."""
        return self._options

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        selectedTargetSoc = int(option.replace("%", ""))
        await self._octopus_system.async_set_target_soc(selectedTargetSoc)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def unit_of_measurement(self) -> bool:
        """Return the unit of measurement."""
        return PERCENTAGE

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("AccountID", self._octopus_system.account_id),
            },
            "name": "Octopus Intelligent Tariff",
            "manufacturer": "Octopus",
        }
    # @property
    # def extra_state_attributes(self):
    #     """Attributes of the sensor."""
    #     return self._attributes

    # @property
    # def should_poll(self) -> bool:
    #     """No polling needed for a sensor."""
    #     return False

    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return BinarySensorDeviceClass.RUNNING.value


class OctopusIntelligentTargetTime(CoordinatorEntity, SelectEntity):
    def __init__(self, octopus_system) -> None:
        """Initialize the select."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_target_time"
        self._name = "Target Ready By Time"
        self._octopus_system = octopus_system
        self._available = False

        self._current_option = None
        self._options = INTELLIGENT_CHARGE_TIMES

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._available = True
        targetTime = self._octopus_system.get_target_time()
        self._current_option = targetTime
        self.async_write_ha_state()

    @property
    def current_option(self) -> str:
        """Return the current value."""
        return self._current_option

    @property
    def options(self) -> list:
        """Return the list of values."""
        return self._options

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        selectedTargetTime = option
        await self._octopus_system.async_set_target_time(selectedTargetTime)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available
    
    @property
    def device_info(self):
        return {
            "identifiers": {
                ("AccountID", self._octopus_system.account_id),
            },
            "name": "Octopus Intelligent Tariff",
            "manufacturer": "Octopus",
        }
    # @property
    # def extra_state_attributes(self):
    #     """Attributes of the sensor."""
    #     return self._attributes

    # @property
    # def should_poll(self) -> bool:
    #     """No polling needed for a sensor."""
    #     return False

    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return BinarySensorDeviceClass.RUNNING.value

    