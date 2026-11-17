#!/usr/bin/env python3
"""Inventory the v3.2 reference-photo folders and, after review, write an external allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
CATALOG_LINE = re.compile(r"^\s{2}([A-Za-z0-9_]+):\s*([^\s#]+)\s*(?:#.*)?$")


def parse_catalog(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    in_assets = False
    mapping: dict[str, str] = {}
    for line in text.splitlines():
        if line.strip() == "assets:":
            in_assets = True
            continue
        if not in_assets or not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith("  "):
            break
        match = CATALOG_LINE.match(line)
        if match is None:
            raise ValueError("reference_assets.yaml contains an unsupported mapping line")
        reference_id, source = match.groups()
        prefix = "assets/raw/"
        if not source.startswith(prefix):
            raise ValueError("catalog image mapping is outside assets/raw")
        relative = source.removeprefix(prefix)
        _safe_components(relative)
        mapping[reference_id] = relative
    if not mapping:
        raise ValueError("no legacy reference mappings were found")
    return mapping


def inventory(root: Path, mapping: dict[str, str]) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    resolved_root = Path(os.path.abspath(root.expanduser()))
    _reject_symlink_components(resolved_root)
    if not resolved_root.is_dir():
        raise ValueError("legacy assets root is not a directory")
    allowlist: dict[str, list[dict[str, str]]] = {}
    mapped_top_levels: set[str] = set()
    for reference_id, relative in mapping.items():
        components = _safe_components(relative)
        mapped_top_levels.add(components[0])
        start = resolved_root.joinpath(*components)
        _reject_symlink_components(start)
        if start.is_symlink():
            raise ValueError("catalog mapping points through a symlink")
        candidates: list[Path]
        if start.is_file() and start.suffix.lower() in IMAGE_SUFFIXES:
            candidates = [start]
        elif start.is_dir():
            candidates = _walk_images(start)
        else:
            candidates = []
        entries: list[dict[str, str]] = []
        for candidate in candidates:
            relative_path = candidate.relative_to(resolved_root).as_posix()
            _safe_components(relative_path)
            if candidate.is_symlink():
                continue
            digest = _sha256_file(resolved_root, relative_path)
            entries.append({"path": relative_path, "sha256": digest})
        allowlist[reference_id] = sorted(entries, key=lambda entry: entry["path"])
    unmapped: list[str] = []
    with os.scandir(resolved_root) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False) and entry.name not in mapped_top_levels:
                unmapped.append(entry.name)
    return allowlist, sorted(unmapped)


def _walk_images(directory: Path) -> list[Path]:
    _reject_symlink_components(directory)
    found: list[Path] = []
    with os.scandir(directory) as entries:
        for entry in sorted(entries, key=lambda value: value.name):
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                found.extend(_walk_images(Path(entry.path)))
            elif entry.is_file(follow_symlinks=False) and Path(entry.name).suffix.lower() in IMAGE_SUFFIXES:
                found.append(Path(entry.path))
    return found


def _sha256_file(root: Path, relative_path: str) -> str:
    digest = hashlib.sha256()
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(root.anchor, directory_flags | no_follow)
    try:
        for component in root.parts[1:]:
            next_fd = os.open(component, directory_flags | no_follow, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        components = _safe_components(relative_path)
        for component in components[:-1]:
            next_fd = os.open(component, directory_flags | no_follow, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        file_fd = os.open(
            components[-1],
            os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow,
            dir_fd=descriptor,
        )
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                raise ValueError("legacy image candidate is not a regular file")
            while chunk := os.read(file_fd, 1024 * 1024):
                digest.update(chunk)
        finally:
            os.close(file_fd)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        if current.is_symlink():
            raise ValueError("legacy image root contains a symlink component")


def _safe_components(value: str) -> tuple[str, ...]:
    if not value or value.startswith("/") or "\\" in value or "\x00" in value:
        raise ValueError("image catalog path must be relative")
    components = tuple(value.split("/"))
    if any(component in {"", ".", ".."} for component in components):
        raise ValueError("image catalog path contains an unsafe component")
    return components


def render_yaml(allowlist: dict[str, list[dict[str, str]]]) -> str:
    lines = [
        "version: 1",
        "source: local_legacy_library",
        "# Generated from the v3.2 reference_assets.yaml mapping after operator review.",
        "allowlist:",
    ]
    for reference_id, entries in sorted(allowlist.items()):
        if not entries:
            lines.append(f"  {reference_id}: []")
            continue
        lines.append(f"  {reference_id}:")
        for entry in entries:
            lines.append(f"    - path: {json.dumps(entry['path'], ensure_ascii=False)}")
            lines.append(f"      sha256: {entry['sha256']}")
    return "\n".join(lines) + "\n"


def write_private(path: Path, contents: str) -> None:
    path = path.expanduser()
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--assets-root",
        type=Path,
        default=home / "venho/growth-runtime/venho-ai-studio/assets/raw",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=repo_root / "config/projects/venho_hotel/growth/reference_assets.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=home / "venho/config/growth-engine-image-library.yaml",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the external allowlist only after displaying candidates and receiving WRITE confirmation",
    )
    arguments = parser.parse_args()
    try:
        mapping = parse_catalog(arguments.catalog)
        allowlist, unmapped_dirs = inventory(arguments.assets_root, mapping)
    except (OSError, ValueError) as error:
        print(f"IMAGE_LIBRARY_SCAN=FAIL code={type(error).__name__}", file=sys.stderr)
        return 1

    empty_groups = [reference_id for reference_id, entries in allowlist.items() if not entries]
    total = sum(len(entries) for entries in allowlist.values())
    print("source=legacy_reference_assets.yaml -> assets/raw/<mapped directory>")
    print(f"root={arguments.assets_root}")
    print("group\tsha256\trelative_path")
    for reference_id, entries in sorted(allowlist.items()):
        for entry in entries:
            print(f"{reference_id}\t{entry['sha256']}\t{entry['path']}")
    print(f"mapped_groups={len(allowlist)} candidate_entries={total}")
    print("unmapped_top_level_dirs=" + (",".join(unmapped_dirs) if unmapped_dirs else "none"))
    print("excluded_policy=unmapped directories (including linh_an) are not inventoried or allowlisted")
    if empty_groups:
        print("EMPTY_MAPPED_GROUPS=" + ",".join(sorted(empty_groups)), file=sys.stderr)
        print("IMAGE_LIBRARY_WRITE=BLOCKED", file=sys.stderr)
        return 2
    if not arguments.apply:
        print("IMAGE_LIBRARY_WRITE=NOT_REQUESTED")
        return 0

    print(f"review the table above; target config is {arguments.output}")
    try:
        answer = input("Type WRITE to replace/create this allowlist: ").strip()
    except EOFError:
        answer = ""
    if answer != "WRITE":
        print("IMAGE_LIBRARY_WRITE=CANCELLED")
        return 3
    write_private(arguments.output, render_yaml(allowlist))
    print(f"IMAGE_LIBRARY_WRITE=PASS entries={total} mode=600")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
