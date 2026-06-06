# STAGE-110 Do-not-stage Cleanup Audit

## Scope

This audit reviews the remaining dirty working tree items that should not be mixed into product, frontend, GA, security, or docs commits without an explicit follow-up decision.

Reviewed items:

- `.workflow/`
- `AGENTS.md`
- `data/__pycache__/WechatIMG319.jpg` tracked deletion
- `docs/stage_014_offline_data_requirements_audit_report.md`

No staging, deletion, restore, cleanup, or commit was performed for this stage.

## Current Git Evidence

`git status --short` still reports:

- `D data/__pycache__/WechatIMG319.jpg`
- `?? .workflow/`
- `?? AGENTS.md`
- `?? docs/stage_014_offline_data_requirements_audit_report.md`

Additional unrelated untracked future-stage files remain present and should stay out of this cleanup decision.

## Item Review

### `.workflow/`

Classification: DO_NOT_STAGE

Evidence:

- Contains local audit workflow artifacts under `.workflow/current-project-audit/`.
- Files include `plan.md`, `state.json`, packet files, packet results, and `final-report.md`.
- `state.json` marks the workflow as complete and records command history.
- Static scan found only placeholder/safety wording, not raw secrets.
- `git check-ignore` did not show `.workflow/` as ignored.

Decision:

- Do not stage `.workflow/` by default.
- Treat it as local process output.
- Consider adding `.workflow/` to `.gitignore` in a future hygiene commit if the team decides workflow artifacts should remain ephemeral.

### `AGENTS.md`

Classification: HOLD_FOR_SEPARATE_REVIEW

Evidence:

- The file is a project-level Codex/GeneTrader guide.
- It includes adaptive optimization, Agent API, deployment approval/rejection, rollback guidance, and `X-API-Key: <API_KEY>` placeholders.
- It does not appear to contain raw secrets, but it describes sensitive operational paths.

Decision:

- Do not stage with cleanup or feature work.
- If kept, submit only as a separate STAGE-111 guardrails commit.
- Before STAGE-111, revise wording so all optimization/deployment/rollback actions are explicitly fail-closed, mock-first/dry-run by default, and require user approval for any live or real execution path.

### `data/__pycache__/WechatIMG319.jpg` tracked deletion

Classification: HOLD_FOR_EXPLICIT_CLEANUP_COMMIT

Evidence:

- `git ls-files -s` shows the path is tracked in HEAD.
- `git cat-file -t` reports a blob and `git cat-file -s` reports `169607` bytes.
- `git log -- data/__pycache__/WechatIMG319.jpg` shows it was added in commit `db429a6 edit README`.
- The path is inside a Python cache directory, but the filename resembles a WeChat image, not a Python artifact.
- Current directory listing contains only `downloader.cpython-311.pyc`; the image file is absent locally.

Decision:

- Do not stage the deletion in unrelated commits.
- This likely represents an accidental historical binary tracked under a cache path.
- Recommended follow-up: create a dedicated cleanup commit after user confirmation, for example `Remove accidental tracked cache image`.
- Optional future hygiene: verify whether history rewrite is needed only if the file is sensitive. Current audit did not inspect image contents and did not confirm sensitivity.

### `docs/stage_014_offline_data_requirements_audit_report.md`

Classification: SAFE_DOCS_HOLD

Evidence:

- The report is a read-only audit report for offline data requirements work.
- It records validation and boundary checks.
- Static scan found only section headings and safety claims such as `Secret Scan` and "No real API key...".

Decision:

- Safe to keep unstaged for a future docs-only commit.
- Do not mix with code or frontend commits.

## Recommended Task Cards

### STAGE-111: Add repository agent guardrails

Scope:

- `AGENTS.md`

Acceptance criteria:

- No raw secrets.
- Fail-closed language for real execution, live trading, deployment, rollback, and Agent API use.
- Explicit mock-first/dry-run default.
- Clear rule that Codex must not run real trading/deployment/rollback commands without explicit user approval.

Verification:

- Static scan for secret placeholders and dangerous command wording.
- `git diff --cached --check`.

### STAGE-112: Workspace hygiene ignore update

Scope:

- `.gitignore`

Acceptance criteria:

- Decide whether `.workflow/` should be ignored.
- Do not hide tracked files unintentionally.
- Do not stage runtime outputs.

Verification:

- `git check-ignore -v .workflow/current-project-audit/state.json`.
- `git diff --cached --check`.

### STAGE-113: Remove accidental tracked cache image

Scope:

- `data/__pycache__/WechatIMG319.jpg`

Acceptance criteria:

- User confirms deletion should be committed.
- Commit contains only the tracked image removal, or a tightly scoped cache cleanup.
- No unrelated dirty working tree files are staged.

Verification:

- `git diff --cached --name-status`.
- `git diff --cached --check`.

### STAGE-114: Submit deferred audit docs

Scope:

- `docs/stage_014_offline_data_requirements_audit_report.md`
- `docs/stage_109_e2e_mock_pipeline_audit_report.md`
- `docs/stage_110_do_not_stage_cleanup_audit.md`

Acceptance criteria:

- Docs-only commit.
- No code, runtime output, frontend dist, node_modules, or cache files.

Verification:

- `git diff --cached --name-only`.
- `git diff --cached --check`.

## Verdict

PASS / cleanup audit complete.

No do-not-stage item should be added to the next feature commit.
