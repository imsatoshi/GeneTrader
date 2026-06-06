# Frontend Dashboard

This dashboard is launched as a local Vite app from the `frontend` package.
The helper scripts are thin wrappers around the existing npm scripts.

## Launch

PowerShell:

```powershell
.\scripts\start_frontend.ps1
```

CMD:

```cmd
scripts\start_frontend.cmd
```

POSIX shell:

```sh
scripts/start_frontend.sh
```

## Checks

```powershell
cd frontend
npm.cmd test
npm.cmd run build
cd ..
```

The launch helpers do not read credentials or start services outside the
frontend package.
