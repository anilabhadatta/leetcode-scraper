"""Rich terminal UI for the LeetCode Scraper."""

from __future__ import annotations

import sys
from typing import Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

from scraper import config as cfg
from scraper.api import check_premium_status
from scraper.utils import clear
from scraper.html.assets import manual_convert_images_to_base64
from scraper.html.indexes import create_base_index_html


console = Console()

# ---------------------------------------------------------------------------
# Menu definition
# ---------------------------------------------------------------------------

MENU_GROUPS = [
    {
        "label": "⚙  Config",
        "color": "cyan",
        "items": [
            ("1", "Setup / edit config"),
            ("2", "Select config slot"),
        ],
    },
    {
        "label": "🔗  URL Fetching",
        "color": "blue",
        "items": [
            ("3", "Get all cards URLs"),
            ("4", "Get all question URLs"),
        ],
    },
    {
        "label": "📦  Bulk Scraping",
        "color": "green",
        "items": [
            ("5", "Scrape all cards"),
            ("6", "Scrape all questions"),
            ("7", "Scrape ALL company question indexes"),
            ("8", "Scrape ALL company questions"),
            ("9", "Scrape SELECTED company question indexes"),
            ("10", "Scrape SELECTED company questions"),
        ],
    },
    {
        "label": "🎯  Single-URL Scraping",
        "color": "yellow",
        "items": [
            ("14", "Scrape single question  (URL or slug)"),
            ("15", "Scrape single card      (URL or slug)"),
            ("16", "Scrape single company   (URL or slug)"),
        ],
    },
    {
        "label": "🛠  Tools",
        "color": "magenta",
        "items": [
            ("11", "Convert images to base64 (os.walk)"),
            ("12", "Create base index.html for http.server"),
        ],
    },
    {
        "label": "🔑  Account",
        "color": "red",
        "items": [
            ("13", "Check LeetCode Premium status"),
        ],
    },
]


def _build_menu_table(current_config: str) -> Table:
    table = Table(
        box=box.ROUNDED,
        show_header=False,
        padding=(0, 1),
        expand=False,
        border_style="bright_black",
    )
    table.add_column("Key", style="bold white", width=4)
    table.add_column("Description")

    for group in MENU_GROUPS:
        table.add_row(
            Text("", style=""),
            Text(f"  {group['label']}", style=f"bold {group['color']}"),
        )
        for key, desc in group["items"]:
            table.add_row(
                Text(f"[{key}]", style=f"bold {group['color']}"),
                Text(desc),
            )
    return table


def _header(current_config: str) -> Panel:
    slot = f"config_{current_config}.ini"
    return Panel(
        f"[bold yellow]LeetCode Scraper[/bold yellow]  "
        f"[dim]v2.0  ·  Built by Anilabha Datta[/dim]\n"
        f"[dim]Active config:[/dim] [bold cyan]{slot}[/bold cyan]",
        box=box.HEAVY_HEAD,
        border_style="yellow",
        expand=False,
    )


# ---------------------------------------------------------------------------
# Action dispatcher
# ---------------------------------------------------------------------------

def _run_with_spinner(label: str, fn: Callable) -> None:
    """Run *fn()* while displaying a spinner, then print any exception."""
    with console.status(f"[bold green]{label}…[/bold green]", spinner="dots"):
        fn()


