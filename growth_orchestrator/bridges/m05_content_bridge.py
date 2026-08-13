from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from agent_studio.growth.scenario_registry import ScenarioRegistry
from content_studio.content_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT, load_content_config
from content_studio.content_engine import generate_content
from content_studio.generators.claude_social_generator import claude_social_generator
from content_studio.schemas.content_request import ContentRequest, SourceKnowledgeRef
from growth_orchestrator.weekend_events import load_verified_weekend_events

GeneratorFn = Callable[..., dict[str, Any]]

SATURDAY_LANE = "saturday_trend"

_PLATFORM_CONTENT_TYPES = {
    "facebook": "facebook_post",
    "instagram": "instagram_post",
    "threads": "threads_post",
    "zalo": "zalo_post",
}


class M05ContentBridge:
    """Real bridge to content_studio -- replaces the old 3-hardcoded-angle stub.

    One candidate per call, for `brief["platforms"][0]` (the domain model does
    not yet represent "one package, many platform variants", so a multi-
    platform brief is expected to be split into one brief per platform by the
    caller -- see growth_orchestrator/application/daily_cycle.py).

    `scene_summary.entities` is taken from the scenario's `required_entities`
    in scenario_registry.yaml, not extracted from the generated prose --
    this is honest by construction (M02's prompt builder embeds those DNA
    facts into the final_prompt, verified by prompt_studio's own tests) but
    is not proof the *generated text* actually mentions them. Real NLP
    entity-extraction from prose is not built.
    """

    def __init__(
        self,
        *,
        config_root: Path = DEFAULT_CONFIG_ROOT,
        data_root: Path = DEFAULT_DATA_ROOT,
        scenario_registry: ScenarioRegistry | None = None,
        generator_fn: GeneratorFn = claude_social_generator,
    ) -> None:
        self.config_root = config_root
        self.data_root = data_root
        self.scenario_registry = scenario_registry or ScenarioRegistry.from_file()
        self.generator_fn = generator_fn

    def _dna_source_ref(self, project: str, dna_subject: str) -> SourceKnowledgeRef:
        root = self.data_root / project / "knowledge"
        dna_path = root / f"VENHO_HOTEL_{dna_subject.upper()}_DNA.json"
        if dna_subject == "lake_view_room":
            variants = sorted(root.glob("VENHO_HOTEL_LAKE_VIEW_ROOM_[12]_DNA.json"))
            if variants:
                dna_path = variants[0]
        payload = json.loads(dna_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(dna_path.read_bytes()).hexdigest()
        return SourceKnowledgeRef(
            file=dna_path.name,
            dna_version=str(payload.get("dna_version") or payload.get("version") or "1.0"),
            hash=f"sha256:{digest}",
        )

    def generate_candidates(self, brief: dict[str, Any]) -> list[dict[str, Any]]:
        platform = brief["platforms"][0]
        project = brief.get("project", "venho_hotel")
        scenario_key = brief["visual"]["scenario_key"]
        scenario = self.scenario_registry.resolve(scenario_key)
        config = load_content_config(project, config_root=self.config_root)
        lane = brief.get("lane", "daily")
        verified_events = (
            load_verified_weekend_events(project, config_root=self.config_root) if lane == SATURDAY_LANE else []
        )
        request = ContentRequest(
            project=project,
            content_type=_PLATFORM_CONTENT_TYPES[platform],
            topic=brief["single_minded_message"],
            target_audience=brief.get("audience_segment", "Vietnamese leisure guests"),
            content_pillar=brief.get("content_angle", "growth_agent"),
            tone=config["tone_of_voice"].get("tone", {}).get("default", "warm, clear, trustworthy"),
            target_language="vi",
            cta_type="booking_soft",
            source_knowledge=[self._dna_source_ref(project, scenario.dna_subject)],
            lane=lane,
            verified_events=verified_events,
            dna_subject=scenario.dna_subject,
            # 2026-08-13 diversity fix: proof_points/recent_topics/prompt_rules
            # are non-enum extensions on the brief (additionalProperties: true
            # in creative_brief.schema.json) -- see daily_cycle._build_creative_brief.
            research_facts=brief.get("proof_points", []),
            recent_topics=brief.get("recent_topics", []),
            prompt_rules=brief.get("prompt_rules", "default"),
        )
        result = generate_content(
            request,
            config_root=self.config_root,
            data_root=self.data_root,
            generator_fn=self.generator_fn,
            validate=False,
        )
        output = result.output

        return [
            {
                "id": f"{brief['id']}-content_studio",
                "creative_brief_id": brief["id"],
                "platform": platform,
                "dna_subject": scenario.dna_subject,
                "language": output.target_language,
                "angle_type": "content_studio",
                "hook": output.hook,
                "title": output.title,
                "body": output.body,
                "cta": output.cta,
                "hashtags": output.hashtags,
                "alt_text": output.title,
                "claims": [],
                "scene_summary": {
                    "location": scenario.display_name,
                    "time_of_day": "morning",
                    "entities": list(scenario.required_entities),
                    "mood": "calm",
                },
                "source_prompt_file": output.source_prompt.file,
                "content_package_paths": {"markdown": str(result.markdown_path), "json": str(result.json_path)},
                "rubric": {"total": 0},
            }
        ]
