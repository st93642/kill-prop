#!/usr/bin/env bash
#
# kill-prop — one-file launcher for Linux / macOS
#
# Starts both the Python/FastAPI backend and the React/Vite frontend
# from the project root.  Backend runs on port 8000, frontend on 5173.
#
# Usage:
#   chmod +x kill-prop.sh
#   ./kill-prop.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── colours ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour
info()  { printf "${GREEN}[kill-prop]${NC} %s\n" "$*"; }
cmd()   { printf "${CYAN}  ▶${NC} %s\n" "$*"; }

# ── Python virtual environment ───────────────────────────────────────
VENV="$ROOT/backend/.venv"
if [ ! -f "$VENV/bin/activate" ]; then
    info "Creating Python virtual environment …"
    python3 -m venv "$VENV"
fi

info "Installing backend dependencies …"
"$VENV/bin/pip" install -q -r "$ROOT/backend/requirements.txt"

# ── Node dependencies ────────────────────────────────────────────────
if [ ! -d "$ROOT/frontend/node_modules" ]; then
    info "Installing frontend dependencies …"
    (cd "$ROOT/frontend" && npm install --silent)
fi

# ── Start both servers ───────────────────────────────────────────────
info "Starting backend (uvicorn on :8000) …"
"$VENV/bin/uvicorn" backend.main:app --reload --port 8000 --app-dir "$ROOT" &
BACKEND_PID=$!

info "Starting frontend (vite dev on :5173) …"
(cd "$ROOT/frontend" && npx vite --host) &
FRONTEND_PID=$!

# ── Trap & cleanup ───────────────────────────────────────────────────
cleanup() {
    info "Shutting down …"
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
    info "Done."
}
trap cleanup EXIT INT TERM

info "───────────────────────────────────────────────────────"
info "  Backend  →  http://localhost:8000"
info "  Frontend →  http://localhost:5173"
info "  API docs →  http://localhost:8000/docs"
info "───────────────────────────────────────────────────────"
info "Press Ctrl+C to stop both servers."

# Wait for either child to exit, then stop everything
wait