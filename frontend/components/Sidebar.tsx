import AnimatedSection from "@/components/AnimatedSection";
import BreakdownBars from "@/components/BreakdownBars";
import ScoreBadge from "@/components/ScoreBadge";
import SignalsTable from "@/components/SignalsTable";
import { formatMiles, formatTimestamp } from "@/lib/format";
import type { AnalyzeResponse, EvidenceCategory, EvidenceItem, LatLon, ReportResponse } from "@/lib/types";
import { useEffect, useState } from "react";

interface SidebarProps {
  selectedPoint: LatLon | null;
  analysis: AnalyzeResponse | null;
  report: ReportResponse | null;
  analysisError: string | null;
  reportError: string | null;
  isAnalyzing: boolean;
  isGeneratingReport: boolean;
  onGenerateReport: () => void;
  isReportFocusMode: boolean;
  onToggleReportFocusMode: () => void;
  lastUpdated: string | null;
  isCached?: boolean;
  backendStatusLabel: string;
  backendHealthy: boolean | null;
  apiBaseUrl: string;
  onEvidenceSelect: (category: EvidenceCategory, item: EvidenceItem, index: number) => void;
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
      {message}
    </div>
  );
}

function confidencePillClass(level: string | undefined): string {
  if (level === "High") {
    return "bg-low/20 text-low border-low/35";
  }
  if (level === "Moderate") {
    return "bg-moderate/20 text-moderate border-moderate/35";
  }
  return "bg-high/20 text-high border-high/35";
}

