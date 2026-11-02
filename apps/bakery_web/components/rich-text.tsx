import type { ReactNode } from "react";

/**
 * Renders light inline markdown from assistant copy:
 * **bold** → <strong>, `code` → <code>. Escapes nothing else.
 */
export function RichText({
  text,
  className,
  as: Tag = "span",
}: {
  text: string;
  className?: string;
  as?: "span" | "p" | "div";
}) {
  return <Tag className={className}>{renderInlineMarkdown(text)}</Tag>;
}

export function renderInlineMarkdown(text: string): ReactNode[] {
  if (!text) return [];
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return (
        <strong key={i} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return (
        <code
          key={i}
          className="rounded px-1 py-0.5 font-mono text-[0.9em] bg-black/5"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={i}>{part}</span>;
  });
}
