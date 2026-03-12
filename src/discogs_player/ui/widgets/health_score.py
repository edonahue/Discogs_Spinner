"""Collection health score widget — shows overall health and per-bucket gaps."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


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
    return 0


def _as_float(value: object | None) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def _score_css_class(score: int) -> str:
    if score >= 80:
        return "success"
    if score >= 50:
        return "warning"
    return "error"


class HealthScoreWidget(Gtk.Box):
    def __init__(
        self,
        *,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)
        self.set_hexpand(True)
        self.set_vexpand(True)

        self._on_refresh = on_refresh

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_bottom(12)

        title = Gtk.Label(label="Collection Health Score")
        title.add_css_class("ipod-section-header")
        title.set_xalign(0.0)
        title.set_hexpand(True)
        header.append(title)

        self._refresh_btn = Gtk.Button(label="Refresh")
        self._refresh_btn.add_css_class("suggested-action")
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.append(self._refresh_btn)

        self.append(header)

        # Score hero section
        score_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        score_box.set_halign(Gtk.Align.CENTER)
        score_box.set_margin_bottom(20)

        self._score_label = Gtk.Label(label="—")
        self._score_label.add_css_class("title-1")
        self._score_label.set_halign(Gtk.Align.CENTER)
        score_box.append(self._score_label)

        self._score_subtitle = Gtk.Label(label="")
        self._score_subtitle.add_css_class("dim-label")
        self._score_subtitle.set_halign(Gtk.Align.CENTER)
        score_box.append(self._score_subtitle)

        self.append(score_box)

        # Buckets section label
        buckets_header = Gtk.Label(label="Gap Breakdown")
        buckets_header.add_css_class("heading")
        buckets_header.set_xalign(0.0)
        buckets_header.set_margin_bottom(8)
        self.append(buckets_header)

        # Buckets list
        self._buckets_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.append(self._buckets_box)

        # Empty/loading state
        self._status_label = Gtk.Label(label="No data loaded. Click Refresh.")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_margin_top(16)
        self._status_label.set_halign(Gtk.Align.CENTER)
        self.append(self._status_label)

    def _on_refresh_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_refresh:
            self._on_refresh()

    def set_busy(self, message: str = "Loading…") -> None:
        self._refresh_btn.set_sensitive(False)
        self._status_label.set_text(message)
        self._status_label.set_visible(True)

    def set_error(self, message: str) -> None:
        self._refresh_btn.set_sensitive(True)
        self._status_label.set_text(f"Error: {message}")
        self._status_label.set_visible(True)
        self._score_label.set_text("—")
        self._score_subtitle.set_text("")
        self._clear_buckets()

    def set_health(self, report: dict[str, object]) -> None:
        self._refresh_btn.set_sensitive(True)

        score = _as_int(report.get("score"))
        total_active = _as_int(report.get("total_active"))

        # Update score hero
        self._score_label.set_text(f"{score}/100")
        # Remove previous colour classes
        for cls in ("success", "warning", "error"):
            self._score_label.remove_css_class(cls)
        self._score_label.add_css_class(_score_css_class(score))

        self._score_subtitle.set_text(
            f"{total_active} active release{'s' if total_active != 1 else ''}"
        )

        # Update buckets
        buckets_raw = report.get("buckets")
        buckets: list[dict[str, object]] = (
            [dict(b) for b in buckets_raw if isinstance(b, dict)]
            if isinstance(buckets_raw, list)
            else []
        )

        self._clear_buckets()
        self._status_label.set_visible(False)

        for bucket in buckets:
            row = self._build_bucket_row(bucket, total_active)
            self._buckets_box.append(row)

        if not buckets:
            self._status_label.set_text("No buckets returned.")
            self._status_label.set_visible(True)

    def _clear_buckets(self) -> None:
        child = self._buckets_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._buckets_box.remove(child)
            child = next_child

    def _build_bucket_row(
        self, bucket: dict[str, object], total_active: int
    ) -> Gtk.Widget:
        label_text = _as_str(bucket.get("label")) or _as_str(bucket.get("name"))
        gap_count = _as_int(bucket.get("gap_count"))
        gap_pct = _as_float(bucket.get("gap_pct"))
        deduction = _as_float(bucket.get("deduction"))

        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # Label row: name on left, count+deduction on right
        label_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        name_label = Gtk.Label(label=label_text)
        name_label.set_xalign(0.0)
        name_label.set_hexpand(True)
        label_row.append(name_label)

        deduction_text = f"−{deduction:.0f} pts" if deduction > 0 else "OK"
        count_str = f"{gap_count} releases ({gap_pct:.1f}%)  {deduction_text}"
        count_label = Gtk.Label(label=count_str)
        count_label.add_css_class("dim-label")
        count_label.set_xalign(1.0)
        label_row.append(count_label)

        row.append(label_row)

        # Progress bar
        bar = Gtk.ProgressBar()
        fraction = gap_pct / 100.0
        bar.set_fraction(min(1.0, max(0.0, fraction)))
        if deduction > 0:
            bar.add_css_class("error" if deduction >= 15 else "warning")
        row.append(bar)

        return row
