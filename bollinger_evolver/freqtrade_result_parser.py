"""Parse Freqtrade-like backtest payloads into NormalizedBacktestResult.

The parser accepts already-loaded JSON dictionaries only. It does not read
files, import Freqtrade, start subprocesses, or inspect result directories.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from bollinger_evolver.backtest_adapter import (
    NormalizedBacktestResult,
    validate_normalized_backtest_result,
)


PROFIT_FIELDS = ("profit_total", "total_profit", "profit_total_abs")
DRAWDOWN_FIELDS = ("max_drawdown", "max_drawdown_account")
SHARPE_FIELDS = ("sharpe",)
WIN_RATE_FIELDS = ("win_rate", "winrate")
TOTAL_TRADES_FIELDS = ("total_trades", "trades_length")
LOSS_STREAK_FIELDS = ("max_consecutive_losses", "max_loss_streak")


def _select_strategy_payload(payload: Mapping[str, Any], strategy_name: str | None) -> tuple[str | None, Mapping[str, Any]]:
    strategies = payload.get("strategy")
    if not isinstance(strategies, Mapping):
        return None, payload
    if strategy_name is not None:
        selected = strategies.get(strategy_name)
        if not isinstance(selected, Mapping):
            raise ValueError(f"freqtrade_strategy_not_found:{strategy_name}")
        return strategy_name, selected
    if len(strategies) != 1:
        raise ValueError("freqtrade_strategy_name_required")
    selected_name, selected_payload = next(iter(strategies.items()))
    if not isinstance(selected_payload, Mapping):
        raise ValueError(f"freqtrade_strategy_payload_invalid:{selected_name}")
    return str(selected_name), selected_payload


def _field(payload: Mapping[str, Any], field_names: tuple[str, ...], *, metric_name: str) -> Any:
    for field_name in field_names:
        if field_name in payload:
            return payload[field_name]
    raise ValueError(f"freqtrade_metric_missing:{metric_name}")


def _field_name(payload: Mapping[str, Any], field_names: tuple[str, ...], *, metric_name: str) -> str:
    for field_name in field_names:
        if field_name in payload:
            return field_name
    raise ValueError(f"freqtrade_metric_missing:{metric_name}")


def _number(value: Any, *, metric_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"freqtrade_metric_non_numeric:{metric_name}")
    return float(value)


def _non_negative_int(value: Any, *, metric_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"freqtrade_metric_non_numeric:{metric_name}")
    if value < 0:
        raise ValueError(f"freqtrade_metric_negative:{metric_name}")
    return value


def parse_freqtrade_result_payload(
    payload: Mapping[str, Any],
    *,
    strategy_name: str | None = None,
    default_leverage: float = 1.0,
    default_risk_per_trade: float = 0.01,
) -> NormalizedBacktestResult:
    """Parse a Freqtrade-like JSON payload into the normalized result contract."""

    if not isinstance(payload, Mapping):
        raise TypeError("freqtrade_payload_must_be_mapping")
    selected_name, metrics = _select_strategy_payload(payload, strategy_name)
    profit_field = _field_name(metrics, PROFIT_FIELDS, metric_name="profit")
    drawdown_field = _field_name(metrics, DRAWDOWN_FIELDS, metric_name="max_drawdown")

    profit = _number(_field(metrics, PROFIT_FIELDS, metric_name="profit"), metric_name="profit")
    max_drawdown = _number(_field(metrics, DRAWDOWN_FIELDS, metric_name="max_drawdown"), metric_name="max_drawdown")
    sharpe = _number(_field(metrics, SHARPE_FIELDS, metric_name="sharpe"), metric_name="sharpe")
    win_rate = _number(_field(metrics, WIN_RATE_FIELDS, metric_name="win_rate"), metric_name="win_rate")
    if win_rate > 1.0 and win_rate <= 100.0:
        win_rate = win_rate / 100.0
    total_trades = _non_negative_int(
        _field(metrics, TOTAL_TRADES_FIELDS, metric_name="total_trades"),
        metric_name="total_trades",
    )
    max_consecutive_losses = _non_negative_int(
        _field(metrics, LOSS_STREAK_FIELDS, metric_name="max_consecutive_losses"),
        metric_name="max_consecutive_losses",
    )
    leverage = _number(metrics.get("leverage", default_leverage), metric_name="leverage")
    risk_per_trade = _number(metrics.get("risk_per_trade", default_risk_per_trade), metric_name="risk_per_trade")

    result = NormalizedBacktestResult(
        profit=profit,
        sharpe=sharpe,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        total_trades=total_trades,
        max_consecutive_losses=max_consecutive_losses,
        leverage=leverage,
        risk_per_trade=risk_per_trade,
        metadata={
            "source": "freqtrade_result_parser",
            "strategy_name": selected_name,
            "profit_field": profit_field,
            "drawdown_field": drawdown_field,
        },
    )
    json.dumps(result.to_dict(), sort_keys=True)
    return validate_normalized_backtest_result(result)
