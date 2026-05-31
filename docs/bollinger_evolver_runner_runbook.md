# Bollinger Evolver Runner Runbook

## Safety Positioning

- mock-first
- real_backtest=false
- allow_real_backtest=False
- no exchange connection
- no API key / secret
- no live trading
- no Freqtrade backtest/hyperopt by default

The Bollinger Evolver runner is intentionally read-only and mock-first. It does
not change `main.py`, does not change the upstream GeneTrader GA core, and does
not require a live exchange session.

## Prerequisites

- `GENETRADER_CONFIG=ga.json.example`
- no real `ga.json` required
- a data manifest is required by default unless `--disable-data-quality-gate`
  is explicitly used

Example PowerShell baseline:

```powershell
$env:GENETRADER_CONFIG='ga.json.example'
python -m unittest discover bollinger_evolver.tests
python -m pytest tests -q
```

## Basic Command

This command keeps the runner mock-first and read-only, but explicitly disables
the data gate. Use it only when you intentionally want to bypass manifest
validation.

```powershell
python -m bollinger_evolver.ga.runner_cli `
  --config config/ga_bollinger_resonance.json `
  --generations 2 `
  --population-size 8 `
  --output-root .runtime/bollinger_evolver/sessions `
  --disable-data-quality-gate
```

## Safer Command With Data QA

Prefer a manifest-backed run so `dataQualityGate` can block incomplete or
degraded datasets before any GA evaluation starts.

```powershell
python -m bollinger_evolver.ga.runner_cli `
  --config config/ga_bollinger_resonance.json `
  --generations 2 `
  --population-size 8 `
  --output-root .runtime/bollinger_evolver/sessions `
  --data-manifest .runtime/bollinger_evolver/manifests/example_manifest.json
```

## Dry Run

Use `--dry-run` to validate configuration and data QA only. This does not run a
GA session and does not generate full GA metrics/report artifacts.

```powershell
python -m bollinger_evolver.ga.runner_cli `
  --config config/ga_bollinger_resonance.json `
  --data-manifest .runtime/bollinger_evolver/manifests/example_manifest.json `
  --output-root .runtime/bollinger_evolver/sessions `
  --dry-run
```

## Generated Artifacts

Under `<output_root>/<session_id>/`, the runner can generate:

- `session_summary.json`
- `session_report.json`
- `session_report.md`
- generated strategy files under the session temp/output directory

Artifact hygiene guarantees:

- no `reports` writes outside the session output directory
- no `registry.json` writes
- no `main.py` mutation
- no exchange writes
- no live trading deployment

## How To Review Results

Start from `session_summary.json` for the machine-readable session envelope, then
use `session_report.json` and `session_report.md` for human review.

Key fields:

- `dataQualityGate`
- `generation_summaries`
- `final_best`
- `riskAndSafety`
- `recommendation`
- `mock_evaluation=true`
- `real_backtest=false`

## What PASS Means

`PASS` means the session completed in mock-first mode, the session summary was
written, and the final summary marks `mock_evaluation=true` and
`real_backtest=false`.

It does not mean a real Freqtrade backtest ran.

## What BLOCKED Means

`BLOCKED` means the session stopped before GA evaluation because preflight or
`dataQualityGate` rejected the inputs, such as:

- manifest missing
- required pair/timeframe coverage missing
- not enough candles
- invalid data gate thresholds

## What NO_FINAL_BEST Means

`NO_FINAL_BEST` means the session wrote its artifacts, but no valid champion
individual was produced. Review the `recommendation`, failures, and gate status
before rerunning.

## Forbidden Usage

The CLI explicitly rejects unsafe or live-oriented flags:

- `--allow-real-backtest`
- `--live`
- `--api-key`
- `--secret`
- exchange/live args

Do not add real exchange credentials, do not attempt live trading, and do not
use this runner as a Freqtrade execution entrypoint.

## Troubleshooting

### manifest missing

If no manifest is provided, the runner blocks by default unless
`--disable-data-quality-gate` is explicitly used.

### data quality gate failed

Review `dataQualityGate.fail_reasons` and fix the manifest or data coverage
before rerunning.

### no final best

Open `session_report.md` and inspect `generation_summaries`, `final_best`, and
`recommendation`.

### strategy import skipped because freqtrade missing

Some tests or review flows may skip strategy-import checks when the local
Freqtrade dependency is unavailable. This is acceptable for mock-first
validation and does not imply a real backtest path was used.
