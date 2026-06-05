"""Workflow-friendly offline data preflight adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.offline_preflight_cli import (
    EXIT_OK,
    EXIT_PREFLIGHT_FAILED,
    EXIT_USAGE_ERROR,
)
from bollinger_evolver.preflight import build_offline_data_preflight_report


def _json_payload(report_dict: Mapping[str, Any], *, pretty: bool) -> str:
    if pretty:
        return json.dumps(report_dict, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    return json.dumps(report_dict, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"


def run_offline_data_workflow_preflight(
    root: str | Path,
    output: str | Path | None = None,
    *,
    pretty: bool = False,
    fail_on_warning: bool = False,
    requirements: Mapping[str, Any] | None = None,
    requirements_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run offline data preflight for workflow callers without default file writes."""

    root_path = Path(root).expanduser()
    if not root_path.exists():
        return {
            "exit_code": EXIT_USAGE_ERROR,
            "report_dict": {},
            "json_text": "",
            "stdout_text": "",
            "stderr_text": f"root_not_found: {root_path}\n",
            "metadata": {"source": "offline_data_workflow_preflight", "wrote_output": False},
        }
    if not root_path.is_dir():
        return {
            "exit_code": EXIT_USAGE_ERROR,
            "report_dict": {},
            "json_text": "",
            "stdout_text": "",
            "stderr_text": f"root_not_directory: {root_path}\n",
            "metadata": {"source": "offline_data_workflow_preflight", "wrote_output": False},
        }

    try:
        report = build_offline_data_preflight_report(
            root_path,
            requirements=requirements,
            requirements_path=requirements_path,
        )
        report_dict = report.to_dict()
        json_text = _json_payload(report_dict, pretty=pretty)
    except (OSError, ValueError) as exc:
        return {
            "exit_code": EXIT_USAGE_ERROR,
            "report_dict": {},
            "json_text": "",
            "stdout_text": "",
            "stderr_text": f"preflight_failed: {type(exc).__name__}\n",
            "metadata": {"source": "offline_data_workflow_preflight", "wrote_output": False},
        }

    wrote_output = False
    if output is not None:
        try:
            Path(output).write_text(json_text, encoding="utf-8")
            wrote_output = True
        except OSError as exc:
            return {
                "exit_code": EXIT_USAGE_ERROR,
                "report_dict": report_dict,
                "json_text": json_text,
                "stdout_text": "",
                "stderr_text": f"output_write_failed: {type(exc).__name__}\n",
                "metadata": {"source": "offline_data_workflow_preflight", "wrote_output": False},
            }

    exit_code = EXIT_OK
    if not report.ok or (fail_on_warning and report.warnings):
        exit_code = EXIT_PREFLIGHT_FAILED

    return {
        "exit_code": exit_code,
        "report_dict": report_dict,
        "json_text": json_text,
        "stdout_text": json_text,
        "stderr_text": "",
        "metadata": {
            "source": "offline_data_workflow_preflight",
            "pretty": bool(pretty),
            "fail_on_warning": bool(fail_on_warning),
            "wrote_output": wrote_output,
        },
    }
