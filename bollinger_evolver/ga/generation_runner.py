"""Generation-level GA evaluation helpers for Bollinger Evolver."""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from bollinger_evolver.evaluators import FitnessConfig, FitnessResult, evaluate_candidate, sanitize_mapping
from bollinger_evolver.ga.population_ops import extract_gene_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENERATION_DIR = (PROJECT_ROOT / "results" / "bollinger_evolver" / "generations").resolve()
DEFAULT_BEST_DIR = (PROJECT_ROOT / "results" / "bollinger_evolver" / "best").resolve()


@dataclass(frozen=True)
class GenerationConfig:
    generation_index: int
    run_id: str | None = None
    output_dir: Path | str = "results/bollinger_evolver/generations"
    best_dir: Path | str = "results/bollinger_evolver/best"
    failed_score: float = -1_000_000.0
    sort_descending: bool = True
    persist_individuals: bool = True
    persist_best: bool = True


@dataclass(frozen=True)
class IndividualEvaluation:
    index: int
    candidate_id: str
    success: bool
    fitness_score: float
    candidate: dict[str, Any]
    metrics: dict[str, Any]
    reason: str | None = None
    artifact_path: str | None = None


@dataclass(frozen=True)
class GenerationResult:
    success: bool
    run_id: str
    generation_index: int
    population_size: int
    evaluated_count: int
    success_count: int
    failure_count: int
    best: IndividualEvaluation | None
    individuals: list[IndividualEvaluation] = field(default_factory=list)
    summary_path: str | None = None
    best_path: str | None = None
    reason: str | None = None


