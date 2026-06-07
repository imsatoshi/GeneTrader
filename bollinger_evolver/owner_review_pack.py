"""Owner review pack generator for custom strategy abstraction."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path
from typing import Any, Sequence

from bollinger_evolver.custom_strategy_schema import CustomStrategyBounds, CustomStrategyGenome
from bollinger_evolver.fixtures.custom_strategy_fixtures import get_custom_strategy_fixtures
from bollinger_evolver.risk_cli import build_fixture_risk_report


PACK_JSON_FILENAME = "owner_review_pack.json"
PACK_MD_FILENAME = "owner_review_summary.md"
SENSITIVE_MARKERS = ("api_key", "api_secret", "secret", "token", "password", "private_key")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_owner_review_output_dir(output: str | Path) -> Path:
    """Validate an explicit owner review pack output directory."""

    if output is None or not str(output).strip():
        raise ValueError("owner_review_output_dir_required")
    destination = Path(output).resolve()
    root = _repo_root().resolve()
    if destination == root:
        raise ValueError("owner_review_output_must_not_be_repo_root")
    disallowed_roots = (
        root / ".runtime",
        root / "user_data" / "data",
    )
    if any(destination == item or _is_relative_to(destination, item) for item in disallowed_roots):
        raise ValueError("owner_review_output_disallowed")
    return destination


def _contains_sensitive_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if not lowered.startswith("no_") and any(marker in lowered for marker in SENSITIVE_MARKERS):
                return True
            if _contains_sensitive_field(item):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_sensitive_field(item) for item in value)
    return False


def _parameter_table() -> list[dict[str, Any]]:
    defaults = CustomStrategyGenome(genome_id="owner-review-default").to_dict()
    bounds = CustomStrategyBounds()
    rows: list[dict[str, Any]] = []
    for field in fields(CustomStrategyBounds):
        bound = getattr(bounds, field.name)
        rows.append(
            {
                "name": field.name,
                "default": defaults[field.name],
                "minimum": bound.minimum,
                "maximum": bound.maximum,
                "kind": bound.kind,
                "ga_optimized": True,
            }
        )
    return rows


def _risk_level(warnings: list[str]) -> str:
    joined = " ".join(warnings)
    if any(marker in joined for marker in ("pause", "high_leverage", "drawdown", "loss_streak")):
        return "high"
    if any(marker in joined for marker in ("portfolio", "risk_per_trade", "max_position")):
        return "review"
    return "normal"


def _risk_summary(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    warning_counts: dict[str, int] = {}
    risk_level_counts = {"normal": 0, "review": 0, "high": 0}
    max_position_value = 0.0
    max_drawdown = 0.0
    highest_risk_fixture = ""
    for fixture in fixtures:
        warnings = [str(item) for item in fixture["risk_warnings"]]
        for warning in warnings:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
        level = _risk_level(warnings)
        risk_level_counts[level] += 1
        position_value = float(fixture["position_sizing_preview"].get("position_value", 0.0))
        drawdown = float(fixture["metrics"].get("drawdown", fixture["metrics"].get("max_drawdown", 0.0)))
        max_position_value = max(max_position_value, position_value)
        if drawdown >= max_drawdown:
            max_drawdown = drawdown
            highest_risk_fixture = str(fixture["fixture"])

    summary = {
        "schema_version": "owner-review-risk-summary/v1",
        "fixture_count": len(fixtures),
        "fixtures_with_warnings": sum(1 for fixture in fixtures if fixture["risk_warnings"]),
        "risk_level_counts": risk_level_counts,
        "warning_counts": dict(sorted(warning_counts.items())),
        "highest_risk_fixture": highest_risk_fixture,
        "max_drawdown": round(max_drawdown, 10),
        "max_position_value": round(max_position_value, 10),
        "visualization": [
            {"label": "normal", "count": risk_level_counts["normal"], "color": "green"},
            {"label": "review", "count": risk_level_counts["review"], "color": "amber"},
            {"label": "high", "count": risk_level_counts["high"], "color": "red"},
        ],
    }
    json.dumps(summary, sort_keys=True)
    return summary


def _circuit_breaker_status(drawdown: float) -> str:
    if drawdown >= 0.20:
        return "pause_trading"
    if drawdown >= 0.10:
        return "reduce_risk"
    return "none"


def _risk_dashboard_summary(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    status_counts = {"none": 0, "reduce_risk": 0, "pause_trading": 0}
    for fixture in fixtures:
        metrics = fixture["metrics"]
        config = fixture["strategy_config"]
        sizing = config["position_sizing"]
        drawdown = float(metrics.get("drawdown", metrics.get("max_drawdown", 0.0)))
        loss_streak = int(metrics.get("max_consecutive_losses", 0))
        status = _circuit_breaker_status(drawdown)
        status_counts[status] += 1
        row = {
            "fixture": fixture["fixture"],
            "max_drawdown": round(drawdown, 10),
            "loss_streak": loss_streak,
            "portfolio_exposure": round(float(sizing["max_portfolio_exposure"]), 10),
            "risk_per_trade": round(float(sizing["risk_per_trade"]), 10),
            "leverage": round(float(sizing["leverage"]), 10),
            "circuit_breaker_status": status,
            "risk_warning_count": len(fixture["risk_warnings"]),
        }
        rows.append(row)

    summary = {
        "schema_version": "owner-review-risk-dashboard-summary/v1",
        "fixture_count": len(rows),
        "max_drawdown": max((row["max_drawdown"] for row in rows), default=0.0),
        "max_loss_streak": max((row["loss_streak"] for row in rows), default=0),
        "max_portfolio_exposure": max((row["portfolio_exposure"] for row in rows), default=0.0),
        "max_risk_per_trade": max((row["risk_per_trade"] for row in rows), default=0.0),
        "max_leverage": max((row["leverage"] for row in rows), default=0.0),
        "circuit_breaker_status_counts": status_counts,
        "rows": rows,
    }
    json.dumps(summary, sort_keys=True)
    return summary


def build_owner_review_pack(*, equity: float = 10_000.0) -> dict[str, Any]:
    """Build a JSON-safe owner review pack from static custom strategy fixtures."""

    fixture_payload = get_custom_strategy_fixtures()
    fixture_summaries: list[dict[str, Any]] = []
    for fixture_name in sorted(fixture_payload):
        risk_report, explanation = build_fixture_risk_report(fixture_name, equity=equity)
        fixture_summaries.append(
            {
                "fixture": fixture_name,
                "strategy_id": risk_report["strategy_id"],
                "description": fixture_payload[fixture_name]["description"],
                "strategy_config": fixture_payload[fixture_name]["strategy_config"],
                "metrics": fixture_payload[fixture_name]["metrics"],
                "risk_warnings": risk_report["warnings"],
                "position_sizing_preview": risk_report["position_sizing_preview"],
                "explainability_summary": explanation["summary"],
            }
        )

    pack = {
        "schema_version": "owner-review-pack/v1",
        "status": "PENDING_OWNER_REVIEW",
        "parameter_table": _parameter_table(),
        "hard_constraints": [
            "unknown_genome_fields_rejected",
            "missing_genome_fields_rejected",
            "stoploss_below_takeprofit_required",
            "leverage_cap_3x",
            "risk_per_trade_cap_0_02",
            "json_safe_outputs_required",
        ],
        "risk_summary": _risk_summary(fixture_summaries),
        "risk_dashboard_summary": _risk_dashboard_summary(fixture_summaries),
        "fixtures": fixture_summaries,
        "review_decision_options": ["APPROVED", "NEEDS CHANGES"],
        "real_backtest_gate": "BLOCKED",
        "safety": {
            "fixture_only": True,
            "real_account_information_included": False,
            "external_process_used": False,
            "exchange_api_used": False,
        },
    }
    if _contains_sensitive_field(pack):
        raise ValueError("owner_review_pack_contains_sensitive_field")
    json.dumps(pack, sort_keys=True)
    return pack


def render_owner_review_summary(pack: Mapping[str, Any]) -> str:
    """Render a concise Markdown summary for manual owner review."""

    lines = [
        "# Owner Review Pack",
        "",
        f"Status: {pack['status']}",
        f"Real backtest gate: {pack['real_backtest_gate']}",
        "",
        "## Review Decision",
        "",
        "Owner must return exactly one of:",
        "",
        "- APPROVED",
        "- NEEDS CHANGES",
        "",
        "## Parameter Count",
        "",
        f"GA parameter rows: {len(pack['parameter_table'])}",
        "",
        "## Risk Summary",
        "",
        f"Fixtures with warnings: {pack['risk_summary']['fixtures_with_warnings']}",
        f"Highest risk fixture: {pack['risk_summary']['highest_risk_fixture']}",
        f"Max drawdown: {pack['risk_summary']['max_drawdown']}",
        "",
        "## Risk Dashboard Summary",
        "",
        f"Max loss streak: {pack['risk_dashboard_summary']['max_loss_streak']}",
        f"Max portfolio exposure: {pack['risk_dashboard_summary']['max_portfolio_exposure']}",
        f"Max risk per trade: {pack['risk_dashboard_summary']['max_risk_per_trade']}",
        f"Max leverage: {pack['risk_dashboard_summary']['max_leverage']}",
        "",
        "## Fixture Risk Warnings",
        "",
    ]
    for fixture in pack["fixtures"]:
        warnings = ", ".join(fixture["risk_warnings"]) or "none"
        lines.append(f"- {fixture['fixture']}: {warnings}")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "- Fixture-only local review artifacts.",
            "- No real account information included.",
            "- No external process execution used.",
            "- Real backtest remains BLOCKED until remote sync and owner APPROVED.",
            "",
        ]
    )
    return "\n".join(lines)


def write_owner_review_pack(output: str | Path, *, equity: float = 10_000.0) -> dict[str, str]:
    """Write owner review JSON and Markdown files into an explicit safe directory."""

    output_dir = validate_owner_review_output_dir(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    pack = build_owner_review_pack(equity=equity)
    summary = render_owner_review_summary(pack)
    json_path = output_dir / PACK_JSON_FILENAME
    md_path = output_dir / PACK_MD_FILENAME
    json_path.write_text(json.dumps(pack, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(summary, encoding="utf-8")
    return {
        "owner_review_pack": str(json_path),
        "owner_review_summary": str(md_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bollinger_evolver.owner_review_pack")
    parser.add_argument("--output", required=True)
    parser.add_argument("--equity", type=float, default=10_000.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = write_owner_review_pack(args.output, equity=float(args.equity))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
