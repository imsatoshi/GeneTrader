"""Metadata-only offline data gate for future backtest preflight wiring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bollinger_evolver.offline_preflight_cli import EXIT_OK, EXIT_PREFLIGHT_FAILED
from bollinger_evolver.preflight import build_offline_data_preflight_report


def _normalize_suffix(value: str) -> str:
    text = str(value).strip().lower()
    return text if text.startswith(".") else f".{text}"


def _issue(code: str, message: str, **details: Any) -> dict[str, Any]:
    payload = {"code": code, "message": message}
    payload.update(details)
    return payload


def build_backtest_offline_data_gate(
    root: str | Path,
    *,
    min_files: int = 1,
    max_total_size_bytes: int | None = None,
    required_suffixes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Build a deterministic metadata-only gate result for backtest readiness."""

    report = build_offline_data_preflight_report(root)
    report_dict = report.to_dict()
    issues = [dict(item) for item in report_dict.get("issues", []) if isinstance(item, dict)]
    warnings = [dict(item) for item in report_dict.get("warnings", []) if isinstance(item, dict)]
    datasets = report_dict.get("datasets") if isinstance(report_dict.get("datasets"), list) else []
    accepted_files = int(report_dict.get("accepted_files", 0) or 0)
    total_size_bytes = int(report_dict.get("total_size_bytes", 0) or 0)

    if accepted_files < int(min_files):
        issues.append(
            _issue(
                "min_files_not_met",
                "accepted file count is below required minimum",
                min_files=int(min_files),
                accepted_files=accepted_files,
            )
        )

    if max_total_size_bytes is not None and total_size_bytes > int(max_total_size_bytes):
        issues.append(
            _issue(
                "max_total_size_bytes_exceeded",
                "total metadata size exceeds configured maximum",
                max_total_size_bytes=int(max_total_size_bytes),
                total_size_bytes=total_size_bytes,
            )
        )

    required = sorted({_normalize_suffix(item) for item in (required_suffixes or [])})
    present = sorted(
        {
            _normalize_suffix(str(item.get("suffix") or item.get("file_type") or item.get("format")))
            for item in datasets
            if isinstance(item, dict)
        }
    )
    missing_suffixes = [suffix for suffix in required if suffix not in present]
    for suffix in missing_suffixes:
        issues.append(
            _issue(
                "required_suffix_missing",
                "required offline data suffix is missing",
                suffix=suffix,
            )
        )

    ok = bool(report.ok) and not issues
    gate_summary = {
        "accepted_files": accepted_files,
        "min_files": int(min_files),
        "total_size_bytes": total_size_bytes,
        "max_total_size_bytes": max_total_size_bytes,
        "required_suffixes": required,
        "present_suffixes": present,
        "missing_suffixes": missing_suffixes,
    }
    return json.loads(
        json.dumps(
            {
                "ok": ok,
                "exit_code": EXIT_OK if ok else EXIT_PREFLIGHT_FAILED,
                "report": report_dict,
                "gate_summary": gate_summary,
                "issues": issues,
                "warnings": warnings,
                "metadata": {
                    "source": "backtest_offline_data_gate",
                    "metadata_only": True,
                    "real_backtest_executed": False,
                },
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )


def run_backtest_offline_data_gate(
    root: str | Path,
    *,
    min_files: int = 1,
    max_total_size_bytes: int | None = None,
    required_suffixes: list[str] | tuple[str, ...] | None = None,
    fail_on_warning: bool = False,
) -> dict[str, Any]:
    """Run the metadata-only backtest offline data gate with an exit-code contract."""

    result = build_backtest_offline_data_gate(
        root,
        min_files=min_files,
        max_total_size_bytes=max_total_size_bytes,
        required_suffixes=required_suffixes,
    )
    warning_failed = bool(fail_on_warning and result["warnings"])
    result["ok"] = bool(result["ok"]) and not warning_failed
    result["exit_code"] = EXIT_OK if result["ok"] else EXIT_PREFLIGHT_FAILED
    result["metadata"]["fail_on_warning"] = bool(fail_on_warning)
    return json.loads(json.dumps(result, ensure_ascii=True, sort_keys=True))
