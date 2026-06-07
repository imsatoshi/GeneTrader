$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptRoot "..")

Push-Location $RepoRoot
try {
    python -m pytest tests -q
    python -m unittest discover -s bollinger_evolver/tests

    Push-Location frontend
    try {
        npm.cmd test -- RunExplorerCustomPage RunComparisonPage RiskDashboardPage MockDashboardPage
        npm.cmd test
        npm.cmd run build
    }
    finally {
        Pop-Location
    }

    python -m compileall bollinger_evolver genetic_algorithm config user_data/strategies strategy data scripts tests
    git -c safe.directory="$RepoRoot" diff --check
    git -c safe.directory="$RepoRoot" diff --cached --check
}
finally {
    Pop-Location
}
