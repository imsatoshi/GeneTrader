"""End-to-end mock pipeline tests for Bollinger Evolver GA."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from bollinger_evolver.ga import GAOrchestratorConfig, MockStrategyEvaluator, run_ga
from bollinger_evolver.ga.evaluation_pipeline import (
    build_deterministic_mock_metrics,
    evaluate_individual_with_mock_pipeline,
)
from bollinger_evolver.evaluators import FitnessConfig
from bollinger_evolver.gene_space import load_gene_space, validate_genes
from bollinger_evolver.strategy_factory import GENERATED_ROOT
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


def _valid_genes(**overrides: object) -> dict:
    genes = dict(DEFAULT_GENES)
    genes.update(overrides)
    return genes


def _fitness_config() -> FitnessConfig:
    return FitnessConfig(
        strategy="BollingerResonance_Gen001_Ind001",
        config_path="config.json",
        timerange="20240101-20240201",
        timeframe="15m",
        pairs=("BTC/USDT",),
        result_dir="results/bollinger_evolver/backtests",
        timeout_seconds=120,
        failed_score=-1_000_000.0,
    )


def _orchestrator_config(temp_dir: str, **overrides: object) -> GAOrchestratorConfig:
    base = {
        "generations": 2,
        "population_size": 3,
        "run_id": "run-pipeline-test",
        "seed": 7,
        "run_output_dir": Path(temp_dir) / "runs",
        "generation_output_dir": Path(temp_dir) / "generations",
        "best_output_dir": Path(temp_dir) / "best",
        "elite_count": 1,
        "mutation_rate": 0.2,
        "crossover_rate": 0.8,
        "persist_run_summary": True,
        "persist_final_best": True,
        "mode": "mock",
    }
    base.update(overrides)
    return GAOrchestratorConfig(**base)


def _good_manifest() -> dict:
    return {
        "status": "ready",
        "pairs": ["BTC/USDT"],
        "timeframes": ["15m"],
        "expected_file_count": 1,
        "missing_count": 0,
        "limited_count": 0,
        "invalid_ohlc_count": 0,
        "gap_count": 0,
        "entries": [
            {
                "pair": "BTC/USDT",
                "timeframe": "15m",
                "status": "ready",
                "row_count": 500,
                "gap_count": 0,
                "invalid_ohlc_count": 0,
            }
        ],
    }


class TestMockEvaluationPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy_output_dir = GENERATED_ROOT / f"test_pipeline_{uuid.uuid4().hex}"

    def tearDown(self) -> None:
        if self.strategy_output_dir.exists():
            shutil.rmtree(self.strategy_output_dir)

    def test_mock_evaluator_generates_strategy_file_and_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluator = MockStrategyEvaluator(
                seed=123,
                output_root=temp_dir,
                strategy_output_dir=self.strategy_output_dir,
                data_coverage_manifest=_good_manifest(),
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
            )
            result = evaluator.evaluate(
                _valid_genes(),
                generation=1,
                output_root=temp_dir,
                strategy_output_dir=str(self.strategy_output_dir),
                individual_index=2,
            )

            self.assertTrue(result["success"])
            self.assertTrue(Path(result["strategy_path"]).exists())
            self.assertIn("BollingerResonance_Gen001_Ind002", result["strategy_name"])
            self.assertIsInstance(result["genes_hash"], str)
            self.assertIsInstance(result["fitness"], float)
            self.assertTrue(result["metrics"]["mock"])

    def test_generated_strategy_file_compiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = evaluate_individual_with_mock_pipeline(
                _valid_genes(),
                generation=1,
                output_root=temp_dir,
                strategy_output_dir=str(self.strategy_output_dir),
            )
            source = Path(result["strategy_path"]).read_text(encoding="utf-8")

        compile(source, result["strategy_path"], "exec")

    def test_same_genes_and_seed_are_deterministic(self) -> None:
        genes = _valid_genes()
        first = build_deterministic_mock_metrics(genes, seed=11)
        second = build_deterministic_mock_metrics(genes, seed=11)
        self.assertEqual(first, second)

    def test_different_genes_can_produce_different_metrics(self) -> None:
        first = build_deterministic_mock_metrics(_valid_genes(bb_period_15m=20), seed=11)
        second = build_deterministic_mock_metrics(_valid_genes(bb_period_15m=55), seed=11)
        self.assertNotEqual(first, second)

    def test_invalid_genes_return_failure_and_no_champion_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = _valid_genes()
            invalid["bb_period_15m"] = 999
            result = evaluate_individual_with_mock_pipeline(
                invalid,
                generation=1,
                output_root=temp_dir,
                strategy_output_dir=str(self.strategy_output_dir),
            )

        self.assertFalse(result["success"])
        self.assertIsNone(result["fitness"])
        self.assertTrue(result["metrics"]["dataQualityGate"]["allowed_for_evaluation"])
        self.assertIsNotNone(result["error"])

    def test_mock_evaluator_blocks_failed_data_quality_gate(self) -> None:
        manifest = _good_manifest()
        manifest["entries"][0]["invalid_ohlc_count"] = 1
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluator = MockStrategyEvaluator(
                seed=123,
                output_root=temp_dir,
                strategy_output_dir=self.strategy_output_dir,
                data_coverage_manifest=manifest,
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
            )
            result = evaluator.evaluate(
                _valid_genes(),
                generation=1,
                output_root=temp_dir,
                strategy_output_dir=str(self.strategy_output_dir),
                individual_index=2,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "data_quality_gate_failed")
        self.assertFalse(result["metrics"]["dataQualityGate"]["allowed_for_evaluation"])
        self.assertNotIn("strategy_path", result)

    def test_orchestrator_runs_two_generations_with_mock_evaluator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluator = MockStrategyEvaluator(
                seed=22,
                output_root=temp_dir,
                strategy_output_dir=self.strategy_output_dir,
                data_coverage_manifest=_good_manifest(),
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
            )
            result = run_ga(
                [
                    _valid_genes(bb_period_15m=20),
                    _valid_genes(bb_period_15m=35),
                    _valid_genes(bb_period_15m=50),
                ],
                _fitness_config(),
                _orchestrator_config(temp_dir),
                evaluator=evaluator,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.completed, 2)
            self.assertIsNotNone(result.best_candidate)
            self.assertTrue(Path(result.run_summary_path).exists())
            self.assertTrue(Path(result.final_best_path).exists())

    def test_run_summary_and_final_best_include_mock_pipeline_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluator = MockStrategyEvaluator(
                seed=33,
                output_root=temp_dir,
                strategy_output_dir=self.strategy_output_dir,
                data_coverage_manifest=_good_manifest(),
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
            )
            result = run_ga(
                [
                    _valid_genes(bb_period_15m=20),
                    _valid_genes(bb_period_15m=35),
                    _valid_genes(bb_period_15m=50),
                ],
                _fitness_config(),
                _orchestrator_config(temp_dir),
                evaluator=evaluator,
            )
            run_summary = json.loads(Path(result.run_summary_path).read_text(encoding="utf-8"))
            final_best = json.loads(Path(result.final_best_path).read_text(encoding="utf-8"))

        self.assertTrue(run_summary["mock_evaluation"])
        self.assertIn("final_best", run_summary)
        self.assertTrue(final_best["mock_evaluation"])
        self.assertIn("genes", final_best)
        self.assertIn("genes_hash", final_best)
        self.assertIn("strategy_path", final_best)
        self.assertIn("dataQualityGate", final_best["metrics"])
        validate_genes(final_best["genes"], load_gene_space())

    def test_failed_individual_does_not_become_champion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluator = MockStrategyEvaluator(
                seed=44,
                output_root=temp_dir,
                strategy_output_dir=self.strategy_output_dir,
                data_coverage_manifest=_good_manifest(),
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
            )
            invalid = _valid_genes(bb_period_15m=20)
            invalid["bb_period_15m"] = 999
            result = run_ga(
                [
                    invalid,
                    _valid_genes(bb_period_15m=35),
                    _valid_genes(bb_period_15m=50),
                ],
                _fitness_config(),
                _orchestrator_config(temp_dir, generations=1),
                evaluator=evaluator,
            )

        self.assertTrue(result.success)
        self.assertNotEqual(result.best_candidate.get("bb_period_15m"), 999)

    def test_sensitive_fields_do_not_enter_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            evaluator = MockStrategyEvaluator(
                seed=55,
                output_root=temp_dir,
                strategy_output_dir=self.strategy_output_dir,
                data_coverage_manifest=_good_manifest(),
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
            )
            result = run_ga(
                [
                    dict(
                        _valid_genes(bb_period_15m=20),
                        api_key="secret-api-key-value",
                        token="secret-token-value",
                    ),
                    _valid_genes(bb_period_15m=35),
                    _valid_genes(bb_period_15m=50),
                ],
                _fitness_config(),
                _orchestrator_config(temp_dir),
                evaluator=evaluator,
            )
            run_summary_text = Path(result.run_summary_path).read_text(encoding="utf-8")
            final_best_text = Path(result.final_best_path).read_text(encoding="utf-8")

        self.assertNotIn("secret-api-key-value", run_summary_text)
        self.assertNotIn("secret-token-value", run_summary_text)
        self.assertNotIn("secret-api-key-value", final_best_text)
        self.assertNotIn("secret-token-value", final_best_text)

    def test_deterministic_seed_reproduces_final_best(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first_strategy_dir = GENERATED_ROOT / f"test_pipeline_{uuid.uuid4().hex}"
            second_strategy_dir = GENERATED_ROOT / f"test_pipeline_{uuid.uuid4().hex}"
            try:
                first = run_ga(
                    [
                        _valid_genes(bb_period_15m=20),
                        _valid_genes(bb_period_15m=35),
                        _valid_genes(bb_period_15m=50),
                    ],
                    _fitness_config(),
                    _orchestrator_config(first_dir, run_id="run-det-1"),
                    evaluator=MockStrategyEvaluator(
                        seed=66,
                        output_root=first_dir,
                        strategy_output_dir=first_strategy_dir,
                        data_coverage_manifest=_good_manifest(),
                        required_pairs=["BTC/USDT"],
                        required_timeframes=["15m"],
                    ),
                )
                second = run_ga(
                    [
                        _valid_genes(bb_period_15m=20),
                        _valid_genes(bb_period_15m=35),
                        _valid_genes(bb_period_15m=50),
                    ],
                    _fitness_config(),
                    _orchestrator_config(second_dir, run_id="run-det-2"),
                    evaluator=MockStrategyEvaluator(
                        seed=66,
                        output_root=second_dir,
                        strategy_output_dir=second_strategy_dir,
                        data_coverage_manifest=_good_manifest(),
                        required_pairs=["BTC/USDT"],
                        required_timeframes=["15m"],
                    ),
                )
            finally:
                if first_strategy_dir.exists():
                    shutil.rmtree(first_strategy_dir)
                if second_strategy_dir.exists():
                    shutil.rmtree(second_strategy_dir)

        self.assertEqual(first.best_fitness_score, second.best_fitness_score)
        self.assertEqual(first.best_candidate["genes_hash"], second.best_candidate["genes_hash"])


if __name__ == "__main__":
    unittest.main()
