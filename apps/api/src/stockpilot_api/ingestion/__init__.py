"""Data ingestion — pulls market data from yfinance and writes to Supabase."""

from .yfinance_sync import fetch_daily_ohlcv, sync_stocks_to_supabase

__all__ = ["fetch_daily_ohlcv", "sync_stocks_to_supabase"]
