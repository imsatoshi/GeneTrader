# STAGE-259 Owner Review Question Checklist

## Verdict

READY FOR OWNER REVIEW.

This checklist helps the owner choose one of the only valid review outcomes:

```text
APPROVED
NEEDS CHANGES
```

Codex must not infer or write `APPROVED` on behalf of the owner.

## Required Questions

1. Does the current `CustomStrategyGenome` fully represent the real trading
   system?
2. Which parameters must never be optimized by GA?
3. Is the maximum leverage too high?
4. Is `risk_per_trade` too high?
5. Is adding to losing positions allowed?
6. Should leverage be reduced after consecutive losses?
7. At what drawdown threshold should trading pause?
8. Is the maximum portfolio exposure reasonable?
9. Is holding multiple pairs at the same time allowed?
10. Should real backtest remain blocked?

## Parameter Coverage Questions

- Are Bollinger entry window and standard deviation sufficient to describe the
  intended entry logic?
- Is RSI period and RSI maximum a required entry filter, or should this be
  optional/fixed?
- Are take-profit, stop-loss, and trailing-stop controls sufficient to describe
  the intended exit behavior?
- Is `max_additions` acceptable, or should additions be disabled until further
  review?
- Should `cooldown_candles` be optimized, fixed, or tied to loss streak?

## Risk Governance Questions

- Should `max_leverage = 3.0` be reduced?
- Should `max_risk_per_trade = 0.02` be reduced?
- Should `max_portfolio_exposure = 0.30` be reduced?
- Should drawdown risk reduction trigger at `drawdown_cutoff = 0.10`, or lower?
- Should loss streak risk reduction trigger at `loss_streak_cutoff = 4`, or
  lower?
- Should risk reduction multiply risk by `0.50`, or should it pause trading?

## Real Backtest Gate Questions

- Has the owner reviewed the strategy abstraction and accepted the current
  hard constraints?
- Has the remote mainline or PR been synchronized for review?
- Is the proposed run dry-run-only?
- Will output be written only to an explicit temp or sandbox directory?
- Are all API keys, exchange secrets, live flags, download-data, hyperopt, and
  trade commands absent?

## Final Owner Decision

Owner decision:

```text
PENDING
```

Valid values:

```text
APPROVED
NEEDS CHANGES
```

Until the decision is `APPROVED`, real backtest remains BLOCKED.
