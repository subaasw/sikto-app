import { LibraryBig } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function LibraryPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8 sm:py-14">
      <h1 className="mb-8 text-2xl font-semibold tracking-tight">Library</h1>

      <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-border bg-surface py-16 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <LibraryBig className="size-6" />
        </span>
        <div>
          <p className="font-medium">No lessons yet</p>
          <p className="text-sm text-muted-foreground">Generate your first lesson to see it here.</p>
        </div>
        <Link href="/">
          <Button>Create a lesson</Button>
        </Link>
      </div>
    </div>
  );
}
