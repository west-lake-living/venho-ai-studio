#!/usr/bin/env python3
"""Create a mode-600 Make bearer handoff and matching production token hashes."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import os
import re
import secrets
import stat
import sys
import tempfile
from pathlib import Path
from typing import Callable


PRINCIPALS = (
    ("make-fb-hanoi", "GE_MAKE_BEARER_FB_HANOI"),
    ("make-fb-venho", "GE_MAKE_BEARER_FB_VENHO"),
    ("make-ig", "GE_MAKE_BEARER_IG_VENHO"),
)
ENV_NAMES = tuple(variable for _, variable in PRINCIPALS)


class ProvisionError(ValueError):
    pass


def _assignments(text: str) -> tuple[list[str], dict[str, str]]:
    lines = text.splitlines(keepends=True)
    values: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*?)(?:\r?\n)?$", line)
        if match:
            name, value = match.groups()
            if name in values:
                raise ProvisionError("environment file contains duplicate variable names")
            values[name] = value
    return lines, values


def _service_value(bearers: dict[str, str]) -> str:
    return ",".join(
        f"{principal}:{hashlib.sha256(bearers[variable].strip().encode('utf-8')).hexdigest()}"
        for principal, variable in PRINCIPALS
    )


def _valid_capability_ring(value: str) -> bool:
    if not value.strip():
        return False
    for entry in value.split(","):
        if entry.count(":") != 1:
            return False
        key_id, encoded = entry.split(":", 1)
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", key_id) or not encoded:
            return False
        try:
            decoded = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        except (ValueError, binascii.Error, UnicodeError):
            return False
        if len(decoded) < 32:
            return False
    return True


def _replace_values(text: str, updates: dict[str, str]) -> str:
    lines, _ = _assignments(text)
    output: list[str] = []
    replaced: set[str] = set()
    for line in lines:
        name = line.split("=", 1)[0] if "=" in line else ""
        if name not in updates:
            output.append(line)
            continue
        if name in replaced:
            raise ProvisionError(f"duplicate {name}")
        output.append(f"{name}={updates[name]}\n")
        replaced.add(name)
    for name, value in updates.items():
        if name not in replaced:
            output.append(f"{name}={value}\n")
    return "".join(output)


def _write_private(path: Path, payload: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temporary)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def provision(
    env_path: Path,
    handoff_path: Path,
    *,
    token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(48),
    capability_factory: Callable[[], str] | None = None,
) -> str:
    secrets_dir = env_path.parent.resolve(strict=True)
    if env_path.parent.is_symlink() or handoff_path.parent.resolve(strict=True) != secrets_dir:
        raise ProvisionError("production secret paths must share one non-symlink directory")
    if stat.S_IMODE(secrets_dir.stat().st_mode) != 0o700:
        raise ProvisionError("production secrets directory must have mode 700")
    if env_path.is_symlink() or handoff_path.is_symlink() or not env_path.is_file():
        raise ProvisionError("production env must exist and secret paths must be regular files")
    if stat.S_IMODE(env_path.stat().st_mode) != 0o600:
        raise ProvisionError("production env must have mode 600")
    lock_path = secrets_dir / ".growth-engine-make-bearers.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ProvisionError("another Make bearer provisioning run is active") from None
    os.close(lock_fd)
    try:
        original = env_path.read_text(encoding="utf-8")
        _, values = _assignments(original)
        if values.get("GE_ENV") != "production":
            raise ProvisionError("growth-engine.env must set GE_ENV=production")
        if handoff_path.exists():
            if stat.S_IMODE(handoff_path.stat().st_mode) != 0o600:
                raise ProvisionError("existing bearer handoff must have mode 600")
            _, existing_bearers = _assignments(handoff_path.read_text(encoding="utf-8"))
            if set(existing_bearers) != set(ENV_NAMES) or _service_value(existing_bearers) != values.get("GE_SERVICE_TOKENS"):
                raise ProvisionError("existing bearer handoff does not match production hashes")
            if not _valid_capability_ring(values.get("GE_CAPABILITY_KEYS", "")):
                raise ProvisionError("production capability key is missing")
            return "already_configured"

        old_service_value = values.get("GE_SERVICE_TOKENS", "")
        if old_service_value.strip() and "REQUIRED_FROM_P0" not in old_service_value:
            raise ProvisionError("production bearer hashes exist but handoff is absent; refusing rotation")
        bearers = {variable: token_factory() for _, variable in PRINCIPALS}
        if any(not token.strip() or any(ch in token for ch in "\r\n\0") for token in bearers.values()):
            raise ProvisionError("bearer generator returned invalid values")
        handoff_text = "# Copy values into the matching production Make HTTP Authorization headers; delete after cutover.\n"
        handoff_text += "".join(f"{name}={bearers[name]}\n" for name in ENV_NAMES)
        capability_value = values.get("GE_CAPABILITY_KEYS", "").strip()
        if not capability_value or "REQUIRED_FROM_P0" in capability_value:
            if capability_factory is None:
                key_id = "prod-" + secrets.token_hex(4)
                key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
                capability_value = f"{key_id}:{key}"
            else:
                capability_value = capability_factory()
        if not _valid_capability_ring(capability_value):
            raise ProvisionError("capability key generator returned an invalid key ring")
        env_text = _replace_values(
            original,
            {"GE_SERVICE_TOKENS": _service_value(bearers), "GE_CAPABILITY_KEYS": capability_value},
        )
        _write_private(handoff_path, handoff_text)
        try:
            _write_private(env_path, env_text)
        except Exception:
            handoff_path.unlink(missing_ok=True)
            raise
        return "created"
    finally:
        lock_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=Path.home() / "venho/secrets/growth-engine.env")
    parser.add_argument("--handoff", type=Path, default=Path.home() / "venho/secrets/growth-engine.make-bearers.tmp")
    args = parser.parse_args(argv)
    try:
        result = provision(args.env, args.handoff)
    except (OSError, UnicodeError, ProvisionError):
        print("FAIL: production Make bearer setup did not complete", file=sys.stderr)
        return 1
    print(f"production_make_bearers={result} variables={len(ENV_NAMES)} mode=600")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
