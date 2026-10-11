# jev-ultrafast — 개요

- 원본: https://github.com/browser-use/jev-ultrafast
- 분석 SHA: `1231850a0bf1a0c0341fe408ef1668dbbfdfac46` (2026-09-18, "docs: announce the Cloud waitlist…")
- 분석일: 2026-10-09 · 작업트리: clean (분석 중 생긴 `.venv/`, `__pycache__/`는 gitignore 대상)
- 분석 방식: `open-source-codebase-understanding` 스킬. 추적 파일 40개(py 15개, 약 1,200줄)라 **매우 작은 프로젝트로 분류해 서브에이전트 없이 직접 분석**했다.
- 검증 수준 표기: `코드 확인` / `실행 확인` / `추론` / `미확인`
- 다이어그램: [structure.html](diagrams/structure.html) (모듈 구조) · [tick-flow.html](diagrams/tick-flow.html) (한 번의 tick, TYPE_TEXT 경로)

그림 읽는 순서: `structure.html`에서 가운데 줄(호출자 → Agent → Browser → Browser Harness → Chrome)이 실행 경로다. 위쪽 갈래(model.py → TypeSafe / Text LLM)는 "무엇을 할지" 정하는 쪽이다. 그다음 `tick-flow.html`에서 한 스텝이 predict → act → observe 순서로 어떻게 진행되는지 본다.

---

## 1. 이 프로젝트의 목적

자연어 목표 하나를 받아 실제 Chrome을 조작하는 **브라우저 에이전트**. 핵심 아이디어는 "LLM이 행동을 생성하지 않고, 관찰된 선택지 중에서 **고른다**"이다 (`pyproject.toml` description: "A browser agent that chooses instead of generating."). `코드 확인`

- 고르는 쪽: TypeSafe의 Jev 모델 (`https://api.typesafe.ai/v1/systemone`). 객관식 질문에 확률 분포로 답하는 API다.
- 쓰는 쪽: 작은 LLM(기본 예시는 OpenRouter의 `inception/mercury-2.5`)은 operation이 `TYPE_TEXT`일 때만 입력 문자열을 만든다.
- 목표는 속도. README가 내세우는 수치는 Google Flights 검색 7.1초. 이 수치는 `docs/performance.md`의 측정 기록이며 나는 재실행하지 않았다(유료 API). `미확인`

OpenAI/Claude에 비유하면: 보통 브라우저 에이전트는 Claude에게 "다음 행동을 JSON으로 써라"라고 시키고 그 안에 셀렉터나 좌표가 들어간다. 이 프로젝트는 대신 "다음 operation은 ①CLICK ②TYPE_TEXT ③…중 무엇? 대상은 [1]…[n] 중 무엇?"이라는 **객관식 시험지**를 보내고, 답으로 받은 번호를 코드가 이미 쥐고 있는 실제 DOM 노드로 바꿔 실행한다.

## 2. 프로젝트 유형과 사용 방식

**라이브러리 + 로컬 데모 서버**인 작은 Python 패키지. `코드 확인`

- 라이브러리: `from jev_ultrafast import Agent` → `with Agent(url, goal) as agent: for state in agent.run(): ...` (`jev_ultrafast/__init__.py`, `agent.py:163`)
- CLI: `uv run jev` → `jev_ultrafast.demo:main` (`pyproject.toml [project.scripts]`). 127.0.0.1:8766에 Inspector 웹 UI를 띄운다.
- 예제 스크립트: `examples/run.py` (임의 URL/목표), `examples/flights.py` (Google Flights + 독립 결과 검증)

## 3. 핵심 기능

