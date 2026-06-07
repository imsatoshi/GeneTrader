# STAGE-220 Local Mainline Health Report

## Status

PASS / local mock-first mainline remains healthy for owner review.

## Git State

- Branch: `main`
- HEAD: `7305824 Add pre-push mainline audit report`
- Ahead of `origin/main`: 46 commits
- Cached/staged files: none
- Remote delivery / owner review: pending

## Latest Safe Test Matrix

Command:

```powershell
scripts\run_safe_test_matrix.cmd
```

Result:

- `python -m pytest tests -q`: 237 passed, 4 subtests passed
- `python -m unittest discover -s bollinger_evolver/tests`: 885 passed, 6 skipped
- `npm.cmd test -- RunExplorerCustomPage RunComparisonPage RiskDashboardPage MockDashboardPage`: 4 files passed, 25 tests passed
- `npm.cmd test`: 15 files passed, 54 tests passed
- `npm.cmd run build`: passed, no large chunk warning
- `python -m compileall ...`: passed
- `git diff --check`: passed with Windows LF/CRLF warnings only
- `git diff --cached --check`: passed

## Safety Boundary

- Real backtest remains `BLOCKED`.
- Owner review remains pending.
- No real exchange/API access was used.
- No real account information was read.
- No external deployment or rollback action was used.
- New risk CLI and owner review pack generator are fixture-only and require
  explicit output directories.

## New Local Review Utilities

- `python -m bollinger_evolver.risk_cli explain --fixture safe_default --output <tempdir>`
- `python -m bollinger_evolver.owner_review_pack --output <tempdir>`
- `scripts\run_safe_test_matrix.cmd`

## Working Tree Summary

Modified tracked files:

- `bollinger_evolver/tests/test_position_sizing.py`
- `bollinger_evolver/tests/test_trading_system_adapter.py`
- `bollinger_evolver/trading_system_adapter.py`
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

Untracked files/directories:

- `.workflow/`
- `bollinger_evolver/drawdown_circuit_breaker.py`
- `bollinger_evolver/experiment_compare.py`
- `bollinger_evolver/fixtures/golden/`
- `bollinger_evolver/loss_streak_control.py`
- `bollinger_evolver/local_health_report.py`
- `bollinger_evolver/owner_review_pack.py`
- `bollinger_evolver/pareto.py`
- `bollinger_evolver/position_sizing.py`
- `bollinger_evolver/risk_budget.py`
- `bollinger_evolver/risk_cli.py`
- `bollinger_evolver/schema_registry.py`
- `bollinger_evolver/strategy_explainer.py`
- `bollinger_evolver/tests/test_drawdown_circuit_breaker.py`
- `bollinger_evolver/tests/test_experiment_compare.py`
- `bollinger_evolver/tests/test_frontend_contract_alignment.py`
- `bollinger_evolver/tests/test_golden_fixtures.py`
- `bollinger_evolver/tests/test_loss_streak_control.py`
- `bollinger_evolver/tests/test_local_health_report.py`
- `bollinger_evolver/tests/test_owner_review_pack.py`
- `bollinger_evolver/tests/test_pareto.py`
- `bollinger_evolver/tests/test_risk_budget.py`
- `bollinger_evolver/tests/test_risk_cli.py`
- `bollinger_evolver/tests/test_schema_registry.py`
- `bollinger_evolver/tests/test_strategy_explainer.py`
- `docs/custom_strategy_review_guide.md`
- `docs/stage_223_custom_strategy_documentation_consolidation.md`
- `docs/stage_220_local_mainline_health_report.md`
- `frontend/src/mocks/riskDashboard.ts`
- `frontend/src/mocks/runComparison.ts`
- `frontend/src/pages/RiskDashboardPage.test.tsx`
- `frontend/src/pages/RiskDashboardPage.tsx`
- `frontend/src/pages/RunComparisonPage.test.tsx`
- `frontend/src/pages/RunComparisonPage.tsx`
- `scripts/run_safe_test_matrix.cmd`
- `scripts/run_safe_test_matrix.ps1`
- `tests/test_safe_test_matrix_static.py`

## Verdict

PASS / STAGE-216 through STAGE-240 are local-only, review-safe, and ready for
owner review packaging.

BLOCKED / real backtest remains blocked until remote sync and owner `APPROVED`.
