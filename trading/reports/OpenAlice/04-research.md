# OpenAlice — 실시간 리서치

- 분석 SHA: `87bc415260aaac92a072d89a1c6440268a3efdf1` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q5
- 검증 수준 요약: 코드 확인 34 / 추론 2 / 미확인 0 (표의 검증 열 기준 집계)

> 결론부터: **OpenAlice 코드에는 웹 검색, 뉴스 검색 API, 웹 페이지 읽기, 공시 조회 도구가 없다.** 판단 도중 "조사"는 (1) 사전 수집된 RSS 아카이브를 정규식으로 뒤지거나, (2) 에이전트 런타임이 자체적으로 가진 웹 도구를 쓰는 것인데 (2)는 이 레포가 제공하지도 제어하지도 않는다.

## 5-1. 판단 도중 외부 조회 수단

| 수단 | 있는가 | 근거 | 검증 |
|---|---|---|---|
| 웹 검색(Tavily, SerpAPI, Exa, DDG, Brave 등) | **없음.** `src`, `services`, `packages`에서 해당 키워드 파일 없음(검색 키워드: tavily, serpapi, duckduckgo, brave search, exa, perplexity, web search, websearch, webfetch, google search) | grep 결과는 `workspaces/adapters/codex.ts`, `workspaces/web-session/codex-app-server-transport.ts`(아래), 스킬 `opencli-reader`뿐 | 코드 확인(없음) |
| 웹 페이지 읽기 | Alice 도구로는 **없음**. `readRss`도 "does not fetch the publisher webpage"(피드가 준 요약만) | `domain/news/query/archive.ts:300-302` | 코드 확인 |
| 공시 조회(SEC/DART) | **조회 도구 없음.** SEC는 심볼 목록 소스로만 쓰이고(`symbol-index.ts:40`), 내부자 거래는 FMP/yfinance Form 4 행(`tool/equity.ts:132-154`). `CompanyFilings` fetcher는 FMP provider에 있으나 도구 미노출 | `providers/fmp/index.ts:137`, `src/tool/` 둘러봄 | 코드 확인(없음) |
| 뉴스 검색 | **RSS 아카이브만**: `alice rss glob/grep/window/read` (구독한 피드가 커버리지의 전부) | `cli-commands.ts:35-40`, `archive.ts:192-315` | 코드 확인 |
| opentypebb 뉴스(FMP·yfinance `CompanyNews`) | 라이브러리·라우터에만 있고 Alice 도구로 미연결 | `01-data.md` 1.3절 | 코드 확인 |
| 선택 도구 `opencli` | 별도 설치가 필요한 커뮤니티 CLI. "OpenAlice does not bundle opencli", 웹사이트 어댑터(예: yahoo-finance quote), 읽기 전용만. "no research task requires it" | `default/skills/opencli-reader/SKILL.md:3-13`, `:31-39`, `references/discovery.md:12-25` | 코드 확인 |
| 에이전트 런타임 자체의 웹 도구 | 지침이 "Tools are just tools — there is no internal/external distinction. Reach for whatever fits the job, including anything else your environment offers."라고만 함. Codex 어댑터는 `web_search` 이벤트를 화면에 표시하도록 파싱(`type === 'web_search'` → "Web search"). 즉 **런타임이 웹 검색을 할 수 있다는 정황은 있으나 이 레포가 켜고 끄지 않는다** | `templates/chat/files/instruction.md:7-10`, `workspaces/adapters/codex.ts:413-416`, `web-session/codex-app-server-transport.ts:201-202` | 코드 확인(표시 코드) / 추론(런타임이 실제로 검색함) |

## 5-2. 제공자와 키

