"""Read-only preflight checks for future real-backtest readiness."""

from __future__ import annotations

import importlib
import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.data_quality import evaluate_data_coverage_gate
from bollinger_evolver.evaluators import sanitize_mapping
from bollinger_evolver.ga.backtest_evaluation_adapter import BacktestEvaluationAdapter
from bollinger_evolver.ga.runner_cli import main as runner_cli_main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".runtime" / "bollinger_evolver" / "preflight"
SENSITIVE_KEYWORDS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "jwt",
    "token",
    "private_key",
    "mnemonic",
    "webhook",
)
PLACEHOLDER_MARKERS = (
    "change_me",
    "placeholder",
    "your_",
    "your-",
    "example",
    "dummy",
    "sample",
    "redacted",
    "<redacted>",
    "replace_me",
    "fake",
    "test-",
    "test_",
)
LIVE_FLAG_KEYS = {
    "live",
    "live_trading",
    "trading_enabled",
    "trade_enabled",
    "real_trading",
}
RUNNER_FORBIDDEN_ARGS = (
    "--allow-real-backtest",
    "--live",
    "--api-key",
    "--secret",
)


def _resolve_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return sanitize_mapping(value)
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _normalize_status(status: str) -> str:
    status_upper = str(status).upper()
    if status_upper in {"PASS", "WARN", "FAIL", "SKIP"}:
        return status_upper
    return "FAIL"


def _check_entry(
    check_id: str,
    status: str,
    message: str,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": _normalize_status(status),
        "message": message,
        "evidence": sanitize_mapping(evidence or {}),
    }


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key).lower()
    return any(marker in normalized for marker in SENSITIVE_KEYWORDS)


