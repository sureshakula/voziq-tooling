# =================== AIPass ====================
# Name: search.py
# Description: Search Orchestration Module
# Version: 0.4.0
# Created: 2025-11-27
# Modified: 2026-03-08
# =============================================

"""
Search Orchestration Module

Coordinates semantic search workflow by calling handlers in sequence:
1. Encode query text to embedding (vector/embedder)
2. Search Chroma collections (storage/chroma via subprocess)
3. Format and display results (Rich panels)

Purpose:
    Thin orchestration layer - no business logic implementation.
    All domain logic lives in handlers.
"""

import sys
from typing import List

from rich.panel import Panel
from rich import box

from aipass.prax import logger
from aipass.cli.apps.modules import console

# =============================================================================
# INFRASTRUCTURE SETUP
# =============================================================================

# Handler imports
from aipass.memory.apps.handlers.search.query_executor import (
    execute_search as _handler_execute_search,
)


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

def handle_command(command: str, args: List[str]) -> bool:
    """
    Handle search commands

    Commands supported:
    - search <query>: Execute semantic search across all branches
    - help: Show search help

    Args:
        command: Command name
        args: Additional arguments (query text, options)

    Returns:
        True if command handled, False otherwise
    """
    if command in ('--help', '-h', 'help'):
        print_help()
        return True

    if command == 'search':
        if not args:
            console.print("[red]Error:[/red] Search query required")
            console.print("Usage: search <query> [--branch BRANCH] [--type TYPE] [--n N]")
            return True

        # Parse arguments
        query_parts = []
        branch = None
        memory_type = None
        n_results = 5

        i = 0
        while i < len(args):
            if args[i] == '--branch' and i + 1 < len(args):
                branch = args[i + 1]
                i += 2
            elif args[i] == '--type' and i + 1 < len(args):
                memory_type = args[i + 1]
                i += 2
            elif args[i] == '--n' and i + 1 < len(args):
                try:
                    n_results = int(args[i + 1])
                except ValueError:
                    console.print(f"[red]Error:[/red] Invalid number: {args[i + 1]}")
                    return True
                i += 2
            else:
                query_parts.append(args[i])
                i += 1

        query = ' '.join(query_parts)
        if not query:
            console.print("[red]Error:[/red] Search query required")
            return True

        show_search_results(query, branch=branch, memory_type=memory_type, n_results=n_results)
        return True

    return False


