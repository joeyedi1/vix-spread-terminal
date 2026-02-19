"""
FEB 2026 C20/C25 SPREAD - INTRADAY RANGE ANALYSIS
===================================================
Standalone script - does NOT affect dashboard or data fetcher.
Pulls PX_HIGH / PX_LOW for each leg to find the widest spread on each day.

Run once on your Bloomberg terminal, then you can delete this file.
Output: feb_spread_intraday.csv
"""

import blpapi
import pandas as pd
import datetime
from pathlib import Path

# --- CONFIG ---
OUTPUT_CSV = Path("feb_spread_intraday.csv")
START_DATE = "20260116"  # Your entry date
END_DATE = "20260218"    # Feb expiry date

TICKERS = {
    "C20": "VIX US 02/18/26 C20 Index",
    "C25": "VIX US 02/18/26 C25 Index",
    "Futures": "UXG26 Index",
}

# Fields to pull
FIELDS = ["PX_LAST", "PX_HIGH", "PX_LOW", "PX_BID", "PX_ASK", "PX_MID"]


# --- BLOOMBERG ENGINE ---
def connect():
    print("Connecting to Bloomberg Terminal...")
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)
    session = blpapi.Session(options)
    if not session.start():
        raise ConnectionError("Failed to start Bloomberg session")
    if not session.openService("//blp/refdata"):
        raise ConnectionError("Failed to open //blp/refdata service")
    print("Connected.\n")
    return session


def fetch_data(session, tickers, fields, start_date, end_date):
    service = session.getService("//blp/refdata")
    request = service.createRequest("HistoricalDataRequest")

    for t in tickers:
        request.append("securities", t)
    for f in fields:
        request.append("fields", f)

    request.set("startDate", start_date)
    request.set("endDate", end_date)
    request.set("periodicitySelection", "DAILY")

    session.sendRequest(request)

    records = []
    while True:
        event = session.nextEvent(500)
        for msg in event:
            if msg.hasElement("securityData"):
                sec_data = msg.getElement("securityData")
                ticker = sec_data.getElementAsString("security")

                if sec_data.hasElement("fieldData"):
                    field_data = sec_data.getElement("fieldData")
                    for i in range(field_data.numValues()):
                        point = field_data.getValueAsElement(i)
                        raw_date = point.getElementAsDatetime("date")

                        row = {
                            "Date": pd.Timestamp(raw_date).strftime("%Y-%m-%d"),
                            "Ticker": ticker,
                        }
                        for f in fields:
                            if point.hasElement(f):
                                row[f] = point.getElementAsFloat(f)
                            else:
                                row[f] = 0.0
                        records.append(row)

        if event.eventType() == blpapi.Event.RESPONSE:
            break

    return pd.DataFrame(records)


