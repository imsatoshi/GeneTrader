"""Tests for fixture-only Freqtrade-like backtest report normalization."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from dataclasses import asdict
from pathlib import Path

from bollinger_evolver.artifact_export import write_all_generation_artifacts
from bollinger_evolver.backtest_adapter import AdapterBackedMockEvaluator, NormalizedBacktestResult
from bollinger_evolver.freqtrade_backtest_normalizer import (
    FreqtradeFixtureBacktestAdapter,
    calculate_max_consecutive_losses_from_trades,
    load_freqtrade_backtest_report_json,
    load_freqtrade_backtest_report_from_zip_fixture,
    normalize_freqtrade_backtest_report,
)
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.session_summary import build_ga_session_summary


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "freqtrade_backtest_report.sample.json"


def _write_zip_fixture(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member_name, content in members.items():
            archive.writestr(member_name, content)


class TestFreqtradeBacktestNormalizer(unittest.TestCase):
    def test_load_json_fixture(self) -> None:
        report = load_freqtrade_backtest_report_json(FIXTURE_PATH)

        self.assertIsInstance(report, dict)
        self.assertIn("strategy", report)

    def test_load_json_fixture_rejects_non_object_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "not-object.json"
            path.write_text("[1, 2, 3]", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_freqtrade_backtest_report_json(path)

    def test_load_zip_fixture_reads_backtest_json(self) -> None:
        report_text = FIXTURE_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "freqtrade-result.zip"
            _write_zip_fixture(
                path,
                {
                    "metadata.json": json.dumps({"note": "not a backtest report"}),
                    "nested/backtest-result.json": report_text,
                },
            )

            report = load_freqtrade_backtest_report_from_zip_fixture(path)

        self.assertIn("strategy", report)
        self.assertEqual(normalize_freqtrade_backtest_report(report).total_trades, 42)

    def test_load_zip_fixture_rejects_archive_without_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "freqtrade-result.zip"
            _write_zip_fixture(path, {"notes.txt": "fixture notes"})

            with self.assertRaises(ValueError):
                load_freqtrade_backtest_report_from_zip_fixture(path)

    def test_load_zip_fixture_rejects_json_without_report_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "freqtrade-result.zip"
            _write_zip_fixture(path, {"metadata.json": json.dumps({"hello": "world"})})

            with self.assertRaises(ValueError):
                load_freqtrade_backtest_report_from_zip_fixture(path)

    def test_normalize_aggregate_report(self) -> None:
        report = load_freqtrade_backtest_report_json(FIXTURE_PATH)

        result = normalize_freqtrade_backtest_report(report)

        self.assertIsInstance(result, NormalizedBacktestResult)
        self.assertEqual(result.profit, 0.1285)
        self.assertEqual(result.sharpe, 1.31)
        self.assertAlmostEqual(result.win_rate, 24 / 42)
        self.assertEqual(result.max_drawdown, 0.074)
        self.assertEqual(result.total_trades, 42)
        self.assertEqual(result.max_consecutive_losses, 2)
        self.assertEqual(result.leverage, 1.0)
        self.assertEqual(result.risk_per_trade, 0.01)
        self.assertEqual(result.metadata["source"], "freqtrade_fixture")

    def test_max_consecutive_losses_from_trades(self) -> None:
        self.assertEqual(
            calculate_max_consecutive_losses_from_trades(
                [
                    {"profit_ratio": 0.01},
                    {"profit_ratio": -0.02},
                    {"profit_ratio": -0.01},
                    {"profit_ratio": 0.03},
                    {"profit_ratio": -0.01},
                    {"profit_ratio": -0.02},
                    {"profit_ratio": -0.03},
                ]
            ),
            3,
        )
        self.assertEqual(calculate_max_consecutive_losses_from_trades([]), 0)
        self.assertEqual(calculate_max_consecutive_losses_from_trades([{"profit_ratio": 0.1}]), 0)
        self.assertEqual(
            calculate_max_consecutive_losses_from_trades(
                [{"profit_ratio": -0.1}, {"profit_ratio": -0.2}, {"profit_ratio": -0.3}]
            ),
            3,
        )

    def test_max_consecutive_losses_rejects_missing_or_non_numeric_profit_ratio(self) -> None:
        with self.assertRaises(ValueError):
            calculate_max_consecutive_losses_from_trades([{}])
        with self.assertRaises(ValueError):
            calculate_max_consecutive_losses_from_trades([{"profit_ratio": "loss"}])

    def test_normalized_output_is_json_safe(self) -> None:
        result = normalize_freqtrade_backtest_report(load_freqtrade_backtest_report_json(FIXTURE_PATH))

        encoded = json.dumps(asdict(result), sort_keys=True)

        self.assertIn("NormalizedBacktestResult", str(type(result)))
        self.assertIn("freqtrade_fixture", encoded)

    def test_strategy_selection_supports_multiple_strategies(self) -> None:
        report = load_freqtrade_backtest_report_json(FIXTURE_PATH)
        other_strategy = {
            **report["strategy"]["BollingerBandStrategy"],
            "profit_total": 0.5,
            "max_consecutive_losses": 1,
        }
        multi_report = {
            **report,
            "strategy": {
                **report["strategy"],
                "OtherStrategy": other_strategy,
            },
        }

        selected = normalize_freqtrade_backtest_report(multi_report, strategy_name="OtherStrategy")

        self.assertEqual(selected.profit, 0.5)
        with self.assertRaises(ValueError):
            normalize_freqtrade_backtest_report(multi_report)
        with self.assertRaises(ValueError):
            normalize_freqtrade_backtest_report(multi_report, strategy_name="MissingStrategy")

    def test_fixture_adapter_is_deterministic(self) -> None:
        report = load_freqtrade_backtest_report_json(FIXTURE_PATH)
        adapter = FreqtradeFixtureBacktestAdapter(report, default_leverage=2.0, default_risk_per_trade=0.02)
        genome = {"genome_id": "fixture-genome", "bb_period": 20}

        first = adapter.run_backtest(genome)
        second = adapter.run_backtest(genome)

        self.assertEqual(first, second)
        self.assertEqual(first.leverage, 2.0)
        self.assertEqual(first.risk_per_trade, 0.02)
        self.assertTrue(first.metadata["genome_received"])

    def test_zip_fixture_adapter_is_deterministic(self) -> None:
        report_text = FIXTURE_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "freqtrade-result.zip"
            _write_zip_fixture(path, {"backtest-result.json": report_text})
            adapter = FreqtradeFixtureBacktestAdapter(path, default_leverage=2.0, default_risk_per_trade=0.02)

            first = adapter.run_backtest({"genome_id": "zip-genome"})
            second = adapter.run_backtest({"genome_id": "zip-genome"})

        self.assertEqual(first, second)
        self.assertEqual(first.total_trades, 42)
        self.assertEqual(first.max_consecutive_losses, 2)
        self.assertNotIn("path", first.metadata)

    def test_fixture_adapter_with_adapter_backed_evaluator_e2e(self) -> None:
        report = load_freqtrade_backtest_report_json(FIXTURE_PATH)
        evaluator = AdapterBackedMockEvaluator(FreqtradeFixtureBacktestAdapter(report))

        result = run_ga_execution(GAExecutionConfig(population_size=4, generations=2, seed=82), evaluator=evaluator)
        summary = build_ga_session_summary(result, top_n=3, run_id="freqtrade-fixture-smoke")
        scores = [entry["fitness"] for entry in summary["leaderboard"]]

        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([entry["generation"] for entry in summary["fitness_series"]], [1, 2])
        self.assertIn("fitness_components", summary["leaderboard"][0])
        self.assertEqual(summary["leaderboard"][0]["total_trades"], 42)
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_all_generation_artifacts(result, tmp, top_n=3, run_id="freqtrade-fixture-smoke")
            loaded = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]

        self.assertEqual([item["generation"] for item in loaded], [1, 2])
        self.assertIn("fitness_components", loaded[-1]["genomes"][0])
        self.assertEqual(loaded[-1]["genomes"][0]["total_trades"], 42)

    def test_zip_fixture_adapter_with_adapter_backed_evaluator_e2e(self) -> None:
        report_text = FIXTURE_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "freqtrade-result.zip"
            _write_zip_fixture(zip_path, {"backtest-result.json": report_text})
            evaluator = AdapterBackedMockEvaluator(FreqtradeFixtureBacktestAdapter(zip_path))

            result = run_ga_execution(GAExecutionConfig(population_size=4, generations=2, seed=83), evaluator=evaluator)
            summary = build_ga_session_summary(result, top_n=3, run_id="freqtrade-zip-fixture-smoke")
            paths = write_all_generation_artifacts(result, Path(tmp) / "artifacts", top_n=3, run_id="zip-smoke")
            loaded = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]

        self.assertEqual([entry["generation"] for entry in summary["fitness_series"]], [1, 2])
        self.assertEqual(summary["leaderboard"][0]["total_trades"], 42)
        self.assertEqual(loaded[-1]["genomes"][0]["max_consecutive_losses"], 2)


if __name__ == "__main__":
    unittest.main()
