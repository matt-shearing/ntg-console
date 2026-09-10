from __future__ import annotations

import unittest

from ntg_console.settings import SETTINGS_VERSION, apply_disk, migrate


class MigrateTests(unittest.TestCase):
    def test_stock_calls_drops_compressor(self) -> None:
        data = migrate(
            {
                "hpf_hz": 75,
                "pad": False,
                "hf_boost": False,
                "suppress": True,
                "gate": True,
                "gate_threshold_db": -42,
                "comp": True,
                "comp_amount": 0.55,
                "bottom": False,
                "excite": False,
                "lock_usb": True,
                "settings_version": 1,
            }
        )
        self.assertFalse(data["comp"])
        self.assertTrue(data["claim_default"])
        self.assertTrue(data["steer_apps"])
        self.assertEqual(data["settings_version"], SETTINGS_VERSION)

    def test_custom_compressor_is_kept(self) -> None:
        data = migrate(
            {
                "hpf_hz": 75,
                "suppress": True,
                "gate": True,
                "comp": True,
                "comp_amount": 0.8,
                "bottom": False,
                "excite": False,
                "pad": False,
                "settings_version": 1,
            }
        )
        self.assertTrue(data["comp"])
        self.assertEqual(data["settings_version"], SETTINGS_VERSION)

    def test_v2_is_left_alone(self) -> None:
        data = migrate(
            {
                "comp": True,
                "comp_amount": 0.55,
                "settings_version": SETTINGS_VERSION,
            }
        )
        self.assertTrue(data["comp"])

    def test_old_file_without_version_is_v1(self) -> None:
        data = apply_disk(
            {
                "hpf_hz": 75,
                "pad": False,
                "suppress": True,
                "gate": True,
                "comp": True,
                "comp_amount": 0.55,
                "bottom": False,
                "excite": False,
                "lock_usb": True,
            }
        )
        self.assertFalse(data["comp"])
        self.assertEqual(data["settings_version"], SETTINGS_VERSION)
        self.assertTrue(data["claim_default"])


if __name__ == "__main__":
    unittest.main()
