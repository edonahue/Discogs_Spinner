"""Source-level assertions for the setup wizard module."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

_WIZARD_SOURCE = (
    Path(__file__).parent.parent
    / "src"
    / "discogs_player"
    / "ui"
    / "dialogs"
    / "setup_wizard.py"
).read_text()


def test_wizard_file_exists():
    path = (
        Path(__file__).parent.parent
        / "src"
        / "discogs_player"
        / "ui"
        / "dialogs"
        / "setup_wizard.py"
    )
    assert path.exists(), "setup_wizard.py must exist"


def test_wizard_uses_run_config_set():
    assert "run_config_set" in _WIZARD_SOURCE, (
        "SetupWizard must import and call run_config_set"
    )


def test_wizard_uses_launch_default_for_uri():
    assert "launch_default_for_uri" in _WIZARD_SOURCE, (
        "SetupWizard must use Gio.AppInfo.launch_default_for_uri to open URLs"
    )


def test_wizard_has_progress_callback():
    assert "_make_sync_progress_callback" in _WIZARD_SOURCE, (
        "SetupWizard must have a sync progress callback method"
    )


def test_wizard_has_spotify_step():
    assert "addon_available" in _WIZARD_SOURCE, (
        "Spotify step must be conditional on addon_available"
    )


def test_wizard_emits_setup_complete():
    assert "setup-complete" in _WIZARD_SOURCE, (
        "SetupWizard must emit setup-complete signal on finish"
    )


def test_wizard_inherits_adw_window():
    assert "Adw.Window" in _WIZARD_SOURCE, (
        "SetupWizard must subclass Adw.Window"
    )


def test_wizard_step1_has_password_entry():
    assert "PasswordEntry" in _WIZARD_SOURCE, (
        "Step 1 must use Gtk.PasswordEntry for token input"
    )


def test_wizard_uses_run_sync_collection():
    assert "run_sync_collection" in _WIZARD_SOURCE, (
        "Step 2 must use run_sync_collection"
    )


def test_wizard_spawns_spotify_oauth_in_background():
    assert "run_spotify_oauth_login" in _WIZARD_SOURCE, (
        "Step 3 must call run_spotify_oauth_login"
    )
    assert "on_authorization_url" in _WIZARD_SOURCE, (
        "Step 3 must pass on_authorization_url callback"
    )
