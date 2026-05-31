# Commit Split Plan

## Executive Summary

- recommended_commit_count: `4`
- commit_readiness: `NEEDS_REVIEW`
- manual_review_required: `true`
- do_not_commit_yet list:
  - `.runtime/`
  - `.pytest_cache/`
  - `__pycache__/`
  - generated strategy artifacts under `user_data/strategies/`
  - any local runtime output folders created during manual testing

This is a staging dry run only. The commands below are examples for manual use
and were not executed automatically as part of this task.

## Commit 1: GeneTrader Baseline / Security / Test Fixture Fixes

Include:

- `.gitignore`
- `data/downloader.py`
- `scripts/workflow.py`
- `strategy/backtest.py`
- `tests/test_backtest.py`
- `tests/test_evaluation.py`
- `tests/test_workflow.py`
- `tests/test_data_downloader.py`
- `user_data/example.json`
- `docs/test_baseline.md`

Why included:

- these files are the upstream GeneTrader baseline/security/data-QA fixes
- they are logically independent from the larger `bollinger_evolver/` module tree
- they restore test baseline, placeholder safety, config redaction, artifact cleanup, and data coverage QA

Validation commands:

```powershell
$env:GENETRADER_CONFIG='ga.json.example'
python -m pytest tests -q
python -m compileall genetic_algorithm config user_data/strategies strategy data scripts tests
```

Risk:

- medium
- touches existing tracked upstream files
- should be reviewed carefully for behavior drift in `workflow.py`, `backtest.py`, and `data/downloader.py`

## Commit 2: Bollinger Evolver Core / GA Mock Pipeline

Include:

- `bollinger_evolver/__init__.py`
- `bollinger_evolver/config_loader.py`
- `bollinger_evolver/data_quality.py`
- `bollinger_evolver/strategy_factory.py`
- `bollinger_evolver/evaluators/`
- `bollinger_evolver/gene_space/`
- `bollinger_evolver/scoring/`
- `bollinger_evolver/strategies/`
- `bollinger_evolver/runners/`
- `bollinger_evolver/reports/`
- `bollinger_evolver/utils/`
- `bollinger_evolver/ga/backtest_evaluation_adapter.py`
- `bollinger_evolver/ga/evaluation_pipeline.py`
- `bollinger_evolver/ga/generation_runner.py`
- `bollinger_evolver/ga/orchestrator.py`
- `bollinger_evolver/ga/population_ops.py`
- `bollinger_evolver/ga/smoke_run_pipeline.py`
- `config/ga_bollinger_resonance.json`
- core tests under `bollinger_evolver/tests/` excluding runner/report/doc-only pieces if you want those in commit 3

Why included:

- this is the main new feature surface
- it adds the isolated Bollinger Evolver namespace, mock-first GA pipeline, gene space, scoring, data-quality gate, and strategy generation support
- keeping it separate from upstream baseline fixes makes rollback and review much easier

Validation commands:

```powershell
python -m unittest discover bollinger_evolver.tests
python -m compileall bollinger_evolver
```

Risk:

- medium to high because it is a large new tree
- lower runtime risk because it is isolated from `main.py` and keeps `allow_real_backtest=False`

## Commit 3: Runner CLI / Reports / Runbook

Include:

- `bollinger_evolver/ga/runner.py`
- `bollinger_evolver/ga/runner_cli.py`
- `bollinger_evolver/ga/session_report.py`
- `docs/bollinger_evolver_runner_runbook.md`
- `README.md`
- runner/report-specific tests, for example:
  - `bollinger_evolver/tests/test_ga_runner.py`
  - `bollinger_evolver/tests/test_ga_runner_cli.py`
  - `bollinger_evolver/tests/test_ga_runner_cli_metrics.py`
  - `bollinger_evolver/tests/test_session_report.py`
  - `bollinger_evolver/tests/test_runner_docs_static.py`

Why included:

