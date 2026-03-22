# Project Context

## 목적

이 프로젝트는 외부 뉴스 사이트를 크롤링해서, 방 설정에 맞는 형식으로 가공한 뒤 카카오톡 오픈채팅방에 자동 전송하는 봇이다.

현재 구조는 크게 두 축으로 나뉜다.

1. 뉴스 수집과 방별 매핑
2. 카카오톡 오픈채팅 자동 전송

## 현재 구현 상태

- 루트 `main.py`가 진입점이고, 실제 오케스트레이션은 `app/main.py`가 담당한다.
- `rooms.json` 계열 설정 파일로 방별 섹션, 키워드, 전송 포맷, 최대 기사 수를 제어한다.
- 크롤링 대상 사이트의 기본 URL과 섹션 URL은 저장소에 하드코딩하지 않고 루트 `.env`에서 읽는다.
- 현재 활성 수집 섹션은 `데일리 TOP10`, `정치`, `경제`, `사회`, `세계`, `생활·문화`, `IT·과학`이다.
- `종합` 섹션은 현재 코드에서 비활성화되어 있다.
- 기사별로 제목, 요약, 링크, 발행 시각을 수집한다.
- `데일리 TOP10`을 제외한 일반 섹션은 기사 상세 페이지 본문까지 추가 수집한다.
- 제목 앞 순위 번호는 제거해서 저장한다.
- 일반 섹션 카드에서 제목 끝에 발행 시각이 붙어 있으면 `published_at`으로 분리한다.
- `app/news/service.py`가 공통 수집과 방별 매핑을 담당하며 최종적으로 `NewsItem` 목록을 만든다.
- 키워드 방이 하나라도 있으면 일반 섹션 전체를 공통 수집한 뒤 OR 조건으로 필터링한다.
- 같은 섹션을 보는 여러 방은 가장 큰 `max_items` 기준으로 한 번만 수집한다.
- 메시지 포맷은 `summary`, `daily_top10`, `keyword_bundle`를 지원한다.
- 묶음 메시지 제목은 `bundle_title_template`으로 방마다 다르게 지정할 수 있다.
- `uiautomator2` 기반으로 안드로이드 기기의 카카오톡을 제어한다.
- 검색어 입력, 오픈채팅 탭 이동, 채팅방 입장, 참여 처리, 메시지 입력/전송까지 연결되어 있다.
- 실패 시 로그와 XML 덤프를 남기고 재시도한다.
- UI 동작 사이에 1~3초, 실제 채팅 입력 직후에는 5~7초 랜덤 지연을 둔다.
- 크롤링 요청은 기본 타임아웃 30초, 최대 3회 재시도, 재시도 사이 1~3초 랜덤 지연을 사용한다.
- 실행 로그는 콘솔과 `logs/kakaotalk_bot.log`에 함께 기록된다.
- 방 처리 직후 전송 이력을 저장한다.
- `"테스트채팅방123"` 기준의 실제 카카오톡 전송 테스트 이력이 있다.

## 전체 실행 흐름

1. 루트 `main.py`가 `--rooms` 인자를 해석한다.
2. `app/main.py`가 설정 파일을 읽고 활성 방만 남긴다.
3. 실행 대상 방들을 분석해 필요한 공통 수집 범위를 계산한다.
4. `.env`에 지정된 대상 사이트에서 필요한 섹션 기사와 본문을 수집한다.
5. 방별 섹션 결과 또는 키워드 필터 결과를 매핑한다.
6. 전송 이력 기준으로 신규 기사만 남긴다.
7. 방 설정의 포맷 함수로 메시지를 만든다.
8. 카카오톡 오픈채팅방을 검색해서 입장한다.
9. 메시지를 전송한다.
10. 방 단위로 전송 이력을 즉시 저장한다.

## 파일 구조와 역할

### `main.py`

- CLI 진입점
- `--rooms` 인자 해석
- 상대 경로를 프로젝트 루트 기준 절대 경로로 변환
- `app.main.main()` 호출

### `app/main.py`

