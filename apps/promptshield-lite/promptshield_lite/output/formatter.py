"""
Rich-based output formatter for PromptShield Lite CLI.
"""

from __future__ import annotations

from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_DECISION_COLORS: dict[str, str] = {
    "ALLOW": "green",
    "WARN": "yellow",
    "BLOCK": "red",
    "REROUTE_WEBSEARCH": "cyan",
    "REROUTE_CHEAPER_MODEL": "blue",
    "REQUIRE_CONFIRMATION": "magenta",
}

_DECISION_ICONS: dict[str, str] = {
    "ALLOW": "✓",
    "WARN": "⚠",
    "BLOCK": "✗",
    "REROUTE_WEBSEARCH": "↗",
    "REROUTE_CHEAPER_MODEL": "↓",
    "REQUIRE_CONFIRMATION": "?",
}


def format_decision(response: Any) -> Panel:
    """
    Format a PromptDecisionResponse as a Rich Panel for terminal output.

    Args:
        response: A PromptDecisionResponse instance.

    Returns:
        A Rich Panel ready to be printed to the console.
    """
    decision_str = response.decision.value if hasattr(response.decision, "value") else str(response.decision)
    color = _DECISION_COLORS.get(decision_str, "white")
    icon = _DECISION_ICONS.get(decision_str, "•")

    # Build the main content table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="dim", width=22)
    table.add_column("Value")

    # Decision row with color
    decision_text = Text(f"{icon} {decision_str}", style=f"bold {color}")
    table.add_row("Decision", decision_text)

    # Token info
    table.add_row(
        "Input tokens",
        str(response.estimated_input_tokens),
    )
    table.add_row(
        "Output tokens (est.)",
        str(response.estimated_output_tokens),
    )
    table.add_row(
        "Total tokens (est.)",
        f"[bold]{response.estimated_total_tokens}[/bold]",
    )

    # Cost
    cost = response.estimated_cost_usd
    cost_str = f"${cost:.6f}" if cost < 0.01 else f"${cost:.4f}"
    table.add_row("Estimated cost", f"[bold]{cost_str}[/bold]")

    # Classifications
    cats = [c.value if hasattr(c, "value") else str(c) for c in response.classifications]
    table.add_row("Classifications", ", ".join(cats) if cats else "none")

    # Suggested route
    route = response.suggested_route.value if hasattr(response.suggested_route, "value") else str(response.suggested_route)
    table.add_row("Suggested route", route)

    # Misuse score
    score = response.misuse_score
    score_color = "green" if score < 0.3 else ("yellow" if score < 0.7 else "red")
    table.add_row("Misuse score", f"[{score_color}]{score:.2f}[/{score_color}]")

    # Policy rules triggered
    if response.policy_rules_triggered:
        rules = ", ".join(response.policy_rules_triggered)
        table.add_row("Rules triggered", f"[dim]{rules}[/dim]")

    # Messages
    messages_content = ""
    if response.messages:
        messages_content = "\n".join(f"  [dim]•[/dim] {m}" for m in response.messages)
        messages_content = "\n\n[bold]Messages:[/bold]\n" + messages_content

    panel_content = table
    title = f"[bold {color}]PromptShield Decision[/bold {color}]"

    if messages_content:
        from rich.columns import Columns
        from rich.console import Group

        messages_text = Text.from_markup(messages_content)
        panel_content = Group(table, messages_text)  # type: ignore[arg-type]

    return Panel(
        panel_content,  # type: ignore[arg-type]
        title=title,
        border_style=color,
        box=box.ROUNDED,
    )


def format_stats(stats: dict[str, Any]) -> Table:
    """
    Format local history statistics as a Rich Table.

    Args:
        stats: Dict returned by LocalStore.stats().

    Returns:
        A Rich Table ready to be printed.
    """
    table = Table(title="PromptShield Lite - Usage Statistics", box=box.ROUNDED)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="bold")

    table.add_row("Total Requests", str(stats.get("total_requests", 0)))
    table.add_row("Total Tokens", f"{stats.get('total_tokens', 0):,}")
    table.add_row("Total Cost", f"${stats.get('total_cost_usd', 0):.4f}")

    decision_counts = stats.get("decision_counts", {})
    for decision, count in decision_counts.items():
        color = _DECISION_COLORS.get(decision, "white")
        table.add_row(f"  {decision}", f"[{color}]{count}[/{color}]")

    return table


def format_history_table(records: list[dict[str, Any]]) -> Table:
    """
    Format a list of history records as a Rich Table.

    Args:
        records: List of record dicts from LocalStore.list().

    Returns:
        A Rich Table.
    """
    table = Table(title="PromptShield Lite - Recent History", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Time", width=19)
    table.add_column("Model", width=16)
    table.add_column("Tokens", justify="right", width=8)
    table.add_column("Cost", justify="right", width=10)
    table.add_column("Decision", width=22)
    table.add_column("Category", width=14)

    for i, record in enumerate(records, 1):
        decision = record.get("decision", "UNKNOWN")
        color = _DECISION_COLORS.get(decision, "white")
        icon = _DECISION_ICONS.get(decision, "•")

        # Format timestamp
        ts_raw = record.get("timestamp", "")
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(ts_raw).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts = ts_raw[:19] if ts_raw else "-"

        cats = record.get("classifications", [])
        category = cats[0] if cats else "-"

        tokens = (record.get("input_tokens", 0) or 0) + (record.get("output_tokens", 0) or 0)
        cost = record.get("cost_usd", 0.0) or 0.0

        table.add_row(
            str(i),
            ts,
            record.get("model", "-"),
            f"{tokens:,}",
            f"${cost:.4f}",
            f"[{color}]{icon} {decision}[/{color}]",
            category,
        )

    return table
