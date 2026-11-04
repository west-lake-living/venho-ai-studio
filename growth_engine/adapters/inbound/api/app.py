from __future__ import annotations

from fastapi import FastAPI

from growth_engine.adapters.inbound.api.errors import (
    application_error_handler,
    domain_error_handler,
)
from growth_engine.adapters.inbound.api.middleware import RequestMiddleware
from growth_engine.adapters.inbound.api.routers.health import router as health_router
from growth_engine.adapters.inbound.api.routers.channels import router as channels_router
from growth_engine.adapters.inbound.api.routers.slots import router as slots_router
from growth_engine.adapters.inbound.api.routers.deliveries import router as deliveries_router
from growth_engine.adapters.inbound.api.routers.approvals import router as approvals_router
from growth_engine.adapters.inbound.api.routers.assets import router as assets_router
from growth_engine.adapters.inbound.api.routers.jobs import router as jobs_router
from growth_engine.adapters.inbound.api.routers.candidates import router as candidates_router
from growth_engine.adapters.inbound.api.routers.incidents import router as incidents_router
from growth_engine.adapters.inbound.api.routers.controls import router as controls_router
from growth_engine.adapters.inbound.api.routers.internal_research import router as internal_research_router
from growth_engine.adapters.inbound.api.routers.internal_executions import router as internal_executions_router
from growth_engine.adapters.inbound.api.routers.internal_receipts import router as internal_receipts_router
from growth_engine.application.errors import ApplicationError
from growth_engine.domain.kernel.errors import DomainError


def create_app(container) -> FastAPI:
    app = FastAPI(title="Ven Hồ Growth Engine API", version="2")
    app.state.container = container
    app.add_middleware(RequestMiddleware)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.include_router(health_router)
    for router in (
        channels_router,
        slots_router,
        deliveries_router,
        approvals_router,
        assets_router,
        jobs_router,
        candidates_router,
        incidents_router,
        controls_router,
    ):
        app.include_router(router)
    app.include_router(internal_research_router)
    app.include_router(internal_executions_router)
    app.include_router(internal_receipts_router)
    return app
