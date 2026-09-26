"use client";

import { CircleMarker, MapContainer, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { useCallback, useEffect, useRef, useState } from "react";

import HeatLayer from "@/components/HeatLayer";
import { distanceTone, formatSiteSource } from "@/lib/format";
import type { ActiveEvidence, HeatMode, HeatPoint, LatLon, MapFocusRequest } from "@/lib/types";

interface MapViewProps {
  selectedPoint: LatLon | null;
  onSelect: (point: LatLon) => void;
  onZoomLevelChange?: (zoom: number) => void;
  onAnalyzeClick?: () => void;
  canAnalyze?: boolean;
  isLoading?: boolean;
  heatPoints?: HeatPoint[];
  heatEnabled?: boolean;
  heatMode?: HeatMode;
  onHeatModeChange?: (mode: HeatMode) => void;
  isHeatLoading?: boolean;
  heatError?: string | null;
  focusRequest?: MapFocusRequest | null;
  activeEvidence?: ActiveEvidence | null;
  nearestSites?: ActiveEvidence[];
  onEvidencePopupClose?: () => void;
}

const US_CENTER: [number, number] = [39.5, -98.35];
const US_ZOOM = 4;
const BASEMAP_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const US_BOUNDS = L.latLngBounds(
  [24.396308, -125.0],
  [49.384358, -66.93457],
);

const heatModes: Array<{ value: HeatMode; label: string }> = [
  { value: "off", label: "Off" },
  { value: "landfill", label: "Landfills" },
  { value: "superfund", label: "Superfund" },
  { value: "combined", label: "Combined" },
];

function MapBehavior({
  onSelect,
  focusRequest,
  onZoomChange,
}: {
  onSelect: (point: LatLon) => void;
  focusRequest: MapFocusRequest | null;
  onZoomChange: (zoom: number) => void;
}) {
  const map = useMapEvents({
    click(event) {
      onSelect({ lat: event.latlng.lat, lon: event.latlng.lng });
    },
    zoomend() {
      onZoomChange(map.getZoom());
    },
  });

  useEffect(() => {
    onZoomChange(map.getZoom());
  }, [map, onZoomChange]);

  useEffect(() => {
    if (!focusRequest) {
      return;
    }

    const target = L.latLng(focusRequest.lat, focusRequest.lon);
    const currentCenter = map.getCenter();
    const sameCenter = currentCenter.distanceTo(target) < 40;
    const sameZoom = Math.abs(map.getZoom() - focusRequest.zoom) < 0.1;

    if (sameCenter && sameZoom) {
      const bumpZoom = Math.min(focusRequest.zoom + 1, map.getMaxZoom());
      map.flyTo(target, bumpZoom, {
        animate: true,
        duration: 0.45,
        easeLinearity: 0.2,
      });

      const timer = window.setTimeout(() => {
        map.flyTo(target, focusRequest.zoom, {
          animate: true,
          duration: 0.6,
          easeLinearity: 0.22,
        });
      }, 280);

      return () => {
        window.clearTimeout(timer);
      };
    }

    map.flyTo(target, focusRequest.zoom, {
      animate: true,
      duration: 1.0,
      easeLinearity: 0.22,
    });
  }, [focusRequest, map]);

  return null;
}

function formatEvidenceDistance(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "unknown";
  }
  return `${value.toFixed(2)} mi`;
}

function formatEvidenceCategory(value?: string): string {
  if (!value) {
    return "unknown";
  }
  if (value === "landfill") {
    return "Landfill";
  }
  if (value === "superfund") {
    return "Superfund";
  }
  return value;
}

function evidenceColor(category?: string): string {
  return category === "superfund" ? "#b4c95e" : "#3bcf9f";
}

