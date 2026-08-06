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
from analytics_feedback.attribution import AttributionPolicy, build_tracking_url
from growth_orchestrator.application.budget_gate import BudgetGate
from growth_orchestrator.application.evergreen_pool import choose_evergreen
from growth_orchestrator.application.run_content_pipeline import run_content_pipeline
from growth_orchestrator.application.special_lane import select_special_lane_candidate
from growth_orchestrator.bridges.m03_validator_bridge import M03ValidatorBridge
from growth_orchestrator.bridges.m05_content_bridge import M05ContentBridge
from image_studio_runtime.adapters.gpt_image_provider import gpt_image_provider_from_env
from image_studio_runtime.application.generate_image import generate_image_run
from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import read_dna
from growth_orchestrator.domain.publishing_slot import PublishingSlot
from publishing_gateway.fallback_images import fallback_image_url
from publishing_gateway.image_constraints import aspect_ratio_rejection
from publishing_gateway.publication_registry import PublicationRegistry
from shared.storage.evergreen_pool_store import EvergreenPoolStore
from shared.storage.google_drive import google_drive_uploader_from_env
from shared.jobs.slot_store import SlotStore
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


def _trend_candidate_topic_entries(project: str, data_root: Path) -> list[dict[str, Any]]:
    """Approved Trend Radar candidates (venho-growth trend-approve), shaped
    to slot into the same rotation pool as content_pillars.yaml's hand-
    curated special_topics. Best-effort: a broken/missing trend store must
    never block the Saturday pipeline, which has always worked off the
    hand-curated list alone."""
    try:
        from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

        store = TrendCandidateStore(project, data_root=data_root)
        return [
            {
                "pillar": "Trend Radar",
                "dna_subject": candidate.get("dna_subject", "westlake"),
                "topic": candidate.get("title", ""),
                "special_lane_type": candidate.get("type", "feature_story"),
                "verified_by_human": True,
                "trend_candidate_id": candidate["id"],
            }
            for candidate in store.list_eligible_for_saturday()
        ]
    except Exception:  # noqa: BLE001 - see docstring
        return []


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
                # lifestyle_trend/feature_story). Hand-curated entries
                # default to type 4 (feature_story) -- see content_pillars
                # .yaml comment. Real Trend Radar candidates (see below) get
                # their type from Claude's classification instead.
                entry["special_lane_type"] = group.get("type", "feature_story")
                entry["verified_by_human"] = group.get("verified_by_human", False)
            flat.append(entry)

    if lane == "special":
        flat.extend(_trend_candidate_topic_entries(project, data_root))

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
        if picked.get("trend_candidate_id"):
            try:
                from research_engine.trend_radar.trend_candidate_store import TrendCandidateStore

                TrendCandidateStore(project, data_root=data_root).mark_used(picked["trend_candidate_id"])
            except Exception:  # noqa: BLE001 - marking used is bookkeeping, never a gate on the real pick
                pass

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
    candidate: dict[str, Any],
    *,
    image_run_path: Optional[str] = None,
    image_public_url: Optional[str] = None,
    image_is_fallback: bool = False,
    publication_id: Optional[str] = None,
    platform: Optional[str] = None,
) -> dict[str, Any]:
    text = f"{candidate['hook']}\n\n{candidate['body']}\n\n{candidate['cta']}"
    if candidate.get("hashtags"):
        text += "\n\n" + " ".join(candidate["hashtags"])

    # Minimal attribution (Phase 6, Harry's call 2026-08-06): only Zalo can
    # carry a real clickable deep-link -- FB/IG posts here are plain text
    # (no link at all), so this is the one channel a real
    # ?utm_content=<publication_id> tracking URL can go out on today. See
    # analytics_feedback/attribution.py's module docstring for what's still
    # missing on the receiving side.
    tracking_url: Optional[str] = None
    if platform == "zalo" and publication_id:
        try:
            policy = AttributionPolicy.from_file()
            if policy.tracking_base_url:
                tracking_url = build_tracking_url(publication_id, base_url=policy.tracking_base_url, platform=platform)
                text += f"\n\n{tracking_url}"
        except Exception:  # noqa: BLE001 - a missing/malformed attribution_policy.yaml must not block queuing the text draft
            pass

    return {
        "title": candidate.get("title", ""),
        "text": text,
        "hashtags": candidate.get("hashtags", []),
        "source_prompt_file": candidate.get("source_prompt_file"),
        "image_run_path": image_run_path,
        # Local file paths mean nothing to Make.com's webhook -- it fetches
        # by public URL (see MakeGatewayAdapter.send()'s "image_url" field).
        # Never None since 2026-08-06: when image generation or the Drive
        # upload doesn't produce one, the caller substitutes an on-brand
        # hotel photo and sets image_is_fallback so a reviewer can tell the
        # two apart on the dashboard.
        "image_public_url": image_public_url,
        "image_is_fallback": image_is_fallback,
        "tracking_url": tracking_url,
    }


