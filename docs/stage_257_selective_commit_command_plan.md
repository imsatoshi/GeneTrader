# STAGE-257 Selective Commit Command Plan

## DO NOT EXECUTE WITHOUT EXPLICIT USER APPROVAL

This document is a command plan only. Do not copy and run these commands unless
the user explicitly approves STAGE-252 selective commits.

## Global Rules

- Do not use `git add -A`.
- Do not use `git add .`.
- Stage files explicitly by path.
- Do not stage `.workflow/`.
- Do not stage `.runtime/`, `user_data/data/`, `node_modules/`,
  `frontend/node_modules/`, `frontend/dist/`, `.env`, logs, bundles, patches,
  or real Freqtrade outputs.
- Do not run real Freqtrade, download-data, hyperopt, exchange API calls,
  deployment, rollback, push, or force push.

## Commit 1: Contract schema registry and golden fixtures

```powershell
git add -- bollinger_evolver/schema_registry.py
git add -- bollinger_evolver/tests/test_schema_registry.py
git add -- bollinger_evolver/tests/test_golden_fixtures.py
git add -- bollinger_evolver/tests/test_frontend_contract_alignment.py
git add -- bollinger_evolver/fixtures/golden/custom_strategy_config_sample.json
git add -- bollinger_evolver/fixtures/golden/experiment_registry_record_sample.json
git add -- bollinger_evolver/fixtures/golden/generation_artifact_sample.json
git add -- bollinger_evolver/fixtures/golden/mock_ga_session_summary_sample.json
git add -- bollinger_evolver/fixtures/golden/normalized_backtest_result_sample.json
git add -- bollinger_evolver/fixtures/golden/offline_preflight_sample.json
git add -- bollinger_evolver/fixtures/golden/owner_review_pack_sample.json
git add -- bollinger_evolver/fixtures/golden/risk_report_sample.json
python -m unittest bollinger_evolver.tests.test_schema_registry
python -m unittest bollinger_evolver.tests.test_golden_fixtures
python -m unittest bollinger_evolver.tests.test_frontend_contract_alignment
git diff --cached --name-only
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
git commit -m "Add contract schema registry and golden fixtures"
```

## Commit 2: Local risk and experiment comparison engines

```powershell
git add -- bollinger_evolver/experiment_compare.py
git add -- bollinger_evolver/tests/test_experiment_compare.py
git add -- bollinger_evolver/pareto.py
git add -- bollinger_evolver/tests/test_pareto.py
git add -- bollinger_evolver/risk_budget.py
git add -- bollinger_evolver/tests/test_risk_budget.py
git add -- bollinger_evolver/drawdown_circuit_breaker.py
git add -- bollinger_evolver/tests/test_drawdown_circuit_breaker.py
git add -- bollinger_evolver/loss_streak_control.py
git add -- bollinger_evolver/tests/test_loss_streak_control.py
python -m unittest bollinger_evolver.tests.test_experiment_compare
python -m unittest bollinger_evolver.tests.test_pareto
python -m unittest bollinger_evolver.tests.test_risk_budget
python -m unittest bollinger_evolver.tests.test_drawdown_circuit_breaker
python -m unittest bollinger_evolver.tests.test_loss_streak_control
git diff --cached --name-only
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
git commit -m "Add local risk and experiment comparison engines"
```

## Commit 3: Position sizing and strategy explainability

```powershell
git add -- bollinger_evolver/position_sizing.py
git add -- bollinger_evolver/strategy_explainer.py
git add -- bollinger_evolver/trading_system_adapter.py
git add -- bollinger_evolver/tests/test_position_sizing.py
git add -- bollinger_evolver/tests/test_strategy_explainer.py
git add -- bollinger_evolver/tests/test_trading_system_adapter.py
python -m unittest bollinger_evolver.tests.test_position_sizing
python -m unittest bollinger_evolver.tests.test_strategy_explainer
python -m unittest bollinger_evolver.tests.test_trading_system_adapter
git diff --cached --name-only
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
git commit -m "Add position sizing and strategy explainability reports"
```

