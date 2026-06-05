"""Deterministic comparison helpers for offline data preflight reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from bollinger_evolver.offline_paths import normalize_offline_relative_path, offline_path_sort_key
from bollinger_evolver.preflight import OfflineDataPreflightReport


def _report_dict(value: OfflineDataPreflightReport | Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, OfflineDataPreflightReport):
        return value.to_dict()
    if isinstance(value, str):
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise ValueError("report JSON must decode to an object")
        return payload
    if isinstance(value, Mapping):
        return dict(value)
    raise TypeError("report must be OfflineDataPreflightReport, mapping, or JSON string")


def _identity(dataset: Mapping[str, Any]) -> str:
    value = dataset.get("relative_path") or dataset.get("path") or ""
    return normalize_offline_relative_path(value)


def _project_dataset(dataset: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_path": normalize_offline_relative_path(dataset.get("relative_path") or dataset.get("path")),
        "path": normalize_offline_relative_path(dataset.get("path")),
        "suffix": dataset.get("suffix"),
        "file_type": dataset.get("file_type"),
        "format": dataset.get("format"),
        "size_bytes": dataset.get("size_bytes"),
        "pair": dataset.get("pair"),
        "timeframe": dataset.get("timeframe"),
    }


def _datasets_by_identity(report: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in report.get("datasets", []) or []:
        if not isinstance(item, Mapping):
            continue
        identity = _identity(item)
        if identity:
            result[identity] = _project_dataset(item)
    return result


def _summary(report: Mapping[str, Any]) -> dict[str, Any]:
    summary = report.get("summary")
    if isinstance(summary, Mapping):
        return dict(summary)
    return {
        "scanned_files": report.get("scanned_files", 0),
        "accepted_files": report.get("accepted_files", 0),
        "rejected_files": report.get("rejected_files", 0),
        "total_size_bytes": report.get("total_size_bytes", 0),
    }


@dataclass(frozen=True)
class OfflineDataPreflightDiff:
    ok: bool
    added_datasets: list[dict[str, Any]] = field(default_factory=list)
    removed_datasets: list[dict[str, Any]] = field(default_factory=list)
    changed_datasets: list[dict[str, Any]] = field(default_factory=list)
    unchanged_count: int = 0
    old_summary: dict[str, Any] = field(default_factory=dict)
    new_summary: dict[str, Any] = field(default_factory=dict)
    issues: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "added_datasets": [dict(item) for item in self.added_datasets],
            "removed_datasets": [dict(item) for item in self.removed_datasets],
            "changed_datasets": [dict(item) for item in self.changed_datasets],
            "unchanged_count": self.unchanged_count,
            "old_summary": dict(self.old_summary),
            "new_summary": dict(self.new_summary),
            "issues": [dict(item) for item in self.issues],
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def compare_offline_data_preflight_reports(
    old: OfflineDataPreflightReport | Mapping[str, Any] | str,
    new: OfflineDataPreflightReport | Mapping[str, Any] | str,
) -> OfflineDataPreflightDiff:
    old_report = _report_dict(old)
    new_report = _report_dict(new)
    old_datasets = _datasets_by_identity(old_report)
    new_datasets = _datasets_by_identity(new_report)
    old_keys = set(old_datasets)
    new_keys = set(new_datasets)

    added = [new_datasets[key] for key in sorted(new_keys - old_keys, key=offline_path_sort_key)]
    removed = [old_datasets[key] for key in sorted(old_keys - new_keys, key=offline_path_sort_key)]
    changed: list[dict[str, Any]] = []
    unchanged_count = 0

    for key in sorted(old_keys & new_keys, key=offline_path_sort_key):
        old_item = old_datasets[key]
        new_item = new_datasets[key]
        changed_fields = [
            field
            for field in ("size_bytes", "suffix", "file_type")
            if old_item.get(field) != new_item.get(field)
        ]
        if changed_fields:
            changed.append(
                {
                    "relative_path": key,
                    "changed_fields": changed_fields,
                    "old": old_item,
                    "new": new_item,
                }
            )
        else:
            unchanged_count += 1

    issues: list[dict[str, Any]] = []
    return OfflineDataPreflightDiff(
        ok=True,
        added_datasets=added,
        removed_datasets=removed,
        changed_datasets=changed,
        unchanged_count=unchanged_count,
        old_summary=_summary(old_report),
        new_summary=_summary(new_report),
        issues=issues,
        metadata={
            "source": "offline_data_preflight_diff",
            "old_dataset_count": len(old_datasets),
            "new_dataset_count": len(new_datasets),
        },
    )
