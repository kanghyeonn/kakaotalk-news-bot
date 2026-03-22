# rooms.json Guide

`rooms.json`은 카카오톡으로 뉴스를 보낼 방 설정 파일이다.

파일 형식은 JSON 배열이며, 각 원소가 채팅방 하나의 설정이다.

기본 실행 대상은 `rooms.json`이고, 루트 `main.py` 실행 시 `--rooms` 인자로 다른 설정 파일을 지정할 수 있다.

예시:

```bash
python3 main.py
python3 main.py --rooms rooms-test.json
```

## 현재 프로젝트 구조

- 실행 진입점은 루트 `main.py`다.
- 실제 애플리케이션 코드는 `app/` 아래에 있다.
- 방 설정 파일은 프로젝트 루트에 둔다.
- 크롤링 대상 사이트 URL은 `rooms.json`이 아니라 루트 `.env`에서 관리한다.
- 기본 설정 `rooms.json`은 `sent_history.json`을 사용한다.
- 다른 설정 파일을 쓰면 같은 접미사의 별도 이력 파일을 사용한다.
  - 예: `rooms-test.json` -> `sent_history-test.json`

주요 파일:

- `app/config.py`
  - 설정 파일 로드
- `app/models.py`
  - `RoomConfig`, `NewsItem`
- `app/news/service.py`
  - 공통 수집과 방별 매핑
- `app/messaging/formatters.py`
  - 메시지 포맷 로직
- `app/automation/controller.py`
  - 카카오톡 전송 플로우

## 기본 구조

```json
[
  {
    "room_name": "테스트채팅방123",
    "search_keyword": "테스트채팅방123",
    "source_section": "데일리 TOP10",
    "max_items": 10,
    "message_formatter": "daily_top10",
    "enabled": true
  }
]
```

## 속성 설명

### `room_name`

- 의미: 관리용 방 이름
- 용도: 로그, 출력, 설정 식별용

예시:

```json
"room_name": "경제 뉴스 오픈채팅"
```

### `search_keyword`

- 의미: 카카오톡 오픈채팅 검색창에 입력할 문자열
- 용도: 실제 채팅방 탐색에 사용
- 현재 코드는 완전 일치가 아니라 포함 매칭으로 채팅방을 찾는다
- 이모티콘이 있는 방은 고유 텍스트만 넣는 편이 더 안정적이다

예시:

```json
"search_keyword": "경제 뉴스방"
```

### `source_section`

- 의미: 특정 섹션 뉴스만 수집할 때 사용하는 값
- 기본값: `"데일리 TOP10"`
- 지원 값:
  - `데일리 TOP10`
  - `정치`
  - `경제`
  - `사회`
  - `세계`
  - `생활·문화`
  - `IT·과학`
- 현재 `종합` 섹션은 비활성화 상태다
- `include_keywords`가 있으면 무시된다

예시:

```json
"source_section": "경제"
```

### `include_keywords`

- 의미: 특정 키워드가 들어간 기사만 보내고 싶을 때 쓰는 배열
- 매칭 대상:
  - 제목
  - 요약
  - 본문
- 동작:
  - 값이 있으면 일반 섹션 전체를 공통 수집한다
  - 키워드가 하나라도 포함된 기사만 남긴다
  - 즉 AND가 아니라 OR 조건이다
  - 이 경우 `source_section`은 사용하지 않는다

예시:

```json
"include_keywords": ["대통령", "국민의힘", "추경"]
```

### `max_items`

- 의미: 한 번 실행할 때 최종적으로 전송할 최대 기사 수
- 기본값: `10`
- 동작:
  - 섹션 모드에서는 같은 섹션을 보는 방들 중 가장 큰 `max_items` 기준으로 공통 수집한다
  - 키워드 모드에서는 전체 공통 수집 후 필터링하고 최종 결과를 `max_items`까지 자른다

예시:

```json
"max_items": 5
```

### `message_formatter`

- 의미: 등록된 메시지 포맷 함수 이름
- 현재 지원 값:
  - `summary`
  - `daily_top10`
  - `keyword_bundle`
- 기본값: `"summary"`

예시:

```json
"message_formatter": "summary"
```

### `bundle_title_template`

- 의미: 묶음 메시지 제목을 방마다 직접 지정하는 템플릿
- 적용 대상:
  - `daily_top10`
  - `keyword_bundle`
- 기본값: `<{date}({weekday}) 주요 뉴스>`
- 사용 가능 변수:
  - `{date}`
  - `{weekday}`
  - `{room_name}`
  - `{search_keyword}`

