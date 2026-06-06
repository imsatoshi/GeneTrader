"""Custom strategy experiment registry helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bollinger_evolver.experiment_registry import (
    ExperimentRecord,
    append_experiment_record,
    read_experiment_records,
)
from bollinger_evolver.ga_execution_custom import CustomGAExecutionResult, build_custom_ga_session_summary


def custom_experiment_record_from_ga_result(
    execution_result: CustomGAExecutionResult,
    *,
    artifact_dir: str,
    notes: str = "",
) -> ExperimentRecord:
    """Build a JSON-safe experiment record from a custom GA execution result."""

    summary = build_custom_ga_session_summary(execution_result)
    record = ExperimentRecord(
        run_id=str(summary["run_id"]),
        source="custom-strategy-mock-ga",
        seed=int(execution_result.config.seed),
        generations=int(execution_result.config.generations),
        population_size=int(execution_result.config.population_size),
        best_fitness=float(summary["best_fitness"] or 0.0),
        artifact_dir=str(artifact_dir),
        notes=str(notes),
    )
    json.dumps(record.to_dict(), sort_keys=True)
    return record


def append_custom_experiment_record(
    output_dir: str | Path,
    execution_result: CustomGAExecutionResult,
    *,
    artifact_dir: str,
    notes: str = "",
) -> Path:
    """Append one custom strategy GA run record to a local JSONL registry."""

    return append_experiment_record(
        output_dir,
        custom_experiment_record_from_ga_result(
            execution_result,
            artifact_dir=artifact_dir,
            notes=notes,
        ),
    )


def read_custom_experiment_records(output_dir: str | Path) -> list[dict[str, Any]]:
    """Read custom strategy experiment registry records."""

    records = read_experiment_records(output_dir)
    json.dumps(records, sort_keys=True)
    return records
