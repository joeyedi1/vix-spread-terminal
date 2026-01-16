# Auto-start Cloudflare Tunnel for VIX Dashboard
# This keeps the tunnel running 24/7 even after reboots

$ErrorActionPreference = "Stop"

# Refresh PATH to find cloudflared
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Start tunnel
Write-Host "Starting Cloudflare Tunnel for VIX Dashboard..."
cloudflared tunnel --url http://localhost:8501
