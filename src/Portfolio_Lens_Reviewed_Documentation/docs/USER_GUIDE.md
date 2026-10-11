# User Guide

## Import
Upload a CSV or, if present at the path expected by the app, use `My Stock Portfolio.csv`. Review the normalized preview and transaction count, open-position count, and realized gain. Required columns: `Ticker`, `Date`, `Transaction Type`, `Qty`, and `Price`. Only BUY and SELL are accepted.

## Current Holdings
This tab displays a market-value allocation chart and position breakdown. Metrics include quoted market value, cost basis for priced positions, unrealized gain for priced positions, realized gain, current price, gain percentage, and quote coverage. Current prices use the latest available close returned by yfinance/Yahoo Finance in a recent five-day window—not guaranteed real-time prices. Positions without quotes are excluded from several aggregate totals.

## Historical Performance
- **Lifetime investment:** sum of BUY quantity × price.
- **Total sales/proceeds:** sum of SELL quantity × price.
- **Current portfolio value:** sum of available market values in the holdings dataframe.
- **Total return:** sales proceeds + current value − gross purchases.
- **Return percentage:** total return divided by gross purchases, when nonzero.
- **XIRR:** annualized money-weighted return from dated buys, sells, and terminal historical portfolio value, when solvable.

The tab also shows a portfolio-value line chart and expandable cash-flow table. BUY cash flows are negative; SELL cash flows are positive. Dividends are excluded.
