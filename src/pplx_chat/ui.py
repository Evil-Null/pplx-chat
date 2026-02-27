from rich.console import Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.spinner import Spinner

from . import __version__
from .models import APIResponse
from .config import MODELS


class UIRenderer:
    """All Rich rendering in one place. No business logic."""

    def render_welcome(self) -> Panel:
        """Welcome banner on startup."""
        content = Text()
        content.append("PPLX Chat", style="bold cyan")
        content.append(f" v{__version__}\n", style="dim")
        content.append("Perplexity AI Terminal Client\n", style="dim")
        content.append("by ", style="dim")
        content.append("Evil Null", style="bold magenta")
        content.append("\n", style="dim")
        content.append("Type /help for commands", style="dim italic")
        return Panel(content, border_style="cyan", padding=(1, 2))

    def render_model_selector(self) -> Table:
        """Model selection table."""
        table = Table(
            title="Select Model",
            border_style="cyan",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", style="bold yellow", width=3)
        table.add_column("Model", style="bold green", width=24)
        table.add_column("Description", style="dim")

        for i, (key, info) in enumerate(MODELS.items(), 1):
            table.add_row(str(i), key, info["description"])

        return table

    def render_thinking(self, model: str) -> Panel:
        """Spinner panel while waiting for first token."""
        spinner = Spinner("dots", text=Text(f" {model} is searching...", style="cyan"))
        return Panel(spinner, border_style="blue", title=f"[bold blue]{model}[/bold blue]")

    def render_streaming(self, text: str, model: str) -> Panel:
        """Live-updating panel during streaming."""
        return Panel(
            Markdown(text) if text.strip() else Text("..."),
            border_style="blue",
            title=f"[bold blue]{model}[/bold blue]",
            subtitle="[dim]streaming...[/dim]",
        )

    def render_response(
        self, response: APIResponse, model: str,
        show_citations: bool = True, show_related: bool = True,
    ) -> Panel:
        """Final response panel with all metadata."""
        parts = []

        # Main content as markdown
        parts.append(Markdown(response.content))

        # Citations
        if show_citations and response.citations:
            parts.append(Text())
            parts.append(Rule("Sources", style="dim"))
            for i, url in enumerate(response.citations, 1):
                parts.append(Text(f"  [{i}] {url}", style="dim cyan"))

        # Related questions
        if show_related and response.related_questions:
            parts.append(Text())
            parts.append(Rule("Related", style="dim"))
            for q in response.related_questions:
                parts.append(Text(f"  > {q}", style="dim italic"))

        # Cost line
        subtitle = self._format_cost_subtitle(response)

        return Panel(
            Group(*parts),
            border_style="blue",
            title=f"[bold blue]{model}[/bold blue]",
            subtitle=subtitle,
        )

    def _format_cost_subtitle(self, response: APIResponse) -> str:
        cost = response.cost.total_cost
        tokens = response.usage.total_tokens
        parts = []
        if tokens:
            parts.append(f"{tokens:,} tokens")
        if cost:
            parts.append(f"${cost:.6f}")
        return f"[dim]{' | '.join(parts)}[/dim]" if parts else ""

    def render_session_list(self, sessions: list[dict]) -> Table:
        """Session list table."""
        table = Table(
            title="Saved Sessions",
            border_style="green",
            show_header=True,
            header_style="bold green",
        )
        table.add_column("ID", style="bold yellow", width=5)
        table.add_column("Name", style="bold", width=30)
        table.add_column("Model", style="cyan", width=20)
        table.add_column("Messages", justify="right", width=8)
        table.add_column("Cost", justify="right", width=10)
        table.add_column("Updated", style="dim", width=20)

        for s in sessions:
            name = s["name"] or f"Session #{s['id']}"
            cost = f"${s['total_cost']:.4f}" if s["total_cost"] else "-"
            table.add_row(
                str(s["id"]),
                name,
                s["model"],
                str(s["msg_count"]),
                cost,
                s["updated_at"][:19],
            )

        return table

    def render_session_cost(self, total_cost: float, total_tokens: int) -> Text:
        """Session cost summary line."""
        text = Text()
        text.append("  Session: ", style="dim")
        text.append(f"${total_cost:.6f}", style="bold yellow")
        text.append(f" | {total_tokens:,} tokens", style="dim")
        return text

    def render_error(self, message: str) -> Panel:
        return Panel(
            Text(message, style="bold red"),
            border_style="red",
            title="[bold red]Error[/bold red]",
        )

    def render_help(self, commands: dict) -> Table:
        """Command help table."""
        table = Table(
            title="Commands",
            border_style="cyan",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Command", style="bold green", width=30)
        table.add_column("Description")

        for cmd, desc in commands.items():
            table.add_row(cmd, desc)

        return table
