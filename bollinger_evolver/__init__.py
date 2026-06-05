"""Independent Bollinger Evolver package skeleton.

This package is intentionally isolated from the existing GeneTrader runtime.
It provides placeholders for future Bollinger-specific evolution logic,
configuration loading, reporting, and test coverage.
"""

from typing import Any

from .config_loader import (
    BollingerConfigError,
    REQUIRED_FIELDS,
    load_bollinger_config,
    validate_bollinger_config,
)
from .data_quality import evaluate_data_coverage_gate
from .evaluators import (
    DEFAULT_EVALUATION_DIR,
    FitnessConfig,
    FitnessResult,
    build_backtest_params,
    compute_fitness_score,
    evaluate_candidate,
    normalize_backtest_metrics,
    sanitize_mapping,
    write_evaluation_artifact,
)
from .ga import (
    DEFAULT_BEST_DIR,
    DEFAULT_GENERATION_DIR,
    GAOrchestratorConfig,
    GAOrchestratorResult,
    GASessionConfig,
    GASessionResult,
    GenerationConfig,
    GenerationResult,
    IndividualEvaluation,
    BacktestEvaluationAdapter,
    MockStrategyEvaluator,
    PositionSizingSmokeEvaluator,
    SmokeRunConfig,
    build_next_population,
    calculate_basic_backtest_fitness,
    build_deterministic_mock_metrics,
    build_position_sizing_snapshot,
    build_smoke_initial_population,
    candidate_id,
    crossover_candidates,
    extract_gene_snapshot,
    evaluate_individual_with_mock_pipeline,
    initialize_population,
    mock_fitness_from_metrics,
    mutate_candidate,
    normalize_candidate_genes,
    run_generation,
    run_ga,
    run_ga_session,
    run_smoke_ga_pipeline,
    render_session_report,
    select_elites,
    write_best_candidate,
    write_generation_summary,
)


def run_offline_data_gate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_gate import run_offline_data_gate as _run_offline_data_gate

    return _run_offline_data_gate(*args, **kwargs)


def build_offline_data_manifest(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_manifest import build_offline_data_manifest as _build_offline_data_manifest

    return _build_offline_data_manifest(*args, **kwargs)


def run_backtest_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .preflight import run_backtest_preflight as _run_backtest_preflight

    return _run_backtest_preflight(*args, **kwargs)

__all__ = [
    "BollingerConfigError",
    "REQUIRED_FIELDS",
    "load_bollinger_config",
    "validate_bollinger_config",
    "run_offline_data_gate",
    "build_offline_data_manifest",
    "evaluate_data_coverage_gate",
    "run_backtest_preflight",
    "DEFAULT_EVALUATION_DIR",
    "FitnessConfig",
    "FitnessResult",
    "build_backtest_params",
    "compute_fitness_score",
    "evaluate_candidate",
    "normalize_backtest_metrics",
    "sanitize_mapping",
    "write_evaluation_artifact",
    "DEFAULT_BEST_DIR",
    "DEFAULT_GENERATION_DIR",
    "GAOrchestratorConfig",
    "GAOrchestratorResult",
    "GASessionConfig",
    "GASessionResult",
    "GenerationConfig",
    "GenerationResult",
    "IndividualEvaluation",
    "BacktestEvaluationAdapter",
    "MockStrategyEvaluator",
    "PositionSizingSmokeEvaluator",
    "SmokeRunConfig",
    "build_next_population",
    "calculate_basic_backtest_fitness",
    "build_deterministic_mock_metrics",
    "build_position_sizing_snapshot",
    "build_smoke_initial_population",
    "candidate_id",
    "crossover_candidates",
    "extract_gene_snapshot",
    "evaluate_individual_with_mock_pipeline",
    "initialize_population",
    "mock_fitness_from_metrics",
    "mutate_candidate",
    "normalize_candidate_genes",
    "run_generation",
    "run_ga",
    "run_ga_session",
    "run_smoke_ga_pipeline",
    "render_session_report",
    "select_elites",
    "write_best_candidate",
    "write_generation_summary",
]
