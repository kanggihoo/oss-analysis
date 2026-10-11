# dexter — 데이터 인벤토리와 수집 방식

- 분석 SHA: `534f6be455523c5926eba72bdaf4f914555be5c9` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1, Q2
- 검증 수준 요약: 코드 확인 약 45 / 추론 2 / 미확인 1 (근사치)

<a id="q1"></a>
## Q1. 데이터 인벤토리: 무엇을 보는가

dexter의 데이터는 **모두 LLM이 도구를 호출해서 가져온다**. 사전에 쌓아 둔 데이터 저장소는 없다. 공급자는 사실상 **Financial Datasets API 1개**(`https://api.financialdatasets.ai`, `src/tools/finance/api.ts:4`, 키: `FINANCIAL_DATASETS_API_KEY`, `api.ts:43-45`)와 웹 검색 계열이다. 아래 "소비 주체"는 해당 도구를 부르는 쪽(메인 에이전트/서브에이전트/스킬)이다. 서브에이전트의 허용 도구 목록은 `src/tools/subagent/types.ts:34-45,62-73`.

| 분류 | 데이터 / 필드 | 제공자 | 키 필요 | 소비 주체 | 근거 위치 | 검증 |
|---|---|---|---|---|---|---|
| 가격·거래량 | 주식 현재가 스냅샷(가격·일 변동) | Financial Datasets `/prices/snapshot/` | 예 | `get_market_data` 라우터 → 메인/서브에이전트 | `src/tools/finance/stock-price.ts:21-26` | 코드 확인 |
| 가격·거래량 | 주식 OHLCV 이력(interval day/week/month/year) | `/prices/` | 예 | 같음 | `stock-price.ts:29-69` | 코드 확인 |
| 가격·거래량 | 코인 스냅샷/이력(interval에 minute 포함, `BTC-USD` 형식) | `/crypto/prices/snapshot/`, `/crypto/prices/` | 예 | 같음 | `crypto.ts:15-23,31-60` | 코드 확인 |
| 가격·거래량 | 티커 목록(주식/코인) | `/prices/snapshot/tickers/`, `/crypto/prices/tickers/` | 예 | 같음 | `stock-price.ts:71-79`, `crypto.ts:65-70` | 코드 확인 |
| 기술지표 | **없음**. RSI·이동평균·MACD 계산 코드/도구 없음. LLM이 OHLCV를 읽고 알아서 해석 | - | - | - | `src/tools/finance/` 전체 파일 목록에 지표 계산 모듈 없음(`ls` 확인), `grep -i "rsi\|macd\|moving"` 0건 | 코드 확인(없음) |
| 펀더멘털 | 손익계산서·재무상태표·현금흐름표(annual/quarterly/ttm, limit 기본 4) | `/financials/income-statements/` 등 | 예 | `get_financials` 라우터 | `fundamentals.ts:9-58,60-110` | 코드 확인 |
| 펀더멘털 | 키 비율 스냅샷(P/E,P/B,P/S,EV/EBITDA,PEG,마진,ROE/ROA/ROIC,유동성,부채비율,주당지표,성장률) | `/financial-metrics/snapshot/` | 예 | 같음 | `key-ratios.ts:15-26`(필드 목록은 description `key-ratios.ts:18`) | 코드 확인 |
| 펀더멘털 | 키 비율 이력(period annual/quarterly/ttm, limit 기본 4) | `/financial-metrics/` | 예 | 같음 | `key-ratios.ts:70-91` | 코드 확인 |
| 펀더멘털 | 사업 부문(세그먼트) 매출·마진 | `/financials/segments/` | 예 | 같음 | `segments.ts:24-33` | 코드 확인 |
| 펀더멘털 | 실적 발표(EPS/매출 서프라이즈, 전체 시장 피드 가능) | `/earnings` | 예 | 같음 | `earnings.ts:7-41` | 코드 확인 |
| 펀더멘털 | SEC 공시 본문(10-K/10-Q/8-K Item 단위) | `/filings/`, `/filings/items/` | 예(Item 타입 목록 `/filings/items/types/`는 키 없이 호출) | `read_filings` | `filings.ts:25-37,57-70,87-160` | 코드 확인 |
| 펀더멘털 | 종목 스크리닝(필드/연산자 gt,gte,lt,lte,eq,in) | `/financials/search/screener/` | 예 | `stock_screener` | `screen-stocks.ts:43-51,102-177` | 코드 확인 |
| 수급·자금흐름 | 내부자 거래(Form 4), 내부자 보유(Form 3/5), 13F 기관 보유, 13D/13G 5% 보유·행동주의 | `/insider-trades/`, `/insider-ownership/`, `/institutional-holdings/`, `/beneficial-ownership/` | 예 | `get_market_data` 라우터 | `insider_trades.ts:112-170`, `insider_ownership.ts:48-65`, `institutional_holdings.ts:52-100`, `beneficial_ownership.ts:60-110` | 코드 확인 |
| 수급·자금흐름 | 외국인/기관 순매수, 공매도, 신용잔고 등 한국형 수급 | - | - | - | **없음** (미국 SEC 기반) | 코드 확인(없음) |
| 뉴스 | 종목/시장 헤드라인(title, source, 날짜, URL), limit 기본 5 최대 10 | `/news` | 예 | `get_market_data` | `news.ts:7-31` | 코드 확인 |
| 뉴스 | 웹 검색 결과(제목·URL·스니펫) | Exa / Perplexity / Tavily / LangSearch | 각 키 | 메인/서브(research) | `registry.ts:164-196` (상세 04-research.md) | 코드 확인 |
| 뉴스 | 웹페이지 본문 요약 | 임의 URL → HTML→마크다운→빠른 모델 요약 | 아니오 | `web_fetch` | `fetch/web-fetch.ts:42-125`, `fetch/utils.ts:331-345` | 코드 확인 |
| 뉴스 | JS 렌더 페이지 | Playwright 브라우저 | 아니오 | `browser` | `tools/browser/browser.ts:27-60` | 코드 확인 |
| 감성·소셜 | X(트위터) 최근 7일 트윗·프로필·스레드(좋아요/RT/조회 메트릭) | X API v2 | 예(`X_BEARER_TOKEN`) | `x_search`, 스킬 `x-research` | `search/x-search.ts:5,260-324`, `registry.ts:198-206` | 코드 확인 |
| 감성·소셜 | 공포탐욕지수 등 정량 감성 지표 | - | - | - | 없음 | 코드 확인(없음) |
| 거시 | 금리·CPI·환율 등 거시 시계열 전용 도구 | - | - | - | **없음**. 광역 뉴스(`get_company_news` ticker 생략)와 웹검색으로만 간접 접근 | 코드 확인(없음) |
| 코인 전용 | 코인 가격만. 펀딩비·OI·온체인·공포탐욕지수 없음 | Financial Datasets | 예 | `get_market_data` | `crypto.ts` 전체 | 코드 확인 |
| 포트폴리오·보유 | 사용자 보유/계좌 연동 **없음**. 사용자가 말한 목표·위험성향을 메모리 파일에 저장해 재사용할 뿐 | `.dexter/memory/*.md` | 아니오 | `memory_search`/`memory_update` | `agent/prompts.ts:88-119`, `memory/flush.ts:13-22` | 코드 확인 |
| 과거 판단·메모리 | 대화 기록(마지막 10턴, 최근 3턴은 전문·나머지는 1~2문장 요약) | 인메모리 | 아니오 | 메인 에이전트 | `utils/in-memory-chat-history.ts:4-5,47-60` | 코드 확인 |
| 과거 판단·메모리 | 장기 메모리(MEMORY.md, 일자별 md, 세션 기록) + SQLite FTS5/벡터 하이브리드 검색 | `.dexter/memory/index.sqlite`, 임베딩(OpenAI/Gemini/Ollama) | 임베딩 키 선택 | 메인 에이전트(서브는 `memory_search/get`만) | `memory/index.ts:18-33`, `memory/search.ts:31-145` | 코드 확인 |
| 과거 판단·메모리 | **판단 결과의 수익률 사후 채점** | - | - | - | 없음 (`evals/`는 질의응답 정확도 채점이며 매매 성과와 무관, 03-decision.md 4-7) | 코드 확인(없음) |

