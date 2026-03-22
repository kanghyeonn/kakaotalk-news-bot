# kakaotalk-news-bot

특정 뉴스 웹사이트의 기사를 크롤링해 카카오톡 오픈채팅방에 자동 전송하는 Python 봇입니다.

`rooms.json`으로 방별 수집 대상, 키워드, 메시지 포맷을 제어하고, 실행 시 필요한 뉴스만 공통 수집한 뒤 방별 조건에 맞춰 전송합니다.

## 주요 기능

- 뉴스 섹션별 기사 크롤링
- 일반 섹션 기사 본문 추가 수집
- 방별 섹션 기반 전송
- 방별 키워드 기반 전송
- `daily_top10`, `summary`, `keyword_bundle` 메시지 포맷 지원
- 이미 보낸 기사 URL 중복 전송 방지
- `uiautomator2` 기반 카카오톡 오픈채팅방 검색, 입장, 메시지 전송
- 실패 시 XML 화면 덤프와 로그 저장

## 현재 지원 섹션

- `데일리 TOP10`
- `정치`
- `경제`
- `사회`
- `세계`
- `생활·문화`
- `IT·과학`

`종합` 섹션은 현재 비활성화되어 있습니다.

## 프로젝트 구조

```text
.
├── main.py                     # CLI 진입점
├── rooms.json                  # 기본 방 설정
├── rooms-test.json             # 테스트용 방 설정 예시
├── sent_history.json           # 기본 전송 이력
├── app/
│   ├── main.py                 # 전체 실행 오케스트레이션
│   ├── config.py               # 방 설정 로드
│   ├── history_store.py        # 전송 이력 저장/중복 필터링
│   ├── models.py               # NewsItem, RoomConfig
│   ├── messaging/formatters.py # 메시지 포맷
│   ├── news/crawler.py         # 뉴스 사이트 크롤러
│   ├── news/service.py         # 공통 수집/방별 매핑/키워드 필터링
│   └── automation/
│       ├── controller.py       # 카카오톡 전송 플로우
│       └── utils.py            # UI 자동화 공통 유틸
├── logs/                       # 실행 로그
└── xml/                        # 실패 시 화면 XML 덤프
```

## 동작 흐름

1. `rooms.json` 또는 `--rooms`로 지정한 설정 파일을 로드합니다.
2. 활성화된 방 기준으로 필요한 섹션과 키워드를 분석합니다.
3. 필요한 뉴스만 공통 수집합니다.
4. 방별 조건에 맞게 결과를 매핑합니다.
5. 전송 이력을 기준으로 신규 기사만 남깁니다.
6. 방별 메시지 포맷으로 변환합니다.
7. 카카오톡 오픈채팅방을 검색해 입장합니다.
8. 메시지를 전송하고 이력을 즉시 저장합니다.

## 요구 사항

- Python 3.10+
- Android 기기 또는 에뮬레이터
- PC와 연결 가능한 `adb`
- 안드로이드 기기에 설치된 카카오톡
- `uiautomator2`가 제어할 수 있는 상태의 디바이스

## 설치

가상환경 생성 및 활성화:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

필수 패키지 설치:

```bash
pip install requests beautifulsoup4 uiautomator2
```

필요하면 디바이스 연결 상태를 먼저 확인합니다.

```bash
adb devices
python3 -c "import uiautomator2 as u2; print(u2.connect().info)"
```

## 실행 방법

기본 설정 파일 사용:

```bash
python3 main.py
```

다른 방 설정 파일 사용:

```bash
python3 main.py --rooms rooms-test.json
```

단건 전송 테스트:

```bash
python3 test/send_test_message.py
```

## `rooms.json` 설정 예시

```json
[
  {
    "room_name": "아침 뉴스 방",
    "search_keyword": "아침 뉴스",
    "source_section": "데일리 TOP10",
    "max_items": 10,
    "include_keywords": null,
    "message_formatter": "daily_top10",
    "enabled": true
  },
  {
    "room_name": "키워드 뉴스 방",
    "search_keyword": "키워드 뉴스",
    "source_section": null,
    "max_items": 10,
    "include_keywords": ["부동산"],
    "message_formatter": "keyword_bundle",
    "bundle_title_template": "<{date}({weekday}) 키워드 뉴스>",
    "enabled": true
  }
]
```

## 주요 설정 값

- `room_name`: 관리용 방 이름
- `search_keyword`: 카카오톡 오픈채팅 검색에 사용할 문자열
- `source_section`: 특정 섹션만 수집할 때 사용
- `include_keywords`: 제목, 요약, 본문 기준 OR 조건 키워드 필터
- `max_items`: 최종 전송 최대 건수
- `message_formatter`: `summary`, `daily_top10`, `keyword_bundle`
- `bundle_title_template`: 묶음 메시지 제목 템플릿
- `enabled`: 실행 여부

`include_keywords`가 있으면 `source_section`은 무시됩니다.

## 메시지 포맷

### `summary`

기사별 개별 메시지를 전송합니다.

```text
제목
섹션: 경제
발행: 2026.03.11 09:30
요약
링크
```

### `daily_top10`

데일리 TOP10을 묶음 메시지 1건으로 전송합니다.

```text
<2026.03.17(화) 주요 뉴스>
1. 제목
링크
2. 제목
링크
```

### `keyword_bundle`

키워드로 필터링한 기사를 묶음 메시지 1건으로 전송합니다.

## 전송 이력 파일

- 기본 설정 `rooms.json`은 `sent_history.json`을 사용합니다.
- 예를 들어 `rooms-test.json`을 사용하면 `sent_history-test.json`을 사용합니다.
- 이력은 방 단위로 저장되며, 이미 보낸 URL은 다시 전송하지 않습니다.

## 로그와 디버깅 파일

- 실행 로그: `logs/kakaotalk_bot.log`
- 실패 시 화면 덤프: `xml/*.xml`

카카오톡 UI가 바뀌거나 특정 방 입장에 실패하면 XML 덤프를 먼저 확인하는 편이 가장 빠릅니다.

## 운영 시 주의사항

- `search_keyword`는 방 제목 전체보다 고유한 일부 텍스트가 더 안정적일 수 있습니다.
- 현재 채팅방 탐색은 완전 일치가 아니라 포함 매칭입니다.
- 키워드 방이 하나라도 있으면 일반 섹션 전체를 공통 수집한 뒤 필터링합니다.
- 일반 섹션은 기사 상세 본문까지 추가 요청하므로 실행 시간이 더 길 수 있습니다.
- 자동화 안정성을 위해 UI 동작 사이에 랜덤 지연이 들어 있습니다.

## 참고 문서

- [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md)
- [`ROOMS_GUIDE.md`](./ROOMS_GUIDE.md)
