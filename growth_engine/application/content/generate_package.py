from __future__ import annotations

import json
import re
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from growth_engine.application.dto import DraftPackage, DraftRequest, FactSnapshot
from growth_engine.application.errors import ApplicationError, DraftAfterProviderError, DraftBeforeProviderError
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.media.asset import MediaAsset
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
from growth_engine.domain.kernel.time import BusinessCalendar


class GenerationUnknown(ApplicationError):
    code = "ERR_GC2_GENERATION_UNKNOWN"


class GenerationPostResponseFailed(ApplicationError):
    code = "ERR_GC2_GENERATION_POST_RESPONSE_FAILED"


@dataclass(frozen=True)
class GeneratePackageCommand:
    request: DraftRequest
    package_spec_hash: str
    generator_version: str
    lane: str
    candidate_id: str | None = None


@dataclass(frozen=True)
class GenerationClaim:
    disposition: str
    package: ContentPackage | None = None
    delivery_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PackageFact:
    fact_key: str
    fact_revision: str
    text_hash: str
    valid_until_ms: int | None
    source_ref: str


@dataclass(frozen=True)
class GeneratePackageResult:
    package: ContentPackage
    delivery_ids: tuple[str, ...]
    asset_ids: tuple[str, ...]
    replayed: bool = False


class GeneratePackageStore(Protocol):
    """Transaction seam for budget/job claim and final package/target writes.

    `claim_generation` must atomically check the job key and reserve a paid call under
    BEGIN IMMEDIATE. `settle_response` must record evidence and cost before any
    package writes. `complete_generation` must persist the
    package/facts, reserve one DRAFT delivery per slot target, and enqueue media and
    assemble jobs in one transaction. `mark_generation_unknown` must mark both job and
    paid call UNKNOWN and open the warning incident in one transaction.
    """

    def claim_generation(self, business_key: str, **claims: object) -> GenerationClaim: ...
    def mark_generation_unknown(self, business_key: str, **fields: object) -> None: ...
    def fail_before_provider(self, business_key: str, *, now_ms: int) -> None: ...
    def settle_response(self, business_key: str, evidence: dict, *, cost: int, now_ms: int) -> None: ...
    def retain_evidence(self, business_key: str, evidence: dict) -> None: ...
    def mark_post_response_failed(self, business_key: str, *, reason: str, now_ms: int) -> None: ...
    def complete_generation(
        self,
        business_key: str,
        package: ContentPackage,
        asset_options: tuple[Mapping[str, object], ...],
        package_facts: tuple[PackageFact, ...],
        captions_by_profile: Mapping[str, str],
        **fields: object,
    ) -> tuple[str, ...]: ...


class ContentGenerator(Protocol):
    def draft(self, request: DraftRequest) -> DraftPackage: ...


class FactSource(Protocol):
    def approved_facts(self, keys: list[str], at_ms: int) -> FactSnapshot: ...


class AssetIngestor(Protocol):
    def stage(self, **arguments: object) -> MediaAsset: ...
    def verify_staged(self, asset: MediaAsset) -> bool: ...


class BudgetPolicyView(Protocol):
    monthly_cap_minor: int
    currency: str


