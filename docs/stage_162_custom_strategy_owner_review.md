# STAGE-162 Custom Strategy Owner Review

## Status

PENDING OWNER REVIEW

This report summarizes the current mock-first custom strategy abstraction for
manual owner confirmation. It does not approve real backtesting, exchange/API
access, download-data, live trading, deployment, or rollback.

## Parameter Table

| Parameter | Current Default | Current Bounds | Review Needed |
| --- | ---: | --- | --- |
| `entry_bb_window` | 20 | 10..80 | confirm lookback range |
| `entry_bb_stddev` | 2.0 | 1.2..3.5 | confirm volatility band width |
| `entry_rsi_period` | 14 | 5..40 | confirm RSI lookback |
| `entry_rsi_max` | 35.0 | 10.0..55.0 | confirm oversold threshold |
| `exit_take_profit_pct` | 0.08 | 0.01..0.25 | confirm profit target cap |
| `exit_stop_loss_pct` | 0.03 | 0.005..0.12 | confirm stop-loss cap |
| `trailing_stop_pct` | 0.02 | 0.0..0.08 | confirm trailing stop usage |
| `add_position_threshold_pct` | 0.025 | 0.0..0.08 | confirm add-position trigger |
| `reduce_position_threshold_pct` | 0.04 | 0.0..0.15 | confirm reduce-position trigger |
| `max_additions` | 2 | 0..3 | confirm pyramiding cap |
| `leverage` | 1.0 | 1.0..3.0 | confirm hard leverage cap |
| `risk_per_trade` | 0.01 | 0.001..0.02 | confirm hard per-trade risk cap |
| `max_portfolio_exposure` | 0.30 | 0.05..0.60 | confirm portfolio exposure cap |
| `cooldown_candles` | 3 | 0..72 | confirm cooldown units |

## Hard Constraints

- Missing or unknown genome fields are rejected.
- Boolean, non-finite, and non-numeric numeric values are rejected.
- Integer fields must be real integers.
- `exit_stop_loss_pct` must be lower than `exit_take_profit_pct`.
- `leverage` must not exceed `3.0`.
- `risk_per_trade` must not exceed `0.02`.
- `max_portfolio_exposure` must not exceed `1.0`; the current schema cap is `0.60`.
- `cooldown_candles` must not be negative.
- Output config must be JSON-safe.

## Risk Rules

- RiskGovernor is advisory only.
- Drawdown above `0.10` reduces risk.
- Loss streak above `4` reduces risk.
- Leverage and per-trade risk are clamped before mock evaluation.
- The adapter preview keeps `dry_run_only=true` and `real_trading_enabled=false`.

## GA Optimized Parameters

All 14 genome fields are currently GA-optimized in mock runs. Future owner review
may freeze fields such as leverage, max additions, or cooldown if those should
be controlled only by risk policy.

## Parameters Not In GA

The following values are intentionally not optimized by GA at this stage:

- exchange credentials
- account identifiers
- live trading toggles
- deployment or rollback controls
- download-data controls
- Freqtrade command arguments
- runtime output roots

## Current Mock Evaluation Logic

The custom mock pipeline evaluates:

- mock backtest metrics
- risk-aware fitness
- advisory RiskGovernor output
- walk-forward stability
- Monte Carlo stress distribution
- multi-pair portfolio aggregation
- experiment registry fixture rows
- frontend custom run detail previews

## Risk Boundary

- No real backtest was run.
- No real Freqtrade adapter was enabled.
- No subprocess execution was introduced.
- No exchange/API access was used.
- No download-data path was used.
- No deployment or rollback path was used.
- Quarantined Freqtrade drafts remain outside the committed mainline until
  cleanup or archive is explicitly handled.

## Questions For Owner

- Are leverage and risk caps acceptable for your account size and exchange rules?
- Should risk caps vary by pair, timeframe, or volatility regime?
- Should add/reduce position logic be separated for long and short positions?
- Should the cooldown be candles only, or should the final adapter emit seconds
  or minutes too?
- Should `max_portfolio_exposure` include open correlated positions outside this
  strategy family?

## Verdict

PENDING OWNER REVIEW
