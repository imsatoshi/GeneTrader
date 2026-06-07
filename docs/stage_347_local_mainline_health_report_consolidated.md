# STAGE-347 Local Mainline Health Report Consolidated

## Status

```text
STAGE-347 = PASS
Date = 2026-06-07
HEAD = 586664d Ignore local workflow artifacts
Branch = main
Remote state = ahead origin/main by 72 commits
Owner review = PENDING
REAL BACKTEST = BLOCKED
```

This report consolidates the current local health state after STAGE-343 final
audit v2 and STAGE-346 workflow hygiene. It is a mock-first local validation
record only.

## Git Hygiene

Entry state before this report:

```text
git status --short = clean
git diff --cached --name-only = empty
```

`.workflow/` is now ignored by `.gitignore` through the STAGE-346 commit:

```text
586664d Ignore local workflow artifacts
```

## Validation Matrix

Command executed:

```powershell
scripts\run_safe_test_matrix.cmd
```

Results:

```text
python -m pytest tests -q
239 passed, 4 subtests passed

python -m unittest discover -s bollinger_evolver/tests
900 tests passed, 6 skipped

frontend targeted vitest
4 files passed, 25 tests passed

frontend full vitest
19 files passed, 70 tests passed

npm.cmd run build
passed, no large chunk warning observed

python -m compileall ...
passed

git diff --check
passed

git diff --cached --check
passed
```

Argparse error lines in the unittest output are expected negative tests for
fail-closed output directory validation in the mock CLI modules.

## Current Mock-first Coverage

Validated local-only areas:

- Offline readiness and data gates.
- GA mock execution, artifacts, and session summaries.
- Custom strategy schema and trading system adapter.
- Risk-aware fitness, RiskGovernor, loss streak control, circuit breaker, and
  risk budget simulation.
- Position sizing and strategy explanation.
- Walk-forward, Monte Carlo, and portfolio mock evaluation.
- Experiment registry, comparison, Pareto selection, and contract fixtures.
- Owner review pack and owner review guide.
- Frontend mock dashboard, run explorer, risk dashboard, run comparison, and
  analysis pages.

## Safety Boundary

The following remain blocked:

```text
real Freqtrade execution
download-data
hyperopt
exchange/API access
live trading
deployment
rollback
```

Real backtest gate remains blocked until:

```text
remote sync or PR review complete
owner review returns APPROVED
explicit real-backtest approval is provided
dry-run-only sandbox output is used
no credentials, exchange secrets, download-data, hyperopt, trade, deploy, or rollback
```

## Owner Review

Owner review is still pending. Codex has not produced `APPROVED`.

Accepted owner decisions remain:

```text
APPROVED
NEEDS CHANGES
```

## Verdict

```text
PASS / local mock-first mainline health verified
PASS / workflow artifacts ignored
PASS / safe test matrix passed
BLOCKED / real backtest still requires owner approval and remote sync
```
