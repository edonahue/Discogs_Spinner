"""Source-level assertions for the preferences window module."""

from __future__ import annotations

from pathlib import Path

_PREFS_SOURCE = (
    Path(__file__).parent.parent
    / "src"
    / "discogs_player"
    / "ui"
    / "dialogs"
    / "preferences_window.py"
).read_text()


def test_preferences_file_exists():
    path = (
        Path(__file__).parent.parent
        / "src"
        / "discogs_player"
        / "ui"
        / "dialogs"
        / "preferences_window.py"
    )
    assert path.exists(), "preferences_window.py must exist"


def test_preferences_inherits_adw_preferences_window():
    assert "Adw.PreferencesWindow" in _PREFS_SOURCE, (
        "PreferencesWindow must subclass Adw.PreferencesWindow"
    )


def test_preferences_uses_password_entry_row():
    assert "PasswordEntryRow" in _PREFS_SOURCE, (
        "Discogs group must use Adw.PasswordEntryRow for token input"
    )


def test_preferences_calls_run_config_set_on_token_save():
    assert "run_config_set" in _PREFS_SOURCE, (
        "Token save path must call run_config_set"
    )


def test_preferences_reads_capabilities():
    assert "get_capabilities" in _PREFS_SOURCE, (
        "PreferencesWindow must read capabilities for Spotify status"
    )


def test_preferences_has_discogs_group():
    assert "Discogs" in _PREFS_SOURCE, (
        "PreferencesWindow must have a Discogs preferences group"
    )


def test_preferences_has_spotify_group():
    assert "Spotify" in _PREFS_SOURCE, (
        "PreferencesWindow must have a Spotify preferences group"
    )


def test_preferences_shows_toast_on_save():
    assert "Adw.Toast" in _PREFS_SOURCE, (
        "PreferencesWindow must show an Adw.Toast when token is saved"
    )


def test_preferences_has_disconnect_option():
    assert "run_config_unset" in _PREFS_SOURCE, (
        "PreferencesWindow must allow disconnecting (run_config_unset)"
    )


def test_preferences_uses_launch_default_for_uri():
    assert "launch_default_for_uri" in _PREFS_SOURCE, (
        "PreferencesWindow must use Gio.AppInfo.launch_default_for_uri to open URLs"
    )
