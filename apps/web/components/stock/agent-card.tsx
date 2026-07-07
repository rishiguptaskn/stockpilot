import { ChevronRight } from 'lucide-react';
import type { AgentFinding, Stance } from '@stockpilot/types';
import { Badge } from '@/components/ui/badge';

const AGENT_LABELS: Record<string, string> = {
  technical: 'Technical Analysis Agent',
  master: 'Master Agent',
};

export function AgentCard({
  finding,
  stanceStyles,
}: {
  finding: AgentFinding;
  stanceStyles: Record<Stance, string>;
}) {
  const label = AGENT_LABELS[finding.agentName] ?? finding.agentName;

  return (
    <div className="rounded-md border">
      <div className="flex items-center justify-between border-b px-4 py-2.5">
        <span className="text-sm font-medium">{label}</span>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={stanceStyles[finding.stance]}>
            {finding.stance}
          </Badge>
          <span className="font-mono text-xs text-muted-foreground">
            conf {(finding.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      <div className="space-y-3 px-4 py-3">
        {!finding.dataAvailable && (
          <p className="text-xs text-amber-600 dark:text-amber-400">
            Data was unavailable for this agent — treat with caution.
          </p>
        )}

        <p className="text-sm leading-relaxed text-muted-foreground">{finding.summary}</p>

        {finding.evidence.length > 0 && (
          <ul className="space-y-1.5">
            {finding.evidence.map((e, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm">
                <ChevronRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground/50" />
                <span className="flex-1">
                  {e.claim}
                  <span className="ml-1.5 font-mono text-[10px] text-muted-foreground">
                    ↳ {e.ruleId ?? e.sourceTool}
                    {e.citation ? ` · ${e.citation}` : ''}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}

        <div className="rounded bg-muted/40 px-2.5 py-1.5 text-xs">
          <span className="font-medium text-foreground">Invalidates if: </span>
          <span className="text-muted-foreground">{finding.invalidation}</span>
        </div>
      </div>
    </div>
  );
}
