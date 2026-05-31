"""GA helpers for Bollinger Evolver."""

from .generation_runner import (
    DEFAULT_BEST_DIR,
    DEFAULT_GENERATION_DIR,
    GenerationConfig,
    GenerationResult,
    IndividualEvaluation,
    candidate_id,
    run_generation,
    write_best_candidate,
    write_generation_summary,
)
from .orchestrator import GAOrchestratorConfig, GAOrchestratorResult, run_ga
from .evaluation_pipeline import (
    MockStrategyEvaluator,
    build_deterministic_mock_metrics,
    evaluate_individual_with_mock_pipeline,
    mock_fitness_from_metrics,
)
from .backtest_evaluation_adapter import (
    BacktestEvaluationAdapter,
    calculate_basic_backtest_fitness,
)
from .population_ops import (
    build_next_population,
    crossover_candidates,
    extract_gene_snapshot,
    initialize_population,
    mutate_candidate,
    normalize_candidate_genes,
    select_elites,
)
from .smoke_run_pipeline import (
    PositionSizingSmokeEvaluator,
    SmokeRunConfig,
    build_position_sizing_snapshot,
    build_smoke_initial_population,
    run_smoke_ga_pipeline,
)
from .runner import GASessionConfig, GASessionResult, run_ga_session
from .session_report import render_session_report

__all__ = [
    "DEFAULT_BEST_DIR",
    "DEFAULT_GENERATION_DIR",
    "GenerationConfig",
    "GenerationResult",
    "IndividualEvaluation",
    "candidate_id",
    "run_generation",
    "write_best_candidate",
    "write_generation_summary",
    "GAOrchestratorConfig",
    "GAOrchestratorResult",
    "run_ga",
    "MockStrategyEvaluator",
    "build_deterministic_mock_metrics",
    "evaluate_individual_with_mock_pipeline",
    "mock_fitness_from_metrics",
    "BacktestEvaluationAdapter",
    "calculate_basic_backtest_fitness",
    "select_elites",
    "crossover_candidates",
    "extract_gene_snapshot",
    "initialize_population",
    "mutate_candidate",
    "normalize_candidate_genes",
    "build_next_population",
    "PositionSizingSmokeEvaluator",
    "SmokeRunConfig",
    "GASessionConfig",
    "GASessionResult",
    "build_position_sizing_snapshot",
    "build_smoke_initial_population",
    "run_smoke_ga_pipeline",
    "run_ga_session",
    "render_session_report",
]
