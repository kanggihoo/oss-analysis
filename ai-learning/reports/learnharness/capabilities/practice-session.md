---
sha: "b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9"
created: 2026-10-27
updated: 2026-10-27
sources:
  - repos/learnharness/src/agent/tools/practice.ts
  - repos/learnharness/src/agent/tool-execute.ts
  - repos/learnharness/src/agent/teacher-agent.ts
  - repos/learnharness/src/agent/prompt-segments.ts
  - repos/learnharness/src/core/native-messages.ts
  - repos/learnharness/src/core/input-events.ts
  - repos/learnharness/src/core/contracts/chat.ts
  - repos/learnharness/src/core/chains.ts
  - repos/learnharness/src/core/argument-heal.ts
  - repos/learnharness/src/core/value-debris.ts
  - repos/learnharness/src/server/chat-handler.ts
  - repos/learnharness/src/store/chats.ts
  - repos/learnharness/app/api/chats/route.ts
  - repos/learnharness/src/agent/prompts/practice/00-base.md
  - repos/learnharness/src/agent/prompts/practice/10-doctrine.md
  - repos/learnharness/docs/architecture.md
  - repos/learnharness/src/agent/tools/heal.ts
  - repos/learnharness/src/agent/tools/jobs.ts
  - repos/learnharness/src/agent/tools/graph.ts
  - repos/learnharness/src/core/prompt-segments.ts
  - repos/learnharness/src/core/contracts/graph.ts
  - repos/learnharness/src/core/pending.ts
  - repos/learnharness/src/core/settings-resolution.ts
  - repos/learnharness/src/server/turn-service.ts
  - repos/learnharness/src/server/dismissal-park.ts
  - "repos/learnharness/app/api/chats/[id]/dismiss/route.ts"
  - repos/learnharness/app/api/graph/coverage/extract/route.ts
depends:
  - ./question-answer-contract.md
status: ready
reimplementation: "Python 3 표준 라이브러리, [강제] R-01~R-15(36개 테스트 통과, 원본과 출력 비교는 안 함), 결과: ../../../artifacts/learnharness/reimplementation/practice/RESULT.md"
---

# 연습 세션

> 학습자가 고른 명제(또는 자유 주제·파일)를 자료로, 연습 에이전트가 한 번에 문제 하나를 `problem`으로 내고 학습자의 "생각" 제출을 보며 힌트 사다리로 이끌고 `conclude`로 끝내는 연습 전용 세션이다. 세션 자체가 산출물이며 학습 기록이나 그래프에는 아무 것도 쓰지 않는다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]
1. 학습자가 연습 모드로 세션을 만든다(`kind:"practice"`). 지식 지도에서 고른 명제가 있으면 세션 생성 때 첫 메시지(`graph-context`)로 실리고 거기에는 고른 명제와 그 사이의 추론 연쇄가 들어 있다.
2. 첫 요청부터 연습 에이전트가 만들어진다(프로버→교사 분리도 계획도 없음). 자료가 생기는 즉시 에이전트는 첫 문제를 `problem`으로 낸다.
3. `problem` 호출은 문제 진술·모드·대상 명제·**모범 풀이(출제 시 확정, 학습자에게 숨김)**를 담고 턴을 끝낸다.
4. 학습자가 "생각" 필드로 작업 흔적이나 답 주장을 낸다(제출마다 한 턴). 에이전트는 글을 읽어 흔적(힌트 요청 포함)인지 답 주장인지 가린다. 흔적이면 힌트 사다리에서 한 단계만, 답 주장이면 판정하고 첫 깨짐을 국소화한다.
5. 에이전트가 학습자가 올바르게 풀었거나 끝내자고 할 때 `conclude`를 부른다(결과·판정·필요한 힌트 단계·실수 분류·재시험 여부). 모범 풀이가 그대로 공개되고 에이전트는 맺음말 뒤 **턴을 끝낸다**.
6. 문제 사이의 휴지에서 학습자는 방금 문제를 질문할 수 있다. 다음 문제는 학습자의 명시적 go-ahead(`next` 입력 또는 글로 요청)에서만 낸다. 학습자는 문제를 버릴 수도 있다(건너뜀).
7. 세션 끝 전에 틀리거나 힌트가 많이 필요했거나 포기한 문제를 새 표면으로 재시험한다.

### 1.2 범위·통합 지점 [필수]
- 제공: 연습 세션 생성과 시작 맥락, 연습 에이전트의 도구(`problem`, `conclude`)와 그 게이트, 연습 전용 입력(생각 제출·다음 문제·문제 버리기), 모델 입력 변환, 연습 독트린이 요구하는 출제·힌트·판정·진행·재시험 행동.
- 제외:
  - 질문·답 계약(연습은 질문 도구가 없다) → `question-answer-contract.md`는 연습이 질문 도구를 쓰지 않는다는 점만 관련.
  - 그래프 원장·명제·연쇄 저장(지도 행 15, `미작성`), 그래프 화면에서 명제를 고르는 UI(행 16, `미작성`), 그래프 추출(행 13, `미작성`). 여기서는 호출자가 명제 목록(id·이름·문장)과 연쇄를 제공한다는 경계만.
  - 연습 카드·독 UI(`components/practice-cards.tsx` 등), 마크다운 내보내기(`session-markdown.ts`). 두 곳이 `conclude` 데이터를 읽는다는 사실만 R-14에.
  - `research`·`pdf` 작업의 내부(행 10, 11, `미작성`)와 학습자 파일 도구.
  - 컴팩션(행 9), 프롬프트 사용자 오버라이드(행 7, `미작성`).
- 외부 의존:
  - 저장소: 세션 저장소(`getChat`·`saveMessages`·`saveSettings`), 그래프 저장소 읽기(명제 목록 `readNodes`, 연쇄 `readChains`), 설정의 strong 슬롯 모델.
  - 에이전트 루프(pi): 도구의 `prepareArguments`를 스키마 검증 **앞에서** 부르고, 검증(주석 기준 pi-ai `validateToolArguments` = TypeBox `Value.Convert` 후 `Value.Check`)이 입력을 거절하면 거절 결과를 만들고, `terminate:true` 결과에서 턴을 끝내고, `executionMode:"sequential"` 호출을 순서대로 실행한다. 거절 결과의 문구와 스키마에 없는 추가 필드의 처리는 이 스펙 밖이다.
  - 클라이언트: `thinking`·`next`·`text` 입력은 `POST /api/chat`으로, `dismiss-problem`은 `POST /api/chats/<id>/dismiss`로 보낸다.
  - 선행 계약 `question-answer-contract.md`에서 연습이 실제로 쓰는 것(질문 도구·`answer`/`dismiss` 입력·대기 질문 판정은 쓰지 않는다): ① 오류 결과 모양 `invalidInputResult`(QA C-12, 이 스펙 C-13) ② `INTERRUPTED_TEXT`와 끊긴 호출 합성(QA R-19·C-15, 이 스펙 R-13·C-14) ③ 값 찌꺼기 벗기기 `stripModelValueDebris`(QA C-03, 이 스펙 C-07, `target` 정규화에 쓴다) ④ 한 채팅 한 턴 409(QA R-20).
- 소유 상태·부작용: 세션 기록의 `kind:"practice"`, `graph-context`·`practice-thinking`·`practice-next`·`problem-dismissed` 마커, `problem`·`conclude` 호출과 결과. **다른 영속 상태는 없다**: 자동 추출, 그래프 쓰기, 커버리지 기록이 모두 꺼진다(수동 추출 경로는 R-03). `conclude`가 담는 결과·단계·실수 분류는 기록에만 남고 어떤 저장소·스케줄러도 읽지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

**세션 생성** (`POST /api/chats`): body `{title?, kind?:"practice", graphContext?:{propositions:[{id,name,statement}…]}}`(JSON이 아니면 빈 객체로 본다). 응답 `{id, title}`. `title`은 문자열이 아니거나 비면 "Untitled session"이고, 아니면 공백을 한 칸으로 접고 72자 안에서 단어 경계로 잘라(넘으면 `…`) 쓰며 결과가 비면 "Untitled session"이다(C-06). `kind`가 정확히 `"practice"`일 때만 기록에 `kind:"practice"`가 붙고 teach 세션에는 `kind` 필드가 아예 없다(없음 = teach). 세션 `id`는 불투명한 문자열이다.

**`graph-context` 마커**(기록의 첫 메시지, 모델에게는 사용자 역할 텍스트로 보임): `role:"custom"`, `customType:"graph-context"`, `display:true`, `details:{propositions, chains}`, 모델이 읽는 `content`는 다음 모양이다.
- 첫 줄 `[Session context] — picked from the learner's knowledge map when starting this session:`, 빈 줄, `Propositions (id — name: statement; the problem tool's target field uses these ids):`, 이어서 고른 명제마다 `- [<id>] <이름>: <문장>`.
- 연쇄가 하나라도 있으면 빈 줄과 `Reasoning chains among them (premises → conclusion):` 뒤에 `- <전제 이름들(정렬, 쉼표 구분)> → <결론 이름>`(전제가 없으면 `<이름> (no premises)`).
- 명제 이름·문장은 학습자가 고른 시점에 본 스냅샷이고, 연쇄는 세션 생성 시 **현재 그래프**에서 계산한다.

