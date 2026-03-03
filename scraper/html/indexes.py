import json
import os
import re

from scraper.config import load_config
from scraper.utils import safe_filename
from scraper.html.builder import attach_header_in_html, attach_page_nav


def _ensure_base_index() -> None:
    """Create base index.html in save_path if it does not already exist."""
    config = load_config()
    save_path = config["save_path"]
    if not os.path.exists(os.path.join(save_path, "index.html")):
        create_base_index_html()


def create_base_index_html() -> None:
    print("Creating base index.html")
    config = load_config()
    save_path = config["save_path"]
    sections = [
        {
            "title": "Questions",
            "href": "questions/index.html",
            "desc": "All scraped LeetCode questions",
            "icon": (
                '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" '
                'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">'
                '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                '<polyline points="14 2 14 8 20 8"/>'
                '<line x1="16" y1="13" x2="8" y2="13"/>'
                '<line x1="16" y1="17" x2="8" y2="17"/>'
                '<polyline points="10 9 9 9 8 9"/></svg>'
            ),
        },
        {
            "title": "Cards",
            "href": "cards/index.html",
            "desc": "Explore cards and learning paths",
            "icon": (
                '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" '
                'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">'
                '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>'
                '<line x1="8" y1="21" x2="16" y2="21"/>'
                '<line x1="12" y1="17" x2="12" y2="21"/></svg>'
            ),
        },
        {
            "title": "Company Questions",
            "href": "all_company_questions/index.html",
            "desc": "Questions grouped by company",
            "icon": (
                '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" '
                'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">'
                '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
                '<polyline points="9 22 9 12 15 12 15 22"/></svg>'
            ),
        },
    ]
    cards_html = "".join(
        f'<a class="idx-card" href="{s["href"]}">'
        f'<div class="idx-icon">{s["icon"]}</div>'
        f'<div class="idx-label">{s["title"]}</div>'
        f'<div class="idx-desc">{s["desc"]}</div></a>'
        for s in sections
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<style>
  body {{ background: #f0f4f8 !important; }}
  .dark body, body.dark {{ background: #181818 !important; }}
  .idx-hero {{ text-align:center; padding: 48px 0 24px; }}
  .idx-hero h1 {{ font-size:2em; font-weight:800; margin-bottom:6px; }}
  .idx-hero p {{ color:#6b7280; font-size:1em; }}
  .dark .idx-hero p {{ color:#9ca3af; }}
  .idx-grid {{ display:flex; flex-wrap:wrap; gap:20px; justify-content:center; padding:24px 0 48px; }}
  .idx-card {{ display:flex; flex-direction:column; align-items:center; text-align:center;
               width:220px; padding:28px 20px 22px; border-radius:12px;
               background:#fff; border:1px solid #e5e7eb;
               text-decoration:none; color:inherit;
               transition:box-shadow .2s, transform .15s; }}
  .idx-card:hover {{ box-shadow:0 4px 24px rgba(0,0,0,0.10); transform:translateY(-3px); text-decoration:none; color:inherit; }}
  .dark .idx-card {{ background:#1e1e1e; border-color:#333; }}
  .dark .idx-card:hover {{ box-shadow:0 4px 24px rgba(0,0,0,0.4); }}
  .idx-icon {{ color:#4e9af1; margin-bottom:14px; }}
  .dark .idx-icon {{ color:#60a5fa; }}
  .idx-label {{ font-size:1.05em; font-weight:700; margin-bottom:6px; }}
  .idx-desc {{ font-size:0.82em; color:#6b7280; }}
  .dark .idx-desc {{ color:#9ca3af; }}
  .idx-footer {{ text-align:center; color:#9ca3af; font-size:0.8em; padding-bottom:32px; }}
</style>
<body>
{attach_page_nav()}
<div class="idx-hero">
  <h1>LeetCode Scraper</h1>
  <p>Your local offline LeetCode archive</p>
</div>
<div class="idx-grid">{cards_html}</div>
<div class="idx-footer">
  Built by Anilabha Datta &mdash;
  <a href="https://github.com/anilabhadatta/leetcode-scraper" target="_blank">GitHub</a>
</div>
</body>
</html>"""
    out = os.path.join(save_path, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Base index.html created at: {out}")
    print(f'Run: python -m http.server 8080 --directory "{save_path}"')


def create_question_index_html(save_path: str, all_questions: list) -> None:
    """Build/refresh the question index at <save_path>/questions/index.html."""
    meta_path = os.path.join(save_path, "questions", "meta.json")
    all_meta: dict = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            all_meta = json.load(mf)

    index_data = []
    questions_folder = os.path.join(save_path, "questions")
    for fname in sorted(os.listdir(questions_folder)):
        if fname.endswith(".html") and fname != "index.html":
            # Primary: find meta entry by exact filename (avoids title-casing mismatches)
            meta_entry = next(
                (m for m in all_meta.values() if m.get("file") == fname),
                None,
            )
            if meta_entry:
                index_data.append(meta_entry)
                continue

            # Fallback: derive slug from all_questions list
            title = fname[:-5]
            slug = next(
                (q["titleSlug"] for q in all_questions
                 if safe_filename(q["title"]).lower() == title.lower()),
                None,
            )
            if slug and slug in all_meta:
                index_data.append(all_meta[slug])
            else:
                index_data.append({
                    "title": title,
                    "slug": slug or "",
                    "difficulty": "",
                    "companies": [],
                    "file": fname,
                    "url": f"https://leetcode.com/problems/{slug}/" if slug else "",
                })

    index_json = json.dumps(index_data, ensure_ascii=False)
    with open(os.path.join(save_path, "questions", "index.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<body>
{attach_page_nav()}
<h2>Questions - <span id="qCount"></span></h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin:12px 0;align-items:center">
  <input class="lc-search" id="qSearch" placeholder="Search title or company..." style="max-width:320px" type="text"/>
  <div style="display:flex;gap:4px">
    <button class="diff-btn active" data-diff="all">All</button>
    <button class="diff-btn" data-diff="Easy">Easy</button>
    <button class="diff-btn" data-diff="Medium">Medium</button>
    <button class="diff-btn" data-diff="Hard">Hard</button>
  </div>
</div>
<table class="table table-bordered table-hover table-color" id="qTable">
  <thead><tr>
    <th style="width:40px">#</th>
    <th class="sortable" data-key="title" style="cursor:pointer">Title &#x2195;</th>
    <th class="sortable" data-key="difficulty" style="cursor:pointer;width:100px;text-align:center">Difficulty &#x2195;</th>
    <th>Companies</th>
    <th style="width:50px">Link</th>
  </tr></thead>
  <tbody id="qBody"></tbody>
</table>
<script>
var DATA = {index_json};
var sortKey = null, sortDir = 1, diffFilter = 'all';
function renderTable() {{
    var q = document.getElementById('qSearch').value.toLowerCase();
    var filtered = DATA.filter(function(d) {{
        var matchQ = !q || d.title.toLowerCase().includes(q) ||
                     (d.companies || []).join(' ').toLowerCase().includes(q);
        var matchD = diffFilter === 'all' || d.difficulty === diffFilter;
        return matchQ && matchD;
    }});
    if (sortKey) {{
        filtered.sort(function(a, b) {{
            var av = (a[sortKey] || '').toLowerCase();
            var bv = (b[sortKey] || '').toLowerCase();
            return av < bv ? -sortDir : av > bv ? sortDir : 0;
        }});
    }}
    var tbody = document.getElementById('qBody');
    tbody.innerHTML = filtered.map(function(d, i) {{
        var dc = d.difficulty === 'Easy' ? 'badge-easy'
               : d.difficulty === 'Medium' ? 'badge-medium'
               : d.difficulty === 'Hard' ? 'badge-hard' : '';
        var comps = (d.companies || []).map(function(c) {{
            return '<span class="company-tag">' + c + '</span>';
        }}).join('');
        var link = d.url ? '<a target="_blank" href="' + d.url + '"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></a>' : '';
        return '<tr>' +
            '<td style="text-align:center">' + (i+1) + '</td>' +
            '<td><a href="' + d.file + '">' + d.title + '</a></td>' +
            '<td style="text-align:center"><span class="' + dc + '">' + (d.difficulty || '&#x2014;') + '</span></td>' +
            '<td>' + comps + '</td>' +
            '<td style="text-align:center">' + link + '</td>' +
            '</tr>';
    }}).join('');
    document.getElementById('qCount').textContent = filtered.length + ' / ' + DATA.length;
}}
document.getElementById('qSearch').addEventListener('input', renderTable);
document.querySelectorAll('.diff-btn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
        diffFilter = this.dataset.diff;
        document.querySelectorAll('.diff-btn').forEach(function(b) {{ b.classList.remove('active'); }});
        this.classList.add('active');
        renderTable();
    }});
}});
document.querySelectorAll('.sortable').forEach(function(th) {{
    th.addEventListener('click', function() {{
        var k = this.dataset.key;
        if (sortKey === k) {{ sortDir *= -1; }} else {{ sortKey = k; sortDir = 1; }}
        renderTable();
    }});
}});
renderTable();
</script>
</body>
</html>""")
