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
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
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
        self.model_combo = QComboBox()

        self.setWindowTitle("Settings & Preferences — Auto AI Live Caption")
        self.setMinimumSize(540, 420)
        self.resize(600, 560)
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

    def _wrap_in_scroll_area(self, widget: QWidget) -> QScrollArea:
        """Wrap a tab widget in a sleek, transparent scroll area to prevent clipping."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            """
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.04);
                width: 8px;
                margin: 4px 2px 4px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.22);
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3b82f6;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            """
        )
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setWidget(widget)
        return scroll

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Tab Widget with scroll-wrapped tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._wrap_in_scroll_area(self._create_models_tab()), "ASR Models")
        self.tabs.addTab(self._wrap_in_scroll_area(self._create_audio_tab()), "Audio & Device")
        self.tabs.addTab(self._wrap_in_scroll_area(self._create_appearance_tab()), "Appearance")
        self.tabs.addTab(self._wrap_in_scroll_area(self._create_language_tab()), "Language")
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
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # 1. AI Speech Recognition Model Card
        group_model = QGroupBox("AI Speech Recognition Model")
        form_model = QFormLayout(group_model)
        form_model.setVerticalSpacing(10)

        self.catalog_combo = QComboBox()
        self.catalog_models = get_catalog_models()
        self._populate_unified_model_combo()
        form_model.addRow("Choose Model:", self.catalog_combo)

        # Dynamic Model Description
        self.catalog_desc = QLabel()
        self.catalog_desc.setWordWrap(True)
        self.catalog_desc.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 2px 0;")
        form_model.addRow("", self.catalog_desc)

        # Offline Model Status & One-Click Download Row
        self.status_row_widget = QWidget()
        status_row = QHBoxLayout(self.status_row_widget)
        status_row.setContentsMargins(0, 0, 0, 0)
        self.catalog_status_badge = QLabel()
        self.catalog_status_badge.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.download_btn = QPushButton("⬇ Download Model")
        self.download_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border-radius: 5px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1d4ed8; }
            """
        )
        self.download_btn.clicked.connect(self._on_download_clicked)
        status_row.addWidget(self.catalog_status_badge)
        status_row.addWidget(self.download_btn)
        status_row.addStretch()
        form_model.addRow("Model Status:", self.status_row_widget)

        # Cloud API Key Row (contextually shown for Groq / OpenAI)
        self.cloud_key_label = QLabel("API Key:")
        self.cloud_key_edit = QLineEdit()
        self.cloud_key_edit.setEchoMode(QLineEdit.Password)
        form_model.addRow(self.cloud_key_label, self.cloud_key_edit)

        # Custom Model Path Row (contextually shown for Custom Local Folder)
        self.custom_path_widget = QWidget()
        custom_layout = QHBoxLayout(self.custom_path_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        self.local_path_edit = QLineEdit(self.cfg.local_model_path)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse_model)
        custom_layout.addWidget(self.local_path_edit)
        custom_layout.addWidget(self.browse_btn)
        self.custom_path_label = QLabel("Folder Path:")
        form_model.addRow(self.custom_path_label, self.custom_path_widget)

        layout.addWidget(group_model)

        # 2. Live Caption Speed & Responsiveness Card
        group_speed = QGroupBox("Caption Speed & Responsiveness")
        form_speed = QFormLayout(group_speed)
        form_speed.setVerticalSpacing(8)

        self.latency_combo = QComboBox()
        self.latency_combo.addItem("⚡ Real-Time Word Streaming (Fastest — Live Preview)", "fast")
        self.latency_combo.addItem("⚖ Natural Speech Pauses (Balanced — ~2s chunks)", "balanced")
        self.latency_combo.addItem("🎯 Full Sentences (Accurate Dictation — ~3s chunks)", "accurate")

        curr_lat = getattr(self.cfg, "latency_profile", "fast")
        lat_idx = {"fast": 0, "balanced": 1, "accurate": 2}.get(curr_lat, 0)
        self.latency_combo.setCurrentIndex(lat_idx)
        form_speed.addRow("Speed Mode:", self.latency_combo)

        self.latency_desc = QLabel()
        self.latency_desc.setWordWrap(True)
        self.latency_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        form_speed.addRow("", self.latency_desc)

        self.latency_combo.currentIndexChanged.connect(self._on_latency_changed)
        self._on_latency_changed(self.latency_combo.currentIndex())

        layout.addWidget(group_speed)
        layout.addStretch()

        # Connect model selection change listener
        self.catalog_combo.currentIndexChanged.connect(self._on_unified_model_changed)
        self._on_unified_model_changed(self.catalog_combo.currentIndex())

        return tab

    def _populate_unified_model_combo(self) -> None:
        """Populate single unified model dropdown with offline catalog, cloud, and custom options."""
        self.catalog_combo.clear()
        selected_id = getattr(self.cfg, "selected_catalog_model", "base")
        active_eng = getattr(self.cfg, "active_engine_id", "")

        # 1. Curated Offline Models
        for idx, m in enumerate(self.catalog_models):
            is_dl = is_model_downloaded(m)
            status_tag = "✓ Ready" if is_dl else f"⬇ Download ~{m.size_mb}MB"
            self.catalog_combo.addItem(f"{m.name} ({m.speed_rating}) [{status_tag}]", m.id)

        # 2. Cloud & Custom Models
        self.catalog_combo.addItem("☁ Cloud: Groq Whisper (Ultra-Fast <200ms Cloud)", "cloud-groq")
        self.catalog_combo.addItem("☁ Cloud: OpenAI Whisper (Official API)", "cloud-openai")
        self.catalog_combo.addItem("📁 Custom Offline Model Directory...", "custom-local")

        # Determine initial selection
        if active_eng == "groq-whisper":
            target_id = "cloud-groq"
        elif active_eng == "openai-whisper":
            target_id = "cloud-openai"
        elif self.cfg.local_model_path and not any(m.dir_name in self.cfg.local_model_path for m in self.catalog_models):
            target_id = "custom-local"
        else:
            target_id = selected_id

        for idx in range(self.catalog_combo.count()):
            if self.catalog_combo.itemData(idx) == target_id:
                self.catalog_combo.setCurrentIndex(idx)
                break

    def _on_unified_model_changed(self, index: int) -> None:
        """Dynamically adapt card UI based on chosen model type."""
        if index < 0 or index >= self.catalog_combo.count():
            return

        item_id = self.catalog_combo.itemData(index)

        if item_id == "cloud-groq":
            self.catalog_desc.setText(
                "⚡ Ultra-fast cloud inference on Groq LPUs (<200ms). Requires an internet connection and free Groq API key."
            )
            self.status_row_widget.setVisible(False)
            self.cloud_key_label.setText("Groq API Key:")
            self.cloud_key_label.setVisible(True)
            self.cloud_key_edit.setVisible(True)
            self.cloud_key_edit.setText(self.cfg.groq_api_key)
            self.cloud_key_edit.setPlaceholderText("gsk_...")
            self.custom_path_label.setVisible(False)
            self.custom_path_widget.setVisible(False)

        elif item_id == "cloud-openai":
            self.catalog_desc.setText(
                "☁ Cloud-based Whisper transcription via official OpenAI API. Requires an OpenAI API key."
            )
            self.status_row_widget.setVisible(False)
            self.cloud_key_label.setText("OpenAI API Key:")
            self.cloud_key_label.setVisible(True)
            self.cloud_key_edit.setVisible(True)
            self.cloud_key_edit.setText(self.cfg.openai_api_key)
            self.cloud_key_edit.setPlaceholderText("sk-...")
            self.custom_path_label.setVisible(False)
            self.custom_path_widget.setVisible(False)

        elif item_id == "custom-local":
            self.catalog_desc.setText(
                "📁 Load any pre-quantized CTranslate2 / Faster-Whisper model from a custom local folder on your computer."
            )
            self.status_row_widget.setVisible(False)
            self.cloud_key_label.setVisible(False)
            self.cloud_key_edit.setVisible(False)
            self.custom_path_label.setVisible(True)
            self.custom_path_widget.setVisible(True)

        else:
            # Offline catalog model
            model = get_catalog_model_by_id(item_id)
            if model:
                lang_note = "Multilingual (Indonesian, English, etc.)" if model.is_multilingual else "English Only"
                self.catalog_desc.setText(
                    f"{model.description}\nSpeed: {model.speed_rating} • Size: ~{model.size_mb} MB • Language: {lang_note}"
                )
                is_dl = is_model_downloaded(model)
                self.status_row_widget.setVisible(True)
                if is_dl:
                    self.catalog_status_badge.setText("✓ Ready to Use (Installed)")
                    self.catalog_status_badge.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
                    self.download_btn.setVisible(False)
                    model_path = str(get_model_local_dir(model))
                    self.local_path_edit.setText(model_path)
                else:
                    self.catalog_status_badge.setText("Not Downloaded Yet")
                    self.catalog_status_badge.setStyleSheet("color: #94a3b8; font-size: 11px;")
                    self.download_btn.setVisible(True)
                    self.download_btn.setText(f"⬇ One-Click Download (~{model.size_mb} MB)")

            self.cloud_key_label.setVisible(False)
            self.cloud_key_edit.setVisible(False)
            self.custom_path_label.setVisible(False)
            self.custom_path_widget.setVisible(False)

    def _on_latency_changed(self, index: int) -> None:
        """Update latency profile description helper."""
        data = self.latency_combo.itemData(index)
        if data == "fast":
            self.latency_desc.setText(
                "⚡ Live In-Flight Word Streaming: Emits words in real-time (~300ms) as you speak, then locks into white text at pauses. Recommended for laptops."
            )
        elif data == "balanced":
            self.latency_desc.setText(
                "⚖ Natural Speech Pauses: Groups words into 2-second chunks after short pauses. Good balance of context and latency."
            )
        elif data == "accurate":
            self.latency_desc.setText(
                "🎯 Full Sentences: Collects 3-second sentences before transcribing. Highest grammatical precision, but waits longer."
            )

    def _on_download_clicked(self) -> None:
        index = self.catalog_combo.currentIndex()
        if index < 0 or index >= self.catalog_combo.count():
            return
        item_id = self.catalog_combo.itemData(index)
        model = get_catalog_model_by_id(item_id)
        if not model:
            return
        dialog = ModelDownloadDialog(model, parent=self)
        dialog.model_downloaded.connect(lambda p: self._on_model_downloaded(model, p))
        dialog.exec()

    def _on_model_downloaded(self, model: CatalogModel, model_path: str) -> None:
        engine_id = self.registry.register_local_model(model_path, set_active=True)
        self.local_path_edit.setText(model_path)
        self.cfg.selected_catalog_model = model.id
        self.cfg.active_engine_id = engine_id
        self.cfg.local_model_path = model_path
        self._populate_unified_model_combo()
        self._on_unified_model_changed(self.catalog_combo.currentIndex())

    def _create_audio_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
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
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
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
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

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
        device_id = self.device_combo.currentData()
        # Check if device is monitor from id
        is_monitor = (device_id == "@DEFAULT_MONITOR@") or (".monitor" in str(device_id).lower())

        font_size = self.font_size_spin.value()
        opacity = self.opacity_slider.value() / 100.0
        always_on_top = self.always_on_top_chk.isChecked()
        hide_controls = self.hide_controls_chk.isChecked()
        language = self.lang_combo.currentData()
        latency_profile = self.latency_combo.currentData()

        # Determine model selection from unified dropdown
        cat_idx = self.catalog_combo.currentIndex()
        item_id = self.catalog_combo.itemData(cat_idx) if cat_idx >= 0 else "base"
        local_model_path = self.local_path_edit.text().strip()
        groq_api_key = self.cfg.groq_api_key
        openai_api_key = self.cfg.openai_api_key
        selected_catalog_model = getattr(self.cfg, "selected_catalog_model", "base")

        if item_id == "cloud-groq":
            active_eng_id = "groq-whisper"
            groq_api_key = self.cloud_key_edit.text().strip()
            self.registry.set_active("groq-whisper")
        elif item_id == "cloud-openai":
            active_eng_id = "openai-whisper"
            openai_api_key = self.cloud_key_edit.text().strip()
            self.registry.set_active("openai-whisper")
        elif item_id == "custom-local":
            active_eng_id = self.registry.register_local_model(local_model_path, set_active=True)
        else:
            # Offline catalog model
            selected_catalog_model = item_id
            model = get_catalog_model_by_id(item_id)
            if model and is_model_downloaded(model):
                local_model_path = str(get_model_local_dir(model))
                active_eng_id = self.registry.register_local_model(local_model_path, set_active=True)
            else:
                active_eng_id = getattr(self.cfg, "active_engine_id", "faster-whisper-base")

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
