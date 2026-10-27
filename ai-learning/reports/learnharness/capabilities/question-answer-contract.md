---
sha: "b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9"
created: 2026-10-27
updated: 2026-10-27
sources:
  - repos/learnharness/src/core/question-core.ts
  - repos/learnharness/src/core/value-debris.ts
  - repos/learnharness/src/core/pending.ts
  - repos/learnharness/src/core/native-messages.ts
  - repos/learnharness/src/core/input-events.ts
  - repos/learnharness/src/agent/tools.ts
  - repos/learnharness/src/agent/tool-execute.ts
  - repos/learnharness/src/agent/teacher-agent.ts
  - repos/learnharness/src/agent/tools/heal.ts
  - repos/learnharness/src/core/argument-heal.ts
  - repos/learnharness/src/core/tool-parts.ts
  - repos/learnharness/src/core/phases.ts
  - repos/learnharness/src/core/settings.ts
  - repos/learnharness/src/server/settings-body.ts
  - repos/learnharness/src/server/turn-service.ts
  - repos/learnharness/src/server/dismissal-park.ts
  - repos/learnharness/app/api/chats/[id]/dismiss/route.ts
  - repos/learnharness/src/server/chat-handler.ts
  - repos/learnharness/components/question-dock.tsx
  - repos/learnharness/components/chat.tsx
  - repos/learnharness/src/agent/prompts/shared/20-question-tools.md
  - repos/learnharness/src/agent/prompts/shared/25-confidence.md
  - repos/learnharness/src/agent/prompts/shared/16-mental-model.md
depends: []
status: ready
reimplementation: "Python 3 표준 라이브러리, [강제] R-ID의 순수 검증·변환 로직만(권고 규칙과 UI는 제외). 4개 스펙(question-answer-contract, probe-measurement, plan-tree, teaching-cycle)의 1.6 T-ID 전부를 포함해 83개 테스트 통과. 원본과 같은 입력으로 비교하지 않음(원본은 TypeScript이고 실행하지 않았다). 결과: ../../../artifacts/learnharness/reimplementation/core/RESULT.md"
---

# 질문·답변 계약 (공유 계약 S2)

> 에이전트가 질문 도구로 학습자에게 질문을 내면 그 턴이 끝나고, 학습자의 답(선택·글·확신도·사고글)이 구조화된 객체로 다음 요청에 "그 호출의 결과"로 붙어 모델에게 돌아간다.

<!--
이 스펙은 지도 행 6(학습자 입력 채널)의 확신도·사고 필드를 흡수한 공유 계약이다. 프로버·교사·연습 스펙이 이 계약을 가리킨다.
행 8(도구 레지스트리와 인자 복구)은 `미작성`이고, 여기서는 질문 도구 배치와 인자 복구의 경계만 쓴다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 에이전트가 질문 도구(`ask_user_question`, `probe`, `recall`, `quiz`, `explain`) 중 하나를 호출한다. 호출 직전에 인자 복구(JSON 문자열로 감싼 `options` 풀기 등)가 먼저 돈다.
2. 도구의 `execute`가 스키마로 못 잡는 교차 규칙(선택지 중복, `correctAnswer`가 선택지에 없음 등)을 검사한다. 위반이면 오류 결과(`isError`)를 돌려줘 같은 턴 안에서 모델이 고쳐 다시 호출한다. 통과하면 "질문을 냈다"는 자리표시 결과를 돌려주고 **턴이 끝난다**. 이 자리표시는 턴 끝의 저장 단계에서 걸러져(R-07) 기록에는 결과 없는 호출이 남는다(결과 없는 질문 호출 = "대기 중인 질문").
3. 학습자 쪽 클라이언트가 질문을 그린다. 선택지는 호출 id로 시드한 순서로 섞고, 채점과 답 객체 구성(`buildAnswer`)도 클라이언트가 한다.
4. 클라이언트가 `POST /api/chat`에 `{chatId, input:{type:"answer", toolCallId, answer}}`를 보낸다. 서버는 `toolCallId`가 대기 중인 질문과 같은지만 확인하고(답 내용은 다시 채점하지 않는다), 답을 그 호출의 `toolResult` 메시지로 기록에 붙인다. 모델이 읽는 `content`는 학습자가 새로 더한 것만 담은 압축 JSON이고, 전체 답 객체는 `details`에 둔다.
5. 같은 메시지에 대기 중인 질문이 더 남아 있으면 저장만 하고 턴을 시작하지 않는다. 마지막 답이 도착해야 반응 턴이 한 번 시작된다.
6. 학습자가 질문을 건너뛰면(해제, `dismissed`) 별도 경로 `POST /api/chats/<chatId>/dismiss`로 같은 형태의 결과가 붙고(R-17) `{kind, dismissed:true}`만 모델에게 보이며 턴은 시작되지 않는다. 다음 학습자 입력이 와야 세션이 이어진다.

### 1.2 범위·통합 지점 [필수]
- 제공: 질문 도구 5종의 입력 계약과 거부 규칙, 답 객체(`QuestionAnswerData`)와 모델에게 보이는 압축형, 답이 기록에 붙는 방식, 확신도·사고글 두 채널의 의미, 선택지 순서 섞기·채점 규칙, 해제 처리, 병렬 질문 게이트.
- 제외:
  - 질문 UI(질문 독, 확신도 슬라이더, 음성 받아쓰기 UI). 단 UI가 정하는 데이터 의미(셔플 시드, 확신도 칸, 어떤 필드를 보내는지)는 1.3·1.4에 넣었다.
  - `nodeId` 검증과 `type`(predict/check)의 교육적 의미 → `plan-tree.md`, `teaching-cycle.md`.
  - 질문을 어떻게 잘 만드는가의 프롬프트 독트린 → 프로버·교사 스펙(여기에는 R-22에 공통 권고만).
  - 도구 레지스트리 전체와 job 도구 내부(지도 행 8·11, `미작성`). 여기서는 질문 도구 배치·토글(R-01)과, 모든 도구에 같이 걸리는 공통 인자 복구 규칙(R-02)·검증 경계(R-24)·결과 모양(R-25)만 둔다.
  - 세션 기록 형식 전체(S1, `미작성`). 여기서는 `toolResult`·`details`와 "대기 중인 질문" 판정에 필요한 만큼만.
- 외부 의존: 세션 저장소(`ChatStore`의 `getChat`/`saveMessages`), 에이전트 루프(pi-agent-core: `terminate`, 도구 결과 처리)와 pi-ai의 `validateToolArguments`(스키마 검증, 소스는 이 저장소 밖이라 R-24는 `추론` 수준), 클라이언트(UI)가 `answer`·`dismiss` 입력을 만들어 보낼 것.
- 소유 상태·부작용: 질문 호출(결과 없음)과 답 `toolResult`가 세션 기록의 메시지로 남는다. 서버는 답을 받으면 턴을 시작하기 전에 기록에 먼저 저장한다(write-ahead).

### 1.3 인터페이스와 데이터 의미 [필수]

**질문 도구 5종** (모델이 보는 이름. 한 에이전트에는 채점 질문 도구가 한 번에 하나만 있다: 객관식이면 `probe`/`quiz`, 자유서술이면 `recall`/`explain`)

| 도구 | 에이전트 | 입력 | 의미 |
|---|---|---|---|
| `ask_user_question` | 프로버·교사 | `question`, `details?`, `options?`(2개 이상, 각 `label`, `value?`, `description?`), `multiSelect?` | 채점하지 않는 질문(선호·방향·목표 구체화). `options`가 없으면 글로 답하고, 있으면 학습자가 "Other"를 골라 직접 쓸 수도 있다 |
| `probe` | 프로버 | `question`, `options`(2개 이상, 각 `label`, `value?`), `multiSelect?`, `explanation`, `correctAnswer`(option value 또는 value 배열), `details?` | 객관식 채점 질문. 선택지에 "모르겠음"은 도구가 자동으로 붙이므로 모델이 넣지 않는다 |
| `recall` | 프로버 | `question`, `correctAnswer`(문장), `details?` | 자유서술 채점 질문. 정답은 질문을 내기 전에 확정한 문장이고, 학습자 답을 모델이 이 문장에 대해 채점한다 |
| `quiz` | 교사 | `type`("predict"\|"check"), `nodeId`, 그리고 `probe`와 같은 필드 | `probe`에 교육 사이클 역할과 계획 노드 위치가 더해진 것 |
| `explain` | 교사 | `type`, `nodeId`, 그리고 `recall`과 같은 필드 | `recall`에 같은 두 필드가 더해진 것 |

