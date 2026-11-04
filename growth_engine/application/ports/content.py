from __future__ import annotations

from typing import Protocol, runtime_checkable

from growth_engine.application.dto import (
    CandidateInput,
    DraftPackage,
    DraftRequest,
    EffectiveQcPolicy,
    FactSnapshot,
    QcResult,
    VariantView,
)


@runtime_checkable
class ContentGenerator(Protocol):
    def draft(self, request: DraftRequest) -> DraftPackage: ...


@runtime_checkable
class QcEvaluator(Protocol):
    def evaluate(
        self,
        variant: VariantView,
        caption: str,
        facts: FactSnapshot,
        policy: EffectiveQcPolicy,
    ) -> QcResult: ...
    def compile_policy(
        self, project: str, subject: str, scenario: str | None
    ) -> EffectiveQcPolicy: ...


@runtime_checkable
class FactSource(Protocol):
    def approved_facts(self, keys: list[str], at_ms: int) -> FactSnapshot: ...


@runtime_checkable
class CandidateSource(Protocol):
    def scan(self, now_ms: int) -> list[CandidateInput]: ...
