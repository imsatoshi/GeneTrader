# STAGE-255 Working Tree Risk Classifier

## Verdict

PASS / working tree risk classified.

This classifier is for planning only. No files were staged or committed.

## LOW_RISK

These files are docs, mock fixtures, schema definitions, or read-only frontend
mock views. They are suitable for selective staging after normal validation.

### Docs and audit reports

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

### Mock fixtures and schema contracts

- `bollinger_evolver/schema_registry.py`
- `bollinger_evolver/tests/test_schema_registry.py`
- `bollinger_evolver/tests/test_golden_fixtures.py`
- `bollinger_evolver/tests/test_frontend_contract_alignment.py`
- `bollinger_evolver/fixtures/golden/*.json`

### Frontend mock-only views

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

## MEDIUM_RISK

These files are local-only, but they include CLI helpers, report generators, or
risk calculations. They require targeted tests and output-directory checks
before staging.

### CLI and report helpers

- `bollinger_evolver/risk_cli.py`
- `bollinger_evolver/tests/test_risk_cli.py`
- `bollinger_evolver/owner_review_pack.py`
- `bollinger_evolver/tests/test_owner_review_pack.py`
- `bollinger_evolver/local_health_report.py`
- `bollinger_evolver/tests/test_local_health_report.py`
- `scripts/run_safe_test_matrix.cmd`
- `scripts/run_safe_test_matrix.ps1`
- `tests/test_safe_test_matrix_static.py`

### Risk engines and adapter math

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
- `bollinger_evolver/position_sizing.py`
- `bollinger_evolver/tests/test_position_sizing.py`
- `bollinger_evolver/strategy_explainer.py`
- `bollinger_evolver/tests/test_strategy_explainer.py`
- `bollinger_evolver/trading_system_adapter.py`
- `bollinger_evolver/tests/test_trading_system_adapter.py`

## HIGH_RISK / DO NOT STAGE

These paths must not be staged in the current batch:

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
- any real execution draft not covered by the mock-first staging plan

## Runtime And Secret Review

Observed:

- `.workflow/` exists and is not ignored.
- `.runtime/` exists and is ignored.
- `frontend/node_modules/` exists and is ignored.
- `frontend/dist/` exists and is ignored.
- `user_data/data/` exists with `.gitkeep` only in this review.
- `.env` does not exist.
- No `*.log`, `*.bundle`, `*.patch`, or `*.diff` files were found.
- No `.env*`, `*.pem`, or `*.key` files were found.

## Validation Commands

Executed:

```powershell
git status --short
git ls-files --others --exclude-standard
git diff --name-only
```

## Final Classification

MEDIUM_RISK due to dirty working tree and CLI/report helper additions, but no
confirmed secret leak, staged forbidden path, or live execution path was found.
