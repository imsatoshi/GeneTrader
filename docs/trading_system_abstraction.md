# Trading System Abstraction

## Purpose

This document defines a mock-first strategy-system abstraction that can be
mapped into GA genomes without enabling live trading, real backtests, exchange
access, or Freqtrade subprocess execution.

The abstraction is intentionally parameter-first:

```text
strategy idea
-> parameter table
-> rule table
-> genome bounds
-> JSON-safe StrategyConfig
-> advisory RiskGovernor
```

## Safety Boundary

- No real exchange/API access.
- No real Freqtrade import or subprocess execution.
- No download-data, hyperopt, live trading, deployment, or rollback.
- No credentials, API keys, tokens, passwords, private keys, or `.env` values.
- All outputs must be JSON-safe.
- Risk changes are advisory unless a later explicitly approved stage applies them.

## Parameter Table

| Field | Type | Default | Bounds | GA Optimized | Hard Constraint |
| --- | --- | ---: | --- | --- | --- |
| `entry_bb_window` | int | 20 | 10..80 | yes | positive integer |
| `entry_bb_stddev` | float | 2.0 | 1.2..3.5 | yes | finite numeric |
| `entry_rsi_period` | int | 14 | 5..40 | yes | positive integer |
| `entry_rsi_max` | float | 35.0 | 10.0..55.0 | yes | finite numeric |
| `exit_take_profit_pct` | float | 0.08 | 0.01..0.50 | yes | greater than stop loss preferred |
| `exit_stop_loss_pct` | float | 0.03 | 0.005..0.20 | yes | finite numeric |
| `trailing_stop_pct` | float | 0.02 | 0.0..0.15 | yes | non-negative |
| `add_position_threshold_pct` | float | 0.025 | 0.0..0.12 | yes | non-negative |
| `reduce_position_threshold_pct` | float | 0.04 | 0.0..0.20 | yes | non-negative |
| `max_additions` | int | 2 | 0..5 | yes | integer |
| `leverage` | float | 1.0 | 1.0..10.0 | yes | RiskGovernor clamps preferred max |
| `risk_per_trade` | float | 0.01 | 0.001..0.05 | yes | RiskGovernor clamps preferred max |
| `max_portfolio_exposure` | float | 0.30 | 0.05..1.0 | yes | RiskGovernor clamps preferred max |
| `cooldown_candles` | int | 3 | 0..50 | yes | integer |

## Rule Table

| Rule Group | Inputs | Output | Notes |
| --- | --- | --- | --- |
| Entry | Bollinger lower band, RSI, cooldown | entry intent | mock-only signal definition |
| Exit | take-profit, stop-loss, trailing stop | exit intent | no order placement |
| Add Position | open position, unrealized drawdown, max additions | add intent | bounded by risk config |
| Reduce Position | exposure, profit threshold, drawdown | reduce intent | advisory only |
| Leverage | genome leverage, drawdown, loss streak | adjusted leverage | governed by RiskGovernor |
| Risk | risk per trade, portfolio exposure | adjusted risk | governed by RiskGovernor |

## Genome To StrategyConfig

The schema maps each genome into a JSON-safe strategy config:

```text
CustomStrategyGenome
-> validate_custom_strategy_genome
-> custom_strategy_config_from_genome
```

The config includes top-level compatibility fields:

- `leverage`
- `risk_per_trade`
- `max_portfolio_exposure`

This lets the advisory RiskGovernor inspect custom strategy configs without
needing to mutate the original object.

## Hard Constraints

- Unknown genome fields are rejected.
- Missing genome fields are rejected.
- Boolean values are rejected for numeric fields.
- Non-finite values are rejected.
- Int parameters must be integer values.
- Config output must serialize with `json.dumps(..., sort_keys=True)`.

## Deferred Work

- Real exchange execution remains out of scope.
- Freqtrade execution remains out of scope.
- Real backtest adapters remain behind the committed disabled boundary.
- Strategy-specific position lifecycle rules can be expanded after owner review.
