"""Rule engine — 10 modules totaling ~200 rules per docs/RULEBOOK.md."""

from .module_1_market import evaluate_market_environment, MarketContext
from .module_2_sector import evaluate_sector_strength, SectorContext
from .module_3_fundamentals import evaluate_fundamentals, FundamentalsContext
from .module_4_technical import evaluate_technical_analysis, TechnicalContext
from .module_5_moving_averages import evaluate_moving_averages, MovingAveragesContext
from .module_6_momentum import evaluate_momentum, MomentumContext
from .module_7_volume import evaluate_volume, VolumeContext
from .module_8_news import evaluate_news, NewsContext
from .module_9_risk import evaluate_risk_management, RiskContext
from .module_10_portfolio import evaluate_portfolio_fit, PortfolioContext

__all__ = [
    "evaluate_market_environment", "MarketContext",
    "evaluate_sector_strength", "SectorContext",
    "evaluate_fundamentals", "FundamentalsContext",
    "evaluate_technical_analysis", "TechnicalContext",
    "evaluate_moving_averages", "MovingAveragesContext",
    "evaluate_momentum", "MomentumContext",
    "evaluate_volume", "VolumeContext",
    "evaluate_news", "NewsContext",
    "evaluate_risk_management", "RiskContext",
    "evaluate_portfolio_fit", "PortfolioContext",
]
