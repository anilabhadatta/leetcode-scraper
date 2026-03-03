import requests
import json
from requests.structures import CaseInsensitiveDict
from bs4 import BeautifulSoup
import markdown2
import cloudscraper
import re
import base64
import os
import sys
import shutil
import argparse

OS_ROOT = os.path.expanduser('~')
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def clear():
    global current_os
    if current_os.startswith('darwin'):
        os.system('clear')
    elif current_os.startswith('linux'):
        os.system('clear')
    elif current_os.startswith('win32') or current_os.startswith('cygwin'):
        os.system('cls')


def create_base_config_dir():
    base_config_path = os.path.join(OS_ROOT, ".leetcode-scraper")
    if ".leetcode-scraper" not in os.listdir(OS_ROOT):
        os.mkdir(base_config_path)
    return base_config_path


def create_folder(path):
    if not os.path.exists(path):
        os.mkdir(path)
    os.chdir(path)


def select_config():
    global selected_config
    base_config_path = create_base_config_dir()
    print("\nIf you are creating a new config, Please select 1 in Main Menu to setup the new config\n")

    if len(os.listdir(base_config_path)) > 0:
        for configs in os.listdir(base_config_path):
            if ".json" in configs:
                print(configs)
        selected_config = input(
            "\nSelect a config or Enter a number to create a new config: ") or "0"


def generate_config():
    clear()
    base_config_path = create_base_config_dir()
    print(f'''
        Leave Blank and press Enter if you don't want to overwrite Previous Values
        Config Save Folder: {os.path.join(base_config_path, f"config_{selected_config}.json")}
    ''')
    try:
        leetcode_cookie, cards_url_path, questions_url_path, save_path, save_images_locally, overwrite, company_tag_save_path = load_config()
    except Exception:
        print('''
                    Config doesnt exist, Creating a new one.
                    Enter the paths for your config
            ''')
    leetcode_cookie = input(
        "Enter the LEETCODE_SESSION Cookie Value: ") or leetcode_cookie
    cards_url_path = input("Enter Cards url Save Path: ") or cards_url_path
    questions_url_path = input(
        "Enter Questions url Save Path: ") or questions_url_path
    save_path = input("Enter Save Path: ") or save_path
    company_tag_save_path = input(
        "Enter Company Tag Save Path: ") or company_tag_save_path
    save_images_locally = bool(
        input("Save images locally as base64 T/F? ") == 'T')
    overwrite = bool(input("Overwrite existing files T/F? ") == 'T')

    with open(os.path.join(base_config_path, f"config_{selected_config}.json"), "w+", encoding="utf-8") as config_file:
        json.dump({
            "leetcode_cookie": leetcode_cookie,
            "cards_url_path": cards_url_path,
            "questions_url_path": questions_url_path,
            "save_path": save_path,
            "save_images_locally": save_images_locally,
            "overwrite": overwrite,
            "company_tag_save_path": company_tag_save_path
        }, config_file)


