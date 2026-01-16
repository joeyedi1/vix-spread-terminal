# VIX Spread Terminal

A professional Streamlit dashboard for monitoring and analyzing VIX spread trading opportunities using Bloomberg data.

## Features

- Real-time VIX spread monitoring
- Interactive charts with Plotly
- Daily logging of spread data
- Professional dark theme terminal interface
- Multi-spread tracking (Feb 2026, Mar 2026)

## Requirements

- Python 3.7+
- streamlit
- blpapi (Bloomberg API)
- pandas
- numpy
- plotly

## Installation

```bash
pip install streamlit pandas numpy plotly blpapi
```

## Usage

```bash
streamlit run vix_dashboard.py
```

## Deployment (Bloomberg-connected desktop)

Use this when the desktop with Bloomberg Terminal stays on 24/7 and you want teammates on VPN/LAN (or through a reverse proxy) to view the app.

1. Install dependencies once:
```bash
pip install -r requirements.txt
```
2. Start the app bound to all interfaces:
```bash
streamlit run vix_dashboard.py --server.address 0.0.0.0 --server.port 8501
```
	Or run the helper script:
```powershell
.\start_streamlit.ps1
```
3. Share the URL (VPN/LAN): `http://<desktop-lan-ip>:8501`
4. Secure exposure (recommended): keep access behind VPN; if exposing externally, use a reverse proxy with HTTPS and auth instead of opening port 8501 directly.
5. Keep it running: wrap the command with NSSM or Task Scheduler to auto-restart on reboot.

## Run as a Windows service (NSSM)

Keeps the app alive after reboots/logouts on the Bloomberg desktop.

```powershell
.\install_service.ps1
```

- Service name: VIXStreamlit
- Logs: logs/stdout.log and logs/stderr.log
- Stop/start: `nssm stop VIXStreamlit` / `nssm start VIXStreamlit`

## Access and security

- Preferred: keep access behind VPN and share http://<desktop-lan-ip>:8501
- If exposing externally, front it with HTTPS and optional auth at a reverse proxy; avoid exposing raw port 8501.
- Allow-list IPs where possible; keep Bloomberg desktop firewalled from the public internet.

## Files

- `vix_dashboard.py` - Main dashboard application
- `vix_dashboard_test.py` - Test file
- `vix_spread_daily_log.xlsx` - Daily spread data log
- `requirements.txt` - Python dependencies
- `start_streamlit.ps1` - Helper script to launch Streamlit on port 8501

## Note

Requires Bloomberg Terminal and valid Bloomberg API credentials to fetch live data.
