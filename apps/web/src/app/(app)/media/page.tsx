import { Images } from 'lucide-react';
import { BackgroundTile } from '@/components/media/background-tile';
import { MediaManager } from '@/components/media/media-manager';
import { Badge } from '@/components/ui/badge';
import type { BackgroundStyle } from '@/lib/scene/types';

const BACKGROUNDS: { style: BackgroundStyle; label: string }[] = [
  { style: 'gradient', label: 'Gradient' },
  { style: 'mesh', label: 'Mesh' },
  { style: 'grid', label: 'Grid' },
  { style: 'solid', label: 'Solid' },
];

export default function MediaPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-10 sm:px-8 sm:py-14">
      <header className="mb-8 flex flex-col gap-2">
        <Badge tone="active" className="self-start">
          <Images className="size-3" /> Media
        </Badge>
        <h1 className="text-2xl font-semibold tracking-tight">Media library</h1>
        <p className="text-muted-foreground">
          Visual assets the lesson engine can use. Backgrounds are built-in; images and icons
          collected from the web will appear here.
        </p>
      </header>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold tracking-tight">Backgrounds</h2>
        <div className="grid gap-5 sm:grid-cols-2">
          {BACKGROUNDS.map((b) => (
            <figure key={b.style} className="flex flex-col gap-2">
              <BackgroundTile style={b.style} />
              <figcaption className="text-sm font-medium">{b.label}</figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="mt-10 flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold tracking-tight">Images &amp; icons</h2>
          <p className="text-sm text-muted-foreground">
            Add media by URL or upload files. These become available to the AI when building lessons.
          </p>
        </div>
        <MediaManager />
      </section>
    </div>
  );
}
