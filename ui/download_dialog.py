"""
Model Download Modal Dialog for Auto AI Live Caption.
Provides an interactive progress window when the user selects an offline model
that is not yet downloaded on their local machine.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core.models.catalog import CatalogModel
from core.models.downloader import ModelDownloadWorker


class ModelDownloadDialog(QDialog):
    """
    Modal dialog that orchestrates downloading a Whisper model with live progress.
    """

    model_downloaded = Signal(str)  # emitted with absolute model path on success

    def __init__(self, model: CatalogModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.worker: Optional[ModelDownloadWorker] = None
        self.downloaded_path: Optional[str] = None

        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(f"Download Model — {self.model.name}")
        self.setFixedWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        title_label = QLabel(f"Download {self.model.name}", self)
        title_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(self.model.description, self)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.4;")
        layout.addWidget(desc_label)

        # Specs Badge Box
        specs_box = QLabel(
            f"📦 <b>Size:</b> ~{self.model.size_mb} MB &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"⚡ <b>Speed:</b> {self.model.speed_rating}<br>"
            f"🌐 <b>Language:</b> {'Multilingual (ID, EN, JA, 90+)' if self.model.is_multilingual else 'English Only'}",
            self,
        )
        specs_box.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 10px 12px;
            color: #e2e8f0;
            font-size: 11px;
            """
        )
        layout.addWidget(specs_box)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
                font-weight: bold;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 5px;
            }
            """
        )
        layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("Ready to download model from Hugging Face.", self)
        self.status_label.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.16);
                color: #ffffff;
            }
            """
        )
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)

        self.download_btn = QPushButton("⬇ Start Download", self)
        self.download_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            """
        )
        self.download_btn.clicked.connect(self.start_download)
        btn_layout.addWidget(self.download_btn)

        layout.addLayout(btn_layout)

        # Dialog Styling
        self.setStyleSheet(
            """
            QDialog {
                background-color: #14161f;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
            """
        )

    def start_download(self) -> None:
        """Launch the background download worker."""
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading...")
        self.progress_bar.setValue(10)
        self.status_label.setText(f"Initializing download for {self.model.name}...")

        self.worker = ModelDownloadWorker(self.model, parent=self)
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.download_finished.connect(self._on_finished)
        self.worker.download_failed.connect(self._on_failed)
        self.worker.start()

    def _on_progress(self, percent: int, msg: str) -> None:
        self.progress_bar.setValue(percent)
        self.status_label.setText(msg)

    def _on_finished(self, path: str) -> None:
        self.downloaded_path = path
        self.progress_bar.setValue(100)
        self.status_label.setText("Download complete! Applying model...")
        self.status_label.setStyleSheet("color: #34d399; font-weight: bold; font-size: 11px;")
        self.download_btn.setText("✓ Completed")
        self.model_downloaded.emit(path)
        self.accept()

    def _on_failed(self, error: str) -> None:
        self.download_btn.setEnabled(True)
        self.download_btn.setText("Retry Download")
        self.status_label.setText(error)
        self.status_label.setStyleSheet("color: #f87171; font-size: 11px;")

    def _on_cancel(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        self.reject()

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(1000)
        super().closeEvent(event)
