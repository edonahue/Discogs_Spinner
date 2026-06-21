import { Release, SyncSummary } from "../api";

export type SortKey = "artist_asc" | "artist_desc" | "title_asc" | "year_desc" | "year_asc" | "value_desc";

export const PILL_STYLE: React.CSSProperties = {
  display: "inline-flex",
};

export function sortReleases(releases: Release[], sortKey: SortKey): Release[] {
  return [...releases].sort((a, b) => {
    switch (sortKey) {
      case "artist_asc": return a.artist.localeCompare(b.artist);
      case "artist_desc": return b.artist.localeCompare(a.artist);
      case "title_asc": return a.title.localeCompare(b.title);
      case "year_desc": return (Number(b.year) || 0) - (Number(a.year) || 0);
      case "year_asc": return (Number(a.year) || 0) - (Number(b.year) || 0);
      case "value_desc": return (b.value?.price_median ?? 0) - (a.value?.price_median ?? 0);
    }
  });
}

export function parseFocusId(raw: string | null): number | null {
  if (!raw) return null;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function formatSyncSummary(summary: SyncSummary, label: string = "Collection"): string {
  return (
    `${label} sync complete: fetched ${summary.fetched_count}, `
    + `upserted ${summary.upserted_count}, deactivated ${summary.deactivated_count}.`
  );
}
