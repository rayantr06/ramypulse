interface ProfileMarkProps {
  label?: string;
  className?: string;
}

function initialsFromLabel(label: string) {
  const parts = label.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "RP";
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

export function ProfileMark({ label = "LIDAL Pulse", className = "h-9 w-9" }: ProfileMarkProps) {
  return (
    <div
      aria-label={label}
      className={`${className} flex shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 font-headline text-[11px] font-extrabold text-primary shadow-pulse-glow`}
      role="img"
    >
      {initialsFromLabel(label)}
    </div>
  );
}
