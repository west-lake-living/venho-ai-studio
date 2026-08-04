from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import jsonschema

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver
from agent_studio.growth.scenario_registry import ScenarioRegistry
from content_studio.content_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT, load_content_config
from content_studio.prompt_bridge import slugify
from growth_orchestrator.application.run_content_pipeline import run_content_pipeline
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge
from image_studio_runtime.adapters.gpt_image_provider import gpt_image_provider_from_env
from image_studio_runtime.application.generate_image import generate_image_run
from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from publishing_gateway.publication_registry import PublicationRegistry

# Vietnamese weekday numbering used throughout this codebase (T2=Monday ...
# T7=Saturday) matches config/projects/venho_hotel/growth/cadence_policy.yaml
# and growth_orchestrator.application.special_lane's T3-scan -> T7-publish
# timeline: Mon/Wed/Fri are the regular lane, Saturday is the special lane.
REGULAR_CADENCE_DAYS = {"monday", "wednesday", "friday"}
SPECIAL_CADENCE_DAY = "saturday"
CADENCE_DAYS = REGULAR_CADENCE_DAYS | {SPECIAL_CADENCE_DAY}

DEFAULT_PLATFORMS = ["facebook", "instagram", "threads", "zalo"]

# One scenario per DNA subject used by content_pillars.yaml. Real scenario
# selection (multiple angles per subject) is future work -- this is the
# minimum needed so every CreativeBrief has a valid, DNA-backed scenario_key.
SCENARIO_BY_DNA_SUBJECT = {
    "westlake": "venho_west_lake_landscape",
    "lake_view_room": "venho_lake_view_room_sunrise",
    "outside": "venho_rooftop_sunrise",
}

_CREATIVE_BRIEF_SCHEMA = json.loads(Path("contracts/creative_brief.schema.json").read_text(encoding="utf-8"))


@dataclass
class DailyCycleResult:
    day: str
    topic: dict[str, str]
    publications: list[dict[str, Any]]
    packages: list[dict[str, Any]] = field(default_factory=list)


def _rotation_state_path(project: str, data_root: Path) -> Path:
    return data_root / project / "growth" / "rotation_state.json"


def _next_rotation_index(project: str, data_root: Path, lane: str) -> int:
    """Advance and persist a per-lane rotation cursor (regular vs special).

    Two separate cursors (not one shared index) so the Saturday special-lane
    topic list rotates independently of the Mon/Wed/Fri regular pillars.
    """
    path = _rotation_state_path(project, data_root)
    state = {}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    index = state.get(lane, 0)
    state[lane] = index + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def _pick_topic(config: dict[str, Any], day: str, project: str, data_root: Path) -> dict[str, str]:
    pillars_config = config["content_pillars"]
    if day == SPECIAL_CADENCE_DAY:
        lane, groups = "special", pillars_config.get("special_topics", [])
    else:
        lane, groups = "regular", pillars_config.get("pillars", [])
    if not groups:
        raise ValueError(f"No topic groups configured for lane '{lane}' in content_pillars.yaml")

    flat = [
        {"pillar": group.get("name", group.get("id", lane)), "dna_subject": group["dna_subject"], "topic": topic}
        for group in groups
        for topic in group.get("topics", [])
    ]
    index = _next_rotation_index(project, data_root, lane)
    return flat[index % len(flat)]


