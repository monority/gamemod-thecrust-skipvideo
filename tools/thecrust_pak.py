#!/usr/bin/env python3
"""
The Crust .pak tool (UE4 pak version 3 - same format as the mods distributed
on Nexus). Reads compressed (zlib) and uncompressed entries; always writes
uncompressed archives, which the game accepts.

Usage:
  python thecrust_pak.py list  <file.pak>
  python thecrust_pak.py extract <file.pak> <output_dir>
  python thecrust_pak.py pack <input_dir> <output.pak> [mount_point]

For pack, every file under <input_dir> is stored with its relative path.
The default mount point is "../../../" (the value used by The Crust mods).
"""
import hashlib
import os
import struct
import sys
import zlib

PAK_MAGIC = 0x5A6F12E1
PAK_VERSION = 3
HASH = hashlib.sha1


def fail(action, path, exc):
    return SystemExit(f"{action} failed: {path} ({exc})")


def read_bytes(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except (OSError, ValueError) as exc:
        raise fail("Read", path, exc) from exc


def write_bytes(path, payload):
    try:
        with open(path, "wb") as handle:
            handle.write(payload)
    except (OSError, ValueError) as exc:
        raise fail("Write", path, exc) from exc


def ensure_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
    except (OSError, ValueError) as exc:
        raise fail("Create directory", path, exc) from exc


def read_fstring(data, pos):
    (length,) = struct.unpack_from("<i", data, pos)
    pos += 4
    if length == 0:
        return "", pos
    if length < 0:
        raw = data[pos:pos + (-length) * 2]
        pos += (-length) * 2
        return raw.decode("utf-16-le", "replace").rstrip("\x00"), pos
    raw = data[pos:pos + length]
    pos += length
    return raw.decode("utf-8", "replace").rstrip("\x00"), pos


def write_fstring(text):
    raw = text.encode("utf-8") + b"\x00"
    return struct.pack("<i", len(raw)) + raw


def read_entry_header(data, pos):
    offset, size, usize, cmeth = struct.unpack_from("<qqqI", data, pos)
    pos += 28
    digest = data[pos:pos + 20]
    pos += 20
    blocks = []
    if cmeth != 0:
        (count,) = struct.unpack_from("<i", data, pos)
        pos += 4
        for _ in range(count):
            boff, bsize = struct.unpack_from("<qq", data, pos)
            pos += 16
            blocks.append((boff, bsize))
    flags = data[pos]
    pos += 1
    (block_size,) = struct.unpack_from("<I", data, pos)
    pos += 4
    return {
        "offset": offset, "size": size, "usize": usize, "cmeth": cmeth,
        "hash": digest, "blocks": blocks, "flags": flags,
        "block_size": block_size,
    }, pos


def entry_header_bytes(offset, size, digest):
    return struct.pack("<qqqI", offset, size, size, 0) + digest + struct.pack("<BI", 0, 0)


def data_header_bytes(size, digest):
    """Data header written just before a file's payload inside the archive.

    The offset field is always 0 in a version 3 pak: the real offset only lives
    in the index, and writing it here would produce a non-conforming pak.
    """
    return entry_header_bytes(0, size, digest)


def open_pak(path):
    data = read_bytes(path)
    (magic, version, index_offset, index_size) = struct.unpack_from(
        "<IIqq", data, len(data) - 44
    )
    if magic != PAK_MAGIC:
        raise ValueError("Not a UE4 .pak file (bad magic)")
    if version != PAK_VERSION:
        raise ValueError(
            f"Unsupported pak version {version} (this tool handles version 3)"
        )
    index = data[index_offset:index_offset + index_size]
    if HASH(index).digest() != data[len(data) - 20:]:
        raise ValueError("Corrupted pak index (SHA1 mismatch)")
    pos = 0
    mount, pos = read_fstring(index, pos)
    (count,) = struct.unpack_from("<i", index, pos)
    pos += 4
    entries = []
    for _ in range(count):
        name, pos = read_fstring(index, pos)
        entry, pos = read_entry_header(index, pos)
        entry["name"] = name
        entries.append(entry)
    return data, mount, entries


def cmd_list(path):
    data, mount, entries = open_pak(path)
    print("Mount point:", mount)
    print("Entries:", len(entries))
    for e in entries:
        note = " [zlib]" if e["cmeth"] else ""
        print(f"  {e['name']:<80} {e['usize']:>8} bytes{note}")


def entry_payload(data, entry):
    """Raw payload of one entry, decompressed when needed.

    In version 3 the block offsets are absolute in the file: they point at the
    zlib stream, not at the entry data area.
    """
    if entry["cmeth"] != 0:
        if entry["cmeth"] != 1:
            raise ValueError(
                f"unsupported compression {entry['cmeth']} ({entry['name']})"
            )
        try:
            return b"".join(
                zlib.decompress(data[start:end]) for start, end in entry["blocks"]
            )
        except (zlib.error, struct.error) as exc:
            raise fail("Decompress", entry["name"], exc) from exc
    start = entry["offset"] + 53
    return data[start:start + entry["size"]]


def cmd_extract(path, out_dir):
    try:
        data, mount, entries = open_pak(path)
        for e in entries:
            payload = entry_payload(data, e)
            dest = os.path.join(out_dir, *e["name"].split("/"))
            ensure_dir(os.path.dirname(dest))
            write_bytes(dest, payload)
            print("extracted", dest)
        print("Mount point:", mount)
    except (OSError, ValueError) as exc:
        raise fail("Extract", out_dir, exc) from exc


def cmd_pack(in_dir, out_pak, mount="../../../"):
    try:
        files = []
        for root, _dirs, names in os.walk(in_dir):
            for name in names:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, in_dir).replace("\\", "/")
                files.append((rel, full))
        files.sort()

        out = bytearray()
        entries = []
        for rel, full in files:
            payload = read_bytes(full)
            offset = len(out)
            digest = HASH(payload).digest()
            out += data_header_bytes(len(payload), digest)
            out += payload
            entries.append((rel, offset, len(payload), digest))

        index = bytearray()
        index += write_fstring(mount)
        index += struct.pack("<i", len(entries))
        for rel, offset, size, digest in entries:
            index += write_fstring(rel)
            index += entry_header_bytes(offset, size, digest)

        index_offset = len(out)
        out += index
        out += struct.pack("<IIqq", PAK_MAGIC, PAK_VERSION, index_offset, len(index))
        out += HASH(index).digest()

        write_bytes(out_pak, bytes(out))
        print(f"created {out_pak} ({len(entries)} entries, {len(out)} bytes)")
    except (OSError, ValueError) as exc:
        raise fail("Pack", out_pak, exc) from exc


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd = sys.argv[1].lower()
    if cmd == "list":
        cmd_list(sys.argv[2])
    elif cmd == "extract":
        cmd_extract(sys.argv[2], sys.argv[3])
    elif cmd == "pack":
        mount = sys.argv[4] if len(sys.argv) > 4 else "../../../"
        cmd_pack(sys.argv[2], sys.argv[3], mount)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
