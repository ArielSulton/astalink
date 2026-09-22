"use client";

interface TerminalHeaderProps {
  workspaceName: string | null;
}

export function TerminalHeader({ workspaceName }: TerminalHeaderProps) {
  return (
    <div className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-border bg-card/50 px-4 backdrop-blur-sm">
      <div className="flex items-center gap-2.5">
        {workspaceName && (
          <span className="rounded-lg border border-border bg-secondary px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            {workspaceName}
          </span>
        )}
        <span className="hidden items-center gap-1.5 font-mono text-[10px] text-muted-foreground sm:inline-flex">
          <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 font-mono">
            ⌘K
          </kbd>
          command palette
        </span>
      </div>
    </div>
  );
}
