"""Scoring pipeline — combines module scores into an aggregate + verdict.

Per docs/RULEBOOK.md § Scoring Aggregation:
  - Aggregate = weighted mean of module scores
  - Threshold ≥ 90 = candidate
  - 85–89 = watch
  - < 75 = filter out
  - Any hard-gate failure → aggregate = 0 (rejected)
"""

from .aggregator import aggregate_scores, ScoreVerdict

__all__ = ["aggregate_scores", "ScoreVerdict"]
