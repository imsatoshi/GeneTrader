# STAGE-088 Selective Staging Plan

## Repository Boundary

- repo root: `D:/ReceiveBackup/byhdo-workstation-Core-20260605-155346/staging/User/Documents-C/遗传算法布林交易策略`
- current shell path: `D:\ReceiveBackup\byhdo-workstation-Core-20260605-155346\staging\User\Documents-C\遗传算法布林交易策略`
- branch: `main`
- remote: `origin https://github.com/imsatoshi/GeneTrader.git`
- final repo confirmed: yes for the current Codex workspace. The previously
  referenced C-drive path was not present in this environment, so no C-drive
  staging or commit action was attempted.

## Current Staged Bundle

- file count: 13
- verdict: unchanged; no safety, frontend, runtime, or audit-report files are
  staged.

Files:

- `bollinger_evolver/__init__.py`
- `bollinger_evolver/data_gate.py`
- `bollinger_evolver/data_manifest.py`
- `bollinger_evolver/preflight.py`
- `bollinger_evolver/tests/test_backtest_preflight.py`
- `bollinger_evolver/tests/test_data_gate.py`
- `bollinger_evolver/tests/test_data_manifest.py`
- `bollinger_evolver/tests/test_freqtrade_readiness_docs_static.py`
- `bollinger_evolver/tests/test_offline_data_plan_docs_static.py`
- `bollinger_evolver/tests/test_package_exports.py`
- `docs/freqtrade_environment_readiness_plan.md`
- `docs/offline_data_acquisition_plan.md`
- `docs/offline_data_manifest_gate.md`

Cached stat:

- 13 files changed
- 3,083 insertions
- `git diff --cached --check`: passed

## Working Tree Groups

### Group A: Existing Staged Readiness/Data-prep Bundle

Keep as-is until Commit 1. This group is already staged and should not be
mixed with later security, frontend, or audit report files.

### Group B: Offline Data Pipeline

Candidate files for a later offline-data commit:

- `bollinger_evolver/offline_backtest_gate.py`
- `bollinger_evolver/offline_data.py`
- `bollinger_evolver/offline_data_boundary.py`
- `bollinger_evolver/offline_data_diff.py`
- `bollinger_evolver/offline_data_summary.py`
- `bollinger_evolver/offline_paths.py`
- `bollinger_evolver/offline_preflight_cli.py`
- `bollinger_evolver/offline_release.py`
- `bollinger_evolver/offline_workflow.py`
- `bollinger_evolver/config_requirements.py`
- `bollinger_evolver/tests/test_backtest_offline_data_gate.py`
- `bollinger_evolver/tests/test_config_requirements.py`
- `bollinger_evolver/tests/test_data_manifest_inventory_integration.py`
- `bollinger_evolver/tests/test_offline_data_boundary.py`
- `bollinger_evolver/tests/test_offline_data_cli_subprocess.py`
- `bollinger_evolver/tests/test_offline_data_forbidden_api_static_guard.py`
- `bollinger_evolver/tests/test_offline_data_golden_snapshots.py`
- `bollinger_evolver/tests/test_offline_data_inventory.py`
- `bollinger_evolver/tests/test_offline_data_manifest_persistence.py`
- `bollinger_evolver/tests/test_offline_data_metadata_only_regression.py`
- `bollinger_evolver/tests/test_offline_data_no_runtime_writes.py`
- `bollinger_evolver/tests/test_offline_data_preflight_cli.py`
- `bollinger_evolver/tests/test_offline_data_preflight_cli_diff.py`
- `bollinger_evolver/tests/test_offline_data_preflight_diff.py`
- `bollinger_evolver/tests/test_offline_data_preflight_report_contract.py`
- `bollinger_evolver/tests/test_offline_data_preflight_report_renderer.py`
- `bollinger_evolver/tests/test_offline_data_preflight_report_schema.py`
- `bollinger_evolver/tests/test_offline_data_preflight_schema_snapshot.py`
- `bollinger_evolver/tests/test_offline_data_release_readiness.py`
- `bollinger_evolver/tests/test_offline_data_requirements_file.py`
- `bollinger_evolver/tests/test_offline_data_requirements_gate.py`
- `bollinger_evolver/tests/test_offline_data_summary.py`
- `bollinger_evolver/tests/test_offline_data_usage_examples.py`
- `bollinger_evolver/tests/test_offline_data_windows_paths.py`
- `bollinger_evolver/tests/test_offline_data_workflow_adapter.py`
- `bollinger_evolver/tests/test_preflight_offline_data_mode.py`

