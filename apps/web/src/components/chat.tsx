'use client';

import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useState } from 'react';
import { cn } from '@/lib/utils';

export function Chat() {
  const { messages, sendMessage, status, stop } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  });
  const [input, setInput] = useState('');

  const isBusy = status === 'submitted' || status === 'streaming';

  return (
    <div className="mx-auto flex h-[70vh] w-full max-w-2xl flex-col gap-4 rounded-2xl border border-black/10 bg-white/40 p-6 shadow-sm backdrop-blur dark:border-white/10 dark:bg-black/30">
      <div className="flex-1 space-y-3 overflow-y-auto pr-2">
        {messages.length === 0 && (
          <p className="text-sm text-black/60 dark:text-white/60">Say hello to Sikto.</p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={cn(
              'max-w-[85%] rounded-2xl px-4 py-2 text-sm',
              m.role === 'user'
                ? 'ml-auto bg-black text-white dark:bg-white dark:text-black'
                : 'mr-auto bg-black/5 dark:bg-white/10',
            )}
          >
            {m.parts.map((part, i) =>
              part.type === 'text' ? <span key={i}>{part.text}</span> : null,
            )}
          </div>
        ))}
      </div>

      <form
        className="flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const text = input.trim();
          if (!text || isBusy) return;
          sendMessage({ text });
          setInput('');
        }}
      >
        <input
          className="flex-1 rounded-full border border-black/15 bg-white px-4 py-2 text-sm outline-none focus:border-black dark:border-white/15 dark:bg-black dark:focus:border-white"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Sikto anything…"
          disabled={isBusy}
        />
        {isBusy ? (
          <button
            type="button"
            onClick={stop}
            className="rounded-full bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            className="rounded-full bg-black px-4 py-2 text-sm font-medium text-white hover:bg-black/80 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/80"
            disabled={!input.trim()}
          >
            Send
          </button>
        )}
      </form>
    </div>
  );
}