`type`·`nodeId`가 하는 일은 `teaching-cycle.md`·`plan-tree.md`가 정한다. 이 스펙은 두 필드가 교사 도구에서 필수라는 사실만 가진다. `option`에는 `description` 필드가 없다(채점 질문). 모델이 설명에 정답 단서를 흘려 소거법으로 풀리게 하기 때문이다. `ask_user_question` 선택지만 `description`을 가진다.

**답 객체 `QuestionAnswerData`** (클라이언트가 만들고 `toolResult.details`에 그대로 저장)

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `kind` | "quiz"\|"ask"\|"explain" | 도구→종류 접기: `quiz`·`probe`→quiz, `explain`·`recall`→explain, `ask_user_question`→ask |
| `tool` | string? | 호출된 도구 이름. 이름 바꾸기 전 기록에는 없다 |
| `questionType` | "predict"\|"check"? | quiz 교사 호출만. 프로브 답과 옛 기록에는 없다 |
| `questionText` | string | 질문 문장 스냅샷 |
| `options` | list of {index, label}? | 표시 순서 스냅샷 |
| `answers` | list of {label, value, index} | 선택한 항목. `index`는 **섞인 표시 순서 기준 1부터**. 표시 순서로 정렬됨 |
| `dontKnow` | boolean | "모르겠음". 오답이 아니라 진짜 지식 공백으로 읽는다 |
| `other` | string? | ask의 "Other" 글 |
| `text` | string? | 자유서술(ask 글 모드, explain/recall)의 답 |
| `thinking` | string? | 질문 자체에 대한 학습자의 추론(예전 이름 `note`, 읽을 때 `thinking ?? note`) |
| `readingThinking` | string? | 교사가 가르치는 글을 읽는 동안의 생각. 확인(check) 답 제출 때 따로 얹힌다 |
| `confidence` | number? | quiz 전용. 고른 답이 맞을 확률을 학습자가 말한 값(0~100). `dontKnow`이면 없다 |
| `correct` | boolean? | quiz 전용. 선택 집합이 정답 집합과 정확히 같을 때만 true. `dontKnow`이면 false |
| `correctIndices` | list of int? | quiz 전용(표시 순서 기준, 렌더링용) |
| `committed` | string? | explain 전용. 모델이 확정해 둔 정답 문장(렌더링용). 클라이언트는 explain을 채점하지 않는다 |
| `explanation` | string? | quiz 전용(렌더링용, 모델이 쓴 것) |
| `dismissed` | boolean? | 건너뜀 표식 |
| `answeredAt` | ISO string | 답한 시각 |

**모델에게 보이는 압축형** (`toolResult.content[0].text` = 아래 객체의 JSON 문자열). 모델이 만든 질문·선택지·정답·해설은 호출 인자에 이미 있으므로 되풀이하지 않고, 학습자가 더한 것만 담는다.

| 키 | 조건 |
|---|---|
| `kind` | 항상 |
| `dismissed: true` | 해제이면 이것만(다른 키 없음) |
| `dontKnow: true` | 모르겠음이면 |
| `answers` (각 `{index, label}`) | 선택이 있으면 |
| `text`, `other` | 값이 있으면 |
| `correct` | 값이 있고 `dontKnow`가 아닐 때 |
| `confidence` | 값이 있을 때 |
| `thinking` | `thinking ?? note`가 있을 때 |
| `thinkingWhileReading` | `readingThinking`이 있을 때(키 이름이 다르다) |

**클라이언트가 서버에 보내는 입력** (`POST /api/chat`의 `input`, `chatId`와 함께. 해제만 경로가 다르다)

| 입력 | 형태 | 의미 |
|---|---|---|
| 답 | `{type:"answer", toolCallId, answer: QuestionAnswerData}` | 대기 중인 질문에 대한 답. 턴을 시작한다 |
| 해제 | `POST /api/chats/<chatId>/dismiss`, 본문 `{input:{type:"dismiss", toolCallId, answer}}` (`answer.dismissed`가 true여야 함) | 턴을 만들지 않는 조용한 경로. `/api/chat`에는 보내지 않는다(거기서는 400 `unknown input type: dismiss`) |
| 계속 | `{type:"continue"}` | 기록을 그대로 두고(연습 세션의 보류 해제 쌍만 예외) 다음 턴을 시작한다(R-23) |

**HTTP 경로와 상태 코드**

| 경로 | 조건 | 응답 |
|---|---|---|
| `POST /api/chat` | 본문이 JSON이 아님 | 400 `{error:"Invalid JSON body"}` |
| 〃 | `chatId`가 비어 있거나 문자열이 아님, 또는 그 채팅이 없음 | 404 `{error:"Unknown chat"}` |
| 〃 | `input` 검증 실패(`ChatInputError`: 객체 아님, 알 수 없는 `type`, 필수 필드 없음, R-10의 대기 질문 불일치) | 400 `{error:<메시지>}` |
| 〃 | 모델·제공자 키 게이트(범위 밖) | 503 |
| 〃 | 답을 붙였더니 같은 메시지의 형제 질문이 남음(R-18) | 200, 본문 `data: {"type":"turn-settled"}` 다음 `data: [DONE]`인 `text/event-stream`, 기록만 저장 |
| 〃 | 이 채팅에 이미 턴이 실행 중(R-20) | 409 `{error:"A turn is already running for this session"}` |
| 〃 | 정상 시작 | 200 `{ok:true}` (턴은 백그라운드, 스트림은 별도 GET으로 붙음) |
| `POST /api/chats/<id>/dismiss` | 채팅 없음 / 본문·`input` 검증 실패 / 대기 호출 불일치·종류 불일치 | 404 `{error:"Unknown chat"}` / 400 `{error:<메시지>}` |
| 〃 | 이 채팅의 턴이 실행 중(R-26) | 202 `{ok:true, parked:true}` |
| 〃 | 정상 | 200 `{ok:true}` |

**클라이언트의 질문 데이터(`QuestionData`) 구성** (질문 독, 호출 인자가 입력. 기록에는 복구 전 원본 인자가 남으므로(R-02) 클라이언트가 같은 복구를 다시 한다)
- `kind` = 도구→종류 접기(위 표). `mode`: quiz 종류는 `multiSelect === true`면 multi-select, 아니면 single-select. ask는 `options`가 있으면 같은 규칙, 없으면 text. explain 종류는 항상 text.
- `options` = `normalizeOptions(호출의 options)`(C-05): 각 선택지의 label·value·description을 trim하고 `value`는 비면 label로 대체, 라벨이 빈 선택지는 버리고, 값이 중복이면 예외. quiz 종류이고 선택지가 있을 때만 섞는다(R-14). `questionType` = quiz 종류일 때만 `normalizeQuizType(input.type)`(없거나 모르는 값이면 없음. 프로브의 `probe` 호출은 `type`이 없다). explain 종류에는 `questionType`이 없다.
- quiz 종류: `correctIndices = resolveCorrect(correctAnswer, 섞은 options).indices`(풀리지 않으면 빈 목록), `explanation` 보관. explain 종류: `committedAnswer = correctAnswer`.

**확신도 칸**: `CONFIDENCE_STOPS = [0, 30, 50, 70, 90, 100]`, 기본 칸은 50(인덱스 2). 클라이언트는 이 칸 값만 보내고 반올림·클램프는 `buildAnswer`가 한다(R-15). 칸 간격이 일부러 고르지 않다(위쪽 해상도를 높임). 50은 안 건드린 값과 일부러 고른 값을 구분하지 못한다.

**자리표시 결과** (질문이 통과했을 때): 텍스트 "Question posed — the turn ends here; the learner's graded answer arrives as this call's result.", `details: null`, `terminate: true`(코드 문자열은 C-12에서).

### 1.4 행동 규칙과 남은 질문 [필수]

