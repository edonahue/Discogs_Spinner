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
        'awk -F\'"\'',
        '"$PYTHON_BIN" -m pip wheel --wheel-dir "$WHEEL_DIR" \'.[web]\'',
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
    marker = """build-gtk4-deb:
    name: GTK4 .deb (fpm)
    runs-on: ubuntu-22.04
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
"""
    assert marker in source
