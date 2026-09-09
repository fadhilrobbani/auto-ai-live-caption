"""
Audio Streamer for PulseAudio / PipeWire on Linux.
Streams 16kHz mono float32 PCM chunks via low-latency non-blocking reading.
"""

import logging
import os
import subprocess
import threading
from typing import Callable, Optional
import numpy as np

logger = logging.getLogger(__name__)


class AudioStreamer:
    """
    Continuous low-latency audio streamer utilizing `parec` for zero-overhead,
    PipeWire-native 16kHz mono float32 audio capture.
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        sample_rate: int = 16000,
        chunk_duration_sec: float = 0.1,  # 100ms per callback chunk
    ):
        self.device_id = device_id
        self.sample_rate = sample_rate
        self.chunk_duration_sec = chunk_duration_sec
        
        # 16000 Hz * 0.1s = 1600 float32 samples = 6400 bytes
        self.chunk_samples = int(self.sample_rate * self.chunk_duration_sec)
        self.chunk_bytes = self.chunk_samples * 4

        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self, callback: Callable[[np.ndarray], None]) -> None:
        """
        Start capturing audio and streaming float32 numpy arrays to `callback`.
        """
        with self._lock:
            if self._is_running:
                logger.warning("AudioStreamer is already running.")
                return

            latency_ms = max(20, int(self.chunk_duration_sec * 500))  # e.g., 50ms
            cmd = [
                "parec",
                f"--rate={self.sample_rate}",
                "--channels=1",
                "--format=float32le",
                f"--latency-msec={latency_ms}",
                f"--process-time-msec={latency_ms}",
            ]
            if self.device_id:
                cmd.append(f"--device={self.device_id}")

            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                )
            except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
                logger.error("Failed to start parec process: %s", e)
                raise RuntimeError(f"Could not launch audio capture ('parec'): {e}") from e

            self._is_running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._reader_loop,
                args=(callback,),
                name="AudioStreamerReaderThread",
                daemon=True,
            )
            self._thread.start()
            logger.info(
                "AudioStreamer started (device=%s, rate=%d, chunk=%d samples)",
                self.device_id or "default",
                self.sample_rate,
                self.chunk_samples,
            )

    def _reader_loop(self, callback: Callable[[np.ndarray], None]) -> None:
        """Background loop reading PCM bytes from parec stdout fd."""
        if not self._process or not self._process.stdout:
            return

        fd = self._process.stdout.fileno()
        buffer = bytearray()

        while not self._stop_event.is_set():
            try:
                # Read up to chunk_bytes from the non-buffered pipe
                raw_bytes = os.read(fd, self.chunk_bytes)
                if not raw_bytes:
                    break

                buffer.extend(raw_bytes)

                # Dispatch whenever a complete chunk is accumulated
                while len(buffer) >= self.chunk_bytes:
                    chunk_raw = bytes(buffer[: self.chunk_bytes])
                    del buffer[: self.chunk_bytes]

                    audio_chunk = np.frombuffer(chunk_raw, dtype=np.float32)
                    try:
                        callback(audio_chunk)
                    except Exception as cb_err:
                        logger.exception("Exception in audio streamer callback: %s", cb_err)

            except (OSError, ValueError):
                # Happens cleanly when process stdout is closed or terminated
                break
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error("Error in audio stream reader loop: %s", e)
                break

        self._is_running = False

    def stop(self) -> None:
        """Stop audio capture and terminate worker thread and process."""
        with self._lock:
            if not self._is_running and self._process is None:
                return

            self._stop_event.set()
            if self._process:
                try:
                    if self._process.stdout:
                        self._process.stdout.close()
                    self._process.terminate()
                    self._process.wait(timeout=0.5)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                self._process = None

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.5)
                self._thread = None

            self._is_running = False
            logger.info("AudioStreamer stopped.")

    def is_running(self) -> bool:
        """Return True if audio streamer is currently capturing."""
        return self._is_running
