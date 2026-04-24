from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import yfinance as yf


@dataclass
class OHLCVSnapshot:
    code: str
    as_of: date
    last_close: float
    history_csv: str  # compact CSV the LLM can read directly


def fetch_recent_ohlcv(code: str, lookback_days: int = 180) -> OHLCVSnapshot:
    """Fetch recent daily bars for a Tokyo Stock Exchange ticker.

    Accepts a 4-digit JP code (e.g. "7203"); appends ".T" for Yahoo.
    """
    code = code.strip()
    ticker_symbol = code if "." in code else f"{code}.T"
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period=f"{lookback_days}d", auto_adjust=False)
    if hist.empty:
        raise ValueError(
            f"No price data returned for {ticker_symbol}. "
            "Verify it is a valid TSE code."
        )
    last_close = float(hist["Close"].iloc[-1])
    last_date = hist.index[-1].date()
    compact = hist[["Open", "High", "Low", "Close", "Volume"]].round(2)
    return OHLCVSnapshot(
        code=code,
        as_of=last_date,
        last_close=last_close,
        history_csv=compact.to_csv(),
    )
