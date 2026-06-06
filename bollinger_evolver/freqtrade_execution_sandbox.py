"""Isolated execution sandbox design for future backtest runs.

This module produces JSON-safe sandbox manifests only. It does not execute
commands, create expected backtest output directories, or load external trading
libraries.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from bollinger_evolver.freqtrade_command_manifest import (
    BacktestCommandManifest,
    command_manifest_to_json_safe_dict,
)


SANDBOX_EXECUTION_MODE = "sandbox_design_only_no_execution"
COMMAND_PLAN_MODE = "plan_only_no_execution"
SHELL_META_CHARS = frozenset(";|&<>`$\\")
SECRET_PATH_MARKERS = frozenset(
    {
        ".env",
        "api_key",
        "credentials",
        "password",
        "private_key",
        "secret",
        "secrets",
    }
)
REQUIRED_COMMAND_FLAGS = (
    "freqtrade_executed",
    "subprocess_used",
    "shell_used",
    "exchange_api_used",
    "network_used",
    "secrets_loaded",
    "real_backtest_result_created",
)


@dataclass(frozen=True)
class ExecutionSandboxPolicy:
    execution_mode: str = SANDBOX_EXECUTION_MODE
    require_preapproved_manifest: bool = True
    allow_command_execution: bool = False
    allow_subprocess: bool = False
    allow_shell: bool = False
    allow_network: bool = False
    allow_exchange_api: bool = False
    allow_secret_loading: bool = False
    allow_real_backtest_result_creation: bool = False
    allow_copying_user_config: bool = False
    allow_copying_strategy_file: bool = False
    allow_writing_outside_sandbox: bool = False
    require_temp_output_root: bool = True
    require_report_reimport_via_gate: bool = True
    required_safety_flags: Mapping[str, bool] = field(
        default_factory=lambda: {
            "freqtrade_executed": False,
            "subprocess_used": False,
            "shell_used": False,
            "exchange_api_used": False,
            "network_used": False,
            "secrets_loaded": False,
            "real_backtest_result_created": False,
        }
    )


@dataclass(frozen=True)
class ExecutionSandboxPlan:
    command_manifest: BacktestCommandManifest
    sandbox_root: Path
    allowed_roots: tuple[Path, ...]
    import_allowed_roots: tuple[Path, ...] = ()
    expected_output_subdir: str = "backtest_results"
    cleanup_policy: str = "delete_tempdir_after_review"
    notes: str | None = None


@dataclass(frozen=True)
class ExecutionSandboxManifest:
    source_type: str
    execution_mode: str
    command_manifest_summary: Mapping[str, object]
    redacted_sandbox_root: str
    redacted_expected_output_directory: str
    output_import_gate_required: bool
    allowed_roots_summary: tuple[str, ...]
    cleanup_policy: str
    rollback_plan: Mapping[str, object]
    safety_flags: Mapping[str, bool]
    warnings: tuple[str, ...] = ()


def _has_shell_meta(value: str) -> bool:
    return any(character in value for character in SHELL_META_CHARS)


def _is_redacted_token(value: str) -> bool:
    if not (value.startswith("<redacted:") and value.endswith(">")):
        return False
    inner = value[len("<redacted:") : -1]
    return bool(inner) and not any(character in inner for character in SHELL_META_CHARS)


def _has_glob(value: str) -> bool:
    return any(character in value for character in "*?[]")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_disk_root(path: Path) -> bool:
    resolved = path.resolve()
    return resolved.parent == resolved


def _contains_secret_segment(path: Path) -> bool:
    return any(part.lower() in SECRET_PATH_MARKERS for part in path.parts)


def _contains_real_backtest_results_path(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    return any(
        parts[index] == "user_data" and index + 1 < len(parts) and parts[index + 1] == "backtest_results"
        for index in range(len(parts))
    )


def redact_sandbox_path(path: Path) -> str:
    return f"<redacted:{Path(path).name}>"


def build_expected_backtest_output_directory(
    sandbox_root: Path,
    *,
    output_subdir: str = "backtest_results",
) -> Path:
    """Return a future output path without creating it."""

    if not output_subdir or output_subdir.strip() != output_subdir:
        raise ValueError("expected_output_subdir_invalid")
    subdir_path = Path(output_subdir)
    if subdir_path.is_absolute() or len(subdir_path.parts) != 1:
        raise ValueError("expected_output_subdir_must_be_simple_relative_name")
    if _has_glob(output_subdir) or _has_shell_meta(output_subdir):
        raise ValueError("expected_output_subdir_unsafe")
    if _contains_secret_segment(subdir_path):
        raise ValueError("expected_output_subdir_secret_like")
    return Path(sandbox_root) / output_subdir


def validate_sandbox_paths(plan: ExecutionSandboxPlan) -> Mapping[str, Path]:
    """Validate sandbox path isolation without creating directories."""

    if not plan.allowed_roots:
        raise ValueError("sandbox_allowed_roots_required")
    sandbox_text = str(plan.sandbox_root)
    if _has_glob(sandbox_text):
        raise ValueError("sandbox_root_glob_not_allowed")
    sandbox_root = Path(plan.sandbox_root).resolve()
    if _is_disk_root(sandbox_root):
        raise ValueError("sandbox_root_must_not_be_disk_root")
    if _contains_secret_segment(sandbox_root):
        raise ValueError("sandbox_root_secret_like_path_not_allowed")
    if _contains_real_backtest_results_path(sandbox_root):
        raise ValueError("sandbox_root_must_not_be_real_backtest_results")
    if sandbox_root.exists() and not sandbox_root.is_dir():
        raise ValueError("sandbox_root_must_be_directory_or_future_directory")

    allowed_roots = tuple(Path(root).resolve() for root in plan.allowed_roots)
    if not any(_is_relative_to(sandbox_root, root) for root in allowed_roots):
        raise ValueError("sandbox_root_outside_allowed_roots")

    expected_output = build_expected_backtest_output_directory(
        sandbox_root,
        output_subdir=plan.expected_output_subdir,
    ).resolve()
    if not _is_relative_to(expected_output, sandbox_root):
        raise ValueError("expected_output_directory_outside_sandbox")

    import_roots: list[Path] = []
    for import_root in plan.import_allowed_roots:
        text = str(import_root)
        if _has_glob(text):
            raise ValueError("import_allowed_root_glob_not_allowed")
        resolved_import_root = Path(import_root).resolve()
        if _contains_secret_segment(resolved_import_root):
            raise ValueError("import_allowed_root_secret_like_path_not_allowed")
        if not any(_is_relative_to(resolved_import_root, root) for root in allowed_roots):
            raise ValueError("import_allowed_root_outside_allowed_roots")
        import_roots.append(resolved_import_root)

    return {
        "sandbox_root": sandbox_root,
        "expected_output_directory": expected_output,
        **{f"import_allowed_root_{index}": root for index, root in enumerate(import_roots)},
    }


def _validate_policy(policy: ExecutionSandboxPolicy) -> None:
    if policy.execution_mode != SANDBOX_EXECUTION_MODE:
        raise ValueError("sandbox_policy_execution_mode_invalid")
    unsafe_flags = (
        policy.allow_command_execution,
        policy.allow_subprocess,
        policy.allow_shell,
        policy.allow_network,
        policy.allow_exchange_api,
        policy.allow_secret_loading,
        policy.allow_real_backtest_result_creation,
        policy.allow_copying_user_config,
        policy.allow_copying_strategy_file,
        policy.allow_writing_outside_sandbox,
    )
    if any(unsafe_flags):
        raise ValueError("sandbox_policy_must_be_no_execution")
    for key, expected in policy.required_safety_flags.items():
        if expected is not False:
            raise ValueError(f"sandbox_policy_required_flag_must_be_false:{key}")


def _validate_command_manifest(manifest: BacktestCommandManifest, policy: ExecutionSandboxPolicy) -> None:
    if manifest.execution_mode != COMMAND_PLAN_MODE:
        raise ValueError("command_manifest_must_be_plan_only")
    if isinstance(manifest.argv, str) or not isinstance(manifest.argv, tuple):
        raise ValueError("command_manifest_argv_must_be_tuple")
    for token in manifest.argv:
        if not isinstance(token, str):
            raise ValueError("command_manifest_argv_tokens_must_be_strings")
        if _has_shell_meta(token) and not _is_redacted_token(token):
            raise ValueError("command_manifest_argv_token_shell_meta")
    for key in REQUIRED_COMMAND_FLAGS:
        if manifest.safety_flags.get(key) is not False:
            raise ValueError(f"command_manifest_unsafe_safety_flag:{key}")
    for key, expected in policy.required_safety_flags.items():
        if manifest.safety_flags.get(key) is not expected:
            raise ValueError(f"command_manifest_policy_flag_mismatch:{key}")


def build_sandbox_rollback_plan(
    sandbox_root: Path,
    *,
    cleanup_policy: str,
) -> Mapping[str, object]:
    return {
        "cleanup_policy": cleanup_policy,
        "delete_sandbox_root": cleanup_policy == "delete_tempdir_after_review",
        "delete_expected_output_directory": cleanup_policy == "delete_tempdir_after_review",
        "preserve_manifest_artifact": True,
        "manual_review_required_before_delete": False,
        "execution_outputs_expected": False,
        "redacted_sandbox_root": redact_sandbox_path(sandbox_root),
    }


def _safety_flags() -> dict[str, bool]:
    return {
        "freqtrade_executed": False,
        "subprocess_used": False,
        "shell_used": False,
        "exchange_api_used": False,
        "network_used": False,
        "secrets_loaded": False,
        "real_backtest_result_created": False,
        "sandbox_created": False,
        "output_directory_created": False,
    }


def build_freqtrade_execution_sandbox_manifest(
    plan: ExecutionSandboxPlan,
    *,
    policy: ExecutionSandboxPolicy | None = None,
) -> ExecutionSandboxManifest:
    """Build an isolated sandbox design manifest without performing execution."""

    active_policy = policy or ExecutionSandboxPolicy()
    _validate_policy(active_policy)
    _validate_command_manifest(plan.command_manifest, active_policy)
    resolved_paths = validate_sandbox_paths(plan)
    sandbox_root = resolved_paths["sandbox_root"]
    expected_output = resolved_paths["expected_output_directory"]
    command_dict = command_manifest_to_json_safe_dict(plan.command_manifest)
    command_summary = {
        "source_type": command_dict["source_type"],
        "execution_mode": command_dict["execution_mode"],
        "strategy_name": command_dict["strategy_name"],
        "redacted_argv": command_dict["redacted_argv"],
        "safety_flags": command_dict["safety_flags"],
        "warnings": command_dict["warnings"],
    }
    allowed_roots_summary = tuple(redact_sandbox_path(root) for root in plan.allowed_roots)
    return ExecutionSandboxManifest(
        source_type="freqtrade_execution_sandbox_manifest",
        execution_mode=SANDBOX_EXECUTION_MODE,
        command_manifest_summary=command_summary,
        redacted_sandbox_root=redact_sandbox_path(sandbox_root),
        redacted_expected_output_directory=redact_sandbox_path(expected_output),
        output_import_gate_required=active_policy.require_report_reimport_via_gate,
        allowed_roots_summary=allowed_roots_summary,
        cleanup_policy=plan.cleanup_policy,
        rollback_plan=build_sandbox_rollback_plan(sandbox_root, cleanup_policy=plan.cleanup_policy),
        safety_flags=_safety_flags(),
        warnings=("sandbox_design_only_not_executed",),
    )


def sandbox_manifest_to_json_safe_dict(
    manifest: ExecutionSandboxManifest,
) -> dict[str, object]:
    data = asdict(manifest)
    json.dumps(data, sort_keys=True)
    return data


def write_execution_sandbox_manifest(
    manifest: ExecutionSandboxManifest,
    output_path: Path,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(sandbox_manifest_to_json_safe_dict(manifest), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output
