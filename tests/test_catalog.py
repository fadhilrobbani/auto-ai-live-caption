"""
Unit tests for core.models.catalog.
"""

import tempfile
import unittest
from pathlib import Path

from core.models.catalog import (
    OFFLINE_MODEL_CATALOG,
    get_catalog_models,
    get_catalog_model_by_id,
    get_model_local_dir,
    is_model_downloaded,
)


class TestModelCatalog(unittest.TestCase):
    def test_catalog_entries(self):
        models = get_catalog_models()
        self.assertGreaterEqual(len(models), 5)

        ids = [m.id for m in models]
        self.assertIn("tiny.en", ids)
        self.assertIn("tiny", ids)
        self.assertIn("base", ids)

    def test_get_by_id(self):
        m = get_catalog_model_by_id("tiny.en")
        self.assertIsNotNone(m)
        self.assertEqual(m.size_mb, 75)
        self.assertFalse(m.is_multilingual)

        m_base = get_catalog_model_by_id("base")
        self.assertIsNotNone(m_base)
        self.assertTrue(m_base.is_multilingual)

    def test_is_model_downloaded_with_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model = get_catalog_model_by_id("tiny.en")

            # Initially not downloaded in temp directory
            self.assertFalse(is_model_downloaded(model, base_dir=tmp_path))

            # Create mock model directory with valid config.json and model.bin
            model_dir = tmp_path / model.dir_name
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}")
            (model_dir / "model.bin").write_bytes(b"0" * 2000)

            self.assertTrue(is_model_downloaded(model, base_dir=tmp_path))


if __name__ == "__main__":
    unittest.main()
