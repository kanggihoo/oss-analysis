# jev-ultrafast — 다음 세션 메모

- 분석 SHA: `1231850a0bf1a0c0341fe408ef1668dbbfdfac46` (2026-10-09)
- 확인한 범위: `jev_ultrafast/*.py`, `snapshot.js`, `demo.py`, `examples/`, `docs/design.md`, `docs/performance.md`, 테스트 목록. `uv run pytest` 31 passed.
- 산출물: [overview.md](overview.md), [diagrams/structure.html](diagrams/structure.html), [diagrams/tick-flow.html](diagrams/tick-flow.html)

- 질문 답변: [questions/q1-dynamic-choices-and-context.md](questions/q1-dynamic-choices-and-context.md) (동적 선택지·중복 버튼·context 예시)

## 남은 질문 (후보)

1. TypeSafe `/v1/systemone`은 질문 head들을 어떻게 한 번에 답하나? (docs.typesafe.ai의 fan-out 패턴 문서 확인)
2. click guard(좁은 범위)와 marker(전체) 비교를 나눈 기준은 안전한가? — `scripts/check_guards.py`를 실제 Chrome으로 실행해 확인
3. 일반 LLM 브라우저 에이전트(browser-use 본체)와 비교하면 무엇을 포기하고 무엇을 얻었나?
4. 새 operation(예: 키보드 Enter, 파일 업로드)을 넣으려면 어디까지 바뀌나?
5. 텍스트 캐시(`pending_text`)가 없으면 어떤 실패가 생기나? — `tests/test_agent.py:189-212`

## 다음에 볼 파일·함수

- `scripts/check_guards.py` 전체 (실행 포함)
- `jev_ultrafast/static/app.js` (Inspector가 decisions/raw_answers를 어떻게 보여주는지)
- `tests/test_agent.py:230-280` (atomic read, stale 거부, select 중단)
- 외부: `browser_harness.helpers.cdp`, `browser_harness.admin.ensure_daemon`

6. 중복 라벨 버튼(요소 표에서 index만 다름)을 모델이 페이지 텍스트 순서만으로 구분하나? — 실제 실행 필요 (q1 §3 참고)
