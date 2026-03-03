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
        log.info("Fetching slide timeline: %s", url)
        try:
            resp = _get_scraper().get(url, timeout=15)
            if resp.status_code != 200:
                log.info("Slide fetch HTTP %d: %s", resp.status_code, url)
                continue
            data = json.loads(resp.content)
            if "timeline" in data:
                log.info("Slide timeline fetched OK (%d frames): %s", len(data["timeline"]), url)
                return data["timeline"]
            else:
                log.info("Slide JSON has no 'timeline' key at: %s", url)
        except Exception as exc:
            log.info("Slide fetch failed %s: %s", url, exc)
    log.info("No timeline found for variants: %s", path_variants)
    return []


def find_slides_json(content: str) -> list:
    """Extract and fetch all slide animation JSON blocks from raw HTML content."""
    # re.DOTALL so that .* matches across newlines (LeetCode HTML can wrap mid-marker).
    _FLAGS = re.IGNORECASE | re.DOTALL

    pattern = re.compile(r"\!\?\!.*?/Documents/.*?\!\?\!", _FLAGS)
    found = pattern.findall(content)
    log.info("Slides primary regex found %d marker(s)", len(found))

    if not found:
        found = re.findall(r"\!\?\![^!]*?/Documents/[^!]*?\.json[^!]*?\!\?\!", content, _FLAGS)
        log.info("Slides fallback-1 found %d marker(s)", len(found))

    if not found:
        found = re.findall(r"/Documents/[^\s<\"']+\.json", content, re.IGNORECASE)
        log.info("Slides fallback-2 (no delimiters) found %d marker(s)", len(found))

    results = []
    for raw in found:
        log.info("  Processing slide marker: %.120s", raw)
        m = re.search(r"\!\?\!(.*?)(?::\d+,\d+)?\!\?\!", raw, re.DOTALL)
        raw = (m.group(1) if m else raw).strip()
        log.info("  Extracted path: %s", raw)
        if ".json" not in raw:
            log.info("  Skipped — no .json in extracted path")
            results.append([])
            continue
        parts = [p for p in raw.split(".json")[0].split("/") if p and p not in ("..", ".")]
        log.info("  Path parts: %s", parts)
        if not parts or parts[0].lower() != "documents":
            log.info("  Skipped — first part is %r, expected 'documents'", parts[0] if parts else "<empty>")
            results.append([])
            continue
        stem = "/".join(parts[1:])  # e.g. "4/s1" or "01_LIS"
        log.info("  Stem: %s", stem)
        results.append(_fetch_timeline([
            f"{_BASE}documents/{stem}.json",
            f"{_BASE}documents/{stem.lower()}.json",
        ]))
    return results


def place_solution_slides(soup: BeautifulSoup, slides: list) -> BeautifulSoup:
    """Replace /Documents/…json marker nodes with Bootstrap carousels."""
    marker_nodes = soup.find_all(string=re.compile(r"/Documents/.*?\.json", re.IGNORECASE | re.DOTALL))
    log.info("place_solution_slides: %d text node(s) found, %d slide(s) provided", len(marker_nodes), len(slides))
    for idx, (text_node, frames) in enumerate(zip(marker_nodes, slides)):
        if not frames:
            log.info("  Slide #%d: no frames, skipping", idx)
            continue
        cid = f"carousel-{idx}"
        items = "".join(
            f'<div class="carousel-item {"active" if i == 0 else ""}">'
            f'<img src="{f["image"]}" class="d-block" alt=""></div>'
            for i, f in enumerate(frames)
        )
        carousel_html = (
            f'<div id="{cid}" class="carousel slide" data-bs-ride="carousel">'
            f'<div class="carousel-inner">{items}</div>'
            f'<button class="carousel-control-prev" type="button" data-bs-target="#{cid}" data-bs-slide="prev">'
            f'<span class="carousel-control-prev-icon"></span></button>'
            f'<button class="carousel-control-next" type="button" data-bs-target="#{cid}" data-bs-slide="next">'
            f'<span class="carousel-control-next-icon"></span></button>'
            f'</div>'
        )
        carousel_soup = BeautifulSoup(carousel_html, "html.parser")

        # Use the immediate parent only if it is a simple inline/block wrapper
        # whose sole meaningful content is this marker text (e.g. a <p> that
        # contains only the !?! line).  If the parent has other children
        # (siblings to the text node) replace just the text node itself so we
        # don't destroy surrounding content.
        parent = text_node.parent
        other_content = [c for c in parent.children if c is not text_node and str(c).strip()]
        inline_containers = {"p", "li", "td", "th"}

        if parent.name == "body" or parent is None:
            log.warning("  Slide #%d: text node is a direct child of body, skipping", idx)
            continue

        if not other_content and parent.name in inline_containers:
            # Safe to replace the whole parent element
            if parent.parent is None:
                log.warning("  Slide #%d: parent already detached, skipping", idx)
                continue
            parent.replace_with(carousel_soup)
            log.info("  Slide #%d replaced <%s> with carousel (%d frames)", idx, parent.name, len(frames))
        else:
            # Parent has other children — replace only the text node itself
            text_node.replace_with(carousel_soup)
            log.info("  Slide #%d replaced text node inside <%s> with carousel (%d frames)", idx, parent.name, len(frames))
    return soup

