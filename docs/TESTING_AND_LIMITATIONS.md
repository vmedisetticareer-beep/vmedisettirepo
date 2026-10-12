# Testing and Limitations

The following is a proposed test plan; these tests have not been run as part of this review.

## CSV tests
- [ ] Valid CSV and header case/whitespace variations.
- [ ] Missing required header and extra columns.
- [ ] Invalid dates, blank tickers, unsupported transaction type.
- [ ] Missing, zero, negative, or non-numeric quantity/price.
- [ ] Same-day trades retain original ordering.
- [ ] Sale exceeding held quantity is rejected.

## Calculation tests
- [ ] BUY increases shares and basis.
- [ ] Partial/full SELL produces expected average-cost realized gain.
- [ ] Missing quotes are excluded from quoted totals.
- [ ] Split-adjustment behavior is verified with an example.
- [ ] Historical values reconcile against a manually checked example.
- [ ] Total return and XIRR are tested separately.

## Known limitations
- Only BUY/SELL transactions are accepted.
- Fees, dividends, transfers, deposits, and withdrawals are not explicitly modeled.
- The simple return metric excludes dividends and is different from XIRR.
- Prices rely on Yahoo Finance/yfinance and are not guaranteed real-time.
- The exact dependency versions and automated test coverage were not supplied for review.
