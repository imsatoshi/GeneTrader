# STAGE-241 Worktree Hygiene Audit

## Verdict

PASS with release hygiene follow-up required.

The current worktree contains the local-only STAGE-200 through STAGE-240 work,
but none of it is staged. This stage did not run real Freqtrade, download-data,
hyperopt, exchange API access, deployment, rollback, or push operations.

## Baseline

- Branch: `main`
- HEAD: `7305824 Add pre-push mainline audit report`
- Cached/staged files: none
- Working tree: dirty
- Real backtest gate: BLOCKED
- Owner review: PENDING

## Modified Tracked Files

### Position sizing and custom strategy integration

- `bollinger_evolver/trading_system_adapter.py`
- `bollinger_evolver/tests/test_position_sizing.py`
- `bollinger_evolver/tests/test_trading_system_adapter.py`

### Owner review documentation

- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/trading_system_abstraction.md`

### Frontend dashboard and route updates

- `frontend/src/App.tsx`
- `frontend/src/components/FitnessChart.tsx`
- `frontend/src/components/NavSidebar.tsx`
- `frontend/src/mocks/runRegistryCustom.ts`
- `frontend/src/pages/RunExplorerCustomPage.test.tsx`
- `frontend/src/pages/RunExplorerCustomPage.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/styles.css`

## Untracked Files By Group

### Must Not Stage

- `.workflow/current-project-audit/final-report.md`
- `.workflow/current-project-audit/orchestration.md`
- `.workflow/current-project-audit/packets/packet-a.md`
- `.workflow/current-project-audit/packets/packet-b.md`
- `.workflow/current-project-audit/packets/packet-c.md`
- `.workflow/current-project-audit/plan.md`
- `.workflow/current-project-audit/results/packet-a.md`
- `.workflow/current-project-audit/results/packet-b.md`
- `.workflow/current-project-audit/results/packet-c.md`
- `.workflow/current-project-audit/state.json`

`.workflow/` is generated audit workflow material. It should remain unstaged.
The preferred follow-up is to add `.workflow/` to `.gitignore` in a dedicated
hygiene change, or keep it explicitly out of every selective staging command.

### STAGE-200 to STAGE-202 Contract Artifacts

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

### STAGE-203 to STAGE-207 Risk and Comparison Engines

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

### STAGE-208 to STAGE-211 Position Sizing and Explainability

- `bollinger_evolver/position_sizing.py`
- `bollinger_evolver/strategy_explainer.py`
- `bollinger_evolver/tests/test_strategy_explainer.py`
- tracked updates listed above in `trading_system_adapter.py`,
  `test_position_sizing.py`, and `test_trading_system_adapter.py`
- tracked frontend updates listed above in `RunExplorerCustomPage.tsx`,
  `RunExplorerCustomPage.test.tsx`, `runRegistryCustom.ts`, and `styles.css`

### STAGE-212 to STAGE-215 Frontend Comparison, Risk Dashboard, Lazy Routes

- `frontend/src/mocks/riskDashboard.ts`
- `frontend/src/mocks/runComparison.ts`
- `frontend/src/pages/RiskDashboardPage.test.tsx`
- `frontend/src/pages/RiskDashboardPage.tsx`
- `frontend/src/pages/RunComparisonPage.test.tsx`
- `frontend/src/pages/RunComparisonPage.tsx`
- tracked route/navigation/build updates listed above

### STAGE-216 to STAGE-220 CLI, Review Pack, Docs, Test Matrix, Health

- `bollinger_evolver/risk_cli.py`
- `bollinger_evolver/tests/test_risk_cli.py`
- `bollinger_evolver/owner_review_pack.py`
- `bollinger_evolver/tests/test_owner_review_pack.py`
- `bollinger_evolver/local_health_report.py`
- `bollinger_evolver/tests/test_local_health_report.py`
- `docs/custom_strategy_review_guide.md`
- `docs/stage_220_local_mainline_health_report.md`
- `docs/stage_223_custom_strategy_documentation_consolidation.md`
- `scripts/run_safe_test_matrix.cmd`
- `scripts/run_safe_test_matrix.ps1`
- `tests/test_safe_test_matrix_static.py`

## Validation Commands

Executed:

```powershell
git status --short
git diff --check
git diff --cached --check
git diff --cached --name-only
```

Observed:

- `git diff --check` reported Windows LF to CRLF warnings only.
- `git diff --cached --check` passed.
- `git diff --cached --name-only` returned no files.

## Safety Boundary

- No real Freqtrade execution.
- No download-data or hyperopt.
- No exchange/API access.
- No deployment or rollback.
- No push.
- No staging or commit was performed.

## Follow-up

Proceed to STAGE-242 before any staging. The worktree is suitable for selective
staging only after `.workflow/` is explicitly excluded from the staged set.
