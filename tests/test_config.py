"""
Unit tests for core.config.manager.
"""

import tempfile
import unittest
from pathlib import Path

from core.config.manager import ConfigManager, AppConfig


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.json"
        self.manager = ConfigManager(config_file=self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_config(self):
        cfg = self.manager.config
        self.assertIsInstance(cfg, AppConfig)
        self.assertEqual(cfg.font_size, 18)
        self.assertEqual(cfg.is_monitor, True)
        self.assertEqual(cfg.always_on_top, True)
        self.assertEqual(cfg.overlay_opacity, 0.20)

    def test_save_and_load(self):
        self.manager.update(
            font_size=24,
            language="id",
            groq_api_key="gsk_test_key_123",
        )
        self.assertTrue(self.config_path.exists())

        # Load fresh in another instance
        manager2 = ConfigManager(config_file=self.config_path)
        cfg2 = manager2.config
        self.assertEqual(cfg2.font_size, 24)
        self.assertEqual(cfg2.language, "id")
        self.assertEqual(cfg2.groq_api_key, "gsk_test_key_123")

    def test_corrupt_json_fallback(self):
        with open(self.config_path, "w") as f:
            f.write("{invalid_json: true")

        manager = ConfigManager(config_file=self.config_path)
        # Should cleanly return default AppConfig without raising
        self.assertEqual(manager.config.font_size, 18)


if __name__ == "__main__":
    unittest.main()
