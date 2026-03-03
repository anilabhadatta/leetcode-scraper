"""All LeetCode GraphQL interaction lives here.

Every API call is an explicit typed function.  No query strings
should appear in any other module.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from requests.structures import CaseInsensitiveDict

log = logging.getLogger(__name__)

GRAPHQL_URL = "https://leetcode.com/graphql"


def create_headers(leetcode_cookie: str = "") -> CaseInsensitiveDict:
    h = CaseInsensitiveDict()
    h["content-type"] = "application/json"
    h["cookie"] = f"LEETCODE_SESSION={leetcode_cookie}" if leetcode_cookie else ""
    h["referer"] = "https://leetcode.com/"
    h["user-agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    )
    h["accept"] = "application/json"
    return h


# ---------------------------------------------------------------------------
# Low-level transport
# ---------------------------------------------------------------------------

def _post(headers: CaseInsensitiveDict, payload: dict) -> dict:
    """Execute one GraphQL request. No auth checks – use lc_post() instead."""
    resp = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def lc_post(headers: CaseInsensitiveDict, payload: dict) -> dict:
    """Auth-guarded GraphQL request.  Verifies sign-in + premium when cookie present."""
    if headers.get("cookie", "").strip():
        status = _post(headers, _Q_USER_STATUS)["data"]["userStatus"]
        if not status["isSignedIn"]:
            raise PermissionError(
                f"Not signed in ('{status['username']}'). Update cookie via option [1]."
            )
        if not status["isPremium"]:
            raise PermissionError(
                f"Account '{status['username']}' has no Premium — required for this content."
            )
    return _post(headers, payload)


# ---------------------------------------------------------------------------
# Named query payloads (private)
# ---------------------------------------------------------------------------

_Q_USER_STATUS: dict = {
    "operationName": "getUserStatus",
    "variables": {},
    "query": "query getUserStatus{userStatus{username isSignedIn isPremium activeSessionId}}",
}


# ---------------------------------------------------------------------------
# Public typed API functions
# ---------------------------------------------------------------------------

def fetch_user_status(cookie: str = "") -> dict[str, Any]:
    """Return {username, isSignedIn, isPremium, activeSessionId}."""
    return _post(create_headers(cookie), _Q_USER_STATUS)["data"]["userStatus"]


def fetch_all_categories(headers: CaseInsensitiveDict) -> list[dict]:
    """All card categories (with nested card slugs)."""
    payload = {
        "operationName": "GetCategories",
        "variables": {"num": 1000},
        "query": (
            "query GetCategories($num:Int){"
            "categories{slug cards(num:$num){slug categorySlug}}}"
        ),
    }
    return lc_post(headers, payload)["data"]["categories"]


def fetch_card_chapters(headers: CaseInsensitiveDict, card_slug: str) -> list[dict]:
    """All chapters (with items) for a card."""
    payload = {
        "operationName": "GetChaptersWithItems",
        "variables": {"cardSlug": card_slug},
        "query": (
            "query GetChaptersWithItems($cardSlug:String!){"
            "chapters(cardSlug:$cardSlug){"
            "id title slug description items{id title}}}"
        ),
    }
    return lc_post(headers, payload)["data"]["chapters"]


def fetch_card_intro(headers: CaseInsensitiveDict, card_slug: str) -> dict:
    """Return {title, introduction} for a card."""
    payload = {
        "operationName": "GetExtendedCardDetail",
        "variables": {"cardSlug": card_slug},
        "query": (
            "query GetExtendedCardDetail($cardSlug:String!){"
            "card(cardSlug:$cardSlug){title introduction}}"
        ),
    }
    return lc_post(headers, payload)["data"]["card"]


def fetch_card_item(headers: CaseInsensitiveDict, item_id: str) -> dict | None:
    """Full item payload (question / article / htmlArticle links)."""
    payload = {
        "operationName": "GetItem",
        "variables": {"itemId": item_id},
        "query": (
            "query GetItem($itemId:String!){item(id:$itemId){"
            "id title "
            "question{questionId title titleSlug}"
            "article{id title}"
            "htmlArticle{id}"
            "webPage{id}}}"
        ),
    }
    return lc_post(headers, payload)["data"]["item"]


def fetch_questions_count(headers: CaseInsensitiveDict) -> int:
    """Total number of public LeetCode questions."""
    payload = {
        "query": "query{allQuestionsCount{difficulty count}}"
    }
    counts = _post(headers, payload)["data"]["allQuestionsCount"]
    return next(c["count"] for c in counts if c["difficulty"] == "All")


def fetch_all_questions(headers: CaseInsensitiveDict, total: int) -> list[dict]:
    """Return [{title, titleSlug}] for every question, paginating 100 at a time."""
    PAGE_SIZE = 100
    all_questions: list[dict] = []
    skip = 0
    while skip < total:
        log.info("Fetching questions %d - %d / %d", skip + 1, min(skip + PAGE_SIZE, total), total)
        payload = {
            "operationName": "problemsetQuestionList",
            "variables": {"categorySlug": "", "skip": skip, "limit": PAGE_SIZE, "filters": {}},
            "query": (
                "query problemsetQuestionList($categorySlug:String,$limit:Int,$skip:Int,$filters:QuestionListFilterInput){"
                "problemsetQuestionList:questionList(categorySlug:$categorySlug limit:$limit skip:$skip filters:$filters){"
                "questions:data{title titleSlug}}}"
            ),
        }
        page = lc_post(headers, payload)["data"]["problemsetQuestionList"]["questions"]
        if not page:
            break
        all_questions.extend(page)
        skip += PAGE_SIZE
    log.info("Total questions fetched: %d", len(all_questions))
    return all_questions


def fetch_question(headers: CaseInsensitiveDict, slug: str) -> dict:
    """Full question payload for a single slug."""
    payload = {
        "operationName": "GetQuestion",
        "variables": {"titleSlug": slug},
        "query": (
            "query GetQuestion($titleSlug:String!){"
            "question(titleSlug:$titleSlug){"
            "title submitUrl similarQuestions difficulty "
            "companyTagStatsV2 codeDefinition content hints "
            "solution{content}}}"
        ),
    }
    data = lc_post(headers, payload)["data"]["question"]
    if data is None:
        raise ValueError(f"Question '{slug}' not found.")
    return data


def fetch_article(headers: CaseInsensitiveDict, article_id: str) -> dict:
    """Markdown article body."""
    payload = {
        "operationName": "GetArticle",
        "variables": {"articleId": article_id},
        "query": "query GetArticle($articleId:String!){article(id:$articleId){id title body}}",
    }
    return lc_post(headers, payload)["data"]["article"]


def fetch_html_article(headers: CaseInsensitiveDict, html_article_id: str) -> dict:
    """HTML article body."""
    payload = {
        "operationName": "GetHtmlArticle",
        "variables": {"htmlArticleId": html_article_id},
        "query": "query GetHtmlArticle($htmlArticleId:String!){htmlArticle(id:$htmlArticleId){id html}}",
    }
    return lc_post(headers, payload)["data"]["htmlArticle"]


def fetch_playground_codes(headers: CaseInsensitiveDict, uuid: str) -> list[dict]:
    """Return [{code, langSlug}] for an embedded playground."""
    payload = {
        "operationName": "allPlaygroundCodes",
        "query": f"query allPlaygroundCodes{{allPlaygroundCodes(uuid:\"{uuid}\"){{code langSlug}}}}",
    }
    return lc_post(headers, payload)["data"]["allPlaygroundCodes"]


def fetch_company_tags(headers: CaseInsensitiveDict) -> list[dict]:
    """All company tags [{name, slug, questionCount}]."""
    payload = {
        "operationName": "questionCompanyTags",
        "variables": {},
        "query": "query questionCompanyTags{companyTags{name slug questionCount}}",
    }
    return lc_post(headers, payload)["data"]["companyTags"]


def fetch_company_favorite_meta(headers: CaseInsensitiveDict, slug: str) -> dict:
    """Return {questionNumber, categoriesToSlugs[]} for a company slug."""
    payload = {
        "operationName": "favoriteDetailV2ForCompany",
        "variables": {"favoriteSlug": slug},
        "query": (
            "query favoriteDetailV2ForCompany($favoriteSlug:String!){"
            "favoriteDetailV2(favoriteSlug:$favoriteSlug){"
            "questionNumber generatedFavoritesInfo{"
            "defaultFavoriteSlug categoriesToSlugs{categoryName favoriteSlug displayName}}}}"
        ),
    }
    return lc_post(headers, payload)["data"]["favoriteDetailV2"]


def fetch_company_questions(
    headers: CaseInsensitiveDict, favorite_slug: str, limit: int
) -> list[dict]:
    """Return question list for a company favorite slug."""
    payload = {
        "operationName": "favoriteQuestionList",
        "variables": {
            "favoriteSlug": favorite_slug,
            "filter": {"positionRoleTagSlug": "", "skip": 0, "limit": limit},
        },
        "query": (
            "query favoriteQuestionList($favoriteSlug:String!,$filter:FavoriteQuestionFilterInput){"
            "favoriteQuestionList(favoriteSlug:$favoriteSlug,filter:$filter){"
            "questions{difficulty id paidOnly questionFrontendId status "
            "title titleSlug frequency topicTags{name slug}}"
            "totalLength hasMore}}"
        ),
    }
    return lc_post(headers, payload)["data"]["favoriteQuestionList"]["questions"]


# Keep backward-compat alias
check_premium_status = fetch_user_status
