from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.domain.kernel.errors import DomainError, ErrorCode
from growth_engine.application.content.ingest_candidate import CandidateIngestCommand
from growth_engine.application.dto import CandidateInput


router = APIRouter(tags=["internal-research"])
_MAX_REQUEST_BYTES = 64 * 1024


class ResearchIngestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: StrictStr = Field(pattern=r"^growth\.research_ingest\.v2$")
    project_id: StrictStr = Field(min_length=1, max_length=128)
    source: StrictStr = Field(min_length=1, max_length=128)
    external_key: StrictStr = Field(min_length=1, max_length=512)
    source_revision: StrictStr = Field(min_length=1, max_length=256)
    topic_key: StrictStr = Field(min_length=1, max_length=512)
    event_key: StrictStr | None = Field(default=None, max_length=512)
    event_start_at_ms: StrictInt | None = None
    event_end_at_ms: StrictInt | None = None
    expires_at_ms: StrictInt
    payload: dict[str, Any]


class ResearchIngestResponse(BaseModel):
    schema_version: str = "growth.research_ingest.v2"
    candidate_id: str
    created: bool


@router.post(
    "/internal/growth/v2/research/ingest",
    status_code=201,
    response_model=ResearchIngestResponse,
)
async def ingest_candidate(
    body: ResearchIngestBody,
    request: Request,
    response: Response,
    principal: Principal = Depends(require_scopes("ingest")),
) -> ResearchIngestResponse:
    if len(await request.body()) > _MAX_REQUEST_BYTES:
        raise DomainError(ErrorCode.PAYLOAD_TOO_LARGE, "Request vượt quá giới hạn 64 KB.")
    candidate = CandidateInput(
        source=body.source,
        external_key=body.external_key,
        source_revision=body.source_revision,
        topic_key=body.topic_key,
        event_key=body.event_key,
        event_start_at_ms=body.event_start_at_ms,
        event_end_at_ms=body.event_end_at_ms,
        expires_at_ms=body.expires_at_ms,
        payload=body.payload,
        source_hash="",
    )
    result = request.app.state.container.ingest_candidate.execute(
        CandidateIngestCommand(
            project_id=body.project_id,
            candidate=candidate,
            actor=principal.id,
            correlation_id=getattr(request.state, "correlation_id", "research-ingest"),
        )
    )
    if not result.created:
        response.status_code = 200
    response.headers["Cache-Control"] = "no-store"
    return ResearchIngestResponse(candidate_id=result.candidate.id, created=result.created)
