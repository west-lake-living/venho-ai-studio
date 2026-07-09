"""Real Prompt Optimizer (§9, §16 Step 9).

The AI's only job is to smooth final_prompt wording — it must never add, remove, or
alter a fact, value, or rule (§9.2). It is NOT trusted to enforce that on its own: the
Validate #2 gate that runs right after this step (§8) is what actually catches a drift,
and the pipeline (pipeline.py) is what reverts to the deterministic prompt if it does.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import anthropic
from dotenv import load_dotenv

from prompt_studio.optimizer_mock import assert_schema_valid
from prompt_studio.schemas.prompt_contract import PromptContractBase
from prompt_studio.settings import load_settings
from shared.vision.errors import ProviderError, RetryExhausted

load_dotenv()

SYSTEM_PROMPT = (
    "You polish the wording of an AI production prompt (image/video/content/SEO). "
    "You may ONLY rephrase for clarity and concision. "
    "Do NOT add, remove, or change any factual detail, value, number, key, or rule. "
    "Do NOT introduce anything not already present in the text. "
    "Reply with ONLY the rewritten prompt text — no preamble, no markdown, no explanation."
)


class OptimizerDisabled(Exception):
    """optimizer.enabled is false in settings_prompt.yaml — pipeline should skip this step."""


def optimize(contract: PromptContractBase, settings: Optional[dict] = None) -> PromptContractBase:
    """Return a copy of `contract` with only final_prompt reworded by the AI (temperature 0)."""
    settings = settings or load_settings()
    opt_cfg = settings["optimizer"]

    if not opt_cfg.get("enabled", False):
        raise OptimizerDisabled("optimizer.enabled is false in settings_prompt.yaml")

    provider = opt_cfg.get("provider", "claude")
    model = opt_cfg["model"]
    temperature = opt_cfg.get("temperature", 0)
    max_attempts = opt_cfg.get("max_attempts", 2)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ProviderError("ANTHROPIC_API_KEY not configured", provider=provider)

    client = anthropic.Anthropic(api_key=api_key)

    last_error: Exception = RuntimeError("no attempts made")
    for attempt in range(1, max_attempts + 1):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=2048,
                temperature=temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": contract.final_prompt}],
            )
            polished = message.content[0].text.strip()
            break
        except Exception as exc:  # noqa: BLE001 - any provider failure is retried identically
            last_error = exc
            if attempt < max_attempts:
                time.sleep(2)
    else:
        raise RetryExhausted("prompt_optimizer", max_attempts, last_error)

    optimized = contract.model_copy(
        deep=True,
        update={
            "final_prompt": polished,
            "optimizer": contract.optimizer.model_copy(
                update={"used": True, "provider": provider, "model": model, "temperature": temperature}
            ),
        },
    )
    assert_schema_valid(optimized)
    return optimized
