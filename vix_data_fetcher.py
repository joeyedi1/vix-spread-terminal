import blpapi
import pandas as pd
import datetime
import time
import subprocess
from pathlib import Path

# --- CONFIGURATION ---
CSV_PATH = Path("vix_spread_data.csv")
START_DATE = "20251001"  # Adjusted for 90-day lookback

# Debug mode - set to True to see what Bloomberg returns
DEBUG_MODE = False

# VIX Spot Index
VIX_SPOT_TICKER = "VIX Index"

SPREADS_CONFIG = {
    "Feb 2026": {
        "expiry": "02/18/26",
        "long": "VIX US 02/18/26 C20 Index",
        "short": "VIX US 02/18/26 C25 Index",
    },
    "Mar 2026": {
        "expiry": "03/18/26",
        "long": "VIX US 03/18/26 C20 Index",
        "short": "VIX US 03/18/26 C25 Index",
    },
}

# --- BLOOMBERG ENGINE ---
class BloombergEngine:
    def __init__(self):
        self.session = None
        self._connect()
    
    def _connect(self):
        print("Connecting to Bloomberg Terminal...")
        options = blpapi.SessionOptions()
        options.setServerHost("localhost")
        options.setServerPort(8194)
        self.session = blpapi.Session(options)
        if not self.session.start():
            raise ConnectionError("Failed to start Bloomberg session")
        if not self.session.openService("//blp/refdata"):
            raise ConnectionError("Failed to open //blp/refdata service")
        print("Connected.\n")

    def get_history(self, tickers: list, start_date: str) -> pd.DataFrame:
        print(f"Fetching history for {len(tickers)} tickers from {start_date}...")
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("HistoricalDataRequest")
        
        for ticker in tickers:
            request.append("securities", ticker)
        
        # --- FIELD PRIORITY FOR VIX OPTIONS ---
        # PX_LAST: Last traded price (most accurate for options)
        # PX_MID: Mid of bid/ask (useful when no recent trades)
        # PX_SETTLE: Settlement price (may not exist for options)
        # PX_BID / PX_ASK: For spread calculation if needed
        
        request.append("fields", "PX_LAST")
        request.append("fields", "PX_MID")
        request.append("fields", "PX_BID")
        request.append("fields", "PX_ASK")
        request.append("fields", "PX_SETTLE")
        request.append("fields", "VOLUME")        # Try VOLUME instead of PX_VOLUME
        request.append("fields", "PX_VOLUME")     # Keep as backup
        
        request.set("startDate", start_date)
        request.set("endDate", datetime.datetime.now().strftime("%Y%m%d"))
        request.set("periodicitySelection", "DAILY")
        
        self.session.sendRequest(request)
        
        records = []
        debug_shown = set()  # Track which tickers we've shown debug for
        
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
                            
                            # --- DEBUG OUTPUT (first occurrence per ticker) ---
                            if DEBUG_MODE and ticker not in debug_shown:
                                debug_shown.add(ticker)
                                print(f"\n=== DEBUG: {ticker} ===")
                                print(f"  PX_LAST exists:   {point.hasElement('PX_LAST')}", end="")
                                if point.hasElement('PX_LAST'):
                                    print(f" -> {point.getElementAsFloat('PX_LAST')}")
                                else:
                                    print()
                                print(f"  PX_MID exists:    {point.hasElement('PX_MID')}", end="")
                                if point.hasElement('PX_MID'):
                                    print(f" -> {point.getElementAsFloat('PX_MID')}")
                                else:
                                    print()
                                print(f"  PX_BID exists:    {point.hasElement('PX_BID')}", end="")
                                if point.hasElement('PX_BID'):
                                    print(f" -> {point.getElementAsFloat('PX_BID')}")
                                else:
                                    print()
                                print(f"  PX_ASK exists:    {point.hasElement('PX_ASK')}", end="")
                                if point.hasElement('PX_ASK'):
                                    print(f" -> {point.getElementAsFloat('PX_ASK')}")
                                else:
                                    print()
                                print(f"  PX_SETTLE exists: {point.hasElement('PX_SETTLE')}", end="")
                                if point.hasElement('PX_SETTLE'):
                                    print(f" -> {point.getElementAsFloat('PX_SETTLE')}")
                                else:
                                    print()
                                print(f"  VOLUME exists:    {point.hasElement('VOLUME')}", end="")
                                if point.hasElement('VOLUME'):
                                    print(f" -> {point.getElementAsFloat('VOLUME')}")
                                else:
                                    print()
                                print(f"  PX_VOLUME exists: {point.hasElement('PX_VOLUME')}", end="")
                                if point.hasElement('PX_VOLUME'):
                                    print(f" -> {point.getElementAsFloat('PX_VOLUME')}")
                                else:
                                    print()
                                print("=" * 40)
                            
                            # --- PRICE LOGIC (Priority: LAST > MID > SETTLE) ---
                            price = 0.0
                            price_source = "NONE"
                            
                            if point.hasElement("PX_LAST"):
                                val = point.getElementAsFloat("PX_LAST")
                                if val > 0:
                                    price = val
                                    price_source = "PX_LAST"
                            
                            if price == 0 and point.hasElement("PX_MID"):
                                val = point.getElementAsFloat("PX_MID")
                                if val > 0:
                                    price = val
                                    price_source = "PX_MID"
                            
                            # Calculate mid from bid/ask if PX_MID doesn't exist
                            if price == 0:
                                bid = 0.0
                                ask = 0.0
                                if point.hasElement("PX_BID"):
                                    bid = point.getElementAsFloat("PX_BID")
                                if point.hasElement("PX_ASK"):
                                    ask = point.getElementAsFloat("PX_ASK")
                                if bid > 0 and ask > 0:
                                    price = (bid + ask) / 2
                                    price_source = "CALC_MID"
                            
                            if price == 0 and point.hasElement("PX_SETTLE"):
                                val = point.getElementAsFloat("PX_SETTLE")
                                if val > 0:
                                    price = val
                                    price_source = "PX_SETTLE"
                            
                            # --- VOLUME LOGIC (Priority: VOLUME > PX_VOLUME) ---
                            volume = 0.0
                            
                            if point.hasElement("VOLUME"):
                                vol = point.getElementAsFloat("VOLUME")
                                if vol > 0:
                                    volume = vol
                            
                            if volume == 0 and point.hasElement("PX_VOLUME"):
                                vol = point.getElementAsFloat("PX_VOLUME")
                                if vol > 0:
                                    volume = vol
                            
                            records.append({
                                "Date": pd.Timestamp(raw_date).strftime("%Y-%m-%d"),
                                "Ticker": ticker,
                                "Price": price,
                                "PriceSource": price_source,
                                "Volume": volume
                            })
                            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        return pd.DataFrame(records)

    def close(self):
        if self.session:
            self.session.stop()

