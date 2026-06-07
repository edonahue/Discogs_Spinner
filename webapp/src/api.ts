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

export interface SyncSummary {
  fetched_count: number;
  upserted_count: number;
  deactivated_count: number;
  last_sync_time: string | null;
  skipped_empty_deactivate?: boolean;
  warnings?: string[];
}

export interface ProviderReadinessCoreService {
  service_id: string;
  display_name: string;
  required: boolean;
  optional: boolean;
  configured: boolean;
  auth_required: boolean;
  auth_state: string;
  readiness: string;
  degraded_reasons: string[];
  status_message: string;
  action_label: string;
  supported_capabilities: string[];
  can_skip_setup: boolean;
  can_retry_setup: boolean;
  next_actions: string[];
  setup_url?: string | null;
}

export interface ProviderReadinessProvider {
  provider_id: string;
  display_name: string;
  required: boolean;
  optional: boolean;
  listed: boolean;
  enabled: boolean;
  installed: boolean;
  addon_available: boolean;
  configured: boolean;
  auth_required: boolean;
  auth_state: string;
  readiness: string;
  degraded_reasons: string[];
  status_message: string;
  action_label: string;
  supported_capabilities: string[];
  can_skip_setup: boolean;
  can_retry_setup: boolean;
  next_actions: string[];
  docs_url?: string | null;
  setup_url?: string | null;
  oauth_guide_url?: string | null;
  experimental: boolean;
  experimental_flag?: string | null;
}

export interface ProviderReadinessSummary {
  required_services_configured: boolean;
  optional_provider_count: number;
  ready_provider_count: number;
  degraded_mode: boolean;
  onboarding_state: string;
  collection_synced: boolean | null;
  next_actions: string[];
  can_skip_optional_setup: boolean;
}

export interface ProviderReadinessContract {
  schema_version: number;
  core_service: ProviderReadinessCoreService;
  providers: ProviderReadinessProvider[];
  next_actions: string[];
  summary: ProviderReadinessSummary;
}

const DEFAULT_BASE_URL = "http://127.0.0.1:8768/api/v1";

export function apiBaseUrl(): string {
  const envValue = import.meta.env.VITE_API_BASE_URL;
  if (typeof envValue === "string" && envValue.trim().length > 0) {
    return envValue.trim().replace(/\/$/, "");
  }
  return DEFAULT_BASE_URL;
}

type RequestOptions = {
  signal?: AbortSignal;
};

