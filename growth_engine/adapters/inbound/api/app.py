from __future__ import annotations

from fastapi import FastAPI

from growth_engine.adapters.inbound.api.errors import (
    application_error_handler,
    domain_error_handler,
)
from growth_engine.adapters.inbound.api.middleware import RequestMiddleware
from growth_engine.adapters.inbound.api.routers.health import router as health_router
from growth_engine.adapters.inbound.api.routers.internal_research import router as internal_research_router
from growth_engine.adapters.inbound.api.routers.internal_executions import router as internal_executions_router
from growth_engine.application.errors import ApplicationError
from growth_engine.domain.kernel.errors import DomainError


def create_app(container) -> FastAPI:
    app = FastAPI(title="Ven Hồ Growth Engine API", version="2")
    app.state.container = container
    app.add_middleware(RequestMiddleware)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.include_router(health_router)
    app.include_router(internal_research_router)
    app.include_router(internal_executions_router)
    return app
