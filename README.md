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

## Files

- `vix_dashboard.py` - Main dashboard application
- `vix_dashboard_test.py` - Test file
- `vix_spread_daily_log.xlsx` - Daily spread data log

## Note

Requires Bloomberg Terminal and valid Bloomberg API credentials to fetch live data.
