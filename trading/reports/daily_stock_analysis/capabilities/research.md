---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - src/core/pipeline.py
  - src/search_service.py
  - src/services/intelligence_service.py
  - src/services/social_sentiment_service.py
  - src/repositories/intelligence_repo.py
  - src/config.py
  - src/storage.py
  - src/data/stock_mapping.py
depends: []
status: ready
---

# 뉴스·리서치

> 종목의 고정 검색, 미국 소셜 감성, 저장된 인텔을 모아 기본 LLM의 뉴스 입력을 만든다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 기본 분석 경로에서 코드·이름·시장으로 로컬 인텔을 fail-open 조회한다.
2. 사용 가능한 검색 provider가 있으면 최대 5개 고정 차원을 검색한다.
3. 날짜·관련성·품질로 결과를 걸러 차원별 텍스트를 만든다.
4. 성공한 차원별 결과를 DB에 저장하고 실패는 경고한다.
5. 미국 종목이면 이용 가능한 social 결과를 추가하고 로컬 인텔을 끝에 붙인다.
6. 선택적 텍스트와 검색 결과 수를 기본 판단 단계로 전달한다. Agent는 앞서 분기해 이 경로를 거치지 않는다.

### 1.2 범위·통합 지점
- 제공: 기본 경로의 prefetch, 텍스트 조립, 결과 수, 검색 결과 저장. Agent 도구 검색은 Agent 스펙 경계다.
- 외부 의존: 설정된 검색 provider·시계·DB·선택적 social 및 로컬 인텔 서비스. 네트워크 응답은 provider 계약에 따른다.
- 소유 상태: 서비스 인스턴스의 메모리 cache와 inflight 예약, 성공한 차원의 DB news_intel. 다차원 경로는 그 cache를 사용하지 않는다.

### 1.3 인터페이스와 데이터 의미
| 항목 | 타입 | 의미 |
|---|---|---|
| 종목 | code, stock_name, market: string | 지수 검색은 code를 빈 문자열로 바꾼다. |
| news_context | optional string | 검색 보고서, 미국 social, 저장 인텔을 존재하는 순서대로 빈 줄로 연결한다. |
| news_result_count | optional int | 미실행 None, 실행 시작 0, 반환된 성공 차원의 결과 수 합계. social·저장 인텔은 세지 않는다. |
| SearchResponse | query, provider, error_message, search_time 및 results·success | 차원별 응답; 실패 응답도 차원 맵에 보관한다. 검색 보고서에는 URL을 출력하지 않는다. |

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 기본 경로 검색 가능 | 최대 5차원 검색, 텍스트 포맷, 성공한 비어 있지 않은 응답 DB 저장; 저장 예외는 경고하고 계속한다. | 코드 확인 |
| R-02 | 검색 불가 또는 빈 결과 | 검색 불가는 count=None, 검색 개시 후 결과가 없으면 0; 나머지 입력으로 계속한다. | 코드 확인 |
| R-03 | 검색 차원 | 중국어 6개 중 앞 5개, 외국 ticker 영어 5개; ETF·지수 변형과 정확한 문자열은 C-02. 각 차원은 가용 provider를 round-robin으로 한 번 택하고 실패한 차원에 다른 provider를 재시도하지 않는다. 호출 사이 0.5초 대기한다. | 코드 확인 |
| R-04 | 검색 결과 | 차원별 목표 3건, provider에 6건 요청; 날짜·관련도·품질을 적용해 3건으로 제한한다. 최신·위험·공시는 엄격한 날짜, 분석·실적은 180일 및 날짜 불명을 허용한다. ETF 위험 등 나머지는 날짜 정규화만 한다. | 코드 확인 |
| R-05 | provider 설정 | Anspire, Bocha, Tavily, Brave, SerpAPI, MiniMax, SearXNG 순서로 가용 항목을 구성한다. SearXNG는 자체 URL 또는 공개 인스턴스 옵션이고 나머지는 키가 필요하다. | 코드 확인 |
| R-06 | 로컬 인텔 및 social | 로컬 인텔은 종목 scope 우선 후 시장 scope에서 유효 뉴스 윈도, 최대 6건, URL 중복 제거 후 제목·요약·출처를 만든다. 로드 예외는 None. social은 미국 종목에 한정하고 예외를 삼킨다. | 코드 확인 |
| R-07 | 단건 검색 cache | 단건 검색은 query|건수|일수 키, 600초 TTL, 최대 500건의 성공 cache와 동일 요청 예약을 사용한다. 다차원 검색은 직접 provider 호출로 이를 거치지 않는다. | 코드 확인 |
| R-09 | feed 자동 갱신 | `NEWS_INTEL_AUTO_FETCH_ENABLED` 기본 false. 활성 시 기본 RSS·NewsNow source를 생성 또는 활성화해 enabled source를 순회한다. 프로세스 단위 1시간 cooldown과 동시 호출 병합이 있으며 source 실패는 기록하고 다음 source로 진행한다. 피드는 최대 2 MiB이고 RSS·Atom redirect 최대 5회, NewsNow redirect 불허. URL·DNS가 공인 주소인지 확인한다. | 코드 확인 |
| R-10 | social | 키가 있으면 Adanos Reddit 종목 보고서, X와 Polymarket trending을 순서대로 조회해 종목을 찾는다. trending만 600초 cache; HTTP 200 이외·네트워크 오류는 None. 요청 timeout 8초, 일시적 네트워크 오류는 최대 2회. 세 출처 모두 데이터가 없으면 None. | 코드 확인 |
| R-11 | key 기반 provider 실행 | API key를 round-robin으로 골라 오류 3회 이상인 key를 건너뛰고 모두 소진 시 오류 횟수를 초기화한다. 성공 응답에는 최초 획득시각을 붙이며 실패는 빈 실패 응답과 오류로 변환한다. HTTP 일시 장애 재시도는 요청 helper 및 provider별 구현을 따른다. | 코드 확인 |
| R-08 | 외국 코드 분류 | 영문 ticker 또는 정규화한 5자리 홍콩 코드는 영어 템플릿. 005930.KS는 이 조건에 해당하지 않아 중국어 템플릿이다. | 코드 확인 |

