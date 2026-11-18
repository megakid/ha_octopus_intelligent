"""Options flow tests."""
from unittest.mock import patch

from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.octopus_intelligent.const import DOMAIN


async def test_options_flow_opens_and_updates_entry(hass):
    """Configure must open (issue #70) and save a new API key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="A-1234",
        data={
            "id": "A-1234",
            "api_key": "old-key",
            "account_id": "A-1234",
            "offpeak_start": "23:30",
            "offpeak_end": "05:30",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    with patch("custom_components.octopus_intelligent.config_flow.try_connection"):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "api_key": "new-key",
                "account_id": "A-1234",
                "offpeak_start": "23:30",
                "offpeak_end": "05:30",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data["api_key"] == "new-key"
