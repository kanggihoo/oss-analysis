# ai-hedge-fund — 최신화와 스케줄링

- 분석 SHA: `78b779c1389e2d1452dc29606d2c4126d859b964` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q3
- 검증 수준 요약: 코드 확인 38 / 추론 0 / 미확인 0

## Q3. 최신화와 스케줄링 {#q3}

한 줄 요약: **내장 스케줄러는 없다.** 외부(cron, launchd, 사람)가 장 마감 후 `aihf paper tick <fund>`를 부르는 구조이고, tick은 "다음 미기록 세션 1개"만 진행하는 멱등 연산이다. 데이터 사전 동기화(DB 적재) 작업은 없고, 판단 때마다 FD API를 읽고 디스크 캐시에 쌓는다.

### 트리거

| 트리거 | 설명 | 근거 | 검증 |
|---|---|---|---|
| 수동 TUI | `aihf`(인자 없음) → Paper trading → 펀드에서 Enter → 승인 화면 → 실행 | `hedge_fund/run.py:80-86`, `hedge_fund/tui/app.py:1890-1913` | 코드 확인 |
| 수동/외부 CLI | `aihf paper tick <name>`. docstring 예: `30 18 * * 1-5  aihf paper tick alpha >> ~/.hedge-fund/paper/alpha/tick.log 2>&1` | `hedge_fund/run.py:23-30`, `run.py:255-267` | 코드 확인 |
| 백테스트 | `aihf backtest <mandate> --universe ...` 로 과거 세션을 순차 재생 | `hedge_fund/run.py:183-221`, `hedge_fund/backtesting/fund.py:106-161` | 코드 확인 |
| 내장 cron/APScheduler/GitHub Actions | 없음. `.github/`에는 이슈 템플릿 2개뿐. ROADMAP도 "built-in calendar-aware daemon is next"로 미구현 명시 | `git ls-files`(.github/ISSUE_TEMPLATE만), `ROADMAP.md:98` | 코드 확인 |
| 이벤트(가격 조건) | 없음 | `hedge_fund/` 전체 grep(schedule/cron/websocket) 결과 해당 없음 | 코드 확인 |

### 주기와 시점

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 리밸런스 주기 | mandate의 `rebalance: daily | weekly | monthly`(기본 `weekly`). 해당 주기의 **첫 세션**이 리밸런스(결정) 세션. 펀드의 첫 세션은 항상 리밸런스 | `hedge_fund/fund/spec.py:86-89`, `hedge_fund/pipeline/session.py:201-217` | 코드 확인 |
| 주기 판정 방식 | 현재 세션과 직전 세션만 비교(ISO 주/달력 월). 이후 데이터는 보지 않아 라이브 tick과 백테스트가 일치 | `session.py:16-19`, `session.py:212-217` | 코드 확인 |
| 거래일 캘린더 | 별도 거래소 캘린더 없음. **벤치마크(SPY)의 실제 일봉 bar가 있는 날 = 거래일**. 휴장일은 자연히 빠진다 | `hedge_fund/data/sessions.py:21-30`, `hedge_fund/backtesting/fund.py:11-12` | 코드 확인 |
| 권장 시각 | 예시 cron은 평일 18:30(`30 18 * * 1-5`). 시간대는 문서에 없음. 코드는 뉴욕 날짜 기준 "오늘-1일"까지만 완료로 간주하므로, 마감 당일 tick은 해당 당일 세션을 아직 처리하지 못하고 **다음 날부터** 처리 가능(오늘은 제외) | `hedge_fund/data/sessions.py:12-14` | 코드 확인 |
| 신규 펀드 시작점 | 한 번도 tick하지 않았으면 가장 최근 완료 세션(14일 lookback 내)에서 시작 | `hedge_fund/paper/tick.py:32-34`, `tick.py:41-52` | 코드 확인 |
| 누락 보정 | 하루를 건너뛰어도 건너뛰지 않는다. 다음 tick은 "마지막 기록 세션 다음 벤치마크 세션"을 처리하므로 일주일 쉬면 일주일치 tick 필요 | `tick.py:1-15`, `tick.py:41-52` | 코드 확인 |
| 멱등성 | 이미 기록된 세션을 `--session`으로 주면 기록을 그대로 반환. 처리할 세션이 없으면 `NothingDue` | `tick.py:55-86` | 코드 확인 |
| 재실행 | `--again`: 마지막 세션 기록을 `ledger/superseded/<session>.<hash12>.json`으로 이동하고 브로커 장부를 직전 상태로 복원한 뒤 같은 종가로 다시 판단 | `tick.py:89-118`, `paper/ledger.py:93-104`, `brokers/paper.py:51-59` | 코드 확인 |

### 세션 1회(advance)의 순서

`reconcile → pending 결정 체결 → 장부 mark → (리밸런스 세션이면) 새 평가` 순서이며 모든 모드가 같은 함수를 쓴다.

| 단계 | 동작 | 근거 | 검증 |
|---|---|---|---|
| 0 | 킬스위치/순서/완료 세션 검사 | `pipeline/session.py:124-133` | 코드 확인 |
| 1 | 브로커 장부와 ledger 상태 대조(불일치 시 `BookMismatch`, 자동 복구 안 함) | `session.py:135`, `session.py:185-198` | 코드 확인 |
| 2 | `state.pending`이 있으면 `execute_decision`(체결). 직전일이 결정일이 아니면 **뷰를 다시 평가(refresh)**해서 체결 | `session.py:137-139`, `stages.py:129-132` | 코드 확인 |
| 3 | 보유 종목 + 벤치마크의 정확 종가로 NAV 평가 | `session.py:141-146` | 코드 확인 |
| 4 | 리밸런스 세션이면 `assess_fund` → 다음 세션 체결 대기(`pending`) | `session.py:148-149` | 코드 확인 |
| 5 | `SessionRecord`에 해시를 계산해 ledger에 append | `session.py:151-170`, `paper/ledger.py:69-91` | 코드 확인 |

