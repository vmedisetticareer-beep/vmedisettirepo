# Technical Documentation

## Architecture
`app.py` implements the Streamlit UI and calls helpers from `portfolio.py`.

- `parse_transactions`: reads CSV bytes; validates and normalizes fields; sorts transactions by date while preserving original same-day order.
- `calculate_portfolio`: tracks shares and cost basis per ticker; computes realized gain using average cost.
- `fetch_market_prices` in `app.py`: retrieves recent price data with `yfinance.download`, selects latest non-null Close, and caches for 300 seconds.
- `fetch_price_history`: retrieves history from the earliest transaction date with `Ticker.history(auto_adjust=True, actions=True, repair=True)`, cached for 3600 seconds.
- `split_adjusted_transactions`: applies later stock-split factors to past quantities/prices.
- `historical_portfolio_values`: estimates daily portfolio value using adjusted closes and share quantities.
- `calculate_xirr`: solves annualized money-weighted return by bisection.

## CSV validation
Headers required: `ticker`, `date`, `transaction type`, `qty`, `price`. Matching is case-insensitive and trims header whitespace. Ticker and transaction type are uppercased. Empty tickers, unparseable dates, transaction types other than BUY/SELL, and missing/non-positive quantity or price are rejected. Extra columns are discarded.

## Formulas
BUY increases quantity and cost basis by quantity × price. SELL gain is quantity sold × (sale price − average cost per share before sale). Remaining cost basis is reduced proportionally using that average cost. Fees are not included.

Market value is quantity × current adjusted close. Unrealized gain is market value minus remaining cost basis. Gross purchases and sale proceeds are sums of quantity × price for BUY and SELL rows respectively. Dollar total return is sale proceeds + current portfolio value − gross purchases. XIRR uses dated signed trade cash flows plus final historical portfolio value.

## Important caveats
- Only BUY and SELL are supported; dividends, fees, deposits, withdrawals, and transfers are not explicitly modeled.
- Yahoo Finance data is not guaranteed live and can be missing.
- Unpriced positions are omitted from quoted aggregate totals.
- The simple total-return metric is not the same as XIRR.
- `pyproject.toml`, `uv.lock`, tests, and the optional sample CSV were not supplied, so exact dependencies, test coverage, and sample-file behavior could not be independently verified.
