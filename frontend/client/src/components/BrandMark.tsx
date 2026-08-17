interface BrandMarkProps {
  compact?: boolean;
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-primary text-primary-foreground shadow-pulse-glow"
        aria-hidden="true"
      >
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="7.5" stroke="currentColor" strokeWidth="1.7" />
          <path d="M8.7 5.25A8.25 8.25 0 1 0 18.75 15.7" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          <circle cx="12" cy="12" r="2.15" fill="currentColor" />
        </svg>
      </div>
      {!compact ? (
        <div className="min-w-0">
          <p className="truncate font-headline text-[17px] font-extrabold tracking-[-0.04em] text-on-surface">
            LIDAL <span className="text-primary">Pulse</span>
          </p>
          <p className="mt-0.5 truncate text-[9px] font-semibold uppercase tracking-[0.16em] text-on-surface-variant">
            Intelligence client
          </p>
        </div>
      ) : null}
    </div>
  );
}
