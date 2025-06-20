"""Support for Octopus Intelligent Tariff in the UK."""
import logging
from .octopus_intelligent_system import OctopusIntelligentSystem


import homeassistant.util.dt as dt_util

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
)
from homeassistant.core import HomeAssistant

from .const import(
    DOMAIN,
    OCTOPUS_SYSTEM,

    CONF_ACCOUNT_ID,
    CONF_OFFPEAK_START,
    CONF_OFFPEAK_END
)
from .util import to_timedelta

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch", "binary_sensor", "select", "sensor"]

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
        await octopus_system.start()
    except Exception as ex:
        _LOGGER.error("Got error when setting up Octopus Intelligent Integration: %s", ex)
        return False

    if entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][entry.entry_id] = {}

    hass.data[DOMAIN][entry.entry_id][OCTOPUS_SYSTEM] = octopus_system

    await octopus_system.async_config_entry_first_refresh()        

    #hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lambda event: octopus_system.stop())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("Octopus Intelligent System component setup finished")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Octopus Intelligent config entry."""
    _LOGGER.debug("Unloading Octopus Intelligent System component")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up the system instance
        if entry.entry_id in hass.data[DOMAIN]:
            octopus_system: OctopusIntelligentSystem = (
                hass.data[DOMAIN][entry.entry_id].get(OCTOPUS_SYSTEM)
            )
            if octopus_system:
                try:
                    await octopus_system.async_remove_entry()
                except Exception as ex:  # pylint: disable=broad-exception-caught
                    _LOGGER.error("Error during unload: %s", ex)
            
            # Remove the entry data
            hass.data[DOMAIN].pop(entry.entry_id)
    
    _LOGGER.debug("Octopus Intelligent System component unload finished")
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Called when the config entry is removed (the integration is deleted)."""
    octopus_system: OctopusIntelligentSystem = (
        hass.data[DOMAIN][entry.entry_id][OCTOPUS_SYSTEM]
    )
    try:
        await octopus_system.async_remove_entry()
    except Exception as ex:  # pylint: disable=broad-exception-caught
        _LOGGER.error(ex)
