import json
from pathlib import Path
from typing import Any

from app.models import RoomConfig
from app.paths import PROJECT_ROOT


CONFIG_PATH = PROJECT_ROOT / "rooms.json"


def load_room_configs(path: Path = CONFIG_PATH) -> list[RoomConfig]:
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as file:
        raw_rooms = json.load(file)

    return [RoomConfig(**strip_comment_keys(room)) for room in raw_rooms]


def strip_comment_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_comment_keys(inner_value)
            for key, inner_value in value.items()
            if not key.startswith("_comment")
        }
    if isinstance(value, list):
        return [strip_comment_keys(item) for item in value]
    return value
