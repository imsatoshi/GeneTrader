# Offline Data Manifest Gate

`bollinger_evolver.data_gate` is a read-only readiness gate for local Bollinger Evolver market data. It checks whether local files satisfy the minimum `BTC/USDT` dataset contract before any future real-backtest preparation.

## Safety Boundary

The gate does not download data, does not connect to an exchange, does not call `freqtrade download-data`, does not run Freqtrade backtesting, does not run hyperopt, and does not write API keys or secrets. It only reads local files and prints JSON to stdout.

## Default Contract

- symbol: `BTC/USDT`
- required timeframes: `15m`, `1h`, `4h`
- minimum candles per pair/timeframe: `100`
- accepted formats: `.json`, `.jsonl`, `.csv`, optional `.feather`, optional `.parquet`

## Manifest Shape

The output uses `schema_version=offline_data_manifest.v1` and includes:

```json
{
  "schema_version": "offline_data_manifest.v1",
  "status": "FAIL | PARTIAL | READY",
  "allowed_for_evaluation": false,
  "symbol": "BTC/USDT",
  "required_timeframes": ["15m", "1h", "4h"],
  "detected_files": [],
  "missing_timeframes": [],
  "format_checks": {
    "accepted_format": false,
    "detected_format": null
  },
  "quality_checks": {
    "has_timestamp_column": false,
    "has_ohlcv_columns": false,
    "row_count_ok": false,
    "no_obvious_empty_file": false
  },
  "blocked_reasons": [],
  "safe_next_action": "prepare_offline_data_files"
}
```

## Status Rules

- `FAIL`: any required timeframe is missing, the data directory is missing or empty, or only unsupported formats are present.
- `PARTIAL`: all required timeframes have accepted local files, but basic quality checks fail, such as empty files, missing timestamp, missing OHLCV fields, low row count, missing OHLC, or invalid OHLC.
- `READY`: all required timeframe files exist, formats are accepted, row count is sufficient, and basic timestamp/OHLCV checks pass.

`allowed_for_evaluation=true` is only valid when `status=READY`.

## CLI Usage

The CLI is stdout-only by default and does not write reports:

```powershell
python -m bollinger_evolver.data_gate --data-dir user_data/data --symbol BTC/USDT
```

Optional arguments:

```powershell
python -m bollinger_evolver.data_gate --data-dir user_data/data --symbol BTC/USDT --timeframes 15m 1h 4h --min-candles 100
```

## Test Scenarios

The static and unit coverage protects these scenarios:

- no data directory -> `FAIL`
- empty data directory -> `FAIL`
- only `15m` exists -> `FAIL`
- `15m` and `1h` exist, `4h` missing -> `FAIL`
- unsupported required file format -> `FAIL`
- all files exist but are empty -> `PARTIAL`
- all files exist but missing OHLCV columns -> `PARTIAL`
- all required files valid -> `READY`

## Next Safe Action

If the gate returns `FAIL` or `PARTIAL`, keep `safe_next_action=prepare_offline_data_files`. Only after `READY` should a future separate task re-run backtest preflight with the validated local manifest.
