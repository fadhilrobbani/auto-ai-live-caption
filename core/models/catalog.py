"""
Catalog of offline speech-to-text models for Auto AI Live Caption.
Provides metadata, download targets, and availability checks for local Whisper models.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_MODELS_DIR = Path.home() / ".local" / "share" / "models" / "whisper"


@dataclass
class CatalogModel:
    id: str
    name: str
    size_mb: int
    faster_whisper_id: str
    description: str
    speed_rating: str
    is_multilingual: bool
    dir_name: str


OFFLINE_MODEL_CATALOG: List[CatalogModel] = [
    CatalogModel(
        id="tiny.en",
        name="Tiny English",
        size_mb=75,
        faster_whisper_id="tiny.en",
        description="Lightest and fastest English model. Recommended for low-spec laptops.",
        speed_rating="Ultra Fast (<100ms)",
        is_multilingual=False,
        dir_name="faster-whisper-tiny.en",
    ),
    CatalogModel(
        id="tiny",
        name="Tiny (Multilingual)",
        size_mb=75,
        faster_whisper_id="tiny",
        description="Lightest multilingual model (supports Indonesian, English, Japanese, and 90+ languages).",
        speed_rating="Ultra Fast (<120ms)",
        is_multilingual=True,
        dir_name="faster-whisper-tiny",
    ),
    CatalogModel(
        id="base",
        name="Base (Multilingual)",
        size_mb=142,
        faster_whisper_id="base",
        description="Balanced model for multilingual live captioning with solid accuracy.",
        speed_rating="Balanced (~300ms)",
        is_multilingual=True,
        dir_name="faster-whisper-base",
    ),
    CatalogModel(
        id="base.en",
        name="Base English",
        size_mb=142,
        faster_whisper_id="base.en",
        description="English-optimized base model with high vocabulary fidelity.",
        speed_rating="Balanced (~250ms)",
        is_multilingual=False,
        dir_name="faster-whisper-base.en",
    ),
    CatalogModel(
        id="distil-small.en",
        name="Distil-Small English",
        size_mb=330,
        faster_whisper_id="distil-small.en",
        description="Distilled English model delivering small-tier accuracy at fast speed.",
        speed_rating="Fast Distilled (~180ms)",
        is_multilingual=False,
        dir_name="faster-whisper-distil-small.en",
    ),
    CatalogModel(
        id="small",
        name="Small (Multilingual)",
        size_mb=466,
        faster_whisper_id="small",
        description="High accuracy multilingual model for complex vocabulary and accents.",
        speed_rating="High Accuracy (~550ms)",
        is_multilingual=True,
        dir_name="faster-whisper-small",
    ),
]

_CATALOG_BY_ID: Dict[str, CatalogModel] = {m.id: m for m in OFFLINE_MODEL_CATALOG}


def get_catalog_models() -> List[CatalogModel]:
    """Return all available models in the catalog."""
    return list(OFFLINE_MODEL_CATALOG)


def get_catalog_model_by_id(model_id: str) -> Optional[CatalogModel]:
    """Lookup a catalog model by its ID or directory name."""
    if model_id in _CATALOG_BY_ID:
        return _CATALOG_BY_ID[model_id]
    # Check directory name match
    for m in OFFLINE_MODEL_CATALOG:
        if m.dir_name == model_id or m.dir_name.endswith(model_id):
            return m
    return None


def get_model_local_dir(model: CatalogModel, base_dir: Optional[Path] = None) -> Path:
    """Return the absolute local storage directory path for a catalog model."""
    root = base_dir or DEFAULT_MODELS_DIR
    return root / model.dir_name


def is_model_downloaded(model: CatalogModel, base_dir: Optional[Path] = None) -> bool:
    """Check if a catalog model is already downloaded and valid on disk."""
    model_dir = get_model_local_dir(model, base_dir)
    if not model_dir.is_dir():
        return False
    config_file = model_dir / "config.json"
    model_bin = model_dir / "model.bin"
    return config_file.is_file() and model_bin.is_file() and model_bin.stat().st_size > 1000
