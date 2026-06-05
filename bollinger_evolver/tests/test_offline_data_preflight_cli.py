"""Tests for the offline data preflight CLI adapter."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_preflight_cli import (
    EXIT_OK,
    EXIT_PREFLIGHT_FAILED,
    EXIT_USAGE_ERROR,
    run_offline_data_preflight_cli,
)


class TestOfflineDataPreflightCli(unittest.TestCase):
    def _write(self, root: Path, relative_path: str, content: bytes = b"x") -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _write_requirements(self, root: Path, payload: object) -> Path:
        path = root / "requirements.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _run(self, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_offline_data_preflight_cli(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_root_json_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            code, stdout, stderr = self._run(["--root", str(root), "--json"])

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["ok"])

    def test_requirements_json_is_applied_to_cli_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            data_root = temp_root / "data"
            data_root.mkdir()
            requirements_path = self._write_requirements(
                temp_root,
                {"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
            )
            self._write(data_root, "BTC_USDT-1h.json")
            code, stdout, stderr = self._run(
                [
                    "--root",
                    str(data_root),
                    "--json",
                    "--requirements",
                    str(requirements_path),
                ]
            )

        payload = json.loads(stdout)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertTrue(payload["ok"])
        self.assertEqual(
            payload["metadata"]["requirements"],
            {"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
        )

    def test_requirements_json_missing_coverage_returns_preflight_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            data_root = temp_root / "data"
            data_root.mkdir()
            requirements_path = self._write_requirements(
                temp_root,
                {"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]},
            )
            self._write(data_root, "BTC_USDT-1h.json")
            code, stdout, stderr = self._run(
                [
                    "--root",
                    str(data_root),
                    "--json",
                    "--requirements",
                    str(requirements_path),
                ]
            )

        payload = json.loads(stdout)
        self.assertEqual(code, EXIT_PREFLIGHT_FAILED)
        self.assertEqual(stderr, "")
        self.assertFalse(payload["ok"])
        self.assertIn(
            {
                "code": "missing_required_dataset",
                "message": "missing_required_dataset: BTC/USDT 4h",
                "path": None,
                "severity": "error",
            },
            payload["issues"],
        )

    def test_missing_requirements_file_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            missing_path = root / "missing_requirements.json"
            code, stdout, stderr = self._run(
                ["--root", str(root), "--json", "--requirements", str(missing_path)]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("requirements_not_found", stderr)

    def test_invalid_requirements_file_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            requirements_path = root / "requirements.json"
            requirements_path.write_text("[not-json", encoding="utf-8")
            code, stdout, stderr = self._run(
                ["--root", str(root), "--json", "--requirements", str(requirements_path)]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("preflight_failed: ValueError", stderr)

    def test_cli_builds_requirements_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            data_root = temp_root / "data"
            data_root.mkdir()
            config_path = temp_root / "config.json"
            config_path.write_text(
                json.dumps({"market_filter_pair": "BTC/USDT", "base_timeframe": "1h"}),
                encoding="utf-8",
            )
            self._write(data_root, "BTC_USDT-1h.json")
            code, stdout, stderr = self._run(
                ["--root", str(data_root), "--json", "--config", str(config_path)]
            )

        payload = json.loads(stdout)
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["metadata"]["requirements"], {"pairs": ["BTC/USDT"], "timeframes": ["1h"]})

    def test_cli_rejects_config_and_requirements_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            requirements_path = self._write_requirements(root, {"pairs": ["BTC/USDT"], "timeframes": ["1h"]})
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps({"market_filter_pair": "BTC/USDT", "base_timeframe": "1h"}),
                encoding="utf-8",
            )
            code, stdout, stderr = self._run(
                [
                    "--root",
                    str(root),
                    "--json",
                    "--config",
                    str(config_path),
                    "--requirements",
                    str(requirements_path),
                ]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("config_conflicts_with_requirements", stderr)

    def test_cli_rejects_config_and_inline_requirements_together(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.json"
            config_path.write_text(
                json.dumps({"market_filter_pair": "BTC/USDT", "base_timeframe": "1h"}),
                encoding="utf-8",
            )
            code, stdout, stderr = self._run(
                [
                    "--root",
                    str(root),
                    "--json",
                    "--config",
                    str(config_path),
                    "--pair",
                    "BTC/USDT",
                    "--timeframe",
                    "1h",
                ]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("config_conflicts_with_requirements", stderr)

    def test_cli_config_missing_file_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            code, stdout, stderr = self._run(
                ["--root", str(root), "--json", "--config", str(root / "missing.json")]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("config_not_found", stderr)

    def test_cli_config_invalid_json_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "config.json"
            config_path.write_text("{not-json", encoding="utf-8")
            code, stdout, stderr = self._run(
                ["--root", str(root), "--json", "--config", str(config_path)]
            )

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("config_failed: ValueError", stderr)

    def test_pretty_outputs_deterministic_pretty_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            first = self._run(["--root", str(root), "--pretty"])
            second = self._run(["--root", str(root), "--pretty"])

        self.assertEqual(first[0], EXIT_OK)
        self.assertEqual(first[1], second[1])
        self.assertIn('\n  "accepted_files": 1,', first[1])

    def test_text_outputs_deterministic_text_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            first = self._run(["--root", str(root), "--text"])
            second = self._run(["--root", str(root), "--text"])

        self.assertEqual(first[0], EXIT_OK)
        self.assertEqual(first[1], second[1])
        self.assertIn("Offline Data Preflight Report", first[1])
        self.assertIn("status: PASS", first[1])
        with self.assertRaises(json.JSONDecodeError):
            json.loads(first[1])

    def test_text_output_reports_requirement_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            data_root = temp_root / "data"
            data_root.mkdir()
            requirements_path = self._write_requirements(
                temp_root,
                {"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]},
            )
            self._write(data_root, "BTC_USDT-1h.json")
            code, stdout, stderr = self._run(
                [
                    "--root",
                    str(data_root),
                    "--text",
                    "--requirements",
                    str(requirements_path),
                ]
            )

        self.assertEqual(code, EXIT_PREFLIGHT_FAILED)
        self.assertEqual(stderr, "")
        self.assertIn("missing_required_dataset", stdout)

    def test_json_output_is_deterministic_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "z/ETH_USDT-5m.csv")
            self._write(root, "a/BTC_USDT-1h.json")
            first = self._run(["--root", str(root), "--json"])
            second = self._run(["--root", str(root), "--json"])

        self.assertEqual(first[0], EXIT_OK)
        self.assertEqual(first[1], second[1])

    def test_output_writes_tempfile_and_quiet_suppresses_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            output = Path(temp_dir) / "report.json"
            self._write(root, "BTC_USDT-1h.json")
            code, stdout, stderr = self._run(
                ["--root", str(root), "--json", "--output", str(output), "--quiet"]
            )

            written = output.read_text(encoding="utf-8")

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(written)["ok"])

    def test_empty_directory_returns_preflight_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            code, stdout, stderr = self._run(["--root", temp_dir, "--json"])

        self.assertEqual(code, EXIT_PREFLIGHT_FAILED)
        self.assertEqual(stderr, "")
        self.assertFalse(json.loads(stdout)["ok"])

    def test_missing_root_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"
            code, stdout, stderr = self._run(["--root", str(missing), "--json"])

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("root_not_found", stderr)

    def test_file_root_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_file = Path(temp_dir) / "BTC_USDT-1h.json"
            root_file.write_bytes(b"x")
            code, stdout, stderr = self._run(["--root", str(root_file), "--json"])

        self.assertEqual(code, EXIT_USAGE_ERROR)
        self.assertEqual(stdout, "")
        self.assertIn("root_not_directory", stderr)

    def test_fail_on_warning_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.json")
            self._write(root, "README.txt")
            code, stdout, stderr = self._run(
                ["--root", str(root), "--json", "--fail-on-warning"]
            )

        self.assertEqual(code, EXIT_PREFLIGHT_FAILED)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["ok"])

    def test_secret_payload_does_not_appear_in_stdout_stderr_or_output(self) -> None:
        marker = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "data"
            root.mkdir()
            output = Path(temp_dir) / "report.json"
            self._write(root, "BTC_USDT-1h.csv", marker.encode("ascii"))
            code, stdout, stderr = self._run(
                ["--root", str(root), "--json", "--output", str(output)]
            )
            written = output.read_text(encoding="utf-8")

        self.assertEqual(code, EXIT_OK)
        self.assertNotIn(marker, stdout)
        self.assertNotIn(marker, stderr)
        self.assertNotIn(marker, written)

    def test_cli_path_does_not_read_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write(root, "BTC_USDT-1h.csv", b"content should not be read")
            with patch.object(Path, "read_text", side_effect=AssertionError("content read")):
                code, stdout, stderr = self._run(["--root", str(root), "--json"])

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertTrue(json.loads(stdout)["ok"])

    def test_import_bollinger_evolver_remains_safe(self) -> None:
        import bollinger_evolver

        self.assertTrue(callable(bollinger_evolver.run_offline_data_preflight_cli))


if __name__ == "__main__":
    unittest.main()
