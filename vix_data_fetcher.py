import blpapi
import pandas as pd
import datetime
import time
from pathlib import Path

# --- CONFIGURATION ---
CSV_PATH = Path("vix_spread_data.csv")
START_DATE = "20250101"  # Downloads history starting from here

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
        print("Connected.")

    def get_history(self, tickers: list, start_date: str) -> pd.DataFrame:
        print(f"Fetching history for {len(tickers)} tickers from {start_date}...")
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("HistoricalDataRequest")
        
        for ticker in tickers:
            request.append("securities", ticker)
        
        request.append("fields", "PX_LAST")
        request.append("fields", "VOLUME")
        request.set("startDate", start_date)
        request.set("endDate", datetime.datetime.now().strftime("%Y%m%d"))
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
                            volume = point.getElementAsFloat("VOLUME") if point.hasElement("VOLUME") else 0
                            records.append({
                                "Date": pd.Timestamp(raw_date).strftime("%Y-%m-%d"),
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

# --- MAIN LOGIC ---
def main():
    try:
        engine = BloombergEngine()
        
        all_tickers = []
        for conf in SPREADS_CONFIG.values():
            all_tickers.extend([conf["long"], conf["short"]])
            
        # 1. Get Raw History
        raw_df = engine.get_history(all_tickers, START_DATE)
        if raw_df.empty:
            print("No data received.")
            return

        # 2. Pivot and Format Data
        print("Processing data...")
        dates = raw_df["Date"].unique()
        final_rows = []
        
        for date in sorted(dates):
            date_df = raw_df[raw_df["Date"] == date]
            row = {"Date": date}
            
            for name, conf in SPREADS_CONFIG.items():
                prefix = name.replace(" ", "_")
                
                # Get Long Leg
                l_row = date_df[date_df["Ticker"] == conf["long"]]
                l_price = l_row["Price"].values[0] if not l_row.empty else None
                l_vol = l_row["Volume"].values[0] if not l_row.empty else 0
                
                # Get Short Leg
                s_row = date_df[date_df["Ticker"] == conf["short"]]
                s_price = s_row["Price"].values[0] if not s_row.empty else None
                s_vol = s_row["Volume"].values[0] if not s_row.empty else 0
                
                # Calculate Spread
                spread = (l_price - s_price) if (l_price is not None and s_price is not None) else None
                
                row[f"{prefix}_Long_Price"] = l_price
                row[f"{prefix}_Short_Price"] = s_price
                row[f"{prefix}_Long_Volume"] = l_vol
                row[f"{prefix}_Short_Volume"] = s_vol
                row[f"{prefix}_Spread"] = spread
                row[f"{prefix}_Total_Volume"] = l_vol + s_vol

            final_rows.append(row)
            
        # 3. Save to CSV
        final_df = pd.DataFrame(final_rows)
        final_df.to_csv(CSV_PATH, index=False)
        print(f"✅ Success! Data saved to {CSV_PATH}")
        print(f"   Total Days: {len(final_df)}")
        
        engine.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()