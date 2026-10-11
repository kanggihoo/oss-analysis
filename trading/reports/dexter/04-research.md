# dexter — 실시간 리서치 (이 레포의 핵심)

- 분석 SHA: `534f6be455523c5926eba72bdaf4f914555be5c9` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q5
- 검증 수준 요약: 코드 확인 약 50 / 추론 4 / 미확인 1 (근사치)

dexter에서 "리서치"는 **판단 도중 LLM이 스스로 도구를 골라 웹·공시·SNS를 찾아보는 것**이며, 이것이 이 레포의 본체다. 별도의 리서치 파이프라인(고정 쿼리 목록, 차원 분해 코드)은 없고, 모든 검색어는 **LLM이 직접 생성**한다. 아래는 사용 가능한 수단, 제공자별 동작, 결과 처리, 신뢰성 장치, 종료 조건 순서다.

## 5-1. 판단 도중 할 수 있는 리서치 수단

| 수단 | 도구 이름 | 하는 일 | 키 필요 | 등록 조건 | 근거 | 검증 |
|---|---|---|---|---|---|---|
| 웹 검색 | `web_search` | 검색어 → 결과(제목·URL·스니펫) | 4종 중 하나 이상 | 키가 하나라도 있을 때만 등록 | `tools/registry.ts:164-196` | 코드 확인 |
| 웹 페이지 읽기 | `web_fetch` | URL을 받아 HTML→마크다운, 빠른 모델이 `prompt`에 맞춰 추출 | 아니오(빠른 모델은 LLM 키 사용) | 항상 | `tools/fetch/web-fetch.ts:42-125` | 코드 확인 |
| 브라우저 | `browser` | Playwright로 이동·스냅샷·클릭·입력, JS 렌더 페이지 | 아니오 | 항상(`postinstall`로 chromium 설치, `package.json:18`) | `tools/browser/browser.ts:27-130` | 코드 확인 |
| 공시 조회 | `read_filings` | 10-K/10-Q/8-K 본문 Item 단위 읽기 | Financial Datasets | 항상 | `tools/finance/read-filings.ts:162-320` | 코드 확인 |
| 뉴스 헤드라인 | `get_market_data` → `get_company_news` | 종목/시장 뉴스 | Financial Datasets | 항상 | `tools/finance/news.ts:18-31` | 코드 확인 |
| 소셜(X) | `x_search` | 검색/프로필/스레드, 최근 7일 | `X_BEARER_TOKEN` | 토큰 있을 때만 | `tools/search/x-search.ts:260-324`, `registry.ts:198-206` | 코드 확인 |
| 하위 리서처 | `spawn_subagent` | 격리된 워커가 자체 루프로 조사 후 요약 반환 | - | 항상 | `tools/subagent/spawn-subagent.ts:83-168` | 코드 확인 |

## 5-2. 제공자 4종의 사용 방식 (web_search)

`web_search`는 **하나의 도구 이름으로 4개 제공자를 폴백 체인**으로 감싼다. 4개 제공자 도구는 모두 `name: 'web_search'`, 입력은 `query` 한 개뿐이다 (`search/exa.ts:25-31`, `tavily.ts:17-23`, `perplexity.ts:51-57`, `langsearch.ts:55-61`). LLM에게 보이는 단일 도구 설명은 `WEB_SEARCH_DESCRIPTION` (`search/index.ts:5-27`).

| 제공자 | 호출 | 결과 수 | 반환 형태 | 키 | 위치 | 검증 |
|---|---|---|---|---|---|---|
| Exa | `@langchain/exa` `ExaSearchResults`, `highlights: true` | `numResults: 5` | 원본 결과 JSON(+URL 추출) | `EXASEARCH_API_KEY` | `search/exa.ts:11-23,34-35` | 코드 확인 |
| Perplexity | `POST https://api.perplexity.ai/chat/completions`, 모델 `sonar`, `max_tokens: 4096` | 모델이 반환한 `search_results` 전부 | **LLM이 합성한 답변(`answer`) + 출처 목록** (원문 스니펫이 아니라 답변문) | `PERPLEXITY_API_KEY` | `search/perplexity.ts:6-8,24-49,58-82` | 코드 확인 |
| Tavily | `@langchain/tavily` `TavilySearch` | `maxResults: 5` | 원본 결과 JSON | `TAVILY_API_KEY` | `search/tavily.ts:12,26` | 코드 확인 |
| LangSearch | `POST https://api.langsearch.com/v1/web-search`, `summary: true` | `count: 10` | 제목+URL+요약(없으면 스니펫) | `LANGSEARCH_API_KEY` | `search/langsearch.ts:6,34-45,70-83` | 코드 확인 |

