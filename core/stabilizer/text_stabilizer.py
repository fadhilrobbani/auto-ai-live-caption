"""
Live Subtitle Text Stream Stabilizer & History Reconciler.
Prevents flicker, eliminates repeated words at chunk boundaries,
and manages committed history vs in-flight tentative text.
"""

import re
from typing import List, Tuple


class TextStabilizer:
    """
    Stabilizes real-time text output from streaming ASR chunks,
    reconciling committed history lines with tentative in-flight text.
    """

    def __init__(self, max_history_lines: int = 4, max_chars_per_line: int = 70):
        self.max_history_lines = max_history_lines
        self.max_chars_per_line = max_chars_per_line

        self._history_lines: List[str] = []
        self._tentative: str = ""
        self._last_committed_chunk: str = ""

    def _deduplicate_overlap(self, prev_text: str, new_text: str) -> str:
        """
        Detect and strip overlapping words between end of prev_text and start of new_text.
        e.g., prev: "we are going to" + new: "going to the store" -> "the store"
        """
        prev_words = prev_text.strip().split()
        new_words = new_text.strip().split()

        if not prev_words or not new_words:
            return new_text.strip()

        # Check for multi-word overlap (at least 2 words to avoid stripping common single words)
        max_check = min(len(prev_words), len(new_words), 6)
        if max_check < 2:
            return new_text.strip()

        for overlap_len in range(max_check, 1, -1):
            prev_slice = [w.lower().strip(".,!?:;\"'") for w in prev_words[-overlap_len:]]
            new_slice = [w.lower().strip(".,!?:;\"'") for w in new_words[:overlap_len]]
            if prev_slice == new_slice:
                return " ".join(new_words[overlap_len:]).strip()

        return new_text.strip()

    def update(self, new_chunk_text: str, is_final: bool = False) -> Tuple[str, str]:
        """
        Update with newly transcribed text.
        Returns: (committed_history_text, tentative_in_flight_text)
        """
        # Strip whisper annotation tags like [BLANK_AUDIO], (laughter), [music], etc.
        cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", new_chunk_text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # If it contains no word characters (only punctuation/symbols), treat as blank
        if not re.search(r"[\w]", cleaned):
            if is_final:
                self._tentative = ""
            return self.get_history_text(), self._tentative

        # Remove repetitive boundary words from last committed chunk
        if self._last_committed_chunk:
            cleaned = self._deduplicate_overlap(self._last_committed_chunk, cleaned)
            if not cleaned or not re.search(r"[\w]", cleaned):
                if is_final:
                    self._tentative = ""
                return self.get_history_text(), self._tentative

        if is_final:
            self._commit_text(cleaned)
            self._last_committed_chunk = cleaned
            self._tentative = ""
        else:
            self._tentative = cleaned

        return self.get_history_text(), self._tentative

    def clear_tentative(self) -> Tuple[str, str]:
        """Clear any uncommitted tentative text without affecting history."""
        self._tentative = ""
        return self.get_history_text(), ""

    def has_tentative(self) -> bool:
        """Check whether there is active uncommitted tentative text."""
        return bool(self._tentative)

    def _commit_text(self, text: str) -> None:
        """Add text into rolling line buffer, wrapping to max_chars_per_line."""
        words = text.split()
        if not words:
            return

        current_line = self._history_lines[-1] if self._history_lines else ""
        lines_to_add = []

        if current_line:
            combined = f"{current_line} {words[0]}"
            if len(combined) <= self.max_chars_per_line:
                current_line = combined
                words = words[1:]
            else:
                lines_to_add.append(current_line)
                current_line = ""

        for word in words:
            if not current_line:
                current_line = word
            elif len(current_line) + len(word) + 1 <= self.max_chars_per_line:
                current_line = f"{current_line} {word}"
            else:
                lines_to_add.append(current_line)
                current_line = word

        if current_line:
            lines_to_add.append(current_line)

        # Update history lines
        self._history_lines = lines_to_add[-self.max_history_lines :]

    def get_history_text(self) -> str:
        """Return the current formatted committed history."""
        return "\n".join(self._history_lines)

    def get_full_display_text(self) -> str:
        """Return history combined with active tentative text."""
        history = self.get_history_text()
        if self._tentative:
            if history:
                return f"{history}\n{self._tentative}"
            return self._tentative
        return history

    def clear(self) -> None:
        """Reset all history and in-flight buffers."""
        self._history_lines.clear()
        self._tentative = ""
        self._last_committed_chunk = ""
