# TradingAgents-CN — 최신화와 스케줄링 (Q3)

- 분석 SHA: `51060a7682cf51810b4bc3a704829438d18cd8dc` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q3
- 검증 수준 요약: 코드 확인 25 / 추론 0 / 미확인 2

> 영역 표기: [A] Apache-2.0, [S] source-available, [?] LICENSE 미열거. 이 문서의 파일은 대부분 [S]이다(`app/`).

## Q3. 최신화와 스케줄링 {#q3}

### 3-1. 분석을 시작시키는 트리거

| 트리거 | 내용 | 위치 | 검증 |
|---|---|---|---|
| 수동(웹 UI → API) | `POST` 단일 분석. 엔진은 기본 `v2`, `legacy`는 400으로 거절. 작업을 만들고 **Redis 큐**에 넣는다 | `app/routers/analysis.py:249-300`(엔진 선택), `:350-358`(작업 생성), `:371-392`(큐 투입), `app/services/task_analysis_service.py:94` [S] | 코드 확인 |
| 워커 실행 | 큐에서 꺼낸 작업이 `analysis_worker`에서 `task_service.execute_task` → `UnifiedAnalysisEngine.execute_task` → `_execute_via_workflow` → `WorkflowAPI.execute` | `app/worker/analysis_worker.py:818-842`, `app/services/task_analysis_service.py:270`, `app/services/unified_analysis_engine.py:133-235`, `:499`, `:764` [S] | 코드 확인 |
| 일괄 분석 | 종목 목록을 각각 큐에 넣음. README는 "定时分析 / 批量分析"을 Pro 전용이라고 표기하지만 이 저장소에 일괄 분석 라우트가 있다 | `app/routers/analysis.py:1672-1841` [S], `README.md` 표 "社区版与 Pro 版的差异" | 코드 확인(README와 불일치 기록) |
| 관심종목 정기 분석 | APScheduler 작업 `watchlist_analysis`. **기본 비활성**(`WATCHLIST_ANALYSIS_ENABLED=False`), cron 기본 `0 8 * * 1-5`(평일 08:00). 결과를 모아 이메일 알림(알림은 범위 밖) | `app/main.py:903-916`, `app/core/config.py:407-408`, `app/worker/watchlist_analysis_task.py` [S] | 코드 확인 |
| CLI | `main.py`/`cli/main.py`는 레거시 `TradingAgentsGraph`를 직접 호출한다(Apache 영역에서 아직 실행 가능). 서비스 쪽 차단과는 별개 | `main.py:19-22`, `cli/main.py:1077` [A] | 코드 확인 |
| 가격 이벤트 트리거 | 없음. 손절선 근접 알림(`STOP_LOSS_ALERT_*`)은 사용자가 입력한 보유 종목 기준 알림이며 AI 분석을 시작하지 않는다 | `app/core/config.py:215-218` | 코드 확인 |
| 어시스턴트 | 자연어 질문 → 계획(plan) → 도구 실행. 분석 워크플로와 별도 경로 (04-research.md) | `app/services/planned_analysis_service.py` [S] | 코드 확인 |

### 3-2. 사전 동기화 작업 (판단과 별도로 DB를 채우는 APScheduler)

스케줄러: `AsyncIOScheduler`, 시간대 `Asia/Shanghai`, `coalesce=True`, `max_instances=1`(같은 작업 동시 실행 금지), `misfire_grace_time=30`초 (`app/main.py:535-545`, `app/core/config.py:202`, 코드 확인).
각 작업은 `settings.*_ENABLED`가 꺼져 있으면 **추가한 뒤 `pause_job`** 한다(`app/main.py:629-632` 형태 반복, 예: `pause_job("tushare_basic_info_sync")` `:631`).