class GeneratePackage:
    def __init__(
        self,
        store: GeneratePackageStore,
        generator: ContentGenerator,
        fact_source: FactSource,
        asset_ingestor: AssetIngestor,
        clock: Clock,
        ids: IdGenerator,
        *,
        budget_policy: BudgetPolicyView,
        cost_estimates: Mapping[str, int],
        project: str = "venho_hotel",
    ) -> None:
        self._store = store
        self._generator = generator
        self._fact_source = fact_source
        self._asset_ingestor = asset_ingestor
        self._clock = clock
        self._ids = ids
        self._project = project
        self._budget_policy = budget_policy
        self._cost_estimates = dict(cost_estimates)
        if type(self._budget_policy.monthly_cap_minor) is not int or self._budget_policy.monthly_cap_minor <= 0:
            raise ValueError("monthly budget cap must be a positive integer")
        if not isinstance(self._budget_policy.currency, str) or not self._budget_policy.currency.strip():
            raise ValueError("budget currency is required")
        if type(self._cost_estimates.get("text_generation_minor")) is not int or self._cost_estimates["text_generation_minor"] <= 0:
            raise ValueError("a positive text_generation_minor estimate is required")
        for name, value in self._cost_estimates.items():
            if type(value) is not int or value < 0:
                raise ValueError(f"cost estimate {name!r} must be a non-negative integer")

    def execute(self, command: GeneratePackageCommand) -> GeneratePackageResult:
        request = command.request
        if not command.package_spec_hash.strip() or not command.generator_version.strip() or not command.lane.strip():
            raise ValueError("package_spec_hash, generator_version and lane are required")
        if len(command.package_spec_hash) != 64 or any(
            value not in "0123456789abcdefABCDEF" for value in command.package_spec_hash
        ):
            raise ValueError("package_spec_hash must be a SHA-256 hex digest")
        if request.project_id != self._project:
            raise ValueError("DraftRequest project_id does not match GeneratePackage project")
        if not request.slot_id.strip() or request.lane != command.lane:
            raise ValueError("request slot_id and lane must match the generation command")

        now_ms = self._clock.now_ms()
        business_key = (
            f"generate:{request.slot_id}:{command.package_spec_hash.lower()}:{command.generator_version}"
        )
        estimate = self._estimate_paid_cost()
        calendar = BusinessCalendar("Asia/Ho_Chi_Minh")
        claim = self._store.claim_generation(
            business_key,
            job_id=self._ids.new_id(),
            paid_call_id=self._ids.new_id(),
            slot_id=request.slot_id,
            lane=command.lane,
            package_spec_hash=command.package_spec_hash.lower(),
            generator_version=command.generator_version,
            period_key=calendar.period_key(now_ms),
            currency=self._budget_policy.currency,
            provider="legacy_generation",
            operation="draft_package",
            estimated_cost_minor=estimate,
            monthly_cap_minor=self._budget_policy.monthly_cap_minor,
            now_ms=now_ms,
            correlation_id=business_key,
        )
        if claim.disposition == "SUCCEEDED":
            if claim.package is None:
                raise RuntimeError("succeeded generation claim is missing its package")
            return GeneratePackageResult(claim.package, claim.delivery_ids, (), replayed=True)
        if claim.disposition in {"UNKNOWN", "RESERVED", "RUNNING", "IN_PROGRESS"}:
            raise GenerationUnknown("Generation previously reached a provider and has no safe automatic retry.")
        if claim.disposition == "BEFORE_PROVIDER_FAILED":
            raise DraftBeforeProviderError("stored generation preparation failure")
        if claim.disposition == "POST_RESPONSE_FAILED":
            raise GenerationPostResponseFailed("stored provider response requires operator recovery")
        if claim.disposition == "BUDGET_EXCEEDED":
            raise DomainError(
                ErrorCode.BUDGET_EXCEEDED,
                "Đã vượt ngân sách tháng; lượt tạo nội dung bị chặn.",
                {"estimated_cost_minor": estimate, "currency": self._budget_policy.currency},
            )
        if claim.disposition != "CLAIMED":
            raise RuntimeError(f"invalid generation claim disposition: {claim.disposition!r}")

        try:
            try:
                draft = self._generator.draft(request)
            except DraftBeforeProviderError:
                self._store.fail_before_provider(business_key, now_ms=self._clock.now_ms())
                raise
            except DraftAfterProviderError as error:
                evidence = {"version": 1, "response_received": True, "request_at_ms": request.at_ms}
                try:
                    if isinstance(error.response, Mapping):
                        evidence["partial_response"] = _filter_evidence(_json_safe(error.response))
                    elif isinstance(error.response, str):
                        evidence["unparsed_response_length"] = len(error.response)
                except (TypeError, ValueError):
                    pass
                self._store.settle_response(business_key, evidence, cost=estimate, now_ms=self._clock.now_ms())
                reason = f"{error.message}: provider response could not be assembled"
                self._store.mark_post_response_failed(business_key, reason=reason, now_ms=self._clock.now_ms())
                raise GenerationPostResponseFailed(reason) from None
            except Exception as error:
                self._store.mark_generation_unknown(
                    business_key, error_class=type(error).__name__,
                    now_ms=self._clock.now_ms(), correlation_id=business_key,
                )
                raise GenerationUnknown("Provider outcome is uncertain; automatic retry is disabled.") from None
            step = "draft_evidence"
            try:
                # Record the known outcome even if serialization or staging fails.
                evidence = {"version": 1, "response_received": True, "request_at_ms": request.at_ms}
                try:
                    evidence.update(_draft_evidence(draft))
                finally:
                    self._store.settle_response(business_key, evidence, cost=estimate, now_ms=self._clock.now_ms())
                step = "image_options"
                assets = self._stage_images(business_key, draft.image_options, evidence["images"])
                evidence["assets"] = assets
                self._store.retain_evidence(business_key, evidence)
                return self.complete_from_evidence(business_key, command, evidence)
            except Exception as error:
                reason = diagnostic(error, step)
                self._store.mark_post_response_failed(business_key, reason=reason, now_ms=self._clock.now_ms())
                raise GenerationPostResponseFailed(reason) from None
        finally:
            cleanup = getattr(self._generator, "close", None)
            if callable(cleanup):
                try:
                    cleanup()
                except OSError:
                    pass

    def complete_from_evidence(
        self, business_key: str, command: GeneratePackageCommand, evidence: dict, *, outer_job_id: str | None = None,
    ) -> GeneratePackageResult:
        step = "image_options"
        try:
            assets = evidence["assets"]
            if outer_job_id is not None:
                for option in assets:
                    if not self._asset_ingestor.verify_staged(MediaAsset(**option["candidate"])):
                        raise GenerationPostResponseFailed("image_options: retained original checksum mismatch")
            step = "fact_snapshot"
            request = command.request
            fact_snapshot = self._fact_source.approved_facts(evidence["fact_keys"], request.at_ms)
            safe_facts = _json_safe(fact_snapshot.facts)
            fact_json = canonical_json_bytes(safe_facts)
            package_facts = _package_facts(safe_facts)
            step = "content_package"
            snapshot = {key: evidence[key] for key in ("topic_key", "pillar", "brief", "fact_keys", "images")}
            snapshot.update(package_spec_hash=command.package_spec_hash.lower(), generator_version=command.generator_version)
            now_ms = self._clock.now_ms()
            package = ContentPackage(
                id=self._ids.new_id(), slot_id=request.slot_id, topic_key=evidence["topic_key"],
                pillar=evidence["pillar"], lane=command.lane, source_snapshot_json=canonical_json_bytes(snapshot).decode(),
                fact_snapshot_json=fact_json.decode(), fact_snapshot_hash=sha256_hex(fact_json),
                generation_version=command.generator_version, created_at_ms=now_ms, candidate_id=command.candidate_id,
            )
            step = "complete_generation"
            delivery_ids = self._store.complete_generation(
                business_key, package, tuple(assets), package_facts, evidence["captions_by_profile"],
                settled_at_ms=now_ms, correlation_id=business_key, outer_job_id=outer_job_id,
            )
            return GeneratePackageResult(package, tuple(delivery_ids), tuple(str(item["asset_id"]) for item in assets))
        except Exception as error:
            raise GenerationPostResponseFailed(diagnostic(error, step)) from None

    def _estimate_paid_cost(self) -> int:
        text_cost = self._cost_estimates.get("text_generation_minor", 0)
        provider = getattr(self._generator, "image_provider", None)
        image_calls = 1 if not hasattr(self._generator, "image_provider") else 0
        if provider is not None and getattr(provider, "enabled", True):
            image_calls = 1 + int(bool(getattr(self._generator, "image_alternatives_enabled", False)))
        if image_calls and self._cost_estimates.get("image_generation_minor", 0) <= 0:
            raise ValueError("a positive image_generation_minor estimate is required when image generation is enabled")
        return text_cost + image_calls * self._cost_estimates.get("image_generation_minor", 0)

    def _stage_images(self, business_key: str, images: Sequence[Mapping[str, object]], safe_images: list) -> list[dict]:
        assets = []
        for index, (image, safe) in enumerate(zip(images, safe_images, strict=True)):
            option_id = safe["option_id"]
            source_type = {"A": "ai_generated", "B": "ai_generated", "C": "library", "FALLBACK": "fallback"}[option_id]
            provenance = safe["provenance"]
            source_ref = str(provenance.get("source_ref") or f"{business_key}:{option_id}")
            try:
                with Path(image["path"]).open("rb") as stream:
                    asset = self._asset_ingestor.stage(
                        source_type=source_type, source_ref=source_ref, source_revision=None,
                        stream=stream, metadata={"option_id": option_id, "provenance": provenance},
                    )
            except Exception as error:
                raise GenerationPostResponseFailed(diagnostic(error, f"image_options[{index}].path")) from None
            assets.append({
                "option_id": option_id, "asset_id": asset.id, "candidate": asdict(asset),
                "sha256": asset.source_sha256, "source_type": source_type, "source_ref": source_ref,
                "provenance": provenance, "label": "Ảnh dự phòng" if option_id == "FALLBACK" else None,
            })
        return assets


