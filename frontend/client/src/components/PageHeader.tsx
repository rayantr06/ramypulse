import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description?: string;
  descriptionClassName?: string;
  actions?: ReactNode;
  badge?: ReactNode;
  tone?: "monitor" | "risk" | "insight" | "action" | "setup";
}

const TONE_CLASSES = {
  monitor: "bg-monitor-container text-monitor",
  risk: "bg-error-container text-error",
  insight: "bg-insight-container text-insight",
  action: "bg-action-container text-action",
  setup: "bg-surface-container-high text-on-surface-variant",
} as const;

export function PageHeader({ eyebrow, title, description, descriptionClassName = "", actions, badge, tone = "monitor" }: PageHeaderProps) {
  return (
    <header className="pb-1">
      <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-headline text-[clamp(2rem,3.4vw,3.35rem)] font-semibold leading-[0.98] tracking-[-0.04em] text-on-surface">
              {title}
            </h1>
            <span className={`rounded-full px-3 py-1.5 text-[10px] font-bold ${TONE_CLASSES[tone]}`}>
              {eyebrow}
            </span>
            {badge}
          </div>
          {description ? (
            <p className={`mt-3 max-w-3xl text-sm leading-6 text-on-surface-variant ${descriptionClassName}`}>
              {description}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2 xl:justify-end">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
