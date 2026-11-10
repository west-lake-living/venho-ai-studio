"""GC2-P0-T02 — check_manifest_no_secrets: bắt secret, không báo nhầm placeholder/tên env/đường dẫn."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "check_manifest_no_secrets", ROOT / "scripts/growth_engine/check_manifest_no_secrets.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)  # type: ignore[union-attr]


def rules(text: str):
    return {r for _, r in mod.scan_text(text)}


@pytest.mark.parametrize(
    "line,rule",
    [
        ("token: EAAGm0PX4ZCpsBAKZCZBqwertyuiopasdfghjklzxcvb", "meta_access_token"),
        ("Authorization: Bearer abcdEFGH1234567890xyzXYZ.abc", "bearer_value"),
        ("url: https://hook.eu2.make.com/abc123def456", "make_webhook_url"),
        ("secret = hunter2hunter2", "keyed_secret"),
        ("x: " + "aB3+" * 12, "long_token_like"),
        ("CF-Access-Client-Secret: 0123456789abcdef", "cf_access_secret"),
    ],
)
def test_detects_secret(line, rule):
    assert rule in rules(line)


@pytest.mark.parametrize(
    "line",
    [
        "remote_page_id: REQUIRED_FROM_P0",
        "make_route_ref: GE_MAKE_WEBHOOK_URL_PAGE_A",
        "meta_read_token_ref: GE_META_READ_TOKEN_PAGE_A",
        "token: <điền ở env>",
        "docs/growth_engine/adr/ADR-05_media_hosting_signed_urls.md",
        "Không ghi token vào file này; chỉ ghi tên biến.",
        "a" * 50,  # chỉ một lớp ký tự -> không phải token
    ],
)
def test_no_false_positive(line):
    assert rules(line) == set()


def test_shipped_manifests_are_clean_and_only_production_documentation_has_gates():
    for f in mod.DEFAULT_FILES:
        assert mod.main([str(f)]) == 0
    docs_manifest, channels_manifest = mod.DEFAULT_FILES
    assert mod.main([str(docs_manifest), "--require-filled"]) == 1  # còn gate production trong tài liệu
    assert mod.main([str(channels_manifest), "--require-filled"]) == 0  # TEST đã điền; production dùng null


def test_require_filled_passes_when_filled(tmp_path):
    f = tmp_path / "m.md"
    f.write_text("remote_page_id: 123456789012345\n", encoding="utf-8")
    assert mod.main([str(f), "--require-filled"]) == 0


def test_never_prints_secret_value(tmp_path, capsys):
    f = tmp_path / "m.md"
    f.write_text("token: EAAGm0PX4ZCpsBAKZCZBqwertyuiopasdfghjklzxcvb\n", encoding="utf-8")
    assert mod.main([str(f)]) == 1
    err = capsys.readouterr().err
    assert "EAAGm0PX" not in err and "meta_access_token" in err


def test_missing_file_fails(tmp_path):
    assert mod.main([str(tmp_path / "nope.md")]) == 1
