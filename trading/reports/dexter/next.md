# dexter — 확인 범위와 다음 작업

- 분석 SHA: `534f6be455523c5926eba72bdaf4f914555be5c9` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: 전체
- 검증 수준 요약: 해당 없음(메모 문서)

## 확인한 범위 (직접 열어 본 파일)

- 에이전트 코어: `src/agent/agent.ts`(전체), `scratchpad.ts`(전체), `tool-executor.ts`(전체), `prompts.ts`(전체), `channels.ts`, `compact.ts`, `microcompact.ts`, `run-context.ts`, `types.ts`(일부)
- 도구: `src/tools/registry.ts`, `finance/` (`api.ts`, `get-financials.ts`, `get-market-data.ts`, `read-filings.ts`, `screen-stocks.ts`, `stock-price.ts`, `crypto.ts`, `key-ratios.ts`, `news.ts`, `earnings.ts`, `fundamentals.ts`(일부), `filings.ts`(일부), `insider_trades.ts`(일부), `utils.ts`, `formatters.ts`(레지스트리 부분)), `search/`(전체), `fetch/web-fetch.ts`, `fetch/prompt.ts`, `fetch/utils.ts`(상수·요약부), `subagent/`(전체), `skill.ts`, `cron-tool.ts`·`heartbeat-tool.ts`(일부)
- 모델/유틸: `model/llm.ts`, `providers.ts`, `utils/cache.ts`, `tokens.ts`, `tool-result-budget.ts`, `in-memory-chat-history.ts`
- 스킬: `skills/registry.ts`, `dcf/SKILL.md`, `dcf/sector-wacc.md`, `write-memo/SKILL.md`(+template 슬롯, style 일부), `x-research/SKILL.md`
- 스케줄: `cron/`(`executor.ts`, `runner.ts`, `schedule.ts`, `types.ts`, `store.ts` 일부, `heartbeat-migration.ts`), `gateway/heartbeat/`, `gateway/gateway.ts`, `gateway/agent-runner.ts`
- 기타: `memory/`(`index.ts`, `search.ts`, `flush.ts`, `store.ts` 일부, `embeddings.ts` 일부), `permissions/engine.ts`, `evals/evaluator.ts`, `evals/run.ts`(일부), `README.md`, `AGENTS.md`, `SOUL.md`, `env.example`, `package.json`

## 미확인 항목 체크리스트

- [ ] `src/tools/finance/` 중 `segments.ts`, `insider_ownership.ts`, `institutional_holdings.ts`, `beneficial_ownership.ts`의 입력 스키마 전체(엔드포인트·TTL만 확인함)
- [ ] `src/tools/browser/browser.ts` 후반부(액션 구현·스냅샷 길이 제한 세부)
- [ ] `src/tools/ask-user-question/`, `src/tools/filesystem/*`(읽기/쓰기/편집 도구의 경로 제한)
- [ ] `src/permissions/rules.ts`·`command-parser.ts`의 기본 규칙 내용(엔진 흐름만 확인)
- [ ] `src/utils/errors.ts`의 `isContextOverflowError`/`classifyError` 판별 기준
- [ ] `src/memory/database.ts`, `indexer.ts`, `chunker.ts`, `mmr.ts`, `temporal-decay.ts` 내부 계산(기본값만 확인)
- [ ] `src/gateway/` 나머지(WhatsApp 채널, 접근 제어) — 알림 범위 밖이라 의도적으로 제외
- [ ] `src/evals/dataset/finance_agent.csv` 규모·문항 유형 분포(루브릭 형식만 확인)
- [ ] 실행 확인 전부(설치·실행 금지 제약). 모든 동작 서술은 코드 열람 기준
- [ ] Financial Datasets API의 실제 응답 필드·커버리지(`company facts`·KPI 엔드포인트 존재 여부는 코드에서 호출하지 않아 미확인)

## 다음에 볼 파일·함수

- `src/tools/finance/formatters.ts` 각 `format*()`: 어떤 필드가 LLM에 노출되고 버려지는지(Q1 필드 단위 보강)
- `src/utils/errors.ts` `isContextOverflowError()`: 컨텍스트 초과 재시도 판별이 제공자별로 맞는지
- `src/permissions/rules.ts` `builtinDeny()`: 비밀/환경변수 읽기 차단 기준
- `src/cron/executor.ts` `executeCronJob()` 5~7단계: 전달부를 분리해 "리서치만 정기 실행"하게 바꾸는 최소 변경 지점
- `src/tools/filesystem/read-file.ts`: 디스크 오프로딩된 도구 결과를 다시 읽는 경로와 제한

## 분석 중 생긴 질문

1. `get_financials`가 "company facts"(섹터·시총 등)를 요구받을 때 실제로 어떤 도구가 선택되는가? 라우터 프롬프트와 도구 목록이 어긋나 있어(`get-financials.ts:20,60-73,98`) DCF 스킬 1.5단계가 조용히 실패할 가능성이 있으나, 실행 확인 없이는 추론에 그친다.
2. `WEB_SEARCH_DESCRIPTION`의 "When to Use" 첫 항목(`search/index.ts:10`)은 오탈자인가 의도인가? LLM의 도구 선택에 영향을 주는지 알 수 없다.
3. `gateway.heartbeat.maxIterations` 설정이 cron 실행기에서 무시되는 것(`cron/executor.ts:146`)이 의도된 단순화인지 버그인지.
4. 반복 소진 시 조사 결과를 버리는 설계(`agent.ts:278-288`)는 의도된 안전장치인가, 단순 미구현인가.
5. LICENSE 파일이 없는 상태에서 README의 MIT 선언은 법적으로 충분한가(분석 범위 밖, 사용자 판단 필요).

## README와 코드가 다른 곳 (기록)

| README/문서 | 코드 | 위치 |
|---|---|---|
| 작업 계획·자기성찰·자기검증 기능 | 별도 플래너·리플렉션 모듈 없음, 단일 ReAct 루프 | `README.md:3,37-39` vs `agent/agent.ts:149-289` |
| "Final answer: generated in a separate LLM call with full scratchpad context (no tools bound)" | 최종 답은 도구 호출이 없는 일반 루프 응답이며 별도 호출이 없음 | `AGENTS.md:76` vs `agent.ts:215-218` |
| 스크래치패드 entry에 `llmSummary` | 해당 필드 없음 | `README.md:157` vs `scratchpad.ts:15-24` |
| 기본 모델 `gpt-5.5` | `gpt-5.6-sol`(agent), `gpt-6-astra`(llm/cron/gateway) | `AGENTS.md:49` vs `agent.ts:23`, `llm.ts:19` |
| 검색: Exa 우선·Tavily 폴백 | Exa/Perplexity/Tavily/LangSearch 4종 체인 | `AGENTS.md:17,59` vs `registry.ts:164-196` |
| `AGENTS.md`의 도구 `financial_search`, `financial_metrics`, `src/tools/descriptions/` | 해당 이름/디렉터리 없음(현재는 `get_financials` 등) | `AGENTS.md:15,56-57` vs `registry.ts:48-162` |
| `AGENTS.md`의 `src/cli.tsx` | 파일은 `src/cli.ts` | `AGENTS.md:10` vs `git ls-files` |
| `AGENTS.md`의 `FAST_MODELS` 맵(`llm.ts`) | `providers.ts`의 `fastModel` 필드로 이동 | `AGENTS.md:50` vs `providers.ts:16` |
| README 라이선스 MIT | LICENSE 파일 없음 | `README.md:192` |
