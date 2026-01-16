import streamlit as st
import blpapi
import time
import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import os

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="VIX Spread Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. TRANSLATIONS ---
TRANSLATIONS = {
    "en": {
        # Header
        "page_title": "VIX Spread Terminal",
        "header_subtitle": "VIX Bullish Call Spread Monitor",
        "header_title": "Multi-Expiry Terminal",
        "live_data": "LIVE DATA",
        
        # Sidebar
        "configuration": "Configuration",
        "language": "Language",
        "active_spreads": "Active Spreads",
        "select_expiries": "Select expiries to monitor",
        "data_settings": "Data Settings",
        "historical_lookback": "Historical Lookback",
        "days": "days",
        "refresh_interval": "Refresh Interval",
        "auto_refresh": "Auto Refresh",
        "auto_log": "Auto-log daily to Excel",
        "daily_log": "Daily Log",
        "days_logged": "days logged",
        "no_log_file": "No log file yet",
        "refresh": "🔄 Refresh",
        "export": "📥 Export",
        "reset_log": "🗑️ Reset & Reload Log",
        "download_log": "Download Log",
        
        # Metrics
        "long_leg": "Long Leg (C20)",
        "short_leg": "Short Leg (C30)",
        "net_spread": "Net Spread",
        "volume": "Vol",
        
        # Chart
        "spread_title": "Spread",
        "individual_legs": "Individual Legs",
        "volume_title": "Volume",
        "mean": "Mean",
        
        # Log viewer
        "view_daily_log": "📁 View Daily Log History",
        "no_log_exists": "No daily log file exists yet. Enable 'Auto-log daily to Excel' to start recording.",
        
        # Errors
        "select_spread_warning": "Please select at least one spread expiry in the sidebar.",
        "connection_error": "Connection Error",
        "error_details": "Error Details",
        "troubleshooting": "Troubleshooting",
        "ensure_bloomberg": "Ensure Bloomberg Terminal is running",
        "check_api": "Check that the API is enabled (WAPI<GO>)",
        "verify_connection": "Verify localhost:8194 connection",
        "initializing_log": "Initializing log with historical data from 2026...",
    },
    "zh": {
        # Header
        "page_title": "VIX价差终端",
        "header_subtitle": "VIX看涨期权价差监控",
        "header_title": "多到期日终端",
        "live_data": "实时数据",
        
        # Sidebar
        "configuration": "配置",
        "language": "语言",
        "active_spreads": "活跃价差",
        "select_expiries": "选择要监控的到期日",
        "data_settings": "数据设置",
        "historical_lookback": "历史回溯",
        "days": "天",
        "refresh_interval": "刷新间隔",
        "auto_refresh": "自动刷新",
        "auto_log": "自动记录到Excel",
        "daily_log": "每日日志",
        "days_logged": "天已记录",
        "no_log_file": "暂无日志文件",
        "refresh": "🔄 刷新",
        "export": "📥 导出",
        "reset_log": "🗑️ 重置并重新加载",
        "download_log": "下载日志",
        
        # Metrics
        "long_leg": "多头 (C20)",
        "short_leg": "空头 (C30)",
        "net_spread": "净价差",
        "volume": "成交量",
        
        # Chart
        "spread_title": "价差",
        "individual_legs": "单腿价格",
        "volume_title": "成交量",
        "mean": "均值",
        
        # Log viewer
        "view_daily_log": "📁 查看每日日志历史",
        "no_log_exists": "暂无日志文件。启用'自动记录到Excel'开始记录。",
        
        # Errors
        "select_spread_warning": "请在侧边栏中选择至少一个价差到期日。",
        "connection_error": "连接错误",
        "error_details": "错误详情",
        "troubleshooting": "故障排除",
        "ensure_bloomberg": "确保彭博终端正在运行",
        "check_api": "检查API是否已启用 (WAPI<GO>)",
        "verify_connection": "验证 localhost:8194 连接",
        "initializing_log": "正在从2026年初始化历史数据日志...",
    }
}

