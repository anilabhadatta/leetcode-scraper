import logging
import os

import markdown2
from bs4 import BeautifulSoup

from scraper.api import create_headers, fetch_all_categories, fetch_card_chapters, fetch_card_item
from scraper.config import load_config

log = logging.getLogger(__name__)
from scraper.utils import create_folder, safe_filename, copy_html
from scraper.html.builder import attach_header_in_html, attach_page_nav
from scraper.html.assets import fix_image_urls
from scraper.html.slides import find_slides_json, place_solution_slides
from scraper.html.renderer import (
    get_question_data, get_article_data, get_html_article_data,
    replace_iframes_with_codes, create_card_index_html,
)
from scraper.html.indexes import _ensure_base_index


# ---------------------------------------------------------------------------
# Helper — fetch all card slugs
# ---------------------------------------------------------------------------

def get_all_cards_url(write_to_file: bool = True) -> list:
    """Return list of {categorySlug, slug} dicts for all LeetCode cards.

    Args:
        write_to_file: If True, write card URLs to the configured cards_url_path.
    """
    log.info("Fetching all cards URL")
    config = load_config()
    headers = create_headers()
    categories = fetch_all_categories(headers)
    all_cards = [
        card
        for category in categories
        if category["slug"] != "featured"
        for card in category["cards"]
    ]
    if write_to_file:
        with open(config["cards_url_path"], "w", encoding="utf-8") as f:
            for card in all_cards:
                f.write(
                    f"https://leetcode.com/explore/{card['categorySlug']}/card/{card['slug']}/\n"
                )
    return all_cards


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def create_card_html(
    item_content: dict,
    item_title: str,
    item_id: str,
    headers,
    save_images_locally: bool,
) -> None:
    content = "<body>"
    question_content, _, _ = get_question_data(item_content, headers)
    content += question_content
    content += get_article_data(item_content, item_title, headers)
    content += get_html_article_data(item_content, item_title, headers)
    content += "</body>"
    slides_json = find_slides_json(content)
    content = markdown2.markdown(content)
    content = attach_header_in_html() + content
    soup = BeautifulSoup(content, "html.parser")
    soup = replace_iframes_with_codes(soup, headers)
    soup = place_solution_slides(soup, slides_json)
    soup = fix_image_urls(soup, save_images_locally)
    with open(f"{item_id}-{item_title}.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())


# ---------------------------------------------------------------------------
# Bulk scraper
# ---------------------------------------------------------------------------

def scrape_card_url() -> None:
    config = load_config()
    leetcode_cookie = config["leetcode_cookie"]
    save_path = config["save_path"]
    overwrite = config["overwrite"]
    save_images_locally = config["save_images_locally"]
    cards_url_path = config["cards_url_path"]
    headers = create_headers(leetcode_cookie)

    create_folder(os.path.join(save_path, "cards"))
    if "questions" not in os.listdir(save_path):
        os.makedirs(os.path.join(save_path, "questions"), exist_ok=True)

    # ── Build cards/index.html ──
    with open(cards_url_path, "r", encoding="utf-8") as f:
        card_urls = [u.strip() for u in f.readlines() if u.strip()]

    cards_html = ""
    for card_url in card_urls:
        parts = card_url.rstrip("/").split("/")
        card_slug = parts[-1]
        category_slug = parts[-3] if len(parts) >= 3 else ""
        label = card_slug.replace("-", " ").title()
        category_label = category_slug.replace("-", " ").title()
        cards_html += (
            f'<a class="company-card" href="{card_slug}/index.html" data-cat="{category_slug}">'
            f'<span class="card-cat">{category_label}</span>{label}</a>'
        )

    with open(os.path.join(save_path, "cards", "index.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<style>
  .card-cat {{ display:block; font-size:0.7em; color:#6b7280; margin-bottom:2px; text-transform:uppercase; letter-spacing:.05em; }}
  .dark .card-cat {{ color:#9ca3af; }}
  .company-card {{ flex-direction:column; align-items:flex-start; }}
</style>
<body>
{attach_page_nav()}
<h2>Cards Index</h2>
<input class="lc-search" id="cardSearch" onkeyup="filterCards()" placeholder="Search cards..." type="text"/>
<div class="company-grid" id="cardGrid">{cards_html}</div>
<script>
function filterCards() {{
    var q = document.getElementById('cardSearch').value.toLowerCase();
    document.querySelectorAll('#cardGrid .company-card').forEach(function(el) {{
        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
}}
</script>
</body>
</html>""")

    # ── Scrape each card ──
    try:
        for card_url in card_urls:
            card_url = card_url.strip()
            log.info("Scraping card URL: %s", card_url)
            card_slug = card_url.split("/")[-2]
            chapters = fetch_card_chapters(headers, card_slug)
            if not chapters:
                continue

            create_folder(os.path.join(save_path, "cards", card_slug))
            create_card_index_html(chapters, card_slug, headers)

            for subcategory in chapters:
                log.info("Scraping subcategory: %s", subcategory["title"])
                for item in subcategory["items"]:
                    log.info("  Scraping item: %s", item["title"])
                    item_id = item["id"]
                    item_title = safe_filename(item["title"])

                    if (
                        f"{item_id}-{item_title}.html" in os.listdir(os.path.join(save_path, "cards", card_slug))
                        and not overwrite
                    ):
                        log.info("Already scraped %s-%s.html", item_id, item_title)
                        continue

                    if f"{item_title}.html" in os.listdir(os.path.join(save_path, "questions")) and not overwrite:
                        log.info("Copying from questions folder: %s", item_title)
                        copy_html(
                            os.path.join(save_path, "questions", f"{item_title}.html"),
                            os.path.join(save_path, "cards", card_slug),
                        )
                        try:
                            os.rename(
                                os.path.join(save_path, "cards", card_slug, f"{item_title}.html"),
                                os.path.join(save_path, "cards", card_slug, f"{item_id}-{item_title}.html"),
                            )
                        except Exception:
                            pass
                        continue

                    item_content = fetch_card_item(headers, str(item_id))
                    if item_content is None:
                        break
                    create_card_html(item_content, item_title, item_id, headers, save_images_locally)
            os.chdir("..")
    except KeyboardInterrupt:
        log.warning("Interrupted — building index with cards scraped so far.")
        try:
            os.chdir("..")
        except Exception:
            pass

    os.chdir("..")
    _ensure_base_index()


# ---------------------------------------------------------------------------
# Single-URL scraper (new)
# ---------------------------------------------------------------------------

def scrape_single_card(url_or_slug: str) -> None:
    """Scrape a single card (all chapters) by its slug or URL.

    Examples:
        scrape_single_card("heap")
        scrape_single_card("https://leetcode.com/explore/learn/card/heap/")
    """
    config = load_config()
    leetcode_cookie = config["leetcode_cookie"]
    save_path = config["save_path"]
    save_images_locally = config["save_images_locally"]
    overwrite = config["overwrite"]
    headers = create_headers(leetcode_cookie)

    # Normalise slug
    slug = url_or_slug.rstrip("/").split("/")[-1]

    cards_dir = os.path.join(save_path, "cards")
    os.makedirs(cards_dir, exist_ok=True)
    create_folder(os.path.join(save_path, "cards", slug))

    chapters = fetch_card_chapters(headers, slug)
    if not chapters:
        log.warning("No chapters found for card: %s", slug)
        os.chdir("..")
        return

    create_card_index_html(chapters, slug, headers)
    for chapter in chapters:
        for item in chapter["items"]:
            item_id = item["id"]
            item_title = safe_filename(item["title"])
            if f"{item_id}-{item_title}.html" in os.listdir() and not overwrite:
                log.info("Already scraped %s-%s.html", item_id, item_title)
                continue
            item_content = fetch_card_item(headers, str(item_id))
            if item_content is None:
                continue
            create_card_html(item_content, item_title, item_id, headers, save_images_locally)
            log.info("  Done → %s-%s.html", item_id, item_title)
    os.chdir("..")
    log.info("Card '%s' done.", slug)
    _ensure_base_index()
