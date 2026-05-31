# STAGE-003 Commit 1 Staging Report

## Staging Result

- staged: `true`
- commit_group: `Commit 1`
- staged_file_count: `10`
- staged_files:
  - `.gitignore`
  - `data/downloader.py`
  - `docs/test_baseline.md`
  - `scripts/workflow.py`
  - `strategy/backtest.py`
  - `tests/test_backtest.py`
  - `tests/test_data_downloader.py`
  - `tests/test_evaluation.py`
  - `tests/test_workflow.py`
  - `user_data/example.json`

## Excluded Files

Confirmed not staged in Commit 1:

- `.workflow/`
- `bollinger_evolver/`
- `config/ga_bollinger_resonance.json`
- `README.md`
- `docs/architecture_baseline.md`
- `docs/bollinger_evolver_runner_runbook.md`
- `docs/commit_split_plan.md`
- `docs/workspace_hygiene_report.md`
- `docs/staging_preadd_audit.md`
- `user_data/strategies/BollingerResonanceStrategy.py`

## Cached Diff Check

- `git diff --cached --check` result: `PASS`
- note:
  - one trailing-whitespace issue in `strategy/backtest.py` was removed before final restaging

## Sensitive Scan Summary

Staged diff scan command:

```powershell
git diff --cached | rg -n "api_key|secret|password|private_key|mnemonic|webhook|jwt|token"
```

Summary:

- total matches: `32`
- placeholder: `19`
- redacted: `2`
- structural reference: `11`
- risk: `0`

Interpretation:

- placeholder:
  - sample config placeholder replacements such as `CHANGE_ME_*_PLACEHOLDER`
  - test fixture strings used to verify redaction logic
- redacted:
  - redaction helper names and assertions about redacted payloads
- structural reference:
  - credential field names in redaction lists and workflow/login parameter handling
- risk:
  - no live secret value identified in staged content

## Validation

- GeneTrader tests result:
  - `$env:GENETRADER_CONFIG='ga.json.example'; python -m pytest tests -q`
  - `217 passed`
- Bollinger Evolver tests result:
  - `python -m unittest discover bollinger_evolver.tests`
  - `231 OK (skipped=4)`
- compileall result:
  - `python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests`
  - `PASS`

## Commit Message Suggestion

```text
chore: harden config handling and restore test baseline
```

## Notes

- no `git commit` was executed
- no `git reset` was executed
- no files were deleted
- no real Freqtrade backtest/hyperopt was run
- no exchange connection was used
- this report is intentionally not staged with Commit 1 and should remain for a later docs/process commit
