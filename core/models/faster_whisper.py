"""
Offline Faster-Whisper Caption Engine implementation.
Leverages CTranslate2 and INT8 quantized local model weights.
"""

import gc
import logging
import os
import time
from typing import Optional
import numpy as np

from core.models.base import BaseCaptionEngine, CaptionResult

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_MODEL = "/home/fadhilrobbani/.local/share/models/whisper/faster-whisper-base"


class FasterWhisperEngine(BaseCaptionEngine):
    """
    Offline local speech recognition engine powered by Faster-Whisper & CTranslate2.
    """

    def __init__(
        self,
        model_path_or_name: str = DEFAULT_LOCAL_MODEL,
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
    ):
        self.model_path_or_name = model_path_or_name
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads

        self._model = None
        self._is_initialized = False

    def initialize(self) -> bool:
        """Load the model weights into memory."""
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "Initializing FasterWhisperEngine with model='%s', device=%s, compute_type=%s",
                self.model_path_or_name,
                self.device,
                self.compute_type,
            )
            self._model = WhisperModel(
                self.model_path_or_name,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
            self._is_initialized = True
            logger.info("FasterWhisperEngine initialized successfully.")
            return True
        except Exception as e:
            logger.error("Failed to initialize FasterWhisperEngine: %s", e)
            self._model = None
            self._is_initialized = False
            return False

    def transcribe_chunk(
        self, audio: np.ndarray, language: Optional[str] = None
    ) -> CaptionResult:
        """
        Transcribe a 16kHz float32 mono audio chunk.
        """
        if not self._is_initialized or self._model is None:
            if not self.initialize():
                return CaptionResult(
                    text="",
                    language="unknown",
                    is_final=False,
                    latency_ms=0.0,
                    confidence=0.0,
                )

        t_start = time.perf_counter()

        try:
            # beam_size=1, temperature=0, condition_on_previous_text=False for fastest greedy decoding
            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                condition_on_previous_text=False,
                vad_filter=False,  # Already segmented by VAD upstream
                without_timestamps=True,
            )

            text_parts = []
            for seg in segments:
                t = seg.text.strip()
                if t:
                    text_parts.append(t)

            final_text = " ".join(text_parts).strip()
            detected_lang = info.language if info and info.language else (language or "auto")
            confidence = float(info.language_probability) if info and info.language_probability else 1.0

        except Exception as e:
            logger.error("Transcription error in FasterWhisperEngine: %s", e)
            final_text = ""
            detected_lang = language or "unknown"
            confidence = 0.0

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return CaptionResult(
            text=final_text,
            language=detected_lang,
            is_final=True,
            latency_ms=elapsed_ms,
            confidence=confidence,
        )

    def shutdown(self) -> None:
        """Release model from memory."""
        if self._model is not None:
            del self._model
            self._model = None
            gc.collect()
        self._is_initialized = False
        logger.info("FasterWhisperEngine shutdown complete.")

    def is_initialized(self) -> bool:
        return self._is_initialized

    def get_id(self) -> str:
        basename = os.path.basename(self.model_path_or_name.rstrip("/"))
        return f"faster-whisper-{basename}"

    def get_display_name(self) -> str:
        basename = os.path.basename(self.model_path_or_name.rstrip("/"))
        return f"Offline Faster-Whisper ({basename.replace('faster-whisper-', '').capitalize()})"
