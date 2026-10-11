---
title: jev-ultrafast
created: 2026-10-09
updated: 2026-10-09
type: project
tags: [open-source, project, architecture, agent-framework, pattern, testing, evidence]
sources:
  - reports/jev-ultrafast/overview.md
  - repos/jev-ultrafast/README.md
  - repos/jev-ultrafast/AGENTS.md
  - repos/jev-ultrafast/docs/design.md
  - repos/jev-ultrafast/jev_ultrafast/agent.py
  - repos/jev-ultrafast/jev_ultrafast/model.py
  - repos/jev-ultrafast/jev_ultrafast/browser.py
  - repos/jev-ultrafast/jev_ultrafast/snapshot.js
confidence: high
---

# jev-ultrafast

browser-use가 만든 작은(약 1,200줄) Python 브라우저 에이전트. LLM이 행동을 **생성**하지 않고 관찰된 선택지 중에서 **고르게** 해서 빠르고 안전하게 만든다. 분석 SHA `1231850a`. 상세: `reports/jev-ultrafast/overview.md`.

## 핵심 구조 (코드 확인)

- 루프: `page → 번호 붙은 요소 표 → operation + target → 실행` (`agent.py`).
- 결정: TypeSafe Jev API에 **operation 질문 + operation별 target 질문을 한 요청**으로 보낸다. 선택된 operation의 target 답만 검증·사용하고 나머지는 버린다 (`model.py choose`). 직렬 2회 호출을 1회로 줄이는 "speculative fan-out".
- 텍스트: `TYPE_TEXT`일 때만 작은 LLM을 부르고 `{"text": ...}` 한 키 JSON만 받는다.
- 실행: 모델 출력은 번호뿐이고, 번호 → 코드가 가진 실제 DOM 노드(`window.__jevFast` WeakMap/Map) → 실행 직전 좌표 재계산·가림 검사 → CDP 입력. 셀렉터/좌표/코드를 모델이 만들지 않는다.
- 관찰: `snapshot.js` 한 번의 `Runtime.evaluate`로 보이는 컨트롤과 보이는 텍스트(6,000자)를 읽는다. 스크린샷은 모델에 주지 않는다.

## 재사용할 설계 패턴

- **선택형 action space**: 매 관찰마다 가능한 operation/target만 후보로 주고, 응답이 후보 집합·확률 합 조건을 어기면 실행하지 않는다 (`validate_choice`).
- **결정은 한 번만 소비**: act 시작 시 decision을 먼저 지워 재시도가 이중 클릭이 되지 않게 한다. 실행은 관찰 전에 기록한다.
- **변이는 재시도하지 않는다**: 끊긴 native select는 stale이 아니라 오류로 멈춘다. 모델 HTTP 429/503/529만 백오프 재시도.
- **두 단계 freshness**: click/select는 대상 노드와 주변 form/row만 비교(좁은 guard), 텍스트 생성·스크롤·완료는 전체 marker 비교. 관련 없는 애니메이션 때문에 재예측하지 않는다.
- **DONE은 증거가 아니다**: 예제는 결과 페이지를 독립적으로 검증한다 (`examples/flights.py verify`).

관련: [[pi]] (에이전트 루프의 종료 판단 비교), [[ponytail]] (작은 코드로 유지하는 원칙)

## 한계 (README·코드 확인)

shadow root, iframe, canvas, 업로드, 팝업 탭, 중첩 스크롤 미지원. 접근 가능한 이름 계산은 일반적인 경우만. 성능 수치(7.1초, 25% 감소)는 3쌍 측정이며 재현하지 않음(`미확인`).
