from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_build_deb_script_bundles_offline_wheelhouse():
    source = _read("scripts/build_deb.sh")
    for marker in (
        'PYTHON_BIN="${PYTHON_BIN:-}"',
        "for candidate in python3.10 python3",
        "build_deb.sh must build the wheelhouse with Python 3.10",
        'WHEEL_DIR="${STAGING_DIR}${INSTALL_PREFIX}/wheels"',
        'METAINFO_FILE="${ROOT_DIR}/packaging/deb/io.github.edonahue.SpinnerForDiscogs.metainfo.xml"',
        'cp "${ROOT_DIR}/LICENSE" "${DOC_DIR}/copyright"',
        'awk -F\'"\'',
        '"$PYTHON_BIN" -m pip wheel --wheel-dir "$WHEEL_DIR" \'.[web]\'',
        'cp "$METAINFO_FILE" "${METAINFO_DIR}/io.github.edonahue.SpinnerForDiscogs.metainfo.xml"',
        'Spinner for Discogs Contributors <discogs_player+maintainer@users.noreply.github.com>',
        'exec /opt/discogs-spinner/venv/bin/python -m discogs_player.main "$@"',
        'exec /opt/discogs-spinner/venv/bin/python -m discogs_player.api_main "$@"',
        'export DP_PERF_PROFILE="${DP_PERF_PROFILE:-quiet}"',
        'exec /opt/discogs-spinner/venv/bin/python -m discogs_player.ui_main "$@"',
    ):
        assert marker in source


def test_postinst_installs_only_from_bundled_wheelhouse():
    source = _read("packaging/deb/postinst")
    for marker in (
        'WHEEL_DIR="${INSTALL_PREFIX}/wheels"',
        'app_wheels=("${WHEEL_DIR}"/discogs_player-*.whl)',
        'No bundled discogs_player wheel found',
        'app_version="${app_version#discogs_player-}"',
        'discogs_player[web]==${app_version}',
        "--no-index",
        '--find-links "$WHEEL_DIR"',
    ):
        assert marker in source


def test_debian_clean_install_dockerfile_exercises_installed_runtime():
    source = _read("packaging/test/Dockerfile.debian-clean")
    for marker in (
        "apt-get install -y -q /tmp/dplayer.deb xvfb xauth",
        "test -x /opt/discogs-spinner/venv/bin/python",
        "ls /opt/discogs-spinner/wheels/discogs_player-*.whl",
        "dplayer --help >/dev/null",
        "command -v dplayer-api >/dev/null 2>&1",
        "import discogs_player; import discogs_player.ui_main; import discogs_player.api_main; import discogs_player_api.app; import fastapi; import uvicorn",
        "xvfb-run -a dplayer-gui --smoke-test --limit 1",
    ):
        assert marker in source


def test_installer_workflow_builds_gtk4_deb_with_python_310():
    source = _read(".github/workflows/installer_build.yml")
    for marker in (
        "build-gtk4-deb:",
        "name: GTK4 .deb (fpm)",
        "runs-on: ubuntu-22.04",
        "uses: actions/setup-python@v5",
        'python-version: "3.10"',
    ):
        assert marker in source


def test_linux_packaging_metadata_is_validated_before_release():
    validator = _read("scripts/validate_linux_packaging_metadata.py")
    metainfo = _read("packaging/deb/io.github.edonahue.SpinnerForDiscogs.metainfo.xml")
    workflow = _read(".github/workflows/installer_build.yml")
    hygiene = _read("scripts/prepublish_hygiene_check.sh")

    for marker in (
        "io.github.edonahue.SpinnerForDiscogs",
        "io.github.edonahue.SpinnerForDiscogs.desktop",
        "Discogs personal access token",
        "sync your collection and wantlist",
        "spin a random record",
        "screenshots",
        "0.2.3",
    ):
        assert marker in metainfo
        assert marker in validator

    for marker in (
        "Validate Linux desktop metadata",
        "python3 scripts/validate_linux_packaging_metadata.py",
        "Run GTK4 .deb lintian QA",
        "lintian --allow-root",
        "allowed_lintian_errors",
        "unexpected error-level GTK .deb issues",
    ):
        assert marker in workflow

    assert "scripts/validate_linux_packaging_metadata.py" in hygiene
