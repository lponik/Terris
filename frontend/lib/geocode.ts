const NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search";
const NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse";
const SEARCH_USER_AGENT = "terris-proximity-map/1.0 (contact: demo@local)";

interface NominatimSearchResponseRow {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
  class?: string;
  type?: string;
  address?: Record<string, string | undefined>;
}

export interface GeocodeResult {
  placeId: string;
  displayName: string;
  lat: number;
  lon: number;
  className?: string;
  type?: string;
  stateCode?: string;
}

interface NominatimReverseResponse {
  address?: Record<string, string | undefined>;
}

function stateCodeFromAddress(address?: Record<string, string | undefined>): string | undefined {
  const direct = address?.state_code?.trim().toUpperCase();
  if (direct && /^[A-Z]{2}$/.test(direct)) {
    return direct;
  }

  const isoCode = address?.["ISO3166-2-lvl4"]?.trim().toUpperCase();
  const suffix = isoCode?.match(/^US-([A-Z]{2})$/)?.[1];
  return suffix;
}

export class GeocodeError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "GeocodeError";
    this.status = status;
  }
}

export function inferSearchZoom(result: GeocodeResult): number {
  const type = (result.type ?? "").toLowerCase();
  if (["house", "building", "residential", "amenity"].includes(type)) {
    return 16;
  }
  if (["postcode", "neighbourhood", "suburb"].includes(type)) {
    return 15;
  }
  return 14;
}

export async function searchUsLocations(
  query: string,
  signal?: AbortSignal,
): Promise<GeocodeResult[]> {
  const trimmed = query.trim();
  if (!trimmed) {
    return [];
  }

  const params = new URLSearchParams({
    q: trimmed,
    format: "json",
    limit: "5",
    addressdetails: "1",
    countrycodes: "us",
  });

  const headers = new Headers();
  headers.set("Accept-Language", "en");
  headers.set("X-Client", SEARCH_USER_AGENT);
  const referrer = typeof window !== "undefined" ? window.location.origin : undefined;

  // Browsers generally block custom User-Agent headers. We attempt it and
  // fall back to referrer + custom client header when blocked.
  try {
    headers.set("User-Agent", SEARCH_USER_AGENT);
  } catch {
    // Fallback headers are already set above for browser environments.
  }

  const response = await fetch(`${NOMINATIM_SEARCH_URL}?${params.toString()}`, {
    method: "GET",
    headers,
    signal,
    cache: "no-store",
    referrer,
    referrerPolicy: "strict-origin-when-cross-origin",
  });

  if (!response.ok) {
    if (response.status === 429) {
      throw new GeocodeError("Search rate-limited. Please wait and try again.", response.status);
    }
    throw new GeocodeError(`Search failed (${response.status}).`, response.status);
  }

  const payload = (await response.json()) as NominatimSearchResponseRow[];
  if (!Array.isArray(payload)) {
    throw new GeocodeError("Unexpected search response format.");
  }

  const results: GeocodeResult[] = [];
  for (const item of payload) {
    const lat = Number(item.lat);
    const lon = Number(item.lon);
    if (Number.isNaN(lat) || Number.isNaN(lon)) {
      continue;
    }

    results.push({
      placeId: String(item.place_id),
      displayName: item.display_name,
      lat,
      lon,
      className: item.class,
      type: item.type,
      stateCode: stateCodeFromAddress(item.address),
    });
  }

  return results;
}

export async function reverseGeocodeUsState(
  lat: number,
  lon: number,
  signal?: AbortSignal,
): Promise<string | null> {
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    format: "json",
    addressdetails: "1",
    zoom: "5",
  });
  const response = await fetch(`${NOMINATIM_REVERSE_URL}?${params.toString()}`, {
    method: "GET",
    signal,
    cache: "no-store",
    headers: { "Accept-Language": "en" },
    referrer: typeof window !== "undefined" ? window.location.origin : undefined,
    referrerPolicy: "strict-origin-when-cross-origin",
  });
  if (!response.ok) {
    return null;
  }
  const payload = (await response.json()) as NominatimReverseResponse;
  return stateCodeFromAddress(payload.address) ?? null;
}

export function getGeocodeErrorMessage(error: unknown): string {
  if (error instanceof GeocodeError) {
    return error.message;
  }
  if (error instanceof DOMException && error.name === "AbortError") {
    return "";
  }
  return "Search unavailable.";
}
