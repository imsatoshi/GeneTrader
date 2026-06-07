"""Safe local CLI for mock custom-strategy risk reports.

The CLI writes fixture-based risk reports only. It does not run Freqtrade,
download market data, read account state, or call external processes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from bollinger_evolver.fixtures.custom_strategy_fixtures import get_custom_strategy_fixture
from bollinger_evolver.risk_budget import simulate_risk_budget
from bollinger_evolver.risk_governor import apply_risk_governor
from bollinger_evolver.strategy_explainer import build_strategy_explainability_report
from bollinger_evolver.trading_system_adapter import build_position_sizing_preview, build_trading_system_config


RISK_REPORT_FILENAME = "risk_report.json"
STRATEGY_EXPLANATION_FILENAME = "strategy_explanation.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_risk_output_dir(output: str | Path) -> Path:
    """Validate an explicit risk report output directory."""

    if output is None or not str(output).strip():
        raise ValueError("risk_output_dir_required")
    destination = Path(output).resolve()
    root = _repo_root().resolve()
    disallowed_roots = (
        root,
        root / ".runtime",
        root / "user_data" / "data",
    )
    if destination == root:
        raise ValueError("risk_output_dir_must_not_be_repo_root")
    if any(destination == item or _is_relative_to(destination, item) for item in disallowed_roots[1:]):
        raise ValueError("risk_output_dir_disallowed")
    return destination


def build_fixture_risk_report(fixture_name: str, *, equity: float = 10_000.0) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build JSON-safe risk and explainability reports from one static fixture."""

    fixture = get_custom_strategy_fixture(fixture_name)
    strategy_config = fixture["strategy_config"]
    metrics = fixture["metrics"]
    trading_config = build_trading_system_config(strategy_config)
    position_preview = build_position_sizing_preview(trading_config, equity=equity)
    advice = apply_risk_governor(strategy_config, metrics)
    position = trading_config["position"]
    risk_budget = simulate_risk_budget(
        [
            {
                "pair": "MOCK/USDT",
                "exposure": min(
                    position_preview["position_value"] / float(equity),
                    trading_config["risk_control"]["max_portfolio_exposure"],
                ),
                "leverage": position["base_leverage"],
            }
        ],
        loss_streak=int(metrics.get("max_consecutive_losses", 0)),
    )
    explanation = build_strategy_explainability_report(
        strategy_config,
        metrics=metrics,
        risk_governor=advice,
        position_sizing_preview=position_preview,
    )
    combined_warnings = sorted(
        {
            *position_preview["warnings"],
            *explanation["warnings"],
            *[f"risk_governor:{action}" for action in advice["actions"] if action != "advisory_only_no_strategy_mutation"],
        }
    )
    risk_report = {
        "schema_version": "mock-risk-report/v1",
        "fixture": fixture_name,
        "strategy_id": strategy_config["genome_id"],
        "equity": float(equity),
        "metrics": metrics,
        "risk_governor": advice,
        "position_sizing_preview": position_preview,
        "risk_budget": risk_budget,
        "warnings": combined_warnings,
        "safety": {
            "fixture_only": True,
            "real_backtest_used": False,
            "external_process_used": False,
            "exchange_api_used": False,
        },
    }
    json.dumps(risk_report, sort_keys=True)
    json.dumps(explanation, sort_keys=True)
    return risk_report, explanation


def explain_command(args: argparse.Namespace) -> dict[str, str]:
    output_dir = validate_risk_output_dir(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    risk_report, explanation = build_fixture_risk_report(str(args.fixture), equity=float(args.equity))
    risk_report_path = output_dir / RISK_REPORT_FILENAME
    explanation_path = output_dir / STRATEGY_EXPLANATION_FILENAME
    risk_report_path.write_text(json.dumps(risk_report, indent=2, sort_keys=True), encoding="utf-8")
    explanation_path.write_text(json.dumps(explanation, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "risk_report": str(risk_report_path),
        "strategy_explanation": str(explanation_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bollinger_evolver.risk_cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    explain = subparsers.add_parser("explain")
    explain.add_argument("--fixture", required=True)
    explain.add_argument("--output", required=True)
    explain.add_argument("--equity", type=float, default=10_000.0)
    explain.set_defaults(handler=explain_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.handler(args)
    except (KeyError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
