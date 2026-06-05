"""Read-only preflight checks for future real-backtest readiness."""

from __future__ import annotations

import importlib
import importlib.util
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.data_quality import evaluate_data_coverage_gate
from bollinger_evolver.evaluators import sanitize_mapping
from bollinger_evolver.ga.backtest_evaluation_adapter import BacktestEvaluationAdapter
from bollinger_evolver.ga.runner_cli import main as runner_cli_main
from bollinger_evolver.offline_paths import normalize_offline_relative_path, offline_path_sort_key


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
OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_NAME = "offline_data_preflight_report"
OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_VERSION = "1.0"
OFFLINE_DATA_PREFLIGHT_REPORT_GENERATED_BY = "bollinger_evolver"
OFFLINE_DATA_PREFLIGHT_REPORT_REQUIRED_KEYS = {
    "ok",
    "root",
    "scanned_files",
    "accepted_files",
    "rejected_files",
    "total_size_bytes",
    "summary",
    "datasets",
    "issues",
    "warnings",
    "metadata",
}
OFFLINE_DATA_PREFLIGHT_ISSUE_SEVERITIES = {"error", "warning"}


@dataclass(frozen=True)
class OfflineDataPreflightIssue:
    code: str
    message: str
    path: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OfflineDataPreflightIssue":
        return cls(
            code=str(payload.get("code", "")),
            message=str(payload.get("message", "")),
            path=payload.get("path") if payload.get("path") is None else str(payload.get("path")),
            severity=str(payload.get("severity", "error")),
        )


@dataclass(frozen=True)
class OfflineDataPreflightSummary:
    scanned_files: int
    accepted_files: int
    rejected_files: int
    total_size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned_files": self.scanned_files,
            "accepted_files": self.accepted_files,
            "rejected_files": self.rejected_files,
            "total_size_bytes": self.total_size_bytes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OfflineDataPreflightSummary":
        return cls(
            scanned_files=int(payload.get("scanned_files", 0) or 0),
            accepted_files=int(payload.get("accepted_files", 0) or 0),
            rejected_files=int(payload.get("rejected_files", 0) or 0),
            total_size_bytes=int(payload.get("total_size_bytes", 0) or 0),
        )


