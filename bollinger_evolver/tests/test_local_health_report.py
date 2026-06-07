"""Tests for local mainline health report generator."""

from __future__ import annotations

import html.parser
import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.local_health_report import (
    build_local_mainline_health_report,
    render_health_html,
    render_health_markdown,
    validate_health_report_output_dir,
    write_local_mainline_health_report,
)


class _TitleParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.seen_h1 = False

    def handle_starttag(self, tag, attrs):  # noqa: D401, ANN001
        if tag == "h1":
            self.seen_h1 = True


class TestLocalHealthReport(unittest.TestCase):
    def test_health_report_json_and_html_are_parseable(self) -> None:
        report = build_local_mainline_health_report()
        html_text = render_health_html(report)
        parser = _TitleParser()

        parser.feed(html_text)
        encoded = json.dumps(report, sort_keys=True)

        self.assertIn("local-mainline-health-report/v1", encoded)
        self.assertTrue(parser.seen_h1)

    def test_health_report_module_status_statistics(self) -> None:
        report = build_local_mainline_health_report()

        self.assertEqual(report["module_status"]["schema_registry"], "ready")
        self.assertEqual(report["safety_boundary"]["real_backtest"], "BLOCKED")
        self.assertTrue(all(item["status"] == "passed" for item in report["test_results"]))

    def test_health_report_markdown_mentions_blocked_gate(self) -> None:
        markdown = render_health_markdown(build_local_mainline_health_report())

        self.assertIn("Real backtest: BLOCKED", markdown)
        self.assertIn("npm run build", markdown)

    def test_health_report_writes_to_explicit_tempdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "health"

            paths = write_local_mainline_health_report(output)

            self.assertTrue(Path(paths["json"]).exists())
            self.assertTrue(Path(paths["markdown"]).exists())
            self.assertTrue(Path(paths["html"]).exists())

    def test_health_report_rejects_disallowed_output(self) -> None:
        root = Path(__file__).resolve().parents[2]

        with self.assertRaisesRegex(ValueError, "repo_root"):
            validate_health_report_output_dir(root)
        with self.assertRaisesRegex(ValueError, "disallowed"):
            validate_health_report_output_dir(root / ".runtime" / "health")
        with self.assertRaisesRegex(ValueError, "disallowed"):
            validate_health_report_output_dir(root / "user_data" / "data" / "health")


if __name__ == "__main__":
    unittest.main()
