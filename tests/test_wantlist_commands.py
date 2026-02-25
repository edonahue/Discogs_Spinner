from __future__ import annotations

from discogs_player.cli import wantlist_commands


def test_sync_forwards_full_flag(monkeypatch):
    captured: dict[str, object] = {}

    def _run_sync_wantlist(**kwargs):
        captured.update(kwargs)
        return {"fetched_count": 1}

    monkeypatch.setattr(wantlist_commands, "run_sync_wantlist", _run_sync_wantlist)
    wantlist_commands.sync(full=True)

    assert captured["allow_empty_deactivate"] is True


def test_sync_json_renders_summary(monkeypatch):
    expected = {"fetched_count": 3}
    rendered: list[dict[str, object]] = []

    def _run_sync_wantlist(**kwargs):
        _ = kwargs
        return expected

    monkeypatch.setattr(wantlist_commands, "run_sync_wantlist", _run_sync_wantlist)
    monkeypatch.setattr(
        wantlist_commands,
        "render_json",
        lambda payload: rendered.append(payload),
    )

    wantlist_commands.sync(json_output=True)

    assert rendered == [expected]
