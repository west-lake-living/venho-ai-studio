#!/usr/bin/env python3
"""Add the GC2 production ingress to the locally-managed cloudflared config."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence


HOSTNAME = "growth-api.venhohotel.com"
PATH_RULE = "^/(internal|media/publish)/"
SERVICE = "http://127.0.0.1:8021"
UNIT = "cloudflared.service"


class ConfigError(ValueError):
    pass


def _scalar(value: str) -> str:
    value = value.split("#", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _ingress_entries(lines: list[str]) -> tuple[int, int, list[tuple[int, int, dict[str, str]]]]:
    roots = [i for i, line in enumerate(lines) if re.fullmatch(r"ingress:\s*(?:#.*)?\s*", line.rstrip("\r\n"))]
    if len(roots) != 1:
        raise ConfigError("expected one root ingress section")
    start = roots[0]
    root_indent = len(lines[start]) - len(lines[start].lstrip(" "))
    entry_indent = root_indent + 2
    section_end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        indent = len(lines[i]) - len(lines[i].lstrip(" "))
        if stripped and not stripped.startswith("#") and indent <= root_indent:
            section_end = i
            break
    starts = [
        i for i in range(start + 1, section_end)
        if len(lines[i]) - len(lines[i].lstrip(" ")) == entry_indent
        and re.match(r"\s*-\s+", lines[i])
    ]
    if not starts:
        raise ConfigError("ingress section has no rules")
    entries: list[tuple[int, int, dict[str, str]]] = []
    for offset, rule_start in enumerate(starts):
        rule_end = starts[offset + 1] if offset + 1 < len(starts) else section_end
        fields: dict[str, str] = {}
        for line_number in range(rule_start, rule_end):
            line = lines[line_number]
            indent = len(line) - len(line.lstrip(" "))
            match = re.match(r"\s*(?:-\s+)?([A-Za-z0-9_-]+):\s*(.*?)\s*$", line.rstrip("\r\n"))
            if match and indent in {entry_indent, entry_indent + 2}:
                fields[match.group(1)] = _scalar(match.group(2))
        entries.append((rule_start, rule_end, fields))
    return start, entry_indent, entries


def add_rule(config_text: str) -> tuple[str, bool]:
    lines = config_text.splitlines(keepends=True)
    start, entry_indent, entries = _ingress_entries(lines)
    catchalls = [entry for entry in entries if entry[2].get("service") == "http_status:404"]
    if len(catchalls) != 1 or catchalls[0] is not entries[-1]:
        raise ConfigError("ingress must end with one http_status:404 catch-all")
    matches = [entry for entry in entries if entry[2].get("hostname") == HOSTNAME and entry[2].get("path") == PATH_RULE]
    if matches:
        if len(matches) != 1 or matches[0][2].get("service") != SERVICE:
            raise ConfigError("production ingress exists with a different service or duplicate rule")
        return config_text, False

    # Do not place a broad production host rule after the final 404 catch-all.
    catchall_start = catchalls[0][0]
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    pad = " " * entry_indent
    block = [
        f"{pad}- hostname: {HOSTNAME}{newline}",
        f"{pad}  path: {PATH_RULE}{newline}",
        f"{pad}  service: {SERVICE}{newline}",
    ]
    lines[catchall_start:catchall_start] = block
    return "".join(lines), True


def _run_ok(runner: Callable[..., subprocess.CompletedProcess], command: Sequence[str]) -> bool:
    try:
        result = runner(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _atomic_write(path: Path, content: bytes, *, mode: int, uid: int, gid: int) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temporary)
    try:
        os.fchmod(fd, mode)
        try:
            os.fchown(fd, uid, gid)
        except PermissionError:
            pass
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def configure(
    config_path: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    find_executable: Callable[[str], str | None] = shutil.which,
    now: datetime | None = None,
) -> str:
    if not config_path.is_file() or config_path.is_symlink():
        raise ConfigError("cloudflared config must be an existing regular file")
    if find_executable("cloudflared") is None or find_executable("systemctl") is None:
        raise ConfigError("cloudflared and systemctl must be installed")
    if not _run_ok(runner, ["systemctl", "cat", UNIT]):
        raise ConfigError("cloudflared.service is not installed")

    original = config_path.read_bytes()
    try:
        revised_text, changed = add_rule(original.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ConfigError("cloudflared config is not UTF-8") from error
    if not changed:
        if not _run_ok(runner, ["cloudflared", "--config", str(config_path), "tunnel", "ingress", "validate"]):
            raise ConfigError("existing cloudflared ingress did not validate")
        return "already_configured"

    stat_result = config_path.stat()
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = config_path.with_name(f"{config_path.name}.bak-production-{stamp}")
    if backup.exists():
        raise ConfigError("timestamped config backup already exists")
    candidate = config_path.with_name(f".{config_path.name}.candidate-{os.getpid()}")
    try:
        _atomic_write(candidate, revised_text.encode("utf-8"), mode=stat_result.st_mode & 0o777, uid=stat_result.st_uid, gid=stat_result.st_gid)
        if not _run_ok(runner, ["cloudflared", "--config", str(candidate), "tunnel", "ingress", "validate"]):
            raise ConfigError("candidate cloudflared ingress did not validate")
        shutil.copy2(config_path, backup)
        os.chmod(backup, stat_result.st_mode & 0o777)
        os.replace(candidate, config_path)
        if not _run_ok(runner, ["cloudflared", "--config", str(config_path), "tunnel", "ingress", "validate"]):
            raise ConfigError("installed cloudflared ingress did not validate")
        if not _run_ok(runner, ["systemctl", "restart", UNIT]) or not _run_ok(
            runner, ["systemctl", "is-active", "--quiet", UNIT]
        ):
            raise ConfigError("cloudflared.service failed after restart")
        return f"configured backup={backup}"
    except Exception as error:
        if backup.exists():
            try:
                shutil.copy2(backup, candidate)
                os.replace(candidate, config_path)
                if not _run_ok(runner, ["systemctl", "restart", UNIT]) or not _run_ok(
                    runner, ["systemctl", "is-active", "--quiet", UNIT]
                ):
                    raise OSError("service did not recover")
            except OSError:
                raise ConfigError("change failed and automatic rollback also failed") from None
        if isinstance(error, ConfigError):
            raise
        raise ConfigError("could not update cloudflared config") from None
    finally:
        candidate.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("/etc/cloudflared/config.yml"))
    args = parser.parse_args(argv)
    try:
        result = configure(args.config)
    except ConfigError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"{result} hostname={HOSTNAME} port=8021 unit={UNIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