- **우선순위**: 레지스트리가 키가 있는 제공자를 Exa → Perplexity → Tavily → LangSearch 순으로 모으고, 사용자가 `/search`로 고른 선호 제공자(`webSearchPreferredProvider` 설정)가 있으면 **그것을 맨 앞으로** 옮긴다 (`registry.ts:166-187`). `env.example:21`의 주석 "Exa → Perplexity → Tavily → LangSearch"와 일치.
- **폴백 조건**: 앞선 제공자가 **예외를 던질 때만** 다음으로 넘어간다. 결과가 비었거나 품질이 낮은 경우는 폴백하지 않는다 (`search/web-search.ts:26-37`). 모두 실패하면 `All providers failed: ...` 예외 → 도구 오류 텍스트로 LLM에 전달 (`web-search.ts:36`). 검증: 코드 확인.
- **제공자 간 결과 형태가 다르다**: Perplexity는 합성 답변, 나머지는 원문 스니펫이라 LLM이 받는 데이터의 성격이 폴백에 따라 달라진다. 검증: 코드 확인(영향은 추론).
- **문서 불일치**: ① 설명의 "Returns up to 5 results"(`index.ts:25`) vs LangSearch 10건(`langsearch.ts:43`). ② `WEB_SEARCH_DESCRIPTION`의 "When to Use" 첫 항목이 "Historical stock prices for equities (use get_market_data)"로, 사용하지 말라는 뜻의 문장이 "사용할 때" 목록에 들어가 있다 (`index.ts:10`). ③ `AGENTS.md:17,59`는 "Exa preferred, Tavily fallback"만 기술. 검증: 코드 확인.
- **일반 규칙(프롬프트)**: 도구 정책에는 web_search 사용 지침이 따로 없고 "Only use web_fetch when headlines are insufficient (need quotes, deal specifics, earnings details)" 한 줄만 있다 (`agent/prompts.ts:247`). 구조화 데이터는 금융 도구, 웹 검색은 보완용이라는 구분은 도구 설명이 담당한다 (`search/index.ts:17-26`). 검증: 코드 확인.

## 5-3. 검색어는 누가 만드나 / 몇 번 하나

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 고정 검색어 목록이 있나 | **없음.** 코드에 하드코딩된 쿼리 목록·차원(실적/규제/경쟁 등)이 없다. `web_search`의 `query`는 항상 LLM이 생성한 문자열 | `search/web-search.ts:43-46` | 코드 확인 |
| 몇 차원·몇 회 | 규정 없음. 루프 한도(10회)와 도구별 3회 **경고**가 유일한 간접 제한이다 | `agent.ts:24`, `scratchpad.ts:49-53` | 코드 확인 |
| 같은 도구 반복 호출 | 3회째부터 경고, 유사 질의(Jaccard ≥ 0.7)면 "If the tool isn't returning useful results, consider: (1) trying a different tool, (2) using different search terms..." 경고 (**차단 없음**) | `scratchpad.ts:131-163` | 코드 확인 |
| 스킬이 정한 검색 절차 | **x-research 스킬**: 질문을 **3~5개 쿼리**로 분해(핵심 키워드/`$TICKER`, `from:` 전문가, 약세 키워드 `(overvalued OR bubble OR risk OR concern)`, 강세 키워드 `(bullish OR upside OR catalyst OR beat)`, `has:links`, `-is:reply`), `sort: likes`·`limit: 15`·`min_likes ≥ 5`·`since: 1d/7d`로 시작해 노이즈면 좁히고 결과가 적으면 넓히는 반복 | `skills/x-research/SKILL.md:17-40,67-75` | 코드 확인 |
| 서브에이전트 병렬 조사 | 독립 하위 과제는 한 턴에 `spawn_subagent`를 여러 번 호출해 병렬로. 리서치 전용 유형은 `web_search, x_search, web_fetch, read_filings, get_market_data`만 쓰며 프롬프트는 "cross-check sources, and synthesize a clear, sourced summary" | `prompts.ts:249-251`, `subagent/types.ts:62-67` | 코드 확인 |
| 시장 광역 검색 | `get_company_news`에서 ticker를 생략하면 광역 시장 뉴스(금리·지정학·실적 등) | `news.ts:11,21`, `get-market-data.ts:116,125` | 코드 확인 |

