'use client';

import { useCallback, useState } from 'react';
import {
  Bot,
  CheckCircle2,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Sparkles,
  XCircle,
} from 'lucide-react';
import type { GraphResearchReportWire, ResearchAction, Stance } from '@stockpilot/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { getBrowserSupabase } from '@/lib/supabase/browser';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

const ACTION_STYLES: Record<ResearchAction, string> = {
  candidate: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  watch: 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400',
  'no-trade': 'border-zinc-500/30 bg-zinc-500/10 text-zinc-500',
};

const STANCE_STYLES: Record<Stance, string> = {
  bullish: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  neutral: 'border-zinc-500/30 bg-zinc-500/10 text-zinc-500',
  bearish: 'border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400',
};

function scoreColor(score: number): string {
  if (score >= 90) return 'text-emerald-600 dark:text-emerald-400';
  if (score >= 75) return 'text-amber-600 dark:text-amber-400';
  return 'text-muted-foreground';
}

const inr = (v: number | null | undefined) =>
  v == null ? '—' : `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

export function GraphResearchPanel({ ticker }: { ticker: string }) {
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<GraphResearchReportWire | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      const {
        data: { session },
      } = await getBrowserSupabase().auth.getSession();

      const res = await fetch(`${API_URL}/agents/research`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
        },
        body: JSON.stringify({ ticker }),
      });
      if (!res.ok) {
        const detail = await res
          .json()
          .then((b) => b.detail as string)
          .catch(() => `API responded ${res.status}`);
        throw new Error(detail);
      }
      setReport((await res.json()) as GraphResearchReportWire);
    } catch (err) {
      setError(
        err instanceof Error
          ? `${err.message}. Is the API running at ${API_URL} with an LLM key set?`
          : 'Research failed',
      );
    } finally {
      setRunning(false);
    }
  }, [ticker]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" />
          Deep Research — rule engine + risk gate + AI synthesis
        </CardTitle>
        <Button variant="outline" size="sm" onClick={run} disabled={running}>
          {running ? (
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
          ) : (
            <Bot className="mr-1.5 h-4 w-4" />
          )}
          {running ? 'Researching…' : report ? 'Re-run' : 'Run deep research'}
        </Button>
      </CardHeader>

      <CardContent className="space-y-4">
        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!report && !running && !error && (
          <p className="text-sm text-muted-foreground">
            Full research pass: all 10 rule modules + pattern detectors run deterministically,
            the risk gate can veto (Elder 2%/6%), agents add narrative on top. Every number is
            traceable to a rule; the AI cannot change the decision. You make the final call.
          </p>
        )}

        {report && (
          <div className="space-y-4">
            {/* Decision banner */}
            <div className="flex flex-wrap items-center gap-3 rounded-md border p-4">
              <Badge variant="outline" className={`${ACTION_STYLES[report.action]} text-sm`}>
                {report.action.toUpperCase()}
              </Badge>
              <span className={`font-mono text-2xl font-semibold tabular-nums ${scoreColor(report.aggregate_score)}`}>
                {report.aggregate_score.toFixed(1)}
                <span className="text-sm text-muted-foreground">/100</span>
              </span>
              <Badge variant="outline" className={STANCE_STYLES[report.overall_stance]}>
                {report.overall_stance}
              </Badge>
              <span className="text-xs text-muted-foreground">
                confidence {(report.confidence * 100).toFixed(0)}% · as of {report.as_of}
              </span>
              {report.detected_patterns.length > 0 && (
                <span className="flex flex-wrap gap-1">
                  {report.detected_patterns.map((p) => (
                    <Badge key={p} variant="outline" className="font-mono text-[10px]">
                      {p}
                    </Badge>
                  ))}
                </span>
              )}
            </div>

            {/* Risk gate */}
            <div
              className={`rounded-md border p-4 ${
                report.risk.verdict === 'veto'
                  ? 'border-red-500/30 bg-red-500/5'
                  : 'border-emerald-500/30 bg-emerald-500/5'
              }`}
            >
              <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                {report.risk.verdict === 'veto' ? (
                  <>
                    <ShieldX className="h-4 w-4 text-red-500" />
                    <span className="text-red-600 dark:text-red-400">
                      Risk gate: VETO — no trade regardless of score
                    </span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                    <span className="text-emerald-600 dark:text-emerald-400">
                      Risk gate: passed (Elder 2% / 6%)
                    </span>
                  </>
                )}
              </div>
              {report.risk.reasons.length > 0 && (
                <ul className="list-inside list-disc space-y-0.5 text-xs text-muted-foreground">
                  {report.risk.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
              {report.risk.plan && (
                <div className="mt-2 grid grid-cols-2 gap-2 font-mono text-xs text-muted-foreground sm:grid-cols-5">
                  <span>entry {inr(report.risk.plan.entry)}</span>
                  <span>stop {inr(report.risk.plan.stop)}</span>
                  <span>target {inr(report.risk.plan.target)}</span>
                  <span>{report.risk.plan.shares} shares</span>
                  <span>risk {inr(report.risk.plan.risk_inr)}</span>
                </div>
              )}
            </div>

            {/* AI narrative */}
            <div className="rounded-md border p-4">
              <p className="text-sm leading-relaxed">{report.narrative}</p>
            </div>

            {/* Per-module breakdown */}
            <div className="rounded-md border">
              <p className="border-b px-4 py-2 text-xs font-medium text-muted-foreground">
                Per-module scores — every failed rule listed with its book citation
              </p>
              <div className="divide-y divide-border">
                {report.rule_breakdown.map((m) => (
                  <div key={m.module_id} className="px-4 py-2.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {m.hard_gates_passed ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                        ) : (
                          <XCircle className="h-3.5 w-3.5 text-red-500" />
                        )}
                        <span className="font-mono text-xs text-muted-foreground">
                          {m.module_id}
                        </span>
                        <span className="text-sm">{m.module_name}</span>
                        <Badge variant="outline" className="font-mono text-[10px]">
                          w{m.weight}
                        </Badge>
                      </div>
                      <span
                        className={`font-mono text-sm tabular-nums ${scoreColor(m.score)}`}
                      >
                        {m.score.toFixed(0)}/100
                      </span>
                    </div>
                    {m.failed_rules.length > 0 && (
                      <ul className="mt-1.5 space-y-0.5 pl-6 text-[11px] text-muted-foreground">
                        {m.failed_rules.map((r, i) => (
                          <li key={i} className={r.hard_gate ? 'text-red-500/90' : ''}>
                            {r.hard_gate ? '⛔ ' : ''}
                            <span className="font-mono">{r.rule_id}</span>: {String(r.actual)}{' '}
                            vs {String(r.threshold)}
                            {r.citation && (
                              <span className="text-muted-foreground/60"> — {r.citation}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Uncertainties + notes + errors */}
            {(report.uncertainties.length > 0 ||
              report.notes.length > 0 ||
              report.errors.length > 0) && (
              <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
                <p className="mb-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                  What this does NOT cover
                </p>
                <ul className="list-inside list-disc space-y-0.5 text-xs text-muted-foreground">
                  {[...report.uncertainties, ...report.notes, ...report.errors].map((u, i) => (
                    <li key={i}>{u}</li>
                  ))}
                </ul>
              </div>
            )}

            <Separator />
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              {report.disclaimer}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
