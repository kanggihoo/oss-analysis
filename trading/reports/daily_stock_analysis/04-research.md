# daily_stock_analysis — 실시간 리서치

- 분석 SHA: `ce364e457aab288863a5707e7b3df79786ad07f2` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q5
- 검증 수준 요약: 코드 확인 44 / 추론 2 / 미확인 2 (실행 확인 0; 본문 내 표기 횟수 기준 근사치)

경로 약어: `analyzer.py`=`src/analyzer.py`, `pipeline.py`=`src/core/pipeline.py`, `base.py`=`data_provider/base.py`, `config.py`=`src/config.py`, `search_service.py`=`src/search_service.py`, `storage.py`=`src/storage.py`, `orchestrator.py`/`runner.py`/`executor.py`/`factory.py`/`protocols.py`=`src/agent/…`, `defaults.py`/`aggregator.py`/`router.py`/`deliberation.py`=`src/agent/skills/…`, `agents/*_agent.py`=`src/agent/agents/…`, `search_tools.py`/`data_tools.py`=`src/agent/tools/…`, `stock_analyzer.py`=`src/stock_analyzer.py`. 그 외는 레포 루트 기준 상대경로를 그대로 적었다.

---

## Q5. 실시간 리서치 {#q5}

### 5-1. 한눈에 보기

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 판단 **도중**에 웹/뉴스를 찾아보는가 | **기본(레거시) 경로: 아니오.** 판단(LLM 호출) 전에 코드가 고정 검색을 한 번 끝내고 결과를 프롬프트에 넣는다. **Agent 경로: 예.** LLM이 `search_stock_news`, `search_comprehensive_intel` 도구를 호출 | `src/core/pipeline.py:683-733`, `src/agent/tools/search_tools.py:146-256`, `src/agent/agents/intel_agent.py:25-94` | 코드 확인 |
| 웹 페이지 읽기 | 검색 provider(SerpAPI)가 상위 결과 본문 일부를 추가로 가져오는 옵션이 있음. LLM용 별도 "웹 페이지 읽기" 도구는 없음 | `src/search_service.py:204-232`(`fetch_url_content`), `:953-1000`(SerpAPI organic 본문 병합) | 코드 확인(함수 존재·역할), 상세 조건 미열람 |
| 공시 조회 | 별도 공시 API 없음. "公司公告 上交所 深交所 cninfo" 문구를 **검색어에 넣는** 방식(`announcements` 차원). 미국 SEC/HKEX는 로컬 인텔 풀 RSS(옵트인) | `search_service.py:4493-4503`, `intelligence_service.py:41-66` | 코드 확인 |
| LLM이 검색어를 만드는가 | **아니오(대부분).** 검색어는 코드의 템플릿(종목명+코드+고정 키워드). Agent 도구에서도 LLM은 `stock_code`, `stock_name`만 넘기고 쿼리 문장은 서버 템플릿이 만든다 | `search_service.py:4384-4520`, `:4021-4110`, `search_tools.py:146-175` | 코드 확인 |
| 검색 횟수 | 레거시: 종목당 **최대 5회**(`max_searches=5`). Agent `search_comprehensive_intel`: 최대 **6회**, `search_stock_news`: 1회(제공자 폴백 루프) | `pipeline.py:704`, `search_tools.py:184`(`max_searches=6`), `search_service.py:4136` | 코드 확인 |

### 5-2. 제공자

| 제공자 | 키 | 등록 순서/특이사항 | 근거 | 검증 |
|---|---|---|---|---|
| Anspire Search | `ANSPIRE_API_KEYS` | 키가 있으면 **맨 앞**(`insert(0)`) | `search_service.py:1208-1394`, `:2504-2506` | 코드 확인 |
| Bocha(博查) | 키 필요 | 1순위(중문 최적화, AI 요약) | `:1011`, `:2466-2468` | 코드 확인 |
| Tavily | 키 필요 | `topic='news'` 지원, 2순위 | `:421`, `:2471-2473` | 코드 확인 |
| Brave | 키 필요 | 3순위 | `:1629`, `:2476-2478` | 코드 확인 |
| SerpAPI | 키 필요 | 4순위 | `:571`, `:2481-2483` | 코드 확인 |
| MiniMax Web Search | 키 필요 | 5순위 | `:1397`, `:2486-2488` | 코드 확인 |
| SearXNG | 키 불필요(자체 인스턴스 URL 또는 공개 인스턴스 자동 발견 옵션) | 6순위 | `:1835`, `:2490-2502` | 코드 확인 |
| DDG / Exa / RSS(검색용) | **없음** | - | `search_service.py` 클래스 목록(55-2244)에 없음 | 코드 확인 |
| RSS(로컬 인텔 풀) | 불필요 | 옵트인(`NEWS_INTEL_AUTO_FETCH_ENABLED`). SEC 보도자료, HKEX, MarketWatch + NewsNow(财联社·雪球·华尔街见闻·金十·格隆汇) | `intelligence_service.py:38-106` | 코드 확인 |

