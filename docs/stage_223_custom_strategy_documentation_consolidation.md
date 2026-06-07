# STAGE-223 Custom Strategy Documentation Consolidation

## Purpose

Consolidate the custom strategy review materials into one owner-friendly
reference. This stage is documentation-only and does not change execution
behavior.

## Covered Mock Pipeline

- Custom strategy schema and bounds
- Mock GA execution and artifact summaries
- RiskGovernor advisory adjustments
- Walk-forward stability and overfit penalty
- Monte Carlo stress testing
- Portfolio mock aggregation
- Position sizing preview
- Strategy explainability report
- Owner review pack
- Frontend custom run explorer, run comparison, and risk dashboard

## Manual Owner Review Focus

- Confirm which parameters are allowed for GA optimization.
- Confirm leverage and risk-per-trade caps.
- Confirm max portfolio exposure and add-position policy.
- Confirm whether high-risk fixtures should be rejected or adjusted.
- Confirm whether low-drawdown fixtures match the intended conservative profile.
- Return exactly `APPROVED` or `NEEDS CHANGES`.

## GA-optimizable Parameters

The current `CustomStrategyGenome` exposes these parameters for owner review:

| Parameter | Current Default | Bound | Review Note |
| --- | ---: | --- | --- |
| `entry_bb_window` | 20 | 10 to 80 | Bollinger lookback window |
| `entry_bb_stddev` | 2.0 | 1.2 to 3.5 | Bollinger band width |
| `entry_rsi_period` | 14 | 5 to 40 | RSI lookback |
| `entry_rsi_max` | 35.0 | 10.0 to 55.0 | Entry RSI filter |
| `exit_take_profit_pct` | 0.08 | 0.01 to 0.25 | Take-profit threshold |
| `exit_stop_loss_pct` | 0.03 | 0.005 to 0.12 | Stop-loss threshold |
| `trailing_stop_pct` | 0.02 | 0.0 to 0.08 | Trailing stop distance |
| `add_position_threshold_pct` | 0.025 | 0.0 to 0.08 | Owner must confirm add-position policy |
| `reduce_position_threshold_pct` | 0.04 | 0.0 to 0.15 | Position reduction threshold |
| `max_additions` | 2 | 0 to 3 | Owner must confirm if additions are allowed |
| `leverage` | 1.0 | 1.0 to 3.0 | Owner must confirm leverage cap |
| `risk_per_trade` | 0.01 | 0.001 to 0.02 | Owner must confirm per-trade risk cap |
| `max_portfolio_exposure` | 0.30 | 0.05 to 0.60 | Owner must confirm portfolio exposure cap |
| `cooldown_candles` | 3 | 0 to 72 | Owner must confirm cooldown behavior |

## Fixed Safety Controls

These controls are not GA optimization parameters:

- `real_execution_enabled = false`
- `dry_run_only = true`
- `no_freqtrade_execution = true`
- `no_exchange_api = true`
- `risk_governor_advisory_only = true`

## Safety Boundary

- No real Freqtrade execution.
- No download-data.
- No hyperopt.
- No exchange/API access.
- No deployment or rollback.
- Real backtest remains `BLOCKED` until owner review returns `APPROVED` and
  remote sync is complete.

## Validation References

- `docs/custom_strategy_review_guide.md`
- `docs/trading_system_abstraction.md`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/stage_220_local_mainline_health_report.md`

## Verdict

PASS / documentation consolidated for owner review.
