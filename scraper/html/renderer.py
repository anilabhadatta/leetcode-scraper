"""HTML rendering helpers - business logic for question/article/card HTML."""
from __future__ import annotations

import json
import logging
from bs4 import BeautifulSoup

from scraper.api import (
    fetch_question, fetch_article, fetch_html_article,
    fetch_playground_codes, fetch_card_intro,
)
from scraper.utils import safe_filename
from scraper.html.builder import attach_header_in_html, attach_page_nav

log = logging.getLogger(__name__)

_EXT_LINK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="2">'
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
    '<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'
)


# ---------------------------------------------------------------------------
# HTML snippet generators (pure functions - no I/O)
# ---------------------------------------------------------------------------

def _diff_class(diff: str) -> str:
    return {"Easy": "badge-easy", "Medium": "badge-medium"}.get(diff, "badge-hard")


def _render_similar_questions(raw: str) -> str:
    if not raw:
        return ""
    qs = json.loads(raw)
    rows_list = []
    for i, q in enumerate(qs, 1):
        title = q["title"]
        slug = q["titleSlug"]
        diff = q["difficulty"]
        dc = _diff_class(diff)
        rows_list.append(
            f'<tr>'
            f'<td style="width:28px;color:#9ca3af;text-align:right">{i}</td>'
            f'<td><a href="./{title}.html">{title}</a></td>'
            f'<td style="text-align:center"><span class="{dc}">{diff}</span></td>'
            f'<td><a target="_blank" href="https://leetcode.com/problems/{slug}">{_EXT_LINK_SVG}</a></td>'
            f'</tr>'
        )
    rows = "".join(rows_list)
    return f'<div class="q-section"><h5>Similar Questions</h5><table class="sim-q-table">{rows}</table></div>' if rows else ""


def _render_company_stats(raw: str) -> str:
    if not raw:
        return ""
    cts = json.loads(raw)
    period = {"1": "0 - 3 months", "2": "0 - 6 months", "3": "6 months ago"}
    html = '<div class="q-section"><h5>Company Tag Stats</h5>'
    for key in sorted(cts):
        label = period.get(key, key)
        pills_list = []
        for c in sorted(cts[key], key=lambda x: -x["timesEncountered"]):
            if c["timesEncountered"] > 0:
                name = c["name"]
                cnt = c["timesEncountered"]
                pills_list.append(f'<span class="co-pill">{name}<span class="co-cnt">{cnt}</span></span>')
        if pills_list:
            pills = "".join(pills_list)
            html += f'<div class="stat-section"><div class="stat-period">{label}</div><br>{pills}</div>'
    return html + "</div>"


# ---------------------------------------------------------------------------
# Exported rendering functions
# ---------------------------------------------------------------------------