@dataclass(frozen=True)
class OfflineDataPreflightReport:
    ok: bool
    root: str
    scanned_files: int
    accepted_files: int
    rejected_files: int
    total_size_bytes: int
    schema_name: str = OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_NAME
    schema_version: str = OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_VERSION
    generated_by: str = OFFLINE_DATA_PREFLIGHT_REPORT_GENERATED_BY
    datasets: list[dict[str, Any]] = field(default_factory=list)
    issues: list[OfflineDataPreflightIssue] = field(default_factory=list)
    warnings: list[OfflineDataPreflightIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        metadata = sanitize_mapping(self.metadata)
        metadata.setdefault("contract_version", self.schema_version)
        summary = OfflineDataPreflightSummary(
            scanned_files=self.scanned_files,
            accepted_files=self.accepted_files,
            rejected_files=self.rejected_files,
            total_size_bytes=self.total_size_bytes,
        ).to_dict()
        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "generated_by": self.generated_by,
            "ok": self.ok,
            "root": self.root,
            "scanned_files": self.scanned_files,
            "accepted_files": self.accepted_files,
            "rejected_files": self.rejected_files,
            "total_size_bytes": self.total_size_bytes,
            "summary": summary,
            "datasets": [dict(item) for item in self.datasets],
            "issues": [issue.to_dict() for issue in self.issues],
            "warnings": [warning.to_dict() for warning in self.warnings],
            "metadata": metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OfflineDataPreflightReport":
        return cls(
            ok=bool(payload.get("ok")),
            root=str(payload.get("root", "")),
            scanned_files=int(payload.get("scanned_files", 0) or 0),
            accepted_files=int(payload.get("accepted_files", 0) or 0),
            rejected_files=int(payload.get("rejected_files", 0) or 0),
            total_size_bytes=int(payload.get("total_size_bytes", 0) or 0),
            schema_name=str(payload.get("schema_name", OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_NAME)),
            schema_version=str(
                payload.get("schema_version", OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_VERSION)
            ),
            generated_by=str(payload.get("generated_by", OFFLINE_DATA_PREFLIGHT_REPORT_GENERATED_BY)),
            datasets=[dict(item) for item in payload.get("datasets", []) if isinstance(item, Mapping)],
            issues=[
                OfflineDataPreflightIssue.from_dict(item)
                for item in payload.get("issues", [])
                if isinstance(item, Mapping)
            ],
            warnings=[
                OfflineDataPreflightIssue.from_dict(item)
                for item in payload.get("warnings", [])
                if isinstance(item, Mapping)
            ],
            metadata=dict(payload.get("metadata", {}) or {}),
        )

    def write_json_report(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")


def validate_offline_data_preflight_report_dict(
    data: Mapping[str, Any],
) -> list[OfflineDataPreflightIssue]:
    """Validate the lightweight offline preflight report contract."""

    issues: list[OfflineDataPreflightIssue] = []
    missing_keys = sorted(OFFLINE_DATA_PREFLIGHT_REPORT_REQUIRED_KEYS - set(data.keys()))
    for key in missing_keys:
        issues.append(
            OfflineDataPreflightIssue(
                code="missing_required_key",
                message=f"missing required report key: {key}",
                path=key,
            )
        )

    if "ok" in data and not isinstance(data.get("ok"), bool):
        issues.append(OfflineDataPreflightIssue(code="invalid_ok", message="ok must be bool", path="ok"))

    for key in ("scanned_files", "accepted_files", "rejected_files", "total_size_bytes"):
        if key in data and not isinstance(data.get(key), int):
            issues.append(
                OfflineDataPreflightIssue(
                    code="invalid_counter",
                    message=f"{key} must be int",
                    path=key,
                )
            )

    summary = data.get("summary")
    if "summary" in data:
        if not isinstance(summary, Mapping):
            issues.append(
                OfflineDataPreflightIssue(
                    code="invalid_summary",
                    message="summary must be mapping",
                    path="summary",
                )
            )
        else:
            for key in ("scanned_files", "accepted_files", "rejected_files", "total_size_bytes"):
                if not isinstance(summary.get(key), int):
                    issues.append(
                        OfflineDataPreflightIssue(
                            code="invalid_summary_counter",
                            message=f"summary.{key} must be int",
                            path=f"summary.{key}",
                        )
                    )

    for key in ("datasets", "issues", "warnings"):
        if key in data and not isinstance(data.get(key), list):
            issues.append(
                OfflineDataPreflightIssue(
                    code="invalid_list_field",
                    message=f"{key} must be list",
                    path=key,
                )
            )

    for collection_name in ("issues", "warnings"):
        collection = data.get(collection_name)
        if not isinstance(collection, list):
            continue
        for index, item in enumerate(collection):
            if not isinstance(item, Mapping):
                issues.append(
                    OfflineDataPreflightIssue(
                        code="invalid_issue_shape",
                        message=f"{collection_name}[{index}] must be mapping",
                        path=f"{collection_name}[{index}]",
                    )
                )
                continue
            severity = item.get("severity")
            if severity not in OFFLINE_DATA_PREFLIGHT_ISSUE_SEVERITIES:
                issues.append(
                    OfflineDataPreflightIssue(
                        code="invalid_issue_severity",
                        message="issue severity must be error or warning",
                        path=f"{collection_name}[{index}].severity",
                    )
                )

    datasets = data.get("datasets")
    if isinstance(datasets, list):
        for index, dataset in enumerate(datasets):
            if not isinstance(dataset, Mapping):
                issues.append(
                    OfflineDataPreflightIssue(
                        code="invalid_dataset_shape",
                        message=f"datasets[{index}] must be mapping",
                        path=f"datasets[{index}]",
                    )
                )
                continue
            required_dataset_keys = {"path", "relative_path", "suffix", "file_type", "size_bytes"}
            for key in sorted(required_dataset_keys - set(dataset.keys())):
                issues.append(
                    OfflineDataPreflightIssue(
                        code="missing_dataset_key",
                        message=f"missing dataset key: {key}",
                        path=f"datasets[{index}].{key}",
                    )
                )
            if "size_bytes" in dataset and not isinstance(dataset.get("size_bytes"), int):
                issues.append(
                    OfflineDataPreflightIssue(
                        code="invalid_dataset_size",
                        message="dataset size_bytes must be int",
                        path=f"datasets[{index}].size_bytes",
                    )
                )

    try:
        json.dumps(data, sort_keys=True)
    except TypeError as exc:
        issues.append(
            OfflineDataPreflightIssue(
                code="not_json_serializable",
                message=f"report contains non-JSON-serializable value: {type(exc).__name__}",
                path=None,
            )
        )

    return issues


def _offline_report_payload(report: OfflineDataPreflightReport | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report, OfflineDataPreflightReport):
        return report.to_dict()
    if isinstance(report, Mapping):
        return sanitize_mapping(report)
    raise ValueError("report_must_be_object")


def render_offline_data_preflight_report(
    report: OfflineDataPreflightReport | Mapping[str, Any],
    *,
    output_format: str = "text",
) -> str:
    """Render an offline data preflight report as deterministic text or Markdown."""

    payload = _offline_report_payload(report)
    normalized_format = output_format.strip().lower()
    if normalized_format not in {"text", "markdown"}:
        raise ValueError("unsupported_report_format")

    issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    datasets = payload.get("datasets") if isinstance(payload.get("datasets"), list) else []
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), Mapping) else {}
    coverage_matrix = (
        metadata.get("coverage_matrix")
        if isinstance(metadata.get("coverage_matrix"), Mapping)
        else None
    )
    status = "PASS" if payload.get("ok") else "FAIL"
    root = str(payload.get("root", "unknown"))
    scanned_files = int(payload.get("scanned_files", 0) or 0)
    accepted_files = int(payload.get("accepted_files", 0) or 0)
    rejected_files = int(payload.get("rejected_files", 0) or 0)

    if normalized_format == "markdown":
        lines = [
            "# Offline Data Preflight Report",
            "",
            "## Summary",
            f"- Status: `{status}`",
            f"- Root: `{root}`",
            f"- Scanned files: `{scanned_files}`",
            f"- Accepted files: `{accepted_files}`",
            f"- Rejected files: `{rejected_files}`",
            "",
            "## Issues",
        ]
        lines.extend(
            f"- `{item.get('code', 'unknown_error')}`: {item.get('message', 'unknown')}"
            for item in issues
            if isinstance(item, Mapping)
        )
        if not issues:
            lines.append("- none")
        lines.append("")
        lines.append("## Warnings")
        lines.extend(
            f"- `{item.get('code', 'unknown_warning')}`: {item.get('message', 'unknown')}"
            for item in warnings
            if isinstance(item, Mapping)
        )
        if not warnings:
            lines.append("- none")
        lines.append("")
        lines.append("## Coverage Matrix")
        if coverage_matrix and coverage_matrix.get("matrix"):
            timeframes = [str(item) for item in coverage_matrix.get("timeframes", [])]
            lines.append("| Pair | " + " | ".join(timeframes) + " |")
            lines.append("| --- | " + " | ".join("---" for _ in timeframes) + " |")
            for row in coverage_matrix.get("matrix", []):
                if not isinstance(row, Mapping):
                    continue
                cells = row.get("cells") if isinstance(row.get("cells"), list) else []
                statuses = [
                    str(cell.get("status", "missing")) if isinstance(cell, Mapping) else "missing"
                    for cell in cells
                ]
                lines.append(f"| {row.get('pair', 'unknown')} | " + " | ".join(statuses) + " |")
        else:
            lines.append("- no requirements coverage matrix")
        lines.append("")
        lines.append("## Datasets")
        lines.extend(
            f"- `{item.get('relative_path') or item.get('path')}`"
            for item in datasets
            if isinstance(item, Mapping)
        )
        if not datasets:
            lines.append("- none")
        return "\n".join(lines) + "\n"

    lines = [
        "Offline Data Preflight Report",
        f"status: {status}",
        f"root: {root}",
        f"scanned_files: {scanned_files}",
        f"accepted_files: {accepted_files}",
        f"rejected_files: {rejected_files}",
        "issues:",
    ]
    lines.extend(
        f"- {item.get('code', 'unknown_error')}: {item.get('message', 'unknown')}"
        for item in issues
        if isinstance(item, Mapping)
    )
    if not issues:
        lines.append("- none")
    lines.append("warnings:")
    lines.extend(
        f"- {item.get('code', 'unknown_warning')}: {item.get('message', 'unknown')}"
        for item in warnings
        if isinstance(item, Mapping)
    )
    if not warnings:
        lines.append("- none")
    lines.append("coverage_matrix:")
    if coverage_matrix and coverage_matrix.get("matrix"):
        timeframes = ", ".join(str(item) for item in coverage_matrix.get("timeframes", []))
        lines.append(f"- timeframes: {timeframes}")
        for row in coverage_matrix.get("matrix", []):
            if not isinstance(row, Mapping):
                continue
            statuses = []
            cells = row.get("cells") if isinstance(row.get("cells"), list) else []
            for cell in cells:
                if isinstance(cell, Mapping):
                    statuses.append(f"{cell.get('timeframe')}: {cell.get('status')}")
            lines.append(f"- {row.get('pair', 'unknown')}: {', '.join(statuses)}")
    else:
        lines.append("- no requirements coverage matrix")
    return "\n".join(lines) + "\n"


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


