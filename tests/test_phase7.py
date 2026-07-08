"""Phase 7 — Steps 11-13: Schema Bootstrap, Auto Classify, Face/Linh An subject."""

from datetime import datetime
from pathlib import Path

import pytest
import yaml

from knowledge_studio.vision.pass2_consolidate import _pass2a
from knowledge_studio.vision.schemas.base import BaseObservation, ObservedFeature
from knowledge_studio.vision.subject_resolver import _observe_prompt_path, resolve
from knowledge_studio.vision.overlay_merge import load_overlay

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent

LINH_AN_AGGREGATION_KEYS = [
    {"key": "face_shape", "type": "enum", "values": ["elongated_oval", "round", "square", "heart", "diamond", "not_visible"]},
    {"key": "eye_shape", "type": "enum", "values": ["long_almond", "round_almond", "monolid", "hooded", "not_visible"]},
    {"key": "expression_type", "type": "enum", "values": ["living_expression_subtle_smile", "neutral", "broad_smile", "serious", "not_visible"]},
    {"key": "camera_angle_horizontal", "type": "enum", "values": ["soft_hero_left_10_20deg", "straight_on", "right_angle", "profile_left", "profile_right", "not_visible"]},
]

THRESHOLDS = {
    "consolidation_threshold": 0.6,
    "consistency_threshold": 0.7,
    "weak_threshold": 0.3,
}


def make_obs(idx: int, features: list[dict]) -> BaseObservation:
    return BaseObservation(
        image_hash=f"hash{idx:04d}" * 4,
        image_file=f"img_{idx}.jpg",
        subject="linh_an",
        schema_version="1.0",
        prompt_version="1.0",
        observed_at=datetime.now().isoformat(),
        features=[ObservedFeature(**f) for f in features],
    )


def _dummy_jpg(path: Path) -> Path:
    """Write minimal JPEG magic bytes so load_images() finds it."""
    path.write_bytes(b"\xff\xd8\xff\xe0")
    return path


# ---------------------------------------------------------------------------
# Fake VisionClient classes (no API calls)
# ---------------------------------------------------------------------------

class _MockBootstrapClient:
    """Returns suggested_keys for schema_bootstrap tests."""
    def analyze_image(self, image_path: Path, prompt: str) -> dict:
        return {
            "suggested_keys": [
                {"key": "face_shape", "type": "enum", "values": ["oval", "round", "elongated"]},
                {"key": "skin_tone", "type": "free"},
            ]
        }
    def synthesize(self, *args, **kwargs) -> list:
        return []


class _MockClassifyClient:
    """Returns a fixed subject for classify tests."""
    def __init__(self, subject: str = "room"):
        self._subject = subject

    def analyze_image(self, image_path: Path, prompt: str) -> dict:
        return {"subject": self._subject, "confidence": 0.9}

    def synthesize(self, *args, **kwargs) -> list:
        return []


# ---------------------------------------------------------------------------
# Step 11 — Schema Bootstrap
# ---------------------------------------------------------------------------