def get_question_data(item_content: dict, headers) -> tuple:
    """Return (html_str, question_title, meta_dict)."""
    if not item_content.get("question"):
        return attach_page_nav(), "", {}

    slug = item_content["question"]["titleSlug"]
    log.info("Fetching question: %s", slug)
    qc = fetch_question(headers, slug)

    title = safe_filename(qc["title"])
    diff  = qc["difficulty"]
    url   = "https://leetcode.com" + qc["submitUrl"][:-7]
    code  = json.loads(qc["codeDefinition"])[0]["defaultCode"]
    sol   = (qc["solution"] or {}).get("content") or "No Solution"
    hints = "".join(f'<div class="hint-item">{h}</div>' for h in qc["hints"]) \
            or '<span style="color:#9ca3af">No Hints</span>'

    raw_cts = qc["companyTagStats"]
    top_cos = []
    if raw_cts:
        try:
            cts = json.loads(raw_cts)
            recent = cts.get("1") or cts.get("2") or cts.get("3") or []
            top_cos = [c["name"] for c in sorted(recent, key=lambda x: -x["timesEncountered"])[:8]]
        except Exception:
            pass

    co_pills = "".join(f'<span class="company-tag">{c}</span>' for c in top_cos)
    co_div = f'<div style="margin-bottom:12px">{co_pills}</div>' if co_pills else ""

    html = "\n".join([
        attach_page_nav(),
        f'<div class="q-header">',
        f'  <h2 class="q-title"><a target="_blank" href="{url}">{title}</a></h2>',
        f'  <span class="{_diff_class(diff)}">{diff}</span>',
        f'</div>',
        co_div,
        _render_company_stats(raw_cts),
        _render_similar_questions(qc["similarQuestions"]),
        f'<div class="">\n  <h5>Question</h5>\n  <md-block class="question__content">{qc["content"]}</md-block>\n</div>',
        f'<div class="">\n  <h5>Default Code</h5>\n  <div class=""><pre class="question__default_code">{code}</pre></div>\n</div>',
        f'<div class="q-section">\n  <h5>Hints</h5>\n  <md-block class="question__hints">{hints}</md-block>\n</div>',
        f'<div class="">\n  <md-block class="question__solution">{sol}</md-block>\n</div>',
    ])
    meta = dict(title=title, slug=slug, difficulty=diff, companies=top_cos, url=url, file=f"{title}.html")
    return html, title, meta


def get_article_data(item_content: dict, item_title: str, headers) -> str:
    if not item_content.get("article"):
        return ""
    art = fetch_article(headers, str(item_content["article"]["id"]))
    return f'<h3>{item_title}</h3><md-block class="article__content">{art["body"]}</md-block>'


def get_html_article_data(item_content: dict, item_title: str, headers) -> str:
    if not item_content.get("htmlArticle"):
        return ""
    art = fetch_html_article(headers, str(item_content["htmlArticle"]["id"]))
    return f'<h3>{item_title}</h3><md-block class="html_article__content">{art["html"]}</md-block>'


def replace_iframes_with_codes(soup: BeautifulSoup, headers) -> BeautifulSoup:
    for idx, iframe in enumerate(soup.find_all("iframe"), 1):
        if "playground" not in iframe.get("src", ""):
            continue
        uuid = iframe["src"].split("/")[-2]
        codes = fetch_playground_codes(headers, uuid)
        tabs_list = []
        panes_list = []
        for i, c in enumerate(codes):
            active = "active" if i == 0 else ""
            show_active = "show active" if i == 0 else ""
            tabs_list.append(
                f'<button class="nav-link {active}" '
                f'data-bs-toggle="tab" data-bs-target="#vp-{idx}{i}" type="button">{c["langSlug"]}</button>'
            )
            panes_list.append(
                f'<div class="tab-pane fade {show_active}" id="vp-{idx}{i}">'
                f'<code><pre>{c["code"]}</pre></code></div>'
            )
        tabs = "".join(tabs_list)
        panes = "".join(panes_list)
        html = (
            f'<nav><div class="nav nav-tabs">{tabs}</div></nav>'
            f'<div class="tab-content">{panes}</div>'
        )
        iframe.replace_with(BeautifulSoup(html, "html.parser"))
    return soup


def create_card_index_html(chapters: list, card_slug: str, headers) -> None:
    intro = fetch_card_intro(headers, card_slug)
    body_parts: list[str] = []
    for ch in chapters:
        body_parts.append(f'<br><h3>{ch["title"]}</h3>{ch["description"]}<br>')
        for it in ch["items"]:
            name = safe_filename(it["title"])
            body_parts.append(f'<a href="{it["id"]}-{name}.html">{it["id"]}-{name}</a><br>')
    body = "".join(body_parts)
    html = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n"
        + attach_header_in_html()
        + "\n<body>\n"
        + attach_page_nav() + '\n'
        + "<h1>" + intro["title"] + "</h1>"
        + "<p>" + intro["introduction"] + "</p><br>\n"
        + body
        + "\n</body>\n</html>"
    )
    with open("index.html", "w", encoding="utf-8") as fh:
        fh.write(html)