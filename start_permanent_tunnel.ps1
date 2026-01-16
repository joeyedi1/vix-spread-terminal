# Keep VIX Dashboard tunnel running 24/7
# This script runs the temporary free tunnel and keeps it alive

$ErrorActionPreference = "Stop"

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Starting VIX Dashboard Cloudflare Tunnel..."
Write-Host "Tunnel URL will appear below:"
Write-Host "============================================"

# Run tunnel - it will auto-restart if connection drops
while ($true) {
    cloudflared tunnel --url http://localhost:8501
    Write-Host "Connection lost, reconnecting in 10 seconds..."
    Start-Sleep -Seconds 10
}
