---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/agents/analysts/sentiment_analyst.py
  - tradingagents/dataflows/vendors/stocktwits.py
  - tradingagents/dataflows/vendors/reddit.py
  - tradingagents/agents/post_screen.py
  - tradingagents/agents/schemas.py
  - tradingagents/dataflows/symbols.py
depends:
  - run-state.md
  - configuration.md
  - vendor-routing.md
  - point-in-time.md
  - decision-contract.md
  - run-input.md
status: ready
---

# 소셜 감성 분석

> 뉴스·StockTwits·Reddit을 사전 수집하고 선택적 Jev 선별 후 감성 등급·점수·확신도를 가진 보고서를 생성한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. trade_date에서 7일 전 날짜를 계산한다.
2. 뉴스 도구를 직접 호출하고 TypeSafe 키에 따라 선별 함수를 준비한다.
3. StockTwits를 조회하고, 종목에 맞는 subreddit 묶음으로 Reddit 검색 결과를 가져온다. 이 세 수집 호출은 노드 본문에서 순차다.
4. 가능하면 소셜 게시물을 Jev로 선별하고 날짜 범위·내용·라벨을 텍스트 블록으로 만든다.
5. 수집 블록·종목·기준일·언어와 현재 메시지 이력을 넣어 구조화 감성 보고서를 요청한다.
6. 성공 시 정형 헤더+서술을, 미지원·실패 시 자유텍스트를 sentiment_report와 AIMessage로 반환한다.

### 1.2 범위·통합 지점