범례: **[강제]** 코드가 지킴, **[권고]** 프롬프트가 모델에게 요청할 뿐 코드는 막지 않음.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [강제] 에이전트 도구 구성과 토글 | 프로버: `probe`(또는 자유서술이면 `recall`) + `ask_user_question` + 학습자 파일 도구 `read`·`ls`·`find`·`grep` + `research` + `pdf` + `probe_done`(+ 그래프 읽기 도구가 설정으로 열려 있으면 `list_sessions`·`list_propositions`). 교사: `quiz`(또는 `explain`) + `ask_user_question` + 파일 도구 + `plan_init` + job 도구(`research`·`demo`·`visual`·`pdf`). 자유서술 전환은 설정 `agent.tools.explain === true`일 때만이고 아니면 객관식이다. **토글**: 설정 `agent.tools`는 쓰기 API가 `research`·`demo`·`visual`·`pdf`·`explain` 다섯 키만 받는다(다른 키나 불리언이 아닌 값은 400). 그래서 설정 UI·API로는 `quiz`/`explain`(도구)/`probe`/`recall`/`ask_user_question`/파일 도구/`plan_init`/`probe_done`을 끌 수 없다. 반면 읽는 쪽은 느슨해서 불리언인 키는 이름과 무관하게 보존하고, 도구 팩토리는 `enabled[이름] === false`인 도구를 **이름 불문** 레지스트리에서 뺀다. 예외 둘: ① 필터 입력에서 `quiz`·`explain` 키를 먼저 지우므로(`withoutMechanics`) `explain`은 전환 스위치로만 쓰이고 `quiz:false`는 무시된다. ② 프로버의 `probe_done`은 필터 뒤에 다시 넣는다. 그 밖의 이름(`probe`·`recall`·`ask_user_question`·파일 도구·`plan_init`)은 손으로 편집한 설정 파일에 `false`가 있으면 팩토리가 빼 버린다(막는 코드는 쓰기 검증뿐). 완성된 레지스트리의 모든 도구는 R-02의 공통 복구로 감싼다 | 코드 확인 |
| R-02 | [강제] 질문 호출 직전(모든 도구에 공통) | 순서: ① 도구 자체의 `prepareArguments` — 질문 도구는 `options`가 **문자열**이고 `JSON.parse`한 결과가 **배열**일 때만 그 배열로 바꾼다(파싱 실패·배열이 아닌 JSON은 그대로) → ② 레지스트리 공통 복구 → ③ 스키마 검증(R-24) → ④ `execute`. 공통 복구는 스키마 최상위 속성마다, 값이 **문자열**일 때만 `JSON.parse`해 보고 아래일 때 파싱값으로 교체한다: (a) 속성이 리터럴 합집합이고 그 문자열이 이미 멤버가 아닌데 파싱값이 멤버(`"\"predict\""` → `predict`; 이미 `predict`이면 그대로; `'predict'`·`Predict`·`predict `처럼 JSON이 아니거나 멤버와 다른 값은 풀리지 않는다); (b) null을 받는 속성이고 파싱값이 null; (c) 속성 `type`이 boolean이고 파싱값이 boolean; (d) number/integer이고 파싱값이 number; (e) array이고 파싱값이 배열. 이 밖의 속성(문자열 속성, 객체 속성, `correctAnswer`처럼 string\|array 합집합)은 건드리지 않고(`correctAnswer`의 배열 문자열은 R-05가 푼다), 아무것도 안 바꿨으면 입력 객체를 그대로 돌려준다. 입력이 객체가 아니면 그대로. 호출은 복구 전 원본 인자가 기록에 남는다 | 코드 확인 |
| R-03 | [강제] `ask_user_question`·`probe`·`quiz`의 `options` | 선택지마다 순서대로: `label.trim()`이 비면 문제 `options[i].label is empty — every option needs a label.`을 내고 그 선택지는 키 목록에 넣지 않는다. 아니면 키는 `value.trim() \|\| label.trim()`이고 이미 나온 키와 같으면 문제 `Two options resolve to the same value "<키>" — options must be distinct.`(키는 그대로 목록에 추가). 문제가 하나라도 있으면 `isError` 결과와 문제 목록(R-25의 모양)을 돌려줘 모델이 같은 턴에서 고쳐 다시 부른다(턴은 끝나지 않는다). `probe`·`quiz`는 선택지 문제 목록 뒤에 R-04 문제가 이어 붙고, `quiz`는 그 뒤에 `nodeId` 문제가 붙는다(plan-tree.md) | 코드 확인 |
| R-04 | [강제] `probe`·`quiz`의 `correctAnswer` | 선택지 키 집합에 대해 복구(R-05)한 뒤 중복을 제거한 목록을 본다. 목록이 비었거나 빈 문자열 원소가 있으면 문제 `correctAnswer is required — provide the value (or label) of the correct option(s).` 하나만 더하고 나머지 검사는 건너뛴다. 아니면 키 집합에 없는 값마다 `correctAnswer "<v>" does not match any option value. Valid values: "a", "b", "c". Copy the exact value (or label) of the intended option — never a paraphrase or slug.`(키를 쌍따옴표로 감싸 `, `로 잇는다), 값이 둘 이상인데 `multiSelect !== true`이면 `correctAnswer lists <N> values but multiSelect is not true — …`(전체 문구는 C-02) | 코드 확인 |
| R-05 | [강제] `correctAnswer` 값 비교(`coerceCorrectAnswer`) | 배열이면 원소마다 `clean`. 문자열이면: ① `trim()`한 값이 선택지 키와 같으면 그 값 하나(키 자체가 `[…]` 꼴이어도 그대로). ② 아니고 `trim()`한 값이 `[`로 시작해 `]`로 끝나면 `JSON.parse`해 배열이면 원소마다 `clean(String(원소))`. ③ 그 밖(파싱 실패·배열 아님 포함)은 `[clean(원문)]`. `clean(v)`는 `v.trim()`이 선택지 키와 같으면 그 trim 값, 아니면 `stripModelValueDebris(v)`(양끝의 공백·`:`·`.`·`"`·`'`·백틱의 아무 조합을 반복 제거, 안쪽은 건드리지 않음). 이 벗기기는 소속 비교에만 쓰고 자유 텍스트에는 쓰지 않는다. 채점 쪽 `resolveCorrect`도 같은 복구를 선택지(섞은 뒤) 값에 대해 하고, 각 값을 `trim()`해 값→1부터의 표시 인덱스로 바꾸며 중복을 없애고 오름차순으로 정렬한다 | 코드 확인 |
| R-06 | [강제] `recall`·`explain`의 `correctAnswer` | `trim()`해서 비면 문제 `correctAnswer is required — commit to the full correct answer BEFORE posing the question.`으로 거절(결과 모양은 R-25). 그 밖의 검사는 없다 | 코드 확인 |
| R-07 | [강제] 질문 호출이 검증을 통과 | `terminate: true` 자리표시 결과. 이 호출이 실린 메시지의 질문 호출이 **모두** 오류 없이 해결되면 턴 종료 훅(`finishTurn`)이 한 번 더 `end`를 걸어, 질문과 다른 도구가 섞인 배치도 거기서 끝난다. 질문 호출 중 하나라도 `isError`면 끝내지 않고 모델이 고치게 한다. **자리표시는 저장하지 않는다**: 턴이 끝나 기록에 붙일 때(`persistTurn`) 이 턴의 메시지 중 `role:"toolResult"`이고 `toolName`이 질문 도구 집합(R-09)에 속하며 `isError`가 아닌 것은 건너뛴다(오류 결과는 저장돼 모델의 재시도 맥락이 된다). 중단(abort)된 턴도 부분 기록을 저장하므로 결과 없는 질문 호출이 남는다. 학습자 답이 도착해야 그 호출의 결과가 생긴다 | 코드 확인 |
| R-08 | [강제] 질문 도구 실행 방식 | 모두 순차 실행(`executionMode: sequential`)이라 병렬 호출도 모델이 호출한 순서대로 처리된다 | 코드 확인 |
| R-09 | [강제] 대기 중인 질문 판정(`danglingQuestionOf`) | 기록에서 **가장 최근 assistant 메시지**(내용이 무엇이든 가장 마지막 assistant 역할)를 찾아, 그 안의 도구 호출을 앞에서부터 보며 질문 도구 호출이면서 **결과가 없는 첫 번째** 것을 대기 호출로 한다. "결과가 있다" = 그 메시지 뒤 어디에든(바로 다음이 아니어도) 같은 `toolCallId`의 `toolResult`가 하나라도 있음(`isError` 무관). 질문이 모두 해결됐거나 질문 호출이 없으면 없음(그 앞의 옛 assistant 메시지는 보지 않는다). 질문 도구 집합: `quiz`, `probe`, `ask_user_question`, `explain`, `recall` | 코드 확인 |
| R-10 | [강제] 답 입력 | `toolCallId`가 비어 있거나 문자열이 아니면 400 "answer input requires toolCallId", `answer`가 `null`이거나 `typeof`가 `object`가 아니면 400 "answer input requires the graded answer object"(배열은 통과한다). `toolCallId`가 R-09의 대기 호출과 다르거나 대기 호출이 없으면 400 "answer input targets no pending question call". 통과하면 **내용은 서버가 다시 채점하거나 검증하지 않고** 그대로 `details`에 저장한다. 즉 정오·확신도는 클라이언트 말이다. 상태 코드·본문은 1.3의 HTTP 표 | 코드 확인 |
| R-11 | [강제] 답 → 기록 | `role:"toolResult"`, `toolCallId`, `toolName`(대기 호출의 도구 이름), `content`=[`{type:"text", text:<압축형 JSON 문자열>}`], `details`=전체 답 객체, `isError:false`, 새 메시지 `id`, `timestamp`(밀리초). 서버는 이 메시지를 붙여 기록에 먼저 저장한 뒤(R-20의 순서) 턴을 시작한다 | 코드 확인 |
| R-12 | [강제] 압축형 규칙 | 1.3의 표대로. 특히 `dismissed`이면 `{kind, dismissed:true}`만(그 답에 `readingThinking`이 있어도 모델에게는 안 보임), `dontKnow`이면 `correct`는 생략(암묵적으로 오답)하고 `confidence`는 애초에 없다. 각 키는 조건이 **참인 값**(truthy)일 때만 담긴다: `text`·`other`·`thinking`·`thinkingWhileReading`은 빈 문자열이면 생략(`thinking`이 `""`이면 `note`로 넘어가지 않고 생략), `answers`는 배열이고 비지 않을 때, `correct`는 `undefined`가 아니고 `dontKnow`가 아닐 때(`false`도 담김), `confidence`는 `undefined`가 아니면(0도 담김. 압축 단계가 `dontKnow`를 보고 거르지는 않는다). 입력이 배열이 아니거나 필드가 빠져도 예외 없이 생략만 한다. **직렬화**: 키 삽입 순서가 `kind, dontKnow, answers, text, other, correct, confidence, thinking, thinkingWhileReading`이고 `answers`의 각 원소는 `{index, label}` 순서다. 문자열은 JS `JSON.stringify` 그대로 — 키·값 사이와 원소 사이에 공백이 없고(`{"kind":"quiz",…}`), 비ASCII 글자는 이스케이프하지 않으며, 제어 문자만 `\n`·`\u001f` 같은 형태(16진 소문자)로 이스케이프한다 | 코드 확인 |
| R-13 | [강제] 답 객체 구성(`buildAnswer`) | 모든 종류에 `kind`, `tool`(주어졌을 때), `questionType`(없으면 생략), `questionText`, `options`(표시 순서 `{index, label}` 스냅샷), `dontKnow`(= 요청의 `dontKnow === true`), `answers`, `answeredAt`(ISO 문자열)이 들어간다. 선택한 `value`를 선택지 표시 순서의 `{label, value, index}`로 바꾸고(모르는 value는 무시, **같은 value를 두 번 보내면 두 번 담긴다**) `index` 오름차순으로 정렬. `other`·`text`·`thinking`·`readingThinking`은 앞뒤 공백을 자르고 비면 생략. quiz만 `correct = dontKnow ? false : (선택 인덱스 집합 == 정답 인덱스 집합)`(개수와 정렬한 값이 같아야 함. 중복을 보냈으면 개수가 달라 틀림)이고 `correctIndices`·`explanation` 스냅샷을 담는다. quiz만 `confidence`를 담는데 `dontKnow`가 아니고 요청에 값이 있을 때 `max(0, min(100, round(값)))`이며, `round`는 **JS `Math.round`(소수 .5는 +∞ 쪽으로 올림)**다(파이썬 `round()`의 은행가 반올림과 다르다). explain은 채점하지 않고 `committed`만 스냅샷 | 코드 확인 |
| R-14 | [강제] 선택지 순서 | **quiz 종류(`probe`·`quiz`)만** 섞는다(ask·explain은 안 섞음). 알고리즘(C-07): 시드 문자열의 **UTF-16 코드 단위**마다 `h = (h XOR 코드단위) × 16777619 mod 2^32`(FNV-1a 32비트, 초기값 2166136261, UTF-8 바이트가 아니다), 상태 `a = h`. 난수 한 번: `a = (a + 0x6D2B79F5) mod 2^32; t = imul(a XOR (a>>>15), 1\|a); t = (t + imul(t XOR (t>>>7), 61\|t)) XOR t; 결과 = ((t XOR (t>>>14))>>>0) / 2^32`(mulberry32, 모든 연산 mod 2^32, 시프트는 부호 없는 32비트 값 기준). 섞기는 `i = n-1 … 1`을 내려가며 `j = ⌊난수 × (i+1)⌋`를 뽑아 `out[i]`와 `out[j]`를 맞바꾼다(난수는 반복마다 한 번, 총 n-1번). 시드는 `toolCallId`이므로 같은 호출은 다시 열어도 같은 순서다(시험 벡터 T-17~T-19). `correctAnswer`는 value로 가리키고 섞은 **뒤에** value→1부터의 표시 인덱스로 바꾼다. 따라서 `answers[].index`·`correctIndices`는 표시 순서 기준이고 모델이 쓴 원래 선택지 순서에 적용하면 안 된다 | 코드 확인(알고리즘). 시험 벡터는 코드를 읽고 옮긴 계산이며 원본 실행 값이 아님 |
| R-15 | [강제] 확신도 전송 | quiz 답에는 슬라이더 칸(1.3의 확신도 칸 중 하나, 50도 실제 값)이 항상 요청에 실리고 `buildAnswer`가 `dontKnow`이면 뺀다. 칸 밖 값에 대한 서버 검증은 **없다**: 서버는 `answer` 객체를 검사하지 않으므로(R-10) 기록에는 클라이언트가 보낸 `confidence`가 그대로(칸 밖·비정수·문자열도) 저장된다. 클라이언트가 하는 것은 `buildAnswer`의 반올림·0~100 클램프뿐이다(R-13). explain·ask 답에는 확신도가 없다 | 코드 확인 |
| R-16 | [강제] 두 사고 채널 | `thinking`은 `mode`가 text가 아닐 때만 클라이언트가 보낸다(`qd.mode !== "text"`): 선택지가 있는 답(quiz 종류, 선택지가 있는 ask). 선택지 없는 ask(글 모드)와 explain·recall은 글 자체가 `text`라 `thinking`을 보내지 않는다. `readingThinking`은 읽는 동안 쓴 초안이 답 제출 시점에 `{...answer, readingThinking}`으로 얹힌다(해제에도 얹히지만 R-12로 모델에게는 안 감). 초안 칸은 **교사 단계(`teach`)의 `quiz`·`explain` 질문 중 `type`이 `predict`가 아닌 것**(`check`이거나 `type`이 없는 옛 기록)이 대기 중일 때만 열리고(`questionNeedsReveal`), 질문이 바뀌면 초안은 비워진다. 모델에게는 `thinkingWhileReading` 키로 전해진다. 두 채널은 섞지 않는다 | 코드 확인 |
| R-17 | [강제] 해제 | 경로는 `POST /api/chats/<id>/dismiss`이고 본문 `{input:{type:"dismiss", toolCallId, answer}}`. 이 라우트는 `dismiss-problem`(연습 문제 포기, 연습 스펙의 일)도 받는다. 검증 400 메시지: `toolCallId`가 비면 "dismiss input requires toolCallId", `answer`가 객체가 아니면 "dismiss input requires the dismissal answer object", `answer.dismissed !== true`이면 "dismiss input's answer must be a dismissal (dismissed: true)", 대기 호출(R-09)이 아니면 "dismiss input targets no pending question call", `answer.kind`가 `toolQuestionKind(대기 호출의 도구)`와 다르면 "dismiss input's answer kind does not match the question". 통과하면 R-11과 같은 모양의 `toolResult`(`details`=전달된 `answer`)가 붙고 **턴을 시작하지 않는다**(깨우기 없음, 응답 `{ok:true}`). 기록의 마지막 메시지가 해제 결과인 동안은 연속 턴(`needsContinuation`이 거짓)과 자동 깨움(job 전달 보류)이 모두 막히고 다음 사용자 입력을 기다린다. 클라이언트가 만드는 해제 답은 `{kind, questionText, dontKnow:false, answers:[], dismissed:true, answeredAt}`(+ 있으면 `readingThinking`)다 | 코드 확인 |
| R-18 | [강제] 병렬 질문 게이트 | `answer` 입력을 붙인 뒤(메모리상 `기록+appends`)에도 R-09 판정이 대기 호출을 돌려주면(같은 assistant 메시지의 다른 질문이 결과 없이 남음) `기록+appends`만 저장하고(`record-changed` 이벤트 발행) 1.3 표의 `turn-settled` 응답으로 끝낸다 — 턴도 시작하지 않고 409 검사도 하지 않는다. 마지막 답이 도착해야 한 번의 반응 턴이 모든 결과를 해당 호출 옆에 붙여 시작된다 | 코드 확인 |
| R-19 | [강제] 중단된 턴의 대기 호출 | 모델 입력을 만들 때(`toLlmMessages`) 모든 assistant 메시지에 대해, 그 메시지의 **모든 도구 호출**(질문 도구만이 아니다) 중 그 뒤 어느 메시지에도 같은 `toolCallId`의 `toolResult`가 없는 것마다 `{role:"toolResult", toolCallId, toolName, content:[{type:"text", text:INTERRUPTED_TEXT}], isError:false, timestamp:<그 assistant 메시지의 timestamp>}`를 그 assistant 메시지 **바로 뒤에** 끼운다(호출이 여럿이면 호출 순서대로). 결과 유무는 뒤쪽 모든 `toolResult`의 id 집합으로 본다(`isError`·위치 무관). 합성은 모델 입력에만 있고 기록은 바뀌지 않는다. 고정 문장은 C-15 | 코드 확인 |
| R-20 | [강제] 한 채팅 한 턴과 처리 순서 | `POST /api/chat`의 처리 순서: 본문 파싱(400) → 채팅 조회(404) → 모델·키 게이트(503, 범위 밖) → 컴팩션 게이트(범위 밖) → 입력의 기록 추가분 계산(`inputAppends`, 위반이면 400) → **병렬 질문 게이트(R-18, 저장 후 종료)** → **턴 시작 시도: 이미 실행 중이면 409 "A turn is already running for this session"(아무것도 저장하지 않음)** → 쓰기 선행 저장(R-11) → 턴. 따라서 턴이 도는 중에도 형제 질문이 남는 `answer`는 저장되고 409가 나지 않으며, 마지막 답이나 `text`·`continue` 입력은 409다 | 코드 확인 |
| R-21 | [권고] 확신도 해석 | 정오×확신도: 맞고 확신 높음=단단함(넘어감), 맞고 낮음=취약하거나 우연(한 번 더 건드림), 틀리고 높음=굳은 오개념(균열을 짚고 둘레를 다시 가르침), 틀리고 낮음=아슬한 오답이나 정직한 공백(작은 교정), `dontKnow`=지식 공백(오답 아님). 50은 동전 던지기, n지선다의 우연 확률은 1/n이며 확신도가 그 이하이면 "고른 답이 틀렸다고 믿는다"는 정직한 표시로 읽는다 | 코드 확인(프롬프트 텍스트). 모델이 따르는지는 미확인 |
| R-22 | [권고] 질문 제작과 사고글 읽기 | 객관식은 해설을 `correctAnswer`보다 먼저 쓴다(추론 후 확정). 선택지는 맨 주장만 담고 길이·문체가 같아야 하며, 정답을 먼저 쓰고 구체적 오개념별 오답으로 변형하고(그럴듯한 오류), 정답만 굵게 하는 식의 비대칭을 피한다. 자유서술은 정답 문장에 엄격히 대조하고 근접 오답은 맞힌 것과 놓친 것을 짚는다. 모든 필드에 LaTeX. 한 턴에 질문 하나. 사고글은 가장 정밀한 이해 전달이므로 전부 읽고, 받아쓰기로 쓴 글의 오타를 개념 오류로 보지 않는다 | 코드 확인(프롬프트 텍스트). 모델이 따르는지는 미확인 |
| R-23 | [강제] `continue` 입력 | 서버는 `{type:"continue"}`를 검증 없이 받아(기록이 어떤 모양이든 400이 나지 않는다) 기록에 붙이는 것 없이(연습 세션의 보류된 문제 해제 쌍만 예외, 연습 스펙) R-20의 순서로 턴을 시작한다. 이미 턴이 실행 중이면 409. 언제 보낼지는 클라이언트가 `needsContinuation(기록)`으로 정한다: 마지막 메시지가 `toolResult`이고 해제 결과가 아니며, 그 연속된 `toolResult` 묶음 바로 앞이 assistant 메시지이고 그 메시지의 도구 호출이 1개 이상이면서 **모두** 묶음에 결과가 있고, 묶음에 성공한 연습 문제 출제 응답이 없을 때(채팅 열 때 한 번, 기록을 서버와 다시 맞출 때) | 코드 확인 |
| R-24 | [강제] 스키마 검증 경계 | 질문 도구 스키마는 TypeBox 객체이고 `additionalProperties`를 막지 않는다. 에이전트 루프는 인자를 R-02 복구 뒤 `Value.Convert`(느슨한 형 변환, 예: `correctAnswer`가 숫자 17이면 문자열 "17")로 맞춰 `Value.Check`로 검증하고, 실패하면 `execute`를 부르지 않고 오류 결과를 모델에게 돌려줘 같은 턴에서 다시 부르게 한다(질문 도구 오류는 R-07대로 턴을 끝내지 않는다). 스키마가 모르는 추가 키는 구조 검증을 통과하며 `execute`는 읽지 않는다(교사가 아닌 쪽에 `nodeId`가 있어도 표시용 파싱이 같은 `Value.Check`를 통과하는 것이 근거). 오류 결과의 문구는 외부 라이브러리가 만든다 | 추론: pi-ai 검증 본문은 이 저장소에 없다. `Convert→Check`는 `tool-parts.ts:37-52` 주석 기준, 추가 키 허용은 같은 파일의 표시용 파싱이 `nodeId` 포함 호출을 통과해야 한다는 데서 도출 |
| R-25 | [강제] 도구 결과의 모양 | 질문·`probe_done` 등 서버측 도구의 `execute` 반환값이 도구 결과 메시지가 되는 규칙. ① 검증 실패(`invalidInputResult`): `isError:true`, `content=[{type:"text", text:"Invalid tool input for tool \"<도구>\":\n- <문제1>\n- <문제2>"}]`, `details={tool, problems:[…]}`. ② 자리표시(`questionResult`): 1.3의 고정 문장, `details:null`, `terminate:true`(`isError` 없음). ③ `serverExecute`(`probe_done`·job 도구·그래프 도구의 래퍼): 반환값이 **문자열 `text`를 가진 객체**면 `content=[text 블록(+이미지)]`, `details = 그 객체의 details ?? null`; 그 밖의 값은 문자열이면 그대로, 객체면 `JSON.stringify`한 문자열 하나가 `content`이고 `details`는 반환값 자체. 즉 `{ok:false,error}` 반환은 `content`가 그 객체의 JSON 문자열, `details`가 같은 객체이며 `isError`는 붙지 않는다. 래퍼는 호출마다 30초 시간 제한과 중단 신호를 건다 | 코드 확인 |
| R-26 | [강제] 턴 실행 중의 해제 | 해제 라우트는 이 채팅의 턴이 실행 중이면 검증하지 않고 입력을 채팅당 한 칸에(뒤 것이 앞 것을 덮어씀) **보류**하고 202 `{ok:true, parked:true}`를 돌려준다. 턴이 끝나 `persistTurn`으로 기록이 저장된 직후, 턴 종료 표시 전에 보류분을 저장된 기록에 R-17의 검증으로 적용한다(대기 호출이 사라졌거나 종류가 다르면 오류를 삼키고 버림, 적용하면 `record-changed` 발행) | 코드 확인 |
| R-27 | [강제] 기록에 턴 메시지가 붙는 시점 | 한 요청의 기록 저장은 두 번이다: 입력의 추가분을 턴 시작 전에 저장(R-11, R-20)하고, **그 턴의 모든 새 메시지(assistant 메시지·도구 결과)는 턴이 끝날 때 한 번에** 붙인다(R-07의 필터 적용). 따라서 턴 도중 `getChat`으로 읽은 기록에는 이번 턴의 assistant 메시지와 호출이 없다(`probe_done`이 읽는 기록, probe-measurement.md R-05·R-06) | 코드 확인 |

