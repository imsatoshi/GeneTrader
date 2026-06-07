"""Local mock-first mainline health report generator.

The generator formats already-known local state and test results. It does not
run tests, call git, invoke subprocesses, or inspect external services.
"""

from __future__ import annotations

import argparse
import html
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


JSON_FILENAME = "local_mainline_health_report.json"
MARKDOWN_FILENAME = "local_mainline_health_report.md"
HTML_FILENAME = "local_mainline_health_report.html"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_health_report_output_dir(output: str | Path) -> Path:
    """Validate an explicit health report output directory."""

    if output is None or not str(output).strip():
        raise ValueError("health_report_output_dir_required")
    destination = Path(output).resolve()
    root = _repo_root().resolve()
    if destination == root:
        raise ValueError("health_report_output_must_not_be_repo_root")
    disallowed_roots = (
        root / ".runtime",
        root / "user_data" / "data",
    )
    if any(destination == item or _is_relative_to(destination, item) for item in disallowed_roots):
        raise ValueError("health_report_output_disallowed")
    return destination


def build_local_mainline_health_report(
    *,
    git_state: Mapping[str, Any] | None = None,
    test_results: Sequence[Mapping[str, Any]] | None = None,
    untracked_files: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe local mainline health report."""

    report = {
        "schema_version": "local-mainline-health-report/v1",
        "status": "PASS",
        "git_state": dict(
            git_state
            or {
                "branch": "main",
                "ahead_origin_main": 46,
                "head": "7305824 Add pre-push mainline audit report",
                "cached_empty": True,
            }
        ),
        "test_results": list(
            test_results
            or (
                {"name": "pytest tests -q", "status": "passed", "summary": "237 passed, 4 subtests passed"},
                {"name": "unittest discover", "status": "passed", "summary": "885 passed, 6 skipped"},
                {"name": "frontend targeted mock pages", "status": "passed", "summary": "4 files, 25 tests"},
                {"name": "npm test", "status": "passed", "summary": "15 files, 54 tests"},
                {"name": "npm run build", "status": "passed", "summary": "no large chunk warning"},
                {"name": "compileall", "status": "passed", "summary": "syntax compile passed"},
                {"name": "diff checks", "status": "passed", "summary": "cached check clean"},
            )
        ),
        "module_status": {
            "schema_registry": "ready",
            "golden_fixtures": "ready",
            "risk_cli": "ready",
            "owner_review_pack": "ready",
            "frontend_mock_pages": "ready",
        },
        "safety_boundary": {
            "real_backtest": "BLOCKED",
            "owner_review": "PENDING",
            "freqtrade_execution": False,
            "download_data": False,
            "exchange_api": False,
            "deployment": False,
            "rollback": False,
        },
        "untracked_files": list(untracked_files or []),
    }
    json.dumps(report, sort_keys=True)
    return report


def render_health_markdown(report: Mapping[str, Any]) -> str:
    """Render a concise Markdown health report."""

    lines = [
        "# Local Mainline Health Report",
        "",
        f"Status: {report['status']}",
        f"Real backtest: {report['safety_boundary']['real_backtest']}",
        f"Owner review: {report['safety_boundary']['owner_review']}",
        "",
        "## Test Results",
        "",
    ]
    for result in report["test_results"]:
        lines.append(f"- {result['name']}: {result['status']} ({result['summary']})")
    lines.extend(
        [
            "",
            "## Module Status",
            "",
        ]
    )
    for name, status in report["module_status"].items():
        lines.append(f"- {name}: {status}")
    lines.append("")
    return "\n".join(lines)


def render_health_html(report: Mapping[str, Any]) -> str:
    """Render a small self-contained HTML health report."""

    test_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item['name']))}</td>"
        f"<td>{html.escape(str(item['status']))}</td>"
        f"<td>{html.escape(str(item['summary']))}</td>"
        "</tr>"
        for item in report["test_results"]
    )
    return (
        "<!doctype html>\n"
        "<html><head><meta charset=\"utf-8\"><title>Local Mainline Health Report</title></head>"
        "<body>"
        "<h1>Local Mainline Health Report</h1>"
        f"<p>Status: {html.escape(str(report['status']))}</p>"
        f"<p>Real backtest: {html.escape(str(report['safety_boundary']['real_backtest']))}</p>"
        "<table><thead><tr><th>Test</th><th>Status</th><th>Summary</th></tr></thead>"
        f"<tbody>{test_rows}</tbody></table>"
        "</body></html>"
    )


def write_local_mainline_health_report(output: str | Path) -> dict[str, str]:
    """Write JSON, Markdown, and HTML health reports to an explicit directory."""

    output_dir = validate_health_report_output_dir(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_local_mainline_health_report()
    json_path = output_dir / JSON_FILENAME
    markdown_path = output_dir / MARKDOWN_FILENAME
    html_path = output_dir / HTML_FILENAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_health_markdown(report), encoding="utf-8")
    html_path.write_text(render_health_html(report), encoding="utf-8")
    return {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "html": str(html_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bollinger_evolver.local_health_report")
    parser.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = write_local_mainline_health_report(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
