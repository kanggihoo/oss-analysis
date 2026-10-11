# dexter — 최신화와 스케줄링

- 분석 SHA: `534f6be455523c5926eba72bdaf4f914555be5c9` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q3
- 검증 수준 요약: 코드 확인 약 22 / 추론 1 / 미확인 1 (근사치)

> 알림 전달(WhatsApp)은 범위 밖이다. 여기서는 "정기 실행 트리거가 어떻게 만들어지고 어떤 제약을 갖는지"만 기록한다.

## Q3. 최신화와 스케줄링

### 3.1 트리거

| 트리거 | 설명 | 근거 | 검증 |
|---|---|---|---|
| 수동 질의(기본) | CLI에서 사용자가 입력하면 `AgentRunnerController.runQuery()`가 `Agent.create()` 후 `agent.run()` 실행, `maxIterations: 10` | `src/cli.ts:231-232`, `src/controllers/agent-runner.ts:160-198` | 코드 확인 |
| WhatsApp 수신 메시지 | 게이트웨이가 메시지마다 에이전트를 실행(알림 범위 밖) | `src/gateway/gateway.ts:44-213` | 코드 확인 |
| **cron 작업** | `.dexter/cron/jobs.json`의 작업을 러너가 실행. 스케줄 종류 `at`(1회)/`every`(주기 ms, 최소 60초)/`cron`(croner 표현식+tz) | `src/cron/store.ts:7`, `src/cron/types.ts:3-7`, `src/cron/schedule.ts:10-51`, `src/tools/cron/cron-tool.ts:54-69` | 코드 확인 |
| **heartbeat** | `HEARTBEAT.md` 체크리스트를 주기적으로 에이전트에 던지는 작업. 게이트웨이 시작 시 cron 작업("Heartbeat", `every`)으로 자동 등록 | `src/cron/heartbeat-migration.ts:17-92`, `src/gateway/heartbeat/prompt.ts:46-73` | 코드 확인 |
| 에이전트 자신이 작업 생성 | LLM이 `cron`/`heartbeat` 도구로 사용자 요청("NVDA 150 되면 알려줘")을 스케줄로 저장 | `src/tools/cron/cron-tool.ts:9-52`, `src/tools/heartbeat/heartbeat-tool.ts:13-34` | 코드 확인 |
| 가격 조건 이벤트 | **없음.** "가격이 X 도달" 감시는 이벤트 구독이 아니라 cron이 주기적으로 LLM에게 "현재가 확인 후 조건 충족 시만 알려라"고 묻는 폴링이다 | `cron-tool.ts:42-43`, `cron/executor.ts:132-136` | 코드 확인 |
| GitHub Actions / 외부 스케줄러 | 없음 (`.github/workflows`는 CI·리베이스뿐) | `.github/workflows/ci.yml`, `rebase-on-label.yml` | 코드 확인(없음) |

### 3.2 주기와 시점

| 항목 | 값 | 근거 | 검증 |
|---|---|---|---|
| 러너 폴링 | 가장 이른 `nextRunAtMs`까지 대기하되 **최대 60초 단위로 깨어나** jobs.json을 다시 읽음(도구로 바뀐 작업 즉시 반영) | `cron/runner.ts:13,54-108` | 코드 확인 |
| 실행 방식 | 만기 작업을 **직렬** 실행, 한 번에 하나(`running` 플래그) | `cron/runner.ts:54-76` | 코드 확인 |
| heartbeat 기본 주기 | 설정 파싱 기본 30분, 그러나 `heartbeat` 도구가 자동 활성화할 때 기본 10분(불일치) | `cron/heartbeat-migration.ts:30`, `gateway/config.ts:160` vs `tools/heartbeat/heartbeat-tool.ts:52-55` | 코드 확인 |
| 활성 시간(active hours) | `start/end`(HH:MM), 기본 요일 월~금, 기본 시간대 America/New_York. 시간 밖이면 건너뛰고 다음 실행만 예약. **거래일 캘린더(휴장일) 확인은 없음** | `cron/executor.ts:49-70,102-106`, `cron/types.ts:11-16` | 코드 확인 |
| heartbeat 기본 체크리스트 | "S&P500/NASDAQ/Dow 1세션 2% 초과 변동"과 "주요 실적/연준/시장 이벤트" | `gateway/heartbeat/prompt.ts:7-8` | 코드 확인 |
| 작업 1회 실행 설정 | `maxIterations: 6` 고정, 격리 세션(대화 이력·메모리 비활성), 채널 `whatsapp` | `cron/executor.ts:141-149`, `gateway/agent-runner.ts:75-76,92` | 코드 확인 |
| 설정값 무시 | `gateway.heartbeat.maxIterations`(기본 6)는 파싱되지만 cron 실행기는 상수 6을 쓴다 → 설정이 효과 없음 | `gateway/config.ts:44,164` vs `cron/executor.ts:146` | 코드 확인 |
| 모델 선택 | 작업별 `payload.model` 없으면 설정 `modelId` (기본 `gpt-6-astra`) | `cron/executor.ts:127-129` | 코드 확인 |