### 5-3. 호출 방식: 검색어 구성 (뉴스 검색 차원)

레거시 경로의 `search_comprehensive_intel(stock_code, stock_name, max_searches=5)`(`search_service.py:4384-4636`)의 쿼리 템플릿이다. 제공자는 **차원마다 한 개씩 라운드로빈**(`provider_index % len(available_providers)`: `:4555`)이며, 한 차원이 실패해도 다른 제공자로 재시도하지 않는다(루프에 재시도 코드 없음). `코드 확인`

**A주/기타(중국어 템플릿, `search_service.py:4467-4524`)**

| 순서 | 차원 | 쿼리 원문(일반 종목) | 번역 | ETF/지수 변형 | 신선도 | 검증 |
|---|---|---|---|---|---|---|
| 1 | `latest_news` | `{종목명} {코드} 最新 新闻 重大 事件` | 종목명 코드 최신 뉴스 중대 사건 | 동일 | 엄격(기간 외·날짜 불명 제거), Tavily `topic=news` | 코드 확인 |
| 2 | `market_analysis` | `{종목명} 研报 目标价 评级 深度分析` | 리서치 리포트 목표가 등급 심층 분석 | 동일 | 180일 룩백, 날짜 불명 허용 | 코드 확인 |
| 3 | `risk_check` | `{종목명} 减持 处罚 违规 诉讼 利空 风险` | 감자(대주주 매도) 처벌 위반 소송 악재 리스크 | `{종목명} 指数走势 跟踪误差 净值 表现` | 엄격(ETF는 완화), Tavily `topic=news` | 코드 확인 |
| 4 | `announcements` | `{종목명} {코드} 公司公告 重要公告 上交所 深交所 cninfo` | 회사 공시 중요 공시 상하이·선전거래소 cninfo | `{종목명} {코드} 公告 指数调整 成分变化` | 엄격, Tavily `topic=news` | 코드 확인 |
| 5 | `earnings` | `{종목명} 业绩预告 财报 营收 净利润 同比增长` | 실적 예고 재무보고 매출 순이익 전년비 증가 | `{종목명} 指数成分 净值 跟踪表现` | 180일 룩백 | 코드 확인 |
| 6 | `industry` | `{종목명} 所在行业 竞争对手 市场份额 行业前景` | 소속 업종 경쟁사 점유율 업종 전망 | `{종목명} 指数成分股 行业配置 权重` | 완화 | 코드 확인 |

`max_searches=5`이므로 레거시 경로에서는 **6번째 `industry`는 실행되지 않는다**(`:4547-4548`: `if search_count >= max_searches: break`). 따라서 GUIDE가 말한 "5차원"은 A주에서 `latest_news, market_analysis, risk_check, announcements, earnings`이다. Agent 도구는 `max_searches=6`이라 6차원 모두 실행된다. `코드 확인`

