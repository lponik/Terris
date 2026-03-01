import type { ScoreBreakdown } from "./types";

export function formatMiles(value?: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${value.toFixed(2)} mi`;
}

export function formatLatLon(value?: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return value.toFixed(4);
}

export function formatCount(value?: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return value.toLocaleString("en-US");
}

export function formatTimestamp(value?: string | null): string {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  });
}

export function getBreakdownValues(breakdown?: ScoreBreakdown | null): {
  landfill: number;
  military: number;
  industrial: number;
  superfund: number;
} {
  if (!breakdown) {
    return { landfill: 0, military: 0, industrial: 0, superfund: 0 };
  }

  return {
    landfill: breakdown.landfill ?? breakdown.landfill_proximity ?? 0,
    military: breakdown.military ?? breakdown.military_proximity ?? 0,
    industrial: breakdown.industrial ?? breakdown.industrial_density ?? 0,
    superfund: breakdown.superfund_proximity ?? 0,
  };
}

export function toJsonBlock(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
