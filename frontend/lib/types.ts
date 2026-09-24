export type RiskBand = "Low" | "Moderate" | "High";
export type HeatMode = "off" | "landfill" | "military" | "superfund" | "combined";
export type HeatPoint = [number, number] | [number, number, number];
export type EvidenceCategory = "landfill" | "military_base" | "superfund_npl";

export interface LatLon {
  lat: number;
  lon: number;
}

export interface Location extends LatLon {
  label?: string;
}

export interface Signals {
  nearest_landfill_miles?: number | null;
  nearest_military_base_miles?: number | null;
  nearest_superfund_npl_miles?: number | null;
  superfund_count_3mi?: number;
}

export interface ScoreBreakdown {
  landfill?: number;
  military?: number;
  landfill_proximity?: number;
  military_proximity?: number;
  superfund_proximity?: number;
}

export interface Score {
  total: number;
  band: RiskBand;
  breakdown: ScoreBreakdown;
  top_drivers?: string[];
}

export interface EvidenceItem {
  id?: string | null;
  name?: string | null;
  distance_miles?: number | null;
  lat?: number | null;
  lon?: number | null;
  state?: string | null;
  source?: string | null;
}

export interface Evidence {
  landfill: EvidenceItem[];
  military_base: EvidenceItem[];
  superfund_npl?: EvidenceItem[];
}

export interface ActiveEvidence {
  id: string;
  lat: number;
  lon: number;
  name?: string;
  distance_miles?: number;
  source?: string;
  state?: string;
  category?: EvidenceCategory;
}

export interface Meta {
  version?: string;
  timestamp_utc?: string;
  cached?: boolean;
  notes?: string[];
}

export interface AnalyzeResponse {
  location: Location;
  signals: Signals;
  score: Score;
  evidence: Evidence;
  meta: Meta;
}

export interface HealthResponse {
  status: "ok";
  dataset_loaded: boolean;
  version?: string;
  timestamp_utc?: string;
  ready?: boolean;
  uptime_seconds?: number;
  startup_total_seconds?: number;
}

export interface MapFocusRequest {
  id: number;
  lat: number;
  lon: number;
  zoom: number;
}
