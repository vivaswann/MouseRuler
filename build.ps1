param([string]$Python = ".venv\Scripts\python.exe")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Install requirements-dev.txt in a Python 3.11+ virtual environment, then pass its python.exe with -Python."
}
& $Python -m PyInstaller --noconfirm --clean MouseMeasure.spec
if ($LASTEXITCODE -ne 0) { throw "Executable build failed." }
Copy-Item -LiteralPath "dist\MouseMeasure.exe" -Destination "MouseMeasure.exe" -Force
Write-Output "Built MouseMeasure.exe"
