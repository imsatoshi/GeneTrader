"""Fixture-only normalizer for Freqtrade-like backtest reports.

This module parses static JSON fixtures only. It does not import Freqtrade,
execute commands, scan result directories, read configs, or connect to any
exchange/API.
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bollinger_evolver.backtest_adapter import (
    NormalizedBacktestResult,
    validate_normalized_backtest_result,
)


def load_freqtrade_backtest_report_json(path: str | Path) -> Mapping[str, Any]:
    """Load one explicitly provided JSON fixture file."""

    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, Mapping):
        raise ValueError("freqtrade_backtest_report_must_be_json_object")
    return data


def _looks_like_backtest_report(data: Any) -> bool:
    return isinstance(data, Mapping) and isinstance(data.get("strategy"), Mapping)


def load_freqtrade_backtest_report_from_zip_fixture(path: str | Path) -> Mapping[str, Any]:
    """Load a Freqtrade-like report JSON from a static zip fixture.

    The archive is read in memory and member files are never written to disk.
    """

    archive_path = Path(path)
    json_reports: list[Mapping[str, Any]] = []

    with zipfile.ZipFile(archive_path, "r") as archive:
        json_members = [
            member
            for member in archive.infolist()
            if not member.is_dir() and member.filename.lower().endswith(".json")
        ]
        if not json_members:
            raise ValueError("freqtrade_zip_fixture_has_no_json_report")

        for member in json_members:
            with archive.open(member, "r") as handle:
                try:
                    data = json.loads(handle.read().decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
            if _looks_like_backtest_report(data):
                return data
            if isinstance(data, Mapping):
                json_reports.append(data)

    if json_reports:
        raise ValueError("freqtrade_zip_fixture_report_not_found")
    raise ValueError("freqtrade_zip_fixture_json_invalid")


def calculate_max_consecutive_losses_from_trades(
    trades: list[Mapping[str, Any]],
) -> int:
    """Derive the longest consecutive loss streak from trade profit ratios."""

    max_streak = 0
    current_streak = 0
    for trade in trades:
        if "profit_ratio" not in trade:
            raise ValueError("trade_profit_ratio_missing")
        profit_ratio = trade["profit_ratio"]
        if isinstance(profit_ratio, bool) or not isinstance(profit_ratio, (int, float)):
            raise ValueError("trade_profit_ratio_must_be_numeric")
        if float(profit_ratio) < 0.0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
    return max_streak


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}_must_be_numeric")
    return float(value)


def _non_negative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name}_must_be_int")
    if value < 0:
        raise ValueError(f"{field_name}_must_be_non_negative")
    return value


def _strategy_payload(report: Mapping[str, Any], strategy_name: str | None) -> tuple[str, Mapping[str, Any]]:
    strategies = report.get("strategy")
    if not isinstance(strategies, Mapping) or not strategies:
        raise ValueError("freqtrade_strategy_section_missing")

    if strategy_name is not None:
        selected = strategies.get(strategy_name)
        if not isinstance(selected, Mapping):
            raise ValueError(f"freqtrade_strategy_not_found: {strategy_name}")
        return strategy_name, selected

    if len(strategies) != 1:
        raise ValueError("freqtrade_strategy_name_required")
    selected_name, selected_payload = next(iter(strategies.items()))
    if not isinstance(selected_payload, Mapping):
        raise ValueError(f"freqtrade_strategy_payload_invalid: {selected_name}")
    return str(selected_name), selected_payload


def _trades(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_trades = payload.get("trades", [])
    if raw_trades is None:
        return []
    if not isinstance(raw_trades, list) or not all(isinstance(trade, Mapping) for trade in raw_trades):
        raise ValueError("freqtrade_trades_must_be_list_of_objects")
    return raw_trades


def normalize_freqtrade_backtest_report(
    report: Mapping[str, Any],
    *,
    strategy_name: str | None = None,
    default_leverage: float = 1.0,
    default_risk_per_trade: float = 0.01,
) -> NormalizedBacktestResult:
    """Normalize a Freqtrade-like fixture report into the internal result contract."""

    selected_name, payload = _strategy_payload(report, strategy_name)
    trades = _trades(payload)

    raw_profit_field = "profit_total" if "profit_total" in payload else "total_profit"
    if raw_profit_field not in payload:
        raise ValueError("freqtrade_profit_metric_missing")
    profit = _finite_float(payload[raw_profit_field], field_name=raw_profit_field)

    raw_drawdown_field = "max_drawdown" if "max_drawdown" in payload else "max_drawdown_account"
    if raw_drawdown_field not in payload:
        raise ValueError("freqtrade_drawdown_metric_missing")
    max_drawdown = _finite_float(payload[raw_drawdown_field], field_name=raw_drawdown_field)

    total_trades_source = "total_trades" if "total_trades" in payload else "trades_length"
    if "total_trades" in payload:
        total_trades = _non_negative_int(payload["total_trades"], field_name="total_trades")
    else:
        total_trades = len(trades)

    sharpe = _finite_float(payload.get("sharpe", 0.0), field_name="sharpe")

    if "win_rate" in payload:
        win_rate = _finite_float(payload["win_rate"], field_name="win_rate")
        win_rate_source = "win_rate"
    else:
        wins = _non_negative_int(payload.get("wins", 0), field_name="wins")
        win_rate = 0.0 if total_trades == 0 else wins / total_trades
        win_rate_source = "wins_total_trades"

    if "max_consecutive_losses" in payload:
        max_consecutive_losses = _non_negative_int(
            payload["max_consecutive_losses"],
            field_name="max_consecutive_losses",
        )
        loss_streak_source = "max_consecutive_losses"
    else:
        max_consecutive_losses = calculate_max_consecutive_losses_from_trades(trades)
        loss_streak_source = "trades_profit_ratio"

    leverage = _finite_float(payload.get("leverage", default_leverage), field_name="leverage")
    risk_per_trade = _finite_float(
        payload.get("risk_per_trade", default_risk_per_trade),
        field_name="risk_per_trade",
    )
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
            "source": "freqtrade_fixture",
            "strategy_name": selected_name,
            "raw_profit_field": raw_profit_field,
            "raw_drawdown_field": raw_drawdown_field,
            "total_trades_source": total_trades_source,
            "win_rate_source": win_rate_source,
            "loss_streak_source": loss_streak_source,
        },
    )
    return validate_normalized_backtest_result(result)


class FreqtradeFixtureBacktestAdapter:
    """BacktestAdapter-compatible wrapper around one static fixture report."""

    def __init__(
        self,
        report: Mapping[str, Any] | str | Path,
        *,
        strategy_name: str | None = None,
        default_leverage: float = 1.0,
        default_risk_per_trade: float = 0.01,
    ) -> None:
        if isinstance(report, (str, Path)):
            report_path = Path(report)
            if report_path.suffix.lower() == ".zip":
                self.report = load_freqtrade_backtest_report_from_zip_fixture(report_path)
            else:
                self.report = load_freqtrade_backtest_report_json(report_path)
        else:
            self.report = report
        self.strategy_name = strategy_name
        self.default_leverage = default_leverage
        self.default_risk_per_trade = default_risk_per_trade

    def run_backtest(self, genome: Mapping[str, Any]) -> NormalizedBacktestResult:
        result = normalize_freqtrade_backtest_report(
            self.report,
            strategy_name=self.strategy_name,
            default_leverage=self.default_leverage,
            default_risk_per_trade=self.default_risk_per_trade,
        )
        metadata = dict(result.metadata)
        metadata.update(
            {
                "adapter": "FreqtradeFixtureBacktestAdapter",
                "genome_received": bool(genome),
                "genome_id": str(genome.get("genome_id", "unknown")) if genome else "unknown",
            }
        )
        return validate_normalized_backtest_result(
            NormalizedBacktestResult(
                profit=result.profit,
                sharpe=result.sharpe,
                win_rate=result.win_rate,
                max_drawdown=result.max_drawdown,
                total_trades=result.total_trades,
                max_consecutive_losses=result.max_consecutive_losses,
                leverage=result.leverage,
                risk_per_trade=result.risk_per_trade,
                metadata=metadata,
            )
        )
