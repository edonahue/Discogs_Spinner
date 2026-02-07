"""Main GTK window for Discogs Player."""

from __future__ import annotations

import json
import traceback

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from discogs_player.services.matching import MatchingDependencyError
from discogs_player.services.spotify_client import SpotifyApiError, SpotifyPlaybackError
from discogs_player.services.spotify_oauth import SpotifyAuthError, SpotifyDependencyError
from discogs_player.use_cases.browse_release_grid import run_browse_release_grid
from discogs_player.use_cases.match_play_flow import (
    run_match_action,
    run_override_action,
    run_play_action,
)
from discogs_player.ui.widgets.album_detail import AlbumDetail
from discogs_player.ui.widgets.cover_grid import CoverGrid
from discogs_player.ui.widgets.device_picker import DevicePicker
from discogs_player.ui.widgets.filters import FilterBar
from discogs_player.ui.widgets.spin_wheel import SpinWheel


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        app: Adw.Application,
        *,
        limit: int = 50,
        preload_covers: bool = True,
    ) -> None:
        super().__init__(application=app, title="Discogs Player")
        self.set_default_size(1200, 820)

        self._limit = max(1, int(limit))
        self._preload_covers = bool(preload_covers)
        self._selected_release_id: int | None = None
        self._selected_release: dict[str, object] | None = None

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(root)

        self._filters = FilterBar(default_limit=self._limit, on_refresh=self.refresh)
        root.append(self._filters)

        content = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        content.set_resize_start_child(True)
        content.set_shrink_start_child(False)
        content.set_resize_end_child(True)
        root.append(content)

        self._cover_grid = CoverGrid(on_selection_changed=self._handle_release_selected)
        content.set_start_child(self._cover_grid)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_margin_top(8)
        sidebar.set_margin_bottom(8)
        sidebar.set_margin_start(8)
        sidebar.set_margin_end(8)
        content.set_end_child(sidebar)

        self._album_detail = AlbumDetail(
            on_auto_match=self._handle_auto_match_clicked,
            on_override=self._handle_override_clicked,
            on_play=self._handle_play_clicked,
        )
        sidebar.append(self._album_detail)
        sidebar.append(SpinWheel())
        sidebar.append(DevicePicker())

        self._status = Gtk.Label(label="Ready")
        self._status.set_xalign(0.0)
        self._status.set_margin_top(6)
        self._status.set_margin_bottom(8)
        self._status.set_margin_start(12)
        self._status.set_margin_end(12)
        root.append(self._status)

    def refresh(self) -> dict[str, object]:
        filters = self._filters.current_filters()
        return self.load_releases_with_filters(
            q=filters["q"],  # type: ignore[arg-type]
            year=filters["year"],  # type: ignore[arg-type]
            genres=filters["genres"],  # type: ignore[arg-type]
            styles=filters["styles"],  # type: ignore[arg-type]
            unmatched=bool(filters["unmatched"]),
            limit=int(filters["limit"]),
        )

    def _set_status(self, message: str) -> None:
        self._status.set_text(message)

    def _selected_release_id_or_raise(self) -> int:
        if self._selected_release_id is None:
            raise ValueError("Select a release first.")
        return self._selected_release_id

    def _friendly_error_message(self, exc: Exception) -> str:
        if isinstance(
            exc,
            (
                SpotifyDependencyError,
                SpotifyAuthError,
                SpotifyApiError,
                SpotifyPlaybackError,
                MatchingDependencyError,
                ValueError,
            ),
        ):
            return str(exc)
        return f"{type(exc).__name__}: {exc}"

    def _handle_release_selected(self, item: dict[str, object] | None) -> None:
        self._selected_release = dict(item) if isinstance(item, dict) else None

        if isinstance(item, dict) and isinstance(item.get("discogs_release_id"), int):
            self._selected_release_id = int(item["discogs_release_id"])
            self._album_detail.set_release(item)
            artist = str(item.get("artist") or "Unknown Artist")
            title = str(item.get("title") or "Unknown Title")
            self._set_status(f"Selected release {self._selected_release_id}: {artist} - {title}")
            return

        self._selected_release_id = None
        self._album_detail.set_release(None)
        self._set_status("No release selected.")

    def _handle_auto_match_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
            payload = run_match_action(release_id)
            self._album_detail.set_match_result(payload)
            self._set_status(str(payload.get("status_message") or "Auto-match completed."))
            if self._selected_release is not None:
                self._selected_release["spotify_album_id"] = payload.get("spotify_album_id")
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._album_detail.set_error(message)
            self._set_status(message)

    def _handle_override_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
            spotify_album_id = self._album_detail.get_override_album_id()
            payload = run_override_action(release_id, spotify_album_id)
            self._album_detail.set_override_result(payload)
            self._set_status(str(payload.get("status_message") or "Override saved."))
            if self._selected_release is not None:
                self._selected_release["spotify_album_id"] = payload.get("spotify_album_id")
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._album_detail.set_error(message)
            self._set_status(message)

    def _handle_play_clicked(self) -> None:
        try:
            release_id = self._selected_release_id_or_raise()
            payload = run_play_action(release_id)
            self._album_detail.set_play_result(payload)
            self._set_status(str(payload.get("status_message") or "Play action completed."))
            if self._selected_release is not None:
                album_id = payload.get("spotify_album_id")
                if album_id:
                    self._selected_release["spotify_album_id"] = album_id
        except Exception as exc:
            message = self._friendly_error_message(exc)
            self._album_detail.set_error(message)
            self._set_status(message)

    def load_releases(self, *, q: str | None = None) -> dict[str, object]:
        return self.load_releases_with_filters(q=q)

    def load_releases_with_filters(
        self,
        *,
        q: str | None = None,
        year: str | None = None,
        genres: list[str] | None = None,
        styles: list[str] | None = None,
        unmatched: bool = False,
        limit: int | None = None,
    ) -> dict[str, object]:
        self._status.set_text("Loading releases...")
        effective_limit = max(1, int(limit if limit is not None else self._limit))
        items = run_browse_release_grid(
            limit=effective_limit,
            q=q,
            year=year,
            genres=genres or [],
            styles=styles or [],
            unmatched=unmatched,
            preload_covers=self._preload_covers,
        )

        self._cover_grid.set_items(items)
        cover_count = sum(1 for item in items if item.get("cover_path"))
        if not items:
            self._album_detail.set_release(None)
            self._set_status("Loaded 0 releases.")
        else:
            self._set_status(
                f"Loaded {len(items)} releases ({cover_count} covers cached). Select a release."
            )
        return {
            "ok": True,
            "item_count": len(items),
            "cover_cached_count": cover_count,
            "query": q,
            "year": year,
            "genres": genres or [],
            "styles": styles or [],
            "unmatched": unmatched,
            "limit": effective_limit,
        }


class DiscogsPlayerApp(Adw.Application):
    def __init__(self, *, limit: int = 50, preload_covers: bool = True, smoke_test: bool = False):
        super().__init__(application_id="com.discogs_player.app")
        self._limit = max(1, int(limit))
        self._preload_covers = bool(preload_covers)
        self._smoke_test = bool(smoke_test)
        self.exit_code = 0
        self._did_activate = False

    def do_activate(self) -> None:  # pragma: no cover - driven by integration runtime
        if self._did_activate:
            return
        self._did_activate = True

        window = MainWindow(self, limit=self._limit, preload_covers=self._preload_covers)
        window.present()

        try:
            report = window.load_releases()
        except Exception as exc:
            self.exit_code = 1
            report = {
                "ok": False,
                "error": str(exc),
                "traceback": traceback.format_exc(limit=4),
            }

        if self._smoke_test:
            print(json.dumps(report, sort_keys=True))
            self.quit()
