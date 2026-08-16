import { useEffect, useState } from "react";

interface ProfileMarkProps {
  label?: string;
  imageSrc?: string | null;
  imageAlt?: string;
  className?: string;
}

function initialsFromLabel(label: string) {
  const parts = label.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "RP";
  return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

export function ProfileMark({
  label = "LIDAL Pulse",
  imageSrc,
  imageAlt,
  className = "h-9 w-9",
}: ProfileMarkProps) {
  const [hasImageError, setHasImageError] = useState(false);

  useEffect(() => {
    setHasImageError(false);
  }, [imageSrc]);

  const showImage = Boolean(imageSrc) && !hasImageError;

  return (
    <div
      aria-label={imageAlt || label}
      className={`${className} flex shrink-0 items-center justify-center overflow-hidden rounded-xl border font-headline text-[11px] font-extrabold ${
        showImage
          ? "border-outline-variant bg-surface"
          : "border-primary/20 bg-primary/10 text-primary shadow-pulse-glow"
      }`}
      role="img"
    >
      {showImage ? (
        <img
          alt=""
          className="h-full w-full object-contain p-0.5"
          onError={() => setHasImageError(true)}
          src={imageSrc ?? undefined}
        />
      ) : (
        initialsFromLabel(label)
      )}
    </div>
  );
}
