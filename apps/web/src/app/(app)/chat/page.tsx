import { Chat } from '@/components/chat';

export default function ChatPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-10 sm:px-8 sm:py-14">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="text-muted-foreground">
          Ask about your material, or tell Sikto to make a lesson — it can create lessons, list
          them, and check their status.
        </p>
      </div>
      <Chat />
    </div>
  );
}
