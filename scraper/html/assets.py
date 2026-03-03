"""Image asset helpers."""
from __future__ import annotations

import base64
import logging
from pathlib import Path

import cloudscraper
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
_scraper = None


def _get_scraper():
    global _scraper
    if _scraper is None:
        _scraper = cloudscraper.create_scraper()
    return _scraper


def load_image_in_b64(img_url: str) -> str:
    log.debug("base64 fetch: %s", img_url)
    ext = img_url.rsplit(".", 1)[-1]
    if ext == "svg":
        ext = "svg+xml"
    data = _get_scraper().get(img_url).content
    return f"data:image/{ext};base64,{base64.b64encode(data).decode()}"


def fix_image_urls(soup: BeautifulSoup, save_locally: bool) -> BeautifulSoup:
    for img in soup.select("img[src]"):
        src = img["src"]
        if "base64" in src:
            continue
        if ".." in src.split("/"):
            parts = src.split("/")
            idx = max(i + 1 for i, p in enumerate(parts[:-1]) if p == ".." and parts[i + 1] != "..")
            src = f"https://leetcode.com/explore/{'/'.join(parts[idx:])}"
        img["src"] = load_image_in_b64(src) if save_locally else src
    return soup


def manual_convert_images_to_base64() -> None:
    root = Path(input("Folder containing HTML files: ").strip())
    for html_path in root.rglob("*.html"):
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        html_path.write_text(fix_image_urls(soup, True).prettify(), encoding="utf-8")
        log.info("Converted images in %s", html_path.name)
