"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";

import Sidebar from "@/components/Sidebar";
import {
  ApiError,
  analyzePoint,
  getErrorMessage,
  health,
  isBackendWarmSession,
} from "@/lib/api";
import {
  getGeocodeErrorMessage,
  inferSearchZoom,
  reverseGeocodeUsState,
  searchUsLocations,
} from "@/lib/geocode";
import type {
  ActiveEvidence,
  AnalyzeResponse,
  HeatMode,
  HeatPoint,
  LatLon,
  MapFocusRequest,
  ProximitySite,
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

function formatErrorWithClass(error: unknown): string {
  const message = getErrorMessage(error);
  if (error instanceof ApiError) {
    return `${message} (class: ${error.kind})`;
  }
  return message;
}

function logApiTelemetry(event: string, error: unknown): void {
  const timestamp = new Date().toISOString();
  if (error instanceof ApiError) {
    console.info("api_telemetry", {
      event,
      timestamp,
      kind: error.kind,
      status: error.status ?? null,
      message: error.message,
    });
    return;
  }

  console.info("api_telemetry", {
    event,
    timestamp,
    kind: "unknown",
    status: null,
    message: error instanceof Error ? error.message : String(error),
  });
}

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

export default function HomePage() {
  const [selectedPoint, setSelectedPoint] = useState<LatLon | null>(null);
  const [selectedLocationLabel, setSelectedLocationLabel] = useState<string | null>(null);
  const [selectedStateCode, setSelectedStateCode] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isBackendWarming, setIsBackendWarming] = useState<boolean>(() => !isBackendWarmSession());
  const [backendWarmupWarning, setBackendWarmupWarning] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GeocodeResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  const [mapFocusRequest, setMapFocusRequest] = useState<MapFocusRequest | null>(null);
  const [mapZoomLevel, setMapZoomLevel] = useState(4);

  const [heatMode, setHeatMode] = useState<HeatMode>("combined");
  const [heatPoints, setHeatPoints] = useState<HeatPoint[]>([]);
  const [isHeatLoading, setIsHeatLoading] = useState(false);
  const [heatError, setHeatError] = useState<string | null>(null);
  const [activeEvidence, setActiveEvidence] = useState<ActiveEvidence | null>(null);

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
      setIsBackendWarming(false);
      setBackendWarmupWarning(null);
    } catch (error) {
      if (runId !== analyzeRunId.current) {
        return;
      }
      setAnalysisError(formatErrorWithClass(error));
      logApiTelemetry("analyze_error", error);
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
      setSelectedLocationLabel(null);
      setSelectedStateCode(null);
      setAnalysis(null);
      setAnalysisError(null);
      setActiveEvidence(null);
    },
    [],
  );

  useEffect(() => {
    if (!selectedPoint || selectedStateCode) {
      return;
    }

    const controller = new AbortController();
    const timerId = window.setTimeout(() => {
      void reverseGeocodeUsState(
        selectedPoint.lat,
        selectedPoint.lon,
        controller.signal,
      ).then((stateCode) => {
        if (!controller.signal.aborted) {
          setSelectedStateCode(stateCode);
        }
      }).catch(() => {
        // State context is helpful but should not block point selection.
      });
    }, 700);

    return () => {
      window.clearTimeout(timerId);
      controller.abort();
    };
  }, [selectedPoint, selectedStateCode]);

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

  useEffect(() => {
    let active = true;
    if (isBackendWarmSession()) {
      setIsBackendWarming(false);
      setBackendWarmupWarning(null);
      return () => {
        active = false;
      };
    }

    setIsBackendWarming(true);
    setBackendWarmupWarning(null);

    void health()
      .then(() => {
        if (!active) {
          return;
        }
        setIsBackendWarming(false);
        setBackendWarmupWarning(null);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setIsBackendWarming(false);
        setBackendWarmupWarning(
          "Warm-up check failed. Analyze is still available, but the first request can take up to ~30 seconds and may retry once.",
        );
        logApiTelemetry("warmup_error", error);
      });

    return () => {
      active = false;
    };
  }, []);

  const handleSearchSelect = useCallback(
    (result: GeocodeResult) => {
      const point = { lat: result.lat, lon: result.lon };
      setSearchQuery(result.displayName);
      setSearchResults([]);
      setSearchError(null);
      setIsSearchOpen(false);
      setActiveEvidence(null);

      handleMapSelect(point);
      setSelectedLocationLabel(result.displayName);
      setSelectedStateCode(result.stateCode ?? null);

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

  const handleSiteSelect = useCallback((item: ProximitySite) => {
    setActiveEvidence(item);
  }, []);

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
          cache: "no-store",
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
        setHeatError("Heat layer unavailable. Run python scripts/build_data.py.");
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

  const showSearchDropdown =
    isSearchOpen &&
    (isSearching || searchResults.length > 0 || Boolean(searchError) || searchQuery.trim().length >= 2);

  const handleMapZoomLevelChange = useCallback((zoom: number) => {
    setMapZoomLevel((current) => (current === zoom ? current : zoom));
  }, []);

  const nearestSites: ActiveEvidence[] = analysis
    ? [
        analysis.nearest_by_category.superfund,
        analysis.nearest_by_category.landfill,
      ].filter((site): site is ProximitySite => site !== null)
    : [];

  return (
    <main className="w-full p-3 md:p-4 lg:h-[calc(100vh-5rem)] lg:overflow-hidden">
      <div className="analysis-layout mx-auto grid max-w-[1750px] grid-cols-1 gap-4 lg:h-[min(760px,calc(100vh-7rem))]">
        <section
          className="animate-revealUp flex min-h-0 flex-col gap-3 lg:col-span-1"
        >
          {isBackendWarming ? (
            <div className="rounded-xl border border-border bg-panelSoft px-3 py-2 text-sm text-muted">
              Backend warm-up check in progress. If cold, first analyze may take up to ~30 seconds.
            </div>
          ) : null}
          {backendWarmupWarning ? (
            <div className="rounded-xl border border-border bg-panelSoft px-3 py-2 text-sm text-muted">
              {backendWarmupWarning}
            </div>
          ) : null}
          <div className="relative min-h-0 flex-1">
            <DynamicMap
              selectedPoint={selectedPoint}
              onSelect={handleMapSelect}
              onZoomLevelChange={handleMapZoomLevelChange}
              onAnalyzeClick={handleAnalyzeAgain}
              canAnalyze={Boolean(selectedPoint) && !isAnalyzing}
              isLoading={isAnalyzing}
              heatEnabled={heatMode !== "off"}
              heatMode={heatMode}
              onHeatModeChange={setHeatMode}
              isHeatLoading={isHeatLoading}
              heatError={heatError}
              heatPoints={heatPoints}
              focusRequest={mapFocusRequest}
              activeEvidence={activeEvidence}
              nearestSites={nearestSites}
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

        <section className="min-h-0 lg:col-span-1">
          <Sidebar
            analysis={analysis}
            analysisError={analysisError}
            isAnalyzing={isAnalyzing}
            selectedPoint={selectedPoint}
            selectedLocationLabel={selectedLocationLabel}
            selectedStateCode={selectedStateCode}
            onSiteSelect={handleSiteSelect}
          />
        </section>
      </div>
    </main>
  );
}
