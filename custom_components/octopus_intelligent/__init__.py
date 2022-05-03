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

PLATFORMS = ["switch", "binary_sensor", "select"]

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

