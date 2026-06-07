# STAGE-265 Backend Contract QA Matrix

## Verdict

PASS / backend JSON output contracts are documented for mock-first review.

The contracts below are local-only and JSON-safe by design. They do not grant
approval for real Freqtrade, download-data, hyperopt, exchange API access,
deployment, rollback, or live trading.

## Contract Matrix

| Contract | Primary Source | Test Coverage | Schema / Version | QA Status | Notes |
| --- | --- | --- | --- | --- | --- |
| `NormalizedBacktestResult` | `bollinger_evolver/backtest_adapter.py` | `bollinger_evolver/tests/test_backtest_adapter.py` | `normalized-backtest-result/v1` | PASS | Synthetic/mock result contract; real runner blocked. |
| GA session summary | `bollinger_evolver/session_summary.py` | `bollinger_evolver/tests/test_session_summary.py` | `ga-session-summary/v1` | PASS | Leaderboard and fitness series are JSON-safe. |
| Generation artifact | `bollinger_evolver/artifact_export.py` | `bollinger_evolver/tests/test_artifact_export.py` | `generation-artifact/v1` | PASS | Per-generation artifact snapshot. |
| `CustomStrategyConfig` | `bollinger_evolver/custom_strategy_schema.py` | `bollinger_evolver/tests/test_custom_strategy_schema.py` | `custom-strategy/v1` | PASS | Includes mock-only execution controls. |
| `TradingSystemConfig` | `bollinger_evolver/trading_system_adapter.py` | `bollinger_evolver/tests/test_trading_system_adapter.py` | local trading system config | PASS | Rejects disallowed output roots and secret-like fields. |
| RiskGovernor result | `bollinger_evolver/risk_governor.py` | `bollinger_evolver/tests/test_risk_governor.py` | `risk-governor/v1` | PASS | Advisory only; does not mutate config. |
| WalkForward result | `bollinger_evolver/walk_forward.py`, `walk_forward_custom.py` | walk-forward tests | walk-forward result object | PASS | Train/validation/test and stability outputs. |
| MonteCarlo result | `bollinger_evolver/monte_carlo.py`, `monte_carlo_custom.py` | Monte Carlo tests | Monte Carlo summary | PASS | Distribution/failure-rate outputs are JSON-safe. |
| Portfolio result | `bollinger_evolver/portfolio_evaluator.py`, `portfolio_custom.py` | portfolio tests | portfolio summary | PASS | Pair results and drawdown aggregation. |
| ExperimentRegistry record | `bollinger_evolver/experiment_registry.py`, `experiment_registry_custom.py` | experiment registry tests | `experiment-registry-record/v1` | PASS | JSONL/local-only record shape. |
| OwnerReviewPack | `bollinger_evolver/owner_review_pack.py` | `bollinger_evolver/tests/test_owner_review_pack.py` | owner review pack JSON | PASS | Explicit output directory required. |

## QA Requirements Before Selective Commit

- Keep schema/golden fixture changes in their own commit group.
- Keep CLI/report helpers separate from pure contracts.
- Keep frontend mock contracts separate from backend JSON producers.
- Rerun contract tests for each staged group.

## Safety Boundary

All reviewed contracts are mock-first. Real backtest remains BLOCKED.