function SelectedPointPin({ point }: { point: LatLon }) {
  const map = useMap();

  useEffect(() => {
    const markerPane = map.getPane("markerPane");
    if (!markerPane) {
      return;
    }

    const pin = L.DomUtil.create("div", "terris-location-pin", markerPane);
    pin.setAttribute("aria-hidden", "true");
    pin.innerHTML = `
      <svg viewBox="0 0 32 42" focusable="false" role="presentation">
        <path d="M16 1.5C8.27 1.5 2 7.77 2 15.5c0 10.5 14 25 14 25s14-14.5 14-25C30 7.77 23.73 1.5 16 1.5Z" />
        <circle cx="16" cy="15.5" r="5.25" />
      </svg>
    `;

    const updatePosition = () => {
      L.DomUtil.setPosition(pin, map.latLngToLayerPoint([point.lat, point.lon]));
    };

    updatePosition();
    map.on("move zoom viewreset", updatePosition);

    return () => {
      map.off("move zoom viewreset", updatePosition);
      pin.remove();
    };
  }, [map, point.lat, point.lon]);

  return null;
}

function SitePopupContent({ site }: { site: ActiveEvidence }) {
  return (
    <div className="space-y-1 text-sm">
      <p className={`font-semibold ${distanceTone(site.distance_miles)}`}>{site.name}</p>
      <p className="text-muted">Category: {formatEvidenceCategory(site.category)}</p>
      <p className={distanceTone(site.distance_miles)}>Distance: {formatEvidenceDistance(site.distance_miles)}</p>
      <p className="text-muted">Source: {formatSiteSource(site.source)}</p>
      <p className="text-muted">State: {site.state}</p>
    </div>
  );
}