예시:

```json
"bundle_title_template": "<{date}({weekday}) 경제방 주요 뉴스>"
```

### `enabled`

- 의미: 실제 실행 대상 포함 여부
- 값:
  - `true`: 실행
  - `false`: 무시

예시:

```json
"enabled": true
```

## 설정 우선순위

### 수집 대상 결정

1. `include_keywords`가 있으면 전체 일반 섹션 수집 후 키워드 필터링
2. `include_keywords`가 없으면 `source_section` 사용
3. `source_section`도 없으면 기본값 `데일리 TOP10`

### 실행 방식

1. 설정 파일에서 활성 방 목록을 읽는다
2. 방 설정을 분석해 필요한 뉴스만 공통 수집한다
3. 방별 조건에 맞게 결과를 매핑한다
4. 전송 이력 기준으로 신규 기사만 남긴다
5. 메시지 포맷을 적용해 전송한다

### 메시지 포맷 결정

1. `message_formatter` 사용
2. 없으면 기본값 `summary`

## 포맷 예시

### `daily_top10`

데일리 TOP10 묶음 메시지:

```text
<2026.03.17(화) 주요 뉴스>
1. 제목
링크
2. 제목
링크
```

### `summary`

기사별 개별 메시지:

```text
제목
섹션: 경제
발행: 2026.03.11 09:30
요약
링크
```

### `keyword_bundle`

키워드 기사 묶음 메시지:

```text
<2026.03.17(화) 주요 뉴스>
1. 기사 제목
링크

2. 기사 제목
링크
```

주의:

- `keyword_bundle`은 기사별 `발행:` 줄을 붙이지 않는다.
- 묶음 제목의 날짜는 기사 발행일이 아니라 메시지 생성 날짜다.

## 예시 1: 데일리 TOP10 방

```json
[
  {
    "room_name": "데일리 뉴스방",
    "search_keyword": "데일리 뉴스방",
    "source_section": "데일리 TOP10",
    "max_items": 10,
    "message_formatter": "daily_top10",
    "bundle_title_template": "<{date}({weekday}) 데일리 뉴스방>",
    "enabled": true
  }
]
```

## 예시 2: 경제 섹션 방

```json
[
  {
    "room_name": "경제 뉴스방",
    "search_keyword": "경제 뉴스방",
    "source_section": "경제",
    "max_items": 5,
    "message_formatter": "summary",
    "enabled": true
  }
]
```

## 예시 3: 키워드 방

```json
[
  {
    "room_name": "정책 키워드 뉴스방",
    "search_keyword": "정책 키워드 뉴스방",
    "include_keywords": ["대통령", "국민의힘", "추경"],
    "max_items": 10,
    "message_formatter": "keyword_bundle",
    "bundle_title_template": "<{date}({weekday}) 정책 키워드 뉴스>",
    "enabled": true
  }
]
```

## `.env`와의 역할 분리

`rooms.json`은 방별 수집 조건과 메시지 형식을 제어한다.

루트 `.env`는 크롤링 대상 사이트 URL을 제어한다.

현재 크롤러가 사용하는 주요 환경변수:

- `CRAWLER_BASE_URL`
- `CRAWLER_SECTION_DAILY_TOP10_URL`
- `CRAWLER_SECTION_POLITICS_URL`
- `CRAWLER_SECTION_ECONOMY_URL`
- `CRAWLER_SECTION_SOCIETY_URL`
- `CRAWLER_SECTION_WORLD_URL`
- `CRAWLER_SECTION_CULTURE_URL`
- `CRAWLER_SECTION_IT_SCIENCE_URL`

즉:

- 어떤 뉴스를 어떤 방에 보낼지는 `rooms.json`
- 어디를 크롤링할지는 `.env`

## 운영 시 주의사항

- `source_section`과 `include_keywords`를 동시에 쓰지 않는 편이 명확하다.
- 키워드 방이 하나라도 있으면 일반 섹션 전체를 수집하므로 실행 시간이 늘 수 있다.
- 일반 섹션은 본문까지 추가 요청하므로 `데일리 TOP10`보다 느리다.
- 진행 로그는 `logs/kakaotalk_bot.log`에 저장된다.
- 자동화 실패 시 XML 덤프는 `xml/` 폴더에 남는다.
- `.env`와 `sent_history*.json`은 운영 파일이므로 git에 올리지 않는 전제를 유지한다.
