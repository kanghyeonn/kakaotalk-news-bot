from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from typing import Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from app.automation.utils import log_progress
from app.env import get_env


DEFAULT_TIMEOUT = 30.0
REQUEST_DELAY_RANGE = (1.0, 3.0)
MAX_REQUEST_RETRIES = 3
DATE_PATTERN = re.compile(r"\d{4}\.\d{1,2}\.\d{1,2}\s+\d{1,2}:\d{2}")
RANK_PATTERN = re.compile(r"^\d+$")
LEADING_RANK_PATTERN = re.compile(r"^\d+[\.\)]?\s*")

SECTION_ALIASES: Dict[str, str] = {
    "데일리 TOP10": "데일리 TOP10",
    "데일리_TOP10": "데일리 TOP10",
    "daily_top10": "데일리 TOP10",
    # "종합": "종합",
    "정치": "정치",
    "경제": "경제",
    "사회": "사회",
    "세계": "세계",
    "생활·문화": "생활·문화",
    "생활,문화": "생활·문화",
    "생활_문화": "생활·문화",
    "IT·과학": "IT·과학",
    "IT,과학": "IT·과학",
    "IT_과학": "IT·과학",
    "it_science": "IT·과학",
}


@dataclass
class CrawledNewsItem:
    title: str
    summary: str
    url: str
    published_at: str
    section_name: str
    section_url: str
    body: str = ""


class CrawlError(RuntimeError):
    pass


def log_crawler(message: str) -> None:
    log_progress(message)


def get_base_url() -> str:
    return get_env("CRAWLER_BASE_URL")


def get_section_urls() -> Dict[str, str]:
    return {
        "데일리 TOP10": get_env("CRAWLER_SECTION_DAILY_TOP10_URL"),
        "정치": get_env("CRAWLER_SECTION_POLITICS_URL"),
        "경제": get_env("CRAWLER_SECTION_ECONOMY_URL"),
        "사회": get_env("CRAWLER_SECTION_SOCIETY_URL"),
        "세계": get_env("CRAWLER_SECTION_WORLD_URL"),
        "생활·문화": get_env("CRAWLER_SECTION_CULTURE_URL"),
        "IT·과학": get_env("CRAWLER_SECTION_IT_SCIENCE_URL"),
    }


def fetch_section(section_name: str, limit: int | None = 10) -> List[CrawledNewsItem]:
    canonical_name = normalize_section_name(section_name)
    log_crawler(f"[CRAWLER] 섹션 수집 시작: {canonical_name} (limit={limit or 'all'})")
    section_url = get_section_urls()[canonical_name]
    html = fetch_html(section_url)
    items = parse_section_page(
        html=html,
        section_name=canonical_name,
        section_url=section_url,
        limit=limit,
    )
    log_crawler(f"[CRAWLER] 섹션 수집 완료: {canonical_name} ({len(items)}건)")
    return items


def fetch_all_sections(limit_per_section: int | None = 10) -> Dict[str, List[CrawledNewsItem]]:
    sections: Dict[str, List[CrawledNewsItem]] = {}
    for section_name in get_section_urls():
        try:
            sections[section_name] = fetch_section(section_name, limit=limit_per_section)
        except requests.RequestException:
            log_crawler(f"[CRAWLER] 섹션 수집 실패: {section_name}")
            sections[section_name] = []
    return sections