## Commit 4: Frontend risk and run comparison dashboards

```powershell
git add -- frontend/src/App.tsx
git add -- frontend/src/components/FitnessChart.tsx
git add -- frontend/src/components/NavSidebar.tsx
git add -- frontend/src/mocks/riskDashboard.ts
git add -- frontend/src/mocks/runComparison.ts
git add -- frontend/src/mocks/runRegistryCustom.ts
git add -- frontend/src/pages/RiskDashboardPage.test.tsx
git add -- frontend/src/pages/RiskDashboardPage.tsx
git add -- frontend/src/pages/RunComparisonPage.test.tsx
git add -- frontend/src/pages/RunComparisonPage.tsx
git add -- frontend/src/pages/RunExplorerCustomPage.test.tsx
git add -- frontend/src/pages/RunExplorerCustomPage.tsx
git add -- frontend/src/routes.tsx
git add -- frontend/src/styles.css
Push-Location frontend
npm.cmd test -- RunExplorerCustomPage RiskDashboardPage RunComparisonPage
npm.cmd test
npm.cmd run build
Pop-Location
git diff --cached --name-only
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
git commit -m "Add frontend risk and run comparison dashboards"
```

## Commit 5: Safe mock risk CLI and owner review pack

```powershell
git add -- bollinger_evolver/risk_cli.py
git add -- bollinger_evolver/tests/test_risk_cli.py
git add -- bollinger_evolver/owner_review_pack.py
git add -- bollinger_evolver/tests/test_owner_review_pack.py
git add -- bollinger_evolver/local_health_report.py
git add -- bollinger_evolver/tests/test_local_health_report.py
python -m unittest bollinger_evolver.tests.test_risk_cli
python -m unittest bollinger_evolver.tests.test_owner_review_pack
python -m unittest bollinger_evolver.tests.test_local_health_report
git diff --cached --name-only
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
git commit -m "Add safe mock risk CLI and owner review pack"
```

## Commit 6: Owner review docs and safe test matrix

```powershell
git add -- docs/custom_strategy_review_guide.md
git add -- docs/stage_162_custom_strategy_owner_review.md
git add -- docs/stage_196_custom_strategy_pipeline_e2e_audit_report.md
git add -- docs/stage_220_local_mainline_health_report.md
git add -- docs/stage_223_custom_strategy_documentation_consolidation.md
git add -- docs/stage_241_worktree_hygiene_audit.md
git add -- docs/stage_242_selective_staging_plan.md
git add -- docs/stage_243_redacted_secret_runtime_audit.md
git add -- docs/stage_244_owner_review_readiness_gate.md
git add -- docs/stage_245_selective_staging_commit_preparation.md
git add -- docs/stage_246_owner_review_package.md
git add -- docs/stage_247_local_mock_e2e_verification.md
git add -- docs/stage_248_local_mock_pipeline_health_report.md
git add -- docs/stage_249_owner_review_feedback.md
git add -- docs/stage_254_selective_commit_dry_run_review.md
git add -- docs/stage_255_worktree_risk_classifier.md
git add -- docs/stage_256_module_ownership_map.md
git add -- docs/stage_257_selective_commit_command_plan.md
git add -- docs/stage_258_do_not_stage_policy_review.md
git add -- docs/trading_system_abstraction.md
git add -- scripts/run_safe_test_matrix.cmd
git add -- scripts/run_safe_test_matrix.ps1
git add -- tests/test_safe_test_matrix_static.py
python -m pytest tests/test_safe_test_matrix_static.py -q
git diff --cached --name-only
git diff --cached --check
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
git commit -m "Add owner review docs and safe test matrix"
```

## Final Matrix After All Commits

```powershell
scripts\run_safe_test_matrix.cmd
git status --short
```

## Reminder

This is a plan. Do not execute it until the user explicitly approves
STAGE-252 selective commits.
