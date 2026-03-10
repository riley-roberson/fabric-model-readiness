@echo off
setlocal
title Fabric Model AI Readiness - Launcher
cd /d "%~dp0"

:: -------------------------------------------------------
:: 1. Ensure npm dependencies are installed
:: -------------------------------------------------------
if not exist node_modules\electron (
    echo [setup] Installing npm dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: npm install failed.
        pause
        exit /b 1
    )
)

:: -------------------------------------------------------
:: 2. Compile Electron TypeScript (keeps dist-electron/ current)
:: -------------------------------------------------------
echo [build] Compiling Electron main process...
call npx tsc -p electron\tsconfig.json 2>&1
if errorlevel 1 (
    echo ERROR: Electron TypeScript compilation failed.
    pause
    exit /b 1
)

:: -------------------------------------------------------
:: 3. Start Vite dev server (minimized, in background)
:: -------------------------------------------------------
set VITE_PORT=5173

:: Kill anything already listening on our port
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%VITE_PORT% " ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Use /d to set working directory -- avoids nested-quote issues with spaces in path
start "Vite Dev Server" /d "%~dp0frontend" /min npx vite --port %VITE_PORT% --strictPort

:: Wait for Vite to respond
echo [vite] Waiting for frontend on port %VITE_PORT%...
:wait_vite
timeout /t 1 /nobreak >nul
powershell -Command "try { $null = Invoke-WebRequest -Uri http://localhost:%VITE_PORT% -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto wait_vite
echo [vite] Frontend ready on port %VITE_PORT%.

:: -------------------------------------------------------
:: 4. Launch Electron (spawns Python backend automatically)
:: -------------------------------------------------------
set DEV_VITE_PORT=%VITE_PORT%
echo [electron] Starting app...
call npx electron .
set ELECTRON_EXIT=%errorlevel%

if %ELECTRON_EXIT% neq 0 (
    echo [electron] Exited with code %ELECTRON_EXIT%.
)

:: -------------------------------------------------------
:: 5. Cleanup: kill Vite by port
:: -------------------------------------------------------
echo [cleanup] Shutting down Vite...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%VITE_PORT% " ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo App closed.
endlocal
