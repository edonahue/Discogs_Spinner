"""Source-level assertions for YouTube link integration in album_detail and wantlist_detail."""

from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).parent.parent / "src" / "discogs_player" / "ui" / "widgets"


def _read(name: str) -> str:
    return (SRC / name).read_text()


def _parse(name: str) -> ast.Module:
    return ast.parse(_read(name))


def _has_import(tree: ast.Module, module: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module:
                    return True
        if isinstance(node, ast.ImportFrom):
            if node.module == module:
                return True
    return False


def _function_names(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _top_level_names(tree: ast.Module) -> set[str]:
    return {
        node.targets[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
    }


# --- album_detail.py ---

def test_album_detail_imports_urllib_parse() -> None:
    assert _has_import(_parse("album_detail.py"), "urllib.parse")


def test_album_detail_has_build_youtube_search_url() -> None:
    assert "_build_youtube_search_url" in _function_names(_parse("album_detail.py"))


def test_album_detail_has_set_youtube_link_method() -> None:
    assert "_set_youtube_link" in _function_names(_parse("album_detail.py"))


def test_album_detail_youtube_button_in_source() -> None:
    src = _read("album_detail.py")
    assert "_youtube_link_button" in src


def test_album_detail_dim_label_on_youtube_button() -> None:
    src = _read("album_detail.py")
    # dim-label must appear near youtube_link_button
    idx = src.find("_youtube_link_button")
    assert idx != -1
    snippet = src[idx: idx + 600]
    assert "dim-label" in snippet


def test_album_detail_tooltip_on_youtube_button() -> None:
    src = _read("album_detail.py")
    assert "Search YouTube for this release" in src


def test_album_detail_has_youtube_icon_svg() -> None:
    assert "_YOUTUBE_ICON_SVG" in _top_level_names(_parse("album_detail.py"))


def test_album_detail_has_make_youtube_icon() -> None:
    assert "_make_youtube_icon" in _function_names(_parse("album_detail.py"))


# --- wantlist_detail.py ---

def test_wantlist_detail_imports_urllib_parse() -> None:
    assert _has_import(_parse("wantlist_detail.py"), "urllib.parse")


def test_wantlist_detail_has_build_youtube_search_url() -> None:
    assert "_build_youtube_search_url" in _function_names(_parse("wantlist_detail.py"))


def test_wantlist_detail_has_set_youtube_link_method() -> None:
    assert "_set_youtube_link" in _function_names(_parse("wantlist_detail.py"))


def test_wantlist_detail_youtube_button_in_source() -> None:
    src = _read("wantlist_detail.py")
    assert "_youtube_link_button" in src


def test_wantlist_detail_dim_label_on_youtube_button() -> None:
    src = _read("wantlist_detail.py")
    idx = src.find("_youtube_link_button")
    assert idx != -1
    snippet = src[idx: idx + 600]
    assert "dim-label" in snippet


def test_wantlist_detail_tooltip_on_youtube_button() -> None:
    src = _read("wantlist_detail.py")
    assert "Search YouTube for this release" in src


def test_wantlist_detail_has_youtube_icon_svg() -> None:
    assert "_YOUTUBE_ICON_SVG" in _top_level_names(_parse("wantlist_detail.py"))


def test_wantlist_detail_has_make_youtube_icon() -> None:
    assert "_make_youtube_icon" in _function_names(_parse("wantlist_detail.py"))