def main():
    session = connect()

    all_tickers = list(TICKERS.values())
    print(f"Fetching {len(all_tickers)} tickers: {all_tickers}")
    print(f"Period: {START_DATE} to {END_DATE}")
    print(f"Fields: {FIELDS}\n")

    raw_df = fetch_data(session, all_tickers, FIELDS, START_DATE, END_DATE)
    session.stop()

    if raw_df.empty:
        print("No data received!")
        return

    # --- PIVOT DATA ---
    dates = sorted(raw_df["Date"].unique())
    rows = []

    for date in dates:
        day = raw_df[raw_df["Date"] == date]
        row = {"Date": date}

        for label, ticker in TICKERS.items():
            t_data = day[day["Ticker"] == ticker]
            if t_data.empty:
                continue
            t_row = t_data.iloc[0]
            for f in FIELDS:
                row[f"{label}_{f}"] = t_row.get(f, 0.0)

        # --- CALCULATE SPREAD SCENARIOS ---
        c20_last = row.get("C20_PX_LAST", 0)
        c25_last = row.get("C25_PX_LAST", 0)
        c20_high = row.get("C20_PX_HIGH", 0)
        c20_low = row.get("C20_PX_LOW", 0)
        c25_high = row.get("C25_PX_HIGH", 0)
        c25_low = row.get("C25_PX_LOW", 0)

        # Close-to-close spread (what you currently track)
        row["Spread_Close"] = c20_last - c25_last if c20_last and c25_last else None

        # WIDEST possible spread during the day = C20 High - C25 Low
        # (best case: you sell C25 at its cheapest while C20 is at its peak)
        row["Spread_Widest"] = c20_high - c25_low if c20_high and c25_low else None

        # NARROWEST possible spread = C20 Low - C25 High
        # (worst case during the day)
        row["Spread_Narrowest"] = c20_low - c25_high if c20_low and c25_high else None

        # Futures data
        row["Futures_Last"] = row.get("Futures_PX_LAST", 0)
        row["Futures_High"] = row.get("Futures_PX_HIGH", 0)
        row["Futures_Low"] = row.get("Futures_PX_LOW", 0)

        rows.append(row)

    result = pd.DataFrame(rows)

    # --- P&L ANALYSIS ---
    entry_price = 0.63

    result["PnL_Close"] = result["Spread_Close"] - entry_price
    result["PnL_Close_Pct"] = (result["PnL_Close"] / entry_price * 100).round(1)
    result["PnL_Best_Exit"] = result["Spread_Widest"] - entry_price
    result["PnL_Best_Exit_Pct"] = (result["PnL_Best_Exit"] / entry_price * 100).round(1)
    result["PnL_Worst_Intraday"] = result["Spread_Narrowest"] - entry_price
    result["PnL_Worst_Intraday_Pct"] = (result["PnL_Worst_Intraday"] / entry_price * 100).round(1)

    # Save
    result.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}")
    print(f"Total days: {len(result)}\n")

    # --- PRINT SUMMARY ---
    print("=" * 100)
    print(f"FEB 2026 C20/C25 SPREAD ANALYSIS  |  Entry: $0.63 on Jan 16")
    print("=" * 100)

    # Find best exit day
    best_idx = result["Spread_Widest"].idxmax()
    best_row = result.loc[best_idx]

    worst_idx = result["Spread_Narrowest"].idxmin()
    worst_row = result.loc[worst_idx]

    peak_close_idx = result["Spread_Close"].idxmax()
    peak_close_row = result.loc[peak_close_idx]

    print(f"\nBest possible exit (intraday widest spread):")
    print(f"  Date:       {best_row['Date']}")
    print(f"  Spread:     ${best_row['Spread_Widest']:.2f}  (C20 High: {best_row['C20_PX_HIGH']:.2f} - C25 Low: {best_row['C25_PX_LOW']:.2f})")
    print(f"  P&L:        +${best_row['PnL_Best_Exit']:.2f}  (+{best_row['PnL_Best_Exit_Pct']:.1f}%)")
    print(f"  Futures:    High {best_row['Futures_High']:.2f} / Low {best_row['Futures_Low']:.2f}")

    print(f"\nBest close-to-close exit:")
    print(f"  Date:       {peak_close_row['Date']}")
    print(f"  Spread:     ${peak_close_row['Spread_Close']:.2f}")
    print(f"  P&L:        +${peak_close_row['PnL_Close']:.2f}  (+{peak_close_row['PnL_Close_Pct']:.1f}%)")

    print(f"\nWorst intraday moment:")
    print(f"  Date:       {worst_row['Date']}")
    print(f"  Spread:     ${worst_row['Spread_Narrowest']:.2f}")
    print(f"  P&L:        ${worst_row['PnL_Worst_Intraday']:.2f}  ({worst_row['PnL_Worst_Intraday_Pct']:.1f}%)")

    print(f"\n{'Date':<12} {'Futures':>8} {'F.High':>8} {'F.Low':>8} | {'Close':>7} {'Widest':>8} {'Narrow':>8} | {'PnL Cls':>8} {'PnL Best':>9} {'PnL Wrst':>9}")
    print("-" * 100)
    for _, r in result.iterrows():
        f_last = r.get("Futures_Last", 0) or 0
        f_high = r.get("Futures_High", 0) or 0
        f_low = r.get("Futures_Low", 0) or 0
        s_close = r.get("Spread_Close", 0) or 0
        s_wide = r.get("Spread_Widest", 0) or 0
        s_narrow = r.get("Spread_Narrowest", 0) or 0
        pnl_c = r.get("PnL_Close", 0) or 0
        pnl_b = r.get("PnL_Best_Exit", 0) or 0
        pnl_w = r.get("PnL_Worst_Intraday", 0) or 0

        sign_c = "+" if pnl_c >= 0 else ""
        sign_b = "+" if pnl_b >= 0 else ""
        sign_w = "+" if pnl_w >= 0 else ""

        print(f"{r['Date']:<12} {f_last:>8.2f} {f_high:>8.2f} {f_low:>8.2f} | {s_close:>7.2f} {s_wide:>8.2f} {s_narrow:>8.2f} | {sign_c}{pnl_c:>7.2f} {sign_b}{pnl_b:>8.2f} {sign_w}{pnl_w:>8.2f}")

    print("=" * 100)
    print("Widest  = C20 High - C25 Low  (best realistic exit)")
    print("Narrow  = C20 Low  - C25 High (worst intraday moment)")
    print("Note: Actual fill depends on liquidity and bid-ask spreads")


if __name__ == "__main__":
    main()