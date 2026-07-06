import { ArrowUpRight } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { ScoreBadge } from '@/components/score-badge';
import { cn } from '@/lib/utils';

export interface CandidateRow {
  ticker: string;
  name: string;
  sector: string;
  score: number;
  entry: number;
  stop: number;
  target: number;
  rr: number;
  pattern?: string;
}

const inr = new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 2,
});

export interface CandidatesTableProps {
  rows: CandidateRow[];
  empty?: boolean;
}

export function CandidatesTable({ rows, empty }: CandidatesTableProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="space-y-1">
          <CardTitle>Top Candidates</CardTitle>
          <CardDescription>
            Ranked by aggregate score across the 200-rule engine. Threshold ≥ 90 to
            surface.
          </CardDescription>
        </div>
        <Badge variant="outline" className="font-mono">
          {rows.length}
        </Badge>
      </CardHeader>
      <CardContent className="p-0">
        {empty || rows.length === 0 ? (
          <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
            <p className="text-sm text-muted-foreground">
              No candidates today.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              The rule engine hasn&apos;t identified any stocks meeting all hard
              gates and score ≥ 90.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-border">
                  <TableHead className="w-[28%]">Stock</TableHead>
                  <TableHead>Sector</TableHead>
                  <TableHead>Pattern</TableHead>
                  <TableHead className="text-right">Entry</TableHead>
                  <TableHead className="text-right">Stop</TableHead>
                  <TableHead className="text-right">Target</TableHead>
                  <TableHead className="text-right">R:R</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow
                    key={row.ticker}
                    className="cursor-pointer border-border hover:bg-muted/40"
                  >
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="flex flex-col leading-tight">
                          <span className="font-mono text-sm font-medium">
                            {row.ticker}
                          </span>
                          <span className="max-w-[220px] truncate text-xs text-muted-foreground">
                            {row.name}
                          </span>
                        </div>
                        <ArrowUpRight className="ml-1 h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">
                        {row.sector}
                      </span>
                    </TableCell>
                    <TableCell>
                      {row.pattern ? (
                        <Badge
                          variant="outline"
                          className="border-emerald-500/20 bg-emerald-500/5 font-normal text-emerald-400"
                        >
                          {row.pattern}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm tabular-nums">
                      ₹{inr.format(row.entry)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm tabular-nums text-rose-400">
                      ₹{inr.format(row.stop)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-sm tabular-nums text-emerald-400">
                      ₹{inr.format(row.target)}
                    </TableCell>
                    <TableCell
                      className={cn(
                        'text-right font-mono text-sm tabular-nums',
                        row.rr >= 3 && 'text-emerald-400',
                        row.rr < 2 && 'text-rose-400',
                      )}
                    >
                      1:{row.rr.toFixed(1)}
                    </TableCell>
                    <TableCell className="text-right">
                      <ScoreBadge score={row.score} size="sm" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
