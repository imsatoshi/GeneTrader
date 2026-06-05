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


def check_manifest_requirements(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_gate import check_manifest_requirements as _check_manifest_requirements

    return _check_manifest_requirements(*args, **kwargs)


def build_requirements_coverage_matrix(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_gate import build_requirements_coverage_matrix as _build_matrix

    return _build_matrix(*args, **kwargs)


def build_offline_requirements_from_config(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .config_requirements import build_offline_requirements_from_config as _build_requirements

    return _build_requirements(*args, **kwargs)


def load_offline_requirements_from_config(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .config_requirements import load_offline_requirements_from_config as _load_requirements

    return _load_requirements(*args, **kwargs)


def load_offline_data_requirements(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_gate import load_offline_data_requirements as _load_requirements

    return _load_requirements(*args, **kwargs)


def extract_data_gate_error_codes(*args: Any, **kwargs: Any) -> list[str]:
    from .data_gate import extract_data_gate_error_codes as _extract_error_codes

    return _extract_error_codes(*args, **kwargs)


def normalize_pair_symbol(*args: Any, **kwargs: Any) -> str | None:
    from .data_gate import normalize_pair_symbol as _normalize_pair_symbol

    return _normalize_pair_symbol(*args, **kwargs)


def normalize_timeframe(*args: Any, **kwargs: Any) -> str | None:
    from .data_gate import normalize_timeframe as _normalize_timeframe

    return _normalize_timeframe(*args, **kwargs)


def build_offline_data_manifest(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_manifest import build_offline_data_manifest as _build_offline_data_manifest

    return _build_offline_data_manifest(*args, **kwargs)


def build_manifest_from_inventory(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_manifest import build_manifest_from_inventory as _build_manifest_from_inventory

    return _build_manifest_from_inventory(*args, **kwargs)


def save_offline_data_manifest(*args: Any, **kwargs: Any) -> str:
    from .data_manifest import save_offline_data_manifest as _save_manifest

    return _save_manifest(*args, **kwargs)


def load_offline_data_manifest(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_manifest import load_offline_data_manifest as _load_manifest

    return _load_manifest(*args, **kwargs)


def summarize_manifest(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .data_manifest import summarize_manifest as _summarize_manifest

    return _summarize_manifest(*args, **kwargs)


def inventory_offline_data(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_data import inventory_offline_data as _inventory_offline_data

    return _inventory_offline_data(*args, **kwargs)


def run_backtest_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .preflight import run_backtest_preflight as _run_backtest_preflight

    return _run_backtest_preflight(*args, **kwargs)


def run_offline_data_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .preflight import run_offline_data_preflight as _run_offline_data_preflight

    return _run_offline_data_preflight(*args, **kwargs)


def build_offline_data_preflight_report(*args: Any, **kwargs: Any) -> Any:
    from .preflight import build_offline_data_preflight_report as _build_report

    return _build_report(*args, **kwargs)


def validate_offline_data_preflight_report_dict(*args: Any, **kwargs: Any) -> Any:
    from .preflight import validate_offline_data_preflight_report_dict as _validate_report

    return _validate_report(*args, **kwargs)


def render_offline_data_preflight_report(*args: Any, **kwargs: Any) -> str:
    from .preflight import render_offline_data_preflight_report as _render_report

    return _render_report(*args, **kwargs)


def run_offline_data_preflight_cli(*args: Any, **kwargs: Any) -> int:
    from .offline_preflight_cli import run_offline_data_preflight_cli as _run_cli

    return _run_cli(*args, **kwargs)


def offline_preflight_main(*args: Any, **kwargs: Any) -> int:
    from .offline_preflight_cli import offline_preflight_main as _main

    return _main(*args, **kwargs)


def compare_offline_data_preflight_reports(*args: Any, **kwargs: Any) -> Any:
    from .offline_data_diff import compare_offline_data_preflight_reports as _compare_reports

    return _compare_reports(*args, **kwargs)


def normalize_offline_relative_path(*args: Any, **kwargs: Any) -> str:
    from .offline_paths import normalize_offline_relative_path as _normalize_path

    return _normalize_path(*args, **kwargs)


def run_offline_data_workflow_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_workflow import run_offline_data_workflow_preflight as _run_workflow

    return _run_workflow(*args, **kwargs)


def build_backtest_offline_data_gate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_backtest_gate import build_backtest_offline_data_gate as _build_gate

    return _build_gate(*args, **kwargs)


def run_backtest_offline_data_gate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_backtest_gate import run_backtest_offline_data_gate as _run_gate

    return _run_gate(*args, **kwargs)


def format_offline_data_preflight_summary(*args: Any, **kwargs: Any) -> str:
    from .offline_data_summary import format_offline_data_preflight_summary as _format_summary

    return _format_summary(*args, **kwargs)


def format_offline_data_diff_summary(*args: Any, **kwargs: Any) -> str:
    from .offline_data_summary import format_offline_data_diff_summary as _format_diff_summary

    return _format_diff_summary(*args, **kwargs)


def run_offline_data_release_readiness_audit(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_release import run_offline_data_release_readiness_audit as _run_release

    return _run_release(*args, **kwargs)


def get_offline_data_metadata_only_boundary(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_data_boundary import (
        get_offline_data_metadata_only_boundary as _get_boundary,
    )

    return _get_boundary(*args, **kwargs)


def get_legacy_content_read_allowlist(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    from .offline_data_boundary import get_legacy_content_read_allowlist as _get_allowlist

    return _get_allowlist(*args, **kwargs)


def validate_metadata_only_boundary(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_data_boundary import validate_metadata_only_boundary as _validate_boundary

    return _validate_boundary(*args, **kwargs)


def run_offline_data_boundary_audit(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from .offline_data_boundary import run_offline_data_boundary_audit as _run_audit

    return _run_audit(*args, **kwargs)

__all__ = [
    "BollingerConfigError",
    "REQUIRED_FIELDS",
    "load_bollinger_config",
    "validate_bollinger_config",
    "build_offline_requirements_from_config",
    "load_offline_requirements_from_config",
    "run_offline_data_gate",
    "check_manifest_requirements",
    "build_requirements_coverage_matrix",
    "load_offline_data_requirements",
    "extract_data_gate_error_codes",
    "normalize_pair_symbol",
    "normalize_timeframe",
    "build_offline_data_manifest",
    "build_manifest_from_inventory",
    "save_offline_data_manifest",
    "load_offline_data_manifest",
    "summarize_manifest",
    "inventory_offline_data",
    "evaluate_data_coverage_gate",
    "run_backtest_preflight",
    "run_offline_data_preflight",
    "build_offline_data_preflight_report",
    "validate_offline_data_preflight_report_dict",
    "render_offline_data_preflight_report",
    "run_offline_data_preflight_cli",
    "offline_preflight_main",
    "compare_offline_data_preflight_reports",
    "normalize_offline_relative_path",
    "run_offline_data_workflow_preflight",
    "build_backtest_offline_data_gate",
    "run_backtest_offline_data_gate",
    "format_offline_data_preflight_summary",
    "format_offline_data_diff_summary",
    "run_offline_data_release_readiness_audit",
    "get_offline_data_metadata_only_boundary",
    "get_legacy_content_read_allowlist",
    "validate_metadata_only_boundary",
    "run_offline_data_boundary_audit",
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
