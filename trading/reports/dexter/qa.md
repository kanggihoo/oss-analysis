# dexter — 질문·답변 검증 기록

- 분석 SHA: `534f6be455523c5926eba72bdaf4f914555be5c9`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 1
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | "company facts"(섹터·산업·시총)를 반환하는 도구나 엔드포인트가 실제로 있는가 | Q1 | 없음 확정 | R1 |
| R1-Q2 | 금융 하위 도구 결과에 formatter가 적용되는 경로와, formatter가 없는 도구의 결과 형태 | Q2 | 해소 | R1 |
| R1-Q3 | 이력 가격 영구 캐시의 "오늘 이전" 판정 기준 시간대 | Q2 | 해소 | R1 |
| R1-Q4 | cron 러너를 시작하는 호출처가 게이트웨이뿐인가 | Q3 | 해소 | R1 |
| R1-Q5 | heartbeat 기본 주기 30분/10분 중 실제로 적용되는 값과 조건 | Q3 | 해소 | R1 |
| R1-Q6 | `await` 없는 `ensureHeartbeatCronJob()`과 러너의 jobs.json 쓰기가 겹칠 때의 동작 | Q3 | 해소 | R1 |
| R1-Q7 | CLI 기본 실행 시 메인 모델 ID가 정해지는 경로와 최종값 | Q4-2 | 해소 | R1 |
| R1-Q8 | 도구 호출 한도 경고가 몇 번째 호출에서 어떤 문구로 나오는가 | Q4-2 | 해소 | R1 |
| R1-Q9 | 유사 질의(Jaccard 0.7) 비교 대상의 범위 | Q4-2, Q5 | 해소 | R1 |
| R1-Q10 | 컨텍스트 초과 오류 판별 기준(`isContextOverflowError`) | Q4-6 | 해소 | R1 |
| R1-Q11 | 무인 실행에서 승인 자동 deny가 루프 전체 종료로 이어지는가 | Q4-6, Q6 | 해소 | R1 |
| R1-Q12 | 반복 상한 소진 시 그동안의 도구 결과가 사용자에게 전달되는 경로가 있는가 | Q4-6, Q5 | 해소 | R1 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. "company facts" 데이터의 실제 공급 경로
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` Q1 "정의만 있고 쓰이지 않는 것" 표는 "company facts"(섹터·산업·시총) 도구가 `FINANCE_TOOLS`에 없다고 하고(`get-financials.ts:20,60-73`), 영향은 `추론`으로 남겼다. `next.md` "분석 중 생긴 질문" 1번과 미확인 체크리스트 마지막 항목도 같은 내용이다. 그런데 섹터·시총 같은 필드가 다른 도구(예: `get_key_ratios` 스냅샷, 주가 스냅샷, 스크리너)의 응답이나 formatter에 들어 있는지는 확인되지 않았다. DCF 스킬이 WACC 섹터 선택에 이 값을 쓰므로(`skills/dcf/SKILL.md:53-60`) 데이터 인벤토리상 "없음"인지 "다른 도구로 얻음"인지가 갈린다.
- 질문: `src/` 전체에서 섹터·산업·시가총액(`sector`, `industry`, `market_cap` 및 변형) 필드를 LLM에 전달하는 도구가 하나라도 있는가? 있다면 어떤 도구·formatter의 어느 라인인가?
- 답변 완료 조건: 해당 필드를 출력하는 `파일:라인`과 원문 인용, 또는 "없음 확정"이면 grep 패턴 목록(`sector|industry|market_cap|marketCap|company/facts|company_facts` 등 대소문자 변형 포함)과 확인한 디렉터리(`src/tools/finance/` 전체, `formatters.ts`).

#### R1-Q2. 금융 하위 도구 결과가 LLM에 들어가는 형태 (formatter 적용 경로)
- GUIDE 항목: Q2 (원시 데이터 가공)
- 왜 묻는가: `01-data.md` 2.3절과 `03-decision.md` 4-1절은 "금융 메타툴은 `data`를 마크다운 표 문자열로 압축해 넣는다"(`formatters.ts:416-438`)고 쓰지만, formatter를 **어느 함수가 어느 시점에 호출하는지**, 그리고 레지스트리에 formatter가 없는 하위 도구(예: 내부자·13F·뉴스·공시 Item)는 원본 JSON이 그대로 들어가는지가 적혀 있지 않다. `next.md` "다음에 볼 파일"의 첫 항목이기도 하다.
- 질문: `get_financials`/`get_market_data`가 하위 도구 결과를 합칠 때 formatter 레지스트리를 조회하는 호출 지점은 어디이고, 레지스트리에 키가 없는 하위 도구의 결과는 어떤 형태(원본 JSON 문자열 등)로 ToolMessage에 들어가는가?
- 답변 완료 조건: formatter 조회·호출 지점의 `파일:라인`과 분기 조건 원문, 레지스트리에 등록된 하위 도구 이름 목록과 등록되지 않은 하위 도구 이름 목록.

#### R1-Q3. 이력 가격 영구 캐시의 "오늘" 판정 기준
- GUIDE 항목: Q2 (캐시)
- 왜 묻는가: `01-data.md` 2.4절은 "이력 가격은 `end_date`가 오늘 이전일 때만 캐시하며 이때 TTL이 없어 영구"라고 쓴다(`stock-price.ts:62-66`, `crypto.ts:59`). "오늘"을 UTC로 계산하는지 로컬 시간대로 계산하는지에 따라, 장중이거나 미국 장 마감 직후의 당일 봉이 미완성 상태로 영구 캐시될 수 있다. 신선도(Q3) 판단과 직결되는데 기준 시간대가 적혀 있지 않다.
- 질문: 주식·코인 이력 가격 도구에서 캐시 여부를 정하는 "오늘" 날짜 문자열은 어떤 코드로 만들어지며, 어떤 시간대 기준인가?
- 답변 완료 조건: 날짜 비교 코드의 `파일:라인`과 원문 인용(예: `new Date().toISOString()` 등), 그 결과 시간대(UTC/로컬)의 명시.

#### R1-Q4. cron 러너를 시작하는 호출처
- GUIDE 항목: Q3 (트리거)
- 왜 묻는가: `02-schedule.md` 3.1절은 cron과 heartbeat를 트리거로 나열하고, 3.4절은 "WhatsApp 세션이 없으면 작업을 건너뛴다"고 쓴다. 그러나 cron 러너(`cron/runner.ts`) 자체를 **누가 시작하는지**는 적혀 있지 않다. CLI 단독 실행(`src/cli.ts`)에서도 러너가 도는지, 게이트웨이 프로세스에서만 도는지가 "정기 실행이 가능한 실행 모드"를 정한다.
- 질문: cron 러너의 시작 함수(예: `start()` 또는 동등한 것)를 호출하는 곳은 `src/` 전체에서 어디어디인가?
- 답변 완료 조건: 모든 호출처의 `파일:라인`과 원문 인용, 그리고 CLI 진입점(`src/cli.ts`)에서 러너가 시작되는지 여부. 호출처가 하나뿐이면 사용한 grep 패턴과 범위.

#### R1-Q5. heartbeat 기본 주기 30분/10분 불일치의 실제 적용
- GUIDE 항목: Q3 (주기와 시점)
- 왜 묻는가: `02-schedule.md` 3.2절은 "설정 파싱 기본 30분, 그러나 `heartbeat` 도구가 자동 활성화할 때 기본 10분(불일치)"이라고만 쓴다(`heartbeat-migration.ts:30`, `gateway/config.ts:160` vs `heartbeat-tool.ts:52-55`). 처음 읽는 사람은 실제로 어느 주기로 돌아가는지 알 수 없다. 두 경로가 같은 cron 작업("Heartbeat")을 덮어쓰는지, 서로 다른 작업을 만드는지도 불명확하다.
- 질문: 사용자가 아무 설정도 하지 않은 상태에서 (a) 게이트웨이 시작만 한 경우와 (b) 이후 LLM이 `heartbeat` 도구로 활성화한 경우, jobs.json의 Heartbeat 작업 `every` 값은 각각 얼마가 되며, (b)가 (a)의 작업을 갱신하는가 새로 추가하는가?
- 답변 완료 조건: 두 경로의 작업 생성·갱신 코드 `파일:라인`과 원문, 작업 식별(이름/ID) 비교 조건, 경우별 최종 `every` 값.

#### R1-Q6. `ensureHeartbeatCronJob()` 비동기 호출과 jobs.json 동시 쓰기
- GUIDE 항목: Q3
- 왜 묻는가: `02-schedule.md` 3.4절은 `ensureHeartbeatCronJob()`이 `await` 없이 호출되지만(`gateway/gateway.ts:230`) "실사용 영향은 작을 것으로 보인다"고 `추론`으로 끝낸다. 러너도 실행 후 `nextRunAtMs` 등을 jobs.json에 쓰므로, 두 쓰기가 겹치면 한쪽이 다른 쪽을 덮어써 작업이 유실될 수 있는지가 코드로 정해져야 한다.
- 질문: jobs.json 저장 함수(`cron/store.ts`)는 읽기-수정-쓰기를 어떻게 하며(전체 파일 덮어쓰기인지, 잠금이 있는지), 러너가 시작 직후 jobs.json에 쓰는 시점이 `ensureHeartbeatCronJob()`의 쓰기보다 앞설 수 있는가?
- 답변 완료 조건: 저장·로드 함수의 `파일:라인`과 원문, 잠금/원자적 쓰기 유무(없으면 조사 범위), 게이트웨이 시작 순서(호출 순서대로)와 러너가 처음 쓰는 지점의 `파일:라인`. 결론은 "덮어쓰기 가능/불가능"으로.

#### R1-Q7. CLI 기본 실행 시 메인 모델이 정해지는 경로
- GUIDE 항목: Q4-2 (모델 계층)
- 왜 묻는가: `00-overview.md` 1절과 `next.md` README 차이 표는 기본 모델이 `agent.ts:23`(`gpt-5.6-sol`), `llm.ts:19`(`gpt-6-astra`), `AGENTS.md:49`(`gpt-5.5`)로 서로 다르다고만 기록한다. `03-decision.md` 4-2 모델 계층 표는 메인 루프 모델을 "사용자가 고른 모델"이라고만 쓴다. 설정 파일이 없는 첫 실행에서 실제로 어떤 모델 ID가 LLM 호출에 쓰이는지, 그리고 메타툴 라우터도 같은 값을 받는지가 확정되지 않았다.
- 질문: 설정 파일이 없는 상태에서 `src/cli.ts`로 질의하면, 메인 루프의 LLM 호출에 전달되는 모델 ID는 어느 상수에서 오며 최종값은 무엇인가?
- 답변 완료 조건: CLI 진입 → 컨트롤러 → `Agent.create` → `callLlm`까지 모델 값이 전달되는 각 단계의 `파일:라인`과 원문, 사용되는 기본 상수 하나와 사용되지 않는 상수(있다면)의 명시.

#### R1-Q8. 도구 호출 한도 경고의 정확한 회차와 문구
- GUIDE 항목: Q4-2 (루프 방지)
- 왜 묻는가: `03-decision.md` 4-2 루프 방지 표는 "3회째부터 suggested limit 경고"와 "1회 남음 경고(한도 직전)"를 따로 적었고, `04-research.md` 5-3절도 "3회째부터 경고"라고 쓴다. `maxCallsPerTool: 3`에서 "1회 남음"이 2회째인지, "한도 초과"가 3회째인지 4회째인지가 비교 연산자에 따라 달라지는데 원문이 인용되지 않았다.
- 질문: 같은 도구를 1, 2, 3, 4번째로 호출할 때 `scratchpad.ts`의 한도 검사는 각각 어떤 경고(없음/1회 남음/한도 도달)를 반환하는가?
- 답변 완료 조건: 카운트 증가 시점과 비교 연산자 원문(`scratchpad.ts:131-175` 범위 `파일:라인`), 회차별 반환 문구 표.

#### R1-Q9. 유사 질의 비교 대상의 범위
- GUIDE 항목: Q4-2, Q5 (반복 검색 방지)
- 왜 묻는가: `03-decision.md` 4-2 표와 `04-research.md` 5-3절은 "Jaccard 유사도 ≥ 0.7이면 경고"라고만 쓴다(`scratchpad.ts:245-283`). 새 질의를 **같은 도구의 이전 질의들과만** 비교하는지, 모든 도구의 이전 질의와 비교하는지, 직전 1건과만 비교하는지가 적혀 있지 않다. 예컨대 `web_search`와 `get_market_data`에 같은 문장을 넣으면 경고가 나는지가 이것으로 갈린다.
- 질문: 유사 질의 검사는 새 질의를 어떤 집합(같은 도구 이름의 과거 질의 / 전체 도구 / 직전 1건)과 비교하는가?
- 답변 완료 조건: 비교 대상 목록을 만드는 코드의 `파일:라인`과 원문 인용, 질의 저장 시점의 `파일:라인`.

#### R1-Q10. 컨텍스트 초과 오류 판별 기준
- GUIDE 항목: Q4-6 (실패 처리)
- 왜 묻는가: `03-decision.md` 4-2 종료 조건 표는 "오류 메시지 판별 후 최근 3라운드만 남기고 재시도, 최대 2회"(`agent.ts:25-26,176-183`)라고 쓰지만, 판별 함수 `isContextOverflowError`의 기준은 `next.md` 미확인 체크리스트와 "다음에 볼 파일"에 남아 있다. 판별에서 빠지는 제공자가 있으면 그 제공자는 재시도 없이 바로 `Error:` 종료 경로로 간다.
- 질문: `src/utils/errors.ts`의 `isContextOverflowError()`는 어떤 문자열·상태코드·에러 타입으로 컨텍스트 초과를 판별하는가?
- 답변 완료 조건: 함수 정의 `파일:라인`과 판별 패턴 원문 전체, `agent.ts`에서 이 함수를 호출하는 `파일:라인`.

#### R1-Q11. 무인 실행에서 승인 자동 deny가 루프를 끝내는가
- GUIDE 항목: Q4-6, Q6 (사람 승인 단계)
- 왜 묻는가: `03-decision.md` 4-5 표와 `05-boundary-and-fit.md` Q6 표는 "승인 콜백이 없으면 `deny`"(`tool-executor.ts:153-158`)라고 쓰고, 4-2 종료 조건 표는 "사용자 거부 → 즉시 종료, `answer: ''`"(`agent.ts:245-257`)라고 쓴다. 두 사실을 이으면 cron/heartbeat 실행 중 LLM이 `write_file`(예: write-memo 스킬의 HTML 저장)을 시도하는 순간 루프 전체가 빈 답으로 끝나고, 빈 응답은 억제 규칙(`suppression.ts`)에 걸려 아무것도 전달되지 않을 수 있다. 자동 deny가 "사용자 거부"와 같은 종료 경로를 타는지는 확인되지 않았다.
- 질문: 승인 콜백이 없어서 자동으로 `deny`가 된 경우, `agent.ts:245-257`의 거부 종료 분기가 실행되는가, 아니면 거부 결과만 ToolMessage로 넣고 루프가 계속되는가?
- 답변 완료 조건: 자동 deny 시 tool-executor가 내보내는 이벤트/플래그의 `파일:라인`과 원문, `agent.ts`의 종료 분기 조건 원문, 그리고 cron 실행 경로(`gateway/agent-runner.ts`)에서 승인 콜백을 넘기는지 여부.

#### R1-Q12. 반복 상한 소진 시 부분 결과의 전달 경로
- GUIDE 항목: Q4-6, Q5 (리서치 루프 종료)
- 왜 묻는가: `04-research.md` 5-6절은 "10회를 다 쓰면 그동안의 조사 결과는 사용자에게 전달되지 않는다"고 단정하지만, `03-decision.md` 4-4 출력 스키마 표에는 `DoneEvent.toolCalls[]`(도구 기록과 결과)가 있다. CLI 컨트롤러나 UI가 이 필드나 중간 `thinking` 텍스트를 화면에 남기는지(`05-boundary-and-fit.md` UI 절은 `thinking`을 표시한다고 씀)에 따라 "전달되지 않는다"의 범위가 달라진다.
- 질문: 반복 상한 소진으로 done 이벤트가 발생할 때, CLI 화면(컨트롤러·컴포넌트)에 고정 문구 외에 남는 것은 무엇인가(이미 표시된 thinking·도구 호출 행, `toolCalls` 내용 등)?
- 답변 완료 조건: done 이벤트 처리 코드(`controllers/agent-runner.ts`)의 `파일:라인`과 원문, `toolCalls` 필드를 읽는 UI 코드의 유무(없으면 grep 범위), 반복 소진 시 이미 렌더된 항목이 지워지는지 유지되는지.

### 답변 (답변자)

#### R1-Q1 답변
- 결론: **없음 확정** — "company facts"(섹터·산업)를 LLM에 전달하는 도구·엔드포인트·formatter 필드는 `src/` 전체에 없다. 시가총액(`market_cap`)만 `get_key_ratios` formatter가 출력한다. 단 `stock_screener`는 API 응답을 가공 없이 통과시키므로 그 응답에 섹터 필드가 있는지는 외부 API 응답 의존이라 정적으로 알 수 없다(분기는 동작 설명 4번). 보고서의 "company facts 도구 없음" 서술은 맞다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/tools/finance/get-financials.ts:20` | `GET_FINANCIALS_DESCRIPTION` | `- Company facts (sector, industry, market cap, number of employees, listing date, exchange, location, weighted average shares, website)` | 설명 문구만 있음 |
  | `src/tools/finance/get-financials.ts:60-73` | `FINANCE_TOOLS` | `getIncomeStatements, getBalanceSheets, getCashFlowStatements, getAllFinancialStatements, getEarnings, getKeyRatios, getHistoricalKeyRatios, getFinancialSegments` (8개) | company facts 도구 없음 |
  | `src/tools/finance/formatters.ts:137` | `formatKeyRatios` | ``lines.push(`- Market Cap: ${fmtNum(d.market_cap)}`);`` | 시총만 출력 |
  | `src/tools/finance/formatters.ts:165-174` | `formatStockPrice` | ``return `${ticker}: ${fmtPrice(d.price ?? d.close)}${chg}`;`` | 가격·등락률만. 시총 버림 |
  | `src/tools/finance/screen-stocks.ts:161-166` | `stock_screener` | `const { data, url } = await api.post('/financials/search/screener/', {...}); return formatToolResult(data, [url]);` | 응답을 그대로 반환 |
  | `src/tools/finance/screen-stocks.ts:97` | 스크리너 프롬프트 | `Company fields (sector, industry) use GICS classification and require string values with the "eq" or "in" operator` | 섹터는 **필터 입력**으로만 쓰임 |
  | `src/skills/dcf/SKILL.md:58,74` / `sector-wacc.md:7` | DCF 스킬 | `**Extract:** \`sector\`, \`industry\`, \`market_cap\`` / `Use \`get_financials\` with query "[TICKER] company facts"` | 스킬은 요구하지만 받을 도구가 없음 |

