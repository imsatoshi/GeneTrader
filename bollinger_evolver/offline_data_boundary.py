"""Boundary declarations for metadata-only offline data flows."""

from __future__ import annotations

import importlib
import json
from typing import Any


BOUNDARY_SCHEMA_VERSION = "offline_data_boundary.v1"
BOUNDARY_STATEMENT = (
    "metadata-only guarantee applies to the offline_data inventory, offline "
    "preflight report, CLI, and diff path; legacy manifest/gate content-read "
    "functions remain known legacy behavior"
)

_METADATA_ONLY_APIS: tuple[dict[str, Any], ...] = (
    {
        "name": "build_manifest_from_inventory",
        "module": "bollinger_evolver.data_manifest",
        "qualname": "build_manifest_from_inventory",
        "path": "bollinger_evolver/data_manifest.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "converts an inventory dictionary into manifest metadata",
    },
    {
        "name": "build_offline_data_preflight_report",
        "module": "bollinger_evolver.preflight",
        "qualname": "build_offline_data_preflight_report",
        "path": "bollinger_evolver/preflight.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "composes inventory metadata, manifest metadata, and inventory gate output",
    },
    {
        "name": "compare_offline_data_preflight_reports",
        "module": "bollinger_evolver.offline_data_diff",
        "qualname": "compare_offline_data_preflight_reports",
        "path": "bollinger_evolver/offline_data_diff.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "compares report dictionaries or report JSON strings without touching data files",
    },
    {
        "name": "format_offline_data_diff_summary",
        "module": "bollinger_evolver.offline_data_summary",
        "qualname": "format_offline_data_diff_summary",
        "path": "bollinger_evolver/offline_data_summary.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "formats diff metadata without touching data files",
    },
    {
        "name": "format_offline_data_preflight_summary",
        "module": "bollinger_evolver.offline_data_summary",
        "qualname": "format_offline_data_preflight_summary",
        "path": "bollinger_evolver/offline_data_summary.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "formats report metadata without touching data files",
    },
    {
        "name": "inventory_offline_data",
        "module": "bollinger_evolver.offline_data",
        "qualname": "inventory_offline_data",
        "path": "bollinger_evolver/offline_data.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "uses path, suffix, inferred labels, and file stat metadata only",
    },
    {
        "name": "normalize_offline_relative_path",
        "module": "bollinger_evolver.offline_paths",
        "qualname": "normalize_offline_relative_path",
        "path": "bollinger_evolver/offline_paths.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "normalizes path text only",
    },
    {
        "name": "run_backtest_offline_data_gate",
        "module": "bollinger_evolver.offline_backtest_gate",
        "qualname": "run_backtest_offline_data_gate",
        "path": "bollinger_evolver/offline_backtest_gate.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "checks offline data report metadata before future backtest wiring",
    },
    {
        "name": "build_backtest_offline_data_gate",
        "module": "bollinger_evolver.offline_backtest_gate",
        "qualname": "build_backtest_offline_data_gate",
        "path": "bollinger_evolver/offline_backtest_gate.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "builds a backtest gate from metadata report fields only",
    },
    {
        "name": "run_inventory_manifest_gate",
        "module": "bollinger_evolver.data_gate",
        "qualname": "run_inventory_manifest_gate",
        "path": "bollinger_evolver/data_gate.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "validates inventory manifest metadata and file existence/size only",
    },
    {
        "name": "run_offline_data_preflight",
        "module": "bollinger_evolver.preflight",
        "qualname": "run_offline_data_preflight",
        "path": "bollinger_evolver/preflight.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "runs the metadata inventory, inventory manifest, and inventory gate path",
    },
    {
        "name": "run_offline_data_release_readiness_audit",
        "module": "bollinger_evolver.offline_release",
        "qualname": "run_offline_data_release_readiness_audit",
        "path": "bollinger_evolver/offline_release.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "checks imports and schema metadata without scanning data directories",
    },
    {
        "name": "run_offline_data_preflight_cli",
        "module": "bollinger_evolver.offline_preflight_cli",
        "qualname": "run_offline_data_preflight_cli",
        "path": "bollinger_evolver/offline_preflight_cli.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "non_market_content_reads": ["report_json", "requirements_json"],
        "reason": "normal mode scans metadata only; diff mode reads explicit report JSON files",
    },
    {
        "name": "run_offline_data_workflow_preflight",
        "module": "bollinger_evolver.offline_workflow",
        "qualname": "run_offline_data_workflow_preflight",
        "path": "bollinger_evolver/offline_workflow.py",
        "boundary": "metadata_only",
        "market_data_content_read_allowed": False,
        "reason": "workflow adapter wraps offline preflight without default file writes",
    },
)

_LEGACY_CONTENT_READ_APIS: tuple[dict[str, Any], ...] = (
    {
        "name": "build_offline_data_manifest",
        "module": "bollinger_evolver.data_manifest",
        "qualname": "build_offline_data_manifest",
        "path": "bollinger_evolver/data_manifest.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open(", "read_text", "read_feather", "read_parquet"],
        "reason": "legacy manifest builder parses market data contents to summarize candle coverage",
    },
    {
        "name": "run_offline_data_gate",
        "module": "bollinger_evolver.data_gate",
        "qualname": "run_offline_data_gate",
        "path": "bollinger_evolver/data_gate.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open(", "read_text", "read_feather", "read_parquet"],
        "reason": "legacy gate checks market data schema by inspecting data file contents",
    },
    {
        "name": "_inspect_file_schema",
        "module": "bollinger_evolver.data_gate",
        "qualname": "_inspect_file_schema",
        "path": "bollinger_evolver/data_gate.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open(", "read_text", "read_feather", "read_parquet"],
        "reason": "legacy schema inspection reads representative rows or dataframe columns",
    },
    {
        "name": "parse_candles_from_file",
        "module": "bollinger_evolver.data_manifest",
        "qualname": "parse_candles_from_file",
        "path": "bollinger_evolver/data_manifest.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open(", "read_text", "read_feather", "read_parquet"],
        "reason": "legacy manifest loader dispatches to content parsers",
    },
)