### 정의만 있고 쓰이지 않는 것 / 문서와 코드가 어긋나는 것

| 항목 | 상태 | 근거 | 검증 |
|---|---|---|---|
| `get_institutional_investors` 도구 | 정의·export만 있고 어떤 라우터/레지스트리에도 바인딩되지 않음(사용처 grep: `finance/index.ts:9` export가 전부) | 정의 `institutional_holdings.ts:112-`, 마켓 도구 목록 `get-market-data.ts:68-86` | 코드 확인 |
| `get_filings`(공시 메타) | LLM에 직접 노출되지 않고 `read_filings` 내부에서만 호출 | `read-filings.ts:200-204` | 코드 확인 |
| "company facts"(섹터·산업·시총 등) | `get_financials` 설명과 DCF/write-memo 스킬이 사용하라고 하나 **해당 도구가 `FINANCE_TOOLS`에 없음** (엔드포인트 호출 코드 0건) | 설명 `get-financials.ts:20`, 도구 목록 `get-financials.ts:60-73`, 스킬 `skills/dcf/SKILL.md:53-60`, `skills/write-memo/SKILL.md:49` | 코드 확인(없음) / 영향은 추론 |
| "KPI guidance / KPI metrics" | write-memo 스킬이 요청하나 대응 도구 없음 | `skills/write-memo/SKILL.md:50` | 코드 확인(없음) |
| 라우터 프롬프트의 `get_financial_metrics_snapshot` | 존재하지 않는 도구명. 실제는 `get_key_ratios`(스냅샷) | `get-financials.ts:98` vs `key-ratios.ts:16` | 코드 확인 |
| 웹 검색 결과 수 | 설명은 "up to 5"이나 LangSearch는 `count: 10` | `search/index.ts:25` vs `search/langsearch.ts:40-44` | 코드 확인 |
| README의 검색 제공자 | "Exa preferred, Tavily fallback"(`AGENTS.md:17,59`) vs 코드는 4종 체인 | `registry.ts:164-196` | 코드 확인 |
| README 스크래치패드 예시의 `llmSummary` | 코드의 `ScratchpadEntry`에 해당 필드 없음 | `README.md:157` vs `agent/scratchpad.ts:15-24` | 코드 확인 |