def print_help() -> None:
    """Display search module help"""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Search Module - Semantic Memory Search[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()
    console.print("[bold]USAGE:[/bold]")
    console.print("  python3 -m aipass.memory.apps.modules.search search <query> [options]")
    console.print()
    console.print("[bold]COMMANDS:[/bold]")
    console.print("  [cyan]search <query>[/cyan]     Search across all memory collections")
    console.print("  [cyan]help[/cyan]                Show this help message")
    console.print()
    console.print("[bold]OPTIONS:[/bold]")
    console.print("  [cyan]--branch BRANCH[/cyan]    Filter by branch (e.g., SEED, CLI)")
    console.print("  [cyan]--type TYPE[/cyan]        Filter by memory type (observations, local)")
    console.print("  [cyan]--n N[/cyan]              Number of results (default: 5)")
    console.print()
    console.print("[bold]EXAMPLES:[/bold]")
    console.print("  # Search all branches")
    console.print("  [dim]drone @memory search \"error handling patterns\"[/dim]")
    console.print()
    console.print("  # Search specific branch")
    console.print("  [dim]drone @memory search \"registry bugs\" --branch SEED[/dim]")
    console.print()
    console.print("  # Search specific memory type")
    console.print("  [dim]drone @memory search \"collaboration\" --type observations --n 10[/dim]")
    console.print()
    console.print("[bold]HOW IT WORKS:[/bold]")
    console.print("  1. Convert query to 384-dim embedding (all-MiniLM-L6-v2)")
    console.print("  2. Search ChromaDB collections for similar vectors")
    console.print("  3. Display top N most relevant memories")
    console.print()


# =============================================================================
# SEARCH RESULTS DISPLAY
# =============================================================================

def show_search_results(
    query: str,
    branch: str | None = None,
    memory_type: str | None = None,
    n_results: int = 5
) -> bool:
    """
    Execute semantic search via handler and display results with Rich.

    Args:
        query: Search query text
        branch: Optional branch filter
        memory_type: Optional memory type filter
        n_results: Number of results to return

    Returns:
        True if search successful, False otherwise
    """
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Memory - Semantic Search[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()

    # Display query info
    console.print(f"[cyan]Query:[/cyan] {query}")
    if branch:
        console.print(f"[cyan]Branch:[/cyan] {branch}")
    if memory_type:
        console.print(f"[cyan]Type:[/cyan] {memory_type}")
    console.print()

    console.print("[dim]Encoding query...[/dim]")
    console.print("[dim]Searching collections...[/dim]")

    # Delegate to handler
    result = _handler_execute_search(
        query=query,
        branch=branch,
        memory_type=memory_type,
        n_results=n_results
    )

    if not result['success']:
        console.print(f"[red]x[/red] {result.get('error', 'Unknown error')}")
        return False

    collections_searched = result.get('collections_searched', 0)
    total_results = result.get('total_results', 0)
    filtered_results = result.get('results', [])

    # Display summary
    console.print(f"[green]>[/green] Found {total_results} results in {collections_searched} collections")
    console.print()

    if not filtered_results and total_results == 0:
        console.print("[yellow]No matching memories found[/yellow]")
        console.print()
        console.print("[dim]Try:[/dim]")
        console.print("  * Different search terms")
        console.print("  * Broader query without filters")
        console.print("  * Check if memories have been rolled over (drone @memory status)")
        return True

    if not filtered_results:
        console.print("[yellow]No relevant memories found[/yellow]")
        console.print()
        console.print("[dim]The search found some results but none were relevant enough (>40% similarity).[/dim]")
        console.print("[dim]Try more specific search terms related to your AIPass work.[/dim]")
        return True

    for i, item in enumerate(filtered_results, 1):
        collection = item.get('collection', 'unknown')
        document = item.get('document', '')
        metadata = item.get('metadata', {})
        similarity = item.get('similarity', 0)

        # Parse collection name
        parts = collection.split('_')
        branch_name = parts[0].upper() if parts else 'UNKNOWN'
        mem_type = parts[1] if len(parts) > 1 else 'unknown'

        # Build metadata display
        meta_lines = []
        if 'timestamp' in metadata:
            meta_lines.append(f"[dim]Time:[/dim] {metadata['timestamp']}")
        if 'source' in metadata:
            meta_lines.append(f"[dim]Source:[/dim] {metadata['source']}")

        meta_text = " | ".join(meta_lines) if meta_lines else ""

        # Create panel for each result
        panel_title = f"Result {i} - {branch_name} ({mem_type}) - Similarity: {similarity:.2%}"

        panel_content = document
        if meta_text:
            panel_content += f"\n\n{meta_text}"

        console.print(Panel(
            panel_content,
            title=panel_title,
            title_align="left",
            border_style="cyan" if similarity > 0.7 else "blue" if similarity > 0.5 else "dim"
        ))

    console.print()
    return True


# =============================================================================
# INTROSPECTION
# =============================================================================

def print_introspection():
    """Display module introspection info."""
    console.print()
    console.print("search Module")
    console.print("Orchestrates semantic search across memory collections via vector embeddings and ChromaDB")
    console.print()
    console.print("Connected Handlers:")
    console.print("  handlers/search/")
    console.print("    - query_executor.py (execute_search — encode query, search collections, filter results by similarity)")
    console.print()


# =============================================================================
# STANDALONE EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Handle --help before argparse (module standard)
    if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h', 'help'):
        handle_command('help', [])
        sys.exit(0)

    # Execute command via handle_command
    command = sys.argv[1]
    if not handle_command(command, sys.argv[2:]):
        console.print(f"[red]Unknown command:[/red] {command}")
        console.print("Run with [cyan]help[/cyan] for available commands")
        sys.exit(1)