def _build_creative_brief(topic: dict[str, str], platform: str, day: str, project: str, scenario_registry: ScenarioRegistry) -> dict[str, Any]:
    scenario_key = SCENARIO_BY_DNA_SUBJECT[topic["dna_subject"]]
    scenario = scenario_registry.resolve(scenario_key)
    brief: dict[str, Any] = {
        "schema_version": "1.0",
        "id": f"brief-{day}-{platform}-{uuid.uuid4().hex[:8]}",
        "version": 1,
        "brand_id": "venho-hotel",
        "campaign_id": f"daily-cycle-{day}",
        "objective": "qualified_inquiry",
        "platforms": [platform],
        "audience_segment": "Vietnamese leisure guests",
        "funnel_stage": "consideration",
        "single_minded_message": topic["topic"],
        "proof_points": [],
        "content_angle": topic["pillar"],
        "cta": {"type": "booking_link", "destination_key": "hotel.website", "strength": "soft"},
        "visual": {
            "scenario_key": scenario_key,
            "required_entities": list(scenario.required_entities),
            "forbidden_entities": list(scenario.forbidden_entities),
            "target_formats": ["feed_4_5"],
        },
        "lane": "saturday_trend" if day == SPECIAL_CADENCE_DAY else "daily",
        "status": "LOCKED",
        "checksum": "",
        "project": project,
    }
    payload_for_checksum = {key: value for key, value in brief.items() if key != "checksum"}
    brief["checksum"] = "sha256:" + hashlib.sha256(
        json.dumps(payload_for_checksum, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    jsonschema.Draft202012Validator(_CREATIVE_BRIEF_SCHEMA).validate(brief)
    return brief


def _content_payload(candidate: dict[str, Any], *, image_run_path: Optional[str] = None) -> dict[str, Any]:
    text = f"{candidate['hook']}\n\n{candidate['body']}\n\n{candidate['cta']}"
    if candidate.get("hashtags"):
        text += "\n\n" + " ".join(candidate["hashtags"])
    return {
        "title": candidate.get("title", ""),
        "text": text,
        "hashtags": candidate.get("hashtags", []),
        "source_prompt_file": candidate.get("source_prompt_file"),
        "image_run_path": image_run_path,
    }


def _generate_topic_image(
    topic: dict[str, str],
    day: str,
    project: str,
    data_root: Path,
    scenario_registry: ScenarioRegistry,
    *,
    image_provider: Any,
    reference_resolver: ReferenceAssetResolver,
) -> Optional[Path]:
    """Generate one real image for the day's topic, shared across platforms.

    Returns None (not an exception) on any failure -- image generation is
    best-effort on top of the text pipeline: a disabled/misconfigured
    provider or a missing reference asset must not block queuing the text
    drafts for approval, since those are still independently useful.
    """
    try:
        scenario_key = SCENARIO_BY_DNA_SUBJECT[topic["dna_subject"]]
        scenario = scenario_registry.resolve(scenario_key)
        dna_path = data_root / project / "knowledge" / f"VENHO_HOTEL_{topic['dna_subject'].upper()}_DNA.json"
        dna = read_dna(dna_path)
        image_contract = build_image_prompt(dna, f"A real photo for: {topic['topic']}", brief_slug=slugify(topic["topic"]))
        reference_images = reference_resolver.resolve(list(scenario.reference_asset_ids)) if scenario.reference_asset_ids else None
        prompt_contract = {
            "creative_brief_id": f"daily-cycle-{day}",
            "scenario_key": scenario_key,
            "base_prompt": image_contract.final_prompt,
            "size": "1024x1280",
            "quality": "medium",
        }
        run_folder = generate_image_run(
            prompt_contract,
            content_package_id=f"daily-{day}-{slugify(topic['topic'])}",
            provider=image_provider,
            data_root=data_root,
            reference_images=reference_images,
        )
        return run_folder
    except (RuntimeError, KeyError, FileNotFoundError):
        # RuntimeError: provider disabled (no OPENAI_API_KEY) or transient
        # provider failure. KeyError: no reference_assets.yaml mapping for
        # this scenario's asset id. FileNotFoundError: DNA or reference
        # image file missing on disk. All three are expected, recoverable
        # conditions during rollout -- anything else should still raise.
        return None


def run_daily_cycle(
    day: str,
    *,
    project: str = "venho_hotel",
    platforms: Optional[list[str]] = None,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    registry: Optional[PublicationRegistry] = None,
    scenario_registry: Optional[ScenarioRegistry] = None,
    image_provider: Optional[Any] = None,
    reference_resolver: Optional[ReferenceAssetResolver] = None,
    generate_image: bool = True,
) -> DailyCycleResult:
    """Generate this cadence day's content drafts and queue them for approval.

    Real pipeline as of 2026-08-04: builds a LOCKED CreativeBrief per platform
    (contract-validated against creative_brief.schema.json), runs it through
    growth_orchestrator.run_content_pipeline -- M05ContentBridge (real
    content_studio call) -> M03ValidatorBridge (claim + alignment gate) --
    and only queues PENDING_APPROVAL in PublicationRegistry when the package
    comes back READY_FOR_REVIEW. NEEDS_REVISION/UNVALIDATED packages are
    returned in `.packages` for visibility but never reach the approval
    queue. This is the cron-side half of the publish flow: it does NOT
    dispatch anything -- publishing is Approve-triggered (see
    approve_and_dispatch), not cron-triggered.

    One real image is generated per topic (shared across all platforms, same
    photo concept) via GPTImageProvider -- best-effort: if the provider is
    disabled (no OPENAI_API_KEY) or a reference asset is missing, publications
    are still queued with `content.image_run_path = None` rather than failing
    the whole cycle. Set `generate_image=False` to skip it outright (e.g. cost
    control during rollout).
    """
    day = day.lower()
    if day not in CADENCE_DAYS:
        raise ValueError(f"'{day}' is not a cadence day; expected one of {sorted(CADENCE_DAYS)}")

    config = load_content_config(project, config_root=config_root)
    topic = _pick_topic(config, day, project, data_root)
    registry = registry or PublicationRegistry(project, data_root=data_root)
    scenario_registry = scenario_registry or ScenarioRegistry.from_file()
    content_bridge = M05ContentBridge(config_root=config_root, data_root=data_root, scenario_registry=scenario_registry)

    image_run_path: Optional[str] = None
    if generate_image:
        image_provider = image_provider or gpt_image_provider_from_env(os.environ)
        reference_resolver = reference_resolver or ReferenceAssetResolver.from_file()
        run_folder = _generate_topic_image(
            topic, day, project, data_root, scenario_registry,
            image_provider=image_provider, reference_resolver=reference_resolver,
        )
        image_run_path = str(run_folder) if run_folder else None

    publications: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    for platform in platforms or DEFAULT_PLATFORMS:
        brief = _build_creative_brief(topic, platform, day, project, scenario_registry)
        package = run_content_pipeline(brief, content_bridge=content_bridge)
        packages.append(package)
        if package["state"] != "READY_FOR_REVIEW":
            continue

        selected = next(c for c in package["copy_candidates"] if c["id"] == package["selected_copy_candidate_id"])
        publication_id = f"pub-{day}-{platform}-{uuid.uuid4().hex[:8]}"
        idempotency_key = hashlib.sha256(f"{project}|{platform}|{package['id']}".encode("utf-8")).hexdigest()
        # Canonical shape automation_studio.approval_snapshot expects (see
        # ContentPackage domain model) -- frozen at queue time and carried on
        # the registry row so approve_and_dispatch can build a real exact-
        # version approval snapshot instead of just flipping a status string.
        package_snapshot = {
            "id": package["id"],
            "copy_version_ids": [selected["id"]],
            "asset_version_ids": [],
            "validation_snapshot_id": hashlib.sha256(
                json.dumps(package["validation"], sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            "fact_version_ids": [],
            "brief_version_id": f"{brief['id']}@{brief['version']}",
        }
        reserved = registry.reserve(
            {
                "publication_id": publication_id,
                "content_package_id": package["id"],
                "idempotency_key": idempotency_key,
                "platform": platform,
            }
        )
        publication = registry.update(
            reserved["publication_id"],
            status="PENDING_APPROVAL",
            content=_content_payload(selected, image_run_path=image_run_path),
            creative_brief_id=brief["id"],
            package_snapshot=package_snapshot,
        )
        publications.append(publication)

    return DailyCycleResult(day=day, topic=topic, publications=publications, packages=packages)
