"""
Background Model Downloader for Auto AI Live Caption.
Uses faster_whisper / huggingface_hub to download CTranslate2 Whisper models
asynchronously without freezing the PySide6 user interface.
"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
import faster_whisper

from core.models.catalog import CatalogModel, get_model_local_dir

logger = logging.getLogger(__name__)


class ModelDownloadWorker(QThread):
    """
    Background worker that downloads a Whisper model from the Hugging Face hub
    and emits progress / completion signals to the Qt main thread.
    """

    progress_updated = Signal(int, str)   # (percent 0-100, status_message)
    download_finished = Signal(str)      # local directory path of downloaded model
    download_failed = Signal(str)        # error message

    def __init__(
        self,
        model: CatalogModel,
        target_dir: Optional[Path] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.model = model
        self.target_dir = target_dir or get_model_local_dir(model)
        self._is_cancelled = False

    def cancel(self) -> None:
        """Flag cancellation request."""
        self._is_cancelled = True

    def run(self) -> None:
        """Download model weights asynchronously."""
        try:
            logger.info(
                "Starting download for '%s' (%s) into %s",
                self.model.name,
                self.model.faster_whisper_id,
                self.target_dir,
            )
            self.progress_updated.emit(10, f"Connecting to Hugging Face for {self.model.name}...")

            # Ensure parent directory exists
            self.target_dir.parent.mkdir(parents=True, exist_ok=True)

            if self._is_cancelled:
                self.download_failed.emit("Download cancelled.")
                return

            self.progress_updated.emit(
                30, f"Downloading {self.model.name} (~{self.model.size_mb} MB)..."
            )

            # Download CTranslate2 model files
            downloaded_path = faster_whisper.download_model(
                self.model.faster_whisper_id,
                output_dir=str(self.target_dir),
            )

            if self._is_cancelled:
                self.download_failed.emit("Download cancelled.")
                return

            self.progress_updated.emit(100, f"{self.model.name} downloaded successfully!")
            logger.info("Successfully downloaded %s to %s", self.model.name, downloaded_path)
            self.download_finished.emit(downloaded_path)

        except Exception as e:
            logger.error("Download failed for %s: %s", self.model.name, e)
            self.download_failed.emit(f"Failed to download {self.model.name}: {e}")
