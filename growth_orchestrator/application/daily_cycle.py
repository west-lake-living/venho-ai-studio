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
from growth_orchestrator.application.special_lane import select_special_lane_candidate
from growth_orchestrator.bridges.m03_validator_bridge import M03ValidatorBridge
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge
from image_studio_runtime.adapters.gpt_image_provider import gpt_image_provider_from_env
from image_studio_runtime.application.generate_image import generate_image_run
from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from publishing_gateway.publication_registry import PublicationRegistry
from shared.storage.google_drive import google_drive_uploader_from_env
from validator_studio.image_validator import validate_image
from validator_studio.schemas.validation_base import Recommendation

# Harry's rule (2026-08-04): generated posts/images must pass real Validator
# scoring, not just get queued as-is -- a failed attempt is regenerated from
# scratch (fresh LLM/image call) up to this many times before giving up.
MAX_TEXT_ATTEMPTS = 3
MAX_IMAGE_ATTEMPTS = 2

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
    topic: dict[str, Any]
    publications: list[dict[str, Any]]
    packages: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


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


def _pick_topic(config: dict[str, Any], day: str, project: str, data_root: Path) -> dict[str, Any]:
    pillars_config = config["content_pillars"]
    if day == SPECIAL_CADENCE_DAY:
        lane, groups = "special", pillars_config.get("special_topics", [])
    else:
        lane, groups = "regular", pillars_config.get("pillars", [])
    if not groups:
        raise ValueError(f"No topic groups configured for lane '{lane}' in content_pillars.yaml")

    flat: list[dict[str, Any]] = []
    for group in groups:
        for topic in group.get("topics", []):
            entry: dict[str, Any] = {
                "pillar": group.get("name", group.get("id", lane)),
                "dna_subject": group["dna_subject"],
                "topic": topic,
            }
            if lane == "special":
                # v3.1 9.5 candidate typing (seasonal_nature/cultural_event/
                # lifestyle_trend/feature_story). No live trend/event feed
                # exists yet, so every hand-curated entry defaults to type 4
                # (feature_story) -- see content_pillars.yaml comment.
                entry["special_lane_type"] = group.get("type", "feature_story")
                entry["verified_by_human"] = group.get("verified_by_human", False)
            flat.append(entry)

    index = _next_rotation_index(project, data_root, lane)
    picked = flat[index % len(flat)]

    if lane == "special":
        # Real loại-4 fallback selection (special_lane.select_special_lane_candidate),
        # not just unit-tested in isolation. TR-D3: this only decides WHICH
        # candidate is proposed for approval -- it never approves anything.
        selected = select_special_lane_candidate(
            [{"type": picked["special_lane_type"], "verified_by_human": picked["verified_by_human"]}]
        )
        picked["special_lane_reason"] = selected["selected_reason"]

    return picked


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


def _content_payload(
    candidate: dict[str, Any], *, image_run_path: Optional[str] = None, image_public_url: Optional[str] = None
) -> dict[str, Any]:
    text = f"{candidate['hook']}\n\n{candidate['body']}\n\n{candidate['cta']}"
    if candidate.get("hashtags"):
        text += "\n\n" + " ".join(candidate["hashtags"])
    return {
        "title": candidate.get("title", ""),
        "text": text,
        "hashtags": candidate.get("hashtags", []),
        "source_prompt_file": candidate.get("source_prompt_file"),
        "image_run_path": image_run_path,
        # Local file paths mean nothing to Make.com's webhook -- it fetches
        # by public URL (see MakeGatewayAdapter.send()'s "image_url" field).
        # None until _upload_image_to_drive succeeds; the post still queues
        # text-only if Drive is unconfigured/unreachable (best-effort, same
        # policy as image generation itself).
        "image_public_url": image_public_url,
    }


def _upload_image_to_drive(
    run_folder: Path, *, day: str, content_package_id: str, uploader: Any
) -> Optional[str]:
    """Upload the validated image artifact to Drive and return a public URL.

    Best-effort like `_generate_topic_image`: Drive being unconfigured
    (`MockDriveUploader`, returns a fake but harmless URL -- guarded by
    `generate_image` config, not by this function) or a real upload failure
    (network, expired/revoked OAuth token, quota) must not block queuing the
    text drafts. Returns None on any failure; the text still queues with
    `image_public_url=None`.
    """
    try:
        manifest = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8"))
        artifact_name = manifest["artifacts"][0]["path"]
        return uploader.upload_and_publish(
            run_folder / artifact_name,
            folder_path=[day, content_package_id],
            mimetype="image/png",
        )
    except Exception:  # noqa: BLE001 - any Drive failure (network, auth, quota) must not abort text queuing
        return None


