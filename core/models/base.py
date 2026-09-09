"""
Abstract Base Classes & Data Contracts for Caption Providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class CaptionResult:
    text: str
    language: str
    is_final: bool
    latency_ms: float
    confidence: float = 1.0


class BaseCaptionEngine(ABC):
    """
    Abstract contract for all ASR caption engines (offline local models or cloud APIs).
    """

    @abstractmethod
    def initialize(self) -> bool:
        """Load weights, verify API keys, or connect to endpoint. Returns True on success."""
        ...

    @abstractmethod
    def transcribe_chunk(
        self, audio: np.ndarray, language: Optional[str] = None
    ) -> CaptionResult:
        """
        Transcribe a 16kHz mono float32 audio chunk.
        Language can be ISO 639-1 code (e.g. 'en', 'id') or None for auto-detect.
        """
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up memory, close network sessions, and unload models."""
        ...

    @abstractmethod
    def get_id(self) -> str:
        """Unique machine-readable identifier for the engine (e.g., 'faster-whisper-base')."""
        ...

    @abstractmethod
    def get_display_name(self) -> str:
        """User-friendly display label (e.g., 'Offline Faster-Whisper Base')."""
        ...

    def is_initialized(self) -> bool:
        """Return True if model is ready for transcription."""
        return False
