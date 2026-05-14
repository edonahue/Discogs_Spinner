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

export const STUB_SETUP = envelope({
  onboarding_stage: "ready",
  provider_readiness: {
    schema_version: 2,
    core_service: {
      service_id: "discogs",
      display_name: "Discogs",
      required: true,
      optional: false,
      configured: true,
      auth_required: true,
      auth_state: "authenticated",
      readiness: "ready",
      degraded_reasons: [],
      status_message: "Discogs token configured.",
      action_label: "Configured",
      supported_capabilities: ["collection_sync"],
      can_skip_setup: false,
      can_retry_setup: true,
      next_actions: [],
      setup_url: "https://www.discogs.com/settings/developers",
    },
    providers: [],
    next_actions: [],
    summary: {
      required_services_configured: true,
      optional_provider_count: 0,
      ready_provider_count: 0,
      degraded_mode: false,
      onboarding_state: "ready",
      collection_synced: true,
      next_actions: [],
      can_skip_optional_setup: true,
    },
  },
});

export const STUB_STATUS = envelope({
  release_count_total: 3,
  release_count_active: 3,
  mapped_count: 2,
  unmatched_count: 1,
  wantlist_count: 1,
  last_sync_time: "2026-03-09T00:00:00",
  market_value_last_updated: "2026-03-09T00:00:00",
  spotify_capability: {
    addon_available: false,
    configured: false,
    action_label: "Unavailable",
  },
  provider_readiness: {
    schema_version: 2,
    core_service: {
      service_id: "discogs",
      display_name: "Discogs",
      required: true,
      optional: false,
      configured: true,
      auth_required: true,
      auth_state: "authenticated",
      readiness: "ready",
      degraded_reasons: [],
      status_message: "Discogs token configured.",
      action_label: "Configured",
      supported_capabilities: ["collection_sync"],
      can_skip_setup: false,
      can_retry_setup: true,
      next_actions: [],
      setup_url: "https://www.discogs.com/settings/developers",
    },
    providers: [
      {
        provider_id: "spotify",
        display_name: "Spotify",
        required: false,
        optional: true,
        listed: true,
        enabled: true,
        installed: false,
        addon_available: false,
        configured: false,
        auth_required: true,
        auth_state: "unauthenticated",
        readiness: "unavailable",
        degraded_reasons: ["addon_unavailable"],
        status_message: "Spotify addon is unavailable.",
        action_label: "Enable Spotify (optional)",
        supported_capabilities: ["playback", "catalog_matching"],
        can_skip_setup: true,
        can_retry_setup: true,
        next_actions: ["Install optional addon dependencies for this provider."],
        docs_url: "https://developer.spotify.com/documentation/web-api",
        setup_url: "https://developer.spotify.com/dashboard",
        oauth_guide_url: "https://developer.spotify.com/documentation/web-api/tutorials/code-flow",
        experimental: false,
        experimental_flag: null,
      },
    ],
    next_actions: ["Install optional addon dependencies for this provider."],
    summary: {
      required_services_configured: true,
      optional_provider_count: 1,
      ready_provider_count: 0,
      degraded_mode: true,
      onboarding_state: "core_ready_optional_pending",
      collection_synced: true,
      next_actions: ["Install optional addon dependencies for this provider."],
      can_skip_optional_setup: true,
    },
  },
});

export const STUB_COLLECTOR_INSIGHTS = envelope({
  summary: {
    release_count_active: 3,
    mapped_count: 2,
    unmatched_count: 1,
    wantlist_count: 1,
    market_value_last_updated: "2026-03-09T00:00:00",
    last_sync_time: "2026-03-09T00:00:00",
    last_spin_release_id: 1,
    onboarding_state: "core_ready_optional_pending",
    degraded_mode: true,
    health_score: 86,
    hidden_gems_count: 1,
    refresh_queue_count: 2,
    ready_for_daily_use: true,
  },
  highlights: [
    {
      kind: "discovery",
      title: "Tonight's hidden gem",
      message: "Miles Davis - Kind of Blue (1959)",
      command_hint: "dplayer value gems --limit 10 --json",
      release_id: 1,
    },
  ],
  daily_use_actions: ["Run `dplayer sync` occasionally.", "Try `dplayer spin`."],
  top_hidden_gems: [
    {
      discogs_release_id: 1,
      artist: "Miles Davis",
      title: "Kind of Blue",
      year: 1959,
      market_median: 24.99,
      market_currency: "USD",
      num_for_sale: 12,
      gem_score: 72,
      reasons: ["Valuable and scarce enough to revisit."],
    },
  ],
});

export const STUB_COLLECTION = envelope(STUB_RELEASES);

