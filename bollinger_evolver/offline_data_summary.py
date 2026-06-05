"""Human-readable metadata-only summaries for offline data audits."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from bollinger_evolver.offline_data_diff import OfflineDataPreflightDiff
from bollinger_evolver.offline_paths import normalize_offline_relative_path, offline_path_sort_key
from bollinger_evolver.preflight import OfflineDataPreflightReport


def _report_payload(report: OfflineDataPreflightReport | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(report, OfflineDataPreflightReport):
        return report.to_dict()
    if isinstance(report, Mapping):
        return dict(report)
    raise TypeError("report must be an OfflineDataPreflightReport or mapping")


def _diff_payload(diff: OfflineDataPreflightDiff | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(diff, OfflineDataPreflightDiff):
        return diff.to_dict()
    if isinstance(diff, Mapping):
        return dict(diff)
    raise TypeError("diff must be an OfflineDataPreflightDiff or mapping")


def _suffix_counts(datasets: list[Any]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for item in datasets:
        if not isinstance(item, Mapping):
            continue
        suffix = item.get("suffix") or item.get("file_type") or item.get("format") or "unknown"
        suffix_text = str(suffix)
        if suffix_text and not suffix_text.startswith("."):
            suffix_text = f".{suffix_text}"
        counts[suffix_text or "unknown"] += 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def format_offline_data_preflight_summary(
    report: OfflineDataPreflightReport | Mapping[str, Any],
    *,
    include_datasets: bool = False,
    max_datasets: int = 20,
) -> str:
    """Render a deterministic metadata-only preflight summary."""

    payload = _report_payload(report)
    datasets = payload.get("datasets") if isinstance(payload.get("datasets"), list) else []
    issues = payload.get("issues") if isinstance(payload.get("issues"), list) else []
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    status = "PASS" if payload.get("ok") else "FAIL"
    lines = [
        "Offline Data Preflight Summary",
        f"status: {status}",
        f"scanned_files: {int(payload.get('scanned_files', 0) or 0)}",
        f"accepted_files: {int(payload.get('accepted_files', 0) or 0)}",
        f"rejected_files: {int(payload.get('rejected_files', 0) or 0)}",
        f"total_size_bytes: {int(payload.get('total_size_bytes', 0) or 0)}",
        f"issue_count: {len(issues)}",
        f"warning_count: {len(warnings)}",
        "suffix_counts:",
    ]
    suffix_counts = _suffix_counts(datasets)
    if suffix_counts:
        lines.extend(f"- {suffix}: {count}" for suffix, count in suffix_counts)
    else:
        lines.append("- none")

    if include_datasets:
        limit = max(0, int(max_datasets))
        sorted_datasets = sorted(
            [item for item in datasets if isinstance(item, Mapping)],
            key=lambda item: offline_path_sort_key(item.get("relative_path") or item.get("path")),
        )
        lines.append("datasets:")
        for item in sorted_datasets[:limit]:
            relative_path = normalize_offline_relative_path(item.get("relative_path") or item.get("path"))
            suffix = item.get("suffix") or item.get("file_type") or item.get("format") or "unknown"
            suffix_text = str(suffix)
            if suffix_text and not suffix_text.startswith("."):
                suffix_text = f".{suffix_text}"
            size = int(item.get("size_bytes", 0) or 0)
            lines.append(f"- {relative_path} | {suffix_text} | {size}")
        omitted = max(0, len(sorted_datasets) - limit)
        if omitted:
            lines.append(f"- omitted: {omitted}")
        if not sorted_datasets:
            lines.append("- none")

    return "\n".join(lines) + "\n"

def format_offline_data_diff_summary(diff: OfflineDataPreflightDiff | Mapping[str, Any]) -> str:
    """Render a deterministic metadata-only diff summary."""

    payload = _diff_payload(diff)
    lines = [
        "Offline Data Preflight Diff Summary",
        f"status: {'PASS' if payload.get('ok') else 'FAIL'}",
        f"added_datasets: {len(payload.get('added_datasets') or [])}",
        f"removed_datasets: {len(payload.get('removed_datasets') or [])}",
        f"changed_datasets: {len(payload.get('changed_datasets') or [])}",
        f"unchanged_count: {int(payload.get('unchanged_count', 0) or 0)}",
        f"issue_count: {len(payload.get('issues') or [])}",
    ]
    return "\n".join(lines) + "\n"
