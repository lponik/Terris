"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet.heat";
import { useMap } from "react-leaflet";

import type { HeatMode, HeatPoint } from "@/lib/types";

interface HeatLayerProps {
  points: HeatPoint[];
  enabled: boolean;
  mode?: HeatMode;
}

type HeatFactory = (
  latlngs: HeatPoint[],
  options?: {
    radius?: number;
    blur?: number;
    maxZoom?: number;
    minOpacity?: number;
    gradient?: Record<number, string>;
  },
) => L.Layer;

type LeafletWithHeat = typeof L & { heatLayer?: HeatFactory };

function heatOptionsForMode(mode: HeatMode) {
  if (mode === "industrial") {
    return {
      radius: 22,
      blur: 16,
      maxZoom: 12,
      minOpacity: 0.28,
      gradient: {
        0.2: "#ffbe0b",
        0.5: "#fb5607",
        0.8: "#e63946",
        1.0: "#7f1d1d",
      },
    };
  }

  if (mode === "landfill") {
    return {
      radius: 21,
      blur: 15,
      maxZoom: 12,
      minOpacity: 0.24,
      gradient: {
        0.2: "#84cc16",
        0.5: "#22c55e",
        0.8: "#16a34a",
        1.0: "#166534",
      },
    };
  }

  if (mode === "military") {
    return {
      radius: 23,
      blur: 16,
      maxZoom: 12,
      minOpacity: 0.24,
      gradient: {
        0.2: "#facc15",
        0.5: "#f59e0b",
        0.8: "#b45309",
        1.0: "#78350f",
      },
    };
  }

  if (mode === "superfund") {
    return {
      radius: 22,
      blur: 16,
      maxZoom: 12,
      minOpacity: 0.26,
      gradient: {
        0.2: "#bde680",
        0.5: "#7ebc3a",
        0.8: "#4f7f1d",
        1.0: "#2f4f12",
      },
    };
  }

  return {
    radius: 20,
    blur: 15,
    maxZoom: 12,
    minOpacity: 0.25,
    gradient: {
      0.2: "#34d399",
      0.5: "#f59e0b",
      0.8: "#ef4444",
      1.0: "#7f1d1d",
    },
  };
}

export default function HeatLayer({ points, enabled, mode = "combined" }: HeatLayerProps) {
  const map = useMap();
  const layerRef = useRef<L.Layer | null>(null);

  useEffect(() => {
    if (layerRef.current) {
      map.removeLayer(layerRef.current);
      layerRef.current = null;
    }

    if (!enabled || points.length === 0) {
      return;
    }

    const heatFactory = (L as LeafletWithHeat).heatLayer;
    if (!heatFactory) {
      return;
    }

    const layer = heatFactory(points, heatOptionsForMode(mode));

    layer.addTo(map);
    layerRef.current = layer;

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
        layerRef.current = null;
      }
    };
  }, [enabled, map, mode, points]);

  return null;
}