def dispatch(choice: str) -> bool:
    """Execute the selected menu option.  Returns False if user wants to quit."""
    # lazy imports to keep startup fast
    from scraper.scrapers.questions import scrape_question_url, get_all_questions_url, scrape_single_question
    from scraper.scrapers.cards import scrape_card_url, get_all_cards_url, scrape_single_card
    from scraper.scrapers.companies import (
        scrape_all_company_questions, scrape_selected_company_questions, scrape_single_company
    )

    if choice == "1":
        cfg.generate_config()
    elif choice == "2":
        cfg.select_config_interactive()
    elif choice == "3":
        _run_with_spinner("Fetching all card URLs", get_all_cards_url)
    elif choice == "4":
        _run_with_spinner("Fetching all question URLs", get_all_questions_url)
    elif choice == "5":
        _run_with_spinner("Scraping all cards", scrape_card_url)
    elif choice == "6":
        _run_with_spinner("Scraping all questions", scrape_question_url)
    elif choice == "7":
        _run_with_spinner("Scraping all company indexes", lambda: scrape_all_company_questions("index"))
    elif choice == "8":
        _run_with_spinner("Scraping all company questions", lambda: scrape_all_company_questions("full"))
    elif choice == "9":
        _run_with_spinner("Scraping selected company indexes", lambda: scrape_selected_company_questions("index"))
    elif choice == "10":
        _run_with_spinner("Scraping selected company questions", lambda: scrape_selected_company_questions("full"))
    elif choice == "11":
        manual_convert_images_to_base64()
    elif choice == "12":
        create_base_index_html()
    elif choice == "13":
        _cmd_check_premium()
    elif choice == "14":
        url_or_slug = Prompt.ask("[yellow]Enter question URL or slug[/yellow]")
        _run_with_spinner(f"Scraping question: {url_or_slug}", lambda: scrape_single_question(url_or_slug))
    elif choice == "15":
        url_or_slug = Prompt.ask("[yellow]Enter card URL or slug[/yellow]")
        _run_with_spinner(f"Scraping card: {url_or_slug}", lambda: scrape_single_card(url_or_slug))
    elif choice == "16":
        url_or_slug = Prompt.ask("[yellow]Enter company URL or slug[/yellow]")
        _run_with_spinner(f"Scraping company: {url_or_slug}", lambda: scrape_single_company(url_or_slug))
    else:
        return False  # quit
    return True


def _cmd_check_premium() -> None:
    try:
        loaded = cfg.load_config()
        cookie = loaded["leetcode_cookie"]
    except Exception:
        cookie = ""
    try:
        status = check_premium_status(cookie)
        username = status.get("username", "Unknown")
        signed_in = status.get("isSignedIn", False)
        premium = status.get("isPremium", False)

        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Username", username)
        table.add_row("Signed In", "[green]Yes[/green]" if signed_in else "[red]No (cookie may be expired)[/red]")
        table.add_row("Premium", "[green]Yes ✓[/green]" if premium else "[red]No ✗[/red]")
        console.print(Panel(table, title="[bold]LeetCode Account Status[/bold]", border_style="cyan"))
        if not signed_in:
            console.print("[red]WARNING:[/red] Not signed in. Update your cookie (option 1).")
        elif not premium:
            console.print("[yellow]NOTE:[/yellow] Premium is required for some questions and company stats.")
    except Exception as e:
        console.print(f"[red]Error checking status:[/red] {e}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_menu(non_stop: bool = False, previous_choice: str = "0") -> None:
    choice = previous_choice if previous_choice != "0" else ""
    while True:
        clear()
        console.print(_header(cfg.selected_config))
        console.print(_build_menu_table(cfg.selected_config))
        console.print()

        if not choice:
            choice = Prompt.ask("[bold]Enter your choice[/bold]", default="q")
        try:
            if not dispatch(choice):
                console.print("\n[dim]Goodbye.[/dim]\n")
                sys.exit(0)
            if previous_choice != "0":
                break  # non-stop mode ran one action → done
            Prompt.ask("[dim]Press Enter to return to menu[/dim]", default="")
        except KeyboardInterrupt:
            if non_stop:
                console.print("[red]KeyboardInterrupt — exiting.[/red]")
                sys.exit(0)
        except Exception as exc:
            console.print(
                Panel(
                    f"[bold red]Error:[/bold red] {exc}\n\n"
                    "[dim]Possible causes:\n"
                    "  1. Check your internet connection\n"
                    "  2. LEETCODE_SESSION cookie may have expired\n"
                    "  3. Check your config (option 1)\n"
                    "  4. Too many requests — try again later or use a proxy\n"
                    "  5. LeetCode may have changed their API[/dim]",
                    title="[red]Something went wrong[/red]",
                    border_style="red",
                )
            )
            if non_stop:
                console.print("[yellow]Retrying…[/yellow]")
                previous_choice = choice
            else:
                Prompt.ask("[dim]Press Enter to continue[/dim]", default="")
        finally:
            choice = ""  # reset for next iteration
