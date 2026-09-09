"""
Unit tests for core.vad.processor (Voice Activity Detection & Chunking).
"""

import io
import subprocess
import unittest
import numpy as np
import soundfile as sf
from scipy import signal

from core.vad.processor import VADProcessor


class TestVADProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = VADProcessor(
            sample_rate=16000,
            speech_threshold=0.5,
            energy_threshold=0.005,
            min_speech_duration_sec=0.4,
            max_chunk_duration_sec=2.5,
            silence_timeout_sec=0.5,
        )

    def test_silence_rejection(self):
        """Verify that pure silence and low-level noise are rejected."""
        # 1. Digital zero silence (20 frames of 100ms = 2.0s)
        silence_frame = np.zeros(1600, dtype=np.float32)
        for _ in range(20):
            res = self.processor.process_frame(silence_frame)
            self.assertIsNone(res, "Silence frames should never trigger chunk emission")

        # 2. Low-level ambient noise (RMS below energy threshold)
        noise_frame = (np.random.rand(1600).astype(np.float32) - 0.5) * 0.002
        for _ in range(10):
            res = self.processor.process_frame(noise_frame)
            self.assertIsNone(res, "Low-level noise should be rejected")

        # Flush should also return None since no speech was buffered
        self.assertIsNone(self.processor.flush())

    def test_speech_detection_and_chunking(self):
        """Verify that genuine speech audio is recognized and chunked."""
        # Generate genuine speech using espeak-ng
        try:
            cmd = ["espeak-ng", "Auto AI Live Caption is running.", "--stdout"]
            res = subprocess.run(cmd, capture_output=True, check=True)
            raw_audio, sr = sf.read(io.BytesIO(res.stdout), dtype="float32")
        except Exception as e:
            self.skipTest(f"espeak-ng not available for speech generation: {e}")

        # Resample to 16000Hz if needed
        if sr != 16000:
            num_target_samples = int(len(raw_audio) * 16000 / sr)
            audio = signal.resample(raw_audio, num_target_samples).astype(np.float32)
        else:
            audio = raw_audio.astype(np.float32)

        frame_size = 1600  # 100ms
        chunks = []

        # Feed speech frames
        for i in range(0, len(audio), frame_size):
            frame = audio[i : i + frame_size]
            if len(frame) < frame_size:
                frame = np.pad(frame, (0, frame_size - len(frame)))
            out = self.processor.process_frame(frame)
            if out is not None:
                chunks.append(out)

        # Feed trailing silence to trigger pause finalization
        silence_frame = np.zeros(frame_size, dtype=np.float32)
        for _ in range(8):  # 800ms silence > silence_timeout (500ms)
            out = self.processor.process_frame(silence_frame)
            if out is not None:
                chunks.append(out)

        # Or flush any remaining
        flushed = self.processor.flush()
        if flushed is not None:
            chunks.append(flushed)

        self.assertGreater(len(chunks), 0, "VAD must emit at least one chunk for spoken speech")
        for chunk in chunks:
            self.assertIsInstance(chunk, np.ndarray)
            self.assertEqual(chunk.dtype, np.float32)
            # Must satisfy minimum speech duration (0.4s * 16000 = 6400 samples)
            self.assertGreaterEqual(len(chunk), 6400)

    def test_reset_and_flush(self):
        """Verify that reset clears all internal buffers."""
        frame = np.ones(1600, dtype=np.float32) * 0.1
        # Feed frames
        self.processor._in_speech = True
        self.processor._speech_buffer = [frame, frame]
        self.processor._current_speech_samples = 3200

        self.processor.reset()
        self.assertFalse(self.processor._in_speech)
        self.assertEqual(len(self.processor._speech_buffer), 0)
        self.assertEqual(self.processor._current_speech_samples, 0)
        self.assertIsNone(self.processor.flush())


if __name__ == "__main__":
    unittest.main()
