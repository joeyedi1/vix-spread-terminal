# Install and start the Streamlit app as a Windows service via NSSM.
# Prerequisite: download NSSM and set $nssmPath to its nssm.exe location.

$ErrorActionPreference = "Stop"

$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $repoDir

$nssmPath = "C:\nssm\nssm.exe"  # change if your nssm.exe is elsewhere
if (-not (Test-Path $nssmPath)) {
    Write-Error "nssm.exe not found at $nssmPath. Update the path and retry."
}

$python = (Get-Command python -ErrorAction Stop).Source
$serviceName = "VIXStreamlit"
$appScript = Join-Path $repoDir "vix_dashboard.py"
$logDir = Join-Path $repoDir "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$arguments = "-m streamlit run `"$appScript`" --server.address 0.0.0.0 --server.port 8501"

& $nssmPath install $serviceName $python $arguments
& $nssmPath set $serviceName AppDirectory $repoDir
& $nssmPath set $serviceName AppStdout (Join-Path $logDir "stdout.log")
& $nssmPath set $serviceName AppStderr (Join-Path $logDir "stderr.log")
& $nssmPath set $serviceName Start SERVICE_AUTO_START
& $nssmPath set $serviceName AppStopMethodSkip 0

& $nssmPath start $serviceName
Write-Host "Service '$serviceName' installed and started."
