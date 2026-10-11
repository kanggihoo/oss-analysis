# daily_stock_analysis — 최신화와 스케줄링

- 분석 SHA: `ce364e457aab288863a5707e7b3df79786ad07f2` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q3
- 검증 수준 요약: 코드 확인 29 / 추론 1 / 미확인 2 (실행 확인 0; 본문 내 표기 횟수 기준 근사치)

경로 약어: `analyzer.py`=`src/analyzer.py`, `pipeline.py`=`src/core/pipeline.py`, `base.py`=`data_provider/base.py`, `config.py`=`src/config.py`, `search_service.py`=`src/search_service.py`, `storage.py`=`src/storage.py`, `orchestrator.py`/`runner.py`/`executor.py`/`factory.py`/`protocols.py`=`src/agent/…`, `defaults.py`/`aggregator.py`/`router.py`/`deliberation.py`=`src/agent/skills/…`, `agents/*_agent.py`=`src/agent/agents/…`, `search_tools.py`/`data_tools.py`=`src/agent/tools/…`, `stock_analyzer.py`=`src/stock_analyzer.py`. 그 외는 레포 루트 기준 상대경로를 그대로 적었다.

---

## Q3. 최신화와 스케줄링 {#q3}

### 3-1. 트리거

| 트리거 | 설명 | 기본값 | 근거 | 검증 |
|---|---|---|---|---|
| GitHub Actions cron | 평일(월~금) UTC 10:00 = 북경 18:00. 한국 시간(KST)으로는 19:00 | 켜짐(포크 저장소에서 Actions 활성화 시) | `.github/workflows/00-daily-analysis.yml:5-8` | 코드 확인 |
| GitHub Actions 수동 | `workflow_dispatch` 입력 `mode`(full / market-only / stocks-only), `force_run`(거래일 검사 생략) | - | `00-daily-analysis.yml:10-24`, `:544-549`(분기: `--market-review`, `--no-market-review`, 기본) | 코드 확인 |
| 로컬 상주 스케줄러 | `python main.py --schedule` 또는 `SCHEDULE_ENABLED=true`. `schedule` 라이브러리로 `every().day.at("HH:MM")`, 메인 루프는 30초마다 `run_pending()` | `SCHEDULE_TIME="18:00"`(서버 로컬시간), 시작 시 즉시 1회 실행(`schedule_run_immediately=True`) | `src/scheduler.py:174-178`, `:402-421`, `src/config.py:1259-1262`, `main.py:1808-1893` | 코드 확인 |
| 복수 시각 | 쉼표 구분 `HH:MM` 여러 개(정렬·중복 제거, 형식 오류면 18:00) | - | `src/scheduler.py:27-48`, `main.py:1519-1546` | 코드 확인 |
| 런타임 스케줄러(Web/API) | `--serve`/`--webui`와 스케줄 설정이 함께 있으면 API 프로세스 안의 `RuntimeSchedulerService`가 스케줄을 소유. 전역 분석 락과 watchdog(타임아웃) 보유 | - | `main.py:1671-1713`, `src/services/runtime_scheduler.py:44-60`, `:246-835` | 코드 확인 |
| 수동 CLI | `python main.py`(1회), `--stocks`, `--market-review`, `--dry-run`, `--force-run`, `--backtest`, `--etf-rotation`(LLM 없이 규칙 기반 ETF 이중 모멘텀) | - | `main.py:295-476` | 코드 확인 |
| 이벤트(가격 조건) | `AGENT_EVENT_MONITOR_ENABLED` 켜면 `AlertWorker`가 5분 간격으로 가격 교차/등락률/거래량 급증/지표 규칙을 평가. **분석을 다시 돌리지는 않고** 알림·트리거 기록만 만든다 | 꺼짐, 간격 5분 | `src/services/runtime_scheduler.py:200-243`, `src/config.py:1088-1089`, `src/services/alert_service.py:76`; `alert_worker.py`에서 `StockAnalysisPipeline`/`run_full_analysis`/`analyze_stock` 문자열 grep 결과 없음 | 코드 확인 |
| Web/API 수동 | 분석 요청 API, 챗 | - | `api/v1/endpoints/analysis.py`, `agent.py`(미열람) | 미확인 |

