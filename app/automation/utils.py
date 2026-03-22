import logging
import os
import random
import time
from typing import Callable, Optional, TypeVar

import uiautomator2 as u2
from app.paths import PROJECT_ROOT


XML_DIR = PROJECT_ROOT / "xml"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "kakaotalk_bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("kakaotalk_bot")
T = TypeVar("T")
DEFAULT_ACTION_DELAY_RANGE = (1.0, 3.0)


def connect_device() -> u2.Device:
    return u2.connect()


def log_progress(message: str) -> None:
    print(message, flush=True)
    logger.info(message)


def human_pause(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def download_xml(file_name: str, d: Optional[u2.Device] = None) -> str:
    device = d or connect_device()
    xml = device.dump_hierarchy()
    XML_DIR.mkdir(parents=True, exist_ok=True)
    path = XML_DIR / file_name

    with open(path, "w", encoding="utf-8") as file:
        file.write(xml)

    return os.path.abspath(path)


def timestamped_xml_name(prefix: str = "screen") -> str:
    return f"{prefix}_{time.strftime('%Y%m%d_%H%M%S')}.xml"


def dump_xml_on_failure(d: u2.Device, prefix: str) -> str:
    return download_xml(timestamped_xml_name(prefix), d=d)


def wait_for(d: u2.Device, timeout: float = 5.0, interval: float = 0.3, **kwargs) -> bool:
    deadline = time.time() + timeout
    while time.time() <= deadline:
        if d(**kwargs).exists:
            return True
        time.sleep(interval)
    return False


def retry(
    action: Callable[[], T],
    retries: int = 3,
    delay: float = 1.0,
    action_name: str = "action",
) -> T:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            result = action()
            logger.info("%s succeeded on attempt %s", action_name, attempt)
            return result
        except Exception as error:
            last_error = error
            logger.exception("%s failed on attempt %s", action_name, attempt)
            if attempt < retries:
                time.sleep(delay)

    raise RuntimeError(f"{action_name} failed after {retries} attempts") from last_error


def click(
    d: u2.Device,
    timeout: float = 5.0,
    dump_prefix: Optional[str] = None,
    after_delay_range: tuple[float, float] = DEFAULT_ACTION_DELAY_RANGE,
    **kwargs,
) -> bool:
    try:
        if not wait_for(d, timeout=timeout, **kwargs):
            if dump_prefix:
                dump_xml_on_failure(d, dump_prefix)
            logger.warning("click target not found: %s", kwargs)
            return False

        d(**kwargs).click()
        human_pause(*after_delay_range)
        logger.info("clicked target: %s", kwargs)
        return True
    except Exception:
        if dump_prefix:
            dump_xml_on_failure(d, dump_prefix)
        logger.exception("click raised exception: %s", kwargs)
        return False


def set_text(
    d: u2.Device,
    text: str,
    timeout: float = 5.0,
    dump_prefix: Optional[str] = None,
    after_delay_range: tuple[float, float] = DEFAULT_ACTION_DELAY_RANGE,
    **kwargs,
) -> bool:
    try:
        if not wait_for(d, timeout=timeout, **kwargs):
            if dump_prefix:
                dump_xml_on_failure(d, dump_prefix)
            logger.warning("set_text target not found: %s", kwargs)
            return False

        d(**kwargs).set_text(text)
        human_pause(*after_delay_range)
        logger.info("set text on target: %s", kwargs)
        return True
    except Exception:
        if dump_prefix:
            dump_xml_on_failure(d, dump_prefix)
        logger.exception("set_text raised exception: %s", kwargs)
        return False


def exists(d: u2.Device, timeout: float = 0.0, **kwargs) -> bool:
    if timeout <= 0:
        return d(**kwargs).exists
    return wait_for(d, timeout=timeout, **kwargs)


def is_exit(d: u2.Device, timeout: float = 0.0, **kwargs) -> bool:
    return exists(d, timeout=timeout, **kwargs)


def scroll_until_text(d: u2.Device, text: str, max_scroll: int = 30, pause: float = 0.5) -> bool:
    for _ in range(max_scroll):
        if d(text=text).exists or d(textContains=text).exists:
            return True

        d.swipe_ext("up", scale=0.8)
        time.sleep(pause)

    return False


def press_back(d: u2.Device) -> None:
    d.press("back")
    human_pause(*DEFAULT_ACTION_DELAY_RANGE)
