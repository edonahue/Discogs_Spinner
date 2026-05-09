from __future__ import annotations

import json
from pathlib import Path

from tests.provider_readiness_examples import build_provider_readiness_examples


def test_readiness_example_missing_discogs_token():
    contract = build_provider_readiness_examples()["missing_discogs_token"]
    assert contract["summary"]["onboarding_state"] == "needs_required_setup"
    assert contract["core_service"]["required"] is True
    assert contract["core_service"]["configured"] is False
    assert contract["summary"]["required_services_configured"] is False


def test_readiness_example_discogs_configured_needs_initial_sync():
    contract = build_provider_readiness_examples()[
        "discogs_configured_needs_initial_sync"
    ]
    assert contract["summary"]["required_services_configured"] is True
    assert contract["summary"]["collection_synced"] is False
    assert contract["summary"]["onboarding_state"] == "needs_initial_sync"


def test_readiness_example_discogs_ready_optional_skipped():
    contract = build_provider_readiness_examples()["discogs_ready_optional_skipped"]
    assert contract["summary"]["required_services_configured"] is True
    assert contract["summary"]["optional_provider_count"] == 0
    assert contract["summary"]["ready_provider_count"] == 0
    assert contract["summary"]["onboarding_state"] == "ready"
    assert contract["summary"]["degraded_mode"] is False


def test_readiness_example_spotify_ready():
    contract = build_provider_readiness_examples()["spotify_ready"]
    assert contract["summary"]["onboarding_state"] == "ready"
    assert contract["summary"]["ready_provider_count"] == 1
    assert contract["providers"][0]["provider_id"] == "spotify"
    assert contract["providers"][0]["readiness"] == "ready"


def test_readiness_example_experimental_provider_disabled():
    contract = build_provider_readiness_examples()["experimental_youtube_music_disabled"]
    provider = contract["providers"][0]
    assert provider["provider_id"] == "youtube_music"
    assert provider["readiness"] == "unavailable"
    assert "disabled" in provider["degraded_reasons"]


def test_readiness_example_provider_unavailable():
    contract = build_provider_readiness_examples()["provider_unavailable"]
    provider = contract["providers"][0]
    assert provider["provider_id"] == "alt_provider"
    assert provider["readiness"] == "unavailable"
    assert "backend_not_installed" in provider["degraded_reasons"]


def test_readiness_example_provider_unauthenticated():
    contract = build_provider_readiness_examples()["provider_unauthenticated"]
    provider = contract["providers"][0]
    assert provider["provider_id"] == "spotify"
    assert provider["readiness"] == "degraded"
    assert provider["auth_state"] == "unauthenticated"
    assert "unauthenticated" in provider["degraded_reasons"]


def test_readiness_example_degraded_mode():
    contract = build_provider_readiness_examples()["degraded_mode_optional_pending"]
    assert contract["summary"]["required_services_configured"] is True
    assert contract["summary"]["degraded_mode"] is True
    assert contract["summary"]["onboarding_state"] == "core_ready_optional_pending"
    assert contract["summary"]["ready_provider_count"] == 0


def test_provider_readiness_examples_doc_payload_matches_generated_contracts():
    docs_path = (
        Path(__file__).parent.parent
        / "docs"
        / "api"
        / "provider_readiness_examples.json"
    )
    docs_examples = json.loads(docs_path.read_text())
    assert docs_examples == build_provider_readiness_examples()

