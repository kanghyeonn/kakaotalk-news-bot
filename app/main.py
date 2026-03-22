import random
import time
from pathlib import Path
from typing import List

from app.automation.controller import connect, send_message_to_chatroom
from app.automation.utils import log_progress
from app.config import load_room_configs
from app.history_store import (
    SentHistory,
    filter_new_items,
    history_path_for_config,
    load_sent_history,
    record_sent_items,
    save_sent_history,
)
from app.messaging.formatters import format_messages_for_room, uses_bundle_message
from app.models import NewsItem, RoomConfig
from app.news.service import build_news_map_for_rooms, room_news_map_key


MIN_SEND_DELAY_SECONDS = 1.0
MAX_SEND_DELAY_SECONDS = 5.0


def run_room(room: RoomConfig, news_items: list[NewsItem], history: SentHistory) -> List[NewsItem]:
    log_progress(f"[ROOM] 시작: {room.room_name}")
    log_progress(f"[ROOM] 사전 수집 뉴스 확인: {room.room_name} ({len(news_items)}건)")
    fresh_items = filter_new_items(room.search_keyword, news_items, history)
    log_progress(f"[ROOM] 신규 기사 필터링 완료: {room.room_name} ({len(fresh_items)}건)")
    if not fresh_items:
        log_progress(f"[ROOM] 전송할 신규 기사가 없음: {room.room_name}")
        return []

    log_progress(f"[ROOM] 카카오톡 디바이스 연결 중: {room.room_name}")
    device, _ = connect()
    log_progress(f"[ROOM] 메시지 포맷 생성 중: {room.room_name}")
    messages = format_messages_for_room(room, fresh_items)
    if len(messages) == 1 and uses_bundle_message(room):
        log_progress(f"[ROOM] 묶음 메시지 전송 중: {room.room_name}")
        if send_message_to_chatroom(device, room.search_keyword, messages[0]):
            record_sent_items(room.search_keyword, fresh_items, history)
            log_progress(f"[ROOM] 묶음 메시지 전송 완료: {room.room_name} ({len(fresh_items)}건)")
            return fresh_items
        log_progress(f"[ROOM] 묶음 메시지 전송 실패: {room.room_name}")
        return []

    sent_items: List[NewsItem] = []
    for index, (item, message) in enumerate(zip(fresh_items, messages)):
        if index > 0:
            time.sleep(random.uniform(MIN_SEND_DELAY_SECONDS, MAX_SEND_DELAY_SECONDS))
        log_progress(f"[ROOM] 개별 메시지 전송 중: {room.room_name} ({index + 1}/{len(messages)})")
        if send_message_to_chatroom(device, room.search_keyword, message):
            sent_items.append(item)
            continue
        log_progress(f"[ROOM] 개별 메시지 전송 실패: {room.room_name} ({index + 1}/{len(messages)})")
        break

    record_sent_items(room.search_keyword, sent_items, history)
    log_progress(f"[ROOM] 개별 메시지 전송 완료: {room.room_name} ({len(sent_items)}건)")
    return sent_items


def main(config_path: Path | None = None) -> None:
    rooms = [room for room in load_room_configs(config_path) if room.enabled]
    if not rooms:
        target_name = config_path.name if config_path else "rooms.json"
        print(f"활성화된 채팅방 설정이 없습니다. {target_name}을 확인하세요.")
        return

    target_path = config_path if config_path is not None else "rooms.json"
    history_path = history_path_for_config(config_path)
    log_progress(f"[MAIN] 설정 파일: {target_path}")
    log_progress(f"[MAIN] 전송 이력 파일: {history_path}")
    log_progress(f"[MAIN] 활성화된 방 수: {len(rooms)}")
    history = load_sent_history(history_path)
    total_sent = 0
    log_progress("[MAIN] 방 설정 분석 후 공통 뉴스 수집 시작")
    room_news_map = build_news_map_for_rooms(rooms)
    log_progress("[MAIN] 공통 뉴스 수집 및 방별 매핑 완료")

    for room in rooms:
        try:
            news_items = room_news_map.get(room_news_map_key(room), [])
            sent_items = run_room(room, news_items, history)
        except Exception as error:
            print(f"{room.room_name}: 실행 실패 ({error})")
            save_sent_history(history, history_path)
            continue
        total_sent += len(sent_items)
        save_sent_history(history, history_path)
        log_progress(f"[MAIN] 전송 이력 저장 완료: {room.room_name}")
        print(f"{room.room_name}: {len(sent_items)}건 전송")
    print(f"총 전송 건수: {total_sent}")


if __name__ == "__main__":
    main()
