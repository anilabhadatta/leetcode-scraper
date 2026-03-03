"""Filesystem and string utilities."""
from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path

import markdown2

log = logging.getLogger(__name__)


def clear() -> None:
    os.system("cls" if sys.platform.startswith("win") else "clear")


def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if absent; return Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_folder(path: str | Path) -> None:
    """Create folder then chdir into it (legacy behaviour)."""
    ensure_dir(path)
    os.chdir(path)


def safe_filename(name: str) -> str:
    """Strip characters illegal in file/folder names."""
    return re.sub(r'[:?|></\\]', lambda m: " ", name)


def copy_html(src: str | Path, dst: str | Path) -> None:
    shutil.copy(src, dst)


# Legacy alias kept for old callers
replace_filename = lambda m: " "  # noqa: E731


# ---------------------------------------------------------------------------
# Math-safe markdown renderer
# ---------------------------------------------------------------------------

# Matches (in order of precedence):
#   1. $$...$$  display math (may span multiple lines)
#   2. \[...\]  display math (may span multiple lines)
#   3. \(...\)  inline math
#   4. $...$    inline math (no newlines inside)
_MATH_RE = re.compile(
    r'(\$\$[\s\S]*?\$\$'        # $$ ... $$  (display)
    r'|\\\[[\s\S]*?\\\]'        # \[ ... \]  (display)
    r'|\\\([\s\S]*?\\\)'        # \( ... \)  (inline)
    r'|\$(?!\s)(?:[^\$\n]|\\\$)+?\$)',  # $ ... $  (inline, no blank space after $)
    re.DOTALL,
)


def render_markdown_safe(text: str) -> str:
    """Render markdown to HTML while protecting all LaTeX math expressions.

    Extracts every math block/span before markdown processing, runs markdown2,
    then restores the original math so MathJax can typeset it in the browser.
    """
    if not text:
        return text

    math_store: list[str] = []

    def _protect(m: re.Match) -> str:
        math_store.append(m.group(0))
        # Use a token that markdown2 will never modify:
        # null bytes + index, surrounded by spaces so inline tokens don't merge
        return f" \x00MATH{len(math_store) - 1}\x00 "

    protected = _MATH_RE.sub(_protect, text)

    rendered = markdown2.markdown(
        protected,
        extras=["fenced-code-blocks", "tables", "break-on-newline"],
    )

    # Restore math (strip the extra spaces we added for safety)
    for i, math in enumerate(math_store):
        rendered = rendered.replace(f" \x00MATH{i}\x00 ", math)
        rendered = rendered.replace(f"\x00MATH{i}\x00", math)  # fallback

    return rendered
