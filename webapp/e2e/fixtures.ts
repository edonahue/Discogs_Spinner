/** Typed stub data for Playwright API mocks. */

function envelope<T>(data: T) {
  return { ok: true, data, error: null, meta: {} };
}

export const STUB_RELEASES = [
  {
    discogs_release_id: 1,
    title: "Kind of Blue",
    artist: "Miles Davis",
    year: 1959,
    genres: ["Jazz"],
    styles: ["Modal"],
  },
  {
    discogs_release_id: 2,
    title: "Innervisions",
    artist: "Stevie Wonder",
    year: 1973,
    genres: ["Funk / Soul"],
    styles: ["Soul"],
  },
  {
    discogs_release_id: 3,
    title: "Remain in Light",
    artist: "Talking Heads",
    year: 1980,
    genres: ["Electronic", "Rock"],
    styles: ["Post-Punk", "New Wave"],
  },
];

export const STUB_SETUP = envelope({ onboarding_stage: "complete" });

export const STUB_COLLECTION = envelope(STUB_RELEASES);

export const STUB_WANTLIST = envelope([
  {
    discogs_release_id: 10,
    title: "Dummy",
    artist: "Portishead",
    year: 1994,
    genres: ["Electronic"],
    styles: ["Trip Hop"],
  },
]);

export const STUB_VALUE_DASHBOARD = envelope({
  top_releases: [
    {
      discogs_release_id: 1,
      title: "Kind of Blue",
      artist: "Miles Davis",
      price_median: 24.99,
      price_high: 40.0,
      currency: "USD",
    },
  ],
  last_updated: "2026-03-09T00:00:00",
});

export const STUB_VALUE_QUEUE = envelope({
  total_candidates: 5,
  missing_count: 2,
  unpriced_count: 1,
  stale_count: 2,
  stale_days: 90,
  limit: 25,
  queue: [],
});

export const STUB_HEALTH = envelope({
  score: 82,
  total_active: 100,
  buckets: [
    {
      name: "unmatched",
      label: "Unmatched releases",
      gap_count: 5,
      gap_pct: 5.0,
      max_deduction: 20,
      deduction: 5.0,
    },
    {
      name: "unpriced",
      label: "Unpriced releases",
      gap_count: 8,
      gap_pct: 8.0,
      max_deduction: 15,
      deduction: 7.0,
    },
    {
      name: "stale_value",
      label: "Stale value data",
      gap_count: 3,
      gap_pct: 3.0,
      max_deduction: 10,
      deduction: 1.0,
    },
  ],
});

export const STUB_RECENT = envelope({
  ok: true,
  releases: STUB_RELEASES,
  count: 3,
  days: 30,
  limit: 50,
});

export const STUB_ANALYTICS = envelope({
  release_count_active: 150,
  mapped_count: 120,
  unmatched_count: 30,
  top_limit: 10,
  by_release_year: [
    { year: 1980, count: 12 },
    { year: 1973, count: 9 },
    { year: 1959, count: 5 },
  ],
  acquisition_timeline: [
    { year: 2024, count: 40 },
    { year: 2023, count: 55 },
  ],
  top_genres: [
    { genre: "Jazz", count: 45 },
    { genre: "Rock", count: 38 },
    { genre: "Electronic", count: 27 },
  ],
  top_styles: [
    { style: "Soul", count: 20 },
    { style: "Post-Punk", count: 15 },
  ],
  top_artists: [
    { artist: "Miles Davis", count: 8 },
    { artist: "Stevie Wonder", count: 5 },
  ],
});

export const STUB_TRACKLIST = envelope({
  discogs_release_id: 1,
  title: "Kind of Blue",
  artist: "Miles Davis",
  has_cached_tracklist: true,
  has_tracklist: true,
  tracks: [
    { position: "A1", title: "So What", duration: "9:22", type_: "track" },
    { position: "A2", title: "Freddie Freeloader", duration: "9:46", type_: "track" },
    { position: "B1", title: "Blue in Green", duration: "5:37", type_: "track" },
  ],
  track_count: 5,
  audio_track_count: 5,
  tracklist_last_refreshed_at: "2026-03-09T00:00:00",
});
