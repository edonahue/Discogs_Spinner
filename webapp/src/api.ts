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
