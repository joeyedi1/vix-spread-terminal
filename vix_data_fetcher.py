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
        "long_strike": 20,
        "short_strike": 25,
        "futures": "UXG26 Index",  # Feb 2026 VIX Futures (G = February)
    },
    "Mar 2026": {
        "expiry": "03/18/26",
        "long": "VIX US 03/18/26 C20 Index",
        "short": "VIX US 03/18/26 C25 Index",
        "long_strike": 20,
        "short_strike": 25,
        "futures": "UXH26 Index",  # Mar 2026 VIX Futures (H = March)
    },
    "Mar 2026 20-40": {
        "expiry": "03/18/26",
        "long": "VIX US 03/18/26 C20 Index",
        "short": "VIX US 03/18/26 C40 Index",
        "long_strike": 20,
        "short_strike": 40,
        "futures": "UXH26 Index",  # Same Mar 2026 VIX Futures
    },
    "May 2026": {
        "expiry": "05/19/26",
        "long": "VIX US 05/19/26 C25 Index",
        "short": "VIX US 05/19/26 C35 Index",
        "long_strike": 25,
        "short_strike": 35,
        "futures": "UXK26 Index",  # May 2026 VIX Futures (K = May)
    },
}

# Optional: Also track VIX spot for reference (contango analysis)
VIX_SPOT_TICKER = "VIX Index"
INCLUDE_VIX_SPOT = False  # Set to False if you only want futures

# --- VIX TERM STRUCTURE (UX1 = front-month rolling, UX8 = 8th month) ---
# Generic futures give a clean contango/backwardation view regardless of month.
TERM_STRUCTURE_TICKERS = [f"UX{i} Index" for i in range(1, 9)]

# --- VVIX: vol-of-VIX. Rich VVIX -> VIX options expensive ---
VVIX_TICKER = "VVIX Index"


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

        # --- GREEKS (only populated for option tickers; futures/indices return nothing) ---
        request.append("fields", "IVOL_MID")      # Implied vol (mid)
        request.append("fields", "DELTA_MID")     # Delta
        request.append("fields", "GAMMA_MID")     # Gamma
        request.append("fields", "VEGA_MID")      # Vega (per 1% vol)
        request.append("fields", "THETA_MID")     # Theta (per day)
        
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
                            
                            # --- GREEKS (may be absent for non-options) ---
                            def _g(fld):
                                if point.hasElement(fld):
                                    try:
                                        return point.getElementAsFloat(fld)
                                    except Exception:
                                        return None
                                return None

                            records.append({
                                "Date": pd.Timestamp(raw_date).strftime("%Y-%m-%d"),
                                "Ticker": ticker,
                                "Price": price,
                                "PriceSource": price_source,
                                "Volume": volume,
                                "IV": _g("IVOL_MID"),
                                "Delta": _g("DELTA_MID"),
                                "Gamma": _g("GAMMA_MID"),
                                "Vega": _g("VEGA_MID"),
                                "Theta": _g("THETA_MID"),
                            })
                            
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        
        return pd.DataFrame(records)

    def get_greeks_snapshot(self, tickers: list) -> dict:
        """
        Fetch CURRENT Greeks via ReferenceDataRequest.
        Historical Greeks are unreliable on Bloomberg; snapshot works.
        Returns: {ticker: {iv, delta, gamma, vega, theta}}
        """
        print(f"Fetching Greek snapshot for {len(tickers)} tickers...")
        service = self.session.getService("//blp/refdata")
        request = service.createRequest("ReferenceDataRequest")

        for tk in tickers:
            request.append("securities", tk)

        for fld in ["IVOL_MID", "IVOL_LAST", "DELTA_MID", "GAMMA_MID", "VEGA_MID", "THETA_MID"]:
            request.append("fields", fld)

        self.session.sendRequest(request)

        results = {}
        timeout = time.time() + 10
        while time.time() < timeout:
            event = self.session.nextEvent(500)
            for msg in event:
                if msg.hasElement("securityData"):
                    sd = msg.getElement("securityData")
                    for i in range(sd.numValues()):
                        item = sd.getValueAsElement(i)
                        tk = item.getElementAsString("security")
                        if not item.hasElement("fieldData"):
                            continue
                        fd = item.getElement("fieldData")

                        def _f(fields):
                            for f in fields:
                                if fd.hasElement(f):
                                    try:
                                        return fd.getElementAsFloat(f)
                                    except Exception:
                                        continue
                            return None

                        results[tk] = {
                            "iv":    _f(["IVOL_MID", "IVOL_LAST"]),
                            "delta": _f(["DELTA_MID"]),
                            "gamma": _f(["GAMMA_MID"]),
                            "vega":  _f(["VEGA_MID"]),
                            "theta": _f(["THETA_MID"]),
                        }
            if event.eventType() == blpapi.Event.RESPONSE:
                break
        return results

    def close(self):
        if self.session:
            self.session.stop()

