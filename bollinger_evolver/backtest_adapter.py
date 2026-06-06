"""Mock backtest adapter for synthetic trade-sequence evaluation.

This module is intentionally offline-only. It does not read OHLCV data, call
Freqtrade, connect to exchanges, or write artifacts.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from dataclasses import field
from typing import Any, Mapping, Protocol

from bollinger_evolver.fitness import (
    FitnessEvaluation,
    MockBacktestMetrics,
    calculate_risk_aware_fitness_breakdown,
)
from bollinger_evolver.genome import Genome
from bollinger_evolver.strategy_factory import StrategyConfig, strategy_config_from_genome


@dataclass(frozen=True)
class NormalizedBacktestResult:
    """Stable JSON-safe result shape for future real-backtest adapters."""

    profit: float
    sharpe: float
    win_rate: float
    max_drawdown: float
    total_trades: int
    max_consecutive_losses: int
    leverage: float
    risk_per_trade: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BacktestAdapter(Protocol):
    """Protocol for adapters that normalize backtest output."""

    def run_backtest(self, genome: Mapping[str, Any]) -> NormalizedBacktestResult:
        ...


@dataclass(frozen=True)
class SyntheticTrade:
    trade_id: str
    pair: str
    timeframe: str
    entry_index: int
    exit_index: int
    direction: str
    entry_price: float
    exit_price: float
    return_pct: float
    leverage: float
    risk_per_trade: float
    pnl_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MockBacktestResult:
    schema_version: str
    source: str
    genome_id: str
    strategy_id: str
    pair: str
    timeframe: str
    trade_count: int
    profit: float
    drawdown: float
    sharpe: float
    win_rate: float
    max_loss_streak: int
    leverage: float
    risk_per_trade: float
    fitness: float
    fitness_components: dict[str, float]
    trades: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_strategy_config(strategy_config: StrategyConfig | Genome | dict[str, Any]) -> StrategyConfig:
    if isinstance(strategy_config, StrategyConfig):
        return strategy_config
    if isinstance(strategy_config, Genome):
        return strategy_config_from_genome(strategy_config)
    if isinstance(strategy_config, dict):
        parameters = dict(strategy_config.get("parameters") or {})
        return StrategyConfig(
            genome_id=str(strategy_config.get("genome_id", "dict-strategy")),
            bollinger_window=int(strategy_config.get("bollinger_window", parameters.get("bb_window", 20))),
            bollinger_stddev=float(strategy_config.get("bollinger_stddev", parameters.get("bb_stddev", 2.0))),
            stoploss=float(strategy_config.get("stoploss", parameters.get("stop_loss_pct", 0.03))),
            takeprofit=float(strategy_config.get("takeprofit", parameters.get("take_profit_pct", 0.08))),
            leverage=float(strategy_config.get("leverage", parameters.get("leverage", 1.0))),
            risk_per_trade=float(strategy_config.get("risk_per_trade", parameters.get("risk_per_trade", 0.01))),
            parameters=parameters
            or {
                "bb_window": int(strategy_config.get("bollinger_window", 20)),
                "bb_stddev": float(strategy_config.get("bollinger_stddev", 2.0)),
                "stop_loss_pct": float(strategy_config.get("stoploss", 0.03)),
                "take_profit_pct": float(strategy_config.get("takeprofit", 0.08)),
                "leverage": float(strategy_config.get("leverage", 1.0)),
                "risk_per_trade": float(strategy_config.get("risk_per_trade", 0.01)),
            },
        )
    raise TypeError("strategy_config_must_be_strategy_config_genome_or_dict")


def _stable_seed(seed: int, config: StrategyConfig, namespace: str) -> int:
    payload = json.dumps(
        {"seed": int(seed), "namespace": namespace, "strategy": config.to_dict()},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _is_json_safe(value: Any) -> bool:
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}_must_be_finite_number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name}_must_be_finite_number")
    return numeric


def validate_normalized_backtest_result(
    result: NormalizedBacktestResult,
) -> NormalizedBacktestResult:
    """Validate a normalized backtest result and return it unchanged."""

    profit = _finite_float(result.profit, field_name="profit")
    sharpe = _finite_float(result.sharpe, field_name="sharpe")
    win_rate = _finite_float(result.win_rate, field_name="win_rate")
    max_drawdown = _finite_float(result.max_drawdown, field_name="max_drawdown")
    leverage = _finite_float(result.leverage, field_name="leverage")
    risk_per_trade = _finite_float(result.risk_per_trade, field_name="risk_per_trade")

    if not 0.0 <= win_rate <= 1.0:
        raise ValueError("win_rate_out_of_bounds")
    if not 0.0 <= max_drawdown <= 1.0:
        raise ValueError("max_drawdown_out_of_bounds")
    if not isinstance(result.total_trades, int) or isinstance(result.total_trades, bool) or result.total_trades < 0:
        raise ValueError("total_trades_must_be_non_negative_int")
    if (
        not isinstance(result.max_consecutive_losses, int)
        or isinstance(result.max_consecutive_losses, bool)
        or result.max_consecutive_losses < 0
    ):
        raise ValueError("max_consecutive_losses_must_be_non_negative_int")
    if leverage < 0.0:
        raise ValueError("leverage_must_be_non_negative")
    if risk_per_trade < 0.0:
        raise ValueError("risk_per_trade_must_be_non_negative")
    if not isinstance(result.metadata, Mapping) or not _is_json_safe(dict(result.metadata)):
        raise ValueError("metadata_must_be_json_safe_mapping")
    # Keep local variables intentionally used by validation above.
    _ = profit, sharpe
    return result


def _genome_mapping_to_strategy_config(genome: Mapping[str, Any]) -> StrategyConfig:
    parameters = {
        "bb_window": int(genome.get("bb_window", genome.get("bb_period", genome.get("bollinger_window", 20)))),
        "bb_stddev": float(genome.get("bb_stddev", genome.get("bollinger_stddev", 2.0))),
        "stop_loss_pct": float(genome.get("stop_loss_pct", genome.get("stop_loss", genome.get("stoploss", 0.03)))),
        "take_profit_pct": float(
            genome.get("take_profit_pct", genome.get("take_profit", genome.get("takeprofit", 0.08)))
        ),
        "leverage": float(genome.get("leverage", 1.0)),
        "risk_per_trade": float(genome.get("risk_per_trade", 0.01)),
    }
    return StrategyConfig(
        genome_id=str(genome.get("genome_id", "mapping-genome")),
        bollinger_window=int(parameters["bb_window"]),
        bollinger_stddev=float(parameters["bb_stddev"]),
        stoploss=float(parameters["stop_loss_pct"]),
        takeprofit=float(parameters["take_profit_pct"]),
        leverage=float(parameters["leverage"]),
        risk_per_trade=float(parameters["risk_per_trade"]),
        parameters=parameters,
    )


def generate_synthetic_trades(
    strategy_config: StrategyConfig | Genome | dict[str, Any],
    *,
    pair: str = "BTC/USDT",
    timeframe: str = "1h",
    trade_count: int = 100,
    seed: int = 0,
) -> list[SyntheticTrade]:
    """Generate deterministic synthetic trades from a strategy config."""

    if trade_count < 0:
        raise ValueError("trade_count_must_be_non_negative")

    config = _as_strategy_config(strategy_config)
    rng = random.Random(_stable_seed(seed, config, f"{pair}:{timeframe}:trades"))
    trades: list[SyntheticTrade] = []
    if trade_count == 0:
        return trades

    window_edge = 1.0 - abs(float(config.bollinger_window) - 34.0) / 80.0
    stddev_edge = 1.0 - abs(float(config.bollinger_stddev) - 2.1) / 3.5
    reward_risk = config.takeprofit / max(config.stoploss, 0.001)
    leverage_drag = max(0.0, config.leverage - 3.0) * 0.001 + config.risk_per_trade * 0.03
    expected_return = (
        (window_edge * 0.0025)
        + (stddev_edge * 0.002)
        + min(reward_risk, 5.0) * 0.0008
        - config.risk_per_trade * 0.08
        - leverage_drag
    )
    volatility = _clip((4.0 - config.bollinger_stddev) * 0.004 + config.risk_per_trade * 0.45, 0.003, 0.05)

    price = 100.0
    for index in range(trade_count):
        direction = "long" if rng.random() >= 0.12 else "short"
        raw_return = rng.gauss(expected_return, volatility)
        return_pct = _clip(raw_return, -config.stoploss, config.takeprofit)
        pnl_pct = _clip(return_pct * config.leverage, -0.95, 2.0)
        exit_price = price * (1.0 + return_pct)
        trades.append(
            SyntheticTrade(
                trade_id=f"{config.genome_id}-trade-{index:04d}",
                pair=pair,
                timeframe=timeframe,
                entry_index=index * 2,
                exit_index=index * 2 + 1,
                direction=direction,
                entry_price=round(price, 6),
                exit_price=round(exit_price, 6),
                return_pct=round(return_pct, 6),
                leverage=round(config.leverage, 6),
                risk_per_trade=round(config.risk_per_trade, 6),
                pnl_pct=round(pnl_pct, 6),
            )
        )
        price = max(1.0, exit_price)

    return trades


def calculate_backtest_metrics(
    trades: list[SyntheticTrade],
    *,
    leverage: float,
    risk_per_trade: float,
) -> dict[str, int | float]:
    """Calculate JSON-safe mock backtest metrics from synthetic trades."""

    if not trades:
        return {
            "profit": 0.0,
            "drawdown": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "max_loss_streak": 0,
            "trade_count": 0,
        }

    pnl_values = [float(trade.pnl_pct) for trade in trades]
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    current_loss_streak = 0
    max_loss_streak = 0
    wins = 0

    for pnl in pnl_values:
        if pnl > 0:
            wins += 1
            current_loss_streak = 0
        else:
            current_loss_streak += 1
            max_loss_streak = max(max_loss_streak, current_loss_streak)
        equity = max(0.01, equity * (1.0 + pnl))
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)

    mean_return = sum(pnl_values) / len(pnl_values)
    variance = sum((value - mean_return) ** 2 for value in pnl_values) / len(pnl_values)
    stddev = math.sqrt(variance)
    sharpe = 0.0 if stddev == 0 else (mean_return / stddev) * math.sqrt(len(pnl_values))

    return {
        "profit": round(equity - 1.0, 6),
        "drawdown": round(max_drawdown, 6),
        "sharpe": round(sharpe, 6),
        "win_rate": round(wins / len(pnl_values), 6),
        "max_loss_streak": int(max_loss_streak),
        "trade_count": len(pnl_values),
    }


class MockBacktestAdapter:
    """Deterministic adapter that emits the normalized future-backtest contract."""

    def __init__(
        self,
        *,
        pair: str = "BTC/USDT",
        timeframe: str = "1h",
        trade_count: int = 100,
        seed: int = 0,
    ) -> None:
        self.pair = pair
        self.timeframe = timeframe
        self.trade_count = int(trade_count)
        self.seed = int(seed)

    def run_backtest(self, genome: Mapping[str, Any]) -> NormalizedBacktestResult:
        config = _genome_mapping_to_strategy_config(genome)
        trades = generate_synthetic_trades(
            config,
            pair=self.pair,
            timeframe=self.timeframe,
            trade_count=self.trade_count,
            seed=self.seed,
        )
        metrics = calculate_backtest_metrics(
            trades,
            leverage=config.leverage,
            risk_per_trade=config.risk_per_trade,
        )
        loss_streak = max(
            int(metrics["max_loss_streak"]),
            int(round(config.risk_per_trade * 50.0 + max(0.0, config.leverage - 3.0) * 0.5)),
        )
        result = NormalizedBacktestResult(
            profit=float(metrics["profit"]),
            sharpe=float(metrics["sharpe"]),
            win_rate=float(metrics["win_rate"]),
            max_drawdown=float(metrics["drawdown"]),
            total_trades=int(metrics["trade_count"]),
            max_consecutive_losses=loss_streak,
            leverage=round(config.leverage, 6),
            risk_per_trade=round(config.risk_per_trade, 6),
            metadata={
                "schema_version": "normalized-backtest-result/v1",
                "source": "mock-backtest-adapter",
                "genome_id": config.genome_id,
                "pair": self.pair,
                "timeframe": self.timeframe,
                "trade_count": self.trade_count,
                "seed": self.seed,
            },
        )
        return validate_normalized_backtest_result(result)


def run_mock_backtest(
    strategy_config: StrategyConfig | Genome | dict[str, Any],
    *,
    pair: str = "BTC/USDT",
    timeframe: str = "1h",
    trade_count: int = 100,
    seed: int = 0,
) -> MockBacktestResult:
    """Run a deterministic synthetic backtest and risk-aware scoring pass."""

    config = _as_strategy_config(strategy_config)
    trades = generate_synthetic_trades(
        config,
        pair=pair,
        timeframe=timeframe,
        trade_count=trade_count,
        seed=seed,
    )
    metrics = calculate_backtest_metrics(
        trades,
        leverage=config.leverage,
        risk_per_trade=config.risk_per_trade,
    )
    fitness_components = calculate_risk_aware_fitness_breakdown(
        profit=float(metrics["profit"]),
        drawdown=float(metrics["drawdown"]),
        sharpe=float(metrics["sharpe"]),
        win_rate=float(metrics["win_rate"]),
        leverage=config.leverage,
        risk_per_trade=config.risk_per_trade,
        max_loss_streak=int(metrics["max_loss_streak"]),
    )

    return MockBacktestResult(
        schema_version="mock-backtest-result/v1",
        source="synthetic-trade-sequence",
        genome_id=config.genome_id,
        strategy_id=f"strategy-{config.genome_id}",
        pair=pair,
        timeframe=timeframe,
        trade_count=int(metrics["trade_count"]),
        profit=float(metrics["profit"]),
        drawdown=float(metrics["drawdown"]),
        sharpe=float(metrics["sharpe"]),
        win_rate=float(metrics["win_rate"]),
        max_loss_streak=int(metrics["max_loss_streak"]),
        leverage=round(config.leverage, 6),
        risk_per_trade=round(config.risk_per_trade, 6),
        fitness=fitness_components["final_fitness"],
        fitness_components=fitness_components,
        trades=[trade.to_dict() for trade in trades],
    )


class MockBacktestEvaluator:
    """GA evaluator backed by synthetic trade-sequence metrics."""

    def __init__(
        self,
        *,
        pair: str = "BTC/USDT",
        timeframe: str = "1h",
        trade_count: int = 100,
        seed: int = 0,
    ) -> None:
        self.pair = pair
        self.timeframe = timeframe
        self.trade_count = int(trade_count)
        self.seed = int(seed)

    def evaluate(self, genome: Genome) -> FitnessEvaluation:
        result = run_mock_backtest(
            strategy_config_from_genome(genome),
            pair=self.pair,
            timeframe=self.timeframe,
            trade_count=self.trade_count,
            seed=self.seed,
        )
        metrics = MockBacktestMetrics(
            profit=result.profit,
            drawdown=result.drawdown,
            sharpe=result.sharpe,
            win_rate=result.win_rate,
            total_trades=result.trade_count,
            max_consecutive_losses=result.max_loss_streak,
            leverage=result.leverage,
            risk_per_trade=result.risk_per_trade,
            fitness_components=result.fitness_components,
        )
        return FitnessEvaluation(genome=genome, metrics=metrics, fitness=result.fitness)


class AdapterBackedMockEvaluator:
    """GA evaluator that consumes a normalized backtest adapter contract."""

    def __init__(self, adapter: BacktestAdapter | None = None) -> None:
        self.adapter = adapter or MockBacktestAdapter()

    def evaluate(self, genome: Genome) -> FitnessEvaluation:
        result = validate_normalized_backtest_result(
            self.adapter.run_backtest({"genome_id": genome.genome_id, **dict(genome.parameters)})
        )
        fitness_components = calculate_risk_aware_fitness_breakdown(
            profit=result.profit,
            drawdown=result.max_drawdown,
            sharpe=result.sharpe,
            win_rate=result.win_rate,
            leverage=result.leverage,
            risk_per_trade=result.risk_per_trade,
            max_loss_streak=result.max_consecutive_losses,
        )
        metrics = MockBacktestMetrics(
            profit=result.profit,
            drawdown=result.max_drawdown,
            sharpe=result.sharpe,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            max_consecutive_losses=result.max_consecutive_losses,
            leverage=result.leverage,
            risk_per_trade=result.risk_per_trade,
            fitness_components=fitness_components,
        )
        return FitnessEvaluation(genome=genome, metrics=metrics, fitness=fitness_components["final_fitness"])