| 기능 | 위치 | 검증 |
|---|---|---|
| 한 번의 브라우저 호출로 화면 스냅샷(보이는 컨트롤, 이름, 값, 보이는 텍스트) 읽기 | `snapshot.js`, `browser.py:188` | 코드 확인, 테스트 `test_observation_is_one_atomic_browser_read` |
| 요소 표를 만들고 operation별 target 후보를 분리 (동적 action space) | `model.py:48 action_space` | 코드 확인, 실행 확인(테스트) |
| operation + 모든 target head를 **한 요청**으로 질문, 선택된 head만 사용 | `model.py:81 choose` | 코드 확인, 실행 확인(테스트) |
| TYPE_TEXT일 때만 텍스트 LLM 호출, `{"text": ...}` JSON만 허용 | `model.py:151-198` | 코드 확인, 실행 확인(테스트) |
| 실행 직전 freshness 검사 + 가림(occlusion) 검사 후 CDP 입력 | `browser.py:88-186` | 코드 확인 |
| 반복 무진전/예산 초과 시 자동 중단 | `agent.py:75, 102, 153-158` | 코드 확인 |
| Inspector UI (확률, 실행 기록, 스크린샷 표시) | `demo.py`, `static/` | 코드 확인 (UI JS는 훑어보기만) |

## 4. 실행/사용 진입점

- `Agent.__init__` (`agent.py:13`): `Browser(url)` 생성 → 첫 `observe()` → `self.state` 초기화. `코드 확인`
- `Agent.run()` (`agent.py:163`): status가 `done`/`blocked`가 될 때까지 `command("tick")`을 yield. `코드 확인`
- `Agent.command("tick")` (`agent.py:55`): `predict` → `act`. `StalePage`가 나면 재관찰 후 상태만 돌려준다(행동 없음). `코드 확인`
- `demo.main()` (`demo.py:131`): `.env` 로드 → `ThreadingHTTPServer`. `POST /api/reset`이 Agent를 만들고, `POST /api/<predict|act|tick>`이 그대로 `Agent.command`로 전달된다. `코드 확인`
- 데모 시나리오: `flights`(실제 Google Flights) / `travel`, `research`(로컬 `static/fixture.html`). `코드 확인`

## 5. 주요 모듈과 책임

| 파일 | 줄 | 책임 |
|---|---:|---|
| `agent.py` | 174 | 루프와 상태 기계. decision 1회 소비, 텍스트 캐시, history 기록, 중단 조건 |
| `model.py` | 198 | action space 구성, TypeSafe 요청/응답 검증, 텍스트 LLM 호출, HTTP 재시도 |
| `questions.py` | 26 | 모델에게 주는 규칙 문자열(`NEXT_ACTION`, `TARGET`, `TEXT_VALUE`)과 `MAX_STEPS=60` |
| `browser.py` | 194 | Browser Harness의 `cdp()`로 탭 생성·연결, observe/fresh/act, 입력 이벤트 전송 |
| `snapshot.js` | 107 | 페이지 안에서 실행되는 DOM 리더. 노드 ID 부여, 이름 계산, guard/marker 생성 |
| `demo.py` | 145 | 루프백 전용 Inspector HTTP 서버 |
| `static/app.js`, `index.html`, `style.css` | — | Inspector 화면 |
| `static/fixture.html` | 507 | 로컬 호텔 검색/위키 유사 테스트 페이지 |

설계 원칙은 레포 `AGENTS.md`에 짧게 적혀 있다 ("page -> indexed elements -> operation + target -> execution", "Never retry a browser mutation" 등). `코드 확인`

## 6. 핵심 개념과 용어

