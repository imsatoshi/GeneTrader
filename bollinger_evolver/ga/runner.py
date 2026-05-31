"""Mock-first GA session runner with consolidated reporting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.data_quality import evaluate_data_coverage_gate
from bollinger_evolver.evaluators import sanitize_mapping
from bollinger_evolver.ga.orchestrator import GAOrchestratorResult
from bollinger_evolver.ga.session_report import render_session_report
from bollinger_evolver.ga.smoke_run_pipeline import SmokeRunConfig, build_smoke_initial_population, run_smoke_ga_pipeline
from bollinger_evolver.strategy_factory import GENERATED_ROOT


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GASessionConfig:
    generations: int = 2
    population_size: int = 4
    seed: int = 123
    run_id: str = "ga-session"
    output_root: Path | str = "results/bollinger_evolver/sessions"
    strategy_output_dir: Path | str | None = None
    evaluation_mode: str = "mock"
    allow_real_backtest: bool = False
    elite_count: int = 1
    mutation_rate: float = 0.2
    crossover_rate: float = 0.8
    fail_individual_indexes: tuple[int, ...] = ()
    data_coverage_manifest: Mapping[str, Any] | None = None
    data_quality_gate_enabled: bool = True
    required_pairs: tuple[str, ...] = ("BTC/USDT",)
    required_timeframes: tuple[str, ...] = ("15m",)
    persist_session_summary: bool = True
    min_candles_per_pair_timeframe: int = 100
    max_gap_ratio: float = 0.02
    allow_invalid_ohlc: bool = False
    require_explicit_data_manifest: bool = False
    generate_report: bool = True


@dataclass(frozen=True)
class GASessionResult:
    success: bool
    run_id: str
    session_summary: dict[str, Any]
    session_summary_path: str | None = None
    report_json_path: str | None = None
    report_markdown_path: str | None = None
    orchestrator_result: GAOrchestratorResult | None = None
    reason: str | None = None


def _resolve_path(path_value: Path | str) -> Path:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def _default_manifest(config: GASessionConfig) -> dict[str, Any]:
    entries = []
    for pair in config.required_pairs:
        for timeframe in config.required_timeframes:
            entries.append(
                {
                    "pair": pair,
                    "timeframe": timeframe,
                    "status": "ready",
                    "row_count": 500,
                    "gap_count": 0,
                    "invalid_ohlc_count": 0,
                    "covers_start_date": True,
                }
            )
    return {
        "status": "ready",
        "pairs": list(config.required_pairs),
        "timeframes": list(config.required_timeframes),
        "expected_file_count": len(entries),
        "missing_count": 0,
        "limited_count": 0,
        "invalid_ohlc_count": 0,
        "gap_count": 0,
        "entries": entries,
    }


def _session_gate(config: GASessionConfig) -> dict[str, Any] | None:
    if not config.data_quality_gate_enabled:
        return None
    if config.data_coverage_manifest is None and config.require_explicit_data_manifest:
        manifest = None
    else:
        manifest = (
            sanitize_mapping(config.data_coverage_manifest)
            if config.data_coverage_manifest is not None
            else _default_manifest(config)
        )
    return evaluate_data_coverage_gate(
        manifest,
        required_pairs=list(config.required_pairs),
        required_timeframes=list(config.required_timeframes),
        min_candles_per_pair_timeframe=config.min_candles_per_pair_timeframe,
        max_gap_ratio=config.max_gap_ratio,
        allow_invalid_ohlc=config.allow_invalid_ohlc,
    )


def _read_json(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_session_summary(summary: Mapping[str, Any], session_root: Path) -> Path:
    session_root.mkdir(parents=True, exist_ok=True)
    summary_path = session_root / "session_summary.json"
    summary_path.write_text(
        json.dumps(sanitize_mapping(summary), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary_path


def _blocked_summary(
    config: GASessionConfig,
    session_root: Path,
    data_quality_gate: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "session_id": config.run_id,
        "run_id": config.run_id,
        "success": False,
        "status": "BLOCKED",
        "mode": config.evaluation_mode,
        "mock_first": True,
        "allow_real_backtest": False,
        "mock_evaluation": True,
        "real_backtest": False,
        "dataQualityGateDisabled": not config.data_quality_gate_enabled,
        "completed": 0,
        "population_size": config.population_size,
        "generations_requested": config.generations,
        "run_summary": None,
        "generation_summaries": [],
        "generation_summary_paths": [],
        "final_best": None,
        "final_best_path": None,
        "dataQualityGate": data_quality_gate,
        "reason": "data_quality_gate_failed",
        "output_root": str(session_root.parent),
        "session_root": str(session_root),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "readOnly": True,
    }


def _consolidated_summary(
    config: GASessionConfig,
    session_root: Path,
    data_quality_gate: dict[str, Any] | None,
    orchestrator_result: GAOrchestratorResult,
) -> dict[str, Any]:
    run_summary = _read_json(orchestrator_result.run_summary_path)
    final_best = _read_json(orchestrator_result.final_best_path)
    generation_summaries = []
    generation_summary_paths = []
    for generation_result in orchestrator_result.generation_results:
        generation_summary_paths.append(generation_result.summary_path)
        generation_summaries.append(_read_json(generation_result.summary_path))
    return {
        "session_id": config.run_id,
        "run_id": config.run_id,
        "success": orchestrator_result.success,
        "status": "PASS" if orchestrator_result.success else "FAILED",
        "mode": config.evaluation_mode,
        "mock_first": True,
        "allow_real_backtest": False,
        "mock_evaluation": True,
        "real_backtest": False,
        "dataQualityGateDisabled": not config.data_quality_gate_enabled,
        "completed": orchestrator_result.completed,
        "population_size": orchestrator_result.population_size,
        "generations_requested": orchestrator_result.generations_requested,
        "best_fitness_score": orchestrator_result.best_fitness_score,
        "best_generation_index": orchestrator_result.best_generation_index,
        "run_summary": run_summary,
        "generation_summaries": generation_summaries,
        "generation_summary_paths": generation_summary_paths,
        "final_best": final_best,
        "final_best_path": orchestrator_result.final_best_path,
        "dataQualityGate": data_quality_gate,
        "reason": orchestrator_result.reason,
        "output_root": str(session_root.parent),
        "session_root": str(session_root),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "readOnly": True,
    }


def evaluate_session_preflight(config: GASessionConfig | None = None) -> dict[str, Any]:
    """Run read-only preflight checks without starting a GA session."""

    resolved_config = config or GASessionConfig()
    session_root = _resolve_path(resolved_config.output_root) / resolved_config.run_id
    data_quality_gate = _session_gate(resolved_config)
    status = "PASS"
    reason = None
    if data_quality_gate is not None and not data_quality_gate.get("allowed_for_evaluation"):
        status = "BLOCKED"
        reason = "data_quality_gate_failed"
    return {
        "session_id": resolved_config.run_id,
        "run_id": resolved_config.run_id,
        "status": status,
        "reason": reason,
        "mock_evaluation": True,
        "real_backtest": False,
        "allow_real_backtest": False,
        "dataQualityGateDisabled": not resolved_config.data_quality_gate_enabled,
        "dataQualityGate": data_quality_gate,
        "output_root": str(session_root.parent),
        "session_root": str(session_root),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "readOnly": True,
    }


def run_ga_session(
    config: GASessionConfig | None = None,
    *,
    initial_population: list[dict[str, Any]] | None = None,
) -> GASessionResult:
    """Run a mock-first GA session and consolidate artifacts into one summary."""

    resolved_config = config or GASessionConfig()
    output_root = _resolve_path(resolved_config.output_root)
    session_root = output_root / resolved_config.run_id
    data_quality_gate = _session_gate(resolved_config)

    if data_quality_gate is not None and not data_quality_gate.get("allowed_for_evaluation"):
        summary = _blocked_summary(resolved_config, session_root, data_quality_gate)
        summary_path = None
        report_json_path = None
        report_markdown_path = None
        if resolved_config.generate_report:
            rendered = render_session_report(summary, session_root, write_files=True)
            report_json_path = rendered["report_json_path"]
            report_markdown_path = rendered["report_markdown_path"]
            summary["session_report_path"] = report_json_path
            summary["session_report_markdown_path"] = report_markdown_path
        if resolved_config.persist_session_summary:
            summary_path = str(_write_session_summary(summary, session_root))
        return GASessionResult(
            success=False,
            run_id=resolved_config.run_id,
            session_summary=sanitize_mapping(summary),
            session_summary_path=summary_path,
            report_json_path=report_json_path,
            report_markdown_path=report_markdown_path,
            orchestrator_result=None,
            reason="data_quality_gate_failed",
        )

    if initial_population is None:
        initial_population = build_smoke_initial_population(
            population_size=resolved_config.population_size,
            seed=resolved_config.seed,
        )

    smoke_config = SmokeRunConfig(
        generations=resolved_config.generations,
        population_size=resolved_config.population_size,
        seed=resolved_config.seed,
        run_id=resolved_config.run_id,
        output_root=session_root,
        strategy_output_dir=(
            resolved_config.strategy_output_dir
            if resolved_config.strategy_output_dir is not None
            else GENERATED_ROOT / "ga_sessions" / resolved_config.run_id
        ),
        evaluation_mode=resolved_config.evaluation_mode,
        allow_real_backtest=False,
        elite_count=resolved_config.elite_count,
        mutation_rate=resolved_config.mutation_rate,
        crossover_rate=resolved_config.crossover_rate,
        fail_individual_indexes=resolved_config.fail_individual_indexes,
        data_coverage_manifest=(
            sanitize_mapping(resolved_config.data_coverage_manifest)
            if resolved_config.data_coverage_manifest is not None
            else _default_manifest(resolved_config)
        ),
        data_quality_gate_enabled=resolved_config.data_quality_gate_enabled,
        required_pairs=tuple(resolved_config.required_pairs),
        required_timeframes=tuple(resolved_config.required_timeframes),
        min_candles_per_pair_timeframe=resolved_config.min_candles_per_pair_timeframe,
        max_gap_ratio=resolved_config.max_gap_ratio,
        allow_invalid_ohlc=resolved_config.allow_invalid_ohlc,
    )
    orchestrator_result = run_smoke_ga_pipeline(smoke_config, initial_population=initial_population)
    summary = _consolidated_summary(
        resolved_config,
        session_root,
        data_quality_gate,
        orchestrator_result,
    )
    summary_path = None
    report_json_path = None
    report_markdown_path = None
    if resolved_config.generate_report:
        rendered = render_session_report(summary, session_root, write_files=True)
        report_json_path = rendered["report_json_path"]
        report_markdown_path = rendered["report_markdown_path"]
        summary["session_report_path"] = report_json_path
        summary["session_report_markdown_path"] = report_markdown_path
    if resolved_config.persist_session_summary:
        summary_path = str(_write_session_summary(summary, session_root))
    return GASessionResult(
        success=orchestrator_result.success,
        run_id=resolved_config.run_id,
        session_summary=sanitize_mapping(summary),
        session_summary_path=summary_path,
        report_json_path=report_json_path,
        report_markdown_path=report_markdown_path,
        orchestrator_result=orchestrator_result,
        reason=orchestrator_result.reason,
    )