### 시장별 차이
- 시장 분기 자체가 없다. 모든 금융 도구가 미국 SEC/거래소 기준이며, 코인은 Financial Datasets가 제공하는 `*-USD` 쌍뿐이다 (`crypto.ts:16`). 한국 종목(KRX/KOSDAQ) 지원 코드는 없다(`grep -i "krx\|kospi\|upbit"` 0건). 검증: 코드 확인(없음).

<a id="q2"></a>
## Q2. 수집 방식: 어떻게 가져오는가

### 2.1 수집 계층 구조 (벤더 추상화·폴백)

```text
메인 LLM ──tool call──▶ get_financials / get_market_data (메타툴)
                          └─ 라우터 LLM(메인과 같은 모델)이 하위 도구 선택·인자 생성
                              └─ 하위 도구들 ──▶ api.get() ──▶ Financial Datasets (+ 파일 캐시)
메인 LLM ──tool call──▶ read_filings (LLM 2회: 계획 → Item 선택) ──▶ /filings, /filings/items
메인 LLM ──tool call──▶ stock_screener (LLM 1회: 자연어→필터) ──▶ /financials/search/screener
메인 LLM ──tool call──▶ web_search ──▶ [Exa → Perplexity → Tavily → LangSearch] 폴백체인
```

| 구분 | 위치 | 식별자 | 설명 | 검증 |
|---|---|---|---|---|
| 도구 등록 | `src/tools/registry.ts:48-162` | `getToolRegistry()` | 16개 고정 도구 + 조건부(web_search, x_search, skill, bash) | 코드 확인 |
| 금융 라우터 1 | `src/tools/finance/get-financials.ts:79-118,138-217` | `createGetFinancials()` | `callLlm(query, {tools: FINANCE_TOOLS})`로 도구 선택 후 `Promise.all` 병렬 실행 | 코드 확인 |
| 금융 라우터 2 | `src/tools/finance/get-market-data.ts:89-133,160-240` | `createGetMarketData()` | 같은 구조, 12개 하위 도구 | 코드 확인 |
| 공시 | `src/tools/finance/read-filings.ts:170-320` | `createReadFilings()` | ①구조화 출력으로 `{ticker, filing_types, limit}` 계획 ②Item 도구 호출 선택(최대 3건) | 코드 확인 |
| 스크리너 | `src/tools/finance/screen-stocks.ts:110-177` | `createScreenStocks()` | 필터 필드 목록을 프롬프트에 주입 → 구조화 출력 → POST | 코드 확인 |
| 웹 검색 폴백 | `src/tools/search/web-search.ts:18-37` | `searchWithProviders()` | 제공자를 순서대로 시도, **예외가 날 때만** 다음으로 넘어감(빈 결과는 실패가 아님) | 코드 확인 |
| 우선순위 설정 | `src/tools/registry.ts:164-187` | 키가 있는 제공자만 `[exa, perplexity, tavily, langsearch]` 순, `/search`로 정한 `webSearchPreferredProvider`가 맨 앞 | 코드 확인 |
| 금융 데이터 폴백 | 없음. 단일 공급자, 실패하면 해당 하위 도구가 에러 → 메타툴이 `_errors`에 담아 부분 결과 반환 | `get-financials.ts:176-185,207-214` | 코드 확인 |

