"""
Transcript History & Export Dialog for Auto AI Live Caption.
Provides a modal view to inspect live conversation history, search through
recorded words, and export to TXT, SubRip Subtitles (SRT), or Clipboard.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config.manager import ConfigManager
from core.transcript.recorder import TranscriptRecorder


class TranscriptHistoryDialog(QDialog):
    """
    Dialog for viewing, searching, and exporting session transcripts.
    """

    def __init__(
        self,
        recorder: TranscriptRecorder,
        config_manager: Optional[ConfigManager] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.recorder = recorder
        self.config_manager = config_manager or ConfigManager()
        self.cfg = self.config_manager.config

        self._init_ui()
        self._refresh_content()

    def _init_ui(self) -> None:
        self.setWindowTitle("Transcript History & Export")
        self.resize(700, 500)
        self.setMinimumSize(540, 380)

        self.setStyleSheet(
            """
            QDialog {
                background-color: #141722;
                color: #f8fafc;
            }
            QLabel {
                color: #f8fafc;
            }
            QLineEdit {
                background-color: #1e2230;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            QTextEdit {
                background-color: #181b26;
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                padding: 10px;
                font-family: monospace, sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
            QPushButton {
                background-color: #262a3b;
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #33384c;
                color: #ffffff;
                border-color: rgba(255, 255, 255, 0.25);
            }
            QPushButton:pressed {
                background-color: #1a1d29;
            }
            QPushButton#PrimaryBtn {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#DangerBtn:hover {
                background-color: #7f1d1d;
                border-color: #ef4444;
                color: #ffffff;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Header Bar: Title + Stats
        header_layout = QHBoxLayout()
        title_label = QLabel("Session Transcript", self)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self.stats_label = QLabel(self)
        self.stats_label.setStyleSheet("font-size: 12px; color: #94a3b8;")
        header_layout.addWidget(self.stats_label)

        layout.addLayout(header_layout)

        # 2. Search Box
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search spoken keywords...")
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input)

        # 3. Transcript Text Area
        self.text_area = QTextEdit(self)
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

        # 4. Action Buttons Bar
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        # Export TXT
        self.export_txt_btn = QPushButton("Export .TXT", self)
        self.export_txt_btn.setProperty("class", "PrimaryBtn")
        self.export_txt_btn.setObjectName("PrimaryBtn")
        self.export_txt_btn.setToolTip("Save transcript as formatted text file with timestamps")
        self.export_txt_btn.clicked.connect(self._export_txt)
        actions_layout.addWidget(self.export_txt_btn)

        # Export SRT
        self.export_srt_btn = QPushButton("Export .SRT", self)
        self.export_srt_btn.setProperty("class", "PrimaryBtn")
        self.export_srt_btn.setObjectName("PrimaryBtn")
        self.export_srt_btn.setToolTip("Save as standard SubRip subtitle track (.srt)")
        self.export_srt_btn.clicked.connect(self._export_srt)
        actions_layout.addWidget(self.export_srt_btn)

        # Copy to Clipboard
        self.copy_btn = QPushButton("Copy All", self)
        self.copy_btn.setToolTip("Copy entire transcript to clipboard")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        actions_layout.addWidget(self.copy_btn)

        actions_layout.addStretch()

        # Clear History
        self.clear_btn = QPushButton("Clear History", self)
        self.clear_btn.setObjectName("DangerBtn")
        self.clear_btn.setToolTip("Clear recorded session transcript")
        self.clear_btn.clicked.connect(self._clear_history)
        actions_layout.addWidget(self.clear_btn)

        # Close
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)

        layout.addLayout(actions_layout)

    def _refresh_content(self, filter_text: str = "") -> None:
        """Update text display and statistics."""
        segments = self.recorder.get_segments()
        stats = self.recorder.get_stats()

        # Format stats header
        minutes = int(stats["duration_seconds"] // 60)
        seconds = int(stats["duration_seconds"] % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        status_rec = "⏺ Recording" if stats["is_recording"] else "⏹ Paused"
        self.stats_label.setText(
            f"{stats['word_count']} words  •  {stats['segment_count']} lines  •  {time_str}  •  {status_rec}"
        )

        if not segments:
            self.text_area.setHtml(
                "<p style='color: #64748b; font-style: italic;'>No captions recorded in this session yet. "
                "Speak or play audio to generate live transcript lines.</p>"
            )
            return

        # Render HTML segments
        lines_html = []
        filter_lower = filter_text.strip().lower()

        for seg in segments:
            text = seg.text
            if filter_lower:
                if filter_lower not in text.lower():
                    continue
                # Highlight match
                start_idx = text.lower().find(filter_lower)
                end_idx = start_idx + len(filter_lower)
                highlighted = (
                    text[:start_idx]
                    + f"<span style='background-color: #1d4ed8; color: #ffffff; font-weight: bold;'>{text[start_idx:end_idx]}</span>"
                    + text[end_idx:]
                )
            else:
                highlighted = text

            line_html = (
                f"<div style='margin-bottom: 6px;'>"
                f"<span style='color: #60a5fa; font-weight: 600; font-family: monospace;'>[{seg.wall_time}]</span> "
                f"<span style='color: #f1f5f9;'>{highlighted}</span>"
                f"</div>"
            )
            lines_html.append(line_html)

        if not lines_html and filter_lower:
            self.text_area.setHtml(
                f"<p style='color: #64748b; font-style: italic;'>No matches found for '{filter_text}'.</p>"
            )
        else:
            self.text_area.setHtml("".join(lines_html))
            self.text_area.moveCursor(QTextCursor.End)

    def _on_search_changed(self, text: str) -> None:
        self._refresh_content(filter_text=text)

    def _get_default_dir(self) -> str:
        d = getattr(self.cfg, "save_directory", None)
        if not d:
            d = str(Path.home() / "Documents" / "AutoLiveCaptions")
        Path(d).mkdir(parents=True, exist_ok=True)
        return d

    def _export_txt(self) -> None:
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = f"caption_{now_str}.txt"
        default_path = str(Path(self._get_default_dir()) / default_filename)

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Transcript as Text",
            default_path,
            "Text Files (*.txt);;All Files (*)",
        )
        if filepath:
            try:
                self.recorder.export_txt(filepath, include_timestamps=True)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Transcript exported successfully to:\n{filepath}",
                )
            except Exception as err:
                QMessageBox.critical(self, "Export Failed", f"Could not save file:\n{err}")

    def _export_srt(self) -> None:
        now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = f"caption_{now_str}.srt"
        default_path = str(Path(self._get_default_dir()) / default_filename)

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Transcript as Subtitles",
            default_path,
            "SubRip Subtitle Files (*.srt);;All Files (*)",
        )
        if filepath:
            try:
                self.recorder.export_srt(filepath)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"SubRip Subtitles exported successfully to:\n{filepath}",
                )
            except Exception as err:
                QMessageBox.critical(self, "Export Failed", f"Could not save file:\n{err}")

    def _copy_to_clipboard(self) -> None:
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = self.recorder.get_full_text(include_timestamps=True)
        if text:
            clipboard.setText(text)
            self.copy_btn.setText("✓ Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy All"))
        else:
            self.copy_btn.setText("Empty")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy All"))

    def _clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clear Transcript History",
            "Are you sure you want to clear all recorded transcript history for this session?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.recorder.clear()
            self._refresh_content()