export async function getJson<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiEnvelope<T>> {
  const url = `${apiBaseUrl()}${path}`;
  const response = await fetch(url, {
    method: "GET",
    signal: options.signal,
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

export async function postJson<T>(
  path: string,
  body: unknown,
  options: RequestOptions = {},
): Promise<ApiEnvelope<T>> {
  const url = `${apiBaseUrl()}${path}`;
  const response = await fetch(url, {
    method: "POST",
    signal: options.signal,
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

export interface ReleaseCollectionSummary {
  release_count: number;
  lp_count: number;
  rpm45_count: number;
  format_counts_ready: boolean;
  priced_release_count: number;
  total_median: number | null;
  median_currency: string | null;
  mixed_currencies: boolean;
  most_recent_added_at: string | null;
  most_recent_release_id: number | null;
  most_recent_release_artist: string | null;
  most_recent_release_title: string | null;
}

export interface ReleaseDetail {
  discogs_release_id: number;
  title: string;
  artist: string;
  year: string | number | null;
  genres: string[];
  styles: string[];
  thumb_url: string | null;
  cover_url: string | null;
  added_at: string | null;
  last_synced_at: string | null;
  is_active: boolean;
  spotify_album_id: string | null;
  notes?: string | null;
  market_lowest?: number | null;
  market_median?: number | null;
  market_highest?: number | null;
  market_currency?: string | null;
  market_last_updated_at?: string | null;
  num_for_sale?: number | null;
  lowest_price?: number | null;
  community_have?: number | null;
  community_want?: number | null;
  rating_count?: number | null;
  rating_average?: number | null;
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

export function fetchReleases(
  filters: ReleaseFilters,
  options: RequestOptions = {},
): Promise<ApiEnvelope<Release[]>> {
  return getJson<Release[]>(`/releases?${buildReleaseParams(filters).toString()}`, options);
}

export function fetchReleaseSummary(
  filters: ReleaseFilters,
  options: RequestOptions = {},
): Promise<ApiEnvelope<ReleaseCollectionSummary>> {
  return getJson<ReleaseCollectionSummary>(
    `/releases/summary?${buildReleaseParams(filters).toString()}`,
    options,
  );
}

export function fetchWantlist(
  filters: ReleaseFilters,
  options: RequestOptions = {},
): Promise<ApiEnvelope<Release[]>> {
  return getJson<Release[]>(`/wantlist?${buildReleaseParams(filters).toString()}`, options);
}

export function fetchReleaseDetail(
  releaseId: number,
  params?: { withValue?: boolean },
): Promise<ApiEnvelope<ReleaseDetail>> {
  const qs = new URLSearchParams();
  if (params?.withValue) qs.set("with_value", "true");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return getJson<ReleaseDetail>(`/releases/${releaseId}${suffix}`);
}

export function fetchWantlistDetail(
  releaseId: number,
  params?: { withValue?: boolean },
): Promise<ApiEnvelope<ReleaseDetail>> {
  const qs = new URLSearchParams();
  if (params?.withValue) qs.set("with_value", "true");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return getJson<ReleaseDetail>(`/wantlist/${releaseId}${suffix}`);
}

export function syncCollection(): Promise<ApiEnvelope<SyncSummary>> {
  return postJson<SyncSummary>("/sync/collection", {});
}

export function syncWantlist(): Promise<ApiEnvelope<SyncSummary>> {
  return postJson<SyncSummary>("/sync/wantlist", {});
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

export function fetchValueDashboard(
  params?: { top_limit?: number },
  options: RequestOptions = {},
): Promise<ApiEnvelope<ValueDashboard>> {
  const qs = params?.top_limit !== undefined ? `?top_limit=${params.top_limit}` : "";
  return getJson<ValueDashboard>(`/value/dashboard${qs}`, options);
}

export interface QueueItem {
  discogs_release_id: number;
  artist: string;
  title: string;
  market_need_reason: "missing" | "unpriced" | "stale";
  market_median: number | null;
}
export interface ValueRefreshQueue {
  total_candidates: number;
  missing_count: number;
  unpriced_count: number;
  stale_count: number;
  stale_days: number;
  limit: number;
  queue: QueueItem[];
}
export interface HealthBucket {
  name: string;
  label: string;
  gap_count: number;
  gap_pct: number;
  max_deduction: number;
  deduction: number;
}
export interface CollectionHealth {
  score: number;
  total_active: number;
  buckets: HealthBucket[];
}

export function fetchValueQueue(params?: {
  limit?: number;
  stale_days?: number;
}, options: RequestOptions = {}): Promise<ApiEnvelope<ValueRefreshQueue>> {
  const qs = new URLSearchParams();
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.stale_days != null) qs.set("stale_days", String(params.stale_days));
  const q = qs.toString() ? `?${qs.toString()}` : "";
  return getJson<ValueRefreshQueue>(`/value/queue${q}`, options);
}

export function fetchCollectionHealth(): Promise<ApiEnvelope<CollectionHealth>> {
  return getJson<CollectionHealth>("/value/health");
}

export interface HiddenGem {
  discogs_release_id: number;
  artist: string | null;
  title: string | null;
  year: number | null;
  market_median: number | null;
  market_currency: string | null;
  num_for_sale: number | null;
  community_have: number | null;
  community_want: number | null;
  gem_score: number;
  reasons: string[];
}

export interface HiddenGemsPayload {
  ok: boolean;
  min_median: number;
  limit: number;
  count: number;
  gems: HiddenGem[];
}

export function fetchHiddenGems(params?: {
  min_median?: number;
  limit?: number;
}, options: RequestOptions = {}): Promise<ApiEnvelope<HiddenGemsPayload>> {
  const qs = new URLSearchParams();
  if (params?.min_median != null) qs.set("min_median", String(params.min_median));
  if (params?.limit != null) qs.set("limit", String(params.limit));
  const q = qs.toString() ? `?${qs.toString()}` : "";
  return getJson<HiddenGemsPayload>(`/value/gems${q}`, options);
}

export interface RecentReleasesPayload {
  ok: boolean;
  releases: Release[];
  count: number;
  days: number;
  limit: number | null;
}

export function fetchRecentReleases(params?: {
  days?: number;
  limit?: number;
}): Promise<ApiEnvelope<RecentReleasesPayload>> {
  const qs = new URLSearchParams();
  if (params?.days != null) qs.set("days", String(params.days));
  if (params?.limit != null) qs.set("limit", String(params.limit));
  const q = qs.toString() ? `?${qs.toString()}` : "";
  return getJson<RecentReleasesPayload>(`/releases/recent${q}`);
}

export interface AnalyticsYearRow {
  year: number;
  count: number;
}
export interface AnalyticsGenreRow { genre: string; count: number; }
export interface AnalyticsStyleRow { style: string; count: number; }
export interface AnalyticsArtistRow { artist: string; count: number; }

export interface CollectionAnalytics {
  release_count_active: number;
  mapped_count: number;
  unmatched_count: number;
  top_limit: number;
  by_release_year: AnalyticsYearRow[];
  acquisition_timeline: AnalyticsYearRow[];
  top_genres: AnalyticsGenreRow[];
  top_styles: AnalyticsStyleRow[];
  top_artists: AnalyticsArtistRow[];
}

export function fetchAnalytics(params?: {
  limit?: number;
}): Promise<ApiEnvelope<CollectionAnalytics>> {
  const qs = params?.limit != null ? `?limit=${params.limit}` : "";
  return getJson<CollectionAnalytics>(`/analytics${qs}`);
}

export interface CollectorInsightHighlight {
  kind: string;
  title: string;
  message: string;
  command_hint?: string;
  release_id?: number;
}

export interface CollectorInsightGem {
  discogs_release_id: number | null;
  artist: string | null;
  title: string | null;
  year: number | null;
  market_median: number | null;
  market_currency: string | null;
  num_for_sale: number | null;
  gem_score: number | null;
  reasons: string[];
}

export interface CollectorInsightsPayload {
  summary: {
    release_count_active: number;
    mapped_count: number;
    unmatched_count: number;
    wantlist_count: number;
    market_value_last_updated: string | null;
    last_sync_time: string | null;
    last_spin_release_id: number | null;
    onboarding_state: string;
    degraded_mode: boolean;
    health_score: number;
    hidden_gems_count: number;
    refresh_queue_count: number;
    ready_for_daily_use: boolean;
  };
  highlights: CollectorInsightHighlight[];
  daily_use_actions: string[];
  top_hidden_gems: CollectorInsightGem[];
}

export function fetchCollectorInsights(params?: {
  gems_limit?: number;
  queue_limit?: number;
  min_median?: number;
}, options: RequestOptions = {}): Promise<ApiEnvelope<CollectorInsightsPayload>> {
  const qs = new URLSearchParams();
  if (params?.gems_limit != null) qs.set("gems_limit", String(params.gems_limit));
  if (params?.queue_limit != null) qs.set("queue_limit", String(params.queue_limit));
  if (params?.min_median != null) qs.set("min_median", String(params.min_median));
  const q = qs.toString() ? `?${qs.toString()}` : "";
  return getJson<CollectorInsightsPayload>(`/insights${q}`, options);
}

export interface Track {
  position: string;
  title: string;
  duration: string;
  type_: string;
}

export interface TracklistPayload {
  discogs_release_id: number;
  title: string;
  artist: string;
  has_cached_tracklist: boolean;
  has_tracklist: boolean;
  tracks: Track[];
  track_count: number;
  audio_track_count: number;
  tracklist_last_refreshed_at: string | null;
}

export function fetchTracklist(
  releaseId: number,
): Promise<ApiEnvelope<TracklistPayload>> {
  return getJson<TracklistPayload>(`/releases/${releaseId}/tracklist`);
}
