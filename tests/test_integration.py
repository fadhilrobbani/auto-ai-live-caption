"""
End-to-End Pipeline Integration Test.
Verifies audio frames -> VAD -> Local Faster-Whisper -> TextStabilizer -> Qt signals.
"""

import io
import os
import subprocess
import time
import unittest
import numpy as np
import soundfile as sf
from scipy import signal
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from core.models.registry import create_default_registry
from core.models.faster_whisper import DEFAULT_LOCAL_MODEL
from core.stabilizer.text_stabilizer import TextStabilizer
from ui.worker import CaptionWorker

os.environ["QT_QPA_PLATFORM"] = "offscreen"


class TestEndToEndPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["-platform", "offscreen"])

    def test_full_captioning_pipeline(self):
        # 1. Synthesize real speech
        cmd = ["espeak-ng", "Auto AI Live Caption is ready.", "--stdout"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        raw_audio, sr = sf.read(io.BytesIO(res.stdout), dtype="float32")
        if sr != 16000:
            num_samples = int(len(raw_audio) * 16000 / sr)
            audio = signal.resample(raw_audio, num_samples).astype(np.float32)
        else:
            audio = raw_audio.astype(np.float32)

        # 2. Setup Worker
        registry = create_default_registry(local_model_path=DEFAULT_LOCAL_MODEL)
        stabilizer = TextStabilizer()
        worker = CaptionWorker(
            registry=registry,
            stabilizer=stabilizer,
            is_monitor=False,
            language="en",
        )

        captions_collected = []
        statuses_collected = []

        worker.caption_received.connect(
            lambda hist, tent: captions_collected.append((hist, tent))
        )
        worker.status_updated.connect(lambda s: statuses_collected.append(s))

        # Start worker thread
        worker.start()

        # 3. Feed audio in 100ms frames into worker's frame queue
        frame_size = 1600
        for i in range(0, len(audio), frame_size):
            frame = audio[i : i + frame_size]
            if len(frame) < frame_size:
                frame = np.pad(frame, (0, frame_size - len(frame)))
            worker._on_audio_frame(frame)
            time.sleep(0.01)

        # Feed trailing silence frames to trigger pause boundary
        silence_frame = np.zeros(frame_size, dtype=np.float32)
        for _ in range(8):
            worker._on_audio_frame(silence_frame)
            time.sleep(0.01)

        # Process Qt events and wait for inference to complete
        start_wait = time.time()
        while time.time() - start_wait < 5.0:
            self.app.processEvents()
            if captions_collected and statuses_collected:
                break
            time.sleep(0.05)

        self.app.processEvents()
        worker.stop()
        registry.shutdown_all()

        # Assert results
        self.assertGreater(len(captions_collected), 0, "Worker should emit captions for speech")
        last_hist, last_tent = captions_collected[-1]
        full_text = f"{last_hist} {last_tent}".strip()
        print(f"\n[E2E Test] Pipeline transcribed text: '{full_text}'")
        self.assertTrue(bool(full_text), "Transcribed caption must not be empty")
        self.assertGreater(len(statuses_collected), 0)


if __name__ == "__main__":
    unittest.main()