- 쿼리 확장/재작성 코드가 없으므로 검색 품질은 전적으로 LLM의 쿼리 작성에 달려 있다. 검증: 코드 확인(없음).

## 5-4. 결과 처리

| 단계 | 동작 | 근거 | 검증 |
|---|---|---|---|
| 요약 | 검색 결과 자체는 요약하지 않는다(Perplexity는 제공자 쪽 합성). 웹페이지는 `web_fetch`가 빠른 모델로 **질문 맞춤 요약** | `fetch/utils.ts:331-350` | 코드 확인 |
| 잘라내기 | 페이지 마크다운 100,000자 절단, 도구 결과 50,000자 초과 시 디스크 저장+2,000자 미리보기, 턴 합계 200,000자 | `fetch/utils.ts:74,338-340`, `utils/tool-result-storage.ts:13,16`, `utils/tool-result-budget.ts:13` | 코드 확인 |
| 출처 표기 | 도구 결과 JSON에 `sourceUrls`가 붙는다. 검색은 URL 추출(`parseSearchResults`), 금융 도구는 API URL | `tools/types.ts:6-53` | 코드 확인 |
| **시점(날짜) 표기** | 검색 결과에 수집 시각/기사 날짜를 코드가 붙이거나 필터링하지 않는다. 날짜는 제공자 원본 필드에 있을 때만 LLM이 보게 됨(Perplexity는 `date` 필드를 응답 타입에 정의하나 출력 매핑에서 버림: `perplexity.ts:10-14,76-80`) | `search/perplexity.ts:76-80` | 코드 확인 |
| 중복 제거 | 검색 결과 간 중복 제거 없음. X 검색만 트윗 id로 중복 제거 | `x-search.ts:173-179` | 코드 확인 |
| 캐시 | 웹페이지 15분/50MB LRU. 검색 API 결과 캐시는 없음 | `fetch/utils.ts:35-46` | 코드 확인 |
| 크기 안전장치 | URL 2000자, HTTP 10MB, 60초, 리다이렉트 10회, 이종 호스트 리다이렉트는 "REDIRECT DETECTED"를 반환해 LLM이 재요청 | `fetch/utils.ts:62-71`, `web-fetch.ts:66-96` | 코드 확인 |
| `web_fetch` 실패 | 예외를 던지지 않고 `{error:'[web_fetch] ...', url}` 반환 | `web-fetch.ts:119-122` | 코드 확인 |

### X(트위터) 검색 세부 (`x_search`)

- 명령 3개: `search`, `profile`, `thread` (`x-search.ts:211-216`). 최근 7일만(`X_SEARCH_DESCRIPTION` 설명).
- `search`: 쿼리에 `-is:retweet`를 자동 추가, `pages` 최대 5(1페이지≈100트윗, `x-search.ts:145`), 페이지 사이 350ms 지연, 429면 리셋까지 대기·재시도(최대 3회, 대기 ≤ 60초) (`x-search.ts:6-8,49-81,270-286`). `min_likes` 필터와 `likes/impressions/retweets` 정렬은 코드 쪽 후처리 (`x-search.ts:288-297`). 결과 메트릭: likes, retweets, replies, impressions (`x-search.ts:104-109`).
- 정량 감성 점수화는 없다. 감성 판단은 LLM이 트윗을 읽고 하며 스킬이 요구하는 출력은 "Sentiment Themes + Overall Sentiment + Caveats(7일 창, 목소리 큰 소수 편향)" (`skills/x-research/SKILL.md:77-84`). 검증: 코드 확인.

## 5-5. 신뢰성 장치