Patch-level staging note: staged files `data_gate.py`, `data_manifest.py`, and
`preflight.py` are already part of Commit 1. Their unstaged hunks must be
reviewed separately before any later offline-data commit.

### Group C: GA Mock-first Execution and Backtest Chain

Candidate files for mock-first GA execution, strategy generation, fitness,
artifact, report, and controlled Freqtrade adapter commits:

- `bollinger_evolver/artifact_export.py`
- `bollinger_evolver/backtest_adapter.py`
- `bollinger_evolver/fitness.py`
- `bollinger_evolver/freqtrade_backtest_normalizer.py`
- `bollinger_evolver/freqtrade_command_manifest.py`
- `bollinger_evolver/freqtrade_controlled_stub.py`
- `bollinger_evolver/freqtrade_dryrun_adapter.py`
- `bollinger_evolver/freqtrade_execution_sandbox.py`
- `bollinger_evolver/freqtrade_real_execution.py`
- `bollinger_evolver/freqtrade_report_import_gate.py`
- `bollinger_evolver/freqtrade_sandbox_executor.py`
- `bollinger_evolver/freqtrade_single_genome_smoke.py`
- `bollinger_evolver/freqtrade_small_batch_queue.py`
- `bollinger_evolver/ga_execution.py`
- `bollinger_evolver/genome.py`
- `bollinger_evolver/session_summary.py`
- `bollinger_evolver/strategy_factory.py`
- `bollinger_evolver/tests/fixtures/freqtrade_backtest_report.sample.json`
- `bollinger_evolver/tests/test_artifact_export.py`
- `bollinger_evolver/tests/test_backtest_adapter.py`
- `bollinger_evolver/tests/test_freqtrade_backtest_normalizer.py`
- `bollinger_evolver/tests/test_freqtrade_command_manifest.py`
- `bollinger_evolver/tests/test_freqtrade_controlled_stub.py`
- `bollinger_evolver/tests/test_freqtrade_dryrun_adapter.py`
- `bollinger_evolver/tests/test_freqtrade_execution_sandbox.py`
- `bollinger_evolver/tests/test_freqtrade_real_execution.py`
- `bollinger_evolver/tests/test_freqtrade_report_import_gate.py`
- `bollinger_evolver/tests/test_freqtrade_sandbox_executor.py`
- `bollinger_evolver/tests/test_freqtrade_single_genome_smoke.py`
- `bollinger_evolver/tests/test_freqtrade_small_batch_queue.py`
- `bollinger_evolver/tests/test_ga_execution_framework.py`
- `bollinger_evolver/tests/test_risk_aware_fitness.py`
- `bollinger_evolver/tests/test_session_summary.py`

Patch-level staging note: `bollinger_evolver/__init__.py`,
`bollinger_evolver/tests/test_fitness.py`,
`bollinger_evolver/tests/test_strategy_factory.py`, and
`bollinger_evolver/tests/test_package_exports.py` have overlapping staged and
unstaged changes. Review hunks before staging any later GA commit.

### Group D: Frontend Dashboard

Candidate files for the read-only frontend dashboard commit:

