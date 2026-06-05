"""Static guard for offline data metadata-only and legacy read boundaries."""

from __future__ import annotations

import ast
import importlib
import inspect
import unittest
from pathlib import Path
from typing import Any

from bollinger_evolver.offline_data_boundary import (
    get_legacy_content_read_allowlist,
    get_offline_data_metadata_only_boundary,
)


FORBIDDEN_TOKENS = (
    "read_text",
    "read_bytes",
    "open(",
    "read_csv",
    "json.load",
    "read_json",
    "parquet",
    "pyarrow",
    "feather",
    "gzip.open",
    "shutil.rmtree",
    "os.remove",
    "unlink",
    "git add",
    "git commit",
    "git reset",
    "git stash",
)

MARKET_DATA_READ_TOKENS = (
    "read_text",
    "read_bytes",
    "open(",
    "read_csv",
    "read_json",
    "gzip.open",
    "shutil.rmtree",
    "os.remove",
    "unlink",
)

SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _resolve_qualname(module_name: str, qualname: str) -> Any:
    value: Any = importlib.import_module(module_name)
    for part in qualname.split("."):
        value = getattr(value, part)
    return value


def _function_ranges(source: str) -> dict[str, tuple[int, int]]:
    tree = ast.parse(source)
    ranges: dict[str, tuple[int, int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ranges[node.name] = (node.lineno, int(getattr(node, "end_lineno", node.lineno)))
    return ranges


def _owner_for_line(ranges: dict[str, tuple[int, int]], line_number: int) -> str | None:
    owners = [
        (name, start, end)
        for name, (start, end) in ranges.items()
        if start <= line_number <= end
    ]
    if not owners:
        return None
    return sorted(owners, key=lambda item: item[1], reverse=True)[0][0]


def _token_hits(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    ranges = _function_ranges(source)
    hits: list[dict[str, Any]] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        for token in FORBIDDEN_TOKENS:
            if token in line:
                hits.append(
                    {
                        "path": path.relative_to(SOURCE_ROOT).as_posix(),
                        "line": line_number,
                        "owner": _owner_for_line(ranges, line_number),
                        "token": token,
                        "text": line.strip(),
                    }
                )
    return hits


def _is_format_suffix_hit(hit: dict[str, Any]) -> bool:
    if hit["token"] not in {"feather", "parquet"}:
        return False
    text = str(hit["text"])
    return "read_" not in text


class TestOfflineDataForbiddenApiStaticGuard(unittest.TestCase):
    def test_metadata_only_public_functions_have_no_direct_market_content_reads(self) -> None:
        boundary = get_offline_data_metadata_only_boundary()
        failures: list[str] = []
        for item in boundary["metadata_only_apis"]:
            value = _resolve_qualname(item["module"], item["qualname"])
            source = inspect.getsource(value)
            for token in MARKET_DATA_READ_TOKENS:
                if token in source:
                    failures.append(
                        f"NEW_FORBIDDEN_READ {item['module']}:{item['qualname']} token={token}"
                    )

        self.assertEqual(failures, [])

    def test_known_legacy_content_reads_are_explicitly_allowlisted(self) -> None:
        legacy_allowlist = {
            (item["path"].replace("\\", "/").removeprefix("bollinger_evolver/"), item["qualname"])
            for item in get_legacy_content_read_allowlist()
        }
        non_market_allowed = {
            ("data_gate.py", "load_offline_data_requirements"),
            ("data_manifest.py", "load_offline_data_manifest"),
        }
        failures: list[str] = []
        known: list[str] = []

        for relative_path in ("data_gate.py", "data_manifest.py"):
            for hit in _token_hits(SOURCE_ROOT / relative_path):
                key = (relative_path, hit["owner"])
                if _is_format_suffix_hit(hit):
                    continue
                if key in legacy_allowlist:
                    known.append(
                        "KNOWN_LEGACY_ALLOWED_READ "
                        f"{relative_path}:{hit['line']} owner={hit['owner']} token={hit['token']}"
                    )
                    continue
                if key in non_market_allowed:
                    continue
                failures.append(
                    "NEW_FORBIDDEN_READ "
                    f"{relative_path}:{hit['line']} owner={hit['owner']} token={hit['token']}"
                )

        self.assertGreater(known, [])
        self.assertEqual(failures, [])

    def test_report_json_reads_are_non_market_allowlisted(self) -> None:
        allowed = {
            ("offline_data_diff.py", "_report_dict"),
            ("offline_preflight_cli.py", "_load_report_json"),
        }
        failures: list[str] = []
        for relative_path in ("offline_data_diff.py", "offline_preflight_cli.py"):
            for hit in _token_hits(SOURCE_ROOT / relative_path):
                if _is_format_suffix_hit(hit):
                    continue
                if (relative_path, hit["owner"]) in allowed:
                    continue
                failures.append(
                    "NEW_FORBIDDEN_READ "
                    f"{relative_path}:{hit['line']} owner={hit['owner']} token={hit['token']}"
                )

        self.assertEqual(failures, [])

    def test_offline_inventory_module_only_uses_format_suffix_tokens(self) -> None:
        failures: list[str] = []
        for hit in _token_hits(SOURCE_ROOT / "offline_data.py"):
            if _is_format_suffix_hit(hit):
                continue
            failures.append(
                "NEW_FORBIDDEN_READ "
                f"offline_data.py:{hit['line']} owner={hit['owner']} token={hit['token']}"
            )

        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
