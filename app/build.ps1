# Build script for Fabric Model AI Readiness desktop app
# Run from the project root: .\build.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== Building Python Backend ===" -ForegroundColor Cyan

Push-Location fabric-model-readiness

# Install Python dependencies
pip install -e ".[dev]"
pip install pyinstaller

# Bundle Python backend
pyinstaller pyinstaller.spec --distpath dist/backend --noconfirm
Pop-Location

Write-Host ""
Write-Host "=== Building Electron App ===" -ForegroundColor Cyan

Push-Location app

# Install Node dependencies
npm install

# Build frontend + Electron
npm run build

# Package as installer
npm run build:electron
Pop-Location

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Green
Write-Host "Installer is in: app/release/"
