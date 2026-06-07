# STAGE-261 Real Backtest Gate Threat Model

## Verdict

REAL BACKTEST = BLOCKED.

This threat model describes risks for a future real backtest gate. It does not
approve or run real Freqtrade, download-data, hyperopt, exchange API access,
deployment, rollback, or live trading.

## Current Gate Requirements

All conditions must be true before any future real backtest can be considered:

- owner review is `APPROVED`
- remote mainline or PR is synchronized
- explicit approval is provided for the exact run
- `GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST=1`
- `dry_run_only=True`
- output root is an explicit temp or sandbox directory
- no API key or exchange secret is present
- no download-data command
- no hyperopt command
- no trade/live command
- no deployment or rollback command

## Threats And Mitigations

| Threat | Risk | Current Mitigation | Residual Risk |
| --- | --- | --- | --- |
| Real Freqtrade subprocess starts unexpectedly | Real execution or environment access | Real adapter gate is fail-closed and tests assert no subprocess by default | Medium until owner approval and run command are reviewed |
| `download-data` is triggered accidentally | Network/data writes and policy violation | Command builders and gates reject download-data | Low while gate remains blocked |
| `hyperopt` is triggered accidentally | Expensive or unsafe optimizer execution | Command builders and gates reject hyperopt | Low while gate remains blocked |
| `live` or `trade` args mix into command | Live trading exposure | Gate rejects live/trade commands and requires dry-run-only | Medium if command is manually edited |
| Secret leakage in config/env/args | Credential exposure | Redaction and secret scans are required; request/result must be JSON-safe | Medium until final pre-run scan |
| Output writes to real repo/runtime/data directory | Repo pollution or data leakage | Output root allowlist and tempdir requirements | Medium if manual path override is allowed |
| `dry_run=false` or live config | Real trading risk | Sandbox config builder forces dry-run and rejects live mode | Medium until final config is reviewed |
| Exchange API access | Account or market access | No exchange secrets allowed; gate checks env/request/output | Medium until final env scan |
| Owner approval inferred from tests | Unauthorized escalation | Docs require explicit `APPROVED`; Codex cannot approve | Low |
| Deployment/rollback triggered near backtest | Operational state change | Deployment and rollback gates remain separate and blocked | Low |

## Pre-run Review Checklist

Before any future real backtest gate opening:

```text
owner_review = APPROVED
remote_sync = confirmed
explicit_run_approval = provided
dry_run_only = true
output_root = temp/sandbox
secret_scan = clean
command = backtesting only
download-data = absent
hyperopt = absent
trade/live = absent
deploy/rollback = absent
```

## Current Conclusion

```text
REAL BACKTEST = BLOCKED
```

No real backtest should be attempted in the current state.
