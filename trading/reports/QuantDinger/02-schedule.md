# QuantDinger — 최신화와 스케줄링

- 분석 SHA: `ba8cd667acca3e934bbc1cb354922eff413393dc` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q3
- 검증 수준 요약: 코드 확인 29 / 추론 0 / 미확인 0 (본문 표기 건수 기준)

> 약어: `BE` = `backend_api_python/app`.

**한 줄 요약**: 분석 자체는 *요청 시점에 데이터를 새로 가져오는* 온디맨드 방식이다. 주기 실행은 (1) 포트폴리오 모니터(스케줄러 프로세스의 데몬 스레드, 30초 틱)와 (2) Celery Beat의 유지보수 작업(펀더멘털 동기화·사후검증·보정)뿐이고, **분석 자체를 정기 실행하는 Celery Beat 항목은 없다.**

## Q3-1. 트리거 {#q3}

| 트리거 | 무엇이 시작시키나 | 주기·조건 | 근거 | 검증 |
|---|---|---|---|---|
| 사용자 요청 | `POST /analyze`(로그인 필수). `async_submit=true`면 대기 레코드를 만들고 백그라운드 실행 | 동일 `사용자\|시장\|심볼\|TF`는 330초 동안 중복 실행 차단(in-flight 락). 크레딧 선차감·실패 시 자동 환불 | `BE/routes/fast_analysis.py:73-217`, `BE/services/fast_analysis_tasks.py:20-48,90-149` | 코드 확인 |
| 백그라운드 실행기 | `CELERY_TASKS_ENABLED=true`면 Celery 태스크 `quantdinger.tasks.fast_analysis`(큐 `ai`), 아니면 데몬 스레드 | 기본값은 꺼짐(`false`). docker-compose는 `true` | `BE/services/fast_analysis_tasks.py:51-54,152-159`, `BE/tasks/fast_analysis.py:8-13`, `BE/celery_app.py:52`, `docker-compose.yml:62,302` | 코드 확인 |
| 포트폴리오 모니터 | `_monitor_loop` 데몬 스레드가 **30초마다** 깨어나 `is_active=1 AND next_run_at <= NOW()`인 모니터를 최대 N개(`PORTFOLIO_MONITOR_DUE_BATCH_LIMIT`, 기본 5, 상한 20) 실행 | 모니터별 `run_interval_minutes`(기본 60분, 상한 1주). 실행 후 `next_run_at`을 DB `NOW()+INTERVAL`로 갱신 | `BE/services/portfolio_monitor.py:37-41,156-214,1747-1827` | 코드 확인 |
| 모니터 분석 방식 | 대상 포지션을 `(시장,심볼)`로 중복 제거 후 최대 5개 스레드로 `FastAnalysisService.analyze(timeframe='1D')`를 호출. **보유 수량·평단·손익은 분석 입력이 아님**(보고서 표시용) | 관심종목(`qd_watchlist`)에서 빠졌거나 크레딧 부족이면 건너뛰고 일정만 전진 | `BE/services/portfolio_monitor.py:292-347,350-455,1337-1435` | 코드 확인 |
| 가격 알림 | 같은 루프에서 `qd_position_alerts`를 틱당 최대 300개 검사(가격 조건 이벤트). 알림 내부는 범위 밖 | 30초 | `BE/services/portfolio_monitor.py:34,1483-1560` | 코드 확인(알림 세부는 범위 밖) |
| Celery Beat | 아래 Q3-2 표 | 아래 표 | `BE/celery_app.py:62-91` | 코드 확인 |
| 스케줄러 프로세스 | `commands/scheduler.py`가 리더 리스(`scheduler-global-services`)를 잡은 인스턴스만 `_start_scheduler_services()`로 포트폴리오 모니터 등을 시작 | 리스 30초(`SCHEDULER_LEASE_SEC`), 10초마다 갱신/하트비트 | `BE/commands/scheduler.py:8-52`, `BE/startup.py:261-278` | 코드 확인 |
| 프로세스 역할 | API·CELERY 역할은 프로세스-로컬 백그라운드 서비스를 시작하지 않음. 그 외(단일 프로세스 모드)는 `include_celery_managed=True`로 보정·사후검증 스레드까지 시작 | `ENABLE_PORTFOLIO_MONITOR=true`가 기본 | `BE/startup.py:60-71,213-236,279-292` | 코드 확인 |
| 거래일 캘린더 | **분석·모니터는 캘린더를 확인하지 않는다.** `market_schedule`(XNYS·XHKG·XSHG)은 전략 실행·백테스트 쪽에서만 import됨 | 주말·휴장일에도 같은 주기로 분석 | `BE/services/market_schedule.py:10-15`, import 목록(grep): `events/bar_clock.py`, `services/trading_executor.py`, `services/strategy_v2/market_data.py`, `services/backtest/metrics.py`, `services/strategy_runtime/timeframes.py` | 코드 확인 |
| 이벤트(가격 조건) 트리거 | 분석을 가격 이벤트로 시작하는 경로는 없음. 가격 이벤트는 알림에만 연결 | — | `BE/services/portfolio_monitor.py:1483-1560` | 코드 확인 |

