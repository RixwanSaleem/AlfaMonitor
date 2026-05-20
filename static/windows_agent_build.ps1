<#
Build a self-contained Windows executable for the AlfaMonitor agent.
Run this script on a Windows machine with Python installed.
#>

param(
    [string]$PythonExe = "python",
    [string]$OutputName = "AlfaMonitorAgent",
    [string]$DistFolder = ".\dist",
    [string]$WorkFolder = ".\build"
)

Write-Host "Building Windows agent executable..."

& $PythonExe -m pip install --upgrade pip pyinstaller | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install PyInstaller. Please ensure Python is installed and on PATH."
    exit 1
}

$scriptPath = "agents\agent.py"

if (-not (Test-Path $scriptPath)) {
    Write-Error "Cannot find $scriptPath. Run this script from the repository root."
    exit 1
}

$pyinstallerArgs = @(
    "--onefile",
    "--name", $OutputName,
    "--distpath", $DistFolder,
    "--workpath", $WorkFolder,
    "--clean",
    "--noconsole",
    $scriptPath
)

Write-Host "Running PyInstaller..."
& $PythonExe -m PyInstaller @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed. Check the output above for details."
    exit 1
}

Write-Host "Build complete. Executable created at: $DistFolder\$OutputName.exe"
Write-Host "Copy the executable to your Windows target machine and run it as Administrator or install it as a service."
