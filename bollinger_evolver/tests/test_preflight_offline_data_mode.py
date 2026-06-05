"""Tests for offline data inventory preflight mode."""

from __future__ import annotations

import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.preflight import run_offline_data_preflight


class TestOfflineDataPreflight(unittest.TestCase):
    def test_offline_data_preflight_passes_for_valid_temp_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            result = run_offline_data_preflight(root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["gate"]["ok"])

    def test_offline_data_preflight_fails_for_missing_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_offline_data_preflight(Path(temp_dir) / "missing")

        self.assertFalse(result["ok"])
        self.assertIn("root_not_found", result["errors"])

    def test_offline_data_preflight_fails_for_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_offline_data_preflight(Path(temp_dir))

        self.assertFalse(result["ok"])
        self.assertIn("datasets_empty", result["errors"])
        self.assertIn("datasets_empty", result["error_codes"])

    def test_offline_data_preflight_fails_for_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"")
            result = run_offline_data_preflight(root)

        self.assertFalse(result["ok"])
        self.assertIn("datasets[0].size_bytes_not_positive", result["errors"])

    def test_offline_data_preflight_reports_gate_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"")
            result = run_offline_data_preflight(root)

        self.assertFalse(result["gate"]["ok"])
        self.assertTrue(result["gate"]["errors"])

    def test_offline_data_preflight_does_not_require_network_or_real_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "ETH_USDT-5m.csv").write_bytes(b"x")
            with patch.object(
                socket,
                "create_connection",
                side_effect=AssertionError("network should not be used"),
            ):
                result = run_offline_data_preflight(root)

        self.assertTrue(result["ok"])

    def test_offline_data_preflight_passes_with_satisfied_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            result = run_offline_data_preflight(
                root,
                requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h"]},
            )

        self.assertTrue(result["ok"])
        self.assertTrue(result["gate"]["requirements"]["ok"])
        self.assertEqual(result["requirements"], {"pairs": ["BTC/USDT"], "timeframes": ["1h"]})

    def test_offline_data_preflight_fails_with_missing_required_timeframe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            result = run_offline_data_preflight(
                root,
                requirements={"pairs": ["BTC/USDT"], "timeframes": ["1h", "4h"]},
            )

        self.assertFalse(result["ok"])
        self.assertIn(
            {"code": "missing_required_dataset", "pair": "BTC/USDT", "timeframe": "4h"},
            result["errors"],
        )
        self.assertIn("missing_required_dataset", result["error_codes"])

    def test_offline_data_preflight_fails_with_invalid_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            result = run_offline_data_preflight(
                root,
                requirements={"pairs": ["BTCUSDT"], "timeframes": ["1h"]},
            )

        self.assertFalse(result["ok"])
        self.assertIn({"code": "requirements_pair_invalid", "pair": "BTCUSDT"}, result["errors"])

    def test_offline_data_preflight_without_requirements_preserves_stage_011_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "BTC_USDT-1h.json").write_bytes(b"x")
            result = run_offline_data_preflight(root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["requirements"], {})
        self.assertTrue(result["gate"]["requirements"]["ok"])


if __name__ == "__main__":
    unittest.main()
