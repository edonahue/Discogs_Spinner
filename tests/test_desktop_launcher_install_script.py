from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_install_desktop_app_launcher_includes_logging_and_runtime_fallback():
    source = _script_text("scripts/install_desktop_app.sh")
    for marker in (
        'LOG_PATH="${LOG_DIR}/gui-launch.log"',
        'export DP_PERF_PROFILE="${DP_PERF_PROFILE:-game}"',
        "notify_failure()",
        "run_with_python()",
        'run_with_python "${VENV_PY}" "venv"',
        'run_with_python "${SYS_PYTHON}" "system"',
        'echo "Discogs Spinner launcher failed. See ${LOG_PATH}" >&2',
    ):
        assert marker in source
