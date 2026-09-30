"""Pure-function tests for charge schedule merge/format helpers."""
from datetime import datetime, timezone, timedelta
import unittest
import sys
from pathlib import Path

# Allow importing the integration package without Home Assistant installed.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components" / "octopus_intelligent"))

from util import merge_charge_slots, format_charge_windows  # noqa: E402


def _dt(hour, minute=0, day=25):
    return datetime(2024, 2, day, hour, minute, tzinfo=timezone.utc)


class MergeChargeSlotsTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_charge_slots([]), [])

    def test_merges_back_to_back_and_sums_kwh(self):
        slots = [
            {"start": _dt(1, 30), "end": _dt(2, 0), "kwh": 0.5, "source": "smart-charge"},
            {"start": _dt(2, 0), "end": _dt(3, 0), "kwh": 1.0, "source": "smart-charge"},
        ]
        merged = merge_charge_slots(slots)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["start"], _dt(1, 30))
        self.assertEqual(merged[0]["end"], _dt(3, 0))
        self.assertEqual(merged[0]["kwh"], 1.5)

    def test_keeps_gap_separate(self):
        slots = [
            {"start": _dt(22, 30), "end": _dt(23, 0), "kwh": 0.4, "source": "smart-charge"},
            {"start": _dt(3, 30, day=26), "end": _dt(5, 30, day=26), "kwh": 2.0, "source": "smart-charge"},
        ]
        merged = merge_charge_slots(slots)
        self.assertEqual(len(merged), 2)


class FormatChargeWindowsTest(unittest.TestCase):
    def test_none_when_empty(self):
        self.assertEqual(format_charge_windows([]), "none")

    def test_formats_local_clock_fields(self):
        slots = [
            {"start": _dt(22, 30), "end": _dt(23, 0)},
            {"start": _dt(3, 30, day=26), "end": _dt(5, 30, day=26)},
        ]
        self.assertEqual(
            format_charge_windows(slots),
            "22:30–23:00, 03:30–05:30",
        )


if __name__ == "__main__":
    unittest.main()
