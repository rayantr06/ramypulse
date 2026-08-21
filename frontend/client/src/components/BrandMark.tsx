interface BrandMarkProps {
  compact?: boolean;
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="h-10 w-10 shrink-0 overflow-hidden rounded-[14px] shadow-pulse-glow">
        <img
          src="/brand/lidal-mark-dark.png"
          alt="LIDAL Pulse"
          className="h-full w-full scale-[2.2] object-cover"
        />
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