# --- GIT AUTOMATION FUNCTION ---
def push_to_github(file_path):
    """
    Commits and pushes the specific file to GitHub.
    """
    print(f"\n🚀 Starting Git Push for {file_path}...")
    try:
        # 1. Add the specific file
        subprocess.run(["git", "add", str(file_path)], check=True)
        
        # 2. Commit with a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto-update VIX Data: {timestamp}"
        
        # 'check=False' prevents crash if there are no changes to commit
        subprocess.run(["git", "commit", "-m", commit_message], check=False)
        
        # 3. Push to main/master
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Successfully pushed to GitHub!")
        else:
            print(f"⚠️ Git Push Warning (Check connection): {result.stderr}")
            
    except Exception as e:
        print(f"❌ Git Automation Failed: {e}")

# --- MAIN LOGIC ---
def main():
    try:
        engine = BloombergEngine()
        
        # Collect all tickers including VIX spot
        all_tickers = [VIX_SPOT_TICKER]  # Add VIX spot first
        for conf in SPREADS_CONFIG.values():
            all_tickers.extend([conf["long"], conf["short"]])
            
        # 1. Get Raw History
        raw_df = engine.get_history(all_tickers, START_DATE)
        if raw_df.empty:
            print("No data received.")
            return

        # 2. Show price source summary
        if DEBUG_MODE:
            print("\n=== PRICE SOURCE SUMMARY ===")
            print(raw_df.groupby(["Ticker", "PriceSource"]).size())
            print("=" * 40 + "\n")

        # 3. Pivot and Format Data
        print("Processing data...")
        dates = raw_df["Date"].unique()
        final_rows = []
        
        for date in sorted(dates):
            date_df = raw_df[raw_df["Date"] == date]
            row = {"Date": date}
            
            # Get VIX Spot
            vix_row = date_df[date_df["Ticker"] == VIX_SPOT_TICKER]
            vix_spot = vix_row["Price"].values[0] if not vix_row.empty else 0.0
            row["VIX_Spot"] = vix_spot
            
            for name, conf in SPREADS_CONFIG.items():
                prefix = name.replace(" ", "_")
                
                # Get Long Leg
                l_row = date_df[date_df["Ticker"] == conf["long"]]
                l_price = l_row["Price"].values[0] if not l_row.empty else 0.0
                l_vol = l_row["Volume"].values[0] if not l_row.empty else 0.0
                
                # Get Short Leg
                s_row = date_df[date_df["Ticker"] == conf["short"]]
                s_price = s_row["Price"].values[0] if not s_row.empty else 0.0
                s_vol = s_row["Volume"].values[0] if not s_row.empty else 0.0
                
                # Calculate Spread
                if not l_row.empty and not s_row.empty and l_price > 0 and s_price > 0:
                    spread = l_price - s_price
                else:
                    spread = None
                
                row[f"{prefix}_Long_Price"] = l_price
                row[f"{prefix}_Short_Price"] = s_price
                row[f"{prefix}_Long_Volume"] = l_vol
                row[f"{prefix}_Short_Volume"] = s_vol
                row[f"{prefix}_Spread"] = spread
                row[f"{prefix}_Total_Volume"] = l_vol + s_vol

            final_rows.append(row)
            
        # 4. Save to CSV
        final_df = pd.DataFrame(final_rows)
        final_df.to_csv(CSV_PATH, index=False)
        
        print(f"\n✅ Success! Data saved to {CSV_PATH}")
        print(f"   Total Days: {len(final_df)}")
        print(f"\n   Latest data point:")
        latest = final_df.iloc[-1]
        print(f"   Date: {latest['Date']}")
        print(f"   VIX Spot: {latest['VIX_Spot']:.2f}")
        for name in SPREADS_CONFIG.keys():
            prefix = name.replace(" ", "_")
            print(f"   {name}: Long={latest[f'{prefix}_Long_Price']:.2f}, Short={latest[f'{prefix}_Short_Price']:.2f}, Spread={latest[f'{prefix}_Spread']:.2f}")
        
        engine.close()

        # 5. Push to GitHub
        push_to_github(CSV_PATH)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()