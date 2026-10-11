from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio_lens.portfolio import (
    calculate_portfolio,
    calculate_xirr,
    historical_portfolio_values,
    parse_transactions,
    split_adjusted_transactions,
)


st.set_page_config(page_title="Portfolio Lens", page_icon="◒", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap');
    :root { --ink:#172c25; --muted:#68776f; --paper:#f5f5ef; --line:#dce2d9; --green:#176b50; --lime:#d4ec70; --red:#b44d3d; }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
    .stApp { background:var(--paper); }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stSidebar"] { display:none; }
    .block-container { max-width:1440px; padding-top:2rem; padding-bottom:3rem; }
    .eyebrow { font:500 11px 'DM Mono',monospace; color:var(--green); letter-spacing:1.5px; text-transform:uppercase; }
    .masthead { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--line); padding-bottom:18px; margin-bottom:32px; }
    .brand { font:600 22px 'Playfair Display',Georgia,serif; color:var(--ink); }
    .brand span { color:var(--green); }
    h1 { font:600 38px 'Playfair Display',Georgia,serif !important; color:var(--ink) !important; margin:0 !important; }
    h2, h3 { color:var(--ink) !important; }
    .subtitle { color:var(--muted); font-size:14px; margin:8px 0 25px; }
    [data-baseweb="tab-list"] { gap:28px; border-bottom:1px solid var(--line); }
    [data-baseweb="tab"] { padding:12px 2px; height:48px; color:var(--muted); font-weight:600; }
    [aria-selected="true"][data-baseweb="tab"] { color:var(--green) !important; }
    [data-baseweb="tab-highlight"] { background:var(--green); }
    [data-testid="stMetric"] { background:#fff; padding:17px 20px; border:1px solid var(--line); border-radius:5px; }
    [data-testid="stMetricLabel"] p { color:var(--muted); font:500 11px 'DM Mono',monospace; text-transform:uppercase; letter-spacing:.8px; }
    [data-testid="stMetricValue"] { color:var(--ink); font-family:'DM Sans',sans-serif; font-size:25px; }
    [data-testid="stFileUploader"] section { background:#fff; border:1px dashed #aab8ac; border-radius:5px; }
    [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:5px; }
    .note { color:var(--muted); font-size:12px; }
    .section-label { font:500 11px 'DM Mono',monospace; text-transform:uppercase; letter-spacing:1px; color:var(--muted); padding:8px 0 12px; }
    footer { visibility:hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="masthead"><div class="brand">north<span>/</span>star</div>'
    '<div class="eyebrow">PERSONAL PORTFOLIO · MARKETS</div></div>',
    unsafe_allow_html=True,
)
st.markdown("<h1>Know what you own.</h1>", unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">A clear view of your positions, cost basis, and performance.</div>',
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_market_prices(tickers: tuple[str, ...]) -> dict[str, float]:
    import yfinance as yf

    try:
        history = yf.download(
            tickers=list(tickers),
            period="5d",
            auto_adjust=True,
            group_by="ticker",
            progress=False,
            threads=True,
        )
    except Exception:
        return {}

    if history.empty:
        return {}

    prices: dict[str, float] = {}
    for ticker in tickers:
        try:
            if isinstance(history.columns, pd.MultiIndex):
                if ticker in history.columns.get_level_values(0):
                    close = history[ticker]["Close"].dropna()
                elif ticker in history.columns.get_level_values(1):
                    close = history.xs(ticker, axis=1, level=1)["Close"].dropna()
                else:
                    continue
            else:
                close = history["Close"].dropna()
            if not close.empty:
                prices[ticker] = float(close.iloc[-1])
        except (KeyError, TypeError, ValueError):
            continue
    return prices


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(tickers: tuple[str, ...], start_date: str) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    histories: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            history = yf.Ticker(ticker).history(
                start=start_date, auto_adjust=True, actions=True, repair=True
            )
            if not history.empty and "Close" in history:
                histories[ticker] = history
        except Exception:
            continue
    return histories


sample_path = Path(__file__).resolve().parents[3] / "My Stock Portfolio.csv"
sample_bytes = sample_path.read_bytes() if sample_path.is_file() else None
import_tab, portfolio_tab, history_tab = st.tabs(["Import", "Current Holdings", "Historical Performance"])

with import_tab:
    st.markdown('<div class="section-label">01 / Transaction source</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload transaction history",
        type=["csv"],
        help="Required columns: Ticker, Date, Transaction Type, Qty, Price",
    )
    if uploaded_file is not None:
        csv_bytes = uploaded_file.getvalue()
        source_label = uploaded_file.name
    else:
        csv_bytes = sample_bytes
        source_label = "My Stock Portfolio.csv · sample data" if sample_bytes else ""

    transactions: pd.DataFrame | None = None
    holdings: pd.DataFrame | None = None
    realized_gain = 0.0
    load_error: str | None = None
    price_history: dict[str, pd.DataFrame] = {}
    if csv_bytes is not None:
        try:
            transactions = parse_transactions(csv_bytes)
            holdings, realized_gain = calculate_portfolio(transactions)
        except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
            load_error = str(error)

    if load_error:
        st.error(load_error)
    elif transactions is not None and holdings is not None:
        st.caption(f"Loaded **{source_label}**")
        metrics = st.columns(3)
        metrics[0].metric("Transactions", f"{len(transactions):,}")
        metrics[1].metric("Open positions", f"{len(holdings):,}")
        metrics[2].metric("Realized gain", f"${realized_gain:,.2f}")
        st.markdown("#### Import preview")
        preview = transactions.rename(
            columns={"ticker": "Ticker", "date": "Date", "transaction_type": "Transaction Type", "quantity": "Qty", "price": "Price"}
        )
        st.dataframe(preview, use_container_width=True, hide_index=True)
        st.markdown(
            '<div class="note">Buys increase your average-cost basis; sells reduce it and contribute to realized gain. '
            'The optional first CSV column is ignored.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Upload a CSV to build your portfolio. Required columns: Ticker, Date, Transaction Type, Qty, Price.")

with portfolio_tab:
    st.markdown('<div class="section-label">02 / Allocation & performance</div>', unsafe_allow_html=True)
    if load_error:
        st.error(load_error)
    elif holdings is None:
        st.info("Upload transactions to see your portfolio allocation.")
    elif holdings.empty:
        st.info("There are no open positions in this transaction history.")
    else:
        history_tickers = tuple(sorted(transactions["ticker"].unique()))
        history_start = transactions["date"].min().strftime("%Y-%m-%d")
        with st.spinner("Loading split history and latest market quotes…"):
            price_history = fetch_price_history(history_tickers, history_start)
            adjusted_transactions = split_adjusted_transactions(transactions, price_history)
            holdings, realized_gain = calculate_portfolio(adjusted_transactions)
        with st.spinner("Checking latest available market quotes…"):
            market_prices = fetch_market_prices(tuple(holdings["Ticker"].tolist()))

        holdings = holdings.copy()
        holdings["Current Price"] = holdings["Ticker"].map(market_prices)
        holdings["Price Source"] = holdings["Ticker"].map(
            lambda ticker: "Yahoo Finance · latest close" if ticker in market_prices else "Unavailable"
        )
        holdings["Market Value"] = holdings["quantity"] * holdings["Current Price"]
        holdings["Unrealized Gain"] = holdings["Market Value"] - holdings["cost_basis"]
        holdings["Gain %"] = holdings["Unrealized Gain"] / holdings["cost_basis"] * 100
        priced = holdings.dropna(subset=["Current Price"])
        total_value = priced["Market Value"].sum()
        total_basis = priced["cost_basis"].sum()
        total_gain = priced["Unrealized Gain"].sum()
        quote_coverage = len(priced) / len(holdings) * 100

        summary = st.columns(4)
        summary[0].metric("Quoted market value", f"${total_value:,.2f}")
        summary[1].metric("Cost basis · quoted", f"${total_basis:,.2f}")
        summary[2].metric(
            "Unrealized gain · quoted",
            f"${total_gain:,.2f}",
            f"{total_gain / total_basis * 100:+.2f}%" if total_basis else None,
        )
        summary[3].metric("Realized gain", f"${realized_gain:,.2f}")

        chart_column, table_column = st.columns([0.82, 1.5], gap="large")
        with chart_column:
            st.markdown('<div class="section-label">Allocation by market value</div>', unsafe_allow_html=True)
            if priced.empty or total_value <= 0:
                st.info("Allocation is unavailable because no current quotes were returned.")
            else:
                chart = px.pie(
                    priced,
                    values="Market Value",
                    names="Ticker",
                    hole=0.68,
                    color_discrete_sequence=["#176b50", "#c4d96e", "#e69c62", "#5b8e89", "#d56f5e", "#8a9e5e", "#7890a0", "#ccbd91"],
                )
                chart.update_traces(textposition="outside", textinfo="label+percent", marker_line_color="#f5f5ef", marker_line_width=2)
                chart.update_layout(
                    margin=dict(t=12, b=12, l=12, r=12),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="DM Sans, sans-serif", color="#172c25"),
                    annotations=[dict(text=f"${total_value:,.0f}", x=0.5, y=0.5, font_size=19, showarrow=False)],
                )
                st.plotly_chart(chart, use_container_width=True, config={"displayModeBar": False})

        with table_column:
            st.markdown('<div class="section-label">Position breakdown</div>', unsafe_allow_html=True)
            display_holdings = holdings.assign(
                **{
                    "Current Qty": holdings["quantity"],
                    "Average Cost Basis": holdings["average_cost"],
                    "Profit / Gain": holdings["Unrealized Gain"],
                    "Gain %": holdings["Gain %"],
                }
            )[["Ticker", "Current Qty", "Average Cost Basis", "Current Price", "Profit / Gain", "Gain %", "Price Source"]]
            st.dataframe(
                display_holdings,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Current Qty": st.column_config.NumberColumn(format="%.4g"),
                    "Average Cost Basis": st.column_config.NumberColumn(format="$%.2f"),
                    "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                    "Profit / Gain": st.column_config.NumberColumn(format="$%.2f"),
                    "Gain %": st.column_config.NumberColumn(format="%.2f%%"),
                },
            )
        st.caption(
            f"Current prices use yfinance's latest available close. Quotes available for {len(priced)} of {len(holdings)} positions ({quote_coverage:.0f}%); "
            "unavailable prices are excluded from the value, gain, and allocation totals."
        )

with history_tab:
    st.markdown('<div class="section-label">03 / Returns through time</div>', unsafe_allow_html=True)
    if load_error:
        st.error(load_error)
    elif transactions is None:
        st.info("Upload transactions to view historical performance.")
    else:
        gross_buys = float(
            (transactions.loc[transactions["transaction_type"].eq("BUY"), "quantity"]
             * transactions.loc[transactions["transaction_type"].eq("BUY"), "price"]).sum()
        )
        if not price_history:
            ticker_list = tuple(sorted(transactions["ticker"].unique()))
            history_start = transactions["date"].min().strftime("%Y-%m-%d")
            with st.spinner("Loading historical prices from Yahoo Finance…"):
                price_history = fetch_price_history(ticker_list, history_start)
        sale_rows = transactions[transactions["transaction_type"].eq("SELL")]
        sale_proceeds = float((sale_rows["quantity"] * sale_rows["price"]).sum())
        current_value = float(holdings["Market Value"].sum()) if holdings is not None and not holdings.empty else 0.0
        total_return = sale_proceeds + current_value - gross_buys

        metrics = st.columns(5)
        metrics[0].metric("Lifetime investment", f"${gross_buys:,.2f}")
        metrics[1].metric("Total sales / proceeds", f"${sale_proceeds:,.2f}")
        metrics[2].metric("Current portfolio value", f"${current_value:,.2f}")
        metrics[3].metric(
            "Total return", f"${total_return:,.2f}",
            f"{total_return / gross_buys * 100:+.2f}%" if gross_buys else None,
        )

        st.caption("Historical prices and share quantities are adjusted for stock splits. Dividends are excluded.")
        value_series = historical_portfolio_values(transactions, price_history)

        xirr_value = None
        if value_series.empty:
            metrics[4].metric("XIRR", "Unavailable")
        else:
            end_date = value_series.index[-1]
            cash_flows = transactions.assign(
                amount=transactions["quantity"] * transactions["price"]
                * transactions["transaction_type"].map({"BUY": -1.0, "SELL": 1.0})
            )[["date", "amount"]]
            cash_flows = pd.concat(
                [cash_flows, pd.DataFrame([{"date": end_date, "amount": float(value_series.iloc[-1])}])],
                ignore_index=True,
            )
            xirr_value = calculate_xirr(cash_flows)
            metrics[4].metric("XIRR", f"{xirr_value * 100:.2f}%" if xirr_value is not None else "Unavailable")

        st.markdown('<div class="section-label">Portfolio value over time</div>', unsafe_allow_html=True)
        if value_series.empty:
            st.info("Historical values are unavailable. Check ticker symbols or try again later.")
        else:
            trend = px.line(
                x=value_series.index,
                y=value_series.values,
                labels={"x": "Date", "y": "Portfolio value"},
            )
            trend.update_traces(line_color="#176b50", line_width=2.5)
            trend.update_layout(
                margin=dict(t=16, b=12, l=12, r=12),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="DM Sans, sans-serif", color="#172c25"),
                yaxis=dict(tickprefix="$", gridcolor="#dce2d9", zeroline=False),
                xaxis=dict(gridcolor="#dce2d9", zeroline=False),
                hovermode="x unified",
            )
            st.plotly_chart(trend, use_container_width=True, config={"displayModeBar": False})

        ledger = transactions.rename(
            columns={"ticker": "Ticker", "date": "Date", "transaction_type": "Type", "quantity": "Qty", "price": "Price"}
        ).copy()
        ledger["Cash Flow"] = ledger["Qty"] * ledger["Price"] * ledger["Type"].map({"BUY": -1.0, "SELL": 1.0})
        with st.expander("View transaction cash flows"):
            st.dataframe(
                ledger,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.DateColumn(format="MMM D, YYYY"),
                    "Price": st.column_config.NumberColumn(format="$%.2f"),
                    "Cash Flow": st.column_config.NumberColumn(format="$%.2f"),
                    "Qty": st.column_config.NumberColumn(format="%.4g"),
                },
            )
        st.caption(
            "Total return = sale proceeds + current market value − lifetime purchases. "
            "XIRR uses dated buys and sells plus the latest historical portfolio value. "
            "Historical prices are split adjusted; values use Yahoo Finance closing prices and exclude dividends."
        )


