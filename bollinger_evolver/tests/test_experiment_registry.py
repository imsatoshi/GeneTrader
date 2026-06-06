"""Tests for local JSONL experiment registry."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.experiment_registry import (
    ExperimentRecord,
    append_experiment_record,
    read_experiment_records,
    validate_registry_output_dir,
)


def _record(**overrides):
    data = {
        "run_id": "run-001",
        "source": "mock-ga-cli",
        "seed": 42,
        "generations": 5,
        "population_size": 30,
        "best_fitness": 0.123,
        "artifact_dir": "artifacts/run-001",
        "notes": "local smoke",
        "created_at": "2026-06-06T00:00:00+00:00",
    }
    data.update(overrides)
    return data


class TestExperimentRegistry(unittest.TestCase):
    def test_registry_appends_experiment_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = append_experiment_record(tmp, _record())
            content = path.read_text(encoding="utf-8").strip()

        self.assertIn("run-001", content)
        self.assertEqual(path.name, "experiments.jsonl")

    def test_registry_rejects_disallowed_output_root(self) -> None:
        root = Path(__file__).resolve().parents[2]

        with self.assertRaises(ValueError):
            validate_registry_output_dir(root / ".runtime" / "registry")
        with self.assertRaises(ValueError):
            validate_registry_output_dir(root / "user_data" / "data" / "registry")

    def test_registry_record_is_json_serializable(self) -> None:
        record = ExperimentRecord(
            run_id="run-002",
            source="mock-ga-cli",
            seed=7,
            generations=3,
            population_size=12,
            best_fitness=0.456,
            artifact_dir="artifacts/run-002",
            notes="serializable",
            created_at="2026-06-06T00:00:00+00:00",
        )

        encoded = json.dumps(record.to_dict(), sort_keys=True)
        self.assertIn("run-002", encoded)

    def test_registry_can_read_records_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            append_experiment_record(tmp, _record(run_id="run-a"))
            append_experiment_record(tmp, _record(run_id="run-b"))

            records = read_experiment_records(tmp)

        self.assertEqual([item["run_id"] for item in records], ["run-a", "run-b"])


if __name__ == "__main__":
    unittest.main()