- 전체 오케스트레이션 담당
- 활성 방 설정 로드
- 공통 뉴스 수집 시작
- 방별 뉴스 매핑 결과 생성
- 전송 이력 로드
- 방별 실행 루프
- 포맷 생성 후 카카오톡 전송
- 방 처리 직후 전송 이력 저장

핵심 함수:

- `run_room()`
  - 사전 수집 뉴스 확인
  - 신규 기사 필터링
  - 메시지 생성
  - 묶음/개별 메시지 전송

### `app/config.py`

- 설정 파일 로드
- `_comment...` 키 제거
- `RoomConfig` 변환

### `app/models.py`

- `NewsItem`
- `RoomConfig`

### `app/history_store.py`

- 전송 이력 로드
- 신규 기사 필터링
- 전송 완료 기사 기록
- 이력 저장 파일명 계산

### `app/messaging/formatters.py`

- `summary`
- `daily_top10`
- `keyword_bundle`
- `bundle_title_template` 기반 묶음 제목 생성
- 묶음 메시지 사용 여부 판단

### `app/news/service.py`

뉴스 수집 결과를 실행 단위에서 재사용 가능한 형태로 정리하는 서비스 레이어다.

주요 역할:

- `build_news_map_for_rooms()`
  - 방 설정 전체를 분석해 공통 수집 범위 계산
- `collect_section_limits()`
  - 섹션별 최대 수집 개수 계산
- `fetch_all_sections_for_keywords()`
  - 키워드 방이 있을 때 일반 섹션 전체 공통 수집
- `fetch_section_news()`
  - 섹션별 기사 수집
- `select_news_for_room()`
  - 방별 섹션 결과 또는 키워드 결과 매핑
- `filter_items_by_keywords()`
  - 제목/요약/본문 기준 OR 필터
- `to_news_item()`
  - `CrawledNewsItem -> NewsItem` 변환

주의:

- `include_keywords`가 있으면 `source_section`은 무시된다.
- 키워드 필터는 AND가 아니라 OR 조건이다.
- `max_items`는 최종 전송 개수 기준이다.

### `app/news/crawler.py`

실제 HTML 요청과 카드 파싱을 담당하는 크롤러다.

주요 역할:

- `.env`의 URL 설정 읽기
- 섹션 URL 관리
- HTML 요청
- 섹션 페이지 카드 파싱
- 제목, 요약, 링크, 발행 시각 추출
- 일반 섹션 기사 본문 추가 수집
- `CrawledNewsItem` 반환

현재 구현 기준:

- `requests + BeautifulSoup` 사용
- `데일리 TOP10`은 본문을 추가 수집하지 않음
- 일반 섹션은 기사 상세 페이지까지 요청
- 섹션 전체 수집 중 일부 섹션 실패 시, 해당 섹션만 빈 결과로 처리하고 나머지는 계속 진행

### `app/env.py`

- 루트 `.env`를 읽어서 `os.environ`에 로드
- `get_env()`로 필수 환경변수 조회
- 크롤러 URL 설정 누락 시 즉시 예외 발생

### `app/automation/utils.py`

자동화 공통 저수준 유틸이다.

- `connect_device()`
- `download_xml()`
- `dump_xml_on_failure()`
- `wait_for()`
- `click()`
- `set_text()`
- `exists()`
- `scroll_until_text()`
- `retry()`
- `log_progress()`
- `human_pause()`

### `app/automation/controller.py`

카카오톡 앱 안에서 실제 동작 단위를 담당한다.

주요 역할:

- 카카오톡 실행
- 검색 버튼 클릭
- 검색창 입력
- 오픈채팅 탭 이동
- 채팅방 입장
- 오픈채팅 참여 처리
- 메시지 입력/전송
- 채팅 가능 상태 확인

핵심 함수:

- `open_chatroom_by_keyword()`
- `search_chatroom()`
- `ensure_chatroom_ready()`
- `send_message_to_chatroom()`

특징:

- `search_keyword` 포함 매칭으로 채팅방을 찾는다.
- `send_message_to_chatroom()`은 재시도 로직을 감싼 상위 전송 함수다.

