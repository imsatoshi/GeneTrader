# STAGE-260 Strategy Parameter Decision Log

## Verdict

PENDING OWNER DECISIONS.

This log records owner decisions for each custom strategy parameter. All owner
decision fields are pending until the owner explicitly reviews and updates
them.

## Decision Table

| Parameter | Current Default | Current Min | Current Max | GA Optimize | Owner Decision | Reason | Status |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `entry_bb_window` | 20 | 10 | 80 | yes | pending | Bollinger entry lookback window | pending |
| `entry_bb_stddev` | 2.0 | 1.2 | 3.5 | yes | pending | Bollinger band width | pending |
| `entry_rsi_period` | 14 | 5 | 40 | yes | pending | RSI lookback period | pending |
| `entry_rsi_max` | 35.0 | 10.0 | 55.0 | yes | pending | Entry RSI upper bound | pending |
| `exit_take_profit_pct` | 0.08 | 0.01 | 0.25 | yes | pending | Profit-taking threshold | pending |
| `exit_stop_loss_pct` | 0.03 | 0.005 | 0.12 | yes | pending | Stop-loss threshold | pending |
| `trailing_stop_pct` | 0.02 | 0.0 | 0.08 | yes | pending | Trailing-stop distance | pending |
| `add_position_threshold_pct` | 0.025 | 0.0 | 0.08 | yes | pending | Add-position threshold; owner must confirm whether loss-side additions are allowed | pending |
| `reduce_position_threshold_pct` | 0.04 | 0.0 | 0.15 | yes | pending | Reduce-position threshold | pending |
| `max_additions` | 2 | 0 | 3 | yes | pending | Maximum number of additions | pending |
| `leverage` | 1.0 | 1.0 | 3.0 | yes | pending | Strategy leverage | pending |
| `risk_per_trade` | 0.01 | 0.001 | 0.02 | yes | pending | Per-trade risk budget | pending |
| `max_portfolio_exposure` | 0.30 | 0.05 | 0.60 | yes | pending | Portfolio exposure cap | pending |
| `cooldown_candles` | 3 | 0 | 72 | yes | pending | Cooldown after action or risk event | pending |

## Fixed Execution Controls

These are not GA parameters and should remain fixed unless the owner opens a
separate security review:

| Parameter | Current Value | GA Optimize | Owner Decision | Reason | Status |
| --- | --- | --- | --- | --- | --- |
| `real_execution_enabled` | false | no | pending | Keeps custom strategy mock-first | pending |
| `dry_run_only` | true | no | pending | Prevents live execution | pending |
| `no_freqtrade_execution` | true | no | pending | Keeps real Freqtrade blocked | pending |
| `no_exchange_api` | true | no | pending | Prevents exchange access | pending |
| `risk_governor_advisory_only` | true | no | pending | Avoids mutating strategy config or placing orders | pending |

## Owner Update Rules

- Change `Owner Decision` only after explicit owner review.
- Use `approved`, `needs change`, or `pending` in the status column.
- Do not mark real execution controls approved for live execution in this log.
- Real backtest remains BLOCKED until the separate real backtest gate is
  satisfied.
