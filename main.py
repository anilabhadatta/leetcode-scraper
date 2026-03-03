#!/usr/bin/env python3
"""LeetCode Scraper – main entry point."""

import argparse
import logging
import os
import sys

# Make sure the project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scraper.config as cfg


def _setup_logging() -> None:
    """Configure root logger to render through Rich so logs are visible in the TUI."""
    from rich.logging import RichHandler
    from rich.console import Console

    try:
        config = cfg.load_config()
        level = logging.INFO if config.verbose_logging else logging.WARNING
    except Exception:
        level = logging.WARNING

    handler = RichHandler(
        console=Console(stderr=True),
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        markup=False,
    )
    handler.setLevel(level)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LeetCode Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py\n"
            "  python main.py --non-stop\n"
            "  python main.py --proxy user:pass@1.2.3.4:8080\n"
            "  python main.py --config 1\n"
            "  python main.py --run 14 --slug two-sum\n"
        ),
    )
    parser.add_argument(
        "--non-stop",
        action="store_true",
        help="Retry automatically on errors without prompting",
    )
    parser.add_argument(
        "--proxy",
        type=str,
        help="Rotating or static proxy: username:password@ip:port",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Config slot to use (default: 0)",
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        help=(
            "Run a single menu action non-interactively and exit. "
            "Use the menu number (e.g. 14). "
            "Combine with --slug for single-URL actions."
        ),
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="URL or slug for single-scrape actions (--run 14/15/16)",
    )
    args = parser.parse_args()

    # ── Apply proxy ──────────────────────────────────────────────────────────
    if args.proxy:
        import requests
        proxy_url = f"http://{args.proxy}"
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        try:
            ip = requests.get("https://httpbin.org/ip", timeout=10).json()
            print(f"Proxy active — outbound IP: {ip.get('origin', '?')}")
        except Exception as e:
            print(f"Proxy set (could not verify IP: {e})")

    # ── Config slot ──────────────────────────────────────────────────────────
    if args.config:
        cfg.selected_config = args.config

    # ── Logging (reads verbose_logging from config) ──────────────────────────
    _setup_logging()

    # ── Non-interactive single-run mode ──────────────────────────────────────
    if args.run:
        _run_single(args.run, args.slug, args.non_stop)
        return

    # ── Interactive Rich TUI ─────────────────────────────────────────────────
    from ui.menu import run_menu
    run_menu(non_stop=args.non_stop)


def _run_single(action: str, slug: str | None, non_stop: bool) -> None:
    """Execute a single action headlessly, then exit."""
    from ui.menu import dispatch, console
    from rich.prompt import Prompt

    # For actions that need a slug/URL, patch stdin-based prompts
    single_url_actions = {"14", "15", "16"}
    if action in single_url_actions:
        if not slug:
            print(f"Action {action} requires --slug <url-or-slug>")
            sys.exit(1)
        # Monkey-patch so dispatch's Prompt.ask returns the cli value
        import unittest.mock as mock
        with mock.patch("rich.prompt.Prompt.ask", return_value=slug):
            try:
                dispatch(action)
            except Exception as exc:
                console.print(f"[red]Error:[/red] {exc}")
                if not non_stop:
                    sys.exit(1)
    else:
        try:
            dispatch(action)
        except Exception as exc:
            print(f"Error: {exc}")
            if not non_stop:
                sys.exit(1)


if __name__ == "__main__":
    main()