def diagnostic(error: Exception, field: str) -> str:
    if isinstance(error, GenerationPostResponseFailed):
        return str(error)
    # SQLite's UNIQUE message contains column identifiers only. Other messages
    # (including trigger errors) may contain data, so keep the safe error name.
    match = re.fullmatch(r"UNIQUE constraint failed: ([a-z_0-9., ]+)", str(error))
    if match:
        return f"{field}: UNIQUE({match[1]})"
    constraint = getattr(error, "sqlite_errorname", "")
    return f"{field}: {constraint or type(error).__name__}"


_SENSITIVE = re.compile(r"(?i)https?://[^\s<>]+[?][^\s<>]+|(?:sk-|AIza|EAA)[A-Za-z0-9_\-]{12,}|Bearer\s+[A-Za-z0-9._\-]+")
_SECRET_FIELD = re.compile(r"(?i)token|secret|password|api[_-]?key|authorization|^path$")


def _filter_evidence(value):
    if isinstance(value, str):
        return _SENSITIVE.sub("[REDACTED]", value)
    if isinstance(value, dict):
        return {key: _filter_evidence(item) for key, item in value.items() if not _SECRET_FIELD.search(key)}
    if isinstance(value, list):
        return [_filter_evidence(item) for item in value]
    return value


def _draft_evidence(draft: DraftPackage) -> dict:
    if not isinstance(draft, DraftPackage):
        raise TypeError("invalid draft")
    images = [
        {"option_id": str(item.get("option_id", "")).upper(), "provenance": item.get("provenance", {})}
        for item in draft.image_options
    ]
    return _filter_evidence(_json_safe({
        "topic_key": draft.topic_key, "pillar": draft.pillar, "brief": draft.brief,
        "fact_keys": list(draft.fact_keys), "captions_by_profile": dict(draft.captions_by_profile), "images": images,
    }))


