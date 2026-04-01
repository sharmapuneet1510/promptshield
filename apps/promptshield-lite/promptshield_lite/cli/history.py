"""
history CLI command - browse and manage local precheck history.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

console = Console()

app = typer.Typer(help="Browse and manage local precheck history.")


@app.command("list")
def history_list(
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum number of records to show."),
    ] = 20,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """List recent precheck history records."""
    from promptshield_lite.engine.local_store import LocalStore
    from promptshield_lite.output.formatter import format_history_table

    store = LocalStore()
    records = store.list(limit=limit)

    if not records:
        console.print("[dim]No history records found.[/dim]")
        return

    if json_output:
        import json
        console.print(json.dumps(records, indent=2, default=str))
        return

    table = format_history_table(records)
    console.print(table)
    console.print(f"\n[dim]Showing {len(records)} of most recent records.[/dim]")


@app.command("stats")
def history_stats(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Show aggregate usage statistics from local history."""
    from promptshield_lite.engine.local_store import LocalStore
    from promptshield_lite.output.formatter import format_stats

    store = LocalStore()
    stats = store.stats()

    if not stats["total_requests"]:
        console.print("[dim]No history records found.[/dim]")
        return

    if json_output:
        import json
        console.print(json.dumps(stats, indent=2))
        return

    table = format_stats(stats)
    console.print(table)


@app.command("clear")
def history_clear(
    confirm: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Clear all local history records."""
    from promptshield_lite.engine.local_store import LocalStore

    if not confirm:
        typer.confirm("Are you sure you want to clear all history?", abort=True)

    store = LocalStore()
    count = store.clear()
    console.print(f"[green]Cleared {count} history record(s).[/green]")
