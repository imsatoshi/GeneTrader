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
            "build_offline_data_manifest",
            "evaluate_data_coverage_gate",
            "run_offline_data_gate",
            "run_backtest_preflight",
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
