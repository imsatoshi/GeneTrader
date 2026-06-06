"""Generate lightweight strategy files from Bollinger gene payloads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from pprint import pformat
from typing import Any, Dict

from bollinger_evolver.gene_space import load_gene_space, validate_genes
from bollinger_evolver.genome import Genome, validate_genome as validate_execution_genome
from bollinger_evolver.risk_governor import RiskGovernorConfig, apply_risk_governor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATED_ROOT = (PROJECT_ROOT / "user_data" / "strategies" / "generated").resolve()


class StrategyFactoryError(Exception):
    """Raised when strategy file generation fails."""


@dataclass(frozen=True)
class StrategyConfig:
    """JSON-safe strategy configuration derived from a GA execution genome."""

    genome_id: str
    bollinger_window: int
    bollinger_stddev: float
    stoploss: float
    takeprofit: float
    leverage: float
    risk_per_trade: float
    parameters: Dict[str, int | float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def strategy_config_from_genome(genome: Genome) -> StrategyConfig:
    """Convert one GA execution genome into a strategy config snapshot."""

    validate_execution_genome(genome)
    params = dict(genome.parameters)
    return StrategyConfig(
        genome_id=genome.genome_id,
        bollinger_window=int(params["bb_window"]),
        bollinger_stddev=float(params["bb_stddev"]),
        stoploss=float(params["stop_loss_pct"]),
        takeprofit=float(params["take_profit_pct"]),
        leverage=float(params["leverage"]),
        risk_per_trade=float(params["risk_per_trade"]),
        parameters=params,
    )


def strategy_configs_from_population(population: list[Genome]) -> list[StrategyConfig]:
    """Convert a population of genomes into strategy config snapshots."""

    return [strategy_config_from_genome(genome) for genome in population]


def risk_governor_advice_for_strategy_config(
    strategy_config: StrategyConfig,
    metrics: Any,
    *,
    config: RiskGovernorConfig | None = None,
) -> dict[str, Any]:
    """Build advisory risk-governor output without mutating the strategy config."""

    return apply_risk_governor(strategy_config, metrics, config=config)


def _ensure_non_negative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise StrategyFactoryError(f"{field_name} must be a non-negative integer.")
    return value


def _format_gene_id(generation: int, individual_index: int) -> str:
    return f"gen{generation:03d}_ind{individual_index:03d}"


def _format_strategy_name(generation: int, individual_index: int) -> str:
    return f"BollingerResonance_Gen{generation:03d}_Ind{individual_index:03d}"


def _resolve_output_dir(output_dir: str) -> Path:
    candidate = Path(output_dir)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.resolve()

    if resolved != GENERATED_ROOT and GENERATED_ROOT not in resolved.parents:
        raise StrategyFactoryError(
            f"output_dir must stay within {GENERATED_ROOT}, got {resolved}."
        )
    return resolved


def _stable_genes_hash(genes: Dict[str, Any]) -> str:
    encoded = json.dumps(genes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _render_strategy_file(
    strategy_name: str,
    gene_id: str,
    genes_hash: str,
    genes: Dict[str, Any],
) -> str:
    genes_literal = pformat(dict(sorted(genes.items())), sort_dicts=True, width=88)
    return (
        'from user_data.strategies.BollingerResonanceStrategy import '
        "BollingerResonanceStrategy\n\n"
        f'GENE_ID = "{gene_id}"\n'
        f'GENES_HASH = "{genes_hash}"\n'
        f"GENES = {genes_literal}\n\n"
        f"class {strategy_name}(BollingerResonanceStrategy):\n"
        "    DEFAULT_GENES = GENES.copy()\n"
    )


def generate_strategy_from_genes(
    genes: dict,
    generation: int,
    individual_index: int,
    output_dir: str = "user_data/strategies/generated",
    base_strategy_class: str = "BollingerResonanceStrategy",
    overwrite: bool = False,
) -> dict:
    """Generate a lightweight inheriting strategy file from one gene payload."""

    if base_strategy_class != "BollingerResonanceStrategy":
        raise StrategyFactoryError(
            "Only base_strategy_class='BollingerResonanceStrategy' is supported."
        )
    if not isinstance(genes, dict):
        raise StrategyFactoryError("genes must be provided as a dict.")

    generation = _ensure_non_negative_int(generation, "generation")
    individual_index = _ensure_non_negative_int(individual_index, "individual_index")

    gene_space = load_gene_space()
    validate_genes(genes, gene_space)

    gene_id = _format_gene_id(generation, individual_index)
    strategy_name = _format_strategy_name(generation, individual_index)
    if not strategy_name.isidentifier():
        raise StrategyFactoryError(f"Generated strategy name is not a valid identifier: {strategy_name}")

    resolved_output_dir = _resolve_output_dir(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    output_path = resolved_output_dir / f"{strategy_name}.py"
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Strategy file already exists: {output_path}")

    genes_hash = _stable_genes_hash(genes)
    content = _render_strategy_file(strategy_name, gene_id, genes_hash, genes)
    output_path.write_text(content, encoding="utf-8")

    return {
        "strategy_name": strategy_name,
        "gene_id": gene_id,
        "output_path": str(output_path),
        "genes_hash": genes_hash,
        "written": True,
    }
