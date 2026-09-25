import { distanceTone, formatMiles, formatSiteSource } from "@/lib/format";
import type { AnalyzeResponse, LatLon, ProximitySite, SiteCategory } from "@/lib/types";

interface SidebarProps {
  analysis: AnalyzeResponse | null;
  analysisError: string | null;
  isAnalyzing: boolean;
  selectedPoint: LatLon | null;
  selectedLocationLabel: string | null;
  selectedStateCode: string | null;
  onSiteSelect: (item: ProximitySite, index: number) => void;
}

const categoryDetails: Record<
  SiteCategory,
  { label: string; heading: string; tone: string; dot: string }
> = {
  superfund: {
    label: "Superfund",
    heading: "Nearest mapped Superfund site",
    tone: "text-hazardSuperfund",
    dot: "bg-hazardSuperfund",
  },
  landfill: {
    label: "Landfill",
    heading: "Nearest landfill",
    tone: "text-hazardLandfill",
    dot: "bg-hazardLandfill",
  },
};

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
      {message}
    </div>
  );
}

function SiteSummary({
  site,
  onSelect,
}: {
  site: ProximitySite | null;
  onSelect: () => void;
}) {
  if (!site) {
    return <p className="py-3 text-sm text-muted">No mapped site is available.</p>;
  }

  const details = categoryDetails[site.category];
  return (
    <button
      type="button"
      onClick={onSelect}
      className="group w-full py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
    >
      <div className="flex items-center justify-between gap-4">
        <span className={`inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] ${details.tone}`}>
          <span className={`h-2 w-2 rounded-full ${details.dot}`} />
          {details.label}
        </span>
        <span className={`font-mono text-sm font-semibold tabular-nums ${distanceTone(site.distance_miles)}`}>
          {formatMiles(site.distance_miles)}
        </span>
      </div>
      <p className="mt-1 text-xs text-muted">{details.heading}</p>
      <p className={`mt-1 truncate text-base font-semibold transition group-hover:text-white ${distanceTone(site.distance_miles)}`}>
        {site.name}
      </p>
      <p className="mt-0.5 text-xs text-muted">{formatSiteSource(site.source)}</p>
    </button>
  );
}

export default function Sidebar({
  analysis,
  analysisError,
  isAnalyzing,
  selectedPoint,
  selectedLocationLabel,
  selectedStateCode,
  onSiteSelect,
}: SidebarProps) {
  const nearest = analysis?.nearest_mapped_site ?? null;

  return (
    <aside className="flex h-full min-h-[320px] flex-col overflow-hidden rounded-3xl border border-border bg-panel shadow-panel">
      <div className="flex-1 overflow-y-auto px-5 py-5 md:px-6">
        <header>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent">Analysis</p>
          <h1 className="mt-1 text-2xl font-bold leading-tight text-ink">Environmental Proximity</h1>
          <p className="mt-1 text-sm leading-relaxed text-muted">
            Distance to mapped Superfund sites and landfills.
          </p>
        </header>

        {selectedPoint ? (
          <div className="mt-4 border-t border-border/80 pt-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">Selected location</p>
            {selectedLocationLabel ? (
              <p className="mt-1 line-clamp-2 text-sm text-ink">{selectedLocationLabel}</p>
            ) : null}
            <p className="mt-1 font-mono text-xs tabular-nums text-muted">
              {selectedStateCode ? `${selectedStateCode} · ` : ""}
              {selectedPoint.lat.toFixed(4)}, {selectedPoint.lon.toFixed(4)}
            </p>
          </div>
        ) : null}

        {analysisError ? <div className="mt-4"><ErrorBox message={analysisError} /></div> : null}

        {isAnalyzing ? (
          <div className="mt-6 space-y-3" aria-live="polite">
            <div className="h-4 w-44 animate-pulse rounded bg-border" />
            <div className="h-16 w-32 animate-pulse rounded bg-border" />
            <p className="text-sm text-muted">Calculating mapped-site distances...</p>
          </div>
        ) : null}

        {!isAnalyzing && !analysis ? (
          <div className="mt-6 border-t border-border pt-5">
            <p className="text-sm leading-relaxed text-muted">
              Select a location on the map, then analyze it to see nearby environmental sites.
            </p>
          </div>
        ) : null}

        {!isAnalyzing && analysis ? (
          <div key={analysis.meta.timestamp_utc} className="analysis-enter mt-6">
            <section aria-labelledby="nearest-mapped-site">
              <p id="nearest-mapped-site" className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
                Nearest mapped environmental site
              </p>
              {nearest ? (
                <button
                  type="button"
                  onClick={() => onSiteSelect(nearest, 0)}
                  className="mt-2 block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
                >
                  <span className={`font-mono text-5xl font-bold leading-none tabular-nums ${distanceTone(nearest.distance_miles)}`}>
                    {nearest.distance_miles.toFixed(2)}
                  </span>
                  <span className={`ml-2 text-base font-semibold ${distanceTone(nearest.distance_miles)}`}>mi away</span>
                  <span className={`mt-2 block truncate text-sm ${distanceTone(nearest.distance_miles)}`}>
                    {categoryDetails[nearest.category].label} · {nearest.name}
                  </span>
                </button>
              ) : (
                <p className="mt-2 text-sm text-muted">No mapped sites are available.</p>
              )}
            </section>

            <section className="mt-6 divide-y divide-border border-y border-border" aria-label="Nearest site by category">
              <SiteSummary
                site={analysis.nearest_by_category.superfund}
                onSelect={() => {
                  const site = analysis.nearest_by_category.superfund;
                  if (site) onSiteSelect(site, 0);
                }}
              />
              <SiteSummary
                site={analysis.nearest_by_category.landfill}
                onSelect={() => {
                  const site = analysis.nearest_by_category.landfill;
                  if (site) onSiteSelect(site, 0);
                }}
              />
            </section>

            <section className="mt-6" aria-labelledby="nearby-site-list">
              <div className="flex items-baseline justify-between gap-3">
                <h2 id="nearby-site-list" className="text-sm font-semibold text-ink">Nearby Sites</h2>
                <span className="text-xs text-muted">Within {analysis.meta.nearby_radius_miles.toFixed(0)} mi</span>
              </div>
              {analysis.nearby_sites.length ? (
                <ol className="mt-2 divide-y divide-border/70 border-y border-border/70">
                  {analysis.nearby_sites.map((site, index) => {
                    const details = categoryDetails[site.category];
                    return (
                      <li key={site.id}>
                        <button
                          type="button"
                          onClick={() => onSiteSelect(site, index)}
                          className="grid w-full grid-cols-[4.25rem_5.25rem_minmax(0,1fr)] items-center gap-2 py-2.5 text-left transition hover:bg-panelSoft/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
                        >
                          <span className={`font-mono text-xs font-semibold tabular-nums ${distanceTone(site.distance_miles)}`}>
                            {site.distance_miles.toFixed(2)} mi
                          </span>
                          <span className={`text-[10px] font-bold uppercase tracking-[0.1em] ${details.tone}`}>
                            {details.label}
                          </span>
                          <span className={`truncate text-sm ${distanceTone(site.distance_miles)}`}>{site.name}</span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <p className="mt-2 py-3 text-sm text-muted">
                  No mapped Superfund sites or landfills are within 5 miles.
                </p>
              )}
            </section>

            <p className="mt-6 border-t border-border pt-4 text-xs leading-relaxed text-muted">
              Distances represent proximity to mapped environmental sites and do not estimate personal exposure or health risk.
            </p>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
