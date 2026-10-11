# 실시간 리서치 비교 (Q5)

- 작성일: 2026-10-09
- 기준: 각 레포 `reports/<repo>/04-research.md` (SHA는 `../repos.lock.tsv`)

## 1. 판단 중에 외부 자료를 찾아보는가

| 레포 | 실시간 리서치 | 제공자 | 검색어를 누가 만드나 | 종료 조건 |
|---|---|---|---|---|
| TradingAgents | △ 웹 검색 없음. 고정 글로벌 뉴스 검색어 5개 + LLM이 FRED 지표명·Polymarket 주제 선택 | yfinance, FRED, Polymarket | 고정 + LLM | 도구 라운드 20회, 넘으면 WRAP_UP 강제 |
| TradingAgents-CN | 종목 분석에는 없음. 어시스턴트에만 있음 | SearXNG, 바이두, DashScope, `fetch_url` | LLM | — |
| ai-hedge-fund | ❌ | — | — | — |
| daily_stock_analysis | ✅ **판단 전에** 고정 템플릿으로 검색 | Anspire, Bocha, Tavily, Brave, SerpAPI, MiniMax, SearXNG | **코드 (고정 템플릿)** | 최대 5회 (Agent 모드 6회) |
| Vibe-Trading | ✅ LLM이 자유롭게 호출 | 웹 검색 (IQS → ddgs → sogou/bing), Jina Reader | LLM | 같은 호출 2회 실패 시 차단, 반복 상한 50 |
| OpenAlice | △ 웹 검색 도구 없음. 구독 RSS를 정규식으로 조회 | RSS 28개 | LLM (정규식) | 코드 상한 없음, timeout만 |
| dexter | ✅ **핵심 기능** | Exa → Perplexity → Tavily → LangSearch, X API, 웹페이지, Playwright | LLM | 반복 10회. 루프 방지(도구당 3회, 유사도 0.7)는 경고만 |
| QuantDinger | △ 분석에는 없음 (뉴스 5건 미만이면 고정 검색 1회). 채팅 `research_agent`에만 있음 | Tavily, SerpAPI, Google, Bing, DDG | LLM | 3라운드, 10회 호출, 55초 |

## 2. 신뢰성 장치

| 장치 | 레포 |
|---|---|
| 숫자는 도구 결과에서만 가져온다 (프롬프트 규칙) | OA, VT, DX, CN |
| 숫자를 선언하게 한 뒤 코드가 대조하고 위반 수치를 삭제 | VT (`figures` 블록 + grounding 게이트) |
| 모든 주장에 evidence ID를 인용, 모르는 ID는 제거 | QD (단, 결정에는 영향 없음) |
| 반복 검색 경고 / 차단 | DX (경고), VT (차단) |
| 프롬프트 인젝션 경고 메타 | VT |
| 임의 URL 차단, 도메인 화이트리스트 | QD |

## 3. 패턴 정리

| 패턴 | 레포 | 특징 |
|---|---|---|
| **판단 전 고정 검색** | DSA | 재현 가능, 비용 예측 가능, 검색 차원 고정 (최신 뉴스, 애널리스트, 리스크, 실적, 업종) |
| **LLM 자유 검색 루프** | DX, VT | 유연하지만 비용과 결과가 매번 다름 |
| **구독형 수집 후 조회** | OA (RSS) | 외부 API 키 불필요, 소스가 정해져 있음 |
| **리서치는 채팅에만** | QD, CN | 매매 판단과 분리 |

## 4. 우리 시스템에 대한 결론 (의견)

- **매매 판단 경로**에는 DSA처럼 **판단 전에 고정 템플릿으로 검색**한다. 종목당 최대 3~5회로 제한하고, 검색 차원을 코드에서 정한다.
- **자유 리서치**는 dexter처럼 별도 "질문 모드"로 분리하고, 판단 경로에는 섞지 않는다.
- **숫자 검증**은 VT 방식(LLM이 쓴 숫자를 수집 데이터와 대조)을 최소 버전으로 도입한다.
- **한국 뉴스**를 다루는 레포는 8개 중 하나도 없다. 한국어 뉴스 소스는 직접 정해야 한다. 후보는 검색 API, 언론사 RSS, DART 공시 RSS다.
