'use client';

import { useState } from 'react';
import { Loader2, Play } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// Nifty 50 core — matches the 30 seeded stocks
const DEFAULT_UNIVERSE = [
  'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'BHARTIARTL.NS', 'ICICIBANK.NS',
  'INFY.NS', 'SBIN.NS', 'LICI.NS', 'HINDUNILVR.NS', 'ITC.NS',
  'LT.NS', 'KOTAKBANK.NS', 'AXISBANK.NS', 'BAJFINANCE.NS', 'SUNPHARMA.NS',
  'M&M.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'NTPC.NS', 'TATAMOTORS.NS',
  'TITAN.NS', 'NESTLEIND.NS', 'ULTRACEMCO.NS', 'ADANIENT.NS', 'BAJAJ-AUTO.NS',
  'WIPRO.NS', 'TECHM.NS', 'HCLTECH.NS', 'POWERGRID.NS', 'ONGC.NS',
];

interface Candidate {
  ticker: string;
  aggregate_score: number;
  verdict: string;
  detected_patterns: string[];
  entry: number;
  stop: number;
  target: number;
  shares: number;
  module_scores: Record<string, number>;
}

export function RunWorkflowButton() {
  const [running, setRunning] = useState(false);

  async function handleRun() {
    setRunning(true);
    const toastId = toast.loading('Running workflow…', {
      description: 'Fetching data + scoring 30 stocks against 206 rules',
    });

    try {
      const res = await fetch(`${API_URL}/engine/run-workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers: DEFAULT_UNIVERSE, capital_inr: 500_000 }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }

      const data = (await res.json()) as {
        as_of: string;
        universe_size: number;
        candidates: Candidate[];
        all_results: Candidate[];
      };

      const candidates = data.candidates?.length ?? 0;
      const topScore = data.all_results?.[0]?.aggregate_score ?? 0;

      toast.dismiss(toastId);
      if (candidates > 0) {
        toast.success(`Workflow complete: ${candidates} candidates`, {
          description: `Universe: ${data.universe_size} stocks. Top score: ${topScore.toFixed(1)}. Refresh Candidates table to see results.`,
        });
      } else {
        toast.info('Workflow complete — no candidates today', {
          description: `Scanned ${data.universe_size} stocks. Top score: ${topScore.toFixed(1)} (threshold ≥ 85).`,
        });
      }
    } catch (err) {
      toast.dismiss(toastId);
      toast.error('Workflow failed', {
        description:
          err instanceof Error
            ? err.message
            : `Could not reach API at ${API_URL}. Start it with: cd apps/api && ./.venv/Scripts/uvicorn stockpilot_api.main:app --reload`,
      });
    } finally {
      setRunning(false);
    }
  }

  return (
    <Button variant="outline" size="sm" onClick={handleRun} disabled={running}>
      {running ? (
        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
      ) : (
        <Play className="mr-1.5 h-4 w-4" />
      )}
      {running ? 'Running…' : 'Run workflow'}
    </Button>
  );
}
