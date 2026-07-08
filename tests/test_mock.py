"""Full pipeline tests using mock provider — no API calls, no network."""

import shutil
from datetime import datetime
from pathlib import Path

import pytest

from shared.vision.client import MockVisionClient
from knowledge_studio.vision.schemas.base import BaseObservation, ObservedFeature, ForbiddenRule, AllowedImperfection
from knowledge_studio.vision.subject_resolver import resolve
from knowledge_studio.vision.pass1_observe import observe_all
from knowledge_studio.vision.pass2_consolidate import consolidate
from knowledge_studio.vision.renderers.single_md import render_single_md, write_mode_a_output
from knowledge_studio.vision.renderers.dna_md import render_dna_md, write_dna_output

BASE_DIR = Path(__file__).parent.parent
FIXTURES_DIR = Path(__file__).parent / "fixtures"
ROOM_IMAGES_DIR = BASE_DIR / "data" / "media" / "rooms"


@pytest.fixture
def mock_client():
    return MockVisionClient()


@pytest.fixture
def room_subject():
    return resolve("venho_hotel", "room")


@pytest.fixture
def tmp_obs_dir(tmp_path):
    return tmp_path / "observations"


@pytest.fixture
def tmp_out_dir(tmp_path):
    return tmp_path / "output"


class TestMockClientImports:
    def test_mock_client_has_correct_attributes(self, mock_client):
        assert mock_client.image_provider_name == "mock"
        assert mock_client.image_model == "mock"

    def test_mock_analyze_returns_features(self, mock_client):
        result = mock_client.analyze_image(Path("fake.jpg"), "system prompt")
        assert "features" in result
        assert len(result["features"]) > 0

    def test_mock_synthesize_echoes_keys(self, mock_client):
        import json
        payload = [{"key": "window_frame", "values": ["black_aluminum"]}]
        result = mock_client.synthesize("system", json.dumps(payload))
        assert isinstance(result, list)
        assert result[0]["key"] == "window_frame"
        assert result[0]["canonical"] == "black_aluminum"


class TestSubjectResolver:
    def test_resolves_venho_hotel_room(self, room_subject):
        assert room_subject.name == "room"
        assert room_subject.schema_id == "venho_hotel.room"
        assert len(room_subject.aggregation_keys) > 0

    def test_schema_source_is_project_specific(self, room_subject):
        assert "venho_hotel" in room_subject.schema_source

    def test_resolve_unknown_falls_back_to_universal(self):
        # Per §6: unknown subject falls back to universal_schema.yaml — not an error
        sd = resolve("venho_hotel", "completely_unknown_subject_xyz")
        assert "universal" in sd.schema_source or "universal" in sd.schema_id


class TestPass1WithMock:
    def test_observe_all_returns_observations(self, mock_client, room_subject, tmp_obs_dir):
        if not ROOM_IMAGES_DIR.exists() or not any(ROOM_IMAGES_DIR.iterdir()):
            pytest.skip("Room images not available")

        from shared.vision.image_loader import load_images
        images = load_images(ROOM_IMAGES_DIR)[:2]

        observations, report = observe_all(
            images, tmp_obs_dir, mock_client, "1.0", "1.0", room_subject,
            mode="B", concurrency=2,
        )
        assert len(observations) == 2
        assert report.processed == 2
        assert report.failed == []

    def test_observation_has_provider_and_model(self, mock_client, room_subject, tmp_obs_dir):
        if not ROOM_IMAGES_DIR.exists() or not any(ROOM_IMAGES_DIR.iterdir()):
            pytest.skip("Room images not available")

        from shared.vision.image_loader import load_images
        images = load_images(ROOM_IMAGES_DIR)[:1]

        observations, _ = observe_all(
            images, tmp_obs_dir, mock_client, "1.0", "1.0", room_subject,
            mode="B", concurrency=1,
        )
        obs = observations[0]
        assert obs.provider == "mock"
        assert obs.model == "mock"
        assert obs.contract_version == "1.0"

    def test_cache_hit_on_second_run(self, mock_client, room_subject, tmp_obs_dir):
        if not ROOM_IMAGES_DIR.exists() or not any(ROOM_IMAGES_DIR.iterdir()):
            pytest.skip("Room images not available")

        from shared.vision.image_loader import load_images
        images = load_images(ROOM_IMAGES_DIR)[:1]

        _, report1 = observe_all(images, tmp_obs_dir, mock_client, "1.0", "1.0", room_subject, concurrency=1)
        _, report2 = observe_all(images, tmp_obs_dir, mock_client, "1.0", "1.0", room_subject, concurrency=1)

        assert report1.cache_hits == 0
        assert report2.cache_hits == 1


