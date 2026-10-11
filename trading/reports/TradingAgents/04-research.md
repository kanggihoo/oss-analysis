# TradingAgents — 실시간 리서치

- 분석 SHA: `1394a3f72aa4393e1a98f51b382434c4b4c2d972` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q5
- 검증 수준 요약: 코드 확인 38 / 추론 0 / 미확인 0

<a id="q5"></a>
## Q5. 실시간 리서치

**요약: 자유 웹 검색·페이지 읽기·공시 검색 에이전트는 없다.** 판단 도중 LLM이 부를 수 있는 것은 정해진 데이터 도구 12개(`tools.py`)뿐이고, 그중 검색어를 LLM이 직접 쓰는 도구는 2개(`get_macro_indicators`의 지표명, `get_prediction_markets`의 topic)다. 결정 단계(Research Manager, Trader, PM)는 의도적으로 도구 호출을 금지당한다.

### Q5-1. 판단 도중 외부 조회 여부

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 웹 검색(Tavily, SerpAPI, Exa, DDG 등) | **없음**. 의존성 목록에 검색 라이브러리 없음, 코드에 해당 호출 없음 | `pyproject.toml:11-29`(의존성), `tradingagents/` 전반 | 코드 확인(부재) |
| 웹 페이지 읽기·스크래핑 | 없음. 뉴스는 제목·요약·링크만 사용하고 링크를 따라가지 않음 | `yahoo/news.py:75-84` | 코드 확인(부재) |
| 공시 조회 | SEC EDGAR 재무 **팩트** 조회만(10-K/10-Q 본문·8-K 검색 없음). 도구가 아니라 `get_balance_sheet` 등의 벤더 내부 구현 | `sec_edgar.py:36-37,190-237` | 코드 확인 |
| 뉴스 검색 | Yahoo Finance 뉴스(종목)와 `yf.Search`(글로벌) | `yahoo/news.py:57-201` | 코드 확인 |
| 결정 단계의 도구 사용 | **금지**: Research Manager·Trader·PM 프롬프트에 "Use only the evidence provided in this prompt. Do not call external tools or search the web; if something is missing, say so explicitly." | `agents/structured.py:36-39`, `research_manager.py:51`, `trader.py:60`, `portfolio_manager.py:76` | 코드 확인 |
| 토론 단계(불/베어/리스크) | 도구 바인딩 없음(`llm.invoke(prompt)`만) | `bull_researcher.py:51`, `aggressive_debator.py:48` | 코드 확인 |

번역(`NO_EXTERNAL_TOOLS`): "이 프롬프트에 제공된 근거만 사용하라. 외부 도구를 호출하거나 웹을 검색하지 말라. 없는 것은 없다고 명시하라."

### Q5-2. 제공자와 키

| 제공자 | 용도 | 키 | 근거 | 검증 |
|---|---|---|---|---|
| Yahoo Finance (yfinance) | 종목 뉴스, 글로벌 뉴스 검색 | 불필요 | `yahoo/news.py:57-201` | 코드 확인 |
| FRED | 거시 시계열 | `FRED_API_KEY` | `fred.py:102-110` | 코드 확인 |
| Polymarket Gamma | 예측시장 | 불필요 | `polymarket.py:22-36,96` | 코드 확인 |
| Alpha Vantage News | 대체 뉴스(옵트인) | `ALPHA_VANTAGE_API_KEY` | `router.py:129-136` | 코드 확인 |
| StockTwits / Reddit RSS | 소셜(사전 수집, 검색 에이전트 아님) | 불필요 | `stocktwits.py:30`, `reddit.py:68` | 코드 확인 |
| TypeSafe Jev | 소셜 게시글 관련도·입장 분류 | `TYPESAFE_API_KEY`(선택) | `post_screen.py:133-141` | 코드 확인 |

### Q5-3. 호출 방식: 검색어는 누가 만드는가

| 도구 | 검색어/인자 생성 주체 | 규모 | 근거 | 검증 |
|---|---|---|---|---|
| `get_stock_data(start, end)` | LLM이 날짜만 정함. 심볼은 상태에서 주입(`InjectedState`)되어 LLM이 바꿀 수 없음 | - | `tools.py:18-38` | 코드 확인 |
| `get_indicators(indicator, curr_date, look_back_days=30)` | LLM이 지표명·기간 선택(프롬프트가 12종 목록을 제시) | 지표당 1회 호출 안내 | `tools.py:41-69`, `market_analyst.py:22-46` | 코드 확인 |
| `get_news(start, end)` | LLM이 날짜 윈도 선택. 심볼은 주입 | - | `tools.py:171-191` | 코드 확인 |
| `get_global_news(curr_date, look_back_days, limit)` | **고정 검색어 5개**를 코드가 순회(LLM은 개수·기간만 조절). 기본 7일·10건 | 5개 검색어 | `default_config.py:142-152`, `yahoo/news.py:155-191` | 코드 확인 |
| `get_macro_indicators(indicator, ...)` | **LLM이 지표명 작성**(별칭 40여 개 또는 원시 FRED ID). 잘못된 값은 안내 문구로 반환 | 호출 횟수는 LLM 재량(라운드 상한 내) | `tools.py:232-264`, `fred.py:113-133,206-212` | 코드 확인 |
| `get_prediction_markets(topic, limit)` | **LLM이 topic 자유 작성**(예: "Fed rate cut", "recession 2026") | 검색당 최대 20개 후보 → 거래량 상위 6건 | `tools.py:267-291`, `polymarket.py:96,111,128` | 코드 확인 |
| 재무제표·개요·내부자 | 인자는 빈도(`annual/quarterly`)와 날짜뿐 | - | `tools.py:97-229` | 코드 확인 |

