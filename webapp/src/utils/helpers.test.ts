import { describe, expect, it } from "vitest";
import { Release } from "../api";
import { formatSyncSummary, parseFocusId, PILL_STYLE, sortReleases } from "./helpers";

function makeRelease(overrides: Partial<Release> = {}): Release {
  return {
    discogs_release_id: 1,
    title: "Title",
    artist: "Artist",
    year: 2000,
    genres: [],
    styles: [],
    ...overrides,
  };
}

describe("sortReleases", () => {
  const a = makeRelease({ artist: "Aretha", title: "Amazing", year: 1972 });
  const b = makeRelease({ artist: "Bowie", title: "Blackstar", year: 2016 });
  const c = makeRelease({ artist: "Coltrane", title: "Crescent", year: 1964 });

  it("sorts by artist ascending and descending", () => {
    expect(sortReleases([c, a, b], "artist_asc").map((r) => r.artist)).toEqual([
      "Aretha",
      "Bowie",
      "Coltrane",
    ]);
    expect(sortReleases([a, c, b], "artist_desc").map((r) => r.artist)).toEqual([
      "Coltrane",
      "Bowie",
      "Aretha",
    ]);
  });

  it("sorts by title ascending", () => {
    expect(sortReleases([b, c, a], "title_asc").map((r) => r.title)).toEqual([
      "Amazing",
      "Blackstar",
      "Crescent",
    ]);
  });

  it("sorts by year in both directions", () => {
    expect(sortReleases([a, b, c], "year_desc").map((r) => r.year)).toEqual([2016, 1972, 1964]);
    expect(sortReleases([a, b, c], "year_asc").map((r) => r.year)).toEqual([1964, 1972, 2016]);
  });

  it("treats a null or non-numeric year as 0 for year sorts", () => {
    const noYear = makeRelease({ artist: "Zed", year: null });
    expect(sortReleases([a, noYear], "year_asc")[0]).toBe(noYear);
    expect(sortReleases([a, noYear], "year_desc")[0]).toBe(a);
  });

  it("sorts by value descending, treating a missing value as 0", () => {
    const high = makeRelease({
      artist: "High",
      value: {
        price_median: 90,
        price_low: null,
        price_high: null,
        currency: "USD",
        last_updated: null,
      },
    });
    const low = makeRelease({
      artist: "Low",
      value: {
        price_median: 5,
        price_low: null,
        price_high: null,
        currency: "USD",
        last_updated: null,
      },
    });
    const none = makeRelease({ artist: "None" });
    expect(sortReleases([none, low, high], "value_desc").map((r) => r.artist)).toEqual([
      "High",
      "Low",
      "None",
    ]);
  });

  it("does not mutate the input array", () => {
    const input = [b, a, c];
    const copy = [...input];
    sortReleases(input, "artist_asc");
    expect(input).toEqual(copy);
  });
});

describe("parseFocusId", () => {
  it("parses a positive integer string", () => {
    expect(parseFocusId("42")).toBe(42);
  });

  it("returns null for null, empty, non-numeric, zero, negative, and fractional input", () => {
    expect(parseFocusId(null)).toBeNull();
    expect(parseFocusId("")).toBeNull();
    expect(parseFocusId("abc")).toBeNull();
    expect(parseFocusId("0")).toBeNull();
    expect(parseFocusId("-5")).toBeNull();
    expect(parseFocusId("1.5")).toBeNull();
  });
});

describe("formatSyncSummary", () => {
  const summary = {
    fetched_count: 10,
    upserted_count: 8,
    deactivated_count: 2,
    last_sync_time: null,
  };

  it("defaults the label to Collection", () => {
    expect(formatSyncSummary(summary)).toBe(
      "Collection sync complete: fetched 10, upserted 8, deactivated 2.",
    );
  });

  it("uses an explicit label", () => {
    expect(formatSyncSummary(summary, "Wantlist")).toBe(
      "Wantlist sync complete: fetched 10, upserted 8, deactivated 2.",
    );
  });
});

describe("PILL_STYLE", () => {
  it("is an inline-flex style object", () => {
    expect(PILL_STYLE).toEqual({ display: "inline-flex" });
  });
});
