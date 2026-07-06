import type { LucideIcon } from 'lucide-react';
import { AppShell } from '@/components/layout/app-shell';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface PlaceholderPageProps {
  title: string;
  breadcrumb: string;
  icon: LucideIcon;
  description: string;
  plannedIn: string; // e.g. "Month 3"
  features: string[];
}

/**
 * Placeholder for routes that are in the plan but not yet implemented.
 * Keeps the sidebar navigation working while making the roadmap visible to the user.
 */
export function PlaceholderPage({
  title,
  breadcrumb,
  icon: Icon,
  description,
  plannedIn,
  features,
}: PlaceholderPageProps) {
  return (
    <AppShell breadcrumbs={<span>{breadcrumb}</span>}>
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border bg-muted/40">
            <Icon className="h-6 w-6 text-muted-foreground" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
              <Badge variant="outline" className="ml-2">
                Planned · {plannedIn}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">What this page will do</CardTitle>
            <CardDescription>
              Feature scope per{' '}
              <code className="font-mono text-xs">docs/PLAN.md</code>. Order may
              shift based on backtest findings.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground" />
                  <span className="text-muted-foreground">{f}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <div className="rounded-md border border-border/60 bg-muted/30 p-4 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Status:</span>{' '}
          Not yet implemented. Track progress in the repo commits and{' '}
          <code className="font-mono">docs/PLAN.md § 10</code> roadmap.
        </div>
      </div>
    </AppShell>
  );
}
