# Offline Data Acquisition Plan

This document defines the local, offline dataset required before any future controlled Bollinger Evolver real-backtest readiness work. It is a planning document only: do not download data, do not connect to an exchange, and do not run Freqtrade backtesting or hyperopt from this task.

## Current Data Readiness Verdict

The latest required pair/timeframe data gate was run against `user_data/data/` with the real-readiness constraints:

- `status=FAIL`
- `allowed_for_evaluation=false`
- `required_pairs=["BTC/USDT"]`
- `required_timeframes=["15m","1h","4h"]`
- `min_candles_per_pair_timeframe=100`

The local directory currently does not satisfy the required coverage.

`missing_pair_timeframes`:

- `BTC/USDT 15m`
- `BTC/USDT 1h`
- `BTC/USDT 4h`

## Required Dataset

Minimum required market coverage:

- pair: `BTC/USDT`
- timeframes: `15m`, `1h`, `4h`
- minimum candles per pair/timeframe: `100`

Recommended local coverage for useful future backtest preparation:

- `15m`: `>= 5000` candles
- `1h`: `>= 2000` candles
- `4h`: `>= 1000` candles

Required candle fields:

- `timestamp` or `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

## Accepted Local File Formats

The offline manifest builder supports these local file formats:

- `.json`
- `.jsonl`
- `.csv`

Optional formats may be available when local dependencies support them:

- `.feather`
- `.parquet`

CSV example:

```csv
timestamp,open,high,low,close,volume
1717200000000,68000,68100,67900,68050,123.45
```

JSON list example:

```json
[
  [1717200000000, 68000, 68100, 67900, 68050, 123.45]
]
```

JSON dict list example:

```json
[
  {
    "timestamp": 1717200000000,
    "open": 68000,
    "high": 68100,
    "low": 67900,
    "close": 68050,
    "volume": 123.45
  }
]
```

## Recommended Directory Layout

Nested exchange-style layout:

```text
user_data/data/binance/BTC_USDT-15m.json
user_data/data/binance/BTC_USDT-1h.json
user_data/data/binance/BTC_USDT-4h.json
```

Flat local layout:

```text
user_data/data/BTC_USDT-15m.csv
user_data/data/BTC_USDT-1h.csv
user_data/data/BTC_USDT-4h.csv
```

Do not commit large market data files unless explicitly intended. Prefer local-only storage or an external archive for market data.

## How To Generate Manifest

After local files are prepared manually, generate an offline manifest without downloading data:

```powershell
python -c "from bollinger_evolver.data_manifest import build_offline_data_manifest; build_offline_data_manifest(data_dir='user_data/data', write_report=True)"
```

The manifest report is written under `.runtime/bollinger_evolver/data_manifests/` when data files are present and `write_report=True` is used.

## How To Check Required Gate

Run the required pair/timeframe gate with explicit constraints:

```powershell
python -c "from bollinger_evolver.data_manifest import build_offline_data_manifest; from bollinger_evolver.data_quality import evaluate_data_coverage_gate; m=build_offline_data_manifest(data_dir='user_data/data', write_report=True); g=evaluate_data_coverage_gate(m, required_pairs=['BTC/USDT'], required_timeframes=['15m','1h','4h'], min_candles_per_pair_timeframe=100); print(g)"
```

Expected readiness target:

- `allowed_for_evaluation=true`
- no missing `BTC/USDT 15m`
- no missing `BTC/USDT 1h`
- no missing `BTC/USDT 4h`

## Data Quality Requirements

The required data quality baseline is:

- duplicate timestamps: `0`
- out-of-order rows: `0`
- invalid OHLC: `0` required
- missing OHLC: `0` required
- gap ratio: `<= 0.02`

If these checks fail, do not proceed to real-backtest preparation. Fix or replace the local dataset first.

## Path From FAIL to READY

1. Prepare local `BTC/USDT` files for `15m`, `1h`, and `4h`.
2. Run the offline manifest builder.
3. Run the required pair/timeframe gate.
4. Confirm `allowed_for_evaluation=true`.
5. Re-run backtest preflight with the generated `data_manifest_path`.
6. Only after preflight reaches `READY`, consider a future separately approved short controlled backtest task.

## Still Forbidden

The following remain forbidden in this project phase:

- downloading data
- connecting to an exchange
- using API keys
- writing secrets
- running `freqtrade download-data`
- running Freqtrade backtesting
- running Freqtrade hyperopt
- live trading
- committing large local data accidentally
