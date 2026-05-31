# Staging Pre-Add Audit

## Executive Summary

- staging_readiness: `NEEDS_REVIEW`
- total_files_considered: `87`
- uncovered_changes_count: `3`
- force_add_required_count: `2 candidate paths (1 required, 1 optional)`
- manual_decisions:
  - whether `.workflow/current-project-audit/` should enter version control at all
  - whether `docs/architecture_baseline.md` should ride with workflow/audit docs or be split into a separate docs-only commit
  - whether to force-add ignored strategy source placeholders under `user_data/strategies/`

Current audit is still read-only. No `git add`, `git commit`, or `git reset` was executed.

## Commit 1 Pre-Add List: Baseline / Security / Test Fixture

| file | status | exists | tracked | ignored | force_add_required | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `.gitignore` | modified | yes | yes | no | no | runtime/cache ignore hygiene |
| `data/downloader.py` | modified | yes | yes | no | no | data coverage QA |
| `scripts/workflow.py` | modified | yes | yes | no | no | config redaction + credential key fix |
| `strategy/backtest.py` | modified | yes | yes | no | no | temp config cleanup |
| `tests/test_backtest.py` | modified | yes | yes | no | no | baseline regression coverage |
| `tests/test_evaluation.py` | modified | yes | yes | no | no | fixture compatibility fix |
| `tests/test_workflow.py` | modified | yes | yes | no | no | workflow redaction/placeholder tests |
| `tests/test_data_downloader.py` | untracked | yes | no | no | no | new QA regression tests |
| `user_data/example.json` | modified | yes | yes | no | no | placeholder-only sample config |
| `docs/test_baseline.md` | untracked | yes | no | no | no | baseline test instructions |

## Commit 2 Pre-Add List: Bollinger Evolver Core

| file | status | exists | tracked | ignored | force_add_required | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `config/ga_bollinger_resonance.json` | untracked | yes | no | no | no | Bollinger Evolver config example |
| `bollinger_evolver/__init__.py` | untracked | yes | no | no | no | package root |
| `bollinger_evolver/config_loader.py` | untracked | yes | no | no | no | config isolation |
| `bollinger_evolver/data_quality.py` | untracked | yes | no | no | no | data gate logic |
| `bollinger_evolver/evaluators/` | untracked tree | yes | no | no | no | evaluation helpers |
| `bollinger_evolver/gene_space/` | untracked tree | yes | no | no | no | gene schema + sampler + validator |
| `bollinger_evolver/scoring/` | untracked tree | yes | no | no | no | resonance + fitness scoring |
| `bollinger_evolver/strategies/` | untracked tree | yes | no | no | no | helper logic and position sizing |
| `bollinger_evolver/runners/` | untracked tree | yes | no | no | no | adapter layer |
| `bollinger_evolver/reports/` | untracked tree | yes | no | no | no | report support |
| `bollinger_evolver/utils/` | untracked tree | yes | no | no | no | utility support |
| `bollinger_evolver/ga/backtest_evaluation_adapter.py` | untracked | yes | no | no | no | gated adapter |
| `bollinger_evolver/ga/evaluation_pipeline.py` | untracked | yes | no | no | no | evaluation flow |
| `bollinger_evolver/ga/generation_runner.py` | untracked | yes | no | no | no | generation evaluation |
| `bollinger_evolver/ga/orchestrator.py` | untracked | yes | no | no | no | GA coordination |
| `bollinger_evolver/ga/population_ops.py` | untracked | yes | no | no | no | initialize/mutate/crossover |
| `bollinger_evolver/ga/smoke_run_pipeline.py` | untracked | yes | no | no | no | smoke pipeline |
| `bollinger_evolver/strategy_factory.py` | untracked | yes | no | no | no | strategy generation |
| `bollinger_evolver/tests/` except runner/report docs tests | untracked tree | yes | no | no | no | core regression suite |
| `user_data/strategies/BollingerResonanceStrategy.py` | ignored, untracked | yes | no | yes | yes | hand-written strategy source; broad ignore currently hides it |
| `user_data/strategies/generated/.gitkeep` | ignored, untracked | yes | no | yes | optional | only needed if you want an empty generated-dir anchor tracked |

## Commit 3 Pre-Add List: Runner / CLI / Reports / Runbook

