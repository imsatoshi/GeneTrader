"""Mock multi-pair portfolio evaluation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from bollinger_evolver.backtest_adapter import MockBacktestAdapter, NormalizedBacktestResult


def _strategy_payload(strategy_config: Any) -> Mapping[str, Any]:
    if hasattr(strategy_config, "to_dict"):
        return strategy_config.to_dict()
    if isinstance(strategy_config, Mapping):
        return strategy_config
    raise TypeError("strategy_config_must_be_mapping_or_to_dict")


def _pair_seed(seed: int, pair: str) -> int:
    digest = hashlib.sha256(f"{seed}:{pair}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _snapshot(result: NormalizedBacktestResult) -> dict[str, Any]:
    return {
        "profit": float(result.profit),
        "sharpe": float(result.sharpe),
        "win_rate": float(result.win_rate),
        "max_drawdown": float(result.max_drawdown),
        "total_trades": int(result.total_trades),
        "max_consecutive_losses": int(result.max_consecutive_losses),
        "leverage": float(result.leverage),
        "risk_per_trade": float(result.risk_per_trade),
        "metadata": dict(result.metadata),
    }


def _correlation_penalty(pair_results: Mapping[str, Mapping[str, Any]]) -> float:
    if len(pair_results) <= 1:
        return 0.0
    profits = [float(item["profit"]) for item in pair_results.values()]
    drawdowns = [float(item["max_drawdown"]) for item in pair_results.values()]
    profit_range = max(profits) - min(profits)
    avg_drawdown = sum(drawdowns) / len(drawdowns)
    concentration = 1.0 / len(pair_results)
    return round(max(0.0, avg_drawdown * concentration - profit_range * 0.05), 6)


def evaluate_mock_portfolio(
    strategy_config: Any,
    *,
    pairs: Sequence[str],
    timeframe: str = "1h",
    seed: int = 0,
    trade_count: int = 100,
) -> dict[str, Any]:
    """Evaluate one strategy config across multiple mock pairs."""

    if not pairs:
        raise ValueError("pairs_required")
    if any(not isinstance(pair, str) or not pair.strip() for pair in pairs):
        raise ValueError("pairs_must_be_non_empty_strings")
    genome = _strategy_payload(strategy_config)
    pair_results: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        adapter = MockBacktestAdapter(
            pair=pair,
            timeframe=timeframe,
            trade_count=trade_count,
            seed=_pair_seed(seed, pair),
        )
        pair_results[pair] = _snapshot(adapter.run_backtest(genome))

    portfolio_profit = sum(float(item["profit"]) for item in pair_results.values()) / len(pair_results)
    max_pair_drawdown = max(float(item["max_drawdown"]) for item in pair_results.values())
    avg_pair_drawdown = sum(float(item["max_drawdown"]) for item in pair_results.values()) / len(pair_results)
    correlation_penalty = _correlation_penalty(pair_results)
    portfolio_drawdown = min(1.0, max_pair_drawdown * 0.65 + avg_pair_drawdown * 0.35 + correlation_penalty)
    result = {
        "schema_version": "mock-portfolio-evaluation/v1",
        "source": "mock-backtest-adapter",
        "pairs": list(pairs),
        "timeframe": timeframe,
        "portfolio_profit": round(portfolio_profit, 6),
        "portfolio_drawdown": round(portfolio_drawdown, 6),
        "pair_results": pair_results,
        "correlation_penalty": correlation_penalty,
    }
    json.dumps(result, sort_keys=True)
    return result
