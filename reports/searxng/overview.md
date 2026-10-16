---
sha: "0ce72dd2ccd6bd06d21e6afd1844455c98719605"
created: 2026-10-16
updated: 2026-10-16
---

# searxng Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/searxng/searxng.git`
- **분석 Commit SHA**: `0ce72dd2ccd6bd06d21e6afd1844455c98719605` (2026-10-16)
- **작업트리 상태**: `Clean`
- **분석 목적**: `학습` — 메타검색 엔진이 무엇을 하는지 주요 기능 수준으로 파악한다. 사용자 판단(2026-10-16)으로 더 깊은 분석은 하지 않기로 했다: 사용 중인 주식 데이터 수집은 저장 방식이 달라 얻을 것이 크지 않다고 봄.
- **메타데이터**: [`artifacts/searxng/repo-metadata.txt`](../../artifacts/searxng/repo-metadata.txt)

---

## 2. 프로젝트 개요

SearXNG는 **메타검색 엔진**이다. 자체 색인(크롤링한 웹 DB)을 갖지 않고, 질의가 오면 Google·Bing·Wikipedia 등 외부 검색 서비스(engine)에 대신 요청해 결과를 받아 합쳐 돌려준다 (`searx/search/__init__.py:Search`, `searx/search/processors/online.py:OnlineProcessor.search`: 코드 확인). 사용자 대신 요청을 보내므로 사용자 IP·쿠키가 외부 engine에 직접 노출되지 않는 것이 핵심 가치다. Python(Flask) 서버, 라이선스 AGPL-3.0 (`LICENSE`). engine 모듈 252개가 `searx/engines/*.py`에 있다 (코드 확인, 개수는 `ls` 기준, 실제 활성 engine 수는 `미확인`).

### 소스 구성 (`searx/`)

| 폴더·파일 | 역할 | 검증 수준 |
|---|---|---|
| `webapp.py` | Flask 진입점, `/search` 라우트, 출력 포맷(html/json/csv/rss) 분기 | 코드 확인 |
| `search/` | 질의 실행: engine별 요청 생성, 스레드 병렬 호출, timeout 처리 | 코드 확인 |
| `search/processors/` | engine 종류별 실행기 (`online`, `offline`, `online_currency` 등), 실패 시 engine 일시 중지 관리 | 코드 확인 |
| `engines/` | engine 하나당 파일 하나, `request()`와 `response()` 함수로 외부 서비스 형식을 흡수 | 코드 확인 |
| `results.py` | `ResultContainer`: 중복 병합, 점수 계산, 정렬·그룹화 | 코드 확인 |
| `botdetection/`, `limiter.py` | 봇 요청 판별과 IP 제한 | 존재만 확인, 동작 `미확인` |
| `plugins/`, `answerers/` | 결과 후처리(tracker URL 제거 등), 계산기 같은 즉답 | 존재만 확인, 동작 `미확인` |
| `settings.yml` | engine 목록, timeout, 허용 출력 포맷 등 설정 | 코드 확인 |

### 주요 기능

| 기능 | 설명 | 코드 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|
| engine 병렬 호출 | engine마다 스레드를 띄워 동시에 요청하고, 남은 시간 안에 못 끝낸 engine은 timeout으로 기록 | `search/__init__.py` `Search.search_multiple_requests` | 코드 확인 |
| engine 중지(suspend) | 캡차·접근 거부·429·timeout 같은 오류가 나면 해당 engine을 일정 시간 건너뜀 | `search/processors/online.py` `OnlineProcessor.search`, `abstract.py` `SuspendedStatus` | 코드 확인 (중지 시간 규칙 `미확인`) |
| 결과 병합·중복 제거 | 결과를 hash로 같은 항목끼리 합치고 각 engine에서의 순위(`positions`)를 모음 | `results.py` `ResultContainer._merge_main_result` | 코드 확인 |
| 점수 순위화 | engine `weight` × 등장 횟수, 순위가 낮을수록(숫자 클수록) 점수 감소: 여러 engine에 상위로 나온 결과가 위로 감 | `results.py` `calculate_score` | 코드 확인 |
| 카테고리 그룹화 | 점수순 정렬 후 같은 category·template 결과를 최대 8개씩 가까이 묶음 | `results.py` `ResultContainer.get_ordered_results` | 코드 확인 |
| 질의 전처리 | external bang(`!` 단축)과 answerer(즉답)를 먼저 확인하고, 해당 없으면 일반 검색 | `search/__init__.py` `Search.search` | 코드 확인 (각 동작 내용 `미확인`) |
| 봇 요청 제한 | SearXNG 자신이 봇 요청을 그대로 전달하면 원본 engine에서 캡차·차단을 당하므로, 헤더 검사·IP 목록·요청 행동 기반 rate limit으로 봇의 접근을 막음 (동적 목록에는 Valkey DB 필요) | `searx/limiter.py` 모듈 docstring, `botdetection/` | 코드 확인(docstring) / 동작 `미확인` |
| 자동완성 | 검색어 입력 중 제안을 외부 서비스에서 가져옴 | `searx/autocomplete.py` | 존재만 확인 |
| 프라이버시 | README는 "사용자를 추적·프로파일링하지 않는다"고 명시. 코드상 구현(헤더 제거 등)은 확인하지 않음 | `README.rst` | `미확인` |
| JSON API | `format=json`이면 `query`·`results`·`answers`·`corrections`·`infoboxes`·`suggestions`·`unresponsive_engines`를 JSON으로 반환 | `webapp.py` `search`, `webutils.py` `get_json_response` | 코드 확인 |

