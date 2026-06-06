# STAGE-131 Trading System Abstraction Intake

## Goal

Capture a safe, GA-ready abstraction for the custom trading system before any
real execution integration.

## Outputs

- `docs/trading_system_abstraction.md`
- `docs/stage_131_trading_system_abstraction_intake.md`

## Intake Summary

The initial strategy-system schema is parameter-first and mock-first. It covers:

- entry filters
- exit thresholds
- add/reduce position thresholds
- leverage
- per-trade risk
- portfolio exposure
- cooldown behavior
- RiskGovernor compatibility fields

## GA Optimized Parameters

- `entry_bb_window`
- `entry_bb_stddev`
- `entry_rsi_period`
- `entry_rsi_max`
- `exit_take_profit_pct`
- `exit_stop_loss_pct`
- `trailing_stop_pct`
- `add_position_threshold_pct`
- `reduce_position_threshold_pct`
- `max_additions`
- `leverage`
- `risk_per_trade`
- `max_portfolio_exposure`
- `cooldown_candles`

## Hard Constraints

- Parameters must be JSON-safe.
- Bounds are explicit and finite.
- Int fields must be integer values.
- Unknown fields are rejected.
- Missing fields are rejected.
- Risk output is advisory and does not mutate the source genome/config.

## Safety Boundary

- No real backtest.
- No real trading.
- No Freqtrade import or subprocess.
- No download-data.
- No exchange/API access.
- No deployment or rollback.
- No secret-bearing examples.

## Verification

This intake is designed to be verified by STAGE-132 tests:

- all schema parameters covered
- valid genome maps to JSON-safe config
- invalid bounds fail clearly
- unknown and missing parameters fail clearly
- RiskGovernor can consume the mapped config without mutation

## Verdict

PASS / trading system abstraction ready for schema skeleton.
