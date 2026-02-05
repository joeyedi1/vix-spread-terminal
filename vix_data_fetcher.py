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

# --- CHANGE 1: Replace VIX Spot with VIX Futures ---
# Each spread should reference its corresponding VIX futures contract
# Bloomberg VIX Futures format: UX + month code + year digits + " Index"
# Month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec

SPREADS_CONFIG = {
    "Feb 2026": {
        "expiry": "02/18/26",
        "long": "VIX US 02/18/26 C20 Index",
        "short": "VIX US 02/18/26 C25 Index",
        "futures": "UXG26 Index",  # Feb 2026 VIX Futures (G = February)
    },
    "Mar 2026": {
        "expiry": "03/18/26",
        "long": "VIX US 03/18/26 C20 Index",
        "short": "VIX US 03/18/26 C25 Index",
        "futures": "UXH26 Index",  # Mar 2026 VIX Futures (H = March)
    },
}

# Optional: Also track VIX spot for reference (contango analysis)
VIX_SPOT_TICKER = "VIX Index"
INCLUDE_VIX_SPOT = False  # Set to False if you only want futures


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
        
        # --- CHANGE 2: Collect all tickers including VIX futures for each spread ---
        all_tickers = []
        
        # Optionally include VIX spot for contango reference
        if INCLUDE_VIX_SPOT:
            all_tickers.append(VIX_SPOT_TICKER)
        
        # Add futures and options for each spread
        for conf in SPREADS_CONFIG.values():
            all_tickers.append(conf["futures"])  # VIX Futures
            all_tickers.append(conf["long"])      # Long option leg
            all_tickers.append(conf["short"])     # Short option leg
            
        # Remove duplicates while preserving order
        all_tickers = list(dict.fromkeys(all_tickers))
        
        print(f"Tickers to fetch: {all_tickers}")
            
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
            
            # --- CHANGE 3: Get VIX Spot (optional, for contango analysis) ---
            if INCLUDE_VIX_SPOT:
                vix_row = date_df[date_df["Ticker"] == VIX_SPOT_TICKER]
                vix_spot = vix_row["Price"].values[0] if not vix_row.empty else 0.0
                row["VIX_Spot"] = vix_spot
            
            for name, conf in SPREADS_CONFIG.items():
                prefix = name.replace(" ", "_")
                
                # --- CHANGE 4: Get VIX Futures price for this spread's expiry ---
                futures_row = date_df[date_df["Ticker"] == conf["futures"]]
                futures_price = futures_row["Price"].values[0] if not futures_row.empty else 0.0
                row[f"{prefix}_VIX_Futures"] = futures_price
                
                # Calculate contango (futures - spot) if spot is included
                if INCLUDE_VIX_SPOT and futures_price > 0 and row.get("VIX_Spot", 0) > 0:
                    row[f"{prefix}_Contango"] = futures_price - row["VIX_Spot"]
                
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
                
                # --- CHANGE 5: Calculate moneyness (distance from futures to strikes) ---
                if futures_price > 0:
                    # For C20/C25 spread, show how far futures is from strikes
                    row[f"{prefix}_Futures_to_C20"] = futures_price - 20  # Negative = OTM
                    row[f"{prefix}_Futures_to_C25"] = futures_price - 25  # Negative = OTM

            final_rows.append(row)
            
        # 4. Save to CSV
        final_df = pd.DataFrame(final_rows)
        final_df.to_csv(CSV_PATH, index=False)
        
        print(f"\n✅ Success! Data saved to {CSV_PATH}")
        print(f"   Total Days: {len(final_df)}")
        print(f"\n   Latest data point:")
        latest = final_df.iloc[-1]
        print(f"   Date: {latest['Date']}")
        
        if INCLUDE_VIX_SPOT:
            print(f"   VIX Spot: {latest['VIX_Spot']:.2f}")
        
        for name, conf in SPREADS_CONFIG.items():
            prefix = name.replace(" ", "_")
            futures_val = latest.get(f'{prefix}_VIX_Futures', 0)
            print(f"\n   {name}:")
            print(f"     VIX Futures ({conf['futures']}): {futures_val:.2f}")
            if INCLUDE_VIX_SPOT and futures_val > 0:
                contango = latest.get(f'{prefix}_Contango', 0)
                print(f"     Contango: {contango:+.2f}")
            print(f"     Long (C20): {latest[f'{prefix}_Long_Price']:.2f}")
            print(f"     Short (C25): {latest[f'{prefix}_Short_Price']:.2f}")
            print(f"     Spread: {latest[f'{prefix}_Spread']:.2f}")
            if futures_val > 0:
                print(f"     Futures distance to C20: {latest.get(f'{prefix}_Futures_to_C20', 0):+.2f}")
                print(f"     Futures distance to C25: {latest.get(f'{prefix}_Futures_to_C25', 0):+.2f}")
        
        engine.close()

        # 5. Push to GitHub
        push_to_github(CSV_PATH)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()