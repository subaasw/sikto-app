'use client';

import { Check, Loader2, Plus, Search, Trash2, Upload } from 'lucide-react';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import {
  addAsset,
  deleteAsset,
  listAssets,
  searchMedia,
  uploadAsset,
  type MediaAsset,
  type MediaSearchResult,
} from '@/lib/api';

const KINDS = ['image', 'icon', 'illustration'];

export function MediaManager() {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [kind, setKind] = useState('image');
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  // web search
  const [sq, setSq] = useState('');
  const [sKind, setSKind] = useState('image');
  const [results, setResults] = useState<MediaSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [imported, setImported] = useState<Set<string>>(new Set());

  useEffect(() => {
    listAssets()
      .then(setAssets)
      .catch(() => setError('Could not load media.'))
      .finally(() => setLoading(false));
  }, []);

  async function onAddUrl(e: FormEvent) {
    e.preventDefault();
    if (!url.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const asset = await addAsset({
        kind,
        title: title.trim() || 'Untitled',
        url: url.trim(),
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      setAssets((a) => [asset, ...a]);
      setUrl('');
      setTitle('');
      setTags('');
    } catch {
      setError('Could not add that URL.');
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const asset = await uploadAsset(file, { title: title.trim() || file.name, kind, tags });
      setAssets((a) => [asset, ...a]);
    } catch {
      setError('Upload failed.');
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function onDelete(id: string) {
    setAssets((a) => a.filter((x) => x.id !== id));
    try {
      await deleteAsset(id);
    } catch {
      setError('Delete failed.');
    }
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    if (!sq.trim() || searching) return;
    setSearching(true);
    setError(null);
    try {
      setResults(await searchMedia(sq.trim(), sKind));
    } catch {
      setError('Search failed.');
    } finally {
      setSearching(false);
    }
  }

  async function onImport(r: MediaSearchResult) {
    try {
      const asset = await addAsset({ kind: r.kind, title: r.title, url: r.url, tags: r.tags });
      setAssets((a) => [asset, ...a]);
      setImported((s) => new Set(s).add(r.url));
    } catch {
      setError('Could not import that.');
    }
  }

  const field =
    'border-2 border-border bg-surface px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring';

  return (
    <div className="flex flex-col gap-5">
      <form onSubmit={onAddUrl} className="flex flex-col gap-3 border-2 border-border bg-surface p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <input className={field} placeholder="Image / icon URL" value={url} onChange={(e) => setUrl(e.target.value)} />
          <input className={field} placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className={field} placeholder="Tags (comma separated)" value={tags} onChange={(e) => setTags(e.target.value)} />
          <select className={field} value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" disabled={!url.trim() || busy}>
            {busy ? <Loader2 className="size-4 animate-spin" /> : null} Add by URL
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={() => fileRef.current?.click()}
          >
            <Upload className="size-4" /> Upload file
          </Button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={onUpload} />
          {error ? <span className="text-sm text-red-600 dark:text-red-400">{error}</span> : null}
        </div>
      </form>

      {/* Search free providers (Iconify icons / Openverse images) */}
      <form onSubmit={onSearch} className="flex flex-col gap-3 border-2 border-border bg-surface p-4">
        <div className="flex flex-wrap items-center gap-2">
          <input
            className={`${field} min-w-48 flex-1`}
            placeholder="Search the web for icons or images…"
            value={sq}
            onChange={(e) => setSq(e.target.value)}
          />
          <select className={field} value={sKind} onChange={(e) => setSKind(e.target.value)}>
            <option value="image">Images</option>
            <option value="icon">Icons</option>
          </select>
          <Button type="submit" disabled={!sq.trim() || searching}>
            {searching ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
            Search
          </Button>
        </div>
        {results.length > 0 ? (
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
            {results.map((r) => {
              const done = imported.has(r.url);
              return (
                <button
                  key={r.url}
                  type="button"
                  onClick={() => onImport(r)}
                  disabled={done}
                  title={done ? 'Added' : `Add "${r.title}"`}
                  className="group relative flex aspect-square items-center justify-center overflow-hidden border-2 border-border bg-muted p-1"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={r.thumbnail} alt={r.title} className="size-full object-contain" />
                  <span className="absolute inset-0 flex items-center justify-center bg-black/45 opacity-0 transition-opacity group-hover:opacity-100">
                    {done ? <Check className="size-5 text-primary" /> : <Plus className="size-5 text-white" />}
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}
      </form>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : assets.length === 0 ? (
        <p className="text-sm text-muted-foreground">No media yet — add a URL or upload a file.</p>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {assets.map((a) => (
            <figure key={a.id} className="group relative flex flex-col gap-2">
              <div className="relative aspect-video w-full overflow-hidden border-2 border-border bg-muted">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={a.url} alt={a.title} className="size-full object-contain" />
                <button
                  type="button"
                  onClick={() => onDelete(a.id)}
                  aria-label="Delete"
                  className="absolute right-1 top-1 flex size-7 items-center justify-center border-2 border-border bg-surface opacity-0 transition-opacity hover:bg-muted group-hover:opacity-100"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
              <figcaption className="truncate text-xs font-medium" title={a.title}>
                {a.title}
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </div>
  );
}
