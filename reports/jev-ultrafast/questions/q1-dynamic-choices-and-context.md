# Q1. 선택지(분류기)는 동적인가? 중복 버튼은? context는 충분한가? 루프는 누가 만드나?

- 분석 SHA: `1231850a` (2026-10-14 재확인)
- 검증 수준: 코드 확인. 아래 "예시 요청 body"는 `action_space()`·`choose()`를 **가짜 화면 상태**로 실제 실행해 얻은 출력이다 (API 호출 없음 → 서버 응답은 `미확인`, 응답 예시는 가상).

## 1. 짧은 답

| 질문 | 답 | 근거 |
|---|---|---|
| 분류기 개수가 동적으로 바뀌나 | 매 스텝 새로 만든다. 요청마다 `questions`와 `criteria`(선택지)를 같이 보낸다. | `model.py:81 choose` |
| 같은 라벨 버튼 구분 | DOM 노드마다 고유 정수 → 요소 번호. 모델은 번호만 고른다. | `snapshot.js:3-6`, `model.py:48 action_space` |
| context | goal + 보이는 텍스트 6,000자 + 번호 붙은 요소 표(값/상태) + 최근 행동 10개 | `model.py:108-118` |
| 행동 도구를 LLM에 주나 | 아니오. tool calling 없음. 선택 결과를 코드가 CDP로 실행. | `browser.py browser_operation` |
| 루프 | 직접 작성(`agent.py` 174줄). 외부는 CDP 헬퍼(`browser_harness`)뿐. | `agent.py:163 run` |

## 2. 예시: Google Flights 한 스텝

목표: "Zurich → London, 9/20, economy 편도 검색. 결과가 보이면 멈춰라."
상황: From에 이미 `Zurich`를 입력했고(직전 행동), To는 비어 있고, 화면에 Search 버튼과 Cabin 드롭다운이 있다.

### 2-1. 코드가 만든 요소 표 (`state.elements`)

한 노드는 한 번호만 받는다. From 입력창은 "타이핑"과 "클릭(열기)" 둘 다 가능하지만 번호는 1개다.

| index | role | label | value | operations |
|---|---|---|---|---|
| 1 | textbox | From | Zurich | TYPE_TEXT, CLICK |
| 2 | textbox | To | (빈 값) | TYPE_TEXT, CLICK |
| 3 | button | Search | | CLICK |
| 4 | button | Add | | CLICK |
| 5 | button | Add | | CLICK |
| 6 | combobox | Cabin | Economy | SELECT (옵션 `6:1` Economy, `6:2` Business) |

### 2-2. 한 요청에 담기는 질문들 (실제 생성 결과 요약)

```
operation 질문   criteria: TYPE_TEXT / CLICK / SELECT / SCROLL_DOWN / WAIT / DONE / BLOCKED
type_text_target criteria: 1 "[1] From"(현재값 Zurich), 2 "[2] To"(현재값 "")
click_target     criteria: 1 "[1] Open From", 2 "[2] Open To", 3 "[3] Search", 4 "[4] Add", 5 "[5] Add"
select_target    criteria: 6:1 "Cabin → Economy", 6:2 "Cabin → Business"
공통 instructions: goal = 위 목표 문장, rules = NEXT_ACTION(+TARGET)
state: page{url,title,text}, elements, recent_actions=[From에 "Zurich" 입력, page_changed=true]
```

### 2-3. 서버가 돌려줄 법한 응답 (가상 — 형식은 `validate_choice` 기준)

```
operation:        TYPE_TEXT 0.93 / CLICK 0.05 / ... (합 ≈ 1, 최고 확률이 choice)
type_text_target: "2"(To) 0.97 / "1"(From) 0.03
```

코드는 operation=TYPE_TEXT이므로 `type_text_target` 답만 쓰고 `click_target`·`select_target` 답은 버린다. 그다음 작은 LLM이 `{"text": "London"}`을 만들고, 요소 2번의 노드를 클릭 후 select-all, `Input.insertText`로 입력한다.