class TestSchemaBootstrap:
    """Step 11 DoD: bootstrap() generates a valid starter schema YAML."""

    def test_bootstrap_writes_yaml_file(self, tmp_path):
        """bootstrap() must create a .yaml file at output_path."""
        from knowledge_studio.vision.schema_bootstrap import bootstrap
        img = _dummy_jpg(tmp_path / "sample.jpg")
        output = tmp_path / "new_subject.yaml"
        result = bootstrap([img], _MockBootstrapClient(), "new_subject", output)
        assert result.exists()
        assert result.suffix == ".yaml"

    def test_bootstrap_yaml_has_required_structure(self, tmp_path):
        """Written YAML must have schema_id, aggregation_keys, forbidden_defaults."""
        from knowledge_studio.vision.schema_bootstrap import bootstrap
        img = _dummy_jpg(tmp_path / "sample.jpg")
        output = tmp_path / "test.yaml"
        bootstrap([img], _MockBootstrapClient(), "test_subject", output)
        data = yaml.safe_load(output.read_text())
        assert "schema_id" in data
        assert "aggregation_keys" in data
        assert "forbidden_defaults" in data

    def test_bootstrap_yaml_contains_suggested_keys(self, tmp_path):
        """Suggested keys from AI response appear in aggregation_keys list."""
        from knowledge_studio.vision.schema_bootstrap import bootstrap
        img = _dummy_jpg(tmp_path / "sample.jpg")
        output = tmp_path / "test.yaml"
        bootstrap([img], _MockBootstrapClient(), "test_subject", output)
        data = yaml.safe_load(output.read_text())
        keys = [k["key"] for k in data["aggregation_keys"]]
        assert "face_shape" in keys
        assert "skin_tone" in keys

    def test_bootstrap_merges_values_across_sample_images(self, tmp_path):
        """When same key appears in multiple samples, enum values are union-merged."""
        from knowledge_studio.vision.schema_bootstrap import bootstrap

        call_count = {"n": 0}

        class _TwoRoundMock:
            def analyze_image(self, image_path: Path, prompt: str) -> dict:
                call_count["n"] += 1
                if call_count["n"] % 2 == 1:
                    return {"suggested_keys": [{"key": "eye_shape", "type": "enum", "values": ["almond", "round"]}]}
                return {"suggested_keys": [{"key": "eye_shape", "type": "enum", "values": ["almond", "monolid"]}]}
            def synthesize(self, *args, **kwargs) -> list:
                return []

        imgs = [_dummy_jpg(tmp_path / f"img_{i}.jpg") for i in range(2)]
        output = tmp_path / "merged.yaml"
        bootstrap(imgs, _TwoRoundMock(), "eye_test", output, max_sample=2)
        data = yaml.safe_load(output.read_text())
        eye_key = next(k for k in data["aggregation_keys"] if k["key"] == "eye_shape")
        values = eye_key.get("values", [])
        assert "almond" in values
        assert "monolid" in values  # added by second image

    def test_bootstrap_from_dir_raises_for_empty_dir(self, tmp_path):
        """bootstrap_from_dir raises FileNotFoundError when no images found."""
        from knowledge_studio.vision.schema_bootstrap import bootstrap_from_dir
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            bootstrap_from_dir(empty_dir, _MockBootstrapClient(), "subject", tmp_path / "out.yaml")

    def test_bootstrap_cli_command_registered(self):
        """'bootstrap' must be a registered subcommand of 'venho vision'."""
        from typer.testing import CliRunner
        from knowledge_studio.vision.cli import vision_app
        runner = CliRunner()
        result = runner.invoke(vision_app, ["bootstrap", "--help"])
        assert result.exit_code == 0, f"bootstrap --help failed: {result.output}"
        assert "--subject" in result.output
        assert "--input" in result.output


# ---------------------------------------------------------------------------
# Step 12 — Auto Classify
# ---------------------------------------------------------------------------

class TestAutoClassify:
    """Step 12 DoD: classify_image and classify_folder behaviors."""

    def test_classify_image_returns_general_when_no_subject_key(self, tmp_path):
        """MockVisionClient returns MOCK_OBSERVATION (no 'subject' key) → fallback 'general'."""
        from knowledge_studio.vision.pass0_classify import classify_image
        from shared.vision.client import MockVisionClient
        img = _dummy_jpg(tmp_path / "test.jpg")
        result = classify_image(img, MockVisionClient())
        assert result == "general"

    def test_classify_image_returns_known_subject(self, tmp_path):
        """classify_image with mock returning 'room' → 'room'."""
        from knowledge_studio.vision.pass0_classify import classify_image
        img = _dummy_jpg(tmp_path / "test.jpg")
        result = classify_image(img, _MockClassifyClient("room"))
        assert result == "room"

    def test_classify_image_rejects_unknown_subject_as_general(self, tmp_path):
        """classify_image with unknown subject 'garden' (not in KNOWN_SUBJECTS) → 'general'."""
        from knowledge_studio.vision.pass0_classify import classify_image
        img = _dummy_jpg(tmp_path / "test.jpg")
        result = classify_image(img, _MockClassifyClient("garden"))
        assert result == "general"

    def test_classify_folder_groups_images_by_subject(self, tmp_path):
        """classify_folder returns dict grouping all images under the mock subject."""
        from knowledge_studio.vision.pass0_classify import classify_folder
        for i in range(3):
            _dummy_jpg(tmp_path / f"img_{i}.jpg")
        result = classify_folder(tmp_path, _MockClassifyClient("room"))
        assert isinstance(result, dict)
        assert "room" in result
        assert len(result["room"]) == 3

    def test_classify_folder_empty_dir_returns_empty(self, tmp_path):
        """classify_folder on a folder with no images returns empty dict."""
        from knowledge_studio.vision.pass0_classify import classify_folder
        result = classify_folder(tmp_path, _MockClassifyClient())
        assert result == {}

    def test_classification_review_requires_human_approval(self, tmp_path):
        """Pass 0 writes review manifest, not an auto-approved Mode B input."""
        from knowledge_studio.vision.pass0_classify import write_classification_review

        img = _dummy_jpg(tmp_path / "room.jpg")
        output = tmp_path / "_classification_review.yaml"
        write_classification_review({"room": [img]}, output, input_dir=tmp_path)

        data = yaml.safe_load(output.read_text())
        assert data["status"] == "pending_human_review"
        assert data["approved_for_mode_b"] is False
        assert data["groups"]["room"] == [str(img)]