# Spread names in both languages
SPREADS_CONFIG_NAMES = {
    "en": {"Feb 2026": "Feb 2026", "Mar 2026": "Mar 2026"},
    "zh": {"Feb 2026": "2026年2月", "Mar 2026": "2026年3月"}
}

# --- 3. CONSTANTS ---
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

DAILY_LOG_PATH = Path("vix_spread_daily_log.xlsx")

# --- 4. SESSION STATE FOR LANGUAGE ---
if 'language' not in st.session_state:
    st.session_state.language = 'zh'  # Default to Chinese
if 'prev_data' not in st.session_state:
    st.session_state.prev_data = {}
if 'hist_data' not in st.session_state:
    st.session_state.hist_data = {}
if 'last_log_date' not in st.session_state:
    st.session_state.last_log_date = None
if 'log_initialized' not in st.session_state:
    st.session_state.log_initialized = False
if 'reset_log' not in st.session_state:
    st.session_state.reset_log = False

# Helper function to get translation
def t(key):
    return TRANSLATIONS[st.session_state.language].get(key, key)

# --- 5. ADAPTIVE CSS (works with Streamlit's theme) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
    
    /* Custom dashboard elements that adapt to any theme */
    
    .dashboard-header {
        background: linear-gradient(90deg, rgba(38,166,154,0.12) 0%, transparent 50%);
        border-bottom: 1px solid rgba(38,166,154,0.25);
        padding: 20px 30px;
        margin: -1rem -1rem 2rem -1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title {
        font-family: 'Plus Jakarta Sans', 'Noto Sans SC', sans-serif;
        font-size: 28px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
        font-size: 12px;
        color: #26a69a;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(38,166,154,0.12);
        border: 1px solid rgba(38,166,154,0.35);
        padding: 8px 16px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
        font-size: 11px;
        color: #26a69a;
    }
    .live-dot {
        width: 8px;
        height: 8px;
        background: #26a69a;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(38,166,154,0.4); }
        50% { opacity: 0.8; box-shadow: 0 0 0 8px rgba(38,166,154,0); }
    }
    
    .metric-card {
        border-radius: 12px;
        padding: 24px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        border: 1px solid rgba(128, 128, 128, 0.25);
        background: rgba(128, 128, 128, 0.06);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(38, 166, 154, 0.4);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    }
    
    .metric-label {
        font-family: 'Plus Jakarta Sans', 'Noto Sans SC', sans-serif;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 8px;
        opacity: 0.7;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 36px;
        font-weight: 700;
        line-height: 1;
    }
    .metric-delta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 13px;
        font-weight: 600;
        margin-top: 8px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 6px;
    }
    .delta-positive {
        color: #26a69a;
        background: rgba(38,166,154,0.15);
    }
    .delta-negative {
        color: #ef5350;
        background: rgba(239,83,80,0.15);
    }
    
    .volume-text {
        font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
        font-size: 12px;
        margin-top: 8px;
        opacity: 0.7;
    }
    
    .log-status {
        font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
        font-size: 11px;
        padding: 8px 12px;
        border-radius: 6px;
        margin-top: 10px;
    }
    .log-success {
        background: rgba(38,166,154,0.12);
        color: #26a69a;
        border: 1px solid rgba(38,166,154,0.25);
    }
    .log-info {
        background: rgba(66,165,245,0.12);
        color: #42a5f5;
        border: 1px solid rgba(66,165,245,0.25);
    }
