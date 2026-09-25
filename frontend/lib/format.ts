export function formatMiles(value?: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${value.toFixed(2)} mi`;
}

export function distanceTone(distanceMiles: number): string {
  if (distanceMiles <= 0.5) {
    return "text-danger";
  }
  if (distanceMiles <= 1) {
    return "text-warning";
  }
  return "text-ink";
}

export function formatSiteSource(source: string): string {
  return source.replace(" (legacy)", "");
}
