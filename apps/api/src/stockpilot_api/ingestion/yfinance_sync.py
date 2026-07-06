"""yfinance ingestion — pulls daily OHLCV for the seeded universe and writes to Supabase.

Design:
  - Reads the stock universe from Supabase `public.stocks` (anon-readable)
  - Fetches per-ticker OHLCV via yfinance (`period="2y"` by default)
  - Writes to Supabase `public.stock_prices` (needs service_role — bypasses RLS)
  - Idempotent via upsert on (ticker, date)

Usage:
    python -m stockpilot_api.ingestion.yfinance_sync

Env vars required:
    NEXT_PUBLIC_SUPABASE_URL      — same as web app
    SUPABASE_SERVICE_ROLE_KEY     — server-only, NEVER expose to browser
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def fetch_daily_ohlcv(ticker: str, period: str = "2y") -> pd.DataFrame:
    """
    Fetch daily OHLCV for a single yfinance ticker (e.g., "RELIANCE.NS").

    Returns a DataFrame with columns [open, high, low, close, volume],
    indexed by date. Empty DataFrame on failure (never raises).
    """
    try:
        raw = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as e:
        logger.warning("yfinance download failed for %s: %s", ticker, e)
        return pd.DataFrame()

    if raw is None or raw.empty:
        return pd.DataFrame()

    # yfinance returns a MultiIndex column when a single ticker is passed too
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw.droplevel(1, axis=1)

    # Normalize column names to match our Supabase schema
    df = raw.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )[["open", "high", "low", "close", "volume"]]

    df.index = pd.to_datetime(df.index).date
    df.index.name = "date"
    return df


def sync_stocks_to_supabase(
    tickers: Iterable[str] | None = None,
    *,
    period: str = "2y",
    supabase_url: str | None = None,
    service_role_key: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Ingest OHLCV for each ticker and upsert into `public.stock_prices`.

    Returns a dict of ticker → rows inserted.
    If `dry_run=True`, skips the DB write.
    """
    load_dotenv()

    url = supabase_url or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    if not url:
        raise RuntimeError("NEXT_PUBLIC_SUPABASE_URL not set")

    if not dry_run:
        key = service_role_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not key:
            raise RuntimeError(
                "SUPABASE_SERVICE_ROLE_KEY not set. This ingestion writes to "
                "public.stock_prices which is protected by RLS. Set the "
                "service_role key in your environment. Never expose it to browsers."
            )

    # Get the ticker universe if not provided
    if tickers is None:
        tickers = _load_active_tickers(url)

    results: dict[str, int] = {}

    if not dry_run:
        from supabase import create_client

        client = create_client(url, key)  # type: ignore[arg-type]

    for ticker in tickers:
        df = fetch_daily_ohlcv(ticker, period=period)
        if df.empty:
            results[ticker] = 0
            logger.warning("No data for %s", ticker)
            continue

        rows = [
            {
                "ticker": ticker,
                "date": date.isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            }
            for date, row in df.iterrows()
        ]

        if dry_run:
            results[ticker] = len(rows)
            logger.info("[dry-run] would upsert %d rows for %s", len(rows), ticker)
            continue

        # Upsert into stock_prices (ticker, date is unique)
        # Chunk to avoid oversized payloads
        CHUNK = 500
        inserted = 0
        for i in range(0, len(rows), CHUNK):
            batch = rows[i : i + CHUNK]
            client.table("stock_prices").upsert(  # type: ignore[union-attr]
                batch, on_conflict="ticker,date"
            ).execute()
            inserted += len(batch)

        results[ticker] = inserted
        logger.info("Upserted %d rows for %s", inserted, ticker)

    return results


def _load_active_tickers(supabase_url: str) -> list[str]:
    """Read active tickers from Supabase using the anon key (public read)."""
    import httpx

    anon = os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    if not anon:
        raise RuntimeError("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY not set")

    response = httpx.get(
        f"{supabase_url}/rest/v1/stocks",
        params={"select": "ticker", "is_active": "eq.true"},
        headers={"apikey": anon, "Authorization": f"Bearer {anon}"},
        timeout=30.0,
    )
    response.raise_for_status()
    rows = response.json()
    return [row["ticker"] for row in rows]


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    )
    dry = os.environ.get("DRY_RUN", "").lower() in {"1", "true", "yes"}
    result = sync_stocks_to_supabase(dry_run=dry)
    print(f"\nDone. Rows per ticker: {result}")
