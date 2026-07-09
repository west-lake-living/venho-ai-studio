import json
from pathlib import Path

import pytest

from prompt_studio.knowledge_reader import DnaReadError, read_dna

REAL_DNA = Path("data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json")


def test_read_dna_maps_real_module01_dna_file():
    dna = read_dna(REAL_DNA)
    assert dna.project == "venho_hotel"
    assert dna.subject == "lake_view_room"
    assert dna.contract_version == "1.1"
    assert len(dna.required_dna) == len(json.loads(REAL_DNA.read_text())["invariant"])
    assert all(hasattr(item, "key") and hasattr(item, "value") for item in dna.required_dna)
    assert all(hasattr(item, "key") and hasattr(item, "value_range") for item in dna.allowed_variations)
    assert all(item.source for item in dna.allowed_imperfections)
    assert all(item.source for item in dna.forbidden)

    entry = dna.source_entry()
    assert entry.file == REAL_DNA.name
    assert entry.dna_contract_version == "1.1"
    assert entry.hash.startswith("sha256:")


def test_read_dna_missing_file_raises_clear_error():
    with pytest.raises(DnaReadError, match="not found"):
        read_dna(Path("data/projects/venho_hotel/knowledge/DOES_NOT_EXIST_DNA.json"))


def test_read_dna_missing_required_field_raises_clear_error(tmp_path):
    broken = {
        "contract_version": "1.1",
        "project": "venho_hotel",
        "subject": "lake_view_room",
        "dna_version": "1.0",
        "invariant": [],
        "variable": [],
        # allowed_imperfections and forbidden deliberately missing
    }
    p = tmp_path / "broken.json"
    p.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(DnaReadError, match="missing required field"):
        read_dna(p)


def test_read_dna_contract_version_out_of_range_raises_clear_error(tmp_path):
    future = {
        "contract_version": "2.0",
        "project": "venho_hotel",
        "subject": "lake_view_room",
        "dna_version": "1.0",
        "invariant": [],
        "variable": [],
        "allowed_imperfections": [],
        "forbidden": [],
    }
    p = tmp_path / "future.json"
    p.write_text(json.dumps(future), encoding="utf-8")
    with pytest.raises(DnaReadError, match="outside the supported range"):
        read_dna(p)


def test_read_dna_never_touches_overrides_yaml(monkeypatch):
    """Regression guard for §3.4: reader must not open overrides.yaml, only the merged DNA JSON."""
    import prompt_studio.knowledge_reader as reader_module

    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(self):
        assert "overrides" not in self.name, f"knowledge_reader must not read {self}"
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    reader_module.read_dna(REAL_DNA)
