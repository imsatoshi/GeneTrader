"""Validation for Bollinger Evolver genes."""

from __future__ import annotations

from typing import Any, Mapping

from .schema import GeneDefinition, GeneSpace, load_gene_space


class GeneValidationError(Exception):
    """Raised when a gene payload does not match the declared gene space."""


def _validate_type(gene_name: str, value: Any, definition: GeneDefinition) -> None:
    if definition.gene_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise GeneValidationError(
                f"Gene '{gene_name}' must be int, got {type(value).__name__}."
            )
        return

    if definition.gene_type == "float":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise GeneValidationError(
                f"Gene '{gene_name}' must be float-compatible, got {type(value).__name__}."
            )
        return

    if definition.gene_type == "bool":
        if not isinstance(value, bool):
            raise GeneValidationError(
                f"Gene '{gene_name}' must be bool, got {type(value).__name__}."
            )
        return

    if definition.gene_type == "choice":
        if value not in definition.choices:
            raise GeneValidationError(
                f"Gene '{gene_name}' must be one of {list(definition.choices)}, got {value!r}."
            )
        return

    raise GeneValidationError(
        f"Gene '{gene_name}' uses unsupported type '{definition.gene_type}'."
    )


def _validate_range(gene_name: str, value: Any, definition: GeneDefinition) -> None:
    if definition.gene_type == "int":
        if value < definition.minimum or value > definition.maximum:
            raise GeneValidationError(
                f"Gene '{gene_name}'={value} is out of range "
                f"[{definition.minimum}, {definition.maximum}]."
            )
        return

    if definition.gene_type == "float":
        numeric_value = float(value)
        if numeric_value < float(definition.minimum) or numeric_value > float(definition.maximum):
            raise GeneValidationError(
                f"Gene '{gene_name}'={numeric_value} is out of range "
                f"[{definition.minimum}, {definition.maximum}]."
            )


def validate_genes(
    genes: Mapping[str, Any],
    gene_space: GeneSpace | None = None,
) -> None:
    """Validate a gene dictionary against the declared gene space."""

    if not isinstance(genes, Mapping):
        raise GeneValidationError("Genes must be provided as a mapping.")

    resolved_gene_space = gene_space or load_gene_space()

    unknown_fields = sorted(set(genes.keys()).difference(resolved_gene_space.keys()))
    if unknown_fields:
        raise GeneValidationError(f"Unknown gene fields: {', '.join(unknown_fields)}")

    missing_fields = sorted(set(resolved_gene_space.keys()).difference(genes.keys()))
    if missing_fields:
        raise GeneValidationError(f"Missing gene fields: {', '.join(missing_fields)}")

    for gene_name, definition in resolved_gene_space.items():
        value = genes[gene_name]
        _validate_type(gene_name, value, definition)
        _validate_range(gene_name, value, definition)