**`problem` 입력**

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `statement` | string(필수) | 학습자가 보는 문제(마크다운·LaTeX). 자급자족해야 하고 대상 명제를 밝히지 않는다. 빈 문자열도 스키마가 막지 않는다(R-05) |
| `mode` | "recall" \| "discrimination" \| "composition"(필수, 맨 단어) | 요구의 모드 |
| `target` | list of string(1개 이상)? | 이 문제가 다루는 명제 id(세션 맥락의 `[id]` 목록에서). 자료가 지도에 없으면 **통째로 생략**(자유 주제 세션은 태그 없는 문제) |
| `modelSolution` | string(필수) | 학습자가 보기 전에 확정한 전체 풀이(수 순서대로). `conclude`가 이것을 그대로 공개한다. 빈 문자열도 스키마가 막지 않는다(R-05) |

**`conclude` 입력**: 모두 필수.

| 필드 | 값 | 의미 |
|---|---|---|
| `outcome` | `solved` \| `solvedWithHints` \| `movedOn` \| `surrendered` \| `dismissed` | `dismissed`는 건너뜀에서 합성되는 값이고 모델이 쓰는 것이 아니라고 도구 설명이 말한다 |
| `verdict` | string | 무엇을 인정했고 어디서 깨졌는지. 오답이면 깨진 곳을 짚고 교정은 주지 않는다 |
| `rung` | `R0`~`R5` 또는 null | 그 문제에 필요했던 힌트 사다리 단계. null = 힌트 없음 |
| `missClass` | `cue` \| `discrimination` \| `execution` \| `careless` \| `structural` 또는 null | 실수 분류. null = 실수 없음 |
| `retest` | boolean | true면 세션 끝 전에 새 표면으로 재시험할 문제 |

**연습 전용 입력**

| 입력 | 보내는 곳 | 형태 | 의미 |
|---|---|---|---|
| 생각 제출 | `POST /api/chat` body `{chatId, input}` | `{type:"thinking", problemCallId, text}` | 활성 문제에 대한 학습자 글. 작업 흔적과 답 주장이 같은 통로이며 어느 쪽인지는 글에서 읽는다 |
| 다음 문제 | 같음 | `{type:"next"}` | 문제 사이 휴지에서 학습자의 명시적 go-ahead |
| 문제 버리기 | `POST /api/chats/<id>/dismiss` body `{input}`(`/api/chat`이 아니다) | `{type:"dismiss-problem", problemCallId}` | 턴을 만들지 않는 조용한 경로. 아래 R-12 |
| 글 | `POST /api/chat` | `{type:"text", text}` | 일반 메시지(문제 사이 질문 등) |

**마커 메시지**(모두 `role:"custom"`, `display:true`, 새 `id`, `timestamp`=밀리초): `practice-thinking`(`content = "Your thinking:\n<text>"`, `details:{problemCallId,text}`), `practice-next`(`content = NEXT_PROBLEM_TEXT`: "[NEXT PROBLEM] — the learner's explicit go-ahead: pose the next problem now per the selection rules, or wrap the session in text if the arc is complete.", `details:{}`), `problem-dismissed`(`content:""`, `details:{problemCallId}`, 화면용이고 모델 입력에서 빠진다). 일반 `text` 입력이 만드는 사용자 메시지는 `{role:"user", content:<입력 text 원문 문자열>, id, timestamp}`이다(블록 배열이 아니고 글을 자르지 않는다). `id`는 `msg_<시각 36진수>_<UUID 앞 8자>`이고(C-14) 모델 입력에서는 떼어진다(R-13).

**`problem` 결과**: 텍스트 "Problem posed — the turn ends here; the learner's thinking traces and answer commits arrive as labeled messages.", `details:null`, `terminate:true`, **영속**(질문의 자리표시와 달리 최종 결과). **`conclude` 결과**: 텍스트 `CONCLUDE_ACK_TEXT`("Problem concluded. Say your closing words about the learner's work if useful, then END YOUR TURN — no further tool calls. The next problem is NEVER posed here: it waits for the learner's explicit go-ahead (a *Next problem* message, or their own words asking for the next one). Between problems, answer their questions about the concluded one."), 종료 신호 없음.

**오류 결과**(`problem`·`conclude` 공통, `invalidInputResult`, C-13): `isError:true`, 텍스트는 `Invalid tool input for tool "<도구 이름>":` 한 줄 뒤에 줄바꿈하고 문제마다 `- <문제>` 줄(여러 개면 줄바꿈으로 이음), `details:{tool:<도구 이름>, problems:[문제들]}`, 종료 신호 없음. 스키마가 거절하는 입력의 결과는 이것이 아니라 에이전트 루프가 만든다(1.2).