| 작업 id | 주기(기본값) | 기본 활성 | 대상·저장소 | 근거 |
|---|---|---|---|---|
| 앱 시작 직후 1회 | 시작 시 `run_full_sync(force=False)` (QMT 제외 순서) | 항상 | `stock_basic_info` | `app/main.py:548-580` |
| `basics_sync_service` | 매일 06:30 (cron 미지정 시 `SYNC_STOCK_BASICS_TIME`) | 활성 | 종목 기본 정보(다중 소스) → MongoDB `stock_basic_info` | `app/main.py:587-606`, `config.py:196-200` |
| `quotes_ingestion_service` | **360초 간격**(기본 6분). `_is_trading_time()`이 아니면 건너뛰고 마지막 종가 스냅샷만 보충 | 활성 | 전종목 근실시간 시세 → `market_quotes` | `app/main.py:608-617`, `config.py:205-209`, `quotes_ingestion_service.py:617-622` |
| `tushare_basic_info_sync` | `0 2 * * *` | 활성(통합 플래그 ON) | `stock_basic_info` | `main.py:622-632`, `config.py:259` |
| `tushare_realtime_quotes_hourly` | `31 * * * *` (무료 계정 시간당 1회 제한 때문) | 활성 | `market_quotes` | `main.py:644-658`, `config.py:270-271` |
| `tushare_historical_sync` | `0 18 * * 1-5` 증분 | 활성 | 일봉 → `stock_daily_quotes` | `main.py:659-672`, `config.py:263` |
| `tushare_financial_sync` | `0 3 * * 0` (일요일) | 활성 | 재무 → `stock_financial_data` | `main.py:673-685`, `config.py:265` |
| `tushare_status_check` | `0 * * * *` | 활성 | 소스 상태 점검 | `main.py:686-698` |
| `akshare_*` | 기본정보 `0 3 * * *`, 시세 `*/30 9-15 * * 1-5`, 일봉 `0 18 * * 1-5`, 재무 `0 4 * * 0`, 상태 `30 * * * *` | 활성 | 동일 컬렉션 | `main.py:699-768`, `config.py:293-303` |
| `baostock_*` | 기본정보 `0 4 * * *`, 일봉·히스토리 `0 18 * * 1-5`, 상태 `45 * * * *` | 활성(부트스트랩의 소스 그룹은 baostock 비활성이지만 작업 플래그와 별개) | 동일 컬렉션 | `main.py:769-822`, `config.py:331-344` |
| `etf_sync` | `0 4 * * 1-5`, 강제 회귀창 30일 | 활성 | ETF → `etf_basic_info`, `etf_daily_quotes` | `main.py:824-842`, `config.py:306-308` |
| `favorites_data_sync` | `0 19 * * 1-5` | 활성 | **관심종목만** 일봉+재무 보충 | `main.py:844-858`, `config.py:274-275`, `app/worker/favorites_sync_task.py` |
| `news_sync` | `0 */2 * * *`, 종목당 최대 50건 | 활성 | **관심종목만** AKShare 뉴스 → `stock_news` | `main.py:859-902`, `config.py:401-404` |
| `trading_calendar_refresh` | 매일 18:30 (+ 시작 시 `warm_up`) | 항상 | Redis `trading_calendar:last_trade_date`, TTL 25시간 | `main.py:918-937`, `app/services/trading_calendar_service.py:1-30` |
| `hitl_expire_stale`, `skill_review_expire_stale` | 30분 간격 | 항상 | 사람 승인 대기 항목 정리 (분석 데이터와 무관) | `main.py:939-980` |

공통 사실.
- 일봉/재무 증분 동기화는 장 마감 후(18:00~19:00) 몰려 있다. 전종목 일봉 + 관심종목 보충 이중 구조다 (코드 확인).
- HK/US는 "필요할 때 가져와 캐시"하는 방식이라 정기 동기화가 **없다**: `港股/美股采用按需获取+缓存模式，不再配置定时同步任务` (`app/main.py:888-890`, 코드 확인).
- QMT(국내 증권사 터미널) 동기화는 설정만 있고 기본 비활성(`QMT_UNIFIED_ENABLED=False`, `config.py:349`). `main.py`에 QMT 작업 등록은 보이지 않는다 (코드 확인).
- **정의만 있는 작업**: `TECHNICAL_INDICATORS_MATERIALIZATION_*`(기본 평일 18:20, `config.py:278-279`)는 설정과 구현(`technical_indicator_materialization_service.py`)이 있으나 스케줄러에 등록되지 않았다 → 01-data.md 1-2 참고 (코드 확인).
- IM 요약 작업 `IM_TOPIC_DIGEST_CRON`(`config.py:282-283`)도 설정만 확인했고 등록 위치는 찾지 못했다 (미확인).

저장소 정리.

| 저장소 | 컬렉션/키 | 비고 | 검증 |
|---|---|---|---|
| MongoDB | `stock_basic_info`, `market_quotes`, `stock_daily_quotes`, `stock_financial_data`, `stock_news`, `etf_basic_info`, `etf_daily_quotes`, `social_media_messages`(사용자 업로드), `system_configs`, `datasource_groupings`, `workflows`, `prompt_templates`, `unified_analysis_tasks`, `analysis_reports`, `assistant_memory_facts`, `agent_assertions`, `agent_execution_traces` | 컬렉션명은 각 서비스에서 확인. 스키마 일부는 `config/data_contracts/*.json` | 코드 확인 |
| Redis | 작업 큐, 진행 상황 pub/sub(`task_progress:{id}`), 거래일 캐시 | `app/routers/sse.py:19-25`, `trading_calendar_service.py` | 코드 확인 |

