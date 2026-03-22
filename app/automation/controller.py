from typing import Tuple

import uiautomator2 as u2

from app.automation.utils import (
    click,
    connect_device,
    exists,
    human_pause,
    logger,
    press_back,
    retry,
    scroll_until_text,
    set_text,
)


ADMIN_ONLY_TEXT = "관리자만 말할 수 있는 상태입니다."
KAKAO_PACKAGE = "com.kakao.talk"
DEFAULT_PROFILE_NAME = "뉴스이즈구욷"


def connect() -> Tuple[u2.Device, dict]:
    d = connect_device()
    return d, d.info


def open_kakao(d: u2.Device) -> bool:
    try:
        d.app_stop(KAKAO_PACKAGE)
        d.app_start(KAKAO_PACKAGE)
        d.app_wait(KAKAO_PACKAGE, front=True, timeout=10)
        human_pause()
        logger.info("opened kakao app")
        return True
    except Exception:
        logger.exception("failed to open kakao app")
        return False


def click_search(d: u2.Device) -> bool:
    if exists(d, timeout=0.5, className="android.widget.EditText"):
        return True
    return click(d, descriptionContains="검색", dump_prefix="click_search")


def click_search_box(d: u2.Device) -> bool:
    return click(d, className="android.widget.EditText", dump_prefix="click_search_box")


def input_search(d: u2.Device, keyword: str) -> bool:
    return set_text(
        d,
        keyword,
        className="android.widget.EditText",
        dump_prefix="input_search",
    )


def enter_chatroom(d: u2.Device, keyword: str) -> bool:
    if click(
        d,
        textContains=keyword,
        className="android.widget.Button",
        dump_prefix="enter_chatroom",
    ):
        return True
    if click(d, descriptionContains=keyword, dump_prefix="enter_chatroom_desc"):
        return True
    return click(d, textContains=f"채팅방 명{keyword}", dump_prefix="enter_chatroom_text")


def click_chat_box(d: u2.Device) -> bool:
    return click(
        d,
        resourceId="com.kakao.talk:id/message_edit_text",
        dump_prefix="click_chat_box",
    )


def set_chat(d: u2.Device, text: str) -> bool:
    return set_text(
        d,
        text,
        resourceId="com.kakao.talk:id/message_edit_text",
        dump_prefix="set_chat",
        after_delay_range=(5.0, 7.0),
    )


def send_chat(d: u2.Device) -> bool:
    return click(
        d,
        resourceId="com.kakao.talk:id/send_button_layout",
        dump_prefix="send_chat",
    )


def click_openchat(d: u2.Device) -> bool:
    return click(
        d,
        text="오픈채팅",
        className="android.widget.Button",
        dump_prefix="click_openchat",
    )


def click_more_button(d: u2.Device) -> bool:
    if not scroll_until_text(d, "그룹채팅 더보기"):
        return False
    return click(d, text="그룹채팅 더보기", dump_prefix="click_more_button")


def click_enter_community(d: u2.Device) -> bool:
    return click(d, text="커뮤니티 참여하기", dump_prefix="click_enter_community")


def click_join_openchat(d: u2.Device) -> bool:
    if click(
        d,
        resourceId="com.kakao.talk.openlink:id/join_layout",
        dump_prefix="click_join_openchat",
    ):
        return True
    return click(d, text="오픈채팅 참여하기", dump_prefix="click_join_openchat_text")


def click_kakao_profile(d: u2.Device) -> bool:
    return click(d, text="카카오프렌즈", dump_prefix="click_kakao_profile")


def set_profile(d: u2.Device, profile_name: str = DEFAULT_PROFILE_NAME) -> bool:
    return set_text(
        d,
        profile_name,
        resourceId="com.kakao.talk.openlink:id/inner_edit",
        dump_prefix="set_profile",
    )


def check_chatroom_status(d: u2.Device) -> bool:
    return not exists(d, timeout=1.0, text=ADMIN_ONLY_TEXT)


def ensure_chatroom_ready(d: u2.Device) -> bool:
    if exists(d, timeout=1.0, resourceId="com.kakao.talk:id/message_edit_text"):
        return True
    if exists(d, timeout=1.0, resourceId="com.kakao.talk.openlink:id/join_layout") or exists(
        d,
        timeout=1.0,
        text="오픈채팅 참여하기",
    ):
        if not click_join_openchat(d):
            return False
        return exists(d, timeout=5.0, resourceId="com.kakao.talk:id/message_edit_text")
    return False


def click_notice(d: u2.Device) -> bool:
    return click(d, resourceId="com.kakao.talk:id/scroll_content", dump_prefix="click_notice")


def click_back(d: u2.Device) -> bool:
    press_back(d)
    return True


def more_menu(d: u2.Device) -> bool:
    return click(d, description="메뉴 더보기", dump_prefix="more_menu")


def click_exit_chatroom(d: u2.Device) -> bool:
    if not scroll_until_text(d, "채팅방 나가기"):
        return False
    return click(d, text="채팅방 나가기", dump_prefix="click_exit_chatroom")


def click_exit(d: u2.Device) -> bool:
    return click(d, text="나가기", dump_prefix="click_exit")


def search_chatroom(d: u2.Device, keyword: str) -> bool:
    return (
        click_search(d)
        and click_search_box(d)
        and input_search(d, keyword)
        and click_openchat(d)
    )


def open_chatroom_by_keyword(d: u2.Device, keyword: str) -> bool:
    logger.info("opening chatroom by keyword: %s", keyword)
    if not open_kakao(d):
        return False
    if not search_chatroom(d, keyword):
        return False
    return enter_chatroom(d, keyword)


def send_message(d: u2.Device, text: str) -> bool:
    logger.info("sending message with %s characters", len(text))
    if not click_chat_box(d):
        return False
    if not set_chat(d, text):
        return False
    return send_chat(d)


def send_message_to_chatroom(
    d: u2.Device,
    keyword: str,
    text: str,
    retries: int = 3,
    retry_delay: float = 1.5,
) -> bool:
    def _send_once() -> bool:
        if not open_chatroom_by_keyword(d, keyword):
            raise RuntimeError(f"failed to open chatroom: {keyword}")
        if not ensure_chatroom_ready(d):
            raise RuntimeError(f"chatroom is not ready for messaging: {keyword}")
        if not check_chatroom_status(d):
            raise RuntimeError(f"chatroom is admin-only or unavailable: {keyword}")
        if not send_message(d, text):
            raise RuntimeError(f"failed to send message to chatroom: {keyword}")
        return True

    try:
        return retry(
            _send_once,
            retries=retries,
            delay=retry_delay,
            action_name=f"send_message_to_chatroom[{keyword}]",
        )
    except RuntimeError:
        logger.exception("send_message_to_chatroom exhausted retries for %s", keyword)
        return False
    return send_message(d, text)


def join_openchat_community(d: u2.Device, profile_name: str = DEFAULT_PROFILE_NAME) -> bool:
    steps = (
        click_openchat(d),
        click_more_button(d),
        click_enter_community(d),
        click_kakao_profile(d),
        set_profile(d, profile_name),
    )
    return all(steps)
