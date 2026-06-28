"""Compact collection summary cards for the browse page."""

from __future__ import annotations

from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from discogs_player.ui.utils.coerce import as_int as _as_int
from discogs_player.ui.utils.coerce import as_optional_float as _as_float
from discogs_player.ui.utils.coerce import as_str as _as_str
from discogs_player.ui.utils.formatting import format_price


def _format_local_datetime(value: object | None) -> str:
    text = _as_str(value)
    if not text:
        return "—"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    local = dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M")


def _format_total_median(value: float, currency: str, *, mixed_currencies: bool) -> str:
    if mixed_currencies:
        return f"{value:,.2f}"
    return format_price(value, currency)


class CollectionSummaryWidget(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_hexpand(True)
        self.add_css_class("ipod-collection-summary")

        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_row.set_hexpand(True)
        self.append(header_row)

        title = Gtk.Label(label="Collection Summary")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        title.add_css_class("ipod-value-section-title")
        header_row.append(title)

        self._subtitle = Gtk.Label(label="Filtered totals across all matching releases.")
        self._subtitle.set_xalign(1.0)
        self._subtitle.add_css_class("ipod-collection-summary-subtitle")
        header_row.append(self._subtitle)

        cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cards.set_hexpand(True)
        self.append(cards)

        lp_card, self._lp_value, self._lp_meta = self._build_card("LPs")
        rpm45_card, self._rpm45_value, self._rpm45_meta = self._build_card("45s")
        median_card, self._median_value, self._median_meta = self._build_card("Median")
        recent_card, self._recent_value, self._recent_meta = self._build_card(
            "Most Recently Added"
        )

        lp_card.add_css_class("ipod-collection-card-accent")
        rpm45_card.add_css_class("ipod-collection-card-accent")
        median_card.add_css_class("ipod-collection-card-highlight")
        recent_card.add_css_class("ipod-collection-card-recent")

        cards.append(lp_card)
        cards.append(rpm45_card)
        cards.append(median_card)
        cards.append(recent_card)

        self._status = Gtk.Label(label="")
        self._status.set_xalign(0.0)
        self._status.set_wrap(True)
        self._status.add_css_class("ipod-collection-summary-status")
        self.append(self._status)

        self.set_busy()

    def _build_card(self, title_text: str) -> tuple[Gtk.Box, Gtk.Label, Gtk.Label]:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.set_hexpand(True)
        card.set_margin_top(0)
        card.set_margin_bottom(0)
        card.set_margin_start(0)
        card.set_margin_end(0)
        card.add_css_class("ipod-panel")
        card.add_css_class("ipod-collection-card")

        title = Gtk.Label(label=title_text)
        title.set_xalign(0.0)
        title.add_css_class("ipod-collection-card-title")
        card.append(title)

        value = Gtk.Label(label="—")
        value.set_xalign(0.0)
        value.add_css_class("ipod-collection-card-value")
        card.append(value)

        meta = Gtk.Label(label="")
        meta.set_xalign(0.0)
        meta.set_wrap(True)
        meta.add_css_class("ipod-collection-card-meta")
        card.append(meta)

        return card, value, meta

    def set_busy(self, message: str = "Loading filtered summary…") -> None:
        self._subtitle.set_text("Filtered totals across all matching releases.")
        self._lp_value.set_text("—")
        self._lp_meta.set_text("Waiting for data")
        self._rpm45_value.set_text("—")
        self._rpm45_meta.set_text("Waiting for data")
        self._median_value.set_text("—")
        self._median_meta.set_text("Waiting for data")
        self._recent_value.set_text("—")
        self._recent_meta.set_text("Waiting for data")
        self._status.set_text(message)

    def set_error(self, message: str) -> None:
        self._subtitle.set_text("Filtered totals unavailable.")
        self._lp_value.set_text("—")
        self._lp_meta.set_text("Summary unavailable")
        self._rpm45_value.set_text("—")
        self._rpm45_meta.set_text("Summary unavailable")
        self._median_value.set_text("—")
        self._median_meta.set_text("Summary unavailable")
        self._recent_value.set_text("—")
        self._recent_meta.set_text("Summary unavailable")
        self._status.set_text(f"Summary error: {message}")

    def set_summary(self, report: dict[str, object]) -> None:
        release_count = _as_int(report.get("release_count"))
        format_counts_ready = bool(report.get("format_counts_ready"))
        priced_release_count = _as_int(report.get("priced_release_count"))
        total_median = _as_float(report.get("total_median"))
        median_currency = _as_str(report.get("median_currency"))
        mixed_currencies = bool(report.get("mixed_currencies"))
        recent_added_at = _as_str(report.get("most_recent_added_at"))
        recent_artist = _as_str(report.get("most_recent_release_artist"))
        recent_title = _as_str(report.get("most_recent_release_title"))

        self._subtitle.set_text(
            f"{release_count} matching release{'s' if release_count != 1 else ''} across the current filters."
        )

        if format_counts_ready:
            lp_count = _as_int(report.get("lp_count"))
            rpm45_count = _as_int(report.get("rpm45_count"))
            self._lp_value.set_text(str(lp_count))
            self._lp_meta.set_text(
                f"{release_count - lp_count} other format match{'es' if release_count - lp_count != 1 else ''}"
                if release_count > 0
                else "No matching releases"
            )
            self._rpm45_value.set_text(str(rpm45_count))
            self._rpm45_meta.set_text(
                "Explicit Discogs 45 / 45 RPM format tags"
                if release_count > 0
                else "No matching releases"
            )
        else:
            sync_hint = "Run a fresh sync to populate LP/45 format tags."
            self._lp_value.set_text("—")
            self._lp_meta.set_text(sync_hint)
            self._rpm45_value.set_text("—")
            self._rpm45_meta.set_text(sync_hint)

        if total_median is None or priced_release_count <= 0:
            self._median_value.set_text("—")
            self._median_meta.set_text("No priced releases in the current result set")
        else:
            self._median_value.set_text(
                _format_total_median(
                    total_median,
                    median_currency,
                    mixed_currencies=mixed_currencies,
                )
            )
            if mixed_currencies:
                self._median_meta.set_text(
                    f"Summed across {priced_release_count} priced releases with mixed currencies"
                )
            else:
                self._median_meta.set_text(
                    f"Summed across {priced_release_count} priced releases"
                )

        self._recent_value.set_text(_format_local_datetime(recent_added_at))
        if recent_artist or recent_title:
            label = " - ".join(part for part in (recent_artist, recent_title) if part)
            self._recent_meta.set_text(label)
        else:
            self._recent_meta.set_text("No added timestamp available")

        self._status.set_text("")
