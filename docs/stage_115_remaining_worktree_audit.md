# STAGE-115 Remaining Working Tree Audit

## Current Status

- branch: `main`
- cached: empty
- latest commits:
  - `9cc5fd4` STAGE-114 Add real Freqtrade adapter skeleton with sandbox gate
  - `08f3b06` STAGE-113 Add frontend launch helper scripts
  - `77a55a3` STAGE-112 Add legacy backtest/downloader E2E mock validation
  - `d02dae9` STAGE-111 Add repository agent guardrails
  - `28fb8a0` Add frontend run explorer for GA experiments

Inspection commands run:

```powershell
git status --short
git diff --name-only
git ls-files --others --exclude-standard
git diff --cached --name-only
git diff --cached --check
git ls-files --stage -- data/__pycache__/WechatIMG319.jpg
git log --oneline -- data/__pycache__/WechatIMG319.jpg
git grep -n "WechatIMG319" -- . ':!data/__pycache__/WechatIMG319.jpg'
```

No staging, commit, reset, stash, clean, real Freqtrade, download-data, deployment, rollback, or exchange/API action was run.

## Remaining Files

### Keep Unstaged

- `.workflow/current-project-audit/*`
  - Generated audit workspace and orchestration artifacts.
  - Default action: keep unstaged.
  - Candidate follow-up: add `.workflow/` to `.gitignore` in a separate ignore-only stage if the project wants this convention.

- `bollinger_evolver/freqtrade_controlled_stub.py`
- `bollinger_evolver/freqtrade_sandbox_executor.py`
- `bollinger_evolver/tests/test_freqtrade_controlled_stub.py`
- `bollinger_evolver/tests/test_freqtrade_sandbox_executor.py`
  - These appear to be no-process or controlled sandbox prototypes.
  - They still need STAGE-116 review because they are outside the already committed STAGE-114 disabled real adapter boundary.
  - Keep unstaged until reviewed against fail-closed, no subprocess, no exchange/API, no sensitive config, and safe output-root requirements.

- `bollinger_evolver/freqtrade_single_genome_smoke.py`
- `bollinger_evolver/freqtrade_small_batch_queue.py`
- `bollinger_evolver/tests/test_freqtrade_single_genome_smoke.py`
- `bollinger_evolver/tests/test_freqtrade_small_batch_queue.py`
  - These depend on the real execution prototype and contain opt-in environment gates and smoke/batch concepts.
  - Keep unstaged until STAGE-116 decides whether they are useful as disabled scaffolding or should be discarded.

### Candidate Commit

- `docs/stage_014_offline_data_requirements_audit_report.md`
- `docs/stage_109_e2e_mock_pipeline_audit_report.md`
- `docs/stage_110_do_not_stage_cleanup_audit.md`
  - Candidate for a docs-only STAGE-119 commit after review.
  - Static scan found safety wording and placeholders, not raw credential values.

- `start_frontend.bat`
  - Candidate for STAGE-118 if a root-level launcher is desired.
  - Current content only invokes `scripts/start_frontend.ps1`.
  - It is functionally redundant with the committed `scripts/start_frontend.cmd`.

### Candidate Ignore

- `.workflow/`
  - Generated local workflow artifacts should normally stay out of commits.
  - `.gitignore` currently ignores `.runtime/`, cache files, node modules, frontend dist, and runtime data, but not `.workflow/`.

### Candidate Cleanup

- `data/__pycache__/WechatIMG319.jpg`
  - Current state: tracked deletion.
  - `git ls-files --stage` confirms it is tracked as a regular file.
  - `git log --oneline -- data/__pycache__/WechatIMG319.jpg` shows it was introduced in `db429a6 edit README`.
  - `git grep` only found references in prior audit planning docs, not application code.
  - Candidate for STAGE-117 deletion-only cleanup commit, pending owner approval.

### Requires Manual Approval

- `bollinger_evolver/freqtrade_real_execution.py`
- `bollinger_evolver/tests/test_freqtrade_real_execution.py`
  - The draft contains an actual `subprocess.run` path guarded by policy/env/approval checks.
  - It must not be committed into the current mock-first mainline without explicit owner approval and a dedicated real-execution safety stage.
  - STAGE-114 already committed a disabled skeleton boundary, so this draft is not required for the current fail-closed adapter baseline.

## Risk Notes

- Classification: MEDIUM_RISK for the remaining working tree because untracked real-execution draft code exists, even though it is not staged and was not run.
- The current committed mainline remains fail-closed for real Freqtrade adapter execution.
- No cached changes are present.
- No node modules, frontend dist, runtime output, backtest output, or real market data is staged.
- The tracked cache image deletion is likely cleanup-safe, but should remain a separate deletion-only decision.

## Verdict

PASS / remaining working tree classified.

Ready for targeted cleanup stages:

1. STAGE-116 Freqtrade stub / real execution draft review.
2. STAGE-117 Tracked binary cleanup decision.
3. STAGE-118 Root frontend launcher review.
4. STAGE-119 Docs hold commit.
5. STAGE-120 Post-commit mainline audit.
