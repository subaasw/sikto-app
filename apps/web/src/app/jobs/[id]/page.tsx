import { JobProgress } from '@/components/job-progress';

export default async function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  return (
    <div className="mx-auto max-w-2xl px-6 py-10 sm:px-8 sm:py-14">
      <div className="mb-8 flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Generating your lesson</h1>
        <p className="text-muted-foreground">
          This usually takes a moment — you can keep this tab open.
        </p>
      </div>

      <JobProgress jobId={id} />
    </div>
  );
}
