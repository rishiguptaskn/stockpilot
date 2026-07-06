"""Rule engine — 10 modules totaling ~200 rules per docs/RULEBOOK.md.

Every rule cites its source book. Every module returns a ModuleScore.
"""

from .module_1_market import evaluate_market_environment

__all__ = ["evaluate_market_environment"]
