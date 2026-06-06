# Repository Agent Guardrails for GeneTrader

This file describes how Codex and other local agents may reason about the
GeneTrader adaptive optimization system. It is documentation only. It must not
be treated as approval to run live trading, deployment, rollback, download, or
real Freqtrade execution.

## Default Safety Mode

- Prefer mock-first and read-only workflows.
- Keep real trading, real Freqtrade runs, deployment, rollback, and data
  download paths disabled unless the user gives explicit approval for the exact
  command and target.
- Do not write runtime outputs to repository root, `.runtime`, `user_data/data`,
  frontend build output, or dependency directories.
- Do not print confidential header values, exchange material, local config
  values, or `.env` contents.
- When uncertain, fail closed and report what approval or config is missing.

## Agent API Boundary

Agent API startup must match the hardened contract from STAGE-087 and STAGE-093:

- The API key must be supplied explicitly at startup.
- Placeholder or empty values are invalid.
- The default host must be `127.0.0.1`.
- Public binding such as `0.0.0.0` requires explicit user approval.
- CORS must use an allowlist.
- Wildcard CORS is not acceptable for local agent control routes.
- Auth material is accepted through the `X-API-Key` header only.
- Auth material in URL query strings is forbidden.
- Public health endpoints may return health metadata only.
- POST routes that mutate optimization, deployment, approval, rejection, or
  rollback state must require auth and permission checks.

Example status request with a redacted value:

```powershell
curl.exe -H "X-API-Key: <REDACTED_VALUE>" http://127.0.0.1:8090/api/v1/status
```

The example above is illustrative. Do not run it unless the local API is
already intentionally started with an approved header value.

## Read-only Performance Checks

Checking strategy health may be done only in read-only mode:

```powershell
python run_adaptive.py --strategy GeneTrader --check-only
```

Allowed output:

- health status
- degradation score
- alerts
- recommendation text
- current metrics with no confidential values

Disallowed behavior:

- starting an optimizer
- deploying a strategy
- rolling back a strategy
- calling an exchange
- writing live runtime files

## Optimization Boundary

Optimization requests must be mock-first or explicitly approved. A degradation
score alone is not approval.

Before any optimization that could affect deployment:

- verify minimum trade count and cooldown conditions
- confirm the intended strategy name
- confirm the mode is dry-run or mock
- confirm no real exchange connection will be used
- record the validation command that was run

If approval is absent, the agent must report the recommendation and stop.

## Deployment Approval Boundary

Deployment is fail-closed:

- Missing approval callback means no deployment.
- Missing user approval means no deployment.
- Shadow or rollout behavior must not be claimed unless the component actually
  performed and verified it.
- Deployment state before and after the attempted action must be inspectable.
- Any deployment command must be scoped to the approved strategy and approved
  target only.

Required approval evidence before deploy:

- request id
- strategy id or version id
- expected deployment mode
- validation summary
- explicit user approval in the current workflow

Reject deployment when:

- validation is absent
- improvement is unclear
- drawdown increases beyond the accepted bound
- win rate drops materially
- shadow validation is absent when required
- approval is missing

## Rollback Boundary

Rollback is also fail-closed:

- Automatic rollback is disabled unless explicitly configured and approved.
- Confirmation is required before switching an active version.
- Missing confirmation callback means no rollback.
- Failed deploy callback must not switch active version.
- Rollback result must record whether active state changed.

Before rollback:

- identify active version
- identify target version
- record reason
- confirm the intended mode
- require user confirmation

After rollback:

- verify active version state
- report success or failure
- report whether any state changed
- avoid printing confidential config values

## Legacy Freqtrade Boundary

Legacy backtest and data download subprocess paths remain disabled by default.
Do not enable them during ordinary audits or mock pipeline work.

Allowed current work:

- command specification builders
- sandbox config builders
- fake runners
- fixture parsers
- mock GA runs
- artifact export
- local JSONL registry writes to explicit allowed directories

Disallowed without explicit approval:

- real Freqtrade process execution
- data download
- exchange connection
- live or production mode
- writing to `user_data/data`
- writing to repository root

## Frontend Boundary

Frontend pages must use fixtures or read-only adapters unless the user asks for
backend integration.

Frontend launch helpers may run:

- `npm.cmd test`
- `npm.cmd run build`
- `npm.cmd run dev`

Frontend launch helpers must not run backend trading, deployment, rollback, or
Freqtrade commands.

## Commit And Staging Boundary

- Stage files explicitly by path.
- Keep runtime output, dependency directories, frontend build output, and local
  workflow artifacts out of feature commits.
- Keep `.workflow/` unstaged unless the user asks for a workflow artifact commit.
- Keep tracked cache cleanup separate from feature work.
- Commit guardrail docs separately from code.

## Validation Baseline

For local safety checks:

```powershell
$env:GENETRADER_CONFIG='ga.json.example'
python -m pytest tests -q
python -m unittest discover -s bollinger_evolver\tests
python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests
```

For frontend checks:

```powershell
cd frontend
npm.cmd test
npm.cmd run build
cd ..
```

## Final Rule

This repository is currently being advanced through mock-first, audit-safe
stages. If a request would cross into real trading, real Freqtrade execution,
deployment, rollback, external network use, or confidential material handling,
stop and ask for explicit approval before proceeding.
