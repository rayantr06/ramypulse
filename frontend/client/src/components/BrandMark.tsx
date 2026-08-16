interface BrandMarkProps {
  compact?: boolean;
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-outline-variant bg-surface"
        aria-hidden="true"
      >
        <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
          <path
            d="M3 12h3.2l1.55-5.1L10.4 17l2.25-8.2 1.7 5.2H21"
            className="stroke-primary"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="3" cy="12" r="1.4" className="fill-tertiary" />
          <circle cx="21" cy="14" r="1.4" className="fill-primary" />
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
