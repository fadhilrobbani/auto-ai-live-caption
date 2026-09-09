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
from core.models.catalog import (
    CatalogModel,
    get_catalog_models,
    get_catalog_model_by_id,
    is_model_downloaded,
    get_model_local_dir,
)
from core.models.registry import ModelRegistry
from ui.download_dialog import ModelDownloadDialog


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
        self.cfg: AppConfig = config_manager.config
        self.registry = registry

        self.setWindowTitle("Settings & Preferences — Auto AI Live Caption")
        self.setMinimumSize(560, 480)
        self.setStyleSheet(
            """
            QDialog {
                background-color: #0f111a;
                color: #f8fafc;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 12px;
                font-weight: bold;
                font-size: 12px;
                color: #e2e8f0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: #93c5fd;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 10px;
                color: #f8fafc;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #3b82f6;
            }
            QComboBox QAbstractItemView {
                background-color: #1e2130;
                color: #f8fafc;
                selection-background-color: #3b82f6;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                background: #141622;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: rgba(255, 255, 255, 0.05);
                color: #94a3b8;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #141622;
                color: #ffffff;
                border-bottom: 2px solid #3b82f6;
            }
            """
        )
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_models_tab(), "ASR Models")
        self.tabs.addTab(self._create_audio_tab(), "Audio & Device")
        self.tabs.addTab(self._create_appearance_tab(), "Appearance")
        self.tabs.addTab(self._create_language_tab(), "Language")
        main_layout.addWidget(self.tabs)

        # Action Buttons (Save / Cancel)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            """
        )
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 7px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
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

        # 1. Offline Whisper Models (One-Click Auto-Download)
        group_offline = QGroupBox("Offline Whisper Model (Auto-Download)")
        form_offline = QFormLayout(group_offline)

        self.catalog_combo = QComboBox()
        self.catalog_models = get_catalog_models()
        self._populate_catalog_combo()

        self.catalog_desc = QLabel()
        self.catalog_desc.setWordWrap(True)
        self.catalog_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")

        # Download / Apply Button
        dl_row = QHBoxLayout()
        self.catalog_status_badge = QLabel()
        self.catalog_status_badge.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.download_btn = QPushButton("⬇ Download Model")
        self.download_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border-radius: 5px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            """
        )
        self.download_btn.clicked.connect(self._on_download_clicked)
        dl_row.addWidget(self.catalog_status_badge)
        dl_row.addWidget(self.download_btn)
        dl_row.addStretch()

        form_offline.addRow("Select Model:", self.catalog_combo)
        form_offline.addRow("", self.catalog_desc)
        form_offline.addRow("Status:", dl_row)

        self.catalog_combo.currentIndexChanged.connect(self._on_catalog_changed)

        layout.addWidget(group_offline)

        # 2. Performance & Latency Profile
        group_perf = QGroupBox("Performance & Latency Profile")
        form_perf = QFormLayout(group_perf)

        self.latency_combo = QComboBox()
        self.latency_combo.addItem("⚡ Low Latency (~1.3s chunks) — Recommended for laptops", "fast")
        self.latency_combo.addItem("⚖ Balanced (~2.0s chunks)", "balanced")
        self.latency_combo.addItem("🎯 High Accuracy (~2.8s chunks)", "accurate")

        curr_lat = getattr(self.cfg, "latency_profile", "fast")
        lat_idx = {"fast": 0, "balanced": 1, "accurate": 2}.get(curr_lat, 0)
        self.latency_combo.setCurrentIndex(lat_idx)

        form_perf.addRow("Chunking Profile:", self.latency_combo)
        layout.addWidget(group_perf)

        # 3. Active Engine Provider
        group_engine = QGroupBox("Active ASR Engine Provider")
        form_eng = QFormLayout(group_engine)

        self.model_combo = QComboBox()
        self._refresh_engine_combo()
        form_eng.addRow("Active Provider:", self.model_combo)
        layout.addWidget(group_engine)

        # 4. Custom Model Path (Advanced)
        group_local = QGroupBox("Custom Model Path (Advanced)")
        form_local = QFormLayout(group_local)

        local_layout = QHBoxLayout()
        self.local_path_edit = QLineEdit(self.cfg.local_model_path)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse_model)
        local_layout.addWidget(self.local_path_edit)
        local_layout.addWidget(self.browse_btn)

        form_local.addRow("Model Path:", local_layout)
        layout.addWidget(group_local)

        # 5. Cloud API Keys
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

        self._on_catalog_changed(self.catalog_combo.currentIndex())
        return tab

    def _populate_catalog_combo(self) -> None:
        self.catalog_combo.clear()
        selected_id = getattr(self.cfg, "selected_catalog_model", "base")
        for idx, m in enumerate(self.catalog_models):
            is_dl = is_model_downloaded(m)
            status_tag = "✓ Installed" if is_dl else f"⬇ Download ~{m.size_mb}MB"
            self.catalog_combo.addItem(f"{m.name} ({m.speed_rating}) [{status_tag}]", m.id)
            if selected_id == m.id or (m.dir_name in self.cfg.local_model_path):
                self.catalog_combo.setCurrentIndex(idx)

    def _refresh_engine_combo(self) -> None:
        self.model_combo.clear()
        engines = self.registry.list_engines()
        for idx, eng in enumerate(engines):
            self.model_combo.addItem(eng["display_name"], eng["id"])
            if eng["id"] == self.cfg.active_engine_id:
                self.model_combo.setCurrentIndex(idx)

    def _on_catalog_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.catalog_models):
            return
        model = self.catalog_models[index]
        self.catalog_desc.setText(
            f"{model.description} (Size: ~{model.size_mb} MB | Language: {'Multilingual' if model.is_multilingual else 'English Only'})"
        )
        is_dl = is_model_downloaded(model)
        if is_dl:
            self.catalog_status_badge.setText("✓ Installed & Ready")
            self.catalog_status_badge.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
            self.download_btn.setVisible(False)
            model_path = str(get_model_local_dir(model))
            if hasattr(self, "local_path_edit"):
                self.local_path_edit.setText(model_path)
        else:
            self.catalog_status_badge.setText("Not downloaded")
            self.catalog_status_badge.setStyleSheet("color: #94a3b8; font-size: 11px;")
            self.download_btn.setVisible(True)
            self.download_btn.setText(f"⬇ Download & Apply (~{model.size_mb} MB)")

    def _on_download_clicked(self) -> None:
        index = self.catalog_combo.currentIndex()
        if index < 0 or index >= len(self.catalog_models):
            return
        model = self.catalog_models[index]
        dialog = ModelDownloadDialog(model, parent=self)
        dialog.model_downloaded.connect(lambda p: self._on_model_downloaded(model, p))
        dialog.exec()

    def _on_model_downloaded(self, model: CatalogModel, model_path: str) -> None:
        engine_id = self.registry.register_local_model(model_path, set_active=True)
        self.local_path_edit.setText(model_path)
        self.cfg.selected_catalog_model = model.id
        self.cfg.active_engine_id = engine_id
        self.cfg.local_model_path = model_path
        self._populate_catalog_combo()
        self._refresh_engine_combo()
        self._on_catalog_changed(self.catalog_combo.currentIndex())

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

        latency_profile = self.latency_combo.currentData()
        cat_idx = self.catalog_combo.currentIndex()
        selected_catalog_model = (
            self.catalog_models[cat_idx].id if 0 <= cat_idx < len(self.catalog_models) else "base"
        )

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
            latency_profile=latency_profile,
            selected_catalog_model=selected_catalog_model,
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
            "latency_profile": latency_profile,
            "selected_catalog_model": selected_catalog_model,
        }
        self.settings_applied.emit(changes)
        self.accept()