### 2.2 가져오는 방식: pre-fetch vs tool call

| 데이터 | 방식 | 근거 | 검증 |
|---|---|---|---|
| 모든 금융·뉴스·공시·검색 데이터 | **LLM tool call (on-demand)** | 시스템 프롬프트에 데이터를 미리 넣는 코드 없음. `Agent.create`가 넣는 것은 SOUL/규칙/메모리/스킬 목록뿐 (`agent.ts:93-121`) | 코드 확인 |
| 메모리 세션 컨텍스트(MEMORY.md + 오늘·어제 일지, 상한 2000토큰) | **pre-fetch(프롬프트 주입)** | `agent.ts:103-110`, `memory/store.ts:118-146`, `memory/index.ts:22` | 코드 확인 |
| 현재 날짜 | 프롬프트 문자열로 주입(영문 포맷) | `prompts.ts:19-27,236` | 코드 확인 |

### 2.3 원시 데이터 가공

- **지표 계산은 코드가 아니라 LLM**: 지표 계산 모듈이 없고, 결과 JSON을 마크다운 표로 줄이는 포매터만 있다. 숫자 약식(`1.2T/B/M/K`), 퍼센트 환산(`n*100`, 1자리), 결측은 `—`로 표시 (`src/tools/finance/formatters.ts:13-38`). 포매터 레지스트리: `formatters.ts:416-438`. 검증: 코드 확인.
- **불필요 필드 제거**: `accession_number`, `currency`, `period` 등을 재귀 삭제해 토큰 절약 (`api.ts:15-41`, `key-ratios.ts:7`, `fundamentals.ts:7`). 검증: 코드 확인.
- **동일 일자 조회 보정**: `start_date >= end_date`면 시작일을 7일 앞당김 (`stock-price.ts:47-55`). 검증: 코드 확인.
- **단위·부호**: 스크리너는 마진/성장률이 "퍼센트가 아니라 소수"라는 규칙을 프롬프트로 LLM에 주입 (`screen-stocks.ts:91`). 코드에서 단위를 강제 변환하지는 않는다. 검증: 코드 확인.
- **페이지네이션**: `next_page_url`을 끝까지 따라가 병합한 뒤 캐시에 쓴다 (`api.ts:147-156`, 병합 `api.ts:54-70`). 검증: 코드 확인.
- **웹 결과 가공**: 검색 결과는 원본 JSON에서 URL만 추출해 `sourceUrls`로 붙인다 (`tools/types.ts:19-53`). 요약/중복 제거는 없다.

