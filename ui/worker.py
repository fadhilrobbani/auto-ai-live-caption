"""
Background Pipeline Orchestrator Worker Thread (PySide6 QThread).
Decouples audio capture, VAD, and model inference from the Qt GUI main thread.
"""

import logging
import queue
import time
from typing import Optional
import numpy as np
from PySide6.QtCore import QThread, Signal

from core.audio.device_manager import get_default_device, get_default_sink_name
from core.audio.streamer import AudioStreamer
from core.models.registry import ModelRegistry
from core.stabilizer.text_stabilizer import TextStabilizer
from core.vad.processor import VADProcessor

logger = logging.getLogger(__name__)


class CaptionWorker(QThread):
    """
    QThread worker orchestrating the real-time caption pipeline:
    AudioStreamer -> Queue -> VADProcessor -> ModelRegistry -> TextStabilizer -> Signals.
    """

    # Signals for UI updates
    caption_received = Signal(str, str)  # (committed_history, in_flight_text)
    status_updated = Signal(dict)        # State dictionary (is_live, latency_ms, etc.)
    error_occurred = Signal(str)         # Error message

    def __init__(
        self,
        registry: ModelRegistry,
        stabilizer: Optional[TextStabilizer] = None,
        device_id: Optional[str] = None,
        is_monitor: bool = True,
        language: Optional[str] = None,
        latency_profile: str = "fast",
        parent=None,
    ):
        super().__init__(parent)
        self.registry = registry
        self.stabilizer = stabilizer or TextStabilizer(max_history_lines=3)
        self.device_id = device_id
        self.is_monitor = is_monitor
        self.language = None if language == "auto" else language

        # Pipeline components
        self.vad = VADProcessor(sample_rate=16000, latency_profile=latency_profile)
        self.streamer: Optional[AudioStreamer] = None

        # Thread-safe audio frame queue
        self._frame_queue: queue.Queue[np.float32] = queue.Queue(maxsize=100)
        self._is_running = False
        self._is_paused = False
        self._last_default_sink = get_default_sink_name()

    def run(self) -> None:
        """Main worker execution loop."""
        self._is_running = True

        # Initialize audio source
        self._start_audio_streamer()

        logger.info("CaptionWorker loop started.")
        frame_counter = 0

        while self._is_running:
            try:
                # Wait for audio frame from streamer (100ms timeout)
                frame = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # Periodically check if system default output changed (e.g. TWS connected/disconnected)
            frame_counter += 1
            if frame_counter % 25 == 0 and self.is_monitor:
                if not self.device_id or self.device_id == "@DEFAULT_MONITOR@":
                    curr_sink = get_default_sink_name()
                    if curr_sink and self._last_default_sink and curr_sink != self._last_default_sink:
                        logger.info(
                            "System default sink changed (%s -> %s). Seamlessly reconnecting streamer...",
                            self._last_default_sink,
                            curr_sink,
                        )
                        self._last_default_sink = curr_sink
                        self._start_audio_streamer()

            if self._is_paused:
                continue

            # Feed to Voice Activity Detector
            try:
                chunk = self.vad.process_frame(frame)
            except Exception as vad_err:
                logger.error("VAD error: %s", vad_err)
                chunk = None

            if chunk is not None and len(chunk) > 0:
                # Speech chunk ready for transcription
                active_engine = self.registry.get_active()
                if not active_engine:
                    self.error_occurred.emit("No active ASR engine configured.")
                    continue

                try:
                    result = active_engine.transcribe_chunk(chunk, language=self.language)
                    if result and result.text.strip():
                        hist, tent = self.stabilizer.update(result.text, is_final=result.is_final)
                        self.caption_received.emit(hist, tent)

                        # Emit status update
                        self.status_updated.emit(
                            {
                                "is_live": not self._is_paused,
                                "latency_ms": round(result.latency_ms, 1),
                                "engine_name": active_engine.get_display_name(),
                                "detected_lang": result.language,
                                "is_monitor": self.is_monitor,
                            }
                        )
                except Exception as infer_err:
                    logger.error("Inference exception: %s", infer_err)
                    self.error_occurred.emit(f"ASR error: {infer_err}")

        # Cleanup audio streamer on thread exit
        self._stop_audio_streamer()
        logger.info("CaptionWorker loop finished.")

    def _start_audio_streamer(self) -> None:
        """Start or restart the background audio streamer."""
        self._stop_audio_streamer()

        # If device_id is unset or uses auto-switch, use PipeWire dynamic aliases
        target_dev = self.device_id
        if not target_dev or target_dev.startswith("@DEFAULT_"):
            target_dev = "@DEFAULT_MONITOR@" if self.is_monitor else "@DEFAULT_SOURCE@"

        self.streamer = AudioStreamer(device_id=target_dev, sample_rate=16000)
        try:
            self.streamer.start(self._on_audio_frame)
            logger.info("AudioStreamer started on device '%s'", target_dev)
        except Exception as e:
            logger.error("Failed to start AudioStreamer: %s", e)
            self.error_occurred.emit(f"Audio capture error: {e}")

    def _on_audio_frame(self, frame: np.ndarray) -> None:
        """Callback invoked from AudioStreamer reader thread."""
        if self._is_running and not self._is_paused:
            try:
                self._frame_queue.put_nowait(frame)
            except queue.Full:
                # Drop oldest frame to avoid latency lag
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
                self._frame_queue.put_nowait(frame)

    def _stop_audio_streamer(self) -> None:
        """Stop the audio streamer."""
        if self.streamer:
            try:
                self.streamer.stop()
            except Exception as e:
                logger.error("Error stopping streamer: %s", e)
            self.streamer = None

    def pause(self) -> None:
        """Pause live captioning."""
        self._is_paused = True
        self.status_updated.emit({"is_live": False, "is_paused": True})

    def resume(self) -> None:
        """Resume live captioning."""
        self._is_paused = False
        self.status_updated.emit({"is_live": True, "is_paused": False})

    def toggle_pause(self) -> bool:
        """Toggle between pause and resume. Returns current is_paused state."""
        if self._is_paused:
            self.resume()
        else:
            self.pause()
        return self._is_paused

    def is_paused(self) -> bool:
        return self._is_paused

    def switch_audio_source(self, device_id: Optional[str], is_monitor: bool) -> None:
        """Switch between desktop loopback and microphone or specific device."""
        self.device_id = device_id
        self.is_monitor = is_monitor
        self.vad.reset()
        self._start_audio_streamer()

    def switch_model(self, engine_id: str) -> bool:
        """Switch the active ASR model in registry."""
        ok = self.registry.set_active(engine_id)
        if ok:
            active = self.registry.get_active()
            if active:
                self.status_updated.emit({"engine_name": active.get_display_name()})
        return ok

    def set_language(self, language: str) -> None:
        """Update language code (e.g. 'en', 'id', 'auto')."""
        self.language = None if language == "auto" else language

    def set_latency_profile(self, profile: str) -> None:
        """Dynamically update VAD chunking latency profile."""
        self.vad.set_latency_profile(profile)

    def clear_captions(self) -> None:
        """Clear all active captions."""
        self.stabilizer.clear()
        self.caption_received.emit("", "")

    def stop(self) -> None:
        """Stop the worker thread and all child streamers."""
        self._is_running = False
        self._is_paused = False
        self._stop_audio_streamer()
        self.quit()
        self.wait(1000)
