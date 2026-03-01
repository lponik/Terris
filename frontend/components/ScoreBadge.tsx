import type { RiskBand } from "@/lib/types";

interface ScoreBadgeProps {
  score?: number;
  band?: RiskBand;
  isLoading?: boolean;
}

const bandStyles: Record<RiskBand, { pill: string; ring: string; label: string }> = {
  Low: {
    pill: "bg-low/15 text-low",
    ring: "ring-low/35",
    label: "Low",
  },
  Moderate: {
    pill: "bg-moderate/15 text-moderate",
    ring: "ring-moderate/35",
    label: "Moderate",
  },
  High: {
    pill: "bg-high/15 text-high",
    ring: "ring-high/35",
    label: "High",
  },
};

export default function ScoreBadge({ score, band, isLoading = false }: ScoreBadgeProps) {
  const styles = band ? bandStyles[band] : null;

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-panelSoft p-5 ring-1 ring-border">
        <div className="h-4 w-28 animate-pulse rounded bg-border" />
        <div className="mt-4 h-14 w-32 animate-pulse rounded bg-border" />
      </div>
    );
  }

  const safeScore = typeof score === "number" ? score.toFixed(2) : "--";

  return (
    <div
      className={`rounded-2xl border border-border bg-panel p-5 shadow-sm ring-1 ${
        styles?.ring ?? "ring-border"
      }`}
    >
      <p className="text-sm font-medium text-muted">Total score</p>
      <div className="mt-3 flex items-end justify-between gap-3">
        <p className="text-5xl font-bold leading-none text-ink">
          {safeScore}
        </p>
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            styles?.pill ?? "bg-panelSoft text-muted"
          }`}
        >
          {styles?.label ?? "Pending"}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5 text-[10px] font-semibold">
        <span className="rounded-full border border-hazardLandfill/45 bg-hazardLandfillSoft/70 px-2 py-0.5 text-hazardLandfill">
          Landfill
        </span>
        <span className="rounded-full border border-hazardMilitary/45 bg-hazardMilitarySoft/70 px-2 py-0.5 text-hazardMilitary">
          Military
        </span>
        <span className="rounded-full border border-hazardIndustrial/45 bg-hazardIndustrialSoft/70 px-2 py-0.5 text-hazardIndustrial">
          Industrial
        </span>
        <span className="rounded-full border border-hazardSuperfund/45 bg-hazardSuperfundSoft/70 px-2 py-0.5 text-hazardSuperfund">
          Superfund
        </span>
      </div>
      <p className="mt-2 text-xs text-muted">Scale: deterministic model score out of 10.</p>
    </div>
  );
}
