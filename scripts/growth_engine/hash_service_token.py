from __future__ import annotations

import argparse
import getpass
import hashlib
import sys


_CHANNEL_PRINCIPALS = ("make-fb-hanoi", "make-fb-venho", "make-ig")


def sha256_bearer(bearer: str) -> str:
    normalized = bearer.strip()
    if not normalized:
        raise ValueError("bearer must not be empty")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _read_bearer() -> str:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise RuntimeError("run interactively so the bearer prompt stays hidden")
    return getpass.getpass("TEST route bearer (hidden): ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print a service-token principal:SHA-256 entry without printing the bearer."
    )
    parser.add_argument("--principal", choices=_CHANNEL_PRINCIPALS, required=True)
    args = parser.parse_args(argv)
    try:
        digest = sha256_bearer(_read_bearer())
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(f"{args.principal}:{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
