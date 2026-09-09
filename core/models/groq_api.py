"""
Ultra-fast Cloud Groq Whisper API Caption Engine.
Typically provides <200ms latency for whisper-large-v3-turbo.
"""

import io
import logging
import os
import time
from typing import Optional
import numpy as np
import soundfile as sf
import httpx

from core.models.base import BaseCaptionEngine, CaptionResult

logger = logging.getLogger(__name__)

GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_GROQ_MODEL = "whisper-large-v3-turbo"


class GroqWhisperEngine(BaseCaptionEngine):
    """
    Cloud ASR provider using Groq's high-throughput LPU inference for Whisper.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GROQ_MODEL,
        timeout_sec: float = 5.0,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.timeout_sec = timeout_sec
        self._client: Optional[httpx.Client] = None
        self._is_initialized = False

    def initialize(self) -> bool:
        """Verify API key is present and create persistent HTTP client."""
        if not self.api_key or not self.api_key.strip():
            logger.warning("GroqWhisperEngine: No API key provided.")
            self._is_initialized = False
            return False

        try:
            self._client = httpx.Client(
                timeout=self.timeout_sec,
                headers={"Authorization": f"Bearer {self.api_key.strip()}"},
            )
            self._is_initialized = True
            logger.info("GroqWhisperEngine initialized with model '%s'.", self.model)
            return True
        except Exception as e:
            logger.error("Failed to initialize HTTP client for Groq: %s", e)
            self._is_initialized = False
            return False

    def transcribe_chunk(
        self, audio: np.ndarray, language: Optional[str] = None
    ) -> CaptionResult:
        """
        Send audio chunk to Groq's audio/transcriptions endpoint.
        """
        if not self._is_initialized or self._client is None:
            if not self.initialize():
                return CaptionResult(
                    text="[Groq API Key Required]",
                    language="unknown",
                    is_final=False,
                    latency_ms=0.0,
                    confidence=0.0,
                )

        t_start = time.perf_counter()

        try:
            # Convert float32 numpy array to 16kHz 16-bit PCM WAV in memory
            wav_buffer = io.BytesIO()
            sf.write(wav_buffer, audio, 16000, format="WAV", subtype="PCM_16")
            wav_bytes = wav_buffer.getvalue()

            files = {
                "file": ("audio.wav", wav_bytes, "audio/wav"),
            }
            data = {
                "model": self.model,
                "response_format": "json",
                "temperature": "0.0",
            }
            if language:
                data["language"] = language

            response = self._client.post(
                GROQ_TRANSCRIPTION_URL,
                files=files,
                data=data,
            )

            if response.status_code == 200:
                result_json = response.json()
                text = result_json.get("text", "").strip()
                detected_lang = language or "auto"
                confidence = 1.0
            else:
                logger.error(
                    "Groq API returned HTTP %d: %s",
                    response.status_code,
                    response.text,
                )
                text = f"[Groq Error: {response.status_code}]"
                detected_lang = "unknown"
                confidence = 0.0

        except Exception as e:
            logger.error("Groq API request failed: %s", e)
            text = "[Groq Connection Error]"
            detected_lang = "unknown"
            confidence = 0.0

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return CaptionResult(
            text=text,
            language=detected_lang,
            is_final=True,
            latency_ms=elapsed_ms,
            confidence=confidence,
        )

    def shutdown(self) -> None:
        """Close HTTP client connection pool."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        self._is_initialized = False
        logger.info("GroqWhisperEngine shutdown complete.")

    def is_initialized(self) -> bool:
        return self._is_initialized

    def get_id(self) -> str:
        return f"groq-{self.model}"

    def get_display_name(self) -> str:
        return f"Cloud Groq ({self.model})"
