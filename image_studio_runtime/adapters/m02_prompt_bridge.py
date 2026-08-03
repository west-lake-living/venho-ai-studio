from __future__ import annotations


def build_final_prompt(prompt_contract: dict) -> str:
    base = prompt_contract.get("base_prompt", "").strip()
    if not base:
        raise ValueError("base_prompt is required")
    scenario = prompt_contract.get("scenario_key", "")
    return f"{base}\nScenario: {scenario}".strip()
