import Link from 'next/link';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

// The agent emits bare /lessons/<id> action paths (not markdown links). Wrap them
// as real markdown links so they render clickable through the same `a` renderer.
// ponytail: a plain regex, so a /lessons/ path inside a code fence would also get
// wrapped — vanishingly rare in chat; switch to a remark plugin if it ever bites.
function linkifyLessonPaths(text: string): string {
  return text.replace(/(?<![\w/(])(\/lessons\/[\w-]+)/g, '[$1]($1)');
}

const components: Components = {
  a: ({ href, children }) => {
    const url = href ?? '';
    // Internal app routes -> Next Link (client nav); external -> new tab.
    if (url.startsWith('/')) {
      return (
        <Link href={url} className="font-medium text-foreground underline underline-offset-2">
          {children}
        </Link>
      );
    }
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium underline underline-offset-2"
      >
        {children}
      </a>
    );
  },
  p: ({ children }) => <p className="my-2 first:mt-0 last:mb-0 leading-relaxed">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => <h1 className="mt-3 mb-1.5 text-base font-semibold">{children}</h1>,
  h2: ({ children }) => <h2 className="mt-3 mb-1.5 text-base font-semibold">{children}</h2>,
  h3: ({ children }) => <h3 className="mt-3 mb-1 text-sm font-semibold">{children}</h3>,
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-border pl-3 text-muted-foreground">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-border" />,
  code: ({ className, children, ...props }) => {
    const inline = !className?.includes('language-');
    if (inline) {
      return (
        <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="font-mono text-[0.85em]" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg bg-muted p-3 text-[0.85em]">{children}</pre>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="w-full border-collapse text-left">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border border-border px-2 py-1 font-semibold">{children}</th>,
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
};

/** Render assistant chat content as GitHub-flavored markdown, keeping the agent's
 * /lessons/<id> action links clickable. */
export function Markdown({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn('text-sm [word-break:break-word]', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {linkifyLessonPaths(content)}
      </ReactMarkdown>
    </div>
  );
}
