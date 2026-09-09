from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from research_engine.local_beat.scanner import JsonSearchProvider, load_watchlist, scan_week
from research_engine.local_beat.timeline_store import TimelineStore

app = typer.Typer(help="Ven Ho Local Beat Monitor")


@app.command("scan")
def scan_cmd(
    week: str = typer.Option(..., "--week", help="ISO week, e.g. 2026-W37."),
    input_file: Path = typer.Option(..., "--input-file", help="Operator/research export JSON; no live API is called."),
    watchlist: Optional[Path] = typer.Option(None, "--watchlist"),
    data_root: Path = typer.Option(Path("data/local_beat"), "--data-root"),
    vault_root: Path = typer.Option(Path("vault"), "--vault-root"),
) -> None:
    items = scan_week(
        week,
        provider=JsonSearchProvider(input_file),
        watchlist_path=watchlist,
        store=TimelineStore(data_root),
        vault_root=vault_root,
    )
    typer.echo(json.dumps({"week": week, "new_items": [item.to_dict() for item in items]}, ensure_ascii=False, indent=2))


@app.command("watchlist")
def watchlist_cmd() -> None:
    """Print the bounded entity count; useful for an offline preflight."""
    typer.echo(json.dumps({"entities": len(load_watchlist())}, ensure_ascii=False))


if __name__ == "__main__":
    app()
