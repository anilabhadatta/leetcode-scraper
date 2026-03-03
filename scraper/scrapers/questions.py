import json
import logging
import os

from bs4 import BeautifulSoup

from scraper.api import create_headers, fetch_questions_count, fetch_all_questions
from scraper.config import load_config

log = logging.getLogger(__name__)
from scraper.utils import create_folder, safe_filename, copy_html
from scraper.html.builder import attach_header_in_html
from scraper.html.assets import fix_image_urls
from scraper.html.slides import find_slides_json, place_solution_slides
from scraper.html.renderer import get_question_data, replace_iframes_with_codes
from scraper.html.indexes import _ensure_base_index, create_question_index_html


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def get_all_questions_url(write_to_file: bool = True) -> list:
    """Fetch all question slugs/titles from LeetCode.

    Args:
        write_to_file: If True, write URLs to the configured questions_url_path.

    Returns:
        List of {title, titleSlug} dicts.
    """
    log.info("Fetching all questions URL")
    config = load_config()
    headers = create_headers()
    total = fetch_questions_count(headers)
    log.info("Total questions: %d", total)
    all_questions = fetch_all_questions(headers, total)

    if write_to_file:
        _write_questions_to_file(all_questions, config["questions_url_path"])
    return all_questions


def _write_questions_to_file(questions: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(f"https://leetcode.com/problems/{q['titleSlug']}/\n")


# ---------------------------------------------------------------------------
# HTML generation helpers
# ---------------------------------------------------------------------------

def create_question_html(question_slug: str, headers, save_path: str, save_images_locally: bool) -> dict:
    """Render and write a question's HTML file.  Returns the meta dict."""
    item_content = {"question": {"titleSlug": question_slug}}
    content = "<body>"
    question_content, question_title, meta = get_question_data(item_content, headers)
    content += question_content + "</body>"
    slides_json = find_slides_json(content)
    content = attach_header_in_html() + content
    soup = BeautifulSoup(content, "html.parser")
    soup = replace_iframes_with_codes(soup, headers)
    soup = place_solution_slides(soup, slides_json)
    soup = fix_image_urls(soup, save_images_locally)
    with open(f"{question_title}.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    # Update meta.json
    meta_path = os.path.join(save_path, "questions", "meta.json")
    try:
        all_meta: dict = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as mf:
                all_meta = json.load(mf)
        all_meta[question_slug] = meta
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(all_meta, mf, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.warning("Error updating meta.json: %s", exc)
    return meta


# ---------------------------------------------------------------------------
# Bulk scrapers
# ---------------------------------------------------------------------------

def scrape_question_url() -> None:
    """Scrape questions listed in the configured questions_url_path text file."""
    config = load_config()
    leetcode_cookie = config["leetcode_cookie"]
    save_path = config["save_path"]
    overwrite = config["overwrite"]
    save_images_locally = config["save_images_locally"]
    questions_url_path = config["questions_url_path"]
    headers = create_headers(leetcode_cookie)

    with open(questions_url_path, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Derive {title, titleSlug} from each URL line
    all_questions = [
        {
            "titleSlug": url.rstrip("/").split("/")[-1],
            "title": url.rstrip("/").split("/")[-1].replace("-", " ").title(),
        }
        for url in urls
    ]

    create_folder(os.path.join(save_path, "questions"))
    existing = set(os.listdir(os.path.join(save_path, "questions")))

    # Load meta.json for reliable slug-based skip check
    meta_path = os.path.join(save_path, "questions", "meta.json")
    all_meta: dict = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as _mf:
            all_meta = json.load(_mf)

    try:
        for question in all_questions:
            slug = question["titleSlug"]
            # Skip only when meta entry exists AND the file is actually on disk
            if not overwrite and slug in all_meta:
                saved_file = all_meta[slug].get("file", "")
                if saved_file and saved_file in existing:
                    log.info("Already scraped %s", slug)
                    continue
            # Fallback: probable filename check (handles meta.json missing/corrupt)
            probable_title = safe_filename(question["title"])
            if not overwrite and f"{probable_title}.html" in existing:
                log.info("Already scraped %s.html (filename match)", probable_title)
                continue
            log.info("Scraping question: %s", slug)
            create_question_html(slug, headers, save_path, save_images_locally)
    except KeyboardInterrupt:
        log.warning("Interrupted — building index with questions scraped so far.")

    os.chdir("..")
    create_question_index_html(save_path, all_questions)
    _ensure_base_index()


# ---------------------------------------------------------------------------
# Single-URL scraper (new)
# ---------------------------------------------------------------------------

def scrape_single_question(url_or_slug: str) -> None:
    """Scrape a single question by its LeetCode URL or title-slug.

    Examples:
        scrape_single_question("two-sum")
        scrape_single_question("https://leetcode.com/problems/two-sum/")
    """
    config = load_config()
    leetcode_cookie = config["leetcode_cookie"]
    save_path = config["save_path"]
    save_images_locally = config["save_images_locally"]
    headers = create_headers(leetcode_cookie)

    # Normalise: extract slug from URL if needed
    slug = url_or_slug.rstrip("/").split("/")[-1]
    if slug.startswith("http"):
        raise ValueError(f"Could not parse slug from: {url_or_slug}")

    questions_dir = os.path.join(save_path, "questions")
    if not os.path.exists(questions_dir):
        os.makedirs(questions_dir)
    os.chdir(questions_dir)

    log.info("Scraping single question: %s", slug)
    meta = create_question_html(slug, headers, save_path, save_images_locally)
    log.info("Done → %s.html", meta.get('title', slug))
    os.chdir("..")
    _ensure_base_index()
