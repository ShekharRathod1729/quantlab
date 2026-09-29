"""Searchable stock universe used by the QuantLab interface.

The catalog is refreshed from public constituent lists rather than hard-coding a
rapidly changing index membership list into the UI.  Indian NSE symbols are
translated to their Yahoo Finance form (for example, RELIANCE.NS).
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from urllib.request import urlopen


SP500_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
NIFTY50_URL = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
CACHE_FILE = Path(__file__).with_name("stock_catalog.json")

# A usable offline set; normal operation refreshes this to all index members.
FALLBACK = [
    ("AAPL", "Apple Inc.", "S&P 500"), ("MSFT", "Microsoft Corporation", "S&P 500"),
    ("AMZN", "Amazon.com, Inc.", "S&P 500"), ("GOOGL", "Alphabet Inc.", "S&P 500"),
    ("NVDA", "NVIDIA Corporation", "S&P 500"), ("RELIANCE.NS", "Reliance Industries", "Nifty 50"),
    ("TCS.NS", "Tata Consultancy Services", "Nifty 50"), ("HDFCBANK.NS", "HDFC Bank", "Nifty 50"),
    ("INFY.NS", "Infosys", "Nifty 50"), ("ICICIBANK.NS", "ICICI Bank", "Nifty 50"),
]


def _download_csv(url: str) -> list[dict[str, str]]:
    with urlopen(url, timeout=10) as response:  # nosec B310 -- fixed HTTPS sources
        return list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))


def refresh_catalog() -> list[dict[str, str]]:
    """Download current index constituents and persist a cache for future starts."""
    stocks: dict[str, dict[str, str]] = {}
    for row in _download_csv(SP500_URL):
        symbol = row["Symbol"].replace(".", "-")  # Yahoo uses BRK-B, not BRK.B
        stocks[symbol] = {"symbol": symbol, "name": row["Security"], "index": "S&P 500"}
    for row in _download_csv(NIFTY50_URL):
        symbol = f"{row['Symbol'].strip()}.NS"
        stocks[symbol] = {"symbol": symbol, "name": row["Company Name"].strip(), "index": "Nifty 50"}
    catalog = sorted(stocks.values(), key=lambda item: (item["name"].casefold(), item["symbol"]))
    CACHE_FILE.write_text(json.dumps(catalog), encoding="utf-8")
    return catalog


def get_catalog() -> list[dict[str, str]]:
    """Return current constituents, falling back to the last known cache offline."""
    try:
        return refresh_catalog()
    except Exception:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return [{"symbol": s, "name": n, "index": i} for s, n, i in FALLBACK]
