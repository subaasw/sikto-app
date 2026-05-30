import { Chat } from '@/components/chat';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-50 p-6 font-sans dark:bg-black">
      <header className="max-w-xl text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-black dark:text-zinc-50">
          Sikto
        </h1>
        <p className="mt-3 text-base text-zinc-600 dark:text-zinc-400">
          Video automation and microlearning platform.
        </p>
      </header>
      <Chat />
    </main>
  );
}
