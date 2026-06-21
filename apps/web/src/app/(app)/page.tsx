import { SourceInput } from '@/components/source-input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function CreatePage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10 sm:px-8 sm:py-14">
      <div className="mb-8 flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Create a lesson</h1>
        <p className="text-muted-foreground">
          Turn any source into a narrated microlearning video with a quiz.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New source</CardTitle>
          <CardDescription>Paste text, an article URL, or a YouTube link.</CardDescription>
        </CardHeader>
        <CardContent>
          <SourceInput />
        </CardContent>
      </Card>
    </div>
  );
}