- 미결정: 없음.
- 확인 한계: 원본 실행과 외부 서비스 응답은 확인하지 않았다.

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/pipeline.py:661-755` | 분기·prefetch·저장·병합 | R-01, R-02, R-06 |
| C-02 | `src/search_service.py:4384-4636` `search_comprehensive_intel` | 차원 템플릿, provider 선택과 필터 순서 | R-03, R-04, R-07 |
| C-03 | `src/search_service.py:4638-4693` `format_intel_report` | 보고서 형식과 순서 | R-01 |
| C-04 | `src/search_service.py:2404-2523` `SearchService.__init__` | provider 구성·기본 TTL | R-05, R-07 |
| C-05 | `src/search_service.py:2273-2402, 2815-2818, 2821-3491` | 상수·식별자·관련도·품질 helper | R-04 |
| C-06 | `src/search_service.py:3547-3836` | 날짜 파싱·필터·정규화·제한 | R-04 |
| C-07 | `src/search_service.py:2526-2567, 2673-2696` | 외국·ETF 분기 | R-03, R-08 |
| C-08 | `src/core/pipeline.py:3019-3070` `_load_persisted_intelligence_context` | 로컬 인텔 조회·포맷·예외 | R-06 |
| C-09 | `src/search_service.py:2698-2805, 4021-4318` | 단건 cache·검색·fallback | R-07 |
| C-10 | `src/services/intelligence_service.py:38-105, 122-137, 233-240, 307-358` | 자동 수집 기본 비활성, 1시간 cooldown·동시 호출 병합·실패 완화, 조회 경계 | R-06 |
| C-11 | `src/services/social_sentiment_service.py:28-343` | Adanos 요청·재시도·캐시·데이터 추출·텍스트 포맷 | R-06, R-10 |
| C-12 | `src/config.py:186-191, 329-339, 1749-1779, 1946-1979` | 환경 키 및 시간창 기본값·해석 | R-04, R-05, R-06, R-09 |
| C-13 | `src/search_service.py:170-231, 234-418` | 재시도·문서 본문·검색 결과 타입·key 회전과 실패 변환 | R-05, R-11 |
| C-14 | `src/search_service.py:421-570` | Tavily SDK 요청·응답·실패 | R-05, R-11 |
| C-15 | `src/search_service.py:571-1009` | SerpAPI 요청·응답·본문 보강 helper 및 실패 | R-05, R-11 |
| C-16 | `src/search_service.py:1011-1206, 1208-1395` | Bocha·Anspire HTTP 요청·응답·실패 | R-05, R-11 |
| C-17 | `src/search_service.py:1397-1627, 1629-1834` | MiniMax·Brave 요청·응답·실패 | R-05, R-11 |
| C-18 | `src/search_service.py:1835-2242` | SearXNG 인스턴스 발견·회전·요청·실패 | R-05, R-11 |
| C-19 | `src/services/intelligence_service.py:28-105, 147-230, 252-358, 360-827` | feed bootstrap·요청·DNS·파싱·저장 변환·실패 | R-06, R-09 |
| C-20 | `src/repositories/intelligence_repo.py:15-150, 152-209` | 인텔 source 및 item 영속화·날짜 필터·정렬·보존 | R-06, R-09 |
| C-21 | `src/storage.py:2368-2495, 3571-3659` | 검색 결과 URL 기준 upsert와 실패 전파 | R-01 |
| C-22 | `src/core/pipeline.py:161-225`; `src/data/stock_mapping.py:201-266` | scope·외국 코드 변환 | R-06, R-08 |

### 1.6 수락 사례
출처: 모두 구현에서 도출. provider·DB·시계는 대체물이며 외부 응답 품질은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-03 | 중국 일반 종목, provider 둘, 5회 | latest→analysis→risk→announcements→earnings; 1·2·1·2·1 순으로 provider 선택, industry 미호출 |
| T-02 | R-02, R-06 | 검색 미설정, 로컬 인텔 1건 | count None, news_context에 로컬 항목 포함 |
| T-03 | R-03, R-04 | latest 결과의 날짜 불명과 윈도 밖 뉴스 | 두 항목 제외. 다른 provider로 재시도하지 않는다 |
| T-04 | R-04 | market_analysis 날짜 불명인 관련 결과 | 날짜 불명만을 이유로 제외하지 않는다 |
| T-05 | R-06 | 종목·시장 결과에 같은 URL | 먼저 수집한 항목 한 건만 포함 |
| T-06 | R-07 | 동일 query 단건을 TTL 내 반복 | 성공 응답 cache 재사용. 다차원 호출은 별개다 |
| T-07 | R-08 | `005930.KS` | 중국어 고정 검색어 분기 |
| T-08 | R-09 | 활성 source 2개 중 하나 실패 | 실패 source 상태를 기록하고 나머지는 계속 가져온다. |
| T-09 | R-10 | 미국 종목에서 Reddit 실패, X에 종목 일치 | Reddit 누락과 X 일치 항목을 포함하는 social text를 만든다. |
| T-10 | R-11 | 모든 API key 오류 횟수 3 이상 | 횟수 전체 초기화 후 첫 key를 선택한다. |

## 2부. 근거

### 2.1 요구사항별 근거

핵심 진입점: [기본 경로](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/core/pipeline.py#L681-L755), [다차원 검색](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/search_service.py#L4384-L4636).
| R-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01~R-03 | C-01~C-04 | 호출부·검색 구현 직접 읽음 |
| R-04 | C-02, C-05, C-06 | 필터와 점수 코드 확인 |
| R-05 | C-04 | provider 등록 조건 확인 |
| R-06 | C-01, C-08 | source 자동 수집·조회와 오류 처리 확인 |
| R-07 | C-02, C-04, C-09 | 호출 경로 비교 |
| R-08 | C-07, C-22 | 정적 분기 확인 |
| R-09 | C-10, C-19, C-20 | 자동 갱신과 저장 조회 구현 확인 |
| R-10 | C-11 | social 요청·캐시·포맷 확인 |
| R-11 | C-13~C-18 | provider별 요청과 오류 변환 확인 |
| T-01~T-10 | T별 R-ID의 위 근거 | 모두 구현에서 도출. 외부 의존은 대체물 |
