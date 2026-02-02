import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from datetime import datetime

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="VIX Spread Terminal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. CONFIGURATION ---
CSV_PATH = Path("vix_spread_data.csv")

# --- UPDATED: Added futures ticker reference for each spread ---
SPREADS_CONFIG = {
    "Feb 2026": {
        "prefix": "Feb_2026",
        "expiry_date": "2026-02-18",
        "futures_col": "Feb_2026_VIX_Futures",  # Column name in CSV
        "futures_ticker": "UXG26",  # For display
    },
    "Mar 2026": {
        "prefix": "Mar_2026", 
        "expiry_date": "2026-03-18",
        "futures_col": "Mar_2026_VIX_Futures",
        "futures_ticker": "UXH26",
    },
}

SPREADS_CONFIG_NAMES = {
    "en": {"Feb 2026": "Feb 2026", "Mar 2026": "Mar 2026"},
    "zh": {"Feb 2026": "2026年2月", "Mar 2026": "2026年3月"}
}
SPREAD_KEYS = ["Feb 2026", "Mar 2026"]

# --- 3. TRANSLATIONS ---
TRANSLATIONS = {
    "en": {
        "page_title": "VIX Spread Terminal",
        "header_subtitle": "VIX Bullish Call Spread Monitor",
        "header_title": "Multi-Expiry Terminal",
        "live_data": "STATIC DATA",
        "configuration": "Configuration",
        "language": "Language",
        "active_spreads": "Active Spreads",
        "select_expiries": "Select expiries to monitor",
        "data_settings": "Data Settings",
        "historical_lookback": "Historical Lookback",
        "days": "days",
        "refresh": "Reload CSV",
        "last_updated": "Last Data Point",
        "long_leg": "Long Leg (C20)",
        "short_leg": "Short Leg (C25)",
        "net_spread": "Net Spread",
        "volume": "Vol",
        "spread_title": "Spread",
        "individual_legs": "Individual Legs",
        "volume_title": "Volume",
        "mean": "Mean",
        "feb_be_label": "Feb BE",
        "mar_be_label": "Mar BE",
        "long_leg_chart": "C20 (Long)",
        "short_leg_chart": "C25 (Short)",
        "view_daily_log": "📁 View Data Source",
        "no_file": "❌ 'vix_spread_data.csv' not found. Run 'data_fetcher_v2.py' first.",
        "select_spread_warning": "Please select at least one spread expiry in the sidebar.",
        "cheap": "CHEAP",
        "expensive": "RICH",
        "fair": "FAIR",
        "valuation_title": "Statistical Value",
        "calc_title": "Calculator: Risk/Reward at Expiration",
        "inputs": "Inputs",
        "entry_price": "Entry Price (Debit)",
        "stats": "Stats",
        "max_profit": "Max Profit",
        "max_risk": "Max Risk",
        "rr_ratio": "R/R Ratio",
        "breakeven": "Breakeven",
        "chart_x": "VIX Futures at Expiration",
        "chart_y": "Profit / Loss",
        "dist_title": "Price Distribution",
        "freq": "Frequency",
        "now": "Now",
        "avg": "Avg",
        "be_abbr": "BE",
        "pnl_title": "Trade Performance",
        "entry_date": "Entry Date",
        "entry_px": "Entry",
        "current_px": "Current",
        "pnl": "P&L",
        "pnl_pct": "Return",
        "days_held": "Days Held",
        "dte": "DTE",
        "trade_status": "Status",
        "profit": "PROFIT",
        "loss": "LOSS",
        "flat": "FLAT",
        "trading": "Trading",
        "calendar": "Calendar",
        "market_context": "Market Context",
        "vix_spot": "VIX Spot",
        "vix_futures": "VIX Futures",
        "contango": "Contango",
        "key_dates": "Key Dates",
        "trade_simulation": "Trade Simulation",
        "trading_days_note": "Trading days shown (excl. weekends)",
        "since_listing": "Since Listing",
        "distance_to_be": "Distance to Breakeven",
        "no_vix_data": "VIX futures data not available. Re-run fetcher.",
        "time_progress": "Time Progress",
        "entry_label": "Entry",
        "expiry_label": "Expiry",
        "held_to_expiry": "held →",
        "to_expiry": "to expiry",
        "cal": "cal",
        "feb_entry": "Feb Entry",
        "mar_entry": "Mar Entry",
        "current_pnl": "At current futures",
        "analytics": "Analytics",
        "dist_tooltip": "Historical spread prices over selected period. Compare current price to mean for relative value.",
        "calc_tooltip": "Simulates P&L at expiration based on entry price. Uses VIX futures (not spot) as the underlying.",
        "futures_note": "Options settle to VIX futures, not spot",
    },
    "zh": {
        "page_title": "VIX价差终端",
        "header_subtitle": "VIX看涨期权价差监控",
        "header_title": "多到期日终端",
        "live_data": "静态数据",
        "configuration": "配置",
        "language": "语言",
        "active_spreads": "活跃价差",
        "select_expiries": "选择要监控的到期日",
        "data_settings": "数据设置",
        "historical_lookback": "历史回溯",
        "days": "天",
        "refresh": "重新加载CSV",
        "last_updated": "最新数据",
        "long_leg": "多头 (C20)",
        "short_leg": "空头 (C25)",
        "net_spread": "净价差",
        "volume": "成交量",
        "spread_title": "价差",
        "individual_legs": "单腿价格",
        "volume_title": "成交量",
        "mean": "均值",
        "feb_be_label": "2月保本",
        "mar_be_label": "3月保本",
        "long_leg_chart": "C20 (多头)",
        "short_leg_chart": "C25 (空头)",
        "view_daily_log": "📁 查看源数据",
        "no_file": "❌ 未找到 'vix_spread_data.csv'。请先运行 'data_fetcher_v2.py'。",
        "select_spread_warning": "请在侧边栏中选择至少一个价差到期日。",
        "cheap": "低估",
        "expensive": "高估",
        "fair": "合理",
        "valuation_title": "统计估值",
        "calc_title": "计算器：到期风险/回报",
        "inputs": "输入参数",
        "entry_price": "入场价格 (借方)",
        "stats": "统计数据",
        "max_profit": "最大利润",
        "max_risk": "最大风险",
        "rr_ratio": "盈亏比",
        "breakeven": "保本点",
        "chart_x": "到期时 VIX 期货价格",
        "chart_y": "利润 / 损失",
        "dist_title": "价格分布",
        "freq": "频率 (天数)",
        "now": "现价",
        "avg": "均值",
        "be_abbr": "保本",
        "pnl_title": "交易表现",
        "entry_date": "入场日期",
        "entry_px": "入场价",
        "current_px": "现价",
        "pnl": "盈亏",
        "pnl_pct": "回报率",
        "days_held": "持仓天数",
        "dte": "剩余天数",
        "trade_status": "状态",
        "profit": "盈利",
        "loss": "亏损",
        "flat": "持平",
        "trading": "交易日",
        "calendar": "日历日",
        "market_context": "市场概况",
        "vix_spot": "VIX 现货",
        "vix_futures": "VIX 期货",
        "contango": "升水",
        "key_dates": "关键日期",
        "trade_simulation": "交易模拟",
        "trading_days_note": "显示交易日（不含周末）",
        "since_listing": "自上市以来",
        "distance_to_be": "距离保本点",
        "no_vix_data": "VIX期货数据不可用，请重新运行数据获取程序。",
        "time_progress": "时间进度",
        "entry_label": "入场",
        "expiry_label": "到期",
        "held_to_expiry": "已持仓 →",
        "to_expiry": "后到期",
        "cal": "日历",
        "feb_entry": "二月入场价",
        "mar_entry": "三月入场价",
        "current_pnl": "当前期货价",
        "analytics": "分析",
        "dist_tooltip": "所选期间的历史价差价格。将当前价格与均值比较以判断相对价值。",
        "calc_tooltip": "根据入场价模拟到期盈亏。使用VIX期货（非现货）作为标的。",
        "futures_note": "期权以VIX期货结算，而非现货",
    }
}