### 사전 동기화

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 별도 동기화 작업 | **없음.** DB(PostgreSQL/Mongo 등)도 없다. 저장소는 `~/.hedge-fund/` 아래 파일(JSON/YAML)뿐 | `hedge_fund/paths.py:1-28` | 코드 확인 |
| 저장 구조 | `mandates/<name>.yaml`, `paper/<name>/{fund.yaml, broker.json, ledger/<session>.json, control.json, events.jsonl}`, `research/*.json`, `cache/{data,llm,breakpoints}` | `paths.py:8-11`, `paper/deployed.py:25-26`, `paper/ledger.py:23-26` | 코드 확인 |
| TUI 사전 warm(선택) | TUI 백테스트/실행 화면은 세션을 돌리기 전에 가격·재무지표를 `ThreadPoolExecutor(max_workers=8)`로 미리 캐시하고, 에이전트를 먼저 돌려 LLM 캐시를 채운다. 실제 판단은 `tick`이 하고 warm은 best-effort(예외 무시) | `hedge_fund/tui/app.py:2960-3030`, `tui/app.py:2143-2150`, `tui/app.py:2238-2262` | 코드 확인 |
| ME breakpoints | 35일이 지나면 재다운로드, 실패해도 기존 캐시 사용(없으면 오류) | `features/breakpoints.py:36`, `breakpoints.py:108-131` | 코드 확인 |

### 데이터 신선도 관리 (stale 감지)

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| stale 감지 | **판단에 반영하는 신선도 장치는 없다.** 확신도 하향 등 없음. 대신 (a) 종가 bar가 없으면 종목 제외, (b) 일봉 캐시는 "마감 후 가져온 것"만 재사용, (c) 아직 완료되지 않은 세션 요청은 오류 | `stages.py:190-194`, `data/cached.py:135-147`, `data/sessions.py:12-14` | 코드 확인 |
| 공시 재료의 낡음 | 같은 공시 구간에서는 프롬프트가 동일해 LLM 캐시가 적중해 결과가 변하지 않는다(의도된 동작: "an agent only re-reasons when a new filing changes its snapshot") | `features/snapshot.py:9-13`, `snapshot.py:77-85` | 코드 확인 |
| PEAD 신선도 | 이벤트가 기준일로부터 4일을 넘으면 신호 0 | `signals/pead.py:73-75` | 코드 확인 |
| 가격 mark 신선도 | 분석 mark는 7일 lookback 내 마지막 종가라 휴장·연휴는 흡수하지만 그 이상 오래된 값은 종목 제외 | `stages.py:37`, `stages.py:173-194` | 코드 확인 |

### 실패/중단 정책 (스케줄 관점)

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 자동 halt | `advance`나 ledger append 중 어떤 예외든 발생하면 `tick_failed` 이벤트 기록 + `control.json`에 halt 설정. 이후 모든 tick이 `FundHalted`로 거부된다. cron이 깨진 장부에 계속 거래하는 일을 막는 목적 | `paper/tick.py:13-15`, `tick.py:136-142`, `pipeline/session.py:125-126` | 코드 확인 |
| 수동 킬스위치 | `aihf paper halt <name> --reason ...`, `resume` | `run.py:283-289`, `paper/ledger.py:138-149` | 코드 확인 |
| 이벤트 로그 | `events.jsonl`에 tick/failure/halt/resume/redo 기록 | `paper/ledger.py:153-161`, `tick.py:143-147` | 코드 확인 |
| 알림 | 범위 밖(ROADMAP에 "notifications and a heartbeat are next"만 언급) | `ROADMAP.md:99` | 코드 확인 |

### 실시간 스트림

없음. WebSocket/스트리밍 시세 코드가 없다(`hedge_fund/` grep 결과). 유일한 "스트림"은 LLM 응답 토큰 스트리밍(`ChatLLM.complete`의 `on_token`)이며 TUI에서 논거를 타이핑하듯 보여주는 **화면 표시 전용**이다(`llm/client.py:89-103`, `llm/watch.py:1-13`). 판단에는 영향이 없다. (`코드 확인`)

## 근거 표

| 구분 | 위치 | 식별자 | 설명 | 검증 |
|---|---|---|---|---|
| 진입점 | `hedge_fund/run.py:71-96` | `main()` | TUI / backtest / paper 분기 | 코드 확인 |
| tick | `hedge_fund/paper/tick.py:55-86` | `tick()` | 다음 미기록 세션 1개 진행 | 코드 확인 |
| 다음 세션 | `hedge_fund/paper/tick.py:41-52` | `next_session()` | 벤치마크 일봉 기준 | 코드 확인 |
| 세션 | `hedge_fund/pipeline/session.py:109-170` | `advance()` | 하루 단위 공통 경로 | 코드 확인 |
| 리밸런스 규칙 | `hedge_fund/pipeline/session.py:201-217` | `is_rebalance_session()` | 첫 세션 규칙 | 코드 확인 |
| 완료 세션 | `hedge_fund/data/sessions.py:12-14` | `completed_through()` | 뉴욕 기준 어제까지 | 코드 확인 |
