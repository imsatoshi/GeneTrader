"""Deterministic mock evaluator for the lightweight GA execution framework."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass

from bollinger_evolver.genome import Genome, validate_genome


@dataclass(frozen=True)
class MockBacktestMetrics:
    profit: float
    drawdown: float
    sharpe: float
    win_rate: float
    total_trades: int = 0
    max_consecutive_losses: int = 0
    leverage: float = 1.0
    risk_per_trade: float = 0.0
    fitness_components: dict[str, float] | None = None


@dataclass(frozen=True)
class RiskAwareFitnessConfig:
    profit_weight: float = 1.0
    sharpe_weight: float = 0.25
    win_rate_weight: float = 0.10
    drawdown_penalty_weight: float = 2.0
    leverage_penalty_weight: float = 0.35
    risk_per_trade_penalty_weight: float = 0.50
    loss_streak_penalty_weight: float = 0.15
    max_preferred_leverage: float = 3.0
    max_preferred_risk_per_trade: float = 0.02


@dataclass(frozen=True)
class FitnessEvaluation:
    genome: Genome
    metrics: MockBacktestMetrics
    fitness: float

    def to_dict(self) -> dict[str, object]:
        return {
            "genome_id": self.genome.genome_id,
            "parameters": dict(self.genome.parameters),
            "metrics": asdict(self.metrics),
            "fitness": self.fitness,
        }


def _stable_seed(seed: int, genome: Genome) -> int:
    payload = json.dumps(
        {"seed": seed, "genome_id": genome.genome_id, "parameters": genome.parameters},
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _clip(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def calculate_risk_aware_fitness_breakdown(
    metrics: MockBacktestMetrics | None = None,
    *,
    profit: float | None = None,
    drawdown: float | None = None,
    sharpe: float | None = None,
    win_rate: float | None = None,
    leverage: float | None = None,
    risk_per_trade: float | None = None,
    max_loss_streak: int | None = None,
    config: RiskAwareFitnessConfig | None = None,
) -> dict[str, float]:
    """Return JSON-safe components for risk-aware fitness scoring."""

    resolved_config = config or RiskAwareFitnessConfig()
    resolved_profit = float(profit if profit is not None else (metrics.profit if metrics else 0.0))
    resolved_drawdown = float(drawdown if drawdown is not None else (metrics.drawdown if metrics else 0.0))
    resolved_sharpe = float(sharpe if sharpe is not None else (metrics.sharpe if metrics else 0.0))
    resolved_win_rate = float(win_rate if win_rate is not None else (metrics.win_rate if metrics else 0.0))
    resolved_leverage = float(leverage if leverage is not None else (metrics.leverage if metrics else 1.0))
    resolved_risk = float(risk_per_trade if risk_per_trade is not None else (metrics.risk_per_trade if metrics else 0.0))
    resolved_loss_streak = int(
        max_loss_streak
        if max_loss_streak is not None
        else (metrics.max_consecutive_losses if metrics else 0)
    )

    profit_component = resolved_config.profit_weight * resolved_profit
    sharpe_component = resolved_config.sharpe_weight * resolved_sharpe
    win_rate_component = resolved_config.win_rate_weight * resolved_win_rate
    drawdown_penalty = resolved_config.drawdown_penalty_weight * resolved_drawdown
    leverage_penalty = resolved_config.leverage_penalty_weight * max(
        0.0,
        resolved_leverage - resolved_config.max_preferred_leverage,
    )
    risk_per_trade_penalty = resolved_config.risk_per_trade_penalty_weight * max(
        0.0,
        resolved_risk - resolved_config.max_preferred_risk_per_trade,
    )
    loss_streak_penalty = resolved_config.loss_streak_penalty_weight * max(0, resolved_loss_streak)
    final_fitness = (
        profit_component
        + sharpe_component
        + win_rate_component
        - drawdown_penalty
        - leverage_penalty
        - risk_per_trade_penalty
        - loss_streak_penalty
    )

    return {
        "profit_component": round(profit_component, 6),
        "sharpe_component": round(sharpe_component, 6),
        "win_rate_component": round(win_rate_component, 6),
        "drawdown_penalty": round(drawdown_penalty, 6),
        "leverage_penalty": round(leverage_penalty, 6),
        "risk_per_trade_penalty": round(risk_per_trade_penalty, 6),
        "loss_streak_penalty": round(loss_streak_penalty, 6),
        "final_fitness": round(final_fitness, 6),
    }


def calculate_risk_aware_fitness(
    metrics: MockBacktestMetrics | None = None,
    *,
    profit: float | None = None,
    drawdown: float | None = None,
    sharpe: float | None = None,
    win_rate: float | None = None,
    leverage: float | None = None,
    risk_per_trade: float | None = None,
    max_loss_streak: int | None = None,
    config: RiskAwareFitnessConfig | None = None,
) -> float:
    """Score mock metrics with drawdown, leverage, position-risk, and loss-streak penalties."""

    return calculate_risk_aware_fitness_breakdown(
        metrics,
        profit=profit,
        drawdown=drawdown,
        sharpe=sharpe,
        win_rate=win_rate,
        leverage=leverage,
        risk_per_trade=risk_per_trade,
        max_loss_streak=max_loss_streak,
        config=config,
    )["final_fitness"]


def calculate_mock_fitness(metrics: MockBacktestMetrics, *, leverage: float) -> float:
    """Score mock metrics with simple risk pressure and no real backtest dependency."""

    return calculate_risk_aware_fitness(metrics, leverage=leverage, risk_per_trade=metrics.risk_per_trade)


class MockEvaluator:
    """Deterministic evaluator that produces plausible metrics from genome parameters."""

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)

    def evaluate(self, genome: Genome) -> FitnessEvaluation:
        validate_genome(genome)
        rng = random.Random(_stable_seed(self.seed, genome))
        params = genome.parameters

        bb_window = float(params["bb_window"])
        bb_stddev = float(params["bb_stddev"])
        stop_loss = float(params["stop_loss_pct"])
        take_profit = float(params["take_profit_pct"])
        leverage = float(params["leverage"])
        risk = float(params["risk_per_trade"])

        window_edge = 1.0 - abs(bb_window - 34.0) / 80.0
        stddev_edge = 1.0 - abs(bb_stddev - 2.1) / 3.5
        reward_risk_edge = take_profit / max(stop_loss, 0.001)
        noise = rng.uniform(-0.035, 0.035)

        profit = _clip((window_edge * 0.08) + (stddev_edge * 0.06) + min(reward_risk_edge, 5.0) * 0.025 - risk + noise, -0.30, 0.65)
        drawdown = _clip((stop_loss * 0.8) + (risk * leverage * 1.7) + rng.uniform(0.005, 0.09), 0.01, 0.85)
        sharpe = _clip((profit / max(drawdown, 0.01)) + rng.uniform(-0.25, 0.25), -2.5, 4.5)
        win_rate = _clip(0.43 + profit * 0.55 - drawdown * 0.16 + rng.uniform(-0.05, 0.05), 0.05, 0.95)
        max_consecutive_losses = int(
            _clip(round(drawdown * 8.0 + risk * 100.0 + rng.uniform(0.0, 3.0)), 0.0, 12.0)
        )

        metrics = MockBacktestMetrics(
            profit=round(profit, 6),
            drawdown=round(drawdown, 6),
            sharpe=round(sharpe, 6),
            win_rate=round(win_rate, 6),
            max_consecutive_losses=max_consecutive_losses,
            leverage=round(leverage, 6),
            risk_per_trade=round(risk, 6),
            fitness_components=calculate_risk_aware_fitness_breakdown(
                profit=profit,
                drawdown=drawdown,
                sharpe=sharpe,
                win_rate=win_rate,
                leverage=leverage,
                risk_per_trade=risk,
                max_loss_streak=max_consecutive_losses,
            ),
        )
        return FitnessEvaluation(
            genome=genome,
            metrics=metrics,
            fitness=metrics.fitness_components["final_fitness"],
        )


def evaluate_genome_fitness(genome: Genome, evaluator: MockEvaluator | None = None) -> FitnessEvaluation:
    """Evaluate one genome with the deterministic mock evaluator."""

    return (evaluator or MockEvaluator()).evaluate(genome)


def evaluate_population_fitness(
    population: list[Genome],
    evaluator: MockEvaluator | None = None,
) -> list[FitnessEvaluation]:
    """Evaluate a population of genomes with deterministic mock metrics."""

    resolved_evaluator = evaluator or MockEvaluator()
    return [resolved_evaluator.evaluate(genome) for genome in population]


def build_fitness_summary(evaluations: list[FitnessEvaluation]) -> dict[str, object]:
    """Build a JSON-safe summary for one batch of fitness evaluations."""

    payload = [item.to_dict() for item in evaluations]
    scores = [float(item["fitness"]) for item in payload]
    return {
        "count": len(payload),
        "best_fitness": max(scores) if scores else None,
        "average_fitness": round(sum(scores) / len(scores), 6) if scores else None,
        "evaluations": payload,
    }
