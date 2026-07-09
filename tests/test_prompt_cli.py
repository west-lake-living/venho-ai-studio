from typer.testing import CliRunner

from prompt_studio.cli import _run_all, _run_one, _slugify, app
from prompt_studio.optimizer_mock import optimize_mock
from prompt_studio.prompt_manifest import RegenerationDecision

runner = CliRunner()


def test_slugify_derives_short_kebab_case_slug():
    assert _slugify("Create a realistic booking-style image of the lake view room.") == "create-a-realistic-booking-style"


def test_cli_help_lists_the_documented_flags():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for flag in ("--type", "--project", "--subject", "--brief", "--lang", "--all", "--allow-draft"):
        assert flag in result.output


def test_cli_missing_subject_and_brief_exits_nonzero():
    # No optimizer involved here — validation fails before any pipeline call is made.
    result = runner.invoke(app, ["--type", "image", "--project", "venho_hotel"])
    assert result.exit_code != 0
    assert "--subject and --brief are required" in result.output


def test_cli_unknown_type_exits_nonzero():
    result = runner.invoke(
        app, ["--type", "bogus", "--project", "venho_hotel", "--subject", "lake_view_room", "--brief", "x"]
    )
    assert result.exit_code != 0
    assert "Unknown --type" in result.output


def test_run_one_image_generates_and_saves(tmp_path):
    result = _run_one(
        "image", "venho_hotel", "lake_view_room",
        "Create a realistic booking-style image of the lake view room.",
        None, None, None, False, root=tmp_path, optimize_fn=optimize_mock,
    )
    assert result.contract.prompt_id == "lake_view_room__image__create-a-realistic-booking-style"
    assert result.regeneration_decision == RegenerationDecision.NEW
    assert result.paths is not None and result.paths.markdown.exists()


def test_run_one_video_parses_character_then_environment_subjects(tmp_path):
    result = _run_one(
        "video", "venho_hotel", "linh_an,lake_view_room",
        "A 15-second video of Linh An at the window.", "window-15s",
        None, None, False, root=tmp_path, optimize_fn=optimize_mock,
    )
    assert result.contract.character_lock is not None
    assert result.contract.environment_dna is not None
    assert result.contract.prompt_id.startswith("linh_an+lake_view_room__video__")


def test_run_one_video_single_subject_has_no_character(tmp_path):
    result = _run_one(
        "video", "venho_hotel", "lake_view_room",
        "An empty lake view room at sunrise.", "empty-room",
        None, None, False, root=tmp_path, optimize_fn=optimize_mock,
    )
    assert result.contract.character_lock is None


def test_run_one_content_respects_lang_override(tmp_path):
    result = _run_one(
        "content", "venho_hotel", "westlake",
        "Facebook post about staying near West Lake.", "fb-stay",
        "vi", None, False, root=tmp_path, optimize_fn=optimize_mock,
    )
    assert result.contract.target_language == "vi"


def test_run_one_seo_defaults_keyword_to_brief_when_omitted(tmp_path):
    result = _run_one(
        "seo", "venho_hotel", "westlake",
        "Blog post about hotels near West Lake Hanoi.", "blog",
        "vi", None, False, root=tmp_path, optimize_fn=optimize_mock,
    )
    assert result.contract.keyword_intent == "Blog post about hotels near West Lake Hanoi."


def test_run_all_generates_image_content_seo_and_reports(tmp_path, capsys):
    _run_all(
        "venho_hotel", "westlake", "Facebook post about staying near West Lake.", "fb-stay", "vi", None, False,
        root=tmp_path, optimize_fn=optimize_mock,
    )
    captured = capsys.readouterr()
    assert "[OK]   image" in captured.out
    assert "[OK]   content" in captured.out
    assert "[OK]   seo" in captured.out
