import logging
import os

from bs4 import BeautifulSoup

from scraper.api import create_headers, fetch_company_tags, fetch_company_favorite_meta, fetch_company_questions
from scraper.config import load_config
from scraper.utils import create_folder, safe_filename
from scraper.html.builder import attach_header_in_html, attach_page_nav
from scraper.html.indexes import _ensure_base_index
from scraper.scrapers.questions import create_question_html

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Index builders
# ---------------------------------------------------------------------------

def create_all_company_index_html(company_tags: list, headers, save_path: str, company_tag_save_path: str, overwrite: bool) -> None:
    log.info("Creating company index.html")
    cards_html = ""
    with open(company_tag_save_path, "w", encoding="utf-8") as f:
        for company in company_tags:
            cards_html += f'<a class="company-card" href="{company["slug"]}/index.html">{company["slug"]}</a>'
            f.write(f"https://leetcode.com/company/{company['slug']}/\n")

    with open(os.path.join(save_path, "all_company_questions", "index.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<body>
{attach_page_nav()}
<h2>All Company Questions</h2>
<input class="lc-search" id="companySearch" onkeyup="filterCompanies()" placeholder="Search company..." type="text"/>
<div class="company-grid" id="companyGrid">{cards_html}</div>
<script>
function filterCompanies() {{
    var q = document.getElementById('companySearch').value.toLowerCase();
    document.querySelectorAll('#companyGrid .company-card').forEach(function(el) {{
        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
}}
</script>
</body>
</html>""")

    try:
        for company in company_tags:
            slug = company["slug"]
            company_dir = os.path.join(save_path, "all_company_questions", slug)
            create_folder(company_dir)
            if (
                slug in os.listdir(os.path.join(save_path, "all_company_questions"))
                and not overwrite
                and "index.html" in os.listdir(company_dir)
            ):
                log.info("Already scraped: %s", slug)
                os.chdir("..")
                continue

            log.info("Scraping index for: %s", slug)
            meta = fetch_company_favorite_meta(headers, slug)
            total_questions = meta["questionNumber"]
            categories_to_slugs = meta["generatedFavoritesInfo"]["categoriesToSlugs"]
            favorite_slug = slug + "-all"
            for category in categories_to_slugs:
                if "all" in category["categoryName"]:
                    favorite_slug = category["favoriteSlug"]
                    break

            questions = fetch_company_questions(headers, favorite_slug, total_questions)
            log.info("Successfully scraped index for: %s", slug)

            max_freq = max((float(q["frequency"]) for q in questions), default=1) or 1
            html = ""
            for idx, question in enumerate(questions, start=1):
                question["title"] = safe_filename(question["title"])
                diff = question["difficulty"]
                diff_class = (
                    "badge-easy" if diff == "Easy"
                    else ("badge-medium" if diff == "Medium" else "badge-hard")
                )
                freq = float(question["frequency"])
                freq_pct = int(freq / max_freq * 100)
                html += (
                    f'<tr>'
                    f'<td style="width:40px;text-align:center">{idx}</td>'
                    f'<td><a slug="{question["titleSlug"]}" title="{question["title"]}.html" '
                    f'href="../../questions/{question["title"]}.html">{question["title"]}</a></td>'
                    f'<td style="text-align:center"><span class="{diff_class}">{diff}</span></td>'
                    f'<td style="white-space:nowrap">'
                    f'<span style="margin-right:6px">{freq:.2f}</span>'
                    f'<span class="freq-bar-wrap"><span class="freq-bar" style="width:{freq_pct}%"></span></span>'
                    f'</td>'
                    f'<td><a target="_blank" href="https://leetcode.com/problems/{question["titleSlug"]}">'
                    f'<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
                    f'<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
                    f'<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>'
                    f'</a></td>'
                    f'</tr>'
                )

            with open(os.path.join(save_path, "all_company_questions", slug, "index.html"), "w", encoding="utf-8") as f:
                f.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<body>
{attach_page_nav()}
<h2>{slug} - {len(questions)} Questions</h2>
<input class="lc-search" id="qSearch" onkeyup="filterQ()" placeholder="Search question..." type="text"/>
<table class="table table-bordered table-hover table-color" id="qTable" style="margin-top:10px">
  <thead><tr>
    <th style="width:40px">#</th>
    <th>Title</th>
    <th style="width:90px;text-align:center">Difficulty</th>
    <th style="width:140px">Frequency</th>
    <th style="width:50px">Link</th>
  </tr></thead>
  <tbody>{{html}}</tbody>
</table>
<script>
function filterQ() {{
    var q = document.getElementById('qSearch').value.toLowerCase();
    document.querySelectorAll('#qTable tbody tr').forEach(function(row) {{
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
}}
</script>
</body>
</html>""".replace("{html}", html))
            os.chdir("..")
    except KeyboardInterrupt:
        log.warning("Interrupted — building index with companies scraped so far.")
        try:
            os.chdir("..")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Question scraping for a company's index page
# ---------------------------------------------------------------------------

def scrape_question_data(slug: str, headers, html: str) -> None:
    log.info("Scraping question data for company: %s", slug)
    config = load_config()
    save_path = config["save_path"]
    overwrite = config["overwrite"]
    save_images_locally = config["save_images_locally"]

    question_titles = BeautifulSoup(html, "html.parser").find_all("a", title=True)
    questions_dir = os.path.join(save_path, "questions")
    os.makedirs(questions_dir, exist_ok=True)

    prev_dir = os.getcwd()
    for qtag in question_titles:
        qtag["title"] = safe_filename(qtag["title"])
        questions_file = os.path.join(questions_dir, qtag["title"])

        if os.path.isfile(questions_file) and not overwrite:
            log.info("Already in questions/: %s", qtag["title"])
            continue

        log.info("Scraping: %s", qtag["title"])
        os.chdir(questions_dir)
        create_question_html(qtag["slug"], headers, save_path, save_images_locally)

    os.chdir(prev_dir)


# ---------------------------------------------------------------------------
# Bulk scrapers
# ---------------------------------------------------------------------------

def scrape_all_company_questions(mode: str) -> None:
    """mode: 'index' → fetch all companies from API, write file, build index HTMLs.
       mode: 'full'  → read company slugs from file, scrape their questions.
    """
    log.info("Scraping all company questions (mode=%s)", mode)
    config = load_config()
    leetcode_cookie = config["leetcode_cookie"]
    save_path = config["save_path"]
    overwrite = config["overwrite"]
    company_tag_save_path = config["company_tag_save_path"]
    headers = create_headers(leetcode_cookie)

    create_folder(os.path.join(save_path, "all_company_questions"))

    if mode == "index":
        # Fetch full company list from API, write to file, build index pages
        company_tags = fetch_company_tags(headers)
        create_all_company_index_html(company_tags, headers, save_path, company_tag_save_path, overwrite)
    elif mode == "full":
        # Read slugs from the text file populated by a previous 'index' run
        with open(company_tag_save_path, "r", encoding="utf-8") as f:
            company_tags = [
                {"name": (slug := line.strip().rstrip("/").split("/")[-1]), "slug": slug}
                for line in f if line.strip()
            ]
        try:
            for company in company_tags:
                slug = company["slug"]
                idx_path = os.path.join(save_path, "all_company_questions", slug, "index.html")
                if os.path.exists(idx_path):
                    create_folder(os.path.join(save_path, "all_company_questions", slug))
                    with open(idx_path, "r", encoding="utf-8") as f:
                        html = f.read()
                    scrape_question_data(slug, headers, html)
                    os.chdir("..")
        except KeyboardInterrupt:
            log.warning("Interrupted — building index with companies scraped so far.")
            try:
                os.chdir("..")
            except Exception:
                pass

    os.chdir("..")
    _ensure_base_index()


def scrape_selected_company_questions(mode: str) -> None:
    """mode: 'index' → build company index HTML only; 'full' → also scrape questions."""
    config = load_config()
    leetcode_cookie = config["leetcode_cookie"]
    save_path = config["save_path"]
    company_tag_save_path = config["company_tag_save_path"]
    overwrite = config["overwrite"]
    headers = create_headers(leetcode_cookie)

    create_folder(os.path.join(save_path, "all_company_questions"))
    final_company_tags = []
    with open(company_tag_save_path, "r", encoding="utf-8") as f:
        for line in f:
            slug = line.strip().rstrip("/").split("/")[-1]
            if slug:
                final_company_tags.append({"name": slug, "slug": slug})

    if mode == "index":
        create_all_company_index_html(final_company_tags, headers, save_path, company_tag_save_path, overwrite)
    elif mode == "full":
        try:
            for company in final_company_tags:
                slug = company["slug"]
                idx_path = os.path.join(save_path, "all_company_questions", slug, "index.html")
                create_folder(os.path.join(save_path, "all_company_questions", slug))
                if os.path.exists(idx_path):
                    with open(idx_path, "r", encoding="utf-8") as f:
                        html = f.read()
                    scrape_question_data(slug, headers, html)
                os.chdir("..")
        except KeyboardInterrupt:
            log.warning("Interrupted — building index with selected companies scraped so far.")
            try:
                os.chdir("..")
            except Exception:
                pass
    os.chdir("..")


# ---------------------------------------------------------------------------
# Single-company scraper (new)
# ---------------------------------------------------------------------------

def scrape_single_company(url_or_slug: str) -> None:
    """Scrape all questions for one company by slug or URL.

    Examples:
        scrape_single_company("google")
        scrape_single_company("https://leetcode.com/company/google/")
    """
    config = load_config()
    leetcode_cookie = config["leetcode_cookie"]
    save_path = config["save_path"]
    overwrite = config["overwrite"]
    company_tag_save_path = config["company_tag_save_path"]
    headers = create_headers(leetcode_cookie)

    slug = url_or_slug.rstrip("/").split("/")[-1]
    company_dir = os.path.join(save_path, "all_company_questions", slug)
    os.makedirs(company_dir, exist_ok=True)

    log.info("Building index for company: %s", slug)
    create_all_company_index_html([{"name": slug, "slug": slug}], headers, save_path, company_tag_save_path, overwrite)

    idx_path = os.path.join(save_path, "all_company_questions", slug, "index.html")
    if os.path.exists(idx_path):
        create_folder(company_dir)
        with open(idx_path, "r", encoding="utf-8") as f:
            html = f.read()
        log.info("Scraping questions for company: %s", slug)
        scrape_question_data(slug, headers, html)
        os.chdir("..")

    _ensure_base_index()
    log.info("Done — company '%s'.", slug)