# --- GIT AUTOMATION FUNCTION ---
def push_to_github(file_path):
    """
    Commits and pushes the specific file to GitHub.
    """
    import os
    print(f"\n🚀 Starting Git Push for {file_path}...")
    print(f"   CWD: {os.getcwd()}")
    print(f"   File exists: {Path(file_path).exists()}")
    
    try:
        # 0. Verify we're inside a git repo
        check_repo = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True
        )
        if check_repo.returncode != 0:
            print(f"❌ Not inside a git repository! stderr: {check_repo.stderr.strip()}")
            return
        print(f"   Git repo: {check_repo.stdout.strip()}")
        
        # 1. Show git status before adding
        status = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        print(f"   Git status: {status.stdout.strip() or '(clean)'}")
        
        # 2. Add the specific file
        add_result = subprocess.run(
            ["git", "add", str(file_path)],
            capture_output=True, text=True
        )
        if add_result.returncode != 0:
            print(f"❌ git add failed: {add_result.stderr.strip()}")
            return
        print("   ✓ git add OK")
        
        # 3. Commit with a timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"Auto-update VIX Data: {timestamp}"
        
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            capture_output=True, text=True
        )
        if commit_result.returncode != 0:
            # Check if it's just "nothing to commit"
            if "nothing to commit" in commit_result.stdout:
                print("   ⚠️ Nothing to commit (no changes detected)")
                return
            else:
                print(f"❌ git commit failed:")
                print(f"   stdout: {commit_result.stdout.strip()}")
                print(f"   stderr: {commit_result.stderr.strip()}")
                return
        print(f"   ✓ git commit OK: {commit_result.stdout.strip()}")
        
        # 4. Push to remote
        push_result = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True,
            timeout=30  # Fail fast if network is down
        )
        
        if push_result.returncode == 0:
            print("✅ Successfully pushed to GitHub!")
        else:
            print(f"❌ git push failed:")
            print(f"   stdout: {push_result.stdout.strip()}")
            print(f"   stderr: {push_result.stderr.strip()}")
            # Common fixes
            if "Authentication" in push_result.stderr or "403" in push_result.stderr:
                print("   💡 Fix: Your GitHub token may have expired. Regenerate at github.com/settings/tokens")
            elif "Could not resolve host" in push_result.stderr:
                print("   💡 Fix: No network connection")
            elif "rejected" in push_result.stderr:
                print("   💡 Fix: Remote has changes. Try 'git pull --rebase' first")
                
    except subprocess.TimeoutExpired:
        print("❌ git push timed out after 30s — check your network connection")
    except Exception as e:
        print(f"❌ Git Automation Failed: {type(e).__name__}: {e}")

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

        # Add VIX term structure (UX1..UX8) and VVIX
        all_tickers.extend(TERM_STRUCTURE_TICKERS)
        all_tickers.append(VVIX_TICKER)

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

            # --- VIX TERM STRUCTURE (UX1..UX8) ---
            for i, tk in enumerate(TERM_STRUCTURE_TICKERS, start=1):
                ts_row = date_df[date_df["Ticker"] == tk]
                row[f"UX{i}"] = ts_row["Price"].values[0] if not ts_row.empty else 0.0

            # --- VVIX ---
            vvix_row = date_df[date_df["Ticker"] == VVIX_TICKER]
            row["VVIX"] = vvix_row["Price"].values[0] if not vvix_row.empty else 0.0

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

                # --- GREEKS per leg ---
                def _leg_greek(leg_row, field):
                    if leg_row.empty:
                        return None
                    val = leg_row[field].values[0]
                    return None if pd.isna(val) else float(val)

                long_iv    = _leg_greek(l_row, "IV")
                long_dlt   = _leg_greek(l_row, "Delta")
                long_gma   = _leg_greek(l_row, "Gamma")
                long_vga   = _leg_greek(l_row, "Vega")
                long_tht   = _leg_greek(l_row, "Theta")
                short_iv   = _leg_greek(s_row, "IV")
                short_dlt  = _leg_greek(s_row, "Delta")
                short_gma  = _leg_greek(s_row, "Gamma")
                short_vga  = _leg_greek(s_row, "Vega")
                short_tht  = _leg_greek(s_row, "Theta")

                row[f"{prefix}_Long_IV"]     = long_iv
                row[f"{prefix}_Long_Delta"]  = long_dlt
                row[f"{prefix}_Long_Gamma"]  = long_gma
                row[f"{prefix}_Long_Vega"]   = long_vga
                row[f"{prefix}_Long_Theta"]  = long_tht
                row[f"{prefix}_Short_IV"]    = short_iv
                row[f"{prefix}_Short_Delta"] = short_dlt
                row[f"{prefix}_Short_Gamma"] = short_gma
                row[f"{prefix}_Short_Vega"]  = short_vga
                row[f"{prefix}_Short_Theta"] = short_tht

                # --- AGGREGATED NET GREEKS (long - short) ---
                def _net(a, b):
                    return (a - b) if (a is not None and b is not None) else None
                row[f"{prefix}_Net_Delta"] = _net(long_dlt, short_dlt)
                row[f"{prefix}_Net_Gamma"] = _net(long_gma, short_gma)
                row[f"{prefix}_Net_Vega"]  = _net(long_vga, short_vga)
                row[f"{prefix}_Net_Theta"] = _net(long_tht, short_tht)

                # --- CHANGE 5: Calculate moneyness (distance from futures to strikes) ---
                if futures_price > 0:
                    long_k = conf.get("long_strike", 20)
                    short_k = conf.get("short_strike", 25)
                    row[f"{prefix}_Futures_to_C{long_k}"] = futures_price - long_k
                    row[f"{prefix}_Futures_to_C{short_k}"] = futures_price - short_k

            final_rows.append(row)
            
        # 3b. Snapshot current Greeks (HistoricalDataRequest doesn't return them reliably)
        option_tickers = []
        for conf in SPREADS_CONFIG.values():
            option_tickers.extend([conf["long"], conf["short"]])
        option_tickers = list(dict.fromkeys(option_tickers))

        greek_snap = engine.get_greeks_snapshot(option_tickers)

        # Patch the latest row with snapshot Greeks
        last_idx = len(final_rows) - 1
        for name, conf in SPREADS_CONFIG.items():
            prefix = name.replace(" ", "_")
            lg = greek_snap.get(conf["long"], {})
            sg = greek_snap.get(conf["short"], {})

            final_rows[last_idx][f"{prefix}_Long_IV"]    = lg.get("iv")
            final_rows[last_idx][f"{prefix}_Long_Delta"] = lg.get("delta")
            final_rows[last_idx][f"{prefix}_Long_Gamma"] = lg.get("gamma")
            final_rows[last_idx][f"{prefix}_Long_Vega"]  = lg.get("vega")
            final_rows[last_idx][f"{prefix}_Long_Theta"] = lg.get("theta")
            final_rows[last_idx][f"{prefix}_Short_IV"]    = sg.get("iv")
            final_rows[last_idx][f"{prefix}_Short_Delta"] = sg.get("delta")
            final_rows[last_idx][f"{prefix}_Short_Gamma"] = sg.get("gamma")
            final_rows[last_idx][f"{prefix}_Short_Vega"]  = sg.get("vega")
            final_rows[last_idx][f"{prefix}_Short_Theta"] = sg.get("theta")

            def _net(a, b):
                return (a - b) if (a is not None and b is not None) else None
            final_rows[last_idx][f"{prefix}_Net_Delta"] = _net(lg.get("delta"), sg.get("delta"))
            final_rows[last_idx][f"{prefix}_Net_Gamma"] = _net(lg.get("gamma"), sg.get("gamma"))
            final_rows[last_idx][f"{prefix}_Net_Vega"]  = _net(lg.get("vega"),  sg.get("vega"))
            final_rows[last_idx][f"{prefix}_Net_Theta"] = _net(lg.get("theta"), sg.get("theta"))

            if DEBUG_MODE:
                print(f"  Greeks patched for {name}: long={lg}, short={sg}")

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
            long_k = conf.get("long_strike", 20)
            short_k = conf.get("short_strike", 25)
            futures_val = latest.get(f'{prefix}_VIX_Futures', 0)
            print(f"\n   {name} (C{long_k}/C{short_k}):")
            print(f"     VIX Futures ({conf['futures']}): {futures_val:.2f}")
            if INCLUDE_VIX_SPOT and futures_val > 0:
                contango = latest.get(f'{prefix}_Contango', 0)
                print(f"     Contango: {contango:+.2f}")
            long_px = latest[f'{prefix}_Long_Price']
            short_px = latest[f'{prefix}_Short_Price']
            spread_px = latest[f'{prefix}_Spread']
            print(f"     Long (C{long_k}): {long_px:.2f}" if pd.notna(long_px) else f"     Long (C{long_k}): N/A")
            print(f"     Short (C{short_k}): {short_px:.2f}" if pd.notna(short_px) else f"     Short (C{short_k}): N/A")
            print(f"     Spread: {spread_px:.2f}" if pd.notna(spread_px) else f"     Spread: N/A")
            if futures_val > 0:
                print(f"     Futures distance to C{long_k}: {latest.get(f'{prefix}_Futures_to_C{long_k}', 0):+.2f}")
                print(f"     Futures distance to C{short_k}: {latest.get(f'{prefix}_Futures_to_C{short_k}', 0):+.2f}")
        
        engine.close()

        # 5. Push to GitHub
        push_to_github(CSV_PATH)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()