def _report_dataset_from_manifest_item(item: Mapping[str, Any]) -> dict[str, Any]:
    file_format = item.get("format")
    relative_path = normalize_offline_relative_path(item.get("path"))
    return {
        "path": relative_path,
        "relative_path": relative_path,
        "suffix": f".{file_format}" if file_format else None,
        "file_type": file_format,
        "format": file_format,
        "size_bytes": item.get("size_bytes"),
        "pair": item.get("pair"),
        "timeframe": item.get("timeframe"),
    }


def _issue_from_gate_error(error: Any) -> OfflineDataPreflightIssue:
    if isinstance(error, Mapping):
        code = str(error.get("code", "gate_error"))
        pair = error.get("pair")
        timeframe = error.get("timeframe")
        details = " ".join(str(item) for item in (pair, timeframe) if item)
        message = f"{code}: {details}" if details else code
        return OfflineDataPreflightIssue(code=code, message=message, path=None, severity="error")

    code = str(error)
    path = None
    message = code
    if code.startswith("datasets["):
        message = f"inventory_manifest_gate:{code}"
    return OfflineDataPreflightIssue(code=code, message=message, path=path, severity="error")


def _resolve_offline_data_requirements(
    requirements: Mapping[str, Any] | None,
    requirements_path: str | Path | None,
) -> Mapping[str, Any] | None:
    if requirements is not None and requirements_path is not None:
        raise ValueError("requirements_conflict")
    if requirements_path is None:
        return requirements

    from bollinger_evolver.data_gate import load_offline_data_requirements

    return load_offline_data_requirements(requirements_path)


