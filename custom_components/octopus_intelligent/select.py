from gc import callbacks
from homeassistant.const import (
    PERCENTAGE,
)
from homeassistant.components.select import (
    SelectEntity,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .const import DOMAIN, OCTOPUS_SYSTEM, INTELLIGENT_SOC_OPTIONS, INTELLIGENT_CHARGE_TIMES
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
import logging
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    async_add_entities([
      OctopusIntelligentTargetSoc(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM]),
      OctopusIntelligentTargetTime(hass.data[DOMAIN][config_entry.entry_id][OCTOPUS_SYSTEM])], 
    False)  # False: data was already fetched by __init__.py async_setup_entry()


class OctopusIntelligentTargetSoc(CoordinatorEntity, SelectEntity):
    def __init__(self, octopus_system) -> None:
        """Initialize the select."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_target_soc"
        self._name = "Octopus Target State of Charge"
        self._octopus_system = octopus_system

        self._current_option = None
        self._options = list(map(lambda x: f"{x}", INTELLIGENT_SOC_OPTIONS))

    @callback
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        targetSoc = self._octopus_system.get_target_soc()
        self._current_option = f"{targetSoc}"
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
        self._current_option = option
        self.async_write_ha_state()
        
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

    @property
    def icon(self):
        """Icon of the entity."""
        return "mdi:battery-charging-medium"
        
    # @property
    # def extra_state_attributes(self):
    #     """Attributes of the sensor."""
    #     return self._attributes

    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return BinarySensorDeviceClass.RUNNING.value


class OctopusIntelligentTargetTime(CoordinatorEntity, SelectEntity):
    def __init__(self, octopus_system) -> None:
        """Initialize the select."""
        super().__init__(octopus_system)
        self._unique_id = "octopus_intelligent_target_time"
        self._name = "Octopus Target Ready By Time"
        self._octopus_system = octopus_system

        self._current_option = None
        self._options = INTELLIGENT_CHARGE_TIMES

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
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
        self._current_option = selectedTargetTime
        self.async_write_ha_state()

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
        return "mdi:clock-time-seven-outline"
    # @property
    # def extra_state_attributes(self):
    #     """Attributes of the sensor."""
    #     return self._attributes

    # @property
    # def device_class(self):
    #     """Return the class of this device, from component DEVICE_CLASSES."""
    #     return BinarySensorDeviceClass.RUNNING.value

    