from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from publishing_gateway.schemas.platform_result import PlatformResult
from publishing_gateway.schemas.publishing_request import PublishingRequest
from publishing_gateway.exceptions import ERR_RATE_LIMITED
from publishing_gateway.rate_limit_policy import platform_within_limit


@dataclass
class PublishJob:
    request: PublishingRequest
    platform: str
    attempts: int = 0
    status: str = "queued"


@dataclass
class PublisherQueue:
    max_attempts: int = 2
    rate_limits: Dict[str, int] = field(default_factory=dict)
    jobs: List[PublishJob] = field(default_factory=list)

    def enqueue(self, request: PublishingRequest, platform: str) -> PublishJob:
        job = PublishJob(request=request, platform=platform)
        self.jobs.append(job)
        return job

    def status(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for job in self.jobs:
            counts[job.status] = counts.get(job.status, 0) + 1
        return counts

    def run(self, publish_fn: Callable[[PublishJob], PlatformResult], sent_counts: Optional[Dict[str, int]] = None) -> Dict[str, PlatformResult]:
        results: Dict[str, PlatformResult] = {}
        counts = sent_counts or {}
        for job in self.jobs:
            if job.status == "done":
                continue
            if not platform_within_limit(job.platform, counts, self.rate_limits):
                job.status = "failed"
                results[job.platform] = PlatformResult(
                    platform=job.platform,
                    success=False,
                    status="FAILED",
                    error_code=ERR_RATE_LIMITED,
                    error_message="rate limit policy blocked publish",
                )
                continue
            while job.attempts < self.max_attempts:
                job.attempts += 1
                result = publish_fn(job)
                results[job.platform] = result
                if result.success:
                    job.status = "done"
                    counts[job.platform] = counts.get(job.platform, 0) + 1
                    break
                job.status = "failed"
        return results
