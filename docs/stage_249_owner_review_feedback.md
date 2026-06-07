# STAGE-249 Owner Review Decision Tracking

## Current Status

```text
Owner review decision: PENDING
Real backtest gate: BLOCKED
Remote sync: PENDING
Codex approval authority: NONE
```

## Valid Owner Decision Values

The only accepted decision values are:

```text
APPROVED
NEEDS CHANGES
```

Do not infer approval from silence, successful tests, local health reports, or
mock-first pipeline status.

## Reviewer Feedback Template

```text
Decision:
Reviewer:
Review date:

Reviewer comments:

Required changes:

Risk notes:

Next stage:
```

## If Decision Is NEEDS CHANGES

Trigger:

```text
STAGE-250 Custom Strategy Parameter Revision
```

Allowed scope:

- `bollinger_evolver/custom_strategy_schema.py`
- `bollinger_evolver/tests/test_custom_strategy_schema.py`
- `bollinger_evolver/trading_system_adapter.py`
- `bollinger_evolver/tests/test_trading_system_adapter.py`
- `bollinger_evolver/risk_governor.py`
- `bollinger_evolver/tests/test_risk_governor.py`
- `docs/trading_system_abstraction.md`
- owner review docs and fixtures as needed

Still blocked:

- real Freqtrade backtest
- download-data
- hyperopt
- exchange API access
- deployment
- rollback
- live trading

## If Decision Is APPROVED

Approval alone is not enough to run real backtests. The real backtest gate also
requires:

- remote mainline sync or accepted PR
- explicit approval for the exact run
- `GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST=1`
- `dry_run_only=True`
- sandbox config
- temp output directory
- no API key or exchange secret
- no download-data
- no hyperopt
- no trade command
- no deployment or rollback

## Safety Boundary

This document is tracking-only. It does not trigger code changes, real
backtests, deployment, rollback, or owner approval.
