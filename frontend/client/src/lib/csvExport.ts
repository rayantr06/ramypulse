/**
 * Convertit un tableau d'objets en string CSV.
 * Gère l'échappement des virgules, guillemets et retours à la ligne.
 */
export function convertToCSV(
  items: Record<string, unknown>[],
  columns: { key: string; header: string }[],
): string {
  const headers = columns.map((c) => c.header);
  const rows = items.map((item) =>
    columns
      .map((c) => {
        const val = String(item[c.key] ?? "");
        if (val.includes(",") || val.includes('"') || val.includes("\n")) {
          return `"${val.replace(/"/g, '""')}"`;
        }
        return val;
      })
      .join(","),
  );
  // BOM UTF-8 pour Excel
  return "\uFEFF" + [headers.join(","), ...rows].join("\n");
}

/**
 * Télécharge un string comme fichier via Blob.
 */
export function downloadCSV(content: string, filename: string): void {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
