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

        self._action_widgets: list[QWidget] = []
        self._is_hovered: bool = True
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

        # Drag grip icon
        self.grip_label = QLabel("⠿", self)
        self.grip_label.setToolTip("Click and drag to move overlay")
        self.grip_label.setCursor(Qt.SizeAllCursor)
        self.grip_label.setStyleSheet(
            "color: rgba(255, 255, 255, 0.45); font-size: 14px; font-weight: bold;"
        )
        self.main_layout.addWidget(self.grip_label)

        # Monochrome status pill
        self.status_pill = QLabel("LIVE", self)
        self.status_pill.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 0.12);
            color: #ffffff;
            font-size: 9px;
            font-weight: 700;
            padding: 2px 5px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.18);
            """
        )
        self.main_layout.addWidget(self.status_pill)
        self._action_widgets.append(self.status_pill)

        # Source Toggle (Desktop Audio vs Mic) - Clean text
        self.source_btn = QPushButton(self._get_source_label(), self)
        self.source_btn.setToolTip("Toggle Desktop Audio / Microphone")
        self.source_btn.clicked.connect(self._on_source_click)
        self._style_btn(self.source_btn)
        self.main_layout.addWidget(self.source_btn)
        self._action_widgets.append(self.source_btn)

        # Pause / Resume Button - Clean text
        self.pause_btn = QPushButton("Pause", self)
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

        # Clear button - Clean monochrome text
        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.setToolTip("Clear current captions")
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        self._style_btn(self.clear_btn)
        self.main_layout.addWidget(self.clear_btn)
        self._action_widgets.append(self.clear_btn)

        # Settings gear - Monochrome white
        self.settings_btn = QPushButton("⚙", self)
        self.settings_btn.setToolTip("Settings & Model Selection")
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self._style_btn(self.settings_btn, compact=True)
        self.main_layout.addWidget(self.settings_btn)
        self._action_widgets.append(self.settings_btn)

        # Minimalist Arrow Toggle (▲ = collapse, ▼ = expand)
        self.toggle_mode_btn = QPushButton("▲", self)
        self.toggle_mode_btn.setToolTip("Collapse controls (Clean text mode)")
        self.toggle_mode_btn.clicked.connect(self._on_toggle_clean_mode)
        self._style_toggle_btn(self.toggle_mode_btn)
        self.main_layout.addWidget(self.toggle_mode_btn)

        # Close button - Monochrome white
        self.close_btn = QPushButton("✕", self)
        self.close_btn.setToolTip("Close Auto AI Live Caption")
        self.close_btn.clicked.connect(self.close_requested.emit)
        self._style_btn(self.close_btn, compact=True, is_danger=True)
        self.main_layout.addWidget(self.close_btn)
        self._action_widgets.append(self.close_btn)

        self._update_toolbar_style()

    def set_hovered(self, is_hovered: bool) -> None:
        """Update visibility based on mouse hover / window focus."""
        self._is_hovered = is_hovered
        if self.is_controls_hidden:
            # In clean mode, the toggle arrow and grip completely disappear when cursor leaves
            self.toggle_mode_btn.setVisible(is_hovered)
            self.grip_label.setVisible(is_hovered)
            self.setVisible(is_hovered)
        else:
            self.setVisible(True)
            self.toggle_mode_btn.setVisible(True)
            self.grip_label.setVisible(True)

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
                    background: rgba(20, 22, 30, 0.75);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.10);
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
            self.toggle_mode_btn.setText("▼")
            self.toggle_mode_btn.setToolTip("Expand toolbar controls")
            self.main_layout.setContentsMargins(4, 2, 4, 2)
            if not self._is_hovered:
                self.toggle_mode_btn.setVisible(False)
                self.grip_label.setVisible(False)
                self.setVisible(False)
        else:
            self.setVisible(True)
            self.toggle_mode_btn.setVisible(True)
            self.grip_label.setVisible(True)
            self.toggle_mode_btn.setText("▲")
            self.toggle_mode_btn.setToolTip("Collapse toolbar controls (Clean mode)")
            self.main_layout.setContentsMargins(8, 4, 8, 4)

        self._update_toolbar_style()

    def _get_source_label(self) -> str:
        return "Desktop" if self.is_monitor else "Mic"

    def _on_source_click(self) -> None:
        self.is_monitor = not self.is_monitor
        self.source_btn.setText(self._get_source_label())
        self.source_toggled.emit(self.is_monitor)

    def _on_pause_click(self) -> None:
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText("Resume")
            self.status_pill.setText("PAUSED")
            self.status_pill.setStyleSheet(
                """
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.45);
                font-size: 9px;
                font-weight: 700;
                padding: 2px 5px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.10);
                """
            )
        else:
            self.pause_btn.setText("Pause")
            self.status_pill.setText("LIVE")
            self.status_pill.setStyleSheet(
                """
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
                font-size: 9px;
                font-weight: 700;
                padding: 2px 5px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.18);
                """
            )
        self.pause_toggled.emit(self.is_paused)

    def set_source(self, is_monitor: bool) -> None:
        self.is_monitor = is_monitor
        self.source_btn.setText(self._get_source_label())

    def _style_toggle_btn(self, btn: QPushButton) -> None:
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.55);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 1px 7px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.35);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.25);
            }
            """
        )

    def _style_btn(
        self,
        btn: QPushButton,
        compact: bool = False,
        is_danger: bool = False,
    ) -> None:
        padding = "3px 7px" if compact else "4px 10px"
        btn.setCursor(Qt.PointingHandCursor)

        if is_danger:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 5px;
                    padding: {padding};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: rgba(220, 38, 38, 0.75);
                    color: #ffffff;
                    border: 1px solid rgba(220, 38, 38, 0.9);
                }}
                QPushButton:pressed {{
                    background-color: rgba(220, 38, 38, 0.9);
                }}
                """
            )
        else:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    border-radius: 5px;
                    padding: {padding};
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.20);
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.30);
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 0.28);
                }}
                """
            )
