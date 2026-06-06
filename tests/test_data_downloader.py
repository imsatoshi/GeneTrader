import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from data.downloader import (
    DataDownloader,
    LEGACY_EXECUTION_ENV,
    LegacyFreqtradeExecutionDisabled,
    MANIFEST_FILENAME,
    build_coverage_manifest,
    coverage_manifest_is_ready,
    load_coverage_manifest,
    _redact_command_for_log,
)


class TestDataDownloaderCoverage(unittest.TestCase):
    def _write_config(self, root: Path, pairs):
        config_path = root / "config.json"
        config_path.write_text(
            json.dumps({"exchange": {"pair_whitelist": pairs}}),
            encoding="utf-8",
        )
        return config_path

    def test_build_coverage_manifest_flags_missing_gaps_and_invalid_ohlc(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            data_dir.mkdir()
            config_path = self._write_config(root, ["BTC/USDT"])
            (data_dir / "BTC_USDT-1m.json").write_text(
                json.dumps([
                    [1704067200000, 100, 101, 99, 100],
                    [1704067380000, 100, 101, -1, 100],
                ]),
                encoding="utf-8",
            )

            manifest = build_coverage_manifest(
                str(config_path),
                str(data_dir),
                ["1m", "5m"],
                date(2024, 1, 1),
            )

        self.assertEqual(manifest["status"], "partial")
        self.assertEqual(manifest["missing_count"], 1)
        self.assertEqual(manifest["gap_count"], 1)
        self.assertEqual(manifest["invalid_ohlc_count"], 1)
        self.assertFalse(coverage_manifest_is_ready(manifest))

    def test_download_data_writes_coverage_manifest_without_real_freqtrade(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data_dir = root / "data"
            data_dir.mkdir()
            config_path = self._write_config(root, ["BTC/USDT"])
            (data_dir / "BTC_USDT-1m.json").write_text(
                json.dumps([
                    [1704067200000, 100, 101, 99, 100],
                    [1704067260000, 100, 101, 99, 100],
                ]),
                encoding="utf-8",
            )
            downloader = DataDownloader.__new__(DataDownloader)
            downloader.config_file = str(config_path)
            downloader.data_dir = str(data_dir)
            downloader.freqtrade_path = "freqtrade"
            downloader.timeframes = ["1m"]

            with patch.dict(os.environ, {LEGACY_EXECUTION_ENV: "1"}), patch(
                "data.downloader.subprocess.run",
                return_value=SimpleNamespace(stdout="download ok"),
            ) as mocked_run:
                manifest = downloader.download_data(date(2024, 1, 1))

            mocked_run.assert_called_once()
            self.assertEqual(manifest["status"], "ready")
            self.assertTrue((data_dir / MANIFEST_FILENAME).exists())
            self.assertTrue(coverage_manifest_is_ready(load_coverage_manifest(str(data_dir))))

    def test_download_data_disabled_without_explicit_opt_in(self):
        downloader = DataDownloader.__new__(DataDownloader)
        downloader.config_file = "config.json"
        downloader.data_dir = "data"
        downloader.freqtrade_path = "freqtrade"
        downloader.timeframes = ["1m"]

        with patch.dict(os.environ, {LEGACY_EXECUTION_ENV: ""}, clear=False), patch(
            "data.downloader.subprocess.run",
            side_effect=AssertionError("subprocess must not run without explicit opt-in"),
        ) as mocked_run:
            with self.assertRaises(LegacyFreqtradeExecutionDisabled):
                downloader.download_data(date(2024, 1, 1))
            self.assertFalse(mocked_run.called)

    def test_download_command_log_redacts_paths_and_secret_values(self):
        redacted = _redact_command_for_log([
            "freqtrade",
            "download-data",
            "--config",
            "C:/Users/name/.env",
            "--api-key=abc",
            "token=secret-value",
        ])

        self.assertNotIn("C:/Users", redacted)
        self.assertNotIn(".env", redacted)
        self.assertNotIn("abc", redacted)
        self.assertNotIn("secret-value", redacted)


if __name__ == "__main__":
    unittest.main()
