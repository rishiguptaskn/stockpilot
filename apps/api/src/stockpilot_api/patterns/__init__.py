"""Pattern detectors — per docs/RULEBOOK.md § Pattern Detectors.

All 8 patterns implemented:
  P1 VCP · P2 Cup & Handle · P3 Flat Base · P4 Bull Flag
  P5 Darvas Box · P6 Ascending Triangle · P7 Stage 2 Breakout · P8 EMA Pullback

Every detector returns a dict:
  { pattern_name: str, detected: bool, quality_score: float (0-100), metadata: dict }
"""

from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

from .vcp import detect_vcp
from .cup_and_handle import detect_cup_and_handle
from .flat_base import detect_flat_base
from .bull_flag import detect_bull_flag
from .darvas_box import detect_darvas_box
from .ascending_triangle import detect_ascending_triangle
from .stage_2_breakout import detect_stage_2_breakout
from .ema_pullback import detect_ema_pullback

__all__ = [
    "detect_vcp",
    "detect_cup_and_handle",
    "detect_flat_base",
    "detect_bull_flag",
    "detect_darvas_box",
    "detect_ascending_triangle",
    "detect_stage_2_breakout",
    "detect_ema_pullback",
    "detect_all_patterns",
    "PatternDetection",
]


@dataclass
class PatternDetection:
    pattern_name: str
    detected: bool
    quality_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


ALL_DETECTORS: list[Callable[[pd.DataFrame], dict]] = [
    detect_vcp,
    detect_cup_and_handle,
    detect_flat_base,
    detect_bull_flag,
    detect_darvas_box,
    detect_ascending_triangle,
    detect_stage_2_breakout,
    detect_ema_pullback,
]


def detect_all_patterns(daily: pd.DataFrame) -> list[dict]:
    """Run every detector; return only those that detected a pattern."""
    results = []
    for detector in ALL_DETECTORS:
        try:
            r = detector(daily)
            if r.get("detected"):
                results.append(r)
        except Exception:
            # Any detector that errors is simply reported as not detected
            continue
    return results
