from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_discofy_converter_script_contains_expected_options():
    source = _script_text("scripts/convert_discofy_bootstrap.py")
    for marker in (
        "--format",
        "--output-format",
        "--fail-on-invalid",
        "discogs_spotify_bootstrap/v1",
        "extract_bootstrap_mappings",
        "discogs-to-spotify",
    ):
        assert marker in source


def test_discofy_converter_script_converts_to_direct_json(tmp_path):
    input_path = tmp_path / "discofy.json"
    output_path = tmp_path / "bootstrap.json"
    input_payload = {
        "transfer_collection_status": {
            "results": [
                {
                    "discogs": {"release_id": 10},
                    "spotify": {"spotify_album_uri": "spotify:album:AAA10"},
                },
                {
                    "discogs_id": 11,
                    "spotify_uri": "https://open.spotify.com/album/BBB11?si=123",
                    "confidence": 0.91,
                },
            ]
        }
    }
    input_path.write_text(json.dumps(input_payload), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "convert_discofy_bootstrap.py"),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "discofy",
            "--output-format",
            "json",
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "discogs_spotify_bootstrap/v1"
    assert payload["source_format_used"] == "discofy"
    assert payload["mapping_count"] == 2
    assert payload["mappings"] == [
        {
            "discogs_release_id": 10,
            "spotify_album_id": "AAA10",
            "confidence": None,
            "is_override": None,
        },
        {
            "discogs_release_id": 11,
            "spotify_album_id": "BBB11",
            "confidence": 0.91,
            "is_override": None,
        },
    ]


def test_discofy_converter_script_direct_csv_output(tmp_path):
    input_path = tmp_path / "direct.json"
    output_path = tmp_path / "direct.csv"
    input_payload = {
        "mappings": [
            {
                "discogs_release_id": "12",
                "spotify_album_id": "spotify:album:CCC12",
                "confidence": "0.8",
                "is_override": "true",
            }
        ]
    }
    input_path.write_text(json.dumps(input_payload), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "convert_discofy_bootstrap.py"),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "direct",
            "--output-format",
            "csv",
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode == 0
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {
            "discogs_release_id": "12",
            "spotify_album_id": "CCC12",
            "confidence": "0.8",
            "is_override": "True",
        }
    ]


def test_discofy_converter_accepts_discogs_to_spotify_format_alias(tmp_path):
    input_path = tmp_path / "discogs_to_spotify.json"
    output_path = tmp_path / "bootstrap.json"
    input_payload = {
        "transfer_collection_status": {
            "results": [
                {
                    "discogs": {"release_id": 77},
                    "spotify": {"spotify_album_uri": "spotify:album:DDD77"},
                }
            ]
        }
    }
    input_path.write_text(json.dumps(input_payload), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "convert_discofy_bootstrap.py"),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "discogs-to-spotify",
            "--output-format",
            "json",
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert completed.returncode == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["mapping_count"] == 1
    assert payload["mappings"][0]["discogs_release_id"] == 77
    assert payload["mappings"][0]["spotify_album_id"] == "DDD77"
