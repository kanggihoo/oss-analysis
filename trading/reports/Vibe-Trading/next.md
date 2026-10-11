# Vibe-Trading — 확인한 범위와 다음에 볼 것

- 분석 SHA: `e532650b527ba3fb146ef00d533f6fc5040d5d2d` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1–Q7 전체
- 검증 수준 요약: 코드 확인 0 / 추론 0 / 미확인 9

## 확인한 범위

- 판단 경로 4갈래의 진입점부터 최종 출력까지: 메인 ReAct(`agent/src/agent/loop.py`, `context.py`), grounding 게이트(`agent/src/agent/grounding/ledger.py`, `release.py`, `registry.py` 및 `policies.py` 목록), swarm(`runtime.py`, `worker.py`, `presets/investment_committee.yaml`, `swarm/grounding.py`), 스케줄 리서치(`executor.py`, `verdict.py`, `store.py`, 플레이북 2종 전문), 라이브 러너·게이트(`order_guard.py`, `sdk_order_gate.py` 머리, `enforcement.py` 일부, `mandate/model.py`, `halt.py`, `runtime/runner.py`, `runtime/triggers.py`).
- 데이터: loader 레지스트리 전체 앞부분(체인·caliber), `pykrx_loader.py` 전문, `korea_equity.py` 전문, 도구 약 30개의 docstring 머리, `technical_indicator_tool.py` 상수부, 웹 검색·읽기 도구, 보안 스캐너 머리.
- 한국 연동: Upbit·KIS `sdk.py`의 조회 함수와 주문 가드, `profiles.py`, `classification.py`.
- 하지 않은 것: 코드 설치·빌드·실행 없음. 클론은 읽기 전용(작업트리 clean).

## 미확인 항목 체크리스트

- [ ] 펀딩비·온체인·OI 데이터가 실제로 어느 loader/스킬에서 채워지는지 (`agent/backtest/loaders/okx.py`, `binance_loader.py`, `agent/src/skills/crypto-derivatives/SKILL.md`, `defi-yield/SKILL.md`)
- [ ] `fundamentals_loader.py`의 PIT(공시일 이후에만 노출) 구현 본문
- [ ] `run_swarm` 결과가 메인 에이전트의 grounding 장부(`ingest_tool_result`)에 증거로 들어가는지 (`agent/src/agent/grounding/ledger.py:274-320`, `agent/src/tools/swarm_tool.py`)
- [ ] 메인 프롬프트 원칙 4("조언 금지")와 라이브 러너 프롬프트("Trade freely")가 충돌할 때의 실제 동작 (실행 확인 필요, 사용자 합의 전에는 실행 안 함)
- [ ] 한국 종목(`005930.KS`)으로 `investment_committee`를 돌렸을 때 도구별 에러 봉투 (코드상 추론만 함)
- [ ] KIS 일봉 조회의 페이지네이션: `inquire-daily-itemchartprice`는 시작일 1990-01-01로 1회 호출하고 `limit`으로 자르는데(`kis/sdk.py:445-465`), 응답 1회당 행 수 상한 때문에 긴 기간이 잘리는지는 확인 못 함
- [ ] 프론트 `Runtime.tsx`(라이브 화면)가 표시하는 판단 근거
- [ ] `PersistentMemory.find_relevant`의 점수 산식과 `remember` 도구가 저장하는 항목(`agent/src/memory/persistent.py`, `agent/src/tools/remember_tool.py`)
- [ ] `agent/src/agent/grounding/policies.py`의 `_validate_figures` 전체 분기(허용 오차 값, `_close` 기준)

## 다음에 볼 파일과 함수

1. `agent/src/agent/grounding/policies.py:463-666` `_validate_figures`, `:1549` `_check_observed` — 수치 허용 오차와 증거 매칭. 우리 최소판 게이트 설계에 직접 필요.
2. `agent/src/live/enforcement.py:476` `check_mandate` — 한도 계산식 전문(노출·레버리지·유니버스).
3. `agent/src/live/sdk_order_gate.py:62` `execute_live_order` — 보류 주문(`pending_action`) 복구 흐름(Alpaca 전용 분기 `:92`).
4. `agent/src/tools/swarm_tool.py:32-436` — 키워드 프리셋 선택 규칙.
5. `agent/src/tools/swarm_tool.py:456` — swarm 호출·변수 추출·타임아웃.
6. `agent/backtest/loaders/okx.py`, `binance_loader.py` — 코인 쪽 추가 필드.

## 분석 중 생긴 질문

- system prompt의 "analysis, not advice"가 사용자 메시지("Trade freely")보다 우선한다는 코드 보장이 있는가?
- swarm PM의 "확신도 0–100%"와 비중이 어떤 코드 경로로도 검증·제한되지 않는다면, 라이브 러너와 swarm을 조합했을 때 한도(mandate)가 유일한 방어선인가?
- 한국 장(09:00–15:30 KST) 트리거와 KRW 한도를 지원하려면 `MARKET_SPECS`와 `AssetClass`만 늘리면 되는가, 아니면 `enforcement.py`의 USD 가정이 더 있는가?
