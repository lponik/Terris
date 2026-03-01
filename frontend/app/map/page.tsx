"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import Sidebar from "@/components/Sidebar";
import { analyzePoint, generateReport, getApiBaseUrl, getErrorMessage, health } from "@/lib/api";
import { getGeocodeErrorMessage, inferSearchZoom, searchUsLocations } from "@/lib/geocode";
import type {
  ActiveEvidence,
  AnalyzeResponse,
  EvidenceCategory,
  EvidenceItem,
  HeatMode,
  HeatPoint,
  HealthResponse,
  LatLon,
  MapFocusRequest,
  ReportResponse,
} from "@/lib/types";
import type { GeocodeResult } from "@/lib/geocode";

const DynamicMap = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="h-full min-h-[360px] animate-pulse rounded-3xl border border-border bg-panelSoft" />
  ),
});

type HeatDataMode = Exclude<HeatMode, "off">;

const MAX_COMBINED_HEAT_POINTS = 45_000;
const ANALYZE_FOCUS_ZOOM = 11;

function normalizeHeatPoints(payload: unknown): HeatPoint[] {
  if (!Array.isArray(payload)) {
    return [];
  }

  const points: HeatPoint[] = [];
  for (const row of payload) {
    if (!Array.isArray(row) || row.length < 2) {
      continue;
    }

    const lat = Number(row[0]);
    const lon = Number(row[1]);
    const weight = row.length >= 3 ? Number(row[2]) : undefined;

    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      continue;
    }

    if (weight != null && !Number.isNaN(weight)) {
      points.push([lat, lon, weight]);
    } else {
      points.push([lat, lon]);
    }
  }

  return points;
}

function downsampleHeatPoints(points: HeatPoint[], maxPoints: number): HeatPoint[] {
  if (points.length <= maxPoints) {
    return points;
  }

  // Keep rendering responsive when combined mode contains very large national datasets.
  const step = Math.ceil(points.length / maxPoints);
  return points.filter((_, index) => index % step === 0);
}

function parseNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function mapEvidenceToActive(
  item: EvidenceItem,
  category: EvidenceCategory,
  index: number,
): ActiveEvidence | null {
  const record = item as Record<string, unknown>;

  const lat =
    parseNumber(record.lat) ??
    parseNumber(record.latitude) ??
    parseNumber(record.lat_deg);
  const lon =
    parseNumber(record.lon) ??
    parseNumber(record.longitude) ??
    parseNumber(record.lng) ??
    parseNumber(record.lon_deg);

  if (lat == null || lon == null) {
    return null;
  }

  const id =
    (typeof record.id === "string" && record.id) ||
    `${category}-${index}-${lat.toFixed(4)}-${lon.toFixed(4)}`;

  const name =
    (typeof record.name === "string" && record.name) ||
    (typeof record.site_name === "string" && record.site_name) ||
    (typeof record.facility_name === "string" && record.facility_name) ||
    (typeof record.title === "string" && record.title) ||
    undefined;

  const distance_miles =
    parseNumber(record.distance_miles) ??
    parseNumber(record.distance) ??
    parseNumber(record.distanceMi) ??
    undefined;

  const source =
    (typeof record.source === "string" && record.source) ||
    (typeof record.program === "string" && record.program) ||
    (typeof record.dataset === "string" && record.dataset) ||
    undefined;

  const state =
    (typeof record.state === "string" && record.state) ||
    (typeof record.state_code === "string" && record.state_code) ||
    (typeof record.st === "string" && record.st) ||
    undefined;

  return {
    id,
    lat,
    lon,
    name,
    distance_miles,
    source,
    state,
    category,
  };
}