> 가이드의 "Celery 정기 모니터링"은 **코드와 다르다.** 포트폴리오 모니터는 Celery 태스크가 아니라 스케줄러 프로세스(또는 단일 프로세스)의 스레드다(`BE/startup.py:60-71`, `BE/services/portfolio_monitor.py:1830-1841`). Celery Beat에 들어 있는 것은 아래 표의 유지보수 작업이다.

## Q3-2. Celery Beat 스케줄 전체 (`BE/celery_app.py:62-91`)

| Beat 이름 | 태스크 | 주기 | 큐 | 하는 일 | 근거 | 검증 |
|---|---|---|---|---|---|---|
| `fundamental-sync` | `fundamental_sync_tick` | 60초 | maintenance | 예약된 유니버스를 큐에 넣고 항목 1개 처리, 남았으면 2초 뒤 재호출 | `BE/tasks/fundamental_sync.py:5-12`, `BE/services/fundamental_sync.py:98-138` | 코드 확인 |
| `reflection-cycle` | `reflection` | 86,400초(`REFLECTION_WORKER_INTERVAL_SEC`, 최소 300) | maintenance | 7일 이상 지난 미검증 판단을 현재가로 채점, 채점이 있으면 보정 실행 | `BE/tasks/maintenance.py:36-50`, `BE/services/reflection.py:27-48` | 코드 확인 |
| `ai-calibration-cycle` | `ai_calibration` | 86,400초(최소 3,600) | maintenance | 시장별(`AI_CALIBRATION_MARKETS`, 기본 Crypto) 매수/매도 임계값 재탐색 | `BE/tasks/maintenance.py:53-81` | 코드 확인 |
| `market-catalog-sync` | `market_catalog_sync` | 86,400초(최소 900) | maintenance | 종목 마스터 동기화(판단 데이터 아님) | `BE/tasks/maintenance.py:84-98` | 코드 확인 |
| `expire-billed-agent-jobs` | `expire_agent_jobs` | 60초 | maintenance | 에이전트 잡 만료(범위 밖) | `BE/celery_app.py:67-70` | 코드 확인 |
| `celery-worker-heartbeat`, `runtime-metadata-cleanup` | 하트비트(10초), 정리(86,400초) | — | maintenance | 운영 유지 | `BE/celery_app.py:83-90` | 코드 확인 |

Celery 타임존은 `TZ` 환경변수, 기본 `Asia/Shanghai`다(`BE/celery_app.py:32`). 한국 배포 시 `TZ`를 명시해야 한다(의견).

## Q3-3. 사전 동기화 (판단과 별도로 DB에 쌓는 데이터)

| 대상 | 방식 | 저장소 | 주기 | 근거 | 검증 |
|---|---|---|---|---|---|
| 펀더멘털(미국·홍콩·중국 A주) | 관리자가 유니버스별로 스케줄을 켜면 Beat가 매일(`next_at + 1 day`) 작업을 큐에 넣고, 항목 단위(리스 5분, 최대 3회 시도, 실패 시 60초 후 재시도)로 처리. 모드 `history`(yfinance 분기 재무, 미국·홍콩만) / `current`(수집기의 펀더멘털 호출) | PostgreSQL `qd_fundamental_snapshots`(+ `qd_fundamental_sync_jobs/items/schedules`). 컬럼: revenue, net_income, net_income_ttm, book_value, shareholder_equity, total_debt, free_cash_flow, shares_outstanding, market_cap, pe_ratio, pb_ratio, return_on_equity, revenue_growth, debt_to_equity + `period_end`, `available_at`, `metadata_json` | `BE/services/fundamental_sync.py:33-38,41-106,98-138`, `BE/services/fundamental_data.py:17-32,395-420`, `BE/routes/fundamental_sync.py:27-42` | 코드 확인 |
| 분석 중 write-back | 분석이 제공자 호출로 펀더멘털을 새로 받으면 같은 테이블에 현재 스냅샷으로 저장(`available_at = 오늘`, `pointInTime: true`) | 동일 | 분석 시점 | `BE/services/market_data_collector.py:529-547`, `BE/services/fundamental_data.py:310-379` | 코드 확인 |
| 가격·K선·뉴스·매크로·암호화폐 지표 | **사전 동기화 없음.** 분석할 때마다 가져오고 단기 캐시(초~시간 단위)만 둠. 매크로만 글로벌 마켓 페이지가 채운 6시간 캐시를 *우연히* 재사용 | 메모리/Redis 캐시 | — | `BE/services/market_data_collector.py:2349-2353`, `BE/routes/global_market.py:145-154` | 코드 확인 |
| 판단 이력 | 분석 결과·점수·지표 스냅샷·합의 점수 저장 | `qd_analysis_memory`(+ `qd_analysis_tasks`) | 분석 시점 | `BE/services/analysis_memory.py:84-209,211-268`, `BE/services/fast_analysis.py:1548-1627` | 코드 확인 |