# --- 4. SESSION STATE ---
if 'language' not in st.session_state:
    st.session_state.language = 'zh'

def t(key):
    return TRANSLATIONS[st.session_state.language].get(key, key)

# --- 5. ADAPTIVE CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
    
    .dashboard-header {
        background: linear-gradient(90deg, rgba(38,166,154,0.12) 0%, transparent 50%);
        border-bottom: 1px solid rgba(38,166,154,0.25);
        padding: 20px 30px;
        margin: -1rem -1rem 2rem -1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
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
        height: 100%;
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
    .delta-positive { color: #26a69a; background: rgba(38,166,154,0.15); }
    .delta-negative { color: #ef5350; background: rgba(239,83,80,0.15); }
    .delta-neutral { color: #9e9e9e; background: rgba(158,158,158,0.15); }
    
    .volume-text {
        font-family: 'JetBrains Mono', 'Noto Sans SC', monospace;
        font-size: 12px;
        margin-top: 8px;
        opacity: 0.7;
    }

    .val-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        padding: 4px 8px;
        border-radius: 4px;
        margin-top: 12px;
        display: inline-block;
        font-weight: 600;
    }
    .val-cheap { background: rgba(38,166,154,0.2); color: #26a69a; border: 1px solid rgba(38,166,154,0.4); }
    .val-expensive { background: rgba(239,83,80,0.2); color: #ef5350; border: 1px solid rgba(239,83,80,0.4); }
    .val-fair { background: rgba(158,158,158,0.2); color: #bdbdbd; border: 1px solid rgba(158,158,158,0.4); }
    
    /* Futures info box */
    .futures-info {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        padding: 8px 12px;
        border-radius: 6px;
        background: rgba(66, 165, 245, 0.1);
        border: 1px solid rgba(66, 165, 245, 0.3);
        color: #42a5f5;
        margin-top: 8px;
    }
    
    /* P&L Card Styles */
    .pnl-card {
        border-radius: 12px;
        padding: 14px 20px;
        margin: 10px 0;
        border: 1px solid rgba(128, 128, 128, 0.25);
        background: rgba(128, 128, 128, 0.06);
    }
    .pnl-card-profit {
        border: 1px solid rgba(38, 166, 154, 0.4);
        background: linear-gradient(135deg, rgba(38, 166, 154, 0.08) 0%, rgba(38, 166, 154, 0.02) 100%);
    }
    .pnl-card-loss {
        border: 1px solid rgba(239, 83, 80, 0.4);
        background: linear-gradient(135deg, rgba(239, 83, 80, 0.08) 0%, rgba(239, 83, 80, 0.02) 100%);
    }
    .pnl-header {
        font-family: 'Plus Jakarta Sans', 'Noto Sans SC', sans-serif;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 12px;
        opacity: 0.8;
    }
    
    /* Custom Tooltip Styles */
    .tooltip-container {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    .tooltip-container .tooltip-text {
        visibility: hidden;
        opacity: 0;
        width: 280px;
        background: #4a4a4a;
        color: #ffffff;
        text-align: left;
        border-radius: 8px;
        padding: 14px 16px;
        position: absolute;
        z-index: 1000;
        top: 140%;
        left: 50%;
        transform: translateX(-50%);
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        line-height: 1.6;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
        border: 1px solid #5a5a5a;
        transition: opacity 0.2s ease, visibility 0.2s ease;
        white-space: normal;
        word-wrap: break-word;
    }
    .tooltip-container .tooltip-text::after {
        content: "";
        position: absolute;
        bottom: 100%;
        left: 50%;
        margin-left: -6px;
        border-width: 6px;
        border-style: solid;
        border-color: transparent transparent #4a4a4a transparent;
    }
    .tooltip-container:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    .tooltip-label {
        color: rgba(255, 255, 255, 0.7);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .tooltip-value {
        font-weight: 600;
        font-size: 13px;
        color: #ffffff;
    }
    .tooltip-hint {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6);
    }
</style>
""", unsafe_allow_html=True)

# --- 6. DATA LOADER ---
@st.cache_data
def load_data(csv_path):
    if not csv_path.exists():
        return None
    try:
        df = pd.read_csv(csv_path)
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        cols_to_convert = [c for c in df.columns if c != "Date"]
        for col in cols_to_convert:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Clean data: Remove rows where spread data is 0 or missing
        spread_cols = [col for col in df.columns if col.endswith("_Spread")]
        for col in spread_cols:
            df.loc[df[col] == 0, col] = pd.NA
        
        if spread_cols:
            df = df.dropna(subset=spread_cols, how='all')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# --- P&L CALCULATION HELPER ---
def calculate_pnl(entry_price: float, current_price: float, entry_date: str, current_date: str, expiry_date: str):
    """Calculate P&L metrics for a trade."""
    pnl = current_price - entry_price
    pnl_pct = (pnl / entry_price) * 100 if entry_price > 0 else 0
    
    entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
    current_dt = datetime.strptime(current_date, "%Y-%m-%d")
    expiry_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
    
    days_held_cal = (current_dt - entry_dt).days
    dte_cal = (expiry_dt - current_dt).days
    days_held_trd = int(np.busday_count(entry_date, current_date))
    dte_trd = int(np.busday_count(current_date, expiry_date))
    
    return {
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "days_held_cal": days_held_cal,
        "days_held_trd": days_held_trd,
        "dte_cal": dte_cal,
        "dte_trd": dte_trd,
    }

# --- ANALYTICS HELPER ---
def calculate_valuation(series: pd.Series, current_value: float):
    if series.empty or len(series) < 5:
        return 0.0, 50.0
    mean = series.mean()
    std = series.std()
    z_score = (current_value - mean) / std if std != 0 else 0
    percentile = (series < current_value).mean() * 100
    return z_score, percentile

# --- 7. CHART FUNCTION ---
def create_spread_chart(df: pd.DataFrame, spread_name: str, lang: str, entry_price: float = None, entry_date: str = None):
    prefix = SPREADS_CONFIG[spread_name]["prefix"]
    
    if f"{prefix}_Spread" not in df.columns:
        return go.Figure()

    plot_df = pd.DataFrame(index=df["Date"])
    plot_df["Spread"] = df[f"{prefix}_Spread"].values
    plot_df["Long"] = df[f"{prefix}_Long_Price"].values
    plot_df["Short"] = df[f"{prefix}_Short_Price"].values
    plot_df["Volume"] = df[f"{prefix}_Total_Volume"].values
    plot_df = plot_df.apply(pd.to_numeric, errors='coerce')
    
    has_volume = plot_df["Volume"].sum() > 0

    spread_label = TRANSLATIONS[lang]["spread_title"]
    legs_label = TRANSLATIONS[lang]["individual_legs"]
    volume_label = TRANSLATIONS[lang]["volume_title"]
    mean_label = TRANSLATIONS[lang]["mean"]
    long_leg_label = TRANSLATIONS[lang]["long_leg_chart"]
    short_leg_label = TRANSLATIONS[lang]["short_leg_chart"]
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

    # 1. Spread Trace
    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df["Spread"],
        mode='lines', name=spread_label,
        line=dict(color='#26a69a', width=2.5),
        fill='tozeroy', fillcolor='rgba(38,166,154,0.15)',
        hovertemplate=f'<b>{spread_label}</b>: %{{y:.2f}}<extra></extra>'
    ), row=1, col=1)

    # Mean Line
    mean_val = plot_df["Spread"].mean()
    fig.add_hline(y=mean_val, line_dash="dash", line_color="#9e9e9e",
                 annotation_text=f"{mean_label}: {mean_val:.2f}",
                 annotation_position="right",
                 annotation_font=dict(size=10, color="#9e9e9e"),
                 row=1, col=1)

    # Entry Price Line
    if entry_price is not None:
        entry_label = "Entry" if lang == "en" else "入场"
        fig.add_hline(
            y=entry_price, 
            line_dash="dot", 
            line_color="#ffa726",
            annotation_text=f"{entry_label}: {entry_price:.2f}",
            annotation_position="right",
            annotation_font=dict(size=10, color="#ffa726"),
            row=1, col=1
        )
    
    # Entry Date Vertical Line
    if entry_date is not None:
        entry_dt = pd.to_datetime(entry_date)
        fig.add_vline(
            x=entry_dt,
            line_dash="dot",
            line_color="#ffa726",
            line_width=1,
            row=1, col=1
        )

    # 2. Legs Traces
    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df["Long"], mode='lines', name=long_leg_label,
        line=dict(color='#42a5f5', width=1.5)
    ), row=2, col=1)
    
    fig.add_trace(go.Scatter(
        x=plot_df.index, y=plot_df["Short"], mode='lines', name=short_leg_label,
        line=dict(color='#ab47bc', width=1.5)
    ), row=2, col=1)

    # 3. Volume Trace
    if has_volume:
        fig.add_trace(go.Bar(
            x=plot_df.index, y=plot_df["Volume"], name=volume_label,
            marker_color='rgba(38,166,154,0.5)'
        ), row=3, col=1)

    fig.update_layout(
        height=550 if has_volume else 450,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="JetBrains Mono, Noto Sans SC, monospace", size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor='rgba(0,0,0,0)'),
        margin=dict(l=60, r=100, t=80, b=50),
        hovermode='x unified',
        showlegend=True
    )
    fig.update_xaxes(gridcolor='rgba(128,128,128,0.2)', showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor='rgba(128,128,128,0.2)', showgrid=True, zeroline=False)
    fig.update_yaxes(showticklabels=True, row=1, col=1)
    fig.update_yaxes(showticklabels=True, row=2, col=1)
    
    if has_volume:
        max_vol = plot_df["Volume"].max()
        fig.update_yaxes(showticklabels=True, range=[0, max_vol * 1.1], row=3, col=1)
    
    return fig

# --- HISTOGRAM FUNCTION ---
def create_distribution_chart(df, prefix, current_val, lang):
    spread_data = df[f"{prefix}_Spread"].dropna()
    mean_val = spread_data.mean()
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=spread_data, name='History', nbinsx=25,
        marker_color='rgba(128, 128, 128, 0.3)', marker_line_color='rgba(128, 128, 128, 0.5)', marker_line_width=1
    ))
    
    fig.add_vline(x=current_val, line_width=3, line_color="#26a69a" if current_val < mean_val else "#ef5350")
    fig.add_vline(x=mean_val, line_dash="dash", line_width=1, line_color="#ffa726")
    
    avg_text = TRANSLATIONS[lang]["avg"]
    fig.add_annotation(x=mean_val, y=1.02, yref="paper", text=f"{avg_text}: {mean_val:.2f}", showarrow=False, font=dict(color="#ffa726", size=10))

    now_text = TRANSLATIONS[lang]["now"]
    fig.add_annotation(x=current_val, y=0.9, yref="paper", text=f"{now_text}: {current_val:.2f}", showarrow=True, arrowhead=2, ax=0, ay=-20, font=dict(color="#ffffff", size=12), bgcolor="rgba(0,0,0,0.6)")

    fig.update_layout(
        height=380, 
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
        font=dict(family="JetBrains Mono, monospace", size=11), 
        xaxis_title=TRANSLATIONS[lang]["spread_title"], 
        yaxis_title=TRANSLATIONS[lang]["freq"], 
        showlegend=False, bargap=0.05
    )
    fig.update_xaxes(gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(gridcolor='rgba(128,128,128,0.2)')
    return fig

# --- PAYOFF CALCULATOR CHART (Updated to use VIX Futures) ---
def create_payoff_chart(entry_price, lang, current_futures=None):
    """
    Payoff chart using VIX FUTURES as x-axis (not spot).
    VIX options settle to futures at expiration.
    """
    K1 = 20  # Long call strike
    K2 = 25  # Short call strike
    
    futures_prices = list(range(10, 50, 1))
    pnl = []
    
    for f in futures_prices:
        val_long = max(f - K1, 0)
        val_short = max(f - K2, 0)
        spread_val = val_long - val_short
        profit = spread_val - entry_price
        pnl.append(profit)
        
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=futures_prices, y=pnl,
        mode='lines', name='P&L',
        line=dict(color='#ffffff', width=2),
        fill='tozeroy', 
        fillcolor='rgba(255, 255, 255, 0.1)'
    ))

    fig.add_hline(y=0, line_dash="solid", line_color="#9e9e9e", line_width=1)
    
    breakeven = K1 + entry_price
    
    t_x = TRANSLATIONS[lang]["chart_x"]
    t_y = TRANSLATIONS[lang]["chart_y"]
    
    be_text = TRANSLATIONS[lang]["be_abbr"]
    fig.add_vline(x=breakeven, line_dash="dash", line_color="#ffa726", 
                  annotation_text=f"{be_text}: {breakeven:.2f}", annotation_position="top right",
                  annotation_font=dict(color="#ffa726", size=10))
    
    # Add current FUTURES marker (not spot!)
    if current_futures is not None:
        futures_label = "Futures" if lang == "en" else "期货"
        fig.add_vline(x=current_futures, line_dash="dot", line_color="#42a5f5", line_width=2,
                      annotation_text=f"{futures_label}: {current_futures:.2f}", annotation_position="bottom left",
                      annotation_font=dict(color="#42a5f5", size=10))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_title=t_x,
        yaxis_title=t_y,
        font=dict(family="JetBrains Mono, monospace", size=11),
        hovermode="x unified"
    )
    
    fig.add_shape(type="rect", x0=10, y0=0, x1=50, y1=15, 
                  fillcolor="rgba(38,166,154,0.1)", layer="below", line_width=0)
    fig.add_shape(type="rect", x0=10, y0=-15, x1=50, y1=0, 
                  fillcolor="rgba(239,83,80,0.1)", layer="below", line_width=0)

    return fig

# --- 8. SIDEBAR ---

# Initialize session state for trade simulation
if 'trade_entry_date' not in st.session_state:
    st.session_state.trade_entry_date = datetime.strptime("2026-01-16", "%Y-%m-%d").date()
if 'feb_entry_price' not in st.session_state:
    st.session_state.feb_entry_price = 0.63
if 'mar_entry_price' not in st.session_state:
    st.session_state.mar_entry_price = 0.91

today = datetime.now().date()

# Load data early
full_df = load_data(CSV_PATH)

# --- UPDATED: Check for VIX Futures data instead of spot ---
def get_futures_data(df, spread_name):
    """Get VIX futures data for a specific spread."""
    if df is None:
        return None, None, None
    
    futures_col = SPREADS_CONFIG[spread_name]["futures_col"]
    
    if futures_col not in df.columns:
        return None, None, None
    
    latest_val = df.iloc[-1][futures_col]
    prev_val = df.iloc[-2][futures_col] if len(df) > 1 else latest_val
    
    # Handle NaN and 0 values
    if pd.isna(latest_val) or latest_val == 0:
        return None, None, None
    
    if pd.isna(prev_val):
        prev_val = latest_val
    
    change = latest_val - prev_val
    return float(latest_val), float(prev_val), float(change)

# Get VIX spot for context (optional) - only if it's valid (non-zero)
vix_spot_available = False
latest_vix_spot = None
if full_df is not None and "VIX_Spot" in full_df.columns:
    spot_val = full_df.iloc[-1]["VIX_Spot"]
    if not pd.isna(spot_val) and spot_val > 0:
        latest_vix_spot = float(spot_val)
        vix_spot_available = True

# Get futures for each spread
feb_futures, feb_futures_prev, feb_futures_change = get_futures_data(full_df, "Feb 2026")
mar_futures, mar_futures_prev, mar_futures_change = get_futures_data(full_df, "Mar 2026")

# Debug output (can remove later)
# st.write(f"DEBUG: Feb Futures = {feb_futures}, Mar Futures = {mar_futures}, VIX Spot = {latest_vix_spot}")

with st.sidebar:
    # Language toggle
    col_title, col_lang = st.columns([3, 1])
    with col_title:
        st.markdown(f"## ⚙️ {t('configuration')}")
    with col_lang:
        if st.session_state.language == 'en':
            if st.button("中文", key='lang_zh', width='stretch'):
                st.session_state.language = 'zh'
                st.rerun()
        else:
            if st.button("EN", key='lang_en', width='stretch'):
                st.session_state.language = 'en'
                st.rerun()
    
    st.markdown("---")
    
    # Trade Simulation
    st.markdown(f"### 💼 {t('trade_simulation')}")
    
    trade_entry_date = st.date_input(
        t('entry_date'),
        value=st.session_state.trade_entry_date,
        min_value=datetime.strptime("2025-10-01", "%Y-%m-%d").date(),
        max_value=today,
        key="entry_date_input"
    )
    st.session_state.trade_entry_date = trade_entry_date
    
    col_feb_entry, col_mar_entry = st.columns(2)
    with col_feb_entry:
        feb_entry = st.number_input(
            t('feb_entry'),
            min_value=0.0, max_value=5.0,
            value=st.session_state.feb_entry_price,
            step=0.01, format="%.2f",
            key="feb_entry_input"
        )
        st.session_state.feb_entry_price = feb_entry
    
    with col_mar_entry:
        mar_entry = st.number_input(
            t('mar_entry'),
            min_value=0.0, max_value=5.0,
            value=st.session_state.mar_entry_price,
            step=0.01, format="%.2f",
            key="mar_entry_input"
        )
        st.session_state.mar_entry_price = mar_entry
    
    st.markdown("---")
    
    # Data Settings
    st.markdown(f"### ⚙️ {t('data_settings')}")
    
    lookback_days = st.selectbox(
        t('historical_lookback'),
        options=[30, 60, 90, 180, 9999],
        index=2,
        format_func=lambda x: f"{x} {t('days')}" if x < 9999 else t('since_listing')
    )
    
    st.markdown("")
    
    if st.button(t('refresh'), width='stretch'):
        st.cache_data.clear()
        st.rerun()

active_spreads = SPREAD_KEYS.copy()

# Build TRADE_CONFIG
TRADE_CONFIG = {
    "Feb 2026": {
        "entry_date": st.session_state.trade_entry_date.strftime("%Y-%m-%d"),
        "entry_price": st.session_state.feb_entry_price,
        "expiry_date": "2026-02-18",
    },
    "Mar 2026": {
        "entry_date": st.session_state.trade_entry_date.strftime("%Y-%m-%d"),
        "entry_price": st.session_state.mar_entry_price,
        "expiry_date": "2026-03-18",
    },
}

# --- UPDATED: Calculate breakeven distances using FUTURES ---
feb_be = 20 + st.session_state.feb_entry_price
mar_be = 20 + st.session_state.mar_entry_price

# Use corresponding futures for each spread's breakeven calculation
feb_distance = ((feb_be - feb_futures) / feb_futures) * 100 if feb_futures and feb_futures > 0 else None
mar_distance = ((mar_be - mar_futures) / mar_futures) * 100 if mar_futures and mar_futures > 0 else None

# --- 9. MAIN DASHBOARD ---

# Header with VIX Futures info
futures_available = feb_futures is not None or mar_futures is not None

# Build header HTML
header_parts = []
header_parts.append(f'<div class="header-subtitle">{t("header_subtitle")}</div>')
header_parts.append(f'<div class="header-title">{t("header_title")}</div>')

# Build futures section
futures_section = ""
if futures_available:
    futures_items = []
    
    # VIX Spot (only if valid)
    if vix_spot_available and latest_vix_spot and latest_vix_spot > 0:
        futures_items.append(f'<div style="text-align:center;"><div style="opacity:0.6;font-size:10px;">VIX SPOT</div><div style="font-size:18px;font-weight:600;">{latest_vix_spot:.2f}</div></div>')
    
    # Feb Futures
    if feb_futures and feb_futures > 0:
        f_color = "#26a69a" if feb_futures_change >= 0 else "#ef5350"
        f_arrow = "+" if feb_futures_change >= 0 else ""
        futures_items.append(f'<div style="text-align:center;"><div style="opacity:0.6;font-size:10px;">FEB UXG26</div><div style="font-size:18px;font-weight:600;">{feb_futures:.2f}</div><div style="font-size:11px;color:{f_color};">{f_arrow}{feb_futures_change:.2f}</div></div>')
    
    # Mar Futures
    if mar_futures and mar_futures > 0:
        f_color = "#26a69a" if mar_futures_change >= 0 else "#ef5350"
        f_arrow = "+" if mar_futures_change >= 0 else ""
        futures_items.append(f'<div style="text-align:center;"><div style="opacity:0.6;font-size:10px;">MAR UXH26</div><div style="font-size:18px;font-weight:600;">{mar_futures:.2f}</div><div style="font-size:11px;color:{f_color};">{f_arrow}{mar_futures_change:.2f}</div></div>')
    
    if futures_items:
        futures_section = '<div style="display:flex;gap:24px;font-family:monospace;">' + ''.join(futures_items) + '</div>'

# Build breakeven section
be_section = ""
be_items = []
if feb_futures and feb_futures > 0 and feb_distance is not None:
    be_color = "#ef5350" if feb_distance > 0 else "#26a69a"
    be_items.append(f'{t("feb_be_label")}: <span style="color:{be_color};">{feb_be:.2f} ({feb_distance:+.1f}%)</span>')
if mar_futures and mar_futures > 0 and mar_distance is not None:
    be_color = "#ef5350" if mar_distance > 0 else "#26a69a"
    be_items.append(f'{t("mar_be_label")}: <span style="color:{be_color};">{mar_be:.2f} ({mar_distance:+.1f}%)</span>')
if be_items:
    be_section = '<div style="font-family:monospace;font-size:11px;">' + ' | '.join(be_items) + '</div>'

# Render header
st.markdown(f'''
<div class="dashboard-header">
    <div>
        <div class="header-subtitle">{t("header_subtitle")}</div>
        <div class="header-title">{t("header_title")}</div>
    </div>
    {futures_section}
    {be_section}
    <div class="live-badge">
        <div class="live-dot"></div>
        {t("live_data")}
    </div>
</div>
''', unsafe_allow_html=True)

if full_df is None or full_df.empty:
    st.error(t('no_file'))
    st.stop()

# Filter by lookback
if lookback_days < 9999:
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=lookback_days)
    df_chart = full_df[full_df["Date"] >= cutoff]
else:
    df_chart = full_df

latest = full_df.iloc[-1]
prev = full_df.iloc[-2] if len(full_df) > 1 else latest
current_date_str = latest['Date'].strftime('%Y-%m-%d')

st.caption(f"{t('last_updated')}: {current_date_str}")

# --- TABS & METRICS ---
tab_names = [SPREADS_CONFIG_NAMES[st.session_state.language][s] for s in active_spreads]
tabs = st.tabs(tab_names)

for tab, spread_name in zip(tabs, active_spreads):
    with tab:
        prefix = SPREADS_CONFIG[spread_name]["prefix"]
        
        # Get current futures for this spread from the config
        futures_col = SPREADS_CONFIG[spread_name]["futures_col"]
        futures_ticker = SPREADS_CONFIG[spread_name]["futures_ticker"]
        
        # Get current futures value - handle NaN and 0
        current_futures = None
        prev_futures_val = None
        if futures_col in full_df.columns:
            fut_val = latest.get(futures_col, None)
            if fut_val is not None and not pd.isna(fut_val) and fut_val > 0:
                current_futures = float(fut_val)
                # Get previous futures value
                prev_fut = prev.get(futures_col, None)
                if prev_fut is not None and not pd.isna(prev_fut) and prev_fut > 0:
                    prev_futures_val = float(prev_fut)
                else:
                    prev_futures_val = current_futures
        
        # 1. PREPARE DATA
        def get_val(row, key, default=0.0):
            val = row.get(key, default)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return default
            return float(val)
            
        cur_long = get_val(latest, f"{prefix}_Long_Price")
        cur_short = get_val(latest, f"{prefix}_Short_Price")
        cur_spread = get_val(latest, f"{prefix}_Spread")
        cur_l_vol = get_val(latest, f"{prefix}_Long_Volume")
        cur_s_vol = get_val(latest, f"{prefix}_Short_Volume")
        
        prev_long = get_val(prev, f"{prefix}_Long_Price")
        prev_short = get_val(prev, f"{prefix}_Short_Price")
        prev_spread = get_val(prev, f"{prefix}_Spread")
        
        d_long = cur_long - prev_long
        d_short = cur_short - prev_short
        d_spread = cur_spread - prev_spread
        
        # Calculate Valuation
        spread_history = df_chart[f"{prefix}_Spread"].dropna()
        z_score, percentile = calculate_valuation(spread_history, cur_spread)

        # 2. RENDER METRICS (4 COLUMNS - added futures)
        c1, c2, c3, c4 = st.columns(4)
        
        def render_metric(col, label, val, delta, vol=None, is_futures=False):
            delta_cls = "positive" if delta > 0 else "negative" if delta < 0 else "neutral"
            sign = "+" if delta > 0 else ""
            arrow = "▲" if delta > 0 else "▼" if delta < 0 else "−"
            
            html = [
                f'<div class="metric-card">',
                f'<div class="metric-label">{label}</div>',
                f'<div class="metric-value">{val:.2f}</div>',
                f'<div class="metric-delta delta-{delta_cls}">{arrow} {sign}{delta:.2f}</div>'
            ]
            if vol is not None:
                html.append(f'<div class="volume-text">{t("volume")}: {int(vol):,}</div>')
            else:
                html.append('<div class="volume-text">&nbsp;</div>')
            html.append('</div>')
            col.markdown("".join(html), unsafe_allow_html=True)
        
        # Show VIX Futures for this spread (FIRST COLUMN)
        if current_futures is not None and current_futures > 0:
            d_futures = current_futures - prev_futures_val if prev_futures_val else 0
            render_metric(c1, f"{t('vix_futures')} ({futures_ticker})", current_futures, d_futures, is_futures=True)
        else:
            c1.markdown(f"""
            <div class="metric-card" style="border-color: rgba(239, 83, 80, 0.4);">
                <div class="metric-label">{t('vix_futures')} ({futures_ticker})</div>
                <div class="metric-value" style="font-size: 20px; opacity: 0.5;">N/A</div>
                <div class="volume-text" style="color: #ef5350;">{t('no_vix_data')}</div>
            </div>
            """, unsafe_allow_html=True)
            
        render_metric(c2, t('long_leg'), cur_long, d_long, cur_l_vol)
        render_metric(c3, t('short_leg'), cur_short, d_short, cur_s_vol)
        render_metric(c4, t('net_spread'), cur_spread, d_spread)
        
        # 3. VALUATION LINE
        if z_score <= -1.0: status = t('cheap')
        elif z_score >= 1.0: status = t('expensive')
        else: status = t('fair')
        
        if st.session_state.language == 'en':
            stat_tooltip_label = "How to read this"
            stat_tooltip_line1 = "<b>Z-score:</b> Distance from average (in std deviations)"
            stat_tooltip_line2 = "<b>Percentile:</b> % of historical prices that were lower"
            stat_tooltip_line3 = "<b>CHEAP:</b> Z ≤ -1 | <b>FAIR:</b> -1 to 1 | <b>RICH:</b> Z ≥ 1"
        else:
            stat_tooltip_label = "如何解读"
            stat_tooltip_line1 = "<b>Z分数:</b> 与均值的距离（以标准差计）"
            stat_tooltip_line2 = "<b>百分位:</b> 历史上低于当前价格的比例"
            stat_tooltip_line3 = "<b>低估:</b> Z ≤ -1 | <b>合理:</b> -1 到 1 | <b>高估:</b> Z ≥ 1"
            
        st.markdown(f"""
        <div style="text-align: left; margin-top: 8px; margin-bottom: 16px;">
            <span class="tooltip-container">
                <span class="volume-text" style="cursor: help;">
                    {t('valuation_title')}: <b>{status}</b> (Z-score: {z_score:.1f}σ | Percentile: {int(percentile)}%) ⓘ
                </span>
                <span class="tooltip-text" style="width: 280px;">
                    <div class="tooltip-label">{stat_tooltip_label}</div>
                    <div style="font-size: 11px; line-height: 1.8;">{stat_tooltip_line1}</div>
                    <div style="font-size: 11px; line-height: 1.8;">{stat_tooltip_line2}</div>
                    <div class="tooltip-hint">{stat_tooltip_line3}</div>
                </span>
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # --- P&L TRACKING SECTION ---
        trade_conf = TRADE_CONFIG.get(spread_name)
        if trade_conf:
            pnl_data = calculate_pnl(
                entry_price=trade_conf["entry_price"],
                current_price=cur_spread,
                entry_date=trade_conf["entry_date"],
                current_date=current_date_str,
                expiry_date=trade_conf["expiry_date"]
            )
            
            if pnl_data["pnl"] > 0.01:
                pnl_color = "#26a69a"
            elif pnl_data["pnl"] < -0.01:
                pnl_color = "#ef5350"
            else:
                pnl_color = "#9e9e9e"
            
            pnl_sign = "+" if pnl_data["pnl"] >= 0 else ""
            pct_sign = "+" if pnl_data["pnl_pct"] >= 0 else ""
            
            total_days = pnl_data['days_held_cal'] + pnl_data['dte_cal']
            progress_pct = (pnl_data['days_held_cal'] / total_days * 100) if total_days > 0 else 0
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; border: 1px solid rgba(128,128,128,0.25); border-radius: 8px; background: rgba(128,128,128,0.06); margin-bottom: 8px;">
                <span style="font-size: 12px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; opacity: 0.8;">📊 {t('pnl_title')}</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px; opacity: 0.6;">{pnl_data['days_held_trd']}d {t('held_to_expiry')} {pnl_data['dte_trd']}d {t('to_expiry')}</span>
            </div>
            """, unsafe_allow_html=True)
            
            col_entry, col_pnl, col_time = st.columns([1, 1.2, 1])
            
            with col_entry:
                st.markdown(f"""
                <div style="padding: 0 8px;">
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(128,128,128,0.2);">
                        <span style="font-size: 11px; opacity: 0.6; text-transform: uppercase;">{t('entry_date')}</span>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 14px;">{trade_conf['entry_date']}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(128,128,128,0.2);">
                        <span style="font-size: 11px; opacity: 0.6; text-transform: uppercase;">{t('entry_px')}</span>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 14px;">{trade_conf['entry_price']:.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 8px 0;">
                        <span style="font-size: 11px; opacity: 0.6; text-transform: uppercase;">{t('current_px')}</span>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 14px;">{cur_spread:.2f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_pnl:
                st.markdown(f"""
                <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; background: rgba(128,128,128,0.1); border-radius: 8px; padding: 16px; height: 100%; min-height: 100px;">
                    <div style="font-size: 11px; opacity: 0.6; text-transform: uppercase; margin-bottom: 6px;">{t('pnl')}</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 700; color: {pnl_color};">{pnl_sign}{pnl_data['pnl']:.2f}</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 16px; color: {pnl_color}; margin-top: 4px;">{pct_sign}{pnl_data['pnl_pct']:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_time:
                st.markdown(f"""
                <div style="padding: 0 8px;">
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(128,128,128,0.2);">
                        <span style="font-size: 11px; opacity: 0.6; text-transform: uppercase;">{t('days_held')}</span>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 14px;">{pnl_data['days_held_trd']}d <span style="opacity:0.5;">({pnl_data['days_held_cal']} {t('cal')})</span></span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(128,128,128,0.2);">
                        <span style="font-size: 11px; opacity: 0.6; text-transform: uppercase;">{t('dte')}</span>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 14px;">{pnl_data['dte_trd']}d <span style="opacity:0.5;">({pnl_data['dte_cal']} {t('cal')})</span></span>
                    </div>
                    <div style="padding: 8px 0;">
                        <div style="font-size: 10px; opacity: 0.5; margin-bottom: 6px;">{t('time_progress')}</div>
                        <div style="background: rgba(128,128,128,0.2); border-radius: 4px; height: 6px; overflow: hidden;">
                            <div style="background: {pnl_color}; height: 100%; width: {progress_pct:.1f}%; border-radius: 4px;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 9px; opacity: 0.4; margin-top: 4px;">
                            <span>{t('entry_label')}</span>
                            <span>{t('expiry_label')}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 4. CHART
        chart_entry_price = trade_conf["entry_price"] if trade_conf else None
        chart_entry_date = trade_conf["entry_date"] if trade_conf else None
        fig = create_spread_chart(df_chart, spread_name, st.session_state.language, chart_entry_price, chart_entry_date)
        st.plotly_chart(fig, use_container_width=True, key=f"main_chart_{prefix}")

        # --- ANALYTICS SECTION ---
        with st.expander(f"📊 {t('analytics')}", expanded=True):
            col_hist, col_calc = st.columns(2)
            
            with col_hist:
                lookback_label = f"{lookback_days} {t('days')}" if lookback_days < 9999 else t('since_listing')
                st.markdown(f"""
                <span class="tooltip-container">
                    <span style="font-weight: 600; cursor: help;">{t('dist_title')} ({lookback_label}) ⓘ</span>
                    <span class="tooltip-text" style="width: 260px;">
                        <div class="tooltip-label">{t('dist_title')}</div>
                        <div style="font-size: 11px; line-height: 1.6;">{t('dist_tooltip')}</div>
                    </span>
                </span>
                """, unsafe_allow_html=True)
                hist_fig = create_distribution_chart(df_chart, prefix, cur_spread, st.session_state.language)
                st.plotly_chart(hist_fig, use_container_width=True, key=f"hist_{prefix}")

            with col_calc:
                st.markdown(f"""
                <span class="tooltip-container">
                    <span style="font-weight: 600; cursor: help;">{t('calc_title')} ⓘ</span>
                    <span class="tooltip-text" style="width: 260px;">
                        <div class="tooltip-label">{t('calc_title')}</div>
                        <div style="font-size: 11px; line-height: 1.6;">{t('calc_tooltip')}</div>
                    </span>
                </span>
                """, unsafe_allow_html=True)
                
                # Note about futures vs spot
                st.caption(f"ℹ️ {t('futures_note')}")
                
                default_entry = trade_conf["entry_price"] if trade_conf else float(cur_spread)
                sim_key = f"sim_{prefix}"
                
                if sim_key not in st.session_state:
                    st.session_state[sim_key] = default_entry
                
                sim_entry = st.number_input(
                    t('entry_price'), 
                    min_value=0.0, max_value=10.0, 
                    value=st.session_state[sim_key], step=0.05, format="%.2f", 
                    key=f"sim_input_{prefix}"
                )
                st.session_state[sim_key] = sim_entry
                
                spread_width = 5.0
                max_profit = spread_width - sim_entry
                max_loss = sim_entry
                rr_ratio = max_profit / max_loss if max_loss > 0 else 0
                breakeven = 20 + sim_entry
                
                # --- UPDATED: Calculate P&L at current FUTURES (not spot) ---
                if current_futures is not None:
                    if current_futures <= 20:
                        pnl_at_futures = -sim_entry
                    elif current_futures >= 25:
                        pnl_at_futures = spread_width - sim_entry
                    else:
                        pnl_at_futures = (current_futures - 20) - sim_entry
                    pnl_color = "#26a69a" if pnl_at_futures >= 0 else "#ef5350"
                    pnl_sign = "+" if pnl_at_futures >= 0 else ""
                else:
                    pnl_at_futures = None

                st.markdown(f"""
                <div style="font-size: 13px; margin: 8px 0; line-height: 1.6;">
                    <span style="color: #26a69a;">{t('max_profit')}: <b>+{max_profit:.2f}</b></span>
                    <span style="opacity: 0.4; margin: 0 8px;">|</span>
                    <span style="color: #ef5350;">{t('max_risk')}: <b>-{max_loss:.2f}</b></span>
                    <span style="opacity: 0.4; margin: 0 8px;">|</span>
                    <span>R/R: <b>1:{rr_ratio:.1f}</b></span>
                    <span style="opacity: 0.4; margin: 0 8px;">|</span>
                    <span style="color: #ffa726;">BE: <b>{breakeven:.2f}</b></span>
                </div>
                """, unsafe_allow_html=True)
                
                # Show P&L at current FUTURES
                if pnl_at_futures is not None:
                    st.markdown(f"""
                    <div style="font-size: 12px; margin: 4px 0 8px 0; opacity: 0.8;">
                        {t('current_pnl')} ({futures_ticker}: {current_futures:.2f}): <span style="color: {pnl_color}; font-weight: 600;">{pnl_sign}{pnl_at_futures:.2f}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # --- UPDATED: Payoff chart uses futures price ---
                payoff_fig = create_payoff_chart(sim_entry, st.session_state.language, current_futures)
                payoff_fig.update_layout(height=220, margin=dict(t=10, b=20))
                st.plotly_chart(payoff_fig, use_container_width=True, key=f"payoff_{prefix}")

# --- DATA TABLE ---
st.markdown("---")
with st.expander(t('view_daily_log'), expanded=False):
    st.dataframe(full_df.sort_values("Date", ascending=False), use_container_width=True)