def _generate_topic_image(
    topic: dict[str, str],
    day: str,
    project: str,
    data_root: Path,
    scenario_registry: ScenarioRegistry,
    *,
    image_provider: Any,
    reference_resolver: ReferenceAssetResolver,
    image_validation_provider: str = "mock",
) -> Optional[Path]:
    """Generate one real image for the day's topic, shared across platforms.

    Returns None (not an exception) on any failure -- image generation is
    best-effort on top of the text pipeline: a disabled/misconfigured
    provider or a missing reference asset must not block queuing the text
    drafts for approval, since those are still independently useful.

    After generation, the image is run through validator_studio's real
    DNA-match validator (cross-modal: does the photo actually match the DNA
    subject it was supposed to depict, not just "an image exists"). Per
    Harry's rule (2026-08-04), only a real APPROVE verdict (score >= 90, see
    validator_studio.scoring.verdict_for_score) counts as passing -- a
    kill_switch or a sub-APPROVE score both discard the image and trigger a
    fresh regenerate attempt, up to MAX_IMAGE_ATTEMPTS, before giving up and
    queuing the text without a photo. The last attempt's report is written
    next to the artifact as image_validation_report.json for traceability
    even on final failure. `image_validation_provider` defaults to "mock"
    (no paid vision API call) to match this repo's 0-API-call test/cost
    discipline; pass "openai" (the real provider, see
    growth_orchestrator.cli) once Harry approves paid QC spend.
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
        for attempt in range(MAX_IMAGE_ATTEMPTS):
            run_folder = generate_image_run(
                prompt_contract,
                content_package_id=f"daily-{day}-{slugify(topic['topic'])}",
                provider=image_provider,
                data_root=data_root,
                reference_images=reference_images,
            )
            manifest = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8"))
            artifact_name = manifest["artifacts"][0]["path"]
            report = validate_image(
                project, topic["dna_subject"], run_folder / artifact_name, provider=image_validation_provider
            )
            (run_folder / "image_validation_report.json").write_text(
                report.model_dump_json(indent=2), encoding="utf-8"
            )
            if not report.kill_switch.triggered and report.verdict == Recommendation.APPROVE:
                return run_folder
        return None
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
    content_bridge: Optional[M05ContentBridge] = None,
    validator_bridge: Optional[M03ValidatorBridge] = None,
    image_validation_provider: str = "mock",
    drive_uploader: Optional[Any] = None,
) -> DailyCycleResult:
    """Generate this cadence day's content drafts and queue them for approval.

    Real pipeline as of 2026-08-04: builds a LOCKED CreativeBrief per platform
    (contract-validated against creative_brief.schema.json), runs it through
    growth_orchestrator.run_content_pipeline -- M05ContentBridge (real
    content_studio call) -> M03ValidatorBridge (claim + alignment + real
    scored content rubric) -- and only queues PENDING_APPROVAL in
    PublicationRegistry when the package comes back READY_FOR_REVIEW. Per
    Harry's rule (2026-08-04), a draft that fails validation is regenerated
    from scratch (fresh LLM call, new candidate) up to MAX_TEXT_ATTEMPTS
    before being given up on; the last attempt's package is still returned
    in `.packages` for visibility but never reaches the approval queue. This
    is the cron-side half of the publish flow: it does NOT dispatch anything
    -- publishing is Approve-triggered (see approve_and_dispatch), not
    cron-triggered.

    One real image is generated per topic (shared across all platforms, same
    photo concept) via GPTImageProvider -- best-effort: if the provider is
    disabled (no OPENAI_API_KEY) or a reference asset is missing, publications
    are still queued with `content.image_run_path = None` rather than failing
    the whole cycle. Set `generate_image=False` to skip it outright (e.g. cost
    control during rollout). `image_validation_provider` defaults to "mock"
    for test/cost safety -- pass "openai" for the real per-image vision QC
    gate (see growth_orchestrator.cli, which does this for the actual
    daily-cycle/weekly-cycle CLI commands).

    Once a photo passes validation, it is also uploaded to Google Drive and
    made publicly readable (`content.image_public_url`) -- Make.com's "HTTP:
    Get a file" step fetches by URL, so a local-only file path (the old
    behavior) never reached the actual Facebook/Instagram post. `drive_uploader`
    defaults to `google_drive_uploader_from_env` (real uploader if
    GOOGLE_DRIVE_TOKEN_JSON is set, else a no-op Mock) -- best-effort like
    image generation itself: an upload failure (network, expired token,
    quota) still queues the text draft, just without a photo attached.

    `content_bridge` defaults to a real M05ContentBridge, whose default
    `generator_fn` (gpt_social_generator) calls the OpenAI API (gpt-5.5) for
    real -- pass a bridge built with a mock generator_fn (e.g. in tests) to
    avoid billed calls. `validator_bridge` defaults to a real
    M03ValidatorBridge (real scored content rubric, also billed-free but CPU
    real) -- pass a bridge that always approves in tests that aren't
    exercising validation itself, since mock-generated boilerplate text
    reliably scores below the real APPROVE bar.
    """
    day = day.lower()
    if day not in CADENCE_DAYS:
        raise ValueError(f"'{day}' is not a cadence day; expected one of {sorted(CADENCE_DAYS)}")

    config = load_content_config(project, config_root=config_root)
    topic = _pick_topic(config, day, project, data_root)
    registry = registry or PublicationRegistry(project, data_root=data_root)
    scenario_registry = scenario_registry or ScenarioRegistry.from_file()
    content_bridge = content_bridge or M05ContentBridge(
        config_root=config_root, data_root=data_root, scenario_registry=scenario_registry
    )

    image_run_path: Optional[str] = None
    image_public_url: Optional[str] = None
    asset_version_ids: list[str] = []
    if generate_image:
        image_provider = image_provider or gpt_image_provider_from_env(os.environ)
        reference_resolver = reference_resolver or ReferenceAssetResolver.from_file()
        run_folder = _generate_topic_image(
            topic, day, project, data_root, scenario_registry,
            image_provider=image_provider, reference_resolver=reference_resolver,
            image_validation_provider=image_validation_provider,
        )
        if run_folder:
            image_run_path = str(run_folder)
            # RunStore folders are named after the image's run_id (see
            # image_studio_runtime.storage.run_store.RunStore.create_run) --
            # that's the real asset version identifier DoD #7 requires the
            # approval snapshot to reference.
            asset_version_ids = [run_folder.name]
            drive_uploader = drive_uploader or google_drive_uploader_from_env(os.environ)
            image_public_url = _upload_image_to_drive(
                run_folder, day=day, content_package_id=f"daily-{day}-{slugify(topic['topic'])}", uploader=drive_uploader
            )

    publications: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for platform in platforms or DEFAULT_PLATFORMS:
        try:
            brief = _build_creative_brief(topic, platform, day, project, scenario_registry)
            package = run_content_pipeline(brief, content_bridge=content_bridge, validator_bridge=validator_bridge)
            for _attempt in range(MAX_TEXT_ATTEMPTS - 1):
                if package["state"] == "READY_FOR_REVIEW":
                    break
                package = run_content_pipeline(brief, content_bridge=content_bridge, validator_bridge=validator_bridge)
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
                "asset_version_ids": asset_version_ids,
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
                content=_content_payload(selected, image_run_path=image_run_path, image_public_url=image_public_url),
                creative_brief_id=brief["id"],
                package_snapshot=package_snapshot,
                # day/pillar/topic so the dashboard can group same-day publications
                # (one per platform) into a single reviewable row instead of a flat
                # per-platform list -- see PublishingSection.tsx's GrowthApprovalQueue.
                day=day,
                pillar=topic["pillar"],
                topic=topic["topic"],
                # dna_subject alongside day/pillar/topic so edit_publication can
                # re-run the real content_validator rubric against the correct
                # DNA subject without needing the original CreativeBrief object
                # persisted anywhere -- see approve_and_dispatch.edit_publication.
                dna_subject=topic["dna_subject"],
            )
            publications.append(publication)
        except Exception as exc:  # noqa: BLE001 - one platform's provider/network failure (rate limit, timeout) must not abort the other platforms' drafts for this day
            errors.append({"platform": platform, "error": f"{type(exc).__name__}: {exc}"})
            continue

    return DailyCycleResult(day=day, topic=topic, publications=publications, packages=packages, errors=errors)
