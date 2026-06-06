"""Tests for custom experiment registry helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.experiment_registry_custom import (
    append_custom_experiment_record,
    custom_experiment_record_from_ga_result,
    read_custom_experiment_records,
)
from bollinger_evolver.ga_execution_custom import CustomGAExecutionConfig, run_custom_ga_execution


class TestCustomExperimentRegistry(unittest.TestCase):
    def test_custom_registry_builds_json_safe_record(self) -> None:
        result = run_custom_ga_execution(CustomGAExecutionConfig(population_size=4, generations=1, seed=13))
        record = custom_experiment_record_from_ga_result(result, artifact_dir="artifacts/custom-13")

        encoded = json.dumps(record.to_dict(), sort_keys=True)
        self.assertIn("custom-strategy-mock-ga", encoded)
        self.assertEqual(record.run_id, "custom-ga-seed-13")

    def test_custom_registry_appends_and_reads_record(self) -> None:
        result = run_custom_ga_execution(CustomGAExecutionConfig(population_size=4, generations=1, seed=14))
        with tempfile.TemporaryDirectory() as tmp:
            registry_path = append_custom_experiment_record(
                tmp,
                result,
                artifact_dir="artifacts/custom-14",
                notes="custom registry smoke",
            )
            records = read_custom_experiment_records(tmp)

        self.assertEqual(registry_path.name, "experiments.jsonl")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["notes"], "custom registry smoke")

    def test_custom_registry_rejects_disallowed_output_root(self) -> None:
        result = run_custom_ga_execution(CustomGAExecutionConfig(population_size=4, generations=1, seed=15))
        repo_root = Path(__file__).resolve().parents[2]

        with self.assertRaises(ValueError):
            append_custom_experiment_record(
                repo_root / ".runtime" / "custom-registry",
                result,
                artifact_dir="artifacts/custom-15",
            )


if __name__ == "__main__":
    unittest.main()