- **몇 차원에서 몇 번 검색하는가**: 코드가 정한 고정 쿼터는 없다. 도구 사용은 분석가별 최대 20라운드(`default_config.py:137`)이며 라운드당 병렬 호출은 모델 재량이다. 분석가별 도구 수: Market 3, News 4, Fundamentals 5(`market_analyst.py:8-12`, `news_analyst.py:13-18`, `fundamentals_analyst.py:14-20`). 코드 확인.
- Sentiment Analyst는 도구 없이 3원천을 **고정 쿼리**(티커, 최근 7일)로 한 번 가져온다(`sentiment_analyst.py:60-76`). 코드 확인.

### Q5-4. 결과 처리

| 처리 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 요약 | 도구는 요약하지 않는다. 가공된 텍스트(CSV/마크다운/표)를 그대로 LLM에 반환 | `tools.py` 전반 | 코드 확인 |
| 잘라내기 | 뉴스 20건/글로벌 10건, FRED 최근 40행, Polymarket 6건, 소셜 항목 길이 컷 | `default_config.py:141-143`, `fred.py:40,276-278`, `polymarket.py:28`, `stocktwits.py:139-140` | 코드 확인 |
| 중복 제거 | 글로벌 뉴스만 제목 기준 중복 제거 | `yahoo/news.py:166-186` | 코드 확인 |
| 출처·시점 표기 | 뉴스는 `(source: 출판사)`와 링크, 날짜는 헤더의 조회 윈도. FRED는 시리즈 제목·단위·빈도·최신값 날짜. 개별 뉴스의 게시 시각은 출력하지 않음 | `yahoo/news.py:75-84`, `fred.py:244-272` | 코드 확인 |
| 인용 ID | **없음**(분석가 보고서에 출처 ID를 달게 하는 계약 없음) | `tools.py`, 분석가 프롬프트 전반 | 코드 확인(부재) |

### Q5-5. 신뢰성 장치

| 장치 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 숫자는 도구 결과에서만 | Market Analyst는 "정확한 OHLCV·가격·지표 주장은 `get_verified_market_snapshot`을 진실원으로", 충돌 시 "조정된 숫자를 지어내지 말고 불일치를 표시" | `market_analyst.py:48`, `snapshot.py:118-126` | 코드 확인 |
| 날조 금지 센티널 | 데이터 없음/장애 시 "Do not estimate or fabricate values" 문구 반환 | `router.py:176-197,291-294` | 코드 확인 |
| 시계열 날짜 강제 | LLM이 어떤 날짜를 넣어도 `trade_date`로 클램프 | `tools.py:1-5`, `date_window.py:78-105` | 코드 확인 |
| 종목 정체성 고정 | 회사명을 결정론적으로 주입해 차트 모양으로 엉뚱한 회사를 상상하지 못하게 함(#814) | `agents/context.py:61-82,126-169` | 코드 확인 |
| 반복 검색 방지 | 전용 장치 **없음**. 라운드 상한(20)이 유일한 제동이고, 상한 도달 시 사용 횟수를 도구별로 로깅 | `setup.py:79-83` | 코드 확인 |
| 소셜 신뢰도 | 선택적 Jev 필터(오프토픽 제거 + 입장 집계). 키 없으면 비필터 | `post_screen.py:133-164` | 코드 확인 |
| 도구 외 출력 형식 | 환각 도구호출 방지를 위해 Sentiment·결정 단계 프롬프트에 "도구 없음" 명시(#1130) | `sentiment_analyst.py:94-99`, `structured.py:31-39` | 코드 확인 |

### Q5-6. 리서치 루프의 종료 조건

| 조건 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 도구 라운드 상한 | `max_tool_rounds=20` (환경변수 `TRADINGAGENTS_MAX_TOOL_ROUNDS`). 도구호출이 있는 AI 메시지 수를 센다 | `default_config.py:137`, `setup.py:73-77`, `default_config.py:22` | 코드 확인 |
| 상한 도달 시 | `WRAP_UP` 메시지("You have used every tool round this report allows. Write your final report now from the tool results above, and say which data you could not retrieve.")를 붙여 **도구 없이** 마지막 한 턴으로 보고서를 쓰게 하고 그 턴에서 종료 | `turn.py:7-10,13-27`, `setup.py:79-90` | 코드 확인 |
| 번역 | "이 보고서에 허용된 도구 라운드를 모두 사용했다. 위 도구 결과로 지금 최종 보고서를 쓰고, 가져오지 못한 데이터를 밝혀라." | `turn.py:7-10` | 코드 확인 |
| 재귀 한도 | `max_recur_limit=100`. `2*max_tool_rounds+2 >= max_recur_limit`면 시작 시 거부 | `trading_graph.py:88-95` | 코드 확인 |
| 시간 제한 | 그래프 수준 타임아웃 **없음**. 개별 HTTP 타임아웃만 있음(Yahoo 외 10-30초) | `fred.py:32`, `polymarket.py:25`, `sec_edgar.py:110`, `stocktwits.py:77` | 코드 확인 |

### Q5-7. 우리 시스템 관점 메모 (의견)

- 의견: "웹 리서치 루프"가 필요하면 이 레포에서 가져올 것은 없다. 대신 도구 라운드 상한 + WRAP_UP 패턴(`turn.py`, `setup.py:53-90`)과 날짜 클램프 주입(`tools.py`의 `InjectedState`)은 그대로 참고할 가치가 있다.
- 의견: 뉴스·공시 리서치는 별도 레포(dexter, Vibe-Trading 등)의 루프 설계와 비교해서 고르는 것이 맞다.
