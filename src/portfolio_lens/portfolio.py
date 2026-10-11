from __future__ import annotations

from io import BytesIO
from math import isfinite

import pandas as pd


REQUIRED_COLUMNS = ("ticker", "date", "transaction type", "qty", "price")


def parse_transactions(csv_bytes: bytes) -> pd.DataFrame:
    transactions = pd.read_csv(BytesIO(csv_bytes))
    columns = {str(column).strip().lower(): column for column in transactions.columns}
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    transactions = transactions.rename(
        columns={original: normalized for normalized, original in columns.items()}
    )
    transactions = transactions.loc[:, list(REQUIRED_COLUMNS)].copy()
    transactions.columns = ["ticker", "date", "transaction_type", "quantity", "price"]
    transactions["ticker"] = transactions["ticker"].astype("string").str.strip().str.upper()
    transactions["transaction_type"] = (
        transactions["transaction_type"].astype("string").str.strip().str.upper()
    )
    transactions["date"] = pd.to_datetime(transactions["date"], errors="coerce")
    transactions["quantity"] = pd.to_numeric(transactions["quantity"], errors="coerce")
    transactions["price"] = pd.to_numeric(transactions["price"], errors="coerce")

    invalid = (
        transactions["ticker"].isna()
        | transactions["ticker"].eq("")
        | transactions["date"].isna()
        | ~transactions["transaction_type"].isin(["BUY", "SELL"])
        | transactions["quantity"].isna()
        | transactions["quantity"].le(0)
        | transactions["price"].isna()
        | transactions["price"].le(0)
    )
    if invalid.any():
        rows = ", ".join(str(index + 2) for index in transactions.index[invalid])
        raise ValueError(f"Invalid or incomplete transaction data on CSV row(s): {rows}")

    transactions["_order"] = range(len(transactions))
    transactions = transactions.sort_values(["date", "_order"], kind="stable")
    return transactions.drop(columns="_order").reset_index(drop=True)


