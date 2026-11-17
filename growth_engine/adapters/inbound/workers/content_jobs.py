from __future__ import annotations

import json
import logging
import re
import secrets
import time
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
_ERROR_SECRET = re.compile(
    r"(?i)\b(authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password)"
    r"(\s*[:=]\s*|\s+)([^\s,;]+)"
)
_URL = re.compile(r"https?://[^\s\])}>,]+", re.IGNORECASE)
_LONG_SECRET = re.compile(r"\b[A-Za-z0-9_-]{48,}\b")
_API_KEY = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|EAA[A-Za-z0-9_-]{16,}|ya29\.[A-Za-z0-9._-]{16,})\b")
_ERROR_CODE = re.compile(r"^(?:ERR_)?[A-Z][A-Z0-9_]{1,96}$")
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContentJobsResult:
    claimed: int = 0
    completed: int = 0
    deferred: int = 0
    failed: int = 0
    unknown: int = 0


class _WaitingForContentDependency(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.public_message = message
        super().__init__(message)


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
            started = time.monotonic()
            _LOG.info("content job started: id=%s kind=%s", job_id, kind)
            try:
                if kind == "generate_slot":
                    self._generate_slot(payload)
                elif kind == "prepare_variant":
                    self._prepare(payload)
                elif kind == "assemble_revision":
                    self._assemble(payload)
                else:
                    raise ValueError("unsupported content job kind")
            except _WaitingForContentDependency as error:
                self._defer(job_id, lease_token, _format_error(error))
                deferred += 1
                _LOG.info(
                    "content job finished: id=%s kind=%s outcome=DEFERRED elapsed_ms=%d error=%s",
                    job_id, kind, _elapsed_ms(started), _format_error(error),
                )
            except (GenerationUnknown, QcPaidCallUnknown) as error:
                self._complete(job_id, lease_token, "UNKNOWN", _format_error(error))
                unknown += 1
                _LOG.info(
                    "content job finished: id=%s kind=%s outcome=UNKNOWN elapsed_ms=%d error=%s",
                    job_id, kind, _elapsed_ms(started), _format_error(error),
                )
            except Exception as error:
                safe_error = _format_error(error)
                self._complete(job_id, lease_token, "FAILED", safe_error)
                failed += 1
                _LOG.info(
                    "content job finished: id=%s kind=%s outcome=FAILED elapsed_ms=%d error=%s",
                    job_id, kind, _elapsed_ms(started), safe_error,
                )
            else:
                self._complete(job_id, lease_token, "SUCCEEDED", None)
                completed += 1
                _LOG.info(
                    "content job finished: id=%s kind=%s outcome=SUCCEEDED elapsed_ms=%d",
                    job_id, kind, _elapsed_ms(started),
                )
        return ContentJobsResult(claimed, completed, deferred, failed, unknown)

    def _claim_next(self) -> tuple[str, str, str, dict[str, object]] | None:
        now_ms = self._clock.now_ms()
        with self._uow_factory().begin_immediate() as tx:
            rows = tx.connection.execute(
                """SELECT id, kind, state, run_at, lease_until, payload_json
                   FROM jobs WHERE lane='jobs' AND kind IN ('generate_slot','prepare_variant','assemble_revision')
                     AND run_at<=? AND (state='PENDING' OR (state='RUNNING' AND lease_until<=?))
                   ORDER BY CASE kind WHEN 'generate_slot' THEN 0 WHEN 'prepare_variant' THEN 1 ELSE 2 END,
                            run_at, created_at, id LIMIT 100""",
                (now_ms, now_ms),
            ).fetchall()
            for row in rows:
                payload = json.loads(str(row["payload_json"]))
                if not isinstance(payload, dict):
                    raise ValueError("content job payload must be an object")
                if str(row["kind"]) == "assemble_revision":
                    wait_error = self._assembly_dependency_wait(tx.connection, payload)
                    if wait_error is not None:
                        safe_error = _format_error(wait_error)
                        tx.connection.execute(
                            """UPDATE jobs SET state='PENDING',run_at=?,last_error=?,lease_owner=NULL,
                                      lease_token=NULL,lease_until=NULL,updated_at=? WHERE id=?""",
                            (now_ms + self._dependency_delay_ms, safe_error, now_ms, row["id"]),
                        )
                        _LOG.info(
                            "content job waiting: id=%s kind=assemble_revision error=%s",
                            row["id"], safe_error,
                        )
                        continue
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
                    continue
                claimed, token = result
                return str(claimed["id"]), token, str(claimed["kind"]), payload
            return None

    def _assembly_dependency_wait(
        self, connection: Any, payload: Mapping[str, object]
    ) -> _WaitingForContentDependency | None:
        options = payload.get("asset_options")
        if not isinstance(options, list) or not options:
            return _WaitingForContentDependency(
                "ERR_GC2_MEDIA_SOURCE_PENDING",
                "No media source is attached to the existing content package.",
            )
        try:
            profile = _media_profile(_required(payload, "media_profile"))
            version = self._transform_version_for_profile(profile)
        except ValueError:
            return None  # Let the job handler persist the malformed payload as a failure.
        usable = [
            option for option in options
            if isinstance(option, dict)
            and str(option.get("option_id", "")).upper() in {"A", "C", "FALLBACK"}
            and isinstance(option.get("asset_id"), str)
            and str(option.get("asset_id")).strip()
        ]
        if not usable:
            return _WaitingForContentDependency(
                "ERR_GC2_MEDIA_SOURCE_PENDING",
                "The assembly job has no durable image asset to prepare.",
            )
        for option in usable:
            asset_id = str(option["asset_id"])
            variant = connection.execute(
                "SELECT id FROM media_variants WHERE asset_id=? AND transform_version=? LIMIT 1",
                (asset_id, version),
            ).fetchone()
            if variant is not None:
                continue
            prepare = connection.execute(
                "SELECT state FROM jobs WHERE kind='prepare_variant' AND business_key=?",
                (f"prepare-variant:{asset_id}:{profile.name}",),
            ).fetchone()
            prepare_state = None if prepare is None else str(prepare["state"])
            if prepare_state in {"FAILED", "DEAD", "UNKNOWN"}:
                return _WaitingForContentDependency(
                    "ERR_GC2_MEDIA_VARIANT_PREPARE_FAILED",
                    f"Media variant preparation is {prepare_state}; requeue the media step before assembly.",
                )
            return _WaitingForContentDependency(
                "ERR_GC2_MEDIA_VARIANT_PENDING",
                "The required media variant is not ready; assembly is waiting for preparation.",
            )
        return None

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
            queued_options = payload.get("asset_options")
            image_options = queued_options if isinstance(queued_options, list) and queued_options else snapshot.get("images", [])
            if not isinstance(image_options, list) or not image_options:
                raise _WaitingForContentDependency(
                    "ERR_GC2_MEDIA_SOURCE_PENDING",
                    "No media source is attached to the existing content package.",
                )
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
            if variant_row is None:
                raise _WaitingForContentDependency(
                    "ERR_GC2_MEDIA_VARIANT_PENDING",
                    "The required media variant is not ready; assembly is deferred.",
                )
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


def _format_error(error: Exception) -> str:
    code = getattr(error, "code", None)
    if isinstance(code, str) and _ERROR_CODE.fullmatch(code) is not None:
        if not code.startswith("ERR_"):
            code = f"ERR_GC2_{code}"
    else:
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", type(error).__name__)
        name = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper() or "UNKNOWN"
        code = f"ERR_GC2_JOB_{name[:64]}"
    message = getattr(error, "public_message", None)
    if not isinstance(message, str):
        message = str(error) or type(error).__name__
    message = _ERROR_SECRET.sub(r"\1\2[REDACTED]", message)
    message = _URL.sub("[URL REDACTED]", message)
    message = _API_KEY.sub("[SECRET REDACTED]", message)
    message = _LONG_SECRET.sub("[SECRET REDACTED]", message)
    message = " ".join(message.split())[:384]
    return f"{code}: {message}"[:512]


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


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
