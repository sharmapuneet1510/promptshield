"""
PromptShield Lite - CLI entry point.

Usage:
    promptshield precheck "your prompt here"
    promptshield precheck --model gpt-4o --file prompt.txt
    promptshield analyze "what is quantum computing?"
    promptshield history list
    promptshield history stats
    promptshield config show
"""

from __future__ import annotations

import typer
from rich.console import Console

from promptshield_lite import __version__
from promptshield_lite.cli.analyze import app as analyze_app
from promptshield_lite.cli.config_cmd import app as config_app
from promptshield_lite.cli.history import app as history_app
from promptshield_lite.cli.precheck import app as precheck_app

console = Console()

app = typer.Typer(
    name="promptshield",
    help="PromptShield Lite - local prompt governance and cost awareness CLI.",
    add_completion=True,
    rich_markup_mode="rich",
)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"PromptShield Lite [bold]{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """
    [bold]PromptShield Lite[/bold] - prompt governance and cost awareness for AI developers.

    Check prompts before sending them to LLMs to catch oversized requests,
    wasteful queries, and policy violations locally.

    [dim]Run 'promptshield COMMAND --help' for command-specific help.[/dim]
    """


# Register sub-commands
app.add_typer(precheck_app, name="precheck")
app.add_typer(analyze_app, name="analyze")
app.add_typer(history_app, name="history")
app.add_typer(config_app, name="config")


if __name__ == "__main__":
    app()
