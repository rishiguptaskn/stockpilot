import { formatINR, formatPercent } from '@stockpilot/ui';

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="w-full max-w-3xl space-y-12">
        <header className="space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/50 px-3 py-1 text-xs font-medium text-zinc-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span>v0.1.0 · pre-implementation</span>
          </div>
          <h1 className="text-4xl font-semibold tracking-tight text-zinc-50 sm:text-5xl">
            StockPilot
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-zinc-400">
            AI-Powered Swing Trading Operating System for Indian Equities.
            Decision-support built on{' '}
            <span className="font-medium text-zinc-200">~200 objective rules</span>{' '}
            from respected trading literature.
          </p>
        </header>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard label="Capital" value={formatINR(500000)} />
          <StatCard label="Risk per trade" value={formatPercent(2)} />
          <StatCard label="Max open positions" value="5" />
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">
            Setup status
          </h2>
          <ul className="space-y-2 text-sm">
            <StatusRow ok label="Monorepo scaffolded" />
            <StatusRow ok label="Next.js 16 + React 19 + Tailwind v4" />
            <StatusRow ok label="Shared packages: config, types, services, ui" />
            <StatusRow ok label="Supabase env vars loaded" />
            <StatusRow label="Supabase schema applied (run migration in dashboard)" />
            <StatusRow label="shadcn/ui components — TBD" />
            <StatusRow label="Rule engine (FastAPI) — Month 3" />
          </ul>
        </section>

        <footer className="border-t border-zinc-800/60 pt-6 text-xs text-zinc-500">
          <p>
            Reference docs:{' '}
            <code className="rounded bg-zinc-900 px-1.5 py-0.5 font-mono text-zinc-400">
              docs/PLAN.md
            </code>{' '}
            ·{' '}
            <code className="rounded bg-zinc-900 px-1.5 py-0.5 font-mono text-zinc-400">
              docs/RULEBOOK.md
            </code>{' '}
            (206 rules)
          </p>
        </footer>
      </div>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="text-xs font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      <div className="mt-1 font-mono text-lg font-medium text-zinc-100">
        {value}
      </div>
    </div>
  );
}

function StatusRow({ ok, label }: { ok?: boolean; label: string }) {
  return (
    <li className="flex items-center gap-3">
      <span
        className={
          ok
            ? 'inline-flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-400'
            : 'inline-flex h-4 w-4 items-center justify-center rounded-full bg-zinc-800 text-zinc-600'
        }
      >
        {ok ? (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-3 w-3"
          >
            <path
              fillRule="evenodd"
              d="M16.704 5.29a1 1 0 010 1.42l-8 8a1 1 0 01-1.41 0l-4-4a1 1 0 111.41-1.42L8 12.585l7.29-7.295a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-3 w-3"
          >
            <circle cx="10" cy="10" r="3" />
          </svg>
        )}
      </span>
      <span className={ok ? 'text-zinc-300' : 'text-zinc-500'}>{label}</span>
    </li>
  );
}
