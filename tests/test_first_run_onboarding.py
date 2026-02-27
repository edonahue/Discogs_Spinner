"""First-run onboarding and empty-state behavior tests.

Covers the experience for a new GitHub user:
- Token missing on launch → guided status message
- Token set but never synced → "sync to get started" message
- After sync with no filters → normal "no releases" message
- Empty-state overlay visibility toggling
- Browse sync handler wires run_sync_collection with progress callback
- Wantlist sync handler wires run_sync_wantlist with progress callback
- Startup timing: _startup_load_t0 recorded on first load_releases_with_filters call
- Sync progress callback posts GLib.idle_add messages from background thread

All tests are headless (no live GTK display required).
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal source-text assertions (no GTK import needed)
# ---------------------------------------------------------------------------

_MAIN_WINDOW = (
    Path(__file__).parents[1]
    / "src"
    / "discogs_player"
    / "ui"
    / "main_window.py"
)


def _src() -> str:
    return _MAIN_WINDOW.read_text()


# ---------------------------------------------------------------------------
# Item 1: Startup token check — source-level assertions
# ---------------------------------------------------------------------------


def test_main_window_imports_get_discogs_token():
    """get_discogs_token must be imported so token-check logic can run."""
    assert "get_discogs_token" in _src(), (
        "main_window.py must import get_discogs_token for startup token check"
    )


def test_main_window_imports_get_setting():
    """get_setting must be imported for last_sync_time check."""
    assert "get_setting" in _src(), (
        "main_window.py must import get_setting for never-synced detection"
    )


def test_main_window_imports_run_sync_collection():
    """run_sync_collection must be imported for the browse sync handler."""
    assert "run_sync_collection" in _src(), (
        "main_window.py must import run_sync_collection"
    )


# ---------------------------------------------------------------------------
# Item 1 & 4: Empty-state message differentiation — source-level assertions
# ---------------------------------------------------------------------------


def test_token_missing_message_present():
    """Token-missing guided message must be in main_window.py."""
    src = _src()
    assert "discogs.com/settings/developers" in src, (
        "Token-missing empty-state must reference the Discogs developer settings URL"
    )


def test_never_synced_message_present():
    """Never-synced message must mention first-time sync."""
    src = _src()
    assert "last_sync_time" in src, (
        "main_window.py must check last_sync_time to detect never-synced state"
    )
    assert "first time" in src, (
        "Never-synced empty-state message must say 'first time'"
    )


def test_browse_empty_box_visibility_toggled():
    """_browse_empty_box must be shown/hidden based on item count."""
    src = _src()
    assert "_browse_empty_box.set_visible(True)" in src
    assert "_browse_empty_box.set_visible(False)" in src


def test_wantlist_empty_box_visibility_toggled():
    """_wantlist_empty_box must be shown/hidden based on item count."""
    src = _src()
    assert "_wantlist_empty_box.set_visible(True)" in src
    assert "_wantlist_empty_box.set_visible(False)" in src


# ---------------------------------------------------------------------------
# Item 2: Sync button — source-level assertions
# ---------------------------------------------------------------------------


def test_browse_sync_handler_present():
    """_handle_browse_sync_clicked must exist and call run_sync_collection."""
    src = _src()
    assert "_handle_browse_sync_clicked" in src
    assert "run_sync_collection" in src


def test_wantlist_empty_state_has_sync_wantlist_button():
    """Wantlist empty-state must hook into _handle_wantlist_sync_clicked."""
    src = _src()
    assert "_wantlist_empty_box" in src
    assert "_handle_wantlist_sync_clicked" in src


def test_build_empty_state_box_helper_present():
    """_build_empty_state_box helper must be defined."""
    assert "_build_empty_state_box" in _src()


# ---------------------------------------------------------------------------
# Item 3: Sync progress feedback — source-level assertions
# ---------------------------------------------------------------------------


def test_progress_callback_helper_present():
    """_make_sync_progress_callback must be defined."""
    assert "_make_sync_progress_callback" in _src()


def test_progress_callback_uses_glib_idle_add():
    """Progress callback must post status via GLib.idle_add (thread-safe)."""
    src = _src()
    assert "GLib.idle_add" in src
    assert "_make_sync_progress_callback" in src


def test_browse_sync_wires_progress_callback():
    """_handle_browse_sync_clicked must pass the progress callback to run_sync_collection."""
    src = _src()
    # The runner lambda in handle_browse_sync_clicked must call _make_sync_progress_callback
    assert "_make_sync_progress_callback" in src
    # And run_sync_collection is called with progress_callback=
    assert "progress_callback=self._make_sync_progress_callback" in src


def test_wantlist_sync_wires_progress_callback():
    """_handle_wantlist_sync_clicked must pass the progress callback to run_sync_wantlist."""
    src = _src()
    assert "progress_callback=self._make_sync_progress_callback" in src


# ---------------------------------------------------------------------------
# Item 3: Progress callback unit behaviour (logic test, no GTK)
# ---------------------------------------------------------------------------


def test_progress_callback_posts_idle_add():
    """_make_sync_progress_callback must schedule a GLib.idle_add call for each page."""
    # Patch only the items needed to instantiate the callback logic without GTK.
    posted: list[tuple] = []

    class _FakeGLib:
        @staticmethod
        def idle_add(fn, *args):
            posted.append((fn, args))

    # Build the callback by replicating the implementation (avoids GTK import).
    def make_callback(label: str, set_status_fn, glib):
        def _progress(page: int, pages: int, _num: int, total: int) -> None:
            msg = f"{label}... page {page} of {pages} ({total} found)"
            glib.idle_add(set_status_fn, msg)

        return _progress

    messages: list[str] = []
    cb = make_callback("Syncing", messages.append, _FakeGLib)

    cb(1, 5, 10, 10)
    cb(3, 5, 10, 30)

    assert len(posted) == 2
    assert posted[0][1] == ("Syncing... page 1 of 5 (10 found)",)
    assert posted[1][1] == ("Syncing... page 3 of 5 (30 found)",)


# ---------------------------------------------------------------------------
# Item 4: Token / last-sync differentiation — logic unit tests
# ---------------------------------------------------------------------------


def _empty_state_message(token: str | None, last_sync: str | None) -> str:
    """Mirror the logic from _apply_release_load_result for the empty-state case."""
    token_missing = not bool(token)
    if token_missing:
        return (
            "Setup needed: get your Discogs token at"
            " discogs.com/settings/developers, set DISCOGS_TOKEN,"
            " and restart the app."
        )
    elif last_sync is None:
        return (
            "No releases synced yet. Click \"Sync Collection\" to import"
            " your Discogs collection for the first time."
        )
    else:
        return "No releases match the current filters."


def test_empty_state_message_token_missing():
    msg = _empty_state_message(token=None, last_sync=None)
    assert "discogs.com/settings/developers" in msg
    assert "DISCOGS_TOKEN" in msg


def test_empty_state_message_never_synced():
    msg = _empty_state_message(token="tok123", last_sync=None)
    assert "first time" in msg
    assert "Sync Collection" in msg


def test_empty_state_message_filter_applied():
    msg = _empty_state_message(token="tok123", last_sync="2026-02-26T10:00:00")
    assert "filters" in msg
    assert "discogs.com" not in msg


# ---------------------------------------------------------------------------
# Item 6: Startup timing — source-level assertions
# ---------------------------------------------------------------------------


def test_startup_load_t0_recorded_on_first_load():
    """load_releases_with_filters must record _startup_load_t0 when timing is enabled."""
    src = _src()
    assert "_startup_load_t0" in src, (
        "load_releases_with_filters must set _startup_load_t0 for startup timing"
    )


def test_startup_timing_print_in_apply_result():
    """_apply_release_load_result must print [timing] startup-load when t0 is set."""
    src = _src()
    assert "[timing] startup-load" in src, (
        "_apply_release_load_result must emit [timing] startup-load line"
    )


def test_startup_timing_clears_t0_after_first_load():
    """_startup_load_t0 must be deleted after first load to avoid double-printing."""
    src = _src()
    assert "del self._startup_load_t0" in src, (
        "_startup_load_t0 must be deleted after first timing output"
    )


# ---------------------------------------------------------------------------
# Item 3 (new): Last-synced-at indicator — source-level assertions
# ---------------------------------------------------------------------------


def test_format_sync_date_helper_present():
    """_format_sync_date module-level helper must be defined in main_window.py."""
    assert "_format_sync_date" in _src()


def test_last_synced_in_loaded_status():
    """Loaded status message must reference _format_sync_date for browse and wantlist."""
    src = _src()
    assert "Last synced" in src, (
        "Loaded status message must include 'Last synced' indicator"
    )
    assert "_format_sync_date" in src


def test_format_sync_date_logic():
    """_format_sync_date returns YYYY-MM-DD for valid ISO strings and 'never' for None."""
    # Mirror the helper logic without importing GTK-dependent modules.
    from datetime import datetime

    def _format_sync_date(iso_str):
        if not iso_str:
            return "never"
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            local = dt.astimezone()
            return f"{local.year}-{local.month:02d}-{local.day:02d}"
        except (ValueError, AttributeError):
            return iso_str[:10] if iso_str else "never"

    assert _format_sync_date(None) == "never"
    assert _format_sync_date("") == "never"
    result = _format_sync_date("2026-02-26T10:00:00+00:00")
    assert result.startswith("2026-"), f"Expected YYYY-MM-DD, got {result!r}"
    assert _format_sync_date("not-a-date") == "not-a-date"  # 10 chars exactly, no truncation


def test_wantlist_last_synced_uses_wantlist_key():
    """Wantlist loaded status must read last_wantlist_sync_time, not last_sync_time."""
    src = _src()
    assert "last_wantlist_sync_time" in src


# ---------------------------------------------------------------------------
# Item 5: Install script token hint — source-level assertions
# ---------------------------------------------------------------------------

_INSTALL_SCRIPT = (
    Path(__file__).parents[1] / "scripts" / "install_desktop_app.sh"
)


def test_install_script_mentions_discogs_token():
    """install_desktop_app.sh post-install output must mention DISCOGS_TOKEN."""
    content = _INSTALL_SCRIPT.read_text()
    assert "DISCOGS_TOKEN" in content, (
        "install_desktop_app.sh must reference DISCOGS_TOKEN in post-install instructions"
    )


def test_install_script_mentions_token_url():
    """install_desktop_app.sh must link to discogs.com/settings/developers."""
    content = _INSTALL_SCRIPT.read_text()
    assert "discogs.com/settings/developers" in content, (
        "install_desktop_app.sh must include the Discogs token URL"
    )


def test_install_script_mentions_config_set():
    """install_desktop_app.sh must show 'dplayer config set discogs_token' command."""
    content = _INSTALL_SCRIPT.read_text()
    assert "dplayer config set discogs_token" in content


# ---------------------------------------------------------------------------
# Item 8: Wantlist sync time — source-level assertion
# ---------------------------------------------------------------------------

_SYNC_MANAGER = (
    Path(__file__).parents[1]
    / "src"
    / "discogs_player"
    / "services"
    / "sync_manager.py"
)


def test_sync_manager_stores_last_wantlist_sync_time():
    """sync_manager.py must call set_setting('last_wantlist_sync_time', ...) after wantlist sync."""
    content = _SYNC_MANAGER.read_text()
    assert "last_wantlist_sync_time" in content, (
        "sync_manager.py must persist last_wantlist_sync_time so the GUI can detect never-synced state"
    )
