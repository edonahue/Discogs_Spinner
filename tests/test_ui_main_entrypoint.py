from __future__ import annotations

import builtins
import sys
from types import ModuleType

from discogs_player import ui_main


def test_ui_main_handles_missing_gi_dependency(monkeypatch, capsys):
    real_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "gi":
            raise ModuleNotFoundError("No module named 'gi'", name="gi")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    exit_code = ui_main.main(["--smoke-test", "--limit", "3"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Missing GUI dependency: gi" in captured.err
    assert "sudo apt install -y" in captured.err


def test_ui_main_passes_args_to_discogs_player_app(monkeypatch):
    fake_gi = ModuleType("gi")
    fake_gi.require_version = lambda *_args, **_kwargs: None  # type: ignore[attr-defined]

    captured: dict[str, object] = {}

    fake_main_window = ModuleType("discogs_player.ui.main_window")

    class FakeApp:
        def __init__(self, *, limit: int, preload_covers: bool, smoke_test: bool):
            captured["limit"] = limit
            captured["preload_covers"] = preload_covers
            captured["smoke_test"] = smoke_test
            self.exit_code = 7

        def run(self, argv):
            captured["argv"] = list(argv)

    fake_main_window.DiscogsPlayerApp = FakeApp  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "gi", fake_gi)
    monkeypatch.setitem(sys.modules, "discogs_player.ui.main_window", fake_main_window)

    exit_code = ui_main.main(["--limit", "17", "--no-preload-covers", "--smoke-test"])

    assert exit_code == 7
    assert captured["limit"] == 17
    assert captured["preload_covers"] is False
    assert captured["smoke_test"] is True
    assert captured["argv"] == ["dplayer-gui"]


def test_ui_main_default_limit_is_zero_for_full_catalogue(monkeypatch):
    fake_gi = ModuleType("gi")
    fake_gi.require_version = lambda *_args, **_kwargs: None  # type: ignore[attr-defined]

    captured: dict[str, object] = {}

    fake_main_window = ModuleType("discogs_player.ui.main_window")

    class FakeApp:
        def __init__(self, *, limit: int, preload_covers: bool, smoke_test: bool):
            captured["limit"] = limit
            captured["preload_covers"] = preload_covers
            captured["smoke_test"] = smoke_test
            self.exit_code = 0

        def run(self, argv):
            captured["argv"] = list(argv)

    fake_main_window.DiscogsPlayerApp = FakeApp  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "gi", fake_gi)
    monkeypatch.setitem(sys.modules, "discogs_player.ui.main_window", fake_main_window)

    exit_code = ui_main.main([])

    assert exit_code == 0
    assert captured["limit"] == 0
    assert captured["preload_covers"] is True
    assert captured["smoke_test"] is False
    assert captured["argv"] == ["dplayer-gui"]
