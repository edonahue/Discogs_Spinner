"""Album detail and action controls for match/override/play/tracklist refresh."""

from __future__ import annotations

import logging
import urllib.parse
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

logger = logging.getLogger(__name__)


from discogs_player.ui.utils.formatting import (
    format_community_stats,
    format_discogs_date,
    format_discogs_terms,
    format_market_metrics,
    format_market_summary,
    format_tracklist_body_text,
    format_tracklist_meta_text,
)

_YOUTUBE_ICON_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    b'<rect width="24" height="24" rx="5" fill="#FF0000"/>'
    b'<polygon points="9.5,7 18,12 9.5,17" fill="white"/>'
    b'</svg>'
)


def _make_youtube_icon() -> Gtk.Image:
    try:
        from gi.repository import GdkPixbuf
        loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
        loader.set_size(16, 16)
        loader.write(_YOUTUBE_ICON_SVG)
        loader.close()
        return Gtk.Image.new_from_pixbuf(loader.get_pixbuf())
    except Exception:
        logger.debug("Could not render YouTube icon SVG; using blank image", exc_info=True)
        return Gtk.Image()


def _build_youtube_search_url(artist: str, title: str, year: int | None) -> str:
    parts = [p for p in [artist, title, str(year) if year else None] if p]
    query = urllib.parse.quote_plus(" ".join(parts))
    return f"https://www.youtube.com/results?search_query={query}"


_SPOTIFY_DASHBOARD_URL = "https://developer.spotify.com/dashboard"
_SPOTIFY_OAUTH_GUIDE_URL = (
    "https://developer.spotify.com/documentation/web-api/tutorials/code-flow"
)


