"""Tests for owner review pack generator."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from bollinger_evolver import owner_review_pack


def _run_cli(args: list[str]) -> str:
    stream = io.StringIO()
    with redirect_stdout(stream):
        exit_code = owner_review_pack.main(args)
    if exit_code != 0:
        raise AssertionError(f"unexpected exit code: {exit_code}")
    return stream.getvalue()


def _contains_sensitive_field(value) -> bool:
    markers = ("api_key", "api_secret", "secret", "token", "password", "private_key")
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if not lowered.startswith("no_") and any(marker in lowered for marker in markers):
                return True
            if _contains_sensitive_field(item):
                return True
    if isinstance(value, list):
        return any(_contains_sensitive_field(item) for item in value)
    return False


class TestOwnerReviewPack(unittest.TestCase):
    def test_owner_review_pack_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "owner-review"

            stdout = _run_cli(["--output", str(output)])
            pack = json.loads((output / "owner_review_pack.json").read_text(encoding="utf-8"))
            summary = (output / "owner_review_summary.md").read_text(encoding="utf-8")

        self.assertIn("owner_review_pack", json.loads(stdout))
        self.assertEqual(pack["schema_version"], "owner-review-pack/v1")
        self.assertIn("APPROVED", summary)
        self.assertIn("NEEDS CHANGES", summary)

    def test_owner_review_pack_contains_parameter_table_and_fixtures(self) -> None:
        pack = owner_review_pack.build_owner_review_pack()

        self.assertGreaterEqual(len(pack["parameter_table"]), 14)
        self.assertIn("risk_summary", pack)
        self.assertIn("safe_default", [fixture["fixture"] for fixture in pack["fixtures"]])
        self.assertIn("position_sizing_preview", pack["fixtures"][0])
        self.assertIn("explainability_summary", pack["fixtures"][0])

    def test_owner_review_pack_contains_risk_summary(self) -> None:
        pack = owner_review_pack.build_owner_review_pack()

        self.assertEqual(pack["risk_summary"]["schema_version"], "owner-review-risk-summary/v1")
        self.assertGreater(pack["risk_summary"]["fixture_count"], 0)
        self.assertIn("visualization", pack["risk_summary"])
        self.assertIn("high", pack["risk_summary"]["risk_level_counts"])

    def test_owner_review_pack_rejects_disallowed_output(self) -> None:
        root = owner_review_pack._repo_root()

        with self.assertRaises(SystemExit):
            owner_review_pack.main(["--output", str(root)])
        with self.assertRaises(SystemExit):
            owner_review_pack.main(["--output", str(root / ".runtime" / "owner")])
        with self.assertRaises(SystemExit):
            owner_review_pack.main(["--output", str(root / "user_data" / "data" / "owner")])

    def test_owner_review_pack_contains_no_sensitive_fields(self) -> None:
        pack = owner_review_pack.build_owner_review_pack()

        self.assertFalse(_contains_sensitive_field(pack))
        json.dumps(pack, sort_keys=True)

    def test_owner_review_pack_json_serializable(self) -> None:
        pack = owner_review_pack.build_owner_review_pack()

        encoded = json.dumps(pack, sort_keys=True)

        self.assertIn("owner-review-pack/v1", encoded)


if __name__ == "__main__":
    unittest.main()