export default function HomePage() {
  const [selectedPoint, setSelectedPoint] = useState<LatLon | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const [healthState, setHealthState] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GeocodeResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const [mapFocusRequest, setMapFocusRequest] = useState<MapFocusRequest | null>(null);
  const [mapZoomLevel, setMapZoomLevel] = useState(4);

  const [heatMode, setHeatMode] = useState<HeatMode>("off");
  const [heatPoints, setHeatPoints] = useState<HeatPoint[]>([]);
  const [isHeatLoading, setIsHeatLoading] = useState(false);
  const [heatError, setHeatError] = useState<string | null>(null);
  const [activeEvidence, setActiveEvidence] = useState<ActiveEvidence | null>(null);
  const [isReportFocusMode, setIsReportFocusMode] = useState(false);

  const analyzeRunId = useRef(0);
  const searchRunId = useRef(0);
  const heatCacheRef = useRef<Partial<Record<HeatDataMode, HeatPoint[]>>>({});

  const runAnalysis = useCallback(async (point: LatLon) => {
    const runId = ++analyzeRunId.current;
    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const response = await analyzePoint(point.lat, point.lon);
      if (runId !== analyzeRunId.current) {
        return;
      }

      setAnalysis(response);
      setLastUpdated(response.meta?.timestamp_utc ?? new Date().toISOString());
    } catch (error) {
      if (runId !== analyzeRunId.current) {
        return;
      }
      setAnalysisError(getErrorMessage(error));
    } finally {
      if (runId === analyzeRunId.current) {
        setIsAnalyzing(false);
      }
    }
  }, []);

  const handleMapSelect = useCallback(
    (point: LatLon) => {
      // Invalidate any in-flight analysis for older selections.
      analyzeRunId.current += 1;
      setIsAnalyzing(false);
      setMapFocusRequest(null);
      setSelectedPoint(point);
      setAnalysis(null);
      setAnalysisError(null);
      setLastUpdated(null);
      setReport(null);
      setReportError(null);
      setIsReportFocusMode(false);
      setActiveEvidence(null);
    },
    [],
  );

  const handleAnalyzeAgain = useCallback(() => {
    const point = selectedPoint;
    if (!point) {
      return;
    }

    setActiveEvidence(null);
    if (mapZoomLevel < ANALYZE_FOCUS_ZOOM) {
      setMapFocusRequest({
        id: Date.now(),
        lat: point.lat,
        lon: point.lon,
        zoom: ANALYZE_FOCUS_ZOOM,
      });
    }
    void runAnalysis(point);
  }, [mapZoomLevel, runAnalysis, selectedPoint]);

  const handleGenerateReport = useCallback(async () => {
    const point = selectedPoint ?? analysis?.location ?? null;
    if (!point) {
      return;
    }

    setIsGeneratingReport(true);
    setReportError(null);

    try {
      const response = await generateReport({
        lat: point.lat,
        lon: point.lon,
      });
      setReport(response);
    } catch (error) {
      setReportError(getErrorMessage(error));
    } finally {
      setIsGeneratingReport(false);
    }
  }, [analysis, selectedPoint]);

  const handleSearchSelect = useCallback(
    (result: GeocodeResult) => {
      const point = { lat: result.lat, lon: result.lon };
      setSearchQuery(result.displayName);
      setSearchResults([]);
      setSearchError(null);
      setIsSearchOpen(false);
      setActiveEvidence(null);

      handleMapSelect(point);

      setMapFocusRequest({
        id: Date.now(),
        lat: point.lat,
        lon: point.lon,
        zoom: inferSearchZoom(result),
      });
    },
    [handleMapSelect],
  );

  const handleSearchEnter = useCallback(async () => {
    const query = searchQuery.trim();
    if (query.length < 2) {
      return;
    }

    if (searchResults[0]) {
      handleSearchSelect(searchResults[0]);
      return;
    }

    const runId = ++searchRunId.current;
    setIsSearching(true);
    setSearchError(null);

    try {
      const results = await searchUsLocations(query);
      if (runId !== searchRunId.current) {
        return;
      }

      setSearchResults(results);

      if (results[0]) {
        handleSearchSelect(results[0]);
        return;
      }

      setSearchError("No matches found.");
      setIsSearchOpen(true);
    } catch (error) {
      if (runId !== searchRunId.current) {
        return;
      }
      const message = getGeocodeErrorMessage(error);
      setSearchError(message || "Search unavailable.");
      setSearchResults([]);
      setIsSearchOpen(true);
    } finally {
      if (runId === searchRunId.current) {
        setIsSearching(false);
      }
    }
  }, [handleSearchSelect, searchQuery, searchResults]);

  const handleEvidenceSelect = useCallback(
    (category: EvidenceCategory, item: EvidenceItem, index: number) => {
      const mapped = mapEvidenceToActive(item, category, index);
      if (!mapped) {
        return;
      }
      setActiveEvidence(mapped);
      setSelectedPoint({ lat: mapped.lat, lon: mapped.lon });
    },
    [],
  );

  useEffect(() => {
    const query = searchQuery.trim();
    if (query.length < 2) {
      setSearchResults([]);
      setSearchError(null);
      setIsSearching(false);
      return;
    }

    const controller = new AbortController();
    const runId = ++searchRunId.current;

    const timerId = window.setTimeout(async () => {
      setIsSearching(true);
      setSearchError(null);

      try {
        const results = await searchUsLocations(query, controller.signal);
        if (runId !== searchRunId.current) {
          return;
        }

        setSearchResults(results);
        setIsSearchOpen(true);
      } catch (error) {
        if (controller.signal.aborted || runId !== searchRunId.current) {
          return;
        }

        const message = getGeocodeErrorMessage(error);
        setSearchError(message || "Search unavailable.");
        setSearchResults([]);
      } finally {
        if (!controller.signal.aborted && runId === searchRunId.current) {
          setIsSearching(false);
        }
      }
    }, 400);

    return () => {
      window.clearTimeout(timerId);
      controller.abort();
    };
  }, [searchQuery]);

  useEffect(() => {
    if (heatMode === "off") {
      setHeatPoints([]);
      setHeatError(null);
      setIsHeatLoading(false);
      return;
    }

    const mode = heatMode as HeatDataMode;
    const cached = heatCacheRef.current[mode];

    if (cached) {
      setHeatPoints(cached);
      setHeatError(null);
      setIsHeatLoading(false);
      return;
    }

    const controller = new AbortController();
    let active = true;

    setIsHeatLoading(true);
    setHeatError(null);
    setHeatPoints([]);

    void (async () => {
      try {
        const response = await fetch(`/heat/${mode}.json`, {
          method: "GET",
          signal: controller.signal,
          cache: "force-cache",
        });

        if (!response.ok) {
          throw new Error(`Heat layer request failed (${response.status}).`);
        }

        const payload = await response.json();
        const normalized = normalizeHeatPoints(payload);
        const points =
          mode === "combined"
            ? downsampleHeatPoints(normalized, MAX_COMBINED_HEAT_POINTS)
            : normalized;

        heatCacheRef.current[mode] = points;

        if (!active) {
          return;
        }

        setHeatPoints(points);
      } catch {
        if (!active || controller.signal.aborted) {
          return;
        }

        setHeatPoints([]);
        setHeatError("Heat layer unavailable. Run python scripts/export_heat_points.py.");
      } finally {
        if (active && !controller.signal.aborted) {
          setIsHeatLoading(false);
        }
      }
    })();

    return () => {
      active = false;
      controller.abort();
    };
  }, [heatMode]);

  useEffect(() => {
    let active = true;

    const pollHealth = async () => {
      try {
        const response = await health();
        if (!active) {
          return;
        }
        setHealthState(response);
        setHealthError(null);
      } catch (error) {
        if (!active) {
          return;
        }
        setHealthError(getErrorMessage(error));
      }
    };

    void pollHealth();
    const intervalId = setInterval(() => {
      void pollHealth();
    }, 30_000);

    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, []);

  const backendHealthy = useMemo(() => {
    if (!healthState && !healthError) {
      return null;
    }

    if (healthError) {
      return false;
    }

    return Boolean(healthState?.status === "ok" && healthState.dataset_loaded);
  }, [healthState, healthError]);

  const backendStatusLabel = useMemo(() => {
    if (healthError) {
      return `Backend unreachable (${healthError})`;
    }
    if (!healthState) {
      return "Checking backend health...";
    }
    if (!healthState.dataset_loaded) {
      return "Backend online, dataset not loaded";
    }
    return "Backend healthy";
  }, [healthState, healthError]);

  const showSearchDropdown =
    isSearchOpen &&
    (isSearching || searchResults.length > 0 || Boolean(searchError) || searchQuery.trim().length >= 2);

  const handleMapZoomLevelChange = useCallback((zoom: number) => {
    setMapZoomLevel((current) => (current === zoom ? current : zoom));
  }, []);

  return (
    <main className="w-full p-3 md:p-4 lg:h-[calc(100vh-3.5rem)] lg:overflow-hidden">
      <div
        className={`report-layout mx-auto grid max-w-[1750px] grid-cols-1 gap-4 lg:h-[min(760px,calc(100vh-6.5rem))] ${
          isReportFocusMode ? "report-layout--focus" : ""
        }`}
      >
        <section
          className="report-map-shell animate-revealUp flex min-h-0 flex-col gap-3 lg:col-span-1"
        >
          <div className="relative min-h-0 flex-1">
            <DynamicMap
              selectedPoint={selectedPoint}
              onSelect={handleMapSelect}
              onZoomLevelChange={handleMapZoomLevelChange}
              onAnalyzeClick={handleAnalyzeAgain}
              canAnalyze={Boolean(selectedPoint) && !isAnalyzing && !isGeneratingReport}
              isLoading={isAnalyzing}
              heatEnabled={heatMode !== "off"}
              heatMode={heatMode}
              onHeatModeChange={setHeatMode}
              isHeatLoading={isHeatLoading}
              heatError={heatError}
              heatPoints={heatPoints}
              focusRequest={mapFocusRequest}
              activeEvidence={activeEvidence}
              onEvidencePopupClose={() => setActiveEvidence(null)}
            />

            <div className="pointer-events-none absolute left-1/2 top-4 z-[700] -translate-x-1/2">
              <div
                data-open={showSearchDropdown || isSearchOpen}
                className="map-search-collapsible map-search-shell pointer-events-auto rounded-xl border border-border p-2 backdrop-blur-sm"
              >
                <label
                  htmlFor="location-search"
                  className="block text-center text-sm font-medium text-ink"
                >
                  Search U.S. Location
                </label>

                <div className="map-search-body">
                  <input
                    id="location-search"
                    type="text"
                    value={searchQuery}
                    onChange={(event) => {
                      setSearchQuery(event.target.value);
                      setIsSearchOpen(true);
                    }}
                    onFocus={() => setIsSearchOpen(true)}
                    onBlur={() => {
                      window.setTimeout(() => {
                        setIsSearchOpen(false);
                      }, 120);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void handleSearchEnter();
                      }
                    }}
                    placeholder="City, State, ZIP, or address"
                    className="map-search-input w-full rounded-lg border border-border px-3 py-2 text-sm text-ink outline-none transition placeholder:text-muted focus:border-accent focus:ring-2 focus:ring-accent/20"
                  />

                  {showSearchDropdown ? (
                    <div className="map-search-dropdown mt-2 max-h-60 overflow-auto rounded-lg border border-border shadow-panel">
                      {isSearching ? <p className="px-3 py-2 text-sm text-muted">Searching...</p> : null}

                      {!isSearching && searchError ? (
                        <p className="px-3 py-2 text-sm text-danger">{searchError}</p>
                      ) : null}

                      {!isSearching && !searchError && searchResults.length === 0 ? (
                        <p className="px-3 py-2 text-sm text-muted">No matches found.</p>
                      ) : null}

                      {!isSearching && !searchError
                        ? searchResults.map((result) => (
                            <button
                              key={result.placeId}
                              type="button"
                              onMouseDown={(event) => {
                                event.preventDefault();
                              }}
                              onClick={() => handleSearchSelect(result)}
                              className="map-search-option block w-full border-b border-border px-3 py-2 text-left text-sm text-ink transition last:border-b-0"
                            >
                              {result.displayName}
                            </button>
                          ))
                        : null}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="report-sidebar-shell animate-revealUp stagger-1 min-h-0 lg:col-span-1">
          <Sidebar
            selectedPoint={selectedPoint}
            analysis={analysis}
            report={report}
            analysisError={analysisError}
            reportError={reportError}
            isAnalyzing={isAnalyzing}
            isGeneratingReport={isGeneratingReport}
            onGenerateReport={handleGenerateReport}
            isReportFocusMode={isReportFocusMode}
            onToggleReportFocusMode={() => setIsReportFocusMode((current) => !current)}
            lastUpdated={lastUpdated}
            isCached={Boolean(analysis?.meta?.cached)}
            backendStatusLabel={backendStatusLabel}
            backendHealthy={backendHealthy}
            apiBaseUrl={getApiBaseUrl()}
            onEvidenceSelect={handleEvidenceSelect}
          />
        </section>
      </div>
    </main>
  );
}