def choose_default_image(
    image_options: Sequence[Mapping[str, object]],
    qc_decisions: Mapping[str, str],
) -> dict[str, object] | None:
    """Choose A, then C; use a labelled fallback only when both fail QC."""
    by_id = {str(option.get("option_id")): option for option in image_options}
    for option_id in ("A", "C"):
        if qc_decisions.get(option_id) == "PASS" and option_id in by_id:
            return dict(by_id[option_id])
    fallback_allowed = qc_decisions.get("A") == "FAIL" and qc_decisions.get("C") == "FAIL"
    fallback = by_id.get("FALLBACK")
    if fallback_allowed and fallback is not None:
        return {**fallback, "label": "Ảnh dự phòng"}
    return None


def _json_safe(value: object, path: str = "$") -> object:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"field {path}: snapshot cannot contain a non-finite number")
        return format(value, ".15g")
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError(f"field {path}: snapshot object keys must be strings")
        return {key: _json_safe(nested, f"{path}.{key}") for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(nested, f"{path}[{index}]") for index, nested in enumerate(value)]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError(f"field {path}: snapshot value is not JSON-compatible ({type(value).__name__})")


def _package_facts(facts: Mapping[str, object]) -> tuple[PackageFact, ...]:
    result: list[PackageFact] = []
    for fact_key, raw in sorted(facts.items()):
        if not isinstance(raw, Mapping):
            raw = {"value": raw}
        value = raw.get("text", raw.get("value", ""))
        text = str(value)
        valid_to = raw.get("valid_to")
        valid_until_ms = _epoch_ms(valid_to) if isinstance(valid_to, str) and valid_to else None
        revision = str(raw.get("revision") or raw.get("version") or "1")
        source_ref = str(raw.get("source_ref") or raw.get("source") or f"legacy_facts:{fact_key}")
        result.append(
            PackageFact(
                fact_key=fact_key,
                fact_revision=revision,
                text_hash=sha256_hex(canonical_json_bytes(text)),
                valid_until_ms=valid_until_ms,
                source_ref=source_ref,
            )
        )
    return tuple(result)


def _epoch_ms(value: str) -> int | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)