def _is_placeholder_value(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    lowered = text.lower()
    if lowered in {"none", "null", "n/a"}:
        return True
    if lowered.startswith("${") and lowered.endswith("}"):
        return False
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def _scan_sensitive_values(value: Any, prefix: str = "") -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if _is_sensitive_key(str(key)):
                if not _is_placeholder_value(child):
                    matches.append({"key": next_prefix, "reason": "real_looking_secret"})
                continue
            matches.extend(_scan_sensitive_values(child, next_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            matches.extend(_scan_sensitive_values(child, next_prefix))
    return matches


def _scan_live_flags(value: Any, prefix: str = "") -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    if not isinstance(value, Mapping):
        return matches

    for key, child in value.items():
        normalized_key = str(key).lower()
        next_prefix = f"{prefix}.{key}" if prefix else str(key)
        if normalized_key == "dry_run" and child is False:
            matches.append({"key": next_prefix, "reason": "dry_run_disabled"})
        elif normalized_key in {"runmode", "run_mode"} and str(child).lower() in {
            "live",
            "real",
            "production",
            "prod",
        }:
            matches.append({"key": next_prefix, "reason": "live_runmode"})
        elif normalized_key in LIVE_FLAG_KEYS and bool(child):
            matches.append({"key": next_prefix, "reason": "live_flag_enabled"})

        if isinstance(child, Mapping):
            matches.extend(_scan_live_flags(child, next_prefix))
        elif isinstance(child, list):
            for index, item in enumerate(child):
                if isinstance(item, Mapping):
                    matches.extend(_scan_live_flags(item, f"{next_prefix}[{index}]"))
    return matches


def _load_json_mapping(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be an object")
    return data


def _import_strategy_module(strategy_name: str, strategy_path: Path) -> Any:
    strategy_file = strategy_path / f"{strategy_name}.py"
    if not strategy_file.exists():
        raise FileNotFoundError(strategy_file)
    spec = importlib.util.spec_from_file_location(
        f"bollinger_preflight_{strategy_name}",
        strategy_file,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to build import spec for {strategy_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _check_python_runtime() -> dict[str, Any]:
    return _check_entry(
        "check_python_runtime",
        "PASS",
        "python_runtime_available",
        {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
    )


def _check_freqtrade_import() -> dict[str, Any]:
    try:
        importlib.import_module("freqtrade")
    except ModuleNotFoundError as exc:
        missing_name = str(exc.name or "")
        if missing_name == "freqtrade" or "freqtrade" in str(exc).lower():
            return _check_entry(
                "check_freqtrade_import",
                "WARN",
                "freqtrade_not_installed",
                {"module": "freqtrade"},
            )
        return _check_entry(
            "check_freqtrade_import",
            "FAIL",
            "freqtrade_dependency_missing",
            {"module": exc.name or "unknown"},
        )
    except Exception as exc:  # pragma: no cover - defensive
        return _check_entry(
            "check_freqtrade_import",
            "FAIL",
            "freqtrade_import_failed",
            {"error_type": type(exc).__name__},
        )

    return _check_entry(
        "check_freqtrade_import",
        "PASS",
        "freqtrade_import_ok",
        {"module": "freqtrade"},
    )


def _check_bollinger_strategy_import(strategy_name: str, strategy_path: Path) -> dict[str, Any]:
    try:
        _import_strategy_module(strategy_name, strategy_path)
    except FileNotFoundError:
        return _check_entry(
            "check_bollinger_strategy_import",
            "FAIL",
            "strategy_file_missing",
            {"strategy_name": strategy_name, "strategy_path": str(strategy_path)},
        )
    except ModuleNotFoundError as exc:
        missing_name = str(exc.name or "")
        if missing_name.startswith("freqtrade") or "freqtrade" in str(exc).lower():
            return _check_entry(
                "check_bollinger_strategy_import",
                "WARN",
                "strategy_import_blocked_by_missing_freqtrade",
                {"strategy_name": strategy_name},
            )
        return _check_entry(
            "check_bollinger_strategy_import",
            "FAIL",
            "strategy_dependency_missing",
            {"missing_module": exc.name or "unknown"},
        )
    except Exception as exc:  # pragma: no cover - defensive
        return _check_entry(
            "check_bollinger_strategy_import",
            "FAIL",
            "strategy_import_failed",
            {"error_type": type(exc).__name__},
        )

    return _check_entry(
        "check_bollinger_strategy_import",
        "PASS",
        "strategy_import_ok",
        {"strategy_name": strategy_name},
    )


def _check_config_state(config_path: Path | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], bool, bool]:
    if config_path is None:
        return (
            _check_entry("check_config_exists", "WARN", "config_not_provided", {}),
            _check_entry("check_config_secret_scan", "WARN", "config_not_provided", {}),
            _check_entry("check_config_no_live_flags", "WARN", "config_not_provided", {}),
            False,
            False,
        )

    if not config_path.exists():
        return (
            _check_entry(
                "check_config_exists",
                "WARN",
                "config_not_found",
                {"config_path": str(config_path)},
            ),
            _check_entry("check_config_secret_scan", "WARN", "config_not_found", {}),
            _check_entry("check_config_no_live_flags", "WARN", "config_not_found", {}),
            False,
            False,
        )

    try:
        config_data = _load_json_mapping(config_path)
    except Exception as exc:
        fail = _check_entry(
            "check_config_exists",
            "FAIL",
            "config_invalid_json",
            {"config_path": str(config_path), "error_type": type(exc).__name__},
        )
        return (
            fail,
            _check_entry("check_config_secret_scan", "FAIL", "config_invalid_json", {}),
            _check_entry("check_config_no_live_flags", "FAIL", "config_invalid_json", {}),
            True,
            False,
        )

    exists_check = _check_entry(
        "check_config_exists",
        "PASS",
        "config_present",
        {"config_path": str(config_path)},
    )
    secret_matches = _scan_sensitive_values(config_data)
    live_matches = _scan_live_flags(config_data)

    if secret_matches:
        secret_check = _check_entry(
            "check_config_secret_scan",
            "FAIL",
            "config_contains_real_looking_secret",
            {"matched_keys": [match["key"] for match in secret_matches]},
        )
    else:
        secret_check = _check_entry(
            "check_config_secret_scan",
            "PASS",
            "config_secret_scan_ok",
            {},
        )

    if live_matches:
        live_check = _check_entry(
            "check_config_no_live_flags",
            "FAIL",
            "config_contains_live_trading_flag",
            {"matched_keys": [match["key"] for match in live_matches]},
        )
    else:
        live_check = _check_entry(
            "check_config_no_live_flags",
            "PASS",
            "config_no_live_flags",
            {},
        )

    return (
        exists_check,
        secret_check,
        live_check,
        True,
        secret_check["status"] == "PASS" and live_check["status"] == "PASS",
    )


def _check_generated_strategy_dir(path: Path) -> tuple[dict[str, Any], bool]:
    parent = path.parent
    created_dir = False
    probe_path: Path | None = None
    try:
        if not path.exists():
            parent.mkdir(parents=True, exist_ok=True)
            path.mkdir(parents=True, exist_ok=False)
            created_dir = True
        elif not path.is_dir():
            return (
                _check_entry(
                    "check_generated_strategy_dir",
                    "FAIL",
                    "generated_strategy_dir_not_directory",
                    {"path": str(path)},
                ),
                False,
            )

        probe_path = path / ".preflight_probe"
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink()
    except Exception as exc:
        if probe_path is not None and probe_path.exists():
            probe_path.unlink(missing_ok=True)
        if created_dir and path.exists():
            path.rmdir()
        return (
            _check_entry(
                "check_generated_strategy_dir",
                "FAIL",
                "generated_strategy_dir_not_writable",
                {"path": str(path), "error_type": type(exc).__name__},
            ),
            False,
        )

    if created_dir and path.exists():
        path.rmdir()
    return (
        _check_entry(
            "check_generated_strategy_dir",
            "PASS",
            "generated_strategy_dir_ready",
            {"path": str(path)},
        ),
        True,
    )


def _check_data_manifest_state(
    data_manifest_path: Path | None,
) -> tuple[dict[str, Any], bool]:
    if data_manifest_path is None:
        return (
            _check_entry(
                "check_data_manifest_gate",
                "WARN",
                "data_manifest_not_provided",
                {},
            ),
            False,
        )

    if not data_manifest_path.exists():
        return (
            _check_entry(
                "check_data_manifest_gate",
                "FAIL",
                "data_manifest_not_found",
                {"data_manifest_path": str(data_manifest_path)},
            ),
            False,
        )

    try:
        manifest = _load_json_mapping(data_manifest_path)
    except Exception as exc:
        return (
            _check_entry(
                "check_data_manifest_gate",
                "FAIL",
                "data_manifest_invalid_json",
                {"error_type": type(exc).__name__},
            ),
            False,
        )

    gate = evaluate_data_coverage_gate(manifest)
    if gate["status"] == "PASS":
        return (
            _check_entry(
                "check_data_manifest_gate",
                "PASS",
                "data_quality_gate_ok",
                {
                    "status": gate["status"],
                    "checked_pairs": gate["checked_pairs"],
                    "checked_timeframes": gate["checked_timeframes"],
                },
            ),
            True,
        )
    if gate["status"] == "WARN":
        return (
            _check_entry(
                "check_data_manifest_gate",
                "WARN",
                "data_quality_gate_warn",
                {
                    "warnings": gate["warnings"],
                },
            ),
            True,
        )
    return (
        _check_entry(
            "check_data_manifest_gate",
            "FAIL",
            "data_quality_gate_failed",
            {
                "fail_reasons": gate["fail_reasons"],
            },
        ),
        False,
    )


def _check_backtest_adapter_default_disabled() -> tuple[dict[str, Any], bool]:
    default = BacktestEvaluationAdapter.__init__.__defaults__
    signature_default = importlib.import_module("inspect").signature(
        BacktestEvaluationAdapter.__init__
    ).parameters["allow_real_backtest"].default
    if default is None:
        default = ()
    passed = signature_default is False
    return (
        _check_entry(
            "check_backtest_adapter_default_disabled",
            "PASS" if passed else "FAIL",
            "real_backtest_default_disabled" if passed else "real_backtest_default_not_disabled",
            {"default": bool(signature_default)},
        ),
        passed,
    )


def _check_runner_cli_rejects_live_args() -> tuple[dict[str, Any], bool]:
    results: list[dict[str, Any]] = []
    passed = True
    for forbidden in RUNNER_FORBIDDEN_ARGS:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = runner_cli_main([forbidden, "placeholder"] if forbidden in {"--api-key", "--secret"} else [forbidden])
        item_ok = code == 2 and "unsupported_live_or_secret_argument" in stderr.getvalue()
        passed = passed and item_ok
        results.append({"arg": forbidden, "code": code, "rejected": item_ok})
    return (
        _check_entry(
            "check_runner_cli_rejects_live_args",
            "PASS" if passed else "FAIL",
            "runner_cli_live_args_rejected" if passed else "runner_cli_live_args_not_rejected",
            {"results": results},
        ),
        passed,
    )


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "FAIL" in statuses:
        return "BLOCKED"
    if "WARN" in statuses:
        return "WARN"
    return "READY"


def _build_next_steps(
    *,
    freqtrade_available: bool,
    strategy_import_ok: bool,
    config_present: bool,
    config_safe: bool,
    generated_strategy_dir_ok: bool,
    data_quality_gate_ok: bool,
    real_backtest_default_disabled: bool,
    runner_cli_live_args_rejected: bool,
    data_manifest_path: Path | None,
) -> list[str]:
    next_steps: list[str] = []
    if not freqtrade_available:
        next_steps.append("Install Freqtrade into the active Python environment before real backtest execution.")
    if not strategy_import_ok:
        next_steps.append("Resolve BollingerResonanceStrategy import issues in a Freqtrade-enabled environment.")
    if not config_present:
        next_steps.append("Provide a safe Freqtrade config path before real backtest execution.")
    elif not config_safe:
        next_steps.append("Replace live-looking secrets or live-trading flags in the provided config.")
    if not generated_strategy_dir_ok:
        next_steps.append("Fix generated strategy directory permissions before writing generated strategies.")
    if data_manifest_path is None:
        next_steps.append("Provide a data manifest before attempting any real backtest.")
    elif not data_quality_gate_ok:
        next_steps.append("Repair or replace the provided data manifest until the data quality gate passes.")
    if not real_backtest_default_disabled:
        next_steps.append("Restore allow_real_backtest=False as the default safety boundary.")
    if not runner_cli_live_args_rejected:
        next_steps.append("Restore runner CLI rejection for live/secret arguments before any real backtest.")
    return next_steps


def _write_reports(result: Mapping[str, Any], output_dir: Path) -> tuple[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"backtest_preflight_{stamp}.json"
    markdown_path = output_dir / f"backtest_preflight_{stamp}.md"

    safe_result = sanitize_mapping(result)
    json_path.write_text(json.dumps(safe_result, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Backtest Readiness Preflight",
        "",
        "## Status",
        safe_result["status"],
        "",
        "## Checks",
    ]
    for check in safe_result["checks"]:
        lines.append(f"- `{check['id']}`: {check['status']} - {check['message']}")
    lines.extend(
        [
            "",
            "## Blocked Reasons",
        ]
    )
    if safe_result["blocked_reasons"]:
        lines.extend(f"- {reason}" for reason in safe_result["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Warnings",
        ]
    )
    if safe_result["warnings"]:
        lines.extend(f"- {warning}" for warning in safe_result["warnings"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Next Steps",
        ]
    )
    if safe_result["next_steps"]:
        lines.extend(f"- {step}" for step in safe_result["next_steps"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "- real backtest not executed",
            "- hyperopt not executed",
            "- no exchange connection",
            "- no secrets written",
        ]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(json_path), str(markdown_path)


def run_backtest_preflight(
    config_path: str | None = None,
    strategy_name: str = "BollingerResonanceStrategy",
    strategy_path: str = "user_data/strategies",
    generated_strategy_dir: str = "user_data/strategies/generated",
    data_manifest_path: str | None = None,
    output_dir: str | None = ".runtime/bollinger_evolver/preflight",
    write_report: bool = True,
) -> dict[str, Any]:
    """Run a read-only readiness check for future real backtesting."""

    resolved_strategy_path = _resolve_path(strategy_path) or PROJECT_ROOT / "user_data" / "strategies"
    resolved_generated_dir = _resolve_path(generated_strategy_dir) or PROJECT_ROOT / "user_data" / "strategies" / "generated"
    resolved_config_path = _resolve_path(config_path)
    resolved_manifest_path = _resolve_path(data_manifest_path)

    checks: list[dict[str, Any]] = []
    checks.append(_check_python_runtime())

    freqtrade_check = _check_freqtrade_import()
    checks.append(freqtrade_check)
    freqtrade_available = freqtrade_check["status"] == "PASS"

    strategy_check = _check_bollinger_strategy_import(strategy_name, resolved_strategy_path)
    checks.append(strategy_check)
    strategy_import_ok = strategy_check["status"] == "PASS"

    config_exists_check, config_secret_check, config_live_check, config_present, config_safe = _check_config_state(
        resolved_config_path
    )
    checks.extend([config_exists_check, config_secret_check, config_live_check])

    dir_check, generated_strategy_dir_ok = _check_generated_strategy_dir(resolved_generated_dir)
    checks.append(dir_check)

    data_check, data_quality_gate_ok = _check_data_manifest_state(resolved_manifest_path)
    checks.append(data_check)

    adapter_check, real_backtest_default_disabled = _check_backtest_adapter_default_disabled()
    checks.append(adapter_check)

    runner_cli_check, runner_cli_live_args_rejected = _check_runner_cli_rejects_live_args()
    checks.append(runner_cli_check)

    status = _overall_status(checks)
    blocked_reasons = [check["message"] for check in checks if check["status"] == "FAIL"]
    warnings = [check["message"] for check in checks if check["status"] == "WARN"]
    next_steps = _build_next_steps(
        freqtrade_available=freqtrade_available,
        strategy_import_ok=strategy_import_ok,
        config_present=config_present,
        config_safe=config_safe,
        generated_strategy_dir_ok=generated_strategy_dir_ok,
        data_quality_gate_ok=data_quality_gate_ok,
        real_backtest_default_disabled=real_backtest_default_disabled,
        runner_cli_live_args_rejected=runner_cli_live_args_rejected,
        data_manifest_path=resolved_manifest_path,
    )

    result: dict[str, Any] = {
        "status": status,
        "readiness": {
            "freqtrade_available": freqtrade_available,
            "strategy_import_ok": strategy_import_ok,
            "config_present": config_present,
            "config_safe": config_safe,
            "generated_strategy_dir_ok": generated_strategy_dir_ok,
            "data_quality_gate_ok": data_quality_gate_ok,
            "real_backtest_default_disabled": real_backtest_default_disabled,
            "runner_cli_live_args_rejected": runner_cli_live_args_rejected,
        },
        "checks": checks,
        "blocked_reasons": blocked_reasons,
        "warnings": warnings,
        "next_steps": next_steps,
        "report_path": None,
        "report_markdown_path": None,
        "readOnly": True,
    }

    if write_report and output_dir is not None:
        resolved_output_dir = _resolve_path(output_dir) or DEFAULT_OUTPUT_DIR
        report_path, markdown_path = _write_reports(result, resolved_output_dir)
        result["report_path"] = report_path
        result["report_markdown_path"] = markdown_path

    return sanitize_mapping(result)
