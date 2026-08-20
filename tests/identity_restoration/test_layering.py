from __future__ import annotations

import ast
from pathlib import Path

IDR_ROOT = Path(__file__).resolve().parents[2] / "identity_restoration"
DOMAIN_ROOT = IDR_ROOT / "domain"
APPLICATION_ROOT = IDR_ROOT / "application"

# Forbidden at the module-import level in domain/. PIL is intentionally NOT
# in this list: domain code decodes/encodes PNG bytes already held in memory
# (BytesIO), which is not disk or network I/O — see domain/compositing.py's
# module docstring for the rationale. What IS forbidden is anything that
# reaches outside the bytes/numbers the function was given.
FORBIDDEN_DOMAIN_IMPORTS = {"requests", "httpx", "os", "pathlib", "time", "random", "urllib"}
# datetime is allowed for type-only use (Protocol return types); reading the
# wall clock (`datetime.now()`) is what's actually forbidden, checked below.


def _iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if path.name == "__init__.py" and path.stat().st_size == 0:
            continue
        yield path


def _imported_top_level_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def test_domain_has_no_io_imports() -> None:
    """Domain receives bytes, returns bytes. If it needs to read a file or the
    wall clock, that belongs in infrastructure/ (v2.0 PHẦN 3.1)."""
    offenders: list[str] = []
    for path in _iter_py_files(DOMAIN_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        hit = _imported_top_level_names(tree) & FORBIDDEN_DOMAIN_IMPORTS
        if hit:
            offenders.append(f"{path.relative_to(IDR_ROOT)}: {sorted(hit)}")
    assert not offenders, "Domain layer imports I/O modules:\n" + "\n".join(offenders)


def test_domain_never_calls_datetime_now_or_environ() -> None:
    offenders: list[str] = []
    for path in _iter_py_files(DOMAIN_ROOT):
        source = path.read_text(encoding="utf-8")
        if "datetime.now(" in source or "os.environ" in source:
            offenders.append(str(path.relative_to(IDR_ROOT)))
    assert not offenders, f"Domain layer reads wall clock or env: {offenders}"


def test_application_does_not_import_infrastructure() -> None:
    """Application defines Ports. If it imports a concrete adapter, the
    dependency arrow has reversed and Clean Architecture is a name only."""
    offenders: list[str] = []
    for path in _iter_py_files(APPLICATION_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "identity_restoration.infrastructure" in node.module or node.module.startswith("infrastructure"):
                    offenders.append(f"{path.relative_to(IDR_ROOT)}: {node.module}")
    assert not offenders, "Application layer imports infrastructure:\n" + "\n".join(offenders)
