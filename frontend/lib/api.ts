import type {
  AnalyzeResponse,
  GenerateReportPayload,
  HealthResponse,
  ReportResponse,
} from "./types";

const DEFAULT_BASE_URL = "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 20_000;
const MAX_RETRIES = 1;
const RETRY_DELAY_MS = 750;

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") || DEFAULT_BASE_URL;

export class ApiError extends Error {
  status?: number;
  details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function extractErrorMessage(body: unknown): string | null {
  if (!body) {
    return null;
  }

  if (typeof body === "string") {
    return body;
  }

  if (typeof body === "object" && body !== null) {
    const maybeDetail = (body as { detail?: unknown }).detail;
    if (typeof maybeDetail === "string") {
      return maybeDetail;
    }
    if (Array.isArray(maybeDetail)) {
      const first = maybeDetail[0];
      if (typeof first === "string") {
        return first;
      }
      if (first && typeof first === "object" && "msg" in first) {
        return String((first as { msg: unknown }).msg);
      }
    }
    if ("message" in body) {
      return String((body as { message: unknown }).message);
    }
  }

  return null;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let attempt = 0;

  while (attempt <= MAX_RETRIES) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(`${apiBaseUrl}${path}`, {
        ...init,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers || {}),
        },
        cache: "no-store",
      });

      const raw = await response.text();
      const parsed = raw ? safeParseJson(raw) : null;

      if (!response.ok) {
        const message =
          extractErrorMessage(parsed) ||
          `Request failed with status ${response.status}`;
        throw new ApiError(message, response.status, parsed);
      }

      return parsed as T;
    } catch (error) {
      const apiError =
        error instanceof ApiError
          ? error
          : error instanceof DOMException && error.name === "AbortError"
            ? new ApiError(
                `Request timed out after ${REQUEST_TIMEOUT_MS / 1000} seconds.`,
                408,
              )
            : new ApiError("Network request failed.", undefined, error);

      const isRetriable = apiError.status === 408 || apiError.status == null;
      if (attempt < MAX_RETRIES && isRetriable) {
        attempt += 1;
        await delay(RETRY_DELAY_MS * attempt);
        continue;
      }
      throw apiError;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  throw new ApiError("Network request failed.");
}

function safeParseJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function getApiBaseUrl(): string {
  return apiBaseUrl;
}

export function health(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health", {
    method: "GET",
  });
}

export function analyzePoint(lat: number, lon: number): Promise<AnalyzeResponse> {
  return requestJson<AnalyzeResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify({ lat, lon }),
  });
}

export function generateReport(payload: GenerateReportPayload): Promise<ReportResponse> {
  return requestJson<ReportResponse>("/report", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status) {
      return `${error.status}: ${error.message}`;
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown error";
}
