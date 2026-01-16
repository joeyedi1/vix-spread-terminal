# Simple launcher for the VIX Spread Terminal
$ErrorActionPreference = "Stop"

# Always run from the repo directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

$port = 8501
$address = "0.0.0.0"

# Launch Streamlit bound to all interfaces so teammates on VPN/LAN can reach it
python -m streamlit run vix_dashboard.py --server.address $address --server.port $port
