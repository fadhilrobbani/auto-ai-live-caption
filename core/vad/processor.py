"""
Voice Activity Detection (VAD) & Speech Chunking Processor.
Uses Silero VAD (bundled in faster-whisper) with energy gating to segment
continuous audio streams into 1.5s - 3.0s speech chunks while eliminating silence.
"""

import collections
import logging
from typing import Deque, Optional
import numpy as np

logger = logging.getLogger(__name__)


class VADProcessor:
    """
    Real-time speech chunk accumulator using Silero VAD and energy heuristics.
    Buffers incoming PCM audio frames and emits consolidated speech chunks
    when speech boundaries or max chunk durations are encountered.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        speech_threshold: float = 0.5,
        energy_threshold: float = 0.005,
        min_speech_duration_sec: float = 0.35,
        max_chunk_duration_sec: Optional[float] = None,
        silence_timeout_sec: Optional[float] = None,
        pre_speech_padding_sec: float = 0.25,
        latency_profile: str = "fast",
    ):
        self.sample_rate = sample_rate
        self.speech_threshold = speech_threshold
        self.energy_threshold = energy_threshold
        self.min_speech_samples = int(min_speech_duration_sec * sample_rate)
        self.pre_speech_padding_sec = pre_speech_padding_sec

        # Configure latency profile
        self.latency_profile = latency_profile
        self._apply_latency_profile(latency_profile, max_chunk_duration_sec, silence_timeout_sec)

        # Ring buffer for pre-speech context (avoids clipping beginning of words)
        pre_padding_count = max(1, int(pre_speech_padding_sec * sample_rate / 1600))
        self._pre_buffer: Deque[np.ndarray] = collections.deque(maxlen=pre_padding_count)

        # State tracking
        self._in_speech = False
        self._speech_buffer: list[np.ndarray] = []
        self._current_speech_samples = 0
        self._trailing_silence_samples = 0

        # Load Silero VAD model
        self._vad_model = None
        self._init_vad()

    def _apply_latency_profile(
        self,
        profile: str,
        max_chunk: Optional[float] = None,
        silence_timeout: Optional[float] = None,
    ) -> None:
        """Apply chunking bounds according to latency profile."""
        self.latency_profile = profile
        if max_chunk is not None and silence_timeout is not None:
            self.max_chunk_samples = int(max_chunk * self.sample_rate)
            self.silence_timeout_samples = int(silence_timeout * self.sample_rate)
            return

        if profile == "fast":
            # 1.35s chunks with 0.30s pause detection for instant response
            chunk_sec = 1.35
            silence_sec = 0.30
        elif profile == "accurate":
            # 2.8s chunks for maximum sentence context
            chunk_sec = 2.80
            silence_sec = 0.60
        else:  # balanced
            chunk_sec = 2.00
            silence_sec = 0.45

        self.max_chunk_samples = int(chunk_sec * self.sample_rate)
        self.silence_timeout_samples = int(silence_sec * self.sample_rate)
        logger.info(
            "VAD latency profile set to '%s' (max_chunk=%.2fs, silence_timeout=%.2fs)",
            profile,
            chunk_sec,
            silence_sec,
        )

    def set_latency_profile(self, profile: str) -> None:
        """Dynamically update chunking latency profile."""
        self._apply_latency_profile(profile)

    def _init_vad(self) -> None:
        """Initialize the Silero VAD model from faster-whisper."""
        try:
            from faster_whisper.vad import get_vad_model
            self._vad_model = get_vad_model()
            logger.info("Silero VAD model initialized successfully.")
        except Exception as e:
            logger.warning("Failed to initialize Silero VAD (%s); using energy VAD fallback.", e)
            self._vad_model = None

    def is_speech(self, frame: np.ndarray) -> bool:
        """
        Evaluate whether a given audio frame contains human speech.
        Combines RMS energy gating with Silero neural VAD.
        """
        if len(frame) == 0:
            return False

        # Fast path: Check RMS energy first
        rms = float(np.sqrt(np.mean(frame**2)))
        if rms < self.energy_threshold:
            return False

        # If neural VAD is unavailable, use energy heuristic
        if self._vad_model is None:
            return rms >= self.energy_threshold

        # Silero VAD requires frames in multiples of 512 samples
        num_blocks = len(frame) // 512
        if num_blocks == 0:
            # Frame too short for Silero, pad to 512
            padded = np.zeros(512, dtype=np.float32)
            padded[: len(frame)] = frame
            vad_input = padded
        else:
            vad_input = frame[: num_blocks * 512]

        try:
            probs = self._vad_model(vad_input)
            mean_prob = float(np.mean(probs))
            return mean_prob >= self.speech_threshold
        except Exception as e:
            logger.debug("VAD inference error (%s); falling back to energy.", e)
            return rms >= self.energy_threshold

    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Process an incoming audio frame (typically 100ms / 1600 samples at 16kHz).
        Returns a consolidated speech chunk (np.ndarray) if a boundary or max
        duration is reached; otherwise returns None.
        """
        if len(frame) == 0:
            return None

        # Ensure float32 1D
        if frame.dtype != np.float32:
            frame = frame.astype(np.float32)
        if frame.ndim > 1:
            frame = frame.flatten()

        has_speech = self.is_speech(frame)
        frame_len = len(frame)

        if has_speech:
            if not self._in_speech:
                # Transitioning from silence to speech
                self._in_speech = True
                self._speech_buffer = list(self._pre_buffer)
                self._current_speech_samples = sum(len(f) for f in self._speech_buffer)
                self._pre_buffer.clear()

            self._speech_buffer.append(frame)
            self._current_speech_samples += frame_len
            self._trailing_silence_samples = 0

            # Check if max chunk duration reached
            if self._current_speech_samples >= self.max_chunk_samples:
                return self._emit_chunk(keep_overlap=True)

        else:
            # Silence detected in this frame
            if self._in_speech:
                self._speech_buffer.append(frame)
                self._current_speech_samples += frame_len
                self._trailing_silence_samples += frame_len

                # If silence has exceeded the timeout, finalize this speech chunk
                if self._trailing_silence_samples >= self.silence_timeout_samples:
                    return self._emit_chunk(keep_overlap=False)
                
                # If chunk is already sufficiently long while in trailing silence
                if self._current_speech_samples >= self.max_chunk_samples:
                    return self._emit_chunk(keep_overlap=False)
            else:
                # In ongoing silence: maintain rolling pre-speech buffer
                self._pre_buffer.append(frame)

        return None

    def _emit_chunk(self, keep_overlap: bool = False) -> Optional[np.ndarray]:
        """Consolidate accumulated frames into a single float32 array."""
        if not self._speech_buffer:
            self._in_speech = False
            return None

        chunk = np.concatenate(self._speech_buffer)
        
        # Reset state
        if keep_overlap:
            # Retain the last ~0.3s as context for the next chunk
            overlap_samples = int(0.3 * self.sample_rate)
            if len(chunk) > overlap_samples:
                overlap_part = chunk[-overlap_samples:]
                self._speech_buffer = [overlap_part]
                self._current_speech_samples = len(overlap_part)
            else:
                self._speech_buffer = []
                self._current_speech_samples = 0
            self._trailing_silence_samples = 0
            self._in_speech = True
        else:
            self._speech_buffer = []
            self._current_speech_samples = 0
            self._trailing_silence_samples = 0
            self._in_speech = False

        # Only emit if it meets the minimum speech length
        if len(chunk) >= self.min_speech_samples:
            return chunk

        return None

    def flush(self) -> Optional[np.ndarray]:
        """Force emit any remaining buffered speech frames."""
        if self._speech_buffer and self._current_speech_samples >= self.min_speech_samples:
            chunk = np.concatenate(self._speech_buffer)
            self.reset()
            return chunk
        self.reset()
        return None

    def is_in_speech(self) -> bool:
        """Check if currently within an active speech segment."""
        return self._in_speech

    def get_in_flight_speech(self, min_samples: int = 5600) -> Optional[np.ndarray]:
        """
        Peek at the currently accumulating speech buffer without consuming it.
        Returns concatenated float32 audio if buffer has at least min_samples (~350ms).
        """
        if self._in_speech and self._speech_buffer and self._current_speech_samples >= min_samples:
            return np.concatenate(self._speech_buffer)
        return None

    def reset(self) -> None:
        """Clear all buffers and reset state to silence."""
        self._in_speech = False
        self._speech_buffer.clear()
        self._pre_buffer.clear()
        self._current_speech_samples = 0
        self._trailing_silence_samples = 0
