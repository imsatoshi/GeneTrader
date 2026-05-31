"""Schema loading for Bollinger Evolver gene spaces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping


DEFAULT_GENE_SPACE_PATH = (
    Path(__file__).resolve().parent / "bollinger_resonance_gene_space.json"
)
SUPPORTED_GENE_TYPES = {"int", "float", "bool", "choice"}


class GeneSchemaError(Exception):
    """Raised when a gene-space definition is missing or malformed."""


@dataclass(frozen=True)
class GeneDefinition:
    """Normalized definition for a single gene."""

    name: str
    gene_type: str
    minimum: int | float | None = None
    maximum: int | float | None = None
    choices: tuple[Any, ...] = ()


GeneSpace = Dict[str, GeneDefinition]


def _ensure_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GeneSchemaError(f"{context} must be a JSON object.")
    return value


def _build_definition(name: str, raw_definition: Mapping[str, Any]) -> GeneDefinition:
    gene_type = raw_definition.get("type")
    if gene_type not in SUPPORTED_GENE_TYPES:
        raise GeneSchemaError(
            f"Gene '{name}' has unsupported type '{gene_type}'. "
            f"Supported types: {sorted(SUPPORTED_GENE_TYPES)}."
        )

    if gene_type == "choice":
        choices = raw_definition.get("choice")
        if not isinstance(choices, list) or not choices:
            raise GeneSchemaError(
                f"Gene '{name}' of type 'choice' must define a non-empty 'choice' list."
            )
        return GeneDefinition(name=name, gene_type=gene_type, choices=tuple(choices))

    if gene_type == "bool":
        return GeneDefinition(name=name, gene_type=gene_type)

    minimum = raw_definition.get("min")
    maximum = raw_definition.get("max")
    if not isinstance(minimum, (int, float)) or isinstance(minimum, bool):
        raise GeneSchemaError(f"Gene '{name}' must define numeric 'min'.")
    if not isinstance(maximum, (int, float)) or isinstance(maximum, bool):
        raise GeneSchemaError(f"Gene '{name}' must define numeric 'max'.")
    if minimum > maximum:
        raise GeneSchemaError(f"Gene '{name}' has min greater than max.")

    if gene_type == "int":
        if not isinstance(minimum, int) or not isinstance(maximum, int):
            raise GeneSchemaError(f"Gene '{name}' of type 'int' must use integer min/max.")
    return GeneDefinition(
        name=name,
        gene_type=gene_type,
        minimum=minimum,
        maximum=maximum,
    )


def normalize_gene_space(raw_gene_space: Mapping[str, Any]) -> GeneSpace:
    """Normalize a parsed gene-space JSON object into typed definitions."""

    root = _ensure_mapping(raw_gene_space, context="Gene space")
    genes = _ensure_mapping(root.get("genes"), context="Gene space 'genes'")
    if not genes:
        raise GeneSchemaError("Gene space must contain at least one gene definition.")

    normalized: GeneSpace = {}
    for gene_name, raw_definition in genes.items():
        normalized[gene_name] = _build_definition(
            gene_name,
            _ensure_mapping(raw_definition, context=f"Gene '{gene_name}'"),
        )
    return normalized


def load_gene_space(gene_space_path: str | Path = DEFAULT_GENE_SPACE_PATH) -> GeneSpace:
    """Load a Bollinger Evolver gene space from JSON."""

    path = Path(gene_space_path)
    if not path.exists():
        raise GeneSchemaError(f"Gene-space file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GeneSchemaError(f"Invalid JSON in gene-space file: {exc}") from exc

    return normalize_gene_space(data)
