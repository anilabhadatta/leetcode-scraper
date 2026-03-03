"""Filesystem and string utilities."""
from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path

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
