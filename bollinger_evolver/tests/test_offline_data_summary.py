"""Tests for human-readable offline data audit summaries."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.offline_data_summary import (
    format_offline_data_diff_summary,
    format_offline_data_preflight_summary,
)
from bollinger_evolver.offline_preflight_cli import EXIT_OK, run_offline_data_preflight_cli
from bollinger_evolver.preflight import build_offline_data_preflight_report


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataSummary(unittest.TestCase):
    def _write(self, root: Path, name: str, content: str = PAYLOAD) -> Path:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_offline_data_preflight_cli(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_preflight_summary_is_deterministic_and_counts_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv")
            self._write(root, "ETH_USDT-5m.json")
            report = build_offline_data_preflight_report(root)
            first = format_offline_data_preflight_summary(report)
            second = format_offline_data_preflight_summary(report)

        self.assertEqual(first, second)
        self.assertIn("status: PASS", first)
        self.assertIn("- .csv: 1", first)
        self.assertIn("- .json: 1", first)
        self.assertNotIn(PAYLOAD, first)

    def test_preflight_summary_dataset_limit_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "a/BTC_USDT-1h.csv")
            self._write(root, "b/ETH_USDT-5m.json")
            report = build_offline_data_preflight_report(root)
            rendered = format_offline_data_preflight_summary(
                report,
                include_datasets=True,
                max_datasets=1,
            )

        self.assertIn("datasets:", rendered)
        self.assertIn("a/BTC_USDT-1h.csv", rendered)
        self.assertIn("- omitted: 1", rendered)
        self.assertNotIn("b/ETH_USDT-5m.json", rendered)

    def test_diff_summary_is_deterministic(self) -> None:
        old = {"datasets": [{"relative_path": "a.csv", "size_bytes": 1, "suffix": ".csv"}]}
        new = {
            "datasets": [
                {"relative_path": "a.csv", "size_bytes": 2, "suffix": ".csv"},
                {"relative_path": "b.json", "size_bytes": 1, "suffix": ".json"},
            ]
        }
        diff = compare_offline_data_preflight_reports(old, new)
        first = format_offline_data_diff_summary(diff)
        second = format_offline_data_diff_summary(diff)

        self.assertEqual(first, second)
        self.assertIn("added_datasets: 1", first)
        self.assertIn("changed_datasets: 1", first)

    def test_cli_summary_outputs_summary_and_quiet_suppresses_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv")
            first = self._run_cli(["--root", str(root), "--summary"])
            second = self._run_cli(["--root", str(root), "--summary"])
            quiet = self._run_cli(["--root", str(root), "--summary", "--quiet"])

        self.assertEqual(first[0], EXIT_OK)
        self.assertEqual(first[1], second[1])
        self.assertEqual(first[2], "")
        self.assertIn("Offline Data Preflight Summary", first[1])
        self.assertEqual(quiet[1], "")
        self.assertEqual(quiet[2], "")
        self.assertNotIn(PAYLOAD, first[1])


if __name__ == "__main__":
    unittest.main()
