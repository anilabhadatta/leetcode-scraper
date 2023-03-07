import requests
import json
from requests.structures import CaseInsensitiveDict
from bs4 import BeautifulSoup
import markdown2
import re
import base64
import os
import sys
import shutil

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
    print('''
        Leave Blank and press Enter if you don't want to overwrite Previous Values
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

    base_config_path = create_base_config_dir()

    with open(os.path.join(base_config_path, f"config_{selected_config}.json"), "w+") as config_file:
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
    with open(os.path.join(config_path, f"config_{selected_config}.json"), "r") as config_file:
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
    headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.56"
    return headers


def get_all_cards_url():
    print("Getting all cards url")
    _, cards_url_path, _, _, _, _, _ = load_config()
    headers = create_headers()
    cards_data = {"operationName": "GetCategories", "variables": {
        "num": 1000}, "query": "query GetCategories($categorySlug: String, $num: Int) {\n  categories(slug: $categorySlug) {\n  slug\n    cards(num: $num) {\n ...CardDetailFragment\n }\n  }\n  }\n\nfragment CardDetailFragment on CardNode {\n   slug\n  categorySlug\n  }\n"}
    cards = json.loads(requests.post(url=url, headers=headers,
                                     json=cards_data).content)['data']['categories']
    with open(cards_url_path, "w") as f:
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
    all_questions_count = json.loads(requests.post(
        url=url, headers=headers, json=question_count_data).content)['data']['allQuestionsCount'][0]['count']
    print("Total no of questions: ", all_questions_count)

    question_data = {"query": "\n query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {\n  problemsetQuestionList: questionList(\n    categorySlug: $categorySlug\n    limit: $limit\n    skip: $skip\n    filters: $filters\n  ) {\n  questions: data {\n title\n titleSlug\n  }\n  }\n}\n    ", "variables": {
        "categorySlug": "", "skip": 0, "limit": int(all_questions_count), "filters": {}}}
    all_questions = json.loads(requests.post(
        url=url, headers=headers, json=question_data).content)['data']['problemsetQuestionList']['questions']
    if not self_function:
        return all_questions
    write_questions_to_file(all_questions, questions_url_path)


def write_questions_to_file(all_questions, questions_url_path):
    with open(questions_url_path, "w") as f:
        for question in all_questions:
            question_url = "https://leetcode.com/problems/" + \
                question['titleSlug'] + "/\n"
            f.write(question_url)


def scrape_question_url():
    leetcode_cookie, _, questions_url_path, save_path, _, overwrite, _ = load_config()
    headers = create_headers(leetcode_cookie)
    all_questions = get_all_questions_url(self_function=False)
    create_folder(os.path.join(save_path, "questions"))
    with open(questions_url_path, "r") as f:
        question_urls = f.readlines()
        for question_url in question_urls:
            question_url = question_url.strip()
            question_slug = question_url.split("/")[-2]
            for question in all_questions:
                if question['titleSlug'] == question_slug:
                    question_title = question['title']
                    break
            if f"{question_title}.html" in os.listdir(os.path.join(save_path, "questions")) and overwrite == False and os.path.getsize(os.path.join(save_path, "questions", f"{question_title}.html")) > 0:
                print("Already scraped")
                continue
            print("Scraping question url: ", question_url)
            create_question_html(question_slug, headers)
    os.chdir('..')


def create_question_html(question_slug, headers):
    item_content = {"question": {'titleSlug': question_slug}}
    content = """<body>"""
    question_content, question_title = get_question_data(item_content, headers)
    content += question_content
    content += """</body>"""
    slides_json = find_slides_json(content)
    content = markdown2.markdown(content)
    content = attach_header_in_html() + content
    content_soup = BeautifulSoup(content, 'html.parser')
    content_soup = replace_iframes_with_codes(content_soup, headers)
    content_soup = place_solution_slides(content_soup, slides_json)
    content_soup = fix_image_urls(content_soup)
    with open(f"{question_title}.html", 'w', encoding="utf-8") as f:
        f.write(content_soup.prettify())


def scrape_card_url():
    leetcode_cookie, cards_url_path, _, save_path, _, overwrite, _ = load_config()
    headers = create_headers(leetcode_cookie)
    create_folder(os.path.join(save_path, "cards"))
    if "questions" not in os.listdir(save_path):
        os.mkdir(os.path.join(save_path, "questions"))
    with open(cards_url_path, "r") as f:
        card_urls = f.readlines()
        for card_url in card_urls:
            card_url = card_url.strip()
            print("Scraping card url: ", card_url)
            card_slug = card_url.split("/")[-2]
            card_data = {"operationName": "GetChaptersWithItems", "variables": {"cardSlug": card_slug},
                         "query": "query GetChaptersWithItems($cardSlug: String!) {\n  chapters(cardSlug: $cardSlug) {\n    ...ExtendedChapterDetail\n   }\n}\n\nfragment ExtendedChapterDetail on ChapterNode {\n  id\n  title\n  slug\n description\n items {\n    id\n    title\n  }\n }\n"}
            chapters = json.loads(requests.post(url=url, headers=headers,
                                                json=card_data).content)['data']['chapters']
            if chapters:
                create_folder(os.path.join(save_path, "cards", card_slug))
                create_card_index_html(chapters, card_slug, headers)
                for subcategory in chapters:
                    print("Scraping subcategory: ", subcategory['title'])
                    for item in subcategory['items']:
                        print("Scraping Item: ", item['title'])
                        item_id = item['id']
                        item_title = item['title']

                        if f"{item_id}-{item_title}.html" in os.listdir(os.path.join(save_path, "cards", card_slug)) and overwrite == False:
                            print("Already scraped")
                            continue
                        if f"{item_id}-{item_title}.html" not in os.listdir(os.path.join(save_path, "cards", card_slug)) and "questions" in os.listdir(save_path) and f"{item_title}.html" in os.listdir(os.path.join(save_path, "questions")) and overwrite == False:
                            print("Copying from questions folder", item_title)
                            copy_html(os.path.join(save_path, "questions", f"{item_title}.html"), os.path.join(
                                save_path, "cards", card_slug))
                            os.rename(os.path.join(save_path, "cards", card_slug, f"{item_title}.html"), os.path.join(
                                save_path, "cards", card_slug, f"{item_id}-{item_title}.html"))
                            continue
                        item_data = {"operationName": "GetItem", "variables": {"itemId": f"{item_id}"},
                                     "query": "query GetItem($itemId: String!) {\n  item(id: $itemId) {\n    id\n title\n  question {\n questionId\n   title\n  titleSlug\n }\n  article {\n id\n title\n }\n  htmlArticle {\n id\n  }\n  webPage {\n id\n  }\n  }\n }\n"}
                        item_content = json.loads(requests.post(url=url, headers=headers,
                                                                json=item_data).content)['data']['item']
                        if item_content == None:
                            break
                        create_card_html(
                            item_content, item_title, item_id, headers)
                os.chdir("..")
    os.chdir('..')


def create_card_html(item_content, item_title, item_id, headers):
    content = """<body>"""
    question_content, _ = get_question_data(item_content, headers)
    content += question_content
    content += get_article_data(item_content, item_title, headers)
    content += get_html_article_data(item_content, item_title, headers)
    content += """</body>"""
    slides_json = find_slides_json(content)
    content = markdown2.markdown(content)
    content = attach_header_in_html() + content
    content_soup = BeautifulSoup(content, 'html.parser')
    content_soup = replace_iframes_with_codes(content_soup, headers)
    content_soup = place_solution_slides(content_soup, slides_json)
    content_soup = fix_image_urls(content_soup)
    with open(f"{item_id}-{item_title}.html", "w", encoding="utf-8") as f:
        f.write(content_soup.prettify())


def load_image_in_b64(img_url):
    print("Loading image in base64: ", img_url)
    img_ext = img_url.split('.')[-1]
    if img_ext == "svg":
        img_ext = "svg+xml"
    encoded_string = base64.b64encode(requests.get(
        url=img_url, headers=create_headers()).content)
    decoded_string = encoded_string.decode('utf-8')
    return f"data:image/{img_ext};base64,{decoded_string}"


def fix_image_urls(content_soup):
    print("Fixing image urls")
    _, _, _, _, save_images_locally, _, _ = load_config()
    images = content_soup.find_all('img')
    for image in images:
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
        # image['style'] = 'width: 100%; height: auto; object-fit: contain;'
    return content_soup


def place_solution_slides(content_soup, slides_json):
    print("Placing solution slides")
    slide_p_tags = content_soup.select("p:contains('/Documents/')")
    for slide_idx, slide_p_tag in enumerate(slide_p_tags):
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
            playground_content = json.loads(requests.post(
                url=url, headers=headers, json=playground_data).content)['data']['allPlaygroundCodes']

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
                                            inlineMath: [["$", "$"], ["\\(", "\\)"]],
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
                    document.addEventListener('DOMContentLoaded', function() {
                                                const carousel = document.querySelectorAll('.carousel');
                                                console.log(carousel)
                                                const items = Array.from(document.querySelectorAll('.carousel-item'));
                                                console.log(items)
                                                const maxWidth = Math.max(...items.map(item => item.querySelector('img').clientWidth));
                                                console.log(maxWidth);
                                                for (let i = 0; i < carousel.length; i++) {
                                                    carousel[i].style.width = maxWidth + 'px';            }
                                                
                                                $( ".change" ).on("click", function() {
                                                if( $( "body" ).hasClass( "dark" )) {
                                                    $( "body" ).removeClass( "dark" );
                                                    $( "div[style*='background: wheat;']" ).removeClass( "dark-banner" );
                                                    $( "div[style*='background: beige;']" ).removeClass( "dark-banner-sq" );
                                                    $("div[id*='v-pills-tabContent']").removeClass( "tab-content dark" );
                                                    $("table").removeClass( "table-color-dark" );
                                                    $("table").addClass( "table-color" );
                                                    $("div[id*='v-pills-tabContent']").addClass( "tab-content" );
                                                    $( ".change" ).text( "OFF" );
                                                } else {
                                                    $( "body" ).addClass( "dark" );
                                                    $( "div[style*='background: wheat;']" ).addClass( "dark-banner" );
                                                    $( "div[style*='background: beige;']" ).addClass( "dark-banner-sq" );
                                                    $("div[id*='v-pills-tabContent']").addClass( "tab-content dark" );
                                                    $("table").removeClass( "table-color" );
                                                    $("table").addClass( "table-color-dark" );
                                                    $( ".change" ).text( "ON" );
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
                                            background: repeating-linear-gradient(45deg, #130f0f, #3b3b3b4d 100px) !important;
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
    all_slides_json_list = re.compile(
        fr".*{word}.*", re.MULTILINE).findall(content)
    slides_json_list = [x for x in all_slides_json_list if ".json" in x]
    slides_json = []
    for links in slides_json_list:
        slide_img_url = "https://leetcode.com/explore/" + \
            "/".join(links.strip().split(".json")[-2].split("/")[1:]) + ".json"
        slides_json.append(json.loads(requests.get(
            url=slide_img_url, headers=create_headers()).content)['timeline'])
    return slides_json


def get_article_data(item_content, item_title, headers):
    print("Getting article data")
    if item_content['article']:
        article_id = item_content['article']['id']
        article_data = {"operationName": "GetArticle", "variables": {
            "articleId": f"{article_id}"}, "query": "query GetArticle($articleId: String!) {\n  article(id: $articleId) {\n    id\n    title\n    body\n  }\n}\n"}
        article_content = json.loads(requests.post(
            url=url, headers=headers, json=article_data).content)['data']['article']
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
        html_article_content = json.loads(requests.post(
            url=url, headers=headers, json=html_article_data).content)['data']['htmlArticle']
        html_article = html_article_content['html']
        return f"""<h3>{item_title}</h3>
                    <md-block class="html_article__content">{html_article}</md-block>
                """
    return ""


def generate_similar_questions(similar_questions):
    print("Generating similar questions")
    similar_questions_html = ""
    if similar_questions:
        similar_questions = json.loads(similar_questions)
        if similar_questions != []:
            similar_questions_html += f"""<div style="background: beige;"><h5>Similar Questions</h5>"""
            for idx, similar_question in enumerate(similar_questions, start=1):
                similar_questions_html += f"""<div class="similar-questions-container"><div class="left"><a target="_blank" href="https://leetcode.com/problems/{similar_question['titleSlug']}">{idx}-{similar_question['title']}</a></div><div class="right"> <span>{idx}-Difficulty: {similar_question['difficulty']} <a target="_blank" href="./{similar_question['title']}.html">Local Url</a></span></div></div>"""
            similar_questions_html += f"""</div><br>"""
    return similar_questions_html


def get_question_company_tag_stats(company_tag_stats):
    print("Getting question company tag stats")
    company_tag_stats_html = ""
    if company_tag_stats:
        company_tag_stats = json.loads(company_tag_stats)
        if company_tag_stats != {}:
            company_tag_stats_html += f"""<div style="background: wheat;"><h5>Company Tag Stats</h5>"""
            for key, value in company_tag_stats.items():
                company_tag_stats_html += f"""<h6>Years: {str(int(key)-1)}-{key}</h6><div>"""
                for company_tag_stat in value:
                    company_tag_stats_html += f"""<td>{company_tag_stat['name']}</td>"""
                    company_tag_stats_html += f"""<td>: {company_tag_stat['timesEncountered']} • </td>"""
                company_tag_stats_html += "</div><br>"
    return company_tag_stats_html


def get_question_data(item_content, headers):
    print("Getting question data")
    if item_content['question']:
        question_title_slug = item_content['question']['titleSlug']
        question_data = {"operationName": "GetQuestion", "variables": {"titleSlug": question_title_slug},
                         "query": "query GetQuestion($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n title\n submitUrl\n similarQuestions\n difficulty\n  companyTagStats\n codeDefinition\n    content\n    hints\n    solution {\n      content\n   }\n   }\n }\n"}
        question_content = json.loads(requests.post(
            url=url, headers=headers, json=question_data).content)
        try:
            question_content = question_content['data']['question']
        except:
            raise Exception("Error in getting question data")
        question_title = question_content['title']
        question = question_content['content']
        difficulty = question_content['difficulty']
        company_tag_stats = get_question_company_tag_stats(
            question_content['companyTagStats'])
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
                hint_content += f"<div> > {hint}</div>"
        else:
            hint_content = "No Hints"
        return f""" <div class="mode">
                    Dark mode:  <span class="change">OFF</span>
                    </div>
                    <h3 class="question__url"><a target="_blank" href="{question_url}">{question_title}</a></h3><p> Difficulty: {difficulty}</p>
                    <div>{company_tag_stats}</div>
                    <br>
                    <div>{similar_questions}</div>
                    <h5>Question</h5>
                    <md-block class="question__content">{question}</md-block>
                    <h3>Default Code</h3>
                    <pre class="question__default_code">{default_code}</pre>
                    <h3>Hints</h3>
                    <md-block class="question__hints">{hint_content}</md-block>
                    <h3>Solution</h3>
                    <md-block class="question__solution">{solution}</md-block>
                """, question_title
    return """<div class="mode">
                    Dark mode:  <span class="change">OFF</span>
                </div>""", ""


def create_card_index_html(chapters, card_slug, headers):
    print("Creating index.html")
    intro_data = {"operationName": "GetExtendedCardDetail", "variables": {"cardSlug": card_slug},
                  "query": "query GetExtendedCardDetail($cardSlug: String!) {\n  card(cardSlug: $cardSlug) {\n title\n  introduction\n}\n}\n", }
    introduction = json.loads(requests.post(url=url, headers=headers,
                                            json=intro_data).content)['data']['card']
    body = ""
    for chapter in chapters:
        body += f"""<div class="card">
                    <h3>{chapter['title']}</h3>
                    {chapter['description']}
                    <br>
        """
        for item in chapter['items']:
            body += f"""<a href="{item['id']}-{item['title']}.html">{item['id']}-{item['title']}</a><br>"""
        body += "</div>"
    chapter_html = f"""<div class="container">
                        <div class="row">
                            <div class="col-md-12">
                                {body}
                            </div>
                        </div>
                    </div>"""
    with open("index.html", 'w') as f:
        f.write(f"""<!DOCTYPE html>
                <html lang="en">
                {attach_header_in_html()}
                <body>
                    <div class="container">
                        <div class="row">
                            <div class="col-md-12">
                                <div class="card">
                                    <div class="card-body">
                                        <h1 class="card-title">{introduction['title']}</h1>
                                        <p class="card-text">{introduction['introduction']}</p>
                                        <br>
                                    </div>
                                    {chapter_html}
                                </div>
                            </div>
                        </div>
                    </div>
                </body>
                </html>""")


def scrape_company_questions():
    leetcode_cookie, _, _, save_path, _, _, company_tag_save_path = load_config()
    create_folder(os.path.join(save_path, "all_company_questions"))
    headers = create_headers(leetcode_cookie)
    final_company_tags = []
    with open(company_tag_save_path, 'r') as f:
        company_tags = f.readlines()
        for company_tag in company_tags:
            company_tag = company_tag.replace("\n", "").split("/")[-2]
            final_company_tags.append(
                {"name": company_tag,
                 'slug': company_tag})
    create_all_company_index_html(final_company_tags, headers)
    os.chdir("..")


def scrape_all_company_questions():
    print("Scraping all company questions")
    leetcode_cookie, _, _, save_path, _, overwrite, _ = load_config()
    create_folder(os.path.join(save_path, "all_company_questions"))
    headers = create_headers(leetcode_cookie)
    companies_tag_url = "https://leetcode.com/_next/data/5t12MQGNqIncLszIGV8Ce/problemset/all.json?slug=all"
    company_tags = json.loads(requests.get(url=companies_tag_url,
                                           headers=create_headers(), json={'slug': 'all'}).content)['pageProps']['dehydratedState']['queries'][0]['state']['data']['companyTags']
    create_all_company_index_html(company_tags, headers)
    os.chdir('..')


def create_all_company_index_html(company_tags, headers):
    print("Creating company index.html")
    _, _, _, save_path, _, overwrite, _ = load_config()
    cols = 10
    rows = len(company_tags)//10 + 1
    html = ''
    company_idx = 0
    for _ in range(rows):
        html += '<tr>'
        for _ in range(cols):
            if company_idx < len(company_tags):
                html += f'''<td><a href="{company_tags[company_idx]['slug']}/index.html">{company_tags[company_idx]['slug']}</a></td>'''
                company_idx += 1
        html += '</tr>'

    with open(os.path.join(save_path, "all_company_questions", "index.html"), 'w') as f:
        f.write(f"""<!DOCTYPE html>
                <html lang="en">
                <head> </head>
                <body>
                    '<table>{html}</table>'
                </body>
                </html>""")
    for company in company_tags:
        slug = company['slug']
        print("Scrapping Index for ", slug)

        create_folder(os.path.join(
            save_path, "all_company_questions", slug))
        company_data = {"operationName": "getCompanyTag", "variables": {"slug": slug},
                        "query": "query getCompanyTag($slug: String!) {\n  companyTag(slug: $slug) {\n   questions {\n      ...questionFields\n          }\n    frequencies\n      }\n  }\nfragment questionFields on QuestionNode {\n questionId\n  titleSlug\n title\n  difficulty\n }\n"}
        company_response = json.loads(requests.post(
            url=url, headers=headers, json=company_data).content)['data']['companyTag']
        company_questions = company_response['questions']
        frequencies = json.loads(company_response['frequencies'])
        if slug in os.listdir(os.path.join(
                save_path, "all_company_questions")) and overwrite == False and len(os.listdir(os.path.join(
                save_path, "all_company_questions", slug))) >= len(company_questions) + 1:
            print("Already Scraped")
            continue
        html = ''
        for question in company_questions:
            html += f'''<tr>
                        <td><a slug="{question['titleSlug']}" title="{question['title']}.html" href="{question['title']}.html">{question['title']}.html</a></td>
                        <td> Difficulty: {question['difficulty']} </td><td>Frequency: {frequencies[question['questionId']][-2]*10}</td>
                        <td><a target="_blank" href="https://leetcode.com/problems/{question['titleSlug']}">Leetcode Url</a></td>
                        </tr>'''
        with open(os.path.join(save_path, "all_company_questions", slug, "index.html"), 'w') as f:
            f.write(f"""<!DOCTYPE html>
                <html lang="en">
                <head> </head>
                <body>
                    '<table>{html}</table>'
                </body>
                </html>""")
        scrape_question_data(slug, headers, html)
        os.chdir("..")


def scrape_question_data(slug, headers, html):
    print("Scraping question data")
    _, _, _, save_path, _, overwrite, _ = load_config()
    question_titles = BeautifulSoup(
        html, 'html.parser').find_all('a', title=True)
    if "questions" not in os.listdir(save_path):
        os.mkdir(os.path.join(save_path, "questions"))
    for question_title in question_titles:
        if question_title['title'] in os.listdir(os.path.join(save_path, "all_company_questions", slug)) and overwrite == False:
            print("Already Scraped", question_title['title'])
            copy_html(os.path.join(save_path, "all_company_questions",
                                   slug, question_title['title']), os.path.join(
                save_path, "questions"))
            continue
        if "questions" in os.listdir(save_path) and question_title['title'] in os.listdir(os.path.join(save_path, "questions")) and overwrite == False:
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


if __name__ == '__main__':
    current_os = sys.platform
    url = "https://leetcode.com/graphql"
    selected_config = "0"
    clear()

    while True:
        try:
            print("""Starting Leetcode-Scraper v1.1-stable, Built by Anilabha Datta
                Github-Repo: https://github.com/anilabhadatta/leetcode-scraper
                Press 1: To setup config
                Press 2: To select config[Default: 0]
                Press 3: To get all cards url
                Press 4: To get all question url
                Press 5: To scrape card url
                Press 6: To scrape question url
                Press 7: To scrape all company questions
                Press 8: To scrape selected company questions
                Press any to quit
                """)
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
            elif choice == "7":
                scrape_all_company_questions()
            elif choice == "8":
                scrape_company_questions()
            else:
                break
        except KeyboardInterrupt:
            input("Press Enter to continue")
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
            input("Press Enter to continue")
