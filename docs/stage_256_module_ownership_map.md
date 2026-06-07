# STAGE-256 Module Ownership Map

## Verdict

PASS / module ownership map generated.

This map is for owner review and selective staging. It does not grant approval
for real backtesting or live execution.

## Offline Data

- Main files: `bollinger_evolver/data_gate.py`,
  `bollinger_evolver/data_manifest.py`, `bollinger_evolver/preflight.py`,
  `bollinger_evolver/offline_data_boundary.py`
- Tests: `bollinger_evolver/tests/test_data_gate.py`,
  `bollinger_evolver/tests/test_data_manifest.py`,
  `bollinger_evolver/tests/test_backtest_preflight.py`, offline data tests
- Schema output: offline preflight and manifest outputs
- Mock-only: yes for current pipeline
- Real execution: no
- Owner review needed: no, unless data policy changes

## GA Execution

- Main files: `bollinger_evolver/ga_execution.py`,
  `bollinger_evolver/ga_optimization_custom.py`,
  `bollinger_evolver/ga_execution_custom.py`
- Tests: GA execution and optimization tests
- Schema output: GA session summary, leaderboard, fitness series
- Mock-only: yes
- Real execution: no
- Owner review needed: no, unless optimization objectives change

## Mock Backtest Adapter

- Main files: `bollinger_evolver/backtest_adapter.py`,
  `bollinger_evolver/freqtrade_adapter.py` fake-runner boundary pieces
- Tests: `bollinger_evolver/tests/test_backtest_adapter.py`,
  `bollinger_evolver/tests/test_freqtrade_adapter_e2e.py`
- Schema output: normalized mock backtest result
- Mock-only: yes
- Real execution: no
- Owner review needed: no, but safety gate should remain checked

## Risk-aware Fitness

- Main files: `bollinger_evolver/fitness.py`
- Tests: risk-aware fitness tests
- Schema output: fitness components and penalties
- Mock-only: yes
- Real execution: no
- Owner review needed: yes for weighting assumptions

## Custom Strategy Schema

- Main files: `bollinger_evolver/custom_strategy_schema.py`,
  `bollinger_evolver/trading_system_adapter.py`
- Tests: `bollinger_evolver/tests/test_custom_strategy_schema.py`,
  `bollinger_evolver/tests/test_trading_system_adapter.py`
- Schema output: custom strategy config
- Mock-only: yes
- Real execution: no
- Owner review needed: yes

## Risk Governor

- Main files: `bollinger_evolver/risk_governor.py`
- Tests: `bollinger_evolver/tests/test_risk_governor.py`
- Schema output: risk adjustments and explanations
- Mock-only: yes
- Real execution: no
- Owner review needed: yes

## Walk-forward

- Main files: `bollinger_evolver/walk_forward.py`,
  `bollinger_evolver/walk_forward_custom.py`
- Tests: walk-forward tests
- Schema output: train / validation / test metrics and stability score
- Mock-only: yes
- Real execution: no
- Owner review needed: no, unless split policy changes

## Monte Carlo

- Main files: `bollinger_evolver/monte_carlo.py`,
  `bollinger_evolver/monte_carlo_custom.py`
- Tests: Monte Carlo tests
- Schema output: perturbation distribution and failure rate
- Mock-only: yes
- Real execution: no
- Owner review needed: yes for failure thresholds

## Portfolio Evaluator

- Main files: `bollinger_evolver/portfolio_evaluator.py`,
  `bollinger_evolver/portfolio_custom.py`
- Tests: portfolio evaluator tests
- Schema output: portfolio profit, drawdown, pair results, correlation penalty
- Mock-only: yes
- Real execution: no
- Owner review needed: yes for exposure rules

## Experiment Registry

- Main files: `bollinger_evolver/experiment_registry.py`,
  `bollinger_evolver/experiment_registry_custom.py`
- Tests: experiment registry tests
- Schema output: JSONL experiment records
- Mock-only: yes
- Real execution: no
- Owner review needed: no

## Frontend Dashboard

- Main files: `frontend/src/pages/MockDashboardPage.tsx`,
  `frontend/src/pages/RunExplorerCustomPage.tsx`,
  `frontend/src/pages/RunComparisonPage.tsx`,
  `frontend/src/pages/RiskDashboardPage.tsx`,
  frontend mocks, routes, nav, and styles
- Tests: frontend page and adapter tests
- Schema output: frontend view models derived from mock fixtures
- Mock-only: yes
- Real execution: no
- Owner review needed: visual/UX review optional

## Security Hardening

- Main files: `agent_api/api_server.py`, `run_adaptive.py`,
  `config/settings.py`, `deployment/strategy_deployer.py`,
  `rollback_manager.py`
- Tests: `tests/test_agent_api.py`, `tests/test_deployment.py`,
  `tests/test_rollback_manager.py`, static compose tests
- Schema output: API/deployment results
- Mock-only: local safety and gate tests
- Real execution: deployment and rollback remain blocked without approval
- Owner review needed: yes before any operational use

## Real Adapter Gate

- Main files: `bollinger_evolver/execution_gate.py`,
  `bollinger_evolver/freqtrade_adapter.py`,
  `bollinger_evolver/freqtrade_execution_sandbox.py`,
  `bollinger_evolver/freqtrade_command_manifest.py`
- Tests: execution gate, command builder, sandbox, and fake-runner tests
- Schema output: gate decision, command manifest, normalized parser output
- Mock-only: yes in current workflow
- Real execution: blocked
- Owner review needed: yes plus explicit run approval and remote sync

## Docs / Audit

- Main files: `docs/stage_*.md`, review guides, health reports
- Tests: static docs tests where present
- Schema output: none
- Mock-only: yes
- Real execution: no
- Owner review needed: yes for strategy abstraction and real gate readiness

## Ownership Summary

The owner-sensitive modules are:

- Custom Strategy Schema
- Risk Governor
- Risk-aware Fitness
- Monte Carlo thresholds
- Portfolio exposure rules
- Security Hardening
- Real Adapter Gate

All real execution paths remain blocked.