### 1.4 행동 규칙과 남은 질문 [필수]
범례: **[강제]** 코드가 지킴, **[권고]** 프롬프트가 모델에게 요청할 뿐 코드는 막지 않음.

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [강제] 세션 생성 | 요청 `kind === "practice"`(엄격 일치, 다른 값·누락은 teach)일 때만 기록에 표시. 설정의 strong 슬롯에 `model`이 있으면 `{model:{provider,id}, thinkingLevel}`(`thinkingLevel`은 슬롯 값 그대로, 없을 수 있음)을 세션 설정으로 저장하고(`kind`와 무관, teach도 같다) 없으면 저장하지 않는다. `graphContext.propositions`가 배열이면 그중 객체이고 `id`·`name`·`statement`가 모두 문자열(빈 문자열·중복 허용)인 항목만 쓰고 **걸러낸 뒤** 앞 64개만 남긴다(`details.propositions`에는 걸러진 원본 객체가 그대로 들어간다). 하나라도 있으면 기록의 첫 메시지로 `graph-context` 마커를 저장한다 | 코드 확인 |
| R-02 | [강제] 맥락의 연쇄 | 고른 명제 중 **현재 그래프에 실제로 있는 것**만 연쇄 계산에 쓴다(같은 id를 두 번 고르면 노드가 두 번 들어가 단독 항목도 두 번 생긴다). 저장된 연쇄 중 결론과 전제가 **모두** 선택되어 있는 것만 포함(전제는 id로 정렬). 선택됐지만 어떤 연쇄에도 안 들어간 명제는 **노드 id를 연쇄 id로 쓰는** 전제 없는 단독 항목. 결과는 저장된 연쇄 id와 단독 항목의 노드 id를 한 목록으로 문자열 비교(JavaScript `<`, UTF-16 코드 단위 순서)로 정렬. 줄의 이름은 고른 시점 스냅샷이 아니라 **현재 그래프의 이름**이고 전제는 이름이 아니라 id 순으로 늘어놓는다(선택된 노드는 모두 그래프에 있어 id로 대체되는 경우는 이 경로에서 없다). 줄 모양은 C-07 | 코드 확인 |
| R-03 | [강제] 에이전트 선택 | `kind:"practice"`이면 모든 요청에서 연습 에이전트(프로버·교사 단계 없음, 계획·질문 도구 없음)를 만든다. 연습 에이전트는 그래프를 쓰는 도구가 없다(R-04의 그래프 도구는 읽기 전용). 턴 종료 후의 **자동** 추출 트리거는 `kind !== "practice"`일 때만 켜지고(조건: 요청 사이클 조건 && `kind !== "practice"` && 설정의 추출 활성) 그 밖의 추출·그래프 쓰기·커버리지 기록 경로는 연습 에이전트가 열지 않는다. 수동 추출 경로 `POST /api/graph/coverage/extract`는 채팅의 `kind`를 검사하지 않는다(그 경로가 연습 세션 기록을 실제로 처리하는지는 미확인, 확인 한계) | 코드 확인 |
| R-04 | [강제] 연습 에이전트 구성 | 도구(레지스트리 키 순서): `problem`, `conclude`, `read`, `ls`, `find`, `grep`, 작업 맥락(`jobs`)이 주어지면 `research`와 `pdf` **둘 다**(검색 엔진 유무와 무관하고 둘이 따로 빠지지 않는다, 서버 배선은 연습에도 항상 `jobs`를 준다), 그래프 맥락이 주어지면 `list_sessions`·`list_propositions`(서버는 그래프 마스터 스위치 AND `agent.graphTools.enabled ?? true`일 때만 준다). 설정 토글(`toolToggles`)로 거르지 않는다. 모든 도구는 레지스트리 공통 인자 복구로 한 번 더 감싼다(R-05). 시스템 프롬프트는 공통 기반 `system-prompt.md` **없이** ① 연습 디렉터리 조각(파일명이 `FRAGMENT_RE` = `^\d+-[\w.-]+\.md$`인 것, 파일명 정렬: `00-base`, `10-doctrine`) 뒤에 ② 공유 디렉터리 조각 중 허용 목록 `10-voice`, `15-accuracy`, `16-mental-model`, `40-formatting`만(파일명 정렬). 조각 텍스트는 각각 앞뒤 공백을 자르고 빈 것은 버린 뒤 `\n\n---\n\n`로 잇는다(C-09). 사용자 오버라이드는 행 7 범위 밖 | 코드 확인 |
| R-05 | [강제] `problem` 호출 직전(`prepareArguments`, 스키마 검증 앞) | 순서: ① 인자 복구(C-12: 스키마가 기대하는 enum·불리언·null·숫자·배열을 JSON 문자열로 감싼 값을 풂, 예 `"mode":"\"recall\""`) → ② `target` 정규화 → ③ 레지스트리 공통 복구(①을 한 번 더, 멱등). `conclude`는 ①과 ③만 거친다(R-07). 정규화(그래프 노드 목록이 주어졌을 때): `target`이 배열이 아니거나(풀리지 않는 문자열 `"zzz"`·숫자 등) 비어 있으면 **`target`을 아예 제거**한다(기록은 태그 있음 또는 없음뿐). 배열이면 문자열 원소마다 `resolveTargetId`(C-07)로 id를 찾는다: 앞뒤의 공백·`:`·`.`·따옴표·백틱을 벗긴 값이 ⓐ 어떤 노드 id와 정확히 같으면 그 id(id가 이름보다 먼저), 아니면 ⓑ 노드 이름(이름도 같은 식으로 벗기고 안쪽 공백은 그대로)과 대소문자 무시로 같은 **저장 순서상 첫** 노드의 id. 못 찾은 원소(벗기면 빈 문자열이 되는 것 포함)와 문자열이 아닌 원소는 원래 값 그대로 두어 execute가 거절한다(R-06). 노드 목록이 주어지지 않으면 정규화·검증은 건너뛰고 빈 배열 제거만 한다(비배열 `target`은 그대로 두어 스키마가 거절). 스키마는 `statement`·`modelSolution`에 최소 길이를 두지 않아 **빈 문자열도 막지 않는다**. 스키마 검증과 그 거절 결과는 에이전트 루프 몫(1.2) | 코드 확인 |
| R-06 | [강제] `problem` 실행 | ① 이 턴의 게이트가 "활성"이면 오류 결과(모양은 1.3) "a problem is already active — call conclude on it before posing the next one"(②보다 먼저 검사). ② 그래프 노드 목록이 주어지고 `target`이 비어 있지 않을 때 `resolveTargetId`가 못 찾는 원소가 있으면 오류 `target <못 찾은 원소 목록> is not a known proposition — targets must be proposition ids from the session context; if the material is not in the map, omit target entirely`(목록은 JavaScript `JSON.stringify` 모양: 공백 없이 `["a","b"]`, 비ASCII 이스케이프 없음, 원소는 정규화 뒤에도 못 푼 원래 문자열이라 푼 원소는 빠진다. 검증은 세션 선택이 아니라 **그래프 전체** 기준). ③ 통과하면 게이트를 활성으로 바꾸고 `terminate:true` 결과. ①②의 오류는 게이트를 바꾸지 않는다 | 코드 확인 |
| R-07 | [강제] `conclude` 실행 | 게이트가 "활성"이 아니면 오류 "no active problem to conclude — pose one first". 통과하면 게이트를 비활성으로 바꾸고 종료 신호 없는 `CONCLUDE_ACK_TEXT` 결과. execute는 입력 내용(`verdict` 등)을 읽지 않고 게이트만 본다. `prepareArguments`는 R-05 ①(복구)뿐이다(`target` 정규화 없음): `rung:"null"`→`null`, `missClass:"null"`→`null`, `retest:"true"`→`true`, `outcome:"\"solved\""`→`solved`처럼 풀리는 값만 풀고 나머지(`outcome:"null"`, `rung:"R6"`, 필수 필드 누락 등)는 그대로 스키마 검증이 거절한다. `outcome:"dismissed"`는 스키마가 받아들이며 막는 코드는 없다 | 코드 확인 |
| R-08 | [강제] 게이트 상태 | 요청마다 새로 만든다. 시작값은 기록에서 계산한 활성 여부이고, 턴 안에서는 **클로저의 값이 진실**이다(기록은 턴 끝에서야 저장되므로 같은 턴의 `conclude` → 새 `problem`이 서로를 볼 수 있어야 하기 때문). 같은 턴 안에서 `conclude` 뒤에 새 `problem`을 내는 것은 도구가 막지 않는다(막는 것은 R-21 프롬프트 규칙). 두 도구는 `executionMode:"sequential"`로 선언돼 한 메시지의 호출이 순서대로 실행된다(선언만 확인, 실행은 루프 몫) | 코드 확인 |
| R-09 | [강제] 활성 문제 판정(`activeProblemOf`) | "깨끗한 호출" = 그 호출 id의 `toolResult` 중 `isError`가 거짓(또는 없음)인 것이 기록 어딘가에 있는 호출(결과의 위치는 상관없음). 호출은 깨끗할 때만 센다. 최신 메시지부터 거슬러 올라가며: `problem-dismissed` 마커를 만나면(마커의 `problemCallId`는 비교하지 않음) 비활성; assistant 메시지 안에서는 **마지막 블록부터 첫 블록 순으로** 훑어 깨끗한 `conclude` 호출이면 비활성, 깨끗한 `problem` 호출이면 그 호출이 활성(`{toolCallId, input:arguments}`); 오류이거나 결과 없는 호출, 다른 도구, 다른 역할의 메시지, 다른 마커는 건너뜀. 따라서 풀기 중 `conclude`가 오류였으면 문제는 여전히 활성이고, `problem`이 오류였으면 안 일어난 일이다. 한 메시지에 `[conclude, problem]`(둘 다 깨끗)이면 뒤 블록인 `problem`이 먼저 만나져 활성, `[problem, conclude]`이면 비활성 | 코드 확인 |
| R-10 | [강제] 생각 제출 | 검증 순서는 **파싱 → 활성 확인**이다. 파싱: `problemCallId`가 비어 있지 않은 문자열이 아니면 400 "thinking input requires problemCallId"(글이 비어도 이 오류가 먼저), `text`가 문자열이 아니거나 `trim()`하면 비면(공백뿐인 글) 400 "thinking input requires non-empty text"(활성 문제가 없어도 이 오류). 활성 확인: `problemCallId`가 활성 문제의 호출 id와 다르거나 활성 문제가 없으면 400 "thinking input targets no active problem"(건너뛴 문제는 활성이 아니므로 그 문제에 대한 제출도 400이고, 그래서 건너뜀의 합성 쌍이 `thinking`에 붙는 일은 사실상 없다). 통과하면 `practice-thinking` 마커를 붙이고(글은 자르지 않고 원문 그대로 `content`·`details.text`에 넣는다) 턴을 시작한다. 한 문제가 여러 제출을 가질 수 있고 각각이 한 턴이다. 일반 `text` 입력도 같은 파서를 거쳐 `trim()`이 비면 400 "text input requires non-empty text"이고 통과하면 사용자 메시지에 원문이 실린다. 모든 400은 입력의 추가분을 저장하기 전, 실행 중 턴 409보다 앞에서 나간다 | 코드 확인 |
| R-11 | [강제] 다음 문제 | 연습 세션이 아니면(`kind !== "practice"`) 400 "next input is a practice-session affordance", 활성 문제가 있으면 400 "next input requires no active problem"(`kind` 검사가 먼저). `{type:"next"}` 외의 필드는 무시한다. 통과하면 (대기 중인 건너뜀의 합성 쌍 먼저) `practice-next` 마커를 붙이고 턴을 시작한다 | 코드 확인 |
| R-12 | [강제] 문제 버리기 | **경로·파싱**: `POST /api/chats/<id>/dismiss` body `{input}`(`POST /api/chat`에서는 "unknown input type: dismiss-problem" 400). 모르는 채팅 404; `input`이 객체가 아니면 400 "input must be an object", `problemCallId`가 비어 있지 않은 문자열이 아니면 400 "dismiss-problem input requires problemCallId". 턴이 실행 중이면 입력을 서버에 보관(채팅당 하나, 마지막 것만)하고 202 `{ok:true,parked:true}`를 돌려주며, 턴이 저장을 마친 뒤 같은 검사로 적용한다(그때 활성 문제가 아니면 오류 없이 버림). 실행 중이 아니면 `problemCallId`가 활성 문제의 호출 id와 같아야 하고(아니면 400 "dismiss-problem input targets no active problem") 모델 입력에서 빠지는 `problem-dismissed` 마커 하나만 붙이고 `{ok:true}`, **턴을 시작하지 않는다**. **합성 쌍**: 대기 판정은 최신 메시지부터 거슬러 올라가 `problem-dismissed` 마커를 먼저 만나면 그 `problemCallId`(검증 없이), 깨끗한 `conclude`나 깨끗한 `problem` 호출을 먼저 만나면 대기 없음이다. 대기가 있으면 다음 `text`·`continue`·`next` 입력 **앞에** 쌍이 붙는다(`answer`와 서버가 깨우는 `steers`에는 붙지 않고, `thinking`은 R-10대로 400이다). 쌍은 assistant 메시지의 `conclude{outcome:"dismissed"}` 호출(인자는 `outcome` 하나뿐, 호출 id `call_conc_<problemCallId>`) + `CONCLUDE_ACK_TEXT` 결과(`isError:false`, `details:{outcome:"dismissed", problemCallId}`)이고 나머지 필드는 C-03이다. 쌍이 붙으면 문제 슬롯이 비고 모델에게는 자기 어휘로 읽힌다. 마커 하나당 쌍은 한 번만 붙는다(쌍의 깨끗한 `conclude`가 대기를 끝낸다). 쌍 assistant 메시지의 `api`·`provider`·`model`·사용량·`stopReason`은 의미 없는 자리표시다(주석 근거) | 코드 확인 |
| R-13 | [강제] 모델 입력 변환(`toLlmMessages`) | `plan-block`·`problem-dismissed`(와 활성 컴팩션 마커)만 빠지고 나머지 마커는 `{role:"user", content:[{type:"text", text:<마커 content>}], timestamp:<마커 timestamp>}`로 평탄화되어 모델에게 간다(`graph-context`·`practice-thinking`·`practice-next` 포함). 마커가 아닌 메시지는 기록용 `id`만 떼고 그대로 간다. **끊긴 호출 합성**(QA R-19): assistant 메시지의 `toolCall`마다 그 메시지 **뒤의 모든 메시지** 중에 같은 `toolCallId`의 `toolResult`가 하나도 없으면(바로 다음 메시지일 필요 없음) 그 assistant 메시지 바로 뒤에 `{role:"toolResult", toolCallId, toolName:<그 호출의 이름>, content:[{type:"text", text:INTERRUPTED_TEXT}], isError:false, timestamp:<assistant 메시지의 timestamp>}`를 끼운다. 대상은 `problem`·`conclude`를 포함한 모든 도구 호출이고 문구는 "질문"을 말하지만 그대로 쓴다. 이 합성은 모델 입력에만 있고 기록은 바뀌지 않으며 활성 문제 판정(R-09)은 합성을 보지 않는다(결과 없는 호출은 안 일어난 일). 컴팩션 절단은 행 9 | 코드 확인 |
| R-14 | [강제] 공개와 결과 사용처 | 공개 대상은 `conclude` 호출 id가 든 assistant 메시지에서 시작해 **뒤로** 거슬러 올라가며, 각 assistant 메시지 안에서는 **마지막 블록부터 첫 블록 순으로** 훑어 처음 만나는 **깨끗한 결과가 있는 `problem` 호출**의 `arguments`다. 공개 값은 그 `arguments.modelSolution`이 문자열이면 그 값이고 아니면 없음이다(더 앞의 `problem`으로 넘어가지 않는다). 다시 쓰지 않는다. 따라서 ⓐ 오류로 거절됐거나 결과 없는 출제는 건너뛰고(공개할 것이 없다) ⓑ **`conclude`와 같은 메시지에 있는 `problem`도 대상**이다: `[conclude, problem]`이면 뒤 블록인 새 `problem`이 먼저 만나져 conclude에 **새 문제의 풀이**가 공개되고(R-08이 이 조합을 막지 않는다), `[problem, conclude]`이면 그 앞 `problem`의 풀이가 공개된다 ⓒ 대상 `conclude` 호출 자체가 깨끗한지는 보지 않는다. 호출 id가 든 메시지가 없으면 공개 없음. `conclude`의 `outcome`·`rung`·`missClass`·`retest`를 읽는 코드는 연습 카드 렌더와 마크다운 내보내기뿐이고 그것을 집계·저장·일정화하는 저장소는 없다 | 코드 확인(`outcome`/`missClass`/`solvedWithHints`를 쓰는 파일을 검색해 3곳 확인, 두 UI 파일 본문은 미열람) |
| R-15 | [강제] 컴팩션 종류 | 연습 세션(`kind:"practice"`)의 컴팩션 종류는 `"practice"`(프로브/교사 아님)이다. 요청 시작의 컴팩션 게이트와 턴 종료 뒤의 컴팩션 킥 두 곳 모두 같고, 프롬프트 크기 추정도 연습 프롬프트로 한다. 연습이 아니면 프로브 완료 여부로 `teach`/`probe`(이 스펙 밖) | 코드 확인(상세 동작은 행 9 `미작성`) |
| R-16 | [권고] 열기 | 자료가 생기면 곧바로 출제한다: 첫 답이 `problem`이고 앞에 한 줄 이하의 안내. 워밍업 대화나 이미 자료가 한정하는 질문은 하지 않는다. 자료는 고른 명제와 자유 입력(학습자의 말로 된 주제, 교재, 파일, 외부 문제) 모두 1급 시작이고 거절하거나 형식을 바꾸게 하지 않는다. 자유 주제는 `target` 생략. 보정은 시작 요구 자체가 한다(워밍업 면담이 아니라) | 코드 확인(프롬프트 텍스트) |
| R-17 | [권고] 연습의 정의 | 연습은 대상 명제가 학습자 마음에서 **비활성**일 때 상황의 특징만으로 떠오르게 하는 것이다(가르친 직후의 확인은 활성 상태의 이해를 잰다). 시험이 아니다(가장 값싼 채점 가능 요구가 아니라 가장 많이 강화하는 요구를 만든다). 가르치기가 아니다(오개념은 최소한의 외과적 넛지로 다루고 재교육으로 흐르지 않는다). 탐색 훈련이 아니다(분당 의사결정 지점을 극대화). 산출물은 한 번의 "클릭"이 아니라 상태(도움 없이 새 상황에 배치됨)이고, 아하의 순간을 기획하지 않고 배치를 누적한다 | 코드 확인(프롬프트 텍스트) |
| R-18 | [권고] 이론 | 연산 3개: 회수·실행·확인. 같은 활성 사슬 안의 이동은 유지일 뿐이다. 피드백 직후 같은 것을 다시 묻는 것은 약하다(재시도는 새 표면). 대상 교차가 기본(같은 대상 연속 블록은 반복이지 회수가 아님). 문제 시간 = 파싱 + 탐색 + 실행 + 회복이므로 분당 의사결정 지점을 극대화(긴 문제도 어려운 탐색도 아님). 난이도는 노력으로 성공하는 회수가 강화하고 **회수 한 번당 성공률 약 85%** 대(여덟 수짜리 문제는 85%여도 전체 성공이 약 1/4). 부산물(스키마 귀납, 보정)을 해치는 정책은 쓰지 않는다 | 코드 확인(프롬프트 텍스트) |
| R-19 | [권고] 모드 | 요구는 세 모드 중 하나: **회수**(약하거나 다양한 단서에서 명제가 배치됨, 의사결정 지점 1~2, 새 상황 부류, 짧게), **변별**(살아 있는 혼동 후보에 맞서 옳은 명제가 이김, 쌍둥이 상황이고 가르는 특징이 신호), **조합**(사슬이 부하 아래 하나로 실행됨, 길이는 사슬을 따름, 접합부에 의사결정 지점, 방해 요소 허용). 선행 순서 회수 → 변별 → 조합: 뒤층이 실패하면 앞층이 약하다는 뜻이니 되돌아가 시험. 난이도 손잡이는 모드 안(회수는 단서 거리, 변별은 표면 유사도, 조합은 길이와 간섭). 수식 변형 3개: 역방향(결론을 주고 근거를 요구), 변별, 전제 점검(전제 하나를 약화시켜 무엇이 깨지는지) | 코드 확인(프롬프트 텍스트) |
| R-20 | [권고] 선택 | 매 요구 앞의 표준 질문: "아직 증명되지 않은 가장 약한 능력을 가장 싸게 최대로 강화하거나 불확실성을 가장 많이 푸는 요구는?" 모드는 그 대상이 아직 보이지 않은 **가장 싼 모드**. 대상은 **가장 약한 것 먼저, 가장 많이 쓰이는 것(전제가 여러 사슬에 먹이는 것), 가장 오래 활성이 아니었던 것** 순으로 자료 구조와 세션의 증거에 근거해 고른다. 세션이 보이지 않은 것은 없다고 가정한다 | 코드 확인(프롬프트 텍스트) |
| R-21 | [권고] 출제 절차 | ① 대상 ② 모드 ③ 난이도: 최근 결과에서 — 깨끗한 성공은 한 칸 위, 힌트가 필요했으면 유지, 오답이면 한 칸 아래(모드를 내릴지 고려), 한 대상에서 종결한 문제를 연속 둘 틀리면 다음 요구는 대상 전환(활성 문제는 시도 횟수 때문에 버리지 않음) ④ 상황: 이 세션에서 그 대상에 쓰지 않은 단서 부류(이론적/응용적 표면은 학습자 선호이고 구조를 안 바꿈) ⑤ 확정: 학습자가 보기 전에 모범 풀이를 수 순서대로 확정 ⑥ 점검: 직접 풀어 보고 깨 본다 — 대상을 건너뛰는 경로로 풀리면 부당한 문제이니 고치거나 버린다, 자료 밖의 것을 요구하지 않는다. 풀고 지름길을 찾아 보지 않은 문제는 내지 않는다. 진술은 대상을 밝히지 않는다(상황상 명백하면 의도한 낮은 단계 회수) | 코드 확인(프롬프트 텍스트) |
| R-22 | [권고] 힌트 | 흔적이 답을 주장하지 않는 모든 제출(빈 흔적의 "막혔다" 포함)에 적용. 계량 원칙: 공개한 정보는 되돌릴 수 없고 학습자는 언제나 더 생각하고 다시 물을 수 있으니 도움은 최소로. 규칙: **흔적에서 루프(인지·종류 선택·명제 변별·실행·점검)의 첫 번째 못 답하거나 틀린 질문을 진단하고, 그것에만 가장 굵은 단위로 응답, 한 요청에 한 단계.** 사다리: R0 주의 돌리기 / R1 패턴 재서술 / R2 후보 부류 / R3 명제를 이름으로 / R4 수를 개요로 / R5 풀이 한 단계. 막힌 곳이 주의가 간 곳이 아닐 수 있다 — 엉뚱한 명제로 실행에 낑낑대면 "어느 명제인가"가 이미 틀린 것이니 최소 응답은 검증 넛지("움직이는 수의 전제를 확인해 보라")이고 학습자가 아직 만들 수 있는 교정은 말하지 않는다. 진술 수리("무엇을 묻는지 모르겠다")는 파싱 실패이므로 즉시 완전히 고친다(문장은 물류), 풀이 정보는 계량. 넛지가 안 닿으면 새 정보 한 조각만. 그 문제가 필요로 한 단계는 난이도 판독(R0~R1만이면 적당, R3 이상이면 경계 밖)이고 다음 요구의 난이도에 반영 | 코드 확인(프롬프트 텍스트) |
| R-23 | [권고] 답 주장과 실수 분류 | 흔적은 일부러 군더더기를 담는다. 점수가 아니라 **수**(어떤 명제를 어떤 순서로 썼고 어디서 깨졌나)를 뽑는다. 오답: 판정을 평이하게 말하고 첫 깨짐을 국소화하되 교정은 주지 않는다. 학습자가 다음 수를 낼 수 있는 가장 작은 넛지를 주고 기다린다. 안 닿으면 새 사고에 맞춰 또 최소 넛지. 실패한 시도는 교정 공개나 종결의 이유가 아니다. 정답: 확인하고 하중을 진 수를 짚어 한 줄. 모든 실수를 분류: cue(아무 것도 안 떠오름) / discrimination(엉뚱한 후보가 이김) / execution(맞는 명제를 잘못 실행) / careless / structural(회수한 명제 자체가 틀림=오개념). 앞의 넷은 연습 정보, 구조적 실수는 즉시 교정이나 재교육이 아니라 최소 넛지로 오개념을 고치게 한다 | 코드 확인(프롬프트 텍스트) |
| R-24 | [권고] 진행과 휴지 | 답 주장은 진행 신호가 아니다. 한 문제가 여러 주장을 가질 수 있고 머무름이 기본이다. `conclude`는 학습자가 바르게 풀었거나 명시적으로 끝내자고 할 때만 부른다(실수·시간·시도 횟수·좌절·막힘에서 허락을 추론하지 않음). `conclude` 뒤 에이전트는 맺음말 후 **턴을 끝내고** 같은 턴에서 다음 문제를 내지 않는다. 다음 문제는 `next` 메시지나 글로 요청할 때만. 휴지에서는 방금 끝난 문제에 관한 질문(무엇이 틀렸나, 왜 그 수가 맞았나, 힌트의 뜻)에 충분하되 외과적으로 답한다(수리·명료화·후속, 재교육 아님). 각 답이 턴을 끝내며 답의 끝에서 문제를 내지 않는다. 명료화 질문은 go-ahead가 아니다. 학습자가 문제를 건너뛰면(합성된 `dismissed`) 문제 전체를 포기한 것으로 보고 중요했다면 새 표면 재시험 표시를 한다. 건너뜀에 대해 스트림이 필요한 것 이상으로 말하지 않는다 | 코드 확인(프롬프트 텍스트, `CONCLUDE_ACK_TEXT`, 도구 설명). 도구가 강제하지 않음(R-08) |
| R-25 | [권고] 아크와 재시험 | ① **워밍업 열기**: 가장 약한 인접 대상의 저(低)단서거리 회수 1~3개로 묶음을 다시 깨우고 난이도를 보정 ② **본문**: 교차(대상 전환, 모드는 R-20, 난이도는 R-21, 성공하면 단서 부류 확장) ③ **마무리 재시험**: 세션이 끝나기 전 틀린 것, 힌트가 무거웠던 것, 포기한 것을 모두 **새 표면**으로 재시험한다(원 문제의 표면은 안 씀). 세션에서 실패한 것은 재시험 없이 세션을 끝내지 않는다. 학습자가 외부 문제를 가져오면 풀어 보고 필요한 명제·연쇄를 지도화한 뒤 같은 기계(힌트·판정·재시험)에 태운다 | 코드 확인(프롬프트 텍스트) |
| R-26 | [권고] 금지 목록과 사실 확인 | 풀고 지름길을 찾아 보지 않은 문제를 내지 않음 / 자료 밖의 것을 요구하지 않음 / 대상을 밝히지 않음 / 학습자가 아직 만들 수 있는 것을 알려 주지 않음(한 요청 한 단계, 교정 전 검증) / 같은 표면으로 재질문하지 않음 / 외과적 한 줄 넘게 가르치지 않음 / 답 주장을 진행 신호로 착각하지 않음 / 판정을 누그러뜨리거나 부풀리지 않음. 문제·모범 풀이·판정·힌트에 넣을 사실이 조금이라도 불확실하면 출제 전에 `research`로 확인한다(백그라운드, 메시지로 결과가 오고 그 뒤 출제) — 틀린 모범 풀이는 거짓에 대해 채점하는 것이다. 어조는 교사와 같다(칭찬·열광 없음) | 코드 확인(프롬프트 텍스트) |