| 장치 | 내용 | 근거 | 검증 |
|---|---|---|---|
| "숫자는 도구 결과에서만" | **일반 규칙으로는 없음.** write-memo 스킬("Do not invent consensus numbers")과 웹 요약기("using only the provided web page content")에만 있음 | `skills/write-memo/SKILL.md:188`, `fetch/utils.ts:347-348` | 코드 확인 |
| 인용 ID/출처 의무 | 없음. `sourceUrls`는 LLM 컨텍스트에 들어가나 답변에 인용하라는 지시가 프롬프트에 없고 UI에도 표시되지 않음 | `prompts.ts:128-283`, 사용처 4개 파일뿐 | 코드 확인 |
| 반복 검색 방지 | 도구별 3회·유사도 0.7 **경고**(차단 아님) | `scratchpad.ts:131-175` | 코드 확인 |
| 인용 길이 제한 | 웹 요약기가 원문 인용을 **125자 이내**로 제한하고, 인용부호 밖 문장은 원문과 같으면 안 된다고 지시 | `fetch/prompt.ts:55-59` | 코드 확인 |
| 교차 검증 | research 서브에이전트 프롬프트에만 "cross-check sources" 문구. 코드 수준 교차 검증 없음 | `subagent/types.ts:64` | 코드 확인 |
| 소셜 신뢰도 경고 | x-research 스킬 Caveats: "X sentiment is not a reliable predictor; sample bias toward vocal minorities" | `skills/x-research/SKILL.md:84` | 코드 확인 |
| URL 추측 금지 | 브라우저 설명: "NEVER make up or guess URLs based on common patterns" | `tools/browser/browser.ts:58` | 코드 확인 |
| 웹 콘텐츠 주입 방어 | 웹/트윗/공시 텍스트를 신뢰 경계로 구분하거나 정제하는 코드 없음(요약기 시스템 프롬프트가 "using only the provided web page content"라고만 지시) | `fetch/utils.ts:347-348` | 코드 확인(없음), 위험성은 추론 |

## 5-6. 리서치 루프의 종료 조건

- 별도의 "리서치 루프"는 없고 **메인 ReAct 루프가 곧 리서치 루프**다 (`agent.ts:149-289`). 종료: LLM이 더 이상 도구를 부르지 않을 때 / 반복 10회 / 오류 / 거부. 서브에이전트는 8회 (`subagent/types.ts:60,66,72`), cron/heartbeat는 6회 (`cron/executor.ts:146`).
- **시간 제한 없음**(루프 차원). 단일 호출 제한만: 메타툴 하위 호출 60초, 웹페이지 60초, X 대기 ≤ 60초×3 (`finance/utils.ts:8`, `fetch/utils.ts:68`, `x-search.ts:7-8`).
- 반복 상한에 도달하면 **조사한 내용을 요약하지 않고** 고정 문구("Reached maximum iterations (10). I was unable to complete the research in the allotted steps.")를 돌려준다 (`agent.ts:278-288`). 즉 10회를 다 쓰면 그동안의 조사 결과는 사용자에게 전달되지 않는다. 검증: 코드 확인.
- 컨텍스트가 커져도 리서치가 이어지도록 마이크로컴팩트(8개 초과 시 오래된 결과 제거), LLM 컴팩션(요약 9항목 중 "Numerical Data: ALL key numbers" 보존 강조, `compact.ts:56`), 메모리 플러시 순서로 관리한다 (`agent.ts:558-660`). 검증: 코드 확인.

## 5-7. 요약 평가 (분석자 관찰)

- **강점(관찰)**: 질문→도구 선택이 전부 LLM 재량이라 유연하고, 도구 결과 압축·캡·컴팩션이 잘 갖춰져 긴 조사에도 컨텍스트가 터지지 않는다. 서브에이전트 병렬화가 코드 수준에서 지원된다.
- **약점(관찰, 추론 포함)**: ① 검색 결과의 시점·신뢰도 메타가 없다. ② 출처 인용·수치 근거 의무가 프롬프트에 없다. ③ 루프 소진 시 부분 결과 폐기. ④ 폴백이 예외에만 반응. 이상은 코드로 확인된 부재이며, 그것이 답변 품질에 미치는 영향은 `추론`이다.
