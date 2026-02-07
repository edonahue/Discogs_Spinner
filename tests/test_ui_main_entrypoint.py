from __future__ import annotations

import builtins

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

