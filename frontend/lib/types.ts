export type HeatMode = "off" | "landfill" | "superfund" | "combined";
export type HeatPoint = [number, number] | [number, number, number];
export type SiteCategory = "landfill" | "superfund";

export interface LatLon {
  lat: number;
  lon: number;
}

export interface Location extends LatLon {
  label?: string;
}

export interface ProximitySite {
  id: string;
  name: string;
  category: SiteCategory;
  distance_miles: number;
  lat: number;
  lon: number;
  state: string;
  source: string;
}

export interface NearestByCategory {
  landfill: ProximitySite | null;
  superfund: ProximitySite | null;
}

export interface RadiusCounts {
  within_1_mile: number;
  within_5_miles: number;
  within_10_miles: number;
}

export interface CountsWithinMiles {
  landfill: RadiusCounts;
  superfund: RadiusCounts;
}

export interface Meta {
  version: string;
  timestamp_utc: string;
  nearby_radius_miles: number;
  nearby_site_limit: number;
  notes: string[];
}

export interface AnalyzeResponse {
  location: Location;
  nearest_mapped_site: ProximitySite | null;
  nearest_by_category: NearestByCategory;
  counts_within_miles: CountsWithinMiles;
  nearby_sites: ProximitySite[];
  meta: Meta;
}

export type ActiveEvidence = ProximitySite;

export interface MapFocusRequest {
  id: number;
  lat: number;
  lon: number;
  zoom: number;
}
