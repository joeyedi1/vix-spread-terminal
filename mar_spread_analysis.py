"""
MAR 2026 SPREAD ANALYSIS - INTRADAY RANGE
==========================================
Standalone script - does NOT affect dashboard or data fetcher.
Pulls PX_HIGH / PX_LOW for each leg to find the widest spread on each day.

Covers BOTH spreads in one run (shared C20 long leg + UXH26 futures):
  1) C20/C25 call spread  (entry: $0.91)
  2) C20/C40 call spread  (entry: $1.45)

Run once on your Bloomberg terminal after Mar 18 expiry.
Output: mar_spread_intraday.csv, mar_2040_spread_intraday.csv
"""

import blpapi
import pandas as pd
import datetime
from pathlib import Path

# --- CONFIG ---
OUTPUT_CSV_2025 = Path("mar_spread_intraday.csv")
OUTPUT_CSV_2040 = Path("mar_2040_spread_intraday.csv")

START_DATE = "20260116"  # Your entry date
END_DATE = "20260318"    # Mar expiry date

# Entry prices
ENTRY_C20_C25 = 0.91
ENTRY_C20_C40 = 1.45

TICKERS = {
    "C20": "VIX US 03/18/26 C20 Index",
    "C25": "VIX US 03/18/26 C25 Index",
    "C40": "VIX US 03/18/26 C40 Index",
    "Futures": "UXH26 Index",
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


def build_spread_csv(dates, raw_df, long_label, short_label, entry_price, output_csv):
    """Build intraday spread CSV for a given long/short pair."""
    rows = []

    for date in dates:
        day = raw_df[raw_df["Date"] == date]
        row = {"Date": date}

        for label in [long_label, short_label, "Futures"]:
            ticker = TICKERS[label]
            t_data = day[day["Ticker"] == ticker]
            if t_data.empty:
                continue
            t_row = t_data.iloc[0]
            for f in FIELDS:
                row[f"{label}_{f}"] = t_row.get(f, 0.0)

        # --- CALCULATE SPREAD SCENARIOS ---
        long_last = row.get(f"{long_label}_PX_LAST", 0)
        short_last = row.get(f"{short_label}_PX_LAST", 0)
        long_high = row.get(f"{long_label}_PX_HIGH", 0)
        long_low = row.get(f"{long_label}_PX_LOW", 0)
        short_high = row.get(f"{short_label}_PX_HIGH", 0)
        short_low = row.get(f"{short_label}_PX_LOW", 0)

        # Close-to-close spread
        row["Spread_Close"] = long_last - short_last if long_last and short_last else None

        # WIDEST possible spread = Long High - Short Low
        row["Spread_Widest"] = long_high - short_low if long_high and short_low else None

        # NARROWEST possible spread = Long Low - Short High
        row["Spread_Narrowest"] = long_low - short_high if long_low and short_high else None

        # Futures data
        row["Futures_Last"] = row.get("Futures_PX_LAST", 0)
        row["Futures_High"] = row.get("Futures_PX_HIGH", 0)
        row["Futures_Low"] = row.get("Futures_PX_LOW", 0)

        rows.append(row)

    result = pd.DataFrame(rows)

    # --- P&L ANALYSIS ---
    result["PnL_Close"] = result["Spread_Close"] - entry_price
    result["PnL_Close_Pct"] = (result["PnL_Close"] / entry_price * 100).round(1)
    result["PnL_Best_Exit"] = result["Spread_Widest"] - entry_price
    result["PnL_Best_Exit_Pct"] = (result["PnL_Best_Exit"] / entry_price * 100).round(1)
    result["PnL_Worst_Intraday"] = result["Spread_Narrowest"] - entry_price
    result["PnL_Worst_Intraday_Pct"] = (result["PnL_Worst_Intraday"] / entry_price * 100).round(1)

    # Save
    result.to_csv(output_csv, index=False)
    return result


def print_summary(result, spread_name, entry_price, long_strike, short_strike):
    """Print formatted summary table."""
    print("=" * 100)
    print(f"{spread_name}  |  Entry: ${entry_price:.2f} on Jan 16")
    print("=" * 100)

    # Find extremes
    valid = result.dropna(subset=["Spread_Widest"])
    if valid.empty:
        print("No valid data!")
        return

    best_idx = valid["Spread_Widest"].idxmax()
    best_row = valid.loc[best_idx]

    worst_idx = valid["Spread_Narrowest"].idxmin()
    worst_row = valid.loc[worst_idx]

    peak_close_idx = valid["Spread_Close"].dropna().idxmax()
    peak_close_row = valid.loc[peak_close_idx]

    print(f"\nBest possible exit (intraday widest spread):")
    print(f"  Date:       {best_row['Date']}")
    print(f"  Spread:     ${best_row['Spread_Widest']:.2f}")
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

    # Spike days
    spike_threshold = entry_price * 2  # Days where widest > 2x entry
    spike_days = valid[valid["Spread_Widest"] > spike_threshold]
    if not spike_days.empty:
        print(f"\nDays with widest spread > ${spike_threshold:.2f} (2x entry): {len(spike_days)}")
        for _, s in spike_days.sort_values("Spread_Widest", ascending=False).iterrows():
            print(f"  {s['Date']}  Widest: ${s['Spread_Widest']:.2f}  Close: ${s['Spread_Close']:.2f}  Futures: {s['Futures_Low']:.2f}-{s['Futures_High']:.2f}")

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
    print("Widest  = Long High - Short Low  (best realistic exit)")
    print("Narrow  = Long Low  - Short High (worst intraday moment)")
    print("Note: Actual fill depends on liquidity and bid-ask spreads")


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

    dates = sorted(raw_df["Date"].unique())

    # --- 1) C20/C25 SPREAD ---
    print(f"\n{'='*50}")
    print("Building C20/C25 spread...")
    result_2025 = build_spread_csv(dates, raw_df, "C20", "C25", ENTRY_C20_C25, OUTPUT_CSV_2025)
    print(f"Saved to {OUTPUT_CSV_2025} ({len(result_2025)} days)\n")
    print_summary(result_2025, "MAR 2026 C20/C25 SPREAD ANALYSIS", ENTRY_C20_C25, 20, 25)

    # --- 2) C20/C40 SPREAD ---
    print(f"\n\n{'='*50}")
    print("Building C20/C40 spread...")
    result_2040 = build_spread_csv(dates, raw_df, "C20", "C40", ENTRY_C20_C40, OUTPUT_CSV_2040)
    print(f"Saved to {OUTPUT_CSV_2040} ({len(result_2040)} days)\n")
    print_summary(result_2040, "MAR 2026 C20/C40 SPREAD ANALYSIS", ENTRY_C20_C40, 20, 40)

    print(f"\n\nDone! Files created:")
    print(f"  {OUTPUT_CSV_2025}")
    print(f"  {OUTPUT_CSV_2040}")
    print(f"Drop them in your VIX dashboard folder and refresh Streamlit.")


if __name__ == "__main__":
    main()