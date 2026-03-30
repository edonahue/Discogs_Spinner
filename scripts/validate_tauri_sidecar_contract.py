#!/usr/bin/env python3
"""Validate Tauri sidecar naming and config contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import stat
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
TAURI_CONFIG_PATH = ROOT_DIR / "desktop_shell" / "src-tauri" / "tauri.conf.json"
SIDECAR_DIR = ROOT_DIR / "desktop_shell" / "src-tauri" / "binaries"
EXPECTED_EXTERNAL_BIN = "binaries/dplayer-api"


def expected_sidecar_name(target_triple: str) -> str:
    suffix = ".exe" if "-windows-" in target_triple else ""
    return f"dplayer-api-{target_triple}{suffix}"


def load_external_bins() -> list[str]:
    payload = json.loads(TAURI_CONFIG_PATH.read_text(encoding="utf-8"))
    bundle = payload.get("bundle")
    if not isinstance(bundle, dict):
        raise ValueError("tauri.conf.json is missing the bundle object.")
    external_bins = bundle.get("externalBin")
    if not isinstance(external_bins, list) or not all(
        isinstance(item, str) for item in external_bins
    ):
        raise ValueError("tauri.conf.json bundle.externalBin must be a list of strings.")
    return [str(item) for item in external_bins]


def validate_contract(
    *,
    target_triple: str,
    sidecar_path: Path,
    require_file: bool,
    check_executable: bool,
) -> None:
    external_bins = load_external_bins()
    if EXPECTED_EXTERNAL_BIN not in external_bins:
        raise ValueError(
            f"tauri.conf.json bundle.externalBin must include {EXPECTED_EXTERNAL_BIN!r}."
        )

    expected_name = expected_sidecar_name(target_triple)
    if sidecar_path.name != expected_name:
        raise ValueError(
            f"Expected sidecar filename {expected_name!r}, got {sidecar_path.name!r}."
        )

    if require_file and not sidecar_path.is_file():
        raise FileNotFoundError(f"Expected sidecar binary at {sidecar_path}.")

    if check_executable and require_file:
        mode = sidecar_path.stat().st_mode
        if not (mode & stat.S_IXUSR):
            raise PermissionError(f"Sidecar binary is not executable: {sidecar_path}.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="validate_tauri_sidecar_contract.py",
        description="Validate Tauri sidecar naming and config contract.",
    )
    parser.add_argument("--target-triple", required=True)
    parser.add_argument("--sidecar-path")
    parser.add_argument("--require-file", action="store_true")
    parser.add_argument("--check-executable", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    default_sidecar_path = SIDECAR_DIR / expected_sidecar_name(args.target_triple)
    sidecar_path = Path(args.sidecar_path) if args.sidecar_path else default_sidecar_path
    if not sidecar_path.is_absolute():
        sidecar_path = (ROOT_DIR / sidecar_path).resolve()

    try:
        validate_contract(
            target_triple=str(args.target_triple),
            sidecar_path=sidecar_path,
            require_file=bool(args.require_file),
            check_executable=bool(args.check_executable),
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "PASS: Tauri sidecar contract is valid for "
        f"{args.target_triple} ({os.path.relpath(sidecar_path, ROOT_DIR)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
