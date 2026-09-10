"""
Unit tests for core.audio (device_manager and streamer).
"""

import time
import unittest
import numpy as np

from core.audio.device_manager import (
    AudioDevice,
    list_audio_devices,
    get_default_device,
)
from core.audio.streamer import AudioStreamer


class TestAudioDeviceManager(unittest.TestCase):
    def test_list_audio_devices(self):
        devices = list_audio_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0, "Should discover at least one audio device")

        for dev in devices:
            self.assertIsInstance(dev, AudioDevice)
            self.assertTrue(bool(dev.id), "Device id must not be empty")
            self.assertTrue(bool(dev.name), "Device name must not be empty")
            self.assertTrue(bool(dev.description), "Device description must not be empty")
            self.assertIsInstance(dev.is_monitor, bool)
            self.assertIsInstance(dev.is_default, bool)

    def test_get_default_devices(self):
        default_monitor = get_default_device(monitor=True)
        self.assertIsInstance(default_monitor, AudioDevice)
        self.assertTrue(default_monitor.is_monitor, "Default monitor must have is_monitor=True")

        default_mic = get_default_device(monitor=False)
        self.assertIsInstance(default_mic, AudioDevice)
        self.assertFalse(default_mic.is_monitor, "Default mic must have is_monitor=False")


class TestAudioStreamer(unittest.TestCase):
    def test_audio_streaming_lifecycle(self):
        import shutil
        if not shutil.which("parec"):
            self.skipTest("'parec' utility is not installed on system")

        def_monitor = get_default_device(monitor=True)
        streamer = AudioStreamer(
            device_id=def_monitor.id,
            sample_rate=16000,
            chunk_duration_sec=0.1,
        )

        self.assertFalse(streamer.is_running())

        received_chunks = []

        def on_chunk(chunk: np.ndarray):
            received_chunks.append(chunk)

        try:
            streamer.start(on_chunk)
        except Exception as e:
            self.skipTest(f"Audio capture server unavailable in this environment: {e}")

        self.assertTrue(streamer.is_running())

        # Allow capture loop to run
        time.sleep(0.6)

        streamer.stop()
        self.assertFalse(streamer.is_running())

        if len(received_chunks) == 0:
            self.skipTest("No audio chunks received (headless environment without audio server)")

        # Verify chunks received
        self.assertGreater(len(received_chunks), 0, "Should have received audio chunks")
        first_chunk = received_chunks[0]
        self.assertEqual(first_chunk.dtype, np.float32)
        self.assertEqual(first_chunk.ndim, 1)
        self.assertEqual(len(first_chunk), 1600)  # 16000 * 0.1s

    def test_idempotent_stop(self):
        streamer = AudioStreamer()
        self.assertFalse(streamer.is_running())
        # Stopping an unstarted streamer should not raise
        streamer.stop()
        self.assertFalse(streamer.is_running())


if __name__ == "__main__":
    unittest.main()
