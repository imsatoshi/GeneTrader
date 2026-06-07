# STAGE-262 Secret and Runtime Regression Scan Report

## Verdict

PASS for confirmed secret leakage. Runtime staging risk remains present because
`.workflow/` is untracked and visible.

```text
confirmed_secret_risk = 0
runtime_staging_risk = 1
```

## Commands

Required scan intent:

```powershell
git diff | Select-String -Pattern "api_key|apikey|secret|token|password|private_key|BEGIN|sk-|xoxb-|AKIA|default-key|AGENT_API_KEY" -CaseSensitive:$false
git status --short | Select-String -Pattern "\.env|node_modules|dist|\.runtime|user_data/data|\.workflow|\.log|\.pem|\.key" -CaseSensitive:$false
```

To avoid printing possible secret values, the first command was executed as a
redacted count and path-level review.

## Results

### Diff keyword scan

```text
git_diff_secret_pattern_hit_count = 6
```

Path-level redacted review found keyword references in modified files related
to forbidden-field checks, docs, routes, and styling. No raw credential value
was confirmed.

Files with keyword references in the modified tracked diff:

- `bollinger_evolver/tests/test_trading_system_adapter.py`
- `bollinger_evolver/trading_system_adapter.py`
- `docs/stage_162_custom_strategy_owner_review.md`
- `docs/trading_system_abstraction.md`
- `frontend/src/components/NavSidebar.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/styles.css`

### Runtime/status scan

Status scan hit:

```text
.workflow/
```

No staged files are present. `.workflow/` must remain unstaged.

### Filename scan

No files were found for:

- `.env*`
- `*.pem`
- `*.key`
- `*.log`
- `*.bundle`
- `*.patch`
- `*.diff`

## Interpretation

- Keyword hits are not automatically secret leaks; they include expected
  guardrail and redaction references.
- `.workflow/` is the active regression risk because it is untracked and not
  ignored.
- The cached area is empty, so no secret or runtime artifact is staged.

## Required Follow-up Before Any Commit

Run:

```powershell
git diff --cached --name-only | Select-String -Pattern "\.workflow|\.runtime|user_data/data|node_modules|dist|\.env|\.log" -CaseSensitive:$false
git diff --cached --check
```

Expected result:

```text
no forbidden staged path output
```

## Safety Boundary

No real Freqtrade, download-data, hyperopt, exchange API, deployment, rollback,
push, staging, or commit was performed.
