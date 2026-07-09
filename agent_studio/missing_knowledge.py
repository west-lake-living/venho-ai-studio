from __future__ import annotations

from agent_studio.exceptions import ERR_MISSING_KNOWLEDGE
from agent_studio.schemas import Persona


def detect_missing_knowledge(persona: Persona, loaded_context: dict) -> dict:
    loaded = set(loaded_context.get("knowledge", {}).keys())
    missing = [ref for ref in persona.required_knowledge if ref not in loaded]
    missing.extend(ref for ref in loaded_context.get("missing_refs", []) if ref not in missing)
    return {
        "error_code": ERR_MISSING_KNOWLEDGE if missing else None,
        "missing_knowledge": missing,
        "suggested_module": "M01_KNOWLEDGE_STUDIO" if missing else None,
    }
