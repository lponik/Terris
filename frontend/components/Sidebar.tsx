import { useEffect, useState } from "react";

import AnimatedSection from "@/components/AnimatedSection";
import BreakdownBars from "@/components/BreakdownBars";
import ScoreBadge from "@/components/ScoreBadge";
import SignalsTable from "@/components/SignalsTable";
import { formatMiles } from "@/lib/format";
import type { AnalyzeResponse, EvidenceCategory, EvidenceItem } from "@/lib/types";

interface SidebarProps {
  analysis: AnalyzeResponse | null;
  analysisError: string | null;
  isAnalyzing: boolean;
  onEvidenceSelect: (category: EvidenceCategory, item: EvidenceItem, index: number) => void;
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
      {message}
    </div>
  );
}

export default function Sidebar({
  analysis,
  analysisError,
  isAnalyzing,
  onEvidenceSelect,
}: SidebarProps) {
  const [isBreakdownOpen, setIsBreakdownOpen] = useState(true);
  const [isTopDriversOpen, setIsTopDriversOpen] = useState(true);
  const [isSignalsOpen, setIsSignalsOpen] = useState(true);
  const [analysisRevealKey, setAnalysisRevealKey] = useState(0);

  useEffect(() => {
    if (!analysis) {
      return;
    }

    setIsBreakdownOpen(true);
    setIsTopDriversOpen(true);
    setIsSignalsOpen(true);
    setAnalysisRevealKey((current) => current + 1);
  }, [analysis]);

  const hazardToneClasses = {
    landfill: {
      chip: "border-hazardLandfill/45 bg-hazardLandfillSoft/70 text-hazardLandfill",
      card: "border-hazardLandfill/35 bg-hazardLandfillSoft/22",
    },
    military: {
      chip: "border-hazardMilitary/45 bg-hazardMilitarySoft/70 text-hazardMilitary",
      card: "border-hazardMilitary/35 bg-hazardMilitarySoft/22",
    },
    superfund: {
      chip: "border-hazardSuperfund/45 bg-hazardSuperfundSoft/70 text-hazardSuperfund",
      card: "border-hazardSuperfund/35 bg-hazardSuperfundSoft/22",
    },
    neutral: {
      chip: "border-border bg-panel text-muted",
      card: "border-border bg-panel",
    },
  } as const;

  const hazardToneLabel: Record<keyof typeof hazardToneClasses, string> = {
    landfill: "Landfill",
    military: "Military",
    superfund: "Superfund",
    neutral: "Driver",
  };

  const nearbyHazards = [
    {
      category: "landfill" as const,
      categoryLabel: "Landfill",
      tone: "landfill" as const,
      items: analysis?.evidence.landfill ?? [],
    },
    {
      category: "military_base" as const,
      categoryLabel: "Military",
      tone: "military" as const,
      items: analysis?.evidence.military_base ?? [],
    },
    {
      category: "superfund_npl" as const,
      categoryLabel: "Superfund",
      tone: "superfund" as const,
      items: analysis?.evidence.superfund_npl ?? [],
    },
  ]
    .flatMap((group) =>
      group.items.slice(0, 3).map((item, sourceIndex) => ({
        category: group.category,
        categoryLabel: group.categoryLabel,
        tone: group.tone,
        item,
        sourceIndex,
        distance: item.distance_miles,
      })),
    )
    .sort((left, right) => {
      const leftDistance = typeof left.distance === "number" ? left.distance : Number.POSITIVE_INFINITY;
      const rightDistance = typeof right.distance === "number" ? right.distance : Number.POSITIVE_INFINITY;
      return leftDistance - rightDistance;
    });

  const driverTone = (text: string): keyof typeof hazardToneClasses => {
    const normalized = text.toLowerCase();
    if (normalized.includes("superfund") || normalized.includes("npl")) {
      return "superfund";
    }
    if (normalized.includes("military")) {
      return "military";
    }
    if (normalized.includes("landfill")) {
      return "landfill";
    }
    return "neutral";
  };

  return (
    <aside className="flex h-full min-h-[320px] flex-col overflow-hidden rounded-3xl border border-border bg-panel shadow-panel">
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        <header>
          <h1 className="text-2xl font-bold leading-tight text-ink">Exposure Screening</h1>
          <p className="mt-1 text-sm text-muted">Proximity signals from three public site datasets.</p>
        </header>

        {analysisError ? <ErrorBox message={analysisError} /> : null}

        <div key={`analysis-score-${analysisRevealKey}`} className="analysis-enter">
          <ScoreBadge
            score={analysis?.score.total}
            band={analysis?.score.band}
            isLoading={isAnalyzing}
          />
        </div>

        <div key={`analysis-breakdown-${analysisRevealKey}`} className="analysis-enter analysis-delay-1">
          <AnimatedSection
            title="Score Breakdown"
            isOpen={isBreakdownOpen}
            onToggle={() => setIsBreakdownOpen((current) => !current)}
          >
            <BreakdownBars breakdown={analysis?.score.breakdown} />
          </AnimatedSection>
        </div>

        <div key={`analysis-drivers-${analysisRevealKey}`} className="analysis-enter analysis-delay-2">
          <AnimatedSection
            title="Top Drivers"
            isOpen={isTopDriversOpen}
            onToggle={() => setIsTopDriversOpen((current) => !current)}
          >
            <ul className="space-y-1 text-sm text-ink">
              {analysis?.score.top_drivers?.length ? (
                analysis.score.top_drivers.map((driver) => {
                  const tone = driverTone(driver);
                  const classes = hazardToneClasses[tone];
                  return (
                    <li key={driver} className={`rounded-lg border px-2 py-1 ${classes.card}`}>
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${classes.chip}`}>
                        {hazardToneLabel[tone]}
                      </span>
                      <p className="mt-1">{driver}</p>
                    </li>
                  );
                })
              ) : (
                <li className="rounded-lg bg-panelSoft/60 px-2 py-1 text-muted">
                  Run analysis to view top drivers.
                </li>
              )}
            </ul>
          </AnimatedSection>
        </div>

        <div key={`analysis-signals-${analysisRevealKey}`} className="analysis-enter analysis-delay-3">
          <AnimatedSection
            title="Signals"
            isOpen={isSignalsOpen}
            onToggle={() => setIsSignalsOpen((current) => !current)}
          >
            <SignalsTable signals={analysis?.signals} />
          </AnimatedSection>
        </div>

        <AnimatedSection title="Nearby sites" defaultOpen={false}>
          {nearbyHazards.length === 0 ? (
            <p className="text-sm text-muted">No nearby sites found.</p>
          ) : (
            <ul className="space-y-2">
              {nearbyHazards.map((hazard, index) => {
                const classes = hazardToneClasses[hazard.tone];
                const key = hazard.item.id ?? `${hazard.category}-${hazard.item.name ?? "item"}-${index}`;
                const stateSuffix = hazard.item.state ? ` (${hazard.item.state})` : "";
                return (
                  <li key={key} className={`interactive-card rounded-xl border px-3 py-2 text-sm ${classes.card}`}>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => onEvidenceSelect(hazard.category, hazard.item, hazard.sourceIndex)}
                        className="flex-1 cursor-pointer text-left transition hover:text-white"
                      >
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${classes.chip}`}>
                          {hazard.categoryLabel}
                        </span>
                        <p className="mt-1">
                          <span className="font-medium text-ink">{hazard.item.name ?? "Unnamed Site"}</span>
                          <span className="text-muted">{stateSuffix}</span>
                          <span className="text-muted"> — {formatMiles(hazard.item.distance_miles)}</span>
                        </p>
                      </button>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          onEvidenceSelect(hazard.category, hazard.item, hazard.sourceIndex);
                        }}
                        aria-label="Show on map"
                        title="Show on map"
                        className="rounded-md border border-border bg-panel px-2 py-1 text-xs text-muted transition hover:bg-panelSoft hover:text-ink"
                      >
                        Map
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </AnimatedSection>
      </div>
    </aside>
  );
}
