import pytest

from prompt_studio.template_loader import TemplateLoadError, load_template


@pytest.mark.parametrize(
    "prompt_type,expected_max_length",
    [
        ("image", 1800),
        ("video", 3200),
        ("content", 2000),
        ("seo", 2200),
    ],
)
def test_load_template_has_required_fields(prompt_type, expected_max_length):
    template = load_template(prompt_type)
    assert template.template_version == "1.0"
    assert template.prompt_type == prompt_type
    assert isinstance(template.sections, list) and template.sections
    assert template.rules["language"] == "english"
    assert template.rules["max_length"] == expected_max_length


def test_load_template_unknown_type_raises_clear_error():
    with pytest.raises(TemplateLoadError, match="No template"):
        load_template("does_not_exist")
