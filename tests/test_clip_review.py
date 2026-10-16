from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from identity_restoration.application.contact_sheet import SCHEMA as SHEET_SCHEMA, build_contact_sheets
from identity_restoration.application.temporal_scan import DecodedFrame
from shared.vision.paid_call_guard import PaidCallBlocked
from validator_studio.clip_reviewer import review_clip


def _reader(video, fps):  # type: ignore[no-untyped-def]
    for index in range(10):  # 0..9 s at 1 fps -> two 3x3 sheets
        yield DecodedFrame(index=index * 24, timestamp_ms=index * 1000, image=Image.new("RGB", (1080, 1920), (index * 20, 0, 0)))


def test_contact_sheets_hold_nine_timestamped_tiles_each(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"clip")
    doc = build_contact_sheets(video, tmp_path / "sheets", reader=_reader)
    assert doc["schema"] == SHEET_SCHEMA and doc["duration_sec"] == 9.0
    first, second = doc["sheets"]
    assert first["timestamps_ms"] == [i * 1000 for i in range(9)] and second["timestamps_ms"] == [9000]
    assert Image.open(first["path"]).size == (1080, 1920)


def _sheet(tmp_path: Path) -> Path:
    path = tmp_path / "sheet.png"
    Image.new("RGB", (10, 10)).save(path)
    return path


def test_critical_error_fails_and_usable_segments_are_clamped_and_sorted(tmp_path: Path) -> None:
    def analyzer(sheets, system, text, schema):  # type: ignore[no-untyped-def]
        assert "Ho Tay" in system and "8.0s" in text
        return {
            "dimensions": {"identity_consistency": 9, "prompt_adherence": 8, "motion_quality": 7,
                           "location_fidelity": 2, "visual_fidelity": 9, "temporal_coherence": 12},
            "errors": [
                {"severity": "critical", "category": "location_swap", "time_range": "0s-8s", "description": "pagoda"},
                {"severity": "BOGUS", "category": "x", "time_range": "", "description": ""},
            ],
            "usable_segments": [{"start_sec": 5, "end_sec": 20}, {"start_sec": -1, "end_sec": 3}],
        }

    report = review_clip([_sheet(tmp_path)], {"prompt": "walk", "duration_sec": 8}, analyzer=analyzer)
    assert report["verdict"] == "FAIL" and len(report["errors"]) == 1
    assert report["dimensions"]["temporal_coherence"] == 10.0
    assert report["usable_segments"] == [{"start_sec": 0.0, "end_sec": 3.0}, {"start_sec": 5.0, "end_sec": 8.0}]


def test_high_errors_pass_with_their_clean_segment(tmp_path: Path) -> None:
    def analyzer(*_):  # type: ignore[no-untyped-def]
        return {
            "dimensions": {name: 8 for name in ("identity_consistency", "prompt_adherence", "motion_quality",
                                                 "location_fidelity", "visual_fidelity", "temporal_coherence")},
            "errors": [{"severity": "HIGH", "category": "camera_drift", "time_range": "5s-8s", "description": "zoom"}],
            "usable_segments": [{"start_sec": 0, "end_sec": 5}],
        }

    report = review_clip([_sheet(tmp_path)], {"duration_sec": 8}, analyzer=analyzer)
    assert report["verdict"] == "PASS" and report["overall_score"] == 8.0
    assert report["usable_segments"] == [{"start_sec": 0.0, "end_sec": 5.0}]


def test_clip_cli_prints_report_path_then_usage_and_reports_blocked_calls(monkeypatch, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    import validator_studio.cli as cli
    import validator_studio.clip_reviewer as reviewer

    brief = tmp_path / "brief.json"
    brief.write_text(json.dumps({"duration_sec": 8}))
    sheet = _sheet(tmp_path)
    monkeypatch.setattr(reviewer, "review_clip", lambda sheets, b: {"sheets": [str(sheet)], "verdict": "PASS"})
    args = ["clip", "--sheet", str(sheet), "--brief", str(brief), "--output-root", str(tmp_path / "out")]
    result = CliRunner().invoke(cli.app, args)
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    json_line = next(line for line in lines if "JSON" in line and ":" in line)
    assert Path(json_line.split(":", 1)[1].strip()).is_file()
    assert lines.index(json_line) < next(i for i, l in enumerate(lines) if l.startswith(cli.USAGE_MARKER))

    def blocked(*_):  # type: ignore[no-untyped-def]
        raise PaidCallBlocked("exhausted")

    monkeypatch.setattr(reviewer, "review_clip", blocked)
    assert CliRunner().invoke(cli.app, args).exit_code == cli.PAID_CALL_BLOCKED_EXIT_CODE
