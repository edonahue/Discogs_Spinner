"""Public brand, attribution, and third-party notice strings."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

APP_NAME = "Spinner for Discogs"
REPO_URL = "https://github.com/edonahue/spinner-for-discogs"
ISSUES_URL = f"{REPO_URL}/issues"
DISCOGS_URL = "https://www.discogs.com/"
DISCOGS_ATTRIBUTION_TEXT = "Data provided by Discogs"
DISCOGS_ATTRIBUTION = {
    "text": DISCOGS_ATTRIBUTION_TEXT,
    "url": DISCOGS_URL,
}
DISCOGS_NON_AFFILIATION_NOTICE = (
    "This product uses a Discogs API but is not endorsed, certified or "
    "otherwise approved in any way by Discogs."
)


def package_version() -> str:
    try:
        return version("discogs_player")
    except PackageNotFoundError:
        return "0.2.3"


def discogs_user_agent() -> str:
    return f"SpinnerForDiscogs/{package_version()} (+{REPO_URL})"