**외국 티커(미국·홍콩; 영어 템플릿, `search_service.py:4412-4466`)**: `{영문명} {코드} latest news events` / `{영문명} analyst rating target price report` / `{영문명} risk insider selling lawsuit litigation` / `{영문명} earnings revenue profit growth forecast` / `{영문명} industry competitors market share outlook`(5차원, `announcements` 없음). 영문명은 `STOCK_ENGLISH_NAME_MAP`에서 해결(`:4419-4420`, issue #2026). `코드 확인`

**한국 종목(`005930.KS`)**: `_is_foreign_stock`은 `^[A-Za-z]{1,5}(\.[A-Za-z])?$` 또는 5자리 숫자만 외국으로 본다(`search_service.py:2279`, `:2526-2548`). 숫자+`.KS`는 해당하지 않아 **중국어 템플릿으로 검색**된다. 한국 종목명은 STOCK_NAME_MAP/한국 시드 인덱스의 이름이 들어가므로 중국어 키워드(`最新 新闻 重大 事件` 등) 사이에 한국어/중문 종목명이 섞인 쿼리가 된다. `코드 확인`(정규식·분기 구조) / `추론`(실제 검색 품질은 실행 미확인)

**단건 뉴스 검색**(`search_stock_news`, Agent `search_stock_news` 도구와 시장복기가 사용, `search_service.py:4021-4110`)

| 조건 | 쿼리 | 근거 |
|---|---|---|
| 중국어 선호(A주 기본) | `{종목명} {코드} 股票 最新消息` (코드 없으면 `{종목명} 股票 最新消息`) | `:4068-4075` |
| 외국 + 영문 별칭 있음 | `{영문명} {단축명} {코드} stock latest news` 또는 `{영문명} {코드} stock latest news` | `:4076-4086` |
| `focus_keywords` 지정 | 키워드를 공백으로 이은 문자열 그대로(시장 복기가 사용) | `:4065-4066` |

시장 복기 뉴스(`market_analyzer.py:721-778`)는 지역별 고정 쿼리 3개를 사용한다. 한국: "韩国股市 KOSPI", "Korea stock market KOSPI KOSDAQ", "KOSPI KOSDAQ 行情"(`core/market_profile.py:82-96`). `코드 확인`

### 5-4. 결과 처리

| 단계 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 요청 규모 | 차원당 목표 3건, provider에는 `_provider_request_size(3)`만큼 요청 | `search_service.py:4526-4527`, `:2815-2820` | 코드 확인 |
| 날짜 필터 | `strict_freshness` 차원은 발행일을 정규화해 기간 밖·날짜 불명 제거. 상대 날짜 표현("3天前") 파싱 | `:3547-3686`, `:3687-3776`, `:4584-4600` | 코드 확인 |
| 랭킹 | 종목 식별어(코드·종목명)·이벤트 용어·섹터 용어 포함 여부로 관련도 점수와 이유를 계산, 카테고리(직접 기업 뉴스 0 / 섹터 1 / 거시 2) 우선 정렬 | `:2276-2300`, `:3186-3427` | 코드 확인 |
| 품질 필터 | 비공식 출처의 저품질 페이지 신호, 성인/스팸 신호, 관련도 0 필러 제거(공식 출처는 예외) | `:3428-3491`, `:3004-3185` | 코드 확인 |
| 중복 제거 | URL 단위 dedupe 코드는 열람 범위에서 확인하지 못함 | `:3777-3840` | 미확인 |
| 보고서 형식 | 차원별 제목 `📰 最新消息 (来源: provider)`, 항목당 `제목 [발행일]` + 요약 150자 + `关联度: 카테고리; score=N; 依据: …`, 차원당 최대 4건. **URL은 레거시 텍스트에 포함되지 않음**(`title`, `published_date`, `snippet[:150]`, 관련도 정보만) | `:4638-4693` | 코드 확인 |
| 캐시 | 메모리 10분(키 = 쿼리\|건수\|일수), 동시 동일 요청 병합 | `:2516`, `:2698-2800` | 코드 확인 |
| 영속화 | 차원별 성공 결과를 `news_intel` 테이블에 저장(재분석·조회용) | `pipeline.py:717-731`, `search_tools.py:44-80` | 코드 확인 |
| 다른 출처와 합치기 | 뉴스 텍스트 + (미국) 소셜 감성 텍스트 + 로컬 인텔 풀(최대 6건)을 `\n\n`로 이어 붙여 같은 "舆情情报" 섹션으로 주입 | `pipeline.py:735-770` | 코드 확인 |

### 5-5. 신뢰성 장치

| 장치 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 날짜 강제 | 프롬프트가 위험·호재·최신뉴스 항목마다 YYYY-MM-DD를 요구하고 윈도 밖 뉴스는 무시하라고 명시 | `analyzer.py:4913-4918`, `:5056` | 코드 확인 |
| "수치는 도구 결과에서만" | 단일 Agent 프롬프트 규칙 1: "必须调用工具获取真实数据 — 绝不编造数字，所有数据必须来自工具返回结果。" (번역: 반드시 도구로 실제 데이터를 얻고 숫자를 지어내지 말 것, 모든 데이터는 도구 결과에서) | `executor.py:254` | 코드 확인 |
| 결측 시 조작 금지 | "严禁编造数据", "数据缺失，无法判断" | `analyzer.py:4941-4947` | 코드 확인 |
| 인용 ID | **없음**(근거에 evidence ID를 붙이는 계약 없음. 대신 `signal_attribution` 기여도와 `data_sources`/`search_performed` 필드) | `analyzer.py:2241-2249`, `:2270-2271` | 코드 확인 |
| 뉴스 증거 공개 | 뉴스 검색을 "설정 안 함/0건/정상 히트"로 3상태 구분해 보고서에 별도 문구를 붙이고, 실제 LLM 입력에 뉴스 증거가 있었는지(`news_evidence_present`)도 별도 판정 | `analyzer.py:1773-1782`(AnalysisResult 필드), `agent/news_evidence.py:1-30`, `pipeline.py:858-862` | 코드 확인 |
| 반복 검색 방지 | **없음**(코드 레벨 중복 호출 방지 없음). 프롬프트의 "실패 도구 재호출 금지"와 `max_steps`, 검색 캐시(10분)가 사실상 방지 역할 | `executor.py:259`, `runner.py:404`, `search_service.py:2698-2800` | 코드 확인(방지 코드 부재) |
| 프롬프트 인젝션 | 검색 결과/RSS는 신뢰하지 않는 데이터지만 프롬프트에 코드블록(```)으로 감싸 넣을 뿐 별도 sanitize는 확인 못함. 대시장 요약에는 `BEGIN_UNTRUSTED_MARKET_SUMMARY` 센티널 상수가 있음 | `analyzer.py:4919-4921`, `daily_market_context.py:37-40` | 추론(뉴스 sanitize 코드 미발견) |

### 5-6. 리서치 루프의 종료 조건

| 경로 | 조건 | 근거 | 검증 |
|---|---|---|---|
| 레거시 | 정해진 차원 수 소진 또는 사용 가능한 provider 없음 시 중단. 차원 사이 0.5초 대기. 반복/토론 없음 | `search_service.py:4546-4634` | 코드 확인 |
| 단일 Agent | `AGENT_MAX_STEPS`(10) 초과 시 오류, 전체 벽시계 예산(`agent_orchestrator_timeout_s=600`, 0이면 무제한), 남은 예산이 최소 스텝 예산 이하면 중단 | `runner.py:404-440`, `:589-598`, `config.py:184`, `:1063` | 코드 확인 |
| multi Agent | 에이전트별 `max_steps`(technical 6, intel 4, risk 4, decision 3, skill 4), 오케스트레이터 타임아웃, 단계 최소 예산 15초 | `technical_agent.py:25`, `intel_agent.py:27`, `risk_agent.py:32`, `decision_agent.py:28`, `skill_agent.py:28`, `orchestrator.py:552-600` | 코드 확인 |
| 시간 제한(검색 provider) | 제공자 호출별 타임아웃/재시도(`_post_with_retry`, `_get_with_retry`), SearXNG는 별도 타임아웃 설정 | `search_service.py:185-203`, `:1856-1875` | 코드 확인(함수 존재) |

### 5-7. 한국 종목 관점 메모

- Agent의 `get_capital_flow` 도구 설명은 "A-share individual stocks만 지원(HK/US 미지원)"(`data_tools.py:717-731`), IntelAgent 프롬프트도 "HK/US는 건너뜀"이라 지시한다(`intel_agent.py:88-92`). 한국은 이 문구에 명시되지 않지만 `get_capital_flow_context`가 `_market_tag != cn`이면 `not_supported`를 반환하므로 동일하게 데이터가 없다(`base.py:4627-4631`). `코드 확인`
- 한국어 뉴스를 직접 겨냥한 템플릿은 없다. 키움/업비트 환경에서는 이 모듈을 그대로 쓰기보다 한국어·영어 쿼리 템플릿으로 교체해야 한다(분석자 의견은 05 문서 참조).