_LEGACY_HELPERS: tuple[dict[str, Any], ...] = (
    {
        "name": "_parse_csv_file",
        "module": "bollinger_evolver.data_manifest",
        "qualname": "_parse_csv_file",
        "path": "bollinger_evolver/data_manifest.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open("],
        "reason": "legacy CSV candle parser",
    },
    {
        "name": "_parse_json_file",
        "module": "bollinger_evolver.data_manifest",
        "qualname": "_parse_json_file",
        "path": "bollinger_evolver/data_manifest.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["read_text"],
        "reason": "legacy JSON candle parser",
    },
    {
        "name": "_parse_jsonl_file",
        "module": "bollinger_evolver.data_manifest",
        "qualname": "_parse_jsonl_file",
        "path": "bollinger_evolver/data_manifest.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open("],
        "reason": "legacy JSONL candle parser",
    },
    {
        "name": "_parse_pandas_file",
        "module": "bollinger_evolver.data_manifest",
        "qualname": "_parse_pandas_file",
        "path": "bollinger_evolver/data_manifest.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["read_feather", "read_parquet"],
        "reason": "legacy pandas-backed data parser",
    },
    {
        "name": "_read_csv_columns",
        "module": "bollinger_evolver.data_gate",
        "qualname": "_read_csv_columns",
        "path": "bollinger_evolver/data_gate.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open("],
        "reason": "legacy CSV schema reader",
    },
    {
        "name": "_read_first_json_row",
        "module": "bollinger_evolver.data_gate",
        "qualname": "_read_first_json_row",
        "path": "bollinger_evolver/data_gate.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["read_text"],
        "reason": "legacy JSON schema reader",
    },
    {
        "name": "_read_first_jsonl_row",
        "module": "bollinger_evolver.data_gate",
        "qualname": "_read_first_jsonl_row",
        "path": "bollinger_evolver/data_gate.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["open("],
        "reason": "legacy JSONL schema reader",
    },
    {
        "name": "_read_pandas_columns",
        "module": "bollinger_evolver.data_gate",
        "qualname": "_read_pandas_columns",
        "path": "bollinger_evolver/data_gate.py",
        "boundary": "legacy_content_read_allowed",
        "tokens": ["read_feather", "read_parquet"],
        "reason": "legacy pandas schema reader",
    },
)


def _copy_entries(entries: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return [dict(item) for item in entries]


def _resolve_qualname(module_name: str, qualname: str) -> Any:
    value: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


def get_offline_data_metadata_only_boundary() -> dict[str, Any]:
    """Return the explicit metadata-only boundary contract."""

    apis = _copy_entries(_METADATA_ONLY_APIS)
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "statement": BOUNDARY_STATEMENT,
        "metadata_only_apis": apis,
        "metadata": {
            "api_count": len(apis),
            "guarantee_scope": "offline_data inventory / offline preflight report / CLI / diff path",
            "legacy_scope_excluded": True,
        },
    }


def get_legacy_content_read_allowlist() -> list[dict[str, Any]]:
    """Return known legacy content-read APIs without changing their behavior."""

    entries = (*_LEGACY_CONTENT_READ_APIS, *_LEGACY_HELPERS)
    return _copy_entries(tuple(sorted(entries, key=lambda item: (str(item["module"]), str(item["qualname"])))))


def validate_metadata_only_boundary() -> dict[str, Any]:
    """Validate that boundary declarations are stable and importable."""

    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    metadata_only_apis = get_offline_data_metadata_only_boundary()["metadata_only_apis"]
    legacy_content_read_apis = get_legacy_content_read_allowlist()

    seen: set[tuple[str, str]] = set()
    for item in metadata_only_apis:
        key = (str(item["module"]), str(item["qualname"]))
        if key in seen:
            issues.append({"code": "duplicate_metadata_only_api", "api": item["name"]})
        seen.add(key)
        try:
            value = _resolve_qualname(str(item["module"]), str(item["qualname"]))
        except (AttributeError, ModuleNotFoundError) as exc:
            issues.append(
                {
                    "code": "metadata_only_api_not_importable",
                    "api": item["name"],
                    "error": type(exc).__name__,
                }
            )
            continue
        if not callable(value):
            issues.append({"code": "metadata_only_api_not_callable", "api": item["name"]})
        if item.get("market_data_content_read_allowed") is not False:
            issues.append({"code": "metadata_only_api_allows_market_content_read", "api": item["name"]})

    if legacy_content_read_apis:
        warnings.append(
            {
                "code": "known_legacy_content_read_paths",
                "count": len(legacy_content_read_apis),
                "classification": "KNOWN_LEGACY_ALLOWED_READ",
            }
        )

    return {
        "ok": not issues,
        "metadata_only_apis": metadata_only_apis,
        "legacy_content_read_apis": legacy_content_read_apis,
        "issues": issues,
        "warnings": warnings,
        "metadata": {
            "schema_version": BOUNDARY_SCHEMA_VERSION,
            "statement": BOUNDARY_STATEMENT,
        },
    }


def run_offline_data_boundary_audit() -> dict[str, Any]:
    """Return a deterministic boundary audit payload."""

    result = validate_metadata_only_boundary()
    return json.loads(json.dumps(result, ensure_ascii=True, sort_keys=True))
