"""Package export safety tests for the public Bollinger Evolver API."""

from __future__ import annotations

import importlib
import socket
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


class TestPackageExports(unittest.TestCase):
    def test_package_import_is_safe(self) -> None:
        sys.modules.pop("bollinger_evolver", None)

        with patch("subprocess.run", side_effect=AssertionError("subprocess should not run on import")):
            with patch("socket.create_connection", side_effect=AssertionError("network should not run on import")):
                with patch("pathlib.Path.write_text", side_effect=AssertionError("writes should not run on import")):
                    with patch("pathlib.Path.write_bytes", side_effect=AssertionError("writes should not run on import")):
                        module = importlib.import_module("bollinger_evolver")

        self.assertIsNotNone(module)

    def test_package_exports_readiness_symbols(self) -> None:
        import bollinger_evolver

        expected_exports = [
            "build_manifest_from_inventory",
            "build_offline_data_manifest",
            "build_offline_data_preflight_report",
            "build_offline_requirements_from_config",
            "build_requirements_coverage_matrix",
            "check_manifest_requirements",
            "compare_offline_data_preflight_reports",
            "evaluate_data_coverage_gate",
            "extract_data_gate_error_codes",
            "format_offline_data_diff_summary",
            "format_offline_data_preflight_summary",
            "get_legacy_content_read_allowlist",
            "get_offline_data_metadata_only_boundary",
            "inventory_offline_data",
            "load_offline_data_manifest",
            "load_offline_data_requirements",
            "load_offline_requirements_from_config",
            "normalize_offline_relative_path",
            "normalize_pair_symbol",
            "normalize_timeframe",
            "offline_preflight_main",
            "render_offline_data_preflight_report",
            "run_backtest_offline_data_gate",
            "run_offline_data_gate",
            "run_offline_data_preflight_cli",
            "run_offline_data_preflight",
            "save_offline_data_manifest",
            "summarize_manifest",
            "build_backtest_offline_data_gate",
            "run_backtest_preflight",
            "run_offline_data_boundary_audit",
            "run_offline_data_release_readiness_audit",
            "run_offline_data_workflow_preflight",
            "validate_metadata_only_boundary",
            "validate_offline_data_preflight_report_dict",
        ]
        for name in expected_exports:
            with self.subTest(name=name):
                self.assertTrue(hasattr(bollinger_evolver, name))
                self.assertIn(name, bollinger_evolver.__all__)

    def test_package_import_does_not_require_freqtrade_or_data_dir(self) -> None:
        import bollinger_evolver

        self.assertTrue(callable(bollinger_evolver.run_backtest_preflight))
        self.assertTrue(callable(bollinger_evolver.build_offline_data_manifest))
        self.assertTrue(callable(bollinger_evolver.run_offline_data_gate))

    def test_package_import_is_repeatable(self) -> None:
        import bollinger_evolver

        reloaded = importlib.reload(bollinger_evolver)
        self.assertIsNotNone(reloaded)
        self.assertTrue(hasattr(reloaded, "run_offline_data_gate"))

    def test_public_import_does_not_create_runtime_report_files(self) -> None:
        runtime_root = Path(__file__).resolve().parents[2] / ".runtime" / "bollinger_evolver"
        before = {path.relative_to(runtime_root) for path in runtime_root.rglob("*")} if runtime_root.exists() else set()

        import bollinger_evolver  # noqa: F401

        after = {path.relative_to(runtime_root) for path in runtime_root.rglob("*")} if runtime_root.exists() else set()
        self.assertEqual(before, after)

    def test_package_module_source_has_no_live_import_side_effect_calls(self) -> None:
        source = (Path(__file__).resolve().parents[1] / "__init__.py").read_text(encoding="utf-8")
        forbidden_tokens = [
            "subprocess.run(",
            "requests.",
            "ccxt",
            "freqtrade backtesting",
            "write_text(",
            "write_bytes(",
            "mkdir(",
            "socket.create_connection(",
        ]
        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
