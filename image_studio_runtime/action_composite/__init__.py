"""Action Composite v2: global scene generation with local identity finishing."""

from .analytics import build_analytics
from .audit_store import AuditStore
from .orchestration import AuditTrail, CostLedger, IdempotencyStore, IterationRecord, RetryPolicy, StopCondition
from .pipeline import ActionCompositePipeline
from .masks import HierarchicalFaceMasks, hierarchical_face_masks
from .workflow_v2 import CandidateSelector, RegionalGate, SceneCandidate, WorkflowLedger
from .geometry import (FaceGeometryEvidenceBlocked, InsightFaceGeometryExtractor,
                       YuNetGeometryExtractor, create_geometry_extractor)
from .production import ProductionRunner
from .regression_guard import assert_no_regression, protected_region, unchanged_outside_mask
from .selective_repair import SelectiveRepairController
from .service import ActionCompositeService, JobEnvelope, JobStatus
from .validators import RegionalValidator, RegionValidation, ValidationStatus
from .regional_score_gateway import (REGIONAL_FIELDS, RegionalScoreBlocked,
                                      RegionalScoreEvidence, RegionalScoreGateway,
                                      RegionalScoreResult, ValidatorStudioScoreProducer,
                                      GeometryEvidenceProducer, SceneEvidenceProducer,
                                      StageCorrectGeometryEvidenceAdapter,
                                      StagePreservationEvidenceAdapter, PreservationRegionEvidence,
                                      ValidatorExecutionContext)
from .workflow_registry import WorkflowRegistry

__all__ = [
    "ActionCompositePipeline", "ActionCompositeService", "AuditStore", "AuditTrail", "CostLedger",
    "HierarchicalFaceMasks", "hierarchical_face_masks",
    "CandidateSelector", "RegionalGate", "SceneCandidate", "WorkflowLedger",
    "FaceGeometryEvidenceBlocked", "InsightFaceGeometryExtractor", "YuNetGeometryExtractor",
    "create_geometry_extractor",
    "IdempotencyStore", "IterationRecord", "JobEnvelope", "JobStatus", "ProductionRunner",
    "RegionValidation", "RegionalValidator", "RetryPolicy", "SelectiveRepairController",
    "StopCondition", "ValidationStatus", "WorkflowRegistry", "assert_no_regression",
    "build_analytics", "protected_region", "unchanged_outside_mask",
    "REGIONAL_FIELDS", "RegionalScoreBlocked", "RegionalScoreEvidence",
    "RegionalScoreGateway", "RegionalScoreResult",
    "ValidatorStudioScoreProducer",
    "GeometryEvidenceProducer", "SceneEvidenceProducer",
    "StageCorrectGeometryEvidenceAdapter",
    "StagePreservationEvidenceAdapter", "PreservationRegionEvidence",
    "ValidatorExecutionContext",
]
