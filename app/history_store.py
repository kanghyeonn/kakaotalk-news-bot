import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from app.models import NewsItem
from app.paths import PROJECT_ROOT


HISTORY_PATH = PROJECT_ROOT / "sent_history.json"
RoomHistory = dict[str, list[str]]
SentHistory = dict[str, RoomHistory]
MAX_HISTORY_ITEMS_PER_ROOM = 200


def current_history_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def history_path_for_config(config_path: Path | None = None) -> Path:
    if config_path is None or config_path.name == "rooms.json":
        return HISTORY_PATH

    config_name = config_path.stem
    suffix = config_name.removeprefix("rooms")
    if suffix.startswith("-"):
        suffix = suffix[1:]
    if not suffix:
        return HISTORY_PATH
    return PROJECT_ROOT / f"sent_history-{suffix}.json"


def normalize_room_history(raw_room_history: object) -> RoomHistory:
    if isinstance(raw_room_history, list):
        return {current_history_date(): [url for url in raw_room_history if isinstance(url, str)]}

    if not isinstance(raw_room_history, dict):
        return {}

    normalized: RoomHistory = {}
    for date_key, urls in raw_room_history.items():
        if not isinstance(date_key, str) or not isinstance(urls, list):
            continue
        normalized[date_key] = [url for url in urls if isinstance(url, str)]
    return normalized


def normalize_history(raw_history: object) -> SentHistory:
    if not isinstance(raw_history, dict):
        return {}

    normalized: SentHistory = {}
    for room_key, room_history in raw_history.items():
        if not isinstance(room_key, str):
            continue
        normalized[room_key] = normalize_room_history(room_history)
    return normalized


def flatten_room_urls(room_history: RoomHistory) -> list[str]:
    flattened: list[str] = []
    seen_urls: set[str] = set()
    for date_key in sorted(room_history.keys()):
        for url in room_history[date_key]:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            flattened.append(url)
    return flattened


def prune_room_history(room_history: RoomHistory, max_items: int = MAX_HISTORY_ITEMS_PER_ROOM) -> RoomHistory:
    flattened_urls = flatten_room_urls(room_history)
    keep_urls = set(flattened_urls[-max_items:])
    if len(keep_urls) == len(flattened_urls):
        return room_history

    pruned_history: RoomHistory = {}
    for date_key in sorted(room_history.keys()):
        kept_urls = [url for url in room_history[date_key] if url in keep_urls]
        if kept_urls:
            pruned_history[date_key] = kept_urls
    return pruned_history


def load_sent_history(path: Path = HISTORY_PATH) -> SentHistory:
    if not path.exists():
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return normalize_history(json.load(file))


def save_sent_history(history: SentHistory, path: Path = HISTORY_PATH) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(normalize_history(history), file, ensure_ascii=False, indent=2)


def filter_new_items(room_key: str, items: Iterable[NewsItem], history: SentHistory) -> list[NewsItem]:
    sent_urls = set(flatten_room_urls(history.get(room_key, {})))
    return [item for item in items if item.url not in sent_urls]


def record_sent_items(room_key: str, items: Iterable[NewsItem], history: SentHistory) -> None:
    room_history = normalize_room_history(history.get(room_key, {}))
    sent_urls = set(flatten_room_urls(room_history))
    date_key = current_history_date()
    today_urls = list(room_history.get(date_key, []))
    for item in items:
        if item.url in sent_urls:
            continue
        today_urls.append(item.url)
        sent_urls.add(item.url)
    if today_urls:
        room_history[date_key] = today_urls
    history[room_key] = prune_room_history(room_history)