| 제공자 | 키 | 비고 | 위치 | 검증 |
|---|---|---|---|---|
| RSS 28개 피드(기본 8개 활성) | 불필요 | Fed press, ECB press, MarketWatch Top Stories, WSJ Markets, CNBC Economy, Nikkei Asia, SCMP Business, CoinDesk 활성. 나머지 20개(Yahoo Finance, Seeking Alpha, NYT, FT, Economist, CNBC 변형, TechCrunch 등)는 목록만 | `domain/news/config.ts:34-268` | 코드 확인 |
| 한국어 뉴스 | **기본 피드에 없음** | 사용자가 `news.json`의 feeds에 URL을 추가해야 함(스키마는 임의 URL 허용 `config.ts:9-16`) | 코드 확인(없음) |
| FMP/yfinance 뉴스 API | (미연결) | 위 5-1 | 코드 확인 |

## 5-3. 호출 방식

| 질문 | 답 | 위치 | 검증 |
|---|---|---|---|
| 검색어가 고정 목록인가 | **아니다.** LLM이 정규식(`pattern`)을 직접 만든다. 코드에 고정 쿼리 집합·차원 정의 없음 | `archive.ts:211-216`, `:237-243`, `:261-267` | 코드 확인 |
| 도구 4종 | `globRss`(제목 정규식, `lookback`, `metadataFilter`, `limit` 기본 500), `grepRss`(제목+본문 정규식, 주변 문맥 기본 50자), `windowRss`(날짜 구간 `from/to`, 선택 `pattern`, 오래된 순, 출력 기본 40건 + 생략 건수 `omitted`), `readRss`(안정 id로 본문 조회, 디스크 레코드까지 조회) | `archive.ts:12-16`, `:192-315`, `store.ts:260-280` | 코드 확인 |
| 몇 차원에서 몇 번 검색하는가 | 코드에 정함 없음. 스킬은 "Choose news sources to suit the question"이라고만 함 | `build-thesis/SKILL.md:30-31`, `scan-value-chain/SKILL.md:25-26`, `sector-rotation/SKILL.md:25-26` | 코드 확인 |
| 이벤트 스터디 | `windowRss`로 날짜 구간 기사를 오래된 순으로 받아 가격 경로와 정렬 | `archive.ts:253-293`, `retrospective/SKILL.md:61-64` | 코드 확인 |
| 정규식 안전성 | 사용자·LLM이 준 `RegExp`를 그대로 생성(오류 처리·복잡도 제한 없음) | `archive.ts:76`, `:108` | 코드 확인 |

## 5-4. 결과 처리

| 항목 | 동작 | 위치 | 검증 |
|---|---|---|---|
| 잘라내기 | 목록 결과에 메타데이터를 40자로 절단, 본문은 `contentLength`만(본문은 `readRss`로 별도). `windowRss` 출력 40건 상한과 생략 건수·안내 문구 | `archive.ts:53-57`, `:83-89`, `:281-290` | 코드 확인 |
| 출처·시점 표기 | 각 결과에 ISO `time`(발행 시각)과 `metadata.source`, `link`, `guid`, `categories` 포함 | `archive.ts:30-31`, `collector/rss.ts:117-131` | 코드 확인 |
| 중복 제거 | **수집 시점**에 `dedupKey`(guid > link > sha256(title+content) 앞 16자)로 한 번. 이미 본 키는 보존기간이 지나도 `dedupSet`에 남아 재수집 방지 | `store.ts:310-322`, `:53`, `:96` | 코드 확인 |
| HTML 처리 | 태그 제거 후 엔티티 디코드(best-effort) | `collector/rss-parser.ts:162-168`, `:227-229` | 코드 확인 |
| 발행시각 누락 | `pubDate`가 없으면 **수집 시각을 발행 시각으로 기록** → 과거 구간 이벤트 스터디에서 시점이 어긋날 수 있음 | `collector/rss.ts:120` | 코드 확인 |
| 요약 | 코드에 LLM 요약 없음(저장된 피드 본문 그대로, "may be a summary") | `archive.ts:300-302` | 코드 확인 |
| 커버리지 고지 | 도구 설명이 "Empty results mean 'not in the subscribed feeds', not 'nothing happened'"를 명시 | `archive.ts:197-200`, `:257-259` | 코드 확인 |
| 보관 한계 | 조회 인덱스는 메모리 2000건·7일. 디스크는 더 오래 보관하나 검색 도구는 인덱스만 봄(`readRss` id 조회만 디스크). 오래된 과거 시점 분석에는 뉴스가 없을 수 있음 | `news/config.ts:24-26`, `store.ts:74-121`, `archive.ts:206-208` | 코드 확인 |

