# Setup Guide

## Prerequisites
Install a Python version compatible with the project's `.python-version`/`pyproject.toml` and install `uv` using https://docs.astral.sh/uv/getting-started/installation/. Verify with `uv --version`.

## Get the project
If cloning from GitHub:

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

Replace `OWNER/REPOSITORY` with the actual repository. For an existing local copy, open Git Bash in the project root. The development path used previously was `/c/Projects/uvdemo`.

## Install and run

```bash
uv sync --link-mode copy
uv run --link-mode copy streamlit run src/portfolio_lens/app.py
```

Open the local URL printed by Streamlit. Stop with `Ctrl+C`.

### PowerShell import fallback

```powershell
$env:PYTHONPATH = "$PWD\src"
uv run --link-mode copy streamlit run src/portfolio_lens/app.py
```

If needed every time, review package configuration in `pyproject.toml`.

## Troubleshooting
- **`uv` not found:** install it, reopen the terminal, and run `uv --version`.
- **`ModuleNotFoundError: portfolio_lens`:** confirm the project root, `src/portfolio_lens` directory, and package configuration.
- **CSV rejected:** include `Ticker`, `Date`, `Transaction Type`, `Qty`, `Price`; use BUY/SELL, parseable dates, and positive numeric quantity/price.
- **Sell exceeds shares held:** check dates, transaction order, and quantities.
- **No price/history:** verify ticker symbols and internet access; Yahoo Finance data can be unavailable.
- **Port conflict:** append `--server.port 8502` to the Streamlit command.

Never commit credentials, account identifiers, or private brokerage exports. `.gitignore` does not erase secrets already committed.
