# Vibe-Trading — 최신화와 스케줄링

- 분석 SHA: `e532650b527ba3fb146ef00d533f6fc5040d5d2d` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q3
- 검증 수준 요약: 코드 확인 19 / 추론 1 / 미확인 0

> 한 줄 결론: **데이터를 미리 쌓는 동기화 작업이 없다.** 모든 분석은 실행 시점에 도구로 가져온다. 정기 실행은 "스케줄 리서치"(플레이북 프롬프트를 cron으로 에이전트 세션에 던지는 방식)와 "라이브 러너" 두 가지이고, 둘 다 기본값은 꺼짐이다.

<a id="q3"></a>
## Q3. 트리거와 주기

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 수동 트리거 | CLI(`vibe-trading`), 웹 UI 채팅, MCP 서버(`mcp_server.py`). 모두 `AgentLoop.run()`으로 합류(웹은 `session/service.py`, CLI는 `cli/_legacy.py`) | `agent/src/session/service.py:543-547`, `agent/cli/_legacy.py:1248` | 코드 확인 |
| 스케줄 리서치 | 앱 내부 `asyncio` 폴러. **60초 틱**, `VIBE_TRADING_ENABLE_SCHEDULER`가 참일 때만 켜짐(기본 꺼짐) | `agent/src/scheduled_research/executor.py:42-43,73-82,280-291`, `agent/src/api/scheduled_routes.py:49-51`, `agent/src/config/env_schema.py:467` | 코드 확인 |
| 스케줄 문법 | 양의 정수 문자열이면 "간격(ms)", 아니면 5필드 cron. cron은 IANA 타임존 벽시계로 평가(미지정 시 UTC) | `agent/src/scheduled_research/executor.py:121-159` | 코드 확인 |
| 실행 방식 | 만기 작업 → 새 세션 생성 → `send_message(job.prompt)`로 큐에 넣고 **즉시 반환**. 따라서 상태 `COMPLETED`는 "enqueue 성공"일 뿐 분석 성공이 아니다 | `agent/src/api/scheduled_routes.py:64-90` | 코드 확인 |
| 재시도 | 디스패치 실패 시 연속 실패 카운터 + 지수 백오프(`max(next, now+delay)`), 상한 초과 시 `FAILED`(재디스패치 안 함) | `agent/src/scheduled_research/executor.py:478-523,777-785` | 코드 확인 |
| 거래일 캘린더 | 스케줄 리서치에는 **없음**(cron의 요일 필드로만 평일 지정). 라이브 러너 트리거는 `us_equity`(뉴욕 09:30-16:00, 공휴일·조기폐장 표)와 `crypto`(24h)만 정의 → **한국 장 시간 없음** | `agent/src/live/runtime/triggers.py:108-127` | 코드 확인 |
| 번들 플레이북 5종 | premarket-brief(`30 8 * * 1-5`, Asia/Shanghai), a-share-money-flow(`0 19 * * 1-5`), earnings-season-tracker(`0 7 * * 1-5`, New_York), institutional-holdings-diff(분기 15일), portfolio-checkup(`0 9 * * 6`). 시장 태그는 cn/hk/us/global/crypto, **kr 없음** | `agent/src/scheduled_research/playbooks/*.md:4-6` | 코드 확인 |
| 라이브 러너 | 틱마다 `halt → 만료 → 정합성 점검 → 자율 턴 → 감사` 순서. 에이전트에 "AUTONOMOUS live-trading tick" 프롬프트를 던짐 (Q6에서 다룸) | `agent/src/live/runtime/runner.py:1-30,219-263` | 코드 확인 |
| GitHub Actions | 판단 파이프라인용 cron **없음**. 있는 것은 CI와 `loader-health.yml`(매주 월 04:17 UTC, 공개 소스 canary — pykrx는 `005930.KS`로 프로브) | `.github/workflows/loader-health.yml:3-6,31-33`, `agent/backtest/loader_health.py:35,52` | 코드 확인 |

<a id="q3-sync"></a>
## 사전 동기화와 저장소

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 가격·재무 사전 동기화 | **없음**. 찾아본 곳: `scheduled_research/`(프롬프트 실행기뿐), `live/runtime/`, `.github/workflows/`. 데이터 DB 없음 | 위 디렉터리 전체 | 코드 확인 (없음) |
| 로컬 캐시 | 옵트인 파일 캐시(기본 꺼짐). "사전 동기화"가 아니라 요청 결과 재사용 | `agent/backtest/loaders/base.py:457-485` | 코드 확인 |
| 작업·판정 저장 | 단일 JSON 파일 `scheduled_research_jobs.json`(원자적 쓰기: temp → fsync → replace). 파싱 실패 시 격리(quarantine) 후 예외 | `agent/src/scheduled_research/store.py:1-10,59-120` | 코드 확인 |
| 실행 산출물 | run 디렉터리와 세션별 trace(`TraceWriter`)에 요청·도구 결과·grounding 증거(`grounding_evidence.json`) 저장 | `agent/src/agent/loop.py:1139-1150,1173`, `agent/src/agent/grounding/ledger.py:46` | 코드 확인 |

## 신선도 관리 (stale 감지)

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 프롬프트 수준 | 모든 수치에 as-of(시세 시각, 봉 날짜, 공시 기간) 명시를 강제. "날짜 없는 숫자는 쓸 수 없는 숫자" | `agent/src/agent/context.py:45-48` | 코드 확인 |
| 플레이북 수준 | "최신 값이 보고 구간보다 오래됐으면 as-of 날짜를 옆에 적어라", 데이터 누락은 `Data gaps` 섹션에 기록 | `agent/src/scheduled_research/playbooks/premarket-brief.md:61-76` | 코드 확인 |
| 코드 수준 | 값의 나이를 계산해 확신도를 낮추거나 판단을 막는 로직은 **찾지 못함**. grounding 게이트는 "숫자가 이번 세션 도구 결과와 맞는가"만 검사하고 시각의 신선도는 검사하지 않음 | `agent/src/agent/grounding/policies.py:463-666` (`_validate_figures`) | 추론 (게이트가 검사하는 항목 목록을 코드로 확인했으나, 신선도 검사 부재는 전수 grep이 아니라 함수 읽기 기반) |
| 시스템 프롬프트 날짜 | 현재 UTC 시각을 system prompt에 주입. 플레이북은 "작성일이 곧 실행일이라고 가정하지 말라"고 지시 | `agent/src/agent/context.py:266-268,338-347`, `premarket-brief.md:22-24` | 코드 확인 |
| 한국 시장 | 정규장 시간·휴장일 인식 없음. 종가 기준 일봉을 쓰되 장중 미확정 봉 구분은 캐시에서만 (`end_date`가 오늘이면 캐시 안 함) | `agent/backtest/loaders/base.py:552-564` | 코드 확인 |

## 실시간 스트림

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 시세 스트림 | 없음. Upbit·KIS 시세는 REST 폴링(`/ticker`, `inquire-price`) | `agent/src/trading/connectors/upbit/sdk.py:296-319`, `agent/src/trading/connectors/kis/sdk.py:390-418` | 코드 확인 |
| SSE/WebSocket | 에이전트 이벤트(도구 호출, 텍스트 델타, grounding 상태)를 UI로 푸시하는 용도. 판단 입력이 아님 | `frontend/src/hooks/useSSE.ts:74,87`, `frontend/src/pages/Agent.tsx:782-786` | 코드 확인 (UI 표시용) |
