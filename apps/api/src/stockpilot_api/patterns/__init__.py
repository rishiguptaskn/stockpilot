"""Pattern detectors — per docs/RULEBOOK.md § Pattern Detectors.

Only 8 patterns allowed, no more:
  P1 VCP · P2 Cup & Handle · P3 Flat Base · P4 Bull Flag
  P5 Darvas Box · P6 Ascending Triangle · P7 Stage 2 Breakout · P8 EMA Pullback

Each detector returns a `PatternDetection` object with:
  - detected (bool)
  - quality_score (0-100)
  - metadata (dict of pattern-specific details)
"""

from dataclasses import dataclass, field
from typing import Any

from .vcp import detect_vcp
from .stage_2_breakout import detect_stage_2_breakout

__all__ = ["detect_vcp", "detect_stage_2_breakout", "PatternDetection"]


@dataclass
class PatternDetection:
    """Return type for every pattern detector."""

    pattern_name: str
    detected: bool
    quality_score: float = 0.0  # 0-100
    metadata: dict[str, Any] = field(default_factory=dict)
