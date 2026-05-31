# STAGE-004A Commit 2 Staging Repair Report

## Repair Result
- repaired: true
- unstaged_file:
  - `bollinger_evolver/tests/test_runner_docs_static.py`
- reason:
  - moved to runner docs/runbook commit because it depends on runbook docs and README coverage that are not part of Commit 2

## Post-Repair Staged Files
Post-repair `git diff --cached --name-only` contains the Commit 2 core set only:

- `bollinger_evolver/`
  - package modules
  - evaluators
  - GA pipeline
  - gene space
  - runners
  - scoring
  - strategy helpers
  - core tests except `test_runner_docs_static.py`
- `config/ga_bollinger_resonance.json`
- `user_data/strategies/BollingerResonanceStrategy.py`
- `user_data/strategies/generated/.gitkeep`

Post-repair cached diff summary:

- staged file count: `60`
- `git diff --cached --stat`: `60 files changed, 10432 insertions(+)`

## Confirmed Exclusions
Confirmed not staged after repair:

- `README.md`
- `docs/bollinger_evolver_runner_runbook.md`
- `docs/architecture_baseline.md`
- `docs/commit_split_plan.md`
- `docs/workspace_hygiene_report.md`
- `docs/staging_preadd_audit.md`
- `docs/stage_003_commit1_staging_report.md`
- `.workflow/`
- `bollinger_evolver/tests/test_runner_docs_static.py`

## Cached Diff Check
- `git diff --cached --check`: pass

## Validation
- GeneTrader tests:
  - `$env:GENETRADER_CONFIG='ga.json.example'; python -m pytest tests -q`
  - result: `217 passed`
- Bollinger Evolver tests:
  - `python -m unittest discover bollinger_evolver.tests`
  - result: `231 OK (skipped=4)`
- compileall:
  - `python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests`
  - result: pass

## Recommendation
Commit 2 can proceed to `COMMIT-002` only if the intended scope is:

- Bollinger Evolver core package
- GA mock-first pipeline
- config and strategy template
- tests that are self-contained without runbook/docs files

`test_runner_docs_static.py` should stay out of Commit 2 and move with:

- `docs/bollinger_evolver_runner_runbook.md`
- any related `README.md` documentation update
- process/docs commit content
