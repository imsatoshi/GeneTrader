# STAGE-155 Custom Strategy Parameter Reconciliation

## Source Parameters

The current owner-facing custom strategy abstraction is built around a
Bollinger + RSI entry model, explicit exit thresholds, bounded add/reduce
position controls, and advisory risk governance.

The active source files reviewed in this stage are:

- `docs/trading_system_abstraction.md`
- `bollinger_evolver/custom_strategy_schema.py`
- `bollinger_evolver/tests/test_custom_strategy_schema.py`

## Current Genome Fields

The active `CustomStrategyGenome` contains 14 GA-optimized parameters:

| Field | Role | Owner Review Status |
| --- | --- | --- |
| `entry_bb_window` | Bollinger lookback | keep |
| `entry_bb_stddev` | Bollinger band width | keep |
| `entry_rsi_period` | RSI lookback | keep |
| `entry_rsi_max` | RSI entry ceiling | keep |
| `exit_take_profit_pct` | take-profit threshold | keep |
| `exit_stop_loss_pct` | stop-loss threshold | keep |
| `trailing_stop_pct` | trailing stop threshold | keep |
| `add_position_threshold_pct` | add-position trigger | keep |
| `reduce_position_threshold_pct` | reduce-position trigger | keep |
| `max_additions` | pyramiding cap | keep |
| `leverage` | strategy leverage request | keep, hard bounded |
| `risk_per_trade` | per-trade risk request | keep, hard bounded |
| `max_portfolio_exposure` | portfolio exposure request | keep, hard bounded |
| `cooldown_candles` | cooldown after action | keep |

## Added / Removed / Renamed Parameters

No parameter was added, removed, or renamed in STAGE-155. The existing schema
remains stable so downstream mock GA, artifact, frontend, and adapter work can
continue to consume the same field names.

## Bounds Review

The prior schema used broad exploratory bounds. STAGE-155 records the owner
review decision to calibrate them toward conservative mock-first defaults in
the next code change:

- cap leverage at the RiskGovernor default maximum of `3.0`
- cap per-trade risk at `0.02`
- cap portfolio exposure below `1.0`
- keep stop-loss below take-profit
- keep cooldown non-negative
- keep add-position count small enough for mock portfolio stress tests

## Hard Constraints

The schema must reject:

- missing or unknown genome fields
- non-numeric, boolean, non-finite, or incorrectly typed numeric fields
- leverage above the calibrated maximum
- risk per trade above the calibrated maximum
- stop-loss greater than or equal to take-profit
- negative cooldown values
- non-JSON-safe request or config output

## Open Questions

- Confirm whether pair-specific leverage caps are needed.
- Confirm whether volatility-adjusted risk per trade should be added later.
- Confirm whether position lifecycle controls need separate long/short values.
- Confirm whether cooldown should be converted to wall-clock time in the final
  trading system adapter.

## Verdict

PASS / ready for calibrated bounds and adapter mapping.
