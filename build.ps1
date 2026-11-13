param([string]$Python = ".venv\Scripts\python.exe")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Install requirements-dev.txt in a Python 3.11+ virtual environment, then pass its python.exe with -Python."
}
& $Python -m PyInstaller --noconfirm --clean MouseRuler.spec
if ($LASTEXITCODE -ne 0) { throw "Executable build failed." }
Copy-Item -LiteralPath "dist\MouseRuler.exe" -Destination "MouseRuler.exe" -Force
Write-Output "Built MouseRuler.exe"
