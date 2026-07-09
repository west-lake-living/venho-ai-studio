"""Two-tier validator (§12).

Validate #1 (structural) runs right after the Builder — checks shape, not content.
Validate #2 (faithfulness) runs after the Optimizer and is the main gate before a prompt
is official (§8): every required_dna invariant must still appear in final_prompt, and
every forbidden rule must still be intact in negative_prompt (image/video) or restrictions
(content/seo). A failed Validate #2 does not raise here — pipeline.py (§16 Step 9) decides
whether to fall back to the deterministic draft or reject per --allow-draft.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from prompt_studio.schemas.prompt_contract import PromptContractBase
from prompt_studio.settings import max_length_for

_VIETNAMESE_DIACRITICS = re.compile(
    "[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    "ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]"
)
_ALPHA = re.compile(r"[^\W\d_]", re.UNICODE)

# A proper noun with diacritics (e.g. a Vietnamese place name) embedded in otherwise-English
# instructions must not fail this check — only prose actually WRITTEN in Vietnamese should
# (§10 guards the instruction frame's language, not the odd Vietnamese proper noun in it).
# Note: the brand name itself is spelled "Ven Ho Hotel" (no diacritics) by convention in all
# AI prompt/instructions, so it never exercises this tolerance in practice.
_MAX_VIETNAMESE_DIACRITIC_DENSITY = 0.03


def _vietnamese_diacritic_density(text: str) -> float:
    alpha_chars = _ALPHA.findall(text)
    if not alpha_chars:
        return 0.0
    diacritic_chars = _VIETNAMESE_DIACRITICS.findall(text)
    return len(diacritic_chars) / len(alpha_chars)


@dataclass
class ValidationResult:
    passed: bool
    errors: List[str] = field(default_factory=list)


def validate_structural(
    contract: PromptContractBase,
    dna_had_forbidden: bool,
    dna_had_allowed_imperfections: bool,
    allow_empty_required_dna: bool = False,
) -> ValidationResult:
    """§12 Validate #1 — structural, right after the Builder."""
    errors: List[str] = []

    if not contract.source_knowledge:
        errors.append("source_knowledge is empty")
    if not contract.template.template_version:
        errors.append("template.template_version is empty")
    if not contract.contract_version:
        errors.append("contract_version is empty")
    if contract.prompt_type not in ("image", "video", "content", "seo"):
        errors.append(f"invalid prompt_type: {contract.prompt_type}")
    if not contract.required_dna and not allow_empty_required_dna:
        errors.append("required_dna is empty")
    if dna_had_forbidden and not contract.forbidden:
        errors.append("DNA has forbidden rules but prompt.forbidden is empty")
    if dna_had_allowed_imperfections and not contract.allowed_imperfections:
        errors.append("DNA has allowed_imperfections but prompt.allowed_imperfections is empty")

    return ValidationResult(passed=not errors, errors=errors)


def validate_faithfulness(contract: PromptContractBase) -> ValidationResult:
    """§12 Validate #2 — faithfulness, the main gate after the Optimizer."""
    errors: List[str] = []

    for item in contract.required_dna:
        if item.value not in contract.final_prompt:
            errors.append(f"required_dna '{item.key}' value not found in final_prompt: {item.value!r}")

    negative_prompt = getattr(contract, "negative_prompt", None)
    restrictions = getattr(contract, "restrictions", None)
    for item in contract.forbidden:
        if negative_prompt is not None:
            if item.rule not in negative_prompt:
                errors.append(f"forbidden rule missing from negative_prompt: {item.rule!r}")
        elif restrictions is not None:
            if not any(item.rule in text for text in restrictions):
                errors.append(f"forbidden rule missing from restrictions: {item.rule!r}")

    max_length = max_length_for(contract.prompt_type)
    if len(contract.final_prompt) > max_length:
        errors.append(f"final_prompt length {len(contract.final_prompt)} exceeds max_length {max_length}")

    density = _vietnamese_diacritic_density(contract.final_prompt)
    if density > _MAX_VIETNAMESE_DIACRITIC_DENSITY:
        errors.append(
            f"final_prompt looks written in Vietnamese (diacritic density {density:.1%}) — "
            f"instructions must be English (§10)"
        )

    return ValidationResult(passed=not errors, errors=errors)