### 3.3 결과 억제(suppression) — 정기 모니터링의 "무소식" 처리

- 프롬프트가 "조건 미충족이면 정확히 `HEARTBEAT_OK`만 답하라"고 지시한다 (`cron/executor.ts:136`).
- 코드가 응답을 사후 검사해 억제한다: 빈 응답, `HEARTBEAT_OK` 단독/병기, **정규식 휴리스틱**("no action needed", "nothing to report", "no change" 등), **24시간 내 동일 문구 중복** (`gateway/heartbeat/suppression.ts:16,43-49,58-97`). 
- 이것은 LLM 출력을 규칙으로 걸러내는 유일한 후처리지만 **투자 판단이 아니라 메시지 발송 여부**를 정한다. 검증: 코드 확인.
- 억제 상태는 프로세스 메모리에만 있어 재시작 시 초기화된다 (`cron/executor.ts:23-24`). 검증: 코드 확인.

### 3.4 정기 실행과 알림 경로의 결합 (제약)

- cron 작업은 실행 전 **WhatsApp 전달 대상 세션을 찾고(`findTargetSession`), 없으면 작업 자체를 건너뛴다** (`cron/executor.ts:81-88,110-116`). 즉 알림 채널 없이 "리서치만 정기 실행"하는 모드는 현재 구조에 없다. 우리 시스템에 쓰려면 전달부(`executor.ts:172-179`)를 분리해야 한다. 검증: 코드 확인.
- 게이트웨이 시작 시 `ensureHeartbeatCronJob()`은 `await` 없이 호출된다(`gateway/gateway.ts:230`). 러너가 곧바로 시작되지만 60초 주기로 jobs.json을 다시 읽으므로(`runner.ts:86-108`) 실사용 영향은 작을 것으로 보인다. 검증: 코드 확인(영향은 추론).
- 오류 시 백오프: 30초→1분→5분→15분→60분, 1회성(`at`) 작업은 3회 후 비활성, 스케줄 계산 오류 3회 시 비활성 (`cron/executor.ts:26-35,199-255`). 검증: 코드 확인.

### 3.5 사전 동기화

- **없음.** 판단과 별개로 데이터를 DB에 미리 쌓는 작업이 없다. 근거: 스케줄러가 호출하는 것은 `runAgentForMessage()`(에이전트 질의)뿐이다 (`cron/executor.ts:141-149`). `.dexter/`에 쌓이는 것은 API 응답 캐시(질의 시 채움), 스크래치패드, 메모리 인덱스뿐이다 (`utils/cache.ts:32`, `agent/scratchpad.ts:67,91-97`, `memory/index.ts:89`). 검증: 코드 확인(없음).
- 메모리 인덱서는 파일 변경을 감시해 SQLite를 갱신한다(데이터 사전 동기화가 아니라 사용자 메모 색인) (`memory/index.ts:110-115`). 검증: 코드 확인.

### 3.6 데이터 신선도 관리

- **stale 감지 없음.** 데이터에 수집 시각·기준일을 붙여 판단에 반영하는 코드가 없고, 신선도는 캐시 TTL(15분~24시간, 01-data.md 참조)로만 간접 통제된다. 주가 스냅샷은 캐시하지 않아 항상 최신이다(`stock-price.ts:24`). 확신도 하향 같은 후처리 없음. 검증: 코드 확인(`grep -i "stale\|fresh"` 결과에 데이터 신선도 관련 코드 없음).
- 최근 데이터를 쓰라는 지시는 프롬프트에 "Current date"만 있다 (`agent/prompts.ts:236`). 검증: 코드 확인.

### 3.7 실시간 스트림

- 금융 데이터에 대한 WebSocket 등 **실시간 스트림 없음** (`grep -i "websocket\|wss://"` 비-WhatsApp 코드 0건). "스트리밍"은 LLM 응답 토큰 스트림과 UI 진행 표시용이다 (`agent/agent.ts:299-360`). WhatsApp 연결은 Baileys 세션이며 알림 범위 밖이다. 검증: 코드 확인(없음).
