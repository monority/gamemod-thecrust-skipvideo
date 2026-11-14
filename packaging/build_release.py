#!/usr/bin/env python3
"""Build the distribution archives from output/.

Produces:

  dist/SkipCinematics/            pak + README (archive payload)
  dist/SkipCinematics_v<ver>.zip  archive to publish
  dist/SHA256SUMS.txt
  dist/NEXUS_MODPAGE.md
  nexus/                          upload-ready copy (zip + thumbnail + texts)

Files are written in place (overwritten), never deleted: re-running the script
simply refreshes the distribution.

The pak keeps eight leading "z": paks are mounted in alphabetical order and the
last one mounted wins, so it has to sort after the game's `pakchunk*` files.

Usage:
  python packaging/build_release.py
"""
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT = ROOT / "output"
DIST = ROOT / "dist"
NEXUS = ROOT / "nexus"

VERSION = "1.0.0"
PAK = "zzzzzzzz_SkipCinematics_P.pak"
THUMBNAIL = ROOT / "thumbnail.png"


def _fail(action: str, path: Path, exc: Exception) -> SystemExit:
    return SystemExit(f"{action} failed: {path} ({exc})")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise _fail("Read", path, exc) from exc


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except (OSError, ValueError) as exc:
        raise _fail("Read", path, exc) from exc


def write_text(path: Path, text: str) -> None:
    try:
        path.write_text(text, encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise _fail("Write", path, exc) from exc


def ensure_dir(path: Path) -> None:
    """Create a directory (and its parents) if it does not exist."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        raise _fail("Create directory", path, exc) from exc


def copy_file(src: Path, dst: Path) -> None:
    try:
        shutil.copy2(src, dst)
    except (OSError, ValueError) as exc:
        raise _fail("Copy", src, exc) from exc


def sha256(path: Path) -> str:
    return hashlib.sha256(read_bytes(path)).hexdigest()


def file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except (OSError, ValueError) as exc:
        raise _fail("Read size", path, exc) from exc


def build_zip(archive: Path, entries: list) -> None:
    """Ecrit une archive reproductible (horodatages figes)."""
    try:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for src, arcname in entries:
                info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                zf.writestr(info, read_bytes(src))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise _fail("Create archive", archive, exc) from exc


def check_zip(archive: Path, member: str, expected: bytes) -> str | None:
    """Return an error message, or None when the archive is valid."""
    try:
        with zipfile.ZipFile(archive) as zf:
            broken = zf.testzip()
            if broken:
                return f"corrupted entry: {broken}"
            inside = zf.read(member)
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        return f"unreadable archive: {exc}"
    if hashlib.sha256(inside).digest() != hashlib.sha256(expected).digest():
        return "the pak inside the archive differs from the source pak"
    return None


def main() -> int:
    source = OUTPUT / PAK
    if not source.exists():
        print(f"Missing pak: {source}")
        print("Run this first: python tools/build_pak.py")
        return 1

    for folder in (DIST, NEXUS):
        ensure_dir(folder)

    payload = DIST / "SkipCinematics"
    ensure_dir(payload)
    copy_file(source, payload / PAK)
    write_text(payload / "README.md", read_text(HERE / "README_ARCHIVE.md").rstrip() + "\n")

    archive = DIST / f"SkipCinematics_v{VERSION}.zip"
    build_zip(
        archive,
        [(payload / PAK, PAK), (payload / "README.md", "README.md")],
    )

    problem = check_zip(archive, PAK, read_bytes(source))
    if problem:
        print(problem)
        return 1

    digest = sha256(archive)
    write_text(DIST / "SHA256SUMS.txt", f"{digest}  {archive.name}\n")
    copy_file(HERE / "MODPAGE.md", DIST / "NEXUS_MODPAGE.md")

    copy_file(archive, NEXUS / archive.name)
    copy_file(HERE / "MODPAGE.md", NEXUS / "MODPAGE.txt")
    write_text(NEXUS / "SHA256SUMS.txt", f"{digest}  {archive.name}\n")
    if THUMBNAIL.exists():
        copy_file(THUMBNAIL, NEXUS / "thumbnail.png")

    checklist = (
        "NEXUSMODS - UPLOAD CHECKLIST\n"
        "============================\n\n"
        f"File to upload : {archive.name}\n"
        "Thumbnail      : thumbnail.png\n"
        "Description    : copy MODPAGE.txt\n\n"
        "ARCHIVE CONTENT\n"
        f"  {PAK}   the mod\n"
        "  README.md          install / limitations\n\n"
        "INSTALL PATH\n"
        r"  The Crust\TheCrust\Content\Paks\~mods" + "\n\n"
        "CHECKSUM\n"
        f"  {digest}\n"
    )
    write_text(NEXUS / "README.txt", checklist)

    print(f"source pak      : {PAK} ({file_size(source)} bytes)")
    print(f"archive         : {archive.name} ({file_size(archive) / 2**20:.2f} MiB)")
    print(f"sha256          : {digest}")
    print(f"archive content : README.md + {PAK}")
    print("dist/           : SkipCinematics/, NEXUS_MODPAGE.md, SHA256SUMS.txt")
    print("nexus/          : archive, MODPAGE.txt, README.txt, SHA256SUMS.txt, thumbnail")
    return 0


if __name__ == "__main__":
    sys.exit(main())
