# STAGE-263 Test Matrix Coverage Map

## Verdict

PASS / test matrix coverage mapped.

This map links major modules to known tests and current safety boundaries.

## Coverage Table

| Module | Test file | Test count | Mock-only | Real execution blocked | Notes |
| --- | --- | ---: | --- | --- | --- |
| Offline Data | `bollinger_evolver/tests/test_data_gate.py` | 39 | yes | yes | Data gate and coverage checks |
| Offline Data | `bollinger_evolver/tests/test_data_manifest.py` | 15 | yes | yes | Manifest contract coverage |
| Offline Data | `bollinger_evolver/tests/test_backtest_preflight.py` | 15 | yes | yes | Preflight readiness coverage |
| GA Execution | `bollinger_evolver/tests/test_ga_execution_framework.py` | 10 | yes | yes | Core GA execution framework |
| GA Execution | `bollinger_evolver/tests/test_ga_execution_custom.py` | 4 | yes | yes | Custom strategy GA integration |
| GA Execution | `bollinger_evolver/tests/test_ga_optimization_custom.py` | 7 | yes | yes | Custom GA optimization loop |
| Risk Fitness | `bollinger_evolver/tests/test_risk_aware_fitness.py` | 13 | yes | yes | Drawdown, leverage, loss streak, overfit penalty |
| Mock Backtest | `bollinger_evolver/tests/test_backtest_adapter.py` | 19 | yes | yes | Synthetic trades and normalized result |
| Custom Strategy Schema | `bollinger_evolver/tests/test_custom_strategy_schema.py` | 14 | yes | yes | Genome bounds and JSON-safe config |
| Risk Governor | `bollinger_evolver/tests/test_risk_governor.py` | 6 | yes | yes | Advisory risk adjustments |
| Walk-forward | `bollinger_evolver/tests/test_walk_forward.py` | 5 | yes | yes | Train/validation/test segmentation |
| Walk-forward | `bollinger_evolver/tests/test_walk_forward_custom.py` | 2 | yes | yes | Custom strategy walk-forward output |
| Monte Carlo | `bollinger_evolver/tests/test_monte_carlo.py` | 4 | yes | yes | Synthetic trade perturbation |
| Monte Carlo | `bollinger_evolver/tests/test_monte_carlo_custom.py` | 2 | yes | yes | Custom robustness summary |
| Portfolio | `bollinger_evolver/tests/test_portfolio_evaluator.py` | 4 | yes | yes | Multi-pair portfolio mock evaluator |
| Portfolio | `bollinger_evolver/tests/test_portfolio_custom.py` | 2 | yes | yes | Custom portfolio summary |
| Experiment Registry | `bollinger_evolver/tests/test_experiment_registry.py` | 4 | yes | yes | JSONL local registry |
| Experiment Registry | `bollinger_evolver/tests/test_experiment_registry_custom.py` | 3 | yes | yes | Custom run metadata |
| Frontend Dashboard | `frontend/src/pages/MockDashboardPage.test.tsx` | 1 | yes | yes | Mock session dashboard |
| Frontend Dashboard | `frontend/src/pages/RunExplorerCustomPage.test.tsx` | 16 | yes | yes | Custom run explorer and detail view |
| Frontend Dashboard | `frontend/src/pages/RunComparisonPage.test.tsx` | 4 | yes | yes | Mock run comparison |
| Frontend Dashboard | `frontend/src/pages/RiskDashboardPage.test.tsx` | 4 | yes | yes | Mock risk dashboard |
| Security Hardening | `tests/test_agent_api.py` | 33 | local | yes | API key, CORS, auth, error handling |
| Security Hardening | `tests/test_deployment.py` | 30 | local | yes | Deployment fail-closed behavior |
| Legacy Guard | `tests/test_backtest.py` | 4 | local | yes | Legacy backtest opt-in guard |
| Legacy Guard | `tests/test_data_downloader.py` | 4 | local | yes | Legacy downloader opt-in guard |
| Real Adapter Gate | `bollinger_evolver/tests/test_execution_gate.py` | 7 | yes | yes | Real backtest gate fail-closed checks |
| Real Adapter Gate | `bollinger_evolver/tests/test_real_backtest_adapter_skeleton.py` | 6 | yes | yes | Real adapter disabled skeleton |
| Real Adapter Gate | `bollinger_evolver/tests/test_freqtrade_adapter.py` | 7 | yes | yes | Request/result and adapter boundaries |
| Real Adapter Gate | `bollinger_evolver/tests/test_freqtrade_adapter_e2e.py` | 7 | yes | yes | Fake-runner E2E boundary |

## Aggregate Notes

- Last safe matrix run passed:
  - `pytest tests -q`: 237 passed, 4 subtests passed
  - frontend targeted tests: 4 files, 25 tests passed
  - frontend full tests: 15 files, 54 tests passed
  - frontend build: passed
  - `unittest discover`: 885 tests OK, 6 skipped
- All listed real execution pathways remain blocked in current workflow.
- Frontend views remain fixture-driven and mock-only.

## Gaps To Watch

- Owner review is still required for custom strategy parameter approval.
- Real backtest gate needs a separate pre-run test matrix if it is ever
  unlocked.
- `.workflow/` remains untracked and should not be staged.