- 불변식: 질문 호출에는 결과가 하나뿐이고 그것은 학습자의 답이다(자리표시는 모델 입력에서만 쓰이고 영속하지 않음, 중단된 호출만 합성 결과가 모델 입력에 끼움). 답 객체의 인덱스는 항상 그 답이 제출될 때의 표시 순서 기준이다. 전제: 한 채팅에서 동시에 한 턴만 돈다(R-20).
- 미결정: 없음
- 확인 한계: 코드를 실행하지 않았다. 원본 테스트는 `tests/question-tools.test.ts:255-320`(토글)과 `tests/tool-heal.test.ts:55-190`(복구)만 읽었고 이것도 실행하지 않았으며, 코드를 읽고 얻은 결론과 어긋나는 점은 없었다. pi-ai의 스키마 검증과 pi-agent-core 루프의 본문은 이 저장소에 없어 R-24는 `추론`이고 거절 문구는 알 수 없다. 프롬프트 규칙을 모델이 따르는 정도는 확인하지 못했다. 시험 벡터(T-17~T-19)는 원본 실행이 아니라 코드를 읽고 옮긴 계산이다.

### 1.5 필수 코드 참조 [필수]
라이선스는 AGPL-3.0(overview 1절)이다. 아래 범위는 구현자가 `git -C repos/learnharness show <SHA>:<path>`로 읽는 용도이며 본문 인용은 하지 않는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/core/question-core.ts:158-193` `quizInputBase`; `:303-318` `explainInputBase`; `:367-389` `askInputSchema` | 세 질문 입력 스키마(필드, 필수 여부, `minItems`) | R-03, R-04, R-06 |
| C-02 | `src/core/question-core.ts:85-142` `optionProblems`, `askOptionProblems`, `quizInputProblems`; `:352-357` `explainInputProblems` | 선택지·정답 교차 검증 규칙과 오류 문구 | R-03~R-06 |
| C-03 | `src/core/question-core.ts:609-669` `coerceCorrectAnswer`, `resolveCorrect`, `isCorrect`; `src/core/value-debris.ts:24-26` `stripModelValueDebris` | 정답 값 복구·인덱스 변환·정확 집합 일치 | R-04, R-05, R-13 |
| C-04 | `src/core/question-core.ts:400-501` `OptionAnswer`, `QuestionKind`, `QuestionAnswerData`, `AnswerRequest`, `CONFIDENCE_STOPS` | 답 객체와 요청 타입, 확신도 칸 | 1.3, R-13, R-15 |
| C-05 | `src/core/question-core.ts:543-566` `normalizeOptions` | 클라이언트 쪽 선택지 정규화(트림, 중복 시 예외, JSON 문자열 선택지도 해석) | R-02, R-14 |
| C-06 | `src/core/question-core.ts:693-736` `buildAnswer` | 답 객체 구성과 채점 | R-13, R-15 |
| C-07 | `src/core/question-core.ts:573-605` `seededRandom`, `shuffleOptions` | 문자열 시드 난수(FNV-1a 계열 해시 + mulberry32)와 섞기 | R-14 |
| C-08 | `src/core/question-core.ts:753-787` `dismissedAnswer`, `compactAnswerForModel` | 해제 답과 모델 압축형 | R-12, R-17 |
| C-09 | `src/core/question-core.ts:63-72` `parseOptionsIfString`; `src/agent/tools.ts:67-77` `prepareQuestionArguments`; `src/agent/tools/heal.ts:28-48` `withArgumentHeal`, `healToolRecord`; `src/core/argument-heal.ts:27-96` `healEncodedArguments`와 헬퍼 | 인자 복구 순서(옵션 풀기 → 공통 복구 → 스키마 검증)와 복구 규칙 | R-02 |
| C-10 | `src/agent/tools.ts:79-95` `askUserQuestionTool`; `:205-261` `probeQuizTool`, `teachExplainToolFor`, `probeExplainTool`; `:375-391` `teachQuizToolFor`; `:422-432` `quizMechanics`, `withoutMechanics` | 도구별 execute(검증 → 자리표시)와 객관식/자유서술 전환 | R-01, R-03, R-04, R-06, R-08 |
| C-11 | `src/agent/tools.ts:287-348` `createProberTools`; `:434-466` `createTeacherTools` | 에이전트별 도구 구성 | R-01 |
| C-12 | `src/agent/tool-execute.ts:117-131` `invalidInputResult`; `:214-233` `questionResult` | 검증 실패 결과 모양과 자리표시 결과 | R-03, R-07 |
| C-13 | `src/agent/teacher-agent.ts:152-169` `makeQuestionStopper`; `:203` `finishTurn` | 질문 종료 훅 | R-07 |
| C-14 | `src/core/pending.ts:45-58` `QUESTION_TOOLS`, `toolQuestionKind` | 질문 도구 집합과 종류 접기 | R-09, R-17 |
| C-15 | `src/core/native-messages.ts:136-153` `newAnswerResult`; `:485-493` `resultIdsFrom`; `:512-595` `toLlmMessages`(중단 호출 합성부 `:573-592`); `:602-619` `danglingQuestionOf`; `:657-675` `isDismissedResult`, `endsInDismissal`; `:51-55` `INTERRUPTED_TEXT` | 답 → 결과 메시지, 대기 질문 판정, 합성 결과, 해제 휴지 | R-09, R-11, R-17, R-19 |
| C-16 | `src/core/input-events.ts:44-47`, `:75-148`, `:154-170`, `:197-210` | 답·해제·계속 입력의 검증과 기록 추가 | R-10, R-17 |
| C-17 | `src/server/chat-handler.ts:280-303` | 병렬 질문 게이트, 한 채팅 한 턴 | R-18, R-20 |
| C-18 | `components/question-dock.tsx:262-306`, `:381-394`; `components/chat.tsx:388-412`, `:1656-1669` | 클라이언트가 선택지를 섞고 답 요청을 만들고 읽기 사고글을 얹는 위치 | R-14, R-15, R-16 |
| C-19 | `src/agent/prompts/shared/20-question-tools.md:5-28`; `shared/25-confidence.md:3-11`; `shared/16-mental-model.md:3-5` | 질문 제작·확신도 해석·사고글 독트린(권고) | R-21, R-22 |
| C-20 | `src/core/pending.ts:60-106` `TOGGLEABLE_TOOLS`, `WRITABLE_TOOL_KEYS`, `EnabledTools`, `filterEnabledTools`; `src/server/settings-body.ts:121-132`, `:156-172` 쓰기 검증; `src/core/settings.ts:491-498`, `:512-513` 읽기 쪽 정리 | 토글 가능 도구 목록과 필터 규칙 | R-01 |
| C-21 | `src/server/turn-service.ts:50-84` `persistTurn`; `src/server/chat-handler.ts:499-502` | 턴 끝의 저장과 자리표시 필터 | R-07, R-27 |
| C-22 | `app/api/chats/[id]/dismiss/route.ts:22-65`; `src/server/dismissal-park.ts:45-80` | 해제 라우트와 실행 중 턴의 보류 | R-17, R-26 |
| C-23 | `src/core/native-messages.ts:728-771` `needsContinuation`; `src/core/input-events.ts:211-212`, `:236-244` `dismissalConclusion`; `components/chat.tsx:426-441`, `:717-733` | `continue` 입력과 클라이언트의 전송 조건 | R-23 |
| C-24 | `src/server/chat-handler.ts:145-198`, `:260-324`; `src/server/turn-runs.ts:73-81` `settledTurnResponse` | `/api/chat`의 처리 순서와 응답 | R-18, R-20, 1.3 HTTP 표 |
| C-25 | `src/agent/tool-execute.ts:117-131` `invalidInputResult`; `:155-212` `toToolResult`, `serverExecute` | 도구 결과 변환 규칙 | R-25 |
| C-26 | `src/core/tool-parts.ts:37-52` `boundaryParse` | 스키마 경계(Convert → Check) | R-24 |
| C-27 | `src/core/question-core.ts:212-235` `normalizeQuizType`, `questionNeedsReveal`; `components/chat.tsx:505-538`, `:2275-2294`; `src/core/phases.ts:39-97` | 읽기 사고글 칸이 열리는 조건(교사 단계의 판정 포함) | R-16 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(T-17~T-19의 값은 코드를 읽고 옮긴 계산, 나머지 신규 사례는 코드 읽기에서 도출). 코드를 실행하지 않았고 원본 테스트 사례를 옮기지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-13, R-11, R-12 | `probe` 호출(선택지 value a·b·c, `correctAnswer:"a"`). 학습자가 a를 고르고 확신도 90, `thinking:"x"` | 답 객체 `correct:true`, `confidence:90`, `answers[0].index`는 섞인 표시 순서의 a 위치. 모델이 보는 압축 JSON은 `{kind:"quiz",answers:[{index,label}],correct:true,confidence:90,thinking:"x"}` |
| T-02 | R-13, R-12 | 같은 질문에 학습자가 "모르겠음" | 답 객체 `dontKnow:true`, `correct:false`, `confidence` 없음. 압축 JSON은 `{kind:"quiz",dontKnow:true}`(`correct`·`confidence` 없음) |
| T-03 | R-04, R-13 | `multiSelect:true`, `correctAnswer:["a","b"]`. 학습자가 {a,b}를 고름 / {a}만 고름 | 첫째 `correct:true`, 둘째 `correct:false` |
| T-04 | R-04, R-07 | `correctAnswer:"z"`(선택지에 없음) | 오류 결과(유효 값 목록 포함)가 모델에게 돌아가고 턴은 끝나지 않아 모델이 같은 턴에서 다시 호출한다. 학습자에게는 질문이 가지 않는다 |
| T-05 | R-03 | 선택지 `[{label:"A",value:"x"},{label:"B",value:"x"}]` | 같은 값 "x" 중복으로 거절 |
| T-06 | R-04 | `correctAnswer:["a","b"]`, `multiSelect` 없음 | "multiSelect가 true가 아니다"로 거절 |
| T-07 | R-05 | `correctAnswer:":a"`(콜론이 붙음)이고 선택지 value는 `a` | 통과(접두 콜론 제거 후 일치). value가 정확히 `":a"`인 선택지가 있으면 그대로 일치 |
| T-08 | R-06, R-13, R-12 | `recall` 호출 후 학습자가 글 "…"로 답 | 답 객체 `kind:"explain"`, `text`, `committed`=모델의 정답 문장, `correct` 없음. 압축 JSON에 `text`만 |
| T-09 | R-10 | 대기 질문이 없는데(또는 다른 호출 id로) `answer` 입력 | 400 "answer input targets no pending question call", 기록 불변 |
| T-10 | R-12, R-16 | 답 `dismissed:true`, `readingThinking:"r"` | 압축 JSON `{kind,dismissed:true}`만. `details`에는 전체 보존 |
| T-11 | R-12 | `thinking` 없이 옛 키 `note:"n"`, `readingThinking:"r"` | 압축 JSON에 `thinking:"n"`, `thinkingWhileReading:"r"` |
| T-12 | R-18 | 한 메시지에 질문 호출 둘. 첫 질문에 `answer` | 기록에 결과 하나가 붙고 턴 시작 안 함. 둘째 질문의 `answer`가 오면 턴 한 번 시작 |
| T-13 | R-14 | 같은 `toolCallId`로 선택지 [a,b,c]를 두 번 섞음 | 순서가 같다. `correctAnswer:"b"`이면 `correctIndices`는 섞인 순서에서 b의 1부터의 위치 |
| T-14 | R-13 | `AnswerRequest.confidence`가 130 / 49.6 | 기록값 100 / 50 |
| T-15 | R-02 | `options`가 `"[{\"label\":\"A\"},{\"label\":\"B\"}]"`(문자열) | 배열로 풀려 검증을 통과. 풀 수 없는 문자열은 그대로 두어 스키마가 거절 |
| T-16 | R-17 | 대기 질문에 `/dismiss`로 `{type:"dismiss", answer:{dismissed:true, kind:"quiz"…}}`, 질문은 ask인데 `kind:"quiz"` | 종류 불일치로 400. 일치하면 결과가 붙고 턴 시작 안 함 |
| T-17 | R-14 | `toolCallId:"abc"`, 선택지 value [a,b,c]를 섞음 | 순서 [a,c,b]. 계산: FNV-1a("abc") = 0x1A47E90B, 난수 정수 출력 2218960489(0.51664…), 2833055473(0.65962…). i=2: j=⌊0.51664×3⌋=1 → [a,c,b], i=1: j=⌊0.65962×2⌋=1 → 자기 자신과 교환. `correctAnswer:"b"`이면 `correctIndices=[3]` |
| T-18 | R-14 | `toolCallId:"call_1"`, 선택지 value [a,b,c,d] | 순서 [c,b,d,a]. 계산: h=0xA6591209, 난수 정수 882148140, 732799200, 2698476940 → j=0,0,1: [a,b,c,d] → i=3 ↔ 0: [d,b,c,a] → i=2 ↔ 0: [c,b,d,a] → i=1 자기 자신. `correctAnswer:"a"`이면 `correctIndices=[4]` |
| T-19 | R-14 | 시드 `""`와 `"가"`(U+AC00, 코드 단위 1개), 선택지 [a,b,c] | `""`: h=0x811C9DC5, 난수 정수 2625274932, 2119670693 → [c,a,b]. `"가"`: h=0x0462591F(UTF-8 바이트로 해시하면 0xCDD08B15로 달라진다), 난수 정수 2876166366, 1463596730 → [b,a,c] |
| T-20 | R-12 | 답 객체 `{kind:"quiz", answers:[{label:"B",value:"b",index:2}], dontKnow:false, correct:true, confidence:90, thinking:"x", options:[…]}` | `content[0].text`가 정확히 `{"kind":"quiz","answers":[{"index":2,"label":"B"}],"correct":true,"confidence":90,"thinking":"x"}`(공백 없음). `thinking:""`, `note:"n"`이면 `thinking` 키는 생략된다 |
| T-21 | R-13, R-15 | 요청 `confidence`가 49.5 / 50.5 / -0.4, 또 `values:["a","a"]`(a가 정답 하나) | 기록 `confidence`는 50 / 51 / 0(JS `Math.round`; 파이썬 `round`면 50 / 50 / 0이라 둘째가 다르다). 중복 value는 `answers` 2개가 되어 `correct:false` |
| T-22 | R-23 | 연습이 아닌 세션 기록이 답 결과로 끝남. `{type:"continue"}` / 같은 기록에서 턴이 실행 중일 때 | 기록에 붙는 것 없이 턴 시작(200 `{ok:true}`) / 409. 기록이 질문 호출로 끝나 있어도 `continue`는 400이 아니다 |
| T-23 | R-17, R-26 | `/api/chat`에 `{type:"dismiss",…}` / `/dismiss`에 대기 질문 해제, 턴이 실행 중일 때 | 400 `unknown input type: dismiss` / 202 `{ok:true,parked:true}`, 턴이 끝난 뒤 그 질문이 여전히 대기 호출이면 결과가 붙고 아니면 아무 일도 없음 |
| T-24 | R-18, R-20 | 턴이 실행 중일 때 ① 질문 둘 중 첫째에 `answer` ② 마지막 질문에 `answer` | ① 200 `turn-settled`, 결과 하나가 저장됨(409 아님) ② 409, 아무것도 저장 안 됨 |
| T-25 | R-16 | 선택지 없는 ask에 글 "…" / 선택지 있는 ask에서 하나 고르고 사고글 "t" / `recall`에 글 | 첫째·셋째: 답에 `text`만, `thinking` 없음. 둘째: `answers`와 `thinking:"t"` |
| T-26 | R-25, R-03 | `probe`에 선택지 value [a,b,c], `correctAnswer:"z"` | `isError:true`, `content[0].text`는 `Invalid tool input for tool "probe":\n- correctAnswer "z" does not match any option value. Valid values: "a", "b", "c". Copy the exact value (or label) of the intended option — never a paraphrase or slug.`, `details={tool:"probe", problems:[그 한 줄]}` |
| T-27 | R-01 | 설정 `{ask_user_question:false}` / `{quiz:false}` / `{explain:true}` / `{probe_done:false}` | 프로버 레지스트리: `ask_user_question` 없음 / 변화 없음 / `probe` 대신 `recall` / `probe_done` 그대로 있음. 쓰기 API는 `{probe:false}` 같은 키를 400으로 거절 |
| T-28 | R-02 | 인자 `{type:"\"predict\"", multiSelect:"true", options:"[{\"label\":\"A\"},{\"label\":\"B\"}]", correctAnswer:"[\"a\",\"b\"]"}` | 복구 후 `type:"predict"`, `multiSelect:true`, `options`는 배열, `correctAnswer`는 문자열 그대로(R-05가 배열로 해석). 고칠 게 없는 인자는 같은 객체를 돌려줌 |
| T-29 | R-07, R-27 | 턴의 새 메시지 [assistant(질문 호출 c1), toolResult(c1, `isError:false`, 자리표시)] / 같은 호출의 결과가 `isError:true` | 첫째: 저장 결과에 assistant 메시지만. 둘째: 오류 결과도 저장 |
| T-30 | R-19 | 기록: assistant 메시지가 호출 둘(질문 c1, 다른 도구 c2)을 하고 c2의 결과만 뒤에 있음 | 모델 입력에는 그 assistant 메시지 바로 뒤에 c1의 `INTERRUPTED_TEXT` 결과가 끼고(`isError:false`), 기록은 그대로 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@b277ee3) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-10, C-11, C-20 | 도구 레지스트리 소스 전문과 `pending.ts:60-106`, 쓰기 검증(`settings-body.ts:156-172`), 읽기 정리(`settings.ts:512-513`)를 읽음. 그래프 읽기 도구 게이트는 probe-measurement.md R-11. 팩토리 동작은 `tests/question-tools.test.ts:266-319`를 읽어 코드 읽기 결론과 일치함을 확인(실행 아님) |
| R-02 | C-09 | `argument-heal.ts:27-96` 본문과 `heal.ts:28-48`을 읽음. `correctAnswer`(string\|array 합집합)가 복구 대상이 아님은 합집합 스키마에 `type`이 없고 리터럴도 없기 때문(코드 읽기) |
| R-03~R-06 | C-02, C-03, C-10 | 소스 전문 읽음. 문구는 `question-core.ts:93,98,123-139,354` |
| R-07 | C-12, C-13, C-21 | 소스 전문 읽음. `teacher-agent.ts:152-168`은 같은 메시지의 질문 호출 id 중 하나라도 `isError`이면 `false`. 저장 필터는 `turn-service.ts:61-72`(질문 도구 이름 + `!isError`인 `toolResult` 건너뜀) |
| R-08~R-09 | C-10, C-14, C-15 | 소스 전문 읽음 |
| R-10 | C-16 | `input-events.ts:163-170`이 `toolCallId`(비지 않은 문자열)·`answer`(객체)만 검사, `:204-210`이 대기 호출 일치만 검사. 내용 검증 코드는 이 경로 어디에도 없다(`newAnswerResult`도 검증 없음) |
| R-11~R-12 | C-15, C-08 | 소스 전문 읽음 |
| R-13~R-15 | C-04, C-06, C-07, C-18 | 소스 전문 읽음. 슬라이더 칸을 몇 번째가 기본으로 두는지는 `question-core.ts:500-501`, 클라이언트가 항상 보냄은 `question-dock.tsx:389-391`. 시드 섞기의 시험 벡터는 `seededRandom` 코드를 읽고 옮긴 계산을 서로 다른 두 방식(마스크 정수 연산, JS 부호 있는 int32 `imul` 에뮬레이션)으로 해 일치를 확인했다. FNV-1a("a")=0xE40C292C, ("abc")=0x1A47E90B는 표준 FNV-1a 32비트 값과 같다. 원본 실행 값이 아니다 |
| R-16 | C-18, C-27 | `question-dock.tsx:388`은 `qd.mode !== "text"`일 때만 `thinking`을 담는다. 읽기 사고글 칸의 열림 조건은 `chat.tsx:508`(`questionNeedsReveal`)과 `:2279`(`pending && requiresReveal`), 초안 초기화는 `:533-538` |
| R-17~R-20 | C-15, C-16, C-17, C-22, C-24 | 소스 전문 읽음. 해제 라우트는 `app/api/chats/[id]/dismiss/route.ts`(`/api/chat`이 아님), 처리 순서는 `chat-handler.ts:175-324` |
| R-21~R-22 | C-19 | 프롬프트 텍스트 전문 읽음 |
| R-23 | C-23 | `input-events.ts:171-172`(파싱), `:211-212`(추가분: 보류된 연습 해제 쌍뿐), 클라이언트 전송은 `chat.tsx:437-439`, `:730-732` |
| R-24 | C-26 | `tool-parts.ts:37-52` 주석과 코드. pi-ai `validateToolArguments` 본문은 열지 않음(저장소 밖). `tests/tool-heal.test.ts:70-90`이 이 함수로 복구된 인자가 통과하고 원본이 던지는 것을 보인다(읽기만) |
| R-25 | C-12, C-25 | `tool-execute.ts:117-131`, `:162-212` 전문 읽음 |
| R-26 | C-22 | 라우트 전문과 `dismissal-park.ts:45-80` 전문 읽음 |
| R-27 | C-21 | `chat-handler.ts:305-324`(쓰기 선행 저장)와 `:499-502`(턴 끝 저장). 턴 중간에 턴 메시지를 쓰는 `saveMessages` 호출은 저장소 전체에서 없다(`src` 검색) |
| 문서·코드 차이 | `question-core.ts:1-18`(헤더 주석), `:411` 주석 | 헤더 주석은 "서버 execute 없음 → `input-available` 상태 → `addToolOutput`으로 되돌림"(옛 UIMessage 방식)이라 쓰고 `QuestionData`를 "`lh_question` custom 항목에 저장"이라 하지만 현재 구현은 `terminate: true` 자리표시와 입력 이벤트 `answer`다. 구현을 사실로 썼다 |
| T-01~T-16 | 구현에서 도출 | 실행·원본 테스트 사례 미반영 |
| T-17~T-30 | 구현에서 도출 | 재구현 검증(RESULT.md)의 지적을 코드로 확인해 추가. T-17~T-19는 코드를 읽고 옮긴 계산(원본 미실행) |
| 문서·코드 차이 | `pending.ts:65-78` 주석, `tools.ts:59-95`·`pending.ts:17-24` 주석 | 주석은 "`quiz`+`ask_user_question`·파일 도구·계획 도구·`probe_done`은 영원히 토글 불가"(P2 합의)이고 `pending.ts:17-24`는 "서버는 아무것도 강제하지 않는다(질문 대기는 클라이언트 파생 상태)"라고 한다. 실제로 토글 불가를 만드는 것은 쓰기 검증(`WRITABLE_TOOL_KEYS`)과 `quiz`/`explain`·`probe_done`의 예외 처리뿐이고, 팩토리의 필터는 이름 불문 `false`를 뺀다. 구현을 사실로 썼다(R-01) |
| 문서·코드 차이 | `question-core.ts:724-725` 주석 | 주석은 "기록은 임의의 정수를 받는다"지만 서버에는 `answer` 내용 검증 코드가 없어 비정수·칸 밖 값도 그대로 저장된다(R-15). 구현을 사실로 썼다 |
| 문서·코드 차이 | `input-events.ts:9-26`, `chat-handler.ts:68-69` 헤더 주석 | 헤더는 입력 이벤트 목록(`text`·`answer`·`continue`…)을 `POST /api/chat` 하나로 설명하지만 `dismiss`는 `parseChatInput`이 받지 않고 별도 라우트로만 처리된다(R-17). 구현을 사실로 썼다 |

### 2.2 코드 읽는 순서 [선택]
1. `src/agent/tools.ts` `probeQuizTool`·`teachQuizToolFor` → 2. `question-core.ts` `quizInputProblems` → 3. `tool-execute.ts` `questionResult` → 4. `teacher-agent.ts` `makeQuestionStopper` → 5. 클라이언트 `question-dock.tsx` 262~394 → 6. `input-events.ts` `inputAppends` → 7. `native-messages.ts` `newAnswerResult`, `compactAnswerForModel`.

### 2.3 비교·재사용 출처 [선택]
다른 레포에 같은 기능 스펙은 아직 없다. 코드를 복사한 범위 없음.

## 적용 메모 [선택]
Claude Code 터미널에서 쓰는 가벼운 스킬이라는 목적에서 앱 UI에 기댄 부분만 표시한다. 원본 동작을 바꾸는 결정이 아니라 걸리는 지점의 목록이다.

| 관련 R-ID | 원본과 다르게 할 점(걸리는 곳) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-13~R-15 | 채점·셔플·확신도 칸은 모두 클라이언트(질문 독) 몫이다. 터미널 대화에는 이 클라이언트가 없다 | 정오는 서버가 검증하지 않는 클라이언트 말이다(R-10) | 터미널에서는 모델이 선택지를 보여 주고 학습자 답을 글로 받아 스스로 대조하거나, 작은 스크립트가 채점해야 한다. 확신도는 칸 대신 "0~100 중 하나"를 묻는 문장이 된다(T-01, T-14가 바뀜) |
| R-07, R-09 | "턴을 끝내고 다음 입력으로 답을 받는" 구조는 질문 독 UI가 답을 보낼 때까지 기다리는 것을 전제한다 | 터미널 대화는 이미 한 턴씩 오가므로 모델이 질문을 한 뒤 응답을 기다리는 것으로 충분하다 | 도구 호출·자리표시·대기 질문 판정이 필요 없을 수 있다. 질문 호출 한 번에 하나라는 권고(R-22)만 남음 |
| R-16 | `readingThinking`은 접힌 "확인" 버튼 뒤에서 읽는 동안 쓰는 칸이 있어야 의미가 있다 | 터미널에는 접힌 버튼이 없다 | 두 채널 중 `thinking`만 남기거나, "설명을 읽고 떠오른 생각" 질문으로 대체 |