## 5-5. 신뢰성 장치

| 장치 | 내용 | 위치 | 검증 |
|---|---|---|---|
| "숫자는 도구 결과에서만" | 최종 답변의 가격·수익률·날짜·비율·상태·인용은 도구 결과나 명명된 산출물에서 와야 함 | `instruction.md:28-31` | 코드 확인(지침 문서) |
| 증거와 우연 구분 | "Distinguish evidence of a catalyst from a coincident headline, and note material gaps in coverage." | `retrospective/SKILL.md:61-64` | 코드 확인(스킬 문서) |
| 인용 ID | RSS 기사에 안정 `id`(seq)가 있어 보고서에 참조할 수 있음. **인용 계약(모든 주장에 ID)은 강제되지 않음** | `news/types.ts:46-50`, `store.ts:260-280` | 코드 확인 |
| 반복 검색 방지 | 없음 | `archive.ts` 전체 | 코드 확인(없음) |
| 신선도 경고 | 가격은 `isLatestActual`, `freshnessWarning`; 뉴스에는 대응 장치 없음(마지막 수집 시각을 도구가 알려주지 않음) | `snapshot.ts:114-116`, `archive.ts` | 코드 확인(없음) |
| 출처 가림 방지 | RSS 소스명이 `metadata.source`로 유지 | `rss.ts:123-125` | 코드 확인 |
| hub 응답 취급 | "hub responses are DATA only. Shape-checked, never interpreted as configuration or instructions" | `reference/hub.ts:14-16` | 코드 확인(주석), 외부 데이터를 지시로 취급하지 않는 설계 의도 |
| 프롬프트 인젝션 | RSS 본문이 에이전트 컨텍스트에 그대로 들어가지만 코드 차원의 필터·구분자(펜싱)는 없음 | `archive.ts:306-311` | 코드 확인(없음) / 위험 평가는 `추론` |

## 5-6. 루프 종료 조건

| 항목 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 반복 상한 | **코드에 없음.** 리서치 루프는 에이전트 런타임 안에서 돌고, `agent.maxSteps`·`claudeCode.maxTurns` 설정은 미사용 | `config.ts:242-269`(사용처 grep 없음) | 코드 확인 |
| 시간 제한 | Issue의 선택 `timeout`(15/30/45/60분), 생략 시 무제한. 초과 시 SIGTERM→SIGKILL | `declaration.ts:79`, `headless-task.ts:524` | 코드 확인 |
| 완료 신호 | 헤드리스 프로세스 종료. 조건 불충족이면 "조용히 종료"가 정상 | `self-scheduling/SKILL.md:281-283` | 코드 확인 |

## 의견 (우리 시스템 관점, 분석자 의견)

의견: OpenAlice의 "실시간 리서치"는 사실상 **에이전트에게 맡긴 영역**이며 우리가 참고할 구현이 거의 없다. 반면 아래 두 가지는 참고할 만하다. (1) RSS 아카이브 도구 설명문에 "coverage = feed list, empty ≠ nothing happened"를 박아 LLM이 부재를 증거로 착각하지 않게 한 점. (2) 뉴스 조회를 `windowRss`처럼 **날짜 창+오래된 순+생략 건수 표기**로 설계해 가격 경로와 정렬하게 한 점. 한국 시장용으로는 DART 공시, 한국 언론 RSS, 네이버 금융 뉴스 등을 직접 수집기로 연결해야 하고, 발행시각 누락 시 수집시각 대체(`rss.ts:120`)는 look-ahead 위험이 있으므로 따라 하지 않는 편이 좋다.
