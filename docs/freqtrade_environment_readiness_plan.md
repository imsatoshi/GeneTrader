# Freqtrade Environment Readiness Plan

## Current Preflight Verdict
- `status=WARN`
- `freqtrade_available=false`
- `strategy_import_ok=false`
- data manifest missing
- safety boundaries PASS

Current read-only preflight means the project is not blocked by a security violation, but it is not ready for real Freqtrade backtesting yet.

## Environment Isolation Recommendation
- Use a dedicated virtual environment or conda environment.
- Do not install Freqtrade into the base Python used for day-to-day development.
- Recommended environment name: `bollinger-ft-readiness`
- Keep API keys out of the repository.
- Keep exchange connectivity disabled.
- Keep `allow_real_backtest=False` as the checked-in default safety boundary until a future explicit task changes it.

## Suggested Python Version
- Use a Python version supported by the target Freqtrade release.
- Verify the exact supported version against current Freqtrade documentation before install.
- Do not assume the current system Python is automatically compatible.

## Non-Executing Setup Commands
These commands are documented for future use only. They are not executed in this task.

```powershell
python -m venv .venv-freqtrade
.venv-freqtrade\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install freqtrade
```

If a conda-based workflow is preferred, keep it equally isolated and avoid the base environment.

## Readiness Checks After Install
After Freqtrade is installed in the isolated environment, use read-only checks first:

```powershell
python -c "import freqtrade; print(freqtrade.__version__)"
python -c "from user_data.strategies.BollingerResonanceStrategy import BollingerResonanceStrategy; print('ok')"
python -m unittest bollinger_evolver.tests.test_backtest_preflight
```

These checks confirm package import readiness and strategy import readiness without running a backtest.

## Config Safety
- Use example or sanitized config only.
- Do not place real exchange credentials in repo files.
- No API keys.
- No live trading.
- No dry-run live wallet setup yet.
- No upload or webhook integration.
- Keep config secret fields as placeholders only.

## Data Manifest Requirements
Before any future real backtest attempt, provide a manifest path to preflight and ensure it passes the data quality gate.

Required expectations:
- required pairs are present
- required timeframes are present
- minimum candle count is satisfied
- gap ratio is within the accepted threshold
- invalid OHLC count is `0`
- manifest path is passed into `run_backtest_preflight(...)`

Until a manifest is provided and validated, preflight should remain `WARN`.

## Path to READY
1. Install Freqtrade in an isolated environment.
2. Confirm `freqtrade` import passes.
3. Confirm `BollingerResonanceStrategy` import passes.
4. Use only sanitized config and confirm config safety checks pass.
5. Provide a valid data manifest and pass the data quality gate.
6. Re-run preflight and confirm status becomes `READY`, or remains only `WARN` for non-critical issues.

## Still Forbidden
The following remain forbidden until a future explicit task authorizes a short controlled real-backtest step:

- Freqtrade backtesting
- Freqtrade hyperopt
- live trading
- exchange connection
- API keys
- secret injection

The current project phase is still mock-first and read-only for backtest readiness work.
