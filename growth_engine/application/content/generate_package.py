from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from growth_engine.application.dto import DraftPackage, DraftRequest, FactSnapshot
from growth_engine.application.errors import ApplicationError
from growth_engine.application.media.ingest_asset import MAX_ORIGINAL_BYTES
from growth_engine.application.ports.clock import Clock, IdGenerator
from growth_engine.domain.content.package import ContentPackage
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
from growth_engine.domain.kernel.time import BusinessCalendar


class GenerationUnknown(ApplicationError):
    code = "ERR_GC2_GENERATION_UNKNOWN"


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
    BEGIN IMMEDIATE. `complete_generation` must settle the reservation, persist the
    package/facts, reserve one DRAFT delivery per slot target, and enqueue media and
    assemble jobs in one transaction. `mark_generation_unknown` must mark both job and
    paid call UNKNOWN and open the warning incident in one transaction.
    """

    def claim_generation(self, business_key: str, **claims: object) -> GenerationClaim: ...
    def mark_generation_unknown(self, business_key: str, **fields: object) -> None: ...
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
    def execute(self, **arguments: object) -> object: ...


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
        if claim.disposition == "BUDGET_EXCEEDED":
            raise DomainError(
                ErrorCode.BUDGET_EXCEEDED,
                "Đã vượt ngân sách tháng; lượt tạo nội dung bị chặn.",
                {"estimated_cost_minor": estimate, "currency": self._budget_policy.currency},
            )
        if claim.disposition != "CLAIMED":
            raise RuntimeError(f"invalid generation claim disposition: {claim.disposition!r}")

        try:
            draft = self._generator.draft(request)
            if not isinstance(draft, DraftPackage):
                raise TypeError("ContentGenerator returned a non-DraftPackage value")
            fact_snapshot = self._fact_source.approved_facts(list(draft.fact_keys), request.at_ms)
            safe_facts = _json_safe(fact_snapshot.facts)
            fact_snapshot_json = canonical_json_bytes(safe_facts).decode("utf-8")
            fact_snapshot_hash = sha256_hex(fact_snapshot_json.encode("utf-8"))
            package_id = self._ids.new_id()
            source_snapshot = {
                "package_spec_hash": command.package_spec_hash.lower(),
                "generator_version": command.generator_version,
                "topic_key": draft.topic_key,
                "pillar": draft.pillar,
                "brief": draft.brief,
                "fact_keys": list(draft.fact_keys),
                "images": [
                    {
                        "option_id": item.get("option_id"),
                        "provenance": _json_safe(item.get("provenance", {})),
                    }
                    for item in draft.image_options
                ],
            }
            package = ContentPackage(
                id=package_id,
                slot_id=request.slot_id,
                topic_key=draft.topic_key,
                pillar=draft.pillar,
                lane=command.lane,
                source_snapshot_json=canonical_json_bytes(source_snapshot).decode("utf-8"),
                fact_snapshot_json=fact_snapshot_json,
                fact_snapshot_hash=fact_snapshot_hash,
                generation_version=command.generator_version,
                created_at_ms=now_ms,
                candidate_id=command.candidate_id,
            )
            package_facts = _package_facts(safe_facts)
            assets = self._ingest_images(business_key, draft.image_options)
            delivery_ids = self._store.complete_generation(
                business_key,
                package,
                tuple(assets),
                package_facts,
                draft.captions_by_profile,
                settled_at_ms=self._clock.now_ms(),
                estimated_cost_minor=estimate,
                correlation_id=business_key,
            )
            return GeneratePackageResult(
                package=package,
                delivery_ids=tuple(delivery_ids),
                asset_ids=tuple(str(item["asset_id"]) for item in assets),
            )
        except Exception as exc:
            self._store.mark_generation_unknown(
                business_key,
                error_class=type(exc).__name__,
                now_ms=self._clock.now_ms(),
                correlation_id=business_key,
            )
            raise GenerationUnknown(
                "Generation result is uncertain; the paid provider call will not be repeated automatically."
            ) from exc
        finally:
            cleanup = getattr(self._generator, "close", None)
            if callable(cleanup):
                try:
                    cleanup()
                except OSError:
                    pass

    def _estimate_paid_cost(self) -> int:
        text_cost = self._cost_estimates.get("text_generation_minor", 0)
        provider = getattr(self._generator, "image_provider", None)
        image_calls = 1 if not hasattr(self._generator, "image_provider") else 0
        if provider is not None and getattr(provider, "enabled", True):
            image_calls = 1 + int(bool(getattr(self._generator, "image_alternatives_enabled", False)))
        if image_calls and self._cost_estimates.get("image_generation_minor", 0) <= 0:
            raise ValueError("a positive image_generation_minor estimate is required when image generation is enabled")
        return text_cost + image_calls * self._cost_estimates.get("image_generation_minor", 0)

    def _ingest_images(
        self,
        business_key: str,
        image_options: Sequence[Mapping[str, object]],
    ) -> list[dict[str, object]]:
        assets: list[dict[str, object]] = []
        for option in image_options:
            option_id = str(option.get("option_id") or "").upper()
            path_text = option.get("path")
            provenance = option.get("provenance") or {}
            if not option_id or not isinstance(path_text, str) or not isinstance(provenance, Mapping):
                raise ValueError("image option must include option_id, path and provenance")
            if option_id not in {"A", "B", "C", "FALLBACK"}:
                raise ValueError(f"unsupported image option_id: {option_id!r}")
            path = Path(path_text)
            if not path.is_file():
                raise FileNotFoundError(f"generated image path is unavailable for option {option_id}")
            digest_builder = hashlib.sha256()
            byte_count = 0
            with path.open("rb") as source_stream:
                while True:
                    chunk = source_stream.read(64 * 1024)
                    if not chunk:
                        break
                    byte_count += len(chunk)
                    if byte_count > MAX_ORIGINAL_BYTES:
                        raise ValueError(f"image option {option_id} exceeds 25 MiB")
                    digest_builder.update(chunk)
            digest = digest_builder.hexdigest()
            source_type = "ai_generated" if option_id in {"A", "B"} else "fallback" if option_id == "FALLBACK" else "library"
            source_ref = str(provenance.get("source_ref") or f"{business_key}:{option_id}")
            with path.open("rb") as stream:
                asset = self._asset_ingestor.execute(
                    source_type=source_type,
                    source_ref=source_ref,
                    source_revision=digest,
                    stream=stream,
                    metadata={
                        "option_id": option_id,
                        "provenance": dict(provenance),
                        **({"label": "Ảnh dự phòng"} if option_id == "FALLBACK" else {}),
                    },
                )
            asset_id = getattr(asset, "id", None)
            if not isinstance(asset_id, str) or not asset_id:
                raise ValueError("AssetIngestor returned an invalid asset id")
            assets.append(
                {
                    "option_id": option_id,
                    "asset_id": asset_id,
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "sha256": digest,
                    "provenance": _json_safe(dict(provenance)),
                    "label": "Ảnh dự phòng" if option_id == "FALLBACK" else None,
                }
            )
        return assets


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


def _json_safe(value: object) -> object:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("fact snapshot cannot contain a non-finite number")
        return format(value, ".15g")
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("snapshot object keys must be strings")
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(nested) for nested in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ValueError(f"snapshot value is not JSON-compatible: {type(value).__name__}")


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