## 3. "context가 부족해서 판단 못 하지 않나?"

모델은 전체 계획을 세우지 않는다. 매 스텝 **"지금 화면에서 다음 한 동작"** 만 고른다. 그 판단에 필요한 정보가 요청에 들어 있다.

- 목표 전체가 매번 같이 간다 (`instructions.goal`).
- 요소의 **현재 값**이 보인다: From=Zurich, To=빈 값 → "To가 비었으니 To를 채워라"가 판단 가능. `TARGET` 규칙에도 "이미 요청값이 있는 필드는 고르지 마라"가 있다.
- `recent_actions`로 방금 한 일을 안다 → 같은 입력 반복 방지.
- 보이는 페이지 텍스트가 있어 결과 목록이 떴는지 판단(DONE).
- `NEXT_ACTION` 프롬프트가 도메인 규칙을 준다: "자동완성은 제안을 클릭해야 확정", "Search가 보이고 필드가 준비되면 즉시 클릭", "DONE은 모든 요구가 보일 때만" (`questions.py`).
- 어휘가 작다: 선택지가 수~수십 개 번호이고, 모델은 자유 생성 없이 그중 하나의 확률만 낸다. 그래서 짧은 문맥으로도 빠르게 가능한 구조다 (`추론`: 이 설계 의도는 `docs/design.md`가 "finite-choice"를 강조하는 것과 일치하나, 서버 모델 내부는 `미확인`).

### 정보가 실제로 모자랄 수 있는 곳 (이 코드의 약점)

1. **동일 라벨 중복**: 위 표의 4번과 5번은 모델 입장에서 `Add` / `button` / 빈 값으로 **완전히 같다**. 요소 정보에 주변 텍스트·위치가 없다 (`action_space`가 `role, value, checked, selected, expanded, index, label, operations`만 전달). 구분 단서는 페이지 텍스트의 순서(`Cheese pizza\nAdd\nCola\nAdd`)뿐이고, 요소 번호가 DOM 순서라는 점과 대응시키는 것은 모델의 몫이다. 이 경우 정확도는 `미확인`.
   - 참고: 주변 form/row 텍스트는 `cache.guard`(freshness 검사)에는 쓰이지만 모델 입력에는 안 들어간다 (`snapshot.js:36-45`, `model.py`).
2. **화면 밖 요소**: viewport 안 요소만 후보다. 필요한 버튼이 아래에 있으면 SCROLL_DOWN을 먼저 골라야 한다.
3. **텍스트 6,000자 / 요소 250개 제한**: 잘린 뒤쪽은 선택 불가 (`omitted_actions`).
4. 스크린샷은 모델에 주지 않으므로 이미지로만 구분되는 아이콘 버튼은 라벨(aria-label, title 등)에 의존한다.

## 4. 루프 구조 (직접 구현)

```
run(): while status ∉ {done, blocked}: tick()
tick(): predict() → act(fingerprint)        # 화면이 바뀌면 StalePage → 재관찰 후 재예측
predict: (필요시 observe) → choose()  [Jev API 1회]
act:     decision 소비 → TYPE_TEXT면 작은 LLM 1회 → 실행 → observe → history 기록
중단:    DONE/BLOCKED 선택, 60 액션, 3연속 page_changed=false, 결정 120회
```

외부 의존은 `browser_harness`의 `cdp()`와 `ensure_daemon()` (`browser.py:5-6`)뿐. 이 모듈의 내부는 `미확인`.

## 5. 남은 확인

- 중복 라벨 버튼 페이지에서 실제 `raw_answers`가 어떻게 나오는지 → 로컬 fixture(`static/fixture.html`) 또는 `examples/run.py`로 실행 필요 (`TYPESAFE_API_KEY` 필요).
- 서버가 `criteria` 문구를 어떻게 소비하는지 → docs.typesafe.ai 확인.
