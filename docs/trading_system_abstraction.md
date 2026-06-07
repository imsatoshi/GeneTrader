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
| `exit_take_profit_pct` | float | 0.08 | 0.01..0.25 | yes | must be greater than stop loss |
| `exit_stop_loss_pct` | float | 0.03 | 0.005..0.12 | yes | must be below take profit |
| `trailing_stop_pct` | float | 0.02 | 0.0..0.08 | yes | non-negative |
| `add_position_threshold_pct` | float | 0.025 | 0.0..0.08 | yes | non-negative |
| `reduce_position_threshold_pct` | float | 0.04 | 0.0..0.15 | yes | non-negative |
| `max_additions` | int | 2 | 0..3 | yes | integer |
| `leverage` | float | 1.0 | 1.0..3.0 | yes | hard max aligned with RiskGovernor default |
| `risk_per_trade` | float | 0.01 | 0.001..0.02 | yes | hard max aligned with RiskGovernor default |
| `max_portfolio_exposure` | float | 0.30 | 0.05..0.60 | yes | must not exceed 1.0 |
| `cooldown_candles` | int | 3 | 0..72 | yes | integer |

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
- `exit_stop_loss_pct` must be lower than `exit_take_profit_pct`.
- `leverage` is capped at `3.0` by the genome bounds.
- `risk_per_trade` is capped at `0.02` by the genome bounds.
- `max_portfolio_exposure` must not exceed `1.0`; current calibration caps it at `0.60`.
- `cooldown_candles` cannot be negative.
- Config output must serialize with `json.dumps(..., sort_keys=True)`.

## Owner Review Questions

- Confirm whether `3.0` is the right hard leverage maximum for all pairs or only
  for the first mock portfolio basket.
- Confirm whether `0.02` risk per trade should be absolute, or further reduced
  by pair volatility and account drawdown state.
- Confirm whether `max_additions` should remain at `3`, or be split by pair,
  regime, or position direction.
- Confirm whether `cooldown_candles` should be expressed in candles only or also
  mapped to wall-clock time in the final trading system adapter.

## Owner Review Artifacts

The local review pack generator can produce a JSON and Markdown bundle for
manual inspection:

```powershell
python -m bollinger_evolver.owner_review_pack --output <tempdir>
```

The pack summarizes:

- parameter table and bounds
- hard constraints
- fixture metrics
- risk warnings
- position sizing previews
- explainability summaries

The standalone risk CLI can produce fixture-specific reports:

```powershell
python -m bollinger_evolver.risk_cli explain --fixture safe_default --output <tempdir>
```

Both commands are fixture-only and require an explicit output directory.

## Deferred Work

- Real exchange execution remains out of scope.
- Freqtrade execution remains out of scope.
- Real backtest adapters remain behind the committed disabled boundary.
- Strategy-specific position lifecycle rules can be expanded after owner review.
