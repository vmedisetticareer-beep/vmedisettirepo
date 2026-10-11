# Portfolio Lens

Portfolio Lens is a Streamlit dashboard for reviewing stock transactions, current holdings, and historical portfolio performance. It uses pandas for transaction processing, Plotly Express for charts, and `yfinance` to retrieve price data from Yahoo Finance.

## Dashboard tabs

- **Import:** Upload CSV transactions; preview normalized rows; view transaction count, open positions, and realized gain. If no upload is selected, the app attempts to load `My Stock Portfolio.csv` from a path derived from `app.py`.
- **Current Holdings:** Allocation chart and position breakdown, with quoted market value, cost basis for quoted holdings, unrealized gain, realized gain, gain percentage, price source, and quote coverage.
- **Historical Performance:** Gross purchases (“Lifetime investment”), sale proceeds, current portfolio value, simple total return and percentage, XIRR when available, a historical value chart, and an expandable transaction cash-flow table.

## CSV format

Required columns (case-insensitive headers; surrounding spaces are ignored):

| Column | Rules |
|---|---|
| `Ticker` | Required; normalized to uppercase |
| `Date` | Must parse as a date |
| `Transaction Type` | Only `BUY` or `SELL` |
| `Qty` | Numeric and greater than zero |
| `Price` | Numeric and greater than zero |

Extra columns are discarded. Rows are sorted by date while preserving input order for same-day transactions.

Example (fictional data):

```csv
Ticker,Date,Transaction Type,Qty,Price
ABC,2024-01-10,BUY,10,25.00
ABC,2024-06-15,SELL,4,32.00
XYZ,2024-03-01,BUY,5,80.00
```

## Calculation rules in the supplied code

- A BUY adds `quantity × price` to cost basis and adds shares to the position.
- A SELL cannot exceed the shares held. Realized gain is `quantity sold × (sale price − average cost per share before sale)`.
- Cost basis uses a moving average-cost approach; commissions/fees are not included.
- Current market value = remaining quantity × latest available adjusted close.
- Unrealized gain = market value − remaining cost basis.
- Lifetime investment = sum of BUY quantity × price.
- Sales proceeds = sum of SELL quantity × price.
- Dollar total return = sales proceeds + current portfolio value − lifetime purchases.
- Displayed total-return percentage = dollar total return ÷ lifetime purchases × 100, when purchases are nonzero.
- XIRR uses dated BUY outflows, SELL inflows, and the final historical portfolio value to estimate an annualized money-weighted return.
- Historical prices and quantities are adjusted for stock splits. Dividends are excluded.

## Market data behavior

Current prices come from `yfinance`/Yahoo Finance using a five-day download window and the latest non-null close; this is not guaranteed to be a live intraday quote. Current-price results are cached for five minutes; historical data is cached for one hour. Positions without current quotes are excluded from quoted market-value, cost-basis, unrealized-gain, and allocation totals.

## Setup

From the project root (containing `pyproject.toml`):

```bash
uv sync --link-mode copy
uv run --link-mode copy streamlit run src/portfolio_lens/app.py
```

Open the local URL printed by Streamlit and stop with `Ctrl+C`. In PowerShell, the previously used import fallback is:

```powershell
$env:PYTHONPATH = "$PWD\src"
uv run --link-mode copy streamlit run src/portfolio_lens/app.py
```

## Project structure

```text
uvdemo/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
└── src/portfolio_lens/
    ├── app.py
    └── portfolio.py
```

## Limitations

The parser accepts only BUY and SELL. Dividends, fees, deposits, withdrawals, transfers, and multiple-currency handling are not explicitly modeled. Simple total return is different from XIRR and excludes dividends. Yahoo Finance data may be unavailable or delayed. The app is for analysis/education, not tax or investment advice.

**Not verified:** `pyproject.toml`, `uv.lock`, tests, and `My Stock Portfolio.csv` were not included in this review, so exact dependency versions, test coverage, and sample CSV contents cannot be confirmed.
