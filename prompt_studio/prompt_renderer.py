"""Renders a Prompt Contract into the fixed Markdown section layout (§7.2). Purely a
presentation of the JSON contract — no new content is invented here."""

from __future__ import annotations

from prompt_studio.schemas.prompt_contract import PromptContractBase


def render_markdown(contract: PromptContractBase) -> str:
    lines = ["# PROMPT FILE", ""]

    lines += ["## META", ""]
    lines += [
        f"- contract_version: {contract.contract_version}",
        f"- module: {contract.module}",
        f"- project: {contract.project}",
        f"- prompt_type: {contract.prompt_type}",
        f"- prompt_id: {contract.prompt_id}",
        f"- prompt_version: {contract.prompt_version}",
        f"- generated_at: {contract.generated_at}",
        f"- target_language: {contract.target_language}",
        f"- template: {contract.template.name} (v{contract.template.template_version})",
        f"- optimizer: used={contract.optimizer.used}"
        + (f", provider={contract.optimizer.provider}, model={contract.optimizer.model}" if contract.optimizer.used else ""),
        "",
    ]

    lines += ["## TASK BRIEF", "", contract.task_brief, ""]

    lines += ["## SOURCE KNOWLEDGE", ""]
    for entry in contract.source_knowledge:
        lines.append(f"- {entry.file} — dna_version={entry.dna_version}, dna_contract_version={entry.dna_contract_version}, hash={entry.hash}")
    lines.append("")

    lines += ["## REQUIRED DNA", ""]
    for item in contract.required_dna:
        lines.append(f"- {item.key}: {item.value}")
    lines.append("")

    lines += ["## ALLOWED VARIATIONS", ""]
    for item in contract.allowed_variations:
        lines.append(f"- {item.key}: {' / '.join(item.value_range)}")
    lines.append("")

    lines += ["## ALLOWED IMPERFECTIONS", ""]
    for item in contract.allowed_imperfections:
        lines.append(f"- {item.value} (source: {item.source})")
    lines.append("")

    lines += ["## FORBIDDEN / RESTRICTIONS", ""]
    for item in contract.forbidden:
        lines.append(f"- {item.rule} (source: {item.source})")
    restrictions = getattr(contract, "restrictions", None)
    if restrictions:
        for text in restrictions:
            lines.append(f"- {text}")
    lines.append("")

    lines += ["## FINAL PROMPT", "", contract.final_prompt, ""]

    negative_prompt = getattr(contract, "negative_prompt", None)
    if negative_prompt is not None:
        lines += ["## NEGATIVE PROMPT", "", negative_prompt, ""]

    lines += ["## VALIDATION", ""]
    lines += [
        f"- structural: {contract.validation.structural}",
        f"- faithfulness: {contract.validation.faithfulness}",
        "",
    ]

    lines += ["## NOTES", ""]
    lines += [f"- {note}" for note in contract.notes] or ["(none)"]
    lines.append("")

    return "\n".join(lines)
