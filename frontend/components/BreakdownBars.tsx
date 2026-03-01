import { getBreakdownValues } from "@/lib/format";
import type { ScoreBreakdown } from "@/lib/types";

interface BreakdownBarsProps {
  breakdown?: ScoreBreakdown;
}

const breakdownTheme = {
  landfill: {
    bar: "bg-hazardLandfill",
    chip: "border-hazardLandfill/45 bg-hazardLandfillSoft/75 text-hazardLandfill",
    track: "bg-hazardLandfill/12",
  },
  military: {
    bar: "bg-hazardMilitary",
    chip: "border-hazardMilitary/45 bg-hazardMilitarySoft/75 text-hazardMilitary",
    track: "bg-hazardMilitary/12",
  },
  industrial: {
    bar: "bg-hazardIndustrial",
    chip: "border-hazardIndustrial/45 bg-hazardIndustrialSoft/75 text-hazardIndustrial",
    track: "bg-hazardIndustrial/12",
  },
  superfund: {
    bar: "bg-hazardSuperfund",
    chip: "border-hazardSuperfund/45 bg-hazardSuperfundSoft/75 text-hazardSuperfund",
    track: "bg-hazardSuperfund/12",
  },
};

function BreakdownRow({
  label,
  value,
  maxValue,
  barColor,
  chipColor,
  trackColor,
}: {
  label: string;
  value: number;
  maxValue: number;
  barColor: string;
  chipColor: string;
  trackColor: string;
}) {
  const percent = Math.max(0, Math.min(100, (value / maxValue) * 100));

  return (
    <div className="space-y-1.5 rounded-xl border border-border/70 bg-panelSoft/30 px-2.5 py-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${chipColor}`}>
          {label}
        </span>
        <span className="font-semibold tabular-nums text-muted">{value.toFixed(2)}</span>
      </div>
      <div className={`h-2 overflow-hidden rounded-full ${trackColor}`}>
        <div
          className={`h-full rounded-full transition-all duration-300 ${barColor}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export default function BreakdownBars({ breakdown }: BreakdownBarsProps) {
  const values = getBreakdownValues(breakdown);
  const maxValue = Math.max(values.landfill, values.military, values.industrial, values.superfund, 1);

  return (
    <div className="space-y-3">
      <BreakdownRow
        label="Landfill"
        value={values.landfill}
        maxValue={maxValue}
        barColor={breakdownTheme.landfill.bar}
        chipColor={breakdownTheme.landfill.chip}
        trackColor={breakdownTheme.landfill.track}
      />
      <BreakdownRow
        label="Military"
        value={values.military}
        maxValue={maxValue}
        barColor={breakdownTheme.military.bar}
        chipColor={breakdownTheme.military.chip}
        trackColor={breakdownTheme.military.track}
      />
      <BreakdownRow
        label="Industrial"
        value={values.industrial}
        maxValue={maxValue}
        barColor={breakdownTheme.industrial.bar}
        chipColor={breakdownTheme.industrial.chip}
        trackColor={breakdownTheme.industrial.track}
      />
      <BreakdownRow
        label="Superfund"
        value={values.superfund}
        maxValue={maxValue}
        barColor={breakdownTheme.superfund.bar}
        chipColor={breakdownTheme.superfund.chip}
        trackColor={breakdownTheme.superfund.track}
      />
    </div>
  );
}
