"""Central registry for stable JSON contract schema names.

The registry is descriptive only. It does not validate business payloads, run
backtests, import Freqtrade, or write artifacts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SchemaRegistration:
    name: str
    version: str
    producer: str
    required_fields: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_fields"] = list(self.required_fields)
        json.dumps(payload, sort_keys=True)
        return payload


_SCHEMAS: tuple[SchemaRegistration, ...] = (
    SchemaRegistration(
        name="offline-preflight/v1",
        version="1.0",
        producer="bollinger_evolver.preflight",
        required_fields=(
            "schema_name",
            "schema_version",
            "ok",
            "summary",
            "datasets",
            "issues",
            "warnings",
            "metadata",
        ),
        description="Read-only offline data preflight report.",
    ),
    SchemaRegistration(
        name="ga-session-summary/v1",
        version="ga-session-summary/v1",
        producer="bollinger_evolver.session_summary",
        required_fields=(
            "schema_version",
            "source",
            "run_id",
            "status",
            "generation",
            "population_size",
            "best_fitness",
            "fitness_series",
            "leaderboard",
        ),
        description="Mock-first GA session summary consumed by frontend adapters.",
    ),
    SchemaRegistration(
        name="generation-artifact/v1",
        version="ga-generation-artifact/v1",
        producer="bollinger_evolver.artifact_export",
        required_fields=(
            "schema_version",
            "source",
            "run_id",
            "generation",
            "population_size",
            "best_fitness",
            "genomes",
            "session_summary",
        ),
        description="Mock GA generation artifact with session summary snapshot.",
    ),
    SchemaRegistration(
        name="normalized-backtest-result/v1",
        version="normalized-backtest-result/v1",
        producer="bollinger_evolver.backtest_adapter",
        required_fields=(
            "profit",
            "sharpe",
            "win_rate",
            "max_drawdown",
            "total_trades",
            "max_consecutive_losses",
            "leverage",
            "risk_per_trade",
            "metadata",
        ),
        description="Stable JSON-safe backtest result contract for mock and future gated real adapters.",
    ),
    SchemaRegistration(
        name="custom-strategy-config/v1",
        version="custom-strategy/v1",
        producer="bollinger_evolver.custom_strategy_schema",
        required_fields=(
            "schema_version",
            "genome_id",
            "entry",
            "exit",
            "position_sizing",
            "execution_controls",
            "constraints",
            "parameters",
        ),
        description="Custom strategy config derived from a validated custom genome.",
    ),
    SchemaRegistration(
        name="experiment-registry-record/v1",
        version="experiment-registry-record/v1",
        producer="bollinger_evolver.experiment_registry",
        required_fields=(
            "run_id",
            "created_at",
            "source",
            "seed",
            "generations",
            "population_size",
            "best_fitness",
            "artifact_dir",
            "notes",
        ),
        description="Local JSONL experiment registry record.",
    ),
    SchemaRegistration(
        name="frontend-session-summary/v1",
        version="session-summary/v1",
        producer="frontend/src/types/sessionSummary.ts",
        required_fields=(
            "schemaVersion",
            "generatedAt",
            "source",
            "offlineData",
            "requirementsGate",
            "gaRunSummary",
        ),
        description="Frontend dashboard session summary fixture contract.",
    ),
    SchemaRegistration(
        name="experiment-comparison/v1",
        version="experiment-comparison/v1",
        producer="bollinger_evolver.experiment_compare",
        required_fields=("schema_version", "run_count", "best_by_fitness", "best_by_drawdown", "best_by_stability", "ranked"),
        description="Local mock experiment comparison output.",
    ),
    SchemaRegistration(
        name="risk-budget-simulation/v1",
        version="risk-budget-simulation/v1",
        producer="bollinger_evolver.risk_budget",
        required_fields=("schema_version", "ok", "total_exposure", "pair_exposures", "violations", "recommendations"),
        description="Mock account-level risk budget simulation.",
    ),
    SchemaRegistration(
        name="drawdown-circuit-breaker/v1",
        version="drawdown-circuit-breaker/v1",
        producer="bollinger_evolver.drawdown_circuit_breaker",
        required_fields=("schema_version", "triggered", "trigger_index", "max_drawdown", "action"),
        description="Mock drawdown circuit breaker simulation.",
    ),
    SchemaRegistration(
        name="loss-streak-control/v1",
        version="loss-streak-control/v1",
        producer="bollinger_evolver.loss_streak_control",
        required_fields=("schema_version", "loss_streak", "triggered", "actions", "original", "adjusted"),
        description="Mock loss streak risk reducer output.",
    ),
    SchemaRegistration(
        name="position-sizing/v1",
        version="position-sizing/v1",
        producer="bollinger_evolver.position_sizing",
        required_fields=("schema_version", "position_value", "margin_required", "risk_amount", "leverage", "warnings"),
        description="Mock position sizing preview.",
    ),
    SchemaRegistration(
        name="strategy-explainability/v1",
        version="strategy-explainability/v1",
        producer="bollinger_evolver.strategy_explainer",
        required_fields=("schema_version", "summary", "entry_logic", "exit_logic", "risk_logic", "warnings", "fitness_explanation"),
        description="JSON-safe strategy explainability report.",
    ),
    SchemaRegistration(
        name="mock-risk-report/v1",
        version="mock-risk-report/v1",
        producer="bollinger_evolver.risk_cli",
        required_fields=("schema_version", "fixture", "strategy_id", "metrics", "risk_governor", "position_sizing_preview", "warnings", "safety"),
        description="Fixture-only custom strategy risk report.",
    ),
    SchemaRegistration(
        name="owner-review-pack/v1",
        version="owner-review-pack/v1",
        producer="bollinger_evolver.owner_review_pack",
        required_fields=("schema_version", "status", "parameter_table", "hard_constraints", "risk_summary", "fixtures", "real_backtest_gate", "safety"),
        description="Owner review package for custom strategy abstraction.",
    ),
    SchemaRegistration(
        name="owner-review-risk-summary/v1",
        version="owner-review-risk-summary/v1",
        producer="bollinger_evolver.owner_review_pack",
        required_fields=("schema_version", "fixture_count", "fixtures_with_warnings", "risk_level_counts", "warning_counts", "visualization"),
        description="Risk visualization summary embedded in owner review packs.",
    ),
    SchemaRegistration(
        name="local-mainline-health-report/v1",
        version="local-mainline-health-report/v1",
        producer="bollinger_evolver.local_health_report",
        required_fields=("schema_version", "status", "git_state", "test_results", "module_status", "safety_boundary", "untracked_files"),
        description="Local mock-first mainline health report.",
    ),
)

_SCHEMAS_BY_NAME = {schema.name: schema for schema in _SCHEMAS}


def get_schema_version(name: str) -> str:
    """Return the stable schema version for a registered schema name."""

    try:
        return _SCHEMAS_BY_NAME[name].version
    except KeyError as exc:
        raise KeyError(f"unknown_schema_name:{name}") from exc


def list_registered_schemas() -> list[dict[str, Any]]:
    """Return all registered schemas as JSON-safe dictionaries."""

    payload = [schema.to_dict() for schema in sorted(_SCHEMAS, key=lambda item: item.name)]
    json.dumps(payload, sort_keys=True)
    return payload


def validate_known_schema_name(name: str) -> bool:
    """Return True when the schema name is registered."""

    return name in _SCHEMAS_BY_NAME
