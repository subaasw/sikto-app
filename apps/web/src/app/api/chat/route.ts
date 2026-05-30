import { convertToModelMessages, type UIMessage } from 'ai';
import { getSiktoAgent } from '@/lib/agent';

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  const result = await getSiktoAgent().stream({
    messages: await convertToModelMessages(messages),
  });

  return result.toUIMessageStreamResponse();
}
