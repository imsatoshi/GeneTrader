"""Tests for execution sandbox design manifests."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from bollinger_evolver.freqtrade_command_manifest import (
    BacktestCommandPlan,
    build_freqtrade_backtest_command_manifest,
)
from bollinger_evolver.freqtrade_execution_sandbox import (
    ExecutionSandboxManifest,
    ExecutionSandboxPlan,
    ExecutionSandboxPolicy,
    build_expected_backtest_output_directory,
    build_freqtrade_execution_sandbox_manifest,
    sandbox_manifest_to_json_safe_dict,
    validate_sandbox_paths,
    write_execution_sandbox_manifest,
)


def _build_command_manifest(root: Path):
    config = root / "config.json"
    config.write_text("{}", encoding="utf-8")
    return build_freqtrade_backtest_command_manifest(
        BacktestCommandPlan(
            strategy_name="BollingerBandStrategy",
            config_path=config,
            timeframe="5m",
            timerange="20240101-20240201",
            pairs=("BTC/USDT",),
            backtest_directory=root / "future_command_output",
            allowed_roots=(root,),
        )
    )


class TestFreqtradeExecutionSandbox(unittest.TestCase):
    def test_builds_sandbox_manifest_from_command_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "tmp-stage-088"
            sandbox_root.mkdir()
            command_manifest = _build_command_manifest(root)

            manifest = build_freqtrade_execution_sandbox_manifest(
                ExecutionSandboxPlan(
                    command_manifest=command_manifest,
                    sandbox_root=sandbox_root,
                    allowed_roots=(root,),
                )
            )

        self.assertIsInstance(manifest, ExecutionSandboxManifest)
        self.assertEqual(manifest.execution_mode, "sandbox_design_only_no_execution")
        self.assertFalse(manifest.safety_flags["freqtrade_executed"])
        self.assertFalse(manifest.safety_flags["subprocess_used"])
        self.assertFalse(manifest.safety_flags["real_backtest_result_created"])

    def test_validates_sandbox_root_under_allowed_root(self) -> None:
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as outside:
            allowed_root = Path(allowed)
            sandbox_root = allowed_root / "sandbox"
            sandbox_root.mkdir()
            command_manifest = _build_command_manifest(allowed_root)

            validated = validate_sandbox_paths(
                ExecutionSandboxPlan(
                    command_manifest=command_manifest,
                    sandbox_root=sandbox_root,
                    allowed_roots=(allowed_root,),
                )
            )

            self.assertEqual(validated["sandbox_root"], sandbox_root.resolve())
            with self.assertRaises(ValueError):
                validate_sandbox_paths(
                    ExecutionSandboxPlan(
                        command_manifest=command_manifest,
                        sandbox_root=Path(outside) / "sandbox",
                        allowed_roots=(allowed_root,),
                    )
                )

    def test_rejects_real_backtest_directory_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_manifest = _build_command_manifest(root)

            with self.assertRaises(ValueError):
                validate_sandbox_paths(
                    ExecutionSandboxPlan(
                        command_manifest=command_manifest,
                        sandbox_root=root / "user_data" / "backtest_results",
                        allowed_roots=(root,),
                    )
                )

    def test_rejects_secret_like_path_segments(self) -> None:
        markers = (".env", "secret", "secrets", "credentials", "private_key", "password", "api_key")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command_manifest = _build_command_manifest(root)
            for marker in markers:
                with self.subTest(marker=marker):
                    with self.assertRaises(ValueError):
                        validate_sandbox_paths(
                            ExecutionSandboxPlan(
                                command_manifest=command_manifest,
                                sandbox_root=root / marker / "sandbox",
                                allowed_roots=(root,),
                            )
                        )

    def test_output_directory_stays_inside_sandbox_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()

            self.assertEqual(
                build_expected_backtest_output_directory(sandbox_root, output_subdir="backtest_results"),
                sandbox_root / "backtest_results",
            )
            for unsafe in ("../escape", "/absolute", "bad;rm"):
                with self.subTest(unsafe=unsafe):
                    with self.assertRaises(ValueError):
                        build_expected_backtest_output_directory(sandbox_root, output_subdir=unsafe)

    def test_does_not_create_expected_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            command_manifest = _build_command_manifest(root)
            expected_output = sandbox_root / "backtest_results"

            build_freqtrade_execution_sandbox_manifest(
                ExecutionSandboxPlan(
                    command_manifest=command_manifest,
                    sandbox_root=sandbox_root,
                    allowed_roots=(root,),
                )
            )

            self.assertFalse(expected_output.exists())

    def test_rejects_unsafe_command_manifest_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            command_manifest = _build_command_manifest(root)

            for key in ("subprocess_used", "shell_used", "network_used", "real_backtest_result_created"):
                unsafe_flags = dict(command_manifest.safety_flags)
                unsafe_flags[key] = True
                unsafe_manifest = replace(command_manifest, safety_flags=unsafe_flags)
                with self.subTest(key=key):
                    with self.assertRaises(ValueError):
                        build_freqtrade_execution_sandbox_manifest(
                            ExecutionSandboxPlan(
                                command_manifest=unsafe_manifest,
                                sandbox_root=sandbox_root,
                                allowed_roots=(root,),
                            )
                        )

    def test_rejects_unsafe_command_manifest_execution_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            command_manifest = replace(_build_command_manifest(root), execution_mode="real_execution")

            with self.assertRaises(ValueError):
                build_freqtrade_execution_sandbox_manifest(
                    ExecutionSandboxPlan(
                        command_manifest=command_manifest,
                        sandbox_root=sandbox_root,
                        allowed_roots=(root,),
                    )
                )

    def test_redacts_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "tmp-stage-088"
            sandbox_root.mkdir()
            manifest = build_freqtrade_execution_sandbox_manifest(
                ExecutionSandboxPlan(
                    command_manifest=_build_command_manifest(root),
                    sandbox_root=sandbox_root,
                    allowed_roots=(root,),
                )
            )
            encoded = json.dumps(sandbox_manifest_to_json_safe_dict(manifest), sort_keys=True)

        self.assertNotIn(str(root), encoded)
        self.assertNotIn("C:/Users", encoded)
        self.assertNotIn("/home/", encoded)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn(".env", encoded)
        self.assertIn("<redacted:tmp-stage-088>", encoded)

    def test_json_safe_and_deterministic_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            command_manifest = _build_command_manifest(root)
            plan = ExecutionSandboxPlan(
                command_manifest=command_manifest,
                sandbox_root=sandbox_root,
                allowed_roots=(root,),
            )
            first = sandbox_manifest_to_json_safe_dict(build_freqtrade_execution_sandbox_manifest(plan))
            second = sandbox_manifest_to_json_safe_dict(build_freqtrade_execution_sandbox_manifest(plan))

        json.dumps(first, sort_keys=True)
        self.assertEqual(first, second)

    def test_rollback_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            manifest = build_freqtrade_execution_sandbox_manifest(
                ExecutionSandboxPlan(
                    command_manifest=_build_command_manifest(root),
                    sandbox_root=sandbox_root,
                    allowed_roots=(root,),
                    cleanup_policy="delete_tempdir_after_review",
                )
            )

        self.assertEqual(manifest.rollback_plan["cleanup_policy"], "delete_tempdir_after_review")
        self.assertTrue(manifest.rollback_plan["delete_sandbox_root"])
        self.assertFalse(manifest.rollback_plan["execution_outputs_expected"])

    def test_write_manifest_artifact_to_explicit_temp_path_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            expected_output = sandbox_root / "backtest_results"
            manifest = build_freqtrade_execution_sandbox_manifest(
                ExecutionSandboxPlan(
                    command_manifest=_build_command_manifest(root),
                    sandbox_root=sandbox_root,
                    allowed_roots=(root,),
                )
            )
            output_path = root / "audit" / "sandbox_manifest.json"

            written = write_execution_sandbox_manifest(manifest, output_path)
            loaded = json.loads(written.read_text(encoding="utf-8"))

            self.assertTrue(written.exists())
            self.assertEqual(loaded["execution_mode"], "sandbox_design_only_no_execution")
            self.assertFalse(expected_output.exists())
            self.assertNotIn(str(root), json.dumps(loaded, sort_keys=True))

    def test_policy_rejects_execution_allowances(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()

            with self.assertRaises(ValueError):
                build_freqtrade_execution_sandbox_manifest(
                    ExecutionSandboxPlan(
                        command_manifest=_build_command_manifest(root),
                        sandbox_root=sandbox_root,
                        allowed_roots=(root,),
                    ),
                    policy=ExecutionSandboxPolicy(allow_subprocess=True),
                )


if __name__ == "__main__":
    unittest.main()
