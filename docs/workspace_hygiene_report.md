# Workspace Hygiene Report

## Executive Summary

- commit_readiness: `NEEDS_REVIEW`
- key risks:
  - mixed scope in one worktree: upstream GeneTrader baseline/security fixes, large untracked `bollinger_evolver/`, docs, and workflow audit artifacts are all present together
  - `.workflow/` is untracked and not ignored; this needs an explicit keep-or-drop decision before commit
  - `.runtime/` was not repo-locally ignored before this task; a minimal `.gitignore` patch was added
  - sensitive-field scan found many keyword hits, but they are currently dominated by placeholders, tests, docs, and code paths that reference credential field names rather than live values
- recommended commit split:
  1. baseline/test fixture/security
  2. Bollinger Evolver core modules
  3. runner/CLI/report docs
  4. workflow audit docs

## Git Status Summary

- branch: `main...origin/main`
- modified files:
  - `.gitignore`
  - `README.md`
  - `data/downloader.py`
  - `scripts/workflow.py`
  - `strategy/backtest.py`
  - `tests/test_backtest.py`
  - `tests/test_evaluation.py`
  - `tests/test_workflow.py`
  - `user_data/example.json`
- untracked files/directories:
  - `.workflow/`
  - `bollinger_evolver/`
  - `config/ga_bollinger_resonance.json`
  - `docs/architecture_baseline.md`
  - `docs/bollinger_evolver_runner_runbook.md`
  - `docs/test_baseline.md`
  - `tests/test_data_downloader.py`
- ignored files summary:
  - cache directories under `__pycache__/`
  - `.pytest_cache/`
  - generated strategy output under `user_data/strategies/`
  - other repo-local ignored runtime paths already present in `.gitignore`, such as `results/*`, `bestgenerations/*`, `candidates/*`, and temp config files

## File Classification

### 1. Source code to commit

- `bollinger_evolver/`
  - new mock-first Bollinger Evolver package, including `ga/`, `gene_space/`, `runners/`, `scoring/`, `strategies/`, `reports/`, `utils/`
- `data/downloader.py`
- `scripts/workflow.py`
- `strategy/backtest.py`
- `config/ga_bollinger_resonance.json`

### 2. Tests to commit

- `bollinger_evolver/tests/`
- `tests/test_backtest.py`
- `tests/test_evaluation.py`
- `tests/test_workflow.py`
- `tests/test_data_downloader.py`

### 3. Docs to commit

- `README.md`
- `docs/architecture_baseline.md`
- `docs/bollinger_evolver_runner_runbook.md`
- `docs/test_baseline.md`

### 4. Config examples to commit

- `user_data/example.json`
- `config/ga_bollinger_resonance.json`

### 5. Generated artifacts / runtime outputs

- `user_data/strategies/` generated strategy files are ignored
- `.pytest_cache/` is ignored
- `__pycache__/` trees are ignored
- `.runtime/` is now repo-locally ignored by this task
- tracked historical runtime-style content still exists in the upstream repo, for example under `daily_results/`; it is not part of this task and was not modified

### 6. Workflow audit artifacts

- `.workflow/current-project-audit/`
  - `plan.md`
  - `orchestration.md`
  - `final-report.md`
  - `state.json`
  - `packets/`
  - `results/`

These look intentional and useful for audit traceability, but they are not ignored and do not belong in the same commit as core code unless you explicitly want them versioned.

### 7. Ignored files

- `.pytest_cache/`
- `__pycache__/`
- `user_data/strategies/`
- runtime directories already covered by `.gitignore`
- `.runtime/` after this task's minimal `.gitignore` patch

### 8. Needs manual review

- `.workflow/`
  - decide whether to keep as permanent audit evidence or leave out of commits
- `docs/architecture_baseline.md`
  - valid doc artifact, but likely better in a docs-only commit
- `README.md`
  - small doc touch, but mixed into a larger security/runtime change set
- `openclaw_skill/genetrader`, `agent_api/`, `monitoring/`, `config/settings.py`, `scripts/restart_freqtrade.py`
  - not modified in this task, but they contain credential-key references and should stay on the manual review list for future security work

## Sensitive Field Scan

- scan command:
  - `rg -n --hidden --glob '!*.pyc' --glob '!__pycache__/**' --glob '!.git/**' "api_key|secret|password|private_key|mnemonic|webhook|jwt|token" .`
- total matches: `293`
- placeholder matches: `147`
  - examples: `ga.json.example`, `user_data/example.json`, docs examples, runbook text, test fixtures, redaction tests
- redacted matches: `0`
- real risk matches: `0`
  - no clear live credential value was identified in the current scan
- unknown matches: `146`
  - mostly code paths that define, pass, redact, or validate credential field names in `config/`, `scripts/`, `monitoring/`, `agent_api/`, `openclaw_skill/`, and non-test `bollinger_evolver/`
- recommended actions:
  - do not treat keyword hits as secrets by default; most are schema names, tests, or placeholders
  - manually spot-check future commits touching credential-bearing code paths
  - keep sample/example files on obvious placeholders only
  - avoid copying `.workflow/` or future runtime artifacts into commits without a review pass

No real secret value is reproduced in this report. Example/sample values should remain placeholders such as `<REDACTED>` or `CHANGE_ME_*_PLACEHOLDER`.

## .gitignore Review

- current status:
  - repo already ignored many runtime outputs: generated strategies, results, best generations, candidates, temp configs
  - repo-local ignore did not explicitly cover `.runtime/`
  - `.pytest_cache/` appeared ignored in practice, but not repo-locally documented
  - `.workflow/` is not ignored
- missing ignore patterns found:
  - `.runtime/`
  - `.pytest_cache/`
- recommended additions:
  - keep `.runtime/` ignored because it is the default runner output root
  - keep `.pytest_cache/` ignored for repo-local portability
  - do not automatically ignore `.workflow/` until you decide whether those audit artifacts should be committed or kept ephemeral
- whether this task changed `.gitignore`:
  - yes
  - added `.runtime/`
  - added `.pytest_cache/`

## Recommended Commit Split

### 1. baseline/test fixture/security

- `.gitignore`
- `data/downloader.py`
- `scripts/workflow.py`
- `strategy/backtest.py`
- `tests/test_backtest.py`
- `tests/test_evaluation.py`
- `tests/test_workflow.py`
- `tests/test_data_downloader.py`
- `user_data/example.json`

### 2. Bollinger Evolver core modules

- `bollinger_evolver/`
- `config/ga_bollinger_resonance.json`

### 3. runner/CLI/report docs

- `README.md`
- `docs/test_baseline.md`
- `docs/bollinger_evolver_runner_runbook.md`

### 4. workflow audit docs

- `.workflow/current-project-audit/`
- `docs/architecture_baseline.md`

## Verification Commands

- `$env:GENETRADER_CONFIG='ga.json.example'; python -m pytest tests -q`
  - result: `217 passed`
- `python -m unittest discover bollinger_evolver.tests`
  - result: `231 OK (skipped=4)`
- `python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests`
  - result: passed

## Final Recommendation

- ready to commit?
  - `NEEDS_REVIEW`
- what to review manually first?
  - decide whether `.workflow/` belongs in version control
  - confirm `docs/architecture_baseline.md` should ship with this change set or in a later docs-only commit
  - stage runtime/security baseline fixes separately from the full `bollinger_evolver/` tree
  - keep the commit boundary clear: upstream baseline/security fixes first, then new module introduction, then runner/docs, then optional audit artifacts

The workspace is technically healthy enough to prepare commits: tests pass, compile checks pass, and no clear live secret was found. It is not yet clean enough for a single undifferentiated commit.
