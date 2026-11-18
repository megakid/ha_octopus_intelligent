"""Setting the target SOC re-submits the cached ready-by time."""
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.octopus_intelligent.octopus_intelligent_system import (
    OctopusIntelligentSystem,
)


def _system(hass, ready_by: str) -> OctopusIntelligentSystem:
    system = OctopusIntelligentSystem(
        hass,
        api_key="key",
        account_id="A-1234",
        off_peak_start=timedelta(hours=23, minutes=30),
        off_peak_end=timedelta(hours=5, minutes=30),
    )
    system.data = {
        "vehicleChargingPreferences": {
            "weekdayTargetTime": ready_by,
            "weekdayTargetSoc": 80,
        }
    }
    system.client = AsyncMock()
    return system


async def test_target_soc_rejected_when_cached_ready_by_is_midnight(hass):
    """Octopus reports 00:00 with no schedule; the API would reject that time."""
    system = _system(hass, "00:00")

    with pytest.raises(HomeAssistantError, match="Ready By Time"):
        await system.async_set_target_soc(90)

    system.client.async_set_charge_preferences.assert_not_called()


async def test_target_soc_is_sent_with_valid_ready_by_time(hass):
    system = _system(hass, "08:00")

    with patch.object(system, "async_refresh", new=AsyncMock()):
        await system.async_set_target_soc(90)

    system.client.async_set_charge_preferences.assert_awaited_once_with(
        "A-1234", 8.0, 90
    )
