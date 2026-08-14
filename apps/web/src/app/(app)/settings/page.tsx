import { Settings2 } from 'lucide-react';
import { ModelPicker } from '@/components/model-picker';
import { Badge } from '@/components/ui/badge';
import { listProviders, type Provider } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  let providers: Provider[] = [];
  try {
    providers = await listProviders();
  } catch {
    providers = [];
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8 sm:py-14">
      <header className="mb-8 flex flex-col gap-2">
        <Badge tone="active" className="self-start">
          <Settings2 className="size-3" /> Settings
        </Badge>
        <h1 className="text-2xl font-semibold tracking-tight">Model</h1>
        <p className="text-muted-foreground">
          Choose which model writes your lessons. Only providers with an API key configured on
          the server appear here. Your choice is saved in this browser.
        </p>
      </header>

      <ModelPicker providers={providers} />
    </div>
  );
}
