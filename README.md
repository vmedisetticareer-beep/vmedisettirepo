# Portfolio Lens

A local stock portfolio analyzer built with Streamlit, pandas, Plotly, and yfinance. Upload a CSV of buys and sells to review current holdings, return metrics, and historical portfolio value.

## Run

From this directory, install the project with uv and start the app:

```powershell
uv sync
uv run streamlit run src/uvdemo/app.py
```

## CSV format

Include these columns (an optional leading row-number column is ignored):

| Column | Description |
| --- | --- |
| `Ticker` | Yahoo Finance ticker symbol |
| `Date` | Transaction date |
| `Transaction Type` | `Buy` or `Sell` |
| `Qty` | Number of shares traded |
| `Price` | Per-share transaction price |

The app includes three tabs: CSV import and validation, current holdings with price and gain breakdowns, and historical performance with lifetime investment, sale proceeds, current value, total return, XIRR, and a portfolio value trend line.

Current prices and historical closes come from yfinance. Quotes are latest available closes, and historical prices are adjusted for stock splits. Dividends, fees, and taxes are not included in performance calculations. Total return is sale proceeds plus current value minus lifetime purchases; XIRR uses dated buy and sell cash flows plus the latest historical portfolio value.
