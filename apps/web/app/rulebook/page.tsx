import { ScrollText } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

export const metadata = { title: 'Rulebook · StockPilot' };

const MODULES = [
  { id: 'M1',  name: 'Market Environment',    count: 15, weight: 15, hardGate: true,  source: "O'Neil (M), Weinstein" },
  { id: 'M2',  name: 'Sector Strength',        count: 10, weight: 10, hardGate: false, source: "O'Neil, Murphy" },
  { id: 'M3',  name: 'Fundamentals (CAN SLIM)',count: 28, weight: 15, hardGate: true,  source: "O'Neil" },
  { id: 'M4',  name: 'Technical Analysis',     count: 40, weight: 15, hardGate: false, source: "Murphy, Minervini" },
  { id: 'M5',  name: 'Moving Averages',        count: 20, weight: 10, hardGate: false, source: "Minervini, Weinstein" },
  { id: 'M6',  name: 'Momentum Indicators',    count: 20, weight: 5,  hardGate: false, source: "Murphy" },
  { id: 'M7',  name: 'Volume Analysis',        count: 15, weight: 10, hardGate: true,  source: "O'Neil, Elder" },
  { id: 'M8',  name: 'News & Events',          count: 15, weight: 5,  hardGate: true,  source: "Claude API" },
  { id: 'M9',  name: 'Risk Management',        count: 25, weight: 10, hardGate: true,  source: "Elder" },
  { id: 'M10', name: 'Portfolio Fit',          count: 10, weight: 5,  hardGate: true,  source: "Portfolio construction" },
] as const;

const PATTERNS = [
  'VCP', 'Cup & Handle', 'Flat Base', 'Bull Flag',
  'Darvas Box', 'Ascending Triangle', 'Stage 2 Breakout', 'EMA Pullback',
] as const;

const BOOKS = [
  { code: '[O]',  title: 'How to Make Money in Stocks',              author: "William J. O'Neil" },
  { code: '[Mv]', title: 'Trade Like a Stock Market Wizard',         author: 'Mark Minervini' },
  { code: '[Mv2]',title: 'Think & Trade Like a Champion',            author: 'Mark Minervini' },
  { code: '[D]',  title: 'How I Made $2,000,000 in the Stock Market',author: 'Nicolas Darvas' },
  { code: '[W]',  title: 'Secrets for Profiting in Bull and Bear Markets', author: 'Stan Weinstein' },
  { code: '[N]',  title: 'Japanese Candlestick Charting Techniques', author: 'Steve Nison' },
  { code: '[Mu]', title: 'Technical Analysis of the Financial Markets', author: 'John Murphy' },
  { code: '[Dg]', title: 'Trading in the Zone / Disciplined Trader', author: 'Mark Douglas' },
  { code: '[E]',  title: 'The New Trading for a Living',             author: 'Alexander Elder' },
] as const;

export default function RulebookPage() {
  const totalRules = MODULES.reduce((sum, m) => sum + m.count, 0);

  return (
    <AppShell breadcrumbs={<span>Rulebook</span>}>
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border bg-muted/40">
            <ScrollText className="h-6 w-6 text-muted-foreground" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">Rulebook</h1>
              <Badge variant="outline" className="font-mono">
                {totalRules} rules · {PATTERNS.length} patterns
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              The complete specification of what the rule engine evaluates on every
              candidate stock. Every rule cites its source book.
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">10 Modules</CardTitle>
            <CardDescription>
              Aggregate score = weighted mean across modules. Threshold ≥ 90 to
              surface as a candidate. Any hard-gate failure rejects the trade.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0">
            <table className="w-full">
              <thead>
                <tr className="border-y border-border text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="px-6 py-2 text-left">Module</th>
                  <th className="px-4 py-2 text-right">Rules</th>
                  <th className="px-4 py-2 text-right">Weight</th>
                  <th className="px-4 py-2 text-center">Hard gate</th>
                  <th className="px-6 py-2 text-left">Primary source</th>
                </tr>
              </thead>
              <tbody>
                {MODULES.map((m) => (
                  <tr key={m.id} className="border-b border-border/60">
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-muted-foreground">
                          {m.id}
                        </span>
                        <span className="font-medium">{m.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm tabular-nums">
                      {m.count}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-sm tabular-nums">
                      {m.weight}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {m.hardGate && (
                        <Badge
                          variant="outline"
                          className="border-amber-500/30 bg-amber-500/10 text-amber-400"
                        >
                          ⚠️ Gate
                        </Badge>
                      )}
                    </td>
                    <td className="px-6 py-3 text-sm text-muted-foreground">
                      {m.source}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-border">
                  <td className="px-6 py-3 font-medium">Total</td>
                  <td className="px-4 py-3 text-right font-mono text-sm font-semibold tabular-nums">
                    {totalRules}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm font-semibold tabular-nums">
                    100
                  </td>
                  <td className="px-4 py-3" />
                  <td className="px-6 py-3" />
                </tr>
              </tfoot>
            </table>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pattern detectors</CardTitle>
              <CardDescription>Only these 8, no more.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {PATTERNS.map((p) => (
                  <Badge key={p} variant="outline" className="font-normal">
                    {p}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Indicators computed</CardTitle>
              <CardDescription>Nothing outside this list.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {['20 EMA', '50 SMA', '150 SMA', '200 SMA', 'Volume', 'RS', 'ADV', 'ATR', 'RSI (context)'].map((i) => (
                  <Badge key={i} variant="outline" className="font-mono font-normal">
                    {i}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Source books</CardTitle>
            <CardDescription>
              Every rule cites one. No rule without a citation.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {BOOKS.map((b) => (
                <li key={b.code} className="flex items-start gap-3">
                  <span className="mt-0.5 shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                    {b.code}
                  </span>
                  <div>
                    <div className="font-medium">{b.title}</div>
                    <div className="text-xs text-muted-foreground">{b.author}</div>
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Separator />

        <p className="text-xs text-muted-foreground">
          Full specification with every rule, threshold, and pseudocode:{' '}
          <code className="font-mono">docs/RULEBOOK.md</code> in the repo.
        </p>
      </div>
    </AppShell>
  );
}