- 제공: 최근 데이터의 수집·선별·감성 보고서.
- 제외: 별도 임의 검색 도구·게시물 아카이브·가격 예측·주문. 뉴스 벤더 내부는 데이터 계약에 둔다.
- 의존: HTTP·시계·모델·선택적 TypeSafe 서비스. 소셜 제공자가 반환한다고 가정한 형태를 코드로 확인했으며 실제 서버 보장은 미확인.
- 상태·부작용: 소셜 수집은 HTTP 조회이며 이 경로 자체에 영속 캐시나 사전 동기화 DB는 없다. 보고서 부분 상태와 AIMessage만 반환한다. Jev는 게시물 본문을 외부로 전송한다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 감성 노드 | state map → messages=list, sentiment_report=string | 종목과 기준일·현재 messages 사용. 도구 호출 루프 없음 |
| 수집 기간 | YYYY-MM-DD string 쌍 | trade_date-7일 .. trade_date. 공통 시점 계약에 따라 일 경계 필터 |
| StockTwits | ticker, limit=30, timeout=10초, 기간, optional screen → string | 라벨·시간·사용자·본문, 실패와 기간 미포함을 표식으로 구분 |
| Reddit | ticker, subreddits, limit_per_sub=5, timeout=10초, 기간, optional screen → string | 종목 검색·new 순·최근 week·한 페이지100건; 점수·댓글수 없음 |
| screen | list[string] → (list[bool], string) | 모든 입력당 keep 하나와 요약 note, 원래 순서 유지 |
| SentimentReport | overall_band enum, overall_score float[0,10], confidence enum, narrative string | S2 스키마·렌더링. 노드는 이 object를 상태에 직접 보관하지 않고 렌더 문자열만 보관 |
| TypeSafe 환경변수 | TYPESAFE_API_KEY, TYPESAFE_DEFAULT_MODEL, TYPESAFE_BASE_URL | 기본 jev-latest, https://api.typesafe.ai + /v1/systemone. 키 없으면 선별 생략 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 기간·수집 조립 | 뉴스 get_news.func→jev_screen 생성→StockTwits→Reddit 순서. 소셜 조회 함수는 router를 거치지 않는다. 잘못된 trade_date는 날짜 파싱 예외를 전파한다. 뉴스 get_news.func 예외도 노드가 catch하지 않으므로 전부 항상 문자열로 성공한다는 주석보다 코드 경로가 우선이다. | 코드 확인 |
| R-02 | StockTwits 수집·필터 | 암호화폐는 <BASE>.X, 나머지는 upper ticker로 공개 symbol stream 요청. HTTP/OS/JSON 오류는 unavailable. 기간 내 게시물만 남기며 coverage_gap이면 자료 없음과 구분. message가 기대한 map 형태가 아니거나 screen의 keep 길이가 다르면 후속 처리 예외를 별도 포착하지 않는다. 선별은 표시 limit 전 전체 기간 내 게시물에 적용한다. | 코드 확인 |
| R-03 | StockTwits 표시 | 최대30개 본문을 HTML unescape·줄바꿈 제거 후280자로 잘라 시간·사용자·Bullish/Bearish/no-label 표시. 라벨 비율 분모는 no-label 포함 표시 총수다. Jev note는 선별된 전체 모집단을, 아래 비율은 최대30개 표본을 다루므로 서로 다를 수 있다. | 코드 확인 |
| R-04 | Reddit 소스·검색 | 기본 wallstreetbets/stocks/investing; 인식된 crypto pair는 CryptoCurrency/CryptoMarkets와 BTC=Bitcoin, ETH=ethereum, SOL=solana 선행 커뮤니티. coin base를 검색어로 쓰고 subreddit을 +로 연결한 한 RSS 요청으로 최신100개를 수집한다. | 코드 확인 |
| R-05 | Reddit 전송·가공·표시 | RSS 본문은5MiB까지만 읽고 Atom published와 HTML 본문을 해석한다. 기간 필터 후 title+body 최대1000자로 선별, 요청 커뮤니티 순으로 그룹·그룹당5개를 표시, 본문은240자. 실패 None은 unavailable, 정상 빈 결과는 no posts, 꽉 찬 페이지에 없는 커뮤니티는 최신100건에 없다고 표시한다. | 코드 확인 |
| R-06 | Reddit 429·기타 실패 | 429는 한 번만 재시도. Retry-After 숫자가 있으면 min(value,60초), 없으면60초±20% 지터 대기. 재실패·기타 HTTP/OS/XML 오류·크기 초과는 unavailable. 캐시·페이지 순회·시간 예산 기반 별도 종료는 없다. | 코드 확인 |
| R-07 | Jev 요청·확률 판정 | 키 없으면 screen=None. 키 있으면 종목 이름을 가능한 한 해석하고 게시물마다 about/stance 두 질문을 한 요청으로 보낸다. about.noul<0.3이면 제외, 나머지를 유지. stance confidence<0.5 또는 선택값 미지원이면 unclear. 유지한 전체 게시물의 bullish/bearish/neutral/unclear 수를 요약한다. | 코드 확인 |
| R-08 | Jev 실행·실패 | 게시물별 요청을 최대16 worker로 병렬 수행하고 원래 순서로 모은다. 429·529·일시 연결 오류는 최대3회, 기본1초 지터 백오프×2, Retry-After는[0,30]초로 제한. HTTP timeout15초. 요청 하나라도 TypeSafeError 또는 선별 중 KeyError/TypeError면 해당 소스 전체를 원문 그대로 유지하고 unscreened 안내를 붙인다. 미전송 작업 취소, 실행 중 작업은 기다리지 않는다. 이 외 예외는 선별 함수가 흡수하지 않는다. | 코드 확인 |
| R-09 | 모델 입력·판단 | news/stocktwits/reddit 각각 start_of/end_of 텍스트 표식 사이에 넣고 일반 prompt messages로 전달한다. 70/30 moderately bullish·90/10 이상 과열·50/50 불확실성, 출처 불일치·의견과 사건 구분·데이터 한계 고려를 지시한다. 사용자 게시물을 신뢰 경계로 파싱하거나 주입 공격을 차단하는 코드가 아니다. | 코드 확인 |
| R-10 | 모델 출력·검증 | tool bind 없이 S2 구조화 호출 및 자유텍스트 fallback. 점수0~10·confidence 값·6개 band는 스키마 제약, band별 권장 점수 범위와 자료5건 미만 low는 지시이며 강제 재계산하지 않는다. 자유텍스트 fallback은 정형 헤더를 보장하지 않으며 그것마저 실패하면 예외가 전파한다. | 코드 확인 |
| R-11 | 과거 분석 | 검색 결과를 날짜로 잘라도 소셜은 최근 피드일 뿐 아카이브가 아니다. coverage_gap/자료 한계를 표시하며 과거시점의 소셜 전체를 재현했다고 보장하지 않는다. | 코드 확인 |

- 미결정: 없음. 선행 스펙을 대조했고 선언한 범위의 원본 경계는 정해져 있다.
- 확인 한계: 설치·실행 및 실제 모델·외부 API 응답 검증은 하지 않았다. 프롬프트 지시가 모델 응답에 항상 지켜진다는 보장은 없다.

### 1.5 필수 코드 참조