def _unsupported_file_warnings(root_path: Path, accepted_paths: set[str]) -> list[OfflineDataPreflightIssue]:
    if not root_path.exists() or not root_path.is_dir():
        return []
    warnings: list[OfflineDataPreflightIssue] = []
    for path in sorted(item for item in root_path.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root_path).as_posix()
        if relative_path in accepted_paths:
            continue
        warnings.append(
            OfflineDataPreflightIssue(
                code="unsupported_file",
                message="unsupported file ignored by offline data inventory",
                path=relative_path,
                severity="warning",
            )
        )
    return warnings


def build_offline_data_preflight_report(
    root: str | Path,
    requirements: Mapping[str, Any] | None = None,
    requirements_path: str | Path | None = None,
) -> OfflineDataPreflightReport:
    """Build a deterministic metadata-only report for offline data preflight."""

    from bollinger_evolver.data_gate import run_inventory_manifest_gate
    from bollinger_evolver.data_gate import build_requirements_coverage_matrix
    from bollinger_evolver.data_gate import extract_data_gate_error_codes
    from bollinger_evolver.data_manifest import build_manifest_from_inventory
    from bollinger_evolver.offline_data import inventory_offline_data

    resolved_requirements = _resolve_offline_data_requirements(requirements, requirements_path)
    root_path = Path(root).expanduser().resolve()
    inventory = inventory_offline_data(root_path)
    manifest = build_manifest_from_inventory(inventory)
    gate = run_inventory_manifest_gate(manifest, requirements=resolved_requirements)
    coverage_matrix = (
        build_requirements_coverage_matrix(manifest, resolved_requirements)
        if resolved_requirements is not None
        else None
    )

    datasets = [
        _report_dataset_from_manifest_item(item)
        for item in manifest.get("datasets", [])
        if isinstance(item, Mapping)
    ]
    datasets = sorted(
        datasets,
        key=lambda item: offline_path_sort_key(item.get("relative_path") or ""),
    )
    accepted_paths = {str(item.get("relative_path")) for item in datasets}
    warnings = _unsupported_file_warnings(root_path, accepted_paths)
    issues = [
        OfflineDataPreflightIssue(
            code=str(code),
            message=str(code),
            path=None,
            severity="error",
        )
        for code in inventory.get("errors", [])
    ]
    issues.extend(_issue_from_gate_error(error) for error in gate.get("errors", []))
    issues = sorted(issues, key=lambda item: (item.severity, item.code, item.path or ""))
    warnings = sorted(warnings, key=lambda item: (item.severity, item.code, item.path or ""))

    accepted_files = len(datasets)
    rejected_files = len(warnings)
    scanned_files = accepted_files + rejected_files
    total_size_bytes = sum(
        int(item.get("size_bytes") or 0)
        for item in datasets
        if isinstance(item.get("size_bytes"), int)
    )

    return OfflineDataPreflightReport(
        ok=not issues and bool(gate.get("ok")),
        root=str(root_path),
        scanned_files=scanned_files,
        accepted_files=accepted_files,
        rejected_files=rejected_files,
        total_size_bytes=total_size_bytes,
        datasets=datasets,
        issues=issues,
        warnings=warnings,
        metadata={
            "source": "offline_data_preflight",
            "inventory_source": "metadata_only",
            "manifest_source": manifest.get("source"),
            "gate_ok": bool(gate.get("ok")),
            "error_codes": extract_data_gate_error_codes(list(gate.get("errors") or [])),
            "requirements": sanitize_mapping(resolved_requirements or {}),
            "coverage_matrix": coverage_matrix,
            "summary": OfflineDataPreflightSummary(
                scanned_files=scanned_files,
                accepted_files=accepted_files,
                rejected_files=rejected_files,
                total_size_bytes=total_size_bytes,
            ).to_dict(),
        },
    )


