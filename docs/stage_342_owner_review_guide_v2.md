# STAGE-342 Owner Review Guide v2

## Goal

Update the owner review guide so the manual review can evaluate the newer
mock-first analysis modules without unlocking real execution.

## Review Inputs

- `docs/custom_strategy_review_guide.md`
- `bollinger_evolver.owner_review_pack`
- `bollinger_evolver.risk_cli explain`
- `bollinger_evolver.risk_cli explain-strategy`
- Frontend mock risk dashboard fixtures

## Added Review Areas

### Position Sizing

The owner should review notional position value, margin required, risk amount,
leverage, and max-position caps. These values are fixture-based arithmetic only.
They do not read a real balance or exchange margin state.

### Strategy Explanation

The owner should compare generated entry, exit, risk, warning, and fitness
explanations against the intended strategy logic. A clear explanation is not
approval. It is review evidence.

### Risk Dashboard Summary

The owner review pack now includes a dashboard-style summary for:

- max drawdown
- loss streak
- portfolio exposure
- risk per trade
- leverage
- circuit breaker status

Rows marked `reduce_risk` or `pause_trading` require manual review before any
future real-backtest gate is considered.

## Owner Decision

The only accepted owner decisions are:

- `APPROVED`
- `NEEDS CHANGES`

Codex must not produce `APPROVED` for the owner.

## Safety Boundary

Current status:

```text
REAL BACKTEST = BLOCKED
Freqtrade / download-data / hyperopt / exchange API / deploy / rollback = BLOCKED
```

This guide is documentation only. It does not approve execution, trading,
deployment, rollback, data download, or exchange access.

## Verification

Recommended local checks:

```powershell
python -m unittest bollinger_evolver.tests.test_owner_review_pack
python -m unittest bollinger_evolver.tests.test_risk_cli
git diff --check
git diff --cached --check
```

## Verdict

PASS / owner review guide updated for risk analysis modules, with real backtest
remaining blocked.
