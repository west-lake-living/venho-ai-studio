from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_studio.schemas import AgentRequest


def _ref_aliases(ref: str) -> list[str]:
    normalized = ref.lower()
    aliases = [normalized]
    for prefix in ("venho_", "hotel_", "the_west_lake_living_"):
        if normalized.startswith(prefix):
            aliases.append(normalized.removeprefix(prefix))
    for suffix in ("_dna", "_knowledge", "_config"):
        if normalized.endswith(suffix):
            aliases.append(normalized.removesuffix(suffix))
    aliases.append(normalized.replace("westlake", "westlake"))
    return list(dict.fromkeys(aliases))


def _candidate_paths(project: str, ref: str, data_root: Path, config_root: Path) -> list[Path]:
    aliases = _ref_aliases(ref)
    paths: list[Path] = []
    for normalized in aliases:
        paths.extend(
            [
                data_root / "knowledge" / f"{ref}.json",
                data_root / "knowledge" / f"{ref}.md",
                config_root / project / "subjects" / f"{normalized}.yaml",
                config_root / project / "content" / f"{normalized}.yaml",
                config_root / project / "analytics" / f"{normalized}.yaml",
                config_root / project / f"{normalized}.yaml",
            ]
        )
    if "brand" in ref.lower():
        paths.extend([config_root / project / "prompt_rules.yaml", config_root / project / "content" / "tone_of_voice.yaml"])
    if "content_pillar" in ref.lower():
        paths.append(config_root / project / "content" / "content_pillars.yaml")
    if "westlake" in ref.lower() or "west_lake" in ref.lower():
        paths.append(config_root / project / "subjects" / "westlake.yaml")
    return list(dict.fromkeys(paths))


def load_context(request: AgentRequest, data_root: Path = Path("data"), config_root: Path = Path("config/projects")) -> dict[str, Any]:
    context = {"knowledge": {}, "analytics": {}, "prompt": {}, "missing_refs": []}
    knowledge_refs = list(request.context.get("knowledge_refs", []))
    analytics_refs = list(request.context.get("analytics_refs", []))
    prompt_refs = list(request.context.get("prompt_refs", []))
    for ref in knowledge_refs:
        found = next((path for path in _candidate_paths(request.project, ref, data_root, config_root) if path.exists()), None)
        if found:
            context["knowledge"][ref] = {"path": str(found), "content": found.read_text(encoding="utf-8")}
        else:
            context["missing_refs"].append(ref)
    for ref in analytics_refs:
        found = next((path for path in _candidate_paths(request.project, ref, data_root, config_root) if path.exists()), None)
        if found:
            context["analytics"][ref] = {"path": str(found), "content": found.read_text(encoding="utf-8")}
        else:
            context["analytics"][ref] = {"path": None, "content": "analytics advisory unavailable; request M08 read_advisory"}
    for ref in prompt_refs:
        context["prompt"][ref] = {"path": None, "content": "prompt ref registered for downstream module"}
    return context
