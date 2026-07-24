"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Markdown renderer for assistant chat bubbles. The backend's allocation
 * report uses GFM tables/headings/lists; user bubbles stay plain text.
 * Hand-styled component map (no typography plugin) so it inherits the
 * bubble's foreground color and stays compact inside a chat column.
 */
export function ChatMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h2: ({ children }) => (
          <h2 className="text-sm font-bold mt-3 mb-1.5 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-[13px] font-bold mt-3 mb-1 first:mt-0">{children}</h3>
        ),
        p: ({ children }) => <p className="my-1.5 first:mt-0 last:mb-0">{children}</p>,
        ul: ({ children }) => (
          <ul className="my-1.5 pl-4 list-disc space-y-0.5">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="my-1.5 pl-4 list-decimal space-y-0.5">{children}</ol>
        ),
        li: ({ children }) => <li className="leading-snug">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        code: ({ children }) => (
          <code className="px-1 py-0.5 rounded bg-secondary text-[12px] font-mono">
            {children}
          </code>
        ),
        hr: () => <hr className="my-3 border-border" />,
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="w-full text-xs border-collapse">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-border px-2 py-1 text-left font-semibold bg-secondary/50">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-border px-2 py-1 text-left">{children}</td>
        ),
        a: ({ children, href }) => (
          <a href={href} className="underline underline-offset-2" target="_blank" rel="noreferrer">
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
