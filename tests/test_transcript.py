"""
Unit tests for TranscriptRecorder and Subtitle Export module.
"""

import json
import tempfile
import unittest
from pathlib import Path

from core.transcript.recorder import (
    TranscriptRecorder,
    TranscriptSegment,
    format_srt_timestamp,
    format_wall_time,
)


class TestTranscriptRecorder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.export_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_format_srt_timestamp(self):
        self.assertEqual(format_srt_timestamp(0.0), "00:00:00,000")
        self.assertEqual(format_srt_timestamp(-5.0), "00:00:00,000")
        self.assertEqual(format_srt_timestamp(1.25), "00:00:01,250")
        self.assertEqual(format_srt_timestamp(65.5), "00:01:05,500")
        self.assertEqual(format_srt_timestamp(3661.045), "01:01:01,045")

    def test_format_wall_time(self):
        wt = format_wall_time(1700000000)
        self.assertRegex(wt, r"^\d{2}:\d{2}:\d{2}$")

    def test_recorder_initialization_and_toggle(self):
        recorder = TranscriptRecorder(auto_record=True)
        self.assertTrue(recorder.is_recording)

        # Toggle off
        new_state = recorder.toggle_recording()
        self.assertFalse(new_state)
        self.assertFalse(recorder.is_recording)

        # Toggle on
        new_state = recorder.toggle_recording()
        self.assertTrue(new_state)
        self.assertTrue(recorder.is_recording)

        # Explicit stop / start
        recorder.stop_recording()
        self.assertFalse(recorder.is_recording)
        recorder.start_recording()
        self.assertTrue(recorder.is_recording)

    def test_add_segment(self):
        recorder = TranscriptRecorder(auto_record=True)

        # Empty segment should be ignored
        seg0 = recorder.add_segment("   ")
        self.assertIsNone(seg0)
        self.assertEqual(len(recorder.get_segments()), 0)

        # Add valid segment
        seg1 = recorder.add_segment("Hello world", duration_sec=2.0, language="en")
        self.assertIsNotNone(seg1)
        self.assertEqual(seg1.index, 1)
        self.assertEqual(seg1.text, "Hello world")
        self.assertEqual(seg1.language, "en")
        self.assertGreaterEqual(seg1.end_time, seg1.start_time)
        self.assertEqual(len(recorder.get_segments()), 1)

        # Add second segment
        seg2 = recorder.add_segment("This is caption recording.", duration_sec=1.8, language="en")
        self.assertIsNotNone(seg2)
        self.assertEqual(seg2.index, 2)
        self.assertGreaterEqual(seg2.start_time, seg1.end_time)
        self.assertEqual(len(recorder.get_segments()), 2)

    def test_add_segment_when_recording_paused(self):
        recorder = TranscriptRecorder(auto_record=False)
        self.assertFalse(recorder.is_recording)

        # Segment returns object but is NOT saved in segments list
        seg = recorder.add_segment("Unrecorded speech")
        self.assertIsNotNone(seg)
        self.assertEqual(len(recorder.get_segments()), 0)

        # Resume recording
        recorder.start_recording()
        seg2 = recorder.add_segment("Recorded speech")
        self.assertEqual(len(recorder.get_segments()), 1)
        self.assertEqual(recorder.get_segments()[0].text, "Recorded speech")

    def test_get_full_text(self):
        recorder = TranscriptRecorder(auto_record=True)
        self.assertEqual(recorder.get_full_text(), "")

        recorder.add_segment("First sentence.")
        recorder.add_segment("Second sentence.")

        plain = recorder.get_full_text(include_timestamps=False)
        self.assertEqual(plain, "First sentence.\nSecond sentence.")

        with_time = recorder.get_full_text(include_timestamps=True)
        self.assertIn("First sentence.", with_time)
        self.assertIn("Second sentence.", with_time)
        self.assertIn("[", with_time)
        self.assertIn("]", with_time)

    def test_format_srt(self):
        recorder = TranscriptRecorder(auto_record=True)
        self.assertEqual(recorder.format_srt(), "")

        recorder.add_segment("Testing subtitle format 1.", duration_sec=2.0)
        recorder.add_segment("Testing subtitle format 2.", duration_sec=2.5)

        srt = recorder.format_srt()
        self.assertIn("1\n", srt)
        self.assertIn(" --> ", srt)
        self.assertIn("Testing subtitle format 1.", srt)
        self.assertIn("2\n", srt)
        self.assertIn("Testing subtitle format 2.", srt)

    def test_export_txt(self):
        recorder = TranscriptRecorder(auto_record=True)
        recorder.add_segment("Export test line 1")
        recorder.add_segment("Export test line 2")

        file_path = self.export_dir / "captions.txt"
        exported = recorder.export_txt(file_path, include_timestamps=True)
        self.assertTrue(exported.exists())

        content = exported.read_text(encoding="utf-8")
        self.assertIn("Export test line 1", content)
        self.assertIn("Export test line 2", content)

    def test_export_srt(self):
        recorder = TranscriptRecorder(auto_record=True)
        recorder.add_segment("SRT line one", duration_sec=1.5)
        recorder.add_segment("SRT line two", duration_sec=2.0)

        file_path = self.export_dir / "captions.srt"
        exported = recorder.export_srt(file_path)
        self.assertTrue(exported.exists())

        content = exported.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("1\n"))
        self.assertIn("00:00:", content)
        self.assertIn("SRT line one", content)
        self.assertIn("SRT line two", content)

    def test_export_json(self):
        recorder = TranscriptRecorder(auto_record=True)
        recorder.add_segment("JSON test sentence", language="en")

        file_path = self.export_dir / "captions.json"
        exported = recorder.export_json(file_path)
        self.assertTrue(exported.exists())

        data = json.loads(exported.read_text(encoding="utf-8"))
        self.assertEqual(data["total_segments"], 1)
        self.assertEqual(data["segments"][0]["text"], "JSON test sentence")
        self.assertEqual(data["segments"][0]["language"], "en")
        self.assertIn("stats", data)

    def test_clear_and_stats(self):
        recorder = TranscriptRecorder(auto_record=True)
        recorder.add_segment("Four word test phrase", duration_sec=3.0)

        stats = recorder.get_stats()
        self.assertEqual(stats["segment_count"], 1)
        self.assertEqual(stats["word_count"], 4)
        self.assertGreater(stats["duration_seconds"], 0)
        self.assertTrue(stats["is_recording"])

        recorder.clear()
        self.assertEqual(len(recorder.get_segments()), 0)
        stats_cleared = recorder.get_stats()
        self.assertEqual(stats_cleared["segment_count"], 0)
        self.assertEqual(stats_cleared["word_count"], 0)
        self.assertEqual(stats_cleared["duration_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
