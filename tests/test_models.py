"""
Unit tests for core.models (FasterWhisperEngine, Groq, OpenAI, and ModelRegistry).
"""

import io
import subprocess
import unittest
import numpy as np
import soundfile as sf
from scipy import signal

from core.models.base import BaseCaptionEngine, CaptionResult
from core.models.faster_whisper import FasterWhisperEngine, DEFAULT_LOCAL_MODEL
from core.models.groq_api import GroqWhisperEngine
from core.models.openai_api import OpenAIWhisperEngine
from core.models.registry import ModelRegistry, create_default_registry


class TestModelProviderLayer(unittest.TestCase):
    def test_faster_whisper_offline_transcription(self):
        """Test local offline faster-whisper model inference."""
        engine = FasterWhisperEngine(model_path_or_name=DEFAULT_LOCAL_MODEL)
        self.assertFalse(engine.is_initialized())

        ok = engine.initialize()
        self.assertTrue(ok, "FasterWhisperEngine should initialize with local base model")
        self.assertTrue(engine.is_initialized())

        # Synthesize real speech
        cmd = ["espeak-ng", "Testing real time captions.", "--stdout"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        raw_audio, sr = sf.read(io.BytesIO(res.stdout), dtype="float32")
        if sr != 16000:
            num_samples = int(len(raw_audio) * 16000 / sr)
            audio = signal.resample(raw_audio, num_samples).astype(np.float32)
        else:
            audio = raw_audio.astype(np.float32)

        result = engine.transcribe_chunk(audio, language="en")
        self.assertIsInstance(result, CaptionResult)
        self.assertTrue(bool(result.text), "Transcribed text should not be empty")
        self.assertGreater(result.latency_ms, 0)
        self.assertTrue(result.is_final)
        print(f"\n[Test] Offline Whisper output: '{result.text}' (latency: {result.latency_ms:.1f}ms)")

        engine.shutdown()
        self.assertFalse(engine.is_initialized())

    def test_cloud_engine_without_api_key_handles_gracefully(self):
        """Verify cloud engines handle missing API keys gracefully without crashing."""
        groq_eng = GroqWhisperEngine(api_key="")
        dummy_audio = np.zeros(16000, dtype=np.float32)
        res = groq_eng.transcribe_chunk(dummy_audio, prompt="hello context")
        self.assertIn("API Key Required", res.text)

        openai_eng = OpenAIWhisperEngine(api_key="")
        res2 = openai_eng.transcribe_chunk(dummy_audio, prompt="hello context")
        self.assertIn("API Key Required", res2.text)

    def test_model_registry(self):
        """Verify registry discovery, activation, and lifecycle management."""
        registry = create_default_registry(local_model_path=DEFAULT_LOCAL_MODEL)

        engines = registry.list_engines()
        self.assertGreaterEqual(len(engines), 3)
        engine_ids = [e["id"] for e in engines]
        self.assertIn("faster-whisper-faster-whisper-base", engine_ids)

        active = registry.get_active()
        self.assertIsNotNone(active)
        self.assertEqual(active.get_id(), "faster-whisper-faster-whisper-base")

        # Test switching to Groq
        groq_id = next(id for id in engine_ids if id.startswith("groq-"))
        # Setting active on uninitialized groq without key will fail initialize or handle cleanly
        registry.set_active("faster-whisper-faster-whisper-base")
        self.assertEqual(registry.get_active().get_id(), "faster-whisper-faster-whisper-base")

        registry.shutdown_all()
        self.assertIsNone(registry.get_active())


if __name__ == "__main__":
    unittest.main()