def _to_int(value: object | None, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped.lstrip("-").isdigit():
            return int(stripped)
    return default


def _spotify_album_url(album_id_value: object | None) -> str | None:
    raw = str(album_id_value or "").strip()
    if not raw:
        return None
    if raw.startswith("https://open.spotify.com/album/"):
        return raw
    if raw.startswith("http://open.spotify.com/album/"):
        return f"https://{raw.removeprefix('http://')}"
    if raw.startswith("spotify:album:"):
        normalized = raw.removeprefix("spotify:album:").strip()
        if not normalized:
            return None
        return f"https://open.spotify.com/album/{normalized}"
    if "://" in raw:
        return None
    if any(char.isspace() for char in raw):
        return None
    return f"https://open.spotify.com/album/{raw}"


class AlbumDetail(Gtk.Box):
    def __init__(
        self,
        *,
        on_auto_match: Callable[[], None] | None = None,
        on_override: Callable[[], None] | None = None,
        on_play: Callable[[], None] | None = None,
        on_match_audit: Callable[[], None] | None = None,
        on_apply_safe_matches: Callable[[], None] | None = None,
        on_review_apply: Callable[[], None] | None = None,
        on_review_reject: Callable[[], None] | None = None,
        on_retry_audit_errors: Callable[[], None] | None = None,
        on_refresh_tracklist: Callable[[], None] | None = None,
        on_view_market_value: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._current_release_id: int | None = None
        self._spotify_addon_available = True
        self._spotify_configured = True
        self._global_spotify_actions_enabled = True

        # Remove the "Album Details" heading
        # heading = Gtk.Label(label="Album Details")
        # heading.set_xalign(0.0)
        # heading.add_css_class("title-4")
        # self.append(heading)

        # Create more prominent artist/album/year/genre display
        self._artist_album_label = Gtk.Label(label="Select a release to view details.")
        self._artist_album_label.set_xalign(0.0)
        self._artist_album_label.set_wrap(True)
        self._artist_album_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._artist_album_label.set_use_markup(True)
        self._artist_album_label.add_css_class("ipod-artist-album-title")
        self.append(self._artist_album_label)

        # Gtk.LinkButton.new_with_label/new() signatures vary across distro GTK bindings.
        # Create with URI first, then set the label for compatibility.
        self._discogs_link_button = Gtk.LinkButton.new("https://www.discogs.com")
        self._discogs_link_button.set_label("Discogs release page")
        self._discogs_link_button.set_halign(Gtk.Align.START)
        self._discogs_link_button.set_valign(Gtk.Align.START)
        self._discogs_link_button.add_css_class("dim-label")
        self._discogs_link_button.set_sensitive(False)
        self.append(self._discogs_link_button)

        self._youtube_link_button = Gtk.LinkButton.new("https://www.youtube.com")
        _ytb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        _ytb_box.append(_make_youtube_icon())
        _ytb_box.append(Gtk.Label(label="Search on YouTube"))
        self._youtube_link_button.set_child(_ytb_box)
        self._youtube_link_button.set_halign(Gtk.Align.START)
        self._youtube_link_button.set_valign(Gtk.Align.START)
        self._youtube_link_button.add_css_class("dim-label")
        self._youtube_link_button.set_sensitive(False)
        self._youtube_link_button.set_tooltip_text("Search YouTube for this release")
        self.append(self._youtube_link_button)

        self._marketplace_button = Gtk.Button(label="Open Marketplace")
        self._marketplace_button.set_halign(Gtk.Align.START)
        self._marketplace_button.set_sensitive(False)
        self._marketplace_button.connect("clicked", self._on_marketplace_clicked)
        self.append(self._marketplace_button)

        self._view_market_value_button = Gtk.Button(label="See in Value Tab")
        self._view_market_value_button.set_halign(Gtk.Align.START)
        self._view_market_value_button.set_sensitive(False)
        if on_view_market_value is not None:
            self._view_market_value_button.connect(
                "clicked", lambda *_: on_view_market_value()
            )
        self.append(self._view_market_value_button)

        market_heading = Gtk.Label(label="Discogs Marketplace")
        market_heading.set_xalign(0.0)
        market_heading.set_margin_top(4)
        market_heading.add_css_class("title-5")
        self.append(market_heading)

        self._market_value_label = Gtk.Label(label="Market: n/a")
        self._market_value_label.set_xalign(0.0)
        self._market_value_label.set_wrap(True)
        self._market_value_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._market_value_label.add_css_class("ipod-detail-data")
        self.append(self._market_value_label)

        self._market_metrics_label = Gtk.Label(label="Metrics: n/a")
        self._market_metrics_label.set_xalign(0.0)
        self._market_metrics_label.set_wrap(True)
        self._market_metrics_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._market_metrics_label.add_css_class("ipod-detail-data")
        self.append(self._market_metrics_label)

        self._community_stats_label = Gtk.Label(label="Stats: n/a")
        self._community_stats_label.set_xalign(0.0)
        self._community_stats_label.set_wrap(True)
        self._community_stats_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._community_stats_label.add_css_class("ipod-detail-data")
        self.append(self._community_stats_label)

        self._discogs_grid = Gtk.Grid()
        self._discogs_grid.set_column_spacing(8)
        self._discogs_grid.set_row_spacing(2)
        self._discogs_grid.set_hexpand(True)
        self.append(self._discogs_grid)

        self._discogs_genres_value = self._add_discogs_row(0, "Genres")
        self._discogs_styles_value = self._add_discogs_row(1, "Styles")
        self._discogs_added_value = self._add_discogs_row(2, "Added")
        self._discogs_synced_value = self._add_discogs_row(3, "Last Sync")

        tracklist_header_row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=6
        )
        tracklist_header_row.set_hexpand(True)
        self.append(tracklist_header_row)

        self._tracklist_heading = Gtk.Label(label="Tracklist")
        self._tracklist_heading.set_xalign(0.0)
        self._tracklist_heading.set_hexpand(True)
        self._tracklist_heading.add_css_class("title-5")
        tracklist_header_row.append(self._tracklist_heading)

        self._refresh_tracklist_button = Gtk.Button(label="Refresh Tracklist")
        self._refresh_tracklist_button.set_tooltip_text(
            "Fetch latest tracklist from Discogs and update local cache."
        )
        if on_refresh_tracklist is not None:
            self._refresh_tracklist_button.connect(
                "clicked", lambda *_: on_refresh_tracklist()
            )
        tracklist_header_row.append(self._refresh_tracklist_button)

        self._tracklist_meta = Gtk.Label(label="Tracklist cache: n/a")
        self._tracklist_meta.set_xalign(0.0)
        self._tracklist_meta.set_wrap(True)
        self._tracklist_meta.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._tracklist_meta.add_css_class("dim-label")
        self.append(self._tracklist_meta)

        self._tracklist_body = Gtk.Label(label="No release selected.")
        self._tracklist_body.set_xalign(0.0)
        self._tracklist_body.set_wrap(True)
        self._tracklist_body.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._tracklist_body.set_selectable(True)
        self.append(self._tracklist_body)

        self._mapping_label = Gtk.Label(label="Mapping: none")
        self._mapping_label.set_xalign(0.0)
        self._mapping_label.set_wrap(True)
        self._mapping_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.append(self._mapping_label)

        self._spotify_mapping_link_button = Gtk.LinkButton.new(
            "https://open.spotify.com"
        )
        self._spotify_mapping_link_button.set_label("Spotify album link unavailable")
        self._spotify_mapping_link_button.set_halign(Gtk.Align.START)
        self._spotify_mapping_link_button.set_sensitive(False)
        self._spotify_mapping_link_button.add_css_class("dim-label")
        self.append(self._spotify_mapping_link_button)

        self._candidate_label = Gtk.Label(label="Candidate: none")
        self._candidate_label.set_xalign(0.0)
        self._candidate_label.set_wrap(True)
        self._candidate_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.append(self._candidate_label)

        self._spotify_hint_label = Gtk.Label(label="")
        self._spotify_hint_label.set_xalign(0.0)
        self._spotify_hint_label.set_wrap(True)
        self._spotify_hint_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._spotify_hint_label.add_css_class("dim-label")
        self.append(self._spotify_hint_label)

        self._spotify_help_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._spotify_dashboard_link = Gtk.LinkButton.new(_SPOTIFY_DASHBOARD_URL)
        self._spotify_dashboard_link.set_label("Spotify Dashboard")
        self._spotify_dashboard_link.set_halign(Gtk.Align.START)
        self._spotify_help_row.append(self._spotify_dashboard_link)

        self._spotify_oauth_guide_link = Gtk.LinkButton.new(_SPOTIFY_OAUTH_GUIDE_URL)
        self._spotify_oauth_guide_link.set_label("Spotify OAuth Guide")
        self._spotify_oauth_guide_link.set_halign(Gtk.Align.START)
        self._spotify_help_row.append(self._spotify_oauth_guide_link)
        self._spotify_help_row.set_visible(False)
        self.append(self._spotify_help_row)

        self._override_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._override_entry = Gtk.Entry()
        self._override_entry.set_hexpand(True)
        self._override_entry.set_placeholder_text("Paste Spotify album URI or URL")
        self._override_row.append(self._override_entry)

        self._override_button = Gtk.Button(label="Save Override")
        if on_override is not None:
            self._override_button.connect("clicked", lambda *_: on_override())
        self._override_row.append(self._override_button)
        self.append(self._override_row)

        self._action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._match_button = Gtk.Button(label="Auto Match")
        if on_auto_match is not None:
            self._match_button.connect("clicked", lambda *_: on_auto_match())
        self._action_row.append(self._match_button)

        self._play_button = Gtk.Button(label="Play")
        if on_play is not None:
            self._play_button.connect("clicked", lambda *_: on_play())
        self._action_row.append(self._play_button)
        self.append(self._action_row)

        self._audit_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._audit_button = Gtk.Button(label="Audit Matching")
        if on_match_audit is not None:
            self._audit_button.connect("clicked", lambda *_: on_match_audit())
        self._audit_row.append(self._audit_button)

        self._apply_safe_button = Gtk.Button(label="Apply Safe Matches")
        if on_apply_safe_matches is not None:
            self._apply_safe_button.connect(
                "clicked", lambda *_: on_apply_safe_matches()
            )
        self._audit_row.append(self._apply_safe_button)

        self._apply_review_button = Gtk.Button(label="Apply Review Queue")
        if on_review_apply is not None:
            self._apply_review_button.connect("clicked", lambda *_: on_review_apply())
        self._audit_row.append(self._apply_review_button)

        self._reject_review_button = Gtk.Button(label="Reject Review Queue")
        if on_review_reject is not None:
            self._reject_review_button.connect("clicked", lambda *_: on_review_reject())
        self._audit_row.append(self._reject_review_button)

        self._retry_audit_errors_button = Gtk.Button(label="Retry Audit Errors")
        if on_retry_audit_errors is not None:
            self._retry_audit_errors_button.connect(
                "clicked", lambda *_: on_retry_audit_errors()
            )
        self._audit_row.append(self._retry_audit_errors_button)
        self.append(self._audit_row)

        self._audit_label = Gtk.Label(label="Audit: not run.")
        self._audit_label.set_xalign(0.0)
        self._audit_label.set_wrap(True)
        self._audit_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._audit_label.add_css_class("dim-label")
        self.append(self._audit_label)

        self._result_label = Gtk.Label(label="Status: idle")
        self._result_label.set_xalign(0.0)
        self._result_label.set_wrap(True)
        self._result_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.append(self._result_label)

        self.set_actions_enabled(False)

    def set_spotify_capability(
        self,
        *,
        addon_available: bool,
        configured: bool,
        action_label: str | None = None,
    ) -> None:
        self._spotify_addon_available = bool(addon_available)
        self._spotify_configured = bool(configured)

        if not self._spotify_addon_available:
            hint = action_label or "Enable Spotify (optional)"
            self._spotify_hint_label.set_text(hint)
            self._mapping_label.set_visible(False)
            self._spotify_mapping_link_button.set_visible(False)
            self._candidate_label.set_visible(False)
            self._override_row.set_visible(False)
            self._match_button.set_visible(False)
            self._play_button.set_label("Open in Spotify")
            self._audit_row.set_visible(False)
            self._audit_label.set_visible(False)
        elif not self._spotify_configured:
            hint = action_label or "Connect Spotify"
            self._spotify_hint_label.set_text(hint)
            self._mapping_label.set_visible(True)
            self._spotify_mapping_link_button.set_visible(True)
            self._candidate_label.set_visible(True)
            self._override_row.set_visible(False)
            self._match_button.set_visible(False)
            self._play_button.set_label("Open in Spotify")
            self._audit_row.set_visible(False)
            self._audit_label.set_visible(False)
        else:
            self._spotify_hint_label.set_text("")
            self._mapping_label.set_visible(True)
            self._spotify_mapping_link_button.set_visible(True)
            self._candidate_label.set_visible(True)
            self._override_row.set_visible(True)
            self._match_button.set_visible(True)
            self._play_button.set_label("Play")
            self._audit_row.set_visible(True)
            self._audit_label.set_visible(True)

        self._spotify_hint_label.set_visible(bool(self._spotify_hint_label.get_text()))
        self._spotify_help_row.set_visible(bool(self._spotify_hint_label.get_text()))
        self._apply_global_spotify_action_sensitivity()

    def set_actions_enabled(self, enabled: bool) -> None:
        spotify_actions_enabled = bool(
            enabled and self._spotify_addon_available and self._spotify_configured
        )
        self._override_entry.set_sensitive(spotify_actions_enabled)
        self._override_button.set_sensitive(spotify_actions_enabled)
        self._match_button.set_sensitive(spotify_actions_enabled)
        self._play_button.set_sensitive(bool(enabled))
        self._refresh_tracklist_button.set_sensitive(enabled)
        self._apply_global_spotify_action_sensitivity()

    def _apply_global_spotify_action_sensitivity(self) -> None:
        global_actions_enabled = bool(
            self._global_spotify_actions_enabled
            and self._spotify_addon_available
            and self._spotify_configured
        )
        self._audit_button.set_sensitive(global_actions_enabled)
        self._apply_safe_button.set_sensitive(global_actions_enabled)
        self._apply_review_button.set_sensitive(global_actions_enabled)
        self._reject_review_button.set_sensitive(global_actions_enabled)
        self._retry_audit_errors_button.set_sensitive(global_actions_enabled)

    def set_global_spotify_actions_enabled(self, enabled: bool) -> None:
        self._global_spotify_actions_enabled = bool(enabled)
        self._apply_global_spotify_action_sensitivity()

    def _add_discogs_row(self, row: int, key_text: str) -> Gtk.Label:
        key_label = Gtk.Label(label=f"{key_text}:")
        key_label.set_xalign(0.0)
        key_label.add_css_class("dim-label")
        self._discogs_grid.attach(key_label, 0, row, 1, 1)

        value_label = Gtk.Label(label="n/a")
        value_label.set_xalign(0.0)
        value_label.set_wrap(True)
        value_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._discogs_grid.attach(value_label, 1, row, 1, 1)
        return value_label

    def _set_discogs_extract_defaults(self) -> None:
        self._discogs_genres_value.set_text("n/a")
        self._discogs_styles_value.set_text("n/a")
        self._discogs_added_value.set_text("n/a")
        self._discogs_synced_value.set_text("n/a")

    def _set_discogs_extract_values(self, item: dict[str, object]) -> None:
        self._discogs_genres_value.set_text(format_discogs_terms(item.get("genres")))
        self._discogs_styles_value.set_text(format_discogs_terms(item.get("styles")))
        self._discogs_added_value.set_text(format_discogs_date(item.get("added_at")))
        self._discogs_synced_value.set_text(
            format_discogs_date(item.get("last_synced_at"))
        )

    def _set_tracklist_defaults(self) -> None:
        self._tracklist_meta.set_text("Tracklist cache: n/a")
        self._tracklist_body.set_text("No release selected.")

    def _set_tracklist_values(self, item: dict[str, object]) -> None:
        self._tracklist_meta.set_text(format_tracklist_meta_text(item))
        self._tracklist_body.set_text(format_tracklist_body_text(item))

    def _set_discogs_link(self, release_id: int | None) -> None:
        if isinstance(release_id, int) and release_id > 0:
            url = f"https://www.discogs.com/release/{release_id}"
            self._discogs_link_button.set_label(f"Open Discogs #{release_id}")
            self._discogs_link_button.set_uri(url)
            self._discogs_link_button.set_sensitive(True)
            self._marketplace_button.set_sensitive(True)
            self._current_release_id = release_id
        else:
            self._discogs_link_button.set_label("Discogs release page")
            self._discogs_link_button.set_uri("https://www.discogs.com")
            self._discogs_link_button.set_sensitive(False)
            self._marketplace_button.set_sensitive(False)
            self._current_release_id = None

    def _set_youtube_link(self, artist: str | None, title: str | None, year: int | None) -> None:
        if artist or title:
            url = _build_youtube_search_url(
                str(artist or "").strip(),
                str(title or "").strip(),
                year,
            )
            self._youtube_link_button.set_uri(url)
            self._youtube_link_button.set_sensitive(True)
        else:
            self._youtube_link_button.set_uri("https://www.youtube.com")
            self._youtube_link_button.set_sensitive(False)

    def _on_marketplace_clicked(self, _button: Gtk.Button) -> None:
        import webbrowser
        if isinstance(self._current_release_id, int):
            url = f"https://www.discogs.com/sell/release/{self._current_release_id}"
            webbrowser.open(url)

    def _set_spotify_mapping_link(self, album_id_value: object | None) -> None:
        url = _spotify_album_url(album_id_value)
        if not url:
            self._spotify_mapping_link_button.set_label("Spotify album link unavailable")
            self._spotify_mapping_link_button.set_uri("https://open.spotify.com")
            self._spotify_mapping_link_button.set_sensitive(False)
            return
        self._spotify_mapping_link_button.set_label("Open mapped Spotify album")
        self._spotify_mapping_link_button.set_uri(url)
        self._spotify_mapping_link_button.set_sensitive(True)

    def set_release(self, item: dict[str, object] | None) -> None:
        if not isinstance(item, dict):
            self._artist_album_label.set_text("Select a release to view details.")
            self._market_value_label.set_text("Market: n/a")
            self._market_metrics_label.set_text("Metrics: n/a")
            self._community_stats_label.set_text("Stats: n/a")
            self._set_discogs_extract_defaults()
            self._set_tracklist_defaults()
            self._mapping_label.set_text("Mapping: none")
            self._set_spotify_mapping_link(None)
            self._candidate_label.set_text("Candidate: none")
            self._result_label.set_text("Status: idle")
            self._override_entry.set_text("")
            self._set_discogs_link(None)
            self._set_youtube_link(None, None, None)
            self._view_market_value_button.set_sensitive(False)
            self.set_actions_enabled(False)
            return

        artist = str(item.get("artist") or "Unknown Artist")
        title = str(item.get("title") or "Unknown Title")
        year = item.get("year")
        year_text = str(year) if year is not None else "Unknown Year"
        genres = item.get("genres")
        genres_text = ", ".join(genres) if isinstance(genres, list) and genres else "Unknown Genre"

        # Format prominent artist/album/year/genre text
        # Escape special chars for Pango markup
        import html
        artist_esc = html.escape(artist)
        title_esc = html.escape(title)
        year_text_esc = html.escape(year_text)
        genres_text_esc = html.escape(genres_text)

        markup = (
            f"<span size='x-large' weight='bold' foreground='#ffffff'>{artist_esc} - {title_esc}</span>\n"
            f"<span size='medium' foreground='#cbd5e1' weight='medium'>{year_text_esc} • {genres_text_esc}</span>"
        )
        self._artist_album_label.set_markup(markup)

        release_id = item.get("discogs_release_id")
        self._set_discogs_link(release_id if isinstance(release_id, int) else None)
        self._set_youtube_link(
            item.get("artist"),  # type: ignore[arg-type]
            item.get("title"),  # type: ignore[arg-type]
            item.get("year"),  # type: ignore[arg-type]
        )
        self._market_value_label.set_text(format_market_summary(item))
        self._market_metrics_label.set_text(format_market_metrics(item))
        self._community_stats_label.set_text(format_community_stats(item))
        self._set_discogs_extract_values(item)
        self._set_tracklist_values(item)

        album_id = str(item.get("spotify_album_id") or "").strip()
        if album_id:
            self._mapping_label.set_text(f"Mapping: {album_id}")
            self._override_entry.set_text(album_id)
        else:
            self._mapping_label.set_text("Mapping: none")
            self._override_entry.set_text("")
        self._set_spotify_mapping_link(album_id)

        self._candidate_label.set_text("Candidate: none")
        self._result_label.set_text("Status: ready")
        self._view_market_value_button.set_sensitive(True)
        self.set_actions_enabled(True)

    def get_override_album_id(self) -> str:
        return str(self._override_entry.get_text() or "").strip()

    def set_match_result(self, payload: dict[str, object]) -> None:
        album_id = str(payload.get("spotify_album_id") or "").strip()
        confidence = payload.get("confidence")
        source = str(payload.get("source") or "auto")
        if album_id:
            confidence_text = (
                f"{float(confidence):.3f}"
                if isinstance(confidence, (int, float))
                else "n/a"
            )
            self._mapping_label.set_text(
                f"Mapping: {album_id} (confidence {confidence_text}, source {source})"
            )
            self._override_entry.set_text(album_id)
        else:
            self._mapping_label.set_text("Mapping: none")
        self._set_spotify_mapping_link(album_id)

        candidate_summary = str(payload.get("candidate_summary") or "").strip()
        if candidate_summary:
            self._candidate_label.set_text(f"Candidate: {candidate_summary}")
        else:
            self._candidate_label.set_text("Candidate: none")

        self._result_label.set_text(
            str(payload.get("status_message") or "Match complete.")
        )

    def set_override_result(self, payload: dict[str, object]) -> None:
        album_id = str(payload.get("spotify_album_id") or "").strip()
        if album_id:
            self._mapping_label.set_text(f"Mapping: {album_id} (override)")
            self._override_entry.set_text(album_id)
        else:
            self._mapping_label.set_text("Mapping: none")
            self._override_entry.set_text("")
        self._set_spotify_mapping_link(album_id)
        self._result_label.set_text(
            str(payload.get("status_message") or "Override saved.")
        )

    def set_play_result(self, payload: dict[str, object]) -> None:
        self._result_label.set_text(
            str(payload.get("status_message") or "Play action complete.")
        )

    def set_match_audit_result(self, payload: dict[str, object]) -> None:
        processed = _to_int(payload.get("run_processed_count"))
        auto_applied = _to_int(payload.get("run_auto_applied_count"))
        manual_applied = _to_int(payload.get("run_manual_applied_count"))
        manual_rejected = _to_int(payload.get("run_manual_rejected_count"))
        review = _to_int(payload.get("run_review_queue_count"))
        errors = _to_int(payload.get("run_error_count"))
        report_path = str(payload.get("report_path") or "").strip()
        label = (
            f"Audit: processed {processed}, auto-applied {auto_applied}, "
            f"manual-applied {manual_applied}, manual-rejected {manual_rejected}, "
            f"review {review}, errors {errors}."
        )
        if report_path:
            label = f"{label} Report: {report_path}"
        self._audit_label.set_text(label)
        self._result_label.set_text(
            str(payload.get("status_message") or "Match audit complete.")
        )

    def set_match_review_result(self, payload: dict[str, object]) -> None:
        review = _to_int(payload.get("review_queue_count"))
        updated = _to_int(payload.get("updated_count"))
        action = str(payload.get("action") or "review")
        report_path = str(payload.get("report_path") or "").strip()
        label = f"Review action {action}: updated {updated}, remaining review {review}."
        if report_path:
            label = f"{label} Report: {report_path}"
        self._audit_label.set_text(label)
        self._result_label.set_text(
            str(payload.get("status_message") or "Review action complete.")
        )

    def set_error(self, message: str) -> None:
        self._result_label.set_text(f"Error: {message}")