def _scorecard_signals(validation: dict[str, Any]) -> dict[str, Any]:
    """Pull the real, already-computed M03 scores out of a package's
    validation result so they survive on the registry row instead of being
    thrown away as soon as `package_snapshot`'s hash is taken (Phase 8,
    2026-08-06). Without this, `controlled_rollout.collect_real_scorecard_metrics`
    would have zero historical signal to build a real golden scorecard from
    -- every publication's validation had already happened and passed, the
    numbers just weren't kept anywhere.

    `validation["reports"]` is `[claim_report, alignment_report, content_report?]`
    (see M03ValidatorBridge.validate_package) -- content_report is only
    present when the package had a real markdown/dna_subject/project to
    validate against, so its absence here is a real "not scored" state, not
    a bug.
    """
    reports = validation.get("reports") or []
    claim_report = reports[0] if reports else {}
    content_report = next((r for r in reports if isinstance(r, dict) and "overall_score" in r), None)
    return {
        # ClaimValidator kill-switches = UNSUPPORTED/CONFLICTED/EXPIRED
        # critical claims -- a real proxy for "critical factual precision"
        # per publication (Part 1.3's north-star quality gate), computed
        # today, not retrofitted.
        "claim_kill_switch_triggered": bool(claim_report.get("kill_switches")),
        # brand_fit is the real weighted brand-adherence dimension inside
        # content_validator's rubric (Part 5.6/5.7) -- an honest proxy for
        # the plan's "brand_adherence" gate, not the same measurement
        # instrument the plan originally imagined (human/reviewer scored),
        # but it is a real number computed on every real draft today.
        "content_brand_fit": content_report.get("dna_match_score") if content_report else None,
        "content_overall_score": content_report.get("overall_score") if content_report else None,
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
        # Instagram rejects an out-of-window photo inside Make, long after this
        # code has recorded success, so the ratio is checked on the real bytes
        # here -- while there is still a good alternative. Declining to publish
        # falls through to the on-brand fallback photo, which beats a post that
        # dies on the platform's side.
        rejection = aspect_ratio_rejection(run_folder / artifact_name)
        if rejection:
            _send_alert_best_effort(
                "image_rejected_by_constraint",
                f"VENHO Growth: generated photo not published -- {rejection}. Fell back to a hotel photo.",
            )
            return None
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
    budget_gate: Optional[BudgetGate] = None,
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

    `budget_gate` (Phase 5, 2026-08-06) reserves against the real monthly
    cap before each real image-generation and vision-QC call; a blocked
    reservation raises RuntimeError, which the outer except below already
    treats as a normal recoverable failure -- a budget-blocked day degrades
    to "no image" exactly like a disabled provider does, never a crash.
    Defaults to a fresh BudgetGate so existing callers that don't pass one
    still get metered against the real ledger/policy files.
    """
    budget_gate = budget_gate or BudgetGate(project=project, data_root=data_root)
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
            image_reservation_id = f"image-{day}-{slugify(topic['topic'])}-{uuid.uuid4().hex[:8]}"
            image_reserved, image_evaluation = budget_gate.try_reserve("image_generation_minor", image_reservation_id)
            _alert_on_budget_threshold(image_evaluation)
            if not image_reserved:
                raise RuntimeError(f"budget cap reached ({image_evaluation['ratio']:.0%}) -- image generation skipped")
            try:
                run_folder = generate_image_run(
                    prompt_contract,
                    content_package_id=f"daily-{day}-{slugify(topic['topic'])}",
                    provider=image_provider,
                    data_root=data_root,
                    reference_images=reference_images,
                )
            except Exception:
                budget_gate.release(image_reservation_id, "image_generation_minor")
                raise
            budget_gate.commit(image_reservation_id, "image_generation_minor")

            manifest = json.loads((run_folder / "manifest.json").read_text(encoding="utf-8"))
            artifact_name = manifest["artifacts"][0]["path"]

            # Only the real "openai" provider spends real money -- "mock"
            # (test/dev default) never reaches VisionClient, so metering it
            # would just add ledger noise for a call that never happens.
            vision_reservation_id = f"vision-{day}-{slugify(topic['topic'])}-{uuid.uuid4().hex[:8]}"
            if image_validation_provider != "mock":
                vision_reserved, vision_evaluation = budget_gate.try_reserve("vision_qc_minor", vision_reservation_id)
                _alert_on_budget_threshold(vision_evaluation)
                if not vision_reserved:
                    raise RuntimeError(f"budget cap reached ({vision_evaluation['ratio']:.0%}) -- vision QC skipped")
            try:
                report = validate_image(
                    project, topic["dna_subject"], run_folder / artifact_name, provider=image_validation_provider
                )
            except Exception:
                if image_validation_provider != "mock":
                    budget_gate.release(vision_reservation_id, "vision_qc_minor")
                raise
            if image_validation_provider != "mock":
                budget_gate.commit(vision_reservation_id, "vision_qc_minor")

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


def _alert_on_budget_threshold(evaluation: dict[str, Any]) -> None:
    """Fire the (previously-defined, never-called) `budget_threshold_crossed`
    alert the first time -- and every time, no dedupe -- a reservation's
    evaluation reports 70%/85%/100% crossed (BudgetPolicy.evaluate's
    `alerts` list). Not deduped per month: acceptable at this cadence (a
    handful of real paid calls/week), and erring toward "too many alerts"
    is safer than silently going over budget unnoticed."""
    alerts = evaluation.get("alerts") or []
    if not alerts:
        return
    _send_alert_best_effort(
        "budget_threshold_crossed",
        f"VENHO Growth budget {'/'.join(alerts)}: {evaluation['ratio']:.0%} of {evaluation['monthly_cap_minor']:,} {evaluation['currency']} monthly cap.",
    )


def _send_alert_best_effort(event: str, message: str) -> None:
    """Fire a real Telegram alert if TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID are
    set, else silently no-op (MockTelegramNotifier / missing chat_id) --
    never raises. Mirrors `manage_queue.check_runway`'s alert convention;
    used here for the `evergreen_used`/`slot_missed` events already defined
    in `shared/notify/alert_policy.yaml` but previously never fired by any
    real caller."""
    from shared.notify.telegram import send_alert, telegram_notifier_or_mock_from_env

    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    try:
        send_alert(event, message, notifier=telegram_notifier_or_mock_from_env(os.environ), chat_id=chat_id)
    except Exception:  # noqa: BLE001 - an alert failure must never block real slot bookkeeping
        pass


def _slot_id_for(day: str, slot_date: str) -> str:
    # Matches growth_orchestrator.application.manage_slots.generate_slots'
    # deterministic slot_id scheme so a slot ensured by the weekly batch and
    # one ensured ad-hoc here always agree on identity.
    return f"slot-{slot_date}-{day}"


def _ensure_slot_best_effort(slot_store: SlotStore, *, day: str, slot_date: str) -> Optional[str]:
    """Get-or-create the slot for this cadence day, never raising.

    Prefers an already-ensured slot (weekly_cycle normally ensures the whole
    week's slots up front); falls back to inserting one directly here so
    run_daily_cycle stays usable standalone (CLI `daily-cycle`, tests) without
    requiring the caller to pre-run manage_slots.
    """
    slot_id = _slot_id_for(day, slot_date)
    try:
        if slot_store.get(slot_id) is None:
            slot_type = "special" if day == SPECIAL_CADENCE_DAY else "regular"
            lane = "special" if day == SPECIAL_CADENCE_DAY else "regular"
            slot_store.ensure_slots([PublishingSlot(slot_id=slot_id, slot_date=slot_date, slot_type=slot_type, lane=lane)])
        return slot_id
    except Exception:  # noqa: BLE001 - slot bookkeeping must never block real content generation
        return None


def _fill_slot_from_evergreen(
    *,
    project: str,
    data_root: Path,
    config_root: Path,
    registry: PublicationRegistry,
    slot_store: SlotStore,
    slot_id: str,
    day: str,
) -> Optional[dict[str, Any]]:
    """Evergreen Pool fallback (plan v3.1 §9.3, PB-004) -- tried once every
    platform's real generation attempt has failed for this slot, before the
    slot is allowed to go MISSED.

    Reuses a pre-approved past publication (added by Harry via CLI
    `evergreen-add`, never invented here) as this slot's draft. It still
    lands on PENDING_APPROVAL like any fresh draft -- Harry decided
    2026-08-06 that reused content gets exactly the same one-click Duyệt
    gate as new content, no auto-dispatch, so this can never itself publish
    anything (DoD #23 invariant holds regardless of pool contents).

    Returns the new publication row, or None if the pool has nothing
    eligible (empty, or every item still inside its reuse cooldown) -- the
    caller treats None as "evergreen pool exhausted" and proceeds to MISSED.
    """
    import yaml  # local import matches the existing pattern in cli.py's trend-scan command

    policy_path = config_root / project / "growth" / "queue_policy.yaml"
    cooldown_days = 90
    if policy_path.exists():
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        cooldown_days = policy.get("evergreen_reuse_cooldown_days", cooldown_days)

    pool = EvergreenPoolStore(project, data_root=data_root)
    item = choose_evergreen(pool.list_items(), cooldown_days=cooldown_days)
    if item is None:
        return None

    content = item.get("content") or {}
    publication_id = f"pub-{day}-evergreen-{uuid.uuid4().hex[:8]}"
    content_package_id = f"evergreen-{item['id']}-{day}"
    idempotency_key = hashlib.sha256(f"{project}|{item['platform']}|{content_package_id}".encode("utf-8")).hexdigest()
    reserved = registry.reserve(
        {
            "publication_id": publication_id,
            "content_package_id": content_package_id,
            "idempotency_key": idempotency_key,
            "platform": item["platform"],
        }
    )
    publication = registry.update(
        reserved["publication_id"],
        status="PENDING_APPROVAL",
        content=content,
        day=day,
        dna_subject=item.get("dna_subject"),
        slot_id=slot_id,
        filled_from="evergreen",
        evergreen_source_publication_id=item.get("source_publication_id"),
        # No creative_brief/claims on a reused post -- _preflight_claim_alignment
        # and edit_publication both already treat this as claim_alignment_skipped
        # rather than silently passing, same as any pre-2026-08-05 manual row.
    )
    slot_store.transition(slot_id, "EVERGREEN_FALLBACK", filled_from="evergreen", content_package_id=content_package_id)
    slot_store.transition(slot_id, "PENDING_APPROVAL")
    pool.mark_used(item["id"])
    return publication


def _run_content_pipeline_budgeted(
    brief: dict[str, Any],
    *,
    budget_gate: BudgetGate,
    day: str,
    platform: str,
    content_bridge: Optional[M05ContentBridge],
    validator_bridge: Optional[M03ValidatorBridge],
) -> dict[str, Any]:
    """Meter one real text-generation call (Phase 5, 2026-08-06) -- each
    call to this is 1 real gpt-5.5 call via M05ContentBridge's default
    generator_fn. A blocked reservation raises RuntimeError, caught by the
    per-platform try/except in `run_daily_cycle`'s loop exactly like any
    other real generation failure (recorded in `errors`, other platforms
    unaffected)."""
    reservation_id = f"text-{day}-{platform}-{uuid.uuid4().hex[:8]}"
    reserved, evaluation = budget_gate.try_reserve("text_generation_minor", reservation_id)
    _alert_on_budget_threshold(evaluation)
    if not reserved:
        raise RuntimeError(f"budget cap reached ({evaluation['ratio']:.0%}) -- text generation for {platform}/{day} skipped")
    try:
        package = run_content_pipeline(brief, content_bridge=content_bridge, validator_bridge=validator_bridge)
    except Exception:
        budget_gate.release(reservation_id, "text_generation_minor")
        raise
    budget_gate.commit(reservation_id, "text_generation_minor")
    return package


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
    slot_store: Optional[SlotStore] = None,
    slot_date: Optional[str] = None,
    budget_gate: Optional[BudgetGate] = None,
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

    `slot_store`/`slot_date` wire this cadence day into the PublishingSlot
    state machine (plan v3.1 §4.4) so the dashboard has real per-slot
    visibility (filled / stranded / missed) instead of only inferring it
    from PublicationRegistry rows. Adapted for the ephemeral GitHub Actions
    cron model (see shared.jobs.slot_store.SlotStore's module docstring):
    both are optional and default to a no-op (slot tracking skipped) so
    existing callers/tests that don't care about calendar dates are
    unaffected. Slot bookkeeping is always best-effort -- a bad transition
    or a missing slot never raises out of this function; it's diagnostic,
    not a gate on real content generation.
    """
    day = day.lower()
    if day not in CADENCE_DAYS:
        raise ValueError(f"'{day}' is not a cadence day; expected one of {sorted(CADENCE_DAYS)}")

    config = load_content_config(project, config_root=config_root)
    topic = _pick_topic(config, day, project, data_root)
    registry = registry or PublicationRegistry(project, data_root=data_root)
    budget_gate = budget_gate or BudgetGate(project=project, data_root=data_root, config_root=config_root)

    slot_id: Optional[str] = None
    if slot_store is not None and slot_date is not None:
        slot_id = _ensure_slot_best_effort(slot_store, day=day, slot_date=slot_date)
        if slot_id is not None:
            try:
                slot_store.transition(slot_id, "DRAFT_ASSIGNED")
            except Exception:  # noqa: BLE001 - see _ensure_slot_best_effort
                pass

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
            budget_gate=budget_gate,
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

    # No generated image (image generation off/failed, or Drive upload failed)
    # still has to reach Make.com with a fetchable photo URL -- FB/IG's photo
    # post modules require one and the scenario's HTTP module rejects a null
    # `url` outright, taking the text down with it. See
    # publishing_gateway.fallback_images for the why and the image set.
    image_is_fallback = image_public_url is None
    if image_is_fallback:
        image_public_url = fallback_image_url(topic.get("dna_subject"))

    publications: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for platform in platforms or DEFAULT_PLATFORMS:
        try:
            brief = _build_creative_brief(topic, platform, day, project, scenario_registry)
            package = _run_content_pipeline_budgeted(
                brief, budget_gate=budget_gate, day=day, platform=platform,
                content_bridge=content_bridge, validator_bridge=validator_bridge,
            )
            for _attempt in range(MAX_TEXT_ATTEMPTS - 1):
                if package["state"] == "READY_FOR_REVIEW":
                    break
                package = _run_content_pipeline_budgeted(
                    brief, budget_gate=budget_gate, day=day, platform=platform,
                    content_bridge=content_bridge, validator_bridge=validator_bridge,
                )
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
                content=_content_payload(
                    selected, image_run_path=image_run_path, image_public_url=image_public_url,
                    image_is_fallback=image_is_fallback,
                    publication_id=publication_id, platform=platform,
                ),
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
                slot_id=slot_id,
                # Persisted so edit_publication can re-run the real claim +
                # alignment validators (not just the content-quality rubric)
                # against an edited draft without needing to regenerate the
                # CreativeBrief from scratch -- see approve_and_dispatch.
                creative_brief=brief,
                claims=selected.get("claims", []),
                scene_summary=selected.get("scene_summary", {}),
                # Real M03 scores kept alongside the snapshot hash so Phase 8's
                # scorecard can aggregate real historical signal instead of
                # rebuilding validation after the fact -- see _scorecard_signals.
                scorecard_signals=_scorecard_signals(package["validation"]),
            )
            publications.append(publication)
        except Exception as exc:  # noqa: BLE001 - one platform's provider/network failure (rate limit, timeout) must not abort the other platforms' drafts for this day
            errors.append({"platform": platform, "error": f"{type(exc).__name__}: {exc}"})
            continue

    if slot_id is not None:
        try:
            if publications:
                # One PublishingSlot maps to N per-platform ContentPackages
                # here (daily_cycle builds a separate CreativeBrief per
                # platform) -- the slot isn't tied 1:1 to a single package,
                # so this just records the first as a traceability pointer.
                slot_store.transition(slot_id, "PENDING_APPROVAL", content_package_id=publications[0]["content_package_id"])
            else:
                # Every platform's real generation attempt failed -- try the
                # Evergreen Pool (v3.1 §9.3, PB-004) before giving up on this
                # slot. `assert_missed_only_after_evergreen_exhausted` is the
                # domain-level guard for this invariant; calling it here
                # (rather than only in its own unit test) is what actually
                # enforces "no MISSED before evergreen is exhausted" in
                # production.
                evergreen_publication = _fill_slot_from_evergreen(
                    project=project, data_root=data_root, config_root=config_root,
                    registry=registry, slot_store=slot_store, slot_id=slot_id, day=day,
                )
                if evergreen_publication is not None:
                    publications.append(evergreen_publication)
                    _send_alert_best_effort(
                        "evergreen_used", f"Slot {slot_id} ({day}) filled from Evergreen Pool -- cần Duyệt.",
                    )
                else:
                    slot = slot_store.get(slot_id)
                    if slot is not None:
                        slot.assert_missed_only_after_evergreen_exhausted(evergreen_exhausted=True)
                    slot_store.transition(slot_id, "MISSED")
                    _send_alert_best_effort(
                        "slot_missed", f"Slot {slot_id} ({day}) MISSED -- mọi platform + Evergreen Pool đều không có nội dung.",
                    )
        except Exception:  # noqa: BLE001 - see _ensure_slot_best_effort
            pass

    return DailyCycleResult(day=day, topic=topic, publications=publications, packages=packages, errors=errors)
