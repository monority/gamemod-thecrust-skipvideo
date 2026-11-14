#!/usr/bin/env python3
"""Pack the mod sources into a .pak.

Reads `SkipCinematics/` and writes `output/zzzzzzzz_SkipCinematics_P.pak`.
Use `--install` to also copy the result into the game's `~mods` folder.

The pak keeps eight leading "z": UE4 mounts paks in alphabetical order and the
last one mounted wins, so it has to sort after the game's `pakchunk*` files and
after other mods. Do not rename it without a reason.

Usage:
  python tools/build_pak.py              # build only
  python tools/build_pak.py --install    # build and copy into ~mods
"""
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import thecrust_pak  # noqa: E402

SOURCES = ROOT / "sources"
OUTPUT = ROOT / "output"
PAK_NAME = "zzzzzzzz_SkipCinematics_P.pak"
GAME_MODS = Path(
    os.environ.get(
        "THECRUST_PAKS",
        r"C:\Games\The Crust\TheCrust\Content\Paks\~mods",
    )
)
ASSET_SUFFIXES = (".uasset", ".uexp")


def _fail(action: str, path: Path, exc: Exception) -> SystemExit:
    return SystemExit(f"{action} failed: {path} ({exc})")


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except (OSError, ValueError) as exc:
        raise _fail("Read", path, exc) from exc


def ensure_dir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        raise _fail("Create directory", path, exc) from exc


def copy_file(src: Path, dst: Path) -> None:
    try:
        shutil.copy2(src, dst)
    except (OSError, ValueError) as exc:
        raise _fail("Copy", src, exc) from exc


def collect() -> list[Path]:
    """Return the asset files to pack, sorted for a stable archive."""
    try:
        return sorted(
            path
            for path in SOURCES.rglob("*")
            if path.is_file() and path.suffix in ASSET_SUFFIXES
        )
    except (OSError, ValueError) as exc:
        raise _fail("Scan", SOURCES, exc) from exc


def main(argv: list[str]) -> int:
    install = "--install" in argv

    if not SOURCES.is_dir():
        print(f"Source folder missing: {SOURCES}")
        return 1

    files = collect()
    if not files:
        print(f"No .uasset/.uexp found under {SOURCES}")
        return 1

    stage = Path(tempfile.mkdtemp(prefix="thecrust_pak_"))
    for src in files:
        dst = stage / src.relative_to(SOURCES)
        ensure_dir(dst.parent)
        copy_file(src, dst)

    ensure_dir(OUTPUT)
    out = OUTPUT / PAK_NAME
    thecrust_pak.cmd_pack(str(stage), str(out))

    payload = read_bytes(out)
    print(f"files           : {len(files)}")
    print(f"pak             : {out}")
    print(f"size            : {len(payload)} bytes")
    print(f"sha256          : {hashlib.sha256(payload).hexdigest()}")

    if install:
        if GAME_MODS.is_dir():
            target = GAME_MODS / PAK_NAME
            copy_file(out, target)
            print(f"installed       : {target}")
        else:
            print(f"game folder not found: {GAME_MODS}")
            print("copy the pak manually, or set THECRUST_PAKS")
    else:
        print("not installed    : pass --install to copy it into ~mods")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
