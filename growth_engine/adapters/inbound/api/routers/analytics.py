from __future__ import annotations

import errno

from fastapi import APIRouter, Depends, Query, Request, Response

from growth_engine.adapters.inbound.api.auth import Principal, require_scopes
from growth_engine.domain.kernel.errors import DomainError, ErrorCode


router = APIRouter(prefix="/api/growth/v2", tags=["growth-dashboard"])


@router.get("/analytics/weekly")
def weekly_analytics(
    request: Request,
    response: Response,
    week_start: str = Query(..., description="Monday date in Asia/Ho_Chi_Minh, YYYY-MM-DD"),
    checkpoint: str = Query("7d", description="24h, 72h, or 7d"),
    principal: Principal = Depends(require_scopes("dashboard:read")),
) -> object:
    service = getattr(request.app.state.container, "analytics_views", None)
    if service is None or not callable(getattr(service, "weekly", None)):
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Analytics chưa được cấu hình.")
    try:
        report = service.weekly(week_start=week_start, checkpoint=checkpoint)
    except DomainError:
        raise
    except ValueError as error:
        raise DomainError(ErrorCode.VALIDATION, str(error)) from error
    except Exception as error:
        code = getattr(error, "code", "")
        if code == "ERR_GC2_DB_BUSY" or isinstance(error, (OSError, TimeoutError)) or getattr(error, "errno", None) in {errno.EBUSY, errno.EAGAIN}:
            raise DomainError(ErrorCode.DB_BUSY, "Không đọc được dữ liệu Analytics.") from error
        raise DomainError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Analytics chưa sẵn sàng.") from error
    response.headers["Cache-Control"] = "no-store"
    return report
