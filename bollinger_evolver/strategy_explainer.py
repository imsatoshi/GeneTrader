"""JSON-safe explainability report for mock custom strategies."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = "strategy-explainability/v1"


def _get_mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = source.get(key, {})
    return value if isinstance(value, Mapping) else {}


def _number(source: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    value = source.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    numeric = float(value)
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        return default
    return numeric


def _list_strings(value: Any) -> list[str]:
    if isinstance(value, list | tuple):
        return [str(item) for item in value]
    return []


def build_strategy_explainability_report(
    strategy_config: Mapping[str, Any],
    *,
    metrics: Mapping[str, Any] | None = None,
    risk_governor: Mapping[str, Any] | None = None,
    position_sizing_preview: Mapping[str, Any] | None = None,
    fitness_components: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Explain a mock genome/config without running a backtest or live action."""

    if not isinstance(strategy_config, Mapping):
        raise TypeError("strategy_config_must_be_mapping")

    entry = _get_mapping(strategy_config, "entry")
    exit_config = _get_mapping(strategy_config, "exit")
    position = _get_mapping(strategy_config, "position_sizing")
    if not position:
        position = _get_mapping(strategy_config, "position")
    risk_control = _get_mapping(strategy_config, "risk_control")
    active_metrics = metrics or {}
    active_risk_governor = risk_governor or {}
    active_position_preview = position_sizing_preview or {}
    active_fitness = fitness_components or {}

    leverage = _number(position, "leverage", _number(position, "base_leverage", 1.0))
    risk_per_trade = _number(position, "risk_per_trade", _number(strategy_config, "risk_per_trade", 0.0))
    max_portfolio_exposure = _number(
        position,
        "max_portfolio_exposure",
        _number(risk_control, "max_portfolio_exposure", _number(strategy_config, "max_portfolio_exposure", 0.0)),
    )
    drawdown = _number(active_metrics, "drawdown", _number(active_metrics, "max_drawdown", 0.0))
    stability_score = _number(active_metrics, "stability_score", 0.0)
    warnings: list[str] = []

    if leverage >= 3.0:
        warnings.append("high_leverage_strategy")
    if risk_per_trade >= 0.02:
        warnings.append("risk_per_trade_near_limit")
    if max_portfolio_exposure > 0.30:
        warnings.append("high_portfolio_exposure")
    if drawdown >= 0.10:
        warnings.append("drawdown_requires_risk_review")
    warnings.extend(_list_strings(active_position_preview.get("warnings")))

    risk_actions = _list_strings(active_risk_governor.get("actions"))
    if risk_actions:
        warnings.extend([f"risk_governor:{action}" for action in risk_actions if action != "advisory_only_no_strategy_mutation"])

    fitness_explanation: list[str] = []
    if active_fitness:
        if "final_fitness" in active_fitness:
            fitness_explanation.append(f"final_fitness={_number(active_fitness, 'final_fitness'):.3f}")
        if _number(active_fitness, "drawdown_penalty") > 0:
            fitness_explanation.append("drawdown_penalty_applied")
        if _number(active_fitness, "overfit_penalty") > 0:
            fitness_explanation.append("overfit_penalty_applied")
        if _number(active_fitness, "stability_component") > 0:
            fitness_explanation.append("stability_component_rewards_walk_forward_consistency")

    if drawdown <= 0.05 and (stability_score >= 0.75 or stability_score == 0.0):
        summary = "Low-drawdown strategy profile with comparatively stable mock metrics."
    elif warnings:
        summary = "Strategy profile requires risk review before any real backtest gate."
    else:
        summary = "Balanced custom strategy profile for mock-first evaluation."

    report = {
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "entry_logic": [
            f"bollinger_window={entry.get('bollinger_window', entry.get('bollinger', {}))}",
            f"bollinger_stddev={entry.get('bollinger_stddev', 'unknown')}",
            f"rsi_max={entry.get('rsi_max', 'unknown')}",
        ],
        "exit_logic": [
            f"stoploss_pct={exit_config.get('stop_loss_pct', exit_config.get('stoploss_pct', 'unknown'))}",
            f"takeprofit_pct={exit_config.get('take_profit_pct', exit_config.get('takeprofit_pct', 'unknown'))}",
            f"trailing_stop_pct={exit_config.get('trailing_stop_pct', 'unknown')}",
        ],
        "risk_logic": [
            f"leverage={leverage:g}",
            f"risk_per_trade={risk_per_trade:g}",
            f"max_portfolio_exposure={max_portfolio_exposure:g}",
            *[f"risk_governor_action={action}" for action in risk_actions],
        ],
        "warnings": sorted(dict.fromkeys(warnings)),
        "fitness_explanation": fitness_explanation,
    }
    json.dumps(report, sort_keys=True)
    return report
