from __future__ import annotations

import re
from pathlib import Path

import pytest

from discogs_player import __version__

fastapi = pytest.importorskip("fastapi")

from discogs_player_api.app import create_app


ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, "Could not find version field in pyproject.toml"
    return match.group(1)


def test_package_version_matches_pyproject() -> None:
    assert __version__ == _pyproject_version()


def test_api_version_matches_pyproject() -> None:
    assert create_app().version == _pyproject_version()
