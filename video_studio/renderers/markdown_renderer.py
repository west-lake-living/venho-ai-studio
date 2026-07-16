from __future__ import annotations

from video_studio.schemas.video_package import VideoPackage


def _source_knowledge(package: VideoPackage) -> str:
    return "\n".join(f"- {item.file} (version {item.dna_version}, {item.hash})" for item in package.source_knowledge)


def _contract_refs(package: VideoPackage) -> str:
    if not package.contract_refs:
        return "None"
    lines = []
    if package.contract_refs.character_id:
        lines.append(f"- character_id: {package.contract_refs.character_id}")
    if package.contract_refs.outfit:
        lines.extend([
            f"- outfit_id: {package.contract_refs.outfit.outfit_id}",
            f"- outfit_label: {package.contract_refs.outfit.display_label}",
            f"- outfit_status: {package.contract_refs.outfit.status}",
            f"- outfit_source: {package.contract_refs.outfit.source_kind}",
        ])
    return "\n".join(lines) or "None"


def _storyboard(package: VideoPackage) -> str:
    lines = []
    for scene in package.storyboard:
        lines.append(f"### Scene {scene.scene_number} — {scene.duration_seconds}s")
        lines.append(scene.description)
        lines.append(f"- Camera: {scene.camera_movement}")
        lines.append(f"- Prompt source: {scene.scene_prompt_ref.file if scene.scene_prompt_ref else 'pending'}")
        lines.append("")
    return "\n".join(lines).strip()


def _shot_list(package: VideoPackage) -> str:
    return "\n".join(
        f"- Scene {shot.scene_number}: {shot.angle}; {shot.camera_movement}; {shot.motion_note}; {shot.lighting_note}"
        for shot in package.shot_list
    )


def render_markdown(package: VideoPackage) -> str:
    validation_notes = "\n".join(f"- {note}" for note in package.validation.notes) or "- None"
    return f"""# VIDEO PRODUCTION PACKAGE

## META
- Project: {package.project}
- Video type: {package.video_type}
- Duration: {package.duration_seconds}s
- Aspect ratio: {package.aspect_ratio}
- Platform: {package.platform}
- Target engine: {package.target_engine}
- Generated at: {package.generated_at}
- Status: {package.status}

## SOURCE KNOWLEDGE
{_source_knowledge(package)}

## CONTRACT REFS
{_contract_refs(package)}

## CONTINUITY KEYS
{chr(10).join(f"- {key}" for key in package.continuity_keys)}

## VIDEO OBJECTIVE
{package.concept.objective}

## TARGET PLATFORM / ENGINE
- Platform: {package.platform}
- Target engine: {package.target_engine}
- Alternate engines: {", ".join(package.alt_engines) or "None"}

## CONCEPT
- Title: {package.concept.title}
- Tone: {package.concept.tone}

## STORYBOARD
{_storyboard(package)}

## SHOT LIST
{_shot_list(package)}

## ENGINE PROMPT (English)
{package.engine_prompt_full}

## MOTION NEGATIVE
{package.motion_negative_prompt}

## CONTINUITY RULES
- Every scene prompt must contain every continuity key exactly.
- Continuity is validated pre-render only.

## CHARACTER RULES
{package.character_rules or "None"}

## CAMERA / MOTION RULES
{package.camera_motion_rules}

## CAPTION / VOICEOVER
- Hook: {package.text_from_content.hook or "None"}
- Caption: {package.text_from_content.caption or "None"}
- Voiceover: {package.text_from_content.voiceover or "None"}
- CTA: {package.text_from_content.cta or "None"}
- Language: {package.text_from_content.caption_language}
- Source: {package.text_from_content.source_file or "None"}

## DURATION CHECK
- Sum scenes: {package.duration_check.sum_scenes}
- Target: {package.duration_check.target}
- OK: {package.duration_check.ok}

## VALIDATION
- Scope: {package.validation.scope}
- Required: {package.validation.required}
- Status: {package.validation.status}
- Reports: {", ".join(package.validation.reports) or "None"}

{validation_notes}
""".strip()
