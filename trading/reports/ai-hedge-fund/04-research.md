# ai-hedge-fund — 실시간 리서치

- 분석 SHA: `78b779c1389e2d1452dc29606d2c4126d859b964` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q5
- 검증 수준 요약: 코드 확인 12 / 추론 0 / 미확인 0

## Q5. 실시간 리서치 {#q5}

**결론: 없음.** 판단 도중 웹 검색, 뉴스 검색, 웹 페이지 읽기, 공시 조회를 하는 코드가 이 SHA에 없다. 에이전트는 사전에 수집된 단일 스냅샷 텍스트를 1회 읽고 JSON 한 개를 내놓는다.

### 찾아본 곳과 결과 (없다는 근거)

| 확인 대상 | 방법 | 결과 | 근거 | 검증 |
|---|---|---|---|---|
| 에이전트 호출 방식 | `LLMClient.complete(system, user) -> str` 한 번 호출이 전부. 도구 바인딩/툴 호출/ReAct 루프 없음. 설계 의도로 langchain 구조화 출력·도구 모드도 쓰지 않는다고 명시 | `hedge_fund/llm/client.py:1-11`, `client.py:55-68`, `hedge_fund/signals/llm_agent.py:92-93` | 코드 확인 |
| 검색 제공자 | `tavily`, `serp`, `duckduckgo`, `search`, `exa`, `rss`, `websocket`, `urllib`, `httpx`, `bs4` 등으로 `hedge_fund/` 전체 grep(`.py`) | 외부 요청은 FD API, TypeSafe(Jev) 엔드포인트, Ken French 분위 CSV, LLM 공급자뿐. 검색·웹 읽기 호출 없음 | `hedge_fund/data/client.py:45`, `hedge_fund/llm/client.py:114`, `hedge_fund/features/breakpoints.py:32-36` | 코드 확인 |
| 뉴스 | FD `get_news()`는 정의·캐시 래퍼만 있고 어떤 에이전트도 호출하지 않음 | `hedge_fund/data/client.py:126-138`, `hedge_fund/data/cached.py:73-78` | 코드 확인 |
| 공시(SEC) | `Filing` 모델만 정의, 조회 메서드 없음. 공시는 FD의 가공된 재무지표/실적으로만 간접 소비 | `hedge_fund/data/models.py:262-275`, `hedge_fund/data/protocol.py:33-88` | 코드 확인 |
| 로드맵 | "Alternative data connectors — ... web & social-media search ..."는 **미구현(⬜)** | `ROADMAP.md:120` | 코드 확인 |
| 환경 변수 | `.env.example`에 검색 API 키 없음(FD + LLM 공급자 키뿐) | `.env.example:5-38` | 코드 확인 |

### 질문 항목별 답

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 판단 중 웹/뉴스/공시 조회를 하는가 | 아니오 | 위 표 | 코드 확인 |
| 제공자/키 | 해당 없음 | - | 코드 확인 |
| 검색어는 고정인가 LLM이 만드는가 | 해당 없음(LLM이 외부를 호출할 수단이 없음) | `llm/client.py:55-68` | 코드 확인 |
| 결과 처리(요약, 잘라내기, 출처 표기) | 해당 없음. 대신 **입력 쪽 통제**: "Reason ONLY from the data provided ... Do not invent numbers."를 모든 페르소나에 명시 | `signals/buffett.py:48-52` 외 | 코드 확인 |
| 신뢰성 장치 | 숫자는 코드가 계산(`gross_margin_trend`, `bvps_cagr`, `eps_growth_yoy`)해서 넣어 LLM이 산술하지 않게 함. 사후 지식 차단용 blind 렌더. 출력이 JSON 스키마가 아니면 기권 | `features/snapshot.py:3-7`, `snapshot.py:95-105`, `llm_agent.py:147-165` | 코드 확인 |
| 루프 종료 조건 | 루프 없음(에이전트당 호출 1회) | `llm_agent.py:92-93` | 코드 확인 |

### 시사점 (의견)

- 이 레포는 "리서치 에이전트"가 아니라 "스냅샷 → 의견" 채점기다. 뉴스·공시 본문 같은 비정형 근거는 설계상 입력에 포함되지 않는다.
- 뉴스/감성 판단이 필요하면 `DataClient` Protocol에 메서드를 추가하고 `LLMAgent.build_snapshot()`을 오버라이드하라는 확장 지점이 docstring에 있다(`signals/llm_agent.py:125-137`: "Override for personas that reason over different data (macro, news)"). 이 가이드는 우리 시스템 설계 의견이므로 `05-boundary-and-fit.md`에 이어서 정리한다.
