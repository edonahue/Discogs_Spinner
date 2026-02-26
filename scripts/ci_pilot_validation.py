#!/usr/bin/env python3
"""Clean-runner pilot validation for Windows/macOS CI hosts.

This script validates install and first-run command paths using built artifacts
inside isolated virtualenv and XDG profile directories.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any


def _run(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        rendered = " ".join(cmd)
        raise RuntimeError(
            f"command failed ({proc.returncode}): {rendered}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    return proc


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _latest_one(paths: list[Path], pattern: str) -> Path:
    if not paths:
        raise FileNotFoundError(f"missing required file: {pattern}")
    return paths[-1]


def _write_command_logs(
    logs_dir: Path,
    name: str,
    proc: subprocess.CompletedProcess[str],
) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / f"{name}.stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (logs_dir / f"{name}.stderr.txt").write_text(proc.stderr, encoding="utf-8")


def _record_json_output(
    proc: subprocess.CompletedProcess[str],
    *,
    name: str,
) -> Any:
    payload = (proc.stdout or "").strip()
    if not payload:
        raise RuntimeError(f"{name} produced empty stdout; expected JSON")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} produced invalid JSON: {exc}") from exc


def _assert(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def run_pilot_validation(
    *,
    workspace: Path,
    output_dir: Path,
    skip_dependency_resolution: bool,
) -> dict[str, Any]:
    artifacts_root = workspace / "dist" / "artifacts"
    core_tarball = _latest_one(
        sorted(artifacts_root.glob("**/discogs_player-core-*.tar.gz")),
        "dist/artifacts/**/discogs_player-core-*.tar.gz",
    )
    plus_tarball = _latest_one(
        sorted(artifacts_root.glob("**/discogs_player-plus-*.tar.gz")),
        "dist/artifacts/**/discogs_player-plus-*.tar.gz",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = output_dir / "commands"
    result: dict[str, Any] = {
        "platform": sys.platform,
        "python": sys.version,
        "workspace": str(workspace),
        "core_tarball": str(core_tarball),
        "plus_tarball": str(plus_tarball),
        "skip_dependency_resolution": skip_dependency_resolution,
        "commands": {},
        "assertions": [],
    }

    with tempfile.TemporaryDirectory(prefix="dplayer_pilot_validation_") as tmp:
        temp_root = Path(tmp)
        core_extract = temp_root / "core_artifact"
        plus_extract = temp_root / "plus_artifact"
        core_extract.mkdir(parents=True, exist_ok=True)
        plus_extract.mkdir(parents=True, exist_ok=True)

        with tarfile.open(core_tarball, "r:gz") as tgz:
            tgz.extractall(core_extract)
        with tarfile.open(plus_tarball, "r:gz") as tgz:
            tgz.extractall(plus_extract)

        core_wheel = _latest_one(
            sorted(core_extract.glob("discogs_player-*.whl")),
            "core artifact wheel",
        )
        plus_wheel = _latest_one(
            sorted(plus_extract.glob("discogs_player-*.whl")),
            "plus artifact wheel",
        )
        result["core_wheel"] = str(core_wheel)
        result["plus_wheel"] = str(plus_wheel)

        core_venv = temp_root / "core_venv"
        plus_venv = temp_root / "plus_venv"
        _run([sys.executable, "-m", "venv", str(core_venv)])
        _run([sys.executable, "-m", "venv", str(plus_venv)])
        core_python = _venv_python(core_venv)
        plus_python = _venv_python(plus_venv)

        _run([str(core_python), "-m", "pip", "install", "--upgrade", "pip"])
        _run([str(plus_python), "-m", "pip", "install", "--upgrade", "pip"])

        core_install_cmd = [str(core_python), "-m", "pip", "install"]
        plus_install_cmd = [str(plus_python), "-m", "pip", "install"]
        if skip_dependency_resolution:
            core_install_cmd.append("--no-deps")
            plus_install_cmd.append("--no-deps")
        core_install_cmd.append(str(core_wheel))
        plus_install_cmd.append(f"{plus_wheel}[spotify]")

        core_install = _run(core_install_cmd)
        plus_install = _run(plus_install_cmd)
        _write_command_logs(logs_dir, "core_install", core_install)
        _write_command_logs(logs_dir, "plus_install", plus_install)
        result["commands"]["core_install"] = {"returncode": core_install.returncode}
        result["commands"]["plus_install"] = {"returncode": plus_install.returncode}

        profile = temp_root / "clean_profile"
        config_dir = profile / "config"
        data_dir = profile / "data"
        cache_dir = profile / "cache"
        config_dir.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cli_env = os.environ.copy()
        cli_env.update(
            {
                "XDG_CONFIG_HOME": str(config_dir),
                "XDG_DATA_HOME": str(data_dir),
                "XDG_CACHE_HOME": str(cache_dir),
                "DISCOGS_TOKEN": "",
            }
        )

        def run_command(
            name: str,
            cmd: list[str],
            *,
            expected_rcs: set[int],
            parse_json: bool,
        ) -> tuple[subprocess.CompletedProcess[str], Any]:
            proc = _run(cmd, env=cli_env, check=False)
            _write_command_logs(logs_dir, name, proc)
            result["commands"][name] = {
                "returncode": proc.returncode,
                "cmd": cmd,
            }
            _assert(
                proc.returncode in expected_rcs,
                f"{name} returned {proc.returncode}, expected {sorted(expected_rcs)}",
            )
            payload: Any = None
            if parse_json:
                payload = _record_json_output(proc, name=name)
                result["commands"][name]["json"] = payload
            return proc, payload

        _, setup_json = run_command(
            "setup_json",
            [str(core_python), "-m", "discogs_player.main", "setup", "--json"],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(setup_json, dict), "setup_json payload must be object")
        _assert(
            setup_json.get("discogs", {}).get("configured") is False,
            "setup_json expected discogs configured=false in clean profile",
        )
        _assert(
            "discogs.com/settings/developers"
            in str(setup_json.get("links", {}).get("discogs_token_url") or ""),
            "setup_json missing Discogs token setup URL",
        )
        result["assertions"].append("setup_json clean-profile onboarding signals present")

        _, status_json = run_command(
            "status_json",
            [str(core_python), "-m", "discogs_player.main", "status", "--json"],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(status_json, dict), "status_json payload must be object")
        _assert(
            int(status_json.get("release_count_total") or 0) == 0,
            "status_json expected zero releases before import",
        )
        result["assertions"].append("status_json shows empty clean profile")

        sync_proc, _ = run_command(
            "sync_expected_missing_token",
            [str(core_python), "-m", "discogs_player.main", "sync"],
            expected_rcs={3},
            parse_json=False,
        )
        sync_output = f"{sync_proc.stdout}\n{sync_proc.stderr}"
        _assert(
            "DISCOGS_TOKEN is not set" in sync_output,
            "sync missing-token guidance not found",
        )
        result["assertions"].append("sync command path verified (expected missing token)")

        _, list_empty_json = run_command(
            "list_empty_json",
            [str(core_python), "-m", "discogs_player.main", "list", "--limit", "5", "--json"],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(list_empty_json, list), "list_empty_json payload must be list")
        _assert(len(list_empty_json) == 0, "list_empty_json expected empty list")
        result["assertions"].append("list command returns empty list before import")

        snapshot_path = temp_root / "snapshot.json"
        schema_proc = _run(
            [
                str(core_python),
                "-c",
                (
                    "from discogs_player.data.db import LATEST_SCHEMA_VERSION as v;"
                    "print(v)"
                ),
            ]
        )
        schema_version = int((schema_proc.stdout or "").strip())
        snapshot_payload = {
            "schema_version": schema_version,
            "release_count": 1,
            "settings": {},
            "releases": [
                {
                    "discogs_release_id": 41,
                    "artist": "CI Artist",
                    "title": "CI Album",
                    "year": 2001,
                    "genres": ["Rock"],
                    "styles": ["Alt"],
                    "thumb_url": None,
                    "cover_url": None,
                    "added_at": "2026-01-01T00:00:00Z",
                    "last_synced_at": "2026-01-01T00:00:00Z",
                    "is_active": 1,
                    "spotify_album_id": "spotify:album:ci-album",
                    "spotify_confidence": 0.99,
                    "spotify_last_checked_at": "2026-02-07T00:00:00Z",
                    "spotify_is_override": True,
                }
            ],
        }
        snapshot_path.write_text(json.dumps(snapshot_payload), encoding="utf-8")
        shutil.copy2(snapshot_path, output_dir / "snapshot.json")

        _, import_json = run_command(
            "import_json",
            [
                str(plus_python),
                "-m",
                "discogs_player.main",
                "import",
                "--input",
                str(snapshot_path),
                "--conflict-mode",
                "replace",
                "--json",
            ],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(import_json, dict), "import_json payload must be object")
        _assert(
            int(import_json.get("imported_release_count") or 0) == 1,
            "import_json expected imported_release_count=1",
        )
        result["assertions"].append("import command seeds one release for list/spin/play")

        _, list_after_json = run_command(
            "list_after_import_json",
            [str(plus_python), "-m", "discogs_player.main", "list", "--limit", "5", "--json"],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(list_after_json, list), "list_after_import_json payload must be list")
        _assert(len(list_after_json) >= 1, "list_after_import_json expected at least one row")
        result["assertions"].append("list command returns imported release rows")

        _, spin_json = run_command(
            "spin_json",
            [str(plus_python), "-m", "discogs_player.main", "spin", "--seed", "7", "--json"],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(spin_json, dict), "spin_json payload must be object")
        _assert(
            int(spin_json.get("discogs_release_id") or 0) == 41,
            "spin_json expected seeded release_id=41",
        )
        result["assertions"].append("spin command path verified on imported snapshot")

        _, play_open_json = run_command(
            "play_open_json",
            [
                str(plus_python),
                "-m",
                "discogs_player.main",
                "play",
                "41",
                "--open",
                "--json",
            ],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(play_open_json, dict), "play_open_json payload must be object")
        _assert(
            bool(play_open_json.get("spotify_open_url"))
            or bool(play_open_json.get("fallback_open_url")),
            "play_open_json expected spotify_open_url or fallback_open_url",
        )
        result["assertions"].append("play --open command path verified")

        _, doctor_json = run_command(
            "spotify_doctor_json",
            [
                str(plus_python),
                "-m",
                "discogs_player.main",
                "auth",
                "spotify-doctor",
                "--json",
            ],
            expected_rcs={0},
            parse_json=True,
        )
        _assert(isinstance(doctor_json, dict), "spotify_doctor_json payload must be object")
        _assert(
            "diagnosis" in doctor_json,
            "spotify_doctor_json expected diagnosis field",
        )
        result["assertions"].append("spotify auth-doctor command path verified")

        devices_proc, devices_json = run_command(
            "devices_json",
            [str(plus_python), "-m", "discogs_player.main", "devices", "--json"],
            expected_rcs={0, 3},
            parse_json=False,
        )
        if devices_proc.returncode == 0:
            devices_json = _record_json_output(devices_proc, name="devices_json")
            _assert(isinstance(devices_json, list), "devices_json success payload must be list")
            result["assertions"].append("devices command succeeded and returned list")
        else:
            device_output = f"{devices_proc.stdout}\n{devices_proc.stderr}"
            _assert(
                "Spotify access token not configured" in device_output,
                "devices_json expected missing-token guidance when rc=3",
            )
            result["assertions"].append("devices command path verified (expected missing token)")

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote pilot validation report: {report_path}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run clean-runner pilot validation from built artifacts."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Repository workspace root (default: current directory).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist/pilot-validation"),
        help="Directory for validation report and command logs.",
    )
    parser.add_argument(
        "--skip-dependency-resolution",
        action="store_true",
        help="Install wheels with --no-deps (for offline/local debugging).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    output_dir = args.output_dir.resolve()
    run_pilot_validation(
        workspace=workspace,
        output_dir=output_dir,
        skip_dependency_resolution=bool(args.skip_dependency_resolution),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
