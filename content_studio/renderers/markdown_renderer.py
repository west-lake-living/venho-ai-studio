from __future__ import annotations

from content_studio.schemas.content_output import ContentOutput


def _render_payload(payload: dict) -> str:
    if not payload:
        return ""
    lines = ["", "## STRUCTURED PAYLOAD"]
    for key, value in payload.items():
        title = key.replace("_", " ").upper()
        lines.append("")
        lines.append(f"### {title}")
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    compact = "; ".join(f"{k}: {v}" for k, v in item.items())
                    lines.append(f"- {compact}")
                else:
                    lines.append(f"- {item}")
        elif isinstance(value, dict):
            for child_key, child_value in value.items():
                lines.append(f"- {child_key}: {child_value}")
        else:
            lines.append(str(value))
    return "\n".join(lines)


def render_markdown(output: ContentOutput) -> str:
    hashtags = " ".join(output.hashtags)
    source_knowledge = "\n".join(
        f"- {item.file} (version {item.dna_version}, {item.hash})" for item in output.source_knowledge
    )
    validation_notes = "\n".join(f"- {note}" for note in output.validation.notes) or "- None"
    return f"""# {output.content_type.replace("_", " ").upper()} DRAFT

## META
- Project: {output.project}
- Content type: {output.content_type}
- Target language: {output.target_language}
- Generated at: {output.generated_at}
- Status: {output.status}

## SOURCE KNOWLEDGE
{source_knowledge}

## SOURCE PROMPT
- Prompt ID: {output.source_prompt.prompt_id}
- Prompt version: {output.source_prompt.prompt_version}
- File: {output.source_prompt.file or "in-memory"}

## AUDIENCE
Generated from the ContentRequest audience and Module 02 content prompt.

## HOOK
{output.hook}

## BODY
{output.body}

## CTA
{output.cta}

## HASHTAGS
{hashtags}

## VISUAL NOTE
{output.visual_note or "None"}
{_render_payload(output.payload)}

## VALIDATION STATUS
- Required: {output.validation.required}
- Status: {output.validation.status}
- Report: {output.validation.report_file or "None"}

{validation_notes}
""".strip()
