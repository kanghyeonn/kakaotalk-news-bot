from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    summary: str
    url: str
    published_at: str = ""
    section_name: str = ""
    section_url: str = ""
    body: str = ""


@dataclass
class RoomConfig:
    room_name: str
    search_keyword: str
    message_formatter: str = "summary"
    bundle_title_template: str | None = None
    enabled: bool = True
    source_section: str | None = None
    max_items: int = 10
    include_keywords: list[str] | None = None
