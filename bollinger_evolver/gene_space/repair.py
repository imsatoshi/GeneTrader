"""Repair helpers for Bollinger Evolver genes."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from .schema import GeneSpace, load_gene_space


def repair_genes(
    genes: Mapping[str, Any],
    gene_space: GeneSpace | None = None,
) -> Dict[str, Any]:
    """Repair numeric out-of-range gene values without touching unknown fields."""

    resolved_gene_space = gene_space or load_gene_space()
    repaired = dict(genes)

    for gene_name, definition in resolved_gene_space.items():
        if gene_name not in repaired:
            continue

        value = repaired[gene_name]
        if definition.gene_type == "int":
            if isinstance(value, int) and not isinstance(value, bool):
                repaired[gene_name] = max(
                    int(definition.minimum),
                    min(int(definition.maximum), value),
                )
        elif definition.gene_type == "float":
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_value = float(value)
                repaired[gene_name] = max(
                    float(definition.minimum),
                    min(float(definition.maximum), numeric_value),
                )

    return repaired