- 불변식: 한 세션에 활성 문제는 최대 하나다(R-06, R-09). 연습 세션은 학습 기록·그래프·커버리지를 바꾸지 않는다(R-03). 전제: 한 채팅에서 동시에 한 턴만 돈다(`question-answer-contract.md` R-20).
- 미결정: 없음
- 확인 한계: 코드를 실행하지 않았고 테스트를 열지 않았다. 독트린(R-16~R-26)을 모델이 따르는 정도는 미확인이다. 두 UI 파일(`practice-cards.tsx`, `session-markdown.ts`)의 본문은 열지 않았다. 에이전트 루프(pi)와 검증기(pi-ai)는 repo 밖이라 열지 않았고, 스키마 검증이 `Value.Convert` 후 `Value.Check`라는 것(코드 주석)과 스키마에 없는 추가 필드를 거절하지 않는다는 것(TypeBox 일반 동작)은 추론이다. `research`·`pdf`·그래프 읽기 도구의 본문과 추출 파이프라인은 범위 밖이라 열지 않았다(수동 추출 경로가 연습 세션을 처리하는지는 미확인, R-03). 입력 `continue`와 일반 `text`의 다른 처리 경로(턴 시작 전 모든 입력에 대한 게이트: 모델 설정·키·컴팩션)는 이 스펙이 아니라 세션 턴 파이프라인(행 1, `미작성`) 몫이다.

