# STAGE-246 Owner Review Package

## Verdict

PASS for owner review preparation. Human review remains PENDING.

This package summarizes the mock-first custom strategy materials that are ready
for owner review. It does not approve real backtesting and does not trigger any
execution path.

## Review Inputs

Primary documents:

- `docs/custom_strategy_review_guide.md`
- `docs/trading_system_abstraction.md`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/stage_220_local_mainline_health_report.md`
- `docs/stage_244_owner_review_readiness_gate.md`

Primary code contracts:

- `bollinger_evolver/custom_strategy_schema.py`
- `bollinger_evolver/trading_system_adapter.py`
- `bollinger_evolver/risk_governor.py`
- `bollinger_evolver/position_sizing.py`
- `bollinger_evolver/strategy_explainer.py`

Primary fixtures:

- `bollinger_evolver/fixtures/golden/custom_strategy_config_sample.json`
- `bollinger_evolver/fixtures/golden/mock_ga_session_summary_sample.json`
- `bollinger_evolver/fixtures/golden/owner_review_pack_sample.json`
- `bollinger_evolver/fixtures/golden/risk_report_sample.json`

## What The Owner Should Review

### Parameters and bounds

- Confirm that the custom strategy parameters represent the intended trading
  system.
- Confirm which parameters are allowed for GA optimization.
- Confirm which parameters must stay fixed.
- Confirm that default values are conservative.

### Risk constraints

- Confirm maximum leverage.
- Confirm maximum risk per trade.
- Confirm maximum portfolio exposure.
- Confirm maximum open positions.
- Confirm drawdown cutoff behavior.
- Confirm loss streak cooldown and risk reduction behavior.

### Position sizing

- Confirm that `risk_per_trade`, stoploss, leverage, and exposure constraints
  produce acceptable mock position previews.
- Confirm that high-risk fixtures produce warnings.
- Confirm that no real account balance or exchange data is required.

### Explainability

- Confirm that the strategy explanation is understandable.
- Confirm that risk warnings are visible.
- Confirm that fitness explanations do not hide drawdown or leverage risk.

## Review Outcome Contract

The owner must choose one:

```text
APPROVED
NEEDS CHANGES
```

Codex must not write `APPROVED` on behalf of the owner.

## Blocked Until Approval

The following remain blocked until owner approval and remote sync are both
complete:

- real Freqtrade backtest
- download-data
- hyperopt
- exchange API access
- deployment
- rollback
- live trading

## Safe Local Commands

These commands are local-only and mock-first:

```powershell
python -m unittest bollinger_evolver.tests.test_owner_review_pack
python -m unittest bollinger_evolver.tests.test_local_health_report
python -m pytest tests -q
```

## Handoff Notes

The owner review pack can be generated only to an explicit output directory.
It must not be generated into the repository root, `.runtime`, or
`user_data/data`.
