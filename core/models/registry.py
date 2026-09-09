"""
Model Provider Registry & Lifecycle Manager.
Supports dynamic model registration, switching, and fallback.
"""

import logging
from typing import Dict, List, Optional

from core.models.base import BaseCaptionEngine
from core.models.faster_whisper import FasterWhisperEngine, DEFAULT_LOCAL_MODEL
from core.models.groq_api import GroqWhisperEngine
from core.models.openai_api import OpenAIWhisperEngine

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central repository for instantiating, querying, and switching
    between offline local models and cloud ASR providers.
    """

    def __init__(self):
        self._engines: Dict[str, BaseCaptionEngine] = {}
        self._active_id: Optional[str] = None

    def register(self, engine: BaseCaptionEngine, set_active: bool = False) -> None:
        """Register an engine instance."""
        eng_id = engine.get_id()
        self._engines[eng_id] = engine
        logger.info("Registered caption engine: '%s' (%s)", eng_id, engine.get_display_name())

        if set_active or self._active_id is None:
            self._active_id = eng_id

    def unregister(self, engine_id: str) -> None:
        """Unregister and shutdown an engine."""
        if engine_id in self._engines:
            eng = self._engines.pop(engine_id)
            eng.shutdown()
            if self._active_id == engine_id:
                self._active_id = next(iter(self._engines.keys())) if self._engines else None

    def get_engine(self, engine_id: str) -> Optional[BaseCaptionEngine]:
        """Retrieve an engine by its identifier."""
        return self._engines.get(engine_id)

    def get_active(self) -> Optional[BaseCaptionEngine]:
        """Get the currently active caption engine."""
        if self._active_id and self._active_id in self._engines:
            return self._engines[self._active_id]
        return None

    def set_active(self, engine_id: str) -> bool:
        """Switch the active engine."""
        if engine_id not in self._engines:
            logger.warning("Cannot set active engine to unknown id: '%s'", engine_id)
            return False

        current = self.get_active()
        if current and current.get_id() != engine_id:
            # We don't necessarily shutdown the old one to avoid re-load cost,
            # but we initialize the new one
            pass

        target = self._engines[engine_id]
        if not target.is_initialized():
            ok = target.initialize()
            if not ok:
                logger.error("Failed to initialize target engine '%s'", engine_id)
                return False

        self._active_id = engine_id
        logger.info("Switched active engine to: '%s'", engine_id)
        return True

    def list_engines(self) -> List[Dict[str, any]]:
        """Return a summary of all registered engines."""
        results = []
        for eng_id, eng in self._engines.items():
            results.append(
                {
                    "id": eng_id,
                    "display_name": eng.get_display_name(),
                    "is_active": (eng_id == self._active_id),
                    "is_initialized": eng.is_initialized(),
                    "is_cloud": isinstance(eng, (GroqWhisperEngine, OpenAIWhisperEngine)),
                }
            )
        return results

    def shutdown_all(self) -> None:
        """Clean up all registered engines."""
        for eng in self._engines.values():
            try:
                eng.shutdown()
            except Exception as e:
                logger.error("Error shutting down engine '%s': %s", eng.get_id(), e)
        self._engines.clear()
        self._active_id = None


def create_default_registry(
    local_model_path: str = DEFAULT_LOCAL_MODEL,
    groq_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
) -> ModelRegistry:
    """
    Factory creating a standard registry with offline Faster-Whisper
    and cloud API engines pre-registered.
    """
    registry = ModelRegistry()

    # 1. Offline Faster-Whisper Base (Default)
    faster_eng = FasterWhisperEngine(model_path_or_name=local_model_path)
    registry.register(faster_eng, set_active=True)

    # 2. Cloud Groq Whisper
    groq_eng = GroqWhisperEngine(api_key=groq_api_key)
    registry.register(groq_eng, set_active=False)

    # 3. Cloud OpenAI Whisper
    openai_eng = OpenAIWhisperEngine(api_key=openai_api_key)
    registry.register(openai_eng, set_active=False)

    return registry
