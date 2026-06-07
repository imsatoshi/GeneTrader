# STAGE-242 Selective Staging Plan for STAGE-200 to STAGE-240

## Verdict

PLAN ONLY. No files were staged or committed in this stage.

## Staging Rules

- Do not use `git add -A`.
- Do not use `git add .`.
- Stage files explicitly by path.
- Keep `.workflow/`, `.runtime/`, `user_data/data/`, `node_modules/`,
  `frontend/dist/`, `.env`, logs, and runtime outputs out of every commit.
- Keep real backtest, exchange API, deployment, rollback, and download paths
  blocked.

## Proposed Commit Groups

### Commit 1: Contract schema registry and golden fixtures

Suggested message:

```text
Add contract schema registry and golden fixtures
```

Files:

- `bollinger_evolver/schema_registry.py`
- `bollinger_evolver/tests/test_schema_registry.py`
- `bollinger_evolver/tests/test_golden_fixtures.py`
- `bollinger_evolver/tests/test_frontend_contract_alignment.py`
- `bollinger_evolver/fixtures/golden/custom_strategy_config_sample.json`
- `bollinger_evolver/fixtures/golden/experiment_registry_record_sample.json`
- `bollinger_evolver/fixtures/golden/generation_artifact_sample.json`
- `bollinger_evolver/fixtures/golden/mock_ga_session_summary_sample.json`
- `bollinger_evolver/fixtures/golden/normalized_backtest_result_sample.json`
- `bollinger_evolver/fixtures/golden/offline_preflight_sample.json`
- `bollinger_evolver/fixtures/golden/owner_review_pack_sample.json`
- `bollinger_evolver/fixtures/golden/risk_report_sample.json`

Verification:

```powershell
python -m unittest bollinger_evolver.tests.test_schema_registry
python -m unittest bollinger_evolver.tests.test_golden_fixtures
python -m unittest bollinger_evolver.tests.test_frontend_contract_alignment
```

### Commit 2: Local risk and comparison engines

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

Verification:

```powershell
python -m unittest bollinger_evolver.tests.test_experiment_compare
python -m unittest bollinger_evolver.tests.test_pareto
python -m unittest bollinger_evolver.tests.test_risk_budget
python -m unittest bollinger_evolver.tests.test_drawdown_circuit_breaker
python -m unittest bollinger_evolver.tests.test_loss_streak_control
```

### Commit 3: Position sizing and strategy explainability

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

Verification:

```powershell
python -m unittest bollinger_evolver.tests.test_position_sizing
python -m unittest bollinger_evolver.tests.test_strategy_explainer
python -m unittest bollinger_evolver.tests.test_trading_system_adapter
```

### Commit 4: Frontend risk and run comparison dashboards

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

Verification:

```powershell
cd frontend
npm.cmd test -- RunExplorerCustomPage RiskDashboardPage RunComparisonPage
npm.cmd test
npm.cmd run build
cd ..
```

### Commit 5: Safe mock risk CLI and owner review pack

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

Verification:

```powershell
python -m unittest bollinger_evolver.tests.test_risk_cli
python -m unittest bollinger_evolver.tests.test_owner_review_pack
python -m unittest bollinger_evolver.tests.test_local_health_report
```

### Commit 6: Owner review documentation and safe test matrix

Suggested message:

```text
Add owner review docs and safe test matrix
```

Files:

- `docs/custom_strategy_review_guide.md`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/stage_220_local_mainline_health_report.md`
- `docs/stage_223_custom_strategy_documentation_consolidation.md`
- `docs/trading_system_abstraction.md`
- `scripts/run_safe_test_matrix.cmd`
- `scripts/run_safe_test_matrix.ps1`
- `tests/test_safe_test_matrix_static.py`

Verification:

```powershell
python -m pytest tests/test_safe_test_matrix_static.py -q
scripts\run_safe_test_matrix.cmd
```

## Forbidden Path Scan

Run after staging each group:

```powershell
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
```

Expected result: no output.

## Final Checks For Each Commit

```powershell
git diff --cached --name-only
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
```

## Acceptance

This plan is ready for selective staging, but staging and commits require an
explicit user approval step.
