"""
Settings & Preferences Dialog for Auto AI Live Caption (PySide6).
Provides model switching, API key configuration, audio device selection, and appearance tuning.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.audio.device_manager import list_audio_devices, AudioDevice
from core.config.manager import ConfigManager, AppConfig
from core.models.registry import ModelRegistry


class SettingsDialog(QDialog):
    """
    Preferences modal allowing runtime model switching, device selection,
    and visual customization.
    """

    settings_applied = Signal(dict)

    def __init__(
        self,
        config_manager: ConfigManager,
        registry: ModelRegistry,
        parent=None,
    ):
        super().__init__(parent)
        self.config_manager = config_manager
        self.registry = registry
        self.cfg: AppConfig = self.config_manager.config

        self.setWindowTitle("Auto AI Live Caption — Settings")
        self.setMinimumSize(540, 420)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._create_models_tab(), "Models & APIs")
        self.tabs.addTab(self._create_audio_tab(), "Audio Source")
        self.tabs.addTab(self._create_appearance_tab(), "Appearance")
        self.tabs.addTab(self._create_language_tab(), "Language")
        main_layout.addWidget(self.tabs)

        # Bottom Button Bar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save & Apply", self)
        self.save_btn.setDefault(True)
        self.save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            """
        )
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    def _create_models_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # 1. Active Engine Selector
        group_engine = QGroupBox("Active ASR Engine")
        form_eng = QFormLayout(group_engine)

        self.model_combo = QComboBox()
        engines = self.registry.list_engines()
        for idx, eng in enumerate(engines):
            self.model_combo.addItem(eng["display_name"], eng["id"])
            if eng["id"] == self.cfg.active_engine_id:
                self.model_combo.setCurrentIndex(idx)

        form_eng.addRow("Select Engine:", self.model_combo)
        layout.addWidget(group_engine)

        # 2. Local Model Settings
        group_local = QGroupBox("Offline Local Model")
        form_local = QFormLayout(group_local)

        local_layout = QHBoxLayout()
        self.local_path_edit = QLineEdit(self.cfg.local_model_path)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse_model)
        local_layout.addWidget(self.local_path_edit)
        local_layout.addWidget(self.browse_btn)

        form_local.addRow("Model Path:", local_layout)
        layout.addWidget(group_local)

        # 3. Cloud API Keys
        group_api = QGroupBox("Cloud API Keys (Optional)")
        form_api = QFormLayout(group_api)

        self.groq_key_edit = QLineEdit(self.cfg.groq_api_key)
        self.groq_key_edit.setEchoMode(QLineEdit.Password)
        self.groq_key_edit.setPlaceholderText("gsk_...")
        form_api.addRow("Groq API Key:", self.groq_key_edit)

        self.openai_key_edit = QLineEdit(self.cfg.openai_api_key)
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        self.openai_key_edit.setPlaceholderText("sk-...")
        form_api.addRow("OpenAI API Key:", self.openai_key_edit)

        layout.addWidget(group_api)
        layout.addStretch()
        return tab

    def _create_audio_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        group_device = QGroupBox("Capture Source")
        form = QFormLayout(group_device)

        # Specific Device Picker
        self.device_combo = QComboBox()
        devices = list_audio_devices()
        current_id = self.cfg.audio_device_id

        selected_idx = 0
        for idx, dev in enumerate(devices):
            prefix = "🔊 [Desktop]" if dev.is_monitor else "🎙 [Mic]"
            self.device_combo.addItem(f"{prefix} {dev.description}", dev.id)
            if current_id and dev.id == current_id:
                selected_idx = idx

        self.device_combo.setCurrentIndex(selected_idx)
        form.addRow("Audio Device:", self.device_combo)

        layout.addWidget(group_device)
        layout.addStretch()
        return tab

    def _create_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        group = QGroupBox("Overlay Appearance")
        form = QFormLayout(group)

        # Font Size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 36)
        self.font_size_spin.setValue(self.cfg.font_size)
        form.addRow("Font Size (px):", self.font_size_spin)

        # Overlay Opacity Slider (0% to 100%)
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.cfg.overlay_opacity * 100))
        self.opacity_label = QLabel()
        
        def _update_opacity_text(v):
            if v == 0:
                self.opacity_label.setText("0% (Fully Transparent)")
            else:
                self.opacity_label.setText(f"{v}%")

        self.opacity_slider.valueChanged.connect(_update_opacity_text)
        _update_opacity_text(self.opacity_slider.value())

        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        form.addRow("Overlay Opacity:", opacity_layout)

        # Always on Top
        self.always_on_top_chk = QCheckBox("Keep overlay always on top")
        self.always_on_top_chk.setChecked(self.cfg.always_on_top)
        form.addRow("", self.always_on_top_chk)

        # Clean text-only mode
        self.hide_controls_chk = QCheckBox("Clean mode (hide toolbar buttons for full text)")
        self.hide_controls_chk.setChecked(getattr(self.cfg, "hide_controls", False))
        form.addRow("", self.hide_controls_chk)

        layout.addWidget(group)
        layout.addStretch()
        return tab

    def _create_language_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = QGroupBox("Spoken Language")
        form = QFormLayout(group)

        self.lang_combo = QComboBox()
        languages = [
            ("Auto-Detect (Multilingual)", "auto"),
            ("English", "en"),
            ("Indonesian (Bahasa Indonesia)", "id"),
            ("Japanese (日本語)", "ja"),
            ("Chinese (中文)", "zh"),
            ("Spanish (Español)", "es"),
            ("German (Deutsch)", "de"),
            ("French (Français)", "fr"),
            ("Russian (Русский)", "ru"),
            ("Arabic (العربية)", "ar"),
        ]
        curr_lang = self.cfg.language
        sel_idx = 0
        for idx, (label, code) in enumerate(languages):
            self.lang_combo.addItem(label, code)
            if code == curr_lang:
                sel_idx = idx

        self.lang_combo.setCurrentIndex(sel_idx)
        form.addRow("Spoken Language:", self.lang_combo)

        layout.addWidget(group)
        layout.addStretch()
        return tab

    def _on_browse_model(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Local Faster-Whisper Model Directory", self.local_path_edit.text()
        )
        if dir_path:
            self.local_path_edit.setText(dir_path)

    def _on_save(self) -> None:
        active_eng_id = self.model_combo.currentData()
        device_id = self.device_combo.currentData()
        # Check if device is monitor from id
        is_monitor = (device_id == "@DEFAULT_MONITOR@") or (".monitor" in str(device_id).lower())

        font_size = self.font_size_spin.value()
        opacity = self.opacity_slider.value() / 100.0
        always_on_top = self.always_on_top_chk.isChecked()
        hide_controls = self.hide_controls_chk.isChecked()
        language = self.lang_combo.currentData()
        local_model_path = self.local_path_edit.text().strip()
        groq_api_key = self.groq_key_edit.text().strip()
        openai_api_key = self.openai_key_edit.text().strip()

        # Update in-memory and on-disk config
        self.config_manager.update(
            active_engine_id=active_eng_id,
            audio_device_id=device_id,
            is_monitor=is_monitor,
            font_size=font_size,
            overlay_opacity=opacity,
            always_on_top=always_on_top,
            hide_controls=hide_controls,
            language=language,
            local_model_path=local_model_path,
            groq_api_key=groq_api_key,
            openai_api_key=openai_api_key,
        )

        # Notify listeners
        changes = {
            "active_engine_id": active_eng_id,
            "audio_device_id": device_id,
            "is_monitor": is_monitor,
            "font_size": font_size,
            "overlay_opacity": opacity,
            "always_on_top": always_on_top,
            "hide_controls": hide_controls,
            "language": language,
            "local_model_path": local_model_path,
            "groq_api_key": groq_api_key,
            "openai_api_key": openai_api_key,
        }
        self.settings_applied.emit(changes)
        self.accept()