### 한 번의 검색이 처리되는 방식

- **같은 질의, 다른 URL**: 사용자가 입력한 검색어를 모든 engine에 그대로 보내되, engine의 `request()`가 서비스마다 다른 URL로 바꾼다. 예: Brave는 `search.brave.com/search?q=...&source=web`, Wikipedia는 `<언어>.wikipedia.org/api/rest_v1/page/summary/<제목>` (`engines/brave.py:request`, `engines/wikipedia.py:request`: 코드 확인).
- **순서**: 중지 중인 engine 제외 → engine별 요청 준비(`processors/online.py:get_params`) → engine마다 스레드로 동시 전송 → engine의 `response()`가 응답을 `url`·`title`·`content` 공통 형식으로 변환 → `ResultContainer`에서 병합·점수순 정렬 (`search/__init__.py`: 코드 확인).
- **사전 수집 없음**: 크롤링이나 미리 쌓아 둔 데이터가 없고, 검색할 때마다 외부를 새로 호출한다. 서버 시작 시 engine 초기화(`processors/abstract.py:initialize`)는 있으나 내용은 `미확인`.
- **질의 확장 없음**: 검색어를 여러 표현으로 늘려 보내는 로직은 없다. `search/`, `query.py`, `plugins/`에서 `expan`·`synonym`·`paraphras`·`rewrite`를 검색했고 `rewrite`는 결과 URL을 고치는 plugin(`hostnames`, `oa_doi_rewrite`)에만 있었다 (코드 확인). 즉 SearXNG는 "같은 질문을 여러 engine에" 방식이고, "여러 질문을 한 engine에"(query fan-out)는 구현하지 않았다. 둘은 얻는 것이 다르다: 앞쪽은 서로 다른 색인과 여러 engine 상위 결과에 주는 신뢰 점수, 뒤쪽은 표현 차이로 놓친 문서. AI와 연동한다면 질문 확장은 AI 쪽이 맡고 SearXNG를 여러 번 호출하는 구조가 자연스럽다 (`추론`).

### AI 검색 도구 연동에 대해

- JSON 출력 코드는 있다 (위 표). 다만 **기본 설정(`settings.yml`)은 `search.formats: [html]`뿐이라 JSON을 쓰려면 설정에서 `json`을 켜야 한다.** (`settings.yml` 83~86행, `webapp.py` 654행 근처 포맷 허용 검사: 코드 확인. 거부 시 동작은 `미확인`)
- 이 레포에는 MCP 서버나 AI 연동 코드가 없다 (`.py`·`.rst`·`.yml`·`.md`에서 `mcp` 대소문자 무시 검색 결과 없음: 코드 확인). AI와 연결하려면 JSON 응답을 감싸는 얇은 도구(tool) 계층을 별도로 만들어야 한다 (`추론`).
- 오류 정보가 응답에 들어 있어(`unresponsive_engines`) agent가 검색 실패와 결과 없음을 구분할 수 있다 (`코드 확인`).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

`그리지 않음` — 사용자 판단으로 주요 기능 정리에서 멈췄다. 다시 이어간다면 모듈 구조도와 대표 실행 흐름(`/search?q=...&format=json` 한 번의 요청)을 archify로 그리고 "그림 해설"을 쓴다. 지금까지 읽은 근거는 위 2절 표.

---

## 4. 질문과 조사 기록 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 없음
