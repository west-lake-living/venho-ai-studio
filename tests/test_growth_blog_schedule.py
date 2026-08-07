from __future__ import annotations

from pathlib import Path


def test_tuesday_blog_workflow_generates_a_draft_without_publishing() -> None:
    workflow = Path(".github/workflows/growth-blog-seo.yml").read_text(encoding="utf-8")

    assert 'cron: "0 1 * * 2"' in workflow
    assert "venho-growth blog" in workflow
    assert "approve-and-dispatch" not in workflow
    assert "MAKE_GROWTH_WEBHOOK_URL" not in workflow
