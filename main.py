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
from PySide6.QtWidgets import QApplication

from core.config.manager import ConfigManager, AppConfig
from core.models.registry import create_default_registry
from core.models.faster_whisper import DEFAULT_LOCAL_MODEL
from ui.overlay import OverlayWindow
from ui.settings_dialog import SettingsDialog
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
    if args.opacity:
        cfg.overlay_opacity = max(0.3, min(1.0, args.opacity))

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

            settings_dialog.settings_applied.connect(on_settings_applied)

        settings_dialog.show()
        settings_dialog.raise_()
        settings_dialog.activateWindow()

    overlay.settings_requested.connect(open_settings)

    # Clean shutdown
    def on_close():
        logger.info("Closing application...")
        worker.stop()
        registry.shutdown_all()
        app.quit()

    overlay.closed.connect(on_close)
    app.aboutToQuit.connect(lambda: worker.stop())

    # 6. Start Captioning Pipeline & Display Window
    worker.start()
    overlay.show()
    logger.info("Auto AI Live Caption is running. Overlay visible.")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
