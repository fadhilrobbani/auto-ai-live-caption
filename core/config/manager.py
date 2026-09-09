"""
Persistent JSON Configuration Manager for Auto AI Live Caption.
Stores settings in ~/.config/auto-ai-live-caption/config.json.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "auto-ai-live-caption"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_LOCAL_MODEL = "/home/fadhilrobbani/.local/share/models/whisper/faster-whisper-base"


@dataclass
class AppConfig:
    audio_device_id: Optional[str] = "@DEFAULT_MONITOR@"
    is_monitor: bool = True
    active_engine_id: str = "faster-whisper-faster-whisper-base"
    local_model_path: str = DEFAULT_LOCAL_MODEL
    groq_api_key: str = ""
    openai_api_key: str = ""
    language: str = "auto"
    font_size: int = 18
    font_family: str = "Inter, Roboto, sans-serif"
    overlay_opacity: float = 0.85
    overlay_width: int = 760
    overlay_height: int = 150
    overlay_x: int = -1
    overlay_y: int = -1
    always_on_top: bool = True
    hide_controls: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """
    Thread-safe config manager handling serialization to and from JSON.
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self.config_dir = self.config_file.parent
        self._config: AppConfig = self.load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def load(self) -> AppConfig:
        """Load config from disk or return default if missing/corrupt."""
        if not self.config_file.exists():
            return AppConfig()

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Match fields with dataclass
            known_fields = {k: v for k, v in data.items() if k in AppConfig.__annotations__}
            extra_fields = {k: v for k, v in data.items() if k not in AppConfig.__annotations__}
            if extra_fields:
                known_fields["extra"] = extra_fields

            return AppConfig(**known_fields)
        except Exception as e:
            logger.warning("Failed to load config from %s: %s (using defaults)", self.config_file, e)
            return AppConfig()

    def save(self, config: Optional[AppConfig] = None) -> bool:
        """Save current or provided config to disk."""
        if config is not None:
            self._config = config

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            data = asdict(self._config)
            # Flatten extra if present
            extra = data.pop("extra", {})
            data.update(extra)

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved config to %s", self.config_file)
            return True
        except Exception as e:
            logger.error("Failed to save config to %s: %s", self.config_file, e)
            return False

    def update(self, **kwargs) -> bool:
        """Update specific config properties and persist to disk."""
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
            else:
                self._config.extra[k] = v
        return self.save()