- these files document and expose the mock-first session entrypoint
- they form a coherent surface around `run_ga_session()`, `runner_cli`, `session_summary.json`, `session_report.json`, and `session_report.md`
- pairing the runbook and static docs tests with the runner/report layer keeps review context tight

Validation commands:

```powershell
python -m unittest bollinger_evolver.tests.test_ga_runner
python -m unittest bollinger_evolver.tests.test_ga_runner_cli
python -m unittest bollinger_evolver.tests.test_ga_runner_cli_metrics
python -m unittest bollinger_evolver.tests.test_session_report
python -m unittest bollinger_evolver.tests.test_runner_docs_static
```

Risk:

- low to medium
- mostly additive, but it defines the review-facing operator flow and artifact contract

## Commit 4: Workflow Audit Artifacts

Include, if you explicitly want them versioned:

- `.workflow/current-project-audit/`
- `docs/architecture_baseline.md`

Alternative recommendation:

- keep `.workflow/current-project-audit/` out of the repo
- archive it externally or in a separate audit branch
- commit `docs/architecture_baseline.md` separately as a docs-only change if you want the architecture baseline tracked

Why this is separated:

- `.workflow/` is not product code
- it is easy to accidentally mix audit trace files into unrelated commits
- keeping audit artifacts separate reduces long-term repo noise

Risk:

- medium repo-hygiene risk
- low product-runtime risk
- main decision is policy, not code correctness

## Do Not Commit Yet

Do not stage these paths unless you intentionally want runtime/test artifacts:

- `.runtime/`
- `.pytest_cache/`
- all `__pycache__/` directories
- generated strategy artifacts under `user_data/strategies/`
- temporary session outputs
- local machine-specific output folders

## Manual Review Items

- `.workflow/` decision:
  - keep in repo, separate branch, or external archive
- `docs/architecture_baseline.md` decision:
  - include now or ship as a docs-only follow-up
- unknown sensitive-scan references:
  - `config/settings.py`
  - `agent_api/`
  - `monitoring/freqtrade_client.py`
  - `openclaw_skill/genetrader`
  - `scripts/restart_freqtrade.py`
- untracked docs decision:
  - `docs/test_baseline.md`
  - `docs/bollinger_evolver_runner_runbook.md`
- ignored generated strategy files decision:
  - verify nothing important is stranded only under ignored `user_data/strategies/`

## Dry-run Staging Commands

Do not run automatically. These are manual examples only.

Commit 1 dry run:

```powershell
git add .gitignore `
  data/downloader.py `
  scripts/workflow.py `
  strategy/backtest.py `
  tests/test_backtest.py `
  tests/test_evaluation.py `
  tests/test_workflow.py `
  tests/test_data_downloader.py `
  user_data/example.json `
  docs/test_baseline.md
```

Commit 2 dry run:

```powershell
git add bollinger_evolver `
  config/ga_bollinger_resonance.json
```

Commit 3 dry run:

```powershell
git add README.md `
  docs/bollinger_evolver_runner_runbook.md `
  bollinger_evolver/ga/runner.py `
  bollinger_evolver/ga/runner_cli.py `
  bollinger_evolver/ga/session_report.py `
  bollinger_evolver/tests/test_ga_runner.py `
  bollinger_evolver/tests/test_ga_runner_cli.py `
  bollinger_evolver/tests/test_ga_runner_cli_metrics.py `
  bollinger_evolver/tests/test_session_report.py `
  bollinger_evolver/tests/test_runner_docs_static.py
```

Commit 4 dry run:

```powershell
git add .workflow/current-project-audit `
  docs/architecture_baseline.md
```

## Verification Before Commit

```powershell
$env:GENETRADER_CONFIG='ga.json.example'
python -m pytest tests -q
python -m unittest discover bollinger_evolver.tests
python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests
```

## Final Note

The workspace is close to commit-ready, but not as one large commit. The safest
path is:

1. baseline/security fixes first
2. Bollinger Evolver core second
3. runner/report/runbook third
4. workflow audit artifacts only after a manual policy decision
