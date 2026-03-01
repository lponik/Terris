export type RiskBand = "Low" | "Moderate" | "High";
export type HeatMode = "off" | "industrial" | "landfill" | "military" | "superfund" | "combined";
export type HeatPoint = [number, number] | [number, number, number];
export type EvidenceCategory = "landfill" | "military_base" | "industrial_frs" | "superfund_npl";

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
  nearest_industrial_frs_miles?: number | null;
  nearest_superfund_npl_miles?: number | null;
  industrial_count_1mi?: number;
  industrial_count_3mi?: number;
  industrial_count_10mi?: number;
  superfund_count_3mi?: number;
}

export interface ScoreBreakdown {
  landfill?: number;
  military?: number;
  industrial?: number;
  landfill_proximity?: number;
  military_proximity?: number;
  industrial_density?: number;
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
  industrial_frs: EvidenceItem[];
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
}

export interface ReportDriver {
  title: string;
  detail: string;
}

export interface ReportSiteTypeContext {
  site_type: string;
  what_it_can_indicate: string;
}

export interface ReportNextStep {
  action: string;
  why: string;
}

export interface ReportConfidence {
  level: RiskBand;
  rationale: string;
}

export interface ReportResponse {
  summary: string;
  top_drivers_explained: ReportDriver[];
  site_type_context: ReportSiteTypeContext[];
  recommended_next_steps: ReportNextStep[];
  limitations: string[];
  confidence: ReportConfidence;
}

export interface GenerateReportPayload {
  lat: number;
  lon: number;
}

export interface MapFocusRequest {
  id: number;
  lat: number;
  lon: number;
  zoom: number;
}
