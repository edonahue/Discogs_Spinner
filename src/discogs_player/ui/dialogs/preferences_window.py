"""Persistent Preferences panel for Discogs Player GUI."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from discogs_player.capabilities import get_capabilities
from discogs_player.core.settings import get_discogs_token
from discogs_player.use_cases.config_management import run_config_set, run_config_unset

logger = logging.getLogger(__name__)


def _open_uri(uri: str) -> None:
    try:
        Gio.AppInfo.launch_default_for_uri(uri, None)
    except Exception:
        logger.warning("Could not open URI in default handler: %s", uri, exc_info=True)


class PreferencesWindow(Adw.PreferencesWindow):
    """Application preferences window using libadwaita patterns."""

    def __init__(self, parent: Gtk.Window) -> None:
        super().__init__(title="Preferences")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(560, 480)

        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="prefs")
        self.connect("close-request", self._on_close_request)

        services_page = Adw.PreferencesPage(
            title="Services",
            icon_name="network-server-symbolic",
        )
        self.add(services_page)

        services_page.add(self._build_discogs_group())
        services_page.add(self._build_spotify_group())

    # ---------------------------------------------------------------- Discogs

    def _build_discogs_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Discogs")
        group.set_description("Connect your Discogs account to import your collection.")

        existing_token = get_discogs_token()
        token_row_cls = getattr(Adw, "PasswordEntryRow", None)
        if token_row_cls is not None:
            self._token_row = token_row_cls(title="Personal Access Token")
            if existing_token:
                self._token_row.set_text(existing_token)
            self._token_row.connect("apply", self._on_token_apply)
            group.add(self._token_row)
        else:
            token_row = Adw.ActionRow(title="Personal Access Token")
            token_row.set_subtitle("Paste your Discogs personal access token and save it.")
            self._token_row = Gtk.PasswordEntry()
            self._token_row.set_show_peek_icon(True)
            self._token_row.set_hexpand(True)
            if existing_token:
                self._token_row.set_text(existing_token)
            self._token_row.connect("activate", self._on_token_apply)

            save_button = Gtk.Button(label="Save")
            save_button.add_css_class("suggested-action")
            save_button.set_valign(Gtk.Align.CENTER)
            save_button.connect("clicked", self._on_token_apply)

            token_row.add_suffix(self._token_row)
            token_row.add_suffix(save_button)
            token_row.set_activatable_widget(save_button)
            group.add(token_row)

        # Link to token page
        link_row = Adw.ActionRow(
            title="Get a token",
            subtitle="discogs.com/settings/developers",
        )
        link_row.set_activatable(True)
        link_row.connect(
            "activated",
            lambda _: _open_uri("https://www.discogs.com/settings/developers"),
        )
        link_icon = Gtk.Image.new_from_icon_name("adw-external-link-symbolic")
        link_row.add_suffix(link_icon)
        group.add(link_row)

        # Status row
        self._discogs_status_row = Adw.ActionRow(title="Status")
        self._refresh_discogs_status()
        group.add(self._discogs_status_row)

        return group

    def _refresh_discogs_status(self) -> None:
        token = get_discogs_token()
        if token:
            self._discogs_status_row.set_subtitle("Connected")
            self._discogs_status_row.set_icon_name("emblem-ok-symbolic")
        else:
            self._discogs_status_row.set_subtitle("Not configured")
            self._discogs_status_row.set_icon_name("dialog-warning-symbolic")

    def _on_token_apply(self, _row: object) -> None:
        token = self._token_row.get_text().strip()
        if not token:
            return
        try:
            run_config_set("discogs_token", token)
            self._refresh_discogs_status()
            toast = Adw.Toast(title="Token saved")
            toast.set_timeout(2)
            self.add_toast(toast)
        except Exception as exc:
            toast = Adw.Toast(title=f"Failed to save token: {exc}")
            toast.set_timeout(4)
            self.add_toast(toast)

    # ---------------------------------------------------------------- Spotify

    def _build_spotify_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Spotify Playback (Optional)")
        group.set_description(
            "Link a Spotify account to play records directly. "
            "Requires the Spotify addon: pip install \".[spotify]\""
        )

        self._spotify_status_row = Adw.ActionRow(title="Status")
        self._spotify_connect_row = Adw.ActionRow(title="Connect Spotify")
        self._spotify_connect_row.set_activatable(True)
        self._spotify_connect_row.connect("activated", self._on_spotify_connect)

        self._spotify_disconnect_row = Adw.ActionRow(title="Disconnect Spotify")
        self._spotify_disconnect_row.set_activatable(True)
        self._spotify_disconnect_row.add_css_class("destructive-action")
        self._spotify_disconnect_row.connect("activated", self._on_spotify_disconnect)

        group.add(self._spotify_status_row)
        group.add(self._spotify_connect_row)
        group.add(self._spotify_disconnect_row)

        self._refresh_spotify_status()
        return group

    def _on_close_request(self, _window: Adw.PreferencesWindow) -> bool:
        self._executor.shutdown(wait=False)
        return False

    def _refresh_spotify_status(self) -> None:
        caps = get_capabilities()
        sp = caps.spotify
        self._spotify_status_row.set_subtitle(sp.status_message)

        if not sp.addon_available:
            self._spotify_connect_row.set_sensitive(False)
            self._spotify_disconnect_row.set_sensitive(False)
        elif sp.configured:
            self._spotify_connect_row.set_title("Reconnect Spotify")
            self._spotify_connect_row.set_sensitive(True)
            self._spotify_disconnect_row.set_sensitive(True)
        else:
            self._spotify_connect_row.set_title("Connect Spotify")
            self._spotify_connect_row.set_sensitive(True)
            self._spotify_disconnect_row.set_sensitive(False)

    def _on_spotify_connect(self, _row: Adw.ActionRow) -> None:
        self._spotify_connect_row.set_sensitive(False)
        self._spotify_status_row.set_subtitle("Waiting for browser authentication…")

        def _on_auth_url(url: str) -> None:
            GLib.idle_add(_open_uri, url)

        def _runner() -> dict[str, object]:
            from discogs_player.integrations.spotify.oauth import run_spotify_oauth_login

            return run_spotify_oauth_login(
                open_browser=False,
                on_authorization_url=_on_auth_url,
            )

        future = self._executor.submit(_runner)

        def _on_done(f: Future[dict[str, object]]) -> None:
            GLib.idle_add(self._apply_spotify_connect_result, f)

        future.add_done_callback(_on_done)

    def _apply_spotify_connect_result(self, future: Future[dict[str, object]]) -> bool:
        try:
            result = future.result()
            if result.get("ok"):
                toast = Adw.Toast(title="Spotify connected")
                toast.set_timeout(2)
                self.add_toast(toast)
            else:
                msg = str(result.get("message") or result.get("error") or "Unknown error.")
                toast = Adw.Toast(title=f"Spotify connection failed: {msg}")
                toast.set_timeout(4)
                self.add_toast(toast)
        except Exception as exc:
            toast = Adw.Toast(title=f"Spotify error: {exc}")
            toast.set_timeout(4)
            self.add_toast(toast)
        finally:
            self._refresh_spotify_status()
        return False

    def _on_spotify_disconnect(self, _row: Adw.ActionRow) -> None:
        try:
            run_config_unset("spotify_client_id")
        except Exception:
            pass
        self._refresh_spotify_status()
        toast = Adw.Toast(title="Spotify disconnected")
        toast.set_timeout(2)
        self.add_toast(toast)
