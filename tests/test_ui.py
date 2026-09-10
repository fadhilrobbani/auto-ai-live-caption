"""
Unit tests for PySide6 UI layer (tested offscreen).
"""

import os
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from core.config.manager import ConfigManager
from core.models.registry import create_default_registry
from ui.controls import ControlToolbar
from ui.overlay import OverlayWindow
from ui.settings_dialog import SettingsDialog

# Ensure offscreen platform for headless unit testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.config_mgr = ConfigManager()
        self.registry = create_default_registry()

    def test_control_toolbar(self):
        toolbar = ControlToolbar(is_monitor=True)
        self.assertTrue(toolbar.is_monitor)
        self.assertFalse(toolbar.is_paused)

        events = []
        toolbar.pause_toggled.connect(lambda p: events.append(("pause", p)))
        toolbar.source_toggled.connect(lambda m: events.append(("source", m)))

        # Toggle pause
        toolbar._on_pause_click()
        self.assertTrue(toolbar.is_paused)
        self.assertIn(("pause", True), events)

        # Toggle source
        toolbar._on_source_click()
        self.assertFalse(toolbar.is_monitor)
        self.assertIn(("source", False), events)

        # Toggle clean mode (hide controls)
        clean_events = []
        toolbar.hide_controls_toggled.connect(lambda h: clean_events.append(h))
        self.assertFalse(toolbar.is_controls_hidden)
        toolbar._on_toggle_clean_mode()
        self.assertTrue(toolbar.is_controls_hidden)
        self.assertIn(True, clean_events)
        self.assertTrue(toolbar.source_btn.isHidden())
        self.assertTrue(toolbar.clear_btn.isHidden())
        self.assertFalse(toolbar.toggle_mode_btn.isHidden())

        # Restore controls
        toolbar._on_toggle_clean_mode()
        self.assertFalse(toolbar.is_controls_hidden)
        self.assertIn(False, clean_events)
        self.assertFalse(toolbar.source_btn.isHidden())

        # Test hover auto-hide in clean mode
        toolbar.set_controls_hidden(True)
        toolbar.set_hovered(False)
        self.assertTrue(toolbar.isHidden())
        self.assertTrue(toolbar.toggle_mode_btn.isHidden())
        toolbar.set_hovered(True)
        self.assertFalse(toolbar.isHidden())
        self.assertFalse(toolbar.toggle_mode_btn.isHidden())
        self.assertEqual(toolbar.toggle_mode_btn.text(), "▼")

    def test_overlay_window(self):
        overlay = OverlayWindow(config_manager=self.config_mgr)
        self.assertIsNotNone(overlay)

        # Update caption
        overlay.update_caption("Committed sentence.", "Tentative phrase")
        plain_text = overlay.text_box.toPlainText()
        self.assertIn("Committed sentence.", plain_text)
        self.assertIn("Tentative phrase", plain_text)

        # Font sizing
        curr_size = overlay.cfg.font_size
        overlay._adjust_font_size(+2)
        self.assertEqual(overlay.cfg.font_size, curr_size + 2)

        # Opacity 0.0 (fully transparent mode)
        overlay.set_overlay_opacity(0.0)
        self.assertEqual(overlay.cfg.overlay_opacity, 0.0)
        self.assertIn("background-color: transparent", overlay.card.styleSheet())

        # Clean mode toggling & geometry stability
        geom_before = overlay.text_box.geometry()
        overlay.set_controls_hidden(True)
        self.assertTrue(overlay.cfg.hide_controls)
        self.assertTrue(overlay.toolbar.is_controls_hidden)

        # Hover in/out does not shift text_box geometry
        overlay._set_hovered(False)
        self.app.processEvents()
        geom_unhovered = overlay.text_box.geometry()
        overlay._set_hovered(True)
        self.app.processEvents()
        geom_hovered = overlay.text_box.geometry()
        self.assertEqual(geom_unhovered.x(), geom_hovered.x())
        self.assertEqual(geom_unhovered.y(), geom_hovered.y())

        # Vertical centering verification
        overlay.update_caption("Short text line.", "")
        self.assertGreater(overlay.text_box.viewportMargins().top(), 0)

        overlay._force_close = True
        overlay.close()

    def test_settings_dialog(self):
        dialog = SettingsDialog(config_manager=self.config_mgr, registry=self.registry)
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.tabs.count(), 4)

        # Apply settings with opacity 0 and clean mode
        dialog.font_size_spin.setValue(22)
        dialog.opacity_slider.setValue(0)
        dialog.hide_controls_chk.setChecked(True)
        dialog.latency_combo.setCurrentIndex(0)
        applied = []
        dialog.settings_applied.connect(lambda s: applied.append(s))
        dialog._on_save()
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0]["font_size"], 22)
        self.assertEqual(applied[0]["overlay_opacity"], 0.0)
        self.assertTrue(applied[0]["hide_controls"])
        self.assertEqual(applied[0]["latency_profile"], "fast")
        self.assertIn("selected_catalog_model", applied[0])
        self.assertGreaterEqual(dialog.catalog_combo.count(), 5)

        # Test download dialog instantiation
        from core.models.catalog import get_catalog_model_by_id
        from ui.download_dialog import ModelDownloadDialog
        m = get_catalog_model_by_id("tiny.en")
        dl_dialog = ModelDownloadDialog(m)
        self.assertIsNotNone(dl_dialog)
        self.assertIn("Tiny English", dl_dialog.windowTitle())


if __name__ == "__main__":
    unittest.main()