### 3-3. 분석 직전의 "JIT" 동기화 (판단 시점 보강)

분석 도중 시장 데이터 도구가 DB의 최신 일봉 일자와 Redis의 `last_trade_date`를 비교한다. DB가 더 오래됐으면 새 스레드·새 이벤트 루프에서 `jit_sync_stock_data`를 호출해 최근 60일 일봉을 우선순위 소스로 가져와 MongoDB에 쓴다(최대 120초 대기, 실패해도 기존 데이터로 계속). A주만 대상이며 ETF·HK·US는 건너뛴다 (`core/tools/implementations/market/stock_market_data.py:215-262`, `:148-212`, `app/worker/analysis_worker.py:33-125`, 코드 확인).

### 3-4. 데이터 신선도 관리 (stale 감지와 판단 반영)

| 장치 | 감지 | 판단에 반영되는 방식 | 위치 | 검증 |
|---|---|---|---|---|
| JIT 신선도 검사 | `db_latest < last_trade_date` | 데이터를 새로 받아 채운다(판단 입력 자체를 갱신) | `stock_market_data.py:244-262` | 코드 확인 |
| 실제 데이터 일자 표시 | 요청일과 실제 일봉 일자가 다름 | 도구 출력에 "实际数据日期", "日期说明" 삽입 + 프롬프트가 본문에 실제 일자를 쓰게 강제 | `stock_market_data.py:42-87`, 시장 분석 `analysis_prompt` `market_analyst_v2.py:436-437` | 코드 확인 |
| 안정화 컷오프 | 19시 이전 → 전날 | `effective_data_date`, `stable_data_note`를 프롬프트 변수로 주입 | `core/tools/trade_date_policy.py:9-44`, `workflow_api.py:838-852` | 코드 확인 |
| 수치 충돌 | 보고서 간 현재가·시가총액·일자 불일치 | **LLM 규칙**: "必须直接点明‘工具结果口径不一致’，并降低结论强度" | 연구 매니저·리스크 매니저·trader 프롬프트(DB `prompt_templates`) | 코드 확인(프롬프트 문구), 실제 준수 여부는 미확인 |
| 분석가 품질 게이트 | 짧음·실패 문구·키워드 없음 | `quality_flags` → 연구원 프롬프트의 "质量提示"(가중치 하향 권고) | `core/agents/quality_gate.py`, `core/agents/researcher.py:164-170`, `:284-324` | 코드 확인 |
| 신뢰도 하향의 코드화 | 없음. 확신도(`confidence`)를 코드가 데이터 신선도로 깎는 로직은 찾지 못했다 | — | `grep -rn "stale\|freshness" core app/utils` 관련 확신도 보정 없음 | 코드 확인(부재) |

즉 신선도는 "입력 갱신 + 표시 + LLM에게 약하게 말하라고 지시"로 다룬다. 확신도를 숫자로 보정하는 코드는 없다.

### 3-5. 실시간 스트림

| 항목 | 내용 | 판단에 쓰나 | 위치 | 검증 |
|---|---|---|---|---|
| SSE | 작업 진행률(`task_progress:{task_id}`) | 화면 표시만 | `app/routers/sse.py:19-40` | 코드 확인 |
| WebSocket | 알림, 작업 진행 | 화면 표시만 | `app/routers/websocket_notifications.py:201`, `:293` | 코드 확인 |
| 시세 입력 | 6분 간격 폴링으로 `market_quotes` 갱신. 시세 스트림을 판단에 직접 넣지 않는다. 판단용 현재가는 DB 최신값 | 간접(DB 경유) | `quotes_ingestion_service.py`, `workflow_api.py:880-906` | 코드 확인 |
| QMT K선 미러 | 옵션 `QMT_KLINE_MIRROR_ENABLED=False` | 기본 꺼짐 | `config.py:368` | 코드 확인 |

### 3-6. 우리 시스템 관점 메모 (의견)

- 의견: "전종목 일봉을 거래 후에 한꺼번에 채우고, 분석 시점에는 DB에서 읽고 오래됐으면 그 종목만 JIT로 보충"하는 구조는 키움 REST/업비트에 그대로 옮길 만하다. 다만 JIT가 별도 스레드·이벤트 루프를 새로 만드는 방식은 복잡하므로(`stock_market_data.py:148-212`) 우리는 분석 오케스트레이터가 직접 "동기화 → 분석" 순서를 호출하는 쪽이 단순하다.
- 의견: `max_instances=1` + `coalesce`는 단일 프로세스 스케줄러의 중복 실행 방지로 유용하다.
- 코드 재사용: 스케줄러 등록부(`app/main.py`)는 [S]라 코드 재사용 불가, 구조만 참고.
