from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from content_studio.content_context import DEFAULT_CONFIG_ROOT, DEFAULT_DATA_ROOT, load_content_config
from content_studio.content_engine import ContentEngineResult, generate_content
from content_studio.schemas.content_request import ContentRequest
from publishing_gateway.publication_registry import PublicationRegistry

# Vietnamese weekday numbering used throughout this codebase (T2=Monday ...
# T7=Saturday) matches config/projects/venho_hotel/growth/cadence_policy.yaml
# and growth_orchestrator.application.special_lane's T3-scan -> T7-publish
# timeline: Mon/Wed/Fri are the regular lane, Saturday is the special lane.
REGULAR_CADENCE_DAYS = {"monday", "wednesday", "friday"}
SPECIAL_CADENCE_DAY = "saturday"
CADENCE_DAYS = REGULAR_CADENCE_DAYS | {SPECIAL_CADENCE_DAY}

PLATFORM_CONTENT_TYPES = {
    "facebook": "facebook_post",
    "instagram": "instagram_post",
    "threads": "threads_post",
    "zalo": "zalo_post",
}
DEFAULT_PLATFORMS = ["facebook", "instagram", "threads", "zalo"]


@dataclass
class DailyCycleResult:
    day: str
    topic: dict[str, str]
    publications: list[dict[str, Any]]


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


def _dna_source_ref(project: str, dna_subject: str, data_root: Path) -> dict[str, str]:
    dna_path = data_root / project / "knowledge" / f"VENHO_HOTEL_{dna_subject.upper()}_DNA.json"
    payload = json.loads(dna_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(dna_path.read_bytes()).hexdigest()
    return {
        "file": dna_path.name,
        "dna_version": str(payload.get("dna_version") or payload.get("version") or "1.0"),
        "hash": f"sha256:{digest}",
    }


def _content_payload(result: ContentEngineResult) -> dict[str, Any]:
    output = result.output
    text = f"{output.hook}\n\n{output.body}\n\n{output.cta}"
    if output.hashtags:
        text += "\n\n" + " ".join(output.hashtags)
    return {
        "title": output.title,
        "text": text,
        "hashtags": output.hashtags,
        "visual_note": output.visual_note,
        "source_prompt_file": output.source_prompt.file,
    }


def run_daily_cycle(
    day: str,
    *,
    project: str = "venho_hotel",
    platforms: Optional[list[str]] = None,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    data_root: Path = DEFAULT_DATA_ROOT,
    registry: Optional[PublicationRegistry] = None,
) -> DailyCycleResult:
    """Generate this cadence day's content drafts and queue them for approval.

    This is the cron-side half of the publish flow: it does NOT dispatch
    anything (no Make.com webhook is fired here). It only produces drafts via
    content_studio and reserves a PENDING_APPROVAL row per platform in
    PublicationRegistry. The actual post only fires when a human approves
    (see approve_and_dispatch), matching Harry's decision that publishing is
    Approve-triggered, not cron-triggered -- the cron's job is content prep.
    """
    day = day.lower()
    if day not in CADENCE_DAYS:
        raise ValueError(f"'{day}' is not a cadence day; expected one of {sorted(CADENCE_DAYS)}")

    config = load_content_config(project, config_root=config_root)
    topic = _pick_topic(config, day, project, data_root)
    source_ref = _dna_source_ref(project, topic["dna_subject"], data_root)
    registry = registry or PublicationRegistry(project, data_root=data_root)

    publications: list[dict[str, Any]] = []
    for platform in platforms or DEFAULT_PLATFORMS:
        request = ContentRequest(
            project=project,
            content_type=PLATFORM_CONTENT_TYPES[platform],
            topic=topic["topic"],
            target_audience="Vietnamese leisure guests",
            content_pillar=topic["pillar"],
            tone=config["tone_of_voice"].get("tone", {}).get("default", "warm, clear, trustworthy"),
            target_language="vi",
            cta_type="booking_soft",
            source_knowledge=[source_ref],
        )
        result = generate_content(request, config_root=config_root, data_root=data_root, validate=False)

        publication_id = f"pub-{day}-{platform}-{uuid.uuid4().hex[:8]}"
        idempotency_key = hashlib.sha256(
            f"{project}|{platform}|{result.json_path}".encode("utf-8")
        ).hexdigest()
        reserved = registry.reserve(
            {
                "publication_id": publication_id,
                "content_package_id": str(result.json_path),
                "idempotency_key": idempotency_key,
                "platform": platform,
            }
        )
        publication = registry.update(
            reserved["publication_id"],
            status="PENDING_APPROVAL",
            content=_content_payload(result),
        )
        publications.append(publication)

    return DailyCycleResult(day=day, topic=topic, publications=publications)
