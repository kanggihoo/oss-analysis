# 데이터 매트릭스 (Q1·Q2 비교)

- 작성일: 2026-10-09
- 기준: 각 레포 `reports/<repo>/01-data.md` (SHA는 `../repos.lock.tsv`)
- 표기: ✅ 판단에 사용 / △ 일부·대리지표·특정 시장만 / ❌ 없음 / (정의만) 코드는 있으나 판단 경로에 연결되지 않음
- 근거(`파일:라인`)는 각 레포 문서에 있으므로 여기에는 복제하지 않는다.

약칭: **TA** TradingAgents · **CN** TradingAgents-CN · **AHF** ai-hedge-fund · **DSA** daily_stock_analysis · **VT** Vibe-Trading · **OA** OpenAlice · **DX** dexter · **QD** QuantDinger

## 1. 데이터 분류별 사용 현황

| 분류 | TA | CN | AHF | DSA | VT | OA | DX | QD |
|---|---|---|---|---|---|---|---|---|
| 가격·OHLCV | ✅ yfinance (대체 Alpha Vantage) | ✅ MongoDB → Tushare/AKShare/BaoStock | △ 종가만 (FD) | ✅ efinance > akshare > … > yfinance | ✅ loader 28종 | ✅ yfinance 등 + 거래소 공개 데이터 | ✅ FD | ✅ Yahoo/Nasdaq/yfinance, 코인은 거래소 REST |
| 기술지표 | ✅ stockstats 12종 (LLM이 골라서 호출) | ✅ 코드 계산 | ❌ (RSI 함수 정의만) | ✅ 코드 계산 | ✅ 코드 계산 + LLM이 직접 쓴 스크립트 | ✅ 코드 도구 | ❌ | ✅ 코드 계산 (지지/저항, ATR 손절 포함) |
| 펀더멘털 | ✅ yfinance 28필드 + SEC | ✅ Tushare 등 (A주) | ✅ FD 14필드 TTM (**유일한 입력**) | ✅ akshare 재무 | ✅ SEC/Eastmoney/Yahoo | ✅ yfinance + FMP | ✅ FD (가장 넓음: 세그먼트, 공시 본문, 스크리너) | ✅ Finnhub/yfinance/SEC + DB 스냅샷 |
| 수급·자금흐름 | ❌ | ✅ 북향·신용·섹터 자금 (A주) | ❌ | ✅ 주력 순유입 (A주만) | △ Eastmoney (중화권) | △ 섹터 거래대금 점유율 (대리지표) | △ 내부자, 13F (미국) | △ Form 4 건수, 공매도 |
| 뉴스 | ✅ yfinance + 고정 글로벌 검색어 5개 | ✅ DB + AKShare | ❌ (정의만) | ✅ 검색엔진 7종, 고정 템플릿 | ✅ Eastmoney/Yahoo + 자유 웹 검색 | ✅ RSS 28개 (기본 8개 활성) | ✅ FD 뉴스 + 웹 검색 4종 | ✅ Finnhub, 5건 미만이면 검색 1회 보충 |
| 감성·소셜 | ✅ StockTwits + Reddit | △ 사용자 업로드 / 뉴스 키워드 | ❌ | △ adanos (미국만) | △ 사전 기반 점수 + 공포탐욕지수 | ❌ | ✅ X API | △ Finnhub 소셜 + 공포탐욕지수 |
| 거시 | ✅ FRED 40여 개 + Polymarket | △ 지수, 시장 폭 | ❌ | ✅ 대시장 복기 + 장 단계 | ✅ FRED + Polymarket | ✅ FRED/BLS/EIA/OECD/IMF (가장 넓음) | ❌ | △ VIX, DXY, 미 10년물 |
| 코인 전용 | ❌ | ❌ | ❌ | ❌ | △ 호가 깊이, 공포탐욕지수 | △ Deribit 기간구조, 옵션 OI | △ 가격만 | ✅ 펀딩비, OI, 롱숏비 (CoinGlass → 거래소) |
| 보유 현황 → 판단 입력 | ✅ PortfolioContext JSON → 프롬프트 | △ 포지션 워크플로에서만 | ❌ (사이징에만 쓰고 LLM에는 안 넣음) | ✅ 로컬 DB | ✅ 브로커 조회 도구 | ✅ getPortfolio | ❌ | △ 수동 입력 보유 |
| 과거 판단 메모리 | ✅ 5일 정산 교훈 → PM | ✅ mem0 교훈 | ❌ | ✅ AgentMemory, 스킬 가중치 | △ 영속 메모리 recall | △ 워크스페이스 파일 | △ 대화·장기 메모리 (채점 없음) | ✅ 검증된 과거 판단 3건 |

