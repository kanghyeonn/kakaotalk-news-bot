import argparse
from pathlib import Path

from app.main import main
from app.paths import PROJECT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rooms",
        default="rooms.json",
        help="사용할 방 설정 JSON 파일 경로. 기본값은 rooms.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    config_path = Path(args.rooms)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    main(config_path=config_path)
