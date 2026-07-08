"""v2.5 Phase 7 — Vault (search, diff, export) and EXIF tests.

Coverage:
  vault_search  : search(), format_results()
  vault_diff    : list_versions(), diff_versions(), format_version_list()
  vault_export  : export_subject(), export_all()
  vault CLI     : venho vault search/diff/export registered
  image_loader  : read_exif()
"""

from __future__ import annotations

from pathlib import Path

import pytest

BASE_DIR = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_kd(tmp_path: Path) -> Path:
    kd = tmp_path / "knowledge"
    kd.mkdir()
    return kd


# ---------------------------------------------------------------------------
# TestVaultSearch
# ---------------------------------------------------------------------------

class TestVaultSearch:
    def test_finds_keyword_in_dna_file(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("jade teal lake view\nother line\n", encoding="utf-8")
        import knowledge_studio.vision.vault_search as vs
        monkeypatch.setattr(vs, "_knowledge_dir", lambda p: kd)
        hits = vs.search("jade teal", project="venho_hotel")
        assert len(hits) == 1
        assert hits[0].line_number == 1

    def test_search_case_insensitive(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("Black wooden floor\n", encoding="utf-8")
        import knowledge_studio.vision.vault_search as vs
        monkeypatch.setattr(vs, "_knowledge_dir", lambda p: kd)
        hits = vs.search("black", project="venho_hotel")
        assert len(hits) == 1

    def test_subject_filter_limits_results(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("marble floor\n", encoding="utf-8")
        (kd / "VENHO_HOTEL_LOBBY_DNA.md").write_text("marble reception\n", encoding="utf-8")
        import knowledge_studio.vision.vault_search as vs
        monkeypatch.setattr(vs, "_knowledge_dir", lambda p: kd)
        hits = vs.search("marble", project="venho_hotel", subject="ROOM")
        assert len(hits) == 1
        assert "ROOM" in hits[0].file

    def test_no_results_returns_empty_list(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("lake view\n", encoding="utf-8")
        import knowledge_studio.vision.vault_search as vs
        monkeypatch.setattr(vs, "_knowledge_dir", lambda p: kd)
        hits = vs.search("xyz_nonexistent_term", project="venho_hotel")
        assert hits == []

    def test_missing_knowledge_dir_raises(self, tmp_path, monkeypatch):
        import knowledge_studio.vision.vault_search as vs
        monkeypatch.setattr(vs, "_knowledge_dir", lambda p: tmp_path / "no_such_dir")
        with pytest.raises(FileNotFoundError):
            vs.search("any", project="venho_hotel")

    def test_format_results_empty_returns_no_results_message(self):
        from knowledge_studio.vision.vault_search import format_results
        out = format_results([], "my_query")
        assert "No results" in out
        assert "my_query" in out

    def test_format_results_with_hits_includes_filename(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_LOBBY_DNA.md").write_text("marble floor\n", encoding="utf-8")
        import knowledge_studio.vision.vault_search as vs
        monkeypatch.setattr(vs, "_knowledge_dir", lambda p: kd)
        hits = vs.search("marble", project="venho_hotel")
        out = vs.format_results(hits, "marble")
        assert "VENHO_HOTEL_LOBBY_DNA.md" in out
        assert "Line" in out


# ---------------------------------------------------------------------------
# TestVaultDiff
# ---------------------------------------------------------------------------

class TestVaultDiff:
    def _setup(self, tmp_path: Path, *, current: str, archived: str, version: str = "1.0") -> Path:
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text(current, encoding="utf-8")
        archive_dir = kd / "_archive"
        archive_dir.mkdir()
        (archive_dir / f"VENHO_HOTEL_ROOM_DNA_v{version}_20260707_162912.md").write_text(
            archived, encoding="utf-8"
        )
        return kd

    def test_list_versions_finds_archive_file(self, tmp_path, monkeypatch):
        kd = self._setup(tmp_path, current="line A\n", archived="line B\n")
        import knowledge_studio.vision.vault_diff as vd
        monkeypatch.setattr(vd, "_knowledge_dir", lambda p: kd)
        versions = vd.list_versions("venho_hotel", "room")
        assert len(versions) == 1
        assert versions[0]["version"] == "1.0"
        assert versions[0]["timestamp"] == "20260707_162912"

    def test_list_versions_returns_empty_when_no_archive(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("current\n", encoding="utf-8")
        import knowledge_studio.vision.vault_diff as vd
        monkeypatch.setattr(vd, "_knowledge_dir", lambda p: kd)
        assert vd.list_versions("venho_hotel", "room") == []

    def test_diff_versions_returns_unified_diff(self, tmp_path, monkeypatch):
        kd = self._setup(tmp_path, current="line A\nline B\n", archived="line X\nline B\n")
        import knowledge_studio.vision.vault_diff as vd
        monkeypatch.setattr(vd, "_knowledge_dir", lambda p: kd)
        result = vd.diff_versions("venho_hotel", "room")
        assert "---" in result
        assert "+++" in result

    def test_diff_no_archive_returns_message(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("current\n", encoding="utf-8")
        import knowledge_studio.vision.vault_diff as vd
        monkeypatch.setattr(vd, "_knowledge_dir", lambda p: kd)
        result = vd.diff_versions("venho_hotel", "room")
        assert "No archived" in result

    def test_diff_version_not_found_returns_message(self, tmp_path, monkeypatch):
        kd = self._setup(tmp_path, current="A\n", archived="B\n", version="1.0")
        import knowledge_studio.vision.vault_diff as vd
        monkeypatch.setattr(vd, "_knowledge_dir", lambda p: kd)
        result = vd.diff_versions("venho_hotel", "room", from_version="9.9")
        assert "9.9" in result
        assert "not found" in result.lower() or "Available" in result

    def test_format_version_list_no_versions(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        import knowledge_studio.vision.vault_diff as vd
        monkeypatch.setattr(vd, "_knowledge_dir", lambda p: kd)
        result = vd.format_version_list("venho_hotel", "room")
        assert "No archived" in result


# ---------------------------------------------------------------------------
# TestVaultExport
# ---------------------------------------------------------------------------

class TestVaultExport:
    def test_export_subject_returns_header_and_content(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA_COMPACT.md").write_text("compact dna content\n", encoding="utf-8")
        import knowledge_studio.vision.vault_export as ve
        monkeypatch.setattr(ve, "_knowledge_dir", lambda p: kd)
        result = ve.export_subject("venho_hotel", "room")
        assert "VENHO DNA Export" in result
        assert "compact dna content" in result

    def test_export_compact_default(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA_COMPACT.md").write_text("compact version\n", encoding="utf-8")
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("full version\n", encoding="utf-8")
        import knowledge_studio.vision.vault_export as ve
        monkeypatch.setattr(ve, "_knowledge_dir", lambda p: kd)
        result = ve.export_subject("venho_hotel", "room", compact=True)
        assert "compact version" in result
        assert "COMPACT" in result

    def test_export_fallback_to_full_when_no_compact(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA.md").write_text("full version only\n", encoding="utf-8")
        import knowledge_studio.vision.vault_export as ve
        monkeypatch.setattr(ve, "_knowledge_dir", lambda p: kd)
        result = ve.export_subject("venho_hotel", "room", compact=True)
        assert "full version only" in result
        assert "FULL" in result

    def test_export_raises_for_missing_dna(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        import knowledge_studio.vision.vault_export as ve
        monkeypatch.setattr(ve, "_knowledge_dir", lambda p: kd)
        with pytest.raises(FileNotFoundError):
            ve.export_subject("venho_hotel", "room")

    def test_export_all_concatenates_subjects(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        (kd / "VENHO_HOTEL_ROOM_DNA_COMPACT.md").write_text("room content\n", encoding="utf-8")
        (kd / "VENHO_HOTEL_LOBBY_DNA_COMPACT.md").write_text("lobby content\n", encoding="utf-8")
        import knowledge_studio.vision.vault_export as ve
        monkeypatch.setattr(ve, "_knowledge_dir", lambda p: kd)
        result = ve.export_all("venho_hotel", compact=True)
        assert "room content" in result
        assert "lobby content" in result
        assert "2 DNA files" in result

    def test_export_all_raises_for_empty_dir(self, tmp_path, monkeypatch):
        kd = _make_kd(tmp_path)
        import knowledge_studio.vision.vault_export as ve
        monkeypatch.setattr(ve, "_knowledge_dir", lambda p: kd)
        with pytest.raises(FileNotFoundError):
            ve.export_all("venho_hotel", compact=True)


# ---------------------------------------------------------------------------
# TestVaultCLI
# ---------------------------------------------------------------------------

class TestVaultCLI:
    def _vault_help(self) -> str:
        from typer.testing import CliRunner
        from knowledge_studio.vision.cli import app
        return CliRunner().invoke(app, ["vault", "--help"]).output

    def test_vault_search_command_registered(self):
        assert "search" in self._vault_help()

    def test_vault_diff_command_registered(self):
        assert "diff" in self._vault_help()

    def test_vault_export_command_registered(self):
        assert "export" in self._vault_help()


# ---------------------------------------------------------------------------
# TestEXIFReading
# ---------------------------------------------------------------------------

class TestEXIFReading:
    def test_read_exif_returns_empty_for_nonexistent_path(self):
        from shared.vision.image_loader import read_exif
        result = read_exif(Path("/nonexistent/path/image.jpg"))
        assert result == {}

    def test_read_exif_returns_empty_for_non_image_file(self, tmp_path):
        from shared.vision.image_loader import read_exif
        fake = tmp_path / "not_an_image.jpg"
        fake.write_bytes(b"this is not a jpeg")
        result = read_exif(fake)
        assert result == {}

    def test_read_exif_returns_dict_for_real_image(self):
        from shared.vision.image_loader import read_exif
        room_dir = BASE_DIR / "assets" / "raw" / "room"
        if not room_dir.exists():
            pytest.skip("assets/raw/room/ not present")
        images = list(room_dir.rglob("*.jpg")) + list(room_dir.rglob("*.jpeg"))
        if not images:
            pytest.skip("No JPEG files in assets/raw/room/")
        result = read_exif(images[0])
        assert isinstance(result, dict)
