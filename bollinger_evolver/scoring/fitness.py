"""Formal fitness scoring for Bollinger Evolver candidates."""

from __future__ import annotations

import math
from typing import Any, Mapping

from bollinger_evolver.evaluators import sanitize_mapping


DEFAULT_FITNESS_CONFIG: dict[str, float | int] = {
    "min_trades": 30,
    "min_profit_factor": 1.05,
    "max_drawdown_limit": 0.35,
    "max_train_oos_gap": 0.5,
    "min_oos_profit": 0.0,
    "max_turnover_penalty_threshold": 500,
    "min_worst_window_profit": -0.15,
}


RETURN_KEYS = {
    "total_profit",
    "profit_total",
    "profit_total_pct",
    "total_profit_pct",
    "profit_pct",
    "train_profit",
    "oos_profit",
    "avg_oos_profit",
    "worst_oos_profit",
    "worst_window_profit",
    "avg_window_profit",
}
RATIO_KEYS = {
    "max_drawdown",
    "max_drawdown_pct",
    "max_drawdown_abs",
    "max_drawdown_account",
    "drawdown_max",
    "train_oos_gap",
    "window_profit_std",
}


def _finite_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _finite_int(value: Any) -> int | None:
    numeric = _finite_float(value)
    if numeric is None:
        return None
    return int(numeric)


def _normalize_ratio(value: float | None) -> float | None:
    if value is None:
        return None
    if abs(value) > 1.5:
        return value / 100.0
    return value


def _clip(value: float, minimum: float, maximum: float) -> float:
    if not math.isfinite(value):
        return minimum
    return max(minimum, min(maximum, value))


