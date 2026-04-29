import type {
  AnalyzeResponse,
  GenerateReportPayload,
  HealthResponse,
  ReportResponse,
} from "./types";

const DEFAULT_BASE_URL = "http://localhost:8000";
const HEALTH_TIMEOUT_MS = 10_000;
const COLD_ANALYZE_TIMEOUT_MS = 30_000;
const WARM_ANALYZE_TIMEOUT_MS = 15_000;
const COLD_REPORT_TIMEOUT_MS = 30_000;
const WARM_REPORT_TIMEOUT_MS = 15_000;
const HEALTH_MAX_ATTEMPTS = 1;
const ANALYZE_MAX_ATTEMPTS = 2;
const REPORT_MAX_ATTEMPTS = 2;
const RETRY_DELAY_BASE_MS = 600;
const RETRY_DELAY_JITTER_MS = 300;
const RETRIABLE_HTTP_STATUS_CODES = new Set([502, 503, 504]);

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") || DEFAULT_BASE_URL;

export type ApiErrorKind = "timeout" | "network" | "http_4xx" | "http_5xx";

type RequestPolicy = {
  coldTimeoutMs: number;
  warmTimeoutMs: number;
  maxAttempts: number;
  markBackendWarm: boolean;
};

let isBackendWarm = false;

export class ApiError extends Error {
  kind: ApiErrorKind;
  status?: number;
  details?: unknown;

  constructor(kind: ApiErrorKind, message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.details = details;
  }
}

function getErrorKindForStatus(status: number): ApiErrorKind {
  if (status >= 500) {
    return "http_5xx";
  }
  return "http_4xx";
}

function markBackendWarm(): void {
  if (isBackendWarm) {
    return;
  }
  isBackendWarm = true;
}

function getRequestPolicy(path: string): RequestPolicy {
  if (path === "/health") {
    return {
      coldTimeoutMs: HEALTH_TIMEOUT_MS,
      warmTimeoutMs: HEALTH_TIMEOUT_MS,
      maxAttempts: HEALTH_MAX_ATTEMPTS,
      markBackendWarm: false,
    };
  }
  if (path === "/analyze") {
    return {
      coldTimeoutMs: COLD_ANALYZE_TIMEOUT_MS,
      warmTimeoutMs: WARM_ANALYZE_TIMEOUT_MS,
      maxAttempts: ANALYZE_MAX_ATTEMPTS,
      markBackendWarm: true,
    };
  }
  if (path === "/report") {
    return {
      coldTimeoutMs: COLD_REPORT_TIMEOUT_MS,
      warmTimeoutMs: WARM_REPORT_TIMEOUT_MS,
      maxAttempts: REPORT_MAX_ATTEMPTS,
      markBackendWarm: false,
    };
  }
  return {
    coldTimeoutMs: COLD_ANALYZE_TIMEOUT_MS,
    warmTimeoutMs: WARM_ANALYZE_TIMEOUT_MS,
    maxAttempts: ANALYZE_MAX_ATTEMPTS,
    markBackendWarm: false,
  };
}

function getRequestTimeoutMs(policy: RequestPolicy): number {
  return isBackendWarm ? policy.warmTimeoutMs : policy.coldTimeoutMs;
}

function getRetryDelayMs(attempt: number): number {
  const exponentialBase = RETRY_DELAY_BASE_MS * 2 ** (attempt - 1);
  const jitter = Math.floor(Math.random() * RETRY_DELAY_JITTER_MS);
  return exponentialBase + jitter;
}

function isRetriableError(error: ApiError): boolean {
  if (error.kind === "timeout" || error.kind === "network") {
    return true;
  }
  if (error.status != null && RETRIABLE_HTTP_STATUS_CODES.has(error.status)) {
    return true;
  }
  return false;
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
  const policy = getRequestPolicy(path);
  let attempt = 1;
  while (attempt <= policy.maxAttempts) {
    const controller = new AbortController();
    const timeoutMs = getRequestTimeoutMs(policy);
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

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
        throw new ApiError(
          getErrorKindForStatus(response.status),
          message,
          response.status,
          parsed,
        );
      }

      if (policy.markBackendWarm) {
        markBackendWarm();
      }
      return parsed as T;
    } catch (error) {
      const apiError =
        error instanceof ApiError
          ? error
          : error instanceof DOMException && error.name === "AbortError"
            ? new ApiError(
                "timeout",
                `Request timed out after ${timeoutMs / 1000} seconds.`,
                408,
              )
            : new ApiError("network", "Network request failed.", undefined, error);

      const hasMoreAttempts = attempt < policy.maxAttempts;
      if (hasMoreAttempts && isRetriableError(apiError)) {
        const delayMs = getRetryDelayMs(attempt);
        attempt += 1;
        await delay(delayMs);
        continue;
      }
      throw apiError;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  throw new ApiError("network", "Network request failed.");
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

export function isBackendWarmSession(): boolean {
  return isBackendWarm;
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
