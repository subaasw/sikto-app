'use client';

import Link from 'next/link';
import { Loader2, Send, Square } from 'lucide-react';
import { Fragment, useEffect, useRef, useState } from 'react';
import { streamChat, type ChatMessage } from '@/lib/api';
import { cn } from '@/lib/utils';

type Message = ChatMessage & { id: string };

let counter = 0;
const nextId = () => `m${++counter}`;

// Make the agent's /lessons/<id> action links clickable instead of plain text.
function renderContent(text: string) {
  const parts = text.split(/(\/lessons\/[\w-]+)/g);
  return parts.map((part, i) =>
    /^\/lessons\/[\w-]+$/.test(part) ? (
      <Link key={i} href={part} className="underline underline-offset-2">
        {part}
      </Link>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep the transcript pinned to the latest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  function stop() {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;

    const userMsg: Message = { id: nextId(), role: 'user', content: text };
    const assistantId = nextId();
    const history = [...messages, userMsg];
    setMessages([...history, { id: assistantId, role: 'assistant', content: '' }]);
    setInput('');
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const payload = history.map(({ role, content }) => ({ role, content }));
      let received = false;
      for await (const chunk of streamChat(payload, controller.signal)) {
        received = true;
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + chunk } : m)),
        );
      }
      // A 200 with an empty stream must not leave a blank bubble — surface it.
      if (!received && !controller.signal.aborted) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: '⚠ No response from the assistant. Is the API running?' }
              : m,
          ),
        );
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        const detail = err instanceof Error ? err.message : 'Something went wrong';
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content || `⚠ ${detail}` } : m,
          ),
        );
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
    }
  }

  return (
    <div className="flex h-[70vh] w-full flex-col border-2 border-border bg-surface shadow-pixel">
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-5">
        {messages.length === 0 ? (
          <p className="text-sm text-muted-foreground">Say hello to Sikto.</p>
        ) : null}
        {messages.map((m) => (
          <div
            key={m.id}
            className={cn(
              'max-w-[85%] border-2 border-border px-3 py-2 text-sm',
              m.role === 'user'
                ? 'ml-auto bg-primary text-primary-foreground'
                : 'mr-auto bg-muted text-foreground',
            )}
          >
            {m.content ? (
              <span className="whitespace-pre-wrap">{renderContent(m.content)}</span>
            ) : (
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
            )}
          </div>
        ))}
      </div>

      <form
        className="flex items-center gap-2 border-t-2 border-border p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          className="flex-1 border-2 border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Sikto anything…"
        />
        {busy ? (
          <button
            type="button"
            onClick={stop}
            aria-label="Stop"
            className="flex size-10 items-center justify-center border-2 border-border bg-red-500 text-white transition-colors hover:bg-red-600"
          >
            <Square className="size-4" />
          </button>
        ) : (
          <button
            type="submit"
            aria-label="Send"
            disabled={!input.trim()}
            className="flex size-10 items-center justify-center border-2 border-border bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            <Send className="size-4" />
          </button>
        )}
      </form>
    </div>
  );
}
