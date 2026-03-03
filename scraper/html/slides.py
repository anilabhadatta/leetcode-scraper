"""Solution slide carousel helpers."""
from __future__ import annotations

import json
import logging
import re

import cloudscraper
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)
_BASE = "https://assets.leetcode.com/static_assets/media/"
_scraper = None


def _get_scraper():
    global _scraper
    if _scraper is None:
        _scraper = cloudscraper.create_scraper()
    return _scraper


def _fetch_timeline(path_variants: list[str]) -> list:
    for url in path_variants:
        try:
            data = json.loads(_get_scraper().get(url, timeout=15).content)
            if "timeline" in data:
                return data["timeline"]
        except Exception as exc:
            log.debug("Slide fetch failed %s: %s", url, exc)
    return []


def find_slides_json(content: str) -> list:
    """Extract and fetch all slide animation JSON blocks from raw HTML content."""
    pattern = re.compile(r"\!\?\!.*?/Documents/.*?\!\?\!", re.IGNORECASE | re.MULTILINE)
    found = pattern.findall(content) or re.findall(r".*?/Documents/.*?\.json.*", content, re.IGNORECASE | re.MULTILINE)
    results = []
    for raw in found:
        m = re.search(r"\!\?\!(.*?)(?::\d+,\d+)?\!\?\!", raw)
        raw = (m.group(1) if m else raw).strip()
        if ".json" not in raw:
            results.append([])
            continue
        parts = [p for p in raw.split(".json")[0].split("/") if p and p != ".."]
        if not parts or parts[0].lower() != "documents":
            results.append([])
            continue
        stem = "/".join(parts[1:])  # e.g. "4/s1" or "01_LIS"
        results.append(_fetch_timeline([
            f"{_BASE}documents/{stem}.json",
            f"{_BASE}documents/{stem.lower()}.json",
        ]))
    return results


def place_solution_slides(soup: BeautifulSoup, slides: list) -> BeautifulSoup:
    """Replace /Documents/…json marker <p> tags with Bootstrap carousels."""
    tags = [
        t for t in soup.find_all("p")
        if "/Documents/" in t.get_text() and not t.find("p") and ".json" in str(t)
    ]
    for idx, (tag, frames) in enumerate(zip(tags, slides)):
        if not frames:
            continue
        cid = f"carousel-{idx}"
        items = "".join(
            f'<div class="carousel-item {"active" if i == 0 else ""}">'  # noqa: E501
            f'<img src="{f["image"]}" class="d-block" alt=""></div>'
            for i, f in enumerate(frames)
        )
        html = (
            f'<div id="{cid}" class="carousel slide" data-bs-ride="carousel">'
            f'<div class="carousel-inner">{items}</div>'
            f'<button class="carousel-control-prev" type="button" data-bs-target="#{cid}" data-bs-slide="prev">'
            f'<span class="carousel-control-prev-icon"></span></button>'
            f'<button class="carousel-control-next" type="button" data-bs-target="#{cid}" data-bs-slide="next">'
            f'<span class="carousel-control-next-icon"></span></button>'
            f'</div>'
        )
        if tag.parent is None:
            log.warning(
                "Skipping slide #%d — <p> tag is no longer in the tree.", idx
            )
            continue
        try:
            tag.replace_with(BeautifulSoup(html, "html.parser"))
        except Exception as exc:
            log.error(
                "replace_with failed in place_solution_slides [slide #%d]: %s",
                idx, exc
            )
            log.error("  tag text    : %.120s", tag.get_text())
            log.error("  tag parent  : %s", getattr(tag.parent, 'name', None))
            log.error("  tag in tree : %s", tag.parent is not None)
            raise
    return soup