기준은 frontmatter SHA이며 경로는 원본 레포 상대 경로다. 호출한 공통 helper는 위 선행 계약에서 정의한다.
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/agents/analysts/sentiment_analyst.py:43-127 _seven_days_back, create_sentiment_analyst` | 기간·수집 순서·입력 조립·모델·반환 | R-01, R-09, R-10 |
| C-02 | `tradingagents/dataflows/vendors/stocktwits.py:30-162 _created_at, _within_window, _body, _stocktwits_symbol, fetch_stocktwits_messages` | StockTwits URL·정규화·필터·형식·실패 | R-02, R-03, R-11 |
| C-03 | `tradingagents/dataflows/vendors/reddit.py:38-134 _within_window, _posted_at, _coverage_dates, subreddits_for, _search_qs, _iso_to_timestamp, _strip_html` | RSS 상수·게시물 해석·기간 및 subreddit 선택 | R-04, R-05, R-11 |
| C-04 | `tradingagents/dataflows/vendors/reddit.py:142-245 _jitter, _retry_after_seconds, _read_capped, _fetch_subreddit_rss` | 전송·단일429 재시도·크기 제한·RSS 파싱 | R-05, R-06 |
| C-05 | `tradingagents/dataflows/vendors/reddit.py:248-337 fetch_reddit_posts` | 그룹·선별·샘플 제한·placeholder 출력 | R-04, R-05, R-11 |
| C-06 | `tradingagents/agents/post_screen.py:27-181 constants, system_one, jev_screen, _ask_each` | 선별 질문·재시도·선별 기준·실패 시 보존 및 병렬 순서 | R-07, R-08 |
| C-07 | `tradingagents/agents/analysts/sentiment_analyst.py:130-199 _build_system_message` | 데이터 블록·점수 해석 지시·분석 보고서 형식 | R-09, R-10 |
| C-08 | `tradingagents/agents/schemas.py:296-379 SentimentBand, SentimentReport, render_sentiment_report` | 6종 band·0~10 점수·확신도와 정형 문자열 렌더링 | R-10 |
| C-09 | `tradingagents/dataflows/symbols.py:43-45 _CRYPTO_BASES; tradingagents/dataflows/symbols.py:79-94 _CRYPTO_QUOTES, crypto_base` | 알려진 USD/USDT/USDC pair만 crypto로 판별, 이외 None | R-02, R-04 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 모델·네트워크를 대체 응답으로 바꿔 분기를 검증하는 사례이며 모델 품질이나 실제 제공자 가용성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | trade_date=2026-10-20 | 수집기간2026-10-13..2026-10-20 |
| T-02 | R-03 | 표시30건: Bullish15·Bearish5·unlabeled10 | Bullish50%·Bearish17%·Unlabeled10·Total30 |
| T-03 | R-06 | Reddit429 Retry-After=0, 이후 정상RSS | 추가 대기0으로 한 번만 재시도 |
| T-04 | R-05 | Reddit 응답5MiB 초과 | HTTPException 경로의 unavailable, no posts로 위장하지 않는다 |
| T-05 | R-07 | Jev about0.29·about0.30, stance confidence0.49 | 첫 게시물 제외, 둘째 유지·stance unclear |
| T-06 | R-08 | 한 게시물 Jev 요청 실패 | 해당 소스 전체 입력 게시물을 유지하고 unscreened 표식 |
| T-07 | R-10 | band=Bearish·score9·confidence=high typed object | 범위0~10이면 band와 score 불일치만으로 코드가 거부하지 않음 |
| T-08 | R-01 | 뉴스 get_news.func가 비정형 예외 발생 | 감성 노드가 예외를 삼키지 않고 이후 수집/모델 호출로 진행하지 않는다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01, R-09, R-10 | C-01 | 원본 코드 직접 열람, 실행하지 않음 |
| R-02, R-03, R-11 | C-02 | 원본 코드 직접 열람, 실행하지 않음 |
| R-04, R-05, R-11 | C-03 | 원본 코드 직접 열람, 실행하지 않음 |
| R-05, R-06 | C-04 | 원본 코드 직접 열람, 실행하지 않음 |
| R-04, R-05, R-11 | C-05 | 원본 코드 직접 열람, 실행하지 않음 |
| R-07, R-08 | C-06 | 원본 코드 직접 열람, 실행하지 않음 |
| R-09, R-10 | C-07 | 원본 코드 직접 열람, 실행하지 않음 |
| R-10 | C-08 | 원본 코드 직접 열람, 실행하지 않음 |
| R-02, R-04 | C-09 | 원본 코드 직접 열람, 실행하지 않음 |

T-ID의 기대 결과는 해당 R-ID 및 C-ID의 분기에서 도출했다. 테스트는 이름 검색까지만 참고했으며 수락 사례의 출처로 삼지 않았다.

핵심 프롬프트(R-09): “Past sentiment is not predictive.”

번역: “과거 감성이 미래를 예측하는 것은 아니다.” 감성 결론은 가격 결론이 아닌 다른 근거와 함께 고려할 신호로 제시하도록 지시한다.

문서/주석 차이: pre-fetch 주석은 예외가 노드 밖으로 나오지 않는다고 설명하지만 뉴스 도구 호출은 catch 없이 수행한다(C-01). 네트워크 제공자의 실제 서버 형태와 Jev 응답 보정 정확도는 미확인이다.

[핵심 원본](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/agents/analysts/sentiment_analyst.py#L43-L127).

## 적용 메모

분석자 의견: 미국 주식 분석용 기본 subreddit·StockTwits는 유지한다. 국장에서는 cashtag·검색어·커뮤니티 적합성을 별도 검증하고 동일한 출처 블록·unavailable 의미·점수 출력 계약 아래 소스를 교체할 수 있다. 현재 사용자 요청에 따라 교체하지 않는다.