- **action**: `snapshot.js`가 만든 실행 가능한 후보 하나. `{id: 'e1', kind: 'click'|'fill'|'select'|'scroll'|'wait', node, label, role, value, ...}`. 편집 가능한 입력칸은 `fill`과 `Open <label>` click 두 개의 action이 된다 (`snapshot.js:78-79`). 최대 250개 (`snapshot.js:99-100`).
- **node**: 코드가 붙인 정수 ID. `WeakMap`(요소→ID) + `Map`(ID→요소)로 실제 DOM 노드를 기억한다 (`snapshot.js:3-8`). CDP backend node id가 아니다.
- **element index**: 모델에게 보여주는 번호 `[1]`, `[2]`…. 같은 노드는 operation이 여러 개여도 번호 하나 (`model.py:58-62`).
- **operation**: `CLICK`, `TYPE_TEXT`, `SELECT` + 컨트롤(`SCROLL_DOWN`, `SCROLL_UP`, `WAIT`) + `DONE`, `BLOCKED`. 현재 화면에 가능한 것만 질문에 넣는다 (`model.py:88-90`).
- **target head**: `click_target`, `type_text_target`, `select_target` 같은 operation별 질문. SELECT target은 `"3:2"`(요소:옵션) 형태 (`model.py:75`).
- **marker / page_key / guards / fingerprint**:
  - `marker`: URL·스크롤·뷰포트·제목·보이는 텍스트·action 의미(좌표 제외)·폼 값 묶음. 전체 freshness 비교용 (`snapshot.js:97`).
  - `page_key` + `guards[node]`: click/select 때 쓰는 **범위가 좁은** 비교. 대상 노드 속성과 주변 form/dialog/row 텍스트만 본다 (`snapshot.js:44-54`). 관련 없는 영역의 변화는 허용.
  - `fingerprint`: 파이썬 쪽 SHA-256 (`browser.py:115`). act 요청이 같은 관찰에 대한 것인지, 행동 후 페이지가 바뀌었는지 판단.
- **StalePage**: "결정이 더 이상 관찰한 페이지를 가리키지 않음". `ValueError` 하위 클래스 (`browser.py:16`).

## 7. 입력/데이터/상태/제어 흐름

한 tick (TYPE_TEXT인 경우, [tick-flow.html](diagrams/tick-flow.html)). 모두 `코드 확인`, 3·5·7은 offline 테스트로 `실행 확인`.

1. **predict** (`agent.py:65-85`): 첫 predict에서 타이머 시작. `fresh(page)`가 아니면 다시 observe. 결정 예산(120회) 확인 → `choose(page, goal, history)`.
2. `choose` (`model.py:81-148`): `action_space`로 요소 표·target 그룹 생성 → 질문 묶음(`operation` + `<op>_target`들) + state(`url/title/text`, elements, 최근 10개 행동)를 한 번에 POST.
3. 응답 검증 `validate_choice` (`model.py:30-45`): choice가 후보 안에 있는지, 확률 집합=후보 집합, 0~1, 합≈1(±0.02), choice가 최댓값인지. operation head만 먼저 검증하고, **선택된 operation의 target head만** 검증·사용한다. 나머지 head는 무시.
4. **act** (`agent.py:86-158`): fingerprint 일치 확인 후 **decision을 먼저 None으로 지워** 재시도 시 두 번 클릭하지 않게 한다.
   - `DONE`/`BLOCKED`: freshness 확인 후 종료 상태.
   - 60개 action 예산 확인.
   - `fill`이면: freshness 확인 → `field_context` 생성 → 직전 stale 재시도와 context가 **완전히 같을 때만** 캐시된 텍스트 재사용, 아니면 `field_text` 호출.
5. `Browser.act` (`browser.py:100`): 다시 `fresh(page, action)` (click/select는 좁은 guard, 나머지는 marker). 통과하면 `browser_operation("act")`:
   - 노드가 연결·보임·활성·뷰포트 안인지, 중심점 `elementFromPoint`가 그 노드 안인지(가림 검사) 확인. 좌표는 **이때 새로 계산**.
   - click: mousePressed/Released. fill: 클릭 → selectAll 키 → `Input.insertText`. select: 페이지 JS로 `value` 설정 + input/change 이벤트.
6. 실행을 **observe 전에** `history`에 기록 (`agent.py:120-141`). 그 뒤 observe가 실패해도 행동 기록은 남는다.
7. **observe** (`browser.py:44-86`): 직전 입력이 combobox fill이면 보이는 `role="option"`이 뜰 때까지 최대 200ms, 아니면 2프레임/50ms 대기 → `snapshot.js` 실행. 탐색 중이면 20ms 간격 최대 10회 재시도.
8. 3개 연속 non-wait 행동이 페이지를 바꾸지 못하면 `blocked` (`agent.py:153-158`).

상태는 전부 `Agent.state` 딕셔너리 하나에 있다 (`goal`, `page`, `decision`, `history`, `decisions`, `text_calls`, `status`, 타이밍). `plan`/`plan_index`는 목표 1개짜리 리스트로 남아 있는 흔적이다. `추론`: 이전 "준비된 다단계 계획" 프로토타입(`docs/design.md` "What changed after the first demo")의 잔재.

