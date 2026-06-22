'use client';

import { Check, Link2, Loader2, Plus, Search, Trash2, Upload, X } from 'lucide-react';
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import {
  addAsset,
  deleteAsset,
  listAssets,
  searchMedia,
  uploadAssets,
  type MediaAsset,
  type MediaSearchResult,
} from '@/lib/api';

const SEARCH_KINDS = [
  { value: 'image', label: 'Images' },
  { value: 'icon', label: 'Icons' },
  { value: 'logo', label: 'Logos' },
];

const field =
  'border-2 border-border bg-surface px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring';

export function MediaManager() {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  // web search
  const [sq, setSq] = useState('');
  const [sKind, setSKind] = useState('image');
  const [results, setResults] = useState<MediaSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [imported, setImported] = useState<Set<string>>(new Set());
  // add-by-url (secondary)
  const [showUrl, setShowUrl] = useState(false);
  const [url, setUrl] = useState('');

  useEffect(() => {
    listAssets()
      .then(setAssets)
      .catch(() => setError('Could not load media.'))
      .finally(() => setLoading(false));
  }, []);

  async function doUpload(files: File[]) {
    const imgs = files.filter((f) => f.type.startsWith('image/'));
    if (imgs.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const added = await uploadAssets(imgs, { kind: 'image', tags: '' });
      setAssets((a) => [...added, ...a]);
    } catch {
      setError('Upload failed.');
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    void doUpload(Array.from(e.dataTransfer.files));
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

  async function onAddUrl(e: FormEvent) {
    e.preventDefault();
    if (!url.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const asset = await addAsset({ kind: 'image', title: 'Untitled', url: url.trim(), tags: [] });
      setAssets((a) => [asset, ...a]);
      setUrl('');
      setShowUrl(false);
    } catch {
      setError('Could not add that URL.');
    } finally {
      setBusy(false);
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

  return (
    <div className="flex flex-col gap-6">
      {/* Toolbar: search + kind toggle + drag-and-drop upload */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col gap-3 border-2 border-dashed p-4 transition-colors ${
          dragging ? 'border-primary bg-primary/5' : 'border-border bg-surface'
        }`}
      >
        <form onSubmit={onSearch} className="flex flex-wrap items-center gap-2">
          <div className="flex min-w-56 flex-1 items-center gap-2">
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              className={`${field} flex-1`}
              placeholder="Search the web…"
              value={sq}
              onChange={(e) => setSq(e.target.value)}
            />
          </div>
          <div className="flex overflow-hidden border-2 border-border">
            {SEARCH_KINDS.map((k) => (
              <button
                key={k.value}
                type="button"
                onClick={() => setSKind(k.value)}
                className={`px-3 py-2 text-sm transition-colors ${
                  sKind === k.value ? 'bg-primary text-primary-foreground' : 'bg-surface hover:bg-muted'
                }`}
              >
                {k.label}
              </button>
            ))}
          </div>
          <Button type="submit" disabled={!sq.trim() || searching}>
            {searching ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />} Search
          </Button>
        </form>

        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <Upload className="size-4" />
          <span>Drag &amp; drop images here, or</span>
          <Button
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={() => fileRef.current?.click()}
          >
            {busy ? <Loader2 className="size-4 animate-spin" /> : null} Choose files
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => void doUpload(Array.from(e.target.files ?? []))}
          />
          <button
            type="button"
            onClick={() => setShowUrl((v) => !v)}
            className="ml-auto inline-flex items-center gap-1 underline-offset-2 hover:underline"
          >
            <Link2 className="size-3.5" /> Add by URL
          </button>
        </div>

        {showUrl ? (
          <form onSubmit={onAddUrl} className="flex items-center gap-2">
            <input
              className={`${field} flex-1`}
              placeholder="https://…/image.png"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              autoFocus
            />
            <Button type="submit" disabled={!url.trim() || busy}>
              Add
            </Button>
            <button type="button" onClick={() => setShowUrl(false)} aria-label="Cancel">
              <X className="size-4" />
            </button>
          </form>
        ) : null}

        {error ? <span className="text-sm text-red-600 dark:text-red-400">{error}</span> : null}
      </div>

      {/* Web results to import */}
      {results.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-sm font-medium text-muted-foreground">
            Results — click to add to your library
          </h2>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
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
        </section>
      ) : null}

      {/* Library */}
      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-medium text-muted-foreground">Your library</h2>
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : assets.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nothing yet — search the web or drop in some files.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {assets.map((a) => (
              <figure key={a.id} className="group relative flex flex-col gap-2">
                <div className="relative aspect-square w-full overflow-hidden border-2 border-border bg-muted">
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
      </section>
    </div>
  );
}
