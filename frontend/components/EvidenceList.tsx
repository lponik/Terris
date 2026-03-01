import AnimatedSection from "@/components/AnimatedSection";
import { formatMiles } from "@/lib/format";
import type { EvidenceCategory, EvidenceItem } from "@/lib/types";

interface EvidenceListProps {
  title: string;
  category: EvidenceCategory;
  items?: EvidenceItem[];
  onEvidenceSelect?: (category: EvidenceCategory, item: EvidenceItem, index: number) => void;
  defaultOpen?: boolean;
}

const categoryTheme: Record<
  EvidenceCategory,
  {
    shell: string;
    card: string;
    mapButton: string;
    mapButtonHover: string;
    name: string;
  }
> = {
  landfill: {
    shell: "border-hazardLandfill/35 bg-hazardLandfillSoft/12",
    card: "border-hazardLandfill/35 bg-hazardLandfillSoft/18",
    mapButton: "border-hazardLandfill/45 text-hazardLandfill",
    mapButtonHover: "hover:bg-hazardLandfill/20 hover:text-hazardLandfill",
    name: "text-hazardLandfill",
  },
  military_base: {
    shell: "border-hazardMilitary/35 bg-hazardMilitarySoft/12",
    card: "border-hazardMilitary/35 bg-hazardMilitarySoft/18",
    mapButton: "border-hazardMilitary/45 text-hazardMilitary",
    mapButtonHover: "hover:bg-hazardMilitary/20 hover:text-hazardMilitary",
    name: "text-hazardMilitary",
  },
  industrial_frs: {
    shell: "border-hazardIndustrial/35 bg-hazardIndustrialSoft/12",
    card: "border-hazardIndustrial/35 bg-hazardIndustrialSoft/18",
    mapButton: "border-hazardIndustrial/45 text-hazardIndustrial",
    mapButtonHover: "hover:bg-hazardIndustrial/20 hover:text-hazardIndustrial",
    name: "text-hazardIndustrial",
  },
  superfund_npl: {
    shell: "border-hazardSuperfund/35 bg-hazardSuperfundSoft/12",
    card: "border-hazardSuperfund/35 bg-hazardSuperfundSoft/18",
    mapButton: "border-hazardSuperfund/45 text-hazardSuperfund",
    mapButtonHover: "hover:bg-hazardSuperfund/20 hover:text-hazardSuperfund",
    name: "text-hazardSuperfund",
  },
};

export default function EvidenceList({
  title,
  category,
  items,
  onEvidenceSelect,
  defaultOpen = false,
}: EvidenceListProps) {
  const theme = categoryTheme[category];
  const topItems = (items ?? []).slice(0, 3);

  const handleSelect = (item: EvidenceItem, index: number) => {
    onEvidenceSelect?.(category, item, index);
  };

  return (
    <AnimatedSection title={title} defaultOpen={defaultOpen} contentClassName={`rounded-xl px-2 py-2 ${theme.shell}`}>
      {topItems.length === 0 ? (
        <p className="text-sm text-muted">No nearby items found.</p>
      ) : (
        <ul className="space-y-2">
          {topItems.map((item, index) => {
            const key = item.id ?? `${item.name ?? "item"}-${index}`;
            const stateSuffix = item.state ? ` (${item.state})` : "";
            return (
              <li key={key} className={`rounded-xl border px-3 py-2 text-sm text-ink ${theme.card}`}>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleSelect(item, index)}
                    className="flex-1 cursor-pointer text-left transition hover:text-white"
                  >
                    <span className={`font-medium ${theme.name}`}>{item.name ?? "Unnamed Site"}</span>
                    <span className="text-muted">{stateSuffix}</span>
                    <span className="text-muted"> - {formatMiles(item.distance_miles)}</span>
                  </button>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      handleSelect(item, index);
                    }}
                    aria-label="Show on map"
                    title="Show on map"
                    className={`rounded-md border bg-panel px-2 py-1 text-xs transition ${theme.mapButton} ${theme.mapButtonHover}`}
                  >
                    📍
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </AnimatedSection>
  );
}
