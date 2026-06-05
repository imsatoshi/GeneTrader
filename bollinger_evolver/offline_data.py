"""Metadata-only local offline data inventory helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from bollinger_evolver.evaluators import sanitize_mapping
from bollinger_evolver.offline_paths import offline_path_sort_key


SUPPORTED_OFFLINE_DATA_SUFFIXES = (
    ".csv",
    ".json",
    ".json.gz",
    ".feather",
    ".parquet",
)
IGNORED_TEMP_SUFFIXES = (
    ".tmp",
    ".temp",
    ".bak",
    ".backup",
    ".old",
    ".swp",
)

_PAIR_TIMEFRAME_RE = re.compile(
    r"^(?P<base>[A-Za-z0-9]+)[_-](?P<quote>[A-Za-z0-9]+)[-_](?P<timeframe>\d+[mhdwM])$"
)
def _offline_data_format(path: Path) -> str | None:
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] == [".json", ".gz"]:
        return "json.gz"
    if suffixes and suffixes[-1] in SUPPORTED_OFFLINE_DATA_SUFFIXES:
        return suffixes[-1].lstrip(".")
    return None


def _data_stem(path: Path) -> str:
    name = path.name
    for suffix in sorted(SUPPORTED_OFFLINE_DATA_SUFFIXES, key=len, reverse=True):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _infer_pair_timeframe(path: Path) -> tuple[str | None, str | None]:
    match = _PAIR_TIMEFRAME_RE.match(_data_stem(path))
    if match is None:
        return None, None
    return (
        f"{match.group('base').upper()}/{match.group('quote').upper()}",
        match.group("timeframe").lower(),
    )


def _probe_file(path: Path, file_format: str, max_probe_bytes: int) -> dict[str, Any]:
    if max_probe_bytes <= 0:
        raise ValueError("max_probe_bytes_must_be_positive")
    return {
        "enabled": False,
        "format": file_format,
        "metadata_only": True,
        "max_probe_bytes": max_probe_bytes,
        "size_bytes": path.stat().st_size,
        "reason": "content_probe_disabled_metadata_only",
    }


def _is_hidden_or_temp_path(path: Path, root_path: Path) -> bool:
    try:
        relative_parts = path.relative_to(root_path).parts
    except ValueError:
        relative_parts = path.parts
    if any(part.startswith(".") for part in relative_parts):
        return True
    lowered_name = path.name.lower()
    return lowered_name.endswith(IGNORED_TEMP_SUFFIXES)


def inventory_offline_data(
    root: str | Path,
    *,
    max_files: int | None = None,
    include_ignored: bool = False,
    probe: bool = False,
    max_probe_bytes: int = 65_536,
) -> dict[str, Any]:
    """Return a stable metadata inventory without reading full market data files."""

    if max_files is not None and max_files <= 0:
        raise ValueError("max_files_must_be_positive")

    root_path = Path(root).expanduser().resolve()
    inventory: dict[str, Any] = {"root": str(root_path), "files": [], "warnings": []}
    if not root_path.exists():
        inventory["errors"] = ["root_not_found"]
        return sanitize_mapping(inventory)
    if not root_path.is_dir():
        inventory["errors"] = ["root_not_directory"]
        return sanitize_mapping(inventory)

    files: list[dict[str, Any]] = []
    ignored_files: list[dict[str, Any]] = []
    for path in root_path.rglob("*"):
        if path.is_symlink():
            warning = {
                "path": path.relative_to(root_path).as_posix(),
                "reason": "symlink_ignored",
            }
            inventory["warnings"].append(warning)
            if include_ignored:
                ignored_files.append(warning)
            continue
        if not path.is_file():
            continue
        relative_path = path.relative_to(root_path).as_posix()
        if _is_hidden_or_temp_path(path, root_path):
            ignored = {"path": relative_path, "reason": "hidden_or_temp_file"}
            if include_ignored:
                ignored_files.append(ignored)
            continue
        file_format = _offline_data_format(path)
        if file_format is None:
            if include_ignored:
                ignored_files.append({"path": relative_path, "reason": "unsupported_format"})
            continue
        pair, timeframe = _infer_pair_timeframe(path)
        item = {
            "path": relative_path,
            "format": file_format,
            "size_bytes": path.stat().st_size,
            "pair": pair,
            "timeframe": timeframe,
        }
        if probe:
            item["probe"] = _probe_file(path, file_format, max_probe_bytes)
        files.append(item)
        if max_files is not None and len(files) > max_files:
            inventory["warnings"].append(
                {"code": "too_many_files", "max_files": max_files, "scanned_files": len(files)}
            )
            files = files[:max_files]
            break

    inventory["files"] = sorted(files, key=lambda item: offline_path_sort_key(item["path"]))
    if include_ignored:
        inventory["ignored_files"] = sorted(
            ignored_files,
            key=lambda item: offline_path_sort_key(item["path"]),
        )
    return sanitize_mapping(inventory)


def summarize_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    """Return a compact summary for an offline inventory payload."""

    files = inventory.get("files") if isinstance(inventory, dict) else []
    if not isinstance(files, list):
        files = []
    parsed_files = [
        item
        for item in files
        if isinstance(item, dict) and item.get("pair") is not None and item.get("timeframe") is not None
    ]
    total_size_bytes = sum(
        int(item.get("size_bytes") or 0)
        for item in files
        if isinstance(item, dict) and isinstance(item.get("size_bytes"), int)
    )
    pairs = sorted(
        {str(item.get("pair")) for item in parsed_files if item.get("pair") is not None}
    )
    timeframes = sorted(
        {str(item.get("timeframe")) for item in parsed_files if item.get("timeframe") is not None}
    )
    return sanitize_mapping(
        {
            "file_count": len(files),
            "parsed_file_count": len(parsed_files),
            "unparsed_file_count": len(files) - len(parsed_files),
            "ignored_file_count": len(inventory.get("ignored_files", []))
            if isinstance(inventory, dict) and isinstance(inventory.get("ignored_files"), list)
            else 0,
            "total_size_bytes": total_size_bytes,
            "pairs": pairs,
            "timeframes": timeframes,
            "warnings_count": len(inventory.get("warnings", []))
            if isinstance(inventory, dict) and isinstance(inventory.get("warnings"), list)
            else 0,
        }
    )
