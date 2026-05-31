"""End-to-end mock evaluation pipeline for Bollinger Evolver GA smoke runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.data_quality import evaluate_data_coverage_gate
from bollinger_evolver.evaluators import sanitize_mapping
from bollinger_evolver.ga.generation_runner import GenerationConfig, candidate_id
from bollinger_evolver.scoring.fitness import calculate_fitness
from bollinger_evolver.strategy_factory import GENERATED_ROOT, generate_strategy_from_genes


def _stable_hash(data: Mapping[str, Any], seed: int | None = None) -> str:
    payload = {"genes": sanitize_mapping(data), "seed": seed}
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _hash_to_float(digest: str, start: int, minimum: float, maximum: float) -> float:
    value = int(digest[start : start + 8], 16) / 0xFFFFFFFF
    return minimum + ((maximum - minimum) * value)


def build_deterministic_mock_metrics(genes: Mapping[str, Any], seed: int | None = None) -> dict[str, Any]:
    """Build deterministic mock metrics that are explicitly marked as mock data."""

    digest = _stable_hash(genes, seed)
    total_profit = round(_hash_to_float(digest, 0, -5.0, 30.0), 6)
    max_drawdown = round(_hash_to_float(digest, 8, 1.0, 25.0), 6)
    profit_factor = round(_hash_to_float(digest, 16, 0.7, 2.5), 6)
    trade_count = int(_hash_to_float(digest, 24, 8.0, 120.0))
    win_rate = round(_hash_to_float(digest, 32, 35.0, 75.0), 6)
    calmar = round(total_profit / max(max_drawdown, 0.001), 6)

    return {
        "total_profit": total_profit,
        "total_profit_pct": total_profit,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown,
        "profit_factor": profit_factor,
        "trade_count": trade_count,
        "win_rate": win_rate,
        "calmar": calmar,
        "mock": True,
    }


def mock_fitness_from_metrics(metrics: Mapping[str, Any]) -> float:
    """Compute formal fitness from deterministic mock metrics."""

    fitness, breakdown = calculate_fitness(dict(metrics))
    return float(fitness if breakdown.get("accepted") else -1_000_000.0)


class MockStrategyEvaluator:
    """Generate strategy files and deterministic mock metrics without Freqtrade."""

    def __init__(
        self,
        *,
        seed: int | None = None,
        output_root: str | Path = "results/bollinger_evolver/mock_pipeline",
        strategy_output_dir: str | Path | None = None,
        overwrite: bool = False,
        data_coverage_manifest: Mapping[str, Any] | None = None,
        data_quality_gate_enabled: bool = True,
        required_pairs: list[str] | None = None,
        required_timeframes: list[str] | None = None,
        min_candles_per_pair_timeframe: int = 100,
        max_gap_ratio: float = 0.02,
        allow_invalid_ohlc: bool = False,
    ) -> None:
        self.seed = seed
        self.output_root = Path(output_root)
        self.strategy_output_dir = Path(strategy_output_dir) if strategy_output_dir else GENERATED_ROOT / "mock_pipeline"
        self.overwrite = overwrite
        self.data_coverage_manifest = sanitize_mapping(data_coverage_manifest) if data_coverage_manifest is not None else None
        self.data_quality_gate_enabled = data_quality_gate_enabled
        self.required_pairs = list(required_pairs) if required_pairs is not None else None
        self.required_timeframes = list(required_timeframes) if required_timeframes is not None else None
        self.min_candles_per_pair_timeframe = min_candles_per_pair_timeframe
        self.max_gap_ratio = max_gap_ratio
        self.allow_invalid_ohlc = allow_invalid_ohlc

    def __call__(
        self,
        individual: Mapping[str, Any],
        fitness_config: Any,
        *,
        generation_config: GenerationConfig | None = None,
        individual_index: int = 0,
    ) -> dict[str, Any]:
        generation = generation_config.generation_index if generation_config else 0
        output_root = generation_config.output_dir if generation_config else self.output_root
        return self.evaluate(
            individual,
            generation=generation,
            output_root=str(output_root),
            strategy_output_dir=str(self.strategy_output_dir),
            individual_index=individual_index,
        )

    def evaluate(
        self,
        individual: Mapping[str, Any],
        generation: int,
        output_root: str,
        strategy_output_dir: str | None = None,
        individual_index: int = 0,
    ) -> dict[str, Any]:
        sanitized_genes = sanitize_mapping(individual)
        individual_id = candidate_id(sanitized_genes)
        destination = strategy_output_dir or str(self.strategy_output_dir)
        data_quality_gate = self._data_quality_gate()

        if data_quality_gate is not None and not data_quality_gate.get("allowed_for_evaluation"):
            error = (
                "data_quality_manifest_missing"
                if data_quality_gate.get("status") == "MISSING"
                else "data_quality_gate_failed"
            )
            return {
                "success": False,
                "individual_id": individual_id,
                "generation": generation,
                "fitness": None,
                "fitness_score": -1_000_000.0,
                "metrics": {"dataQualityGate": data_quality_gate, "mock": True},
                "genes": sanitized_genes,
                "params": {"mock_evaluation": True, "dataQualityGate": data_quality_gate},
                "error": error,
                "reason": error,
            }

        try:
            strategy_info = generate_strategy_from_genes(
                dict(sanitized_genes),
                generation=generation,
                individual_index=individual_index,
                output_dir=str(destination),
                overwrite=self.overwrite,
            )
        except Exception as exc:
            return {
                "success": False,
                "individual_id": individual_id,
                "generation": generation,
                "fitness": None,
                "fitness_score": -1_000_000.0,
                "metrics": {"dataQualityGate": data_quality_gate} if data_quality_gate else {},
                "genes": sanitized_genes,
                "params": {"mock_evaluation": True},
                "error": str(exc),
                "reason": str(exc),
            }

        metrics = build_deterministic_mock_metrics(sanitized_genes, self.seed)
        if data_quality_gate is not None:
            metrics["dataQualityGate"] = data_quality_gate
        fitness, breakdown = calculate_fitness(metrics, genes=sanitized_genes)
        accepted = bool(breakdown.get("accepted"))
        metrics["fitness_breakdown"] = breakdown
        fitness_score = float(fitness if accepted else -1_000_000.0)
        params = {
            "individual_id": individual_id,
            "strategy_name": strategy_info["strategy_name"],
            "strategy_path": strategy_info["output_path"],
            "genes_hash": strategy_info["genes_hash"],
            "gene_id": strategy_info["gene_id"],
            "mock_evaluation": True,
        }
        return {
            "success": accepted,
            "individual_id": individual_id,
            "generation": generation,
            "strategy_name": strategy_info["strategy_name"],
            "strategy_path": strategy_info["output_path"],
            "genes_hash": strategy_info["genes_hash"],
            "fitness": fitness if accepted else None,
            "fitness_score": fitness_score,
            "metrics": metrics,
            "genes": sanitized_genes,
            "params": params,
            "error": None if accepted else breakdown.get("reject_reason"),
            "reason": None if accepted else breakdown.get("reject_reason"),
        }

    def _data_quality_gate(self) -> dict[str, Any] | None:
        if not self.data_quality_gate_enabled:
            return None
        return evaluate_data_coverage_gate(
            dict(self.data_coverage_manifest) if self.data_coverage_manifest is not None else None,
            required_pairs=self.required_pairs,
            required_timeframes=self.required_timeframes,
            min_candles_per_pair_timeframe=self.min_candles_per_pair_timeframe,
            max_gap_ratio=self.max_gap_ratio,
            allow_invalid_ohlc=self.allow_invalid_ohlc,
        )


def evaluate_individual_with_mock_pipeline(
    individual: dict,
    generation: int,
    output_root: str,
    strategy_output_dir: str,
) -> dict[str, Any]:
    manifest = {
        "status": "ready",
        "pairs": ["BTC/USDT"],
        "timeframes": ["15m"],
        "expected_file_count": 1,
        "missing_count": 0,
        "limited_count": 0,
        "invalid_ohlc_count": 0,
        "gap_count": 0,
        "entries": [
            {
                "pair": "BTC/USDT",
                "timeframe": "15m",
                "status": "ready",
                "row_count": 500,
                "gap_count": 0,
                "invalid_ohlc_count": 0,
            }
        ],
    }
    evaluator = MockStrategyEvaluator(
        output_root=output_root,
        strategy_output_dir=strategy_output_dir,
        overwrite=False,
        data_coverage_manifest=manifest,
        required_pairs=["BTC/USDT"],
        required_timeframes=["15m"],
    )
    return evaluator.evaluate(
        individual,
        generation=generation,
        output_root=output_root,
        strategy_output_dir=strategy_output_dir,
    )
