"""Static checks for the safe local test matrix scripts."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_safe_test_matrix_scripts_only_run_validation_commands() -> None:
    script = (ROOT / "scripts" / "run_safe_test_matrix.ps1").read_text(encoding="utf-8").lower()

    for expected in (
        "python -m pytest tests -q",
        "python -m unittest discover -s bollinger_evolver/tests",
        "npm.cmd test -- runexplorercustompage runcomparisonpage riskdashboardpage mockdashboardpage",
        "npm.cmd test",
        "npm.cmd run build",
        "python -m compileall",
        "diff --check",
        "diff --cached --check",
    ):
        assert expected in script


def test_safe_test_matrix_scripts_do_not_include_blocked_actions() -> None:
    combined = "\n".join(
        [
            (ROOT / "scripts" / "run_safe_test_matrix.ps1").read_text(encoding="utf-8").lower(),
            (ROOT / "scripts" / "run_safe_test_matrix.cmd").read_text(encoding="utf-8").lower(),
        ]
    )

    for forbidden in (
        "freqtrade",
        "download-data",
        "hyperopt",
        "deploy",
        "rollback",
        "exchange api",
        "git reset",
        "git clean",
        "git push",
    ):
        assert forbidden not in combined


def test_safe_test_matrix_covers_mock_pipeline_validation_roots() -> None:
    script = (ROOT / "scripts" / "run_safe_test_matrix.ps1").read_text(encoding="utf-8").lower()

    for expected in (
        "python -m pytest tests -q",
        "python -m unittest discover -s bollinger_evolver/tests",
        "runexplorercustompage",
        "runcomparisonpage",
        "riskdashboardpage",
        "mockdashboardpage",
        "npm.cmd run build",
        "python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests",
    ):
        assert expected in script


def test_safe_test_matrix_keeps_diff_checks_at_repo_root() -> None:
    script = (ROOT / "scripts" / "run_safe_test_matrix.ps1").read_text(encoding="utf-8").lower()

    assert "push-location $reporoot" in script
    assert 'git -c safe.directory="$reporoot" diff --check' in script
    assert 'git -c safe.directory="$reporoot" diff --cached --check' in script
