#!/usr/bin/env python3
"""GC2-P0-T02 — Quét manifest/channels.yaml tìm chuỗi giống secret.

Dùng:
    python3 scripts/growth_engine/check_manifest_no_secrets.py [files...] [--require-filled]

Exit 0 = sạch; 1 = có nghi vấn secret (hoặc, với --require-filled, còn REQUIRED_FROM_P0).
Không bao giờ in giá trị nghi vấn ra màn hình, chỉ in file:dòng và tên luật.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILES = (
    ROOT / "docs/growth_engine/environment_manifest.md",
    ROOT / "config/projects/venho_hotel/growth_engine/channels.yaml",
)
PLACEHOLDER = "REQUIRED_FROM_P0"

_RULES: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("meta_access_token", re.compile(r"\bEA[A-Za-z]{2,}[A-Za-z0-9]{20,}")),
    ("bearer_value", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("make_webhook_url", re.compile(r"https?://hook\.[a-z0-9.-]*make\.com/\S+", re.I)),
    ("cf_access_secret", re.compile(r"\bCF-Access-Client-Secret\s*[:=]\s*\S{8,}", re.I)),
)
# secret/token/password: <giá trị> — bỏ qua placeholder, <...>, và tên biến môi trường VIẾT HOA.
_KEYED = re.compile(
    r"(?i)\b(secret|token|password|passwd|api[_-]?key)\b[\"'`]?\s*[:=]\s*[\"'`]?([^\s\"'`,;|]{8,})"
)
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
_LONG = re.compile(r"[A-Za-z0-9+/=_-]{41,}")


def _classes(s: str) -> int:
    return sum(
        (
            any(c.islower() for c in s),
            any(c.isupper() for c in s),
            any(c.isdigit() for c in s),
            any(c in "+/=" for c in s),
        )
    )


def scan_text(text: str) -> List[Tuple[int, str]]:
    """Trả [(số dòng, tên luật)]; không trả giá trị."""
    found: List[Tuple[int, str]] = []
    for no, line in enumerate(text.splitlines(), 1):
        for name, rx in _RULES:
            if rx.search(line):
                found.append((no, name))
        for m in _KEYED.finditer(line):
            val = m.group(2)
            if PLACEHOLDER in val or val.startswith("<") or _ENV_NAME.match(val):
                continue
            found.append((no, "keyed_secret"))
        for m in _LONG.finditer(line):
            tok = m.group(0)
            if "/" in tok and "." in line[m.start() : m.end() + 6]:
                continue  # đường dẫn file
            if _classes(tok) >= 3:
                found.append((no, "long_token_like"))
    return sorted(set(found))


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--require-filled", action="store_true", help=f"lỗi nếu còn {PLACEHOLDER}")
    args = ap.parse_args(argv)
    files = args.files or list(DEFAULT_FILES)

    bad = 0
    for f in files:
        if not f.exists():
            print(f"{f}: không tồn tại", file=sys.stderr)
            bad += 1
            continue
        text = f.read_text(encoding="utf-8")
        for no, rule in scan_text(text):
            print(f"{f}:{no}: nghi vấn secret [{rule}]", file=sys.stderr)
            bad += 1
        if args.require_filled:
            for no, line in enumerate(text.splitlines(), 1):
                if PLACEHOLDER in line:
                    print(f"{f}:{no}: còn {PLACEHOLDER}", file=sys.stderr)
                    bad += 1
    if bad:
        print(f"FAIL: {bad} vấn đề", file=sys.stderr)
        return 1
    print("OK: không thấy secret" + (", đã điền đủ" if args.require_filled else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
