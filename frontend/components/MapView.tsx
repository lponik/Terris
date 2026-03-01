"use client";

import { MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { useCallback, useEffect, useRef, useState } from "react";

import HeatLayer from "@/components/HeatLayer";
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
  onEvidencePopupClose?: () => void;
}

const US_CENTER: [number, number] = [39.5, -98.35];
const US_ZOOM = 4;
const MIN_HEAT_ZOOM = 7;
const US_BOUNDS = L.latLngBounds(
  [24.396308, -125.0],
  [49.384358, -66.93457],
);

const selectedPointIcon = L.icon({
  iconRetinaUrl: markerIcon2x.src,
  iconUrl: markerIcon.src,
  shadowUrl: markerShadow.src,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const heatModes: Array<{ value: HeatMode; label: string }> = [
  { value: "off", label: "Off" },
  { value: "industrial", label: "Industrial" },
  { value: "landfill", label: "Landfills" },
  { value: "military", label: "Military" },
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

function formatCoord(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "----";
  }
  return value.toFixed(4);
}

function formatEvidenceCategory(value?: string): string {
  if (!value) {
    return "unknown";
  }
  if (value === "industrial_frs") {
    return "Industrial";
  }
  if (value === "military_base") {
    return "Military Base";
  }
  if (value === "landfill") {
    return "Landfill";
  }
  if (value === "superfund_npl") {
    return "Superfund NPL";
  }
  return value;
}

function EvidencePopupMarker({
  activeEvidence,
  onEvidencePopupClose,
}: {
  activeEvidence: ActiveEvidence;
  onEvidencePopupClose?: () => void;
}) {
  const map = useMap();
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    map.flyTo([activeEvidence.lat, activeEvidence.lon], 12, {
      animate: true,
      duration: 0.6,
    });

    const timer = window.setTimeout(() => {
      markerRef.current?.openPopup();
    }, 120);

    return () => {
      window.clearTimeout(timer);
    };
  }, [activeEvidence, map]);

  return (
    <Marker
      ref={markerRef}
      position={[activeEvidence.lat, activeEvidence.lon]}
      icon={selectedPointIcon}
      eventHandlers={{
        popupclose: () => {
          onEvidencePopupClose?.();
        },
      }}
    >
      <Popup>
        <div className="space-y-1 text-sm">
          <p className="font-semibold text-ink">{activeEvidence.name ?? "Evidence site"}</p>
          <p className="text-muted">Category: {formatEvidenceCategory(activeEvidence.category)}</p>
          <p className="text-muted">Distance: {formatEvidenceDistance(activeEvidence.distance_miles)}</p>
          <p className="text-muted">Source: {activeEvidence.source ?? "unknown"}</p>
          <p className="text-muted">State: {activeEvidence.state ?? "unknown"}</p>
        </div>
      </Popup>
    </Marker>
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
  onEvidencePopupClose,
}: MapViewProps) {
  const [zoomLevel, setZoomLevel] = useState(US_ZOOM);
  const [userHeatOverride, setUserHeatOverride] = useState(false);
  const activeHeatLabel = heatModes.find((mode) => mode.value === heatMode)?.label ?? "Off";
  const isHeatZoomReady = zoomLevel >= MIN_HEAT_ZOOM;
  const showHeatLayer = heatEnabled && heatMode !== "off" && isHeatZoomReady;

  const handleZoomChange = useCallback((zoom: number) => {
    onZoomLevelChange?.(zoom);
    setZoomLevel((current) => (current === zoom ? current : zoom));
  }, [onZoomLevelChange]);

  const handleHeatModeSelect = useCallback(
    (mode: HeatMode) => {
      setUserHeatOverride(true);
      if (mode !== heatMode) {
        onHeatModeChange?.(mode);
      }
    },
    [heatMode, onHeatModeChange],
  );

  useEffect(() => {
    if (!onHeatModeChange) {
      return;
    }

    if (zoomLevel < MIN_HEAT_ZOOM) {
      if (heatMode !== "off") {
        onHeatModeChange("off");
      }
      return;
    }

    if (!userHeatOverride && heatMode === "off") {
      onHeatModeChange("combined");
    }
  }, [heatMode, onHeatModeChange, userHeatOverride, zoomLevel]);

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
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          noWrap={true}
        />
        <MapBehavior onSelect={onSelect} focusRequest={focusRequest} onZoomChange={handleZoomChange} />
        {showHeatLayer ? <HeatLayer enabled={true} points={heatPoints} mode={heatMode} /> : null}
        {activeEvidence ? (
          <EvidencePopupMarker
            activeEvidence={activeEvidence}
            onEvidencePopupClose={onEvidencePopupClose}
          />
        ) : null}
        {selectedPoint ? <Marker position={[selectedPoint.lat, selectedPoint.lon]} icon={selectedPointIcon} /> : null}
      </MapContainer>

      <div className="pointer-events-none absolute left-4 top-24 rounded-xl border border-border bg-panel/55 px-3 py-2 text-xs font-medium text-muted backdrop-blur-sm">
        Click anywhere in the U.S. to select a point.
      </div>

      <div className="pointer-events-none absolute bottom-4 left-4 z-[650]">
        <div className="w-[200px] rounded-xl border border-border bg-panel/55 p-2 backdrop-blur-sm">
          <p className="text-sm font-medium text-ink">Selected coordinates</p>
          <p className="mt-1 text-sm font-semibold text-ink">Lat: {formatCoord(selectedPoint?.lat)}</p>
          <p className="text-sm font-semibold text-ink">Lon: {formatCoord(selectedPoint?.lon)}</p>
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-4 right-4 z-[650]">
        <div className="group pointer-events-auto w-[154px] rounded-xl border border-border bg-panel/55 p-2 backdrop-blur-sm transition-all duration-300 hover:w-[276px]">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-ink">Heat layer</span>
            <span className="rounded-md border border-border bg-panelSoft/70 px-1.5 py-0.5 text-xs font-medium text-muted">
              {activeHeatLabel}
            </span>
          </div>
          <div className="mt-2 hidden grid-cols-3 gap-1 group-hover:grid">
            {heatModes.map((mode) => (
              <button
                key={mode.value}
                type="button"
                onClick={() => handleHeatModeSelect(mode.value)}
                disabled={!isHeatZoomReady}
                className={`rounded-md border px-1.5 py-1 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-55 ${
                  heatMode === mode.value
                    ? "border-accent bg-accent text-white"
                    : "border-border bg-panelSoft text-ink hover:bg-panelSoft/70"
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
          {!isHeatZoomReady ? (
            <p className="mt-2 text-xs text-muted">Zoom in to enable heat layer (zoom ≥ 7).</p>
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
          {isLoading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {isLoading ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-12 flex items-center justify-center bg-gradient-to-t from-panel/80 via-panel/55 to-transparent py-4">
          <div className="flex items-center gap-2 rounded-full border border-border bg-panel px-4 py-1.5 text-sm text-ink shadow-sm">
            <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
            Running analysis...
          </div>
        </div>
      ) : null}
    </div>
  );
}