def run_offline_data_preflight(
    root: str | Path,
    requirements: Mapping[str, Any] | None = None,
    requirements_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run metadata inventory, manifest conversion, gate checks, and report shaping."""

    from bollinger_evolver.data_gate import run_inventory_manifest_gate
    from bollinger_evolver.data_gate import extract_data_gate_error_codes
    from bollinger_evolver.data_manifest import build_manifest_from_inventory
    from bollinger_evolver.offline_data import inventory_offline_data

    resolved_requirements = _resolve_offline_data_requirements(requirements, requirements_path)
    inventory = inventory_offline_data(root)
    manifest = build_manifest_from_inventory(inventory)
    gate = run_inventory_manifest_gate(manifest, requirements=resolved_requirements)
    report = build_offline_data_preflight_report(root, requirements=resolved_requirements)
    errors = list(inventory.get("errors") or []) + list(gate.get("errors") or [])
    error_codes = extract_data_gate_error_codes(errors)
    return sanitize_mapping(
        {
            "ok": not errors and bool(gate.get("ok")),
            "errors": errors,
            "error_codes": error_codes,
            "inventory": inventory,
            "manifest": manifest,
            "requirements": sanitize_mapping(resolved_requirements or {}),
            "gate": gate,
            "report": report.to_dict(),
        }
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
