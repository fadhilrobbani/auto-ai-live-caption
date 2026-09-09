"""
Hover-Revealed Control Toolbar for the Floating Caption Overlay.
Provides quick actions: Pause/Resume, Mic/Desktop toggle, Font sizing,
Settings modal, and a Clean Mode toggle to hide/reveal all buttons.
"""

from typing import Callable, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QWidget,
)


class ControlToolbar(QWidget):
    """
    Subtle glassmorphic toolbar with quick controls and a Clean Mode toggle
    to collapse buttons for a distraction-free full-text view.
    """

    pause_toggled = Signal(bool)          # True if paused
    source_toggled = Signal(bool)         # True if monitor, False if mic
    font_size_changed = Signal(int)       # Delta (-2 or +2)
    clear_requested = Signal()
    settings_requested = Signal()
    close_requested = Signal()
    hide_controls_toggled = Signal(bool)  # True if hidden (clean mode)

    def __init__(self, is_monitor: bool = True, initial_hidden: bool = False, parent=None):
        super().__init__(parent)
        self.is_monitor = is_monitor
        self.is_paused = False
        self.is_controls_hidden = initial_hidden

        self._action_widgets: List[QWidget] = []
        self._init_ui()
        if self.is_controls_hidden:
            self.set_controls_hidden(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if not isinstance(child, (QPushButton, QToolButton)):
                win = self.window()
                if hasattr(win, "start_system_move"):
                    win.start_system_move()
                    event.accept()
                    return
        super().mousePressEvent(event)

    def _init_ui(self) -> None:
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 4, 8, 4)
        self.main_layout.setSpacing(6)

        # Drag grip icon / label
        self.grip_label = QLabel("⠿", self)
        self.grip_label.setToolTip("Click and drag to move overlay")
        self.grip_label.setCursor(Qt.SizeAllCursor)
        self.grip_label.setStyleSheet(
            "color: rgba(255, 255, 255, 0.4); font-size: 16px; font-weight: bold;"
        )
        self.main_layout.addWidget(self.grip_label)

        # Status indicator pill
        self.status_pill = QLabel("LIVE", self)
        self.status_pill.setStyleSheet(
            """
            background-color: #10b981;
            color: #ffffff;
            font-size: 10px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            """
        )
        self.main_layout.addWidget(self.status_pill)
        self._action_widgets.append(self.status_pill)

        # Source Toggle (Desktop Audio vs Mic)
        self.source_btn = QPushButton(self._get_source_label(), self)
        self.source_btn.setToolTip("Toggle Desktop Audio / Microphone")
        self.source_btn.clicked.connect(self._on_source_click)
        self._style_btn(self.source_btn)
        self.main_layout.addWidget(self.source_btn)
        self._action_widgets.append(self.source_btn)

        # Pause / Resume Button
        self.pause_btn = QPushButton("⏸ Pause", self)
        self.pause_btn.setToolTip("Pause / Resume live captioning")
        self.pause_btn.clicked.connect(self._on_pause_click)
        self._style_btn(self.pause_btn)
        self.main_layout.addWidget(self.pause_btn)
        self._action_widgets.append(self.pause_btn)

        self.spacer = self.main_layout.addStretch()

        # Font decrease
        self.font_dec_btn = QPushButton("A-", self)
        self.font_dec_btn.setToolTip("Decrease font size")
        self.font_dec_btn.clicked.connect(lambda: self.font_size_changed.emit(-2))
        self._style_btn(self.font_dec_btn, compact=True)
        self.main_layout.addWidget(self.font_dec_btn)
        self._action_widgets.append(self.font_dec_btn)

        # Font increase
        self.font_inc_btn = QPushButton("A+", self)
        self.font_inc_btn.setToolTip("Increase font size")
        self.font_inc_btn.clicked.connect(lambda: self.font_size_changed.emit(+2))
        self._style_btn(self.font_inc_btn, compact=True)
        self.main_layout.addWidget(self.font_inc_btn)
        self._action_widgets.append(self.font_inc_btn)

        # Clear button
        self.clear_btn = QPushButton("🧹 Clear", self)
        self.clear_btn.setToolTip("Clear current captions")
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        self._style_btn(self.clear_btn)
        self.main_layout.addWidget(self.clear_btn)
        self._action_widgets.append(self.clear_btn)

        # Settings gear
        self.settings_btn = QPushButton("⚙", self)
        self.settings_btn.setToolTip("Settings & Model Selection")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self._style_btn(self.settings_btn, compact=True)
        self.main_layout.addWidget(self.settings_btn)
        self._action_widgets.append(self.settings_btn)

        # Clean Mode / Toggle Buttons Button (Always accessible)
        self.toggle_mode_btn = QPushButton("▲ Clean", self)
        self.toggle_mode_btn.setToolTip("Hide buttons for clean text-only view (Click to restore)")
        self.toggle_mode_btn.clicked.connect(self._on_toggle_clean_mode)
        self._style_btn(self.toggle_mode_btn, is_accent=True)
        self.main_layout.addWidget(self.toggle_mode_btn)

        # Close button
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setToolTip("Close Auto AI Live Caption")
        self.close_btn.clicked.connect(self.close_requested.emit)
        self._style_btn(self.close_btn, compact=True, is_danger=True)
        self.main_layout.addWidget(self.close_btn)
        self._action_widgets.append(self.close_btn)

        self._update_toolbar_style()

    def _update_toolbar_style(self) -> None:
        if self.is_controls_hidden:
            self.setStyleSheet(
                """
                QWidget {
                    background: transparent;
                    border: none;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QWidget {
                    background: rgba(26, 28, 38, 0.92);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                }
                """
            )

    def _on_toggle_clean_mode(self) -> None:
        """Toggle clean text-only mode."""
        self.set_controls_hidden(not self.is_controls_hidden)
        self.hide_controls_toggled.emit(self.is_controls_hidden)

    def set_controls_hidden(self, hidden: bool) -> None:
        """Hide or reveal the action buttons."""
        self.is_controls_hidden = hidden
        for w in self._action_widgets:
            w.setVisible(not hidden)

        if hidden:
            self.toggle_mode_btn.setText("▼ Controls")
            self.toggle_mode_btn.setToolTip("Restore toolbar buttons")
            self.main_layout.setContentsMargins(4, 2, 4, 2)
        else:
            self.toggle_mode_btn.setText("▲ Clean")
            self.toggle_mode_btn.setToolTip("Hide buttons for clean text-only view")
            self.main_layout.setContentsMargins(8, 4, 8, 4)

        self._update_toolbar_style()

    def _get_source_label(self) -> str:
        return "🔊 Desktop" if self.is_monitor else "🎙 Mic"

    def _on_source_click(self) -> None:
        self.is_monitor = not self.is_monitor
        self.source_btn.setText(self._get_source_label())
        self.source_toggled.emit(self.is_monitor)

    def _on_pause_click(self) -> None:
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("▶ Resume")
            self.status_pill.setText("PAUSED")
            self.status_pill.setStyleSheet(
                """
                background-color: #f59e0b;
                color: #ffffff;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 6px;
                border-radius: 4px;
                """
            )
        else:
            self.pause_btn.setText("⏸ Pause")
            self.status_pill.setText("LIVE")
            self.status_pill.setStyleSheet(
                """
                background-color: #10b981;
                color: #ffffff;
                font-size: 10px;
                font-weight: 800;
                padding: 2px 6px;
                border-radius: 4px;
                """
            )
        self.pause_toggled.emit(self.is_paused)

    def set_source(self, is_monitor: bool) -> None:
        self.is_monitor = is_monitor
        self.source_btn.setText(self._get_source_label())

    def _style_btn(
        self,
        btn: QPushButton,
        compact: bool = False,
        is_danger: bool = False,
        is_accent: bool = False,
    ) -> None:
        padding = "3px 7px" if compact else "4px 10px"
        btn.setCursor(Qt.PointingHandCursor)

        if is_accent:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(59, 130, 246, 0.25);
                    color: #93c5fd;
                    border: 1px solid rgba(59, 130, 246, 0.4);
                    border-radius: 6px;
                    padding: {padding};
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: rgba(59, 130, 246, 0.45);
                    color: #ffffff;
                    border: 1px solid rgba(59, 130, 246, 0.7);
                }}
                QPushButton:pressed {{
                    background-color: rgba(59, 130, 246, 0.6);
                }}
                """
            )
        elif is_danger:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(239, 68, 68, 0.15);
                    color: #fca5a5;
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    border-radius: 6px;
                    padding: {padding};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #ef4444;
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.4);
                }}
                """
            )
        else:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #e2e8f0;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: {padding};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.18);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.25);
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 0.25);
                }}
                """
            )
