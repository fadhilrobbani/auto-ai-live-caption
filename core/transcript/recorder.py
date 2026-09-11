"""
Session Transcript Recorder & Subtitle Exporter.
Tracks real-time committed speech segments with timestamps and exports to
TXT, standard SubRip Subtitles (SRT), and JSON.
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


def format_srt_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp format: HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_wall_time(epoch_time: Optional[float] = None) -> str:
    """Format epoch time into local time string: HH:MM:SS."""
    dt = datetime.fromtimestamp(epoch_time) if epoch_time else datetime.now()
    return dt.strftime("%H:%M:%S")


@dataclass
class TranscriptSegment:
    index: int
    start_time: float      # Seconds from session start
    end_time: float        # Seconds from session start
    wall_time: str         # Local wall-clock time HH:MM:SS
    text: str              # Finalized text
    language: str = ""     # Language code
    epoch_time: float = 0.0  # Unix timestamp


class TranscriptRecorder:
    """
    Records, aggregates, and exports live caption history.
    """

    def __init__(self, auto_record: bool = True):
        self._is_recording: bool = auto_record
        self._start_epoch: float = time.time()
        self._last_segment_end: float = 0.0
        self._segments: List[TranscriptSegment] = []

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start_recording(self) -> None:
        """Start or resume recording caption segments."""
        if not self._is_recording:
            self._is_recording = True
            logger.info("Transcript recording started.")

    def stop_recording(self) -> None:
        """Pause or stop recording caption segments."""
        if self._is_recording:
            self._is_recording = False
            logger.info("Transcript recording stopped.")

    def toggle_recording(self) -> bool:
        """Toggle recording state and return the new state."""
        if self._is_recording:
            self.stop_recording()
        else:
            self.start_recording()
        return self._is_recording

    def add_segment(
        self,
        text: str,
        duration_sec: float = 0.0,
        language: str = "",
        epoch_time: Optional[float] = None,
    ) -> Optional[TranscriptSegment]:
        """
        Add a committed subtitle chunk to the session transcript.
        """
        cleaned = text.strip()
        if not cleaned:
            return None

        now = epoch_time or time.time()
        rel_time = max(0.0, now - self._start_epoch)

        # Estimate segment start and end times
        dur = max(duration_sec, 1.2)
        start_t = max(self._last_segment_end, rel_time - dur)
        end_t = max(start_t + 0.5, rel_time)
        self._last_segment_end = end_t

        segment = TranscriptSegment(
            index=len(self._segments) + 1,
            start_time=round(start_t, 3),
            end_time=round(end_t, 3),
            wall_time=format_wall_time(now),
            text=cleaned,
            language=language,
            epoch_time=now,
        )

        # Only append if recording is active
        if self._is_recording:
            self._segments.append(segment)
            logger.debug("Recorded segment #%d: '%s'", segment.index, segment.text)

        return segment

    def get_segments(self) -> List[TranscriptSegment]:
        """Return a copy of all recorded segments."""
        return list(self._segments)

    def get_full_text(self, include_timestamps: bool = False) -> str:
        """Return concatenated transcript lines."""
        if not self._segments:
            return ""

        if include_timestamps:
            return "\n".join(
                f"[{seg.wall_time}] {seg.text}" for seg in self._segments
            )
        return "\n".join(seg.text for seg in self._segments)

    def format_srt(self) -> str:
        """Format recorded segments into SubRip Subtitles (SRT) format."""
        if not self._segments:
            return ""

        blocks = []
        for i, seg in enumerate(self._segments, 1):
            start_fmt = format_srt_timestamp(seg.start_time)
            end_fmt = format_srt_timestamp(seg.end_time)
            blocks.append(f"{i}\n{start_fmt} --> {end_fmt}\n{seg.text}\n")

        return "\n".join(blocks).strip() + "\n"

    def export_txt(
        self, filepath: Union[str, Path], include_timestamps: bool = True
    ) -> Path:
        """Export transcript to a plain text file."""
        target = Path(filepath).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        content = self.get_full_text(include_timestamps=include_timestamps)
        target.write_text(content, encoding="utf-8")
        logger.info("Exported transcript TXT to: %s", target)
        return target

    def export_srt(self, filepath: Union[str, Path]) -> Path:
        """Export transcript to a standard SRT subtitle file."""
        target = Path(filepath).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        content = self.format_srt()
        target.write_text(content, encoding="utf-8")
        logger.info("Exported transcript SRT to: %s", target)
        return target

    def export_json(self, filepath: Union[str, Path]) -> Path:
        """Export transcript segments to a structured JSON file."""
        target = Path(filepath).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_start": format_wall_time(self._start_epoch),
            "total_segments": len(self._segments),
            "stats": self.get_stats(),
            "segments": [asdict(s) for s in self._segments],
        }
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Exported transcript JSON to: %s", target)
        return target

    def clear(self) -> None:
        """Clear all recorded segments and reset timeline."""
        self._segments.clear()
        self._start_epoch = time.time()
        self._last_segment_end = 0.0
        logger.info("Transcript history cleared.")

    def get_stats(self) -> dict:
        """Return session statistics."""
        word_count = sum(len(seg.text.split()) for seg in self._segments)
        duration = self._last_segment_end
        return {
            "segment_count": len(self._segments),
            "word_count": word_count,
            "duration_seconds": round(duration, 1),
            "is_recording": self._is_recording,
        }
