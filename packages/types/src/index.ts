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

// ---------- AI Agent layer ----------
// Mirrors apps/api/src/stockpilot_api/agents/schemas.py. Every number in a report
// originates from an MCP tool call — agents never fabricate market data.

export type Stance = 'bullish' | 'neutral' | 'bearish';

/** One data-backed claim, tied to the MCP tool that produced it. */
export interface Evidence {
  claim: string;
  sourceTool: string; // e.g. "detect_patterns"
  ruleId?: string; // e.g. "M5.3"
  citation?: string; // e.g. "[O] O'Neil"
}

/** A single domain agent's verdict on a ticker. */
export interface AgentFinding {
  agentName: string;
  stance: Stance;
  confidence: number; // 0-1
  summary: string;
  evidence: Evidence[];
  invalidation: string;
  dataAvailable: boolean;
}

/** The Master agent's synthesis across all domain findings. */
export interface ResearchReport {
  ticker: StockTicker;
  asOf: ISODate;
  overallStance: Stance;
  confidence: number; // 0-1
  masterSynthesis: string;
  findings: AgentFinding[];
  uncertainties: string[];
  aggregateScore?: number;
  verdict?: string;
  disclaimer: string;
  generatedAt?: ISODateTime;
  /** Populated by the API response (not the model). */
  runId?: string;
  costUsd?: number;
}

/** SSE events streamed from GET /agents/analyze/stream. */
export type AgentStreamEvent =
  | { type: 'agent_started'; agent: string }
  | { type: 'tool_call'; agent: string; tool: string; args: Record<string, unknown> }
  | { type: 'agent_finding'; agent: string; finding: AgentFindingWire }
  | { type: 'report'; agent: string; report: ResearchReportWire }
  | { type: 'done'; report: ResearchReportWire & { run_id?: string; cost_usd?: number } }
  | { type: 'error'; detail: string };

/**
 * Wire shapes: the API serialises Pydantic models with snake_case field names.
 * Use `normalizeReport` (in the web app) to map these to the camelCase types above.
 */
export interface AgentFindingWire {
  agent_name: string;
  stance: Stance;
  confidence: number;
  summary: string;
  evidence: Array<{ claim: string; source_tool: string; rule_id?: string; citation?: string }>;
  invalidation: string;
  data_available: boolean;
}

export interface ResearchReportWire {
  ticker: string;
  as_of: string;
  overall_stance: Stance;
  confidence: number;
  master_synthesis: string;
  findings: AgentFindingWire[];
  uncertainties: string[];
  aggregate_score?: number;
  verdict?: string;
  disclaimer: string;
  generated_at?: string;
  run_id?: string;
  cost_usd?: number;
}

/**
 * LangGraph research run (POST /agents/research) — the full explainable report:
 * deterministic decision + risk gate + per-rule breakdown + AI narrative.
 */
export type ResearchAction = 'candidate' | 'watch' | 'no-trade';

export interface GraphRiskWire {
  verdict: 'ok' | 'veto';
  reasons: string[];
  plan: {
    entry: number | null;
    stop: number | null;
    target: number | null;
    shares: number;
    risk_inr: number | null;
  } | null;
}

export interface GraphFailedRuleWire {
  rule_id: string | null;
  actual: string | number | null;
  threshold: string | number | null;
  hard_gate: boolean;
  citation: string | null;
}

export interface GraphModuleBreakdownWire {
  module_id: string;
  module_name: string;
  score: number;
  weight: number;
  hard_gates_passed: boolean;
  failed_rules: GraphFailedRuleWire[];
}

export interface GraphResearchReportWire {
  ticker: string;
  as_of: string;
  action: ResearchAction;
  aggregate_score: number;
  engine_verdict: string;
  risk: GraphRiskWire;
  overall_stance: Stance;
  confidence: number;
  narrative: string;
  uncertainties: string[];
  findings: AgentFindingWire[];
  detected_patterns: string[];
  rule_breakdown: GraphModuleBreakdownWire[];
  notes: string[];
  errors: string[];
  disclaimer: string;
  generated_at: string;
}
