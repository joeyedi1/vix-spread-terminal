import streamlit as st
import pandas as pd
from xbbg import blp
import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="VIX Monitor", layout="wide")
st.title("⚡ VIX Strategy Monitor (Debug Mode)")

# Check 1: Verify Streamlit is drawing
st.write("✅ **System Status:** Dashboard has started loading...")

# --- INPUTS ---
col_sidebar1, col_sidebar2 = st.columns(2)
with col_sidebar1:
    long_leg = st.text_input("Long Leg", "VIX US 02/18/26 C20 Index")
with col_sidebar2:
    short_leg = st.text_input("Short Leg", "VIX US 02/18/26 C30 Index")

# --- DATA FETCHING WITH FEEDBACK ---
st.write("---")
st.write(f"🔄 **Attempting to fetch data for:** `{long_leg}` and `{short_leg}`...")

def get_price_safe(ticker):
    try:
        # Fetch data
        df = blp.bdp(ticker, 'PX_LAST')
        
        # DEBUG: Show raw data if it exists
        if df.empty:
            st.warning(f"⚠️ No data returned for {ticker}. Market might be closed or ticker format is wrong.")
            return None
        
        price = df.iloc[0, 0]
        return price
    except Exception as e:
        st.error(f"❌ Error fetching {ticker}: {e}")
        return None

# Fetch Prices
long_price = get_price_safe(long_leg)
short_price = get_price_safe(short_leg)

# --- DISPLAY RESULTS ---
col1, col2, col3 = st.columns(3)

if long_price is not None:
    col1.metric("Long Leg Price", f"{long_price:.2f}")
else:
    col1.metric("Long Leg", "No Data")

if short_price is not None:
    col2.metric("Short Leg Price", f"{short_price:.2f}")
else:
    col2.metric("Short Leg", "No Data")

if long_price is not None and short_price is not None:
    spread = long_price - short_price
    col3.metric("NET SPREAD COST", f"{spread:.2f}", delta_color="inverse")
    st.success(f"✅ **Success!** The spread is trading at {spread:.2f}")
else:
    st.info("Waiting for valid price data...")

# --- TEST BUTTON (Sanity Check) ---
st.write("---")
if st.button("Test Connection with SPY (Click Me)"):
    test_price = get_price_safe("SPY US Equity")
    st.write(f"Test Result: SPY is trading at {test_price}")