### 1.5 필수 코드 참조 [필수]
라이선스는 AGPL-3.0(overview 1절)이다. 프롬프트는 본문 인용 없이 파일:줄 범위로만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/agent/tools/practice.ts:49-68` `PracticeGate`, `createPracticeGate`; `:72-93` `problemInputObject`; `:97-161` `problemTool`; `:165-195` `concludeInputObject`; `:199-220` `concludeTool`; `:223-249` `practiceTools` | 도구 스키마·게이트·실행 규칙·레지스트리 | R-04~R-08 |
| C-02 | `src/agent/tool-execute.ts:235-261` `problemResult`, `concludeResult` | `problem`의 종료·영속 결과, `conclude`의 비종료 결과 | R-06, R-07 |
| C-03 | `src/core/native-messages.ts:189-238` `newGraphContextMessage`; `:246-343` `newThinkingMessage`, `newNextMessage`, `newProblemDismissedMarker`, `concludedByDismissalPair`; `:350-479` `cleanToolCallIds`, `modelSolutionForConclude`, `problemInputForConclude`, `activeProblemOf`, `pendingProblemDismissalOf` | 마커 모양·활성 문제 판정·건너뜀 합성·공개(블록 훑는 방향 포함) | R-09~R-14 |
| C-04 | `src/core/input-events.ts:44-57`, `:75-104` `parseDismissInput`, `:132-186` `dismissAppends`, `ChatInputError`, `parseChatInput`, `:197-244` `inputAppends`, `dismissalConclusion` | 연습 입력 파싱·검증(오류 문구)과 기록 추가, 합성 쌍 순서 | R-10~R-12 |
| C-05 | `src/core/contracts/chat.ts:198-221` `THINKING_LABEL`, `CONCLUDE_ACK_TEXT`, `NEXT_PROBLEM_TEXT` | 마커·결과의 고정 문구 | R-10~R-12 |
| C-06 | `app/api/chats/route.ts:22-71`; `src/store/chats.ts:35-51` `createChat`; `src/core/contracts/graph.ts:355-385` `titleFromPrompt` | 세션 생성과 시작 맥락, 제목, 모델 스탬프, 명제 필터 | R-01 |
| C-07 | `src/core/chains.ts:34-54` `chainsForSelection`; `:70-82` `resolveTargetId`; `:84-93` `formatChainLine`; `src/core/value-debris.ts:24-26` | 맥락 연쇄 계산, 대상 이름→id 정규화, 연쇄 줄 모양 | R-02, R-05 |
| C-08 | `src/server/chat-handler.ts:391-420`, `:515-525` | 연습 에이전트 선택, 추출·그래프 쓰기 없음 | R-03, R-04 |
| C-09 | `src/agent/teacher-agent.ts:74-81` `composeInstructions`, `:310-323` `createPracticeAgent`; `src/agent/prompt-segments.ts:37-43`, `:62-97`; `src/core/prompt-segments.ts:17` `FRAGMENT_RE` | 연습 프롬프트 조립(공통 기반 없음, 공유 조각 허용 목록, 조각 파일 패턴, 합성 구분자) | R-04 |
| C-10 | `src/core/native-messages.ts:512-595` `toLlmMessages`(마커 처리부 `:553-569`) | 마커의 모델 입력 변환 | R-13 |
| C-11 | `src/agent/prompts/practice/00-base.md:1-33`; `10-doctrine.md:7-141`(I `:11-25`, II `:27-41`, III `:43-57`, IV `:59-70`, V `:72-81`, VI `:83-106`, VII `:108-116`, VIII `:118-122`, IX `:124-130`, 금지 `:132-141`) | 연습 독트린과 도구 운용 규칙 | R-16~R-26 |
| C-12 | `src/core/argument-heal.ts:27-96` `healEncodedArguments`; `src/agent/tools/heal.ts:30-48` `withArgumentHeal`, `healToolRecord` | 인자 복구와 레지스트리 공통 복구(도구 자체 prepare 뒤에 적용) | R-05, R-07 |
| C-13 | `src/agent/tool-execute.ts:117-131` `invalidInputResult` | 오류 결과 모양(텍스트·`isError`·`details`) | R-06, R-07 |
| C-14 | `src/core/native-messages.ts:48-52` `INTERRUPTED_TEXT`; `:104-119` `newMessageId`, `newUserMessage` | 끊긴 호출 합성 문구, 메시지 id, `text` 입력의 사용자 메시지 모양 | R-12, R-13 |
| C-15 | `app/api/chats/[id]/dismiss/route.ts:25-65`; `src/server/dismissal-park.ts:45-80` | 문제 버리기 경로(404·400·202 보관·적용 시점) | R-12 |
| C-16 | `src/server/chat-handler.ts:156-166`, `:267-278`, `:297-303` | 입력 파싱·추가분 계산의 400 매핑, 400이 409보다 앞이라는 순서 | R-10~R-12 |
| C-17 | `src/server/chat-handler.ts:248`, `:253`, `:577`, `:582` | 컴팩션 종류·프롬프트 크기 추정의 연습 분기 | R-15 |
| C-18 | `src/server/turn-service.ts:50-84` `persistTurn`; `src/core/pending.ts:45-51` `QUESTION_TOOLS` | 턴 저장: 질문 도구의 깨끗한 자리표시 결과만 거르므로 `problem`·`conclude` 결과는 성공·오류 모두 기록에 남는다 | R-06, R-07 |
| C-19 | `src/agent/tools/jobs.ts:25-30`, `:131-166` `jobTools`; `src/agent/tools/graph.ts:41-79` `proberGraphTools`; `src/core/settings-resolution.ts:249-254` `graphToolsEnabled` | `research`·`pdf`와 그래프 읽기 도구의 이름·조건 | R-04 |
| C-20 | `app/api/graph/coverage/extract/route.ts:17-37` | 수동 추출 경로는 채팅 `kind`를 검사하지 않음 | R-03 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출. 코드를 실행하거나 원본 테스트를 열지 않았다. T-17 이후는 재구현 검증(`RESULT.md`)의 지적을 코드 줄에서 도출한 기대값이다. 사전 상태 칸의 `[배선]`은 서버 배선·저장소·에이전트 루프가 있어야 확인되는 사례이고, 순수 함수 층에서 술어로 줄여 테스트하면 규칙 문장을 되풀이할 뿐이라 약한 검증이다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-06 | 활성 문제가 있는 세션에서 `problem` 호출 | 오류 결과 "a problem is already active — call conclude on it before posing the next one". 새 문제는 안 생김 |
| T-02 | R-07 | 활성 문제가 없을 때 `conclude` 호출 | 오류 결과 "no active problem to conclude — pose one first" |
| T-03 | R-06~R-08 | 한 턴 안에서 `conclude` → `problem`(두 호출이 한 메시지든 따로든 순차 실행) | 둘 다 성공(게이트가 클로저로 바뀜). 도구는 이를 막지 않는다 |
| T-04 | R-05, R-06 | 그래프에 명제 {id:`p1`, name:"Chain rule"}. `target:["chain rule"]` / `target:["zzz"]` / `target:[]` / `target` 없음 | `["p1"]`로 정규화 / 오류(모르는 명제, 생략하라는 안내) / `target` 제거되어 통과 / 태그 없는 문제로 통과 |
| T-05 | R-05 | `mode:"analysis"` / `mode:"\"recall\""` | 복구 단계가 값을 바꾸지 않아 스키마 거절(문구는 루프 몫) / 복구되어 `recall`로 통과 |
| T-06 | R-09 | 기록: `problem`(깨끗한 결과) / 그 뒤 깨끗한 `conclude` / 대신 오류 `conclude` / 대신 `problem-dismissed` 마커 / `problem`이 오류 결과 | 활성 / 비활성 / 여전히 활성 / 비활성 / 활성 아님(안 일어난 일) |
| T-07 | R-10 | 활성 문제 id가 `c1`. `thinking`을 `problemCallId:"c2"` / 빈 글 / `c1`+글 | 400 "…targets no active problem" / 400 "…requires non-empty text" / `practice-thinking` 마커(`content:"Your thinking:\n<글>"`)가 붙고 턴 시작. 공백뿐인 글, 빈 `problemCallId`는 T-20 |
| T-08 | R-11 | teach 세션에 `next` / 연습 세션이고 활성 문제가 있을 때 `next` / 활성 문제 없음 | 400 "…practice-session affordance" / 400 "…requires no active problem" / `practice-next` 마커 + 턴 시작 |
| T-09 | R-12 | 활성 문제 `c1`에 `dismiss-problem`(id 일치). 이어서 `text` 입력, 다시 `text` 입력 | 첫 입력은 `problem-dismissed` 마커만 붙고 턴 없음. 이어지는 `text`는 합성 쌍(`conclude{outcome:"dismissed"}` 호출 id `call_conc_c1` + `CONCLUDE_ACK_TEXT` 결과 `details:{outcome:"dismissed",problemCallId:"c1"}`)이 사용자 메시지 앞에 붙고 턴 시작, 그 다음 `text`에는 쌍이 또 붙지 않음. 입력 종류별 차이는 T-29 |
| T-10 | R-01, R-02 | 명제 A·B·C를 고름. 저장된 연쇄 `{A,B → C}`와 `{A → D}`(D는 안 고름) | 맥락 `content`에 세 명제 줄과 연쇄 줄 하나 `A, B → C`(이름 기준). D 연쇄는 제외 |
| T-11 | R-02 | 명제 X를 골랐으나 현재 그래프에는 X가 없고 연쇄도 없음 | X는 명제 줄에는 나오고(스냅샷) 연쇄 계산에서는 제외됨. 연쇄가 없으면 "Reasoning chains" 절이 없음 |
| T-12 | R-01 | `graphContext.propositions` 70개 / 일부는 `statement`가 문자열이 아님 | 유효한 항목만 남겨 앞 64개 / 부적합 항목은 무시 |
| T-13 | R-03 | [배선] 연습 세션의 한 턴이 끝남 | 턴 종료 뒤 자동 추출 트리거가 호출되지 않음(`chat-handler.ts:521`의 조건). 순수 층에서는 `kind`로 조건을 계산하는 술어만 확인할 수 있다. 그래프 쓰기·커버리지 기록은 연습 에이전트에 그 도구가 없다는 R-04 구성으로 확인하고 수동 추출 경로는 확인 한계(R-03) |
| T-14 | R-06, R-07 | `problem` 호출이 성공 / `conclude` 호출이 성공 | `problem`: 결과가 `terminate:true`·`details:null`·고정 텍스트(순수 층 확인). **"턴이 끝남"은 [배선]**(루프가 `terminate`를 따름, 순수 층 밖). "결과가 기록에 남음"은 저장 함수(`persistTurn`, C-18)에 [assistant(`problem` 호출), toolResult(`problem`)]을 넣으면 둘 다 저장 목록에 있다(질문 도구 이름이 아니므로 걸러지지 않고 오류 결과도 저장됨). / `conclude`: 도구 결과만 있고 `terminate`가 없다(턴이 코드에 의해 끝나지는 않음, 맺음말 뒤 끝내는 것은 프롬프트) |
| T-15 | R-13 | 기록에 `problem-dismissed`와 `practice-thinking` 마커가 있음(그 사이에 `id`가 있는 일반 user 메시지) | 모델 입력에서 `problem-dismissed`는 빠지고 `practice-thinking`은 `{role:"user", content:[{type:"text", text:"Your thinking:\n…"}], timestamp:<마커 값>}`로 들어간다. 일반 메시지는 `id`만 없는 채로 그대로 |
| T-16 | R-14 | 공개 `conclude` 호출이 앞쪽에 오류로 거절된 `problem`과 깨끗한 `problem`을 둠 | 공개는 깨끗한 `problem`의 `modelSolution` |
| T-17 | R-05, R-07 | 활성 게이트에서 `conclude` 입력 `{outcome:"\"solvedWithHints\"", verdict:"v", rung:"\"R3\"", missClass:"null", retest:"true"}`를 `prepareArguments`에 넣고 이어 execute. `rung:"null"`, `retest:"false"`도 | prepare 출력 `{outcome:"solvedWithHints", verdict:"v", rung:"R3", missClass:null, retest:true}`(`rung:"null"`→`null`, `retest:"false"`→`false`). execute는 `CONCLUDE_ACK_TEXT`(종료 신호 없음)를 내고 게이트가 비활성이 된다. `outcome:"dismissed"`도 같은 경로로 성공 |
| T-18 | R-05, R-07 | `conclude` 입력 `outcome:"null"` / `rung:"R6"` / `rung:"\"R6\""` / `missClass:"Cue"` / `retest:"yes"` / `retest:1` / `verdict` 누락 | `prepareArguments`가 값을 바꾸지 않는다(`outcome` 스키마에 null이 없어 `"null"`도 안 풀림). 스키마 검증이 거절한다(문구는 루프 몫) |
| T-19 | R-08, R-09, R-14 | assistant 메시지 하나에 블록 `[conclude(c1), problem(p2)]`, 둘 다 깨끗한 결과(그 앞에 깨끗한 `problem(p1)`과 `modelSolution:"S1"`, p2의 `modelSolution:"S2"`). 순서를 `[problem(p2), conclude(c1)]`로 바꾼 경우도 | 앞 순서: `activeProblemOf` = p2, c1의 공개 = **"S2"**(새 문제 풀이가 공개됨). 바꾼 순서: `activeProblemOf` = null, c1의 공개 = "S2"(앞 블록 p2가 먼저 만나짐). 둘째 `problem(p2)`가 오류 결과였다면 앞 순서의 활성은 null(c1이 깨끗), 공개는 "S1" |
| T-20 | R-10 | `thinking` 입력: ① 활성 `c1`에 `problemCallId:"c1"`, 글 `"  \n\t "` ② 활성 문제 없음, 같은 글 ③ `problemCallId` 누락 / `""` / `5`, 글 `"x"`(그리고 글도 빈 경우) ④ 활성 `c1`에 글 `"  x \n"`. `text` 입력 `" "` / `" hi "`. `{type:"foo"}`, 비객체 | ① ② 400 "thinking input requires non-empty text"(파싱이 활성 확인보다 앞). ③ 400 "thinking input requires problemCallId"(글이 비어도 이 문구). ④ 마커 `content:"Your thinking:\n  x \n"`, `details:{problemCallId:"c1", text:"  x \n"}`(글을 자르지 않음). `text`: 400 "text input requires non-empty text" / 사용자 메시지 `content:" hi "`(문자열 그대로). `{type:"foo"}` 400 "unknown input type: foo", 비객체 400 "input must be an object" |
| T-21 | R-01 | [배선] 세션 생성 body `kind`가 `"practice"` / `"Practice"` / `"teach"` / `true` / 없음. 설정 strong 슬롯이 `{model:{provider:"p",id:"m"}, thinkingLevel:"high"}` / 슬롯 없음 / `model` 없는 슬롯. `title`이 `"   "` / 문자열 아님 / 공백으로 이어진 100자 넘는 여러 단어 | `kind`는 첫 경우만 기록에 `"practice"`(나머지는 필드 없음). 세션 설정은 첫 슬롯에서만 `{model:{provider:"p",id:"m"}, thinkingLevel:"high"}`(teach도 같다)이고 나머지는 설정 없음. 제목은 앞 둘 "Untitled session", 마지막은 72자 안에서 단어 경계로 잘리고 `…`가 붙음. 설정·저장소를 가짜로 바꾼 사례라 실제 파일 쓰기는 검증하지 않음 |
| T-22 | R-13 | 모델 입력 변환에 ① assistant 메시지 A1(`timestamp:100`, 블록 `toolCall(x1,"problem")`)이 마지막 ② A1에 호출 x1·x2, 그 뒤에 user 마커 하나, 그 뒤에 `toolResult(x2)` ③ 호출 없는 assistant 메시지 | ① A1(`id` 제거) 바로 뒤에 `{role:"toolResult", toolCallId:"x1", toolName:"problem", content:[{type:"text", text:INTERRUPTED_TEXT}], isError:false, timestamp:100}`. ② x1에만 합성 결과가 A1 바로 뒤에 끼고(x2는 몇 메시지 뒤 결과가 있어 합성 없음) ③ 합성 없음. 입력 기록은 바뀌지 않음 |
| T-23 | R-15 | [배선] 컴팩션 요청에 쓰이는 종류: 기록 `kind:"practice"`(메시지가 무엇이든) / `kind` 없음 | 연습은 요청 시작 게이트와 턴 종료 뒤 킥 두 곳 모두 `"practice"`이고 프롬프트 크기도 연습 프롬프트. `kind` 없음은 `teach`/`probe`(프로브 완료 여부, 이 스펙 밖) |
| T-24 | R-04 | 연습 도구 구성에 ① `jobs`·`graph` 둘 다 줌 ② `jobs` 없음 ③ `graph` 없음. 프롬프트 파일: 연습 디렉터리 `10-doctrine.md`·`00-base.md`·`notes.md`·`05-x y.md`, 공유 디렉터리 전체 | ① 키 순서 `problem, conclude, read, ls, find, grep, research, pdf, list_sessions, list_propositions`. ② `research`·`pdf` 둘 다 없음. ③ 그래프 도구 둘 다 없음. `toolToggles`는 무시. 프롬프트는 `00-base`, `10-doctrine`(`notes.md`·공백 든 이름은 `FRAGMENT_RE`에 안 맞아 제외) 뒤에 `10-voice`, `15-accuracy`, `16-mental-model`, `40-formatting`(공유의 나머지와 `system-prompt.md` 제외), 각 조각 앞뒤 공백을 자르고 `\n\n---\n\n`로 이음 |
| T-25 | R-05, R-06 | 그래프 노드(저장 순서) `{p1,"Chain rule"}`, `{p2,"chain rule"}`, `{p3,' "Power rule" '}`, `{q,"p1"}`. `target`: `[" :Chain Rule. "]` / `["p1"]` / `["power rule"]` / `["chain  rule"]`(안쪽 공백 둘) / `["q"]` / `[":p1:"]` / `["chain rule","zzz"]` / `["  :: "]` / `"zzz"`(문자열) / `"[\"chain rule\"]"`(JSON 문자열) | `["p1"]`(이름이 같은 p1·p2 중 첫 노드) / `["p1"]`(id가 이름 `"p1"`인 q보다 먼저) / `["p3"]`(노드 이름도 벗김) / 못 풀려 그대로 → execute 오류 `target ["chain  rule"] is not a known proposition — …` / `["q"]` / `["p1"]` / prepare `["p1","zzz"]`, 오류에는 푼 원소를 뺀 `target ["zzz"] is not…` / 벗기면 비어 그대로 → 오류 `target ["  :: "] is not…` / `target` 제거되어 태그 없는 문제로 통과 / 복구로 배열이 된 뒤 `["p1"]` |
| T-26 | R-06 | 게이트 활성에서 `problem`(`target:["zzz"]`) / 게이트 비활성에서 `target:["zzz","p1"]` 다음에 `target` 없는 `problem` | 첫째: ①이 먼저라 오류 텍스트 정확히 `Invalid tool input for tool "problem":\n- a problem is already active — call conclude on it before posing the next one`, `isError:true`, `details:{tool:"problem", problems:["a problem is already active — …"]}`. 둘째: 오류 `- target ["zzz"] is not a known proposition — targets must be proposition ids from the session context; if the material is not in the map, omit target entirely`이고 게이트는 비활성 그대로라 이어지는 `target` 없는 `problem`은 성공 |
| T-27 | R-01, R-02 | 고른 명제(스냅샷 이름) `a:"Zeta-old"`, `b:"Alpha-old"`, `c:"Gamma-old"`, `d:"Delta-old"`(문장은 모두 `s`). 현재 그래프 이름 `a:"Zeta"`, `b:"Alpha"`, `c:"Gamma"`, `d:"Delta"`. 저장된 연쇄 `{id:"zz_1", premises:["b","a"], conclusion:"c"}` | `content`의 명제 줄은 스냅샷 이름(`- [a] Zeta-old: s` …). 연쇄 절은 `- Delta (no premises)` 다음 `- Zeta, Alpha → Gamma`: 단독 항목 d는 노드 id `"d"`로 정렬되어 `"zz_1"`보다 앞, 전제는 이름(Alpha<Zeta)이 아니라 id(a<b) 순, 이름은 현재 그래프에서. `details.chains` = 이 두 줄(`- ` 없이) |
| T-28 | R-12 | [배선] 문제 버리기 경로: body `{input:{type:"dismiss-problem"}}` / `problemCallId:""` / `7` / `{input:null}`·`input` 없음 / `{input:{type:"foo"}}` / 같은 `{type:"dismiss-problem",problemCallId:"c1"}`을 `POST /api/chat`의 `input`으로 / 턴 실행 중 정상 입력 / 모르는 채팅 id | 400 "dismiss-problem input requires problemCallId"(둘째·셋째도 같음) / 400 "input must be an object" / 400 "unknown input type: foo" / 400 "unknown input type: dismiss-problem" / 202 `{ok:true,parked:true}`에 기록 불변, 턴 저장 후 `c1`이 여전히 활성이면 마커가 붙고 아니면 조용히 버려짐 / 404 "Unknown chat". 실행 중이 아니고 id 불일치면 400 "dismiss-problem input targets no active problem" |
| T-29 | R-12 | 기록이 [`problem(c1)` 깨끗한 결과, `problem-dismissed{c1}`]. 입력 `next` / `continue` / `text "hi"` / `thinking{c1,"x"}` / (쌍이 이미 붙은 뒤) `next` 다시 | `next`: [쌍(assistant+toolResult), `practice-next` 마커](세 메시지). `continue`: [쌍]만 붙고 새 메시지 없음. `text`: [쌍, 사용자 메시지]. `thinking`: 400 "thinking input targets no active problem". 쌍이 붙은 뒤에는 `activeProblemOf` = null이고 대기 판정도 없어 쌍이 다시 붙지 않음. 쌍의 assistant 호출 인자는 `{outcome:"dismissed"}`뿐 |
| T-30 | R-14 | 공개 계산의 경계: ① 대상 `problem`의 `modelSolution`이 숫자 `5`(더 앞 `problem`은 문자열 풀이를 가짐) ② [`problem(p0)` 깨끗, `conclude(c0)` 깨끗, `problem(p1)` 오류 결과, `conclude(c1)`]에서 c1 ③ c1 자체가 오류 결과 ④ 존재하지 않는 conclude id ⑤ 바로 앞 `problem`에 결과가 아예 없음 | ① 없음(더 앞 문제로 넘어가지 않음). ② p1을 건너뛰고 p0의 풀이(c0의 메시지는 `problem` 블록이 없어 지나감). ③ 공개 값은 그대로 계산됨(conclude의 깨끗함을 보지 않음). ④ 없음. ⑤ 그 호출은 건너뛰고 더 앞의 깨끗한 `problem`을 찾음 |
| T-31 | R-05, R-06 | `problem` 입력 `{statement:"", mode:"recall", modelSolution:""}`(게이트 비활성) | `prepareArguments`가 입력을 그대로 두고(같은 객체) 스키마에 최소 길이가 없어 거절 사유가 없다. execute는 성공 |

## 2부. 근거

### 2.1 요구사항별 근거 지도 [필수]
| R-ID / T-ID | 근거 (repo@b277ee3) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | C-06, C-07 | 소스 전문 읽음. `route.ts:49-68`이 필터 후 `slice(0, 64)`, 그래프에 있는 명제만 연쇄 계산(`pickedNodes = picks.map(byId.get).filter(defined)`), `chains.ts` 전문(단독 항목 id, 정렬, 전제 id 정렬, 이름은 `Object.fromEntries(byId)`=현재 그래프), `route.ts:36-42` 모델 스탬프, `titleFromPrompt` 전문 |
| R-03, R-04 | C-08, C-09, C-19, C-20 | `chat-handler.ts:391-420`, `:515-525`와 `prompt-segments.ts:37-43`, `:62-97` 읽음. 허용 목록은 `PRACTICE_SHARED_FRAGMENTS`. `composeInstructions`·`FRAGMENT_RE`·`jobTools`·`proberGraphTools`·`graphToolsEnabled` 읽음. 수동 추출 경로는 `kind`를 검사하지 않음(`src/agent/subagents`에는 practice 언급이 없으나 파이프라인 본문은 미열람) |
| R-05~R-09 | C-01, C-02, C-03, C-12, C-13, C-18 | 소스 전문 읽음. `argument-heal.ts`·`heal.ts` 전문(복구 순서: 도구 자체 prepare → 레지스트리 복구), `resolveTargetId`·`stripModelValueDebris` 전문, `persistTurn` 전문. 스키마 검증기(pi-ai)는 repo 밖이라 주석만 |
| R-10~R-13 | C-03, C-04, C-05, C-10, C-14, C-15, C-16 | 소스 전문 읽음. `input-events.ts` 전문, 문제 버리기 라우트·보관(`dismissal-park.ts`) 전문, `chat-handler.ts:150-167`·`:267-303` |
| R-14 | `native-messages.ts:362-409`(C-03); `grep -rln "missClass\|solvedWithHints" src components app` → `session-markdown.ts`, `tools/practice.ts`, `components/practice-cards.tsx` | 공개 규칙은 `problemInputForConclude` 전문 읽음(훑는 방향·같은 메시지 뒤 블록 포함). 두 UI 파일은 파일명 수준만 확인 |
| R-15 | C-17 | 호출처 4곳(`chat-handler.ts:248`, `:253`, `:577`, `:582`) 읽음 |
| R-16~R-26 | C-11 | 프롬프트 전문 읽음 |
| 문서·코드 차이 1 | `docs/architecture.md:161,184,381` §7; `src/core/ports.ts`; `ls src/store` | 문서는 `PracticeStore` 포트와 `data/practice/*.json`, 얼린 `ProblemSet`(명제 스냅샷), 칸막이→문제별 생성기 2단계 생성, 이산 세 축의 난이도 "사다리 0 Worked example … 4 Path-finding"을 설명하지만 **코드에는 없다**. `src/store`에 `practice.ts`가 없고 `ports.ts`에 `PracticeStore`가 없으며 `src/core/practice.ts`(문서가 언급한 `chainsForSelection` 위치)도 없고 `chainsForSelection`은 `src/core/chains.ts`에 있다. `src app components`에서 `splitter|partitioner|grader|ProblemSet`을 검색해도 결과가 없다. 실제 구현은 `kind:"practice"` 세션 + `problem`·`conclude` 두 도구 + 독트린 프롬프트다. 구현을 사실로 썼다 |
| 문서·코드 차이 2 | `agent/tools/practice.ts:1-9`, `agent/tool-execute.ts:253-255` 주석 | 두 주석은 `conclude`를 "턴이 계속되어 같은 답변에서 공개하고 다음 문제를 낸다"고 쓰지만 현재 도구 설명·`CONCLUDE_ACK_TEXT`(owner round 16)는 "맺음말 뒤 턴 종료, 다음 문제는 학습자의 명시적 go-ahead"이고 `conclude`는 종료 신호도 없다. 같은 턴의 `conclude` → `problem`을 막는 코드도 없으므로 이 휴지는 프롬프트 규칙이다(R-08, R-24). 구현·고정 문구를 사실로 썼다 |
| 문서·코드 차이 3 | `agent/teacher-agent.ts:311-319` 주석("ENTIRE registry is problem + conclude"), `practice.ts:223-248` | 레지스트리에는 `read`·`ls`·`find`·`grep`, `research`·`pdf`, 그래프 읽기 도구도 들어 있다. 구현을 사실로 썼다(R-04) |
| 문서·코드 차이 4 | `chat-handler.ts:403-406`의 "TARGET VALIDATION… whole graph" 주석과 `practice.ts:148-156` | 일치. 세션 선택이 아니라 그래프 전체로 검증한다 |
| 문서·코드 차이 5 | `chat-handler.ts:409-411` 주석("research honestly absent when no engine is live")과 `jobs.ts:25-30`, `:128-130`, `practice.ts:233-246` | `jobTools`는 항상 `research`를 돌려주고 `searchAvailable`은 연습 레지스트리에서 쓰이지 않는다("Research dispatch does not depend on it"). `jobs`가 주어지면 `research`와 `pdf`가 함께 있다. 구현을 사실로 썼다(R-04) |
| 문서·코드 차이 6 | `native-messages.ts:362-367` `modelSolutionForConclude` 주석("newest cleanly-posed problem BEFORE this conclude call")과 `:395-406` | 코드는 conclude가 든 메시지의 **뒤 블록**까지 훑으므로 같은 메시지의 새 `problem`이 대상이 된다. 구현을 사실로 썼다(R-14, T-19). 이전 서술 "가장 가까운 앞쪽"을 이 근거로 고쳤다 |
| 문서·코드 차이 7 | `chat-handler.ts:518-520` 주석("no extraction, no graph, no coverage")과 `app/api/graph/coverage/extract/route.ts:17-37` | 자동 트리거만 `kind`로 막히고 수동 추출 경로는 `kind`를 검사하지 않는다. 구현을 사실로 썼다(R-03) |
| 문서·코드 차이 8 | `native-messages.ts:345-349` 주석("newest problem tool call with nothing concluding after it")과 `:411-444`, `:350-360` | 주석은 결과를 보지 않는 옛 서술이다. 현재 코드는 깨끗한 결과가 있는 호출만 센다(R-09). 구현을 사실로 썼다 |
| 재구현 검증 반영(2026-10-27) | `artifacts/learnharness/reimplementation/practice/RESULT.md` 4절 19개·6절 12개 | 원본 코드로 모두 다시 확인했다. 구현자의 말이 코드와 다른 곳: 4-11(`dismiss-problem` 형태 검증이 "어디에도 없다" → `parseDismissInput`에 있음, R-12), 4-13(`text` 메시지 `content`가 블록 배열 → 코드는 문자열, 1.3), 4-17(`research`가 `pdf`와 독립 → 코드는 둘 다 `jobs`에 묶임, R-04; 조각 파일 패턴 `^\d+-.+\.md$` → 코드는 `^\d+-[\w.-]+\.md$`), 6-12(QA 빌림 목록, 1.2에 반영). 나머지는 코드와 같았고 R-ID·T-ID·C-ID로 반영했다 |
| T-01~T-16 | 구현에서 도출 | 실행·원본 테스트 미열람 |
| T-17~T-31 | 구현에서 도출(재구현 검증의 지적) | 기대값은 위 R-ID의 코드 줄에서 도출. 실행·원본 테스트 미열람. T-13·T-14의 배선 부분과 T-21·T-23·T-28은 서버 배선·저장소가 필요해 순수 층만으로는 확인되지 않는다 |

### 2.2 코드 읽는 순서 [선택]
`app/api/chats/route.ts`(생성·맥락) → `server/chat-handler.ts:391-452`(에이전트 선택) → `agent/tools/practice.ts`(도구·게이트) → `core/native-messages.ts:189-474`(마커·활성 문제) → `core/input-events.ts`(입력) → `prompts/practice/10-doctrine.md`.

### 2.3 비교·재사용 출처 [선택]
다른 레포의 같은 기능 스펙은 아직 없다. 코드를 복사한 범위 없음.

## 적용 메모 [선택]
| 관련 R-ID | 원본과 다르게 할 점(걸리는 곳) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-10~R-12 | "생각 제출", "다음 문제" 버튼, 문제 버리기는 앱의 연습 독 UI에 묶여 있다 | 터미널에는 그 버튼이 없다 | 학습자의 글을 그대로 제출로, "다음 문제"라는 말이나 명령을 go-ahead로 쓰는 식으로 대체할 수 있다. 입력 이벤트·마커·합성 쌍이 필요 없어질 수 있다(T-07~T-09가 바뀜) |
| R-08, R-24 | 휴지 규칙은 프롬프트에만 있어서 터미널 스킬에서도 지시문으로 옮기면 된다 | 규칙이 도구가 아니라 글이다 | 변경 없음 |
| R-14, R-25 | 원본은 연습 결과를 어디에도 모으지 않는다("상태 기록 없음") | 지속 관리를 원하면 원본에 없는 것이다 | 연습 결과(`outcome`·`rung`·`missClass`·`retest`)를 학습 기록에 남기는 것은 새로 정할 일이다(원본의 "기록·졸업 기준 없음"과 다름) |
