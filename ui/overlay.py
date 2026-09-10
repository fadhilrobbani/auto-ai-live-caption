"""
Floating Glassmorphism Subtitle Overlay Window for Linux (PySide6 / Qt6).
Features smooth text scrolling, draggable repositioning, and on-hover controls.
"""

from typing import Optional
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QSizeGrip,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.controls import ControlToolbar
from core.config.manager import ConfigManager, AppConfig


class OverlayWindow(QWidget):
    """
    Frameless, translucent floating caption overlay that stays on top.
    """

    font_size_changed = Signal(int)
    settings_requested = Signal()
    visibility_changed = Signal(bool)
    closed = Signal()

    def __init__(self, config_manager: Optional[ConfigManager] = None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager or ConfigManager()
        self.cfg: AppConfig = self.config_manager.config

        self._drag_pos = QPoint()
        self._is_dragging = False
        self._force_close = False

        self._init_window_flags()
        self._init_ui()
        self._restore_geometry()

    def _init_window_flags(self) -> None:
        """Configure Wayland and X11 compatible floating overlay flags."""
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(400, 100)
        self.resize(self.cfg.overlay_width, self.cfg.overlay_height)

    def _init_ui(self) -> None:
        # Outer container layout
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Card container with glassmorphic background
        self.card = QWidget(self)
        self.card.setObjectName("OverlayCard")
        self._update_card_style()

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        # Card layout: QGridLayout layers toolbar cleanly over text without layout jumps
        card_layout = QGridLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 1. Text Display Box (fills entire card area continuously)
        self.text_box = QTextEdit(self.card)
        self.text_box.setReadOnly(True)
        self.text_box.setFrameShape(QTextEdit.NoFrame)
        self.text_box.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_box.setPlaceholderText("Listening for live speech...")
        self._update_text_style()
        card_layout.addWidget(self.text_box, 0, 0)

        # 2. Top Control Toolbar (layered at top over text_box)
        self.toolbar = ControlToolbar(
            is_monitor=self.cfg.is_monitor,
            initial_hidden=getattr(self.cfg, "hide_controls", False),
            parent=self.card,
        )
        self.toolbar.font_size_changed.connect(self._adjust_font_size)
        self.toolbar.settings_requested.connect(self.settings_requested.emit)
        self.toolbar.close_requested.connect(self.close)
        self.toolbar.hide_controls_toggled.connect(self._on_hide_controls_toggled)
        card_layout.addWidget(self.toolbar, 0, 0, Qt.AlignTop)
        self.toolbar.raise_()

        # Install event filters so clicking and dragging anywhere on header or card initiates drag
        self.card.installEventFilter(self)
        self.toolbar.installEventFilter(self)
        self.toolbar.grip_label.installEventFilter(self)

        # 3. Bottom Size Grip (layered at bottom-right)
        grip_container = QWidget(self.card)
        grip_layout = QVBoxLayout(grip_container)
        grip_layout.setContentsMargins(0, 0, 4, 4)
        self.size_grip = QSizeGrip(grip_container)
        grip_layout.addWidget(self.size_grip, 0, Qt.AlignRight | Qt.AlignBottom)
        card_layout.addWidget(grip_container, 0, 0, Qt.AlignBottom | Qt.AlignRight)
        grip_container.raise_()

        outer_layout.addWidget(self.card)

        # Set initial hover state (hidden if not under mouse in clean mode)
        self._set_hovered(self.underMouse())
        self._center_text_vertically()

    def _set_hovered(self, hovered: bool) -> None:
        self.toolbar.set_hovered(hovered)
        if hasattr(self, "size_grip"):
            self.size_grip.setVisible(hovered)

    def enterEvent(self, event) -> None:
        self._set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._set_hovered(False)
        super().leaveEvent(event)

    def changeEvent(self, event) -> None:
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow() and not self.underMouse():
                self._set_hovered(False)
        super().changeEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._center_text_vertically()

    def _center_text_vertically(self) -> None:
        """
        Dynamically center caption text vertically so 1 or 2 lines of subtitles
        do not cling to the top edge leaving excessive dead whitespace below.
        """
        total_h = self.text_box.height()
        doc_h = self.text_box.document().size().height()

        # When toolbar controls are expanded, reserve space for toolbar at top
        top_offset = self.toolbar.height() if not getattr(self.toolbar, "is_controls_hidden", False) else 0
        avail_h = max(10, total_h - top_offset)

        if doc_h < avail_h:
            vertical_margin = top_offset + max(0, int((avail_h - doc_h) / 2))
        else:
            vertical_margin = top_offset

        self.text_box.setViewportMargins(0, vertical_margin, 0, 0)

    def _on_hide_controls_toggled(self, hidden: bool) -> None:
        self.cfg.hide_controls = hidden
        self.config_manager.update(hide_controls=hidden)
        if hidden:
            self._expanded_height = self.height()
            self.setMinimumHeight(60)
            if 130 <= self._expanded_height <= 170:
                self.resize(self.width(), 105)
        else:
            self.setMinimumHeight(100)
            if hasattr(self, "_expanded_height") and self._expanded_height > self.height():
                self.resize(self.width(), self._expanded_height)
            else:
                self.resize(self.width(), max(self.height(), 140))
        self._center_text_vertically()

    def set_controls_hidden(self, hidden: bool) -> None:
        self.toolbar.set_controls_hidden(hidden)
        self._on_hide_controls_toggled(hidden)

    def _update_card_style(self) -> None:
        opacity = getattr(self.cfg, "overlay_opacity", 0.25)
        effect = self.card.graphicsEffect()
        if opacity <= 0.01:
            # 100% Fully transparent mode
            self.card.setStyleSheet(
                """
                #OverlayCard {
                    background-color: transparent;
                    border: none;
                }
                """
            )
            if effect:
                effect.setEnabled(False)
        else:
            self.card.setStyleSheet(
                f"""
                #OverlayCard {{
                    background-color: rgba(15, 17, 26, {opacity});
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    border-radius: 12px;
                }}
                """
            )
            if effect:
                effect.setEnabled(True)

    def _update_text_style(self) -> None:
        font_size = getattr(self.cfg, "font_size", 18)
        font_family = getattr(self.cfg, "font_family", "sans-serif")
        self.text_box.setStyleSheet(
            f"""
            QTextEdit {{
                background: transparent;
                color: #ffffff;
                font-family: "{font_family}";
                font-size: {font_size}px;
                font-weight: 600;
                line-height: 1.4;
                padding: 6px 14px;
                selection-background-color: #3b82f6;
            }}
            """
        )

    def update_caption(self, committed: str, tentative: str) -> None:
        """
        Display current committed and tentative subtitle text.
        Equipped with subtitle text shadow for 100% readability over pure white/black screens.
        """
        opacity = getattr(self.cfg, "overlay_opacity", 0.25)
        # High contrast outline shadow for low or zero opacity
        shadow_css = (
            "text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 0 2px 4px rgba(0,0,0,0.95);"
            if opacity <= 0.5
            else "text-shadow: 0 1px 2px rgba(0,0,0,0.7);"
        )

        html_parts = []
        if committed:
            safe_hist = committed.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            html_parts.append(
                f'<span style="color: #ffffff; {shadow_css} font-weight: 600;">{safe_hist}</span>'
            )

        if tentative:
            safe_tent = tentative.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(
                f'<span style="color: #93c5fd; {shadow_css} font-weight: 600; opacity: 0.95;"> <i>{safe_tent}</i></span>'
            )

        full_html = "".join(html_parts)
        self.text_box.setHtml(full_html)
        self._center_text_vertically()

        # Auto-scroll to the bottom
        scrollbar = self.text_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _adjust_font_size(self, delta: int) -> None:
        new_size = max(12, min(36, self.cfg.font_size + delta))
        self.cfg.font_size = new_size
        self.config_manager.update(font_size=new_size)
        self._update_text_style()
        self._center_text_vertically()
        self.font_size_changed.emit(new_size)

    def set_overlay_opacity(self, opacity: float) -> None:
        self.cfg.overlay_opacity = opacity
        self.config_manager.update(overlay_opacity=opacity)
        self._update_card_style()

    def start_system_move(self) -> bool:
        """Initiate native Wayland / X11 compositor window dragging."""
        handle = self.windowHandle()
        if handle:
            return handle.startSystemMove()
        return False

    def eventFilter(self, watched, event) -> bool:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QPushButton
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            if watched in (self.card, self.toolbar, self.toolbar.grip_label):
                child = self.childAt(event.pos())
                if not isinstance(child, QPushButton):
                    if self.start_system_move():
                        return True
        return super().eventFilter(watched, event)

    # Window Dragging Logic (Cross-DE / Wayland compatible)
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if self.start_system_move():
                event.accept()
                return
            self._is_dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            self._is_dragging = False
            # Save position
            pos = self.pos()
            self.config_manager.update(overlay_x=pos.x(), overlay_y=pos.y())
            event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        size = self.size()
        self.config_manager.update(overlay_width=size.width(), overlay_height=size.height())

    def _restore_geometry(self) -> None:
        if self.cfg.overlay_x >= 0 and self.cfg.overlay_y >= 0:
            self.move(self.cfg.overlay_x, self.cfg.overlay_y)
        else:
            # Center at bottom third of primary screen
            screen = QApplication.primaryScreen()
            if screen:
                screen_geom = screen.availableGeometry()
                x = (screen_geom.width() - self.width()) // 2
                y = screen_geom.height() - self.height() - 80
                self.move(x, y)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.visibility_changed.emit(True)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.visibility_changed.emit(False)

    def closeEvent(self, event) -> None:
        if getattr(self, "_force_close", False):
            self.closed.emit()
            super().closeEvent(event)
        else:
            event.ignore()
            self.hide()
