"""First-run setup wizard for Spinner for Discogs GUI."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
import logging
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from discogs_player.brand import APP_NAME
from discogs_player.capabilities import get_capabilities
from discogs_player.core.settings import get_setting, set_setting
from discogs_player.use_cases.config_management import run_config_set
from discogs_player.use_cases.setup_report import run_setup_report
from discogs_player.use_cases.sync_collection import SyncCancelledError, run_sync_collection

logger = logging.getLogger(__name__)


def _open_uri(uri: str) -> None:
    try:
        Gio.AppInfo.launch_default_for_uri(uri, None)
    except Exception:
        logger.warning("Could not open URI in default handler: %s", uri, exc_info=True)


def _make_heading(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.add_css_class("title-2")
    label.set_wrap(True)
    label.set_xalign(0.5)
    return label


def _make_body(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.set_wrap(True)
    label.set_xalign(0.5)
    label.add_css_class("dim-label")
    return label


class SetupWizard(Adw.Window):
    """Modal setup wizard shown on first run when Discogs token is missing.

    Emits ``setup-complete`` (no args) when the user dismisses after completing
    at least the token step (or clicks Skip all the way through).
    """

    __gsignals__: dict[str, object] = {
        "setup-complete": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, parent: Gtk.Window) -> None:
        super().__init__(title=f"{APP_NAME} Setup")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(440, 500)
        self.set_resizable(False)

        self._token_saved = False
        self._sync_cancel_token: threading.Event | None = None
        self._spotify_auth_url: str | None = None
        self._oauth_countdown_source: int | None = None
        self._oauth_countdown_end: float = 0.0
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="wizard")
        self.connect("close-request", self._on_close_request)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)

        self._step1 = self._build_step1()
        self._step2 = self._build_step2()
        self._step3 = self._build_step3()

        self._stack.add_named(self._step1, "step1")
        self._stack.add_named(self._step2, "step2")
        self._stack.add_named(self._step3, "step3")

        # Resume at the step where the user left off in a previous session.
        resumed_step = get_setting("wizard_completed_step")
        if resumed_step == "2":
            self._stack.set_visible_child_name("step3")
        elif resumed_step == "1":
            self._token_saved = True
            self._step1_next_btn.set_sensitive(True)
            self._stack.set_visible_child_name("step2")

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_cls = getattr(Adw, "ToolbarView", None)
        if toolbar_cls is not None:
            toolbar = toolbar_cls()
            toolbar.add_top_bar(header)
            toolbar.set_content(self._stack)
            self.set_content(toolbar)
        else:
            self.set_titlebar(header)
            self.set_content(self._stack)

    # ------------------------------------------------------------------ Step 1

    def _build_step1(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(32)
        box.set_margin_bottom(24)
        box.set_margin_start(32)
        box.set_margin_end(32)

        box.append(_make_heading("Connect to Discogs"))
        box.append(
            _make_body(
                "You'll need a Personal Access Token from Discogs to import your collection."
            )
        )

        link_btn = Gtk.LinkButton(label="Open discogs.com/settings/developers")
        link_btn.set_uri("https://www.discogs.com/settings/developers")
        link_btn.set_halign(Gtk.Align.CENTER)
        box.append(link_btn)

        self._token_entry = Gtk.PasswordEntry()
        self._token_entry.set_show_peek_icon(True)
        self._token_entry.set_hexpand(True)
        box.append(self._token_entry)

        self._save_token_btn = Gtk.Button(label="Save Token")
        self._save_token_btn.add_css_class("suggested-action")
        self._save_token_btn.set_halign(Gtk.Align.FILL)
        self._save_token_btn.connect("clicked", self._on_save_token_clicked)
        box.append(self._save_token_btn)

        self._token_status = Gtk.Label(label="")
        self._token_status.set_xalign(0.5)
        box.append(self._token_status)

        nav_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav_row.set_halign(Gtk.Align.FILL)
        nav_row.set_hexpand(True)

        skip_btn = Gtk.Button(label="Skip")
        skip_btn.set_hexpand(True)
        skip_btn.connect("clicked", lambda _: self._finish())
        nav_row.append(skip_btn)

        self._step1_next_btn = Gtk.Button(label="Next")
        self._step1_next_btn.add_css_class("suggested-action")
        self._step1_next_btn.set_hexpand(True)
        self._step1_next_btn.set_sensitive(False)
        self._step1_next_btn.connect("clicked", self._on_step1_next)
        nav_row.append(self._step1_next_btn)

        box.append(nav_row)
        return box

    def _on_save_token_clicked(self, _btn: Gtk.Button) -> None:
        token = self._token_entry.get_text().strip()
        if not token:
            self._token_status.set_text("Please enter a token first.")
            return
        self._save_token_btn.set_sensitive(False)
        self._token_status.set_text("Saving…")
        try:
            run_config_set("discogs_token", token)
            self._token_saved = True
            self._token_status.set_text("Token saved.")
            self._step1_next_btn.set_sensitive(True)
        except Exception as exc:
            msg = str(exc)
            if "token" in msg.lower() or "auth" in msg.lower() or "401" in msg:
                self._token_status.set_text(
                    "Token rejected — visit discogs.com/settings/developers to generate a valid token."
                )
            else:
                self._token_status.set_text(f"Could not save token: {msg}")
        finally:
            self._save_token_btn.set_sensitive(True)

    def _on_step1_next(self, _btn: Gtk.Button) -> None:
        set_setting("wizard_completed_step", "1")
        self._stack.set_visible_child_name("step2")

    # ------------------------------------------------------------------ Step 2

    def _build_step2(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(32)
        box.set_margin_bottom(24)
        box.set_margin_start(32)
        box.set_margin_end(32)

        box.append(_make_heading("Import your collection"))
        box.append(
            _make_body(
                "Sync your Discogs collection so you can browse and spin records."
            )
        )

        self._sync_btn = Gtk.Button(label="Sync now")
        self._sync_btn.add_css_class("suggested-action")
        self._sync_btn.set_halign(Gtk.Align.FILL)
        self._sync_btn.connect("clicked", self._on_sync_clicked)
        box.append(self._sync_btn)

        self._sync_cancel_btn = Gtk.Button(label="Cancel sync")
        self._sync_cancel_btn.set_halign(Gtk.Align.FILL)
        self._sync_cancel_btn.set_visible(False)
        self._sync_cancel_btn.connect("clicked", self._on_sync_cancel_clicked)
        box.append(self._sync_cancel_btn)

        self._sync_status = Gtk.Label(label="")
        self._sync_status.set_wrap(True)
        self._sync_status.set_xalign(0.5)
        box.append(self._sync_status)

        nav_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav_row.set_halign(Gtk.Align.FILL)
        nav_row.set_hexpand(True)

        skip_btn = Gtk.Button(label="Skip")
        skip_btn.set_hexpand(True)
        skip_btn.connect("clicked", self._on_step2_skip)
        nav_row.append(skip_btn)

        self._step2_next_btn = Gtk.Button(label="Next")
        self._step2_next_btn.add_css_class("suggested-action")
        self._step2_next_btn.set_hexpand(True)
        self._step2_next_btn.set_sensitive(False)
        self._step2_next_btn.connect("clicked", self._on_step2_next)
        nav_row.append(self._step2_next_btn)

        box.append(nav_row)
        return box

    def _make_sync_progress_callback(self) -> Callable[[int, int, int, int], None]:
        def _progress(page: int, pages: int, _num_items: int, total_items: int) -> None:
            msg = f"Syncing… page {page} of {pages} ({total_items} found)"
            GLib.idle_add(self._sync_status.set_text, msg)

        return _progress

    def _on_sync_clicked(self, _btn: Gtk.Button) -> None:
        self._sync_btn.set_sensitive(False)
        self._sync_cancel_btn.set_visible(True)
        self._sync_status.set_text("Starting sync…")
        self._sync_cancel_token = threading.Event()
        cancel_token = self._sync_cancel_token

        def _runner() -> dict[str, object]:
            return run_sync_collection(
                progress_callback=self._make_sync_progress_callback(),
                cancel_token=cancel_token,
            )

        future = self._executor.submit(_runner)

        def _on_done(f: Future[dict[str, object]]) -> None:
            GLib.idle_add(self._apply_sync_result, f)

        future.add_done_callback(_on_done)

    def _on_sync_cancel_clicked(self, _btn: Gtk.Button) -> None:
        if self._sync_cancel_token is not None:
            self._sync_cancel_token.set()

    def _apply_sync_result(self, future: Future[dict[str, object]]) -> bool:
        self._sync_btn.set_sensitive(True)
        self._sync_cancel_btn.set_visible(False)
        self._sync_cancel_token = None
        try:
            result = future.result()
            total = result.get("upserted_count") or result.get("fetched_count") or 0
            self._sync_status.set_text(f"Sync complete — {total} releases imported.")
            self._step2_next_btn.set_sensitive(True)
        except SyncCancelledError:
            self._sync_status.set_text("Sync cancelled. Click 'Sync now' to try again.")
        except Exception as exc:
            msg = str(exc)
            msg_lower = msg.lower()
            if "token" in msg_lower or "401" in msg or "unauthorized" in msg_lower:
                self._sync_status.set_text(
                    "Sync failed: token rejected — check your token at discogs.com/settings/developers."
                )
            elif "connection" in msg_lower or "timeout" in msg_lower or "network" in msg_lower:
                self._sync_status.set_text(
                    "Sync failed: network error — check your internet connection and try again."
                )
            else:
                self._sync_status.set_text(f"Sync failed: {msg}")
        return False

    def _on_step2_skip(self, _btn: Gtk.Button) -> None:
        self._on_step2_next(None)

    def _on_step2_next(self, _btn: Gtk.Button | None) -> None:
        set_setting("wizard_completed_step", "2")
        caps = get_capabilities()
        try:
            report = run_setup_report()
        except Exception:
            report = {}
        readiness = report.get("provider_readiness")
        summary = readiness.get("summary") if isinstance(readiness, dict) else {}
        optional_provider_count = 0
        if isinstance(summary, dict):
            optional_provider_count = int(summary.get("optional_provider_count") or 0)

        if optional_provider_count > 0 or caps.spotify.addon_available:
            self._stack.set_visible_child_name("step3")
            self._refresh_step3_status()
            return
        self._finish()

    # ------------------------------------------------------------------ Step 3

    def _build_step3(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(32)
        box.set_margin_bottom(24)
        box.set_margin_start(32)
        box.set_margin_end(32)

        box.append(_make_heading("Connect Spotify (Optional)"))
        box.append(
            _make_body(
                "Link a Spotify account to play records directly from your collection."
            )
        )

        self._spotify_status_label = Gtk.Label(label="")
        self._spotify_status_label.set_wrap(True)
        self._spotify_status_label.set_xalign(0.5)
        self._spotify_status_label.add_css_class("dim-label")
        box.append(self._spotify_status_label)

        self._copy_link_btn = Gtk.Button(label="Copy link")
        self._copy_link_btn.set_halign(Gtk.Align.CENTER)
        self._copy_link_btn.set_visible(False)
        self._copy_link_btn.connect("clicked", self._on_copy_link_clicked)
        box.append(self._copy_link_btn)

        self._oauth_countdown_label = Gtk.Label(label="")
        self._oauth_countdown_label.set_xalign(0.5)
        self._oauth_countdown_label.add_css_class("dim-label")
        self._oauth_countdown_label.set_visible(False)
        box.append(self._oauth_countdown_label)

        self._connect_spotify_btn = Gtk.Button(label="Connect Spotify")
        self._connect_spotify_btn.add_css_class("suggested-action")
        self._connect_spotify_btn.set_halign(Gtk.Align.FILL)
        self._connect_spotify_btn.connect("clicked", self._on_connect_spotify_clicked)
        box.append(self._connect_spotify_btn)

        done_btn = Gtk.Button(label="Done")
        done_btn.set_halign(Gtk.Align.FILL)
        done_btn.add_css_class("suggested-action")
        done_btn.connect("clicked", lambda _: self._finish())
        box.append(done_btn)

        return box

    def _refresh_step3_status(self) -> None:
        caps = get_capabilities()
        try:
            report = run_setup_report()
        except Exception:
            report = {}
        readiness = report.get("provider_readiness")
        summary = readiness.get("summary") if isinstance(readiness, dict) else {}
        summary_next_actions: list[str] = []
        if isinstance(summary, dict):
            raw_actions = summary.get("next_actions")
            if isinstance(raw_actions, list):
                summary_next_actions = [
                    str(item).strip() for item in raw_actions if str(item).strip()
                ]
        providers = readiness.get("providers") if isinstance(readiness, dict) else []
        spotify_row: dict[str, object] | None = None
        if isinstance(providers, list):
            for row in providers:
                if isinstance(row, dict) and str(row.get("provider_id")) == "spotify":
                    spotify_row = row
                    break

        if spotify_row is not None:
            status_message = str(spotify_row.get("status_message") or "").strip()
            if status_message:
                self._spotify_status_label.set_text(status_message)
            next_actions = spotify_row.get("next_actions")
            if isinstance(next_actions, list) and next_actions:
                first_action = str(next_actions[0]).strip()
                if first_action:
                    self._spotify_status_label.set_text(
                        f"{self._spotify_status_label.get_text()} Next: {first_action}"
                    )
            readiness_state = str(spotify_row.get("readiness") or "").strip().lower()
            configured = bool(spotify_row.get("configured"))
            can_retry_setup = bool(spotify_row.get("can_retry_setup", True))
            if configured:
                self._connect_spotify_btn.set_label("Connected")
                self._connect_spotify_btn.set_sensitive(False)
                return
            if readiness_state == "unavailable":
                self._connect_spotify_btn.set_label("Optional provider unavailable")
                self._connect_spotify_btn.set_sensitive(False)
                return
            self._connect_spotify_btn.set_label("Connect Spotify")
            self._connect_spotify_btn.set_sensitive(can_retry_setup)
            return

        optional_provider_count = 0
        onboarding_state = ""
        if isinstance(summary, dict):
            optional_provider_count = int(summary.get("optional_provider_count") or 0)
            onboarding_state = str(summary.get("onboarding_state") or "").strip()
        if optional_provider_count > 0 and onboarding_state == "core_ready_optional_pending":
            message = (
                "Optional providers are pending. Spotify is not currently listed as "
                "connectable in this GTK step."
            )
            if summary_next_actions:
                message = f"{message} Next: {summary_next_actions[0]}"
            self._spotify_status_label.set_text(message)
            self._connect_spotify_btn.set_label("Use CLI/Web setup")
            self._connect_spotify_btn.set_sensitive(False)
            return

        self._spotify_status_label.set_text(caps.spotify.status_message)
        if summary_next_actions:
            self._spotify_status_label.set_text(
                f"{self._spotify_status_label.get_text()} Next: {summary_next_actions[0]}"
            )
        already_configured = caps.spotify.configured
        self._connect_spotify_btn.set_sensitive(not already_configured)
        if already_configured:
            self._connect_spotify_btn.set_label("Connected")

    def _on_connect_spotify_clicked(self, _btn: Gtk.Button) -> None:
        self._connect_spotify_btn.set_sensitive(False)
        self._spotify_status_label.set_text("Waiting for browser authentication…")

        def _on_auth_url(url: str) -> None:
            GLib.idle_add(self._on_browser_opened, url)

        def _runner() -> dict[str, object]:
            from discogs_player.integrations.spotify.oauth import run_spotify_oauth_login

            return run_spotify_oauth_login(
                open_browser=False,
                on_authorization_url=_on_auth_url,
            )

        future = self._executor.submit(_runner)

        def _on_done(f: Future[dict[str, object]]) -> None:
            GLib.idle_add(self._apply_spotify_result, f)

        future.add_done_callback(_on_done)

    def _apply_spotify_result(self, future: Future[dict[str, object]]) -> bool:
        if self._oauth_countdown_source is not None:
            GLib.source_remove(self._oauth_countdown_source)
            self._oauth_countdown_source = None
        self._copy_link_btn.set_visible(False)
        self._oauth_countdown_label.set_visible(False)
        self._spotify_auth_url = None

        from discogs_player.integrations.spotify.oauth import SpotifyOAuthTimeoutError

        try:
            result = future.result()
            if result.get("ok"):
                self._spotify_status_label.set_text("Spotify connected.")
                self._connect_spotify_btn.set_label("Connected")
            else:
                msg = str(result.get("message") or result.get("error") or "Unknown error.")
                self._spotify_status_label.set_text(f"Connection failed: {msg}")
                self._connect_spotify_btn.set_sensitive(True)
        except SpotifyOAuthTimeoutError:
            self._spotify_status_label.set_text(
                "Authorization timed out. Click 'Connect Spotify' to try again."
            )
            self._connect_spotify_btn.set_sensitive(True)
        except Exception as exc:
            self._spotify_status_label.set_text(f"Connection error: {exc}")
            self._connect_spotify_btn.set_sensitive(True)
        return False

    # ------------------------------------------------------------------ Finish

    def _on_close_request(self, _window: object) -> bool:
        """Ensure executor is cleaned up on any close path (including the X button)."""
        self._executor.shutdown(wait=False)
        return False  # allow the close to proceed

    def _on_browser_opened(self, url: str) -> bool:
        self._spotify_auth_url = url
        _open_uri(url)
        self._spotify_status_label.set_text(
            "Waiting for Spotify authorization… (browser opened).\n"
            "If your browser didn't open, use 'Copy link' to open it manually."
        )
        self._copy_link_btn.set_visible(True)
        self._start_countdown(180)
        return False

    def _start_countdown(self, seconds: int) -> None:
        self._oauth_countdown_end = time.monotonic() + seconds
        self._oauth_countdown_label.set_visible(True)
        self._tick_countdown()
        self._oauth_countdown_source = GLib.timeout_add(10_000, self._tick_countdown)

    def _tick_countdown(self) -> bool:
        remaining = max(0, int(self._oauth_countdown_end - time.monotonic()))
        mins, secs = divmod(remaining, 60)
        self._oauth_countdown_label.set_text(f"Authorization expires in {mins}:{secs:02d}…")
        if remaining <= 0:
            self._oauth_countdown_source = None
            return False
        return True

    def _on_copy_link_clicked(self, btn: Gtk.Button) -> None:
        if not self._spotify_auth_url:
            return
        try:
            display = Gdk.Display.get_default()
            if display is not None:
                display.get_clipboard().set(self._spotify_auth_url)
                btn.set_label("Copied!")
                GLib.timeout_add(2000, lambda: btn.set_label("Copy link") or False)
        except Exception:
            pass

    def _finish(self) -> None:
        set_setting("wizard_completed_step", None)
        self.emit("setup-complete")
        self.close()  # triggers _on_close_request which shuts down executor
