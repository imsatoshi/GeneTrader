"""Release-readiness audit helpers for offline data preflight."""

from __future__ import annotations

import importlib
import json
from typing import Any

from bollinger_evolver.offline_data_boundary import run_offline_data_boundary_audit
from bollinger_evolver.preflight import (
    OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_NAME,
    OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_VERSION,
)


_PUBLIC_APIS = (
    ("bollinger_evolver.offline_data", "inventory_offline_data"),
    ("bollinger_evolver.data_manifest", "build_manifest_from_inventory"),
    ("bollinger_evolver.data_gate", "run_inventory_manifest_gate"),
    ("bollinger_evolver.preflight", "build_offline_data_preflight_report"),
    ("bollinger_evolver.preflight", "run_offline_data_preflight"),
    ("bollinger_evolver.offline_preflight_cli", "run_offline_data_preflight_cli"),
    ("bollinger_evolver.offline_data_diff", "compare_offline_data_preflight_reports"),
    ("bollinger_evolver.offline_workflow", "run_offline_data_workflow_preflight"),
    ("bollinger_evolver.offline_backtest_gate", "run_backtest_offline_data_gate"),
    ("bollinger_evolver.offline_data_summary", "format_offline_data_preflight_summary"),
)


def _check(code: str, ok: bool, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "ok": bool(ok), "message": message, "details": details}


def _callable_available(module_name: str, name: str) -> bool:
    try:
        module = importlib.import_module(module_name)
        return callable(getattr(module, name))
    except (AttributeError, ModuleNotFoundError):
        return False


def run_offline_data_release_readiness_audit() -> dict[str, Any]:
    """Return a deterministic, import-safe readiness audit for offline data preflight."""

    checks: list[dict[str, Any]] = []
    for module_name, name in _PUBLIC_APIS:
        checks.append(
            _check(
                "public_api_callable",
                _callable_available(module_name, name),
                f"{module_name}.{name}",
                module=module_name,
                name=name,
            )
        )

    checks.append(
        _check(
            "schema_version_present",
            bool(OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_NAME and OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_VERSION),
            "offline data preflight report schema is present",
            schema_name=OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_NAME,
            schema_version=OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_VERSION,
        )
    )

    boundary = run_offline_data_boundary_audit()
    checks.append(
        _check(
            "metadata_only_boundary_valid",
            bool(boundary.get("ok")),
            "metadata-only boundary audit is valid",
            warning_count=len(boundary.get("warnings") or []),
        )
    )

    issues = [
        {"code": check["code"], "message": check["message"], "details": check["details"]}
        for check in checks
        if not check["ok"]
    ]
    result = {
        "ok": not issues,
        "checks": checks,
        "issues": issues,
        "metadata": {
            "source": "offline_data_release_readiness_audit",
            "metadata_only": True,
            "real_data_scanned": False,
            "schema_version": OFFLINE_DATA_PREFLIGHT_REPORT_SCHEMA_VERSION,
        },
    }
    return json.loads(json.dumps(result, ensure_ascii=True, sort_keys=True))
