from app.automation.utils import log_progress
from app.models import NewsItem, RoomConfig
from app.news.crawler import CrawledNewsItem, fetch_all_sections, fetch_section


def log_news_service(message: str) -> None:
    log_progress(message)


def room_news_map_key(room: RoomConfig) -> str:
    keywords = ",".join(room.include_keywords or [])
    source_section = room.source_section or "데일리 TOP10"
    return "|".join(
        [
            room.room_name,
            room.search_keyword,
            source_section,
            room.message_formatter,
            keywords,
            str(room.max_items),
        ]
    )


def build_news_map_for_rooms(rooms: list[RoomConfig]) -> dict[str, list[NewsItem]]:
    if not rooms:
        return {}

    rooms_with_keywords = [room for room in rooms if room.include_keywords]
    section_limits = collect_section_limits(rooms)
    section_cache: dict[str, list[NewsItem]] = {}
    all_keyword_items: list[NewsItem] = []

    if rooms_with_keywords:
        keyword_source_sections = fetch_all_sections_for_keywords()
        all_keyword_items = flatten_section_items(keyword_source_sections)
        for section_name, items in keyword_source_sections.items():
            if section_name in section_limits:
                section_cache[section_name] = items

    for section_name, limit in section_limits.items():
        if section_name in section_cache:
            continue
        section_cache[section_name] = fetch_section_news(section_name, limit=limit)

    room_news_map: dict[str, list[NewsItem]] = {}
    for room in rooms:
        room_news_map[room_news_map_key(room)] = select_news_for_room(
            room,
            section_cache=section_cache,
            all_keyword_items=all_keyword_items,
        )
    return room_news_map


def fetch_news_for_room(room: RoomConfig) -> list[NewsItem]:
    return build_news_map_for_rooms([room]).get(room_news_map_key(room), [])


def collect_section_limits(rooms: list[RoomConfig]) -> dict[str, int]:
    section_limits: dict[str, int] = {}
    for room in rooms:
        if room.include_keywords:
            continue
        section_name = room.source_section or "데일리 TOP10"
        previous_limit = section_limits.get(section_name, 0)
        section_limits[section_name] = max(previous_limit, room.max_items)
    return section_limits


def fetch_all_sections_for_keywords() -> dict[str, list[NewsItem]]:
    log_news_service("[NEWS] 키워드 방 감지: 전체 섹션 공통 수집 시작")
    all_sections = fetch_all_sections(limit_per_section=None)
    section_cache = {
        section_name: [to_news_item(item) for item in section_items]
        for section_name, section_items in all_sections.items()
    }
    total_items = sum(len(items) for items in section_cache.values())
    log_news_service(f"[NEWS] 전체 섹션 공통 수집 완료 ({total_items}건)")
    return section_cache


def fetch_section_news(section_name: str, limit: int) -> list[NewsItem]:
    log_news_service(f"[NEWS] 공통 섹션 수집 시작: {section_name} (limit={limit})")
    crawled_items = fetch_section(section_name=section_name, limit=limit)
    log_news_service(f"[NEWS] 공통 섹션 수집 완료: {section_name} ({len(crawled_items)}건)")
    return [to_news_item(item) for item in crawled_items]


def flatten_section_items(section_cache: dict[str, list[NewsItem]]) -> list[NewsItem]:
    flattened: list[NewsItem] = []
    seen_urls: set[str] = set()
    for items in section_cache.values():
        for item in items:
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            flattened.append(item)
    return flattened


def select_news_for_room(
    room: RoomConfig,
    section_cache: dict[str, list[NewsItem]],
    all_keyword_items: list[NewsItem],
) -> list[NewsItem]:
    if room.include_keywords:
        log_news_service(
            f"[NEWS] 방별 키워드 매핑 시작: {room.room_name} "
            f"(keywords={room.include_keywords}, max_items={room.max_items})"
        )
        filtered_items = filter_items_by_keywords(all_keyword_items, room.include_keywords)
        log_news_service(f"[NEWS] 방별 키워드 매핑 완료: {room.room_name} ({len(filtered_items)}건)")
        return filtered_items[: room.max_items]

    section_name = room.source_section or "데일리 TOP10"
    section_items = section_cache.get(section_name, [])
    selected_items = section_items[: room.max_items]
    log_news_service(
        f"[NEWS] 방별 섹션 매핑 완료: {room.room_name} "
        f"(section={section_name}, items={len(selected_items)})"
    )
    return selected_items


def filter_items_by_keywords(items: list[NewsItem], keywords: list[str] | None) -> list[NewsItem]:
    normalized_keywords = [keyword.strip().lower() for keyword in (keywords or []) if keyword.strip()]
    if not normalized_keywords:
        return list(items)

    filtered_items: list[NewsItem] = []
    for item in items:
        haystack = " ".join([item.title, item.summary, item.body]).lower()
        if any(keyword in haystack for keyword in normalized_keywords):
            filtered_items.append(item)
    return filtered_items


def to_news_item(item: CrawledNewsItem) -> NewsItem:
    return NewsItem(
        title=item.title,
        summary=item.summary,
        url=item.url,
        published_at=item.published_at,
        section_name=item.section_name,
        section_url=item.section_url,
        body=item.body,
    )
