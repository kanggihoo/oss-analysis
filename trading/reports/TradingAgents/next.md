---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-03
---

# TradingAgents — 다음 작업

## 1. 확인한 범위

[overview](overview.md) 행1~14와 공유계약 S1·S2를 사용자 진행 승인에 따라 원본 동작으로 스펙화했다. ready16 / draft0 / 미작성3(부속15~17). 메인이 공통5개, 데이터 담당2개, AI 담당6개, 메모리 담당3개를 작성했고 공통 계약 교차검토·대표 흐름 통합 검토를 마쳤다. 국장용으로 원본을 변경하지 않았다.

- 스펙·읽는 순서: overview 2절 선행 열. S1·S2·configuration부터 읽고 run-input·point-in-time·analysis-orchestration·vendor-routing, 분석가·판단·메모리/재개·백테스트로 이어간다.
- 대표 입력→결정→정산 연결, 호출 수 근사 및 주요 한계: overview 6절.
- 이전 Q1~Q7 상세 보고서는 `1394a3f` 기록으로 유지한다. 최신 동작의 원본은 현재 capabilities이며 예전 숫자·주장을 혼용하지 않는다.

## 2. 남은 질문·확인 한계

선언한 스펙 범위의 구현을 막는 미결정은 없다. 외부 모델·API·LangGraph·stockstats 내부 기본값·실제 성능은 실행 검증하지 않았다. 원본 설치·실행 금지 규칙을 유지했다.

특히 검증 스냅샷·종목 identity·정산 종가는 Yahoo 직접 경로다. 벤더 등록만 추가해 전부 교체됐다고 볼 수 없다. 날짜 guard·교훈 resolved 제한이 모델 사전학습 지식이나 현 다운로드 조정주가의 과거 개정을 되돌리지는 않는다(각 스펙 코드 확인·확인 한계).

## 3. 다음 후보

- 사용자가 원하면 미국주식 대표 종목의 입력·도구·보고서·교훈을 스펙 순서로 설명한다.
- 국장 설계를 요청하면 수집 계약을 유지하며 종목 식별·검증 스냅샷·정산·공시/수급·뉴스 소스를 각각 어디서 바꿀지 설계한다. 국내 API 매핑은 아직 검증하지 않았다.
- 미작성 부속15~17(CLI/보고서, ChatGPT 인증, CLI 기억/업데이트)은 추가 요청 범위다. 현재 승인 대기 항목 없음.

## 4. 재개 지점·검증

문서 정합 검사 `python3 scripts/check.py TradingAgents` → ERROR0 / NOTE0. [별도 감사 기록](../../artifacts/TradingAgents/spec-audit.json)은 스펙16개·원본 인용 범위152개, sources 존재·줄 경계·depends 존재/순환을 검사했다. 이 감사는 원본 의미의 자동 검증이 아니며 의미는 직접 열람·교차검토했다. 원본 worktree clean, 고정 SHA 유지. 구조도는 이전 자동 검사 통과본을 유지했고 이번에는 다시 렌더링하거나 육안 검토하지 않았다.

## 5. 재구현 계획 (2026-11-03)

Claude·Codex 토론으로 합의한 순서([토론 요약](../../../.herdr-discuss/20261103-1949-tradingagents-impl-order/summary.md), 로컬 전용)와 사용자 결정이다. 화살표 하나가 구현→확인→검토 한 단위다.

configuration → decision-contract(S2) → run-state(S1) → run-input → 그래프 골격(가짜 모델) → point-in-time → vendor-routing(첫 가격 소스) → market → investment-decision → risk-decision → fundamentals(+SEC) → news(+뉴스·FRED) → sentiment → decision-memory → checkpoint → backtest

- 사용자 결정: 시장은 교체 가능한 구조로 두고 미국 주식부터 한다. LangGraph는 쓰지 않는다. 구현은 대시보드 레포의 CONSTRAINTS(httpx 경계 등)를 피해 별도 레포 `~/Desktop/vps/trading-agents`에서 한다. 동기 코드, 병렬은 스레드. 실제 모델은 Codex 구독 또는 OpenRouter이고, 단위 테스트·회귀는 가짜 모델로 한다.
- 기준 고정: 원본 `c4544913`, 스펙 문서 `2b66149`. 원본의 새 커밋은 마일스톤 사이에서만 반영한다.
- 완료 기준(기능마다 한 줄): R/T-ID 통과, 고정 입력 회귀, 오류 처리, 검토 결론과 남은 대역.
- 마일스톤: M1 골격이 가짜 모델로 끝까지 돈다 / M2 실제 모델로 market→PM 1회 판단 / M3 분석가 4명 / M4 memory·checkpoint·backtest.
- 진행 방식 A: 단위마다 사용자 승인 후 다음 단위로 간다.
- 상세 진행 기록은 구현 레포 [`docs/progress.md`](../../../../vps/trading-agents/docs/progress.md)에 둔다. 이 절에는 현재 마일스톤만 적는다. 현재: 2026-11-03 초기 설정 완료, 단위1 대기, M1 이전. 첫 가격 소스(Yahoo/키움 `usa06012`)는 단위7에서 정한다.
