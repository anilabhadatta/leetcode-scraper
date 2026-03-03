"""build_indexes.py — Rebuild all index.html files to reference questions/ centrally.

Instead of copying question HTML files into every company / card subfolder,
the index.html files now link directly to ../../questions/<file> so a single
copy of each question page is kept in questions/.

Modes
-----
    python build_indexes.py                   # rebuild everything
    python build_indexes.py --companies       # only all_company_questions/*/index.html
    python build_indexes.py --cards           # only cards/*/index.html
    python build_indexes.py --questions       # only questions/index.html

What it reads
-------------
- questions/meta.json         — title / difficulty / companies / file per slug
- existing company index.html — question list + frequency (no API call needed)
- existing card   index.html  — question list (no API call needed)

What it writes
--------------
- questions/index.html                        (rebuilt from meta.json)
- all_company_questions/<slug>/index.html     (hrefs → ../../questions/<file>)
- cards/<card>/index.html                     (hrefs → ../../questions/<file>)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)

# ── relative path from a subfolder 2 levels deep to questions/ ──
_Q_REL = "../../questions"

_EXT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    '<polyline points="15 3 21 3 21 9"/>'
    '<line x1="10" y1="14" x2="21" y2="3"/></svg>'
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_meta(save_path: str) -> dict:
    path = os.path.join(save_path, "questions", "meta.json")
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _diff_badge(diff: str) -> str:
    cls = {"Easy": "badge-easy", "Medium": "badge-medium"}.get(diff, "badge-hard")
    return f'<span class="{cls}">{diff}</span>' if diff else "<span>—</span>"


def _ext_link(url: str) -> str:
    if not url:
        return ""
    return f'<a target="_blank" href="{url}">{_EXT_SVG}</a>'


def _attach_header() -> str:
    """Import from scraper if available, else minimal fallback."""
    try:
        from scraper.html.builder import attach_header_in_html
        return attach_header_in_html()
    except Exception:
        return "<head><meta charset='UTF-8'></head>"


def _attach_nav() -> str:
    try:
        from scraper.html.builder import attach_page_nav
        return attach_page_nav()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Parse an *existing* company or card index.html to extract question rows
# ---------------------------------------------------------------------------

def _parse_existing_company_index(index_path: str) -> list[dict]:
    """Return list of {title, file, slug, difficulty, frequency, url} dicts."""
    if not os.path.isfile(index_path):
        return []
    with open(index_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for a in soup.find_all("a", title=True):
        title_file = a.get("title", "")        # e.g. "Two Sum.html"
        slug       = a.get("slug", "")
        title_text = a.get_text(strip=True)
        # frequency lives in the previous <td> sibling area — grab from tr text
        tr = a.find_parent("tr")
        freq = 0.0
        if tr:
            tds = tr.find_all("td")
            # freq td is index 3 (0-based): #, title, diff, freq, link
            if len(tds) >= 4:
                freq_text = re.search(r"[\d.]+", tds[3].get_text())
                if freq_text:
                    try:
                        freq = float(freq_text.group())
                    except ValueError:
                        pass
            diff_span = tr.find("span", class_=re.compile(r"badge-"))
            diff = diff_span.get_text(strip=True) if diff_span else ""
        else:
            diff = ""
        if title_file:
            rows.append(dict(
                title=title_text,
                file=title_file,
                slug=slug,
                difficulty=diff,
                frequency=freq,
                url=f"https://leetcode.com/problems/{slug}/" if slug else "",
            ))
    return rows


# ---------------------------------------------------------------------------
# Build company index.html
# ---------------------------------------------------------------------------

def rebuild_company_index(slug: str, company_dir: str, meta: dict) -> None:
    """Rewrite a single company's index.html with hrefs pointing to ../../questions/."""
    index_path = os.path.join(company_dir, "index.html")
    rows = _parse_existing_company_index(index_path)

    if not rows:
        log.warning("  No questions found in existing index for %s — skipping", slug)
        return

    # Enrich with meta data where available
    meta_by_file = {m.get("file", ""): m for m in meta.values()}
    meta_by_slug = meta

    max_freq = max((r["frequency"] for r in rows), default=1) or 1
    tbody = ""
    for i, r in enumerate(rows, 1):
        # prefer meta for difficulty
        m = meta_by_file.get(r["file"]) or meta_by_slug.get(r["slug"]) or {}
        diff = m.get("difficulty") or r["difficulty"]
        url  = m.get("url") or r["url"]
        fname = r["file"]
        href  = f"{_Q_REL}/{fname}"
        freq  = r["frequency"]
        freq_pct = int(freq / max_freq * 100)
        tbody += (
            f"<tr>"
            f"<td style='width:40px;text-align:center'>{i}</td>"
            f"<td><a href='{href}'>{r['title']}</a></td>"
            f"<td style='text-align:center'>{_diff_badge(diff)}</td>"
            f"<td style='white-space:nowrap'>"
            f"<span style='margin-right:6px'>{freq:.2f}</span>"
            f"<span class='freq-bar-wrap'><span class='freq-bar' style='width:{freq_pct}%'></span></span>"
            f"</td>"
            f"<td style='text-align:center'>{_ext_link(url)}</td>"
            f"</tr>"
        )

    header = _attach_header()
    nav    = _attach_nav()
    html = f"""<!DOCTYPE html>
<html lang="en">
{header}
<body>
{nav}
<h2>{slug} — {len(rows)} Questions</h2>
<input class="lc-search" id="qSearch" onkeyup="filterQ()" placeholder="Search question..." type="text"/>
<table class="table table-bordered table-hover table-color" id="qTable" style="margin-top:10px">
  <thead><tr>
    <th style="width:40px">#</th>
    <th>Title</th>
    <th style="width:90px;text-align:center">Difficulty</th>
    <th style="width:160px">Frequency</th>
    <th style="width:50px">Link</th>
  </tr></thead>
  <tbody>{tbody}</tbody>
</table>
<script>
function filterQ() {{
  var q = document.getElementById('qSearch').value.toLowerCase();
  document.querySelectorAll('#qTable tbody tr').forEach(function(r) {{
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</body>
</html>"""

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info("  rebuilt company index: %s (%d questions)", slug, len(rows))