## 8. 설정 및 환경 구성

`.env.example` (`코드 확인`):

| 변수 | 기본/예시 | 쓰는 곳 |
|---|---|---|
| `TYPESAFE_API_KEY` | (필수) | `model.py:119` |
| `TYPESAFE_MODEL` | `jev-latest` | `model.py:108` |
| `TEXT_MODEL_API_KEY` | (TYPE_TEXT에 필수) | `model.py:161` — 없으면 추측하지 않고 `ValueError` |
| `TEXT_MODEL_BASE_URL` | 예시 `https://openrouter.ai/api/v1`, 코드 기본값 `https://api.deepseek.com/v1` | `model.py:164` |
| `TEXT_MODEL` | 예시 `inception/mercury-2.5`, 코드 기본값 `deepseek-chat` | `model.py:165` |
| `TEXT_MODEL_REASONING` | `none`이면 `reasoning.enabled=false` | `model.py:166-168` |
| `TYPESAFE_DEMO_PORT` | `8766` | `demo.py:16` |

- `.env` 로딩: `demo.py`의 `load_environment()`만 직접 읽는다(이미 있는 값은 덮지 않음). 라이브러리/예제는 `uv run --env-file .env`에 의존. `코드 확인`
- 브라우저: `browser-harness==0.1.13`의 `ensure_daemon()` + `cdp()`. 사용자의 기존 Chrome 프로필에 **백그라운드 탭**을 새로 만들고 1120×780으로 고정, `setFocusEmulationEnabled`로 숨은 탭에서도 애니메이션 프레임이 돌게 한다 (`browser.py:21-33`). `코드 확인`

## 9. 의존성 구조

- 런타임: `browser-harness==0.1.13`(CDP 데몬/헬퍼), `httpx[http2]`(모델 API 호출). 그 외는 표준 라이브러리. `코드 확인`
- dev: `pytest`, `ruff`, `pillow`(녹화 렌더링 스크립트용 `추론`).
- 내부 의존 방향: `demo → agent → {browser, model} → questions`. `browser`는 `snapshot.js`를 문자열로 읽어 페이지에 주입. `model`과 `browser`는 서로 모른다. `코드 확인`
- 외부 서비스: TypeSafe API, OpenAI 호환 chat completions 엔드포인트, 로컬 Chrome.

## 10. 빌드/실행/테스트 방식

```bash
uv sync
cp .env.example .env   # 키 입력
uv run jev             # http://127.0.0.1:8766
uv run --env-file .env python examples/run.py --url URL --goal '...'
uv run --env-file .env python examples/flights.py --keep-open
```

- 테스트: `uv run pytest` → **31 passed in 0.38s** (2026-10-09, 이 SHA). `실행 확인`. 모두 offline이며 `Mock`/`monkeypatch`로 브라우저와 모델 API를 대체한다.
- `scripts/check_guards.py`: 모델 호출 없이 **실제 로컬 Chrome**으로 freshness/가림/교체 노드 회귀를 확인. 이번에는 실행하지 않음 (Chrome 원격 디버깅 연결 필요). `미확인`
- `scripts/smoke.py`, `measure_flights.py`, `record_flights.py`: 유료 API 호출. 실행하지 않음.
- 기타 검사: `ruff check`, `node --check` (static/app.js, snapshot.js), `uv build`.

## 11. 에러 처리와 디버깅 포인트

`코드 확인`

