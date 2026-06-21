import { Sparkles } from 'lucide-react';
import { ScenePreview } from '@/components/templates/scene-preview';
import { Badge } from '@/components/ui/badge';
import { listTemplates, type Template } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function TemplatesPage() {
  let templates: Template[] = [];
  try {
    templates = await listTemplates();
  } catch {
    templates = [];
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 sm:px-8 sm:py-14">
      <header className="mb-8 flex flex-col gap-2">
        <Badge tone="active" className="self-start">
          <Sparkles className="size-3" /> Templates
        </Badge>
        <h1 className="text-2xl font-semibold tracking-tight">Lesson templates</h1>
        <p className="text-muted-foreground">
          Pick a look for your videos. Each template restyles the whole lesson — palette,
          background, and accents — in both the player and the rendered MP4.
        </p>
      </header>

      {templates.length === 0 ? (
        <div className="border-2 border-dashed border-border bg-surface py-16 text-center text-sm text-muted-foreground">
          No templates available — is the API running?
        </div>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2">
          {templates.map((t) => (
            <article key={t.id} className="flex flex-col gap-3">
              <ScenePreview theme={t.theme} />
              <div className="flex flex-col gap-1">
                <h2 className="text-lg font-semibold tracking-tight">{t.name}</h2>
                <p className="text-sm text-muted-foreground">{t.description}</p>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
