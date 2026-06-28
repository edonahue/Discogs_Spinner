import { afterEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl, getJson, postJson } from "./api";

const DEFAULT_BASE_URL = "http://127.0.0.1:8768/api/v1";

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

function okEnvelope<T>(data: T) {
  return { ok: true, data, error: null, meta: {} };
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("apiBaseUrl", () => {
  it("returns the default localhost base when no env override is set", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    expect(apiBaseUrl()).toBe(DEFAULT_BASE_URL);
  });

  it("uses the env override and trims a trailing slash", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://example.com/api/");
    expect(apiBaseUrl()).toBe("https://example.com/api");
  });

  it("trims surrounding whitespace on the env override", () => {
    vi.stubEnv("VITE_API_BASE_URL", "  https://example.com/api  ");
    expect(apiBaseUrl()).toBe("https://example.com/api");
  });
});

describe("getJson", () => {
  it("returns the parsed envelope on success and calls the expected URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(okEnvelope({ value: 1 })));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getJson<{ value: number }>("/status");

    expect(result.data).toEqual({ value: 1 });
    expect(fetchMock).toHaveBeenCalledWith(
      `${DEFAULT_BASE_URL}/status`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws the server error message when the HTTP response is not ok", async () => {
    const body = { ok: false, data: null, error: { message: "boom" }, meta: {} };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body, false, 500)));

    await expect(getJson("/status")).rejects.toThrow("boom");
  });

  it("throws when the envelope reports ok: false even on a 200", async () => {
    const body = { ok: false, data: null, error: { message: "nope" }, meta: {} };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body, true, 200)));

    await expect(getJson("/status")).rejects.toThrow("nope");
  });

  it("falls back to a status-code message when no error message is present", async () => {
    const body = { ok: false, data: null, error: null, meta: {} };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body, false, 503)));

    await expect(getJson("/status")).rejects.toThrow("Request failed (503)");
  });
});

describe("postJson", () => {
  it("posts a JSON body and returns the envelope", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(okEnvelope({ saved: true })));
    vi.stubGlobal("fetch", fetchMock);

    const result = await postJson<{ saved: boolean }>("/setup", { discogs_token: "t" });

    expect(result.data).toEqual({ saved: true });
    expect(fetchMock).toHaveBeenCalledWith(
      `${DEFAULT_BASE_URL}/setup`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ discogs_token: "t" }),
      }),
    );
  });

  it("throws on an error envelope", async () => {
    const body = { ok: false, data: null, error: { message: "bad token" }, meta: {} };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(body, false, 400)));

    await expect(postJson("/setup", {})).rejects.toThrow("bad token");
  });
});