펀더멘털 동기화는 **사용자가 만든 유니버스(최대 5,000종목)에 대해서만** 돈다(`members_for`, `BE/services/fundamental_sync.py:33-38`). 자동으로 모든 분석 종목을 사전 적재하는 구조가 아니다(코드 확인).

## Q3-4. 데이터 신선도 관리

| 장치 | 동작 | 판단 반영 | 근거 | 검증 |
|---|---|---|---|---|
| 관측별 fresh 판정 | `retrieved_at - as_of <= freshness_limit_seconds`이면 fresh. `stale`/`expired` 플래그도 stale | `freshness_ratio = fresh 메트릭 수 / 커버된 메트릭 수` | `BE/professional_report/quality.py:29-33,95-102,109-111` | 코드 확인 |
| 품질 점수 | `0.50×coverage + 0.35×freshness + 0.15×(1−conflict)` | 리스크 플랜의 `data_quality_score`로 포지션 상한을 곱함 | `BE/professional_report/quality.py:112-115`, `BE/professional_report/risk.py:184-186` | 코드 확인 |
| 결론 강도 구간 | `none`: coverage<0.60 또는 freshness<0.50 또는 conflict>0.25 / `low`: <0.80, <0.70, >0.10 / `medium`: <0.95, <0.90, >0 / 그 외 `high` | `none`이면 방향성 결정 불가 → **BUY/SELL을 HOLD로 강등**. 확신도 상한 none 35, low 55, medium 75, high 100 | `BE/professional_report/quality.py:14,129-140,162-186` | 코드 확인 |
| 필수 메트릭(시장별) | 미국·홍콩: `quote.price, ohlcv.latest_bar, indicator.rsi.value, indicator.moving_averages.trend, market_cap, revenue_growth, profit_margin`. 암호화폐: `quote.price, ohlcv.latest_bar, indicator.rsi.value, indicator.moving_averages.trend, crypto.volume_24h, crypto.funding_rate, crypto.open_interest`. 그 외 시장: `quote.price, ohlcv.latest_bar` | 필수 7개 중 5개 이상 있어야 coverage ≥ 0.6 | `BE/professional_report/snapshot.py:433-447` | 코드 확인 |
| 펀더멘털 DB 신선도 | `ingested_at` 기준 24시간 초과(`snapshot_age`)면 재조회 필요, 보고서 기준일이 200일 초과(`report_age`)면 사유만 기록하고 재조회는 강제하지 않음 | 재조회 시 제공자 호출. 제공자 실패하면 `database_fallback` + `refresh_failed` 표시로 오래된 값을 그대로 사용 | `BE/services/fundamental_data.py:277-300`, `BE/services/market_data_collector.py:515-553` | 코드 확인 |
| 전략 AI 필터의 봉 신선도 | 마지막 봉 나이가 `주기×3`을 넘으면 `is_stale`. `fresh/stale_timeframes`, `data_quality: complete|partial|unavailable`을 LLM 입력에 포함 | LLM이 판단(코드가 직접 차단하지 않음) | `BE/services/ai_decision_context.py:119-141,269-291` | 코드 확인 |
| 시세·지표·매크로 | as_of를 안 줘서 항상 fresh로 기록됨 | 신선도 감점 없음 | `BE/professional_report/snapshot.py:162,229-237,260-263` | 코드 확인 |

## Q3-5. 실시간 스트림

- 가격 웹소켓(`market_price_stream`, `shared_market_price_feed`)은 전략 실행기(`trading_executor`)가 쓴다. AI 분석 경로에서 import하지 않는다(코드 확인: `BE/services/trading_executor.py:882,2013`, 분석 파일 grep 결과 없음).
- 따라서 "판단에 쓰는가 / 화면 표시에만 쓰는가"의 답은 **둘 다 아니다. 전략 주문 실행용**이다.
