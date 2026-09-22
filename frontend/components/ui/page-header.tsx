import { cn } from "@/lib/utils";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description?: string;
  className?: string;
  children?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, description, className, children }: PageHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between gap-4 flex-wrap", className)}>
      <div>
        <p className="text-muted-foreground text-[10px] font-extrabold font-mono uppercase tracking-[0.2em] mb-1">
          {eyebrow}
        </p>
        <h1 className="text-foreground text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {children}
    </div>
  );
}