- `frontend/.gitignore`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tsconfig.json`
- `frontend/vite.config.ts`
- `frontend/src/**`
- `scripts/start_frontend.ps1`
- `start_frontend.bat`

Do not stage generated frontend output:

- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/tsconfig.tsbuildinfo`

### Group E: Security Hardening

Candidate files for the adaptive API and execution safety commit:

- `.gitignore`
- `adaptive/adaptive_optimizer.py`
- `agent_api/api_server.py`
- `config/settings.py`
- `data/downloader.py`
- `deployment/rollback_manager.py`
- `deployment/strategy_deployer.py`
- `docker-compose.adaptive.yml`
- `docs/test_baseline.md`
- `run_adaptive.py`
- `strategy/backtest.py`
- `tests/test_adaptive_compose_static.py`
- `tests/test_agent_api.py`
- `tests/test_backtest.py`
- `tests/test_data_downloader.py`
- `tests/test_deployment.py`
- `tests/test_rollback_manager.py`

### Group F: Audit Reports and Docs

Candidate docs for a separate audit/guardrails commit:

- `AGENTS.md`
- `docs/stage_008_readiness_data_prep_staging_report.md`
- `docs/stage_010_commit_readiness_report.md`
- `docs/stage_012_offline_data_inventory_audit_report.md`
- `docs/stage_014_offline_data_requirements_audit_report.md`
- `docs/stage_050_offline_data_development_audit_report.md`
- `docs/stage_071_frontend_mock_dashboard_audit_report.md`
- `docs/stage_087_security_reaudit_report.md`
- `docs/stage_088_selective_staging_plan.md`

Review before staging because some reports are stage-local process artifacts and
may not belong in feature commits.

### Group G: Environment / Dependency Files

- Python requirements are already tracked in `requirements.txt`; no dependency
  version changes were observed in this stage.
- Frontend dependencies are represented by `frontend/package.json` and
  `frontend/package-lock.json`.
- `node_modules/`, `frontend/node_modules/`, `frontend/dist/`, and
  `frontend/tsconfig.tsbuildinfo` are ignored.

### Group X: Do Not Stage

Keep these unstaged unless a future task explicitly asks for them:

- `.workflow/`
- `node_modules/`
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/tsconfig.tsbuildinfo`
- `.runtime/`
- `.pytest_cache/`
- `__pycache__/`
- `data/__pycache__/WechatIMG319.jpg`
- real market data under `user_data/data/`
- backtest outputs
- temporary artifact outputs
- temporary report outputs
- `.env` and local credential files
- `*.log`
- coverage outputs

`data/__pycache__/WechatIMG319.jpg` appears as a tracked deletion. It should be
handled separately as a repository hygiene cleanup, not mixed into feature or
security commits.

## Recommended Commit Order

### Commit 1: Add offline data readiness and gate checks

Use the current 13-file staged bundle only.

### Commit 2: Add offline data inventory and requirements pipeline

Use Group B files. Review unstaged hunks on files already staged in Commit 1
before patch-level staging.

### Commit 3: Add mock-first GA execution and risk-aware evaluation

Use Group C files. Keep real Freqtrade execution disabled by default and ensure
tests remain mock/plan-first.

### Commit 4: Add read-only frontend dashboard for GA session summaries

Use Group D source, test, package, and startup files. Exclude generated output
and dependencies.

### Commit 5: Harden adaptive API and execution safety boundaries

Use Group E files. This should remain separate from feature work because it
changes auth, deployment, rollback, and legacy execution defaults.

### Commit 6: Add audit reports and development guardrails

Use selected Group F docs only. Do not mix reports into feature commits unless a
specific report is required for that feature's traceability.

## Validation

- `python -m pytest tests -q`: 235 passed, 4 subtests passed.
- `python -m unittest discover -s bollinger_evolver\tests`: 722 passed, 9 skipped.
- `python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests`: passed.
- `npm.cmd test`: 11 test files passed, 28 tests passed.
- `npm.cmd run build`: passed with Vite chunk-size warning only.
- `git diff --cached --name-only`: unchanged 13-file bundle.
- `git diff --check`: passed with Windows line-ending warnings only.
- `git diff --cached --check`: passed.
- `git status --short | Select-String "node_modules|frontend/dist|tsconfig.tsbuildinfo|.pytest_cache|__pycache__"`: only matched the tracked deletion `data/__pycache__/WechatIMG319.jpg`.

## Remaining Risks

- The repository is still very dirty and spans offline data, GA, frontend,
  security, docs, and environment changes.
- Several files have both staged and unstaged changes, so later commits require
  patch-level staging.
- `data/__pycache__/WechatIMG319.jpg` is a tracked deletion and should be
  reviewed as a standalone hygiene decision.
- Windows line-ending warnings are present but no whitespace errors were found.
- Frontend build has a large chunk warning. This is not a staging blocker but
  can be addressed in a later frontend performance pass.

## Verdict

PASS / ready for selective staging.

No `git add`, commit, reset, stash, clean, trading, deployment, rollback,
download-data, real Freqtrade process, or exchange/API action was executed in
this stage.
