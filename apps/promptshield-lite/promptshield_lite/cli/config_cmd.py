"""
config CLI command - inspect and validate PromptShield configuration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(help="View and validate PromptShield configuration.")


@app.command("show")
def config_show(
    config_dir: Annotated[
        Optional[Path],
        typer.Option("--config-dir", help="Custom config directory."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """Show the current effective configuration (defaults + overrides)."""
    from promptshield_config.loader import ConfigLoader

    loader = ConfigLoader(config_dir=config_dir)
    config = loader.load_all()

    if json_output:
        import json
        console.print(json.dumps(config.model_dump(), indent=2))
        return

    # Thresholds table
    t_table = Table(title="Thresholds", box=box.SIMPLE)
    t_table.add_column("Setting", style="cyan")
    t_table.add_column("Value", style="bold")
    t = config.thresholds
    t_table.add_row("max_input_tokens", str(t.max_input_tokens))
    t_table.add_row("max_cost_usd", f"${t.max_cost_usd:.2f}")
    t_table.add_row("max_daily_requests", str(t.max_daily_requests))
    t_table.add_row("max_daily_spend_usd", f"${t.max_daily_spend_usd:.2f}")
    t_table.add_row("warn_at_token_pct", f"{t.warn_at_token_pct:.0%}")
    t_table.add_row("warn_at_cost_pct", f"{t.warn_at_cost_pct:.0%}")
    console.print(t_table)

    # Routing table
    r_table = Table(title="Routing", box=box.SIMPLE)
    r_table.add_column("Setting", style="cyan")
    r_table.add_column("Value", style="bold")
    r = config.routing
    r_table.add_row("warn_on_search_like", str(r.warn_on_search_like))
    r_table.add_row("block_oversized", str(r.block_oversized))
    r_table.add_row("reroute_search_to_web", str(r.reroute_search_to_web))
    r_table.add_row("cheaper_model_fallback", r.cheaper_model_fallback or "none")
    r_table.add_row("local_model_fallback", r.local_model_fallback or "none")
    r_table.add_row("blocked_models", ", ".join(r.blocked_models) or "none")
    console.print(r_table)

    # Providers table
    p_table = Table(title="Model Pricing", box=box.SIMPLE)
    p_table.add_column("Model", style="cyan")
    p_table.add_column("Input/1K", justify="right")
    p_table.add_column("Output/1K", justify="right")
    for model_name, pricing in config.providers.models.items():
        p_table.add_row(
            model_name,
            f"${pricing.input_per_1k_usd:.5f}",
            f"${pricing.output_per_1k_usd:.5f}",
        )
    console.print(p_table)


@app.command("defaults")
def config_defaults() -> None:
    """Show the built-in default configuration."""
    from promptshield_config.loader import _DEFAULTS_DIR

    console.print(f"[cyan]Default config directory:[/cyan] {_DEFAULTS_DIR}")
    for yaml_file in sorted(_DEFAULTS_DIR.glob("*.yaml")):
        console.print(f"\n[bold]--- {yaml_file.name} ---[/bold]")
        console.print(yaml_file.read_text())


@app.command("validate")
def config_validate(
    config_dir: Annotated[
        Path,
        typer.Argument(help="Config directory to validate."),
    ],
) -> None:
    """Validate a config directory for correct structure and values."""
    from promptshield_config.loader import ConfigLoader

    console.print(f"Validating config directory: [cyan]{config_dir}[/cyan]")

    if not config_dir.exists():
        err_console.print(f"[red]Error:[/red] Directory does not exist: {config_dir}")
        raise typer.Exit(1)

    try:
        loader = ConfigLoader(config_dir=config_dir)
        config = loader.load_all()
        console.print("[green]✓ Configuration is valid[/green]")
        console.print(f"  Thresholds:  max_input={config.thresholds.max_input_tokens} tokens")
        console.print(f"  Routing:     {len(config.routing.blocked_models)} blocked models")
        console.print(f"  Providers:   {len(config.providers.models)} models in pricing table")
    except Exception as e:
        err_console.print(f"[red]✗ Configuration invalid:[/red] {e}")
        raise typer.Exit(1)
