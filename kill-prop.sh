#!/usr/bin/env bash
#
# kill-prop — all-in-one launcher for Linux / macOS
#
# Bundles everything: prerequisite checks, dependency installation,
# backend start, frontend start, and readiness verification.
#
# Usage:
#   chmod +x kill-prop.sh
#   ./kill-prop.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── Colours ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
info()  { printf "${GREEN}[kill-prop]${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
fail()  { printf "${RED}[ERROR]${NC} %s\n" "$*"; exit 1; }
cmd()   { printf "${CYAN}  ▶${NC} %s\n" "$*"; }

# ── Load API keys from news.env ──────────────────────────────────────
if [ -f "$ROOT/news.env" ]; then
    export NEWSAPI_KEY=$(cat "$ROOT/news.env" | tr -d '\n\r' | xargs)
    info "Loaded NEWSAPI_KEY from news.env"
else
    warn "news.env not found — live API fetching disabled"
fi

# ── Prerequisite checks ──────────────────────────────────────────────
info "Checking prerequisites …"

command -v python3 >/dev/null 2>&1 || fail "python3 is required but not found."
command -v node    >/dev/null 2>&1 || fail "node is required but not found."
command -v npm     >/dev/null 2>&1 || fail "npm is required but not found."

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
NODE_VERSION=$(node --version 2>&1 | grep -oP '\d+' | head -1)

if [ "$(echo "$PYTHON_VERSION < 3.10" | bc -l 2>/dev/null || echo 1)" = "1" ]; then
    fail "Python 3.10+ required (found $PYTHON_VERSION)"
fi
if [ "$NODE_VERSION" -lt 18 ] 2>/dev/null; then
    fail "Node.js 18+ required (found $(node --version))"
fi

info "Prerequisites OK — Python $PYTHON_VERSION, Node $(node --version)"

# ── Backend Python virtual environment & dependencies ────────────────
VENV="$ROOT/backend/.venv"
if [ ! -f "$VENV/bin/activate" ]; then
    info "Creating Python virtual environment …"
    python3 -m venv "$VENV"
fi

info "Installing backend Python dependencies …"
cmd "core packages (fastapi, uvicorn, pydantic, huggingface_hub …)"
"$VENV/bin/pip" install --quiet --upgrade pip 2>/dev/null || true
"$VENV/bin/pip" install --quiet \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.29.0" \
    "pydantic>=2.0.0" \
    "pydantic-settings>=2.0.0" \
    "huggingface_hub" 2>&1 | tail -1 || fail "Failed to install core backend packages."

# ── llama-cpp-python (optional — for LLM extraction) ─────────────────
LLM_INSTALL=${KILLPROP_INSTALL_LLM:-no}
if [ "$LLM_INSTALL" = "yes" ]; then
    info "Installing optional LLM dependency (llama-cpp-python) …"
    warn "This takes several minutes as it compiles from source."
    warn "Set KILLPROP_INSTALL_LLM=yes to include it, or omit to skip."
    if "$VENV/bin/pip" install "llama-cpp-python" 2>&1 | tail -3; then
        info "llama-cpp-python installed — LLM extraction available."
    else
        warn "llama-cpp-python installation failed."
        warn "The app will work without it — only rule-based extraction will be used."
    fi
else
    info "Skipping optional LLM dependency (llama-cpp-python)."
    info "Set KILLPROP_INSTALL_LLM=yes to enable LLM-based claim extraction."
fi

info "Backend dependencies installed."

# ── Frontend Node.js dependencies ────────────────────────────────────
FRONTEND_DIR="$ROOT/frontend"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "Installing frontend dependencies …"
    cmd "npm install"
    (cd "$FRONTEND_DIR" && npm install --silent 2>&1) || fail "npm install failed."
    info "Frontend dependencies installed."
else
    info "Frontend dependencies already installed."
fi

# ── Start backend server ─────────────────────────────────────────────
info "Starting backend (uvicorn on :8000) …"
"$VENV/bin/uvicorn" backend.main:app --reload --port 8000 --app-dir "$ROOT" &
BACKEND_PID=$!

# Wait for backend to be ready
info "Waiting for backend to be ready …"
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
        info "Backend is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        fail "Backend failed to start within 30 seconds."
    fi
    sleep 1
done

# ── Start frontend dev server ────────────────────────────────────────
info "Starting frontend (vite dev on :5173) …"
(cd "$ROOT/frontend" && npx vite --host) &
FRONTEND_PID=$!

# Wait for frontend to be ready
info "Waiting for frontend to be ready …"
for i in $(seq 1 30); do
    if curl -sf http://localhost:5173 >/dev/null 2>&1; then
        info "Frontend is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "Frontend did not respond within 30 seconds. It may still be starting."
    fi
    sleep 1
done

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
info "System is running. Press Ctrl+C to stop both servers."

# Wait for either child to exit, then stop everything
wait