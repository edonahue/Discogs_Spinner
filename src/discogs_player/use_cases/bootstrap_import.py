"""Import Discogs->Spotify mappings from external bootstrap sources."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from discogs_player.data.db import get_connection
from discogs_player.data.repo import get_release_counts, upsert_spotify_mapping
from discogs_player.use_cases._coerce import (
    to_optional_bool as _to_optional_bool,
    to_optional_float as _to_optional_float,
    to_optional_int as _to_optional_int,
    to_optional_str as _to_optional_str,
)

VALID_SOURCE_FORMATS = {
    "auto",
    "discofy",
    "direct",
    "discogs-to-spotify",
    "discogs_to_spotify",
}
_SOURCE_FORMAT_ALIASES = {
    "auto": "auto",
    "direct": "direct",
    "discofy": "discofy",
    # Public project alias: https://github.com/gregisb/Discogs-to-Spotify
    "discogs-to-spotify": "discofy",
    "discogs_to_spotify": "discofy",
}
VALID_CONFLICT_MODES = {"merge", "replace"}
_DISCOGS_ID_KEYS = ("discogs_release_id", "discogs_id", "release_id")
_SPOTIFY_ID_KEYS = (
    "spotify_album_id",
    "spotify_id",
    "spotify_album_uri",
    "spotify_uri",
    "spotify_url",
    "album_uri",
    "album_url",
    "uri",
    "url",
)


@dataclass(frozen=True)
class BootstrapMapping:
    discogs_release_id: int
    spotify_album_id: str
    confidence: float | None
    is_override: bool | None


@dataclass(frozen=True)
class _ParseResult:
    source_format: str
    mappings: list[BootstrapMapping]
    invalid_rows: int
    duplicate_rows: int


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_source_format(raw: str) -> str:
    value = raw.strip().lower()
    if value not in VALID_SOURCE_FORMATS:
        raise ValueError(
            "Source format must be one of: auto, discofy, direct, "
            "discogs-to-spotify."
        )
    return _SOURCE_FORMAT_ALIASES.get(value, value)


def _normalize_conflict_mode(raw: str) -> str:
    value = raw.strip().lower()
    if value not in VALID_CONFLICT_MODES:
        raise ValueError("Conflict mode must be 'merge' or 'replace'.")
    return value


def _parse_discogs_id_from_url(value: str) -> int | None:
    match = re.search(r"discogs\.com/(?:[^/]+/)?release/(\d+)", value, flags=re.I)
    if not match:
        return None
    return int(match.group(1))


def _extract_discogs_release_id(record: dict[str, Any]) -> int | None:
    for key in _DISCOGS_ID_KEYS:
        if key in record:
            release_id = _to_optional_int(record.get(key))
            if release_id is not None and release_id > 0:
                return release_id

    for key in ("discogs_release_url", "discogs_url", "release_url"):
        value = _to_optional_str(record.get(key))
        if not value:
            continue
        release_id = _parse_discogs_id_from_url(value)
        if release_id is not None:
            return release_id

    discogs_obj = record.get("discogs")
    if isinstance(discogs_obj, dict):
        return _extract_discogs_release_id(discogs_obj)

    release_obj = record.get("release")
    if isinstance(release_obj, dict):
        return _extract_discogs_release_id(release_obj)

    return None


def _normalize_spotify_album_id(value: Any) -> str | None:
    text = _to_optional_str(value)
    if not text:
        return None

    if text.startswith("spotify:album:"):
        album = text.removeprefix("spotify:album:").strip()
    elif text.startswith("spotify:"):
        # Track/playlist/artist URIs are not usable for album mapping bootstrap.
        return None
    else:
        album = text
        url_match = re.search(
            r"(?:https?://)?open\.spotify\.com/album/([A-Za-z0-9]+)",
            text,
            flags=re.I,
        )
        if url_match:
            album = url_match.group(1)

    album = album.split("?", 1)[0].strip().strip("/")
    if "/" in album:
        album = album.rsplit("/", 1)[-1]
    if not album:
        return None
    if not re.fullmatch(r"[A-Za-z0-9]+", album):
        return None
    return album


def _extract_spotify_album_id(record: dict[str, Any]) -> str | None:
    for key in _SPOTIFY_ID_KEYS:
        if key not in record:
            continue
        album_id = _normalize_spotify_album_id(record.get(key))
        if album_id:
            return album_id

    spotify_obj = record.get("spotify")
    if isinstance(spotify_obj, dict):
        nested = _extract_spotify_album_id(spotify_obj)
        if nested:
            return nested

    album_obj = record.get("album")
    if isinstance(album_obj, dict):
        nested = _extract_spotify_album_id(album_obj)
        if nested:
            return nested

    spotify_album_obj = record.get("spotify_album")
    if isinstance(spotify_album_obj, dict):
        nested = _extract_spotify_album_id(spotify_album_obj)
        if nested:
            return nested

    return None


def _extract_confidence(record: dict[str, Any]) -> float | None:
    for key in ("confidence", "spotify_confidence", "match_confidence"):
        value = _to_optional_float(record.get(key))
        if value is not None:
            return value

    spotify_obj = record.get("spotify")
    if isinstance(spotify_obj, dict):
        nested = _extract_confidence(spotify_obj)
        if nested is not None:
            return nested

    return None


def _extract_is_override(record: dict[str, Any]) -> bool | None:
    for key in ("is_override", "spotify_is_override", "override"):
        value = _to_optional_bool(record.get(key))
        if value is not None:
            return value
    return None


def _dedupe_mappings(
    mappings: list[BootstrapMapping],
) -> tuple[list[BootstrapMapping], int]:
    by_release: dict[int, BootstrapMapping] = {}
    duplicates = 0
    for mapping in mappings:
        existing = by_release.get(mapping.discogs_release_id)
        if existing is None:
            by_release[mapping.discogs_release_id] = mapping
            continue
        duplicates += 1
        existing_conf = existing.confidence if existing.confidence is not None else -1.0
        current_conf = mapping.confidence if mapping.confidence is not None else -1.0
        if current_conf >= existing_conf:
            by_release[mapping.discogs_release_id] = mapping
    return list(by_release.values()), duplicates


def _iter_dict_nodes(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _iter_dict_nodes(child)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_dict_nodes(item)


def _looks_like_mapping_node(record: dict[str, Any]) -> bool:
    discogs_hints = {
        *_DISCOGS_ID_KEYS,
        "discogs",
        "discogs_release_url",
        "discogs_url",
        "release_url",
    }
    spotify_hints = {
        *_SPOTIFY_ID_KEYS,
        "spotify",
        "spotify_album",
        "album",
    }
    keys = set(record.keys())
    return bool(keys & discogs_hints) and bool(keys & spotify_hints)


def _parse_discofy_payload(payload: Any) -> _ParseResult:
    mappings: list[BootstrapMapping] = []
    invalid_rows = 0
    for node in _iter_dict_nodes(payload):
        release_id = _extract_discogs_release_id(node)
        if release_id is None:
            continue
        album_id = _extract_spotify_album_id(node)
        if not album_id:
            if _looks_like_mapping_node(node):
                invalid_rows += 1
            continue
        mappings.append(
            BootstrapMapping(
                discogs_release_id=release_id,
                spotify_album_id=album_id,
                confidence=_extract_confidence(node),
                is_override=_extract_is_override(node),
            )
        )

    unique, duplicates = _dedupe_mappings(mappings)
    return _ParseResult(
        source_format="discofy",
        mappings=sorted(unique, key=lambda row: row.discogs_release_id),
        invalid_rows=invalid_rows,
        duplicate_rows=duplicates,
    )


def _coerce_direct_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        candidate_keys = ("mappings", "releases", "items", "records")
        selected = None
        for key in candidate_keys:
            if isinstance(payload.get(key), list):
                selected = payload.get(key)
                break
        records = selected if selected is not None else [payload]
    else:
        raise ValueError("Direct bootstrap payload must be a JSON object or array.")

    normalized: list[dict[str, Any]] = []
    for item in records:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized


def _parse_direct_rows(rows: list[dict[str, Any]]) -> _ParseResult:
    mappings: list[BootstrapMapping] = []
    invalid_rows = 0
    for row in rows:
        release_id = _extract_discogs_release_id(row)
        album_id = _extract_spotify_album_id(row)
        if release_id is None or not album_id:
            invalid_rows += 1
            continue
        mappings.append(
            BootstrapMapping(
                discogs_release_id=release_id,
                spotify_album_id=album_id,
                confidence=_extract_confidence(row),
                is_override=_extract_is_override(row),
            )
        )

    unique, duplicates = _dedupe_mappings(mappings)
    return _ParseResult(
        source_format="direct",
        mappings=sorted(unique, key=lambda row: row.discogs_release_id),
        invalid_rows=invalid_rows,
        duplicate_rows=duplicates,
    )


def _parse_json_payload(
    payload: Any,
    *,
    source_format: str,
) -> _ParseResult:
    if source_format == "discofy":
        return _parse_discofy_payload(payload)
    if source_format == "direct":
        return _parse_direct_rows(_coerce_direct_records(payload))

    if source_format == "auto":
        discofy = _parse_discofy_payload(payload)
        direct = _parse_direct_rows(_coerce_direct_records(payload))
        if len(discofy.mappings) >= len(direct.mappings):
            return discofy
        return direct

    raise ValueError("Unsupported source format.")


def _load_input(path: Path) -> tuple[str, Any]:
    if not path.exists():
        raise ValueError(f"Input path does not exist: {path}")
    if path.is_dir():
        raise ValueError(f"Input path is a directory: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return "csv", [dict(row) for row in reader]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Import file is not valid JSON: {exc}") from exc
    return "json", payload


def extract_bootstrap_mappings(
    *,
    input_path: str,
    source_format: str = "auto",
) -> dict[str, object]:
    format_normalized = _normalize_source_format(source_format)
    path = Path(input_path).expanduser()
    input_kind, payload = _load_input(path)

    if input_kind == "csv":
        if format_normalized == "discofy":
            raise ValueError("Discofy bootstrap import expects JSON input.")
        parsed = _parse_direct_rows(payload)
    else:
        parsed = _parse_json_payload(payload, source_format=format_normalized)

    rows = [
        {
            "discogs_release_id": int(item.discogs_release_id),
            "spotify_album_id": str(item.spotify_album_id),
            "confidence": item.confidence,
            "is_override": item.is_override,
        }
        for item in parsed.mappings
    ]
    return {
        "input_path": str(path),
        "input_kind": input_kind,
        "source_format_requested": format_normalized,
        "source_format_used": parsed.source_format,
        "mappings": rows,
        "invalid_row_count": int(parsed.invalid_rows),
        "duplicate_row_count": int(parsed.duplicate_rows),
    }


def run_bootstrap_mapping_import(
    *,
    input_path: str,
    source_format: str = "auto",
    conflict_mode: str = "merge",
    dry_run: bool = False,
    default_confidence: float = 0.85,
    mark_override: bool = False,
    skip_missing_releases: bool = True,
) -> dict[str, object]:
    mode = _normalize_conflict_mode(conflict_mode)
    if default_confidence < 0.0 or default_confidence > 1.0:
        raise ValueError("Default confidence must be between 0.0 and 1.0.")

    extracted = extract_bootstrap_mappings(
        input_path=input_path,
        source_format=source_format,
    )
    path = Path(str(extracted["input_path"]))
    input_kind = str(extracted["input_kind"])
    source_format_requested = str(extracted["source_format_requested"])
    source_format_used = str(extracted["source_format_used"])
    parsed_rows_raw = extracted.get("mappings")
    parsed_rows = parsed_rows_raw if isinstance(parsed_rows_raw, list) else []
    invalid_row_count = _to_optional_int(extracted.get("invalid_row_count")) or 0
    duplicate_row_count = _to_optional_int(extracted.get("duplicate_row_count")) or 0

    if not parsed_rows:
        raise ValueError(
            "No bootstrap mappings found. Use --format direct with a file containing "
            "discogs_release_id + spotify_album_id (or Spotify album URI/URL)."
        )

    conn = get_connection()
    try:
        pre_counts = get_release_counts(conn)
        pre_mapping_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM spotify_mapping WHERE spotify_album_id IS NOT NULL AND spotify_album_id <> ''"
            ).fetchone()[0]
        )
        existing_release_ids = {
            int(row[0]) for row in conn.execute("SELECT discogs_release_id FROM releases")
        }
        existing_rows = conn.execute(
            """
            SELECT discogs_release_id, spotify_album_id, is_override
            FROM spotify_mapping
            """
        ).fetchall()
        existing_mappings = {
            int(row["discogs_release_id"]): {
                "spotify_album_id": str(row["spotify_album_id"] or "").strip(),
                "is_override": bool(row["is_override"]),
            }
            for row in existing_rows
        }

        if not dry_run and mode == "replace":
            conn.execute("DELETE FROM spotify_mapping")
            conn.commit()
            existing_mappings.clear()

        imported = 0
        skipped_missing = 0
        skipped_existing = 0
        skipped_override = 0
        preview: list[dict[str, object]] = []

        for row in parsed_rows:
            if not isinstance(row, dict):
                continue
            release_id = int(row["discogs_release_id"])
            if skip_missing_releases and release_id not in existing_release_ids:
                skipped_missing += 1
                continue

            existing = existing_mappings.get(release_id)
            if mode == "merge" and existing:
                if bool(existing.get("is_override")):
                    skipped_override += 1
                    continue
                if str(existing.get("spotify_album_id") or "").strip():
                    skipped_existing += 1
                    continue

            confidence = _to_optional_float(row.get("confidence"))
            if confidence is None:
                confidence = default_confidence
            is_override = _to_optional_bool(row.get("is_override"))
            if is_override is None:
                is_override = mark_override

            spotify_album_id = str(row["spotify_album_id"]).strip()
            if not dry_run:
                upsert_spotify_mapping(
                    conn,
                    discogs_release_id=release_id,
                    spotify_album_id=spotify_album_id,
                    confidence=confidence,
                    last_checked_at=_now_iso(),
                    is_override=bool(is_override),
                )
                existing_mappings[release_id] = {
                    "spotify_album_id": spotify_album_id,
                    "is_override": bool(is_override),
                }

            imported += 1
            if len(preview) < 20:
                preview.append(
                    {
                        "discogs_release_id": release_id,
                        "spotify_album_id": spotify_album_id,
                        "confidence": confidence,
                        "is_override": bool(is_override),
                    }
                )
    finally:
        conn.close()

    return {
        "ok": True,
        "input_path": str(path),
        "input_kind": input_kind,
        "source_format_requested": source_format_requested,
        "source_format_used": source_format_used,
        "conflict_mode": mode,
        "dry_run": dry_run,
        "default_confidence": float(default_confidence),
        "mark_override": mark_override,
        "skip_missing_releases": skip_missing_releases,
        "parsed_mapping_count": len(parsed_rows),
        "invalid_row_count": invalid_row_count,
        "duplicate_row_count": duplicate_row_count,
        "imported_mapping_count": imported,
        "skipped_missing_release_count": skipped_missing,
        "skipped_existing_mapping_count": skipped_existing,
        "skipped_override_mapping_count": skipped_override,
        "pre_import_release_count_total": int(pre_counts["release_count_total"]),
        "pre_import_release_count_active": int(pre_counts["release_count_active"]),
        "pre_import_mapped_count": int(pre_counts["mapped_count"]),
        "pre_import_mapping_row_count": pre_mapping_count,
        "preview": preview,
    }
