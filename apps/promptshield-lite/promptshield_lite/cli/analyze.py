"""
analyze CLI command - detailed prompt analysis without policy enforcement.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(help="Analyze a prompt in detail without policy enforcement.")


@app.callback(invoke_without_command=True)
def analyze_cmd(
    ctx: typer.Context,
    prompt: Annotated[
        Optional[str],
        typer.Argument(help="Prompt text to analyze. Use '-' for stdin."),
    ] = None,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Target model identifier."),
    ] = "gpt-4o",
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Read prompt from file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON."),
    ] = False,
) -> None:
    """
    Analyze a prompt and show detailed breakdown: token counts, cost estimate,
    classifications, and what policies would trigger — without enforcing them.
    """
    # Resolve prompt
    prompt_text = _resolve_prompt(prompt, file)
    if not prompt_text:
        err_console.print("[red]Error:[/red] No prompt provided.")
        raise typer.Exit(1)

    from promptshield_config.loader import ConfigLoader
    from promptshield_core.classifier import classify_prompt, get_primary_category
    from promptshield_core.cost_estimator import estimate_cost
    from promptshield_core.token_estimator import estimate_output_tokens, estimate_tokens

    loader = ConfigLoader()
    full_config = loader.load_all()
    pricing_table = full_config.providers.get_pricing_table()

    input_tokens = estimate_tokens(prompt_text, model)
    classifications = classify_prompt(prompt_text, input_tokens)
    primary = get_primary_category(classifications)
    output_tokens = estimate_output_tokens(input_tokens, primary.value)
    cost = estimate_cost(model, input_tokens, output_tokens, pricing_table)

    if json_output:
        import json
        result = {
            "model": model,
            "prompt_length_chars": len(prompt_text),
            "input_tokens": input_tokens,
            "output_tokens_estimated": output_tokens,
            "total_tokens_estimated": input_tokens + output_tokens,
            "cost_usd": cost,
            "classifications": [c.value for c in classifications],
            "primary_category": primary.value,
        }
        console.print(json.dumps(result, indent=2))
        return

    # Rich formatted output
    table = Table(title=f"Prompt Analysis — {model}", box=box.ROUNDED)
    table.add_column("Property", style="cyan", width=28)
    table.add_column("Value", style="bold")

    table.add_row("Prompt length (chars)", str(len(prompt_text)))
    table.add_row("Estimated input tokens", str(input_tokens))
    table.add_row("Estimated output tokens", str(output_tokens))
    table.add_row("Total tokens (est.)", str(input_tokens + output_tokens))

    cost_str = f"${cost:.6f}" if cost < 0.01 else f"${cost:.4f}"
    table.add_row("Estimated cost (USD)", cost_str)

    cats = [c.value for c in classifications]
    table.add_row("Classifications", ", ".join(cats))
    table.add_row("Primary category", primary.value)

    # Show which policies would trigger
    thresholds = full_config.thresholds
    routing = full_config.routing

    would_trigger = []
    if input_tokens > thresholds.max_input_tokens:
        would_trigger.append(f"oversized_prompt ({input_tokens} > {thresholds.max_input_tokens})")
    if cost > thresholds.max_cost_usd:
        would_trigger.append(f"cost_threshold (${cost:.4f} > ${thresholds.max_cost_usd:.2f})")
    if any(c.value == "search_like" for c in classifications) and routing.warn_on_search_like:
        would_trigger.append("search_like_prompt")

    if would_trigger:
        table.add_row("Would trigger rules", "\n".join(would_trigger))
    else:
        table.add_row("Would trigger rules", "[green]none[/green]")

    console.print(table)

    # Show prompt preview
    preview = prompt_text[:300].replace("\n", " ")
    if len(prompt_text) > 300:
        preview += "..."
    console.print(f"\n[dim]Prompt preview:[/dim] {preview}")


def _resolve_prompt(prompt: str | None, file: Path | None) -> str:
    if file is not None:
        if not file.exists():
            err_console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)
        return file.read_text(encoding="utf-8").strip()

    if prompt == "-" or (prompt is None and not sys.stdin.isatty()):
        return sys.stdin.read().strip()

    return (prompt or "").strip()