### 2.4 캐시

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 위치 | `.dexter/cache/` (프로세스 cwd 기준 상대경로) | `utils/cache.ts:32`, `utils/paths.ts:3-11` | 코드 확인 |
| 키 | 엔드포인트 + 정렬된 파라미터의 md5 앞 12자, 티커가 있으면 파일명 접두 | `cache.ts:66-91` | 코드 확인 |
| 만료 | `ttlMs`를 넘기면 `cachedAt` 기준 만료, **`ttlMs` 없이 cacheable이면 영구 유효** | `cache.ts:152-158` | 코드 확인 |
| TTL 상수 | 뉴스 15분, 스냅샷 지표·내부자·13F·13D 1시간, 키 비율 이력 6시간, 재무제표·실적·공시 Item·세그먼트 24시간, 티커 목록 24시간 | `finance/utils.ts:11-14`, `news.ts:28`, `key-ratios.ts:23,85`, `fundamentals.ts:66-108`, `filings.ts:99,131,156` | 코드 확인 |
| 캐시 안 하는 것 | **주가 스냅샷**(`stock-price.ts:24`, `crypto.ts:20`), 공시 메타(`filings.ts:67`), 스크리너 POST(`screen-stocks.ts:161`). 이력 가격은 `end_date`가 오늘 이전일 때만 캐시하며 이때 TTL이 없어 영구 | `stock-price.ts:62-66`, `crypto.ts:59` | 코드 확인 |
| 손상 처리 | 구조 검증 실패·파싱 실패 시 파일 삭제 후 미스 처리, 쓰기 실패는 로그만 | `cache.ts:97-119,161-166,198-201` | 코드 확인 |
| 기타 캐시 | 웹 페이지 15분/50MB LRU, 스크리너 필터 메타는 프로세스 메모리 | `fetch/utils.ts:35-46`, `screen-stocks.ts:41-51` | 코드 확인 |

### 2.5 미래 데이터 차단 (look-ahead)

- **장치 없음.** 기준일(as-of) 개념이 코드에 없다. `src/**/*.ts` grep에서 `asOf`/`look-ahead` 0건(`as_of_date`는 13F 응답 필드일 뿐, `formatters.ts:246`). 날짜 범위는 라우터 LLM이 "현재 날짜" 프롬프트를 보고 만든 인자(`get-market-data.ts:102-106`)이며, 코드는 범위를 검증하지 않는다. 따라서 dexter 구조를 백테스트에 그대로 쓰면 누수가 생길 수 있다. 검증: 코드 확인(없음), 백테스트 영향은 추론(근거: 위 as-of 부재 + 최신 데이터 API만 호출).

### 2.6 호출 제한·실패 처리

| 계층 | 동작 | 근거 | 검증 |
|---|---|---|---|
| Financial Datasets HTTP | **재시도 없음.** 네트워크 오류·비-2xx·JSON 오류는 즉시 throw. 키가 없으면 경고 로그만 남기고 빈 키로 호출 | `api.ts:75-114,80-84` | 코드 확인 |
| 하위 도구 타임아웃 | 메타툴 하위 호출마다 60초(`withTimeout`) | `finance/utils.ts:8,20-31`, `get-financials.ts:166` | 코드 확인 |
| 메타툴 라우터 실패 | LLM이 도구를 하나도 고르지 않으면 `{error:'No tools selected for query'}` 반환(예외 아님) | `get-financials.ts:152-154` | 코드 확인 |
| 하위 일부 실패 | 성공분은 반환, 실패분은 `_errors`로 첨부 → LLM이 계속 진행 | `get-financials.ts:189-216` | 코드 확인 |
| LLM API | 3회 시도, 500ms·2^n 백오프, 비재시도 오류는 즉시 중단 | `model/llm.ts:30-50` | 코드 확인 |
| X API | 429면 리셋까지 대기·재시도(최대 3회, 대기 상한 60초) | `search/x-search.ts:6-8,49-81` | 코드 확인 |
| 도구 실행 실패 | 예외는 `tool_error`로 변환, `Error: ...` 텍스트가 ToolMessage로 LLM에 전달되어 **판단은 계속된다**(fail-soft) | `agent/tool-executor.ts:216-222`, `agent.ts:402-407` | 코드 확인 |
| 웹 검색 폴백 소진 | `All providers failed: ...` throw → 위와 같이 LLM에 에러 텍스트 전달 | `web-search.ts:36` | 코드 확인 |
