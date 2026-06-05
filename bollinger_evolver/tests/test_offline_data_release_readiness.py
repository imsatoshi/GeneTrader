"""Tests for offline data release-readiness audit helper."""

from __future__ import annotations

import builtins
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.offline_release import run_offline_data_release_readiness_audit


PAYLOAD = "SECRET_MARKET_PAYLOAD_SHOULD_NOT_APPEAR"


class TestOfflineDataReleaseReadiness(unittest.TestCase):
    def test_release_readiness_audit_is_ok_and_json_serializable(self) -> None:
        audit = run_offline_data_release_readiness_audit()

        self.assertTrue(audit["ok"])
        self.assertEqual(audit["issues"], [])
        self.assertTrue(audit["checks"])
        json.dumps(audit, sort_keys=True)

    def test_release_readiness_audit_is_deterministic(self) -> None:
        first = run_offline_data_release_readiness_audit()
        second = run_offline_data_release_readiness_audit()

        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )

    def test_release_readiness_audit_does_not_scan_or_read_fake_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fake_file = root / "BTC_USDT-1h.csv"
            fake_file.write_text(PAYLOAD, encoding="utf-8")
            fake_file = fake_file.resolve()
            original_read_text = Path.read_text
            original_read_bytes = Path.read_bytes
            original_open = builtins.open

            def guarded_read_text(path: Path, *args, **kwargs):
                if path.resolve() == fake_file:
                    raise AssertionError("fake market content read")
                return original_read_text(path, *args, **kwargs)

            def guarded_read_bytes(path: Path, *args, **kwargs):
                if path.resolve() == fake_file:
                    raise AssertionError("fake market content read")
                return original_read_bytes(path, *args, **kwargs)

            def guarded_open(file, mode="r", *args, **kwargs):
                if "r" in mode:
                    try:
                        if Path(file).resolve() == fake_file:
                            raise AssertionError("fake market content read")
                    except TypeError:
                        pass
                return original_open(file, mode, *args, **kwargs)

            with patch.object(Path, "rglob", side_effect=AssertionError("unexpected scan")):
                with patch.object(Path, "read_text", guarded_read_text):
                    with patch.object(Path, "read_bytes", guarded_read_bytes):
                        with patch.object(builtins, "open", guarded_open):
                            audit = run_offline_data_release_readiness_audit()

        self.assertTrue(audit["ok"])
        self.assertNotIn(PAYLOAD, json.dumps(audit, sort_keys=True))

    def test_package_export_is_callable(self) -> None:
        import bollinger_evolver

        self.assertTrue(callable(bollinger_evolver.run_offline_data_release_readiness_audit))


if __name__ == "__main__":
    unittest.main()
