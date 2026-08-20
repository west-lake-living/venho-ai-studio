from __future__ import annotations

from pathlib import Path

from identity_restoration.infrastructure.comfyui.node_registry import NODE_TITLES

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_FILE = REPO_ROOT / "identity_restoration" / "infrastructure" / "comfyui" / "node_registry.py"

# Excludes: the registry itself, this test (which must name the strings to
# check for them), and anything under _archive/ or golden fixtures, which are
# frozen historical evidence, not live source.
EXCLUDED_DIRS = {"_archive", "golden", ".git", "node_modules", "__pycache__"}
SCAN_ROOTS = [REPO_ROOT / "identity_restoration"]


def _iter_candidate_files():
    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            if path == REGISTRY_FILE:
                continue
            if path == Path(__file__):
                continue
            if any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            yield path


def test_node_titles_do_not_leak_outside_registry() -> None:
    offenders: list[str] = []
    for path in _iter_candidate_files():
        source = path.read_text(encoding="utf-8")
        for title in NODE_TITLES.values():
            if title in source:
                offenders.append(f"{path.relative_to(REPO_ROOT)} contains {title!r}")
    assert not offenders, "ComfyUI node title leaked outside node_registry.py:\n" + "\n".join(offenders)