def _first_float(metrics: Mapping[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = _finite_float(metrics.get(key))
        if value is not None:
            return value
    return None


def _first_int(metrics: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = _finite_int(metrics.get(key))
        if value is not None:
            return value
    return None


def _canonical_metrics(metrics: Mapping[str, Any]) -> dict[str, Any]:
    safe_metrics = sanitize_mapping(metrics)
    total_profit = _first_float(
        safe_metrics,
        ("oos_profit", "avg_oos_profit", "profit_total_pct", "total_profit_pct", "total_profit", "profit_total"),
    )
    canonical = {
        "success": safe_metrics.get("success"),
        "mock": bool(safe_metrics.get("mock", False)),
        "real_backtest": bool(safe_metrics.get("real_backtest", False)),
        "total_profit": _normalize_ratio(total_profit),
        "profit_total_abs": _first_float(safe_metrics, ("profit_total_abs", "absolute_profit")),
        "profit_factor": _first_float(safe_metrics, ("profit_factor", "profitfactor")),
        "max_drawdown": _normalize_ratio(
            _first_float(
                safe_metrics,
                ("max_drawdown", "max_drawdown_pct", "max_drawdown_abs", "max_drawdown_account", "drawdown_max"),
            )
        ),
        "sharpe": _first_float(safe_metrics, ("sharpe", "sharpe_ratio")),
        "sortino": _first_float(safe_metrics, ("sortino", "sortino_ratio")),
        "calmar": _first_float(safe_metrics, ("calmar", "calmar_ratio")),
        "trade_count": _first_int(safe_metrics, ("trade_count", "total_trades", "trades")),
        "win_rate": _first_float(safe_metrics, ("win_rate", "winrate", "winning_rate")),
        "avg_trade_duration": safe_metrics.get("avg_trade_duration"),
        "train_profit": _normalize_ratio(_first_float(safe_metrics, ("train_profit",))),
        "oos_profit": _normalize_ratio(_first_float(safe_metrics, ("oos_profit", "avg_oos_profit"))),
        "train_oos_gap": _normalize_ratio(_first_float(safe_metrics, ("train_oos_gap",))),
        "worst_window_profit": _normalize_ratio(
            _first_float(safe_metrics, ("worst_window_profit", "worst_oos_profit"))
        ),
        "avg_window_profit": _normalize_ratio(_first_float(safe_metrics, ("avg_window_profit",))),
        "window_profit_std": _normalize_ratio(_first_float(safe_metrics, ("window_profit_std",))),
        "turnover": _first_float(safe_metrics, ("turnover",)),
        "trades_per_day": _first_float(safe_metrics, ("trades_per_day",)),
        "max_consecutive_losses": _first_int(safe_metrics, ("max_consecutive_losses",)),
    }
    if canonical["calmar"] is None and canonical["total_profit"] is not None and canonical["max_drawdown"]:
        canonical["calmar"] = canonical["total_profit"] / max(canonical["max_drawdown"], 0.001)
    return canonical


def _walk_forward_metrics(walk_forward_result: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(walk_forward_result, Mapping):
        return {}

    summary = walk_forward_result.get("summary", {})
    windows = walk_forward_result.get("windows", [])
    safe_summary = sanitize_mapping(summary) if isinstance(summary, Mapping) else {}
    safe_windows = windows if isinstance(windows, list) else []

    oos_profits: list[float] = []
    passed_count = 0
    for window in safe_windows:
        if not isinstance(window, Mapping):
            continue
        if window.get("passed") is True:
            passed_count += 1
        test_metrics = window.get("test_metrics", {})
        if isinstance(test_metrics, Mapping):
            test_profit = _canonical_metrics(test_metrics).get("total_profit")
            if test_profit is not None:
                oos_profits.append(float(test_profit))

    avg_oos_profit = _normalize_ratio(_first_float(safe_summary, ("avg_oos_profit",)))
    worst_oos_profit = _normalize_ratio(_first_float(safe_summary, ("worst_oos_profit",)))
    pass_rate = _first_float(safe_summary, ("pass_rate",))
    avg_drawdown = _normalize_ratio(_first_float(safe_summary, ("avg_drawdown",)))

    if avg_oos_profit is None and oos_profits:
        avg_oos_profit = sum(oos_profits) / len(oos_profits)
    if worst_oos_profit is None and oos_profits:
        worst_oos_profit = min(oos_profits)
    if pass_rate is None and safe_windows:
        pass_rate = passed_count / len(safe_windows)

    return {
        "summary": safe_summary,
        "window_count": len(safe_windows),
        "avg_oos_profit": avg_oos_profit,
        "worst_oos_profit": worst_oos_profit,
        "pass_rate": pass_rate,
        "avg_drawdown": avg_drawdown,
    }


def _merge_config(config: Mapping[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = dict(DEFAULT_FITNESS_CONFIG)
    if config:
        merged.update(sanitize_mapping(config))
    return merged


def _score_components(canonical: Mapping[str, Any], walk_forward: Mapping[str, Any]) -> dict[str, float]:
    total_profit = float(canonical.get("oos_profit") if canonical.get("oos_profit") is not None else canonical.get("total_profit") or 0.0)
    profit_factor = float(canonical.get("profit_factor") or 0.0)
    calmar = float(canonical.get("calmar") or 0.0)
    trade_count = float(canonical.get("trade_count") or 0.0)
    worst_window_profit = canonical.get("worst_window_profit")
    window_profit_std = canonical.get("window_profit_std")
    train_oos_gap = canonical.get("train_oos_gap")
    pass_rate = walk_forward.get("pass_rate")

    profit_score = _clip(total_profit / 0.30, -1.0, 1.5)
    profit_factor_score = _clip((profit_factor - 1.0) / 2.0, -1.0, 1.0)
    calmar_score = _clip(calmar / 3.0, -1.0, 1.0)
    trade_count_score = _clip(trade_count / 120.0, 0.0, 1.0)

    stability_score = 0.5
    if worst_window_profit is not None:
        stability_score += _clip(float(worst_window_profit) / 0.20, -1.0, 0.5) * 0.4
    if window_profit_std is not None:
        stability_score -= _clip(float(window_profit_std) / 0.25, 0.0, 1.0) * 0.3
    if train_oos_gap is not None:
        stability_score -= _clip(abs(float(train_oos_gap)) / 0.5, 0.0, 1.0) * 0.3
    if pass_rate is not None:
        stability_score += (_clip(float(pass_rate), 0.0, 1.0) - 0.5) * 0.4
    stability_score = _clip(stability_score, -1.0, 1.0)

    return {
        "profit_score": profit_score,
        "profit_factor_score": profit_factor_score,
        "calmar_score": calmar_score,
        "stability_score": stability_score,
        "trade_count_score": trade_count_score,
    }


def _penalty_components(
    canonical: Mapping[str, Any],
    config: Mapping[str, Any],
    walk_forward: Mapping[str, Any],
) -> dict[str, float]:
    max_drawdown = float(canonical.get("max_drawdown") or 0.0)
    train_oos_gap = abs(float(canonical.get("train_oos_gap") or 0.0))
    trade_count = float(canonical.get("trade_count") or 0.0)
    min_trades = float(config["min_trades"])
    turnover = float(canonical.get("turnover") or 0.0)
    trades_per_day = float(canonical.get("trades_per_day") or 0.0)
    threshold = float(config["max_turnover_penalty_threshold"])
    worst_window_profit = canonical.get("worst_window_profit")
    avg_window_profit = canonical.get("avg_window_profit")
    window_profit_std = canonical.get("window_profit_std")
    pass_rate = walk_forward.get("pass_rate")
    worst_oos_profit = walk_forward.get("worst_oos_profit")

    drawdown_penalty = _clip(max_drawdown / max(float(config["max_drawdown_limit"]), 0.001), 0.0, 2.0)
    train_oos_gap_penalty = _clip(train_oos_gap / max(float(config["max_train_oos_gap"]), 0.001), 0.0, 2.0)
    low_trade_count_penalty = _clip((min_trades - trade_count) / max(min_trades, 1.0), 0.0, 1.0)

    turnover_pressure = max(turnover / max(threshold, 1.0), trades_per_day / 20.0)
    turnover_penalty = _clip(turnover_pressure, 0.0, 2.0)

    single_window_dependency_penalty = 0.0
    if worst_window_profit is not None and avg_window_profit is not None:
        single_window_dependency_penalty += _clip(
            (float(avg_window_profit) - float(worst_window_profit)) / 0.40,
            0.0,
            2.0,
        )
    if window_profit_std is not None:
        single_window_dependency_penalty += _clip(float(window_profit_std) / 0.25, 0.0, 2.0)
    if worst_oos_profit is not None:
        single_window_dependency_penalty += _clip(abs(min(float(worst_oos_profit), 0.0)) / 0.30, 0.0, 2.0)
    if pass_rate is not None:
        single_window_dependency_penalty += _clip((0.75 - float(pass_rate)) / 0.75, 0.0, 1.0)
    single_window_dependency_penalty = _clip(single_window_dependency_penalty, 0.0, 3.0)

    return {
        "drawdown_penalty": drawdown_penalty,
        "train_oos_gap_penalty": train_oos_gap_penalty,
        "low_trade_count_penalty": low_trade_count_penalty,
        "turnover_penalty": turnover_penalty,
        "single_window_dependency_penalty": single_window_dependency_penalty,
    }


def _hard_reject_reasons(canonical: Mapping[str, Any], config: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if canonical.get("success") is False:
        reasons.append("metrics_success_false")

    total_profit = canonical.get("total_profit")
    profit_factor = canonical.get("profit_factor")
    max_drawdown = canonical.get("max_drawdown")
    trade_count = canonical.get("trade_count")
    oos_profit = canonical.get("oos_profit")
    worst_window_profit = canonical.get("worst_window_profit")

    if trade_count is None:
        reasons.append("missing_trade_count")
    elif int(trade_count) < int(config["min_trades"]):
        reasons.append("trade_count_below_min")

    if profit_factor is None:
        reasons.append("missing_profit_factor")
    elif float(profit_factor) < float(config["min_profit_factor"]):
        reasons.append("profit_factor_below_min")

    if max_drawdown is None:
        reasons.append("missing_max_drawdown")
    elif float(max_drawdown) > float(config["max_drawdown_limit"]):
        reasons.append("max_drawdown_above_limit")

    if oos_profit is not None and float(oos_profit) <= float(config["min_oos_profit"]):
        reasons.append("oos_profit_below_min")

    if (
        worst_window_profit is not None
        and float(worst_window_profit) < float(config["min_worst_window_profit"])
    ):
        reasons.append("worst_window_profit_below_min")

    if total_profit is None:
        reasons.append("missing_total_profit")
    elif float(total_profit) <= 0 and not (oos_profit is not None and float(oos_profit) > 0):
        reasons.append("nonpositive_total_profit")

    return reasons


def _data_quality_gate_reject(metrics: Mapping[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    gate = metrics.get("dataQualityGate")
    if gate is None:
        gate = metrics.get("data_quality_gate")
    if gate is None:
        return [], None
    if not isinstance(gate, Mapping):
        return ["data_quality_gate_invalid"], {"status": "INVALID", "allowed_for_evaluation": False}

    safe_gate = sanitize_mapping(gate)
    if safe_gate.get("allowed_for_evaluation") is False:
        status = safe_gate.get("status")
        if status == "MISSING":
            return ["data_quality_manifest_missing"], safe_gate
        return ["data_quality_gate_failed"], safe_gate
    return [], safe_gate


def calculate_fitness(
    metrics: dict,
    config: dict | None = None,
    genes: dict | None = None,
    walk_forward_result: dict | None = None,
) -> tuple[float | None, dict]:
    """Convert backtest or mock metrics into a bounded, explainable fitness value."""

    safe_metrics = sanitize_mapping(metrics if isinstance(metrics, Mapping) else {})
    resolved_config = _merge_config(config)
    canonical = _canonical_metrics(safe_metrics)
    walk_forward = _walk_forward_metrics(walk_forward_result)
    data_quality_rejects, data_quality_gate = _data_quality_gate_reject(safe_metrics)

    if walk_forward.get("avg_oos_profit") is not None:
        canonical["oos_profit"] = walk_forward["avg_oos_profit"]
    if walk_forward.get("worst_oos_profit") is not None:
        canonical["worst_window_profit"] = walk_forward["worst_oos_profit"]
    if walk_forward.get("avg_drawdown") is not None and canonical.get("max_drawdown") is None:
        canonical["max_drawdown"] = walk_forward["avg_drawdown"]

    scores = _score_components(canonical, walk_forward)
    penalties = _penalty_components(canonical, resolved_config, walk_forward)
    hard_rejects = _hard_reject_reasons(canonical, resolved_config)
    hard_rejects = data_quality_rejects + hard_rejects

    raw_fitness = (
        1.2 * scores["profit_score"]
        + 0.8 * scores["profit_factor_score"]
        + 0.8 * scores["calmar_score"]
        + 0.5 * scores["stability_score"]
        + 0.3 * scores["trade_count_score"]
        - 1.5 * penalties["drawdown_penalty"]
        - 1.0 * penalties["train_oos_gap_penalty"]
        - 0.7 * penalties["low_trade_count_penalty"]
        - 0.5 * penalties["turnover_penalty"]
        - 0.5 * penalties["single_window_dependency_penalty"]
    )
    raw_fitness = _clip(raw_fitness, -10.0, 10.0)
    accepted = not hard_rejects
    final_fitness = raw_fitness if accepted else min(raw_fitness, -1.0)
    final_fitness = _clip(final_fitness, -10.0, 10.0)

    breakdown = {
        "accepted": accepted,
        "reject_reason": hard_rejects[0] if hard_rejects else None,
        "hard_rejects": hard_rejects,
        "scores": scores,
        "penalties": penalties,
        "raw_metrics": safe_metrics,
        "canonical_metrics": canonical,
        "dataQualityGate": data_quality_gate,
        "config": sanitize_mapping(resolved_config),
        "genes": sanitize_mapping(genes or {}),
        "walk_forward": walk_forward,
        "final_fitness": final_fitness,
    }
    return final_fitness, breakdown
