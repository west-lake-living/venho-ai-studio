from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from growth_engine.application.content.generate_package import GenerationUnknown
from growth_engine.application.content.run_lanes import LanePackageFactory
from growth_engine.application.dto import FactSnapshot
from growth_engine.application.media.evaluate_qc import EvaluateQc, QcPaidCallUnknown
from growth_engine.application.media.prepare_variant import PrepareVariant
from growth_engine.application.review.create_revision import CreateRevision, RevisionDraft
from growth_engine.application.scheduling.reserve_target import ReserveTarget, TargetAlreadyReserved
from growth_engine.domain.delivery.states import DeliveryState
from growth_engine.domain.media.media_policy import FACEBOOK_PHOTO_V1, INSTAGRAM_PHOTO_V1


_PRODUCTION_TARGETS = {"fb_hanoi": ("facebook", "1124616474074140")}


@dataclass(frozen=True)
class ContentJobsResult:
    claimed: int = 0
    completed: int = 0
    deferred: int = 0
    failed: int = 0
    unknown: int = 0


class _WaitingForContentDependency(Exception):
    pass


class ContentJobsWorker:
    """Lease and process generation, media-normalization and revision-assembly jobs."""

    def __init__(
        self,
        uow_factory: Callable[[], Any],
        clock: Any,
        ids: Any,
        media_store: Any,
        generator: LanePackageFactory,
        reserve_target: ReserveTarget,
        prepare_variant: PrepareVariant,
        evaluate_qc: EvaluateQc,
        create_revision: CreateRevision,
        transform_version_for_profile: Callable[[Any], str],
        *,
        environment: str,
        lease_ms: int = 10 * 60 * 1000,
        dependency_delay_ms: int = 15_000,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._media_store = media_store
        self._generator = generator
        self._reserve_target = reserve_target
        self._prepare_variant = prepare_variant
        self._evaluate_qc = evaluate_qc
        self._create_revision = create_revision
        self._transform_version_for_profile = transform_version_for_profile
        self._environment = environment
        self._lease_ms = lease_ms
        self._dependency_delay_ms = dependency_delay_ms
        self._owner = f"content-jobs-{secrets.token_urlsafe(8)}"

    def process_once(self, *, limit: int = 20) -> ContentJobsResult:
        if type(limit) is not int or limit < 1:
            raise ValueError("content job limit must be positive")
        claimed = completed = deferred = failed = unknown = 0
        for _ in range(limit):
            lease = self._claim_next()
            if lease is None:
                break
            claimed += 1
            job_id, lease_token, kind, payload = lease
            try:
                if kind == "generate_slot":
                    self._generate_slot(payload)
                elif kind == "prepare_variant":
                    self._prepare(payload)
                elif kind == "assemble_revision":
                    self._assemble(payload)
                else:
                    raise ValueError("unsupported content job kind")
            except _WaitingForContentDependency:
                self._defer(job_id, lease_token, "waiting_for_content_dependency")
                deferred += 1
            except (GenerationUnknown, QcPaidCallUnknown):
                self._complete(job_id, lease_token, "UNKNOWN", "paid_provider_result_unknown")
                unknown += 1
            except Exception as error:
                self._complete(job_id, lease_token, "FAILED", type(error).__name__)
                failed += 1
            else:
                self._complete(job_id, lease_token, "SUCCEEDED", None)
                completed += 1
        return ContentJobsResult(claimed, completed, deferred, failed, unknown)

    def _claim_next(self) -> tuple[str, str, str, dict[str, object]] | None:
        now_ms = self._clock.now_ms()
        with self._uow_factory().begin_immediate() as tx:
            row = tx.connection.execute(
                """SELECT id, kind, state, run_at, lease_until, payload_json
                   FROM jobs WHERE lane='jobs' AND kind IN ('generate_slot','prepare_variant','assemble_revision')
                     AND run_at<=? AND (state='PENDING' OR (state='RUNNING' AND lease_until<=?))
                   ORDER BY CASE kind WHEN 'generate_slot' THEN 0 WHEN 'prepare_variant' THEN 1 ELSE 2 END,
                            run_at, created_at, id LIMIT 1""",
                (now_ms, now_ms),
            ).fetchone()
            if row is None:
                return None
            conditions: dict[str, object] = {
                "id": str(row["id"]),
                "state": str(row["state"]),
                "run_at": ("<=", now_ms),
            }
            if row["state"] == "RUNNING":
                conditions["lease_until"] = ("<=", now_ms)
            result = tx.jobs.claim_with_lease(
                conditions,
                owner=self._owner,
                lease_ms=self._lease_ms,
                now_ms=now_ms,
            )
            if result is None:
                return None
            claimed, token = result
            payload = json.loads(str(claimed["payload_json"]))
            if not isinstance(payload, dict):
                raise ValueError("content job payload must be an object")
            return str(claimed["id"]), token, str(claimed["kind"]), payload

    def _generate_slot(self, payload: Mapping[str, object]) -> None:
        slot_id = _required(payload, "slot_id")
        lane = _required(payload, "lane")
        channel_key = _required(payload, "channel_key")
        with self._uow_factory().read_only() as tx:
            controls = tx.controls.get(self._environment)
            if self._environment == "production" and (
                controls is None or controls.mode.value != "DISABLED" or not controls.global_pause
            ):
                raise ValueError("production slot preparation requires DISABLED and global_pause=1")
            targets = tx.connection.execute(
                """SELECT st.id AS target_id, c.channel_key, c.platform, c.remote_account_id,
                          c.enabled, c.paused,
                          EXISTS(SELECT 1 FROM channel_configs cc WHERE cc.channel_id=c.id) AS configured
                   FROM slot_targets st JOIN channels c ON c.id=st.channel_id
                   WHERE st.slot_id=? AND c.environment=? ORDER BY c.channel_key""",
                (slot_id, self._environment),
            ).fetchall()
        enabled = [row for row in targets if bool(row["enabled"])]
        if not enabled or any(str(row["channel_key"]) != channel_key for row in enabled):
            raise ValueError("queued slot channel targets changed after preparation")
        expected = _PRODUCTION_TARGETS.get(channel_key)
        if self._environment == "production" and (
            expected is None
            or len(enabled) != 1
            or (str(enabled[0]["platform"]), str(enabled[0]["remote_account_id"])) != expected
            or bool(enabled[0]["paused"])
            or not bool(enabled[0]["configured"])
        ):
            raise ValueError("production content job no longer matches the prepare-only target mapping")
        package = self._generator.create(slot_id, lane, excluded_topic_keys=())
        for target in enabled:
            with self._uow_factory().read_only() as tx:
                existing = tx.connection.execute(
                    "SELECT id, package_id FROM deliveries WHERE target_id=? AND active=1",
                    (target["target_id"],),
                ).fetchone()
            if existing is not None:
                if str(existing["package_id"]) != package.package_id:
                    raise TargetAlreadyReserved("slot target has an active delivery from another package")
                continue
            self._reserve_target.execute(
                str(target["target_id"]),
                package_id=package.package_id,
                lane=lane,
                correlation_id=f"prepare-slot:{slot_id}:{channel_key}",
            )

    def _prepare(self, payload: Mapping[str, object]) -> None:
        asset_id = _required(payload, "asset_id")
        profile = _media_profile(_required(payload, "media_profile"))
        version = self._transform_version_for_profile(profile)
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                "SELECT id FROM media_variants WHERE asset_id=? AND transform_version=? ORDER BY created_at DESC LIMIT 1",
                (asset_id, version),
            ).fetchone()
        if row is None:
            self._prepare_variant.execute(asset_id, profile, version)

    def _assemble(self, payload: Mapping[str, object]) -> None:
        delivery_id = _required(payload, "delivery_id")
        with self._uow_factory().read_only() as tx:
            row = tx.connection.execute(
                """SELECT d.id, d.state, d.row_version, d.current_revision_id,
                          p.fact_snapshot_json, p.fact_snapshot_hash, p.source_snapshot_json,
                          c.channel_key, c.platform, c.project_id,
                          cc.caption_profile, cc.id AS channel_config_id,
                          s.scheduled_at
                   FROM deliveries d JOIN content_packages p ON p.id=d.package_id
                   JOIN channels c ON c.id=d.channel_id
                   JOIN channel_configs cc ON cc.channel_id=c.id
                   JOIN slots s ON s.id=(SELECT slot_id FROM slot_targets WHERE id=d.target_id)
                   WHERE d.id=? AND c.environment=? ORDER BY cc.version DESC LIMIT 1""",
                (delivery_id, self._environment),
            ).fetchone()
            if row is None:
                raise ValueError("revision assembly delivery is missing")
            state = DeliveryState(str(row["state"]))
            if state is not DeliveryState.DRAFT:
                return
            snapshot = json.loads(str(row["source_snapshot_json"]))
            image_options = snapshot.get("images", [])
            if not isinstance(image_options, list) or not image_options:
                raise ValueError("content package has no generated or curated image option")
            captions = snapshot.get("captions_by_profile", {})
            if not isinstance(captions, dict):
                raise ValueError("content package captions are invalid")
            caption_profile = str(row["caption_profile"] or "default")
            caption = captions.get(caption_profile) or captions.get("default")
            if not isinstance(caption, str) or not caption.strip():
                raise ValueError("content package has no caption for the channel profile")
            facts_value = json.loads(str(row["fact_snapshot_json"]))
            facts_hash = str(row["fact_snapshot_hash"])
            revision_version = int(row["row_version"])
            project = str(row["project_id"])
            platform = str(row["platform"])

        profile = INSTAGRAM_PHOTO_V1 if platform == "instagram" else FACEBOOK_PHOTO_V1
        candidates: dict[str, tuple[Any, Any]] = {}
        for option in image_options:
            if not isinstance(option, dict):
                continue
            option_id = str(option.get("option_id", "")).upper()
            if option_id not in {"A", "C", "FALLBACK"}:
                continue
            asset_id = option.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id:
                continue
            version = self._transform_version_for_profile(profile)
            with self._uow_factory().read_only() as tx:
                variant_row = tx.connection.execute(
                    """SELECT id FROM media_variants
                       WHERE asset_id=? AND transform_version=? ORDER BY created_at DESC LIMIT 1""",
                    (asset_id, version),
                ).fetchone()
                pending = tx.connection.execute(
                    """SELECT state FROM jobs WHERE kind='prepare_variant'
                       AND business_key=? ORDER BY created_at DESC LIMIT 1""",
                    (f"prepare-variant:{asset_id}:{profile.name}",),
                ).fetchone()
            if variant_row is None:
                if pending is not None and str(pending["state"]) in {"FAILED", "DEAD", "UNKNOWN"}:
                    raise ValueError("required media variant preparation did not succeed")
                raise _WaitingForContentDependency
            variant_id = str(variant_row["id"])
            provenance = option.get("provenance", {})
            subject = (
                str(provenance.get("dna_subject"))
                if isinstance(provenance, dict) and provenance.get("dna_subject")
                else "outside"
            )
            qc_report = self._evaluate_qc.execute(
                variant_id=variant_id,
                caption=caption,
                facts=FactSnapshot(facts_value, facts_hash),
                project=project,
                subject=subject,
            )
            candidates[option_id] = (variant_id, qc_report)

        selected = _select_option(candidates)
        if selected is None:
            raise ValueError("no eligible JPEG option passed the automated safety gate")
        variant_id, _report = candidates[selected]
        self._create_revision.execute(
            delivery_id,
            expected_row_version=revision_version,
            draft=RevisionDraft(caption=caption, variant_id=variant_id),
            actor="growth-engine-jobs",
        )

    def _complete(self, job_id: str, token: str, state: str, error: str | None) -> None:
        now_ms = self._clock.now_ms()
        with self._uow_factory().begin_immediate() as tx:
            if not tx.jobs.complete(
                job_id,
                token,
                updated_at_ms=now_ms,
                state=state,
                last_error=error,
            ):
                raise RuntimeError("content job lease was lost")

    def _defer(self, job_id: str, token: str, reason: str) -> None:
        now_ms = self._clock.now_ms()
        with self._uow_factory().begin_immediate() as tx:
            if not tx.jobs.defer(
                job_id,
                token,
                run_at_ms=now_ms + self._dependency_delay_ms,
                updated_at_ms=now_ms,
                last_error=reason,
            ):
                raise RuntimeError("content job lease was lost before dependency defer")


def _required(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"content job {key} is required")
    return value


def _media_profile(name: str):
    profiles = {
        FACEBOOK_PHOTO_V1.name: FACEBOOK_PHOTO_V1,
        INSTAGRAM_PHOTO_V1.name: INSTAGRAM_PHOTO_V1,
    }
    try:
        return profiles[name]
    except KeyError as error:
        raise ValueError("content job media profile is unsupported") from error


def _select_option(candidates: Mapping[str, tuple[Any, Any]]) -> str | None:
    for option_id in ("A", "C"):
        candidate = candidates.get(option_id)
        if candidate is not None and candidate[1].decision.value == "PASS":
            return option_id
    for option_id in ("A", "C"):
        candidate = candidates.get(option_id)
        if candidate is not None and candidate[1].decision.value == "REVIEW":
            return option_id
    fallback = candidates.get("FALLBACK")
    primary_failed = all(
        candidates.get(option_id) is not None
        and candidates[option_id][1].decision.value == "FAIL"
        for option_id in ("A", "C")
    )
    if primary_failed and fallback is not None and fallback[1].decision.value in {"PASS", "REVIEW"}:
        return "FALLBACK"
    return None
