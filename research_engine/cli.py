from __future__ import annotations

from pathlib import Path

import typer

from research_engine.adapters.notebooklm_handoff import NotebookLMHandoff
from research_engine.adapters.vault_reader import VaultReader
from research_engine.application.detect_stale_knowledge import detect_stale_facts
from research_engine.application.propose_fact import propose_fact
from research_engine.domain.research_note import ResearchNote
from research_engine.adapters.m01_facts_bridge import M01FactsBridge

app = typer.Typer(help="Ven Ho Research OS")


@app.command("notebook-inbox")
def notebook_inbox(topic: str, question: str, source: list[str] = typer.Option([])) -> None:
    folder = NotebookLMHandoff().create_inbox(topic, question, list(source))
    typer.echo(str(folder))


@app.command("stale")
def stale(project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
    expired = detect_stale_facts(project=project, data_root=data_root)
    typer.echo(f"expired_facts={len(expired)}")


@app.command("promote")
def promote(
    note_path: Path = typer.Option(..., "--note-path"),
    fact_key: str = typer.Option(..., "--fact-key"),
    value: str = typer.Option(..., "--value"),
    value_type: str = typer.Option("string", "--value-type"),
    approved_by: str = typer.Option(..., "--approved-by"),
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
) -> None:
    frontmatter = VaultReader(Path("research")).read_frontmatter(note_path)
    note = ResearchNote.model_validate(frontmatter)
    fact = propose_fact(note, fact_key=fact_key, value=value, value_type=value_type, approved_by=approved_by)
    path = M01FactsBridge(project=project, data_root=data_root).save_approved_fact(fact)
    typer.echo(str(path))


if __name__ == "__main__":
    app()
