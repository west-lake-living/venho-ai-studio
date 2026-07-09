from __future__ import annotations

from typing import Any, Union

from prompt_studio.schemas.prompt_contract import PromptContractBase

from validator_studio.prompt_validator import validate_prompt_contract
from validator_studio.schemas.validation_base import ValidationReport


def _contract_to_dict(contract: Union[PromptContractBase, dict[str, Any]]) -> dict[str, Any]:
    if isinstance(contract, dict):
        return contract
    return contract.model_dump(mode="json")


def _subject_from_prompt_id(prompt_id: str) -> str:
    subject, sep, _rest = prompt_id.partition("__")
    if not sep:
        raise ValueError(f"Invalid prompt_id: {prompt_id}")
    if "+" in subject:
        raise ValueError("Module 03 prompt advisory scorer currently expects one subject, not multi-DNA video prompts")
    return subject


def score_module02_prompt_contract(contract: Union[PromptContractBase, dict[str, Any]]) -> ValidationReport:
    """Advisory bridge for Module 02.

    Module 02 remains the structural/faithfulness gate. This function lets it attach
    Module 03 quality scoring without duplicating prompt scoring logic.
    """
    payload = _contract_to_dict(contract)
    project = str(payload.get("project", ""))
    prompt_id = str(payload.get("prompt_id", ""))
    subject = _subject_from_prompt_id(prompt_id)
    return validate_prompt_contract(project, subject, payload)