function EvidencePopupMarker({
  activeEvidence,
  onEvidencePopupClose,
}: {
  activeEvidence: ActiveEvidence;
  onEvidencePopupClose?: () => void;
}) {
  const map = useMap();
  const markerRef = useRef<L.CircleMarker | null>(null);

  useEffect(() => {
    map.stop();
    map.setView([activeEvidence.lat, activeEvidence.lon], 12, { animate: false });

    const frame = window.requestAnimationFrame(() => {
      markerRef.current?.openPopup();
    });

    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [activeEvidence, map]);

  return (
    <CircleMarker
      ref={markerRef}
      center={[activeEvidence.lat, activeEvidence.lon]}
      radius={9}
      pathOptions={{
        color: "#e5f2e9",
        fillColor: evidenceColor(activeEvidence.category),
        fillOpacity: 1,
        weight: 3,
      }}
      eventHandlers={{
        popupclose: () => {
          onEvidencePopupClose?.();
        },
      }}
    >
      <Popup>
        <SitePopupContent site={activeEvidence} />
      </Popup>
    </CircleMarker>
  );
}

export default function MapView({
  selectedPoint,
  onSelect,
  onZoomLevelChange,
  onAnalyzeClick,
  canAnalyze = false,
  isLoading = false,
  heatPoints = [],
  heatEnabled = false,
  heatMode = "off",
  onHeatModeChange,
  isHeatLoading = false,
  heatError = null,
  focusRequest = null,
  activeEvidence = null,
  nearestSites = [],
  onEvidencePopupClose,
}: MapViewProps) {
  const [zoomLevel, setZoomLevel] = useState(US_ZOOM);
  const activeHeatLabel = heatModes.find((mode) => mode.value === heatMode)?.label ?? "Off";
  const showHeatLayer = heatEnabled && heatMode !== "off";

  const handleZoomChange = useCallback((zoom: number) => {
    onZoomLevelChange?.(zoom);
    setZoomLevel((current) => (current === zoom ? current : zoom));
  }, [onZoomLevelChange]);

  const handleHeatModeSelect = useCallback(
    (mode: HeatMode) => {
      if (mode !== heatMode) {
        onHeatModeChange?.(mode);
      }
    },
    [heatMode, onHeatModeChange],
  );

  return (
    <div className="relative h-full min-h-[360px] overflow-hidden rounded-3xl border border-border bg-panel shadow-panel">
      <MapContainer
        center={US_CENTER}
        zoom={US_ZOOM}
        minZoom={4}
        maxZoom={16}
        maxBounds={US_BOUNDS}
        maxBoundsViscosity={1.0}
        className="h-full w-full"
        zoomControl={true}
        attributionControl={false}
      >
        <TileLayer
          url={BASEMAP_URL}
          className="basemap-tiles--osm"
          noWrap={true}
        />
        <MapBehavior onSelect={onSelect} focusRequest={focusRequest} onZoomChange={handleZoomChange} />
        {showHeatLayer ? <HeatLayer enabled={true} points={heatPoints} mode={heatMode} zoomLevel={zoomLevel} /> : null}
        {nearestSites.map((site) => {
          const color = evidenceColor(site.category);
          return (
            <CircleMarker
              key={`nearest-${site.category}-${site.id}`}
              center={[site.lat, site.lon]}
              radius={7}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.78, weight: 2 }}
            >
              <Popup>
                <SitePopupContent site={site} />
              </Popup>
            </CircleMarker>
          );
        })}
        {activeEvidence ? (
          <EvidencePopupMarker
            activeEvidence={activeEvidence}
            onEvidencePopupClose={onEvidencePopupClose}
          />
        ) : null}
        {selectedPoint ? <SelectedPointPin point={selectedPoint} /> : null}
      </MapContainer>

      <a
        href="https://www.openstreetmap.org/copyright"
        target="_blank"
        rel="noreferrer"
        className="absolute bottom-3 left-3 z-[650] rounded bg-panel/70 px-1.5 py-0.1 text-[7px] text-muted/80 backdrop-blur-sm transition hover:text-ink"
      >
        © OpenStreetMap contributors
      </a>

      <div className="pointer-events-none absolute left-4 top-24 rounded-xl border border-border bg-panel/55 px-3 py-2 text-xs font-medium text-muted backdrop-blur-sm">
        Click anywhere in the U.S. to select a point.
      </div>

      <div className="pointer-events-none absolute bottom-4 right-4 z-[650]">
        <div className="group pointer-events-auto w-[154px] rounded-xl border border-border bg-panel/55 p-2 backdrop-blur-sm transition-all duration-300 hover:w-[276px]">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-ink">Heat layer</span>
            <span className="rounded-md border border-border bg-panelSoft/70 px-1.5 py-0.5 text-xs font-medium text-muted">
              {activeHeatLabel}
            </span>
          </div>
          <div className="mt-2 hidden grid-cols-2 gap-1 group-hover:grid">
            {heatModes.map((mode) => (
              <button
                key={mode.value}
                type="button"
                onClick={() => handleHeatModeSelect(mode.value)}
                className={`rounded-md border px-1.5 py-1 text-xs font-semibold transition ${
                  heatMode === mode.value
                    ? "border-accent bg-accent text-white"
                    : "border-border bg-panelSoft text-ink hover:bg-panelSoft/70"
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
          {zoomLevel <= 6 && heatMode !== "off" ? (
            <p className="mt-2 hidden text-xs text-muted group-hover:block">National overview density</p>
          ) : null}
          {isHeatLoading ? (
            <p className="mt-2 hidden text-xs text-muted group-hover:block">Loading heat layer...</p>
          ) : null}
          {heatError ? (
            <p className="mt-2 hidden text-xs text-danger group-hover:block">{heatError}</p>
          ) : null}
        </div>
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-4 z-[660] flex justify-center">
        <button
          type="button"
          onClick={onAnalyzeClick}
          disabled={!canAnalyze || isLoading}
          className="pointer-events-auto inline-flex min-w-[180px] items-center justify-center rounded-md border border-border bg-panel/55 px-7 py-3 text-sm font-semibold text-ink backdrop-blur-sm transition hover:bg-panel/70 disabled:cursor-not-allowed disabled:opacity-55"
        >
          {isLoading ? "Calculating distances..." : "Analyze proximity"}
        </button>
      </div>

      {isLoading ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-12 flex items-center justify-center bg-gradient-to-t from-panel/80 via-panel/55 to-transparent py-4">
          <div className="flex items-center gap-2 rounded-full border border-border bg-panel px-4 py-1.5 text-sm text-ink shadow-sm">
            <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
            Measuring mapped-site distances...
          </div>
        </div>
      ) : null}
    </div>
  );
}
