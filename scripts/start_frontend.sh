#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
FRONTEND_DIR="$REPO_ROOT/frontend"
HOST="${FRONTEND_HOST:-127.0.0.1}"
PORT="${FRONTEND_PORT:-5173}"

cd "$FRONTEND_DIR"

if [ ! -d node_modules ]; then
  echo "[frontend-launcher] frontend dependencies missing; run npm install in $FRONTEND_DIR first" >&2
  exit 1
fi

exec npm run dev -- --host "$HOST" --port "$PORT" --strictPort
