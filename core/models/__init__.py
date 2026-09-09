"""
Pluggable Model Provider Layer for Auto AI Live Caption.
"""

from core.models.base import BaseCaptionEngine, CaptionResult
from core.models.registry import ModelRegistry

__all__ = ["BaseCaptionEngine", "CaptionResult", "ModelRegistry"]
