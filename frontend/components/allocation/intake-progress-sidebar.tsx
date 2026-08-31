"use client";

import type { LucideIcon } from "lucide-react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SectionStatus {
  key: string;
  label: string;
  icon: LucideIcon;
  completed: number;
  total: number;
}

interface IntakeProgressSidebarProps {
  sections: SectionStatus[];
  activeSection?: string;
  onSectionClick: (key: string) => void;
  className?: string;
}

export function IntakeProgressSidebar({ sections, activeSection, onSectionClick, className }: IntakeProgressSidebarProps) {
  const totalFilled = sections.reduce((sum, s) => sum + s.completed, 0);
  const totalFields = sections.reduce((sum, s) => sum + s.total, 0);
  const percentage = totalFields > 0 ? (totalFilled / totalFields) * 100 : 0;

  return (
    <div className={cn("space-y-4", className)}>
      {/* Ring Progress */}
      <div className="rounded-xl bg-card ring-1 ring-foreground/10 p-5">
        <div className="flex flex-col items-center gap-3">
          <div className="relative w-20 h-20">
            <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
              <circle
                cx="18" cy="18" r="15.915"
                fill="none"
                className="stroke-secondary"
                strokeWidth="2.5"
              />
              <circle
                cx="18" cy="18" r="15.915"
                fill="none"
                className="stroke-chart-2 transition-all duration-700 ease-out"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeDasharray={`${percentage} ${100 - percentage}`}
                strokeDashoffset="0"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono font-bold text-foreground text-xl leading-none tabular-nums">
                {Math.round(percentage)}%
              </span>
              <span className="text-[8px] text-muted-foreground font-mono uppercase tracking-wider mt-0.5">
                Lengkap
              </span>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground font-mono text-center">
            {totalFilled} dari {totalFields} field terisi
          </p>
        </div>
      </div>

      {/* Section List */}
      <div className="rounded-xl bg-card ring-1 ring-foreground/10 p-3 space-y-0.5">
        {sections.map((section) => (
          <button
            key={section.key}
            onClick={() => onSectionClick(section.key)}
            className={cn(
              "flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-left transition-colors",
              activeSection === section.key
                ? "bg-secondary text-foreground"
                : "hover:bg-secondary/50 text-muted-foreground hover:text-foreground"
            )}
          >
            <section.icon className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[11px] font-medium flex-1 min-w-0 truncate">
              {section.label}
            </span>
            {section.completed === section.total && section.total > 0 ? (
              <span className="w-5 h-5 rounded-full bg-chart-2/15 border border-chart-2/30 flex items-center justify-center shrink-0">
                <Check className="h-3 w-3 text-chart-2" />
              </span>
            ) : section.completed > 0 ? (
              <span className="text-[9px] font-mono font-bold text-amber-400 shrink-0">
                {section.completed}/{section.total}
              </span>
            ) : (
              <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30 shrink-0" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
