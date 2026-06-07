# STAGE-258 Do-not-stage Policy Review

## Verdict

PASS with one follow-up recommendation.

No forbidden files are staged because the cached area is empty. `.workflow/`
exists and is not ignored, so it remains the primary do-not-stage risk.

## Checked Items

### `.workflow/`

- Exists: yes
- Git status: untracked
- Git ignore status: not ignored
- Policy: DO NOT STAGE
- Recommendation: open a future hygiene task to add `.workflow/` to
  `.gitignore`, or continue excluding it explicitly from every staging command.

### `node_modules/`

- Exists: no at repository root
- Policy: DO NOT STAGE

### `frontend/node_modules/`

- Exists: yes
- Git ignore status: ignored
- Policy: DO NOT STAGE

### `frontend/dist/`

- Exists: yes
- Git ignore status: ignored
- Policy: DO NOT STAGE

### `.runtime/`

- Exists: yes
- Git ignore status: ignored
- Policy: DO NOT STAGE

### `user_data/data/`

- Exists: yes
- Observed content in this review: `.gitkeep`
- Git status: no unstaged changes reported for this path
- Policy: do not stage real market data or generated data

### `.env`

- Exists: no
- Policy: DO NOT STAGE

### `*.log`

- Scan result: no files found by `rg --files -g "*.log"`
- Policy: DO NOT STAGE

### Patch and bundle artifacts

- `*.bundle`: none found by file scan
- `*.patch`: none found by file scan
- `*.diff`: none found by file scan
- Policy: DO NOT STAGE in this repo

## Validation Commands

Executed:

```powershell
git status --short
git ls-files --others --exclude-standard
git status --short --ignored .workflow .runtime user_data/data frontend/dist node_modules frontend/node_modules
rg --files -g "*.log" -g "*.bundle" -g "*.patch" -g "*.diff"
rg --files -g ".env*" -g "*.pem" -g "*.key" -g "*secret*" -g "*token*"
```

Observed:

- `.workflow/` is visible as untracked.
- `.runtime/`, `frontend/dist/`, and `frontend/node_modules/` are ignored.
- Secret-like filename scan only found this redacted audit documentation file.

## Optional Follow-up Task

```text
STAGE-259 Add .workflow to .gitignore
```

Suggested scope:

- `.gitignore`
- optional static test or docs note

Boundary:

- no feature code
- no staging of `.workflow/`
- no deletion of workflow artifacts

## Final Safety Boundary

Do not stage:

- `.workflow/`
- `.runtime/`
- `user_data/data/` generated data
- `node_modules/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.env`
- logs
- patch or bundle artifacts
- real Freqtrade outputs
- exchange/API secrets
