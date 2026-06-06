# STAGE-087 Security Re-audit Report

## Scope

Agent API, deployment fail-closed behavior, rollback behavior, legacy Freqtrade
subprocess paths, adaptive Docker runtime defaults, validation environment, and
generated dependency boundaries.

No live trading, deployment, rollback, download-data, real Freqtrade process, or
exchange API execution was run during this re-audit.

## Repository Location Check

- git root: `D:/ReceiveBackup/byhdo-workstation-Core-20260605-155346/staging/User/Documents-C/遗传算法布林交易策略`
- branch: `main`
- remote: `https://github.com/imsatoshi/GeneTrader.git`
- pasted C-drive path check: `C:\Users\byhdo_ocup4f5\Documents\遗传算法布林交易策略` was not present in this environment.
- staged set: unchanged 13-file readiness/data-prep bundle:
  - `bollinger_evolver/__init__.py`
  - `bollinger_evolver/data_gate.py`
  - `bollinger_evolver/data_manifest.py`
  - `bollinger_evolver/preflight.py`
  - `bollinger_evolver/tests/test_backtest_preflight.py`
  - `bollinger_evolver/tests/test_data_gate.py`
  - `bollinger_evolver/tests/test_data_manifest.py`
  - `bollinger_evolver/tests/test_freqtrade_readiness_docs_static.py`
  - `bollinger_evolver/tests/test_offline_data_plan_docs_static.py`
  - `bollinger_evolver/tests/test_package_exports.py`
  - `docs/freqtrade_environment_readiness_plan.md`
  - `docs/offline_data_acquisition_plan.md`
  - `docs/offline_data_manifest_gate.md`

## Findings Addressed

### Agent API

PASS.

- `default-key` fallback removed.
- API keys are accepted from `X-API-Key` headers only.
- Empty, weak, and placeholder API keys fail closed.
- Default host is `127.0.0.1`.
- CORS is allowlist-based, not wildcard.
- Public health endpoint returns only health metadata.
- POST mutation routes remain authenticated and permission-checked.
- Internal exceptions return a generic client error.

### Deployment

PASS.

- Deployment requiring approval fails closed when no approval callback is set.
- Adaptive optimization no longer auto-approves by improvement threshold.
- StrategyDeployer records that shadow trading and gradual rollout are not
  executed by that component when configured but not implemented.
- `deploy_file` is not called when required approval is missing.

### Rollback

PASS.

- Automatic rollback is disabled by default.
- Rollback confirmation is required by default.
- Missing confirmation callback fails closed.
- Missing deploy callback records a failed rollback and does not switch active
  version.
- Failed deploy callback does not switch active version.
- Added `tests/test_rollback_manager.py`.

### Legacy Freqtrade Paths

PASS.

- `strategy/backtest.py` and `data/downloader.py` subprocess paths are disabled
  unless `GENETRADER_ENABLE_LEGACY_FREQTRADE_EXECUTION=1` is explicitly set.
- Legacy command validation rejects unexpected subcommands and live/hyperopt
  style tokens.
- Secret-like values and local paths are redacted in logs.
- Existing tests use mocked subprocesses only.

### Docker / Runtime

PASS.

- Compose no longer contains `default-key`.
- Compose requires `${AGENT_API_KEY:?AGENT_API_KEY is required}`.
- Published API port is bound to `127.0.0.1`.
- Compose references existing `Dockerfile`.
- API service command is not `--check-only`.
- Added `tests/test_adaptive_compose_static.py`.

### Validation Environment

PASS.

- Installed local Python requirements from `requirements.txt`.
- Installed frontend dependencies with `npm install`.
- `.gitignore` excludes `node_modules/`, `frontend/node_modules/`,
  `frontend/dist/`, and `frontend/tsconfig.tsbuildinfo`.
- `git status --short | Select-String "node_modules|frontend/dist|tsconfig.tsbuildinfo"`
  returned no matches.

## Validation Results

- `python -m pytest tests\test_rollback_manager.py -q`: 4 passed.
- `python -m pytest tests\test_adaptive_compose_static.py -q`: 5 passed.
- `python -m pytest tests\test_agent_api.py tests\test_deployment.py tests\test_backtest.py tests\test_data_downloader.py -q`: 69 passed, 4 subtests passed.
- `npm.cmd test`: 11 files passed, 28 tests passed.
- `npm.cmd run build`: passed with Vite chunk-size warning only.
- `$env:GENETRADER_CONFIG='ga.json.example'; python -m pytest tests -q`: 235 passed, 4 subtests passed.
- `python -m unittest discover -s bollinger_evolver\tests`: 722 passed, 9 skipped.
- `python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests`: passed.
- `git diff --cached --check`: passed.
- `git diff --check`: passed with line-ending warnings only.

## Boundary Check

- no trading executed
- no deployment executed
- no rollback executed
- no download-data executed
- no real Freqtrade process executed
- no exchange/API connection executed
- no secrets printed in final report
- dependency output directories ignored
- staged readiness/data-prep bundle remained unchanged

## Remaining Open Risks

- `git diff --check` reports line-ending normalization warnings on Windows; no
  whitespace errors were reported.
- The frontend production build warns that one generated chunk exceeds 500 kB.
  This is a performance concern, not a security blocker for STAGE-087.
- The worktree still contains many pre-existing modified and untracked files.
  Staging should remain deliberate and split by task.

## Verdict

PASS.

Security hardening pass completed; rollback and adaptive runtime contracts were
re-audited and covered by focused tests. Proceed to staging only with an
explicit file list so the existing staged readiness bundle is not polluted.
