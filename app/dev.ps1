# Development mode: run Python backend + Vite dev server separately
# Run from the project root: .\dev.ps1

$ErrorActionPreference = "Stop"

Write-Host "Starting Python backend on port 8000..." -ForegroundColor Cyan
$backend = Start-Process -NoNewWindow -PassThru -FilePath "python" -ArgumentList "-m", "api.server", "--port", "8000" -WorkingDirectory "fabric-model-readiness\src"

Write-Host "Starting Vite dev server..." -ForegroundColor Cyan
Push-Location app
npm run dev
Pop-Location

# Cleanup
if ($backend -and !$backend.HasExited) {
    Stop-Process -Id $backend.Id
}
