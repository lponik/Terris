import { formatCount, formatMiles } from "@/lib/format";
import type { Signals } from "@/lib/types";

interface SignalsTableProps {
  signals?: Signals;
}

export default function SignalsTable({ signals }: SignalsTableProps) {
  const rows = [
    {
      label: "Nearest landfill",
      value: formatMiles(signals?.nearest_landfill_miles),
      tone: "landfill" as const,
    },
    {
      label: "Nearest military base",
      value: formatMiles(signals?.nearest_military_base_miles),
      tone: "military" as const,
    },
    {
      label: "Nearest industrial site",
      value: formatMiles(signals?.nearest_industrial_frs_miles),
      tone: "industrial" as const,
    },
    {
      label: "Nearest Superfund NPL",
      value: formatMiles(signals?.nearest_superfund_npl_miles),
      tone: "superfund" as const,
    },
    {
      label: "Industrial count (1 mi)",
      value: formatCount(signals?.industrial_count_1mi),
      tone: "industrial" as const,
    },
    {
      label: "Industrial count (3 mi)",
      value: formatCount(signals?.industrial_count_3mi),
      tone: "industrial" as const,
    },
    {
      label: "Industrial count (10 mi)",
      value: formatCount(signals?.industrial_count_10mi),
      tone: "industrial" as const,
    },
    {
      label: "Superfund count (3 mi)",
      value: formatCount(signals?.superfund_count_3mi),
      tone: "superfund" as const,
    },
  ];

  const toneClasses: Record<typeof rows[number]["tone"], { dot: string; label: string; value: string }> = {
    landfill: {
      dot: "bg-hazardLandfill",
      label: "text-hazardLandfill",
      value: "text-hazardLandfill",
    },
    military: {
      dot: "bg-hazardMilitary",
      label: "text-hazardMilitary",
      value: "text-hazardMilitary",
    },
    industrial: {
      dot: "bg-hazardIndustrial",
      label: "text-hazardIndustrial",
      value: "text-hazardIndustrial",
    },
    superfund: {
      dot: "bg-hazardSuperfund",
      label: "text-hazardSuperfund",
      value: "text-hazardSuperfund",
    },
  };

  return (
    <div className="divide-y divide-border">
      {rows.map((row) => (
        <div key={row.label} className="flex items-center justify-between gap-4 py-2 text-sm">
          <span className={`inline-flex items-center gap-2 ${toneClasses[row.tone].label}`}>
            <span className={`h-2 w-2 rounded-full ${toneClasses[row.tone].dot}`} />
            {row.label}
          </span>
          <span className={`font-semibold tabular-nums ${toneClasses[row.tone].value}`}>{row.value}</span>
        </div>
      ))}
    </div>
  );
}
