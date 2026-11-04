from __future__ import annotations

import hashlib
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml
from PIL import Image

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver
from agent_studio.growth.scenario_registry import ScenarioRegistry
from content_studio.builders.social_builder import build_social_draft
from content_studio.content_context import load_content_config
from content_studio.generators.claude_social_generator import claude_social_generator
from content_studio.schemas.content_request import ContentRequest
from growth_engine.application.dto import DraftPackage, DraftRequest
from growth_orchestrator.application.image_options import (
    alternate_scenario,
    library_photo_path,
    topic_scenario,
)
from image_studio_runtime.adapters.gpt_image_provider import gpt_image_provider_from_env
from image_studio_runtime.adapters.m02_prompt_bridge import build_final_prompt
from prompt_studio.builders.content_prompt_builder import build_content_prompt
from prompt_studio.builders.image_prompt_builder import build_image_prompt
from prompt_studio.knowledge_reader import KnowledgeDna, read_dna
from prompt_studio.prompt_rules import load_prompt_rules
from shared.security import ensure_safe_slug


TextGenerator = Callable[[ContentRequest, Any, dict[str, Any]], dict[str, Any]]

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[4]
_LANE_ALIASES = {"saturday_trend": "saturday", "trend": "saturday"}


class LegacyGeneratorAdapter:
    """Build a Growth draft with legacy prompt/provider components, without legacy stores."""

    def __init__(
        self,
        *,
        repo_root: Path = _DEFAULT_REPO_ROOT,
        data_root: Path | None = None,
        config_root: Path | None = None,
        scenario_registry: ScenarioRegistry | None = None,
        reference_resolver: ReferenceAssetResolver | None = None,
        generator_fn: TextGenerator | None = None,
        image_provider: Any | None = None,
        temp_root: Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.data_root = Path(data_root) if data_root is not None else self.repo_root / "data" / "projects"
        self.config_root = Path(config_root) if config_root is not None else self.repo_root / "config" / "projects"
        self.scenario_registry = scenario_registry
        self.reference_resolver = reference_resolver
        self.generator_fn = generator_fn or claude_social_generator
        self.image_provider = image_provider or gpt_image_provider_from_env(os.environ)
        self.temp_root = Path(temp_root) if temp_root is not None else None
        self._temporary_directories: list[tempfile.TemporaryDirectory[str]] = []

    def draft(self, request: DraftRequest) -> DraftPackage:
        project = ensure_safe_slug(request.project_id, field="project_id")
        content_config = load_content_config(project, config_root=self.config_root)
        lanes = content_config.get("content_pillars", {}).get("lanes", {})
        lane_key = self._lane_key(request.lane, lanes, request.slot_id)
        lane = lanes[lane_key]
        topic = self._topic(request, lane)
        candidates = list(lane.get("scenario_pool") or [])
        registry = self._scenario_registry(project)
        scenario_key = self._scenario_key(request, topic, candidates)
        scenario = registry.resolve(scenario_key)
        rotation_key = datetime.fromtimestamp(request.at_ms / 1000, tz=timezone.utc).date().isoformat()
        content_dna = self._read_dna(project, scenario.dna_subject, rotation_key=rotation_key)

        tone_config = content_config.get("tone_of_voice", {}).get("tone", {})
        prompt_rules = load_prompt_rules(project, repo_root=self.repo_root)
        target_language = str(request.facts.get("target_language") or prompt_rules.get("default_target_language") or "vi")
        audience = str(
            request.facts.get("target_audience")
            or "Vietnamese and international travelers considering a stay near West Lake"
        )
        pillar = str(lane.get("id") or lane_key)
        tone = str(tone_config.get("default") or prompt_rules.get("tone") or "warm, clear, trustworthy")
        platform_rule = str(lane.get("prompt_rules") or "default")
        request_for_builder = ContentRequest(
            project=project,
            content_type="facebook_post",
            topic=topic,
            target_audience=audience,
            content_pillar=pillar,
            tone=tone,
            target_language=target_language,
            cta_type="booking_soft",
            lane=lane_key,
            dna_subject=scenario.dna_subject,
            recent_topics=self._string_list(request.facts.get("recent_topics")),
            prompt_rules=platform_rule,
        )
        brief = self._brief(request, request_for_builder)
        content_prompt = build_content_prompt(
            dna=content_dna,
            task_brief=brief,
            brief_slug=_slug(f"facebook-{topic}")[:80],
            target_language=target_language,
            prompt_rules=prompt_rules,
            platform="facebook",
        )
        content_output = build_social_draft(
            request_for_builder,
            content_prompt,
            content_config,
            generator_fn=self.generator_fn,
        )
        caption = _caption_text(
            content_output.hook,
            content_output.body,
            content_output.cta,
            content_output.hashtags,
        )
        fact_keys = tuple(sorted(set(self._string_list(request.facts.get("fact_keys")))))
        topic_key = str(request.facts.get("topic_key") or _topic_key(pillar, topic))
        image_options = self._image_options(
            project=project,
            request=request,
            topic=topic,
            scenario_key=scenario_key,
            candidates=candidates,
            registry=registry,
        )
        profiles = self._caption_profiles(project, request.facts)
        return DraftPackage(
            topic_key=topic_key,
            pillar=pillar,
            brief=brief,
            fact_keys=fact_keys,
            captions_by_profile={profile: caption for profile in profiles},
            image_options=tuple(image_options),
        )

    def close(self) -> None:
        """Remove returned temporary image files after the consuming job finishes."""
        while self._temporary_directories:
            self._temporary_directories.pop().cleanup()

    def __enter__(self) -> "LegacyGeneratorAdapter":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def _scenario_registry(self, project: str) -> ScenarioRegistry:
        if self.scenario_registry is None:
            path = self.config_root / project / "growth" / "scenario_registry.yaml"
            self.scenario_registry = ScenarioRegistry.from_file(path)
        return self.scenario_registry

    def _reference_asset_resolver(self, project: str) -> ReferenceAssetResolver:
        if self.reference_resolver is None:
            path = self.config_root / project / "growth" / "reference_assets.yaml"
            self.reference_resolver = ReferenceAssetResolver.from_file(path, assets_root=self.repo_root)
        return self.reference_resolver

    def _lane_key(self, requested: str, lanes: Mapping[str, Any], slot_id: str) -> str:
        normalized = _LANE_ALIASES.get(str(requested).lower(), str(requested).lower())
        if normalized in lanes:
            return normalized
        available = sorted(key for key, value in lanes.items() if value.get("topics"))
        if not available:
            raise ValueError("No content lanes with topics are configured")
        return available[_stable_index(slot_id, len(available))]

    def _topic(self, request: DraftRequest, lane: Mapping[str, Any]) -> str:
        provided = request.facts.get("topic")
        if isinstance(provided, str) and provided.strip():
            return provided.strip()
        topics = [str(value).strip() for value in lane.get("topics", []) if str(value).strip()]
        for special in lane.get("special_topics", []) or []:
            topics.extend(str(value).strip() for value in special.get("topics", []) if str(value).strip())
        recent = {item.casefold() for item in self._string_list(request.facts.get("recent_topics"))}
        candidates = [value for value in topics if value.casefold() not in recent] or topics
        if not candidates:
            raise ValueError(f"Lane has no topic candidates: {lane.get('id', 'unknown')}")
        return candidates[_stable_index(request.slot_id, len(candidates))]

    def _scenario_key(self, request: DraftRequest, topic: str, candidates: list[str]) -> str:
        requested = request.facts.get("scenario_key")
        registry = self._scenario_registry(request.project_id)
        if isinstance(requested, str) and requested:
            if candidates and requested not in candidates:
                raise ValueError("Requested scenario_key is outside the selected lane scenario_pool")
            registry.resolve(requested)
            return requested
        if not candidates:
            raise ValueError("Selected lane has no scenario_pool")
        matched = topic_scenario(topic, candidates)
        return matched or candidates[_stable_index(request.slot_id, len(candidates))]

    def _read_dna(self, project: str, subject: str, *, rotation_key: str) -> KnowledgeDna:
        if not subject:
            raise ValueError("Selected scenario does not declare a DNA subject")
        root = self.data_root / project / "knowledge"
        path = root / f"VENHO_HOTEL_{subject.upper()}_DNA.json"
        if subject == "lake_view_room":
            room_dnas = sorted(root.glob("VENHO_HOTEL_LAKE_VIEW_ROOM_[12]_DNA.json"))
            if room_dnas:
                path = room_dnas[_stable_index(rotation_key, len(room_dnas))]
        return read_dna(path)

    def _caption_profiles(self, project: str, facts: Mapping[str, object]) -> list[str]:
        configured = facts.get("caption_profiles")
        if isinstance(configured, (list, tuple)):
            profiles = [str(item).strip() for item in configured if str(item).strip()]
        else:
            path = self.config_root / project / "growth_engine" / "channels.yaml"
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
            profiles = [
                str(channel.get("caption_profile") or "default")
                for channel in (payload or {}).get("channels", [])
                if isinstance(channel, dict)
            ]
        return sorted(set(profiles or ["default"]))

    def _brief(self, request: DraftRequest, content_request: ContentRequest) -> str:
        supplied = request.facts.get("brief")
        if isinstance(supplied, str) and supplied.strip():
            return supplied.strip()
        return (
            f"Create a Facebook post about '{content_request.topic}' for {content_request.target_audience}. "
            f"Content pillar: {content_request.content_pillar}. Tone: {content_request.tone}. "
            f"Length: medium. CTA type: {content_request.cta_type}."
        )

    def _image_options(
        self,
        *,
        project: str,
        request: DraftRequest,
        topic: str,
        scenario_key: str,
        candidates: list[str],
        registry: ScenarioRegistry,
    ) -> list[dict[str, Any]]:
        resolver = self._reference_asset_resolver(project)
        rotation_key = datetime.fromtimestamp(request.at_ms / 1000, tz=timezone.utc).date().isoformat()
        options: list[dict[str, Any]] = []

        if getattr(self.image_provider, "enabled", True):
            option_a = self._generate_image_option(
                option_id="A",
                project=project,
                topic=topic,
                request=request,
                scenario_key=scenario_key,
                registry=registry,
                resolver=resolver,
                rotation_key=rotation_key,
                rotation_offset=0,
            )
            if option_a:
                options.append(option_a)

            if os.environ.get("GROWTH_IMAGE_ALTERNATIVES") == "1":
                alternative = alternate_scenario(scenario_key, candidates, registry)
                if alternative:
                    option_b = self._generate_image_option(
                        option_id="B",
                        project=project,
                        topic=topic,
                        request=request,
                        scenario_key=alternative,
                        registry=registry,
                        resolver=resolver,
                        rotation_key=rotation_key,
                        rotation_offset=1,
                    )
                    if option_b:
                        options.append(option_b)

        try:
            photo_path = library_photo_path(
                scenario_key,
                registry,
                resolver,
                rotation_key=rotation_key,
            )
            if photo_path and photo_path.is_file():
                option_c = self._copy_library_option(photo_path, scenario_key, request)
                if option_c:
                    options.append(option_c)
        except (OSError, KeyError, ValueError):
            # A missing curated reference is not a reason to write a broken file path.
            pass
        return options

    def _generate_image_option(
        self,
        *,
        option_id: str,
        project: str,
        topic: str,
        request: DraftRequest,
        scenario_key: str,
        registry: ScenarioRegistry,
        resolver: ReferenceAssetResolver,
        rotation_key: str,
        rotation_offset: int,
    ) -> dict[str, Any] | None:
        scenario = registry.resolve(scenario_key)
        try:
            references = (
                resolver.resolve(
                    list(scenario.reference_asset_ids),
                    rotation_key=rotation_key,
                    rotation_offset=rotation_offset,
                )
                if scenario.reference_asset_ids
                else None
            )
        except (OSError, KeyError, ValueError):
            return None

        dna = self._read_dna(project, scenario.dna_subject, rotation_key=rotation_key)
        contract = build_image_prompt(
            dna,
            f"A real photo for: {topic}. Scene: {scenario.display_name}.",
            brief_slug=_slug(f"{scenario_key}-{request.slot_id}")[:80],
        )
        final_prompt = build_final_prompt(
            {
                "base_prompt": contract.final_prompt,
                "scenario_key": scenario_key,
            }
        )
        image_bytes = self.image_provider.generate(
            final_prompt,
            size="1024x1280",
            quality="medium",
            reference_images=references,
        )
        image_path, output_bytes = self._write_generated_image(option_id, scenario_key, image_bytes)
        provenance = {
            "source": "configured_image_provider",
            "provider": str(getattr(self.image_provider, "model", type(self.image_provider).__name__)),
            "scenario_key": scenario_key,
            "reference_asset_ids": list(scenario.reference_asset_ids),
            "prompt_sha256": hashlib.sha256(final_prompt.encode("utf-8")).hexdigest(),
            "image_sha256": hashlib.sha256(output_bytes).hexdigest(),
        }
        return {"option_id": option_id, "path": str(image_path), "provenance": provenance}

    def _copy_library_option(
        self,
        photo_path: Path,
        scenario_key: str,
        request: DraftRequest,
    ) -> dict[str, Any] | None:
        try:
            with Image.open(photo_path) as image:
                image.verify()
            photo_bytes = photo_path.read_bytes()
        except (OSError, ValueError):
            return None
        temporary_dir = self._temporary_directory()
        suffix = photo_path.suffix.lower() or ".img"
        target = Path(temporary_dir.name) / f"C-{_slug(scenario_key)}{suffix}"
        target.write_bytes(photo_bytes)
        return {
            "option_id": "C",
            "path": str(target),
            "provenance": {
                "source": "curated_reference_asset",
                "scenario_key": scenario_key,
                "source_name": photo_path.name,
                "image_sha256": hashlib.sha256(photo_bytes).hexdigest(),
                "at_ms": request.at_ms,
            },
        }

    def _write_generated_image(self, option_id: str, scenario_key: str, image_bytes: bytes) -> tuple[Path, bytes]:
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            output = BytesIO()
            converted = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            converted.save(output, format="PNG", optimize=True)
        output_bytes = output.getvalue()
        target = Path(self._temporary_directory().name) / f"{option_id}-{_slug(scenario_key)}.png"
        target.write_bytes(output_bytes)
        return target, output_bytes

    def _temporary_directory(self) -> tempfile.TemporaryDirectory[str]:
        if self.temp_root is not None:
            self.temp_root.mkdir(parents=True, exist_ok=True)
            directory = tempfile.TemporaryDirectory(prefix="gc2-", dir=self.temp_root)
        else:
            directory = tempfile.TemporaryDirectory(prefix="venho-gc2-")
        self._temporary_directories.append(directory)
        return directory

    @staticmethod
    def _string_list(value: object) -> list[str]:
        if not isinstance(value, (list, tuple)):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _caption_text(hook: str, body: str, cta: str, hashtags: list[str]) -> str:
    pieces = [str(value).strip() for value in (hook, body, cta) if str(value).strip()]
    tag_line = " ".join(str(tag).strip() for tag in hashtags if str(tag).strip())
    if tag_line:
        pieces.append(tag_line)
    return "\n\n".join(pieces)


def _stable_index(key: str, size: int) -> int:
    if size <= 0:
        raise ValueError("Cannot select from an empty candidate list")
    digest = hashlib.sha256(str(key).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % size


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    result = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return result or "draft"


def _topic_key(pillar: str, topic: str) -> str:
    slug = _slug(topic)[:48]
    digest = hashlib.sha256(topic.encode("utf-8")).hexdigest()[:10]
    return f"{_slug(pillar)[:24]}:{slug}-{digest}"
