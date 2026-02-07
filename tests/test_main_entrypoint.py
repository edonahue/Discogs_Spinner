from __future__ import annotations

import builtins

from discogs_player import main as main_module


def test_main_handles_missing_cli_dependency(monkeypatch, capsys):
    real_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("discogs_player.cli.commands"):
            raise ModuleNotFoundError("No module named 'typer'", name="typer")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    exit_code = main_module.main(["status"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Missing Python dependency: typer" in captured.err
    assert "sudo apt install -y" in captured.err
