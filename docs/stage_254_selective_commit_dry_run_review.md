# STAGE-254 Selective Commit Dry-run Review

## Verdict

PASS / selective commit dry-run reviewed.

No staging or commit was performed. This review covers the current unstaged and
untracked STAGE-200 through STAGE-249 work plus the STAGE-253 audit report.

## Baseline

- Branch: `main`
- HEAD: `7305824 Add pre-push mainline audit report`
- Cached/staged files: none
- Working tree: dirty by design
- Real backtest gate: BLOCKED
- Owner review: PENDING

## Git Status Summary

Modified tracked files:

- `bollinger_evolver/trading_system_adapter.py`
- `bollinger_evolver/tests/test_position_sizing.py`
- `bollinger_evolver/tests/test_trading_system_adapter.py`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/trading_system_abstraction.md`
- `frontend/src/App.tsx`
- `frontend/src/components/FitnessChart.tsx`
- `frontend/src/components/NavSidebar.tsx`
- `frontend/src/mocks/runRegistryCustom.ts`
- `frontend/src/pages/RunExplorerCustomPage.test.tsx`
- `frontend/src/pages/RunExplorerCustomPage.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/styles.css`

Untracked groups:

- `.workflow/`
- STAGE-200 through STAGE-240 Python modules and tests
- STAGE-241 through STAGE-249 docs
- STAGE-253 audit report
- frontend mock risk and comparison pages
- safe test matrix scripts

Cached files:

- none

## Suggested Commit Groups

### Group 1: Contract schema registry and golden fixtures

Suggested message:

```text
Add contract schema registry and golden fixtures
```

Files:

- `bollinger_evolver/schema_registry.py`
- `bollinger_evolver/tests/test_schema_registry.py`
- `bollinger_evolver/tests/test_golden_fixtures.py`
- `bollinger_evolver/tests/test_frontend_contract_alignment.py`
- `bollinger_evolver/fixtures/golden/*.json`

### Group 2: Local risk and experiment comparison engines

Suggested message:

```text
Add local risk and experiment comparison engines
```

Files:

- `bollinger_evolver/experiment_compare.py`
- `bollinger_evolver/tests/test_experiment_compare.py`
- `bollinger_evolver/pareto.py`
- `bollinger_evolver/tests/test_pareto.py`
- `bollinger_evolver/risk_budget.py`
- `bollinger_evolver/tests/test_risk_budget.py`
- `bollinger_evolver/drawdown_circuit_breaker.py`
- `bollinger_evolver/tests/test_drawdown_circuit_breaker.py`
- `bollinger_evolver/loss_streak_control.py`
- `bollinger_evolver/tests/test_loss_streak_control.py`

### Group 3: Position sizing and strategy explainability

Suggested message:

```text
Add position sizing and strategy explainability reports
```

Files:

- `bollinger_evolver/position_sizing.py`
- `bollinger_evolver/strategy_explainer.py`
- `bollinger_evolver/trading_system_adapter.py`
- `bollinger_evolver/tests/test_position_sizing.py`
- `bollinger_evolver/tests/test_strategy_explainer.py`
- `bollinger_evolver/tests/test_trading_system_adapter.py`

### Group 4: Frontend risk and run comparison dashboards

Suggested message:

```text
Add frontend risk and run comparison dashboards
```

Files:

- `frontend/src/App.tsx`
- `frontend/src/components/FitnessChart.tsx`
- `frontend/src/components/NavSidebar.tsx`
- `frontend/src/mocks/riskDashboard.ts`
- `frontend/src/mocks/runComparison.ts`
- `frontend/src/mocks/runRegistryCustom.ts`
- `frontend/src/pages/RiskDashboardPage.test.tsx`
- `frontend/src/pages/RiskDashboardPage.tsx`
- `frontend/src/pages/RunComparisonPage.test.tsx`
- `frontend/src/pages/RunComparisonPage.tsx`
- `frontend/src/pages/RunExplorerCustomPage.test.tsx`
- `frontend/src/pages/RunExplorerCustomPage.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/styles.css`

### Group 5: Safe mock risk CLI and owner review pack

Suggested message:

```text
Add safe mock risk CLI and owner review pack
```

Files:

- `bollinger_evolver/risk_cli.py`
- `bollinger_evolver/tests/test_risk_cli.py`
- `bollinger_evolver/owner_review_pack.py`
- `bollinger_evolver/tests/test_owner_review_pack.py`
- `bollinger_evolver/local_health_report.py`
- `bollinger_evolver/tests/test_local_health_report.py`

### Group 6: Owner review docs, audits, and safe test matrix

Suggested message:

```text
Add owner review docs and safe test matrix
```

Files:

- `docs/custom_strategy_review_guide.md`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/stage_196_custom_strategy_pipeline_e2e_audit_report.md`
- `docs/stage_220_local_mainline_health_report.md`
- `docs/stage_223_custom_strategy_documentation_consolidation.md`
- `docs/stage_241_worktree_hygiene_audit.md`
- `docs/stage_242_selective_staging_plan.md`
- `docs/stage_243_redacted_secret_runtime_audit.md`
- `docs/stage_244_owner_review_readiness_gate.md`
- `docs/stage_245_selective_staging_commit_preparation.md`
- `docs/stage_246_owner_review_package.md`
- `docs/stage_247_local_mock_e2e_verification.md`
- `docs/stage_248_local_mock_pipeline_health_report.md`
- `docs/stage_249_owner_review_feedback.md`
- `docs/stage_254_selective_commit_dry_run_review.md`
- `docs/trading_system_abstraction.md`
- `scripts/run_safe_test_matrix.cmd`
- `scripts/run_safe_test_matrix.ps1`
- `tests/test_safe_test_matrix_static.py`

## Patch-level Staging Candidates

Whole-file staging appears acceptable if the commit groups above are preserved.
Patch-level review is still recommended for these tracked files because they
cross routing, styling, or owner-review concerns:

- `bollinger_evolver/trading_system_adapter.py`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/trading_system_abstraction.md`
- `frontend/src/App.tsx`
- `frontend/src/components/NavSidebar.tsx`
- `frontend/src/mocks/runRegistryCustom.ts`
- `frontend/src/pages/RunExplorerCustomPage.tsx`
- `frontend/src/pages/RunExplorerCustomPage.test.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/styles.css`

## Must-not-stage

- `.workflow/`
- `.runtime/`
- `user_data/data/` except tracked `.gitkeep`
- `node_modules/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.env`
- logs
- patch or bundle artifacts
- real exchange data
- real Freqtrade runtime outputs

## Risk Review

- `.workflow/` is present and untracked. It must not be staged.
- No cached files are present.
- No `.env*`, `*.pem`, `*.key`, `*.log`, `*.bundle`, `*.patch`, or `*.diff`
  files were found by the dry-run scans.
- `.runtime/`, `frontend/node_modules/`, and `frontend/dist/` are ignored.
- `user_data/data/` contains only `.gitkeep` in this review.

## Validation Commands

Executed:

```powershell
git status --short
git diff --name-only
git diff --cached --name-only
git diff --check
git diff --cached --check
```

Observed:

- cached output: empty
- `git diff --cached --check`: passed
- `git diff --check`: passed with LF to CRLF warnings only

## Safety Boundary

No staging, commit, real backtest, Freqtrade execution, download-data, hyperopt,
exchange API access, deployment, rollback, or push was performed.
