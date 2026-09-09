"""
Cloud OpenAI Whisper API Caption Engine.
Connects to https://api.openai.com/v1/audio/transcriptions.
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

OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
DEFAULT_OPENAI_MODEL = "whisper-1"


class OpenAIWhisperEngine(BaseCaptionEngine):
    """
    Cloud ASR provider using official OpenAI Whisper API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_OPENAI_MODEL,
        timeout_sec: float = 8.0,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.timeout_sec = timeout_sec
        self._client: Optional[httpx.Client] = None
        self._is_initialized = False

    def initialize(self) -> bool:
        """Verify API key is present and create persistent HTTP client."""
        if not self.api_key or not self.api_key.strip():
            logger.warning("OpenAIWhisperEngine: No API key provided.")
            self._is_initialized = False
            return False

        try:
            self._client = httpx.Client(
                timeout=self.timeout_sec,
                headers={"Authorization": f"Bearer {self.api_key.strip()}"},
            )
            self._is_initialized = True
            logger.info("OpenAIWhisperEngine initialized with model '%s'.", self.model)
            return True
        except Exception as e:
            logger.error("Failed to initialize HTTP client for OpenAI: %s", e)
            self._is_initialized = False
            return False

    def transcribe_chunk(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> CaptionResult:
        """
        Send audio chunk to OpenAI audio/transcriptions endpoint.
        """
        if not self._is_initialized or self._client is None:
            if not self.initialize():
                return CaptionResult(
                    text="[OpenAI API Key Required]",
                    language="unknown",
                    is_final=False,
                    latency_ms=0.0,
                    confidence=0.0,
                )

        t_start = time.perf_counter()

        try:
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
            if prompt:
                data["prompt"] = prompt

            response = self._client.post(
                OPENAI_TRANSCRIPTION_URL,
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
                    "OpenAI API returned HTTP %d: %s",
                    response.status_code,
                    response.text,
                )
                text = f"[OpenAI Error: {response.status_code}]"
                detected_lang = "unknown"
                confidence = 0.0

        except Exception as e:
            logger.error("OpenAI API request failed: %s", e)
            text = "[OpenAI Connection Error]"
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
        logger.info("OpenAIWhisperEngine shutdown complete.")

    def is_initialized(self) -> bool:
        return self._is_initialized

    def get_id(self) -> str:
        return f"openai-{self.model}"

    def get_display_name(self) -> str:
        return f"Cloud OpenAI ({self.model})"
