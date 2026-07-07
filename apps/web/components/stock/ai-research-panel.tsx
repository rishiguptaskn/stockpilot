'use client';

import { useCallback, useRef, useState } from 'react';
import { Bot, Loader2, ShieldAlert, Sparkles, Wrench } from 'lucide-react';
import type {
  AgentFinding,
  AgentFindingWire,
  ResearchReport,
  ResearchReportWire,
  Stance,
} from '@stockpilot/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { getBrowserSupabase } from '@/lib/supabase/browser';
import { AgentCard } from './agent-card';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface TraceEntry {
  agent: string;
  label: string;
}

const STANCE_STYLES: Record<Stance, string> = {
  bullish: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  neutral: 'border-zinc-500/30 bg-zinc-500/10 text-zinc-500',
  bearish: 'border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400',
};

function normalizeFinding(w: AgentFindingWire): AgentFinding {
  return {
    agentName: w.agent_name,
    stance: w.stance,
    confidence: w.confidence,
    summary: w.summary,
    invalidation: w.invalidation,
    dataAvailable: w.data_available,
    evidence: (w.evidence ?? []).map((e) => ({
      claim: e.claim,
      sourceTool: e.source_tool,
      ruleId: e.rule_id,
      citation: e.citation,
    })),
  };
}

function normalizeReport(w: ResearchReportWire): ResearchReport {
  return {
    ticker: w.ticker,
    asOf: w.as_of,
    overallStance: w.overall_stance,
    confidence: w.confidence,
    masterSynthesis: w.master_synthesis,
    findings: (w.findings ?? []).map(normalizeFinding),
    uncertainties: w.uncertainties ?? [],
    aggregateScore: w.aggregate_score,
    verdict: w.verdict,
    disclaimer: w.disclaimer,
    generatedAt: w.generated_at,
    runId: w.run_id,
    costUsd: w.cost_usd,
  };
}

export function AiResearchPanel({ ticker }: { ticker: string }) {
  const [running, setRunning] = useState(false);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async () => {
    setRunning(true);
    setTrace([]);
    setReport(null);
    setError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const {
        data: { session },
      } = await getBrowserSupabase().auth.getSession();

      const res = await fetch(
        `${API_URL}/agents/analyze/stream?ticker=${encodeURIComponent(ticker)}`,
        {
          headers: session?.access_token
            ? { Authorization: `Bearer ${session.access_token}` }
            : {},
          signal: controller.signal,
        },
      );

      if (!res.ok || !res.body) {
        throw new Error(`API responded ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // Read the SSE stream frame by frame.
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx: number;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const line = frame.split('\n').find((l) => l.startsWith('data: '));
          if (!line) continue;
          handleEvent(JSON.parse(line.slice(6)));
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setError(
          err instanceof Error
            ? `${err.message}. Is the API running at ${API_URL} with ANTHROPIC_API_KEY set?`
            : 'Analysis failed',
        );
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }

    function handleEvent(evt: Record<string, unknown>) {
      const type = evt.type as string;
      if (type === 'agent_started') {
        setTrace((t) => [...t, { agent: String(evt.agent), label: `${evt.agent} started` }]);
      } else if (type === 'tool_call') {
        setTrace((t) => [
          ...t,
          { agent: String(evt.agent), label: `${evt.agent} → ${evt.tool}` },
        ]);
      } else if (type === 'agent_finding') {
        setTrace((t) => [
          ...t,
          { agent: String(evt.agent), label: `${evt.agent} finding ready` },
        ]);
      } else if (type === 'done') {
        setReport(normalizeReport(evt.report as ResearchReportWire));
      } else if (type === 'error') {
        setError(String(evt.detail));
      }
    }
  }, [ticker]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" />
          AI Research Report
        </CardTitle>
        <Button variant="outline" size="sm" onClick={run} disabled={running}>
          {running ? (
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
          ) : (
            <Bot className="mr-1.5 h-4 w-4" />
          )}
          {running ? 'Analyzing…' : report ? 'Refresh' : 'Run AI analysis'}
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Live trace */}
        {(running || trace.length > 0) && (
          <div className="rounded-md border bg-muted/30 p-3">
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {trace.map((t, i) => (
                <span key={i} className="inline-flex items-center gap-1">
                  <Wrench className="h-3 w-3" />
                  {t.label}
                  {i < trace.length - 1 && <span className="text-muted-foreground/40">·</span>}
                </span>
              ))}
              {running && <Loader2 className="h-3 w-3 animate-spin" />}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!report && !running && !error && (
          <p className="text-sm text-muted-foreground">
            Run a multi-agent technical analysis. The Master agent orchestrates a Technical
            Analysis agent that reasons only over the deterministic rule engine — every claim
            is traceable to a rule. You make the final decision.
          </p>
        )}

        {report && (
          <div className="space-y-4">
            {/* Master synthesis */}
            <div className="rounded-md border p-4">
              <div className="mb-2 flex items-center gap-2">
                <Badge variant="outline" className={STANCE_STYLES[report.overallStance]}>
                  {report.overallStance}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  confidence {(report.confidence * 100).toFixed(0)}% · as of {report.asOf}
                </span>
                {typeof report.costUsd === 'number' && (
                  <span className="ml-auto font-mono text-[10px] text-muted-foreground">
                    ${report.costUsd.toFixed(4)}
                  </span>
                )}
              </div>
              <p className="text-sm leading-relaxed">{report.masterSynthesis}</p>
            </div>

            {/* Per-agent findings */}
            <div className="space-y-3">
              {report.findings.map((f) => (
                <AgentCard key={f.agentName} finding={f} stanceStyles={STANCE_STYLES} />
              ))}
            </div>

            {/* Uncertainties */}
            {report.uncertainties.length > 0 && (
              <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
                <p className="mb-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                  What this does NOT cover
                </p>
                <ul className="list-inside list-disc space-y-0.5 text-xs text-muted-foreground">
                  {report.uncertainties.map((u, i) => (
                    <li key={i}>{u}</li>
                  ))}
                </ul>
              </div>
            )}

            <Separator />
            <p className="text-[11px] leading-relaxed text-muted-foreground">{report.disclaimer}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
