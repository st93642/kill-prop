@echo off
REM kill-prop — one-file launcher for Windows
REM
REM Starts both the Python/FastAPI backend and the React/Vite frontend
REM from the project root.  Backend runs on port 8000, frontend on 5173.
REM
REM Usage:
REM   double-click kill-prop.bat   (opens two console windows)
REM   or run from a terminal:
REM     kill-prop.bat

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [kill-prop] Starting kill-prop ...

REM ── Load API keys from news.env (KEY=value format) ─────────────────
if exist "news.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in ("news.env") do (
        set "%%a=%%b"
    )
    echo [kill-prop] Loaded API keys from news.env
) else (
    echo [WARN] news.env not found — live fetching and LLM analysis disabled
)

REM ── Python virtual environment ─────────────────────────────────────
set VENV=backend\.venv
if not exist "%VENV%\Scripts\activate.bat" (
    echo [kill-prop] Creating Python virtual environment ...
    python -m venv "%VENV%"
)

echo [kill-prop] Installing backend dependencies ...
call "%VENV%\Scripts\pip.exe" install -q -r backend\requirements.txt

REM ── Optional LLM dependency (pre-built wheel, no compilation) ───────
if /i "%KILLPROP_INSTALL_LLM%"=="yes" (
    echo [kill-prop] Installing optional llama-cpp-python from pre-built wheel ...
    call "%VENV%\Scripts\pip.exe" install --only-binary :all: ^
        --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu ^
        -r backend\requirements-llm.txt
    if errorlevel 1 (
        echo [WARN] LLM wheel install failed. Continuing with rule-based extraction.
    )
) else (
    echo [kill-prop] Skipping optional LLM. Set KILLPROP_INSTALL_LLM=yes to enable.
)

REM ── Node dependencies ──────────────────────────────────────────────
if not exist "frontend\node_modules" (
    echo [kill-prop] Installing frontend dependencies ...
    cd frontend
    call npm install --silent
    cd ..
)

echo [kill-prop] Starting backend (uvicorn on :8000) ...
start "kill-prop-backend" "%VENV%\Scripts\uvicorn.exe" backend.main:app --reload --port 8000 --app-dir "%CD%"

echo [kill-prop] Starting frontend (vite dev on :5173) ...
start "kill-prop-frontend" cmd /c "cd /d "%CD%\frontend" && npx vite --host"

echo [kill-prop] ───────────────────────────────────────────────────────
echo [kill-prop]   Backend  →  http://localhost:8000
echo [kill-prop]   Frontend →  http://localhost:5173
echo [kill-prop]   API docs →  http://localhost:8000/docs
echo [kill-prop] ───────────────────────────────────────────────────────
echo [kill-prop] Close the server windows or press Ctrl+C to stop.
echo [kill-prop] Press any key to exit this launcher window ...
pause >nul