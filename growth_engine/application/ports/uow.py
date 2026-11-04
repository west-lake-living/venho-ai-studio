from __future__ import annotations

from typing import ContextManager, Protocol

from growth_engine.application.ports.repositories import (
    AuditRepo,
    BudgetRepo,
    CandidateRepo,
    ChannelRepo,
    CommandRepo,
    ControlsRepo,
    DeliveryRepo,
    ExecutionRepo,
    IdempotencyRepo,
    IncidentRepo,
    JobRepo,
    LegacyImportRepo,
    MediaRepo,
    MetricRepo,
    PackageRepo,
    QcRepo,
    ReceiptRepo,
    SlotRepo,
    VerificationRepo,
)


class UnitOfWork(Protocol):
    channels: ChannelRepo
    slots: SlotRepo
    packages: PackageRepo
    media: MediaRepo
    qc: QcRepo
    deliveries: DeliveryRepo
    commands: CommandRepo
    executions: ExecutionRepo
    receipts: ReceiptRepo
    verifications: VerificationRepo
    jobs: JobRepo
    audit: AuditRepo
    incidents: IncidentRepo
    controls: ControlsRepo
    idempotency: IdempotencyRepo
    budget: BudgetRepo
    candidates: CandidateRepo
    metrics: MetricRepo
    legacy: LegacyImportRepo

    def begin_immediate(self) -> ContextManager[UnitOfWork]: ...
    def read_only(self) -> ContextManager[UnitOfWork]: ...
