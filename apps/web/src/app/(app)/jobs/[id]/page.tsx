import { redirect } from 'next/navigation';

// Lessons and their generation job share one id, so a lesson lives at a single
// canonical URL (/lessons/[id]). Keep this path as a redirect for old links.
export default async function JobRedirect({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/lessons/${id}`);
}
