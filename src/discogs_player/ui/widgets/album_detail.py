"""Album detail and action controls for match/override/play."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class AlbumDetail(Gtk.Box):
    def __init__(
        self,
        *,
        on_auto_match: Callable[[], None] | None = None,
        on_override: Callable[[], None] | None = None,
        on_play: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        heading = Gtk.Label(label="Album Detail")
        heading.set_xalign(0.0)
        heading.add_css_class("title-4")
        self.append(heading)

        self._release_title = Gtk.Label(label="No release selected")
        self._release_title.set_xalign(0.0)
        self._release_title.set_wrap(True)
        self._release_title.add_css_class("heading")
        self.append(self._release_title)

        self._release_meta = Gtk.Label(label="")
        self._release_meta.set_xalign(0.0)
        self._release_meta.set_wrap(True)
        self._release_meta.add_css_class("dim-label")
        self.append(self._release_meta)

        self._mapping_label = Gtk.Label(label="Mapping: (none)")
        self._mapping_label.set_xalign(0.0)
        self._mapping_label.set_wrap(True)
        self.append(self._mapping_label)

        self._candidate_label = Gtk.Label(label="Candidate: (none)")
        self._candidate_label.set_xalign(0.0)
        self._candidate_label.set_wrap(True)
        self.append(self._candidate_label)

        override_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._override_entry = Gtk.Entry()
        self._override_entry.set_hexpand(True)
        self._override_entry.set_placeholder_text(
            "spotify:album:<id> or https://open.spotify.com/album/<id>"
        )
        override_row.append(self._override_entry)

        self._override_button = Gtk.Button(label="Save Override")
        if on_override is not None:
            self._override_button.connect("clicked", lambda *_: on_override())
        override_row.append(self._override_button)
        self.append(override_row)

        action_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._match_button = Gtk.Button(label="Auto Match")
        if on_auto_match is not None:
            self._match_button.connect("clicked", lambda *_: on_auto_match())
        action_row.append(self._match_button)

        self._play_button = Gtk.Button(label="Play")
        if on_play is not None:
            self._play_button.connect("clicked", lambda *_: on_play())
        action_row.append(self._play_button)
        self.append(action_row)

        self._result_label = Gtk.Label(label="Action: idle")
        self._result_label.set_xalign(0.0)
        self._result_label.set_wrap(True)
        self.append(self._result_label)

        self.set_actions_enabled(False)

    def set_actions_enabled(self, enabled: bool) -> None:
        self._override_entry.set_sensitive(enabled)
        self._override_button.set_sensitive(enabled)
        self._match_button.set_sensitive(enabled)
        self._play_button.set_sensitive(enabled)

    def set_release(self, item: dict[str, object] | None) -> None:
        if not isinstance(item, dict):
            self._release_title.set_text("No release selected")
            self._release_meta.set_text("")
            self._mapping_label.set_text("Mapping: (none)")
            self._candidate_label.set_text("Candidate: (none)")
            self._result_label.set_text("Action: idle")
            self._override_entry.set_text("")
            self.set_actions_enabled(False)
            return

        artist = str(item.get("artist") or "Unknown Artist")
        title = str(item.get("title") or "Unknown Title")
        year = item.get("year")
        year_text = str(year) if year is not None else "Unknown Year"

        self._release_title.set_text(f"{artist} - {title}")
        self._release_meta.set_text(f"Discogs #{item.get('discogs_release_id')} ({year_text})")

        album_id = str(item.get("spotify_album_id") or "").strip()
        if album_id:
            self._mapping_label.set_text(f"Mapping: {album_id}")
            self._override_entry.set_text(album_id)
        else:
            self._mapping_label.set_text("Mapping: (none)")
            self._override_entry.set_text("")

        self._candidate_label.set_text("Candidate: (none)")
        self._result_label.set_text("Action: ready")
        self.set_actions_enabled(True)

    def get_override_album_id(self) -> str:
        return str(self._override_entry.get_text() or "").strip()

    def set_match_result(self, payload: dict[str, object]) -> None:
        album_id = str(payload.get("spotify_album_id") or "").strip()
        confidence = payload.get("confidence")
        source = str(payload.get("source") or "auto")
        if album_id:
            confidence_text = (
                f"{float(confidence):.3f}" if isinstance(confidence, (int, float)) else "n/a"
            )
            self._mapping_label.set_text(
                f"Mapping: {album_id} (confidence {confidence_text}, source {source})"
            )
            self._override_entry.set_text(album_id)
        else:
            self._mapping_label.set_text("Mapping: (none)")

        candidate_summary = str(payload.get("candidate_summary") or "").strip()
        if candidate_summary:
            self._candidate_label.set_text(f"Candidate: {candidate_summary}")
        else:
            self._candidate_label.set_text("Candidate: (none)")

        self._result_label.set_text(str(payload.get("status_message") or "Match complete."))

    def set_override_result(self, payload: dict[str, object]) -> None:
        album_id = str(payload.get("spotify_album_id") or "").strip()
        if album_id:
            self._mapping_label.set_text(f"Mapping: {album_id} (override)")
            self._override_entry.set_text(album_id)
        self._result_label.set_text(str(payload.get("status_message") or "Override saved."))

    def set_play_result(self, payload: dict[str, object]) -> None:
        self._result_label.set_text(str(payload.get("status_message") or "Play action complete."))

    def set_error(self, message: str) -> None:
        self._result_label.set_text(f"Error: {message}")
