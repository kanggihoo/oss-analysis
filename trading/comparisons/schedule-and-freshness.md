# 스케줄링과 데이터 신선도 비교 (Q3)

- 작성일: 2026-10-09
- 기준: 각 레포 `reports/<repo>/02-schedule.md` (SHA는 `../repos.lock.tsv`)

## 1. 트리거와 주기

| 레포 | 분석 트리거 | 주기 / 시점 | 거래일 캘린더 |
|---|---|---|---|
| TradingAgents | 수동 (CLI, API, 백테스트) | 없음 | ❌ |
| TradingAgents-CN | 수동 중심 (웹 → Redis 큐 → 워커). 정기 분석은 기본 꺼짐 | 관심종목 자동 분석 18:30 (옵션) | ✅ 18:30 갱신 |
| ai-hedge-fund | 외부 cron이 `aihf paper tick` 호출 (멱등, 1회 1세션) | 리밸런스 daily/weekly/monthly | 벤치마크 거래일 그리드 |
| daily_stock_analysis | GitHub Actions cron `0 10 * * 1-5` 또는 로컬 `schedule` 라이브러리 | 하루 1회 (KST 19:00) | ✅ 6개 시장 (한국 포함) |
| Vibe-Trading | 앱 내부 asyncio 폴러 (60초 틱, 기본 꺼짐) | 플레이북 cron (예: 평일 08:30 장전 브리핑) | △ |
| OpenAlice | Issue 파일 frontmatter `when` (at/every/cron) → 60초 스캐너 | 사용자 정의, 동시 8개 상한 | ❌ (놓친 cron은 기본 catch-up) |
| dexter | 수동 질의. cron/heartbeat(기본 30분)는 WhatsApp 전달에 묶여 있음 | — | ❌ |
| QuantDinger | 온디맨드. 포트폴리오 모니터는 스케줄러 프로세스 스레드 (30초 틱, 모니터별 기본 60분) | Celery Beat: 펀더멘털 동기화, 사후검증, 보정 | ❌ |

## 2. 사전 동기화 (판단과 별개로 데이터를 미리 쌓는가)

| 레포 | 사전 동기화 | 저장소 |
|---|---|---|
| TradingAgents-CN | ✅ APScheduler: 일봉·재무 18~19시, 시세 6분, 뉴스 2시간 (관심종목만). 분석 직전 부족분 보충 (최대 120초) | MongoDB |
| QuantDinger | ✅ 펀더멘털 스냅샷 (메모리 30분 → DB 24시간 → 제공자 호출 후 write-back) | PostgreSQL |
| OpenAlice | △ RSS 10분 주기, TraderHub 보드 캐시 | 파일 |
| 나머지 | ❌ 분석할 때 가져옴 (일부 디스크 캐시) | — |

## 3. 오래된 데이터(stale) 처리

| 레포 | 감지 | 판단 반영 |
|---|---|---|
| QuantDinger | ✅ 품질 게이트 | ✅ HOLD 강등, 확신도 상한 |
| daily_stock_analysis | ✅ 데이터 품질 블록, 장 단계 | ✅ stale/fallback이면 확신도 High 금지 |
| TradingAgents | △ OHLCV 10일 규칙 | ❌ |
| OpenAlice | △ `isLatestActual`, `staleTradingDays`로 노출만 | ❌ |
| Vibe-Trading | △ 프롬프트의 as-of 규칙뿐 | ❌ |
| 나머지 | ❌ | ❌ |

## 4. 우리 시스템에 대한 결론 (의견)

- **트리거**: 우선 하루 1~2회 cron이면 충분하다(DSA 방식).
  - 국장: 장 마감 후 1회
  - 코인: 정해진 시각에 1회
  - 거래일 캘린더는 반드시 둔다.
- **사전 동기화**: CN 방식으로 **관심종목만** DB에 미리 쌓는다. 키움 호출 제한(초당 5건)을 생각하면 판단 시점에 몰아서 호출하는 것보다 안전하다.
- **신선도**: QD·DSA처럼 데이터 품질을 판단 입력에 넣는다. 오래된 데이터면 코드가 확신도를 깎거나 `REVIEW`로 보낸다.
- **실시간 스트림**: 8개 모두 판단에는 실시간 스트림을 쓰지 않는다. 업비트·키움 WebSocket은 대시보드 표시와 손절 감시용으로만 쓰는 게 맞다.