class TestPhase5RoadmapGates:
    """Roadmap v2.5 Phase 5 gates: shared schemas, fixed keys, and approval."""

    def test_bootstrap_schema_is_draft_until_reviewed(self, tmp_path):
        from knowledge_studio.vision.schema_bootstrap import bootstrap

        img = _dummy_jpg(tmp_path / "sample.jpg")
        output = tmp_path / "draft_subject.yaml"
        bootstrap([img], _MockBootstrapClient(), "draft_subject", output)

        data = yaml.safe_load(output.read_text())
        assert data["status"] == "draft"
        assert data["approved_for_pass1"] is False
        assert "review_notes" in data

    def test_bootstrap_enum_values_are_stable_english_tokens(self, tmp_path):
        from knowledge_studio.vision.schema_bootstrap import bootstrap

        class _NoisyEnumMock:
            def analyze_image(self, image_path: Path, prompt: str) -> dict:
                return {
                    "suggested_keys": [
                        {
                            "key": "wall_color",
                            "type": "enum",
                            "values": ["Warm White", "cream-beige", "đỏ", "not_visible"],
                        }
                    ]
                }

        img = _dummy_jpg(tmp_path / "sample.jpg")
        output = tmp_path / "tokens.yaml"
        bootstrap([img], _NoisyEnumMock(), "tokens", output)

        data = yaml.safe_load(output.read_text())
        values = data["aggregation_keys"][0]["values"]
        assert "warm_white" in values
        assert "cream_beige" in values
        assert "đỏ" not in values
        assert "not_visible" in values

    def test_subject_resolver_blocks_unapproved_bootstrap_schema(self, tmp_path, monkeypatch):
        import knowledge_studio.vision.subject_resolver as resolver

        schema_dir = tmp_path / "config" / "projects" / "test_project" / "subjects"
        schema_dir.mkdir(parents=True)
        schema = schema_dir / "draft_subject.yaml"
        schema.write_text(
            yaml.dump(
                {
                    "schema_id": "test_project.draft_subject",
                    "schema_version": "1.0",
                    "subject": "draft_subject",
                    "approved_for_pass1": False,
                    "aggregation_keys": [{"key": "shape", "type": "free"}],
                    "forbidden_defaults": [],
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(resolver, "CONFIG_DIR", tmp_path / "config")

        with pytest.raises(ValueError, match="not approved for Pass 1"):
            resolver.resolve("test_project", "draft_subject")

    @pytest.mark.parametrize("subject", ["room", "product", "location"])
    def test_shared_subject_schema_exists_with_fixed_keys_and_types(self, subject):
        path = BASE_DIR / "config" / "projects" / "_shared_subjects" / f"{subject}.yaml"
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert data["approved_for_pass1"] is True
        assert data["aggregation_keys"]
        for item in data["aggregation_keys"]:
            assert "key" in item
            assert item["type"] in {"enum", "free"}
            if item["type"] == "enum":
                assert item.get("values")
                assert all(v.isascii() for v in item["values"])


# ---------------------------------------------------------------------------
# Step 13 — Face Subject / Linh An: subject resolution
# ---------------------------------------------------------------------------

class TestLinhAnSubjectResolution:
    """Step 13 DoD: Linh An uses dedicated prompt, schema, and overlay."""

    def test_linh_an_uses_dedicated_observe_prompt(self):
        """_observe_prompt_path('linh_an') → observe_linh_an.md, not universal."""
        prompt_path = _observe_prompt_path("linh_an")
        assert "observe_linh_an" in prompt_path.name
        assert prompt_path.exists()

    def test_linh_an_prompt_has_grounding_disabled_rule(self):
        """observe_linh_an.md must contain grounding/web-search disabled rule."""
        content = _observe_prompt_path("linh_an").read_text(encoding="utf-8")
        assert "PERMANENTLY DISABLED" in content or "Grounding and web search" in content

    def test_linh_an_prompt_enforces_english_values(self):
        """observe_linh_an.md must enforce English-only values for Pass 2A compatibility."""
        content = _observe_prompt_path("linh_an").read_text(encoding="utf-8")
        assert "English" in content

    def test_linh_an_resolves_subject_def_correctly(self):
        """resolve('venho_hotel', 'linh_an') returns correct SubjectDef."""
        sd = resolve("venho_hotel", "linh_an")
        assert sd.name == "linh_an"
        assert sd.schema_id == "venho_hotel.linh_an"

    def test_linh_an_schema_has_face_identity_keys(self):
        """linh_an schema must include all structural face identity keys."""
        sd = resolve("venho_hotel", "linh_an")
        keys = [k["key"] for k in sd.aggregation_keys]
        for required in ("face_shape", "eye_shape", "eye_color", "nose_bridge", "lip_shape", "jaw_line"):
            assert required in keys, f"Missing face identity key: {required}"

    def test_linh_an_schema_has_variable_keys(self):
        """linh_an schema must include variable appearance keys."""
        sd = resolve("venho_hotel", "linh_an")
        keys = [k["key"] for k in sd.aggregation_keys]
        for required in ("hairstyle", "expression_type", "camera_angle_horizontal", "shot_distance"):
            assert required in keys, f"Missing variable key: {required}"

    def test_linh_an_overlay_has_forbidden_rules(self):
        """Curated overlay must have non-empty forbidden list (§7 contract)."""
        overlay = load_overlay("venho_hotel", "linh_an")
        assert overlay is not None
        assert "forbidden" in overlay
        assert len(overlay["forbidden"]) > 0

    def test_linh_an_overlay_has_qc_gate_documentation(self):
        """Overlay notes must document the 07F QC gate with ≥9.0 threshold."""
        overlay = load_overlay("venho_hotel", "linh_an")
        notes_text = " ".join(overlay.get("notes", []))
        assert "07F" in notes_text or "9.0" in notes_text

    def test_linh_an_overlay_has_wording_overrides(self):
        """Curated wording_overrides must be populated for canonical Face Lock output."""
        overlay = load_overlay("venho_hotel", "linh_an")
        assert "wording_overrides" in overlay
        assert len(overlay["wording_overrides"]) > 0


# ---------------------------------------------------------------------------
# Step 13 — Face Subject / Linh An: Pass 2A classification
# ---------------------------------------------------------------------------

class TestFaceDNAClassification:
    """Step 13 DoD: Pass 2A correctly splits face identity vs. variable features."""

    def test_stable_face_feature_becomes_invariant(self):
        """face_shape = elongated_oval in all 4 images → INVARIANT (coverage=1.0, consistency=1.0)."""
        observations = [
            make_obs(i, [
                {"key": "face_shape", "type": "enum", "value": "elongated_oval", "category": "face", "confidence": 0.95},
            ])
            for i in range(4)
        ]
        result = _pass2a(observations, LINH_AN_AGGREGATION_KEYS, [], THRESHOLDS)
        assert "face_shape" in result["invariant_raw"]
        assert result["invariant_raw"]["face_shape"]["coverage"] == 1.0
        assert result["invariant_raw"]["face_shape"]["consistency"] == 1.0

    def test_expression_type_varies_becomes_variable(self):
        """expression_type changes across images → VARIABLE (high coverage, low consistency)."""
        expressions = [
            "living_expression_subtle_smile",
            "neutral",
            "living_expression_subtle_smile",
            "broad_smile",
        ]
        observations = [
            make_obs(i, [
                {"key": "expression_type", "type": "enum", "value": v, "category": "expression", "confidence": 0.9},
            ])
            for i, v in enumerate(expressions)
        ]
        result = _pass2a(observations, LINH_AN_AGGREGATION_KEYS, [], THRESHOLDS)
        assert "expression_type" in result["variable_raw"], (
            "expression_type changes across images → must be VARIABLE, not INVARIANT"
        )
        assert "expression_type" not in result["invariant_raw"]

    def test_eye_shape_identity_key_becomes_invariant(self):
        """eye_shape = long_almond in all images → INVARIANT (structural eye identity is stable)."""
        observations = [
            make_obs(i, [
                {"key": "eye_shape", "type": "enum", "value": "long_almond", "category": "face", "confidence": 0.9},
            ])
            for i in range(4)
        ]
        result = _pass2a(observations, LINH_AN_AGGREGATION_KEYS, [], THRESHOLDS)
        assert "eye_shape" in result["invariant_raw"]
