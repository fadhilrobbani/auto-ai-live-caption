"""
Unit tests for core.stabilizer.text_stabilizer.
"""

import unittest
from core.stabilizer.text_stabilizer import TextStabilizer


class TestTextStabilizer(unittest.TestCase):
    def setUp(self):
        self.stabilizer = TextStabilizer(max_history_lines=3, max_chars_per_line=30)

    def test_tentative_vs_committed(self):
        # Tentative update
        hist, tent = self.stabilizer.update("Hello everyone", is_final=False)
        self.assertEqual(hist, "")
        self.assertEqual(tent, "Hello everyone")

        # Final commit
        hist, tent = self.stabilizer.update("Hello everyone welcome", is_final=True)
        self.assertIn("Hello everyone welcome", hist)
        self.assertEqual(tent, "")

    def test_overlap_deduplication(self):
        # First committed chunk
        self.stabilizer.update("we are going to the store", is_final=True)
        # Second chunk repeating the last words "the store"
        hist, _ = self.stabilizer.update("the store to buy milk", is_final=True)
        # Verify "the store" was not duplicated into "the store the store"
        full = self.stabilizer.get_full_display_text()
        self.assertNotIn("the store the store", full)
        self.assertIn("buy milk", full)

    def test_line_wrapping_and_history_limit(self):
        # Add multiple long sentences
        self.stabilizer.update("Line number one is quite long here", is_final=True)
        self.stabilizer.update("Line number two is also quite long", is_final=True)
        self.stabilizer.update("Line number three is the third line", is_final=True)
        self.stabilizer.update("Line number four should push out line one", is_final=True)

        lines = self.stabilizer.get_history_text().split("\n")
        self.assertLessEqual(len(lines), 3, "Should respect max_history_lines")
        norm_history = " ".join(self.stabilizer.get_history_text().split())
        self.assertNotIn("Line number one", norm_history)
        self.assertIn("Line number four", norm_history)

    def test_clear(self):
        self.stabilizer.update("Some sample caption", is_final=True)
        self.stabilizer.update("Tentative word", is_final=False)
        self.stabilizer.clear()
        self.assertEqual(self.stabilizer.get_history_text(), "")
        self.assertEqual(self.stabilizer.get_full_display_text(), "")

    def test_tentative_helpers_and_filtering(self):
        # Blank audio / whisper tags should be filtered out
        self.stabilizer.update("[BLANK_AUDIO]", is_final=False)
        self.assertFalse(self.stabilizer.has_tentative())

        self.stabilizer.update("...", is_final=False)
        self.assertFalse(self.stabilizer.has_tentative())

        # Valid tentative text
        self.stabilizer.update("[music] Hello there", is_final=False)
        self.assertTrue(self.stabilizer.has_tentative())
        self.assertEqual(self.stabilizer._tentative, "Hello there")

        # Clear tentative
        hist, tent = self.stabilizer.clear_tentative()
        self.assertFalse(self.stabilizer.has_tentative())
        self.assertEqual(tent, "")


if __name__ == "__main__":
    unittest.main()
