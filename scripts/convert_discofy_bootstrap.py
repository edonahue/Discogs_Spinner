#!/usr/bin/env python3
"""Convert Discofy/direct mapping exports into canonical direct bootstrap format."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from discogs_player.use_cases.bootstrap_import import extract_bootstrap_mappings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert external Discogs->Spotify mappings into direct bootstrap schema."
        )
    )
    parser.add_argument("--input", "-i", required=True, help="Input JSON/CSV path")
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output path for converted direct schema",
    )
    parser.add_argument(
        "--format",
        choices=("discofy", "direct", "auto", "discogs-to-spotify", "discogs_to_spotify"),
        default="discofy",
        help=(
            "Input format parser (default: discofy). "
            "Discogs-to-Spotify exports can use --format discogs-to-spotify."
        ),
    )
    parser.add_argument(
        "--output-format",
        choices=("json", "csv"),
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--fail-on-invalid",
        action="store_true",
        help="Exit non-zero if any invalid rows are detected",
    )
    return parser


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "discogs_release_id",
                "spotify_album_id",
                "confidence",
                "is_override",
            ),
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "discogs_release_id": row.get("discogs_release_id"),
                    "spotify_album_id": row.get("spotify_album_id"),
                    "confidence": row.get("confidence"),
                    "is_override": row.get("is_override"),
                }
            )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        result = extract_bootstrap_mappings(
            input_path=args.input,
            source_format=args.format,
        )
    except (ValueError, OSError) as exc:
        print(f"Conversion failed: {exc}", file=sys.stderr)
        return 2

    mappings_raw = result.get("mappings")
    mappings = mappings_raw if isinstance(mappings_raw, list) else []
    invalid_count = int(result.get("invalid_row_count") or 0)
    duplicate_count = int(result.get("duplicate_row_count") or 0)

    payload = {
        "schema": "discogs_spotify_bootstrap/v1",
        "input_path": str(result.get("input_path") or ""),
        "input_kind": str(result.get("input_kind") or ""),
        "source_format_requested": str(result.get("source_format_requested") or ""),
        "source_format_used": str(result.get("source_format_used") or ""),
        "mapping_count": len(mappings),
        "invalid_row_count": invalid_count,
        "duplicate_row_count": duplicate_count,
        "mappings": mappings,
    }

    output_path = Path(args.output).expanduser()
    try:
        if args.output_format == "json":
            _write_json(output_path, payload)
        else:
            _write_csv(output_path, mappings)
    except OSError as exc:
        print(f"Failed to write output: {exc}", file=sys.stderr)
        return 4

    print(
        f"converted={len(mappings)} invalid={invalid_count} "
        f"duplicates={duplicate_count} output={output_path}"
    )

    if args.fail_on_invalid and invalid_count > 0:
        print("Conversion completed but invalid rows were found.", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
