# Custom Strategy Review Guide

## Purpose

This guide helps the owner review the mock-first custom strategy abstraction
before any controlled real-backtest gate is considered. It is a review guide
only; it does not approve execution.

## Review Decision

The owner decision must be exactly one of:

- `APPROVED`
- `NEEDS CHANGES`

Codex must not mark the strategy abstraction as `APPROVED` on behalf of the
owner.

## Parameter Review Checklist

- Confirm every GA-optimized parameter represents the intended trading system.
- Confirm leverage cap `3.0` is acceptable for account size, pair liquidity,
  and exchange limits.
- Confirm `risk_per_trade <= 0.02` is conservative enough.
- Confirm `max_portfolio_exposure` should be allowed above `0.30` only with
  explicit owner acceptance.
- Confirm stop-loss is always below take-profit.
- Confirm `max_additions` matches the intended add-position policy.
- Confirm cooldown units are candles and are appropriate for every timeframe.

## Hard Constraints To Verify

- Unknown genome fields are rejected.
- Missing genome fields are rejected.
- Boolean and non-finite numeric values are rejected.
- Integer parameters require actual integers.
- Stop-loss must be lower than take-profit.
- Strategy config output must remain JSON-safe.
- RiskGovernor output is advisory and must not mutate the source config.

## Risk Items That Require Manual Confirmation

- High leverage warnings.
- High per-trade risk warnings.
- Portfolio exposure above the conservative default.
- Drawdown above the risk cutoff.
- Long loss streaks that trigger risk reduction or cooldown.
- Position sizing previews capped by max position value.

## Mock-First Pipeline To Review

The current custom strategy path is intentionally local and fixture-driven:

```text
CustomStrategyGenome
-> custom_strategy_config_from_genome
-> mock GA evaluation
-> RiskGovernor advisory output
-> walk-forward stability
-> Monte Carlo stress summary
-> multi-pair portfolio mock summary
-> position sizing preview
-> strategy explainability report
-> owner review pack
```

### Mock GA

Mock GA optimizes only the custom strategy parameter table. It does not run
Freqtrade, download market data, or connect to an exchange.

### RiskGovernor

RiskGovernor clamps or reduces leverage and per-trade risk in advisory reports.
It does not mutate the source strategy config or unlock execution.

### Walk-forward

Walk-forward results are train / validation / test mock segments used to review
stability and overfit risk.

### Monte Carlo

Monte Carlo results are synthetic perturbation summaries. Failure rate is a
review signal, not a live trading decision.

### Portfolio

Portfolio summaries aggregate mock multi-pair outputs and correlation penalty.
Owner should confirm whether exposure caps are conservative enough for the
actual account context.

## Local Review Reference Report

The local health report generator can produce JSON, Markdown, and HTML files
for review bookkeeping:

```powershell
python -m bollinger_evolver.local_health_report --output <tempdir>
```

The report records module readiness, latest safe test matrix results, and the
blocked real-backtest boundary.

## Why Real Backtest Remains Blocked

Real backtest remains `BLOCKED` until all of the following are true:

- Remote sync or PR review is complete.
- Owner review returns `APPROVED`.
- Explicit real-backtest approval is given.
- Dry-run-only sandbox config is used.
- No account credentials or exchange secrets are present.
- No data download, hyperopt, live trade, deployment, or rollback path is used.

## Suggested Local Review Commands

```powershell
python -m bollinger_evolver.owner_review_pack --output <tempdir>
python -m bollinger_evolver.risk_cli explain --fixture safe_default --output <tempdir>
python -m unittest bollinger_evolver.tests.test_owner_review_pack bollinger_evolver.tests.test_risk_cli
```