- 동작 설명:
  1. `get_financials`는 라우터 LLM에 `FINANCE_TOOLS` 8개만 바인딩한다(`get-financials.ts:143-147`의 `callLlm(input.query, { model, systemPrompt, tools: FINANCE_TOOLS })`). 섹터·산업을 내는 도구는 없다. `src/tools/finance/` 다른 파일에도 `company/facts` 계열 엔드포인트 호출이 없다.
  2. `get_key_ratios`는 `/financial-metrics/snapshot/`의 `data.snapshot`을 반환하고(`key-ratios.ts:27-28`), `FINANCIAL_FORMATTERS.get_key_ratios`(`formatKeyRatios`)가 `market_cap`, P/E, P/S, P/B, EPS, 성장률, 마진, ROE/ROIC, D/E만 남기고 나머지는 버린다. 스냅샷에 `sector`가 있어도 LLM에는 가지 않는다.
  3. `get_market_data`의 `get_stock_price`는 `formatStockPrice`가 가격·등락률만 남긴다. 라우터 프롬프트는 "(price, market cap, volume)"이라 쓰지만(`get-market-data.ts` Tool Selection 3번) 실제 출력에 시총은 없다(보고서 반영 권장).
  4. 분기: `stock_screener` 결과는 formatter 없이 JSON이 그대로 들어간다. 종목 행에 `sector`/`industry`가 포함되는지는 외부 API(`/financials/search/screener/`) 응답에 달려 있고 이 레포에 응답 스키마가 없다. (a) 포함되면 LLM이 원문 그대로 받고, (b) 없으면 못 받는다. 어느 쪽이든 특정 종목의 company facts를 조회하는 경로는 아니다.
  5. 따라서 DCF 스킬의 `"[TICKER] company facts"` 쿼리에 대해 라우터가 취할 수 있는 경우는 (i) 가장 가까운 도구(`get_key_ratios` 등) 선택, (ii) `No tools selected for query` 오류(`get-financials.ts:152-154`)이며 어느 쪽인지는 LLM 출력이라 정적으로 정해지지 않는다. 어느 경우도 섹터 값이 코드 경로로 공급되지는 않는다.