def _resolve_output_dir(path_value: Path | str, default: Path) -> Path:
    candidate = Path(path_value) if path_value else default
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def _generate_run_id() -> str:
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _safe_generation_index(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("generation_index must be a non-negative integer.")
    return value


def candidate_id(candidate: Mapping[str, Any]) -> str:
    """Create a deterministic ID from sanitized candidate data."""

    sanitized = sanitize_mapping(candidate)
    encoded = json.dumps(sanitized, sort_keys=True, default=str, separators=(",", ":")).encode(
        "utf-8"
    )
    digest = hashlib.sha256(encoded).hexdigest()[:12]
    return f"candidate-{digest}"


def _individual_to_payload(individual: IndividualEvaluation) -> dict[str, Any]:
    candidate_payload = sanitize_mapping(individual.candidate)
    genes = extract_gene_snapshot(candidate_payload)
    return {
        "index": individual.index,
        "candidate_id": individual.candidate_id,
        "individual_id": candidate_payload.get("individual_id", individual.candidate_id),
        "success": individual.success,
        "fitness_score": individual.fitness_score,
        "candidate": candidate_payload,
        "genes": genes,
        "genes_hash": candidate_payload.get("genes_hash"),
        "strategy_name": candidate_payload.get("strategy_name"),
        "strategy_path": candidate_payload.get("strategy_path"),
        "mock_evaluation": bool(candidate_payload.get("mock_evaluation", False)),
        "metrics": sanitize_mapping(individual.metrics),
        "reason": individual.reason,
        "artifact_path": individual.artifact_path,
    }


def write_generation_summary(
    result: GenerationResult,
    output_dir: Path | str,
    *,
    persist_individuals: bool = True,
) -> Path:
    """Persist one generation summary as JSON."""

    destination = _resolve_output_dir(output_dir, DEFAULT_GENERATION_DIR)
    destination.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": result.run_id,
        "generation_index": result.generation_index,
        "population_size": result.population_size,
        "evaluated_count": result.evaluated_count,
        "success_count": result.success_count,
        "failure_count": result.failure_count,
        "best_candidate_id": result.best.candidate_id if result.best else None,
        "best_individual": _individual_to_payload(result.best) if result.best else None,
        "best_fitness_score": result.best.fitness_score if result.best else None,
        "best_metrics": sanitize_mapping(result.best.metrics if result.best else {}),
        "best_genes": sanitize_mapping(result.best.candidate if result.best else {}),
        "individuals": (
            [_individual_to_payload(item) for item in result.individuals]
            if persist_individuals
            else []
        ),
        "reason": result.reason,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    file_path = destination / f"generation-{result.generation_index:06d}-{result.run_id}.json"
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return file_path


def write_best_candidate(
    generation_result: GenerationResult,
    best_dir: Path | str,
) -> Path | None:
    """Persist the best successful candidate of a generation."""

    if generation_result.best is None:
        return None

    destination = _resolve_output_dir(best_dir, DEFAULT_BEST_DIR)
    destination.mkdir(parents=True, exist_ok=True)

    best = generation_result.best
    candidate_payload = sanitize_mapping(best.candidate)
    genes = extract_gene_snapshot(candidate_payload)
    payload = {
        "run_id": generation_result.run_id,
        "generation_index": generation_result.generation_index,
        "candidate_id": best.candidate_id,
        "individual_id": candidate_payload.get("individual_id", best.candidate_id),
        "success": best.success,
        "fitness_score": best.fitness_score,
        "candidate": candidate_payload,
        "genes": genes,
        "genes_hash": candidate_payload.get("genes_hash"),
        "strategy_name": candidate_payload.get("strategy_name"),
        "strategy_path": candidate_payload.get("strategy_path"),
        "mock_evaluation": bool(candidate_payload.get("mock_evaluation", False)),
        "metrics": sanitize_mapping(best.metrics),
        "reason": best.reason,
        "artifact_path": best.artifact_path,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    file_path = destination / (
        f"best-generation-{generation_result.generation_index:06d}-{best.candidate_id}.json"
    )
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return file_path


def _failure_individual(
    index: int,
    candidate: Any,
    generation_config: GenerationConfig,
    reason: str,
) -> IndividualEvaluation:
    safe_candidate = sanitize_mapping(candidate) if isinstance(candidate, Mapping) else {
        "invalid_candidate_type": type(candidate).__name__
    }
    candidate_hash = candidate_id(safe_candidate)
    return IndividualEvaluation(
        index=index,
        candidate_id=candidate_hash,
        success=False,
        fitness_score=float(generation_config.failed_score),
        candidate=safe_candidate,
        metrics={},
        reason=reason,
        artifact_path=None,
    )


def _call_evaluator(
    evaluator: Callable[..., FitnessResult],
    candidate: Mapping[str, Any],
    fitness_config: FitnessConfig,
    generation_config: GenerationConfig,
    individual_index: int,
) -> FitnessResult:
    signature = inspect.signature(evaluator)
    parameters = signature.parameters
    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    if accepts_kwargs or "generation_config" in parameters or "individual_index" in parameters:
        return evaluator(
            candidate,
            fitness_config,
            generation_config=generation_config,
            individual_index=individual_index,
        )

    positional = [
        parameter
        for parameter in parameters.values()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        and parameter.default is inspect.Parameter.empty
    ]
    if len(positional) >= 4:
        return evaluator(candidate, fitness_config, generation_config, individual_index)
    return evaluator(candidate, fitness_config)


def run_generation(
    population: list[dict[str, Any]],
    fitness_config: FitnessConfig,
    generation_config: GenerationConfig,
    evaluator: Callable[..., FitnessResult] | None = None,
) -> GenerationResult:
    """Evaluate a population and persist generation-level artifacts."""

    generation_index = _safe_generation_index(generation_config.generation_index)
    run_id = generation_config.run_id or _generate_run_id()
    evaluator_callable = evaluator or evaluate_candidate

    if not population:
        result = GenerationResult(
            success=False,
            run_id=run_id,
            generation_index=generation_index,
            population_size=0,
            evaluated_count=0,
            success_count=0,
            failure_count=0,
            best=None,
            individuals=[],
            reason="empty_population",
        )
        summary_path = write_generation_summary(
            result,
            generation_config.output_dir,
            persist_individuals=generation_config.persist_individuals,
        )
        return replace(result, summary_path=str(summary_path))

    individuals: list[IndividualEvaluation] = []
    for index, candidate in enumerate(population):
        if not isinstance(candidate, Mapping):
            individuals.append(
                _failure_individual(
                    index,
                    candidate,
                    generation_config,
                    "invalid_candidate: candidate must be a mapping",
                )
            )
            continue

        sanitized_candidate = sanitize_mapping(candidate)
        try:
            fitness_result = _call_evaluator(
                evaluator_callable,
                candidate,
                fitness_config,
                generation_config,
                index,
            )
        except Exception as exc:
            individuals.append(
                _failure_individual(
                    index,
                    candidate,
                    generation_config,
                    f"evaluator_exception: {type(exc).__name__}: {exc}",
                )
            )
            continue

        if not isinstance(fitness_result, FitnessResult):
            if isinstance(fitness_result, Mapping):
                mapped = fitness_result
                success = bool(mapped.get("success"))
                metrics = sanitize_mapping(mapped.get("metrics", {})) if isinstance(
                    mapped.get("metrics", {}), Mapping
                ) else {}
                breakdown = metrics.get("fitness_breakdown", {})
                if isinstance(breakdown, Mapping) and breakdown.get("accepted") is False:
                    success = False
                raw_score = mapped.get("fitness_score", mapped.get("fitness", generation_config.failed_score))
                if raw_score is None:
                    raw_score = generation_config.failed_score
                score = float(raw_score)
                reason = str(mapped.get("reason")) if mapped.get("reason") is not None else None
                if not success and reason is None and isinstance(breakdown, Mapping):
                    reject_reason = breakdown.get("reject_reason")
                    if reject_reason is not None:
                        reason = str(reject_reason)
                artifact_path = (
                    str(mapped.get("artifact_path")) if mapped.get("artifact_path") is not None else None
                )
                mapped_params = mapped.get("params", {})
                mapped_genes = mapped.get("genes", {})
                candidate_payload = dict(sanitized_candidate)
                if isinstance(mapped_genes, Mapping):
                    candidate_payload = sanitize_mapping(mapped_genes)
                if isinstance(mapped_params, Mapping):
                    for key, value in sanitize_mapping(mapped_params).items():
                        if key not in candidate_payload:
                            candidate_payload[key] = value
                individual_id = str(mapped.get("individual_id")) if mapped.get("individual_id") else None
            else:
                individuals.append(
                    _failure_individual(
                        index,
                        candidate,
                        generation_config,
                        "invalid_fitness_result: evaluator must return FitnessResult or mapping",
                    )
                )
                continue
        else:
            success = fitness_result.success
            score = float(fitness_result.fitness_score)
            metrics = sanitize_mapping(fitness_result.metrics)
            reason = fitness_result.reason
            artifact_path = fitness_result.artifact_path
            candidate_payload = dict(sanitized_candidate)
            if isinstance(fitness_result.params, Mapping):
                for key, value in sanitize_mapping(fitness_result.params).items():
                    if key not in candidate_payload:
                        candidate_payload[key] = value
            individual_id = None

        individuals.append(
            IndividualEvaluation(
                index=index,
                candidate_id=individual_id or candidate_id(candidate_payload),
                success=success,
                fitness_score=score,
                candidate=candidate_payload,
                metrics=metrics,
                reason=reason,
                artifact_path=artifact_path,
            )
        )

    sorted_individuals = sorted(
        individuals,
        key=lambda item: item.fitness_score,
        reverse=generation_config.sort_descending,
    )
    successful = [item for item in sorted_individuals if item.success]
    best = successful[0] if successful else None
    success_count = len(successful)
    failure_count = len(sorted_individuals) - success_count
    reason = None if best is not None else "no_successful_individuals"

    result = GenerationResult(
        success=best is not None,
        run_id=run_id,
        generation_index=generation_index,
        population_size=len(population),
        evaluated_count=len(sorted_individuals),
        success_count=success_count,
        failure_count=failure_count,
        best=best,
        individuals=sorted_individuals,
        reason=reason,
    )

    summary_path = write_generation_summary(
        result,
        generation_config.output_dir,
        persist_individuals=generation_config.persist_individuals,
    )
    best_path = None
    if generation_config.persist_best:
        best_written = write_best_candidate(result, generation_config.best_dir)
        best_path = str(best_written) if best_written is not None else None

    return replace(result, summary_path=str(summary_path), best_path=best_path)