### 3-2. 주기와 시점

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 하루 1회(복기 성격) | 장 마감 후 18:00(북경) 기본. 프롬프트도 "장 마감 후 일봉 복기"를 기본으로 가정하고, 시장 단계 컨텍스트로 장전/장중/장후를 구분 | `00-daily-analysis.yml:5-8`, `src/market_phase_prompt.py:136-170` | 코드 확인 |
| 종목 동시성 | `ThreadPoolExecutor(max_workers=MAX_WORKERS)`, 기본 3("低并发防封禁") | `src/config.py:1253`, `src/core/pipeline.py:3522` | 코드 확인 |
| 중복 실행 방지 | Actions: `concurrency: group: stock-analysis, cancel-in-progress: false`. 로컬: `run_claimed_scheduled_analysis`(발생 시각 원자 claim)와 전역 분석 락 | `00-daily-analysis.yml:27-29`, `main.py:1242-1260`, `runtime_scheduler.py:44` | 코드 확인(claim 내부 구현은 미열람) |
| 타임아웃 | Actions job 30분(변수로 조정). Agent 오케스트레이터는 `agent_orchestrator_timeout_s=600`(협조적 예산) | `00-daily-analysis.yml:38`, `src/config.py:1063` | 코드 확인 |
| 종목 목록 갱신 | 매 스케줄 실행마다 `.env`의 `STOCK_LIST`를 재로딩 (Issue #529) | `main.py:853-855`, `pipeline.py:3430-3431` | 코드 확인 |
| 거래일 캘린더 | 종목별 시장(`cn/hk/us/jp/kr/tw`)의 거래일 여부를 시장 현지 날짜로 판정해 휴장 시장 종목은 건너뜀. 모든 시장이 휴장이고 복기도 없으면 전체 스킵. `exchange-calendars` 없으면 fail-open(전부 거래일 취급) | `main.py:478-526`, `src/core/trading_calendar.py:41-50`, `:151-176`, `:618-637` | 코드 확인 |
| 시장 복기 지역 | `MARKET_REVIEW_REGION`(cn/hk/us/jp/kr/both/콤마 부분집합)과 오늘 열린 시장의 교집합을 계산 | `trading_calendar.py:640-687`, `00-daily-analysis.yml:417` | 코드 확인 |
| 자동 백테스트 | 분석 실행 직후 `BACKTEST_ENABLED`(기본 true)면 과거 분석 200건을 평가창 10거래일·최소 경과 14일 기준으로 평가(실패해도 무시) | `main.py:774-798`, `config.py:1233-1236` | 코드 확인 |

### 3-3. 사전 동기화

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 판단과 분리된 데이터 사전 적재 작업 | **없음.** 일봉은 종목 처리 시작 시점에 `fetch_and_save_stock_data`가 "최신 거래일 데이터가 이미 있으면 건너뛰기(断点续传), 없으면 가져와 저장"한다. 즉 분석 때 on-demand 저장이다 | `pipeline.py:376-432`, `:3295-3396` | 코드 확인 |
| 저장소 | SQLite(`./data/stock_analysis.db`, WAL 옵션). 주요 테이블: `stock_daily, news_intel, intelligence_items, fundamental_snapshot, analysis_history, decision_signals, decision_signal_outcomes, backtest_results, skill_opinion_*, portfolio_*, alert_*, llm_usage` | `src/config.py:1222`, `src/storage.py:93-1230` | 코드 확인 |
| GitHub Actions에서의 영속성 | 워크플로는 `data logs reports` 디렉터리를 새로 만들고 `reports/`, `logs/`만 아티팩트로 30일 보관. **DB를 캐시/복원하는 단계가 없다** → 매 실행이 빈 DB에서 시작(일봉도 새로 수집, 사후 백테스트도 과거 분석이 없어 의미 없음) | `00-daily-analysis.yml:61`, `:552-560` | 코드 확인(워크플로에 DB 복원 단계 없음을 읽어 확인) |
| 로컬 인텔 풀 자동 갱신 | 옵트인(`NEWS_INTEL_AUTO_FETCH_ENABLED`, 기본 False). 켜면 분석 전에 `refresh_auto_sources`가 호출되고 최소 간격 1시간(`_AUTO_FETCH_MIN_INTERVAL_SECONDS=3600`) | `intelligence_service.py:38-40`, `:307-358`, `pipeline.py:3019-3069` | 코드 확인 |
| 종목 인덱스 갱신 | 분석 시작 시 best-effort로 종목 인덱스 캐시 갱신 | `main.py:602-617` | 코드 확인 |

### 3-4. 데이터 신선도 관리

| 항목 | 감지 방법 | 판단에 반영하는 방식 | 근거 | 검증 |
|---|---|---|---|---|
| 실시간 시세 stale | `provider_timestamp`와 `fetched_at` 차이가 `realtime_cache_ttl`(기본 600초)을 넘으면 `is_stale=True`. 타임스탬프가 없으면 `None`(stale 미판정) | 컨텍스트팩 `quote` 블록 상태를 `stale`/`fallback`로 기록 → 데이터 품질 점수 하향 | `data_provider/base.py:2391-2423`, `services/analysis_context_builder.py:119-178`, `:504-551` | 코드 확인 |
| 핵심 데이터 degrade | `quote/daily_bars/technical` 중 하나가 `stale/fallback/missing/fetch_failed/partial/estimated`이면 | **코드**가 `confidence_level` "高"를 "中"으로 낮춤. **프롬프트**도 같은 조건에서 신뢰도 높음 금지를 지시 | `phase_decision_guardrail.py:19`, `:159-168`; `analyzer.py:2134`(프롬프트 문장) | 코드 확인 |
| 뉴스 신선도 | 검색 시 `days`(프로필: ultra_short 1 / short 3 / medium 7 / long 30, `NEWS_MAX_AGE_DAYS`로 상한)로 요청 후 **발행일을 엄격 필터**(`strict_freshness`). 발행일 불명 뉴스는 버림. 분석·실적 차원은 180일 룩백 허용 | 프롬프트가 "각 항목에 YYYY-MM-DD 필수, 창 밖/날짜 불명 뉴스는 무시" 강제 | `config.py:186-191`, `:335-339`, `search_service.py:2276-2277`, `:4584-4600`; `analyzer.py:4913-4918` | 코드 확인 |
| 시장 단계 | 개장/마감까지 분, `is_partial_bar`로 오늘 일봉이 미완성인지 표시 | 프롬프트 "장중에는 완성 일봉 복기 금지", 가드레일이 장중에 장후 복기 문구가 나오면 교체 | `market_phase_prompt.py:136-170`, `phase_decision_guardrail.py:188-197` | 코드 확인 |
| 일봉 신선도 | 거래일 판정으로 "재사용 가능한 마지막 완전 일봉 날짜"를 구해 이미 있으면 skip | - | `pipeline.py:3212-3228`(`_resolve_resume_target_date`), `trading_calendar.py:239-340` | 코드 확인(함수 위치 확인, 내부는 일부 미열람) |

### 3-5. 실시간 스트림

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 판단에 쓰는 WebSocket/푸시 | **분석 판단 경로에는 없음.** 판단 시점마다 REST/라이브러리 호출(`get_realtime_quote`)로 한 번 스냅샷을 가져온다 | `pipeline.py:518` | 코드 확인 |
| 스트림 관련 코드 | `bot/platforms/feishu_stream.py`, `dingtalk_stream.py`는 챗봇 수신용(알림/봇 범위 밖). `longbridge_fetcher.py:196-201`의 `push_candlestick_mode`는 Longbridge SDK 옵션 처리이며 분석 판단과의 연결은 확인하지 못함 | `bot/platforms/*`, `data_provider/longbridge_fetcher.py:196-201` | 미확인(롱브릿지 푸시 사용처) |
| Web UI 실시간 | Agent 분석 중 SSE 진행 이벤트(`stream_event`)로 단계 진행만 전달 | `src/agent/stream_events.py`, `orchestrator.py:700-716` | 코드 확인(이벤트 존재 확인) |

### 3-6. 한국 종목 관점 메모

- 한국 시장 거래일 판정은 `XKRX`/`Asia/Seoul`로 들어가 있어 `.KS` 종목은 한국 휴장일에 자동 스킵된다(`trading_calendar.py:41-50`, `main.py:478-526`). `코드 확인`
- 한국 종료 15:30, 종가 단일가 10분 창(15:20-15:30)으로 `closing_auction`을 구분한다(`trading_calendar.py:60-67`, `docs/market-support.md:20`). `코드 확인`
- Actions의 기본 cron(UTC 10:00 = KST 19:00)은 한국 장 마감(15:30) 이후라 한국 종목에도 장후 복기 모드가 자연스럽게 걸린다. 단, 미국 장은 그 시각 아직 열려 있지 않으므로(미국 종목은 전일 종가 기준) 미국 종목 비중이 있으면 별도 cron이 필요하다. `추론`(시간대 계산 기반)
