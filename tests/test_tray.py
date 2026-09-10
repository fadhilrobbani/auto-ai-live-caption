"""
Unit tests for PySide6 System Tray Integration (CaptionTrayIcon).
Tested in headless/offscreen Qt environment.
"""

import os
import unittest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from core.config.manager import ConfigManager
from ui.overlay import OverlayWindow
from ui.tray import CaptionTrayIcon, get_app_icon

# Ensure offscreen platform for headless unit testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestCaptionTrayIcon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def setUp(self):
        self.config_mgr = ConfigManager()
        self.overlay = OverlayWindow(config_manager=self.config_mgr)
        self.tray = CaptionTrayIcon(
            overlay=self.overlay,
            is_monitor=True,
            is_paused=False,
            parent=None,
        )

    def tearDown(self):
        self.tray.hide()
        self.tray.deleteLater()
        self.overlay._force_close = True
        self.overlay.close()
        self.overlay.deleteLater()
        self.app.processEvents()

    def test_get_app_icon(self):
        icon = get_app_icon()
        self.assertIsNotNone(icon)
        self.assertFalse(icon.isNull())

    def test_tray_initialization(self):
        self.assertIsNotNone(self.tray)
        self.assertTrue(self.tray.is_monitor)
        self.assertFalse(self.tray.is_paused)
        self.assertIn("Active", self.tray.toolTip())
        self.assertIn("Desktop", self.tray.toolTip())

    def test_toggle_overlay_action(self):
        self.overlay.show()
        self.app.processEvents()
        self.assertTrue(self.overlay.isVisible())

        # Toggle via method (simulates click or menu trigger)
        self.tray.toggle_overlay()
        self.app.processEvents()
        self.assertFalse(self.overlay.isVisible())
        self.assertEqual(self.tray.action_toggle_overlay.text(), "Show Overlay")

        self.tray.toggle_overlay()
        self.app.processEvents()
        self.assertTrue(self.overlay.isVisible())
        self.assertEqual(self.tray.action_toggle_overlay.text(), "Hide Overlay")

    def test_activation_trigger(self):
        self.overlay.show()
        self.app.processEvents()
        self.assertTrue(self.overlay.isVisible())

        # Simulate left click activation
        self.tray._on_activated(QSystemTrayIcon.Trigger)
        self.app.processEvents()
        self.assertFalse(self.overlay.isVisible())

        self.tray._on_activated(QSystemTrayIcon.Trigger)
        self.app.processEvents()
        self.assertTrue(self.overlay.isVisible())

    def test_source_action_and_signal(self):
        emitted = []
        self.tray.source_toggled.connect(lambda s: emitted.append(s))

        self.tray.action_source.trigger()
        self.assertFalse(self.tray.is_monitor)
        self.assertIn(False, emitted)
        self.assertIn("Microphone", self.tray.action_source.text())
        self.assertIn("Mic", self.tray.toolTip())

        self.tray.action_source.trigger()
        self.assertTrue(self.tray.is_monitor)
        self.assertIn(True, emitted)
        self.assertIn("Desktop Audio", self.tray.action_source.text())

    def test_pause_action_and_signal(self):
        emitted = []
        self.tray.pause_toggled.connect(lambda p: emitted.append(p))

        self.tray.action_pause.trigger()
        self.assertTrue(self.tray.is_paused)
        self.assertIn(True, emitted)
        self.assertEqual(self.tray.action_pause.text(), "Resume Captions")
        self.assertIn("Paused", self.tray.toolTip())

        self.tray.action_pause.trigger()
        self.assertFalse(self.tray.is_paused)
        self.assertIn(False, emitted)
        self.assertEqual(self.tray.action_pause.text(), "Pause Captions")
        self.assertIn("Active", self.tray.toolTip())

    def test_clear_settings_quit_signals(self):
        clear_called = []
        settings_called = []
        quit_called = []

        self.tray.clear_requested.connect(lambda: clear_called.append(True))
        self.tray.settings_requested.connect(lambda: settings_called.append(True))
        self.tray.quit_requested.connect(lambda: quit_called.append(True))

        self.tray.action_clear.trigger()
        self.assertEqual(len(clear_called), 1)

        self.tray.action_settings.trigger()
        self.assertEqual(len(settings_called), 1)

        self.tray.action_quit.trigger()
        self.assertEqual(len(quit_called), 1)

    def test_state_synchronization(self):
        # Sync source state externally
        self.tray.set_source_state(False)
        self.assertFalse(self.tray.is_monitor)
        self.assertIn("Microphone", self.tray.action_source.text())

        # Sync pause state externally
        self.tray.set_pause_state(True)
        self.assertTrue(self.tray.is_paused)
        self.assertEqual(self.tray.action_pause.text(), "Resume Captions")

        # Sync overlay visibility externally
        self.tray.update_overlay_visibility_state(False)
        self.assertEqual(self.tray.action_toggle_overlay.text(), "Show Overlay")
        self.tray.update_overlay_visibility_state(True)
        self.assertEqual(self.tray.action_toggle_overlay.text(), "Hide Overlay")


if __name__ == "__main__":
    unittest.main()
