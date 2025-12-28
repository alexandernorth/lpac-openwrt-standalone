#!/usr/bin/env python3
import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
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


def resolve_readelf(platformprefix: str) -> str:
    """
    Accept either:
      - a prefix like 'aarch64-linux-gnu-' (searched in PATH)
      - or a prefix path like '/opt/tc/bin/aarch64-linux-gnu-'
    """
    candidate = platformprefix + "readelf"
    if os.path.isabs(candidate) or os.sep in candidate:
        return candidate
    return shutil.which(candidate) or candidate


def matches_skip(name: str, skip_patterns: list[str]) -> bool:
    """Return True if library basename matches any skip glob pattern."""
    return any(fnmatch.fnmatch(name, pat) for pat in skip_patterns)


def find_library(libs_dir: str, name: str) -> Optional[str]:
    """
    Search libs_dir recursively for a file whose basename == name.

    IMPORTANT: returns the path as found (may be a symlink). This lets `cp -L`
    decide whether to dereference it.
    """
    for root, _, files in os.walk(libs_dir):
        if name in files:
            return os.path.join(root, name)  # DO NOT realpath()
    return None


def deps_bfs(readelf: str, binary: str, libs_dir: str, skip_patterns: list[str]) -> list[str]:
    """
    Return full paths of all libraries (direct + transitive) needed by `binary`,
    resolved within `libs_dir`.

    Output paths may be symlinks (e.g. libfoo.so.4). Use `cp -L` to copy real files.

    Dedupe/cycle detection is done by realpath() of each found library so the same
    underlying file is not returned multiple times through different symlinks.
    """
    out: list[str] = []
    q: Deque[str] = deque()

    seen_real: Set[str] = set()

    # Cache libname -> found path (or None) to avoid repeated walks
    resolve_cache: dict[str, Optional[str]] = {}

    def resolve(name: str) -> Optional[str]:
        if matches_skip(name, skip_patterns):
            return None
        if name not in resolve_cache:
            resolve_cache[name] = find_library(libs_dir, name)
        return resolve_cache[name]

    # Seed with direct deps (included)
    for name in readelf_needed(readelf, binary):
        p = resolve(name)
        if not p:
            continue
        real = os.path.realpath(p)
        if real in seen_real:
            continue
        seen_real.add(real)
        out.append(p)
        q.append(p)

    # BFS over dependency graph
    while q:
        elf = q.popleft()
        for name in readelf_needed(readelf, elf):
            p = resolve(name)
            if not p:
                continue
            real = os.path.realpath(p)
            if real in seen_real:
                continue
            seen_real.add(real)
            out.append(p)
            q.append(p)

    return out


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
    ap.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Library basename glob to skip (repeatable), e.g. --skip 'libc.so.*'",
    )
    args = ap.parse_args()

    binary = os.path.abspath(args.binary)
    readelf = resolve_readelf(args.platformprefix)
    libs_dir = os.path.abspath(args.libs_dir)
    skip_patterns = args.skip

    if not os.path.isfile(binary):
        print(f"error: binary not found: {binary}", file=sys.stderr)
        return 2
    if (os.sep in readelf or os.path.isabs(readelf)) and not os.path.isfile(readelf):
        print(f"error: readelf not found: {readelf}", file=sys.stderr)
        return 2
    if not os.path.isdir(libs_dir):
        print(f"error: libs_dir not a directory: {libs_dir}", file=sys.stderr)
        return 2

    try:
        for p in deps_bfs(readelf, binary, libs_dir, skip_patterns):
            print(p)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
