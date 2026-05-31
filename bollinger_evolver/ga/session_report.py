"""Human-readable session report rendering for Bollinger Evolver."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.evaluators import sanitize_mapping


SENSITIVE_KEYWORDS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "private_key",
    "mnemonic",
    "webhook",
    "jwt",
)


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key).lower()
    return any(marker in normalized for marker in SENSITIVE_KEYWORDS)


def contains_sensitive_fields(obj: Any) -> bool:
    """Return True when the object still contains sensitive-looking keys."""

    if isinstance(obj, Mapping):
        for key, value in obj.items():
            if _is_sensitive_key(str(key)):
                return True
            if contains_sensitive_fields(value):
                return True
        return False
    if isinstance(obj, (list, tuple, set)):
        return any(contains_sensitive_fields(item) for item in obj)
    return False


def redact_sensitive_fields(obj: Any) -> Any:
    """Recursively remove sensitive-looking keys from arbitrary JSON-like objects."""

    if isinstance(obj, Mapping):
        redacted: dict[str, Any] = {}
        for key, value in obj.items():
            if _is_sensitive_key(str(key)):
                continue
            redacted[str(key)] = redact_sensitive_fields(value)
        return redacted
    if isinstance(obj, list):
        return [redact_sensitive_fields(item) for item in obj]
    if isinstance(obj, tuple):
        return [redact_sensitive_fields(item) for item in obj]
    if isinstance(obj, set):
        return [redact_sensitive_fields(item) for item in obj]
    return obj


def _blocked_reasons(session_summary: Mapping[str, Any]) -> list[str]:
    gate = session_summary.get("dataQualityGate", {})
    if isinstance(gate, Mapping):
        reasons = gate.get("fail_reasons", [])
        if isinstance(reasons, list):
            return [str(item) for item in reasons]
    reason = session_summary.get("reason")
    return [str(reason)] if reason else []


def _blocked_count(generation_summary: Mapping[str, Any]) -> int:
    individuals = generation_summary.get("individuals", [])
    if not isinstance(individuals, list):
        return 0
    blocked_reasons = {"data_quality_gate_failed", "data_quality_manifest_missing"}
    count = 0
    for item in individuals:
        if not isinstance(item, Mapping):
            continue
        reason = item.get("reason")
        if reason in blocked_reasons:
            count += 1
    return count


def _generation_progress(session_summary: Mapping[str, Any]) -> dict[str, Any]:
    generation_summaries = session_summary.get("generation_summaries", [])
    if not isinstance(generation_summaries, list):
        generation_summaries = []
    return {
        "generation_count": len(generation_summaries),
        "best_fitness_by_generation": [
            item.get("best_fitness_score") if isinstance(item, Mapping) else None
            for item in generation_summaries
        ],
        "success_count_by_generation": [
            int(item.get("success_count", 0)) if isinstance(item, Mapping) else 0
            for item in generation_summaries
        ],
        "failed_count_by_generation": [
            int(item.get("failure_count", 0)) if isinstance(item, Mapping) else 0
            for item in generation_summaries
        ],
        "blocked_count_by_generation": [
            _blocked_count(item) if isinstance(item, Mapping) else 0
            for item in generation_summaries
        ],
    }


def _data_quality_gate_report(session_summary: Mapping[str, Any]) -> dict[str, Any]:
    gate = session_summary.get("dataQualityGate")
    if isinstance(gate, Mapping):
        return {
            "status": gate.get("status", "unknown"),
            "allowed_for_evaluation": bool(gate.get("allowed_for_evaluation", False)),
            "fail_reasons": [str(item) for item in gate.get("fail_reasons", []) if item],
            "warnings": [str(item) for item in gate.get("warnings", []) if item],
        }
    status = "disabled" if bool(session_summary.get("dataQualityGateDisabled", False)) else "unknown"
    return {
        "status": status,
        "allowed_for_evaluation": bool(session_summary.get("dataQualityGateDisabled", False)),
        "fail_reasons": [],
        "warnings": [],
    }


def _final_best_report(session_summary: Mapping[str, Any]) -> dict[str, Any]:
    final_best = session_summary.get("final_best")
    if not isinstance(final_best, Mapping):
        return {
            "exists": False,
            "individual_id": None,
            "fitness": None,
            "genes_hash": None,
            "strategy_name": None,
            "strategy_path": None,
            "metrics": {},
            "genes": {},
        }
    return {
        "exists": True,
        "individual_id": final_best.get("individual_id") or final_best.get("best_candidate_id"),
        "fitness": final_best.get("fitness") or final_best.get("best_fitness_score"),
        "genes_hash": final_best.get("genes_hash"),
        "strategy_name": final_best.get("strategy_name"),
        "strategy_path": final_best.get("strategy_path"),
        "metrics": final_best.get("metrics", {}),
        "genes": final_best.get("genes", {}),
    }


def _recommendation(session_summary: Mapping[str, Any], final_best: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    gate = session_summary.get("dataQualityGate")
    if isinstance(gate, Mapping) and gate.get("allowed_for_evaluation") is False:
        reasons.extend([str(item) for item in gate.get("fail_reasons", []) if item])
        return {
            "status": "BLOCKED_BY_DATA_QA",
            "next_step": "Fix data coverage before running additional GA sessions.",
            "reasons": reasons,
        }
    if not final_best.get("exists"):
        reason = session_summary.get("reason")
        if reason:
            reasons.append(str(reason))
        return {
            "status": "NO_FINAL_BEST",
            "next_step": "Investigate failed or rejected individuals before further evaluation.",
            "reasons": reasons,
        }
    completed = int(session_summary.get("completed", 0) or 0)
    requested = int(session_summary.get("generations_requested", 0) or 0)
    if requested > 0 and completed < requested:
        reasons.append("session_stopped_before_requested_generations")
        return {
            "status": "NEEDS_MORE_GENERATIONS",
            "next_step": "Review stop reasons and rerun if additional generations are still useful.",
            "reasons": reasons,
        }
    return {
        "status": "READY_FOR_REVIEW",
        "next_step": "Use the final best candidate as the next review input before any real backtest preparation.",
        "reasons": reasons,
    }


def _risk_and_safety(
    original_session_summary: Mapping[str, Any],
    redacted_session_summary: Mapping[str, Any],
    session_summary: Mapping[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    if bool(session_summary.get("real_backtest", False)):
        warnings.append("unexpected_real_backtest_enabled")
    if bool(session_summary.get("dataQualityGateDisabled", False)):
        warnings.append("data_quality_gate_disabled")
    contains_sensitive = contains_sensitive_fields(original_session_summary)
    if contains_sensitive:
        warnings.append("sensitive_fields_redacted")
    return {
        "allow_real_backtest": bool(session_summary.get("allow_real_backtest", False)),
        "mock_first": bool(session_summary.get("mock_first", False)),
        "contains_sensitive_fields": contains_sensitive,
        "warnings": warnings,
        "blocked_reasons": _blocked_reasons(redacted_session_summary),
    }


def _markdown_report(report: Mapping[str, Any]) -> str:
    session = report["session"]
    data_gate = report["dataQualityGate"]
    generation = report["generationSummary"]
    final_best = report["finalBest"]
    risk = report["riskAndSafety"]
    recommendation = report["recommendation"]

    lines = [
        "# Bollinger Evolver Session Report",
        "",
        "## Executive Summary",
        f"- Session ID: {session['session_id']}",
        f"- Status: {session['status']}",
        f"- Mock evaluation: {str(session['mock_evaluation']).lower()}",
        f"- Real backtest: {str(session['real_backtest']).lower()}",
        f"- Recommendation: {recommendation['status']}",
        "",
        "## Data Quality Gate",
        f"- Status: {data_gate.get('status', 'unknown')}",
        f"- Allowed for evaluation: {str(data_gate.get('allowed_for_evaluation', False)).lower()}",
        f"- Fail reasons: {', '.join(data_gate.get('fail_reasons', [])) or 'none'}",
        f"- Warnings: {', '.join(data_gate.get('warnings', [])) or 'none'}",
        "",
        "## Generation Progress",
        f"- Generation count: {generation['generation_count']}",
        f"- Best fitness by generation: {generation['best_fitness_by_generation']}",
        f"- Success counts: {generation['success_count_by_generation']}",
        f"- Failed counts: {generation['failed_count_by_generation']}",
        f"- Blocked counts: {generation['blocked_count_by_generation']}",
        "",
        "## Final Best Individual",
    ]
    if final_best["exists"]:
        lines.extend(
            [
                f"- Individual ID: {final_best['individual_id']}",
                f"- Fitness: {final_best['fitness']}",
                f"- Genes hash: {final_best['genes_hash']}",
                f"- Strategy name: {final_best['strategy_name']}",
                f"- Strategy path: {final_best['strategy_path']}",
                f"- Key metrics: {json.dumps(final_best['metrics'], sort_keys=True)}",
            ]
        )
    else:
        lines.append("- No final best individual.")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            f"- Mock-first: {str(risk['mock_first']).lower()}",
            f"- Real backtest disabled: {str(not session['real_backtest']).lower()}",
            "- No exchange connection: true",
            f"- No secrets: {str(not risk['contains_sensitive_fields']).lower()}",
        ]
    )
    if risk["warnings"]:
        lines.append(f"- Warnings: {', '.join(risk['warnings'])}")
    if session["real_backtest"]:
        lines.append("- WARN: real_backtest=true appeared unexpectedly in this runner flow.")
    lines.extend(
        [
            "",
            "## Recommended Next Step",
            f"- {recommendation['next_step']}",
        ]
    )
    if recommendation["reasons"]:
        lines.append(f"- Reasons: {', '.join(recommendation['reasons'])}")
    return "\n".join(lines) + "\n"


def render_session_report(
    session_summary: dict,
    output_dir: str | Path,
    write_files: bool = True,
) -> dict[str, Any]:
    """Render machine and human-readable review artifacts from a session summary."""

    original_summary = session_summary if isinstance(session_summary, Mapping) else {}
    redacted_summary = sanitize_mapping(redact_sensitive_fields(original_summary))
    final_best = _final_best_report(redacted_summary)
    data_quality_gate = _data_quality_gate_report(redacted_summary)
    report = {
        "version": "runner-session-report-v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "readOnly": True,
        "session": {
            "session_id": redacted_summary.get("session_id"),
            "status": redacted_summary.get("status"),
            "mock_evaluation": bool(redacted_summary.get("mock_evaluation", False)),
            "real_backtest": bool(redacted_summary.get("real_backtest", False)),
            "generations_completed": int(redacted_summary.get("completed", 0) or 0),
            "population_size": int(redacted_summary.get("population_size", 0) or 0),
        },
        "dataQualityGate": data_quality_gate,
        "generationSummary": _generation_progress(redacted_summary),
        "finalBest": final_best,
        "riskAndSafety": _risk_and_safety(original_summary, redacted_summary, redacted_summary),
        "recommendation": _recommendation(redacted_summary, final_best),
    }
    markdown = _markdown_report(report)

    report_json_path = None
    report_markdown_path = None
    if write_files:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        report_json_path = destination / "session_report.json"
        report_markdown_path = destination / "session_report.md"
        report_json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        report_markdown_path.write_text(markdown, encoding="utf-8")

    return {
        "success": True,
        "report_json_path": str(report_json_path) if report_json_path is not None else None,
        "report_markdown_path": (
            str(report_markdown_path) if report_markdown_path is not None else None
        ),
        "report": report,
        "markdown": markdown,
    }
