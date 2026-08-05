from __future__ import annotations

from pathlib import Path
from typing import List

import typer
import yaml

from research_engine.adapters.notebooklm_handoff import NotebookLMHandoff
from research_engine.adapters.vault_reader import VaultReader
from research_engine.application.collect_sources import collect_source_note, collect_structured_note
from research_engine.application.detect_stale_knowledge import detect_stale_facts
from research_engine.application.propose_fact import propose_fact
from research_engine.domain.research_note import ResearchNote
from research_engine.adapters.m01_facts_bridge import M01FactsBridge

app = typer.Typer(help="Ven Ho Research OS")


def _assert_known_domain(domain: str, *, config_root: Path) -> None:
    """Reject a domain name that isn't registered in domains.yaml -- without
    this, collect-source/collect-note would silently write into the vault
    under an ad-hoc directory name, invisible to any of the 9-domain
    reporting/cadence policy this whole subsystem exists to enforce."""
    domains = yaml.safe_load((config_root / "domains.yaml").read_text(encoding="utf-8"))["domains"]
    if domain not in domains:
        raise typer.BadParameter(f"'{domain}' is not a registered domain. Known domains: {sorted(domains)}")


@app.command("load-seed-facts")
def load_seed_facts(
    seed_file: Path = typer.Option(Path("config/projects/venho_hotel/growth/seed_facts.json"), "--seed-file"),
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
) -> None:
    """Persist already-founder-approved bootstrap facts (seed_facts.json) into FactStore.

    Not a promotion path -- seed_facts.json entries already carry
    `status: approved` + `approved_by` committed to git; this only writes
    them to the resolvable fact store so ClaimValidator can find them. New
    facts still must go through `promote` (real founder y/N gate).
    """
    paths = M01FactsBridge(project=project, data_root=data_root).store.load_seed_facts(seed_file)
    typer.echo(f"loaded {len(paths)} facts")
    for path in paths:
        typer.echo(str(path))


@app.command("notebook-inbox")
def notebook_inbox(topic: str, question: str, source: list[str] = typer.Option([])) -> None:
    folder = NotebookLMHandoff().create_inbox(topic, question, list(source))
    typer.echo(str(folder))


@app.command("stale")
def stale(project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
    expired = detect_stale_facts(project=project, data_root=data_root)
    typer.echo(f"expired_facts={len(expired)}")


@app.command("collect-source")
def collect_source_cmd(
    rs_id: str = typer.Option(..., "--rs-id"),
    domain: str = typer.Option(..., "--domain"),
    source_uri: str = typer.Option(..., "--source-uri"),
    title: str = typer.Option(..., "--title"),
    body_file: Path = typer.Option(..., "--body-file", help="Path to a text/markdown file with the raw source content."),
    vault_root: Path = typer.Option(Path("research"), "--vault-root"),
    config_root: Path = typer.Option(Path("config/projects/venho_hotel/research"), "--config-root"),
) -> None:
    """Ingest one raw source (R0, unverified) into the vault under one of
    the 9 registered domains (see domains.yaml). This is the entrypoint any
    of the 9 domains' collectors (manual research, Trend Radar, weather,
    guest review reading, etc.) should write through -- collect_source_note
    itself was already domain-agnostic, it just had no CLI in front of it."""
    _assert_known_domain(domain, config_root=config_root)
    path = collect_source_note(
        rs_id=rs_id, domain=domain, source_uri=source_uri, title=title,
        body=body_file.read_text(encoding="utf-8"), vault_root=vault_root,
    )
    typer.echo(str(path))


@app.command("collect-note")
def collect_note_cmd(
    rs_id: str = typer.Option(..., "--rs-id"),
    domain: str = typer.Option(..., "--domain"),
    source_uri: str = typer.Option(..., "--source-uri"),
    title: str = typer.Option(..., "--title"),
    observation: List[str] = typer.Option(..., "--observation", help="Repeatable -- one flag per observation line."),
    vault_root: Path = typer.Option(Path("research"), "--vault-root"),
    config_root: Path = typer.Option(Path("config/projects/venho_hotel/research"), "--config-root"),
) -> None:
    """Ingest a structured observation note (R1) into the vault under one of
    the 9 registered domains -- e.g. `--observation "Phòng có 12 phòng"
    --observation "Giá từ 400,000đ"`."""
    _assert_known_domain(domain, config_root=config_root)
    path = collect_structured_note(
        rs_id=rs_id, domain=domain, source_uri=source_uri, title=title,
        observations=observation, vault_root=vault_root,
    )
    typer.echo(str(path))


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