def calculate_portfolio(transactions: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    positions: dict[str, dict[str, float]] = {}
    realized_gain = 0.0

    for transaction in transactions.itertuples(index=False):
        ticker = transaction.ticker
        position = positions.setdefault(ticker, {"quantity": 0.0, "cost_basis": 0.0})
        quantity = float(transaction.quantity)
        price = float(transaction.price)

        if transaction.transaction_type == "BUY":
            position["quantity"] += quantity
            position["cost_basis"] += quantity * price
            continue

        held_quantity = position["quantity"]
        if quantity > held_quantity:
            raise ValueError(
                f"{ticker}: cannot sell {quantity:g} shares when only {held_quantity:g} are held."
            )
        average_cost = position["cost_basis"] / held_quantity if held_quantity else 0.0
        realized_gain += quantity * (price - average_cost)
        position["quantity"] -= quantity
        position["cost_basis"] -= quantity * average_cost
        if abs(position["quantity"]) < 1e-9:
            position["quantity"] = 0.0
            position["cost_basis"] = 0.0

    rows = [
        {"Ticker": ticker, **position, "average_cost": position["cost_basis"] / position["quantity"]}
        for ticker, position in positions.items()
        if position["quantity"] > 1e-9
    ]
    return pd.DataFrame(
        rows, columns=["Ticker", "quantity", "cost_basis", "average_cost"]
    ), realized_gain


def calculate_xirr(cash_flows: pd.DataFrame) -> float | None:
    """Return the annualized money-weighted return for dated cash flows."""
    if cash_flows.empty or not {"date", "amount"}.issubset(cash_flows.columns):
        return None

    flows = cash_flows.copy()
    flows["date"] = pd.to_datetime(flows["date"], errors="coerce")
    flows["amount"] = pd.to_numeric(flows["amount"], errors="coerce")
    flows = flows.dropna(subset=["date", "amount"])
    if not (flows["amount"] > 0).any() or not (flows["amount"] < 0).any():
        return None

    start = flows["date"].min()
    years = (flows["date"] - start).dt.total_seconds() / (365.25 * 24 * 60 * 60)
    amounts = flows["amount"].to_numpy(dtype=float)
    years = years.to_numpy(dtype=float)

    def npv(rate: float) -> float:
        try:
            return float((amounts / (1 + rate) ** years).sum())
        except (OverflowError, ZeroDivisionError):
            return float("inf")

    low, high = -0.9999, 1.0
    low_value, high_value = npv(low), npv(high)
    while low_value * high_value > 0 and high < 1_000_000:
        high = high * 2 + 1
        high_value = npv(high)
    if low_value * high_value > 0:
        return None

    for _ in range(200):
        middle = (low + high) / 2
        value = npv(middle)
        if not isfinite(value):
            low = middle
            continue
        if abs(value) < 1e-7:
            return middle
        if (low_value < 0) == (value < 0):
            low, low_value = middle, value
        else:
            high, high_value = middle, value
    return (low + high) / 2


def split_adjusted_transactions(
    transactions: pd.DataFrame, price_history: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """Express every trade in today's share units while preserving its dollar value."""
    adjusted = transactions.copy()
    for ticker, indices in adjusted.groupby("ticker").groups.items():
        history = price_history.get(ticker)
        if history is None or "Stock Splits" not in history:
            continue
        index = pd.DatetimeIndex(history.index)
        if index.tz is not None:
            index = index.tz_localize(None)
        splits = pd.to_numeric(history["Stock Splits"], errors="coerce").fillna(0)
        splits.index = index.normalize()
        splits = splits[splits > 0]
        for row_index in indices:
            trade_date = pd.Timestamp(adjusted.at[row_index, "date"]).normalize()
            later_splits = splits[splits.index > trade_date]
            factor = float(later_splits.prod()) if not later_splits.empty else 1.0
            adjusted.at[row_index, "quantity"] *= factor
            adjusted.at[row_index, "price"] /= factor
    return adjusted


def historical_portfolio_values(
    transactions: pd.DataFrame,
    price_history: dict[str, pd.DataFrame],
) -> pd.Series:
    """Build daily values using split-adjusted prices and share quantities."""
    if transactions.empty or not price_history:
        return pd.Series(dtype=float, name="Portfolio Value")

    normalized: dict[str, pd.DataFrame] = {}
    all_dates: set[pd.Timestamp] = set()
    for ticker, history in price_history.items():
        if history.empty or "Close" not in history:
            continue
        history = history.copy()
        index = pd.DatetimeIndex(history.index)
        if index.tz is not None:
            index = index.tz_localize(None)
        history.index = index.normalize()
        history = history.loc[~history.index.duplicated(keep="last")]
        normalized[ticker] = history
        all_dates.update(history.index)

    if not all_dates:
        return pd.Series(dtype=float, name="Portfolio Value")
    dates = pd.DatetimeIndex(sorted(all_dates))
    ticker_flows: dict[str, list[tuple[pd.Timestamp, float]]] = {}
    for ticker, rows in transactions.groupby("ticker"):
        history = normalized.get(ticker)
        splits = pd.Series(dtype=float)
        if history is not None and "Stock Splits" in history:
            splits = pd.to_numeric(history["Stock Splits"], errors="coerce").fillna(0)
            splits = splits[splits > 0]

        flows = []
        for row in rows.itertuples(index=False):
            transaction_date = pd.Timestamp(row.date).normalize()
            future_splits = splits[splits.index > transaction_date]
            split_factor = float(future_splits.prod()) if not future_splits.empty else 1.0
            quantity = float(row.quantity) * split_factor
            if row.transaction_type == "SELL":
                quantity = -quantity
            flows.append((transaction_date, quantity))
        ticker_flows[ticker] = flows

    total = pd.Series(0.0, index=dates)
    has_value = pd.Series(False, index=dates)
    for ticker, flows in ticker_flows.items():
        history = normalized.get(ticker)
        if history is None:
            continue
        close = pd.to_numeric(history["Close"], errors="coerce").reindex(dates).ffill()
        shares = pd.Series(0.0, index=dates)
        for transaction_date, quantity in flows:
            shares.loc[dates >= transaction_date] += quantity
        valid = close.notna() & (dates >= min(date for date, _ in flows))
        total.loc[valid] += (shares * close).loc[valid]
        has_value |= valid

    result = total.loc[has_value]
    result.name = "Portfolio Value"
    return result