</style>
""", unsafe_allow_html=True)


# --- 6. BLOOMBERG ENGINE ---
class BloombergEngine:
    """Bloomberg API wrapper with volume support."""
    
    def __init__(self):
        self.session = None
        self._connect()
    
    def _connect(self):
        options = blpapi.SessionOptions()
        options.setServerHost("localhost")
        options.setServerPort(8194)
        self.session = blpapi.Session(options)
        
        if not self.session.start():
            raise ConnectionError("Failed to start Bloomberg session")
        if not self.session.openService("//blp/refdata"):
            raise ConnectionError("Failed to open //blp/refdata service")
    
    def get_live_data(self, tickers: list) -> dict:
        """Fetch current prices AND volume for given tickers."""
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")
        
        for ticker in tickers:
            request.append("securities", ticker)
        
        request.append("fields", "PX_LAST")
        request.append("fields", "PX_OPEN")
        request.append("fields", "PX_HIGH")
        request.append("fields", "PX_LOW")
        request.append("fields", "VOLUME")
        request.append("fields", "PX_VOLUME")
        request.append("fields", "OPEN_INT")
        
        self.session.sendRequest(request)
        
        results = {}
        timeout = time.time() + 5
        
        while time.time() < timeout:
            event = self.session.nextEvent(500)
            
            if event.eventType() in [blpapi.Event.RESPONSE, blpapi.Event.PARTIAL_RESPONSE]:
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        for i in range(sec_data.numValues()):
                            item = sec_data.getValueAsElement(i)
                            security = item.getElementAsString("security")
                            
                            if item.hasElement("fieldData"):
                                fd = item.getElement("fieldData")
                                
                                volume = None
                                for vol_field in ["VOLUME", "PX_VOLUME"]:
                                    if fd.hasElement(vol_field):
                                        try:
                                            volume = fd.getElementAsFloat(vol_field)
                                            break
                                        except:
                                            pass
                                
                                results[security] = {
                                    "last": fd.getElementAsFloat("PX_LAST") if fd.hasElement("PX_LAST") else None,
                                    "open": fd.getElementAsFloat("PX_OPEN") if fd.hasElement("PX_OPEN") else None,
                                    "high": fd.getElementAsFloat("PX_HIGH") if fd.hasElement("PX_HIGH") else None,
                                    "low": fd.getElementAsFloat("PX_LOW") if fd.hasElement("PX_LOW") else None,
                                    "volume": volume,
                                    "open_int": fd.getElementAsFloat("OPEN_INT") if fd.hasElement("OPEN_INT") else None,
                                }
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        return results
    
    def get_history(self, tickers: list, start_date: str, end_date: str = None) -> pd.DataFrame:
        """Fetch historical price and volume data."""
        if end_date is None:
            end_date = datetime.datetime.now().strftime("%Y%m%d")
        
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("HistoricalDataRequest")
        
        for ticker in tickers:
            request.append("securities", ticker)
        
        request.append("fields", "PX_LAST")
        request.append("fields", "VOLUME")
        request.set("startDate", start_date)
        request.set("endDate", end_date)
        request.set("periodicitySelection", "DAILY")
        
        self.session.sendRequest(request)
        
        records = []
        while True:
            event = self.session.nextEvent(500)
            
            for msg in event:
                if msg.hasElement("securityData"):
                    sec_data = msg.getElement("securityData")
                    ticker = sec_data.getElementAsString("security")
                    
                    if sec_data.hasElement("fieldData"):
                        field_data = sec_data.getElement("fieldData")
                        
                        for i in range(field_data.numValues()):
                            point = field_data.getValueAsElement(i)
                            raw_date = point.getElementAsDatetime("date")
                            
                            volume = None
                            if point.hasElement("VOLUME"):
                                try:
                                    volume = point.getElementAsFloat("VOLUME")
                                except:
                                    pass
                            
                            records.append({
                                "Date": pd.Timestamp(year=raw_date.year, month=raw_date.month, day=raw_date.day),
                                "Ticker": ticker,
                                "Price": point.getElementAsFloat("PX_LAST"),
                                "Volume": volume
                            })
            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        return pd.DataFrame(records)
    
    def close(self):
        if self.session:
            self.session.stop()


# --- 7. LOGGING FUNCTIONS ---
def initialize_log_with_history(engine, spreads_config: dict, log_path: Path) -> bool:
    """Initialize the Excel log with historical data from 2026-01-01 to today."""
    start_date = "20260101"
    
    try:
        all_tickers = []
        for spread_name, config in spreads_config.items():
            all_tickers.extend([config["long"], config["short"]])
        
        raw_hist = engine.get_history(all_tickers, start_date)
        
        if raw_hist.empty:
            return False
        
        dates = raw_hist["Date"].unique()
        rows = []
        
        for date in sorted(dates):
            date_data = raw_hist[raw_hist["Date"] == date]
            row = {
                "Date": date.strftime("%Y-%m-%d"),
                "Timestamp": f"{date.strftime('%Y-%m-%d')} 16:00:00"
            }
            
            for spread_name, config in spreads_config.items():
                prefix = spread_name.replace(" ", "_")
                
                long_data = date_data[date_data["Ticker"] == config["long"]]
                short_data = date_data[date_data["Ticker"] == config["short"]]
                
                long_price = long_data["Price"].values[0] if len(long_data) > 0 else None
                short_price = short_data["Price"].values[0] if len(short_data) > 0 else None
                long_vol = long_data["Volume"].values[0] if len(long_data) > 0 and "Volume" in long_data.columns else None
                short_vol = short_data["Volume"].values[0] if len(short_data) > 0 and "Volume" in short_data.columns else None
                
                row[f"{prefix}_Long_Price"] = long_price
                row[f"{prefix}_Long_Volume"] = long_vol
                row[f"{prefix}_Short_Price"] = short_price
                row[f"{prefix}_Short_Volume"] = short_vol
                row[f"{prefix}_Spread"] = (long_price - short_price) if (long_price and short_price) else None
                row[f"{prefix}_Total_Volume"] = (long_vol or 0) + (short_vol or 0) if (long_vol or short_vol) else None
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_excel(log_path, index=False, engine='openpyxl')
        return True
    
    except Exception as e:
        st.error(f"Failed to initialize log: {e}")
        return False


def log_daily_data(spreads_data: dict, log_path: Path) -> bool:
    """Log today's spread data to Excel file."""
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    
    row_data = {"Date": today_str, "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    
    for spread_name, data in spreads_data.items():
        prefix = spread_name.replace(" ", "_")
        row_data[f"{prefix}_Long_Price"] = data.get("long_price")
        row_data[f"{prefix}_Long_Volume"] = data.get("long_volume")
        row_data[f"{prefix}_Short_Price"] = data.get("short_price")
        row_data[f"{prefix}_Short_Volume"] = data.get("short_volume")
        row_data[f"{prefix}_Spread"] = data.get("spread")
        row_data[f"{prefix}_Total_Volume"] = (data.get("long_volume") or 0) + (data.get("short_volume") or 0)
    
    new_row = pd.DataFrame([row_data])
    
    try:
        if log_path.exists():
            existing_df = pd.read_excel(log_path, engine='openpyxl')
            if today_str in existing_df["Date"].values:
                existing_df = existing_df[existing_df["Date"] != today_str]
            combined_df = pd.concat([existing_df, new_row], ignore_index=True)
        else:
            combined_df = new_row
        
        combined_df.to_excel(log_path, index=False, engine='openpyxl')
        return True
    except Exception as e:
        st.error(f"Failed to log data: {e}")
        return False


def get_log_summary(log_path: Path) -> dict:
    """Get summary of logged data."""
    if not log_path.exists():
        return {"exists": False, "rows": 0, "first_date": None, "last_date": None}
    
    try:
        df = pd.read_excel(log_path, engine='openpyxl')
        return {
            "exists": True,
            "rows": len(df),
            "first_date": df["Date"].min() if len(df) > 0 else None,
            "last_date": df["Date"].max() if len(df) > 0 else None,
        }
    except:
        return {"exists": False, "rows": 0, "first_date": None, "last_date": None}


# --- 8. CHART FUNCTION ---
def create_spread_chart(df: pd.DataFrame, spread_name: str, lang: str) -> go.Figure:
    """Create spread chart with volume subplot."""
    
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    has_volume = "Volume" in df.columns and df["Volume"].notna().any()
    
    # Get translated labels
    spread_label = TRANSLATIONS[lang]["spread_title"]
    legs_label = TRANSLATIONS[lang]["individual_legs"]
    volume_label = TRANSLATIONS[lang]["volume_title"]
    mean_label = TRANSLATIONS[lang]["mean"]
    
    display_name = SPREADS_CONFIG_NAMES[lang].get(spread_name, spread_name)
    
    if has_volume:
        fig = make_subplots(
            rows=3, cols=1,
            row_heights=[0.5, 0.25, 0.25],
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(f"{display_name} {spread_label}", legs_label, volume_label)
        )
    else:
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.6, 0.4],
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=(f"{display_name} {spread_label}", legs_label)
        )
    
    # Spread line
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df["Spread"],
            mode='lines', name=spread_label,
            line=dict(color='#26a69a', width=2.5),
            fill='tozeroy',
            fillcolor='rgba(38,166,154,0.15)',
            hovertemplate=f'<b>{spread_label}</b>: %{{y:.2f}}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Mean line
    mean_spread = df["Spread"].mean()
    fig.add_hline(y=mean_spread, line_dash="dash", line_color="#9e9e9e",
                  annotation_text=f"{mean_label}: {mean_spread:.2f}", row=1, col=1)
    
    # Individual legs
    if "Long" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["Long"], mode='lines', name='C20 (Long)',
                      line=dict(color='#42a5f5', width=1.5)),
            row=2, col=1
        )
    if "Short" in df.columns:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["Short"], mode='lines', name='C30 (Short)',
                      line=dict(color='#ab47bc', width=1.5)),
            row=2, col=1
        )
    
    # Volume bars
    if has_volume:
        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], name=volume_label,
                  marker_color='rgba(38,166,154,0.5)'),
            row=3, col=1
        )
    
    # Use transparent backgrounds
    fig.update_layout(
        height=550 if has_volume else 450,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="JetBrains Mono, Noto Sans SC, monospace", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                   bgcolor='rgba(0,0,0,0)'),
        margin=dict(l=60, r=30, t=80, b=50),
        hovermode='x unified',
        showlegend=True
    )
    
    fig.update_xaxes(gridcolor='rgba(128,128,128,0.2)', showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor='rgba(128,128,128,0.2)', showgrid=True, zeroline=False)
    
    return fig


