"""Tests for loading offline data requirements from JSON files."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.data_gate import load_offline_data_requirements
from bollinger_evolver.preflight import run_offline_data_preflight


class TestOfflineDataRequirementsFile(unittest.TestCase):
    def _write_json(self, root: Path, name: str, payload: object) -> Path:
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_load_requirements_json_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = self._write_json(
                root,
                "requirements.json",
                {"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]},
            )

            result = load_offline_data_requirements(path)

        self.assertEqual(result, {"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]})

    def test_load_requirements_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.json"

            with self.assertRaises(FileNotFoundError):
                load_offline_data_requirements(missing_path)

    def test_load_requirements_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "requirements.json"
            path.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "requirements_json_invalid"):
                load_offline_data_requirements(path)

    def test_load_requirements_rejects_non_object_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._write_json(Path(temp_dir), "requirements.json", ["BTC/USDT"])

            with self.assertRaisesRegex(ValueError, "requirements_json_must_be_object"):
                load_offline_data_requirements(path)

    def test_preflight_accepts_requirements_file_equivalent_to_dict(self) -> None:
        requirements = {"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]}
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_root = root / "data"
            data_root.mkdir()
            (data_root / "BTC_USDT-1h.json").write_bytes(b"x")
            requirements_path = self._write_json(root, "requirements.json", requirements)

            from_dict = run_offline_data_preflight(data_root, requirements=requirements)
            from_file = run_offline_data_preflight(data_root, requirements_path=requirements_path)

        self.assertEqual(from_file["requirements"], from_dict["requirements"])
        self.assertEqual(from_file["ok"], from_dict["ok"])
        self.assertEqual(from_file["errors"], from_dict["errors"])
        self.assertEqual(from_file["gate"]["requirements"], from_dict["gate"]["requirements"])
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "4h"},
            from_file["errors"],
        )


if __name__ == "__main__":
    unittest.main()