def load_config():
    config_path = os.path.join(OS_ROOT, ".leetcode-scraper")
    if ".leetcode-scraper" not in os.listdir(OS_ROOT) or f"config_{selected_config}.json" not in os.listdir(config_path):
        raise Exception("No config found, Please create one")
    with open(os.path.join(config_path, f"config_{selected_config}.json"), "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    if len(config) != 7:
        raise Exception("Config is corrupted, Please recreate the config")
    leetcode_cookie = config["leetcode_cookie"]
    cards_url_path = config["cards_url_path"]
    questions_url_path = config["questions_url_path"]
    save_path = config["save_path"]
    company_tag_save_path = config["company_tag_save_path"]
    save_images_locally = bool(config["save_images_locally"])
    overwrite = bool(config["overwrite"])
    return leetcode_cookie, cards_url_path, questions_url_path, save_path, save_images_locally, overwrite, company_tag_save_path


def create_headers(leetcode_cookie=""):
    headers = CaseInsensitiveDict()
    headers["content-type"] = "application/json"
    headers['cookie'] = "LEETCODE_SESSION=" + \
        leetcode_cookie if leetcode_cookie != "" else ""
    headers["referer"] = "https://leetcode.com/"
    headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"
    headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    # headers["accept-encoding"] = "gzip, deflate, br, zstd"
    return headers


def lc_post(headers, json_data):
    """Wrapper for every LeetCode GraphQL request.
    If the headers contain a cookie, calls getUserStatus first to verify sign-in and premium state."""
    has_cookie = bool(headers.get('cookie', '').strip())
    if has_cookie:
        status_data = {
            "operationName": "getUserStatus",
            "variables": {},
            "query": "query getUserStatus {\n  userStatus {\n    username\n    isSignedIn\n    isPremium\n  }\n}\n"
        }
        status_resp = json.loads(requests.post(url=url, headers=headers, json=status_data).content)
        user_status = status_resp['data']['userStatus']
        is_signed_in = user_status.get('isSignedIn', False)
        is_premium = user_status.get('isPremium', False)
        username = user_status.get('username', 'Unknown')
        if not is_signed_in:
            raise Exception(
                f"Not signed in (username: '{username}'). "
                "Please update your LEETCODE_SESSION cookie in the config (option 1)."
            )
        if not is_premium:
            raise Exception(
                f"Account '{username}' does not have LeetCode Premium. "
                "A Premium subscription is required to scrape this content."
            )
    return json.loads(requests.post(url=url, headers=headers, json=json_data).content)


def get_all_cards_url():
    print("Getting all cards url")
    _, cards_url_path, _, _, _, _, _ = load_config()
    headers = create_headers()
    cards_data = {"operationName": "GetCategories", "variables": {
        "num": 1000}, "query": "query GetCategories($categorySlug: String, $num: Int) {\n  categories(slug: $categorySlug) {\n  slug\n    cards(num: $num) {\n ...CardDetailFragment\n }\n  }\n  }\n\nfragment CardDetailFragment on CardNode {\n   slug\n  categorySlug\n  }\n"}
    cards = lc_post(headers, cards_data)['data']['categories']
    with open(cards_url_path, "w", encoding="utf-8") as f:
        for category_card in cards:
            if category_card['slug'] != "featured":
                for card in category_card['cards']:
                    card_url = "https://leetcode.com/explore/" + \
                        card['categorySlug'] + "/card/" + card['slug'] + "/\n"
                    f.write(card_url)


def get_all_questions_url(self_function=True):
    print("Getting all questions url")
    _, _, questions_url_path, _, _, _, _ = load_config()
    headers = create_headers()
    question_count_data = {
        "query": "\n query getQuestionsCount {allQuestionsCount {\n    difficulty\n    count\n }} \n    "}
    all_questions_count = lc_post(headers, question_count_data)['data']['allQuestionsCount'][0]['count']
    print("Total no of questions: ", all_questions_count)

    PAGE_SIZE = 100
    all_questions = []
    skip = 0
    while skip < all_questions_count:
        print(f"Fetching questions {skip + 1} - {min(skip + PAGE_SIZE, all_questions_count)} / {all_questions_count}")
        question_data = {"query": "\n query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {\n  problemsetQuestionList: questionList(\n    categorySlug: $categorySlug\n    limit: $limit\n    skip: $skip\n    filters: $filters\n  ) {\n  questions: data {\n title\n titleSlug\n  }\n  }\n}\n    ", "variables": {
            "categorySlug": "", "skip": skip, "limit": PAGE_SIZE, "filters": {}}}
        page = lc_post(headers, question_data)['data']['problemsetQuestionList']['questions']
        if not page:
            break
        all_questions.extend(page)
        skip += PAGE_SIZE

    print(f"Total questions fetched: {len(all_questions)}")
    if not self_function:
        return all_questions
    write_questions_to_file(all_questions, questions_url_path)


def write_questions_to_file(all_questions, questions_url_path):
    with open(questions_url_path, "w", encoding="utf-8") as f:
        for question in all_questions:
            question_url = "https://leetcode.com/problems/" + \
                question['titleSlug'] + "/\n"
            f.write(question_url)


def scrape_question_url():
    leetcode_cookie, _, questions_url_path, save_path, _, overwrite, _ = load_config()
    headers = create_headers(leetcode_cookie)
    all_questions = get_all_questions_url(self_function=False)
    create_folder(os.path.join(save_path, "questions"))
    with open(questions_url_path, "r", encoding="utf-8") as f:
        question_urls = f.readlines()
        for idx, question_url in enumerate(question_urls, start=1):
            question_url = question_url.strip()
            question_slug = question_url.split("/")[-2]
            for question in all_questions:
                if question['titleSlug'] == question_slug:
                    question_title = re.sub(r'[:?|></\\]', replace_filename, question['title'])
                    break
            if f"{question_title}.html" in os.listdir(os.path.join(save_path, "questions")) and overwrite == False:
                print(f"Already scraped {question_title}.html")
                continue
            print("Scraping question url: ", question_url)
            create_question_html(question_slug, headers)
            
    meta_path = os.path.join(save_path, "questions", "meta.json")
    all_meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            all_meta = json.load(mf)
    index_data = []
    questions_folder = os.path.join(save_path, "questions")
    for fname in sorted(os.listdir(questions_folder)):
        if fname.endswith('.html') and fname != 'index.html':
            title = fname[:-5]
            slug = next((q['titleSlug'] for q in all_questions
                         if re.sub(r'[:?|></\\]', replace_filename, q['title']) == title), None)
            if slug and slug in all_meta:
                index_data.append(all_meta[slug])
            else:
                index_data.append({'title': title, 'slug': slug or '', 'difficulty': '',
                                   'companies': [], 'file': fname,
                                   'url': f'https://leetcode.com/problems/{slug}/' if slug else ''})
    index_json = json.dumps(index_data, ensure_ascii=False)
    with open(os.path.join(save_path, "questions", "index.html"), 'w', encoding="utf-8") as main_index:
        main_index.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<body>
<div class="mode">Dark mode: <span class="change">OFF</span></div>
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
    os.chdir('..')
    _ensure_base_index()


def create_question_html(question_slug, headers):
    _, _, _, save_path, save_images_locally, _, _ = load_config()
    item_content = {"question": {'titleSlug': question_slug}}
    content = """<body>"""
    question_content, question_title, meta = get_question_data(item_content, headers)
    content += question_content
    content += """</body>"""
    slides_json = find_slides_json(content)
    content = attach_header_in_html() + content
    content_soup = BeautifulSoup(content, 'html.parser')
    content_soup = replace_iframes_with_codes(content_soup, headers)
    content_soup = place_solution_slides(content_soup, slides_json)
    content_soup = fix_image_urls(content_soup, save_images_locally)
    with open(f"{question_title}.html", 'w', encoding="utf-8") as f:
        f.write(content_soup.prettify())
    meta_path = os.path.join(save_path, "questions", "meta.json")
    try:
        all_meta = {}
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as mf:
                all_meta = json.load(mf)
        all_meta[question_slug] = meta
        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(all_meta, mf, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error updating meta.json: ", e)
    return meta


def scrape_card_url():
    leetcode_cookie, cards_url_path, _, save_path, _, overwrite, _ = load_config()
    headers = create_headers(leetcode_cookie)
    create_folder(os.path.join(save_path, "cards"))
    if "questions" not in os.listdir(save_path):
        os.mkdir(os.path.join(save_path, "questions"))
    # Creating Index for Card Folder
    with open(os.path.join(save_path, "cards", "index.html"), 'w', encoding="utf-8") as main_index:
        cards_html = ""
        with open(cards_url_path, "r", encoding="utf-8") as f:
            card_urls = f.readlines()
            for card_url in card_urls:
                card_url = card_url.strip()
                parts = card_url.rstrip("/").split("/")
                card_slug = parts[-1]
                category_slug = parts[-3] if len(parts) >= 3 else ""
                label = card_slug.replace("-", " ").title()
                category_label = category_slug.replace("-", " ").title()
                cards_html += f'''<a class="company-card" href="{card_slug}/index.html" data-cat="{category_slug}">
                    <span class="card-cat">{category_label}</span>{label}</a>'''
        main_index.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<style>
  .card-cat {{ display:block; font-size:0.7em; color:#6b7280; margin-bottom:2px; text-transform:uppercase; letter-spacing:.05em; }}
  .dark .card-cat {{ color:#9ca3af; }}
  .company-card {{ flex-direction:column; align-items:flex-start; }}
</style>
<body>
<div class="mode">Dark mode: <span class="change">OFF</span></div>
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
    # Creating HTML for each cards topics
    with open(cards_url_path, "r", encoding="utf-8") as f:
        card_urls = f.readlines()
        for card_url in card_urls:
            card_url = card_url.strip()
            print("Scraping card url: ", card_url)
            card_slug = card_url.split("/")[-2]
            card_data = {"operationName": "GetChaptersWithItems", "variables": {"cardSlug": card_slug},
                        "query": "query GetChaptersWithItems($cardSlug: String!) {\n  chapters(cardSlug: $cardSlug) {\n    ...ExtendedChapterDetail\n   }\n}\n\nfragment ExtendedChapterDetail on ChapterNode {\n  id\n  title\n  slug\n description\n items {\n    id\n    title\n  }\n }\n"}
            chapters = lc_post(headers, card_data)['data']['chapters']
            if chapters:
                create_folder(os.path.join(save_path, "cards", card_slug))
                create_card_index_html(chapters, card_slug, headers)
                for subcategory in chapters:
                    print("Scraping subcategory: ", subcategory['title'])
                    for item in subcategory['items']:
                        print("Scraping Item: ", item['title'])
                        item_id = item['id']
                        item_title = re.sub(r'[:?|></\\]', replace_filename, item['title'])

                        if f"{item_id}-{item_title}.html" in os.listdir(os.path.join(save_path, "cards", card_slug)) and overwrite == False:
                            print(f"Already scraped {item_id}-{item_title}.html")
                            if f"{item_title}.html" in os.path.join(save_path, "questions"):
                                if os.path.getsize(os.path.join(save_path, "questions", f"{item_title}.html")) > os.path.getsize(os.path.join(
                                    save_path, "cards", card_slug, f"{item_id}-{item_title}.html")):
                                    copy_html(os.path.join(save_path, "questions", f"{item_title}.html"), os.path.join(
                                    save_path, "cards", card_slug))
                                    try:
                                        os.remove(os.path.join(
                                    save_path, "cards", card_slug, f"{item_id}-{item_title}.html"))
                                    except:
                                        pass
                                    os.rename(os.path.join(save_path, "cards", card_slug, f"{item_title}.html"), os.path.join(
                                    save_path, "cards", card_slug, f"{item_id}-{item_title}.html"))
                                elif os.path.getsize(os.path.join(save_path, "questions", f"{item_title}.html")) < os.path.getsize(os.path.join(
                                    save_path, "cards", card_slug, f"{item_id}-{item_title}.html")):
                                    copy_html(os.path.join(save_path, "cards", card_slug, f"{item_id}-{item_title}.html"), os.path.join(save_path, "questions"))
                                    try:
                                        os.remove(os.path.join(save_path, "questions", f"{item_title}.html"))
                                    except:
                                        pass
                                    os.rename(os.path.join(save_path, "questions", f"{item_id}-{item_title}.html"), os.path.join(
                                save_path, "questions", f"{item_title}.html"))
                            continue
                        if f"{item_title}.html" in os.listdir(os.path.join(save_path, "questions")) and overwrite == False:
                            print("Copying from questions folder", item_title)
                            copy_html(os.path.join(save_path, "questions", f"{item_title}.html"), os.path.join(
                                save_path, "cards", card_slug))
                            os.rename(os.path.join(save_path, "cards", card_slug, f"{item_title}.html"), os.path.join(
                                save_path, "cards", card_slug, f"{item_id}-{item_title}.html"))
                            continue
                        item_data = {"operationName": "GetItem", "variables": {"itemId": f"{item_id}"},
                                    "query": "query GetItem($itemId: String!) {\n  item(id: $itemId) {\n    id\n title\n  question {\n questionId\n   title\n  titleSlug\n }\n  article {\n id\n title\n }\n  htmlArticle {\n id\n  }\n  webPage {\n id\n  }\n  }\n }\n"}
                        item_content = lc_post(headers, item_data)['data']['item']
                        if item_content == None:
                            break
                        create_card_html(
                            item_content, item_title, item_id, headers)
                os.chdir("..")
    os.chdir('..')
    _ensure_base_index()


def create_card_html(item_content, item_title, item_id, headers):
    _, _, _, _, save_images_locally, _, _ = load_config()
    content = """<body>"""
    question_content, _, _ = get_question_data(item_content, headers)
    content += question_content
    content += get_article_data(item_content, item_title, headers)
    content += get_html_article_data(item_content, item_title, headers)
    content += """</body>"""
    slides_json = find_slides_json(content)
    content = attach_header_in_html() + content
    content_soup = BeautifulSoup(content, 'html.parser')
    content_soup = replace_iframes_with_codes(content_soup, headers)
    content_soup = place_solution_slides(content_soup, slides_json)
    content_soup = fix_image_urls(content_soup, save_images_locally)
    with open(f"{item_id}-{item_title}.html", "w", encoding="utf-8") as f:
        f.write(content_soup.prettify())


def load_image_in_b64(img_url):
    print("Loading image in base64: ", img_url)
    img_ext = img_url.split('.')[-1]
    if img_ext == "svg":
        img_ext = "svg+xml"
    scraper = cloudscraper.create_scraper()
    img_data = scraper.get(url=img_url).content
    encoded_string = base64.b64encode(img_data)
    decoded_string = encoded_string.decode('utf-8')
    return f"data:image/{img_ext};base64,{decoded_string}"


def fix_image_urls(content_soup, save_images_locally):
    print("Fixing image urls")
    images = content_soup.select('img')
    for image in images:
        if image.has_attr('src') and "base64" not in image['src']:
            splitted_image_src = image['src'].split('/')
            if ".." in splitted_image_src:
                index = 0
                for idx in range(len(splitted_image_src)-1):
                    if splitted_image_src[idx] == ".." and splitted_image_src[idx+1] != "..":
                        index = idx+1
                img_url = f"https://leetcode.com/explore/{'/'.join(splitted_image_src[index:])}"
            else:
                img_url = image['src']
            if save_images_locally:
                image['src'] = load_image_in_b64(img_url)
            else:
                image['src'] = img_url
    return content_soup


def place_solution_slides(content_soup, slides_json):
    print("Placing solution slides")
    slide_p_tags = content_soup.select("p:contains('/Documents/')")
    temp = []
    for slide_p_tag in slide_p_tags:
        if len(slide_p_tag.find_all("p")) == 0 and ".json" in str(slide_p_tag) and slide_p_tag not in temp:
            # print(slide_p_tag, type(slide_p_tag))
            temp.append(slide_p_tag)
    slide_p_tags = temp
    # print(slide_p_tags)
    for slide_idx, slide_p_tag in enumerate(slide_p_tags):
        if slides_json[slide_idx] == []:
            continue
        slides_html = f"""<div id="carouselExampleControls-{slide_idx}" class="carousel slide" data-bs-ride="carousel">
                        <div  class="carousel-inner">"""
        for img_idx, img_links in enumerate(slides_json[slide_idx]):
            slides_html += f"""<div class="carousel-item {'active' if img_idx == 0 else ''}">
                                <img src="{img_links['image']}" class="d-block" alt="...">
                            </div>"""
        slides_html += f"""</div>
                            <button class="carousel-control-prev" type="button" data-bs-target="#carouselExampleControls-{slide_idx}" data-bs-slide="prev">
                                <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                                <span class="visually-hidden">Previous</span>
                            </button>
                            <button class="carousel-control-next" type="button" data-bs-target="#carouselExampleControls-{slide_idx}" data-bs-slide="next">
                                <span class="carousel-control-next-icon" aria-hidden="true"></span>
                                <span class="visually-hidden">Next</span>
                            </button>
                            </div>"""
        slide_p_tag.replace_with(BeautifulSoup(
            slides_html, 'html.parser'))
    return content_soup


def replace_iframes_with_codes(content_soup, headers):
    print("Replacing iframes with codes")
    iframes = content_soup.find_all('iframe')
    for if_idx, iframe in enumerate(iframes, start=1):
        src_url = iframe['src']
        if "playground" in src_url:
            playground_data = {"operationName": "allPlaygroundCodes",
                               "query": f"""query allPlaygroundCodes {{\n allPlaygroundCodes(uuid: \"{src_url.split('/')[-2]}\") {{\n    code\n    langSlug\n }}\n}}\n"""}
            playground_content = lc_post(headers, playground_data)['data']['allPlaygroundCodes']

            code_html = f"""<nav>
                            <div class="d-flex align-items-start">
                            <div class="nav nav-tabs" id="nav-tab" role="tablist"> """
            for code_idx in range(len(playground_content)):
                code_html += f"""
                <button class="nav-link {'active' if code_idx == 0 else ''}" id="v-pills-{if_idx}{code_idx}-tab" data-bs-toggle="tab" data-bs-target="#v-pills-{if_idx}{code_idx}" type="button" role="tab" aria-controls="v-pills-{if_idx}{code_idx}" aria-selected="true">{playground_content[code_idx]['langSlug']}</button>"""

            code_html += f"""</div></nav>
                            <div class="tab-content" id="v-pills-tabContent">"""
            for code_idx in range(len(playground_content)):

                code_html += f"""
                                <div class="tab-pane fade show {'active' if code_idx == 0 else ''}" id="v-pills-{if_idx}{code_idx}" role="tabpanel" aria-labelledby="v-pills-{if_idx}{code_idx}-tab" tabindex="{if_idx}"><code><pre>{playground_content[code_idx]['code']}</pre></code></div>
                        """
            code_html += f"""</div></div>"""
            iframe.replace_with(BeautifulSoup(
                f""" {code_html} """, 'html.parser'))
    return content_soup


def attach_header_in_html():
    print("Attaching header in html")
    return r"""<head>
                    <meta charset="UTF-8">
                    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet"/>
                    <link crossorigin="anonymous" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" integrity="sha384-rbsA2VBKQhggwzxH7pPCaAqO46MgnOM80zW1RWuH61DGLwZJEdK2Kadq2F9CUG65" rel="stylesheet"/>
                    <script crossorigin="anonymous" integrity="sha384-kenU1KFdBIe4zVF0s0G1M5b4hcpxyD9F7jL+jjXkk+Q2h455rYXK/7HAuoJl+0I4" src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js">
                    </script>
                    <script src="https://md-block.verou.me/md-block.js" type="module">
                    </script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/9000.0.1/prism.min.js">
                    </script>
                    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6">
                    </script>
                    <!-- <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3.0.1/es5/tex-mml-chtml.js"></script>-->
                    <script async="" src="https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-MML-AM_CHTML" type="text/javascript">
                    MathJax.Hub.Config({
                                        TeX: {
                                            Macros: {
                                            "exclude": "\\def\\exclude#1{}"
                                            }
                                        },
                                        tex2jax: {
                                            inlineMath: [["$", "$"], ["\\(", "\\)"], ["$$", "$$"], ["\\[", "\\]"]],
                                            processEscapes: true,
                                            processEnvironments: true,
                                            skipTags: ['script', 'noscript', 'style', 'textarea', 'pre']
                                        },
                                        CommonHTML: {
                                                            scale: 80
                                                        },
                                        });

                                        MathJax.Hub.Register.StartupHook("TeX Jax Ready", function() {
                                        MathJax.Hub.Insert(MathJax.InputJax.TeX.Definitions.macros, {
                                            exclude: "exclude"
                                        });
                                        });
                    </script>
                    <script>
                    function lcGetCookie(name) {
                        const value = '; ' + document.cookie;
                        const parts = value.split('; ' + name + '=');
                        if (parts.length === 2) return parts.pop().split(';').shift();
                        return null;
                    }
                    function lcSetCookie(name, value, days) {
                        const expires = new Date(Date.now() + days * 864e5).toUTCString();
                        document.cookie = name + '=' + value + '; expires=' + expires + '; path=/';
                    }
                    function applyDarkMode() {
                        $('body').addClass('dark');
                        $('div[style*="background: wheat;"]').addClass('dark-banner');
                        $('div[style*="background: beige;"]').addClass('dark-banner-sq');
                        $('div[id*="v-pills-tabContent"]').addClass('tab-content dark');
                        $('table').removeClass('table-color').addClass('table-color-dark');
                        $('.change').text('ON');
                    }
                    function applyLightMode() {
                        $('body').removeClass('dark');
                        $('div[style*="background: wheat;"]').removeClass('dark-banner');
                        $('div[style*="background: beige;"]').removeClass('dark-banner-sq');
                        $('div[id*="v-pills-tabContent"]').removeClass('dark').addClass('tab-content');
                        $('table').removeClass('table-color-dark').addClass('table-color');
                        $('.change').text('OFF');
                    }
                    document.addEventListener('DOMContentLoaded', function() {
                                                const carousel = document.querySelectorAll('.carousel');
                                                console.log(carousel)
                                                const items = Array.from(document.querySelectorAll('.carousel-item'));
                                                console.log(items)
                                                const maxWidth = Math.max(...items.map(item => item.querySelector('img').clientWidth));
                                                console.log(maxWidth);
                                                for (let i = 0; i < carousel.length; i++) {
                                                    carousel[i].style.width = maxWidth + 'px';            }

                                                if (lcGetCookie('lc_dark_mode') === 'true') {
                                                    applyDarkMode();
                                                }

                                                $( ".change" ).on("click", function() {
                                                if( $( "body" ).hasClass( "dark" )) {
                                                    applyLightMode();
                                                    lcSetCookie('lc_dark_mode', 'false', 365);
                                                } else {
                                                    applyDarkMode();
                                                    lcSetCookie('lc_dark_mode', 'true', 365);
                                                }
                            });
                                    });
                    </script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.4.0/jquery.min.js"></script>
                    <style>
                                body {
                                    overflow-x: hidden;
                                    background-color: lightblue;
                                    left: 10% !important;
                                    right: 10% !important;
                                    position: absolute;

                                    }
                                    .similar-questions-container {
                                        display: flex;
                                        justify-content: space-between;
                                        }

                                        .left::after {
                                        content: "-";
                                        margin-left: 5px;
                                        }

                                        .right::before {
                                        content: "-";
                                        margin-right: 5px;
                                        }
                                    .mode {
                                        float:right;
                                    }
                                    .dark.tab-content{
                                            background-color: #00000036 !important;
                                    }
                                    .dark-banner-sq{
                                            background-color: #3b3451b8 !important;
                                    }
                                    .tab-content{
                                        background: cornsilk !important;
                                    }
                                    .change {
                                        cursor: pointer;
                                        border: 1px solid #555;
                                        border-radius: 40%;
                                        width: 20px;
                                        text-align: center;
                                        padding: 5px;
                                        margin-left: 8px;
                                    }
                                    .dark{
                                        background-color: #222;
                                        color: #e6e6e6;
                                    }
                                    .dark-banner{
                                        background-color: darkslategray !important;
                                        color: #e6e6e6 !important;
                                    }
                                    .carousel-control-prev > span,
                                    .carousel-control-next > span {
                                    background-color: #007bff; 
                                    border-color: #007bff; 
                                    }
                                    img {
                                        width: auto;
                                        height: auto;
                                        max-width: 100%;
                                        max-height: 100%;
                                    }
                                    .dark img {
                                        filter: invert(0.867) hue-rotate(180deg);
                                    }
                                    /* ── Tables ── */
                                    .table-color { background-color: #fff; color: #222; }
                                    .table-color-dark { background-color: #2c2c2c; color: #e6e6e6; }
                                    .table-color td, .table-color th { border-color: #dee2e6 !important; }
                                    .table-color-dark td, .table-color-dark th { border-color: #444 !important; color: #e6e6e6; }
                                    /* ── Difficulty badges ── */
                                    .badge-easy   { background-color: #00b8a3; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
                                    .badge-medium { background-color: #ffc01e; color: #333; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
                                    .badge-hard   { background-color: #ef4743; color: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }
                                    .dark .badge-easy   { background-color: #007d72; }
                                    .dark .badge-medium { background-color: #b38600; color: #eee; }
                                    .dark .badge-hard   { background-color: #b02e2c; }
                                    /* ── Frequency bar ── */
                                    .freq-bar-wrap { background:#ddd; border-radius:4px; width:80px; height:8px; display:inline-block; vertical-align:middle; }
                                    .freq-bar      { background:#4e9af1; border-radius:4px; height:8px; }
                                    .dark .freq-bar-wrap { background:#555; }
                                    /* ── Company cards grid ── */
                                    .company-grid { display:flex; flex-wrap:wrap; gap:8px; padding:12px 0; }
                                    .company-card { display:inline-block; padding:6px 14px; border-radius:6px;
                                                    background:#e8f0fe; color:#174ea6; text-decoration:none;
                                                    font-size:0.9em; font-weight:500;
                                                    border:1px solid #c5d3f0; transition: all .15s; }
                                    .company-card:hover { background:#174ea6; color:#fff; text-decoration:none; }
                                    .dark .company-card { background:#2a3a5c; color:#a8c4ff; border-color:#3a5080; }
                                    .dark .company-card:hover { background:#3d5a8a; color:#fff; }
                                    /* ── Search box ── */
                                    .lc-search { margin:12px 0; padding:6px 12px; border-radius:6px;
                                                 border:1px solid #ccc; width:100%; max-width:400px;
                                                 font-size:1em; }
                                    .dark .lc-search { background:#333; color:#e6e6e6; border-color:#555; }
                                    /* ── Difficulty filter buttons ── */
                                    .diff-btn { padding:4px 12px; border-radius:4px; border:1px solid #ccc;
                                                background:#f5f5f5; color:#333; cursor:pointer; font-size:0.85em; transition:all .15s; }
                                    .diff-btn.active { color:#fff; border-color:transparent; }
                                    .diff-btn[data-diff="all"].active  { background:#555; }
                                    .diff-btn[data-diff="Easy"].active   { background:#00b8a3; }
                                    .diff-btn[data-diff="Medium"].active { background:#ffc01e; color:#333; }
                                    .diff-btn[data-diff="Hard"].active   { background:#ef4743; }
                                    .dark .diff-btn { background:#333; color:#ccc; border-color:#555; }
                                    .dark .diff-btn[data-diff="Easy"].active   { background:#007d72; }
                                    .dark .diff-btn[data-diff="Medium"].active { background:#b38600; color:#eee; }
                                    .dark .diff-btn[data-diff="Hard"].active   { background:#b02e2c; }
                                    /* ── Inline company tags ── */
                                    .company-tag { display:inline-block; padding:1px 7px; margin:2px 1px;
                                                   border-radius:3px; font-size:0.77em;
                                                   background:#e8f0fe; color:#174ea6; border:1px solid #c5d3f0; }
                                    .dark .company-tag { background:#2a3a5c; color:#a8c4ff; border-color:#3a5080; }
                                    /* ── Company stat pill ── */
                                    .co-pill { display:inline-flex; align-items:center; gap:4px;
                                               padding:3px 10px 3px 8px; margin:3px 3px;
                                               border-radius:20px; font-size:0.82em; font-weight:500;
                                               background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe;
                                               text-decoration:none; }
                                    .co-pill .co-cnt { background:#3730a3; color:#fff;
                                                        border-radius:10px; padding:0 6px;
                                                        font-size:0.78em; font-weight:700; }
                                    .dark .co-pill { background:#1e2a4a; color:#93c5fd; border-color:#2d4a7a; }
                                    .dark .co-pill .co-cnt { background:#2563eb; }
                                    /* ── Stat period heading ── */
                                    .stat-period { display:inline-block; font-size:0.78em; font-weight:600;
                                                   padding:2px 10px; border-radius:4px; margin-bottom:6px;
                                                   background:#fef3c7; color:#92400e; border:1px solid #fcd34d; }
                                    .dark .stat-period { background:#3a2a0a; color:#fcd34d; border-color:#92400e; }
                                    .stat-section { margin-bottom:10px; padding:8px 10px;
                                                    border-radius:6px; background:#fffbeb;
                                                    border:1px solid #fde68a; }
                                    .dark .stat-section { background:#1c1a0f; border-color:#4a3a0a; }
                                    /* ── Similar questions table ── */
                                    .sim-q-table { width:100%; border-collapse:collapse; font-size:0.9em; }
                                    .sim-q-table td { padding:5px 8px; border-bottom:1px solid #e5e7eb; vertical-align:middle; }
                                    .dark .sim-q-table td { border-color:#374151; }
                                    .sim-q-table tr:last-child td { border-bottom:none; }
                                    .sim-q-table tr:hover td { background:rgba(0,0,0,0.03); }
                                    .dark .sim-q-table tr:hover td { background:rgba(255,255,255,0.04); }
                                    /* ── Question sections ── */
                                    .q-section { margin:18px 0; padding:14px 18px;
                                                 border-radius:8px; background:#fff;
                                                 border:1px solid #e5e7eb;
                                                 overflow:hidden; box-sizing:border-box; }
                                    .dark .q-section { background:#1e1e1e; border-color:#333; }
                                    .q-section h5, .q-section h3 { margin-top:0; margin-bottom:10px;
                                                                    font-size:1em; font-weight:700;
                                                                    text-transform:uppercase; letter-spacing:.04em;
                                                                    color:#6b7280; }
                                    .dark .q-section h5, .dark .q-section h3 { color:#9ca3af; }
                                    /* ── md-block containment ── */
                                    md-block { display:block; width:100%; box-sizing:border-box;
                                               overflow-wrap:break-word; word-break:break-word; }
                                    md-block p, md-block li, md-block pre { max-width:100%; }
                                    /* ── Code block ── */
                                    .code-wrap { position:relative; }
                                    .code-wrap pre { background:#1e1e2e; color:#cdd6f4;
                                                     padding:16px; border-radius:6px;
                                                     overflow-x:auto; font-size:0.88em;
                                                     line-height:1.6; margin:0; }
                                    .dark .code-wrap pre { background:#111122; }
                                    /* ── Hint items ── */
                                    .hint-item { padding:8px 12px; margin:6px 0;
                                                 border-left:3px solid #6366f1;
                                                 background:#f5f3ff; border-radius:0 6px 6px 0;
                                                 font-size:0.92em; }
                                    .dark .hint-item { background:#1a1830; border-color:#4f46e5; }
                                    /* ── Question title header ── */
                                    .q-header { display:flex; align-items:center; flex-wrap:wrap;
                                                gap:10px; margin-bottom:12px; }
                                    .q-title { font-size:1.4em; font-weight:700; margin:0; }
                                    .q-title a { text-decoration:none; color:inherit; }
                                    .q-title a:hover { text-decoration:underline; }
                    </style>
                    <style>
                    mjx-container, .mjx-chtml {
                                        display: inline !important;
                                    }
                    </style>
 """


def find_slides_json(content):
    print("Finding slides json")
    word = "/Documents/"
    # Match the full !?!...!?! marker blocks that contain a /Documents/ path
    slides_json_list = re.findall(
        fr"\!\?\!.*?{word}.*?\!\?\!",
        content,
        flags=re.IGNORECASE | re.MULTILINE
    )
    # Fallback: bare lines with /Documents/ (no markers) that contain .json
    if not slides_json_list:
        all_lines = re.findall(fr".*?{word}.*?\.json.*", content, re.IGNORECASE | re.MULTILINE)
        slides_json_list = all_lines
    slides_json = []
    if not slides_json_list:
        return slides_json
    scraper = cloudscraper.create_scraper()
    for slide_name in slides_json_list:
        raw = slide_name.strip()
        # Extract path from inside !?!...:line,col!?! markers
        marker_match = re.search(r'\!\?\!(.*?)(?::\d+,\d+)?\!\?\!', raw)
        if marker_match:
            raw = marker_match.group(1).strip()
        if ".json" not in raw:
            print(f"Skipping — no .json in path: {slide_name!r}")
            slides_json.append([])
            continue
        # Parse: e.g. "../Documents/4/s1.json" or "/Documents/01_LIS.json"
        base_name = raw.split(".json")[0]
        parts = base_name.split("/")
        drop_dots = [p for p in parts if p and p != ".."]  # remove empty & ".." segments
        # drop_dots: ['Documents', '4', 's1'] or ['Documents', '01_LIS']
        if not drop_dots or drop_dots[0].lower() != "documents":
            print(f"Skipping unrecognised slide path: {slide_name!r}")
            slides_json.append([])
            continue
        documents = drop_dots[0]                                # "Documents"
        rest = "/".join(drop_dots[1:])                          # "4/s1" or "01_LIS"
        filename_var1 = f"{documents.lower()}/{rest}"           # "documents/4/s1"
        filename_var2 = f"{documents.lower()}/{rest.lower()}"   # fully lowercased fallback
        base_url = "https://assets.leetcode.com/static_assets/media/"
        url1 = base_url + filename_var1 + ".json"
        url2 = base_url + filename_var2 + ".json"
        data = []
        for attempt_url in [url1, url2]:
            try:
                print(f"Trying slide url: {attempt_url}")
                resp = scraper.get(url=attempt_url, timeout=15)
                parsed = json.loads(resp.content)
                if 'timeline' in parsed:
                    data = parsed['timeline']
                    break
                print(f"No 'timeline' key in response from {attempt_url}")
            except Exception as e:
                print(f"Failed for {attempt_url}: {e}")
        slides_json.append(data)
    return slides_json


def get_article_data(item_content, item_title, headers):
    print("Getting article data")
    if item_content['article']:
        article_id = item_content['article']['id']
        article_data = {"operationName": "GetArticle", "variables": {
            "articleId": f"{article_id}"}, "query": "query GetArticle($articleId: String!) {\n  article(id: $articleId) {\n    id\n    title\n    body\n  }\n}\n"}
        article_content = lc_post(headers, article_data)['data']['article']
        article = article_content['body']
        return f"""<h3>{item_title}</h3>
                    <md-block class="article__content">{article}</md-block>
                """
    return ""


def get_html_article_data(item_content, item_title, headers):
    print("Getting html article data")
    if item_content['htmlArticle']:
        html_article_id = item_content['htmlArticle']['id']
        html_article_data = {"operationName": "GetHtmlArticle", "variables": {
            "htmlArticleId": f"{html_article_id}"}, "query": "query GetHtmlArticle($htmlArticleId: String!) {\n  htmlArticle(id: $htmlArticleId) {\n    id\n    html\n      }\n}\n"}
        html_article_content = lc_post(headers, html_article_data)['data']['htmlArticle']
        html_article = html_article_content['html']
        return f"""<h3>{item_title}</h3>
                    <md-block class="html_article__content">{html_article}</md-block>
                """
    return ""


def generate_similar_questions(similar_questions):
    print("Generating similar questions")
    if not similar_questions:
        return ""
    similar_questions = json.loads(similar_questions)
    if not similar_questions:
        return ""
    rows = ""
    for idx, q in enumerate(similar_questions, start=1):
        diff = q['difficulty']
        diff_class = 'badge-easy' if diff == 'Easy' else ('badge-medium' if diff == 'Medium' else 'badge-hard')
        rows += f"""<tr>
            <td style="width:28px;color:#9ca3af;text-align:right">{idx}</td>
            <td><a href="./{q['title']}.html">{q['title']}</a></td>
            <td style="text-align:center"><span class="{diff_class}">{diff}</span></td>
            <td><a target="_blank" href="https://leetcode.com/problems/{q['titleSlug']}" title="Open on LeetCode"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></a></td>
        </tr>"""
    return f"""<div class="q-section">
        <h5>Similar Questions</h5>
        <table class="sim-q-table">{rows}</table>
    </div>"""


def get_question_company_tag_stats(company_tag_stats):
    print("Getting question company tag stats")
    if not company_tag_stats:
        return ""
    cts = json.loads(company_tag_stats)
    if not cts:
        return ""
    period_order = ["three_months", "six_months", "more_than_six_months"]
    period_labels = {
        "three_months": "0 - 3 months",
        "six_months": "3 - 6 months",
        "more_than_six_months": "6 months ago",
    }
    html = """<div class="q-section"><h5>Company Tag Stats</h5>"""
    for key in period_order:
        if key not in cts:
            continue
        companies = sorted(cts[key], key=lambda x: -x['timesEncountered'])
        label = period_labels.get(key, key)
        pills = "".join(
            f"""<span class="co-pill">{c['name']}<span class="co-cnt">{c['timesEncountered']}</span></span>"""
            for c in companies if c['timesEncountered'] > 0
        )
        if pills:
            html += f"""<div class="stat-section">
                <div class="stat-period">{label}</div><br>
                {pills}
            </div>"""
    html += "</div>"
    return html


def get_question_data(item_content, headers):
    print("Getting question data")
    if item_content['question']:
        question_title_slug = item_content['question']['titleSlug']
        question_data = {"operationName": "GetQuestion", "variables": {"titleSlug": question_title_slug},
                         "query": "query GetQuestion($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n title\n submitUrl\n similarQuestions\n difficulty\n  companyTagStatsV2\n codeDefinition\n    content\n    hints\n    solution {\n      content\n   }\n   }\n }\n"}
        question_content = lc_post(headers, question_data)
        try:
            question_content = question_content['data']['question']
        except:
            raise Exception("Error in getting question data")
        question_title = re.sub(r'[:?|></\\]', replace_filename, question_content['title'])
        question = question_content['content']
        difficulty = question_content['difficulty']
        raw_cts = question_content['companyTagStatsV2']
        top_companies = []
        if raw_cts:
            try:
                cts = json.loads(raw_cts)
                totals: dict[str, int] = {}
                for key in ("three_months", "six_months", "more_than_six_months"):
                    for entry in cts.get(key) or []:
                        name = entry.get("name", "")
                        if name:
                            totals[name] = totals.get(name, 0) + entry.get("timesEncountered", 0)
                top_companies = [name for name, _ in sorted(totals.items(), key=lambda x: -x[1])[:8]]
            except Exception:
                pass
        company_tag_stats = get_question_company_tag_stats(raw_cts)
        similar_questions = generate_similar_questions(
            question_content['similarQuestions'])
        question_url = "https://leetcode.com" + \
            question_content['submitUrl'][:-7]
        default_code = json.loads(question_content['codeDefinition'])[
            0]['defaultCode']
        solution = question_content['solution']
        if solution:
            solution = solution['content']
        else:
            solution = "No Solution"
        hints = question_content['hints']

        if hints:
            hint_content = ""
            for hint in hints:
                hint_content += f'<div class="hint-item">{hint}</div>'
        else:
            hint_content = '<span style="color:#9ca3af">No Hints</span>'
        diff_class = 'badge-easy' if difficulty == 'Easy' else ('badge-medium' if difficulty == 'Medium' else 'badge-hard')
        top_co_pills = "".join(
            f'<span class="company-tag">{c}</span>' for c in top_companies
        )
        return f"""<div class="mode">Dark mode: <span class="change">OFF</span></div>
                    <div class="q-header">
                        <h2 class="q-title"><a target="_blank" href="{question_url}">{question_title}</a></h2>
                        <span class="{diff_class}">{difficulty}</span>
                    </div>
                    {f'<div style="margin-bottom:12px">{top_co_pills}</div>' if top_co_pills else ''}
                    {company_tag_stats}
                    {similar_questions}
                    <div class="">
                        <h5>Question</h5>
                        <md-block class="question__content">{question}</md-block>
                    </div>
                    <div class="">
                        <h5>Default Code</h5>
                        <div class=""><pre class="question__default_code">{default_code}</pre></div>
                    </div>
                    <div class="q-section">
                        <h5>Hints</h5>
                        <md-block class="question__hints">{hint_content}</md-block>
                    </div>
                    <div class="">
                        <md-block class="question__solution">{solution}</md-block>
                    </div>
                """, question_title, {
            'title': question_title,
            'slug': question_title_slug,
            'difficulty': difficulty,
            'companies': top_companies,
            'url': question_url,
            'file': question_title + '.html'
        }
    return """<div class="mode">
                    Dark mode:  <span class="change">OFF</span>
                </div>""", "", {}


def create_card_index_html(chapters, card_slug, headers):
    print("Creating index.html")
    intro_data = {"operationName": "GetExtendedCardDetail", "variables": {"cardSlug": card_slug},
                  "query": "query GetExtendedCardDetail($cardSlug: String!) {\n  card(cardSlug: $cardSlug) {\n title\n  introduction\n}\n}\n", }
    introduction = lc_post(headers, intro_data)['data']['card']
    body = ""
    for chapter in chapters:
        body += f"""
                    <br>
                    <h3>{chapter['title']}</h3>
                    {chapter['description']}
                    <br>
        """
        for item in chapter['items']:
            item['title'] = re.sub(r'[:?|></\\]', replace_filename, item['title'])
            body += f"""<a href="{item['id']}-{item['title']}.html">{item['id']}-{item['title']}</a><br>"""
    with open("index.html", 'w', encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
                <html lang="en">
                {attach_header_in_html()}
                <body>
                    <div class="mode">
                    Dark mode:  <span class="change">OFF</span>
                    </div>
                    <h1 class="card-title">{introduction['title']}</h1>
                    <p class="card-text">{introduction['introduction']}</p>
                    <br>
                    {body}
                </body>
                </html>""")


def scrape_selected_company_questions(choice):
    leetcode_cookie, _, _, save_path, _, _, company_tag_save_path = load_config()
    create_folder(os.path.join(save_path, "all_company_questions"))
    headers = create_headers(leetcode_cookie)
    final_company_tags = []
    with open(company_tag_save_path, 'r', encoding="utf-8") as f:
        company_tags = f.readlines()
        for company_tag in company_tags:
            company_tag = company_tag.replace("\n", "").split("/")[-2]
            final_company_tags.append(
                {"name": company_tag,
                 'slug': company_tag})
    if choice == "9":
        create_all_company_index_html(final_company_tags, headers)
    elif choice == "10":
        for company in final_company_tags:
            slug = company['slug']
            create_folder(os.path.join(
                save_path, "all_company_questions", slug))
            with open(os.path.join(save_path, "all_company_questions", slug, "index.html"), 'r', encoding="utf-8") as f:
                html = f.read()
                scrape_question_data(slug, headers, html)
            os.chdir("..")
    os.chdir("..")

def get_next_data_id():
    next_data = requests.get(url="https://leetcode.com/_next/", headers=create_headers()).content
    next_data_soup = BeautifulSoup(next_data, "html.parser")
    next_data_id = json.loads(next_data_soup.select("script[id='__NEXT_DATA__']")[0].text)['buildId']
    return next_data_id

def scrape_all_company_questions(choice):
    print("Scraping all company questions")
    leetcode_cookie, _, _, save_path, _, _, _ = load_config()
    create_folder(os.path.join(save_path, "all_company_questions"))
    headers = create_headers(leetcode_cookie)
    print("Header generated")
    company_data = {"operationName": "questionCompanyTags", "variables": {},
                        "query": "query questionCompanyTags {\n  companyTags {\n    name\n    slug\n    questionCount\n  }\n}\n"}
    company_tags = lc_post(headers, company_data)['data']['companyTags']
    if choice == "7":
        create_all_company_index_html(company_tags, headers)
    elif choice == "8":
        for company in company_tags:
            slug = company['slug']
            create_folder(os.path.join(
                save_path, "all_company_questions", slug))
            with open(os.path.join(save_path, "all_company_questions", slug, "index.html"), 'r', encoding="utf-8") as f:
                html = f.read()
                scrape_question_data(slug, headers, html)
            os.chdir("..")
    os.chdir('..')
    _ensure_base_index()


def create_all_company_index_html(company_tags, headers):
    print("Creating company index.html")
    _, _, _, save_path, _, overwrite, company_tag_save_path = load_config()
    cards_html = ''
    with open(company_tag_save_path, 'w', encoding="utf-8") as f:
        for company in company_tags:
            cards_html += f'''<a class="company-card" href="{company['slug']}/index.html">{company['slug']}</a>'''
            f.write(f"https://leetcode.com/company/{company['slug']}/\n")

    with open(os.path.join(save_path, "all_company_questions", "index.html"), 'w', encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<body>
<div class="mode">Dark mode: <span class="change">OFF</span></div>
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
    for company in company_tags:
        slug = company['slug']
        create_folder(os.path.join(
            save_path, "all_company_questions", slug))
        if slug in os.listdir(os.path.join(
                save_path, "all_company_questions")) and overwrite == False and "index.html" in os.listdir(os.path.join(
                save_path, "all_company_questions", slug)):
            print("Already Scraped", slug)
            continue
        print("Scrapping Index for ", slug)
        company_data = {"operationName": "favoriteDetailV2ForCompany", "variables": {"favoriteSlug": slug},
                        "query": "query favoriteDetailV2ForCompany($favoriteSlug: String!) {\n  favoriteDetailV2(favoriteSlug: $favoriteSlug) {\n    questionNumber\n    collectCount\n    generatedFavoritesInfo {\n      defaultFavoriteSlug\n      categoriesToSlugs {\n        categoryName\n        favoriteSlug\n        displayName\n      }\n    }\n  }\n}\n    "}
        company_response = lc_post(headers, company_data)['data']['favoriteDetailV2']
        total_questions = company_response['questionNumber']
        print("Total Questions", total_questions)
        categories_to_slugs = company_response['generatedFavoritesInfo']['categoriesToSlugs']
        favorite_slug = slug + "-all"
        for category in categories_to_slugs:
            if "all" in category['categoryName']:
                favorite_slug = category['favoriteSlug']
                break
        print("Favorite Slug", favorite_slug)
        company_questions_data = {"operationName": "favoriteQuestionList", "variables": {"favoriteSlug": favorite_slug, "filter": {"positionRoleTagSlug": "", "skip": 0, "limit": total_questions}},
                        "query": "query favoriteQuestionList($favoriteSlug: String!, $filter: FavoriteQuestionFilterInput) {\n  favoriteQuestionList(favoriteSlug: $favoriteSlug, filter: $filter) {\n    questions {\n      difficulty\n      id\n      paidOnly\n      questionFrontendId\n      status\n      title\n      titleSlug\n      translatedTitle\n      isInMyFavorites\n      frequency\n      topicTags {\n        name\n        nameTranslated\n        slug\n      }\n    }\n    totalLength\n    hasMore\n  }\n}\n    "}
        company_questions_response = lc_post(headers, company_questions_data)['data']['favoriteQuestionList']["questions"]
        print("Sucessfully Scraped Index for ", slug)
        html = ''
        max_freq = max((float(q['frequency']) for q in company_questions_response), default=1) or 1
        for idx, question in enumerate(company_questions_response, start=1):
            question['title'] = re.sub(r'[:?|></\\]', replace_filename, question['title'])
            diff = question['difficulty']
            diff_class = 'badge-easy' if diff == 'Easy' else ('badge-medium' if diff == 'Medium' else 'badge-hard')
            freq = round(float(question['frequency']), 2)
            freq_pct = int(float(question['frequency']) / max_freq * 100)
            html += f'''<tr>
                        <td style="width:40px;text-align:center">{idx}</td>
                        <td><a slug="{question['titleSlug']}" title="{question['title']}.html" href="{question['title']}.html">{question['title']}</a></td>
                        <td style="text-align:center"><span class="{diff_class}">{diff}</span></td>
                        <td style="white-space:nowrap">
                            <span style="margin-right:6px">{freq:.2f}</span>
                            <span class="freq-bar-wrap"><span class="freq-bar" style="width:{freq_pct}%"></span></span>
                        </td>
                        <td><a target="_blank" href="https://leetcode.com/problems/{question['titleSlug']}"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></a></td>
                        </tr>'''
        with open(os.path.join(save_path, "all_company_questions", slug, "index.html"), 'w', encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html lang="en">
{attach_header_in_html()}
<body>
<div class="mode">Dark mode: <span class="change">OFF</span></div>
<h2>{slug} - {len(company_questions_response)} Questions</h2>
<input class="lc-search" id="qSearch" onkeyup="filterQ()" placeholder="Search question..." type="text"/>
<table class="table table-bordered table-hover table-color" id="qTable" style="margin-top:10px">
  <thead><tr>
    <th style="width:40px">#</th>
    <th>Title</th>
    <th style="width:90px;text-align:center">Difficulty</th>
    <th style="width:140px">Frequency</th>
    <th style="width:50px">Link</th>
  </tr></thead>
  <tbody>{html}</tbody>
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
</html>""")
        os.chdir("..")


def scrape_question_data(slug, headers, html):
    print("Scraping question data")
    _, _, _, save_path, _, overwrite, _ = load_config()
    question_titles = BeautifulSoup(
        html, 'html.parser').find_all('a', title=True)
    if "questions" not in os.listdir(save_path):
        os.mkdir(os.path.join(save_path, "questions"))
    for question_title in question_titles:
        question_title['title'] = re.sub(r'[:?|></\\]', replace_filename, question_title['title'])
        if question_title['title'] in os.listdir(os.path.join(save_path, "all_company_questions", slug)) and overwrite == False:
            print("Already Scraped Company", question_title['title'], slug)
            if question_title['title'] in os.listdir(os.path.join(save_path, "questions")) and os.path.getsize(os.path.join(save_path, "questions", question_title['title'])) > os.path.getsize(os.path.join(save_path, "all_company_questions",
                                   slug, question_title['title'])):
                copy_html(os.path.join(save_path, "questions", question_title['title']), os.path.join(
                save_path, "all_company_questions", slug))
            else:
                copy_html(os.path.join(save_path, "all_company_questions",
                                    slug, question_title['title']), os.path.join(
                    save_path, "questions"))
            continue
        if question_title['title'] in os.listdir(os.path.join(save_path, "questions")) and overwrite == False:
            print("Copying from questions folder", question_title['title'])
            copy_html(os.path.join(save_path, "questions", question_title['title']), os.path.join(
                save_path, "all_company_questions", slug))
            continue
        print("Scraping ", question_title['title'])
        create_question_html(question_title['slug'], headers)
        copy_html(os.path.join(save_path, "all_company_questions",
                  slug, question_title['title']), os.path.join(
            save_path, "questions"))


def copy_html(src, dst):
    shutil.copy(src, dst)


def replace_filename(str):
    numDict = {':': ' ', '?': ' ', '|': ' ', '>': ' ', '<': ' ', '/': ' ', '\\': ' '}
    return numDict[str.group()]


def _ensure_base_index():
    """Create base index.html in save_path if it doesn't already exist."""
    _, _, _, save_path, _, _, _ = load_config()
    if not os.path.exists(os.path.join(save_path, "index.html")):
        create_base_index_html()


def create_base_index_html():
    print("Creating base index.html")
    _, _, _, save_path, _, _, _ = load_config()
    sections = [
        {"title": "Questions", "href": "questions/index.html", "desc": "All scraped LeetCode questions",
         "icon": '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>'},
        {"title": "Cards", "href": "cards/index.html", "desc": "Explore cards and learning paths",
         "icon": '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>'},
        {"title": "Company Questions", "href": "all_company_questions/index.html", "desc": "Questions grouped by company",
         "icon": '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>'},
    ]
    cards_html = ""
    for s in sections:
        cards_html += f"""<a class="idx-card" href="{s['href']}">
            <div class="idx-icon">{s['icon']}</div>
            <div class="idx-label">{s['title']}</div>
            <div class="idx-desc">{s['desc']}</div>
        </a>"""
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
<div class="mode">Dark mode: <span class="change">OFF</span></div>
<div class="idx-hero">
  <h1>LeetCode Scraper</h1>
  <p>Your local offline LeetCode archive</p>
</div>
<div class="idx-grid">
  {cards_html}
</div>
<div class="idx-footer">Built by Anilabha Datta &mdash; <a href="https://github.com/anilabhadatta/leetcode-scraper" target="_blank">GitHub</a></div>
</body>
</html>"""
    with open(os.path.join(save_path, "index.html"), 'w', encoding="utf-8") as f:
        f.write(html)
    print(f"Base index.html created at: {os.path.join(save_path, 'index.html')}")
    print(f"Run: python -m http.server 8080 --directory \"{save_path}\"")


def check_premium_status():
    print("Checking LeetCode premium status...")
    try:
        leetcode_cookie, _, _, _, _, _, _ = load_config()
    except Exception as e:
        print("Could not load config:", e)
        return
    headers = create_headers(leetcode_cookie)
    premium_data = {
        "operationName": "getUserStatus",
        "variables": {},
        "query": "query getUserStatus {\n  userStatus {\n    username\n    isSignedIn\n    isPremium\n    activeSessionId\n  }\n}\n"
    }
    try:
        response = json.loads(
            requests.post(url=url, headers=headers, json=premium_data).content
        )
        user_status = response['data']['userStatus']
        is_signed_in = user_status.get('isSignedIn', False)
        is_premium = user_status.get('isPremium', False)
        username = user_status.get('username', 'Unknown')
        print(f"\n{'='*40}")
        print(f"  Username   : {username}")
        print(f"  Signed In  : {'Yes' if is_signed_in else 'No (cookie may be expired)'}")
        print(f"  Premium    : {'Yes ✓' if is_premium else 'No ✗'}")
        print(f"{'='*40}\n")
        if not is_signed_in:
            print("WARNING: Not signed in. Please update your LEETCODE_SESSION cookie in the config.")
        elif not is_premium:
            print("NOTE: Some questions and company tag stats require a LeetCode Premium subscription.")
    except Exception as e:
        print("Error checking premium status:", e)


def manual_convert_images_to_base64():
    root_dir = input("Enter path of the folder where html are located: ")
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.html'):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                    res_soup = fix_image_urls(soup, True)
                with open(os.path.join(root, file), "w", encoding="utf-8") as f:
                    f.write(res_soup.prettify())
    

if __name__ == '__main__':
    current_os = sys.platform
    url = "https://leetcode.com/graphql"
    selected_config = "0"
    parser = argparse.ArgumentParser(description='Leetcode Scraper Options')
    parser.add_argument('--non-stop', type=bool,
                        help='True/False - Will run non stop, will retry if any error occurs')
    parser.add_argument('--proxy', type=str,
                        help='Add rotating or static proxy username:password@ip:port')
    clear()
    args = parser.parse_args()
    previous_choice = "0"
    if args.proxy:
        os.environ['http_proxy'] = "http://"+args.proxy
        os.environ['https_proxy'] = "http://"+args.proxy
        print("Proxy set", requests.get(
            "https://httpbin.org/ip").content)

    while True:
        # print("Proxy set", requests.get(
        #     "https://httpbin.org/ip").content)
        try:
            print("""Starting Leetcode-Scraper v1.5-stable, Built by Anilabha Datta
                Github-Repo: https://github.com/anilabhadatta/leetcode-scraper
                Press 1: To setup config
                Press 2: To select config[Default: 0]
                Press 3: To get all cards url
                Press 4: To get all question url
                Press 5: To scrape card url
                Press 6: To scrape question url
                Press 7: To scrape all company questions indexes
                Press 8: To scrape all company questions
                Press 9: To scrape selected company questions indexes
                Press 10: To scrape selected company questions
                Press 11: To convert images to base64 using os.walk
                Press 12: To create base index.html for http.server
                Press 13: To check LeetCode Premium status
                Press any to quit
                """)
            if previous_choice != "0":
                print("Previous Choice: ", previous_choice)
            else:
                choice = input("Enter your choice: ")
            if choice == "1":
                generate_config()
            elif choice == "2":
                select_config()
            elif choice == "3":
                get_all_cards_url()
            elif choice == "4":
                get_all_questions_url()
            elif choice == "5":
                scrape_card_url()
            elif choice == "6":
                scrape_question_url()
            elif choice == "7" or choice == "8":
                scrape_all_company_questions(choice)
            elif choice == "9" or choice == "10":
                scrape_selected_company_questions(choice)
            elif choice =="11":
                manual_convert_images_to_base64()
            elif choice == "12":
                create_base_index_html()
            elif choice == "13":
                check_premium_status()
            else:
                break
            if previous_choice != "0":
                break
        except KeyboardInterrupt:
            if args.non_stop:
                print("Keyboard Interrupt, Exiting")
                break
        except Exception as e:
            print("""
            Error Occured, Possible Causes:
            1. Check your internet connection
            2. Leetcode Session Cookie might have expired 
            3. Check your config file
            4. Too many requests, try again after some time or use proxies
            5. Leetcode might have changed their api queries (Create an issue on github)
            """)
            print("Exception info: ", e)
            if args.non_stop:
                print("Retrying")
                previous_choice = choice
                continue
            input("Press Enter to continue")