def rebuild_all_company_indexes(save_path: str, meta: dict) -> None:
    company_root = os.path.join(save_path, "all_company_questions")
    if not os.path.isdir(company_root):
        log.warning("all_company_questions/ not found — skipping")
        return
    slugs = [
        d for d in os.listdir(company_root)
        if os.path.isdir(os.path.join(company_root, d))
    ]
    log.info("Rebuilding %d company indexes...", len(slugs))
    for slug in sorted(slugs):
        rebuild_company_index(slug, os.path.join(company_root, slug), meta)


# ---------------------------------------------------------------------------
# Build card index.html
# ---------------------------------------------------------------------------

def _parse_existing_card_index(index_path: str) -> list[dict]:
    """Return list of {title, file, slug} from an existing card/chapter index."""
    if not os.path.isfile(index_path):
        return []
    with open(index_path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for a in soup.find_all("a", title=True):
        title_file = a.get("title", "")
        slug       = a.get("slug", "")
        title_text = a.get_text(strip=True)
        if title_file:
            rows.append(dict(title=title_text, file=title_file, slug=slug))
    return rows


def rebuild_card_index(card_slug: str, card_dir: str, meta: dict) -> None:
    """Rewrite a card's index.html so question hrefs point to ../../questions/.

    Only hrefs whose target actually exists in questions/ are repointed.
    Article-only items that live inside the card folder are left alone.
    """
    index_path = os.path.join(card_dir, "index.html")
    if not os.path.isfile(index_path):
        log.debug("  No index.html for card %s — skipping", card_slug)
        return

    # Derive save_path from card_dir  (save_path/cards/<slug> → save_path)
    questions_dir = os.path.join(os.path.dirname(os.path.dirname(card_dir)), "questions")

    with open(index_path, "r", encoding="utf-8", errors="replace") as f:
        original = f.read()

    def _fix_href(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith(("../", "http", "#", "/")):
            return m.group(0)  # already absolute/relative — leave alone
        if href == "index.html":
            return m.group(0)
        # Only repoint if the file actually lives in questions/
        if os.path.isfile(os.path.join(questions_dir, href)):
            return f'href="{_Q_REL}/{href}"'
        return m.group(0)  # article-only item — keep relative

    fixed = re.sub(r'href="([^"]+\.html)"', _fix_href, original)

    if fixed == original:
        log.debug("  card %s already up-to-date", card_slug)
        return

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(fixed)
    log.info("  rebuilt card index: %s", card_slug)


def rebuild_all_card_indexes(save_path: str, meta: dict) -> None:
    for folder_name in ("cards", "card"):
        card_root = os.path.join(save_path, folder_name)
        if not os.path.isdir(card_root):
            continue
        slugs = [
            d for d in os.listdir(card_root)
            if os.path.isdir(os.path.join(card_root, d))
        ]
        log.info("Rebuilding %d %s/ indexes...", len(slugs), folder_name)
        for slug in sorted(slugs):
            rebuild_card_index(slug, os.path.join(card_root, slug), meta)


# ---------------------------------------------------------------------------
# Rebuild questions/index.html from meta.json
# ---------------------------------------------------------------------------

def rebuild_question_index(save_path: str, meta: dict) -> None:
    from scraper.html.indexes import create_question_index_html
    all_questions = [
        {"title": m.get("title", ""), "titleSlug": m.get("slug", "")}
        for m in meta.values()
    ]
    create_question_index_html(save_path, all_questions)
    log.info("questions/index.html rebuilt (%d entries)", len(all_questions))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--companies", action="store_true", help="Rebuild company indexes only")
    parser.add_argument("--cards",     action="store_true", help="Rebuild card indexes only")
    parser.add_argument("--questions", action="store_true", help="Rebuild questions/index.html only")
    args = parser.parse_args()

    # If no flags set, do everything
    do_all = not (args.companies or args.cards or args.questions)

    try:
        from scraper.config import load_config, select_config_interactive
        select_config_interactive()
        config = load_config()
        save_path = config["save_path"]
    except Exception as exc:
        log.error("Could not load config: %s", exc)
        sys.exit(1)

    meta = _load_meta(save_path)
    log.info("Loaded meta.json: %d entries", len(meta))

    if do_all or args.questions:
        rebuild_question_index(save_path, meta)

    if do_all or args.companies:
        rebuild_all_company_indexes(save_path, meta)

    if do_all or args.cards:
        rebuild_all_card_indexes(save_path, meta)

    log.info("All done.")


if __name__ == "__main__":
    main()
