"""Tests for explicit offline data manifest save/load helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.data_manifest import (
    load_offline_data_manifest,
    save_offline_data_manifest,
)


class TestOfflineDataManifestPersistence(unittest.TestCase):
    def test_save_and_load_offline_data_manifest_round_trips_json(self) -> None:
        manifest = {
            "source": "offline_inventory",
            "root": "/tmp/data",
            "datasets": [
                {
                    "path": "BTC_USDT-1h.json",
                    "format": "json",
                    "size_bytes": 1,
                    "pair": "BTC/USDT",
                    "timeframe": "1h",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "manifest.json"
            written_path = save_offline_data_manifest(manifest, output_path)
            loaded = load_offline_data_manifest(output_path)

        self.assertEqual(written_path, str(output_path))
        self.assertEqual(loaded, manifest)

    def test_save_rejects_non_mapping_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "manifest_must_be_object"):
                save_offline_data_manifest(["not", "a", "mapping"], Path(temp_dir) / "manifest.json")

    def test_load_rejects_missing_manifest_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(FileNotFoundError):
                load_offline_data_manifest(Path(temp_dir) / "missing.json")

    def test_load_rejects_invalid_manifest_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "manifest_json_invalid"):
                load_offline_data_manifest(path)

    def test_load_rejects_non_object_manifest_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manifest.json"
            path.write_text(json.dumps(["not", "object"]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "manifest_json_must_be_object"):
                load_offline_data_manifest(path)


if __name__ == "__main__":
    unittest.main()
