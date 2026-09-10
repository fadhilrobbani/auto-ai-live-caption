"""
System Tray Integration for Auto AI Live Caption (PySide6 / Qt6).
Provides a FreeDesktop StatusNotifierItem tray icon with left-click overlay toggle
and right-click context menu for audio source, pause, settings, and quit.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget


def get_app_icon() -> QIcon:
    """Resolve high-res vector application icon across source, PyInstaller, and system paths."""
    search_paths = []

    # 1. PyInstaller bundled path
    if hasattr(sys, "_MEIPASS"):
        search_paths.append(Path(sys._MEIPASS) / "packaging" / "assets" / "io.github.fadhilrobbani.AutoAILiveCaption.svg")
        search_paths.append(Path(sys._MEIPASS) / "io.github.fadhilrobbani.AutoAILiveCaption.svg")

    # 2. Local repository path
    current_dir = Path(__file__).resolve().parent
    search_paths.append(current_dir.parent / "packaging" / "assets" / "io.github.fadhilrobbani.AutoAILiveCaption.svg")

    # 3. System installed paths
    search_paths.append(Path("/usr/share/icons/hicolor/scalable/apps/io.github.fadhilrobbani.AutoAILiveCaption.svg"))
    search_paths.append(Path.home() / ".local/share/icons/hicolor/scalable/apps/io.github.fadhilrobbani.AutoAILiveCaption.svg")

    for p in search_paths:
        if p.exists():
            icon = QIcon(str(p))
            if not icon.isNull():
                return icon

    # Fallback: create dynamic monochrome glass icon if file not found
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(30, 41, 59))
    painter.setPen(QColor(255, 255, 255, 180))
    painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(pix.rect(), Qt.AlignCenter, "CC")
    painter.end()
    return QIcon(pix)


class CaptionTrayIcon(QSystemTrayIcon):
    """
    Taskbar system tray icon managing overlay visibility and quick actions.
    """

    toggle_overlay_requested = Signal()
    source_toggled = Signal(bool)       # True = desktop monitor, False = mic
    pause_toggled = Signal(bool)        # True = paused, False = live
    clear_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self,
        overlay: Optional[QWidget] = None,
        is_monitor: bool = True,
        is_paused: bool = False,
        parent=None,
    ):
        icon = get_app_icon()
        super().__init__(icon, parent)

        self.overlay = overlay
        self.is_monitor = is_monitor
        self.is_paused = is_paused

        self._update_tooltip()
        self._init_menu()

        # Connect activation (left click / trigger)
        self.activated.connect(self._on_activated)

    def _init_menu(self) -> None:
        self.menu = QMenu()
        self.menu.setStyleSheet(
            """
            QMenu {
                background-color: #1e2130;
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.10);
                margin: 4px 6px;
            }
            """
        )

        # 1. Show / Hide Overlay Toggle
        self.action_toggle_overlay = QAction("Hide Overlay", self)
        self.action_toggle_overlay.triggered.connect(self.toggle_overlay)
        self.menu.addAction(self.action_toggle_overlay)

        self.menu.addSeparator()

        # 2. Audio Source (Desktop Audio vs Mic)
        source_text = "Source: Desktop Audio" if self.is_monitor else "Source: Microphone"
        self.action_source = QAction(source_text, self)
        self.action_source.triggered.connect(self._on_source_click)
        self.menu.addAction(self.action_source)

        # 3. Pause / Resume Captions
        pause_text = "Resume Captions" if self.is_paused else "Pause Captions"
        self.action_pause = QAction(pause_text, self)
        self.action_pause.triggered.connect(self._on_pause_click)
        self.menu.addAction(self.action_pause)

        # 4. Clear Subtitles
        self.action_clear = QAction("Clear Subtitles", self)
        self.action_clear.triggered.connect(self.clear_requested.emit)
        self.menu.addAction(self.action_clear)

        self.menu.addSeparator()

        # 5. Settings
        self.action_settings = QAction("Settings & Models...", self)
        self.action_settings.triggered.connect(self.settings_requested.emit)
        self.menu.addAction(self.action_settings)

        self.menu.addSeparator()

        # 6. Quit
        self.action_quit = QAction("Quit Auto AI Live Caption", self)
        self.action_quit.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.action_quit)

        self.setContextMenu(self.menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle single-click or double-click to toggle overlay."""
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_overlay()

    def toggle_overlay(self) -> None:
        """Toggle overlay visibility."""
        if not self.overlay:
            self.toggle_overlay_requested.emit()
            return

        if self.overlay.isVisible():
            self.overlay.hide()
            self.action_toggle_overlay.setText("Show Overlay")
        else:
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
            self.action_toggle_overlay.setText("Hide Overlay")

        self.toggle_overlay_requested.emit()

    def _on_source_click(self) -> None:
        self.is_monitor = not self.is_monitor
        source_name = "Desktop Audio" if self.is_monitor else "Microphone"
        self.action_source.setText(f"Source: {source_name}")
        self._update_tooltip()
        self.source_toggled.emit(self.is_monitor)

    def _on_pause_click(self) -> None:
        self.is_paused = not self.is_paused
        self.action_pause.setText("Resume Captions" if self.is_paused else "Pause Captions")
        self._update_tooltip()
        self.pause_toggled.emit(self.is_paused)

    def set_source_state(self, is_monitor: bool) -> None:
        """Sync audio source state from overlay toolbar or settings."""
        self.is_monitor = is_monitor
        source_name = "Desktop Audio" if self.is_monitor else "Microphone"
        self.action_source.setText(f"Source: {source_name}")
        self._update_tooltip()

    def set_pause_state(self, is_paused: bool) -> None:
        """Sync pause state from overlay toolbar."""
        self.is_paused = is_paused
        self.action_pause.setText("Resume Captions" if self.is_paused else "Pause Captions")
        self._update_tooltip()

    def update_overlay_visibility_state(self, is_visible: bool) -> None:
        """Sync overlay visibility state."""
        self.action_toggle_overlay.setText("Hide Overlay" if is_visible else "Show Overlay")

    def _update_tooltip(self) -> None:
        status = "Paused" if self.is_paused else "Active"
        source = "Desktop" if self.is_monitor else "Mic"
        self.setToolTip(f"Auto AI Live Caption — {status} ({source})")