- 추가 발견(보고서 반영 후보): `get-financials.ts:98` 라우터 프롬프트는 `get_financial_metrics_snapshot` 호출을 안내하지만 그 이름의 도구는 없다(실제 `get_key_ratios`, `key-ratios.ts:16`). 라우터가 그 이름을 호출하면 `Tool 'get_financial_metrics_snapshot' not found`(`get-financials.ts:164`)가 `_errors`에 담긴다. 99행은 `get_key_ratios`를 "historical P/E ... over time"용으로 적어 역할도 뒤섞여 있다.
- 조사 범위: `grep -rniE "sector|industry|market_?cap|company/facts|company_facts|companyFacts" src` 및 레포 루트 전체(`--exclude-dir=node_modules --exclude-dir=.git`)에서 `company/facts|company_facts|get_company_facts|companyFacts` **0건**. `src/tools/finance/` 전 파일 확인, `formatters.ts`의 `market_cap`은 137행 한 곳뿐, `src/tools/finance/index.ts` export 목록에도 company facts 도구 없음.

#### R1-Q2 답변
- 결론: **확정** — formatter 조회·호출 지점은 `get-financials.ts:201-204`와 `get-market-data.ts:224-227` 두 곳이다. 레지스트리에 키가 없는 하위 도구는 `result.data`(파싱된 객체)를 그대로 `combinedData`에 넣고 마지막에 `JSON.stringify`된다. 금융 라우터의 8개 하위 도구는 모두 등록되어 있고, 시장 데이터 라우터 12개 중 ticker 목록 2개만 미등록이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/tools/finance/get-financials.ts:165-175` | 하위 도구 실행 | `const rawResult = await withTimeout(tool.invoke(tc.args), SUB_TOOL_TIMEOUT_MS, tc.name); ... const parsed = JSON.parse(result); return { tool: tc.name, args: tc.args, data: parsed.data, sourceUrls: ... }` | 각 하위 도구의 `formatToolResult` 문자열을 파싱해 `data`만 꺼냄 |
  | `src/tools/finance/get-financials.ts:201-204` | 조회·호출 지점 | `const formatter = FINANCIAL_FORMATTERS[result.tool]; combinedData[key] = formatter ? formatter(result.data, result.args as Record<string, unknown>) : result.data;` | 키가 없으면 원본 객체 |
  | `src/tools/finance/get-financials.ts:216` | 반환 | `return formatToolResult(combinedData, allUrls);` | `types.ts:6-11`이 `JSON.stringify({ data, sourceUrls })` |
  | `src/tools/finance/get-market-data.ts:224-227` | 조회·호출 지점 | `const formatter = MARKET_DATA_FORMATTERS[result.tool]; combinedData[key] = formatter ? formatter(...) : result.data;` | 동일 구조 |
  | `src/tools/finance/formatters.ts:416-425` | `FINANCIAL_FORMATTERS` | `get_income_statements, get_balance_sheets, get_cash_flow_statements, get_all_financial_statements, get_key_ratios, get_historical_key_ratios, get_earnings, get_financial_segments` | 8개 |
  | `src/tools/finance/formatters.ts:427-438` | `MARKET_DATA_FORMATTERS` | `get_stock_price, get_stock_prices, get_crypto_price_snapshot, get_crypto_prices, get_company_news, get_insider_trades, get_insider_names, get_insider_ownership, get_institutional_holdings, get_beneficial_ownership` | 10개 |
  | `src/tools/finance/get-market-data.ts:68-87` | `buildMarketDataTools` | `getStockPrice, getStockPrices, getStockTickers, getCryptoPriceSnapshot, getCryptoPrices, getCryptoTickers, getCompanyNews, createGetInsiderTrades(model), getInsiderNames, getInsiderOwnership, getInstitutionalHoldings, getBeneficialOwnership` | 12개 |
  | `stock-price.ts:72` / `crypto.ts:65` | 도구 `name` | `name: 'get_available_stock_tickers'` / `name: 'get_available_crypto_tickers'` | 레지스트리 키에 없음 |

- 동작 설명:
  1. 메인 에이전트가 `get_financials`/`get_market_data`를 호출하면(`tool-executor.ts:199`의 `tool.invoke`) 라우터 LLM이 하위 도구를 고르고 `Promise.all`로 병렬 실행한다. 각 하위 도구는 `{"data":...,"sourceUrls":[...]}` 문자열을 돌려주고 메타툴이 `JSON.parse` 후 `data`만 취한다.
  2. 키는 `ticker` 인자가 있으면 `${tool}_${ticker}`, 없으면 `tool`.
  3. 등록된 도구는 formatter가 **문자열**(마크다운 표/줄 목록)로 바꾼다. 미등록 도구(`get_available_stock_tickers`, `get_available_crypto_tickers`)는 `data`(배열)가 그대로 들어가 최종 JSON 안에 중첩된다. 즉 등록 도구는 "JSON 안의 마크다운 문자열 값", 미등록은 "JSON 안의 JSON 배열"이다.
  4. 금융 라우터에는 미등록 도구가 없다. 보고서가 예로 든 내부자·13F·뉴스도 모두 **등록**되어 있다(`get_insider_trades`, `get_institutional_holdings`, `get_company_news`). `get_institutional_investors`(`institutional_holdings.ts:113`)와 `get_filings`류는 두 라우터 도구 목록에 없다(`read_filings`는 별도 메타툴).
  5. 실패한 하위 도구는 `_errors: [{tool, args, error}]`로 들어간다(`get-financials.ts:208-214`).
  6. 이 문자열은 `tool-executor.ts:208-212`에서 `tool_end.result`가 되고 `agent.ts:396-401`에서 `ToolMessage.content`가 된다. 크기 상한 초과 시 `agent.ts:229-234`가 디스크에 저장하고 미리보기로 대체한다.
- 조사 범위: `grep -n "FORMATTERS\|formatter" src/tools/finance/*.ts`, `get-financials.ts`·`get-market-data.ts` 전체, `formatters.ts:400-440`, `grep -n "name: '" src/tools/finance/*.ts`(모든 도구 이름), `types.ts:6-12`, `agent.ts:224-243,396-401`.

#### R1-Q3 답변
- 결론: **확정** — "오늘"은 **실행 머신의 로컬 시간대 자정**이다(UTC 아님). `end_date`가 로컬 오늘 자정보다 엄격히 이전일 때만 캐시하고 캐시 항목에는 TTL이 없다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/tools/finance/stock-price.ts:62-66` | `getStockPrices` | `const endDate = new Date(input.end_date + 'T00:00:00'); const today = new Date(); today.setHours(0, 0, 0, 0); const { data, url } = await api.get('/prices/', params, { cacheable: endDate < today });` | 코드 확인 |
  | `src/tools/finance/crypto.ts:56-59` | `getCryptoPrices` | 동일 구조, 엔드포인트 `'/crypto/prices/'` | 코드 확인 |
  | `src/tools/finance/api.ts:124-129,158-160` | `api.get` | `if (options?.cacheable) { const cached = readCache(endpoint, params, options.ttlMs);` / 쓰기도 `if (options?.cacheable) {` | `ttlMs` 미전달 |
  | `src/utils/cache.ts:152-158` | `readCache` | `if (ttlMs !== undefined) { const age = Date.now() - Date.parse(parsed.cachedAt); if (age > ttlMs) { return null; } }` | `ttlMs`가 없으면 만료 검사 없음 = 영구 |
  | `stock-price.ts:76`, `crypto.ts:69` | 티커 목록 | `{ cacheable: true, ttlMs: 24 * 60 * 60 * 1000 }` | 이쪽만 24시간 TTL |

- 동작 설명:
  1. `Z`/오프셋이 없는 `'YYYY-MM-DDT00:00:00'` 문자열은 JS가 **로컬 시각**으로 해석한다. `today.setHours(0,0,0,0)`도 로컬 자정이다. 즉 `endDate < today`는 "end_date가 로컬 달력으로 어제 이전"과 같다.
  2. 캐시 키는 `params`(ticker, interval, start_date, end_date)로 만들어진다(`cache.ts` `buildCacheKey`). end_date가 로컬 오늘이거나 미래면 캐시하지 않는다.
  3. 가능한 경우의 수: 로컬이 KST처럼 미국보다 앞서면 KST 날짜가 D로 넘어간 직후 미국은 아직 D-1이다. `end_date = D-1`로 부른 요청은 코드상 "닫힌 구간"이 되어 장중/마감 직후 상태여도 영구 캐시된다. 그 응답에 D-1 봉이 완성돼 있는지는 외부 API가 정하므로 정적으로 알 수 없다. 로컬이 미국보다 늦은 시간대면 반대로 보수적으로 어긋난다.
  4. 코드에 장 마감 시각·휴장일·봉 완성 여부 검사는 없다.
  5. 참고: 같은 파일 52-54행의 1주 확장은 `toISOString().slice(0, 10)`(UTC 변환)을 써서 캐시 판정(로컬)과 기준이 다르지만, 캐시 판정은 원래 `input.end_date`를 쓰므로 영향이 없다.
- 조사 범위: `grep -n "isPast|toISOString|new Date|today|TTL|cacheable|cache" src/tools/finance/stock-price.ts crypto.ts api.ts`, `src/utils/cache.ts` `readCache`.

#### R1-Q4 답변
- 결론: **확정** — cron 러너 시작 함수 `startCronRunner`의 호출처는 `src/gateway/gateway.ts:231` **하나뿐**이다. CLI(`src/index.tsx` → `src/cli.ts`)에서는 러너가 시작되지 않는다. 정기 실행은 `gateway/index.ts` → `startGateway`로 띄운 별도 프로세스에서만 일어난다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/cron/runner.ts:24` | `startCronRunner` | `export function startCronRunner(params: { configPath?: string }): CronRunner {` | 정의 |
  | `src/gateway/gateway.ts:14,231` | `startGateway` | `import { startCronRunner } from '../cron/runner.js';` / `const cron = startCronRunner({ configPath: params.configPath });` | 유일한 호출 |
  | `src/gateway/index.ts:126` | 게이트웨이 CLI | `const server = await startGateway();` | `startGateway`의 유일한 호출처 |
  | `package.json:11,13` | 스크립트 | `"start": "bun run src/index.tsx"` / `"gateway": "tsx src/gateway/index.ts run"` | 별도 프로세스 |
  | `src/index.tsx:2-8` | CLI 진입 | `import { runCli } from './cli.js'; ... await runCli();` | gateway/cron 러너 import 없음 |

- 동작 설명: `bun run start`(CLI)는 `runCli()`만 실행한다. CLI에서도 LLM이 cron 도구(`tools/cron/cron-tool.ts`)·heartbeat 도구로 `jobs.json`을 **작성**할 수는 있지만 그 작업을 실행하는 `tick`→`executeCronJob`(`runner.ts:54-76`)은 게이트웨이 프로세스에만 있다. 실행 결과 전달도 WhatsApp 전송(`executor.ts:174`)이고, 세션이 없으면 `no delivery target, skipping`(`executor.ts:113`)으로 건너뛴다. 따라서 "정기 실행이 가능한 모드"는 게이트웨이 모드뿐이다.
- 조사 범위: `grep -rn "startCronRunner|createCronRunner|CronRunner|runner.start|startCron|\.start()" src`(`.start()`는 `cli.ts:877`, `evals/run.ts:485`의 TUI 시작뿐), `grep -rn "startGateway" src`, `package.json` scripts 전체, 레포 루트 전체에서 `startCronRunner` 검색(`src` 밖 사용 없음).

#### R1-Q5 답변
- 결론: **확정** — **보고서 정정 필요**. (a) 게이트웨이 시작만 한 경우: `gateway.json`에 `heartbeat` 블록이 없으면 Heartbeat 작업 자체가 만들어지지 않는다. `heartbeat: { enabled: true }`만 쓰고 간격을 생략하면 Zod 기본값 때문에 `every`는 **10분**이다(`?? 30` 분기는 도달 불가). (b) 이후 LLM이 `heartbeat` 도구로 활성화한 경우: cron 작업을 **만들지도, `every`를 바꾸지도 않는다**(`gateway.json`만 쓰고, 기존 Heartbeat 작업이 있을 때만 메시지/활성 여부를 갱신). 작업 생성·주기 반영은 다음 게이트웨이 시작 때 `ensureHeartbeatCronJob`이 한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/gateway/config.ts:31-32` | `HeartbeatConfigSchema` | `enabled: z.boolean().optional().default(false),` / `intervalMinutes: z.number().min(5).optional().default(10),` | 스키마 기본값 10, 최소 5 |
  | `src/gateway/config.ts:157-160` | `loadGatewayConfig` | `heartbeat: parsed.gateway?.heartbeat ? { enabled: ... ?? false, intervalMinutes: parsed.gateway.heartbeat.intervalMinutes ?? 30,` | 파싱값은 이미 10이라 `?? 30` 미실행. 블록이 없으면 `undefined` |
  | `src/cron/heartbeat-migration.ts:19-21` | `ensureHeartbeatCronJob` | `const hb = cfg.gateway.heartbeat; if (!hb?.enabled) return;` | 설정 없으면 작업 없음 |
  | `src/cron/heartbeat-migration.ts:8,24,30` | 〃 | `const HEARTBEAT_JOB_NAME = 'Heartbeat';` / `const existing = store.jobs.find((j) => j.name === HEARTBEAT_JOB_NAME);` / `const everyMs = (hb.intervalMinutes ?? 30) * 60 * 1000;` | 식별은 **이름**. 여기도 `?? 30` 도달 불가 |
  | `src/cron/heartbeat-migration.ts:32-34,59-68` | 갱신/생성 | `existing.schedule = { kind: 'every', everyMs };` / `schedule: { kind: 'every', everyMs },` | 있으면 갱신, 없으면 추가 |
  | `src/tools/heartbeat/heartbeat-tool.ts:48-60` | `ensureHeartbeatEnabled` | `if (cfg.gateway.heartbeat?.enabled) return; ... intervalMinutes: cfg.gateway.heartbeat?.intervalMinutes ?? 10, ... saveGatewayConfig(cfg);` | `gateway.json`만 수정 |
  | `src/tools/heartbeat/heartbeat-tool.ts:66-81` | `syncHeartbeatCronJob` | `const job = store.jobs.find((j) => j.name === HEARTBEAT_JOB_NAME); if (!job) return;` ... `job.payload.message = query;` | 작업이 없으면 생성 안 함. `schedule` 불변 |
  | `src/gateway/gateway.ts:230` | 시작 시 | `ensureHeartbeatCronJob(params.configPath);` | 이 호출이 유일한 생성·주기 반영 지점 |

- 동작 설명:
  1. (a) 게이트웨이 시작: `loadGatewayConfig`가 `gateway.json`을 읽는다. 파일/블록이 없으면 `heartbeat`가 `undefined` → `!hb?.enabled`로 반환 → `jobs.json`에 Heartbeat 없음. `enabled: true`가 있고 `intervalMinutes`를 안 적으면 Zod가 10을 채우므로(`config.ts:32`) `everyMs = 10 * 60 * 1000`. 명시하면 그 값(5 미만은 파싱 오류).
  2. (b) 도구 활성화: 체크리스트에 `-` 항목이 있으면(`heartbeat-tool.ts:107-112`) `ensureHeartbeatEnabled()`가 `enabled: true`로 `gateway.json`을 쓴다. 블록이 없었으면 `intervalMinutes = 10`, 있던 블록(비활성)이면 파싱된 기존 값을 유지한다. 이어서 `syncHeartbeatCronJob()`은 이름 `Heartbeat` 작업이 있으면 `payload.message`만 갱신(체크리스트가 비면 `enabled=false`)하고 없으면 반환한다.
  3. 따라서 (b)는 (a)의 작업을 "갱신"하더라도 `every`는 건드리지 않고, 새 작업을 "추가"하지도 않는다. 같은 이름 `Heartbeat` 작업의 `every`는 다음 게이트웨이 시작 때 `existing.schedule = { kind: 'every', everyMs }`(`heartbeat-migration.ts:34`)로 설정값에 맞춰진다. 게이트웨이가 이미 떠 있는 상태에서 (b)만 일어나면 재시작 전까지 Heartbeat 작업은 없다.
  4. 보고서의 "30분 vs 10분 불일치"는 정정 필요: 두 `?? 30`은 스키마 기본값 때문에 실행될 수 없는 코드이고 실제 기본값은 모든 경로에서 10분이다.
- 조사 범위: `grep -n "intervalMinutes" src/gateway/config.ts`(32, 99, 160), `grep -rn "intervalMinutes\|HEARTBEAT_JOB_NAME" src`, `heartbeat-migration.ts` 전체, `heartbeat-tool.ts:36-135`, `gateway.ts:215-241`, `config.ts:25-60,139-180`.

#### R1-Q6 답변
- 결론: **확정** — **덮어쓰기 가능**. `jobs.json` 저장은 "전체 로드 → 메모리 수정 → 전체 덮어쓰기(임시파일 + rename)"이며 **잠금이 없다**. rename은 파일이 반쯤 쓰이는 것만 막을 뿐 마지막에 쓴 쪽이 이긴다. 시작 직후 러너의 자체 쓰기는 조건부이고, 더 큰 위험은 러너의 `executeCronJob`이 tick 시작 때 읽은 스냅샷을 긴 에이전트 실행 뒤 통째로 저장하는 부분이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/cron/store.ts:15-29` | `loadCronStore` | `const raw = readFileSync(CRON_STORE_PATH, 'utf-8'); ... return parsed;` (실패 시 `{ ...EMPTY_STORE, jobs: [] }`) | 매번 전체 읽기 |
  | `src/cron/store.ts:31-47` | `saveCronStore` | ``const tmp = `${CRON_STORE_PATH}.${process.pid}.${randomBytes(4).toString('hex')}.tmp`; writeFileSync(tmp, data, 'utf-8'); renameSync(tmp, CRON_STORE_PATH);`` | 원자적 교체, 잠금·병합 없음 |
  | `src/gateway/gateway.ts:230-231` | 시작 순서 | `ensureHeartbeatCronJob(params.configPath); const cron = startCronRunner({ configPath: params.configPath });` | `await` 없음 |
  | `src/cron/heartbeat-migration.ts:23,27,55,91` | `ensureHeartbeatCronJob` | `const store = loadCronStore();` → `const query = await buildHeartbeatQuery();` → `saveCronStore(store);` | **읽기와 쓰기 사이에 `await`**(`readFile`, `heartbeat/prompt.ts:16`) |
  | `src/cron/runner.ts:30-52` | `startup()` | `const store = loadCronStore(); ... if (job.state.nextRunAtMs === undefined) {... changed = true;} ... if (changed) saveCronStore(store);` | 시작 시 쓰기는 `nextRunAtMs`가 없는 활성 작업이 있을 때만 |
  | `src/cron/runner.ts:54-71` | `tick` | `const store = loadCronStore(); ... await executeCronJob(job, store, params);` | 스냅샷을 들고 실행 |
  | `src/cron/executor.ts:191,222,254` | 저장 지점 | `saveCronStore(store);` | 에이전트 실행(`await runAgentForMessage`, `executor.ts:141`) **뒤** 스냅샷 전체 저장 |
  | `src/tools/cron/cron-tool.ts:94-136` | cron 도구 | `const store = loadCronStore(); ... store.jobs.push(job); ... saveCronStore(store);` | 같은 방식의 독립 쓰기 |

- 동작 설명(호출 순서대로):
  1. `startGateway`가 `ensureHeartbeatCronJob(...)`을 호출하고 Promise를 기다리지 않는다(`gateway.ts:230`). 함수는 `loadGatewayConfig`, `loadCronStore`(23행)까지 동기 실행한 뒤 `await buildHeartbeatQuery()`(27행)에서 양보한다.
  2. 같은 틱에 `startCronRunner`가 호출되어 `startup()`이 `loadCronStore()`로 다시 읽는다. `nextRunAtMs`가 없는 활성 작업이 있으면 저장하는데, 작업 생성 경로가 `nextRunAtMs`를 채우므로(`cron-tool.ts:109,129`, `heartbeat-migration.ts:84`) 보통 쓰지 않는다. 쓴다면 이어서 재개된 `ensureHeartbeatCronJob`이 옛 스냅샷으로 저장하며 그 변경을 덮어쓴다.
  3. 첫 `tick`은 `scheduleNext`의 `setTimeout`(`runner.ts:101-107`, 지연 0~60초, 밀린 작업이 있으면 0ms)이 발화한 뒤다. 0ms 타이머와 `readFile` 완료 중 무엇이 먼저인지는 이벤트 루프 순서에 달려 있어 정적으로 고정되지 않는다. 어느 쪽이든 가능한 결과: (i) tick이 `ensure`의 저장 **전에** 읽고, 활성 시간 밖/전달 대상 없음 같은 `await` 없는 경로(`executor.ts:100-117`)에서 `scheduleNextRun`이 먼저 저장한 뒤 `ensure`가 옛 스냅샷으로 저장하면 러너가 갱신한 `nextRunAtMs`가 되돌아간다. (ii) 에이전트 실행 중 `ensure`나 cron 도구가 추가한 작업이, 실행 뒤 tick 스냅샷 저장(`executor.ts:222,254`)으로 삭제된다.
  3-1. 따라서 결론은 덮어쓰기 가능이며 영향은 "추가된 작업 유실 또는 `nextRunAtMs` 되돌림"이다. 유실된 Heartbeat 작업은 다음 게이트웨이 시작 때 `ensureHeartbeatCronJob`이 다시 만든다.
- 조사 범위: `grep -rn "saveCronStore\|loadCronStore" src`(runner.ts, executor.ts, heartbeat-migration.ts, cron-tool.ts, heartbeat-tool.ts), `store.ts`·`runner.ts` 전체, `executor.ts:100-260`, `gateway.ts:215-241`. 파일 잠금 관련은 `src/cron`, `src/tools/cron`, `src/gateway`에서 `lock`/`mutex` 기반 코드를 찾지 못했다(`saveCronStore`가 `writeFileSync`+`renameSync`만 사용).

#### R1-Q7 답변
- 결론: **확정** — 설정 파일이 없는 첫 실행에서 CLI 메인 루프와 메타툴 라우터가 쓰는 모델 ID는 **`gpt-6-astra`**(`PROVIDER_MODELS.openai[0]`)다. `agent.ts:23`의 `gpt-5.6-sol`은 이 경로에서 쓰이지 않고, `AGENTS.md:49`의 `gpt-5.5`는 코드 경로에 없다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/index.tsx:2,8` → `src/cli.ts:204-208` | CLI 진입 | `await runCli();` / `const modelSelection = new ModelSelectionController(onError, ...` | 코드 확인 |
  | `src/controllers/model-selection.ts:49-52` | 생성자 | `this.providerValue = getSetting('provider', DEFAULT_PROVIDER); const savedModel = getSetting('modelId', null) as string \| null; this.modelValue = savedModel ?? getDefaultModelForProvider(this.providerValue) ?? DEFAULT_MODEL;` | 설정 없으면 provider=`openai` |
  | `src/model/llm.ts:18-19` | 상수 | `export const DEFAULT_PROVIDER = 'openai'; export const DEFAULT_MODEL = 'gpt-6-astra';` | 코드 확인 |
  | `src/utils/model.ts:15-19,52-55` | `PROVIDER_MODELS`, `getDefaultModelForProvider` | `openai: [ { id: 'gpt-6-astra', ...}, { id: 'gpt-6-sol', ...}, ...` / `return models[0]?.id;` | 첫 번째 = `gpt-6-astra` |
  | `src/utils/config.ts:116-124` | `getSetting` | `return (config[key] as T) ?? defaultValue;` | 설정 파일이 없으면 `loadConfig()`가 `{}`(46-48행) |
  | `src/cli.ts:232` | `AgentRunnerController` 생성 | `{ model: modelSelection.model, modelProvider: modelSelection.provider, maxIterations: 10 },` | 모델 주입 |
  | `src/controllers/agent-runner.ts:182-188` | `runQuery` | `const agent = await Agent.create({ ...this.agentConfig, signal: ..., ...});` | `model` 그대로 전달 |
  | `src/agent/agent.ts:58,78-79` | `Agent` | `this.model = config.model ?? DEFAULT_MODEL;` / `const model = config.model ?? DEFAULT_MODEL; const allTools = getTools(model);` | `config.model`이 있어 23행의 `'gpt-5.6-sol'`은 미사용 |
  | `src/agent/agent.ts:324-328` | 스트리밍 호출 | `streamLlmWithMessages(messages, { model: this.model, ...` | 메인 루프 호출 |
  | `src/tools/registry.ts:52,59,66,73` | 메타툴 | `createGetFinancials(model)`, `createGetMarketData(model)`, `createReadFilings(model)`, `createScreenStocks(model)` | 라우터도 같은 모델 |
  | `src/tools/finance/get-financials.ts:143-147` | 라우터 호출 | `callLlm(input.query, { model, systemPrompt: buildRouterPrompt(), tools: FINANCE_TOOLS })` | 같은 값 |

- 동작 설명: `cli.ts` → `ModelSelectionController`가 `gpt-6-astra`를 정함 → `AgentRunnerController.agentConfig.model` → `Agent.create`(`getTools(model)`로 메타툴에도 전달) → `streamLlmWithMessages(model: this.model)` → `getChatModel`. `agent.ts:23`의 `DEFAULT_MODEL = 'gpt-5.6-sol'`은 `config.model`이 `undefined`일 때만 쓰이는데 CLI(`cli.ts:232`)와 게이트웨이(`gateway/agent-runner.ts:86`, `model: string` 필수 필드)는 항상 값을 넣으므로 이 경로에서는 **사용되지 않는 상수**다. `llm.ts`의 `DEFAULT_MODEL`은 컨트롤러 폴백(`model-selection.ts:52`)과 `callLlm` 등의 `model` 미지정 시 기본값이고 여기서 최종값은 `getDefaultModelForProvider('openai')`가 먼저 정한 같은 `gpt-6-astra`다. `utils/config.ts:21-26`/`68-71`은 저장된 구 모델 ID(`gpt-5.5` → `gpt-6-astra`, `gpt-5.6-sol` → `gpt-6-sol`)를 로드 때 승급시키는 별개 로직이다. 게이트웨이·cron 경로도 기본이 `gpt-6-astra`다(`gateway.ts:160`, `executor.ts:128`).
- 조사 범위: `grep -rn "gpt-5.6-sol|gpt-6-astra|gpt-5.5|DEFAULT_MODEL|DEFAULT_PROVIDER" src`, `cli.ts`, `index.tsx`, `controllers/*`, `agent/agent.ts`, `model/llm.ts`, `utils/model.ts`, `utils/config.ts`, `tools/registry.ts`. `/model` 명령으로 모델을 바꾸는 경로는 "설정 파일이 없는 첫 실행" 조건을 벗어나므로 제외했다.

#### R1-Q8 답변
- 결론: **확정** — 회차별 경고는 아래 표와 같다. **보고서 정정 필요**: (1) "3회째부터 suggested limit 경고"가 아니라 3회째는 "approaching" 문구이고, "suggested limit" 초과 문구는 **4회째부터**다. (2) 더 중요하게, `canCallTool`의 경고 문구는 **LLM에 전달되지 않는다**. `tool_limit` UI 이벤트로만 나가고 CLI도 그리지 않는다(`cli.ts:169`). LLM이 실제로 보는 것은 매 라운드 끝에 `formatToolUsageForPrompt()`가 붙이는 "Tool Usage This Query" 요약이다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/scratchpad.ts:50-53` | `DEFAULT_LIMIT_CONFIG` | `maxCallsPerTool: 3, similarityThreshold: 0.7,` | 코드 확인 |
  | `src/agent/scratchpad.ts:131-144` | `canCallTool` | ``const currentCount = this.toolCallCounts.get(toolName) ?? 0; ... if (currentCount >= maxCalls) { return { allowed: true, warning: `Tool '${toolName}' has been called ${currentCount} times (suggested limit: ${maxCalls}). ...` }`` | 한도 검사가 **가장 먼저** |
  | `src/agent/scratchpad.ts:166-171` | 〃 | ``if (currentCount === maxCalls - 1) { ... warning: `You are approaching the suggested limit for '${toolName}' (${currentCount + 1}/${maxCalls}). ...` ``  | 3회째 |
  | `src/agent/scratchpad.ts:180-183` | `recordToolCall` | `const currentCount = ...; this.toolCallCounts.set(toolName, currentCount + 1);` | 카운트 증가 |
  | `src/agent/tool-executor.ts:175-178,212-215,218-221` | 호출처 | `const limitCheck = ctx.scratchpad.canCallTool(toolName, toolQuery); if (limitCheck.warning) { yield { type: 'tool_limit', tool: toolName, warning: limitCheck.warning, blocked: false }; }` / 성공·실패 모두 `ctx.scratchpad.recordToolCall(toolName, toolQuery);` | 검사는 실행 **전**, 기록은 실행 **후**(오류 포함) |
  | `src/cli.ts:169` | `renderEvent` | `if (event.type === 'tool_limit') return;` | 화면에 안 그림 |
  | `src/agent/agent.ts:243,265-268` | 루프 | `messages.push(...toolMessages);` ... `const toolUsageWarning = ctx.scratchpad.formatToolUsageForPrompt(); if (toolUsageWarning) { messages.push(new HumanMessage(toolUsageWarning)); }` | `tool_limit` 이벤트는 메시지에 넣지 않음 |
  | `src/agent/scratchpad.ts:230-238` | `formatToolUsageForPrompt` | ``${s.callCount} calls (over suggested limit of ${s.maxCalls})`` / ``${s.callCount}/${s.maxCalls} calls`` | LLM이 받는 문구 |

- 동작 설명: 같은 도구(이름 기준)를 한 번의 `agent.run` 안에서 N번째로 호출할 때 `currentCount = N-1`이다. 표는 **유사 질의가 아닌** 경우 기준이다(유사 질의는 Q9).

  | 호출 회차 | `currentCount` | `canCallTool`이 반환하는 `warning` (UI 이벤트로만 나감) | 그 호출이 끝난 뒤 LLM에 붙는 요약 줄 |
  |---|---|---|---|
  | 1번째 | 0 | 없음 | `- <tool>: 1/3 calls` |
  | 2번째 | 1 | 없음 | `- <tool>: 2/3 calls` |
  | 3번째 | 2 (`=== maxCalls - 1`) | `You are approaching the suggested limit for '<tool>' (3/3). If this doesn't return the needed data, consider trying a different approach.` | `- <tool>: 3 calls (over suggested limit of 3)` (`callCount >= maxCalls`) |
  | 4번째 | 3 (`>= maxCalls`) | `Tool '<tool>' has been called 3 times (suggested limit: 3). If previous calls didn't return the needed data, consider: (1) trying a different tool, (2) using different search terms, or (3) proceeding with what you have and noting any data gaps to the user.` | `- <tool>: 4 calls (over suggested limit of 3)` |

  5번째 이상은 4번째와 같은 문구이고 `has been called N times`의 N만 커진다. 어떤 경우에도 호출은 차단되지 않는다(`allowed: true`, `isBlocked: false`, `scratchpad.ts:212`). 따라서 LLM이 "한도 초과"라는 말을 처음 보는 시점은 **3번째 호출이 끝난 직후**(다음 반복의 입력)이고, 보고서의 "3회째부터"는 이 의미로는 맞지만 개별 경고 문구가 LLM에 간다는 전제는 틀리다. 한 응답에서 같은 도구를 동시에 여러 번 부르는 배치는 `recordToolCall`이 각 호출 완료 후라서 같은 `currentCount`로 검사될 수 있다(`executeBatchConcurrently`, `tool-executor.ts:120-126`).
- 조사 범위: `grep -rn "canCallTool\|recordToolCall\|tool_limit\|formatToolUsageForPrompt" src`, `scratchpad.ts:49-53,126-239`, `tool-executor.ts:131-223`, `agent.ts:224-268`, `cli.ts:160-170`, `controllers/agent-runner.ts:333-340`.

#### R1-Q9 답변
- 결론: **확정** — 새 질의는 **같은 도구 이름으로 이번 `agent.run`에서 이미 기록된 모든 과거 질의**와 비교한다(전체 도구와의 비교도, 직전 1건과의 비교도 아님). 따라서 `web_search`와 `get_market_data`에 같은 문장을 넣어도 유사 질의 경고는 나지 않는다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/scratchpad.ts:72-73` | 필드 | `private toolCallCounts: Map<string, number> = new Map(); private toolQueries: Map<string, string[]> = new Map();` | 도구명 → 질의 배열 |
  | `src/agent/scratchpad.ts:147-150` | `canCallTool` | `const previousQueries = this.toolQueries.get(toolName) ?? []; const similarQuery = this.findSimilarQuery(query, previousQueries);` | 비교 대상 목록 생성 |
  | `src/agent/scratchpad.ts:245-258` | `findSimilarQuery` | `for (const prevQuery of previousQueries) { ... if (similarity >= this.limitConfig.similarityThreshold) { return prevQuery; } }` | 전부 순회, `>= 0.7` |
  | `src/agent/scratchpad.ts:186-190` | `recordToolCall` | `if (query) { const queries = this.toolQueries.get(toolName) ?? []; queries.push(query); this.toolQueries.set(toolName, queries); }` | 저장 시점 = 도구 실행 **후**(성공·실패 모두, `tool-executor.ts:214,220`) |
  | `src/agent/scratchpad.ts:263-283` | `tokenize`, `calculateSimilarity` | `.toLowerCase().replace(/[^\w\s]/g, ' ').split(/\s+/).filter(w => w.length > 2)` / `return intersection / union; // Jaccard similarity` | 길이 3 이상 단어 집합의 Jaccard |
  | `src/agent/tool-executor.ts:225-233` | `extractQueryFromArgs` | `const queryKeys = ['query', 'search', 'question', 'q', 'text', 'input']; for (const key of queryKeys) { if (typeof args[key] === 'string') { return args[key] as string; } }` | 질의 문자열을 뽑는 인자 이름 |
  | `src/agent/run-context.ts:22-25` | `createRunContext` | `scratchpad: new Scratchpad(query),` | `agent.run`마다 새 인스턴스 |

- 동작 설명: (1) `executeSingleWithId`가 인자에서 위 6개 키 중 **먼저 일치하는 문자열 하나**를 `toolQuery`로 정한다. 6개 키가 모두 없는 도구(예: `get_stock_prices`의 `ticker`/날짜 인자, `read_file`의 `path`)는 `toolQuery`가 `undefined`라 유사도 검사와 질의 저장을 건너뛴다(카운트만 증가). (2) 검사 순서는 한도 초과 → 유사 질의 → 한도 직전이므로, 유사 질의가 감지되면 3번째 호출이어도 "approaching" 대신 `This query is very similar to a previous '<tool>' call. You have ${remaining} attempt(s) before reaching the suggested limit.`(remaining = 3 - currentCount)가 나온다. (3) 이 경고도 Q8과 같이 `tool_limit` 이벤트로만 나가 LLM에는 가지 않는다(`cli.ts:169`). 따라서 보고서(`03-decision.md` 4-2, `04-research.md` 5-3)의 "Jaccard ≥ 0.7이면 경고"는 LLM 행동을 바꾸는 장치가 아니라 UI 이벤트 생성까지만 영향을 준다(정정 필요).
- 조사 범위: `scratchpad.ts`의 `toolQueries`/`findSimilarQuery`/`tokenize`/`calculateSimilarity`, `grep -rn "toolQueries\|findSimilarQuery" src`, `tool-executor.ts:131-233`, `run-context.ts`, `grep -rn "new Scratchpad" src`(비-테스트는 `run-context.ts:25` 한 곳).

#### R1-Q10 답변
- 결론: **확정** — `isContextOverflowError(raw)`는 **오류 메시지 문자열**만으로 판별한다(HTTP 상태코드·에러 클래스는 보지 않는다). `agent.ts`의 호출은 176행 하나다. `tpm`/`tokens per minute`가 포함되면 무조건 `false`다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/utils/errors.ts:155-185` | `isContextOverflowError` | 아래 동작 설명 참조 | 코드 확인 |
  | `src/utils/errors.ts:65-76` | `ERROR_PATTERNS.contextOverflow` | `'context length exceeded', 'maximum context length', "this model's maximum context length", 'prompt is too long', 'request_too_large', 'exceeds model context window', 'context overflow', 'exceed context limit', 'model token limit', 'your request exceeded model token limit'` | 소문자 포함 검사 |
  | `src/utils/errors.ts:79` | `CHINESE_CONTEXT_OVERFLOW` | `['上下文过长', '上下文超出', '超出最大上下文']` | 원문 포함 검사 |
  | `src/utils/errors.ts:148-153` | `matchesPatterns` | `pattern instanceof RegExp ? pattern.test(raw) : lower.includes(pattern)` | 문자열은 소문자 부분일치 |
  | `src/agent/agent.ts:25-26,173-197` | 호출처 | `const MAX_OVERFLOW_RETRIES = 2; const OVERFLOW_KEEP_ROUNDS = 3;` / `if (isContextOverflowError(errorMessage) && overflowRetries < MAX_OVERFLOW_RETRIES) { overflowRetries++; const removed = this.truncateMessages(messages, OVERFLOW_KEEP_ROUNDS); if (removed > 0) { yield { type: 'context_cleared', ...}; continue; } }` | 유일한 호출처(그 밖에 `errors.ts:210`의 `classifyError` 내부) |

- 동작 설명(`errors.ts:155-185` 순서):
  1. `raw`가 비면 `false`.
  2. 소문자 변환 후 `tpm` 또는 `tokens per minute`를 포함하면 **`false`**(속도 제한으로 간주).
  3. `ERROR_PATTERNS.contextOverflow` 10개 문자열 중 하나를 소문자 비교로 포함하면 `true`.
  4. 중국어 3개 문구 중 하나를 포함하면 `true`.
  5. 조합 조건: `'request size exceeds'`+`'context'`; `'max_tokens'`+`'exceed'`+`'context'`; `'input length'`+`'exceed'`+`'context'`; `'413'`+`'too large'` — 각각 모두 포함하면 `true`.
  6. 그 외 `false`.
  `agent.ts` 흐름: 스트리밍 호출이 실패하면 `callModelWithStreaming`(`agent.ts:299-308`)이 블로킹 호출로 폴백하고, 그 오류가 `catch`(173행)로 올라온다. 판별이 `true`이고 재시도 < 2이면 최근 3라운드만 남기고(`truncateMessages`) 재시도하며, 줄일 것이 없어 `removed === 0`이거나 판별이 `false`이면 바로 `done`(`answer: "Error: ${formatUserFacingError(...)}"`, 185-196행)으로 종료한다. 정적으로 정해지지 않는 부분: 제공자(OpenAI, Anthropic, Google, Ollama 등)가 실제로 내는 메시지가 이 목록과 일치하는지는 외부 SDK/API 응답에 달려 있어 이 레포만으로 확정할 수 없다. 일치하지 않는 제공자는 재시도 없이 `Error:` 종료 경로로 간다.
- 조사 범위: `src/utils/errors.ts` 1-260행, `grep -rn "isContextOverflowError" src`(`agent.ts:11,176`, `errors.ts:155,210`, `utils/index.ts:23` export; 테스트 제외), `agent.ts:25-26,162-198,299-308,510-560`.

#### R1-Q11 답변
- 결론: **확정** — **그렇다**. 승인 콜백이 없어 자동으로 `deny`가 된 경우에도 사용자 거부와 **같은 `tool_denied` 이벤트**가 나가고, `agent.ts`가 `denied = true`로 처리해 루프 전체를 `answer: ''`로 끝낸다. cron/heartbeat/게이트웨이 경로는 승인 콜백을 **전혀 넘기지 않는다**.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/permissions/engine.ts:24,112-114` | `LEGACY_APPROVAL_TOOLS` | `new Set<string>(['write_file', 'edit_file'])` / `return { mode: 'ask', reason: 'This tool modifies files and needs your approval.' };` | 파일 쓰기는 항상 `ask` |
  | `src/agent/tool-executor.ts:153-163` | `executeSingleWithId` | `const decision = (await this.requestToolApproval?.({...})) ?? 'deny'; yield { type: 'tool_approval', ... approved: decision }; if (decision === 'deny') { yield { type: 'tool_denied', tool: toolName, args: toolArgs, toolCallId }; return; }` | 콜백이 `undefined`면 `'deny'` → 사용자 거부와 같은 이벤트 |
  | `src/agent/agent.ts:408-414` | `executeToolsAndCollectMessages` | `} else if (event.type === 'tool_denied' && event.toolCallId) { toolMessageMap.set(..., new ToolMessage({ content: 'Tool execution denied by user.', ...})); denied = true; }` | 이벤트 출처 구분 없음 |
  | `src/agent/agent.ts:245-257` | 종료 분기 | `if (denied) { ... yield { type: 'done', answer: '', toolCalls: ctx.scratchpad.getToolCallRecords(), ... }; return; }` | 루프 종료 |
  | `src/gateway/agent-runner.ts:59-72,85-94` | `AgentRunRequest`, `runAgentForMessage` | `Agent.create({ model: req.model, modelProvider: req.modelProvider, maxIterations: req.maxIterations ?? 10, signal: req.signal, channel: req.channel, groupContext: req.groupContext, memoryEnabled: !isolated, messageQueue: session?.queue })` | `requestToolApproval` 인자·필드 **없음** |
  | `src/cron/executor.ts:141-148` | cron 호출 | `answer = await runAgentForMessage({ sessionKey: ..., query, model, modelProvider, maxIterations: 6, isolatedSession: true, channel: 'whatsapp' });` | 승인 콜백 없음 |
  | `src/agent/agent.ts:29,85-88` | `CLI_ONLY_TOOLS` | `new Set<string>(['ask_user_question', 'bash'])` / `if (!isCli) { tools = tools.filter(t => !CLI_ONLY_TOOLS.has(t.name)); }` | `bash`는 제외되지만 `write_file`/`edit_file`은 비-CLI에도 남음(`registry.ts:113-126`) |
  | `src/cron/executor.ts:159-168`, `src/gateway/heartbeat/suppression.ts:62-67` | 억제 | `const suppResult = evaluateSuppression(answer, suppState);` / `if (!trimmed) { return { shouldSuppress: true, cleanedText: '', reason: 'empty' }; }` | 빈 답은 억제(`lastRunStatus = 'suppressed'`) |
  | `src/gateway/gateway.ts:172-179,186,204-205` | 인바운드 | `const answer = await runAgentForMessage({...});` / `if (answer.trim()) {...}` / `debugLog('[gateway] empty answer, not sending');` | 일반 WhatsApp 메시지도 빈 답이면 전송 안 함 |

- 동작 설명: 게이트웨이/cron 실행 중 LLM이 `write_file`(예: write-memo 스킬의 HTML 저장)이나 `edit_file`을 호출하면 `evaluatePermission`이 `ask`를 반환 → `requestToolApproval`이 `undefined`라 `?? 'deny'` → `tool_approval`(denied)과 `tool_denied` 이벤트가 나가고 해당 호출은 실행되지 않는다. `agent.ts`는 그 호출에 `'Tool execution denied by user.'` ToolMessage를 만들고 `denied = true`로 두며, 같은 라운드의 다른 도구 호출은 이미 실행된 결과를 ToolMessage에 넣은 뒤(`messages.push(...toolMessages)`, 243행) 곧바로 `done(answer: '')`로 끝낸다. LLM은 거부 결과를 보고 대안을 시도할 기회가 없다. cron은 `answer`가 빈 문자열이므로 `suppression.ts:65-67`에서 `reason: 'empty'`로 억제되어(`lastRunStatus = 'suppressed'`) WhatsApp 전송이 없고, 일반 인바운드는 `gateway.ts:204-205`에서 응답이 사라진다. 사용자는 거부된 사실도 듣지 못한다. (CLI에서는 승인 프롬프트가 떠서 사용자가 `deny`를 고르면 같은 종료 분기를 탄다.)
- 조사 범위: `grep -rn "requestToolApproval" src`(`agent/types.ts`, `agent/agent.ts`, `tool-executor.ts`, `controllers/agent-runner.ts`에만 있고 `gateway/`·`cron/` 하위에는 없음), `permissions/engine.ts:20-135`, `tool-executor.ts:131-172`, `agent.ts:224-257,396-428`, `gateway/agent-runner.ts` 전체, `cron/executor.ts:100-190`, `gateway.ts:156-206`. cron/게이트웨이에서 `write_file`을 막는 허용 목록 코드(`toolAllowlist` 전달)는 없다.

#### R1-Q12 답변
- 결론: **확정** — 보고서의 "10회를 다 쓰면 그동안의 조사 결과는 사용자에게 전달되지 않는다"는 **부분적으로만 맞다**(정정 필요). 최종 **답변(answer)** 은 고정 문구뿐이고 `DoneEvent.toolCalls`는 CLI UI가 **읽지 않는다**. 그러나 CLI 화면에는 이미 렌더된 도구 호출 행(요약 포함)과 `thinking` 텍스트(200자 절단)가 **그대로 남는다**(지워지지 않는다). 게이트웨이·cron 경로에서는 이 고정 문구가 그대로 전달 후보가 된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `src/agent/agent.ts:278-288` | 반복 소진 | ``answer: `Reached maximum iterations (${this.maxIterations}). I was unable to complete the research in the allotted steps.`, toolCalls: ctx.scratchpad.getToolCallRecords(),`` | `done`에 `toolCalls` 포함 |
  | `src/agent/types.ts:281-289` | `DoneEvent` | `toolCalls: Array<{ tool: string; args: Record<string, unknown>; result: string }>;` | 타입 |
  | `src/controllers/agent-runner.ts:351-362` | `done` 처리 | `if (done.answer) { await this.inMemoryChatHistory.saveAnswer(done.answer)...} this.updateLastItem((last) => ({ ...last, answer: done.answer, status: 'complete', duration: ..., tokenUsage: ..., tokensPerSecond: ... }));` | `toolCalls`는 사용 안 함, 기존 `events`는 `...last`로 유지 |
  | `src/controllers/agent-runner.ts:262-269` | `thinking` 처리 | ``this.pushEvent({ id: `thinking-${Date.now()}`, event, completed: true });`` | 도중 `thinking`이 `events`에 쌓임 |
  | `src/cli.ts:123-130` | `renderEvent` | `if (event.type === 'thinking') { ... new Text(message.length > 200 ? \`${message.slice(0, 200)}...\` : message, 0, 0)` | 화면 출력(200자 절단) |
  | `src/cli.ts:140-146` | `tool_start` 렌더 | `const component = chatLog.startTool(...); ... component.setComplete(summarizeToolResult(done.tool, toolStart.args, done.result), done.duration);` | 도구별 한 줄 요약 |
  | `src/cli.ts:285-286` | 완료 처리 | `if (lastItem.answer && !lastRenderedAnswer) { chatLog.finalizeAnswer(lastItem.answer);` | 고정 문구를 최종 답변으로 표시 |
  | `src/gateway/agent-runner.ts:96-101` | 게이트웨이 | `if (event.type === 'done') { finalAnswer = event.answer; }` | `toolCalls` 미사용 |
  | `src/evals/run.ts:39,133` | 평가 | `toolCalls: DoneEvent['toolCalls'];` / `toolCallCount: doneEvent.toolCalls.length,` | `toolCalls`를 읽는 유일한 곳(UI 아님) |

- 동작 설명: (1) 반복 한도(CLI는 `maxIterations: 10`, `cli.ts:232`; cron/heartbeat는 6, `executor.ts:146`)까지 최종 텍스트 응답이 없으면 `while` 루프를 빠져나와 위 고정 문구의 `done`이 나온다. (2) 컨트롤러는 진행 중 `tool_start`/`tool_end`/`thinking` 이벤트를 `HistoryItem.events`에 쌓고, `cli.ts`는 이벤트가 쌓이는 즉시 `renderEvent`로 채팅 로그에 추가한다. `done`에서는 `answer`/`status`만 덮어쓰므로 이미 그려진 도구 행과 thinking 문장은 사라지지 않는다. (3) `toolCalls`(결과 본문 전체)는 CLI의 어떤 UI도 읽지 않는다(`grep -rn "toolCalls" src`에서 컨트롤러·컴포넌트 사용 없음). 도구 결과 원문은 `.dexter/scratchpad/*.jsonl`에만 남는다(`scratchpad.ts:67,97`). (4) `saveAnswer(done.answer)`로 대화 기록에는 **고정 문구**가 저장되어 다음 턴 LLM 컨텍스트에도 도구 결과 대신 이 문구가 들어간다(`in-memory-chat-history.ts:81`). (5) 게이트웨이/cron: `finalAnswer`는 고정 문구다. 이 문구는 `HEARTBEAT_OK`도 아니고 `no action needed`류 패턴(`suppression.ts:43-49`)에도 걸리지 않아, cron/heartbeat에서는 **그 문구가 알림으로 WhatsApp 전송**된다(`executor.ts:174-178`).
- 조사 범위: `grep -rn "toolCalls" src`(`agent.ts`, `agent/types.ts`, `evals/run.ts`; `tools/finance/*`의 동명 지역변수는 무관), `controllers/agent-runner.ts:240-365`, `cli.ts:112-300`, `components/chat-log.ts`의 `finalizeAnswer`(286행), `gateway/agent-runner.ts`, `cron/executor.ts:140-190`.

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 없음 확정 | `formatters.ts:137`(`- Market Cap: ${fmtNum(d.market_cap)}`)과 `screen-stocks.ts:161-166`(응답 무가공 `formatToolResult(data, [url])`), `get-financials.ts:98`(존재하지 않는 `get_financial_metrics_snapshot` 안내)을 열어 일치 확인. 섹터·산업 출력 경로 없음은 grep 패턴(`company/facts`, `company_facts`, `companyFacts`, `sector`, `industry`, `market_?cap`)과 범위가 충분함. 스크리너 응답 필드는 외부 API 응답 의존이며 정적 부분(무가공 통과)은 확정되어 허용 |
| R1-Q2 | 해소 | `get-financials.ts:201-204` formatter 조회 분기, `formatters.ts:416-438` 두 레지스트리(8개/10개), `get-market-data.ts:68-87` 12개 목록, `stock-price.ts:72`·`crypto.ts:65` 미등록 이름을 열어 확인. 완료 조건(호출 지점·분기·등록/미등록 목록) 충족 |
| R1-Q3 | 해소 | `stock-price.ts:63-66`(`new Date(input.end_date + 'T00:00:00')`, `today.setHours(0, 0, 0, 0)`, `cacheable: endDate < today`)과 `cache.ts:153-158`(`ttlMs` 없으면 만료 검사 생략) 확인. 로컬 시간대 기준임이 코드로 확정 |
| R1-Q4 | 해소 | `grep -rn startCronRunner src` 재실행 결과 정의(`runner.ts:24`)와 호출(`gateway.ts:231`) 외 없음 확인. CLI 미시작 확정 |
| R1-Q5 | 해소 | `config.ts:32`(`.default(10)`), `config.ts:149`(`GatewayConfigSchema.parse` 결과가 `parsed`이므로 160행 `?? 30` 도달 불가), `heartbeat-migration.ts:21,24,30-34`, `heartbeat-tool.ts:48-81`(`gateway.json`만 저장, 작업 없으면 `return`, `schedule` 불변) 확인. 경우별 `every` 값과 이름 기준 식별 모두 확정 |
| R1-Q6 | 해소 | `store.ts:31-47`(임시파일 + `renameSync`, 잠금 없음), `gateway.ts:230-231`(await 없음), `runner.ts:30-71`(조건부 시작 쓰기, tick 스냅샷), `executor.ts:191,222,254` 저장 지점 확인. 결론 "덮어쓰기 가능"은 정적으로 확정되고, 타이머·I/O 선후만 런타임 의존이라 허용 |
| R1-Q7 | 해소 | `model-selection.ts:49-52`, `llm.ts:18-19`, `utils/model.ts:15-17,52-55`, `cli.ts:232`, `agent.ts:23,58,78` 확인. `gpt-6-astra` 최종값과 `gpt-5.6-sol` 미사용이 단계별로 확정 |
| R1-Q8 | 해소 | `scratchpad.ts:131-171`(검사 순서·연산자 `>=`, `=== maxCalls - 1`), `scratchpad.ts:197-238`(요약은 호출된 모든 도구를 필터 없이 출력, `callCount >= maxCalls`면 over 표기), `tool-executor.ts:174-178,212-221`, `cli.ts:169`, `agent.ts:393-414`(ToolMessage는 `tool_end`/`tool_error`/`tool_denied`만) 확인. 회차별 표가 코드와 일치하며 `tool_limit`이 LLM에 가지 않음도 확정 |
| R1-Q9 | 해소 | `scratchpad.ts:147-149`(`this.toolQueries.get(toolName)`), `scratchpad.ts:245-258`(전체 순회 `>=` 임계값), `scratchpad.ts:186-190`(저장), `tool-executor.ts:225-233`(질의 키 6개) 확인 |
| R1-Q10 | 해소 | `errors.ts:155-185` 판별 순서 전문과 `agent.ts:176-196` 호출·종료 분기 확인. 판별 기준은 코드로 확정되었고, 제공자별 실제 메시지 일치 여부만 외부 응답 의존으로 정당하게 분리됨 |
| R1-Q11 | 해소 | `tool-executor.ts:153-162`(`?? 'deny'` → `tool_denied`), `agent.ts:408-414`(출처 구분 없이 `denied = true`), `agent.ts:245-257`(`answer: ''` 종료), `gateway/agent-runner.ts:85-94`(승인 콜백 없음), `executor.ts:141-148`, `suppression.ts:65-67` 확인 |
| R1-Q12 | 해소 | `agent.ts:279-288` 고정 문구, `controllers/agent-runner.ts:351-362`(`...last` 유지, `toolCalls` 미사용), `gateway/agent-runner.ts:96-101`, `executor.ts:157-180` 확인. CLI 화면 잔존 여부라는 완료 조건 충족. 단 `suppression.ts:87-94`의 24시간 중복 억제(`reason: 'duplicate'`)로 같은 고정 문구가 24시간 안에 다시 나오면 두 번째부터는 전송되지 않는다는 점이 답변에서 빠져 있어 보고서 반영 시 함께 적는다 |

새 질문 없음. 답변의 추가 발견(`get_financial_metrics_snapshot` 미존재, `get_stock_price` 시총 미출력, 24시간 중복 억제)은 모두 코드로 확정된 사실이라 재질문 없이 보고서 반영 목록에 넣는다.

---

## 최종 정리 (질문자)

- 총 라운드: 1 / 총 질문: 12 / 해소 11 · 없음 확정 1 · 정적 확인 불가 0
- 이 레포를 이해하는 데 핵심인 확정 사실:
  1. 섹터·산업("company facts")을 LLM에 주는 도구는 없다. 시가총액은 `get_key_ratios` formatter만 출력한다(`formatters.ts:137`). DCF 스킬의 `"[TICKER] company facts"` 요청은 코드 경로로 충족되지 않는다(`get-financials.ts:60-73`).
  2. 금융 메타툴은 하위 도구 결과를 레지스트리 formatter로 마크다운 문자열화하고, 미등록 도구(티커 목록 2개)만 원본 JSON 배열로 넣는다(`get-financials.ts:201-204`, `get-market-data.ts:224-227`, `formatters.ts:416-438`).
  3. 이력 가격 영구 캐시의 "오늘"은 실행 머신 **로컬 자정** 기준이며 캐시 항목에 TTL이 없다(`stock-price.ts:63-66`, `cache.ts:153-158`).
  4. cron 러너는 게이트웨이 프로세스에서만 시작된다(`gateway.ts:231` 유일). CLI는 작업을 쓸 수만 있고 실행하지 않는다.
  5. heartbeat 기본 주기는 모든 경로에서 **10분**이며(`config.ts:32`), `heartbeat` 도구는 cron 작업을 만들거나 주기를 바꾸지 않는다. 작업 생성·주기 반영은 게이트웨이 시작 시 `ensureHeartbeatCronJob`뿐이다(`heartbeat-migration.ts:30-34`, `heartbeat-tool.ts:66-81`).
  6. `jobs.json`은 잠금 없는 전체 덮어쓰기라 동시 쓰기 시 작업 유실·`nextRunAtMs` 되돌림이 가능하다(`store.ts:31-47`, `executor.ts:222,254`).
  7. 설정 없는 CLI 첫 실행의 메인 루프·라우터 모델은 `gpt-6-astra`이고 `agent.ts:23`의 `gpt-5.6-sol`은 쓰이지 않는다(`model-selection.ts:49-52`, `cli.ts:232`).
  8. 도구 호출 한도·유사 질의 경고(`canCallTool`)는 UI 이벤트로만 나가 LLM에 전달되지 않으며, LLM은 매 라운드 끝의 "Tool Usage This Query" 요약만 본다(`cli.ts:169`, `agent.ts:265-268`, `scratchpad.ts:230-238`). 호출은 결코 차단되지 않는다.
  9. 컨텍스트 초과 판별은 오류 메시지 문자열 매칭뿐이고 `tpm` 포함 시 제외된다(`errors.ts:155-185`).
  10. 게이트웨이·cron 실행에서 `write_file`/`edit_file` 호출은 자동 deny되어 루프 전체가 `answer: ''`로 끝나고 빈 답은 억제되어 아무것도 전송되지 않는다(`tool-executor.ts:153-162`, `agent.ts:245-257`, `suppression.ts:65-67`).
  11. 반복 상한 소진 시 최종 답은 고정 문구뿐이고 `toolCalls`는 UI가 읽지 않지만, CLI에 이미 그려진 도구 행·thinking은 남는다. cron에서는 그 고정 문구가 WhatsApp으로 전송된다(24시간 내 동일 문구 재발은 중복 억제)(`agent.ts:279-288`, `controllers/agent-runner.ts:351-362`, `suppression.ts:87-94`).

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `01-data.md` Q1 "정의만 있고 쓰이지 않는 것" 표, `next.md` 분석 중 생긴 질문 1번·미확인 체크리스트 마지막 항목 | company facts 도구 부재 영향이 `추론` | `없음 확정`으로 올리고, 시총은 `get_key_ratios`(`formatters.ts:137`)에서만 나오며 섹터·산업은 어떤 도구도 출력하지 않음, DCF 스킬 요구가 코드로 충족되지 않음을 명시. 미확인 항목 삭제 | R1-Q1 |
| `01-data.md` (금융 라우터 프롬프트 관련 서술) | 언급 없음 | `get-financials.ts:98` 라우터 프롬프트가 존재하지 않는 `get_financial_metrics_snapshot`을 안내하고(호출 시 `Tool ... not found`가 `_errors`로), 99행은 `get_key_ratios`를 이력용으로 잘못 설명함을 추가. `get-market-data.ts` 프롬프트의 "(price, market cap, volume)"과 달리 `formatStockPrice`는 가격·등락률만 출력함도 추가 | R1-Q1 |
| `01-data.md` 2.3절, `03-decision.md` 4-1절, `next.md` 다음에 볼 파일 첫 항목 | formatter로 마크다운 표 압축(호출 지점·미등록 도구 형태 미기재) | 호출 지점 `get-financials.ts:201-204`·`get-market-data.ts:224-227`, 등록 18개(금융 8·시장 10), 미등록은 `get_available_stock_tickers`·`get_available_crypto_tickers`뿐이며 원본 배열이 JSON 안에 중첩됨. 내부자·13F·뉴스는 등록되어 있음. 해당 next 항목 삭제 | R1-Q2 |
| `01-data.md` 2.4절 | `end_date`가 오늘 이전일 때만 영구 캐시 | "오늘"은 실행 머신 로컬 자정 기준(`stock-price.ts:63-65`). KST 등 미국보다 앞선 시간대에서는 미국 장중의 D-1 데이터도 영구 캐시될 수 있고 장 마감·봉 완성 검사는 없음을 추가 | R1-Q3 |
| `02-schedule.md` 3.1절 | 트리거 나열만, 러너 시작 주체 미기재 | cron 러너는 `gateway.ts:231`에서만 시작. CLI(`bun run start`)는 작업을 쓸 수만 있고 실행하지 않으며 정기 실행은 게이트웨이 프로세스(`bun run gateway`)에서만 가능 | R1-Q4 |
| `02-schedule.md` 3.2절 | 설정 파싱 기본 30분 vs 도구 활성화 기본 10분(불일치) | 정정: 스키마 기본값 10분(`config.ts:32`) 때문에 두 `?? 30`은 도달 불가, 실제 기본값은 모든 경로에서 10분. `heartbeat` 도구는 `gateway.json`만 쓰고 cron 작업을 만들거나 주기를 바꾸지 않음. 작업 생성·주기 반영은 다음 게이트웨이 시작 시에만 일어남 | R1-Q5 |
| `02-schedule.md` 3.4절 | `await` 없는 `ensureHeartbeatCronJob()` 영향은 작을 것(추론) | 확정: `jobs.json`은 잠금 없는 전체 덮어쓰기(`store.ts:31-47`)라 덮어쓰기 가능. 더 큰 위험은 tick 스냅샷을 에이전트 실행 뒤 저장하는 `executor.ts:222,254`로, 실행 중 추가된 작업이 유실되거나 `nextRunAtMs`가 되돌아갈 수 있음 | R1-Q6 |
| `00-overview.md` 1절, `next.md` README 차이 표, `03-decision.md` 4-2 모델 계층 표 | 기본 모델 3개 값 병기, 메인 모델은 "사용자가 고른 모델" | 설정 없는 첫 실행의 메인 루프·메타툴 라우터·게이트웨이 기본 모델은 `gpt-6-astra`(`model-selection.ts:49-52`, `utils/model.ts:15-17`). `agent.ts:23` `gpt-5.6-sol`은 미사용 상수, `AGENTS.md:49` `gpt-5.5`는 저장값 승급 대상일 뿐 | R1-Q7 |
| `03-decision.md` 4-2 루프 방지 표, `04-research.md` 5-3절 | 3회째부터 suggested limit 경고, 1회 남음 경고, Jaccard ≥ 0.7이면 경고 | 정정: `canCallTool` 경고(3회째 "approaching", 4회째부터 "suggested limit", 유사 질의)는 `tool_limit` UI 이벤트로만 나가고 CLI도 그리지 않으며 LLM에 전달되지 않음(`cli.ts:169`). LLM은 라운드 끝 "Tool Usage This Query" 요약만 받고 3번째 호출 뒤부터 "over suggested limit"으로 표기됨. 유사 질의는 같은 도구 이름의 이번 실행 내 과거 질의 전체와 비교(`scratchpad.ts:147-149`). 호출 차단은 없음 | R1-Q8, R1-Q9 |
| `03-decision.md` 4-2 종료 조건 표, `next.md` 미확인 체크리스트·다음에 볼 파일 | `isContextOverflowError` 기준 미확인 | 판별은 메시지 문자열만 사용(`errors.ts:155-185`): `tpm`/`tokens per minute` 포함 시 제외, 영문 10개·중국어 3개 패턴과 4개 조합 조건. 불일치 제공자는 재시도 없이 `Error:` 종료. 해당 미확인 항목 삭제 | R1-Q10 |
| `03-decision.md` 4-5 표·4-2 종료 조건 표, `05-boundary-and-fit.md` Q6 표 | 승인 콜백 없으면 deny / 사용자 거부 시 즉시 종료(별개 서술) | 둘을 연결: 게이트웨이·cron 경로는 승인 콜백을 넘기지 않아(`gateway/agent-runner.ts:85-94`) `write_file`/`edit_file` 호출 시 자동 deny → `tool_denied` → 루프 전체가 `answer: ''`로 종료되고 빈 답은 억제되어 아무것도 전송되지 않음. 무인 실행에서 write-memo 등 파일 저장 스킬은 동작 불가 | R1-Q11 |
| `04-research.md` 5-6절 | 10회를 다 쓰면 조사 결과는 사용자에게 전달되지 않음 | 부분 정정: 최종 답은 고정 문구이고 `toolCalls`는 UI가 읽지 않지만 CLI에 이미 그려진 도구 행·thinking(200자 절단)은 남음. 대화 기록에는 고정 문구가 저장됨. cron/heartbeat(상한 6회)에서는 고정 문구가 WhatsApp으로 전송되며, 24시간 안에 같은 문구가 반복되면 중복 억제(`suppression.ts:87-94`)로 두 번째부터 전송되지 않음 | R1-Q12 |