| 상황 | 처리 |
|---|---|
| 결정 후 페이지가 바뀜 | `StalePage` → tick이 잡아서 재관찰, 행동 없이 반환 (`agent.py:59-64`) |
| act 도중 stale (텍스트 생성 후 등) | 생성된 텍스트를 `pending_text`에 보관, 다음 시도 context가 같을 때만 재사용 |
| native select 실행이 중간에 끊김 | `RuntimeError` — change 이벤트가 이미 발생했을 수 있으므로 **stale로 취급해 재시도하지 않음** (`browser.py:130-131, 162-163`) |
| 모델 HTTP 429/503/529 | 0.5s, 1s 백오프로 최대 3회 (`model.py:16-27`). 네트워크 예외는 즉시 실패 |
| 모델 응답 형식 오류 | `ValueError("Invalid TypeSafe response; no action executed.")` |
| 텍스트 LLM이 빈 값/추가 키/2000자 초과 | `ValueError` — 아무것도 입력하지 않음 |
| 예산 | action 60회, decision 120회 (`MAX_STEPS`) |
| 무진전 | 연속 3회 페이지 변화 없음 → `blocked` |
| Inspector 서버 | Host/Origin/토큰 검사, 동시 요청은 409, 예외는 400/500으로 반환하고 자동 재시도 없음 |

디버깅 포인트: `state["decisions"][i]["request"]`에 TypeSafe로 보낸 본문 전체가, `raw_answers`에 모든 head의 답이 남는다 (`model.py:143-147`). Inspector가 이것을 화면에 보여준다. `examples/flights.py`는 `state.json`으로 덤프.

## 12. 확장하거나 기여할 때 봐야 할 구조

- **새 operation 추가**: `snapshot.js`에서 새 `kind` action 생성 → `model.py action_space`의 `operations` 매핑과 `choose`의 `labels` → `browser_operation`의 실행 분기. 이 세 곳이 한 세트다. `코드 확인`
- **지원하는 컨트롤 범위**: `snapshot.js`의 `roles`/`selector`/`role()`/`name()`. shadow root, iframe, canvas, 업로드, 팝업 탭, 중첩 스크롤은 미지원 (README "Evidence and limits"). `코드 확인`(코드에 traversal 없음)
- **모델 규칙 조정**: `questions.py` 문자열만 바꾸면 된다.
- **텍스트 모델 교체**: OpenAI 호환이면 환경변수로. DeepSeek URL이면 `thinking` 비활성 형식을 자동 선택 (`model.py:166`).
- 레포 `AGENTS.md`의 금지 사항: 사이트별 계획/하드코딩 값 금지, 모델이 셀렉터·코드를 내지 못하게, 브라우저 변이 재시도 금지, 테스트에서 유료 API 금지.

## 13. 처음 기여자가 먼저 읽어야 할 파일

1. `README.md` → `AGENTS.md` (설계 규칙 10줄)
2. `jev_ultrafast/agent.py` — 루프 전체 (174줄)
3. `jev_ultrafast/model.py` — `action_space`, `choose`, `validate_choice`
4. `jev_ultrafast/snapshot.js` — 무엇이 "관찰"되는지
5. `jev_ultrafast/browser.py` — `fresh`와 `browser_operation`
6. `tests/test_agent.py` — 각 불변식이 테스트 이름으로 정리돼 있음
7. `docs/design.md`, `docs/performance.md` — 설계 이유와 측정 경계

## 14. 아직 불확실하거나 추가 확인이 필요한 부분

- TypeSafe `/v1/systemone` API의 정확한 계약(질문 head들이 서버에서 병렬로 평가되는지, 확률이 어떻게 계산되는지). 클라이언트 코드는 "Target questions are speculative… one network round trip"이라고만 말한다. `미확인` — 공식 문서(docs.typesafe.ai) 확인 필요.
- README의 7.1초/25% 감소 수치: 레포의 측정 JSON만 있고 재현하지 않았다. `미확인`
- `scripts/check_guards.py` 실제 Chrome 회귀: 미실행. `미확인`
- `examples/run.py`의 `--goal` "Repeat for an ordered list of goals" 도움말과 달리 `Agent`는 목표들을 줄바꿈으로 합쳐 **한 목표**로 다룬다 (`agent.py:14`). 순서 보장은 모델 판단에 맡겨진다. `코드 확인`, 의도는 `추론`.
- `static/app.js` Inspector UI 내부 동작은 깊게 읽지 않음.
- `browser-harness` 패키지 내부(데몬이 어떤 Chrome에 붙는지, `cdp()`가 동기 호출인지)는 범위 밖. `미확인`
