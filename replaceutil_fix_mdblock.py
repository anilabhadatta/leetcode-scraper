"""fix_mdblock.py — Replace <md-block> custom elements with <div> in all scraped HTML files.

The old pipeline used md-block.js which re-renders its inner content as markdown
client-side.  This causes LaTeX math to be mangled (e.g. $*(1 * *)_2$*$ →
italic/bold noise) because markdown processes * and _ inside math expressions.

This script converts every <md-block class="..."> ... </md-block> to a plain
<div class="..."> ... </div> so the content is rendered as-is by the browser
and MathJax can typeset it correctly.

Usage:
    python fix_mdblock.py              # fix questions/ dir from configured save_path
    python fix_mdblock.py --all        # also fix cards/
    python fix_mdblock.py --dir PATH   # fix a specific directory tree
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core fix
# ---------------------------------------------------------------------------

# Match opening <md-block ...> and closing </md-block> tags
_OPEN_RE  = re.compile(r'<md-block\b([^>]*)>', re.IGNORECASE)
_CLOSE_RE = re.compile(r'</md-block\s*>', re.IGNORECASE)


def fix_html_file(path: str) -> bool:
    """Replace all <md-block> tags with <div> in-place.

    Returns True if the file was modified.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        original = f.read()

    if "<md-block" not in original.lower():
        return False  # nothing to do

    fixed = _OPEN_RE.sub(r'<div\1>', original)
    fixed = _CLOSE_RE.sub(r'</div>', fixed)

    if fixed == original:
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(fixed)
    return True


def fix_directory(dirpath: str) -> tuple[int, int]:
    """Recursively fix all .html files under dirpath.

    Returns (fixed_count, total_count).
    """
    fixed = 0
    total = 0
    for root, _dirs, files in os.walk(dirpath):
        for fname in files:
            if not fname.endswith(".html"):
                continue
            total += 1
            fpath = os.path.join(root, fname)
            try:
                changed = fix_html_file(fpath)
                if changed:
                    fixed += 1
                    log.info("Fixed: %s", os.path.relpath(fpath, dirpath))
                else:
                    log.debug("Skip:  %s", os.path.relpath(fpath, dirpath))
            except Exception as exc:
                log.warning("Error processing %s: %s", fpath, exc)
    return fixed, total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Also fix cards/ directory in addition to questions/.",
    )
    parser.add_argument(
        "--dir", metavar="PATH",
        help="Fix a specific directory tree instead of the configured save_path.",
    )
    args = parser.parse_args()

    if args.dir:
        dirs = [args.dir]
    else:
        # Load configured save_path
        try:
            from scraper.config import load_config, select_config_interactive
            select_config_interactive()
            config = load_config()
            save_path = config["save_path"]
        except Exception as exc:
            log.error("Could not load config: %s", exc)
            sys.exit(1)

        dirs = [os.path.join(save_path, "questions")]
        if args.all:
            dirs.append(os.path.join(save_path, "cards"))
            dirs.append(os.path.join(save_path, "card"))

    total_fixed = total_scanned = 0
    for d in dirs:
        if not os.path.isdir(d):
            log.warning("Directory not found, skipping: %s", d)
            continue
        log.info("Scanning: %s", d)
        f, t = fix_directory(d)
        log.info("  → fixed %d / %d files", f, t)
        total_fixed   += f
        total_scanned += t

    log.info("Done — fixed %d / %d HTML files total", total_fixed, total_scanned)


if __name__ == "__main__":
    main()