# --- 9. SIDEBAR ---
with st.sidebar:
    st.markdown(f"## ⚙️ {t('configuration')}")
    st.markdown("---")
    
    # Language toggle
    st.markdown(f"**{t('language')}**")
    if st.session_state.language == 'en':
        if st.button("中文", key='lang_toggle'):
            st.session_state.language = 'zh'
            st.rerun()
    else:
        if st.button("English", key='lang_toggle'):
            st.session_state.language = 'en'
            st.rerun()
    
    st.markdown("---")
    st.markdown(f"### {t('active_spreads')}")
    
    # Display spread options in current language
    spread_options = list(SPREADS_CONFIG.keys())
    spread_display = [SPREADS_CONFIG_NAMES[st.session_state.language][s] for s in spread_options]
    
    active_spreads_display = st.multiselect(
        t('select_expiries'),
        options=spread_display,
        default=spread_display,
        help=t('select_expiries')
    )
    
    # Map back to internal names
    display_to_internal = {v: k for k, v in SPREADS_CONFIG_NAMES[st.session_state.language].items()}
    active_spreads = [display_to_internal[d] for d in active_spreads_display]
    
    st.markdown("---")
    st.markdown(f"### {t('data_settings')}")
    
    lookback_days = st.selectbox(
        t('historical_lookback'),
        options=[30, 60, 90, 180, 365],
        index=2,
        format_func=lambda x: f"{x} {t('days')}"
    )
    
    refresh_interval = st.selectbox(
        t('refresh_interval'),
        options=[30, 60, 120, 300],
        index=1,
        format_func=lambda x: f"{x}s" if x < 60 else f"{x//60} min"
    )
    
    auto_refresh = st.checkbox(t('auto_refresh'), value=True)
    auto_log = st.checkbox(t('auto_log'), value=True)
    
    st.markdown("---")
    st.markdown(f"### {t('daily_log')}")
    
    log_summary = get_log_summary(DAILY_LOG_PATH)
    if log_summary["exists"]:
        st.markdown(f"""
        <div class="log-status log-success">
            📁 {log_summary['rows']} {t('days_logged')}<br>
            {log_summary['first_date']} → {log_summary['last_date']}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="log-status log-info">
            📁 {t('no_log_file')}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button(t('refresh'), width='stretch'):
            st.session_state.hist_data = {}
            st.rerun()
    with col2:
        if st.button(t('export'), width='stretch'):
            if DAILY_LOG_PATH.exists():
                with open(DAILY_LOG_PATH, "rb") as f:
                    st.download_button(
                        t('download_log'),
                        f.read(),
                        "vix_spread_daily_log.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width='stretch'
                    )
    
    if st.button(t('reset_log'), width='stretch'):
        if DAILY_LOG_PATH.exists():
            DAILY_LOG_PATH.unlink()
        st.session_state.log_initialized = False
        st.session_state.last_log_date = None
        st.rerun()


# --- 10. MAIN DASHBOARD ---
st.markdown(f"""
<div class="dashboard-header">
    <div>
        <div class="header-subtitle">{t('header_subtitle')}</div>
        <div class="header-title">{t('header_title')}</div>
    </div>
    <div class="live-badge">
        <div class="live-dot"></div>
        {t('live_data')}
    </div>
</div>
""", unsafe_allow_html=True)

if not active_spreads:
    st.warning(t('select_spread_warning'))
    st.stop()

try:
    engine = BloombergEngine()
    
    # Collect all tickers
    all_tickers = []
    for spread_name in active_spreads:
        config = SPREADS_CONFIG[spread_name]
        all_tickers.extend([config["long"], config["short"]])
    
    # Fetch live data
    live_data = engine.get_live_data(all_tickers)
    
    # Process each spread
    spreads_results = {}
    
    for spread_name in active_spreads:
        config = SPREADS_CONFIG[spread_name]
        t_long = config["long"]
        t_short = config["short"]
        
        long_data = live_data.get(t_long, {})
        short_data = live_data.get(t_short, {})
        
        p_long = long_data.get("last") or 0
        p_short = short_data.get("last") or 0
        v_long = long_data.get("volume")
        v_short = short_data.get("volume")
        
        spreads_results[spread_name] = {
            "long_price": p_long,
            "short_price": p_short,
            "long_volume": v_long,
            "short_volume": v_short,
            "spread": p_long - p_short,
            "config": config
        }
    
    # Initialize log with historical data if it doesn't exist
    if auto_log and not DAILY_LOG_PATH.exists():
        with st.spinner(t('initializing_log')):
            initialize_log_with_history(engine, SPREADS_CONFIG, DAILY_LOG_PATH)
    
    # Auto-log today's data if enabled
    today = datetime.date.today()
    if auto_log and st.session_state.last_log_date != today:
        if log_daily_data(spreads_results, DAILY_LOG_PATH):
            st.session_state.last_log_date = today
    
    # --- DISPLAY SPREADS ---
    tab_names = [SPREADS_CONFIG_NAMES[st.session_state.language][s] for s in active_spreads]
    tabs = st.tabs(tab_names)
    
    for tab, spread_name in zip(tabs, active_spreads):
        with tab:
            data = spreads_results[spread_name]
            config = data["config"]
            
            # Calculate deltas
            prev = st.session_state.prev_data.get(spread_name, {})
            delta_long = data["long_price"] - prev.get("long_price", data["long_price"])
            delta_short = data["short_price"] - prev.get("short_price", data["short_price"])
            delta_spread = data["spread"] - prev.get("spread", data["spread"])
            
            # Metrics row
            c1, c2, c3 = st.columns(3)
            
            def render_metric(col, label, value, delta, volume=None, show_volume_space=True):
                delta_class = "positive" if delta >= 0 else "negative"
                sign = "+" if delta > 0 else ""
                arrow = "▲" if delta > 0 else "▼" if delta < 0 else ""
                
                html_parts = [
                    '<div class="metric-card">',
                    f'<div class="metric-label">{label}</div>',
                    f'<div class="metric-value">{value:.2f}</div>',
                ]
                
                if abs(delta) >= 0.001:
                    html_parts.append(f'<div class="metric-delta delta-{delta_class}">{arrow} {sign}{delta:.2f}</div>')
                
                if volume is not None:
                    vol_label = t('volume')
                    html_parts.append(f'<div class="volume-text">{vol_label}: {int(volume):,}</div>')
                elif show_volume_space:
                    html_parts.append('<div class="volume-text">&nbsp;</div>')
                
                html_parts.append('</div>')
                
                col.markdown("".join(html_parts), unsafe_allow_html=True)
            
            render_metric(c1, t('long_leg'), data["long_price"], delta_long, data["long_volume"])
            render_metric(c2, t('short_leg'), data["short_price"], delta_short, data["short_volume"])
            render_metric(c3, t('net_spread'), data["spread"], delta_spread)
            
            # Load historical data
            if spread_name not in st.session_state.hist_data:
                start_date = (datetime.datetime.now() - datetime.timedelta(days=lookback_days)).strftime("%Y%m%d")
                raw_hist = engine.get_history([config["long"], config["short"]], start_date)
                
                if not raw_hist.empty:
                    price_pivot = raw_hist.pivot(index="Date", columns="Ticker", values="Price").ffill().bfill()
                    rename_map = {config["long"]: "Long", config["short"]: "Short"}
                    price_pivot = price_pivot.rename(columns=rename_map)
                    
                    if "Volume" in raw_hist.columns:
                        vol_pivot = raw_hist.pivot(index="Date", columns="Ticker", values="Volume").ffill()
                        vol_pivot = vol_pivot.rename(columns=rename_map)
                        price_pivot["Volume"] = vol_pivot.get("Long", 0) + vol_pivot.get("Short", 0)
                    
                    if "Long" in price_pivot.columns and "Short" in price_pivot.columns:
                        price_pivot["Spread"] = price_pivot["Long"] - price_pivot["Short"]
                        st.session_state.hist_data[spread_name] = price_pivot
            
            # Chart
            hist_df = st.session_state.hist_data.get(spread_name, pd.DataFrame())
            st.markdown("---")
            if not hist_df.empty:
                fig = create_spread_chart(hist_df, spread_name, st.session_state.language)
                st.plotly_chart(fig, width='stretch', theme="streamlit")
    
    # Update previous data
    st.session_state.prev_data = {name: {
        "long_price": d["long_price"],
        "short_price": d["short_price"],
        "spread": d["spread"]
    } for name, d in spreads_results.items()}
    
    # --- DAILY LOG VIEWER ---
    st.markdown("---")
    with st.expander(t('view_daily_log'), expanded=False):
        if DAILY_LOG_PATH.exists():
            log_df = pd.read_excel(DAILY_LOG_PATH, engine='openpyxl')
            log_df = log_df.sort_values("Date", ascending=False)
            st.dataframe(log_df, width='stretch', height=400)
        else:
            st.info(t('no_log_exists'))
    
    engine.close()

except Exception as e:
    st.error(f"""
    ### {t('connection_error')}
    
    **{t('error_details')}:** `{str(e)}`
    
    **{t('troubleshooting')}:**
    1. {t('ensure_bloomberg')}
    2. {t('check_api')}
    3. {t('verify_connection')}
    """)

# Auto refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()