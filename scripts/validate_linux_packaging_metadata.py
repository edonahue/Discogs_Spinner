#!/usr/bin/env python3
"""Validate Linux desktop metadata shipped in the GTK .deb package."""

from __future__ import annotations

import configparser
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_PATH = ROOT / "packaging" / "deb" / "dplayer-gui.desktop"
METAINFO_PATH = ROOT / "packaging" / "deb" / "io.github.edonahue.DiscogsSpinner.metainfo.xml"


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _load_desktop_entry(path: Path) -> configparser.SectionProxy:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    with path.open(encoding="utf-8") as handle:
        parser.read_file(handle)
    if "Desktop Entry" not in parser:
        raise ValueError("missing [Desktop Entry] section")
    return parser["Desktop Entry"]


def validate_desktop_entry() -> list[str]:
    entry = _load_desktop_entry(DESKTOP_PATH)
    errors: list[str] = []
    expected = {
        "Type": "Application",
        "Name": "Discogs Spinner",
        "Exec": "dplayer-gui",
        "Icon": "discogs-spinner",
        "Terminal": "false",
    }
    for key, value in expected.items():
        if entry.get(key) != value:
            errors.append(f"desktop entry {key!r} must be {value!r}")

    comment = entry.get("Comment", "")
    if "vinyl collection" not in comment.lower():
        errors.append("desktop entry Comment must sell the vinyl collection value")

    categories = set(filter(None, entry.get("Categories", "").split(";")))
    for category in ("AudioVideo", "Audio", "Music"):
        if category not in categories:
            errors.append(f"desktop entry missing category {category!r}")

    keywords = entry.get("Keywords", "")
    for keyword in ("Discogs", "Records", "Vinyl", "Collection", "Wantlist", "Market Value"):
        if keyword not in keywords:
            errors.append(f"desktop entry missing keyword {keyword!r}")
    return errors


def _required_text(element: ET.Element, selector: str) -> str:
    found = element.find(selector)
    if found is None or not (found.text or "").strip():
        raise ValueError(f"missing required metainfo element: {selector}")
    return (found.text or "").strip()


def validate_metainfo() -> list[str]:
    root = ET.parse(METAINFO_PATH).getroot()
    errors: list[str] = []
    if root.tag != "component":
        errors.append("metainfo root must be <component>")
    if root.attrib.get("type") != "desktop-application":
        errors.append("metainfo component type must be desktop-application")

    expected = {
        "id": "io.github.edonahue.DiscogsSpinner",
        "metadata_license": "CC0-1.0",
        "project_license": "MIT",
        "name": "Discogs Spinner",
        "summary": "Browse, spin, and value your Discogs vinyl collection",
    }
    for selector, value in expected.items():
        try:
            actual = _required_text(root, selector)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if actual != value:
            errors.append(f"metainfo {selector!r} must be {value!r}")

    launchable = root.find("launchable")
    if launchable is None or launchable.attrib.get("type") != "desktop-id" or launchable.text != "discogs-spinner.desktop":
        errors.append("metainfo must launch discogs-spinner.desktop")

    description_text = " ".join(
        (node.text or "").strip() for node in root.findall("description/p") if (node.text or "").strip()
    )
    for marker in ("Discogs personal access token", "sync your collection and wantlist", "spin a random record"):
        if marker not in description_text:
            errors.append(f"metainfo description missing {marker!r}")

    binaries = {(node.text or "").strip() for node in root.findall("provides/binary")}
    for binary in ("dplayer", "dplayer-gui"):
        if binary not in binaries:
            errors.append(f"metainfo missing provided binary {binary!r}")

    screenshots = root.findall("screenshots/screenshot")
    if len(screenshots) < 2:
        errors.append("metainfo should include at least two screenshots")
    for screenshot in screenshots:
        image = screenshot.find("image")
        if image is None or not (image.text or "").startswith("https://"):
            errors.append("metainfo screenshots must use published https image URLs")
        caption = screenshot.find("caption")
        if caption is None or not (caption.text or "").strip():
            errors.append("metainfo screenshots must include captions")

    release = root.find("releases/release")
    if release is None or release.attrib.get("version") != "0.2.2":
        errors.append("metainfo latest release must be version 0.2.2")
    return errors


def main() -> int:
    if not DESKTOP_PATH.is_file():
        return _fail(f"missing desktop entry: {DESKTOP_PATH}")
    if not METAINFO_PATH.is_file():
        return _fail(f"missing AppStream metainfo: {METAINFO_PATH}")

    errors = validate_desktop_entry() + validate_metainfo()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("linux packaging metadata: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
