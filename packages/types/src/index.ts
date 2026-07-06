/**
 * StockPilot — Shared Types
 *
 * Populated during Month 1-2 as we implement the rule engine and data schema.
 * See docs/RULEBOOK.md for the source-of-truth rule definitions.
 * See docs/PLAN.md § 9 for the database schema these types mirror.
 */

// ---------- Core primitives ----------

export type ISODate = string; // YYYY-MM-DD
export type ISODateTime = string; // full ISO-8601

export type StockTicker = string; // e.g., "RELIANCE.NS"

export type Exchange = 'NSE' | 'BSE';

// ---------- Stock ----------

export interface Stock {
  ticker: StockTicker;
  name: string;
  sector: string;
  industry: string;
  exchange: Exchange;
}

// ---------- OHLCV bar ----------

export interface StockPrice {
  ticker: StockTicker;
  date: ISODate;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  /** NSE-specific: delivered quantity as a percentage of total volume */
  deliveryPct?: number;
}

// ---------- Rule engine ----------

/**
 * One of the ~200 rules from RULEBOOK.md, evaluated for a given stock on a given date.
 */
export interface RuleEvaluation {
  ruleId: string; // e.g., "M1.1", "M4.18", "P1"
  moduleId: string; // "M1" ... "M10", "P" for patterns
  passed: boolean;
  score?: number; // 0-100 if this rule produces a sub-score
  actualValue?: number | string;
  threshold?: number | string;
  isHardGate: boolean;
  sourceCitation: string; // e.g., "[O] O'Neil, CAN SLIM"
}

/**
 * Aggregated score for one module (M1..M10) on a given stock.
 */
export interface ModuleScore {
  moduleId: string;
  moduleName: string;
  score: number; // 0-100
  weightInAggregate: number; // 0-100
  ruleEvaluations: RuleEvaluation[];
  hardGatesPassed: boolean;
}

/**
 * Fully-evaluated candidate for a given date.
 */
export interface TradeCandidate {
  id: string;
  ticker: StockTicker;
  candidateDate: ISODate;
  aggregateScore: number; // 0-100
  moduleScores: ModuleScore[];
  hardGatesAllPassed: boolean;
  /** "candidate" (>=90), "watch" (85-89), "reject" (<85) */
  verdict: 'candidate' | 'watch' | 'reject';
  suggestedEntry?: number;
  suggestedStop?: number;
  suggestedTarget?: number;
  suggestedShares?: number;
  detectedPatterns?: string[];
}

// ---------- Trade & Journal ----------

export interface Trade {
  id: string;
  ticker: StockTicker;
  entryDate: ISODate;
  entryPrice: number;
  stopPrice: number;
  targetPrice: number;
  shares: number;
  exitDate?: ISODate;
  exitPrice?: number;
  status: 'open' | 'closed_win' | 'closed_loss' | 'closed_breakeven';
  candidateId?: string; // links back to TradeCandidate that surfaced this
}

export interface JournalEntry {
  id: string;
  tradeId: string;
  entryReason: string;
  exitReason?: string;
  ruleAdherence?: number; // 0-100 self-assessed
  lessons?: string;
  createdAt: ISODateTime;
}

// ---------- Market & Sector context ----------

export interface MarketSnapshot {
  date: ISODate;
  niftyClose: number;
  niftyAbove200SMA: boolean;
  distributionDaysLast20: number;
  fiiNetLast10: number;
  diiNetLast10: number;
  vix: number;
}