def fetch_html(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    last_error: requests.RequestException | None = None
    for attempt in range(1, MAX_REQUEST_RETRIES + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
            if response.encoding is None:
                response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except requests.RequestException as error:
            last_error = error
            log_crawler(
                f"[CRAWLER] 요청 실패: {url} "
                f"(attempt={attempt}/{MAX_REQUEST_RETRIES}, error={error})"
            )
            if attempt == MAX_REQUEST_RETRIES:
                break
            time.sleep(random.uniform(*REQUEST_DELAY_RANGE))

    raise last_error or CrawlError(f"failed to fetch html: {url}")


def parse_section_page(
    html: str,
    section_name: str,
    section_url: str,
    limit: int | None = 10,
) -> List[CrawledNewsItem]:
    soup = BeautifulSoup(html, "html.parser")
    cards = [
        tag for tag in soup.select('a[href^="/news/"]')
        if extract_card_text_parts(tag)
    ]

    items: List[CrawledNewsItem] = []
    seen_urls = set()
    detail_cache: Dict[str, str] = {}

    for card in cards:
        item = parse_card(
            card,
            section_name=section_name,
            section_url=section_url,
            detail_cache=detail_cache,
        )
        if not item or item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        items.append(item)
        if limit is not None and len(items) >= limit:
            break

    return items


def parse_card(
    card: Tag,
    section_name: str,
    section_url: str,
    detail_cache: Dict[str, str],
) -> CrawledNewsItem | None:
    href = clean_text(card.get("href"))
    if not href:
        return None

    parts = extract_card_text_parts(card)
    if len(parts) < 2:
        return None

    title_index = 0
    if is_badge_text(parts[0]) and len(parts) >= 2:
        title_index = 1

    title = normalize_card_title(parts[title_index], section_name=section_name)
    published_at = ""
    summary_parts: List[str] = []

    title, trailing_published_at = split_trailing_published_at(title)
    if trailing_published_at:
        published_at = trailing_published_at

    for part in parts[title_index + 1 :]:
        if DATE_PATTERN.fullmatch(part):
            published_at = part
            continue
        summary_parts.append(part)

    summary = "\n\n".join(summary_parts).strip() or title
    article_url = urljoin(get_base_url(), href)
    body = ""
    if section_name != "데일리 TOP10":
        body = fetch_article_body(article_url, detail_cache)

    return CrawledNewsItem(
        title=title,
        summary=summary,
        url=article_url,
        published_at=published_at,
        section_name=section_name,
        section_url=section_url,
        body=body,
    )


def extract_card_text_parts(card: Tag) -> List[str]:
    content_block = next(
        (
            child for child in card.find_all("div", recursive=False)
            if "flex-1" in child.get("class", [])
        ),
        None,
    )
    if content_block is None:
        return []

    parts = []
    for child in content_block.find_all("div", recursive=False):
        text = clean_text(child.get_text("\n", strip=True))
        if not text or RANK_PATTERN.fullmatch(text):
            continue
        parts.append(text)
    return parts


def normalize_section_name(section_name: str) -> str:
    if not section_name:
        raise CrawlError("section_name is required")

    normalized = SECTION_ALIASES.get(section_name.strip())
    if normalized is None:
        supported = ", ".join(get_section_urls())
        raise CrawlError(f"unsupported section_name: {section_name}. supported: {supported}")
    return normalized


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split())


def normalize_card_title(title: str, section_name: str) -> str:
    del section_name
    return LEADING_RANK_PATTERN.sub("", title).strip()


def split_trailing_published_at(title: str) -> tuple[str, str]:
    match = re.search(r"^(.*?)(\d{4}\.\d{1,2}\.\d{1,2}\s+\d{1,2}:\d{2})$", title)
    if not match:
        return title, ""
    cleaned_title = match.group(1).rstrip()
    published_at = match.group(2)
    return cleaned_title, published_at


def is_badge_text(value: str) -> bool:
    return "건 분석" in value or value.endswith("위")


def fetch_article_body(article_url: str, detail_cache: Dict[str, str]) -> str:
    cached = detail_cache.get(article_url)
    if cached is not None:
        return cached

    try:
        html = fetch_html(article_url)
    except requests.RequestException:
        detail_cache[article_url] = ""
        return ""

    soup = BeautifulSoup(html, "html.parser")
    body_node = soup.select_one("div.prose.max-w-none.whitespace-pre-wrap")
    if body_node is None:
        detail_cache[article_url] = ""
        return ""

    body = clean_body_text(body_node.get_text("\n", strip=True))
    detail_cache[article_url] = body
    return body


def clean_body_text(value: str) -> str:
    lines = [" ".join(line.split()) for line in value.splitlines()]
    filtered = [line for line in lines if line]
    return "\n\n".join(filtered)
