export type ApiEnvelope<T> = {
  ok: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
    retryable: boolean;
    details: unknown;
  } | null;
  meta: Record<string, unknown>;
};

const DEFAULT_BASE_URL = "http://127.0.0.1:8768/api/v1";

export function apiBaseUrl(): string {
  const envValue = import.meta.env.VITE_API_BASE_URL;
  if (typeof envValue === "string" && envValue.trim().length > 0) {
    return envValue.trim().replace(/\/$/, "");
  }
  return DEFAULT_BASE_URL;
}

export async function getJson<T>(path: string): Promise<ApiEnvelope<T>> {
  const url = `${apiBaseUrl()}${path}`;
  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Accept": "application/json"
    }
  });
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error?.message ?? `Request failed (${response.status})`);
  }
  return payload;
}

export async function postJson<T>(path: string, body: unknown): Promise<ApiEnvelope<T>> {
  const url = `${apiBaseUrl()}${path}`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error?.message ?? `Request failed (${response.status})`);
  }
  return payload;
}

export interface ReleaseValue {
  price_median: number | null;
  price_low: number | null;
  price_high: number | null;
  currency: string;
  last_updated: string | null;
}

export interface Release {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: string | number | null;
  genres: string[];
  styles: string[];
  value?: ReleaseValue;
}

export interface ReleaseFilters {
  q?: string;
  year?: string;
  genres?: string[];
  styles?: string[];
  unmatched?: boolean;
  withValue?: boolean;
  limit?: number;
}

function buildReleaseParams(filters: ReleaseFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.q) params.set("q", filters.q);
  if (filters.year) params.set("year", filters.year);
  if (filters.genres) {
    for (const g of filters.genres) params.append("genres[]", g);
  }
  if (filters.styles) {
    for (const s of filters.styles) params.append("styles[]", s);
  }
  if (filters.unmatched) params.set("unmatched", "true");
  if (filters.withValue) params.set("with_value", "true");
  return params;
}

export function fetchReleases(filters: ReleaseFilters): Promise<ApiEnvelope<Release[]>> {
  return getJson<Release[]>(`/releases?${buildReleaseParams(filters).toString()}`);
}

export function fetchWantlist(filters: ReleaseFilters): Promise<ApiEnvelope<Release[]>> {
  return getJson<Release[]>(`/wantlist?${buildReleaseParams(filters).toString()}`);
}

export function syncCollection(): Promise<ApiEnvelope<unknown>> {
  return postJson<unknown>("/sync/collection", {});
}

export function syncWantlist(): Promise<ApiEnvelope<unknown>> {
  return postJson<unknown>("/sync/wantlist", {});
}

export interface ValueEntry {
  discogs_release_id: number;
  title: string;
  artist: string;
  price_median: number | null;
  price_high: number | null;
  currency: string;
}

export interface ValueDashboard {
  top_releases: ValueEntry[];
  last_updated: string | null;
}

export function fetchValueDashboard(params?: { top_limit?: number }): Promise<ApiEnvelope<ValueDashboard>> {
  const qs = params?.top_limit !== undefined ? `?top_limit=${params.top_limit}` : "";
  return getJson<ValueDashboard>(`/value/dashboard${qs}`);
}
