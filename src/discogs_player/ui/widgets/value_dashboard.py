"""Market value dashboard widget for collection pricing insights."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from discogs_player.ui.utils.formatting import format_price

_REVEAL_STAGGER_MS = 60
_REVEAL_DURATION_MS = 220


def _clear_box_children(box: Gtk.Box) -> None:
    child = box.get_first_child()
    while child is not None:
        next_child = child.get_next_sibling()
        box.remove(child)
        child = next_child


def _as_float(value: object | None) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _as_int(value: object | None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _as_str(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


class ValueDashboard(Gtk.Box):
    def __init__(
        self,
        *,
        on_refresh: Callable[[], None] | None = None,
        on_release_selected: Callable[[int], None] | None = None,
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
        self.add_css_class("ipod-value-dashboard")

        self._on_release_selected = on_release_selected
        self._on_ops_controls_changed = on_ops_controls_changed
        self._on_refresh_missing_action = on_refresh_missing
        self._on_open_docs = on_open_docs
        self._syncing_ops_controls = False
        self._syncing_detector_filter_chips = False
        self._detector_filter_mode = "all"
        self._release_row_buttons_by_id: dict[int, list[Gtk.Button]] = {}
        self._highlighted_release_id: int | None = None

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_row.set_hexpand(True)
        self.append(header_row)

        title_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_column.set_hexpand(True)
        header_row.append(title_column)

        kicker = Gtk.Label(label="Market Snapshot")
        kicker.set_xalign(0.0)
        kicker.add_css_class("ipod-value-kicker")
        title_column.append(kicker)

        title = Gtk.Label(label="Collection Value Dashboard")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        title.add_css_class("title-3")
        title.add_css_class("ipod-value-dashboard-title")
        title_column.append(title)

        self._delta_chip = Gtk.Label(label="Median delta n/a")
        self._delta_chip.add_css_class("ipod-value-chip")
        header_row.append(self._delta_chip)

        refresh_button = Gtk.Button(label="Refresh Dashboard")
        refresh_button.add_css_class("pill")
        if on_refresh is not None:
            refresh_button.connect("clicked", lambda *_: on_refresh())
        self._refresh_dashboard_button = refresh_button
        header_row.append(refresh_button)

        self._subtitle = Gtk.Label(label="Load your collection to see market insights.")
        self._subtitle.set_xalign(0.0)
        self._subtitle.set_wrap(True)
        self._subtitle.add_css_class("ipod-value-subtitle")
        self.append(self._subtitle)

        ops_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ops_row.set_hexpand(True)
        ops_row.add_css_class("ipod-value-ops-row")
        self.append(ops_row)

        stale_days_label = Gtk.Label(label="Stale Days")
        stale_days_label.add_css_class("ipod-value-ops-label")
        ops_row.append(stale_days_label)

        self._stale_days_spin = Gtk.SpinButton()
        self._stale_days_spin.add_css_class("ipod-value-ops-spin")
        self._stale_days_spin.set_numeric(True)
        self._stale_days_spin.set_range(0, 3650)
        self._stale_days_spin.set_increments(1, 7)
        self._stale_days_spin.set_value(30)
        self._stale_days_spin.set_tooltip_text("Age threshold for stale market values.")
        self._stale_days_spin.connect(
            "value-changed", self._handle_ops_controls_changed
        )
        ops_row.append(self._stale_days_spin)

        refresh_limit_label = Gtk.Label(label="Refresh Limit")
        refresh_limit_label.add_css_class("ipod-value-ops-label")
        ops_row.append(refresh_limit_label)

        self._refresh_limit_spin = Gtk.SpinButton()
        self._refresh_limit_spin.add_css_class("ipod-value-ops-spin")
        self._refresh_limit_spin.set_numeric(True)
        self._refresh_limit_spin.set_range(1, 100000)
        self._refresh_limit_spin.set_increments(1, 250)
        self._refresh_limit_spin.set_value(10000)
        self._refresh_limit_spin.set_tooltip_text(
            "Maximum releases processed per market operation."
        )
        self._refresh_limit_spin.connect(
            "value-changed", self._handle_ops_controls_changed
        )
        ops_row.append(self._refresh_limit_spin)

        self._refresh_missing_button = Gtk.Button(label="Refresh Missing")
        self._refresh_missing_button.add_css_class("ipod-value-op-button")
        if on_refresh_missing is not None:
            self._refresh_missing_button.connect(
                "clicked", lambda *_: on_refresh_missing()
            )
        ops_row.append(self._refresh_missing_button)

        self._refresh_stale_button = Gtk.Button(label="Refresh Stale")
        self._refresh_stale_button.add_css_class("ipod-value-op-button")
        if on_refresh_stale is not None:
            self._refresh_stale_button.connect("clicked", lambda *_: on_refresh_stale())
        ops_row.append(self._refresh_stale_button)

        self._snapshot_now_button = Gtk.Button(label="Snapshot Now")
        self._snapshot_now_button.add_css_class("ipod-value-op-button")
        if on_snapshot_now is not None:
            self._snapshot_now_button.connect("clicked", lambda *_: on_snapshot_now())
        ops_row.append(self._snapshot_now_button)

        self._ops_spinner = Gtk.Spinner()
        self._ops_spinner.set_visible(False)
        ops_row.append(self._ops_spinner)

        self._ops_status = Gtk.Label(label="Market ops idle.")
        self._ops_status.set_xalign(0.0)
        self._ops_status.set_hexpand(True)
        self._ops_status.set_wrap(True)
        self._ops_status.add_css_class("ipod-value-ops-status")
        ops_row.append(self._ops_status)

        self._summary_revealer = self._build_revealer()
        self._charts_revealer = self._build_revealer()
        self._lists_revealer = self._build_revealer()
        self._trend_revealer = self._build_revealer()
        self._detector_revealer = self._build_revealer()

        # Store revealers for staggered animation
        self._dashboard_revealers = [
            self._summary_revealer,
            self._charts_revealer,
            self._lists_revealer,
            self._trend_revealer,
            self._detector_revealer,
        ]

        summary_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        summary_row.set_hexpand(True)
        self._summary_revealer.set_child(summary_row)
        self.append(self._summary_revealer)

        low_card, self._total_low_label = self._build_summary_card("Total Low")
        median_card, self._total_median_label = self._build_summary_card("Total Median")
        high_card, self._total_high_label = self._build_summary_card("Total High")
        low_card.add_css_class("ipod-value-card-low")
        median_card.add_css_class("ipod-value-card-median")
        high_card.add_css_class("ipod-value-card-high")
        summary_row.append(low_card)
        summary_row.append(median_card)
        summary_row.append(high_card)

        charts_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        charts_row.set_hexpand(True)
        charts_row.set_vexpand(False)
        self._charts_revealer.set_child(charts_row)
        self.append(self._charts_revealer)

        profile_section, self._value_profile_rows = self._build_section(
            "Collection Value Profile"
        )
        currency_section, self._currency_rows = self._build_section("Currency Mix")
        charts_row.append(profile_section)
        charts_row.append(currency_section)

        lists_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lists_row.set_hexpand(True)
        lists_row.set_vexpand(True)
        self._lists_revealer.set_child(lists_row)
        self.append(self._lists_revealer)

        top_section, self._top_rows = self._build_section("Top 25 Priced")
        bottom_section, self._bottom_rows = self._build_section("Bottom 25 Priced")
        lists_row.append(top_section)
        lists_row.append(bottom_section)

        trend_section, self._trend_rows = self._build_section(
            "Median Trend (Snapshots)"
        )
        trend_section.set_hexpand(True)
        self._trend_revealer.set_child(trend_section)
        self.append(self._trend_revealer)

        detector_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        detector_container.set_hexpand(True)
        detector_container.set_vexpand(True)
        self._detector_revealer.set_child(detector_container)
        self.append(self._detector_revealer)

        detector_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        detector_controls.set_hexpand(True)
        detector_container.append(detector_controls)

        detector_title = Gtk.Label(label="Detector")
        detector_title.set_xalign(0.0)
        detector_title.add_css_class("ipod-value-ops-label")
        detector_controls.append(detector_title)

        self._detector_confidence_chip = Gtk.Label(label="Detector confidence n/a")
        self._detector_confidence_chip.add_css_class("ipod-value-chip")
        detector_controls.append(self._detector_confidence_chip)

        detector_controls_spacer = Gtk.Box()
        detector_controls_spacer.set_hexpand(True)
        detector_controls.append(detector_controls_spacer)

        self._duplicate_only_chip = Gtk.ToggleButton(label="Duplicates only")
        self._duplicate_only_chip.add_css_class("ipod-value-filter-chip")
        self._duplicate_only_chip.connect(
            "toggled",
            lambda button: self._handle_detector_chip_toggled(button, "duplicates"),
        )
        detector_controls.append(self._duplicate_only_chip)

        self._variant_only_chip = Gtk.ToggleButton(label="Variants only")
        self._variant_only_chip.add_css_class("ipod-value-filter-chip")
        self._variant_only_chip.connect(
            "toggled",
            lambda button: self._handle_detector_chip_toggled(button, "variants"),
        )
        detector_controls.append(self._variant_only_chip)

        detector_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        detector_row.set_hexpand(True)
        detector_row.set_vexpand(True)
        detector_container.append(detector_row)

        self._duplicate_detector_section, self._duplicate_detector_rows = (
            self._build_section("Likely Duplicates")
        )
        self._variant_detector_section, self._variant_detector_rows = (
            self._build_section("Variant Families")
        )
        detector_row.append(self._duplicate_detector_section)
        detector_row.append(self._variant_detector_section)

        self._set_empty_state()

    def _set_market_ops_enabled(self, enabled: bool) -> None:
        self._refresh_dashboard_button.set_sensitive(enabled)
        self._stale_days_spin.set_sensitive(enabled)
        self._refresh_limit_spin.set_sensitive(enabled)
        self._refresh_missing_button.set_sensitive(enabled)
        self._refresh_stale_button.set_sensitive(enabled)
        self._snapshot_now_button.set_sensitive(enabled)

    def stale_days(self) -> int:
        return max(0, int(self._stale_days_spin.get_value_as_int()))

    def refresh_limit(self) -> int:
        return max(1, int(self._refresh_limit_spin.get_value_as_int()))

    def set_ops_controls(self, *, stale_days: int, refresh_limit: int) -> None:
        normalized_stale_days = max(0, int(stale_days))
        normalized_refresh_limit = max(1, int(refresh_limit))
        self._syncing_ops_controls = True
        try:
            self._stale_days_spin.set_value(normalized_stale_days)
            self._refresh_limit_spin.set_value(normalized_refresh_limit)
        finally:
            self._syncing_ops_controls = False

    def _handle_ops_controls_changed(self, _spin: Gtk.SpinButton) -> None:
        if self._syncing_ops_controls:
            return
        if self._on_ops_controls_changed is not None:
            self._on_ops_controls_changed()

    def set_ops_busy(self, message: str) -> None:
        self._set_market_ops_enabled(False)
        self._ops_spinner.set_visible(True)
        self._ops_spinner.start()
        self._ops_status.set_text(message)

    def set_ops_result(self, message: str) -> None:
        self._set_market_ops_enabled(True)
        self._ops_spinner.stop()
        self._ops_spinner.set_visible(False)
        self._ops_status.set_text(message)

    def _build_revealer(self) -> Gtk.Revealer:
        revealer = Gtk.Revealer()
        revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        revealer.set_transition_duration(_REVEAL_DURATION_MS)
        revealer.set_reveal_child(True)
        return revealer

    def _play_refresh_reveal(self) -> None:
        for revealer in self._dashboard_revealers:
            revealer.set_reveal_child(False)
        for index, revealer in enumerate(self._dashboard_revealers):
            GLib.timeout_add(
                _REVEAL_STAGGER_MS * (index + 1),
                self._reveal_block,
                revealer,
            )

    @staticmethod
    def _reveal_block(revealer: Gtk.Revealer) -> bool:
        revealer.set_reveal_child(True)
        return False

    def _build_summary_card(self, heading: str) -> tuple[Gtk.Frame, Gtk.Label]:
        frame = Gtk.Frame()
        frame.set_hexpand(True)
        frame.add_css_class("ipod-value-card")

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body.set_margin_top(10)
        body.set_margin_bottom(10)
        body.set_margin_start(10)
        body.set_margin_end(10)

        title = Gtk.Label(label=heading)
        title.set_xalign(0.0)
        title.add_css_class("ipod-value-card-title")
        body.append(title)

        amount = Gtk.Label(label="n/a")
        amount.set_xalign(0.0)
        amount.set_wrap(True)
        amount.add_css_class("ipod-value-card-amount")
        body.append(amount)

        frame.set_child(body)
        return frame, amount

    def _build_section(self, heading: str) -> tuple[Gtk.Frame, Gtk.Box]:
        frame = Gtk.Frame()
        frame.set_hexpand(True)
        frame.set_vexpand(True)
        frame.add_css_class("ipod-value-section")

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.set_margin_top(10)
        body.set_margin_bottom(10)
        body.set_margin_start(10)
        body.set_margin_end(10)

        title = Gtk.Label(label=heading)
        title.set_xalign(0.0)
        title.add_css_class("title-5")
        title.add_css_class("ipod-value-section-title")
        body.append(title)

        rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        rows.set_hexpand(True)
        rows.set_vexpand(True)
        body.append(rows)

        frame.set_child(body)
        return frame, rows

    def _build_bar_row(
        self,
        *,
        label: str,
        ratio: float,
        value_text: str,
    ) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        row.set_hexpand(True)
        row.add_css_class("ipod-value-bar-row")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top.set_hexpand(True)
        row.append(top)

        left = Gtk.Label(label=label)
        left.set_xalign(0.0)
        left.set_hexpand(True)
        left.add_css_class("ipod-value-bar-label")
        top.append(left)

        right = Gtk.Label(label=value_text)
        right.set_xalign(1.0)
        right.add_css_class("ipod-value-bar-value")
        top.append(right)

        bar = Gtk.ProgressBar()
        bar.set_hexpand(True)
        bar.set_fraction(max(0.0, min(1.0, ratio)))
        bar.add_css_class("ipod-value-bar")
        row.append(bar)
        return row

    @staticmethod
    def _format_amount(amount: object, *, currency_hint: str) -> str:
        if not isinstance(amount, (int, float)):
            return "n/a"
        return format_price(amount, currency_hint)

    def _format_price_row(self, item: dict[str, object], rank: int) -> str:
        artist = _as_str(item.get("artist")) or "Unknown Artist"
        title = _as_str(item.get("title")) or "Unknown Title"
        median_value = item.get("market_median")
        currency = _as_str(item.get("market_currency")).upper()
        value_text = format_price(median_value, currency)
        return f"{rank:02d}. {artist} - {title}  •  median {value_text}"

    def _parse_last_updated(self, value: object) -> str:
        raw = _as_str(value)
        if not raw:
            return "unknown"
        normalized = raw.replace("Z", "+00:00")
        try:
            timestamp = datetime.fromisoformat(normalized)
            return timestamp.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return raw

    def _set_empty_state(self) -> None:
        self._clear_release_row_registry()
        self._total_low_label.set_text("n/a")
        self._total_median_label.set_text("n/a")
        self._total_high_label.set_text("n/a")
        self._delta_chip.set_text("Median delta n/a")
        self._detector_confidence_chip.set_text("Detector confidence n/a")
        self._delta_chip.remove_css_class("is-positive")
        self._delta_chip.remove_css_class("is-negative")

        _clear_box_children(self._value_profile_rows)
        _clear_box_children(self._currency_rows)
        _clear_box_children(self._top_rows)
        _clear_box_children(self._bottom_rows)
        _clear_box_children(self._trend_rows)
        _clear_box_children(self._duplicate_detector_rows)
        _clear_box_children(self._variant_detector_rows)

        placeholder = Gtk.Label(
            label="No market value data yet. Run `dplayer value refresh --from-missing`."
        )
        placeholder.set_xalign(0.0)
        placeholder.set_wrap(True)
        placeholder.add_css_class("ipod-value-muted")
        self._value_profile_rows.append(placeholder)
        empty_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        empty_actions.set_halign(Gtk.Align.START)
        has_empty_actions = False
        if self._on_refresh_missing_action is not None:
            refresh_button = Gtk.Button(label="Refresh Market Values")
            refresh_button.add_css_class("ipod-value-op-button")
            refresh_button.connect(
                "clicked", lambda *_: self._on_refresh_missing_action()
            )
            empty_actions.append(refresh_button)
            has_empty_actions = True
        if self._on_open_docs is not None:
            docs_button = Gtk.Button(label="Open Docs")
            docs_button.add_css_class("ipod-value-op-button")
            docs_button.connect("clicked", lambda *_: self._on_open_docs())
            empty_actions.append(docs_button)
            has_empty_actions = True
        if has_empty_actions:
            self._value_profile_rows.append(empty_actions)

        self._currency_rows.append(
            self._build_muted_label("No currency data available.")
        )
        self._top_rows.append(self._build_muted_label("No priced releases available."))
        self._bottom_rows.append(
            self._build_muted_label("No priced releases available.")
        )
        self._trend_rows.append(
            self._build_muted_label("Capture snapshots with `dplayer value snapshot`.")
        )
        self._duplicate_detector_rows.append(
            self._build_muted_label("No duplicate groups detected.")
        )
        self._variant_detector_rows.append(
            self._build_muted_label("No variant families detected.")
        )
        self._set_detector_filter_mode("all", sync_buttons=True)

    def _build_muted_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_xalign(0.0)
        label.set_wrap(True)
        label.add_css_class("ipod-value-muted")
        return label

    def _clear_release_row_registry(self) -> None:
        self._release_row_buttons_by_id.clear()
        self._highlighted_release_id = None

    def _register_release_row_button(
        self, discogs_release_id: int, button: Gtk.Button
    ) -> None:
        self._release_row_buttons_by_id.setdefault(int(discogs_release_id), []).append(
            button
        )

    def highlight_release(self, discogs_release_id: int) -> bool:
        if self._highlighted_release_id is not None:
            for button in self._release_row_buttons_by_id.get(
                int(self._highlighted_release_id), []
            ):
                button.remove_css_class("is-highlighted")

        target_buttons = self._release_row_buttons_by_id.get(int(discogs_release_id), [])
        if not target_buttons:
            self._highlighted_release_id = None
            return False

        for button in target_buttons:
            button.add_css_class("is-highlighted")
        self._highlighted_release_id = int(discogs_release_id)
        target_buttons[0].grab_focus()
        return True

    def clear_release_highlight(self) -> None:
        if self._highlighted_release_id is None:
            return
        for button in self._release_row_buttons_by_id.get(
            int(self._highlighted_release_id), []
        ):
            button.remove_css_class("is-highlighted")
        self._highlighted_release_id = None

    def _append_release_rows(
        self,
        *,
        container: Gtk.Box,
        rows: list[dict[str, object]],
    ) -> None:
        _clear_box_children(container)
        if not rows:
            container.append(self._build_muted_label("No priced releases available."))
            return

        for rank, item in enumerate(rows, start=1):
            row_text = self._format_price_row(item, rank)
            release_id = item.get("discogs_release_id")
            if isinstance(release_id, int) and self._on_release_selected is not None:
                button = Gtk.Button()
                button.add_css_class("flat")
                button.add_css_class("ipod-value-list-row")
                button.set_hexpand(True)
                button.set_halign(Gtk.Align.FILL)
                text = Gtk.Label(label=row_text)
                text.set_xalign(0.0)
                text.set_wrap(True)
                text.add_css_class("ipod-value-list-label")
                button.set_child(text)
                button.connect(
                    "clicked",
                    lambda *_args, rid=release_id: self._on_release_selected(rid),
                )
                self._register_release_row_button(release_id, button)
                container.append(button)
            else:
                label = Gtk.Label(label=row_text)
                label.set_xalign(0.0)
                label.set_wrap(True)
                label.add_css_class("ipod-value-list-row")
                label.add_css_class("ipod-value-list-label")
                container.append(label)

    def set_error(self, message: str) -> None:
        self._subtitle.set_text(f"Dashboard unavailable: {message}")
        self._set_empty_state()

    def _set_detector_confidence_chip(self, score: object) -> None:
        if isinstance(score, (int, float)):
            normalized = max(0.0, min(1.0, float(score)))
            self._detector_confidence_chip.set_text(
                f"Detector confidence {normalized * 100:.0f}%"
            )
            return
        self._detector_confidence_chip.set_text("Detector confidence n/a")

    def _handle_detector_chip_toggled(
        self, button: Gtk.ToggleButton, mode: str
    ) -> None:
        if self._syncing_detector_filter_chips:
            return
        is_active = bool(button.get_active())
        if is_active:
            self._set_detector_filter_mode(mode, sync_buttons=True)
        elif self._detector_filter_mode == mode:
            self._set_detector_filter_mode("all", sync_buttons=True)

    def _set_detector_filter_mode(self, mode: str, *, sync_buttons: bool) -> None:
        normalized_mode = mode if mode in {"all", "duplicates", "variants"} else "all"
        self._detector_filter_mode = normalized_mode
        if sync_buttons:
            self._syncing_detector_filter_chips = True
            try:
                self._duplicate_only_chip.set_active(normalized_mode == "duplicates")
                self._variant_only_chip.set_active(normalized_mode == "variants")
            finally:
                self._syncing_detector_filter_chips = False
        self._apply_detector_filter()

    def _apply_detector_filter(self) -> None:
        show_duplicates = self._detector_filter_mode in {"all", "duplicates"}
        show_variants = self._detector_filter_mode in {"all", "variants"}
        self._duplicate_detector_section.set_visible(show_duplicates)
        self._variant_detector_section.set_visible(show_variants)

    def _build_detector_item_label(self, item: dict[str, object]) -> str:
        release_id = _as_int(item.get("discogs_release_id"))
        year = item.get("year")
        year_text = str(year) if isinstance(year, int) else "Unknown"
        median = item.get("market_median")
        currency = _as_str(item.get("market_currency"))
        median_text = format_price(median, currency)
        return f"#{release_id} • {year_text} • median {median_text}"

    def _append_detector_groups(
        self,
        *,
        container: Gtk.Box,
        groups: list[dict[str, object]],
        empty_text: str,
    ) -> None:
        _clear_box_children(container)
        if not groups:
            container.append(self._build_muted_label(empty_text))
            return

        for group in groups:
            group_label = _as_str(group.get("group_label")) or "Group"
            release_count = max(_as_int(group.get("release_count")), 0)
            confidence_percent_raw = group.get("confidence_percent")
            if isinstance(confidence_percent_raw, (int, float)):
                confidence_percent = int(
                    max(0, min(100, round(float(confidence_percent_raw))))
                )
                heading = f"{group_label} • {release_count} releases • {confidence_percent}% confidence"
            else:
                heading = f"{group_label} • {release_count} releases"
            expander = Gtk.Expander(label=heading)
            expander.add_css_class("ipod-value-detector-group")
            expander.set_expanded(False)

            rows_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            rows_box.set_margin_top(4)
            rows_box.set_margin_bottom(4)

            items_raw = group.get("items")
            items = items_raw if isinstance(items_raw, list) else []
            for item in items[:8]:
                if not isinstance(item, dict):
                    continue
                row_text = self._build_detector_item_label(item)
                release_id = item.get("discogs_release_id")
                if (
                    isinstance(release_id, int)
                    and self._on_release_selected is not None
                ):
                    button = Gtk.Button()
                    button.add_css_class("flat")
                    button.add_css_class("ipod-value-list-row")
                    button.set_hexpand(True)
                    button.set_halign(Gtk.Align.FILL)
                    text = Gtk.Label(label=row_text)
                    text.set_xalign(0.0)
                    text.set_wrap(True)
                    text.add_css_class("ipod-value-list-label")
                    button.set_child(text)
                    button.connect(
                        "clicked",
                        lambda *_args, rid=release_id: self._on_release_selected(rid),
                    )
                    self._register_release_row_button(release_id, button)
                    rows_box.append(button)
                else:
                    label = Gtk.Label(label=row_text)
                    label.set_xalign(0.0)
                    label.set_wrap(True)
                    label.add_css_class("ipod-value-list-label")
                    rows_box.append(label)

            expander.set_child(rows_box)
            container.append(expander)

    def set_dashboard(self, report: dict[str, object]) -> None:
        self._clear_release_row_registry()
        summary_raw = report.get("summary")
        summary = dict(summary_raw) if isinstance(summary_raw, dict) else {}
        coverage_raw = report.get("coverage")
        coverage = dict(coverage_raw) if isinstance(coverage_raw, dict) else {}

        currency_mix_raw = report.get("currency_mix")
        currency_mix = currency_mix_raw if isinstance(currency_mix_raw, list) else []
        currencies = [
            _as_str(item.get("currency"))
            for item in currency_mix
            if isinstance(item, dict) and _as_str(item.get("currency"))
        ]
        single_currency = currencies[0] if len(currencies) == 1 else ""
        currency_hint = single_currency if single_currency else ""

        self._total_low_label.set_text(
            self._format_amount(
                summary.get("total_lowest"), currency_hint=currency_hint
            )
        )
        self._total_median_label.set_text(
            self._format_amount(
                summary.get("total_median"), currency_hint=currency_hint
            )
        )
        self._total_high_label.set_text(
            self._format_amount(
                summary.get("total_highest"), currency_hint=currency_hint
            )
        )

        active = max(_as_int(coverage.get("active_release_count")), 0)
        priced = max(_as_int(coverage.get("priced_release_count")), 0)
        coverage_ratio = max(0.0, min(1.0, _as_float(coverage.get("ratio"))))
        unpriced = max(_as_int(coverage.get("unpriced_release_count")), 0)
        last_updated = self._parse_last_updated(
            summary.get("market_value_last_updated")
        )

        self._subtitle.set_text(
            (
                f"Priced {priced}/{active} releases ({coverage_ratio * 100:.1f}% coverage). "
                f"Unpriced: {unpriced}. Last update: {last_updated}."
            )
        )

        _clear_box_children(self._value_profile_rows)
        value_bands_raw = report.get("value_bands")
        value_bands = value_bands_raw if isinstance(value_bands_raw, list) else []
        if value_bands:
            for item in value_bands:
                if not isinstance(item, dict):
                    continue
                self._value_profile_rows.append(
                    self._build_bar_row(
                        label=_as_str(item.get("label")) or "Value",
                        ratio=max(0.0, min(1.0, _as_float(item.get("ratio")))),
                        value_text=self._format_amount(
                            item.get("amount"), currency_hint=currency_hint
                        ),
                    )
                )
        else:
            self._value_profile_rows.append(
                self._build_muted_label("No value-band data available.")
            )

        _clear_box_children(self._currency_rows)
        if currency_mix:
            for item in currency_mix:
                if not isinstance(item, dict):
                    continue
                currency = _as_str(item.get("currency")) or "Unknown"
                count = max(_as_int(item.get("count")), 0)
                ratio = max(0.0, min(1.0, _as_float(item.get("ratio"))))
                self._currency_rows.append(
                    self._build_bar_row(
                        label=currency,
                        ratio=ratio,
                        value_text=f"{count} releases",
                    )
                )
        else:
            self._currency_rows.append(
                self._build_muted_label("No currency data available.")
            )

        top_priced_raw = report.get("top_priced")
        top_priced = (
            [item for item in top_priced_raw if isinstance(item, dict)]
            if isinstance(top_priced_raw, list)
            else []
        )
        bottom_priced_raw = report.get("bottom_priced")
        bottom_priced = (
            [item for item in bottom_priced_raw if isinstance(item, dict)]
            if isinstance(bottom_priced_raw, list)
            else []
        )

        self._append_release_rows(container=self._top_rows, rows=top_priced)
        self._append_release_rows(container=self._bottom_rows, rows=bottom_priced)

        _clear_box_children(self._trend_rows)
        trend_raw = report.get("trend")
        trend = dict(trend_raw) if isinstance(trend_raw, dict) else {}
        delta_total = trend.get("window_delta_total_median")
        delta_percent = trend.get("window_delta_total_median_percent")
        self._delta_chip.remove_css_class("is-positive")
        self._delta_chip.remove_css_class("is-negative")
        if isinstance(delta_total, (int, float)):
            sign = "+" if float(delta_total) >= 0 else "-"
            base = f"Median {sign}{abs(float(delta_total)):,.2f}"
            if isinstance(delta_percent, (int, float)):
                base = f"{base} ({sign}{abs(float(delta_percent)):.1f}%)"
            self._delta_chip.set_text(base)
            if float(delta_total) >= 0:
                self._delta_chip.add_css_class("is-positive")
            else:
                self._delta_chip.add_css_class("is-negative")
        else:
            self._delta_chip.set_text("Median delta n/a")
        points_raw = trend.get("points")
        points = points_raw if isinstance(points_raw, list) else []
        if points:
            # Render a compact window to keep this section dense and scannable.
            for item in points[-8:]:
                if not isinstance(item, dict):
                    continue
                self._trend_rows.append(
                    self._build_bar_row(
                        label=_as_str(item.get("label")) or "(unknown)",
                        ratio=max(0.0, min(1.0, _as_float(item.get("ratio")))),
                        value_text=f"{_as_float(item.get('total_median')):,.2f}",
                    )
                )
        else:
            self._trend_rows.append(
                self._build_muted_label(
                    "Capture snapshots with `dplayer value snapshot`."
                )
            )

        detector_raw = report.get("detector")
        detector = dict(detector_raw) if isinstance(detector_raw, dict) else {}
        self._set_detector_confidence_chip(detector.get("confidence_score"))
        duplicate_groups_raw = detector.get("duplicate_groups")
        duplicate_groups = (
            [item for item in duplicate_groups_raw if isinstance(item, dict)]
            if isinstance(duplicate_groups_raw, list)
            else []
        )
        variant_groups_raw = detector.get("variant_groups")
        variant_groups = (
            [item for item in variant_groups_raw if isinstance(item, dict)]
            if isinstance(variant_groups_raw, list)
            else []
        )
        self._append_detector_groups(
            container=self._duplicate_detector_rows,
            groups=duplicate_groups,
            empty_text="No duplicate groups detected.",
        )
        self._append_detector_groups(
            container=self._variant_detector_rows,
            groups=variant_groups,
            empty_text="No variant families detected.",
        )
        self._apply_detector_filter()

        self._play_refresh_reveal()