### `app/legacy/kakaotalk_crawler.py`

- 현재 핵심 실행 흐름에서는 직접 사용하지 않는다.
- 별도 요청이 있기 전까지 우선 분석 대상이 아니다.

### `test/send_test_message.py`

- 실제 카카오톡 전송 단건 테스트용 스크립트
- 내부적으로 `send_message_to_chatroom()` 호출

## 환경변수

루트 `.env`에는 크롤링 대상 사이트 URL을 저장한다.

- `CRAWLER_BASE_URL`
- `CRAWLER_SECTION_DAILY_TOP10_URL`
- `CRAWLER_SECTION_POLITICS_URL`
- `CRAWLER_SECTION_ECONOMY_URL`
- `CRAWLER_SECTION_SOCIETY_URL`
- `CRAWLER_SECTION_WORLD_URL`
- `CRAWLER_SECTION_CULTURE_URL`
- `CRAWLER_SECTION_IT_SCIENCE_URL`

이 값들은 저장소에 직접 올리지 않는 전제다.

## 운영 파일과 산출물

- `rooms.json`, `rooms-test.json`
  - 방 설정 파일
- `sent_history.json`, `sent_history-test.json`
  - 전송 이력 파일
- `logs/`
  - 실행 로그
- `xml/`
  - 자동화 실패 시점 XML 덤프

현재 `.gitignore`에는 아래 운영 파일이 포함된다.

- `.env`
- `logs/`
- `xml/`
- `sent_history*.json`
- `.DS_Store`

## 현재 설계 원칙

### 1. 역할 분리

- 크롤링 구현은 `app/news/crawler.py`
- 수집 결과 매핑은 `app/news/service.py`
- 카카오톡 제어는 `app/automation/controller.py`
- 공통 UI 유틸은 `app/automation/utils.py`
- 전체 실행 오케스트레이션은 `app/main.py`

### 2. 설정 기반 동작

코드 수정 없이 `rooms.json`과 `.env`로 대부분의 동작을 제어한다.

- 어떤 섹션을 볼지
- 어떤 키워드를 걸지
- 어떤 포맷으로 보낼지
- 어느 방을 실행할지
- 어떤 대상 사이트 URL을 사용할지

### 3. 공통 수집 후 방별 매핑

동일한 실행에서 중복 수집을 줄이기 위해 필요한 섹션만 먼저 공통 수집하고, 결과를 방별로 나눠 쓴다.

### 4. 실패 추적 가능성 확보

카카오톡 UI 자동화는 깨지기 쉬우므로 아래를 유지한다.

- 로그 기록
- XML 덤프 저장
- 재시도
- selector fallback

### 5. 중복 전송 방지

- URL 기준 중복 제거
- 방별 전송 이력 저장
- 방 처리 직후 이력 저장

## 주의사항

- `include_keywords` 모드에서도 최종 전송 대상은 `max_items`개까지만 사용한다.
- 키워드 방이 하나라도 있으면 일반 섹션 전체를 수집하므로 실행 시간이 늘 수 있다.
- 일반 섹션은 기사 상세 본문까지 추가 요청하므로 실행 시간이 더 길 수 있다.
- 카카오톡 UI selector는 앱 업데이트에 따라 바뀔 수 있으므로 실패 시 `xml/` 폴더를 먼저 확인한다.
- `.env`가 없거나 필수 URL이 빠져 있으면 크롤러가 즉시 실패한다.
- `app/legacy/kakaotalk_crawler.py`는 현재 우선 작업 대상이 아니다.

## 다음 턴용 요약

`이 프로젝트는 외부 뉴스 사이트를 크롤링해서 카카오톡 오픈채팅방에 전송하는 봇이야. rooms.json으로 섹션/키워드/포맷을 제어하고, 크롤링 대상 URL은 루트 .env에서 읽어. app/main.py가 app/news/service.py와 app/automation/controller.py를 연결해. 자세한 현재 구조는 PROJECT_CONTEXT.md와 ROOMS_GUIDE.md 기준으로 진행해줘.`
