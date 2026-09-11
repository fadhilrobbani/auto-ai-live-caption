#!/usr/bin/env /home/fadhilrobbani/.local/share/venvs/speech-processing/bin/python
"""
Auto AI Live Caption — Main Application Entry Point.
A real-time speech-to-text live captioning floating overlay for Linux (Wayland / X11).
"""

import argparse
import logging
import signal
import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from core.config.manager import ConfigManager, AppConfig
from core.models.registry import create_default_registry
from core.models.faster_whisper import DEFAULT_LOCAL_MODEL
from ui.history_dialog import TranscriptHistoryDialog
from ui.overlay import OverlayWindow
from ui.settings_dialog import SettingsDialog
from ui.tray import CaptionTrayIcon
from ui.worker import CaptionWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AutoLiveCaption")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Auto AI Live Caption — Real-time live speech captioning desktop overlay."
    )
    parser.add_argument(
        "--source",
        choices=["desktop", "mic"],
        default=None,
        help="Audio source: 'desktop' for loopback speaker monitor, or 'mic' for microphone.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Specific PulseAudio / PipeWire device ID to capture from.",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help=f"Path to local Faster-Whisper model weights (default: {DEFAULT_LOCAL_MODEL}).",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Spoken language code (e.g. 'en', 'id', 'ja'). Default: auto-detect.",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=None,
        help="Subtitle text font size (default from config: 18).",
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=None,
        help="Overlay background opacity 0.0 - 1.0 (default from config: 0.25).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # 1. Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Auto AI Live Caption")
    app.setApplicationDisplayName("Auto AI Live Caption")
    app.setOrganizationName("AutoLiveCaption")
    app.setQuitOnLastWindowClosed(False)

    # Graceful Ctrl+C handling inside Qt event loop
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(500)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())

    # 2. Load Configuration
    config_mgr = ConfigManager()
    cfg: AppConfig = config_mgr.config

    # Apply CLI overrides if specified
    if args.source:
        cfg.is_monitor = (args.source == "desktop")
    if args.device:
        cfg.audio_device_id = args.device
    if args.model_path:
        cfg.local_model_path = args.model_path
    if args.language:
        cfg.language = args.language
    if args.font_size:
        cfg.font_size = args.font_size
    if args.opacity is not None:
        cfg.overlay_opacity = max(0.0, min(1.0, args.opacity))

    # 3. Initialize Model Registry
    registry = create_default_registry(
        local_model_path=cfg.local_model_path,
        groq_api_key=cfg.groq_api_key,
        openai_api_key=cfg.openai_api_key,
    )
    # Set requested active engine
    if cfg.active_engine_id:
        registry.set_active(cfg.active_engine_id)

    # 4. Initialize UI Overlay
    overlay = OverlayWindow(config_manager=config_mgr)

    # 5. Initialize Background Captioning Worker
    worker = CaptionWorker(
        registry=registry,
        device_id=cfg.audio_device_id,
        is_monitor=cfg.is_monitor,
        language=cfg.language,
        latency_profile=getattr(cfg, "latency_profile", "fast"),
    )

    # 6. Initialize System Tray Integration
    tray = CaptionTrayIcon(
        overlay=overlay,
        is_monitor=cfg.is_monitor,
        is_paused=False,
        parent=app,
    )

    # Connect Worker -> Overlay signals
    worker.caption_received.connect(overlay.update_caption)
    worker.status_updated.connect(lambda s: logger.debug("Worker status: %s", s))
    worker.error_occurred.connect(lambda err: logger.error("Worker error: %s", err))

    # Connect Overlay Toolbar -> Worker controls
    overlay.toolbar.pause_toggled.connect(
        lambda is_paused: worker.pause() if is_paused else worker.resume()
    )
    overlay.toolbar.source_toggled.connect(
        lambda is_mon: worker.switch_audio_source(device_id=None, is_monitor=is_mon)
    )
    overlay.toolbar.clear_requested.connect(worker.clear_captions)

    # Connect Tray signals -> Worker and Overlay
    tray.source_toggled.connect(
        lambda is_mon: (worker.switch_audio_source(device_id=None, is_monitor=is_mon), overlay.toolbar.set_source(is_mon))
    )
    tray.pause_toggled.connect(
        lambda is_paused: (worker.pause() if is_paused else worker.resume(), overlay.toolbar.set_pause(is_paused))
    )
    tray.clear_requested.connect(worker.clear_captions)

    # Sync Overlay Toolbar & Visibility -> Tray
    overlay.toolbar.pause_toggled.connect(tray.set_pause_state)
    overlay.toolbar.source_toggled.connect(tray.set_source_state)
    overlay.visibility_changed.connect(tray.update_overlay_visibility_state)

    # Recording synchronization (Toolbar <-> Tray <-> Worker)
    def on_recording_toggled(is_rec: bool):
        if is_rec:
            worker.start_recording()
        else:
            worker.stop_recording()
        overlay.toolbar.set_recording(is_rec)
        tray.set_recording_state(is_rec)

    overlay.toolbar.recording_toggled.connect(on_recording_toggled)
    tray.recording_toggled.connect(on_recording_toggled)
    worker.recording_state_changed.connect(overlay.toolbar.set_recording)
    worker.recording_state_changed.connect(tray.set_recording_state)

    # History & Export Dialog handler
    history_dialog = None

    def open_history():
        nonlocal history_dialog
        if history_dialog is None:
            history_dialog = TranscriptHistoryDialog(
                recorder=worker.recorder,
                config_manager=config_mgr,
                parent=overlay,
            )
        else:
            history_dialog._refresh_content()

        history_dialog.show()
        history_dialog.raise_()
        history_dialog.activateWindow()

    overlay.history_requested.connect(open_history)
    tray.history_requested.connect(open_history)

    # Settings Dialog handler
    settings_dialog = None

    def open_settings():
        nonlocal settings_dialog
        if settings_dialog is None:
            settings_dialog = SettingsDialog(config_manager=config_mgr, registry=registry, parent=overlay)

            def on_settings_applied(changes: dict):
                # Update worker
                if "active_engine_id" in changes:
                    worker.switch_model(changes["active_engine_id"])
                if "audio_device_id" in changes:
                    worker.switch_audio_source(
                        device_id=changes["audio_device_id"],
                        is_monitor=changes.get("is_monitor", True),
                    )
                if "language" in changes:
                    worker.set_language(changes["language"])
                if "latency_profile" in changes:
                    worker.set_latency_profile(changes["latency_profile"])

                # Update overlay visuals
                if "font_size" in changes:
                    overlay._update_text_style()
                if "overlay_opacity" in changes:
                    overlay.set_overlay_opacity(changes["overlay_opacity"])
                if "is_monitor" in changes:
                    overlay.toolbar.set_source(changes["is_monitor"])
                    tray.set_source_state(changes["is_monitor"])

            settings_dialog.settings_applied.connect(on_settings_applied)

        settings_dialog.show()
        settings_dialog.raise_()
        settings_dialog.activateWindow()

    overlay.settings_requested.connect(open_settings)
    tray.settings_requested.connect(open_settings)

    # Clean shutdown
    def on_close():
        logger.info("Closing application...")
        # Auto-save session transcript if configured
        if getattr(cfg, "auto_save_on_close", False) and len(worker.recorder.get_segments()) > 0:
            try:
                from datetime import datetime
                from pathlib import Path
                save_dir = Path(getattr(cfg, "save_directory", None) or Path.home() / "Documents" / "AutoLiveCaptions")
                save_dir.mkdir(parents=True, exist_ok=True)
                now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                fmt = getattr(cfg, "default_export_format", "txt")
                if fmt == "srt":
                    worker.recorder.export_srt(save_dir / f"caption_{now_str}.srt")
                else:
                    worker.recorder.export_txt(save_dir / f"caption_{now_str}.txt")
                logger.info("Auto-saved session transcript to %s", save_dir)
            except Exception as auto_err:
                logger.error("Auto-save transcript error: %s", auto_err)

        tray.hide()
        overlay._force_close = True
        overlay.close()
        worker.stop()
        registry.shutdown_all()
        app.quit()

    tray.quit_requested.connect(on_close)
    overlay.closed.connect(on_close)
    app.aboutToQuit.connect(lambda: worker.stop())

    # 7. Start Captioning Pipeline & Display Window / Tray
    worker.start()
    overlay.show()
    tray.show()
    logger.info("Auto AI Live Caption is running. Overlay and system tray active.")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
