"""Multi-generation GA orchestrator for Bollinger Evolver."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from bollinger_evolver.evaluators import FitnessConfig, sanitize_mapping
from bollinger_evolver.ga.generation_runner import (
    DEFAULT_BEST_DIR,
    DEFAULT_GENERATION_DIR,
    GenerationConfig,
    GenerationResult,
    candidate_id,
    run_generation,
)
from bollinger_evolver.ga.population_ops import build_next_population, extract_gene_snapshot, initialize_population
from bollinger_evolver.gene_space import GeneSpace, load_gene_space


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = (PROJECT_ROOT / "results" / "bollinger_evolver" / "runs").resolve()


@dataclass(frozen=True)
class GAOrchestratorConfig:
    generations: int
    population_size: int
    run_id: str | None = None
    seed: int | None = None
    run_output_dir: Path | str = "results/bollinger_evolver/runs"
    generation_output_dir: Path | str = "results/bollinger_evolver/generations"
    best_output_dir: Path | str = "results/bollinger_evolver/best"
    elite_count: int = 2
    mutation_rate: float = 0.1
    crossover_rate: float = 0.8
    persist_run_summary: bool = True
    persist_final_best: bool = True
    mode: str = "mock"
    gene_space_path: Path | str | None = None


@dataclass(frozen=True)
class GAOrchestratorResult:
    success: bool
    run_id: str
    generations_requested: int
    completed: int
    population_size: int
    best_candidate: dict[str, Any] | None
    best_fitness_score: float | None
    best_generation_index: int | None
    generation_results: list[GenerationResult] = field(default_factory=list)
    run_summary_path: str | None = None
    final_best_path: str | None = None
    reason: str | None = None


def _resolve_output_dir(path_value: Path | str, default: Path) -> Path:
    candidate = Path(path_value) if path_value else default
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def _generate_run_id() -> str:
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _write_run_summary(result: GAOrchestratorResult, output_dir: Path | str) -> Path:
    destination = _resolve_output_dir(output_dir, DEFAULT_RUN_DIR)
    destination.mkdir(parents=True, exist_ok=True)

    best_payload = sanitize_mapping(result.best_candidate or {})
    best_genes = extract_gene_snapshot(best_payload) if best_payload else {}
    payload = {
        "run_id": result.run_id,
        "success": result.success,
        "generations_requested": result.generations_requested,
        "completed": result.completed,
        "population_size": result.population_size,
        "best_candidate": best_payload,
        "best_genes": best_genes,
        "final_best": best_payload if result.best_candidate else None,
        "best_candidate_id": candidate_id(result.best_candidate or {}) if result.best_candidate else None,
        "genes_hash": best_payload.get("genes_hash"),
        "strategy_name": best_payload.get("strategy_name"),
        "strategy_path": best_payload.get("strategy_path"),
        "mock_evaluation": bool(best_payload.get("mock_evaluation", False)),
        "best_fitness_score": result.best_fitness_score,
        "best_generation_index": result.best_generation_index,
        "generation_results": [
            {
                "generation_index": item.generation_index,
                "success": item.success,
                "population_size": item.population_size,
                "evaluated_count": item.evaluated_count,
                "success_count": item.success_count,
                "failure_count": item.failure_count,
                "best_candidate_id": item.best.candidate_id if item.best else None,
                "best_fitness_score": item.best.fitness_score if item.best else None,
                "reason": item.reason,
                "summary_path": item.summary_path,
                "best_path": item.best_path,
            }
            for item in result.generation_results
        ],
        "reason": result.reason,
        "stop_reason": result.reason,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    file_path = destination / f"run-summary-{result.run_id}.json"
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return file_path


def _find_global_best_individual(result: GAOrchestratorResult) -> Any | None:
    if result.best_fitness_score is None:
        return None
    for generation_result in result.generation_results:
        if generation_result.generation_index != result.best_generation_index:
            continue
        for individual in generation_result.individuals:
            if individual.success and individual.fitness_score == result.best_fitness_score:
                return individual
    return None


def _write_final_best(result: GAOrchestratorResult, output_dir: Path | str) -> Path | None:
    if result.best_candidate is None:
        return None

    destination = _resolve_output_dir(output_dir, DEFAULT_BEST_DIR)
    destination.mkdir(parents=True, exist_ok=True)
    safe_candidate = sanitize_mapping(result.best_candidate)
    best_genes = extract_gene_snapshot(safe_candidate)
    best_individual = _find_global_best_individual(result)
    best_metrics = sanitize_mapping(best_individual.metrics) if best_individual is not None else {}
    candidate_hash = candidate_id(safe_candidate)
    payload = {
        "run_id": result.run_id,
        "best_generation_index": result.best_generation_index,
        "best_candidate_id": candidate_hash,
        "individual_id": safe_candidate.get("individual_id", candidate_hash),
        "best_fitness_score": result.best_fitness_score,
        "best_candidate": safe_candidate,
        "genes": best_genes,
        "genes_hash": safe_candidate.get("genes_hash"),
        "strategy_name": safe_candidate.get("strategy_name"),
        "strategy_path": safe_candidate.get("strategy_path"),
        "fitness": result.best_fitness_score,
        "metrics": best_metrics,
        "mock_evaluation": bool(safe_candidate.get("mock_evaluation", False)),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    file_path = destination / f"final-best-{result.run_id}-{candidate_hash}.json"
    file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return file_path


def _load_gene_space_from_config(config: GAOrchestratorConfig) -> GeneSpace:
    if config.gene_space_path is not None:
        return load_gene_space(config.gene_space_path)
    return load_gene_space()


def run_ga(
    initial_population: list[dict[str, Any]],
    fitness_config: FitnessConfig,
    orchestrator_config: GAOrchestratorConfig,
    evaluator: Callable[..., Any] | None = None,
    generation_runner: Callable[..., GenerationResult] | None = None,
) -> GAOrchestratorResult:
    """Run multiple generations through the Task 09 generation runner."""

    run_id = orchestrator_config.run_id or _generate_run_id()
    generations_requested = int(orchestrator_config.generations)
    population_size = int(orchestrator_config.population_size)

    if generations_requested <= 0:
        return GAOrchestratorResult(
            success=False,
            run_id=run_id,
            generations_requested=generations_requested,
            completed=0,
            population_size=population_size,
            best_candidate=None,
            best_fitness_score=None,
            best_generation_index=None,
            reason="invalid_generation_count",
        )
    if not initial_population:
        return GAOrchestratorResult(
            success=False,
            run_id=run_id,
            generations_requested=generations_requested,
            completed=0,
            population_size=population_size,
            best_candidate=None,
            best_fitness_score=None,
            best_generation_index=None,
            reason="empty_initial_population",
        )

    rng = random.Random(orchestrator_config.seed)
    gene_space = _load_gene_space_from_config(orchestrator_config)
    generation_runner_callable = generation_runner or run_generation

    current_population = initialize_population(
        initial_population,
        gene_space,
        population_size,
        rng,
    )
    if not current_population:
        return GAOrchestratorResult(
            success=False,
            run_id=run_id,
            generations_requested=generations_requested,
            completed=0,
            population_size=population_size,
            best_candidate=None,
            best_fitness_score=None,
            best_generation_index=None,
            reason="empty_initial_population",
        )
    generation_results: list[GenerationResult] = []
    best_candidate: dict[str, Any] | None = None
    best_fitness_score: float | None = None
    best_generation_index: int | None = None
    reason: str | None = None

    for generation_offset in range(generations_requested):
        generation_index = generation_offset + 1
        generation_config = GenerationConfig(
            generation_index=generation_index,
            run_id=run_id,
            output_dir=orchestrator_config.generation_output_dir,
            best_dir=orchestrator_config.best_output_dir,
            failed_score=fitness_config.failed_score,
            persist_best=True,
            persist_individuals=True,
        )
        generation_result = generation_runner_callable(
            current_population,
            fitness_config,
            generation_config,
            evaluator=evaluator,
        )
        generation_results.append(generation_result)

        if generation_result.best is not None:
            if best_fitness_score is None or generation_result.best.fitness_score > best_fitness_score:
                best_fitness_score = generation_result.best.fitness_score
                best_candidate = sanitize_mapping(generation_result.best.candidate)
                best_generation_index = generation_result.generation_index

        if not generation_result.success or generation_result.best is None:
            reason = generation_result.reason or "no_successful_individuals"
            break

        next_population = build_next_population(
            generation_result=generation_result,
            gene_space=gene_space,
            population_size=population_size,
            elite_count=orchestrator_config.elite_count,
            mutation_rate=orchestrator_config.mutation_rate,
            crossover_rate=orchestrator_config.crossover_rate,
            rng=rng,
        )
        if not next_population and generation_offset < generations_requested - 1:
            reason = "no_successful_individuals"
            break
        current_population = next_population
    else:
        reason = None

    success = best_candidate is not None and reason is None
    completed = len(generation_results)
    if best_candidate is None and reason is None:
        reason = "no_successful_individuals"

    result = GAOrchestratorResult(
        success=success,
        run_id=run_id,
        generations_requested=generations_requested,
        completed=completed,
        population_size=population_size,
        best_candidate=best_candidate,
        best_fitness_score=best_fitness_score,
        best_generation_index=best_generation_index,
        generation_results=generation_results,
        reason=reason,
    )

    run_summary_path = None
    if orchestrator_config.persist_run_summary:
        run_summary_path = str(_write_run_summary(result, orchestrator_config.run_output_dir))

    final_best_path = None
    if orchestrator_config.persist_final_best:
        written = _write_final_best(result, orchestrator_config.best_output_dir)
        final_best_path = str(written) if written is not None else None

    return replace(result, run_summary_path=run_summary_path, final_best_path=final_best_path)
