# Test Baseline

Use the checked-in example config for upstream GeneTrader tests. Do not create
or commit a real `ga.json` with exchange credentials.

Install local development dependencies before running validation:

```powershell
python -m pip install -r requirements.txt
cd frontend
npm install
cd ..
```

```powershell
$env:GENETRADER_CONFIG='ga.json.example'
python -m pytest tests -q
python -m unittest discover bollinger_evolver.tests
```

The Bollinger Evolver test suite is mock/default-disabled by design and does
not run real Freqtrade backtests.

Legacy `strategy/backtest.py` and `data/downloader.py` subprocess execution is
disabled unless `GENETRADER_ENABLE_LEGACY_FREQTRADE_EXECUTION=1` is set. Keep
that variable unset for normal safety scans and only enable it for controlled,
mocked tests or an explicitly approved local Freqtrade run.

For safe Bollinger Evolver mock-first runner usage, see
`docs/bollinger_evolver_runner_runbook.md`.
