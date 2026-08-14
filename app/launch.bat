@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Fabric Model AI Readiness - Launcher
cd /d "%~dp0"

echo ===============================================
echo   Fabric Model AI Readiness
echo ===============================================
echo.

set VITE_PORT=5173
set VITE_WAIT_LIMIT=60

:: -------------------------------------------------------
:: 0. Preflight -- fail loudly and early with a fix to apply
:: -------------------------------------------------------
echo [check] Verifying prerequisites...

where node >nul 2>&1
if errorlevel 1 call :fail "Node.js is not installed or not on PATH." "Install the LTS build from https://nodejs.org and reopen this window."

where npm >nul 2>&1
if errorlevel 1 call :fail "npm is not on PATH." "Reinstall Node.js from https://nodejs.org -- npm ships with it."

:: python.ts spawns the backend with 'py' on Windows, so check that exact launcher.
where py >nul 2>&1
if errorlevel 1 call :fail "The Python launcher 'py' is not on PATH." "Install Python 3.12+ from https://python.org and tick 'Add Python to PATH'."

:: The backend imports these at startup; a missing one surfaces as an opaque
:: 'Could not start the analysis backend' dialog several steps later.
py -c "import fastapi, uvicorn, sse_starlette, pydantic, typer" >nul 2>&1
if errorlevel 1 call :fail "The backend's Python dependencies are missing." "Run:  py -m pip install -e fabric-model-readiness"

:: Catches the stale-editable-install failure: the package resolving to a path
:: that no longer exists imports fine from src/ but breaks everywhere else.
py -c "import scout, api, shared" >nul 2>&1
if errorlevel 1 call :fail "The 'fabric-model-readiness' package is not installed correctly." "Run:  py -m pip install -e fabric-model-readiness"

echo [check] Prerequisites OK.

:: -------------------------------------------------------
:: 1. Ensure npm dependencies are installed
:: -------------------------------------------------------
if not exist node_modules\electron (
    echo [setup] Installing npm dependencies. First run only, this takes a few minutes...
    call npm install
    if errorlevel 1 call :fail "npm install failed." "Check your network connection and rerun this launcher."
)

:: -------------------------------------------------------
:: 2. Compile Electron TypeScript (keeps dist-electron/ current)
:: -------------------------------------------------------
echo [build] Compiling Electron main process...
call npx tsc -p electron\tsconfig.json
if errorlevel 1 call :fail "Electron TypeScript compilation failed." "See the errors above."

if not exist dist-electron\main.js call :fail "dist-electron\main.js was not produced." "The TypeScript build reported success but emitted nothing."

:: -------------------------------------------------------
:: 3. Start the Vite dev server (minimized, in its own window)
:: -------------------------------------------------------
call :kill_port %VITE_PORT%

:: /d sets the working directory -- avoids nested-quote issues with spaces in the path
start "Vite Dev Server" /d "%~dp0frontend" /min npx vite --port %VITE_PORT% --strictPort

echo [vite] Waiting for the frontend on port %VITE_PORT%...
set /a VITE_TRIES=0
:wait_vite
:: The sleep lives inside the PowerShell call on purpose. Calling timeout.exe
:: here breaks when a shell with GNU coreutils on PATH (Git Bash, MSYS) shadows
:: it -- 'timeout /t' is rejected and the loop busy-spins with no delay.
powershell -NoProfile -Command "Start-Sleep -Seconds 1; try { $null = Invoke-WebRequest -Uri http://localhost:%VITE_PORT% -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto vite_ready
set /a VITE_TRIES+=1
if !VITE_TRIES! geq %VITE_WAIT_LIMIT% (
    call :cleanup
    call :fail "Vite did not come up on port %VITE_PORT% within %VITE_WAIT_LIMIT% seconds." "Check the 'Vite Dev Server' window for the error."
)
goto wait_vite

:vite_ready
echo [vite] Frontend ready on port %VITE_PORT%.

:: -------------------------------------------------------
:: 4. Launch Electron (it spawns the Python backend itself)
:: -------------------------------------------------------
set DEV_VITE_PORT=%VITE_PORT%
echo [electron] Starting app...
echo.
call npx electron .
set ELECTRON_EXIT=%errorlevel%

if not "%ELECTRON_EXIT%"=="0" echo [electron] Exited with code %ELECTRON_EXIT%.

:: -------------------------------------------------------
:: 5. Cleanup
:: -------------------------------------------------------
call :cleanup
echo App closed.
endlocal
exit /b 0


:: =======================================================
:: Subroutines
:: =======================================================

:cleanup
echo [cleanup] Shutting down background processes...
call :kill_port %VITE_PORT%
:: Electron stops the backend on quit, but a force-kill leaves it orphaned and
:: holding its port. Match on image name AND command line so unrelated Python is
:: untouched, and skip $PID -- this command's own line contains 'api.server', so
:: without that guard PowerShell matches and kills itself before finishing.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.Name -match '^(python|py|pythonw)\.exe$' -and $_.CommandLine -like '*api.server*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
exit /b 0

:kill_port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%~1 " ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
exit /b 0

:fail
echo.
echo  ERROR: %~1
if not "%~2"=="" echo  FIX:   %~2
echo.
pause
endlocal
exit 1
