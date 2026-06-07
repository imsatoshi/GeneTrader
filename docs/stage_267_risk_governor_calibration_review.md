# STAGE-267 Risk Governor Calibration Review

## Verdict

PENDING OWNER REVIEW.

The current `RiskGovernorConfig` values are conservative enough for mock-first
development, but the owner must decide whether they are acceptable for the real
strategy abstraction.

## Current Defaults

| Setting | Current Value | Review Question | Preliminary Assessment |
| --- | ---: | --- | --- |
| `max_leverage` | 3.0 | Is 3x too high for this strategy/account? | Needs owner decision. |
| `max_risk_per_trade` | 0.02 | Is 2% per trade too high? | Potentially high for volatile/multi-pair use. |
| `max_portfolio_exposure` | 0.30 | Is 30% aggregate exposure acceptable? | Needs account-size/context review. |
| `drawdown_cutoff` | 0.10 | Should risk reduction trigger before 10% drawdown? | Consider lower threshold if strategy is leveraged. |
| `loss_streak_cutoff` | 4 | Should 4 losses be enough to reduce risk? | Reasonable mock default; owner may prefer 3. |
| `drawdown_risk_multiplier` | 0.50 | Should drawdown halve risk or pause trading? | Halving risk is safer than no action; pause may be required. |
| `loss_streak_risk_multiplier` | 0.50 | Should loss streak halve risk or pause trading? | Needs owner decision. |
| `cooldown_candles` | 3 in `CustomStrategyGenome` | Is cooldown long enough after loss or risk events? | Likely needs strategy/timeframe-specific review. |

## Calibration Risks

- 3x leverage may be too high if combined with multiple pairs.
- 2% risk per trade may be too high during correlated drawdowns.
- 30% portfolio exposure can still produce large account-level drawdown under
  correlated losses.
- A 10% drawdown cutoff may be late for a leveraged strategy.
- Halving risk after drawdown/loss streak may not be strict enough if the owner
  expects a trading pause.

## Recommended Owner Decisions

Owner should explicitly decide:

- approved maximum leverage
- approved max risk per trade
- approved max portfolio exposure
- drawdown level for reduce-risk
- drawdown level for pause-trading
- loss streak level for reduce-risk
- loss streak level for cooldown/pause
- whether additions are allowed after losing entries

## Current Conclusion

```text
PENDING OWNER REVIEW
REAL BACKTEST = BLOCKED
```
