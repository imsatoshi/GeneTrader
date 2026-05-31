"""Tests for Bollinger Evolver gene-space helpers."""

from __future__ import annotations

import json
import random
import unittest

from bollinger_evolver.gene_space import (
    DEFAULT_GENE_SPACE_PATH,
    GeneSchemaError,
    GeneValidationError,
    load_gene_space,
    repair_genes,
    sample_genes,
    validate_genes,
)


class TestGeneSpaceSchema(unittest.TestCase):
    def test_loads_gene_space(self) -> None:
        gene_space = load_gene_space()

        self.assertIn("bb_period_15m", gene_space)
        self.assertIn("mode", gene_space)
        self.assertEqual(gene_space["mode"].gene_type, "choice")

    def test_default_json_exists(self) -> None:
        self.assertTrue(DEFAULT_GENE_SPACE_PATH.exists())


class TestGeneSampling(unittest.TestCase):
    def setUp(self) -> None:
        self.gene_space = load_gene_space()

    def test_sampled_genes_are_json_serializable(self) -> None:
        genes = sample_genes(self.gene_space, rng=random.Random(7))
        encoded = json.dumps(genes)
        self.assertIsInstance(encoded, str)

    def test_sampled_choice_is_from_allowed_values(self) -> None:
        allowed = set(self.gene_space["mode"].choices)
        for seed in range(50):
            genes = sample_genes(self.gene_space, rng=random.Random(seed))
            self.assertIn(genes["mode"], allowed)

    def test_sampling_1000_times_stays_in_range(self) -> None:
        rng = random.Random(42)
        for _ in range(1000):
            genes = sample_genes(self.gene_space, rng=rng)
            validate_genes(genes, self.gene_space)


class TestGeneValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.gene_space = load_gene_space()
        self.valid_genes = sample_genes(self.gene_space, rng=random.Random(1))

    def test_unknown_gene_raises(self) -> None:
        genes = dict(self.valid_genes)
        genes["unknown_gene"] = 123

        with self.assertRaises(GeneValidationError):
            validate_genes(genes, self.gene_space)

    def test_wrong_type_raises(self) -> None:
        genes = dict(self.valid_genes)
        genes["bb_period_15m"] = "20"

        with self.assertRaises(GeneValidationError):
            validate_genes(genes, self.gene_space)

    def test_out_of_range_raises(self) -> None:
        genes = dict(self.valid_genes)
        genes["atr_stop_mult"] = 50.0

        with self.assertRaises(GeneValidationError):
            validate_genes(genes, self.gene_space)


class TestGeneRepair(unittest.TestCase):
    def setUp(self) -> None:
        self.gene_space = load_gene_space()
        self.valid_genes = sample_genes(self.gene_space, rng=random.Random(3))

    def test_repair_clamps_numeric_values(self) -> None:
        genes = dict(self.valid_genes)
        genes["bb_period_15m"] = -5
        genes["atr_stop_mult"] = 99.0

        repaired = repair_genes(genes, self.gene_space)

        self.assertEqual(repaired["bb_period_15m"], 10)
        self.assertEqual(repaired["atr_stop_mult"], 5.0)
        validate_genes(repaired, self.gene_space)

    def test_repair_keeps_unknown_fields(self) -> None:
        genes = dict(self.valid_genes)
        genes["external_note"] = "keep-me"

        repaired = repair_genes(genes, self.gene_space)

        self.assertEqual(repaired["external_note"], "keep-me")
