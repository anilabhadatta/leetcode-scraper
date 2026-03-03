"""refresh_company_tags.py — Rebuild meta / refresh companyTagStatsV2 in question HTML files.

Modes
-----
Scan mode  (--scan):
    Walk every *.html file in questions_dir, extract title / slug / difficulty /
    companies from the HTML itself (no API calls), and write / merge meta.json.
    Use this after you already have HTML files on disk and want to rebuild meta.json
    from scratch without re-scraping.

Refresh mode (default):
    Read slugs from questions.txt.  For each slug that already has an HTML file
    recorded in meta.json the entry is left untouched (already done).  For slugs
    whose HTML file is missing the company-tag data is fetched from the LeetCode
    API, the HTML is patched in-place, and meta.json is updated.
    After running scan mode you can prune questions.txt to only the slugs that
    still need to be processed, then run refresh mode.

Usage
-----
    python refresh_company_tags.py           # refresh mode
    python refresh_company_tags.py --scan    # scan-and-build-meta mode
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys

from bs4 import BeautifulSoup

from scraper.api import create_headers, fetch_question_company_tags
from scraper.config import load_config, select_config_interactive
from scraper.html.indexes import create_question_index_html
from scraper.html.renderer import _render_company_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOP_N = 8  # how many top companies to store in meta


def _top_companies(raw_cts: str, slug: str = "") -> list[str]:
    """Extract top-N company names from raw companyTagStatsV2 JSON string.

    Merges all three time-period buckets (three_months / six_months /
    more_than_six_months), sums timesEncountered per company across all
    periods, then returns the top-N names sorted by that total.
    """
    if not raw_cts:
        return []
    try:
        cts = json.loads(raw_cts)
        totals: dict[str, int] = {}
        for key in ("three_months", "six_months", "more_than_six_months"):
            for entry in cts.get(key) or []:
                name = entry.get("name", "")
                if name:
                    totals[name] = totals.get(name, 0) + entry.get("timesEncountered", 0)
        return [name for name, _ in sorted(totals.items(), key=lambda x: -x[1])[:_TOP_N]]
    except Exception as exc:
        log.warning("  _top_companies failed (slug=%s): %s", slug, exc)
        log.warning("  raw_cts preview: %.200s", raw_cts)
        return []


_LC_PROBLEMS_RE = re.compile(r"https?://leetcode\.com/problems/([^/]+)/")


def _scan_html_file(html_path: str, filename: str) -> dict | None:
    """Extract meta fields from an already-scraped question HTML file.

    Returns a dict with keys: title, slug, difficulty, companies, url, file.
    Returns None if the file doesn't look like a question page.
    """
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        soup = BeautifulSoup(content, "html.parser")

        # ── slug + title from .q-title anchor ──
        q_title_tag = soup.find("h2", class_="q-title")
        if not q_title_tag:
            return None
        anchor = q_title_tag.find("a")
        if not anchor:
            return None
        title = anchor.get_text(strip=True)
        url   = anchor.get("href", "")
        m = _LC_PROBLEMS_RE.search(url)
        if not m:
            return None
        slug = m.group(1)

        # ── difficulty ── (classes: badge-easy / badge-medium / badge-hard)
        q_header = soup.find("div", class_="q-header")
        diff = ""
        if q_header:
            diff_span = q_header.find("span", class_=re.compile(r"badge-(easy|medium|hard)", re.I))
            if diff_span:
                diff = diff_span.get_text(strip=True)

        # ── companies: read from the co-pill spans in Company Tag Stats section,
        #    sum timesEncountered across all period buckets, take top N ──
        totals: dict[str, int] = {}
        for pill in soup.find_all("span", class_="co-pill"):
            cnt_span = pill.find("span", class_="co-cnt")
            if cnt_span:
                cnt_text = cnt_span.get_text(strip=True)
                cnt_span.decompose()
            else:
                cnt_text = "0"
            name = pill.get_text(strip=True)
            try:
                cnt = int(cnt_text)
            except ValueError:
                cnt = 0
            if name:
                totals[name] = totals.get(name, 0) + cnt
        companies: list[str] = [
            name for name, _ in sorted(totals.items(), key=lambda x: -x[1])[:_TOP_N]
        ]

        return dict(
            title=title,
            slug=slug,
            difficulty=diff,
            companies=companies[:_TOP_N],
            url=url,
            file=filename,
        )
    except Exception as exc:
        log.warning("  scan failed for %s: %s", filename, exc)
        return None


def _render_co_div(top_cos: list[str]) -> str:
    """Re-render the company-pill header row (same as renderer.py)."""
    if not top_cos:
        return ""
    pills = "".join(f'<span class="company-tag">{c}</span>' for c in top_cos)
    return f'<div style="margin-bottom:12px">{pills}</div>'


def _patch_html(html_path: str, raw_cts: str, top_cos: list[str]) -> bool:
    """Patch company-tag sections inside an existing HTML file.

    Returns True if the file was modified, False if nothing changed.
    """
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")
    changed = False

    # ── 1. Replace <div class="q-section"> that contains <h5>Company Tag Stats</h5> ──
    h5 = soup.find("h5", string=re.compile(r"Company\s+Tag\s+Stats", re.I))
    if h5:
        stats_div = h5.parent  # the q-section wrapper
        new_stats_html = _render_company_stats(raw_cts)
        if new_stats_html:
            stats_div.replace_with(BeautifulSoup(new_stats_html, "html.parser"))
        else:
            stats_div.decompose()
        changed = True
    else:
        # Section didn't exist before — insert it if we now have data
        if raw_cts:
            # Insert after q-header div (company pills row)
            q_header = soup.find("div", class_="q-header")
            if q_header:
                new_stats = BeautifulSoup(_render_company_stats(raw_cts), "html.parser")
                q_header.insert_after(new_stats)
                changed = True

    # ── 2. Replace the company-pills co_div (style="margin-bottom:12px") ──
    co_div = soup.find("div", style=lambda s: s and "margin-bottom:12px" in s)
    new_co_html = _render_co_div(top_cos)
    if co_div:
        if new_co_html:
            co_div.replace_with(BeautifulSoup(new_co_html, "html.parser"))
        else:
            co_div.decompose()
        changed = True
    else:
        if new_co_html:
            # Insert after q-header
            q_header = soup.find("div", class_="q-header")
            if q_header:
                q_header.insert_after(BeautifulSoup(new_co_html, "html.parser"))
                changed = True

    if changed:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(soup.prettify())

    return changed


# ---------------------------------------------------------------------------
# Scan mode
# ---------------------------------------------------------------------------

def scan_mode(config: dict) -> None:
    """Walk existing HTML files and rebuild meta.json from disk — no API calls."""
    save_path    = config["save_path"]
    questions_dir = os.path.join(save_path, "questions")
    meta_path    = os.path.join(questions_dir, "meta.json")

    if not os.path.isdir(questions_dir):
        log.error("questions dir not found: %s", questions_dir)
        sys.exit(1)

    # Load existing meta so we only overwrite entries we can improve
    all_meta: dict = {}
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            all_meta = json.load(mf)
        log.info("Loaded existing meta.json (%d entries)", len(all_meta))

    html_files = sorted(
        f for f in os.listdir(questions_dir)
        if f.endswith(".html") and f != "index.html"
    )
    log.info("Found %d HTML files to scan", len(html_files))

    added = updated = skipped = 0
    for i, filename in enumerate(html_files, 1):
        html_path = os.path.join(questions_dir, filename)
        entry = _scan_html_file(html_path, filename)
        if entry is None:
            log.debug("[%d/%d] %s — not a question page, skipping", i, len(html_files), filename)
            skipped += 1
            continue

        slug = entry["slug"]
        if slug in all_meta:
            all_meta[slug].update(entry)   # refresh in-place
            updated += 1
            log.debug("[%d/%d] updated  %s", i, len(html_files), slug)
        else:
            all_meta[slug] = entry
            added += 1
            log.info("[%d/%d] added    %s  (%s)", i, len(html_files), slug, entry["title"])

    with open(meta_path, "w", encoding="utf-8") as mf:
        json.dump(all_meta, mf, ensure_ascii=False, indent=2)
    log.info("meta.json saved — added: %d | updated: %d | skipped: %d | total: %d",
             added, updated, skipped, len(all_meta))

    log.info("Regenerating questions/index.html ...")
    all_questions = [
        {"title": m.get("title", ""), "titleSlug": m.get("slug", "")}
        for m in all_meta.values()
    ]
    create_question_index_html(save_path, all_questions)
    log.info("questions/index.html regenerated")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan existing HTML files and rebuild meta.json from disk (no API calls).",
    )
    args = parser.parse_args()

    select_config_interactive()
    config = load_config()

    if args.scan:
        scan_mode(config)
        return

    cookie          = config["leetcode_cookie"]
    save_path       = config["save_path"]
    questions_path  = config["questions_url_path"]
    questions_dir   = os.path.join(save_path, "questions")
    meta_path       = os.path.join(questions_dir, "meta.json")

    if not os.path.isfile(questions_path):
        log.error("questions.txt not found at: %s", questions_path)
        sys.exit(1)

    headers = create_headers(cookie)

    # Read slugs from questions.txt
    with open(questions_path, "r", encoding="utf-8") as f:
        slugs = [
            line.strip().rstrip("/").split("/")[-1]
            for line in f
            if line.strip()
        ]
    log.info("Found %d slugs in questions.txt", len(slugs))

    # Load existing meta.json
    all_meta: dict = {}
    if os.path.isfile(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            all_meta = json.load(mf)

    existing_files = set(os.listdir(questions_dir))

    patched = 0
    skipped = 0
    errors  = 0

    try:
        for i, slug in enumerate(slugs, 1):
            # Resolve HTML filename from meta or skip if not scraped yet
            meta_entry = all_meta.get(slug)
            if meta_entry:
                html_file = meta_entry.get("file", "")
            else:
                # Not in meta — skip (not scraped / not yet downloaded)
                log.debug("[%d/%d] %s — not in meta.json, skipping", i, len(slugs), slug)
                skipped += 1
                continue

            if not html_file or html_file not in existing_files:
                log.debug("[%d/%d] %s — HTML file '%s' not found, skipping", i, len(slugs), slug, html_file)
                skipped += 1
                continue

            # Already has company data — nothing to do
            if meta_entry.get("companies"):
                log.debug("[%d/%d] %s — already has company data, skipping", i, len(slugs), slug)
                skipped += 1
                continue

            log.info("[%d/%d] Refreshing: %s", i, len(slugs), slug)
            try:
                raw_cts  = fetch_question_company_tags(headers, slug)
                top_cos  = _top_companies(raw_cts, slug)
                html_path = os.path.join(questions_dir, html_file)

                changed = _patch_html(html_path, raw_cts or "", top_cos)

                # Update meta.json entry
                all_meta[slug]["companies"] = top_cos
                patched += 1
                status = "updated" if changed else "no change"
                log.info("  → %s  (companies: %s)", status, ", ".join(top_cos) or "none")

            except PermissionError:
                raise  # bubble up to outer handler → saves meta and exits
            except Exception as exc:
                log.error("  ✗ Failed for %s: %s", slug, exc)
                errors += 1

    except PermissionError as exc:
        log.error("Authentication error — %s", exc)
        log.warning("Stopping and saving progress so far...")
    except KeyboardInterrupt:
        log.warning("Interrupted by user — saving progress so far...")
    finally:
        # Always persist meta.json and regenerate index, even on Ctrl+C or crash
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(all_meta, mf, ensure_ascii=False, indent=2)
        log.info("meta.json updated")

        log.info("Regenerating questions/index.html ...")
        all_questions = [
            {"title": m.get("title", ""), "titleSlug": m.get("slug", "")}
            for m in all_meta.values()
        ]
        create_question_index_html(save_path, all_questions)
        log.info("questions/index.html regenerated")

        log.info("Done — patched: %d | skipped: %d | errors: %d", patched, skipped, errors)


if __name__ == "__main__":
    main()
