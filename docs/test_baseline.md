# Test Baseline

Use the checked-in example config for upstream GeneTrader tests. Do not create
or commit a real `ga.json` with exchange credentials.

```powershell
$env:GENETRADER_CONFIG='ga.json.example'
python -m pytest tests -q
python -m unittest discover bollinger_evolver.tests
```

The Bollinger Evolver test suite is mock/default-disabled by design and does
not run real Freqtrade backtests.

For safe Bollinger Evolver mock-first runner usage, see
`docs/bollinger_evolver_runner_runbook.md`.
