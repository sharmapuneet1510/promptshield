"""
precheck CLI command - run the PromptShield precheck engine on a prompt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(help="Run a precheck on a prompt.")


@app.callback(invoke_without_command=True)
def precheck_cmd(
    ctx: typer.Context,
    prompt: Annotated[
        Optional[str],
        typer.Argument(help="Prompt text to check. Use '-' to read from stdin."),
    ] = None,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Target model identifier."),
    ] = "gpt-4o",
    user: Annotated[
        str,
        typer.Option("--user", "-u", help="User identifier."),
    ] = "local-user",
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Read prompt from file."),
    ] = None,
    config_dir: Annotated[
        Optional[Path],
        typer.Option("--config-dir", help="Custom config directory."),
    ] = None,
    no_save: Annotated[
        bool,
        typer.Option("--no-save", help="Do not save result to local history."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output result as JSON."),
    ] = False,
) -> None:
    """
    Run the PromptShield precheck engine on a prompt and display the result.

    Examples:

        promptshield precheck "What is the capital of France?"

        promptshield precheck --model gpt-4o --file my_prompt.txt

        echo "explain quantum computing" | promptshield precheck -
    """
    # Resolve prompt text
    prompt_text = _resolve_prompt(prompt, file)
    if not prompt_text:
        err_console.print("[red]Error:[/red] No prompt provided. Use an argument, --file, or pipe via stdin.")
        raise typer.Exit(1)

    # Load config and run engine
    from promptshield_config.loader import ConfigLoader
    from promptshield_core.contracts.request import PromptRequest
    from promptshield_core.precheck_engine import PreCheckEngine

    loader = ConfigLoader(config_dir=config_dir)
    full_config = loader.load_all()

    engine = PreCheckEngine.from_full_config(full_config)
    request = PromptRequest(
        prompt_text=prompt_text,
        model=model,
        user_id=user,
        source="cli",
    )
    response = engine.run(request)

    if json_output:
        # Use sys.stdout directly — Rich's console.print() reflows long strings
        import sys
        sys.stdout.write(response.model_dump_json(indent=2) + "\n")
        sys.stdout.flush()
    else:
        from promptshield_lite.output.formatter import format_decision
        panel = format_decision(response)
        console.print(panel)

    # Save to local store
    if not no_save:
        try:
            from promptshield_core.utils.hashing import hash_prompt
            from promptshield_lite.engine.local_store import LocalStore
            store = LocalStore()
            store.save(response, user_id=user, model=model, source="cli", prompt_hash=hash_prompt(prompt_text))
        except Exception as e:
            err_console.print(f"[dim]Warning: Could not save history: {e}[/dim]")

    # Exit with non-zero code for BLOCK decisions when running in scripts
    decision_val = response.decision.value if hasattr(response.decision, "value") else str(response.decision)
    if decision_val == "BLOCK":
        raise typer.Exit(2)


def _resolve_prompt(prompt: str | None, file: Path | None) -> str:
    """Resolve prompt text from argument, file, or stdin."""
    if file is not None:
        if not file.exists():
            err_console = Console(stderr=True)
            err_console.print(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)
        return file.read_text(encoding="utf-8").strip()

    if prompt == "-" or (prompt is None and not sys.stdin.isatty()):
        return sys.stdin.read().strip()

    return (prompt or "").strip()
