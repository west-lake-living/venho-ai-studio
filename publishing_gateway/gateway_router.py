from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from publishing_gateway.adapters import FacebookAdapter, GoogleBusinessAdapter, InstagramAdapter, ThreadsAdapter
from publishing_gateway.adapters.base_adapter import BasePlatformAdapter
from publishing_gateway.approval_verifier import verify_approval
from publishing_gateway.brand_guard import validate_brand_display
from publishing_gateway.circuit_breaker import CircuitBreaker
from publishing_gateway.contract_validator import validate_contract
from publishing_gateway.exceptions import ERR_CIRCUIT_OPEN, ERR_DUPLICATE_PUBLISH, PublishingGatewayError
from publishing_gateway.platform_capabilities import validate_platform_capability
from publishing_gateway.publisher_queue import PublishJob, PublisherQueue
from publishing_gateway.rate_limit_policy import load_rate_limits
from publishing_gateway.receipt_store import ReceiptStore
from publishing_gateway.schemas.delivery_receipt import AnalyticsHandoff, CircuitBreakerInfo, DeliveryReceipt
from publishing_gateway.schemas.platform_result import PlatformResult
from publishing_gateway.schemas.publishing_request import PublishingRequest
from publishing_gateway.utils.idempotency import ensure_idempotency_key
from publishing_gateway.utils.time_utils import utc_now_iso


# Fix #1: module-level singleton so failure history accumulates across calls.
# Tests that need isolation should inject their own CircuitBreaker instance.
_SHARED_CIRCUIT_BREAKER = CircuitBreaker()


def default_adapters() -> Dict[str, BasePlatformAdapter]:
    return {
        "facebook": FacebookAdapter(),
        "instagram": InstagramAdapter(),
        "threads": ThreadsAdapter(),
        "google_business": GoogleBusinessAdapter(),
    }


def publish_request(
    request: PublishingRequest,
    approval_secret: str,
    dry_run: bool = True,
    data_root: Path = Path("data/projects"),
    config_root: Path = Path("config/projects"),
    adapters: Optional[Dict[str, BasePlatformAdapter]] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    queue: Optional[PublisherQueue] = None,
) -> DeliveryReceipt:
    request = ensure_idempotency_key(request)
    validate_contract(request, config_root=config_root)
    verify_approval(request, approval_secret)
    validate_brand_display(request, config_root=config_root)
    validate_platform_capability(request)

    store = ReceiptStore(request.project, data_root=data_root)
    successful = store.successful_platforms(request.idempotency_key or "", request.platforms)
    # Fix #1: use injected breaker or module-level singleton — never create a fresh one per call.
    breaker = circuit_breaker if circuit_breaker is not None else _SHARED_CIRCUIT_BREAKER
    adapter_map = adapters or default_adapters()
    publish_queue = queue or PublisherQueue(rate_limits=load_rate_limits(request.project, config_root=config_root))
    platform_results: Dict[str, PlatformResult] = {}
    # Fix #9: accumulate all circuit-tripped platforms; build CircuitBreakerInfo once after the loop.
    circuit_tripped: list[tuple[str, str]] = []

    for platform in request.platforms:
        if platform in successful:
            platform_results[platform] = PlatformResult(
                platform=platform,
                success=True,
                status="SKIPPED",
                error_code=ERR_DUPLICATE_PUBLISH,
                error_message="platform already published successfully for idempotency key",
            )
            continue
        if not breaker.allow(platform):
            platform_results[platform] = PlatformResult(
                platform=platform,
                success=False,
                status="FAILED",
                error_code=ERR_CIRCUIT_OPEN,
                error_message="circuit breaker is open",
            )
            circuit_tripped.append((platform, breaker.state_for(platform)))
            continue
        publish_queue.enqueue(request, platform)

    # Fix #9: set circuit_info from first tripped platform (not last-wins).
    if circuit_tripped:
        first_platform, first_state = circuit_tripped[0]
        circuit_info = CircuitBreakerInfo(triggered=True, platform=first_platform, state=first_state)
    else:
        circuit_info = CircuitBreakerInfo()

    def _publish(job: PublishJob) -> PlatformResult:
        # Fix #10: guard against missing adapter instead of letting KeyError propagate.
        adapter = adapter_map.get(job.platform)
        if adapter is None:
            return PlatformResult(
                platform=job.platform,
                success=False,
                status="FAILED",
                error_code=ERR_ADAPTER_FAILED,
                error_message=f"no adapter registered for platform '{job.platform}'",
            )
        result = adapter.publish(job.request, dry_run=dry_run)
        if result.success:
            breaker.record_success(job.platform)
        else:
            breaker.record_failure(job.platform)
        return result

    platform_results.update(publish_queue.run(_publish))
    timestamp = utc_now_iso()
    receipt = DeliveryReceipt(
        package_id=request.package_id,
        project=request.project,
        overall_status=_overall_status(platform_results, dry_run=dry_run),
        published_timestamp=timestamp,
        idempotency_key=request.idempotency_key or "",
        platform_results=platform_results,
        circuit_breaker=circuit_info,
        analytics_handoff=AnalyticsHandoff(ready_for_m08=True, tracking_started_at=timestamp),
    )
    store.save_receipt(receipt)
    return receipt


def _overall_status(results: Dict[str, PlatformResult], dry_run: bool) -> str:
    if dry_run and results and all(result.success for result in results.values()):
        return "DRY_RUN"
    successes = [result.success for result in results.values()]
    if successes and all(successes):
        return "SUCCESS"
    if any(successes):
        return "PARTIAL_SUCCESS"
    return "FAILED"
