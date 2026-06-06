"""Tests for GA artifact export helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.artifact_export import (
    build_generation_artifact,
    write_all_generation_artifacts,
    write_generation_artifact,
)
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution


def _execution_result():
    return run_ga_execution(GAExecutionConfig(population_size=6, generations=3, seed=77))


class TestArtifactExport(unittest.TestCase):
    def test_build_generation_artifact_is_json_serializable(self) -> None:
        artifact = build_generation_artifact(_execution_result(), run_id="mock-run-077")

        encoded = json.dumps(artifact, sort_keys=True)

        self.assertIn("ga-generation-artifact/v1", encoded)
        self.assertEqual(artifact["run_id"], "mock-run-077")

    def test_artifact_contains_session_summary(self) -> None:
        artifact = build_generation_artifact(_execution_result())

        self.assertEqual(artifact["session_summary"]["schema_version"], "ga-session-summary/v1")
        self.assertEqual(artifact["source"], "mock-ga-execution")

    def test_generation_leaderboard_is_sorted(self) -> None:
        artifact = build_generation_artifact(_execution_result(), generation=2)
        scores = [item["fitness"] for item in artifact["genomes"]]

        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_best_genome_matches_top_entry(self) -> None:
        artifact = build_generation_artifact(_execution_result(), generation=1)

        self.assertEqual(artifact["best_genome"], artifact["genomes"][0]["genome"])
        self.assertEqual(artifact["best_fitness"], artifact["genomes"][0]["fitness"])

    def test_write_generation_artifact_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = write_generation_artifact(_execution_result(), temp_dir, generation=2)
            payload = json.loads(Path(path).read_text(encoding="utf-8"))

        self.assertEqual(path.name, "generation-002.json")
        self.assertEqual(payload["generation"], 2)

    def test_write_all_generation_artifacts_writes_each_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_all_generation_artifacts(_execution_result(), temp_dir)

            self.assertEqual(len(paths), 3)
            self.assertEqual([path.name for path in paths], [
                "generation-001.json",
                "generation-002.json",
                "generation-003.json",
            ])

    def test_top_n_limits_exported_genomes(self) -> None:
        artifact = build_generation_artifact(_execution_result(), top_n=2)

        self.assertEqual(len(artifact["genomes"]), 2)


if __name__ == "__main__":
    unittest.main()
