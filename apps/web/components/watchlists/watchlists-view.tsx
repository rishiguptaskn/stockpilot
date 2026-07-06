'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { Loader2, Plus, Trash2, X } from 'lucide-react';
import { toast } from 'sonner';
import {
  useMyWatchlists,
  useCreateWatchlist,
  useAddTickerToWatchlist,
  useRemoveTickerFromWatchlist,
  useDeleteWatchlist,
  displayTicker,
} from '@stockpilot/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

export function WatchlistsView() {
  const watchlists = useMyWatchlists();
  const createWl = useCreateWatchlist();
  const addTicker = useAddTickerToWatchlist();
  const removeTicker = useRemoveTickerFromWatchlist();
  const deleteWl = useDeleteWatchlist();

  const [newListName, setNewListName] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tickerInput, setTickerInput] = useState('');

  useEffect(() => {
    if (!selectedId && watchlists.data?.length) {
      setSelectedId(watchlists.data[0].id);
    }
  }, [watchlists.data, selectedId]);

  const selected = watchlists.data?.find((w) => w.id === selectedId);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!newListName.trim()) return;
    try {
      const wl = await createWl.mutateAsync({ name: newListName.trim() });
      toast.success('Watchlist created', { description: wl.name });
      setNewListName('');
      setSelectedId(wl.id);
    } catch (err) {
      toast.error('Could not create', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  async function handleAddTicker(e: FormEvent) {
    e.preventDefault();
    if (!selectedId || !tickerInput.trim()) return;
    let t = tickerInput.trim().toUpperCase();
    if (!t.includes('.')) t += '.NS';
    try {
      await addTicker.mutateAsync({ watchlistId: selectedId, ticker: t });
      toast.success('Added', { description: displayTicker(t) });
      setTickerInput('');
    } catch (err) {
      toast.error('Could not add', {
        description: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }

  async function handleRemove(ticker: string) {
    if (!selectedId) return;
    await removeTicker.mutateAsync({ watchlistId: selectedId, ticker });
  }

  async function handleDelete() {
    if (!selectedId) return;
    if (!confirm(`Delete watchlist "${selected?.name}"?`)) return;
    await deleteWl.mutateAsync(selectedId);
    setSelectedId(null);
    toast.success('Watchlist deleted');
  }

  if (watchlists.isLoading) {
    return (
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <Skeleton className="h-64" />
        <Skeleton className="col-span-2 h-64" />
      </div>
    );
  }

  if (watchlists.error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-rose-400">Could not load watchlists.</p>
          <p className="mt-2 text-xs text-muted-foreground">
            You may need to sign in — watchlists are RLS-scoped to your user.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
      {/* Sidebar with list of watchlists */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">My watchlists</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleCreate} className="flex gap-2">
            <Input
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              placeholder="New list name"
              className="text-sm"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!newListName.trim() || createWl.isPending}
            >
              {createWl.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
            </Button>
          </form>

          <div className="space-y-1">
            {watchlists.data?.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No watchlists yet. Create one above.
              </p>
            )}
            {watchlists.data?.map((wl) => (
              <button
                key={wl.id}
                onClick={() => setSelectedId(wl.id)}
                className={cn(
                  'flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors',
                  selectedId === wl.id
                    ? 'bg-accent text-accent-foreground'
                    : 'hover:bg-muted',
                )}
              >
                <span className="truncate">{wl.name}</span>
                <span className="ml-2 shrink-0 rounded-md bg-muted px-1.5 text-[10px] tabular-nums">
                  {wl.tickers.length}
                </span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Main pane: selected watchlist */}
      <Card className="md:col-span-2">
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle className="text-base">
              {selected?.name ?? 'Select a watchlist'}
            </CardTitle>
            {selected && (
              <p className="mt-1 text-xs text-muted-foreground">
                {selected.tickers.length} tickers · created{' '}
                {new Date(selected.created_at).toLocaleDateString('en-IN')}
              </p>
            )}
          </div>
          {selected && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDelete}
              className="text-rose-400 hover:text-rose-300"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {selected ? (
            <>
              <form onSubmit={handleAddTicker} className="flex gap-2">
                <Input
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value)}
                  placeholder="Add ticker (e.g. RELIANCE)"
                  className="text-sm uppercase"
                />
                <Button
                  type="submit"
                  size="sm"
                  disabled={!tickerInput.trim() || addTicker.isPending}
                >
                  {addTicker.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    'Add'
                  )}
                </Button>
              </form>

              <Separator className="my-4" />

              {selected.tickers.length === 0 ? (
                <p className="text-xs text-muted-foreground italic">
                  Empty watchlist. Add tickers above.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {selected.tickers.map((t) => (
                    <Badge
                      key={t}
                      variant="outline"
                      className="group cursor-pointer pr-1 font-mono"
                      onClick={() => handleRemove(t)}
                    >
                      {displayTicker(t)}
                      <X className="ml-1 h-3 w-3 opacity-60 group-hover:opacity-100" />
                    </Badge>
                  ))}
                </div>
              )}

              <p className="mt-4 text-[10px] text-muted-foreground">
                Click a ticker to remove. Scoring against the rule engine — coming with
                Modules 2–10.
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              Create or select a watchlist to get started.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
