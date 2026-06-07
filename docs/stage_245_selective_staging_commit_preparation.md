# STAGE-245 Selective Staging Commit Preparation

## Verdict

PASS for preparation. No staging or commit was performed.

This stage converts the STAGE-242 staging plan into a pre-commit checklist that
can be executed only after explicit user approval.

## Current Baseline

- Branch: `main`
- HEAD: `7305824 Add pre-push mainline audit report`
- Cached/staged files: none
- Working tree: dirty
- Real backtest gate: BLOCKED
- Owner review: PENDING

## Commit Preparation Groups

### Group 1: Contract schema registry and golden fixtures

Purpose: lock stable JSON contracts and fixture snapshots.

Candidate files:

- `bollinger_evolver/schema_registry.py`
- `bollinger_evolver/tests/test_schema_registry.py`
- `bollinger_evolver/tests/test_golden_fixtures.py`
- `bollinger_evolver/tests/test_frontend_contract_alignment.py`
- `bollinger_evolver/fixtures/golden/*.json`

Required checks:

```powershell
python -m unittest bollinger_evolver.tests.test_schema_registry
python -m unittest bollinger_evolver.tests.test_golden_fixtures
python -m unittest bollinger_evolver.tests.test_frontend_contract_alignment
git diff --cached --check
```

### Group 2: Local risk and comparison engines

Purpose: add mock-first local analysis engines.

Candidate files:

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

Required checks:

```powershell
python -m unittest bollinger_evolver.tests.test_experiment_compare
python -m unittest bollinger_evolver.tests.test_pareto
python -m unittest bollinger_evolver.tests.test_risk_budget
python -m unittest bollinger_evolver.tests.test_drawdown_circuit_breaker
python -m unittest bollinger_evolver.tests.test_loss_streak_control
git diff --cached --check
```

### Group 3: Position sizing and strategy explainability

Purpose: connect local strategy configuration to explainable risk previews.

Candidate files:

- `bollinger_evolver/position_sizing.py`
- `bollinger_evolver/strategy_explainer.py`
- `bollinger_evolver/trading_system_adapter.py`
- `bollinger_evolver/tests/test_position_sizing.py`
- `bollinger_evolver/tests/test_strategy_explainer.py`
- `bollinger_evolver/tests/test_trading_system_adapter.py`

Required checks:

```powershell
python -m unittest bollinger_evolver.tests.test_position_sizing
python -m unittest bollinger_evolver.tests.test_strategy_explainer
python -m unittest bollinger_evolver.tests.test_trading_system_adapter
git diff --cached --check
```

### Group 4: Frontend risk and run comparison dashboards

Purpose: add read-only mock frontend views.

Candidate files:

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

Required checks:

```powershell
npm.cmd test -- RunExplorerCustomPage RiskDashboardPage RunComparisonPage
npm.cmd test
npm.cmd run build
git diff --cached --check
```

### Group 5: Safe mock risk CLI and owner review pack

Purpose: add local-only review and report generation tools.

Candidate files:

- `bollinger_evolver/risk_cli.py`
- `bollinger_evolver/tests/test_risk_cli.py`
- `bollinger_evolver/owner_review_pack.py`
- `bollinger_evolver/tests/test_owner_review_pack.py`
- `bollinger_evolver/local_health_report.py`
- `bollinger_evolver/tests/test_local_health_report.py`

Required checks:

```powershell
python -m unittest bollinger_evolver.tests.test_risk_cli
python -m unittest bollinger_evolver.tests.test_owner_review_pack
python -m unittest bollinger_evolver.tests.test_local_health_report
git diff --cached --check
```

### Group 6: Owner review docs and safe test matrix

Purpose: document review state and provide a safe validation wrapper.

Candidate files:

- `docs/custom_strategy_review_guide.md`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/stage_220_local_mainline_health_report.md`
- `docs/stage_223_custom_strategy_documentation_consolidation.md`
- `docs/stage_241_worktree_hygiene_audit.md`
- `docs/stage_242_selective_staging_plan.md`
- `docs/stage_243_redacted_secret_runtime_audit.md`
- `docs/stage_244_owner_review_readiness_gate.md`
- `docs/stage_245_selective_staging_commit_preparation.md`
- `docs/trading_system_abstraction.md`
- `scripts/run_safe_test_matrix.cmd`
- `scripts/run_safe_test_matrix.ps1`
- `tests/test_safe_test_matrix_static.py`

Required checks:

```powershell
python -m pytest tests/test_safe_test_matrix_static.py -q
git diff --cached --check
```

## Mandatory Staged Path Audit

Run after staging each group:

```powershell
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
```

Expected result: no output.

## Must Not Stage

- `.workflow/`
- `.runtime/`
- `user_data/data/`
- `node_modules/`
- `frontend/dist/`
- `.env`
- logs
- real exchange data
- backtest outputs
- Freqtrade runtime outputs

## Safety Boundary

- No real Freqtrade execution.
- No download-data or hyperopt.
- No exchange/API access.
- No deployment or rollback.
- No push.
- No staging or commit was performed in this preparation stage.
