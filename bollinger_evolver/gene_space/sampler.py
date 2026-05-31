"""Random sampling for Bollinger Evolver gene spaces."""

from __future__ import annotations

import random
from typing import Any, Dict

from .schema import GeneSpace, load_gene_space


def sample_genes(
    gene_space: GeneSpace | None = None,
    *,
    rng: random.Random | None = None,
) -> Dict[str, Any]:
    """Sample one JSON-serializable gene set from a gene space."""

    resolved_gene_space = gene_space or load_gene_space()
    generator = rng or random.Random()
    sampled: Dict[str, Any] = {}

    for gene_name, definition in resolved_gene_space.items():
        if definition.gene_type == "int":
            sampled[gene_name] = generator.randint(
                int(definition.minimum),
                int(definition.maximum),
            )
        elif definition.gene_type == "float":
            sampled[gene_name] = float(
                generator.uniform(float(definition.minimum), float(definition.maximum))
            )
        elif definition.gene_type == "bool":
            sampled[gene_name] = generator.choice([True, False])
        elif definition.gene_type == "choice":
            sampled[gene_name] = generator.choice(list(definition.choices))
        else:
            raise ValueError(f"Unsupported gene type: {definition.gene_type}")

    return sampled