## 2. 수집 방식 비교 (Q2)

| | TA | CN | AHF | DSA | VT | OA | DX | QD |
|---|---|---|---|---|---|---|---|---|
| 미리 가져오기 vs 도구 호출 | 도구 호출 (Sentiment만 미리) | 혼합 | 미리 | 미리 (Agent 모드만 도구 호출) | 도구 호출 (swarm만 미리) | 도구 호출 | 도구 호출 | 미리 |
| 벤더 폴백 | ✅ `route_to_vendor` 체인 | ✅ DB → 3개 소스 | ❌ 단일 | ✅ 6단계 + 서킷브레이커 | ✅ `FALLBACK_CHAINS` | △ 도구별 하드코딩 | △ 웹 검색만 | △ 시장당 1개 소스 + 내부 폴백 |
| 미래 데이터 차단 | ✅ 날짜 클램프 | △ 19시 컷오프 | ✅ `filing_date` PIT + blind 모드 | △ | ✅ 신호 1봉 지연 (백테스트) | ✅ `asOf` | ❌ | ❌ ("지금" 기준) |

## 3. 한국 시장 지원 현황

| 레포 | 상태 |
|---|---|
| TA | yfinance `.KS/.KQ` 일봉·지표만. 벤치마크 `^KS11`. 한국 수급·재무·뉴스 없음 |
| DSA | yfinance `.KS` 단일 경로(폴백 없음). **자금흐름이 항상 미지원이라 LLM 매수가 코드에서 hold로 강등된다(코드 추적 결과, 실행 미검증)**. 한국어 리포트 지원 |
| VT | pykrx 일봉, KRX 백테스트 엔진(±30%, 매도세, 공매도 불가). 업비트·KIS는 조회 커넥터만 있음 |
| OA | yfinance `.KS` 설명문만 확인 |
| CN, AHF, DX, QD | 한국 시장 지원 없음 |

**결론**: 8개 중 한국 수급·재무·뉴스를 실제로 판단에 쓰는 레포는 없다. 이 데이터는 우리가 직접 붙여야 한다.

## 4. 우리 시스템의 데이터 매핑 (의견)

| 분류 | 참고할 레포 (방식) | 우리 데이터 소스 |
|---|---|---|
| 가격·OHLCV | VT (시장별 폴백 체인), TA (벤더 라우터) | 업비트 캔들 (`docs/upbit/api/quotation/candles.md`), 키움 차트 `ka10081` 등, 키움 미국 `usa06012` |
| 기술지표 | CN, DSA, QD: **코드로 계산하고 LLM에는 결과만** | 자체 계산 (pandas) |
| 수급 | CN, DSA (A주 수급을 핵심 입력으로 씀) | 키움 `ka10059` 종목별 투자자, `ka10008` 외국인, `ka10009` 기관 |
| 펀더멘털 | AHF (PIT 스냅샷), QD (DB 스냅샷 계층) | DART (새로 필요) |
| 뉴스 | DSA (차원별 고정 템플릿), OA (RSS) | 웹 검색 API 또는 RSS (새로 필요) |
| 코인 전용 | QD (펀딩비, OI, 롱숏비) | 업비트 호가·체결. 펀딩비·OI는 해외 거래소 공개 API (새로 필요) |
| 거시 | TA, OA (FRED) | FRED, 한국은행 ECOS (새로 필요) |
| 과거 판단 | TA (5일 정산), QD (검증된 과거 판단 주입) | 자체 DB |
