from __future__ import annotations

import pytest

from discogs_player.use_cases.config_management import (
    run_config_set,
    run_config_show,
    run_config_unset,
)


def test_config_show_set_unset_round_trip(isolated_xdg):
    assert run_config_show() == {}

    set_result = run_config_set("spotify_client_id", "abc123")
    assert set_result == {"key": "spotify_client_id", "value": "abc123"}
    assert run_config_show() == {"spotify_client_id": "abc123"}

    unset_result = run_config_unset("spotify_client_id")
    assert unset_result == {"key": "spotify_client_id", "removed": True}
    assert run_config_show() == {}


def test_config_unset_reports_missing_key(isolated_xdg):
    result = run_config_unset("not_set")
    assert result == {"key": "not_set", "removed": False}


def test_config_key_validation(isolated_xdg):
    with pytest.raises(ValueError):
        run_config_set("", "value")

    with pytest.raises(ValueError):
        run_config_set("bad key", "value")

    with pytest.raises(ValueError):
        run_config_unset(" ")
