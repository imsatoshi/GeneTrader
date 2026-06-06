"""Tests for external report import path safety and provenance manifest."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from dataclasses import asdict
from pathlib import Path

from bollinger_evolver.artifact_export import write_all_generation_artifacts
from bollinger_evolver.backtest_adapter import AdapterBackedMockEvaluator
from bollinger_evolver.freqtrade_backtest_normalizer import load_freqtrade_backtest_report_json
from bollinger_evolver.freqtrade_report_import_gate import (
    ReportImportManifest,
    ReportImportRequest,
    import_controlled_freqtrade_report,
    validate_report_import_path,
)
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.session_summary import build_ga_session_summary


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "freqtrade_backtest_report.sample.json"


def _write_zip_fixture(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for member_name, content in members.items():
            archive.writestr(member_name, content)


class ImportGateAdapter:
    def __init__(self, request: ReportImportRequest) -> None:
        self.request = request

    def run_backtest(self, genome):
        request = ReportImportRequest(
            report_path=self.request.report_path,
            strategy_name=self.request.strategy_name,
            allowed_roots=self.request.allowed_roots,
            default_leverage=self.request.default_leverage,
            default_risk_per_trade=self.request.default_risk_per_trade,
            genome={"genome_id": genome.get("genome_id", "unknown"), **dict(genome)},
        )
        return import_controlled_freqtrade_report(request)[0]


class TestFreqtradeReportImportGate(unittest.TestCase):
    def test_validates_allowed_json_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            report_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

            validated = validate_report_import_path(report_path, allowed_roots=(root,))

        self.assertEqual(validated.name, "report.json")

    def test_validates_allowed_zip_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.zip"
            _write_zip_fixture(report_path, {"backtest-result.json": FIXTURE_PATH.read_text(encoding="utf-8")})

            validated = validate_report_import_path(report_path, allowed_roots=(root,))

        self.assertEqual(validated.suffix, ".zip")

    def test_rejects_path_outside_allowed_roots(self) -> None:
        with tempfile.TemporaryDirectory() as allowed_tmp, tempfile.TemporaryDirectory() as outside_tmp:
            allowed_root = Path(allowed_tmp)
            report_path = Path(outside_tmp) / "report.json"
            report_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

            with self.assertRaises(ValueError):
                validate_report_import_path(report_path, allowed_roots=(allowed_root,))

    def test_rejects_directory_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaises(ValueError):
                validate_report_import_path(root, allowed_roots=(root,))

    def test_rejects_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaises(FileNotFoundError):
                validate_report_import_path(root / "missing.json", allowed_roots=(root,))

    def test_rejects_unsupported_suffix_and_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.txt"
            report_path.write_text("not a supported report", encoding="utf-8")

            with self.assertRaises(ValueError):
                validate_report_import_path(report_path, allowed_roots=(root,))
            with self.assertRaises(ValueError):
                validate_report_import_path(root / "*.json", allowed_roots=(root,))

    def test_import_manifest_is_json_safe_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            report_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

            result, manifest = import_controlled_freqtrade_report(
                ReportImportRequest(report_path=report_path, allowed_roots=(root,), genome={"genome_id": "gate"})
            )

        self.assertIsInstance(manifest, ReportImportManifest)
        encoded = json.dumps({"manifest": manifest.to_dict(), "result": asdict(result)}, sort_keys=True)
        self.assertIn("no_execution_import_only", encoded)
        self.assertIn("<redacted:report.json>", encoded)
        self.assertNotIn(str(report_path), encoded)
        self.assertEqual(manifest.file_extension, ".json")
        self.assertEqual(len(manifest.sha256), 64)
        self.assertFalse(manifest.safety_flags["freqtrade_executed"])

    def test_import_returns_normalized_result_with_safe_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.zip"
            _write_zip_fixture(report_path, {"backtest-result.json": FIXTURE_PATH.read_text(encoding="utf-8")})

            result, manifest = import_controlled_freqtrade_report(
                ReportImportRequest(
                    report_path=report_path,
                    allowed_roots=(root,),
                    default_leverage=2.0,
                    default_risk_per_trade=0.02,
                    genome={"genome_id": "zip-gate"},
                )
            )

        self.assertEqual(result.total_trades, 42)
        self.assertEqual(result.leverage, 2.0)
        self.assertEqual(result.risk_per_trade, 0.02)
        self.assertEqual(result.metadata["source"], "external_freqtrade_report_import")
        self.assertEqual(result.metadata["execution_mode"], "no_execution_import_only")
        self.assertEqual(result.metadata["report_manifest"], manifest.to_dict())

    def test_multi_strategy_selection_and_missing_strategy_errors(self) -> None:
        report = load_freqtrade_backtest_report_json(FIXTURE_PATH)
        other_strategy = {
            **report["strategy"]["BollingerBandStrategy"],
            "profit_total": 0.25,
            "max_consecutive_losses": 1,
        }
        multi_report = {
            **report,
            "strategy": {
                **report["strategy"],
                "OtherStrategy": other_strategy,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "multi.json"
            report_path.write_text(json.dumps(multi_report), encoding="utf-8")

            selected, _ = import_controlled_freqtrade_report(
                ReportImportRequest(report_path=report_path, allowed_roots=(root,), strategy_name="OtherStrategy")
            )

            with self.assertRaises(ValueError):
                import_controlled_freqtrade_report(ReportImportRequest(report_path=report_path, allowed_roots=(root,)))
            with self.assertRaises(ValueError):
                import_controlled_freqtrade_report(
                    ReportImportRequest(report_path=report_path, allowed_roots=(root,), strategy_name="Missing")
                )

        self.assertEqual(selected.profit, 0.25)
        self.assertEqual(selected.metadata["strategy_name"], "OtherStrategy")

    def test_ga_smoke_preserves_report_import_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "report.json"
            report_path.write_text(FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            request = ReportImportRequest(report_path=report_path, allowed_roots=(root,))
            evaluator = AdapterBackedMockEvaluator(ImportGateAdapter(request))

            result = run_ga_execution(GAExecutionConfig(population_size=4, generations=2, seed=85), evaluator=evaluator)
            summary = build_ga_session_summary(result, top_n=3, run_id="import-gate-smoke")
            paths = write_all_generation_artifacts(result, root / "artifacts", top_n=3, run_id="import-gate-smoke")
            loaded = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]

        self.assertEqual([entry["generation"] for entry in summary["fitness_series"]], [1, 2])
        self.assertEqual(summary["leaderboard"][0]["total_trades"], 42)
        self.assertIn("fitness_components", summary["leaderboard"][0])
        self.assertEqual(loaded[-1]["genomes"][0]["total_trades"], 42)
        self.assertIn("risk_per_trade", loaded[-1]["genomes"][0])


if __name__ == "__main__":
    unittest.main()
