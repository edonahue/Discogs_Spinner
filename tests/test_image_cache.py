from __future__ import annotations

import hashlib
from pathlib import Path

from discogs_player.services import image_cache


class _FakeResponse:
    def __init__(self, data: bytes, content_type: str = "image/jpeg"):
        self._data = data
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        _ = (exc_type, exc, tb)
        return False

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self._data
        return self._data[:size]


def test_get_or_fetch_cover_path_caches_once(isolated_xdg, monkeypatch):
    calls = {"count": 0}

    def _fake_urlopen(request, timeout=None):
        _ = (request, timeout)
        calls["count"] += 1
        return _FakeResponse(b"image-bytes")

    monkeypatch.setattr(image_cache.urllib.request, "urlopen", _fake_urlopen)

    url = "https://example.test/cover.jpg"
    first = image_cache.get_or_fetch_cover_path(url)
    second = image_cache.get_or_fetch_cover_path(url)

    assert first is not None
    assert second == first
    assert calls["count"] == 1
    assert Path(first).exists()
    assert Path(first).suffix == ".jpg"
    assert Path(first).read_bytes() == b"image-bytes"


def test_get_or_fetch_cover_path_rejects_non_image_content(isolated_xdg, monkeypatch):
    def _fake_urlopen(request, timeout=None):
        _ = (request, timeout)
        return _FakeResponse(b"<html>not an image</html>", content_type="text/html")

    monkeypatch.setattr(image_cache.urllib.request, "urlopen", _fake_urlopen)
    result = image_cache.get_or_fetch_cover_path("https://example.test/not-image")
    assert result is None


def test_get_or_fetch_cover_path_rejects_invalid_url(isolated_xdg):
    assert image_cache.get_or_fetch_cover_path(None) is None
    assert image_cache.get_or_fetch_cover_path("") is None
    assert image_cache.get_or_fetch_cover_path("file:///tmp/test.jpg") is None


def test_get_or_fetch_cover_path_migrates_legacy_img_cache(isolated_xdg, monkeypatch):
    calls = {"count": 0}

    def _fake_urlopen(request, timeout=None):
        _ = (request, timeout)
        calls["count"] += 1
        return _FakeResponse(b"new-image-bytes")

    monkeypatch.setattr(image_cache.urllib.request, "urlopen", _fake_urlopen)

    url = "https://example.test/legacy-cover.jpeg"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    legacy = image_cache.cover_cache_dir() / f"{digest}.img"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(b"\xff\xd8\xfflegacy-jpeg-bytes")

    resolved = image_cache.get_or_fetch_cover_path(url)

    assert resolved is not None
    resolved_path = Path(resolved)
    assert resolved_path.suffix == ".jpg"
    assert resolved_path.exists()
    assert resolved_path.read_bytes() == b"\xff\xd8\xfflegacy-jpeg-bytes"
    assert not legacy.exists()
    assert calls["count"] == 0