class TestModeARenderer:
    def test_render_single_md_has_required_sections(self):
        obs = BaseObservation(
            image_hash="a" * 64,
            image_file="test.jpg",
            subject="room",
            schema_version="1.0",
            prompt_version="1.0",
            provider="mock",
            model="mock",
            observed_at=datetime.now().isoformat(),
            features=[
                ObservedFeature(key="lighting_condition", type="enum", value="natural_daylight", category="lighting", confidence=0.9),
            ],
        )
        md = render_single_md(obs)
        required_sections = ["# IMAGE OBSERVATION", "## META", "## LIGHTING", "## UNCERTAINTY"]
        for section in required_sections:
            assert section in md, f"Missing section: {section}"

    def test_render_has_contract_version(self):
        obs = BaseObservation(
            image_hash="b" * 64,
            image_file="test.jpg",
            subject="room",
            schema_version="1.0",
            prompt_version="1.0",
            observed_at=datetime.now().isoformat(),
            features=[],
        )
        md = render_single_md(obs)
        assert "contract_version" in md

    def test_not_visible_features_excluded_from_md(self):
        obs = BaseObservation(
            image_hash="c" * 64,
            image_file="test.jpg",
            subject="room",
            schema_version="1.0",
            prompt_version="1.0",
            observed_at=datetime.now().isoformat(),
            features=[
                ObservedFeature(key="floor", type="enum", value="not_visible", category="structure", confidence=0.0),
            ],
        )
        md = render_single_md(obs)
        assert "not_visible" not in md


class TestModeBRenderer:
    def test_render_dna_md_has_required_sections(self, mock_client, room_subject, tmp_obs_dir):
        from knowledge_studio.vision.schemas.base import InvariantFeature, VariableFeature, EvidenceSummary, BaseDNA
        from datetime import datetime

        dna = room_subject.dna_cls(
            project="venho_hotel",
            subject="room",
            dna_version="1.0",
            schema_version="1.0",
            prompt_version="1.0",
            generated_at=datetime.now().isoformat(),
            source_images=["hash1", "hash2"],
            invariant=[
                InvariantFeature(key="window_frame", value="black aluminum", evidence_count=2, coverage=1.0, consistency=1.0)
            ],
            variable=[
                VariableFeature(key="lighting_condition", value_range=["natural_daylight", "artificial_warm"])
            ],
            forbidden=[ForbiddenRule(rule="no marble interior", source="observed")],
            allowed_imperfections=[AllowedImperfection(value="minor scuff marks acceptable", source="curated")],
            evidence=EvidenceSummary(total_images=2),
        )

        md = render_dna_md(dna, "venho_hotel")
        required_sections = [
            "# PROJECT SUBJECT DNA", "## META", "## INVARIANT", "## VARIABLE",
            "## ALLOWED IMPERFECTIONS", "## FORBIDDEN",
            "## EVIDENCE", "## WEAK FEATURES", "## FUTURE CAPTURE NOTES", "## CURATOR NOTES",
        ]
        for section in required_sections:
            assert section in md, f"Missing DNA section: {section}"

    def test_forbidden_shows_source_tag(self, room_subject):
        from knowledge_studio.vision.schemas.base import BaseDNA, EvidenceSummary
        from datetime import datetime

        dna = room_subject.dna_cls(
            project="venho_hotel",
            subject="room",
            dna_version="1.0",
            schema_version="1.0",
            prompt_version="1.0",
            generated_at=datetime.now().isoformat(),
            source_images=[],
            invariant=[],
            variable=[],
            forbidden=[
                ForbiddenRule(rule="no marble interior", source="curated"),
                ForbiddenRule(rule="no luxury resort look", source="observed"),
            ],
            evidence=EvidenceSummary(total_images=0),
        )
        md = render_dna_md(dna, "venho_hotel")
        assert "[curated]" in md
        assert "[observed]" in md

    def test_dna_json_has_contract_version_1_1(self, room_subject):
        from knowledge_studio.vision.schemas.base import BaseDNA, EvidenceSummary
        from datetime import datetime

        dna = room_subject.dna_cls(
            project="venho_hotel",
            subject="room",
            dna_version="1.0",
            schema_version="1.0",
            prompt_version="1.0",
            generated_at=datetime.now().isoformat(),
            source_images=[],
            invariant=[],
            variable=[],
            forbidden=[],
            evidence=EvidenceSummary(total_images=0),
        )
        data = dna.model_dump()
        assert data["contract_version"] == "1.1"

    def test_forbidden_string_coercion(self, room_subject):
        """ForbiddenRule accepts bare strings (backward compat) — coerced to source=observed."""
        from knowledge_studio.vision.schemas.base import EvidenceSummary
        from datetime import datetime

        dna = room_subject.dna_cls(
            project="venho_hotel",
            subject="room",
            dna_version="1.0",
            schema_version="1.0",
            prompt_version="1.0",
            generated_at=datetime.now().isoformat(),
            source_images=[],
            invariant=[],
            variable=[],
            forbidden=["no marble interior"],  # bare string — should coerce to ForbiddenRule
            evidence=EvidenceSummary(total_images=0),
        )
        assert dna.forbidden[0].rule == "no marble interior"
        assert dna.forbidden[0].source == "observed"
