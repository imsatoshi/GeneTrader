"""CLI adapter for metadata-only offline data preflight reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from bollinger_evolver.config_requirements import load_offline_requirements_from_config
from bollinger_evolver.offline_data_diff import compare_offline_data_preflight_reports
from bollinger_evolver.offline_data_summary import (
    format_offline_data_diff_summary,
    format_offline_data_preflight_summary,
)
from bollinger_evolver.preflight import (
    build_offline_data_preflight_report,
    render_offline_data_preflight_report,
)


EXIT_OK = 0
EXIT_PREFLIGHT_FAILED = 1
EXIT_USAGE_ERROR = 2


def build_offline_preflight_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="offline-preflight",
        description="Build a metadata-only offline data preflight JSON report.",
    )
    parser.add_argument("--root", help="Root directory containing offline data files.")
    output_mode = parser.add_mutually_exclusive_group()
    output_mode.add_argument("--json", action="store_true", help="Emit compact deterministic JSON.")
    output_mode.add_argument("--pretty", action="store_true", help="Emit pretty deterministic JSON.")
    output_mode.add_argument("--text", action="store_true", help="Emit a deterministic text summary.")
    output_mode.add_argument("--summary", action="store_true", help="Emit a compact audit summary.")
    diff_output_mode = parser.add_mutually_exclusive_group()
    diff_output_mode.add_argument("--diff-json", action="store_true", help="Emit compact deterministic diff JSON.")
    diff_output_mode.add_argument("--diff-pretty", action="store_true", help="Emit pretty deterministic diff JSON.")
    parser.add_argument("--diff-old", help="Old offline preflight report JSON path.")
    parser.add_argument("--diff-new", help="New offline preflight report JSON path.")
    parser.add_argument("--requirements", help="Optional JSON requirements file for pair/timeframe coverage.")
    parser.add_argument("--config", help="Optional GA config JSON file used to derive requirements.")
    parser.add_argument("--pair", action="append", help="Inline required pair; can be repeated.")
    parser.add_argument("--timeframe", action="append", help="Inline required timeframe; can be repeated.")
    parser.add_argument("--output", help="Optional path to write the JSON report.")
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return exit code 1 when the report contains warnings.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout output.")
    return parser


def _report_output(
    root: Path,
    *,
    pretty: bool,
    text: bool,
    summary: bool,
    requirements: dict[str, object] | None = None,
    requirements_path: Path | None = None,
) -> tuple[object, str]:
    report = build_offline_data_preflight_report(
        root,
        requirements=requirements,
        requirements_path=requirements_path,
    )
    if summary:
        return report, format_offline_data_preflight_summary(report)
    if text:
        return report, render_offline_data_preflight_report(report, output_format="text")
    if pretty:
        return report, json.dumps(report.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    return report, report.to_json() + "\n"


def _load_report_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("report JSON must be an object")
    return payload


def _diff_json(old_path: Path, new_path: Path, pretty: bool, summary: bool) -> tuple[object, str]:
    old_report = _load_report_json(old_path)
    new_report = _load_report_json(new_path)
    diff = compare_offline_data_preflight_reports(old_report, new_report)
    if summary:
        return diff, format_offline_data_diff_summary(diff)
    if pretty:
        return diff, json.dumps(diff.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    return diff, diff.to_json() + "\n"


def run_offline_data_preflight_cli(
    argv: list[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_offline_preflight_cli_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or EXIT_USAGE_ERROR)

    diff_mode = bool(args.diff_old or args.diff_new or args.diff_json or args.diff_pretty)
    if diff_mode:
        if not args.diff_old or not args.diff_new:
            err.write("diff_requires_old_and_new_reports\n")
            return EXIT_USAGE_ERROR
        old_path = Path(args.diff_old).expanduser()
        new_path = Path(args.diff_new).expanduser()
        if not old_path.exists():
            err.write(f"diff_old_not_found: {old_path}\n")
            return EXIT_USAGE_ERROR
        if not new_path.exists():
            err.write(f"diff_new_not_found: {new_path}\n")
            return EXIT_USAGE_ERROR
        try:
            diff, payload = _diff_json(
                old_path,
                new_path,
                pretty=bool(args.diff_pretty),
                summary=bool(args.summary),
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            err.write(f"diff_failed: {type(exc).__name__}\n")
            return EXIT_USAGE_ERROR

        output_path = Path(args.output) if args.output else None
        if output_path is not None:
            try:
                output_path.write_text(payload, encoding="utf-8")
            except OSError as exc:
                err.write(f"output_write_failed: {type(exc).__name__}\n")
                return EXIT_USAGE_ERROR
        if not args.quiet:
            out.write(payload)
        if not diff.ok or diff.issues:
            return EXIT_PREFLIGHT_FAILED
        return EXIT_OK

    if not args.root:
        err.write("root_required\n")
        return EXIT_USAGE_ERROR

    root = Path(args.root).expanduser()
    if not root.exists():
        err.write(f"root_not_found: {root}\n")
        return EXIT_USAGE_ERROR
    if not root.is_dir():
        err.write(f"root_not_directory: {root}\n")
        return EXIT_USAGE_ERROR

    requirements_path = Path(args.requirements).expanduser() if args.requirements else None
    config_path = Path(args.config).expanduser() if args.config else None
    has_inline_requirements = bool(args.pair or args.timeframe)
    if config_path is not None and (requirements_path is not None or has_inline_requirements):
        err.write("config_conflicts_with_requirements\n")
        return EXIT_USAGE_ERROR
    if requirements_path is not None and not requirements_path.exists():
        err.write(f"requirements_not_found: {requirements_path}\n")
        return EXIT_USAGE_ERROR
    requirements: dict[str, object] | None = None
    if has_inline_requirements:
        if not args.pair or not args.timeframe:
            err.write("inline_requirements_need_pair_and_timeframe\n")
            return EXIT_USAGE_ERROR
        requirements = {"pairs": list(args.pair), "timeframes": list(args.timeframe)}
    if config_path is not None:
        if not config_path.exists():
            err.write(f"config_not_found: {config_path}\n")
            return EXIT_USAGE_ERROR
        try:
            requirements = load_offline_requirements_from_config(config_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            err.write(f"config_failed: {type(exc).__name__}\n")
            return EXIT_USAGE_ERROR

    try:
        report, payload = _report_output(
            root,
            pretty=bool(args.pretty),
            text=bool(args.text),
            summary=bool(args.summary),
            requirements=requirements,
            requirements_path=requirements_path,
        )
    except (OSError, ValueError) as exc:
        err.write(f"preflight_failed: {type(exc).__name__}\n")
        return EXIT_USAGE_ERROR

    output_path = Path(args.output) if args.output else None
    if output_path is not None:
        try:
            output_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            err.write(f"output_write_failed: {type(exc).__name__}\n")
            return EXIT_USAGE_ERROR

    if not args.quiet:
        out.write(payload)

    if not report.ok:
        return EXIT_PREFLIGHT_FAILED
    if args.fail_on_warning and report.warnings:
        return EXIT_PREFLIGHT_FAILED
    return EXIT_OK


def offline_preflight_main(argv: list[str] | None = None) -> int:
    return run_offline_data_preflight_cli(argv)


if __name__ == "__main__":
    raise SystemExit(offline_preflight_main())
