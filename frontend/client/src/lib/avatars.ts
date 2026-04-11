export function generateInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export function hashColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 60%, 35%)`;
}

export function avatarSVGDataUrl(name: string, size = 40): string {
  const initials = generateInitials(name);
  const bg = hashColor(name);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <rect width="${size}" height="${size}" rx="${size / 5}" fill="${bg}"/>
    <text x="50%" y="50%" dy=".35em" text-anchor="middle" fill="white" font-family="Inter,sans-serif" font-size="${size * 0.4}" font-weight="700">${initials}</text>
  </svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
