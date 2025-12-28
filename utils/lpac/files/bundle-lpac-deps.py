#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
import shutil
from collections import deque
from typing import Deque, Optional, Set


NEEDED_RE = re.compile(r"\(NEEDED\)\s+Shared library:\s+\[(.+?)\]")


def readelf_needed(readelf: str, elf_path: str) -> list[str]:
    """Return DT_NEEDED entries from an ELF (names like 'libc.so.6')."""
    try:
        out = subprocess.check_output(
            [readelf, "-d", elf_path],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"readelf not found: {readelf}") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"readelf failed for {elf_path}:\n{e.output}") from e

    return NEEDED_RE.findall(out)


def find_library(libs_dir: str, name: str) -> Optional[str]:
    """Search libs_dir recursively for a file whose basename == name; return realpath if found."""
    for root, _, files in os.walk(libs_dir):
        if name in files:
            return os.path.realpath(os.path.join(root, name))
    return None


def deps_bfs(readelf: str, binary: str, libs_dir: str) -> list[str]:
    """Return full paths of all libraries (direct + transitive) needed by `binary` within `libs_dir`."""
    seen_paths: Set[str] = set()
    out: list[str] = []
    q: Deque[str] = deque()

    # Cache library-name -> resolved path (or None) to avoid repeated directory walks
    resolve_cache: dict[str, Optional[str]] = {}

    def resolve(name: str) -> Optional[str]:
        if name not in resolve_cache:
            resolve_cache[name] = find_library(libs_dir, name)
        return resolve_cache[name]

    # Seed with direct deps (included)
    for name in readelf_needed(readelf, binary):
        p = resolve(name)
        if not p or p in seen_paths:
            continue
        seen_paths.add(p)
        out.append(p)
        q.append(p)

    # BFS over dependency graph
    while q:
        elf = q.popleft()
        for name in readelf_needed(readelf, elf):
            p = resolve(name)
            if not p or p in seen_paths:
                continue
            seen_paths.add(p)
            out.append(p)
            q.append(p)

    return out


def resolve_readelf(platformprefix: str) -> str:
    """
    Accept either:
      - a prefix like 'aarch64-linux-gnu-' (searched in PATH)
      - or a prefix path like '/opt/tc/bin/aarch64-linux-gnu-'
    """
    candidate = platformprefix + "readelf"
    if os.path.isabs(candidate) or os.sep in candidate:
        return candidate
    found = shutil.which(candidate)
    return found or candidate  # fall back; later check will error nicely


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Print full paths of direct+transitive DT_NEEDED libraries of an ELF binary, resolved within a libs directory."
    )
    ap.add_argument("binary", help="Path to the ELF binary")
    ap.add_argument(
        "platformprefix",
        help="Cross prefix for binutils (e.g. 'aarch64-linux-gnu-' or '/opt/tc/bin/aarch64-linux-gnu-')",
    )
    ap.add_argument("libs_dir", help="Directory containing libraries (searched recursively)")
    args = ap.parse_args()

    binary = os.path.abspath(args.binary)
    readelf = resolve_readelf(args.platformprefix)
    libs_dir = os.path.abspath(args.libs_dir)

    if not os.path.isfile(binary):
        print(f"error: binary not found: {binary}", file=sys.stderr)
        return 2
    if not (os.path.isfile(readelf) or shutil.which(readelf)):
        print(f"error: readelf not found: {readelf}", file=sys.stderr)
        return 2
    if not os.path.isdir(libs_dir):
        print(f"error: libs_dir not a directory: {libs_dir}", file=sys.stderr)
        return 2

    for p in deps_bfs(readelf, binary, libs_dir):
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
