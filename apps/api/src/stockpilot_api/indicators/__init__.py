"""Technical indicators — pure numeric functions on OHLCV pandas frames.

Every indicator returns a pandas Series aligned with the input's index.
No indicator outside this package is allowed in the rule engine per PLAN.md.

Indicators implemented (per docs/RULEBOOK.md "Indicators" section):
  - SMA (Simple Moving Average)
  - EMA (Exponential Moving Average, standard 2/(n+1) smoothing)
  - ATR (Average True Range, Wilder's smoothing)
  - RSI (Relative Strength Index, Wilder's smoothing) — CONTEXT ONLY, not entry
  - Relative Strength rank vs a benchmark
"""

from .sma import sma
from .ema import ema
from .atr import atr
from .rsi import rsi
from .relative_strength import rs_rank_252

__all__ = ["sma", "ema", "atr", "rsi", "rs_rank_252"]
