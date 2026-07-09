"""Pipeline orchestration (§8, §16 Step 9, Step 13):

    Build (deterministic) → Validate #1 (structural) → Optimize [optional, AI]
        → Validate #2 (faithfulness, MAIN GATE) → Manifest-aware Render/Store

The one rule this module must never violate (§0 item 1, fixed from v1.0→v1.1): Optimize
runs BEFORE the final validation gate. If the optimized prompt fails Validate #2, we
reject it and re-validate the deterministic version instead of the AI one (§13 risk 3).
If even the deterministic version fails, we only export a draft when `allow_draft=True`.

`run_prompt_pipeline` is builder-agnostic — it takes an already-Built contract. The four
`run_*_pipeline` wrappers below just call the matching Builder first (§16 Steps 5/10/11/12).
Official (non-draft) saves go through the Manifest + Regeneration Policy (§13); drafts are
never tracked there since they aren't the official version of anything yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from prompt_studio.builders.content_prompt_builder import build_content_prompt
from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.builders.seo_prompt_builder import build_seo_prompt
from prompt_studio.builders.video_prompt_builder import build_video_prompt
from prompt_studio.knowledge_reader import KnowledgeDna
from prompt_studio.optimizer import OptimizerDisabled, optimize
from prompt_studio.prompt_manifest import save_with_manifest
from prompt_studio.prompt_store import DEFAULT_PROMPTS_ROOT, PromptFilePaths, save_prompt
from prompt_studio.schemas.base import TargetLanguage
from prompt_studio.schemas.prompt_contract import PromptContractBase
from prompt_studio.validator import ValidationResult, validate_faithfulness, validate_structural

OptimizeFn = Callable[[PromptContractBase], PromptContractBase]
AdvisoryFn = Callable[[PromptContractBase], Any]


class StructuralValidationFailed(Exception):
    """Validate #1 failed — the deterministic Builder output itself is malformed."""

    def __init__(self, errors: List[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class FaithfulnessValidationFailed(Exception):
    """Validate #2 failed on the deterministic prompt too, and allow_draft is False."""

    def __init__(self, errors: List[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass
class PipelineResult:
    contract: PromptContractBase
    structural: ValidationResult
    faithfulness: ValidationResult
    used_optimizer: bool
    is_draft: bool
    paths: Optional[PromptFilePaths] = None
    notes: List[str] = field(default_factory=list)
    regeneration_decision: Optional[str] = None
    advisory_report: Optional[Any] = None


def run_prompt_pipeline(
    deterministic: PromptContractBase,
    dna_had_forbidden: bool,
    dna_had_allowed_imperfections: bool,
    *,
    optimize_fn: OptimizeFn = optimize,
    allow_draft: bool = False,
    save: bool = True,
    root: Path = DEFAULT_PROMPTS_ROOT,
    advisory_fn: Optional[AdvisoryFn] = None,
) -> PipelineResult:
    # 1. Validate #1 — structural, right after the Builder (§12)
    structural = validate_structural(
        deterministic, dna_had_forbidden=dna_had_forbidden, dna_had_allowed_imperfections=dna_had_allowed_imperfections
    )
    if not structural.passed:
        raise StructuralValidationFailed(structural.errors)

    # 2. Optimize — optional AI wording pass, BEFORE the final gate (§8 fix)
    notes: List[str] = []
    candidate = deterministic
    used_optimizer = False
    try:
        candidate = optimize_fn(deterministic)
        used_optimizer = True
    except OptimizerDisabled:
        candidate = deterministic
    except Exception as exc:  # noqa: BLE001 - any optimizer failure falls back identically
        notes.append(f"optimizer failed ({exc}); using deterministic prompt")
        candidate = deterministic

    # 3. Validate #2 — faithfulness, the MAIN GATE (§12)
    faithfulness = validate_faithfulness(candidate)

    if not faithfulness.passed and used_optimizer:
        notes.append("optimized prompt failed faithfulness validation; reverted to deterministic prompt")
        candidate = deterministic
        used_optimizer = False
        faithfulness = validate_faithfulness(candidate)

    is_draft = False
    if not faithfulness.passed:
        if not allow_draft:
            raise FaithfulnessValidationFailed(faithfulness.errors)
        is_draft = True
        notes.append("faithfulness validation failed even on the deterministic prompt; exported as DRAFT only")

    final_contract = candidate.model_copy(
        update={
            "validation": candidate.validation.model_copy(
                update={
                    "structural": "pass" if structural.passed else "fail",
                    "faithfulness": "pass" if faithfulness.passed else "fail",
                }
            ),
            "notes": [*candidate.notes, *notes],
        }
    )

    advisory_report = None
    if advisory_fn is not None:
        try:
            advisory_report = advisory_fn(final_contract)
        except Exception as exc:  # noqa: BLE001 - advisory scoring must not become a build gate
            notes.append(f"advisory validation failed ({exc}); continuing without advisory report")
            final_contract = final_contract.model_copy(update={"notes": [*final_contract.notes, notes[-1]]})

    # 4. Render/Store — official prompts go through the manifest + regeneration policy (§13);
    #    drafts are saved directly and never tracked there.
    paths = None
    decision = None
    if save and (not is_draft or allow_draft):
        if is_draft:
            paths = save_prompt(final_contract, root=root)
        else:
            final_contract, paths, decision = save_with_manifest(final_contract, root=root)

    return PipelineResult(
        contract=final_contract,
        structural=structural,
        faithfulness=faithfulness,
        used_optimizer=used_optimizer,
        is_draft=is_draft,
        paths=paths,
        notes=notes,
        regeneration_decision=decision,
        advisory_report=advisory_report,
    )


def run_image_pipeline(
    dna: KnowledgeDna,
    task_brief: str,
    brief_slug: str,
    *,
    optimize_fn: OptimizeFn = optimize,
    allow_draft: bool = False,
    save: bool = True,
    root: Path = DEFAULT_PROMPTS_ROOT,
    advisory_fn: Optional[AdvisoryFn] = None,
) -> PipelineResult:
    deterministic = build_image_prompt(dna, task_brief, brief_slug)
    return run_prompt_pipeline(
        deterministic,
        dna_had_forbidden=bool(dna.forbidden),
        dna_had_allowed_imperfections=bool(dna.allowed_imperfections),
        optimize_fn=optimize_fn,
        allow_draft=allow_draft,
        save=save,
        root=root,
        advisory_fn=advisory_fn,
    )


def run_video_pipeline(
    environment_dnas: List[KnowledgeDna],
    task_brief: str,
    brief_slug: str,
    character_dna: Optional[KnowledgeDna] = None,
    *,
    optimize_fn: OptimizeFn = optimize,
    allow_draft: bool = False,
    save: bool = True,
    root: Path = DEFAULT_PROMPTS_ROOT,
    advisory_fn: Optional[AdvisoryFn] = None,
) -> PipelineResult:
    deterministic = build_video_prompt(environment_dnas, task_brief, brief_slug, character_dna=character_dna)
    all_dnas = ([character_dna] if character_dna else []) + list(environment_dnas)
    return run_prompt_pipeline(
        deterministic,
        dna_had_forbidden=any(dna.forbidden for dna in all_dnas),
        dna_had_allowed_imperfections=any(dna.allowed_imperfections for dna in all_dnas),
        optimize_fn=optimize_fn,
        allow_draft=allow_draft,
        save=save,
        root=root,
        advisory_fn=advisory_fn,
    )


def run_content_pipeline(
    dna: KnowledgeDna,
    task_brief: str,
    brief_slug: str,
    target_language: Optional[TargetLanguage] = None,
    prompt_rules: Optional[Dict[str, Any]] = None,
    *,
    optimize_fn: OptimizeFn = optimize,
    allow_draft: bool = False,
    save: bool = True,
    root: Path = DEFAULT_PROMPTS_ROOT,
    advisory_fn: Optional[AdvisoryFn] = None,
) -> PipelineResult:
    deterministic = build_content_prompt(
        dna, task_brief, brief_slug, target_language=target_language, prompt_rules=prompt_rules
    )
    return run_prompt_pipeline(
        deterministic,
        dna_had_forbidden=bool(dna.forbidden),
        dna_had_allowed_imperfections=bool(dna.allowed_imperfections),
        optimize_fn=optimize_fn,
        allow_draft=allow_draft,
        save=save,
        root=root,
        advisory_fn=advisory_fn,
    )


def run_seo_pipeline(
    dna: KnowledgeDna,
    task_brief: str,
    brief_slug: str,
    keyword_intent: str,
    target_language: Optional[TargetLanguage] = None,
    prompt_rules: Optional[Dict[str, Any]] = None,
    *,
    optimize_fn: OptimizeFn = optimize,
    allow_draft: bool = False,
    save: bool = True,
    root: Path = DEFAULT_PROMPTS_ROOT,
    advisory_fn: Optional[AdvisoryFn] = None,
) -> PipelineResult:
    deterministic = build_seo_prompt(
        dna, task_brief, brief_slug, keyword_intent, target_language=target_language, prompt_rules=prompt_rules
    )
    return run_prompt_pipeline(
        deterministic,
        dna_had_forbidden=bool(dna.forbidden),
        dna_had_allowed_imperfections=bool(dna.allowed_imperfections),
        optimize_fn=optimize_fn,
        allow_draft=allow_draft,
        save=save,
        root=root,
        advisory_fn=advisory_fn,
    )
