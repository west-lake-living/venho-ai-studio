from __future__ import annotations

import ast
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
GROWTH_ROOT = REPOSITORY_ROOT / "growth_engine"
LEGACY_PACKAGES = (
    "growth_orchestrator",
    "publishing_gateway",
    "validator_studio",
    "content_studio",
    "prompt_studio",
    "research_engine",
    "knowledge_studio",
    "shared",
)
LEGACY_IMPORT_ROOTS = set(LEGACY_PACKAGES)
ALLOWED_INBOUND_LIBRARIES = {"fastapi", "pydantic", "typer"}


def _module_name(path: Path) -> str:
    relative = path.relative_to(REPOSITORY_ROOT).with_suffix("")
    return ".".join(relative.parts)


def _resolve_import(node: ast.Import | ast.ImportFrom, module_name: str) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if node.level == 0:
        return [node.module or ""]
    package_parts = module_name.split(".")[:-1]
    if module_name.endswith(".__init__"):
        package_parts = module_name.split(".")[:-1]
    keep = len(package_parts) - node.level + 1
    base = package_parts[:keep]
    if node.module:
        base.extend(node.module.split("."))
    return [".".join(base)]


def _is_stdlib(module: str) -> bool:
    return module.split(".", 1)[0] in sys.stdlib_module_names


def _attribute_chain(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _attribute_chain(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _violates_boundary(module: str, layer: str) -> bool:
    if not module:
        return False
    root = module.split(".", 1)[0]
    internal = module.startswith("growth_engine.") or module == "growth_engine"
    if layer == "domain":
        return not (
            _is_stdlib(module)
            or module == "growth_engine.domain"
            or module.startswith("growth_engine.domain.")
        )
    if layer == "application":
        return not (
            _is_stdlib(module)
            or module == "growth_engine.domain"
            or module == "growth_engine.application"
            or module.startswith("growth_engine.domain.")
            or module.startswith("growth_engine.application.")
        )
    if layer == "inbound":
        if internal:
            return module.startswith("growth_engine.adapters.outbound.")
        return root in LEGACY_IMPORT_ROOTS or not (
            _is_stdlib(module) or root in ALLOWED_INBOUND_LIBRARIES
        )
    if layer == "outbound":
        return root in LEGACY_IMPORT_ROOTS or (
            internal and module.startswith("growth_engine.adapters.inbound.")
        )
    if layer == "outbound_meta":
        if root == "shared":
            return not (module == "shared.meta" or module.startswith("shared.meta."))
        return root in LEGACY_IMPORT_ROOTS or (
            internal and module.startswith("growth_engine.adapters.inbound.")
        )
    if layer == "outbound_legacy":
        return internal and module.startswith("growth_engine.adapters.inbound.")
    if layer == "bootstrap":
        return False
    return not (_is_stdlib(module) or root == "pydantic")


def test_growth_engine_imports_respect_layer_boundaries() -> None:
    violations: list[str] = []
    for path in sorted(GROWTH_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        name = _module_name(path)
        relative = path.relative_to(GROWTH_ROOT)
        if relative.parts[0] == "domain":
            layer = "domain"
        elif relative.parts[0] == "application":
            layer = "application"
        elif relative.parts[0] == "adapters" and relative.parts[1] == "inbound":
            layer = "inbound"
        elif relative.parts[:3] == ("adapters", "outbound", "meta"):
            layer = "outbound_meta"
        elif relative.parts[:3] == ("adapters", "outbound", "legacy"):
            layer = "outbound_legacy"
        elif relative.parts[:2] == ("adapters", "outbound"):
            layer = "outbound"
        elif relative.parts[0] == "bootstrap":
            layer = "bootstrap"
        else:
            layer = "settings"

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for imported in _resolve_import(node, name):
                    if _violates_boundary(imported, layer):
                        violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}: {imported}")
            if layer == "domain" and isinstance(node, ast.Attribute):
                chain = _attribute_chain(node)
                if chain in {
                    "os.environ",
                    "datetime.now",
                    "datetime.datetime.now",
                    "datetime.date.today",
                    "date.today",
                }:
                    violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}: {chain}")
    assert not violations, "Forbidden imports:\n" + "\n".join(violations)


def test_legacy_packages_do_not_import_growth_engine() -> None:
    violations: list[str] = []
    for package in LEGACY_PACKAGES:
        root = REPOSITORY_ROOT / package
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(alias.name == "growth_engine" or alias.name.startswith("growth_engine.") for alias in node.names):
                        violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom) and (node.module == "growth_engine" or (node.module or "").startswith("growth_engine.")):
                    violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
    assert not violations, "Legacy imports Growth Engine:\n" + "\n".join(violations)
