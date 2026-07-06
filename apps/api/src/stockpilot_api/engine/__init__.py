"""Rule engine — 10 modules totaling ~200 rules per docs/RULEBOOK.md.

Every rule cites its source book. Every module returns a ModuleScore.

Implemented so far:
  ✅ M1 — Market Environment    (15 rules)
  ✅ M5 — Moving Averages       (20 rules incl. Minervini Trend Template)
  ✅ M9 — Risk Management       (25 rules — Elder 2%/6% + hard gates)
  ⏳ M2, M3, M4, M6, M7, M8, M10 — planned
"""

from .module_1_market import evaluate_market_environment, MarketContext
from .module_5_moving_averages import evaluate_moving_averages, MovingAveragesContext
from .module_9_risk import evaluate_risk_management, RiskContext

__all__ = [
    "evaluate_market_environment",
    "MarketContext",
    "evaluate_moving_averages",
    "MovingAveragesContext",
    "evaluate_risk_management",
    "RiskContext",
]
