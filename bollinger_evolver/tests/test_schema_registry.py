"""Tests for the JSON contract schema registry."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.schema_registry import (
    get_schema_version,
    list_registered_schemas,
    validate_known_schema_name,
)


class TestSchemaRegistry(unittest.TestCase):
    def test_all_expected_schema_names_are_registered(self) -> None:
        names = {item["name"] for item in list_registered_schemas()}

        self.assertEqual(
            names,
            {
                "offline-preflight/v1",
                "ga-session-summary/v1",
                "generation-artifact/v1",
                "normalized-backtest-result/v1",
                "custom-strategy-config/v1",
                "experiment-registry-record/v1",
                "frontend-session-summary/v1",
                "experiment-comparison/v1",
                "risk-budget-simulation/v1",
                "drawdown-circuit-breaker/v1",
                "loss-streak-control/v1",
                "position-sizing/v1",
                "strategy-explainability/v1",
                "mock-risk-report/v1",
                "owner-review-pack/v1",
                "owner-review-risk-summary/v1",
                "local-mainline-health-report/v1",
            },
        )

    def test_get_schema_version_returns_stable_versions(self) -> None:
        self.assertEqual(get_schema_version("ga-session-summary/v1"), "ga-session-summary/v1")
        self.assertEqual(get_schema_version("generation-artifact/v1"), "ga-generation-artifact/v1")
        self.assertEqual(get_schema_version("normalized-backtest-result/v1"), "normalized-backtest-result/v1")
        self.assertEqual(get_schema_version("custom-strategy-config/v1"), "custom-strategy/v1")
        self.assertEqual(get_schema_version("offline-preflight/v1"), "1.0")
        self.assertEqual(get_schema_version("owner-review-pack/v1"), "owner-review-pack/v1")
        self.assertEqual(get_schema_version("mock-risk-report/v1"), "mock-risk-report/v1")
        self.assertEqual(get_schema_version("local-mainline-health-report/v1"), "local-mainline-health-report/v1")

    def test_list_registered_schemas_is_json_safe(self) -> None:
        payload = list_registered_schemas()

        encoded = json.dumps(payload, sort_keys=True)

        self.assertIn("experiment-registry-record/v1", encoded)
        self.assertTrue(all("required_fields" in item for item in payload))

    def test_validate_known_schema_name(self) -> None:
        self.assertTrue(validate_known_schema_name("frontend-session-summary/v1"))
        self.assertFalse(validate_known_schema_name("missing/v1"))

    def test_unknown_schema_name_fails(self) -> None:
        with self.assertRaisesRegex(KeyError, "unknown_schema_name"):
            get_schema_version("missing/v1")


if __name__ == "__main__":
    unittest.main()
