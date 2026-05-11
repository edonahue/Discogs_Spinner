"""Hybrid Value tab workspace with local search and selected-release inspector."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from discogs_player.ui.utils.formatting import (
    format_community_stats,
    format_discogs_date,
    format_discogs_terms,
    format_market_metrics,
    format_market_summary,
    format_price,
)
from discogs_player.ui.widgets.hidden_gems_card import HiddenGemsCard
from discogs_player.ui.widgets.value_dashboard import ValueDashboard

_WORKSPACE_STACK_BREAKPOINT = 920


def _clear_box_children(box: Gtk.Box) -> None:
    child = box.get_first_child()
    while child is not None:
        next_child = child.get_next_sibling()
        box.remove(child)
        child = next_child


def _as_str(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        try:
            return int(text)
        except ValueError:
            return 0
    return 0


def _source_label(source: object | None) -> str:
    normalized = _as_str(source).lower()
    if normalized == "wantlist":
        return "Wantlist"
    return "Collection"


class ValueWorkspace(Gtk.Box):
    def __init__(
        self,
        *,
        on_search_changed: Callable[[str], None] | None = None,
        on_search_result_selected: Callable[[str, int], None] | None = None,
        on_refresh_selected: Callable[[str, int], None] | None = None,
        on_open_selected_source: Callable[[str, int], None] | None = None,
        on_dashboard_release_selected: Callable[[int], None] | None = None,
        on_refresh: Callable[[], None] | None = None,
        on_refresh_missing: Callable[[], None] | None = None,
        on_refresh_stale: Callable[[], None] | None = None,
        on_snapshot_now: Callable[[], None] | None = None,
        on_ops_controls_changed: Callable[[], None] | None = None,
        on_open_docs: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.add_css_class("ipod-value-workspace")

        self._on_search_changed = on_search_changed
        self._on_search_result_selected = on_search_result_selected
        self._on_refresh_selected = on_refresh_selected
        self._on_open_selected_source = on_open_selected_source
        self._search_row_payloads: dict[Gtk.ListBoxRow, tuple[str, int]] = {}
        self._selected_source: str | None = None
        self._selected_release_id: int | None = None

        intro = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        intro.set_hexpand(True)
        self.append(intro)

        kicker = Gtk.Label(label="Value Workspace")
        kicker.set_xalign(0.0)
        kicker.add_css_class("ipod-value-kicker")
        intro.append(kicker)

        title = Gtk.Label(label="Release Value Inspector")
        title.set_xalign(0.0)
        title.add_css_class("title-3")
        title.add_css_class("ipod-value-dashboard-title")
        intro.append(title)

        subtitle = Gtk.Label(
            label=(
                "Search synced collection and wantlist records by artist, title, "
                "Discogs release ID, or Discogs release URL."
            )
        )
        subtitle.set_xalign(0.0)
        subtitle.set_wrap(True)
        subtitle.add_css_class("ipod-value-subtitle")
        intro.append(subtitle)

        workspace_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        workspace_row.set_hexpand(True)
        workspace_row.set_vexpand(False)
        self._workspace_row = workspace_row
        self.append(workspace_row)

        self._search_panel = self._build_search_panel()
        self._search_panel.add_css_class("ipod-panel")
        self._search_panel.add_css_class("ipod-value-search-panel")
        workspace_row.append(self._search_panel)

        self._inspector_panel = self._build_inspector_panel()
        self._inspector_panel.add_css_class("ipod-panel")
        self._inspector_panel.add_css_class("ipod-value-inspector")
        workspace_row.append(self._inspector_panel)

        self.dashboard = ValueDashboard(
            on_refresh=on_refresh,
            on_release_selected=on_dashboard_release_selected,
            on_refresh_missing=on_refresh_missing,
            on_refresh_stale=on_refresh_stale,
            on_snapshot_now=on_snapshot_now,
            on_ops_controls_changed=on_ops_controls_changed,
            on_open_docs=on_open_docs,
        )
        self.dashboard.add_css_class("ipod-panel")
        self.dashboard.add_css_class("ipod-value-dashboard-shell")
        self.append(self.dashboard)

        self.hidden_gems = HiddenGemsCard(
            on_release_selected=on_dashboard_release_selected,
        )
        self.append(self.hidden_gems)

        self.connect("notify::width", self._handle_workspace_width_change)
        self._apply_workspace_layout(width_hint=0)
        self.clear_selected_release()
        self.set_search_results(
            {
                "query": "",
                "result_count": 0,
                "collection_count": 0,
                "wantlist_count": 0,
                "results": [],
            }
        )

    def _build_search_panel(self) -> Gtk.Box:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.set_hexpand(True)
        panel.set_vexpand(False)

        search_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_header.set_hexpand(True)
        panel.append(search_header)

        search_title = Gtk.Label(label="Search")
        search_title.set_xalign(0.0)
        search_title.set_hexpand(True)
        search_title.add_css_class("title-5")
        search_header.append(search_title)

        self._search_counts = Gtk.Label(label="Search collection + wantlist")
        self._search_counts.set_xalign(1.0)
        self._search_counts.add_css_class("dim-label")
        search_header.append(self._search_counts)

        self._search_entry = Gtk.Entry()
        self._search_entry.set_hexpand(True)
        self._search_entry.set_placeholder_text(
            "Search artist/title or paste Discogs release ID/URL"
        )
        self._search_entry.connect("changed", self._handle_search_entry_changed)
        self._search_entry.connect("activate", self._handle_search_entry_activate)
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._handle_search_entry_key_pressed)
        self._search_entry.add_controller(key_controller)
        panel.append(self._search_entry)

        self._search_status = Gtk.Label(label="Search collection or wantlist releases.")
        self._search_status.set_xalign(0.0)
        self._search_status.set_wrap(True)
        self._search_status.add_css_class("ipod-value-ops-status")
        panel.append(self._search_status)

        self._unsynced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._unsynced_box.set_visible(False)
        unsynced_title = Gtk.Label(label="Discogs release not synced locally.")
        unsynced_title.set_xalign(0.0)
        unsynced_title.add_css_class("title-5")
        self._unsynced_box.append(unsynced_title)

        self._unsynced_label = Gtk.Label(label="")
        self._unsynced_label.set_xalign(0.0)
        self._unsynced_label.set_wrap(True)
        self._unsynced_box.append(self._unsynced_label)

        unsynced_links = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        unsynced_links.set_halign(Gtk.Align.START)
        self._unsynced_box.append(unsynced_links)

        self._unsynced_discogs_link = Gtk.LinkButton.new("https://www.discogs.com")
        self._unsynced_discogs_link.set_label("Discogs")
        unsynced_links.append(self._unsynced_discogs_link)

        self._unsynced_marketplace_link = Gtk.LinkButton.new(
            "https://www.discogs.com"
        )
        self._unsynced_marketplace_link.set_label("Marketplace")
        unsynced_links.append(self._unsynced_marketplace_link)
        panel.append(self._unsynced_box)

        self._results_list = Gtk.ListBox()
        self._results_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._results_list.add_css_class("boxed-list")
        self._results_list.connect("row-activated", self._handle_result_row_activated)

        self._results_scroll = Gtk.ScrolledWindow()
        self._results_scroll.set_hexpand(True)
        self._results_scroll.set_vexpand(True)
        self._results_scroll.set_min_content_height(220)
        self._results_scroll.set_max_content_height(360)
        self._results_scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        self._results_scroll.set_child(self._results_list)
        panel.append(self._results_scroll)
        return panel

    def _build_inspector_panel(self) -> Gtk.Box:
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.set_hexpand(True)
        panel.set_vexpand(False)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_hexpand(True)
        panel.append(header)

        title = Gtk.Label(label="Selected Release")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        title.add_css_class("title-5")
        header.append(title)

        self._selected_source_chip = Gtk.Label(label="No selection")
        self._selected_source_chip.add_css_class("ipod-value-chip")
        header.append(self._selected_source_chip)

        self._selected_title = Gtk.Label(label="Select a release to inspect value data.")
        self._selected_title.set_xalign(0.0)
        self._selected_title.set_wrap(True)
        self._selected_title.add_css_class("ipod-artist-album-title")
        panel.append(self._selected_title)

        self._selected_meta = Gtk.Label(label="")
        self._selected_meta.set_xalign(0.0)
        self._selected_meta.set_wrap(True)
        self._selected_meta.add_css_class("dim-label")
        panel.append(self._selected_meta)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_halign(Gtk.Align.START)
        panel.append(actions)

        self._refresh_selected_button = Gtk.Button(label="Refresh Selected Value")
        self._refresh_selected_button.connect(
            "clicked", self._handle_refresh_selected_clicked
        )
        actions.append(self._refresh_selected_button)

        self._open_source_button = Gtk.Button(label="Open in Browse")
        self._open_source_button.connect("clicked", self._handle_open_source_clicked)
        actions.append(self._open_source_button)

        self._selected_discogs_link = Gtk.LinkButton.new("https://www.discogs.com")
        self._selected_discogs_link.set_label("Discogs")
        actions.append(self._selected_discogs_link)

        self._selected_marketplace_link = Gtk.LinkButton.new(
            "https://www.discogs.com"
        )
        self._selected_marketplace_link.set_label("Marketplace")
        actions.append(self._selected_marketplace_link)

        self._selected_status = Gtk.Label(
            label="Search for a release or use See in Value Tab from Browse or Wantlist."
        )
        self._selected_status.set_xalign(0.0)
        self._selected_status.set_wrap(True)
        self._selected_status.add_css_class("ipod-value-ops-status")
        panel.append(self._selected_status)

        self._selected_market_summary = Gtk.Label(label="Market: n/a")
        self._selected_market_summary.set_xalign(0.0)
        self._selected_market_summary.set_wrap(True)
        self._selected_market_summary.add_css_class("ipod-detail-data")
        panel.append(self._selected_market_summary)

        self._selected_market_metrics = Gtk.Label(label="Metrics: n/a")
        self._selected_market_metrics.set_xalign(0.0)
        self._selected_market_metrics.set_wrap(True)
        self._selected_market_metrics.add_css_class("ipod-detail-data")
        panel.append(self._selected_market_metrics)

        self._selected_community_stats = Gtk.Label(label="Stats: n/a")
        self._selected_community_stats.set_xalign(0.0)
        self._selected_community_stats.set_wrap(True)
        self._selected_community_stats.add_css_class("ipod-detail-data")
        panel.append(self._selected_community_stats)

        self._selected_grid = Gtk.Grid()
        self._selected_grid.set_column_spacing(8)
        self._selected_grid.set_row_spacing(2)
        self._selected_grid.set_hexpand(True)
        panel.append(self._selected_grid)
        self._selected_id_value = self._add_grid_row(0, "Discogs ID")
        self._selected_year_value = self._add_grid_row(1, "Year")
        self._selected_genres_value = self._add_grid_row(2, "Genres")
        self._selected_styles_value = self._add_grid_row(3, "Styles")
        self._selected_added_value = self._add_grid_row(4, "Added")
        self._selected_synced_value = self._add_grid_row(5, "Last Sync")
        self._selected_mapping_value = self._add_grid_row(6, "Spotify")
        self._selected_points_value = self._add_grid_row(7, "Price Points")

        notes_heading = Gtk.Label(label="Notes")
        notes_heading.set_xalign(0.0)
        notes_heading.add_css_class("title-5")
        panel.append(notes_heading)

        self._selected_notes = Gtk.Label(label="n/a")
        self._selected_notes.set_xalign(0.0)
        self._selected_notes.set_wrap(True)
        self._selected_notes.set_selectable(True)
        self._selected_notes.add_css_class("dim-label")
        panel.append(self._selected_notes)
        return panel

    def _add_grid_row(self, row: int, key_text: str) -> Gtk.Label:
        key_label = Gtk.Label(label=f"{key_text}:")
        key_label.set_xalign(0.0)
        key_label.add_css_class("dim-label")
        self._selected_grid.attach(key_label, 0, row, 1, 1)

        value_label = Gtk.Label(label="n/a")
        value_label.set_xalign(0.0)
        value_label.set_wrap(True)
        value_label.set_selectable(True)
        self._selected_grid.attach(value_label, 1, row, 1, 1)
        return value_label

    def _apply_workspace_layout(self, *, width_hint: int) -> None:
        compact = 0 < int(width_hint) < _WORKSPACE_STACK_BREAKPOINT
        self._workspace_row.set_orientation(
            Gtk.Orientation.VERTICAL if compact else Gtk.Orientation.HORIZONTAL
        )
        self._search_panel.set_hexpand(True)
        self._inspector_panel.set_hexpand(True)

    def _handle_workspace_width_change(
        self,
        _widget: Gtk.Widget,
        _pspec: object,
    ) -> None:
        self._apply_workspace_layout(width_hint=int(self.get_width()))

    def _clear_results(self) -> None:
        _clear_box_children(self._results_list)
        self._search_row_payloads.clear()
        self._results_list.unselect_all()

    def _handle_search_entry_changed(self, _entry: Gtk.Entry) -> None:
        if self._on_search_changed is not None:
            self._on_search_changed(_as_str(self._search_entry.get_text()))

    def _handle_search_entry_activate(self, _entry: Gtk.Entry) -> None:
        row = self._results_list.get_selected_row()
        if row is None:
            row = self._results_list.get_row_at_index(0)
        if row is not None:
            self._activate_result_row(row)

    def _handle_search_entry_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
            self._move_result_selection(1)
            return True
        if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
            self._move_result_selection(-1)
            return True
        return False

    def _move_result_selection(self, delta: int) -> None:
        first_row = self._results_list.get_row_at_index(0)
        if first_row is None:
            return

        current = self._results_list.get_selected_row()
        if current is None:
            target = first_row if delta >= 0 else first_row
        else:
            next_index = max(0, current.get_index() + int(delta))
            target = self._results_list.get_row_at_index(next_index) or current

        self._results_list.select_row(target)
        target.grab_focus()

    def _handle_result_row_activated(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        self._activate_result_row(row)

    def _activate_result_row(self, row: Gtk.ListBoxRow) -> None:
        payload = self._search_row_payloads.get(row)
        if payload is None or self._on_search_result_selected is None:
            return
        source, release_id = payload
        self._results_list.select_row(row)
        self._on_search_result_selected(source, release_id)

    def _handle_refresh_selected_clicked(self, _button: Gtk.Button) -> None:
        if (
            self._on_refresh_selected is None
            or self._selected_source is None
            or self._selected_release_id is None
        ):
            return
        self._on_refresh_selected(self._selected_source, self._selected_release_id)

    def _handle_open_source_clicked(self, _button: Gtk.Button) -> None:
        if (
            self._on_open_selected_source is None
            or self._selected_source is None
            or self._selected_release_id is None
        ):
            return
        self._on_open_selected_source(self._selected_source, self._selected_release_id)

    def set_search_results(self, report: dict[str, object]) -> None:
        query = _as_str(report.get("query"))
        result_count = _as_int(report.get("result_count"))
        collection_count = _as_int(report.get("collection_count"))
        wantlist_count = _as_int(report.get("wantlist_count"))
        unresolved_release_id = report.get("unresolved_release_id")
        unresolved_discogs_url = _as_str(report.get("unresolved_discogs_url"))
        unresolved_marketplace_url = _as_str(report.get("unresolved_marketplace_url"))
        results_raw = report.get("results")
        results = (
            [dict(item) for item in results_raw if isinstance(item, dict)]
            if isinstance(results_raw, list)
            else []
        )

        self._clear_results()
        self._unsynced_box.set_visible(False)

        if not query:
            self._search_counts.set_text("Search collection + wantlist")
            self._search_status.set_text(
                "Search collection or wantlist releases by artist, title, ID, or URL."
            )
            return

        self._search_counts.set_text(
            f"{collection_count} collection · {wantlist_count} wantlist"
        )

        if unresolved_release_id is not None:
            self._search_status.set_text(
                f"Release {_as_int(unresolved_release_id)} is not available in the synced library."
            )
            self._unsynced_label.set_text(
                "Paste a synced release ID or sync the matching record into collection "
                "or wantlist to inspect its cached value data here."
            )
            if unresolved_discogs_url:
                self._unsynced_discogs_link.set_uri(unresolved_discogs_url)
            if unresolved_marketplace_url:
                self._unsynced_marketplace_link.set_uri(unresolved_marketplace_url)
            self._unsynced_box.set_visible(True)
            return

        if not results:
            self._search_status.set_text(
                f'No synced releases matched "{query}".'
            )
            return

        self._search_status.set_text(
            f'{result_count} synced release{"s" if result_count != 1 else ""} matched "{query}".'
        )

        for item in results:
            row = Gtk.ListBoxRow()
            row.set_selectable(True)
            row.set_activatable(True)
            row.set_focusable(True)

            release_id = _as_int(item.get("discogs_release_id"))
            source = _as_str(item.get("source")).lower() or "collection"
            year = _as_int(item.get("year"))
            market_median = item.get("market_median")
            market_currency = _as_str(item.get("market_currency"))
            value_text = (
                f"median {format_price(market_median, market_currency)}"
                if isinstance(market_median, (int, float))
                else "value pending"
            )

            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            body.set_margin_top(8)
            body.set_margin_bottom(8)
            body.set_margin_start(8)
            body.set_margin_end(8)

            title = Gtk.Label(label=_as_str(item.get("search_display")) or f"Release {release_id}")
            title.set_xalign(0.0)
            title.set_wrap(True)
            title.add_css_class("ipod-value-list-label")
            body.append(title)

            meta_parts = [_source_label(source)]
            if year > 0:
                meta_parts.append(str(year))
            meta_parts.append(value_text)
            meta = Gtk.Label(label=" • ".join(meta_parts))
            meta.set_xalign(0.0)
            meta.set_wrap(True)
            meta.add_css_class("dim-label")
            body.append(meta)

            row.set_child(body)
            self._search_row_payloads[row] = (source, release_id)
            self._results_list.append(row)

        if (
            self._selected_source is not None
            and self._selected_release_id is not None
        ):
            self._sync_search_selection(self._selected_source, self._selected_release_id)

    def set_search_error(self, message: str) -> None:
        self._clear_results()
        self._unsynced_box.set_visible(False)
        self._search_counts.set_text("Search unavailable")
        self._search_status.set_text(f"Value search error: {message}")

    def _sync_search_selection(self, source: str, release_id: int) -> None:
        for row, payload in self._search_row_payloads.items():
            if payload == (source, int(release_id)):
                self._results_list.select_row(row)
                return
        self._results_list.unselect_all()

    def clear_selected_release(self) -> None:
        self._selected_source = None
        self._selected_release_id = None
        self._selected_source_chip.set_text("No selection")
        self._selected_title.set_text("Select a release to inspect value data.")
        self._selected_meta.set_text("")
        self._selected_status.set_text(
            "Search for a release or use See in Value Tab from Browse or Wantlist."
        )
        self._selected_market_summary.set_text("Market: n/a")
        self._selected_market_metrics.set_text("Metrics: n/a")
        self._selected_community_stats.set_text("Stats: n/a")
        self._selected_id_value.set_text("n/a")
        self._selected_year_value.set_text("n/a")
        self._selected_genres_value.set_text("n/a")
        self._selected_styles_value.set_text("n/a")
        self._selected_added_value.set_text("n/a")
        self._selected_synced_value.set_text("n/a")
        self._selected_mapping_value.set_text("n/a")
        self._selected_points_value.set_text("n/a")
        self._selected_notes.set_text("n/a")
        self._refresh_selected_button.set_sensitive(False)
        self._open_source_button.set_sensitive(False)
        self._open_source_button.set_label("Open in Browse")
        self._selected_discogs_link.set_sensitive(False)
        self._selected_discogs_link.set_uri("https://www.discogs.com")
        self._selected_marketplace_link.set_sensitive(False)
        self._selected_marketplace_link.set_uri("https://www.discogs.com")

    def set_selected_busy(self, message: str) -> None:
        self._refresh_selected_button.set_sensitive(False)
        self._open_source_button.set_sensitive(False)
        self._selected_status.set_text(message)

    def set_selected_error(self, message: str) -> None:
        if self._selected_source is not None and self._selected_release_id is not None:
            self._refresh_selected_button.set_sensitive(True)
            self._open_source_button.set_sensitive(True)
        self._selected_status.set_text(f"Value inspector error: {message}")

    def set_selected_release(self, item: dict[str, object]) -> None:
        source = _as_str(item.get("source")).lower() or "collection"
        release_id = _as_int(item.get("discogs_release_id"))
        self._selected_source = source
        self._selected_release_id = release_id if release_id > 0 else None

        artist = _as_str(item.get("artist")) or "Unknown Artist"
        title = _as_str(item.get("title")) or "Unknown Title"
        year = _as_int(item.get("year"))
        self._selected_source_chip.set_text(_source_label(source))
        self._selected_title.set_text(f"{artist} - {title}")
        meta_parts = []
        if year > 0:
            meta_parts.append(str(year))
        meta_parts.append(f"#{release_id}" if release_id > 0 else "Discogs ID n/a")
        self._selected_meta.set_text(" • ".join(meta_parts))
        self._selected_status.set_text(
            f"Showing cached value data from {_source_label(source).lower()}."
        )

        self._selected_market_summary.set_text(format_market_summary(item))
        self._selected_market_metrics.set_text(format_market_metrics(item))
        self._selected_community_stats.set_text(format_community_stats(item))
        self._selected_id_value.set_text(str(release_id) if release_id > 0 else "n/a")
        self._selected_year_value.set_text(str(year) if year > 0 else "n/a")
        self._selected_genres_value.set_text(format_discogs_terms(item.get("genres")))
        self._selected_styles_value.set_text(format_discogs_terms(item.get("styles")))
        self._selected_added_value.set_text(format_discogs_date(item.get("added_at")))
        self._selected_synced_value.set_text(
            format_discogs_date(item.get("last_synced_at"))
        )
        spotify_album_id = _as_str(item.get("spotify_album_id"))
        self._selected_mapping_value.set_text(spotify_album_id or "n/a")
        self._selected_points_value.set_text(
            str(_as_int(item.get("market_price_point_count")) or 0)
        )
        notes = _as_str(item.get("notes"))
        self._selected_notes.set_text(notes or "n/a")

        discogs_url = _as_str(item.get("discogs_release_url"))
        if discogs_url:
            self._selected_discogs_link.set_uri(discogs_url)
            self._selected_discogs_link.set_sensitive(True)
        else:
            self._selected_discogs_link.set_sensitive(False)
        marketplace_url = _as_str(item.get("discogs_marketplace_url"))
        if marketplace_url:
            self._selected_marketplace_link.set_uri(marketplace_url)
            self._selected_marketplace_link.set_sensitive(True)
        else:
            self._selected_marketplace_link.set_sensitive(False)

        self._refresh_selected_button.set_sensitive(True)
        self._open_source_button.set_sensitive(True)
        self._open_source_button.set_label(
            "Open in Wantlist" if source == "wantlist" else "Open in Browse"
        )
        self._sync_search_selection(source, release_id)