export const STUB_COLLECTION_SUMMARY = envelope({
  release_count: 3,
  lp_count: 2,
  rpm45_count: 1,
  format_counts_ready: true,
  priced_release_count: 2,
  total_median: 55.49,
  median_currency: "USD",
  mixed_currencies: false,
  most_recent_added_at: "2026-04-18T14:00:00Z",
  most_recent_release_id: 3,
  most_recent_release_artist: "Talking Heads",
  most_recent_release_title: "Remain in Light",
});

export const STUB_COLLECTION_SUMMARY_AFTER_SYNC = envelope({
  release_count: 4,
  lp_count: 3,
  rpm45_count: 1,
  format_counts_ready: true,
  priced_release_count: 3,
  total_median: 88.49,
  median_currency: "USD",
  mixed_currencies: false,
  most_recent_added_at: "2026-04-18T14:00:00Z",
  most_recent_release_id: 4,
  most_recent_release_artist: "Erykah Badu",
  most_recent_release_title: "Baduizm",
});

export const STUB_COLLECTION_AFTER_SYNC = envelope([
  ...STUB_RELEASES,
  {
    discogs_release_id: 4,
    title: "Baduizm",
    artist: "Erykah Badu",
    year: 1997,
    genres: ["Hip Hop", "Funk / Soul"],
    styles: ["Neo Soul"],
  },
]);

export const STUB_COLLECTION_SYNC_SUMMARY = envelope({
  fetched_count: 4,
  upserted_count: 4,
  deactivated_count: 0,
  last_sync_time: "2026-04-18T14:00:00",
  skipped_empty_deactivate: false,
  warnings: [],
});

export const STUB_COLLECTION_DETAIL = envelope({
  discogs_release_id: 1,
  title: "Kind of Blue",
  artist: "Miles Davis",
  year: 1959,
  genres: ["Jazz"],
  styles: ["Modal"],
  thumb_url: null,
  cover_url: null,
  added_at: "2026-01-15T00:00:00",
  last_synced_at: "2026-03-09T00:00:00",
  is_active: true,
  spotify_album_id: "spotify:album:123",
  market_lowest: 18.0,
  market_median: 24.99,
  market_highest: 40.0,
  market_currency: "USD",
  market_last_updated_at: "2026-03-09T00:00:00",
  num_for_sale: 12,
  lowest_price: 18.0,
  community_have: 500,
  community_want: 42,
  rating_count: 320,
  rating_average: 4.8,
});

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

export const STUB_WANTLIST_AFTER_SYNC = envelope([
  {
    discogs_release_id: 10,
    title: "Dummy",
    artist: "Portishead",
    year: 1994,
    genres: ["Electronic"],
    styles: ["Trip Hop"],
  },
  {
    discogs_release_id: 11,
    title: "Black Saint And The Sinner Lady",
    artist: "Charles Mingus",
    year: 1963,
    genres: ["Jazz"],
    styles: ["Post Bop"],
  },
]);

export const STUB_WANTLIST_SYNC_SUMMARY = envelope({
  fetched_count: 2,
  upserted_count: 2,
  deactivated_count: 0,
  last_sync_time: "2026-04-18T14:05:00",
  skipped_empty_deactivate: false,
  warnings: [],
});

export const STUB_WANTLIST_DETAIL = envelope({
  discogs_release_id: 10,
  title: "Dummy",
  artist: "Portishead",
  year: 1994,
  genres: ["Electronic"],
  styles: ["Trip Hop"],
  thumb_url: null,
  cover_url: null,
  notes: "Prefer an early UK pressing.",
  added_at: "2026-02-01T00:00:00",
  last_synced_at: "2026-03-09T00:00:00",
  is_active: true,
  spotify_album_id: null,
  market_lowest: 32.0,
  market_median: 38.5,
  market_highest: 51.0,
  market_currency: "USD",
  market_last_updated_at: "2026-03-09T00:00:00",
  num_for_sale: 8,
  lowest_price: 32.0,
  community_have: 210,
  community_want: 87,
  rating_count: 112,
  rating_average: 4.5,
});

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
  queue: [
    {
      discogs_release_id: 2,
      artist: "Stevie Wonder",
      title: "Innervisions",
      market_need_reason: "missing",
      market_median: null,
    },
  ],
});

export const STUB_HIDDEN_GEMS = envelope({
  ok: true,
  min_median: 25,
  limit: 10,
  count: 1,
  gems: [
    {
      discogs_release_id: 2,
      artist: "Stevie Wonder",
      title: "Innervisions",
      year: 1973,
      market_median: 64.5,
      market_currency: "USD",
      num_for_sale: 1,
      gem_score: 32.25,
      reasons: ["scarce-now", "high-value"],
    },
  ],
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
