"""Setup, retry and removal behaviour of the config entry."""
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.octopus_intelligent import async_remove_entry
from custom_components.octopus_intelligent.const import DOMAIN
from custom_components.octopus_intelligent.graphql_util import InvalidAuthError


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="A-1234",
        data={
            "api_key": "key",
            "account_id": "A-1234",
            "offpeak_start": "23:30",
            "offpeak_end": "05:30",
        },
    )


async def test_setup_is_retried_when_octopus_is_unreachable(hass):
    """A transient Octopus outage must retry, not fail the entry for good."""
    entry = _entry()
    entry.add_to_hass(hass)

    with patch(
        "custom_components.octopus_intelligent.OctopusIntelligentSystem.start",
        side_effect=Exception("502 Bad Gateway"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_remove_entry_that_never_finished_setup(hass):
    """Deleting an entry whose setup failed must not raise."""
    entry = _entry()
    entry.add_to_hass(hass)

    with patch(
        "custom_components.octopus_intelligent.OctopusIntelligentSystem.start",
        side_effect=Exception("502 Bad Gateway"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)

    await async_remove_entry(hass, entry)


async def test_setup_fails_without_retry_on_invalid_auth(hass):
    """Retrying cannot fix a rejected API key, so the entry must not retry."""
    entry = _entry()
    entry.add_to_hass(hass)

    with patch(
        "custom_components.octopus_intelligent.OctopusIntelligentSystem.start",
        side_effect=InvalidAuthError("Authentication failed"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_ERROR
