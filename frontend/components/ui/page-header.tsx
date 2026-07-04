import { cn } from "@/lib/utils";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  className?: string;
  children?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, className, children }: PageHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between gap-4 flex-wrap", className)}>
      <div>
        <p className="text-muted-foreground text-[10px] font-black font-mono uppercase tracking-[0.2em] mb-1">
          {eyebrow}
        </p>
        <h1 className="text-foreground text-2xl font-bold tracking-tight">{title}</h1>
      </div>
      {children}
    </div>
  );
}
