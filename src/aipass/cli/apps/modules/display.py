"""CLI Display - Minimal stub for AIPass public repo."""
from rich.console import Console

console = Console()


def header(title: str, details: dict | None = None) -> None:
    """Display a bordered header."""
    console.print(f"\n[bold cyan]{'─' * 40}[/bold cyan]")
    console.print(f"[bold white]{title}[/bold white]")
    if details:
        for k, v in details.items():
            console.print(f"  {k}: {v}")
    console.print(f"[bold cyan]{'─' * 40}[/bold cyan]\n")


def success(message: str, **kwargs) -> None:
    """Display success message."""
    console.print(f"[green]✓[/green] {message}")


def error(message: str, suggestion: str | None = None) -> None:
    """Display error message."""
    console.print(f"[red]✗[/red] {message}")
    if suggestion:
        console.print(f"  [dim]{suggestion}[/dim]")


def warning(message: str, details: str | None = None) -> None:
    """Display warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")
    if details:
        console.print(f"  [dim]{details}[/dim]")


def section(title: str) -> None:
    """Display section title."""
    console.print(f"\n[bold]{title}[/bold]")
