from datetime import datetime
from typing import Callable

from app.models import NewsItem, RoomConfig


MessageFormatter = Callable[[RoomConfig, list[NewsItem]], list[str]]
WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


def format_single_news_message(news: NewsItem) -> str:
    published_line = f"\n발행: {news.published_at}" if news.published_at else ""
    section_line = f"\n섹션: {news.section_name}" if news.section_name else ""
    return f"{news.title}{section_line}{published_line}\n{news.summary}\n{news.url}"


def build_bundle_title(room: RoomConfig | None = None) -> str:
    now = datetime.now()
    today = now.strftime("%Y.%m.%d")
    weekday = WEEKDAY_NAMES[now.weekday()]
    if room and room.bundle_title_template:
        return room.bundle_title_template.format(
            date=today,
            weekday=weekday,
            room_name=room.room_name,
            search_keyword=room.search_keyword,
        )
    return f"<{today}({weekday}) 주요 뉴스>"


def format_bundle_news_message(items: list[NewsItem], room: RoomConfig | None = None) -> str:
    lines = [build_bundle_title(room)]
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item.title}")
        lines.append(item.url + "\n")
    return "\n".join(lines)


def format_daily_top10_room_message(items: list[NewsItem], room: RoomConfig | None = None) -> str:
    return format_bundle_news_message(items, room=room)


def format_keyword_bundle_message(room: RoomConfig, items: list[NewsItem]) -> str:
    return format_bundle_news_message(items, room=room)


def format_summary_messages(room: RoomConfig, items: list[NewsItem]) -> list[str]:
    del room
    return [format_single_news_message(item) for item in items]


def format_daily_top10_messages(room: RoomConfig, items: list[NewsItem]) -> list[str]:
    return [format_daily_top10_room_message(items, room=room)]


def format_keyword_bundle_messages(room: RoomConfig, items: list[NewsItem]) -> list[str]:
    return [format_keyword_bundle_message(room, items)]


FORMATTERS: dict[str, MessageFormatter] = {
    "summary": format_summary_messages,
    "daily_top10": format_daily_top10_messages,
    "keyword_bundle": format_keyword_bundle_messages,
}


def format_messages_for_room(room: RoomConfig, items: list[NewsItem]) -> list[str]:
    formatter = FORMATTERS.get(resolve_formatter_name(room), format_summary_messages)
    return formatter(room, items)


def uses_bundle_message(room: RoomConfig) -> bool:
    return resolve_formatter_name(room) in {"daily_top10", "keyword_bundle"}


def resolve_formatter_name(room: RoomConfig) -> str:
    return room.message_formatter
