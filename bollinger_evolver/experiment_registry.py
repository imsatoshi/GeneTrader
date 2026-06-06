"""Local JSONL experiment registry for mock GA runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REGISTRY_FILENAME = "experiments.jsonl"


@dataclass(frozen=True)
class ExperimentRecord:
    run_id: str
    source: str
    seed: int
    generations: int
    population_size: int
    best_fitness: float
    artifact_dir: str
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data["created_at"]:
            data["created_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        json.dumps(data, sort_keys=True)
        return data


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_registry_output_dir(output_dir: str | Path) -> Path:
    """Validate explicit registry output directory."""

    if output_dir is None or not str(output_dir).strip():
        raise ValueError("registry_output_dir_required")
    destination = Path(output_dir).resolve()
    root = _repo_root().resolve()
    disallowed = (
        root / ".runtime",
        root / "user_data" / "data",
    )
    if any(destination == item or _is_relative_to(destination, item) for item in disallowed):
        raise ValueError("registry_output_dir_disallowed")
    return destination


def _record_to_dict(record: ExperimentRecord | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(record, ExperimentRecord):
        data = record.to_dict()
    elif isinstance(record, Mapping):
        data = dict(record)
        data.setdefault("created_at", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    else:
        raise TypeError("experiment_record_must_be_mapping_or_dataclass")
    required = (
        "run_id",
        "created_at",
        "source",
        "seed",
        "generations",
        "population_size",
        "best_fitness",
        "artifact_dir",
        "notes",
    )
    missing = [field for field in required if field not in data]
    if missing:
        raise ValueError(f"experiment_record_missing_fields:{','.join(missing)}")
    json.dumps(data, sort_keys=True)
    return data


def append_experiment_record(
    output_dir: str | Path,
    record: ExperimentRecord | Mapping[str, Any],
    *,
    filename: str = REGISTRY_FILENAME,
) -> Path:
    """Append one JSON-safe experiment record and return the registry path."""

    destination = validate_registry_output_dir(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    registry_path = destination / filename
    payload = _record_to_dict(record)
    with registry_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return registry_path


def read_experiment_records(
    output_dir: str | Path,
    *,
    filename: str = REGISTRY_FILENAME,
) -> list[dict[str, Any]]:
    """Read JSONL experiment records from an explicit registry directory."""

    registry_path = validate_registry_output_dir(output_dir) / filename
    if not registry_path.exists():
        return []
    records: list[dict[str, Any]] = []
    with registry_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            item = json.loads(text)
            if not isinstance(item, dict):
                raise ValueError("experiment_record_line_must_be_object")
            records.append(item)
    return records