export default function Sidebar({
  selectedPoint,
  analysis,
  report,
  analysisError,
  reportError,
  isAnalyzing,
  isGeneratingReport,
  onGenerateReport,
  isReportFocusMode,
  onToggleReportFocusMode,
  lastUpdated,
  isCached = false,
  backendStatusLabel,
  backendHealthy,
  apiBaseUrl,
  onEvidenceSelect,
}: SidebarProps) {
  const hasSelection = Boolean(selectedPoint);
  const hasScore = typeof analysis?.score?.total === "number";
  const [isBreakdownOpen, setIsBreakdownOpen] = useState(true);
  const [isTopDriversOpen, setIsTopDriversOpen] = useState(true);
  const [isSignalsOpen, setIsSignalsOpen] = useState(true);
  const [isReportOpen, setIsReportOpen] = useState(Boolean(report));
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

  useEffect(() => {
    setIsReportOpen(Boolean(report));
  }, [report]);

  const hazardToneClasses = {
    landfill: {
      chip: "border-hazardLandfill/45 bg-hazardLandfillSoft/70 text-hazardLandfill",
      card: "border-hazardLandfill/35 bg-hazardLandfillSoft/22",
    },
    military: {
      chip: "border-hazardMilitary/45 bg-hazardMilitarySoft/70 text-hazardMilitary",
      card: "border-hazardMilitary/35 bg-hazardMilitarySoft/22",
    },
    industrial: {
      chip: "border-hazardIndustrial/45 bg-hazardIndustrialSoft/70 text-hazardIndustrial",
      card: "border-hazardIndustrial/35 bg-hazardIndustrialSoft/22",
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
    industrial: "Industrial",
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
      category: "industrial_frs" as const,
      categoryLabel: "Industrial",
      tone: "industrial" as const,
      items: analysis?.evidence.industrial_frs ?? [],
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
    if (normalized.includes("industrial")) {
      return "industrial";
    }
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

  const siteTypeTone = (siteType: string): keyof typeof hazardToneClasses => {
    const normalized = siteType.toLowerCase();
    if (normalized.includes("industrial")) {
      return "industrial";
    }
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
        <header className="space-y-1">

          <h1 className="text-2xl font-bold leading-tight text-ink">
            Exposure Risk Dashboard
          </h1>
        </header>

        {analysisError ? <ErrorBox message={analysisError} /> : null}

        <div key={`analysis-score-${analysisRevealKey}`} className="analysis-enter">
          <ScoreBadge
            score={analysis?.score.total}
            band={analysis?.score.band}
            isLoading={isAnalyzing}
          />
        </div>

        {hasScore ? (
          <>
            <div className="analysis-enter analysis-delay-1">
              <button
                type="button"
                onClick={onGenerateReport}
                disabled={!hasSelection || isAnalyzing || isGeneratingReport}
                className="inline-flex w-full items-center justify-center rounded-xl border border-border bg-panelSoft px-4 py-3 text-sm font-semibold text-ink transition hover:bg-panel disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isGeneratingReport ? "Generating Report..." : "Generate Report"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setIsReportOpen(true);
                  onToggleReportFocusMode();
                }}
                className="mt-2 inline-flex w-full items-center justify-center rounded-xl border border-border/80 bg-panel px-4 py-2 text-xs font-semibold text-muted transition hover:bg-panelSoft hover:text-ink"
              >
                {isReportFocusMode ? "Restore Split View" : "Expand Report View"}
              </button>
            </div>

            {reportError ? <ErrorBox message={reportError} /> : null}

            <AnimatedSection
              title="Report"
              isOpen={isReportOpen}
              onToggle={() => setIsReportOpen((current) => !current)}
            >
              <div className="space-y-3">
              {report ? (
                <div className="space-y-2 report-content">
                  <div className="report-card rounded-xl border border-border bg-panelSoft p-3">
                    <p className="text-sm font-medium text-muted">Summary</p>
                    <p className="mt-1 text-sm text-ink">{report.summary}</p>
                  </div>

                  {report.top_drivers_explained?.length ? (
                    <div className="report-card rounded-xl border border-border bg-panelSoft p-3">
                      <p className="text-sm font-medium text-muted">Top drivers explained</p>
                      <ul className="mt-2 space-y-2">
                        {report.top_drivers_explained.map((driver) => {
                          const tone = driverTone(`${driver.title} ${driver.detail}`);
                          const classes = hazardToneClasses[tone];
                          return (
                          <li key={`${driver.title}-${driver.detail}`} className={`report-card-hover rounded-lg border px-2 py-2 ${classes.card}`}>
                            <p className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${classes.chip}`}>{driver.title}</p>
                            <p className="text-sm text-muted">{driver.detail}</p>
                          </li>
                          );
                        })}
                      </ul>
                    </div>
                  ) : null}

                  {report.site_type_context?.length ? (
                    <div className="report-card rounded-xl border border-border bg-panelSoft p-3">
                      <p className="text-sm font-medium text-muted">Site type context</p>
                      <div className="mt-2 space-y-2">
                        {report.site_type_context.map((row) => {
                          const tone = siteTypeTone(row.site_type);
                          const classes = hazardToneClasses[tone];
                          return (
                          <div key={`${row.site_type}-${row.what_it_can_indicate}`} className={`report-card-hover rounded-lg border px-2 py-2 ${classes.card}`}>
                            <p className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${classes.chip}`}>{row.site_type}</p>
                            <p className="text-sm text-muted">{row.what_it_can_indicate}</p>
                          </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : null}

                  {report.recommended_next_steps?.length ? (
                    <div className="report-card rounded-xl border border-border bg-panelSoft p-3">
                      <p className="text-sm font-medium text-muted">Recommended next steps</p>
                      <ul className="mt-2 space-y-2">
                        {report.recommended_next_steps.map((step) => (
                          <li key={`${step.action}-${step.why}`} className="report-card-hover rounded-lg border border-border/70 bg-panel px-2 py-2">
                            <p className="text-sm font-semibold text-ink">- {step.action}</p>
                            <p className="text-sm text-muted">{step.why}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}

                  <div className="report-card rounded-xl border border-border bg-panelSoft p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-muted">Confidence</p>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${confidencePillClass(
                          report.confidence?.level,
                        )}`}
                      >
                        {report.confidence?.level ?? "Unknown"}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted">{report.confidence?.rationale ?? "-"}</p>
                  </div>

                  {report.limitations?.length ? (
                    <div className="report-card rounded-xl border border-border bg-panelSoft p-3">
                      <p className="text-sm font-medium text-muted">Limitations</p>
                      <ul className="mt-2 space-y-1">
                        {report.limitations.map((item) => (
                          <li key={item} className="text-sm text-muted">
                            - {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-muted">Generate a report for this scored point.</p>
              )}
              </div>
            </AnimatedSection>
          </>
        ) : null}

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
              {analysis?.score.top_drivers?.length
                ? analysis.score.top_drivers.map((driver) => {
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
                : (
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

        <AnimatedSection title="Show nearby potential hazards" defaultOpen={false}>
          {nearbyHazards.length === 0 ? (
            <p className="text-sm text-muted">No nearby potential hazards found.</p>
          ) : (
            <ul className="space-y-2">
              {nearbyHazards.map((hazard, index) => {
                const classes = hazardToneClasses[hazard.tone];
                const key = hazard.item.id ?? `${hazard.category}-${hazard.item.name ?? "item"}-${index}`;
                const stateSuffix = hazard.item.state ? ` (${hazard.item.state})` : "";
                return (
                  <li key={key} className={`report-card-hover rounded-xl border px-3 py-2 text-sm ${classes.card}`}>
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
                          <span className="text-muted"> - {formatMiles(hazard.item.distance_miles)}</span>
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
                        📍
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </AnimatedSection>
      </div>

      <footer className="border-t border-border bg-panelSoft px-5 py-3 text-xs text-muted">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                backendHealthy == null
                  ? "bg-muted/50"
                  : backendHealthy
                    ? "bg-low"
                    : "bg-high"
              }`}
            />
            <span>{backendStatusLabel}</span>
          </div>
          <span>
            Last updated: {formatTimestamp(lastUpdated)}
            {isCached ? " (cached)" : ""}
          </span>
        </div>
      </footer>
    </aside>
  );
}
