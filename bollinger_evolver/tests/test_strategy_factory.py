"""Tests for the Bollinger strategy factory."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import shutil
import unittest
from pathlib import Path

from bollinger_evolver.gene_space import load_gene_space, sample_genes
from bollinger_evolver.genome import Genome, create_population
from bollinger_evolver.strategy_factory import (
    GENERATED_ROOT,
    StrategyConfig,
    StrategyFactoryError,
    generate_strategy_from_genes,
    strategy_config_from_genome,
    strategy_configs_from_population,
)


TEST_OUTPUT_DIR = GENERATED_ROOT / "test_factory"


def _valid_genes() -> dict:
    return sample_genes(load_gene_space())


class TestStrategyFactory(unittest.TestCase):
    def setUp(self) -> None:
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def tearDown(self) -> None:
        if TEST_OUTPUT_DIR.exists():
            shutil.rmtree(TEST_OUTPUT_DIR)

    def test_generates_strategy_file(self) -> None:
        result = generate_strategy_from_genes(
            _valid_genes(),
            generation=3,
            individual_index=42,
            output_dir=str(TEST_OUTPUT_DIR),
        )

        self.assertEqual(result["strategy_name"], "BollingerResonance_Gen003_Ind042")
        self.assertEqual(result["gene_id"], "gen003_ind042")
        self.assertTrue(Path(result["output_path"]).exists())
        self.assertTrue(result["written"])

    def test_generated_file_contains_metadata_and_inheritance(self) -> None:
        genes = _valid_genes()
        result = generate_strategy_from_genes(
            genes,
            generation=3,
            individual_index=42,
            output_dir=str(TEST_OUTPUT_DIR),
        )

        content = Path(result["output_path"]).read_text(encoding="utf-8")
        self.assertIn('GENE_ID = "gen003_ind042"', content)
        self.assertIn('GENES_HASH = "', content)
        self.assertIn("GENES = {", content)
        self.assertIn("DEFAULT_GENES = GENES.copy()", content)
        self.assertIn(
            "class BollingerResonance_Gen003_Ind042(BollingerResonanceStrategy):",
            content,
        )

    def test_missing_gene_validation_fails(self) -> None:
        genes = _valid_genes()
        genes.pop("mode")

        with self.assertRaises(Exception):
            generate_strategy_from_genes(
                genes,
                generation=1,
                individual_index=1,
                output_dir=str(TEST_OUTPUT_DIR),
            )

    def test_out_of_range_gene_validation_fails(self) -> None:
        genes = _valid_genes()
        genes["atr_stop_mult"] = 99.0

        with self.assertRaises(Exception):
            generate_strategy_from_genes(
                genes,
                generation=1,
                individual_index=1,
                output_dir=str(TEST_OUTPUT_DIR),
            )

    def test_existing_file_requires_overwrite(self) -> None:
        genes = _valid_genes()
        generate_strategy_from_genes(
            genes,
            generation=1,
            individual_index=1,
            output_dir=str(TEST_OUTPUT_DIR),
        )

        with self.assertRaises(FileExistsError):
            generate_strategy_from_genes(
                genes,
                generation=1,
                individual_index=1,
                output_dir=str(TEST_OUTPUT_DIR),
            )

    def test_overwrite_true_allows_replace(self) -> None:
        first_genes = _valid_genes()
        second_genes = _valid_genes()
        second_genes["mode"] = "breakout" if first_genes["mode"] != "breakout" else "hybrid"

        first = generate_strategy_from_genes(
            first_genes,
            generation=1,
            individual_index=1,
            output_dir=str(TEST_OUTPUT_DIR),
        )
        second = generate_strategy_from_genes(
            second_genes,
            generation=1,
            individual_index=1,
            output_dir=str(TEST_OUTPUT_DIR),
            overwrite=True,
        )

        self.assertEqual(first["output_path"], second["output_path"])
        content = Path(second["output_path"]).read_text(encoding="utf-8")
        self.assertIn(second_genes["mode"], content)

    def test_output_dir_must_stay_within_generated_root(self) -> None:
        with self.assertRaises(StrategyFactoryError):
            generate_strategy_from_genes(
                _valid_genes(),
                generation=1,
                individual_index=1,
                output_dir=str(GENERATED_ROOT.parent),
            )

    def test_output_dir_path_traversal_fails(self) -> None:
        with self.assertRaises(StrategyFactoryError):
            generate_strategy_from_genes(
                _valid_genes(),
                generation=1,
                individual_index=1,
                output_dir="user_data/strategies/generated/../../outside",
            )

    def test_generated_module_compiles_and_may_import(self) -> None:
        result = generate_strategy_from_genes(
            _valid_genes(),
            generation=2,
            individual_index=5,
            output_dir=str(TEST_OUTPUT_DIR),
        )
        source = Path(result["output_path"]).read_text(encoding="utf-8")
        compile(source, result["output_path"], "exec")

        spec = importlib.util.spec_from_file_location("generated_strategy", result["output_path"])
        module = importlib.util.module_from_spec(spec)
        try:
            assert spec.loader is not None
            spec.loader.exec_module(module)
        except ModuleNotFoundError as exc:
            if exc.name != "freqtrade":
                raise
        else:
            self.assertEqual(module.GENE_ID, "gen002_ind005")
            self.assertTrue(hasattr(module, "GENES_HASH"))

    def test_genes_hash_is_stable(self) -> None:
        genes = _valid_genes()
        result = generate_strategy_from_genes(
            genes,
            generation=7,
            individual_index=9,
            output_dir=str(TEST_OUTPUT_DIR),
        )

        expected_hash = hashlib.sha256(
            json.dumps(genes, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(result["genes_hash"], expected_hash)

    def test_generation_and_individual_must_be_non_negative(self) -> None:
        with self.assertRaises(StrategyFactoryError):
            generate_strategy_from_genes(
                _valid_genes(),
                generation=-1,
                individual_index=0,
                output_dir=str(TEST_OUTPUT_DIR),
            )


class TestStrategyConfigFromGenome(unittest.TestCase):
    def test_single_genome_converts_to_strategy_config(self) -> None:
        genome = Genome(
            genome_id="genome-001",
            parameters={
                "bb_window": 20,
                "bb_stddev": 2.0,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08,
                "leverage": 3.0,
                "risk_per_trade": 0.01,
            },
        )

        config = strategy_config_from_genome(genome)

        self.assertIsInstance(config, StrategyConfig)
        self.assertEqual(config.genome_id, "genome-001")
        self.assertEqual(config.bollinger_window, 20)
        self.assertEqual(config.bollinger_stddev, 2.0)
        self.assertEqual(config.stoploss, 0.03)
        self.assertEqual(config.takeprofit, 0.08)
        self.assertEqual(config.leverage, 3.0)
        self.assertEqual(config.risk_per_trade, 0.01)

    def test_population_converts_to_strategy_configs(self) -> None:
        population = create_population(5, random.Random(21))

        configs = strategy_configs_from_population(population)

        self.assertEqual(len(configs), 5)
        self.assertEqual([item.genome_id for item in configs], [item.genome_id for item in population])

    def test_strategy_config_is_json_safe(self) -> None:
        genome = create_population(1, random.Random(8))[0]
        config = strategy_config_from_genome(genome)

        encoded = json.dumps(config.to_dict(), sort_keys=True)

        self.assertIn(genome.genome_id, encoded)

    def test_invalid_genome_rejected(self) -> None:
        genome = Genome(
            genome_id="bad",
            parameters={
                "bb_window": 999,
                "bb_stddev": 2.0,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.08,
                "leverage": 3.0,
                "risk_per_trade": 0.01,
            },
        )

        with self.assertRaises(ValueError):
            strategy_config_from_genome(genome)