| file | status | exists | tracked | ignored | force_add_required | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `README.md` | modified | yes | yes | no | no | runbook link |
| `docs/bollinger_evolver_runner_runbook.md` | untracked | yes | no | no | no | safe-run operator doc |
| `bollinger_evolver/ga/runner.py` | untracked | yes | no | no | no | session runner |
| `bollinger_evolver/ga/runner_cli.py` | untracked | yes | no | no | no | CLI entrypoint |
| `bollinger_evolver/ga/session_report.py` | untracked | yes | no | no | no | report renderer |
| `bollinger_evolver/tests/test_ga_runner.py` | untracked | yes | no | no | no | runner regression |
| `bollinger_evolver/tests/test_ga_runner_cli.py` | untracked | yes | no | no | no | CLI regression |
| `bollinger_evolver/tests/test_ga_runner_cli_metrics.py` | untracked | yes | no | no | no | metrics/report contract |
| `bollinger_evolver/tests/test_session_report.py` | untracked | yes | no | no | no | report renderer contract |
| `bollinger_evolver/tests/test_runner_docs_static.py` | untracked | yes | no | no | no | doc/static boundary lock |

## Commit 4 Pre-Add List: Workflow Audit Artifacts

| file | status | exists | tracked | ignored | force_add_required | reason |
| --- | --- | --- | --- | --- | --- | --- |
| `.workflow/current-project-audit/` | untracked tree | yes | no | no | no | audit packet set |
| `docs/architecture_baseline.md` | untracked | yes | no | no | no | source-based architecture baseline |

## Architecture Baseline Decision

- recommended commit ownership: `Commit 4`
- reason:
  - `docs/architecture_baseline.md` is an audit/documentation artifact, not part of the runnable Bollinger Evolver core
  - it aligns better with `.workflow/current-project-audit/` than with baseline/security or runner implementation commits
  - if you do not want workflow artifacts versioned, then split `docs/architecture_baseline.md` into a separate docs-only follow-up instead of mixing it into code commits

## Workflow Artifact Decision

- recommendation: `archive externally` or `commit separately`
- do not mix `.workflow/current-project-audit/` into product-code commits
- reason:
  - the directory is useful for traceability
  - it is not product logic
  - it can create long-term repo noise and review distraction
- current recommendation for STAGE-003:
  - do not stage `.workflow/current-project-audit/` until you explicitly decide to keep audit packets in the repo

## Do Not Add List

- `.runtime/`
- `.pytest_cache/`
- all `__pycache__/` directories
- generated runtime outputs
- temporary session output directories
- generated strategy artifacts beyond an intentional `.gitkeep`
- local machine-specific temp files

## Force Add Required

| file | ignored | exists | recommended_action | reason | risk |
| --- | --- | --- | --- | --- | --- |
| `user_data/strategies/BollingerResonanceStrategy.py` | yes | yes | `git add -f` if Commit 2 proceeds | this is source code, not runtime output, but it is hidden by `user_data/strategies/*` ignore rule | medium; force-adding ignored paths should be deliberate |
| `user_data/strategies/generated/.gitkeep` | yes | yes | optional `git add -f` | only needed if you want an empty generated directory anchor tracked | low |

## Uncovered Changes

These current changes are not covered by Commit 1-4 in the original split and need an explicit choice:

- `docs/commit_split_plan.md`
- `docs/workspace_hygiene_report.md`
- `docs/staging_preadd_audit.md`

Recommendation:

- keep them out of STAGE-003 product staging
- or stage them later as a docs/process-only commit after code commits are settled

## Sensitive Scan Summary

- total matches: `293`
- placeholder/test/example: `147`
- structural references: `146`
- real risk: `0`
- unknown / needs review: `0` beyond the structural-reference bucket in this pass
- recommended action:
  - treat current hits as schema/test/doc references unless a future diff introduces an actual secret-looking value
  - keep manual review on credential-bearing code paths such as `config/settings.py`, `monitoring/freqtrade_client.py`, `scripts/restart_freqtrade.py`, `agent_api/`, and `openclaw_skill/genetrader`

This report does not reproduce any live secret value.

## Dry-Run Commands

Text only. Do not run automatically.

Commit 1:

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

Commit 2:

```powershell
git add config/ga_bollinger_resonance.json `
  bollinger_evolver
git add -f user_data/strategies/BollingerResonanceStrategy.py
```

Optional addition for Commit 2 or 3:

```powershell
git add -f user_data/strategies/generated/.gitkeep
```

Commit 3:

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

Commit 4, only after manual policy confirmation:

```powershell
git add .workflow/current-project-audit `
  docs/architecture_baseline.md
```

## Final Recommendation

- enter STAGE-003 real staging now? `not yet`
- required manual confirmation first:
  - confirm whether `.workflow/current-project-audit/` belongs in repo history
  - confirm whether `docs/architecture_baseline.md` follows workflow artifacts or becomes a separate docs-only commit
  - confirm force-add of `user_data/strategies/BollingerResonanceStrategy.py`
  - decide whether the process docs (`docs/commit_split_plan.md`, `docs/workspace_hygiene_report.md`, `docs/staging_preadd_audit.md`) should become a separate fifth docs/process commit

Once those four decisions are made, the workspace is sufficiently verified to move into STAGE-003 controlled staging.
