# VIX Spread Terminal

A real-time monitoring dashboard for VIX bullish call spread strategies with multi-expiry tracking. This application fetches options data from Bloomberg Terminal and visualizes spread performance through an interactive Streamlit interface.

## 📋 Overview

The VIX Spread Terminal tracks VIX call spreads (C20/C30) across multiple expiration dates, providing:
- Real-time price and volume monitoring
- Historical spread analysis with interactive charts
- Multi-language support (English/Chinese)
- Configurable data refresh and lookback periods

**Strategy**: Long VIX C20, Short VIX C30 (bullish call spread)

## 🚀 Features

- **Multi-Expiry Tracking**: Monitor multiple spread expirations simultaneously
- **Live Data Updates**: Automatic CSV refresh with configurable intervals
- **Interactive Charts**: 
  - Spread performance over time
  - Individual leg prices (Long C20 / Short C30)
  - Volume analysis
  - Historical mean reference lines
- **Bilingual Interface**: Toggle between English and Chinese
- **Customizable Display**:
  - Historical lookback period (30-180 days)
  - Auto-refresh settings
  - Selectable spread expirations

## 📦 Requirements

```
streamlit
blpapi
pandas
numpy
plotly
openpyxl
```

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone https://github.com/joeyedi1/vix-spread-terminal.git
cd vix-spread-terminal
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Bloomberg Terminal Setup**:
   - Ensure Bloomberg Terminal is running and logged in
   - Bloomberg API must be accessible on `localhost:8194`

## 📊 Usage

### Step 1: Fetch Data from Bloomberg

Run the data fetcher to download historical data:

```bash
python vix_data_fetcher.py
```

This will:
- Connect to Bloomberg Terminal
- Fetch historical price and volume data for configured spreads
- Save data to `vix_spread_data.csv`
- Default start date: January 1, 2025

### Step 2: Launch Dashboard

Start the Streamlit dashboard:

```bash
streamlit run vix_dashboard_static.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Step 3: Configure & Monitor

- Select target spread expirations from the sidebar
- Adjust historical lookback period (30-180 days)
- Enable auto-refresh for continuous monitoring
- Switch language between English/Chinese as needed

## 📁 Project Structure

```
vix-spread-terminal/
├── vix_data_fetcher.py      # Bloomberg data fetcher
├── vix_dashboard_static.py  # Main Streamlit dashboard
├── vix_dashboard_test.py    # Testing dashboard version
├── vix_dashboard.py         # Alternative dashboard version
├── vix_spread_data.csv      # Generated data file (after running fetcher)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## ⚙️ Configuration

### Spread Configuration

Edit `SPREADS_CONFIG` in [vix_data_fetcher.py](vix_data_fetcher.py) to modify tracked spreads:

```python
SPREADS_CONFIG = {
    "Feb 2026": {
        "expiry": "02/18/26",
        "long": "VIX US 02/18/26 C20 Index",
        "short": "VIX US 02/18/26 C30 Index",
    },
    "Mar 2026": {
        "expiry": "03/18/26",
        "long": "VIX US 03/18/26 C20 Index",
        "short": "VIX US 03/18/26 C30 Index",
    },
}
```

### Historical Data Range

Modify `START_DATE` in [vix_data_fetcher.py](vix_data_fetcher.py):

```python
START_DATE = "20250101"  # Format: YYYYMMDD
```

## 🎨 Dashboard Features

### Metrics Cards
- **Long Leg (C20)**: Current price, daily change, volume
- **Short Leg (C30)**: Current price, daily change, volume
- **Net Spread**: Current spread value and daily change

### Interactive Charts
- **Spread Chart**: Net spread over time with mean reference
- **Individual Legs**: Long and short leg prices on dual-axis chart
- **Volume Chart**: Combined volume analysis for both legs

### Data Table
- Expandable view of raw CSV data
- Sortable by date (most recent first)
- Full historical record of all tracked spreads

## 🔄 Auto-Refresh

Enable auto-refresh in the sidebar to keep data current:
- Default interval: 60 seconds
- Dashboard automatically reloads CSV data
- Re-run data fetcher periodically for fresh Bloomberg data

## 🌐 Language Support

Switch between English and Chinese in the sidebar:
- All UI elements translate dynamically
- Chart labels and tooltips update accordingly
- Spread names localized (e.g., "Feb 2026" → "2026年2月")

## 🐛 Troubleshooting

**Issue**: `vix_spread_data.csv not found`
- **Solution**: Run `python vix_data_fetcher.py` first to generate data file

**Issue**: Bloomberg connection error
- **Solution**: Ensure Bloomberg Terminal is running and logged in
- Check that Bloomberg API service is accessible on port 8194

**Issue**: No data displayed for certain dates
- **Solution**: Bloomberg may not have data for weekends/holidays
- Check date range in data fetcher configuration

**Issue**: Dashboard not updating
- **Solution**: Re-run `vix_data_fetcher.py` to fetch latest data
- Enable auto-refresh in dashboard settings

## 📝 Notes

- **Market Hours**: Data availability depends on Bloomberg Terminal access and market hours
- **Data Latency**: Dashboard reads from CSV; re-run fetcher for latest data
- **Static Mode**: Current version (`vix_dashboard_static.py`) reads from CSV; not direct live Bloomberg feed

## 🤝 Contributing

Feel free to open issues or submit pull requests for improvements.

## 📄 License

This project is provided as-is for monitoring VIX spread strategies.

## 🔗 Repository

GitHub: [joeyedi1/vix-spread-terminal](https://github.com/joeyedi1/vix-spread-terminal)
