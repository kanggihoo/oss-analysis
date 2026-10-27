# learnharness core 재구현 검증 결과 (스펙 1부 + 1.5 코드 범위 기준)

SHA `b277ee3e0fa24249c1b2d0f9b7fd6ed485f484b9`. 원본을 실행하지 않았고, 아래 테스트는 "스펙/코드 읽기에서 도출한 기대값을 내 구현이 만족한다"는 것만 보여 준다. 원본 구현과 같은 출력을 냈다는 주장은 하지 않는다.

## 1. 구현 언어·범위
- Python 3.14(표준 라이브러리만), 테스트는 `unittest`. 실행: `cd .../reimplementation/core && python3 -m unittest -v`.
- 구현한 것(순수 계산·검증 + 질문·답 서버 경로의 최소 모의):
  - `qa.py`: 질문 도구 5종 스키마와 검증 함수, 인자 복구(options 문자열 풀기, 공통 heal), `correctAnswer` 복구, 선택지 정규화, FNV-1a+mulberry32 시드 섞기, `QuestionData` 구성, 확신도 칸·답 요청, `buildAnswer`, 압축형, 자리표시 결과, 종료 훅, 접힘 규칙.
  - `messages.py`: 대기 질문 판정, `hasProbeDone`, 답/핸드오프 메시지, 해제 휴지, 모델 입력의 "중단됨" 결과 합성.
  - `chat_server.py`: `answer`/`dismiss` 입력 파싱·검증·기록 붙이기, 병렬 질문 게이트, 한 채팅 한 턴(409), 에이전트 선택 이음새, wake 전달 테스트 더블, 추출기 입력 필터.
  - `probe.py`: `probe_done` 상수·steer, 그래프 읽기 도구 문구·게이트, 프롬프트 조립(파일 목록 입력).
  - `plan.py`: mermaid 부분집합 해석, 트리 구조 검증, 위치 파생, 단계 판정, `nodeId` 검증.
  - `tools.py`: 도구 객체(스키마, prepareArguments, executionMode, execute), `probe_done`, `plan_init`, 프로버/교사 레지스트리, 에이전트 루프를 흉내 낸 `call_tool`(prepare → heal → 스키마 검증 → execute).
  - `store.py`, `fixtures.py`: 인메모리 ChatStore와 테스트 도우미.
- 구현하지 않은 것: LLM 호출, UI, 네트워크, 프롬프트 본문, 작업 도구 내부(`read`/`ls`/`find`/`grep`/`research`/`pdf`/`demo`/`visual`은 빈 스텁), 컴팩션, `continue` 입력(아래), `dismiss-problem`, `persistTurn` 저장 필터.

## 2. 테스트 실행 결과
`Ran 83 tests ... OK` (통과 83, 실패 0, 오류 0). 실제로 실행한 것은 이 83개뿐이다.

T-ID 대응(이름이 `test_<QA|PM|PT|TC>_Txx_*`): 질문·답 계약 T-01~T-16 전부, 프로버 T-01~T-11 전부, 계획 T-01~T-15 전부, 교사 T-01~T-08 전부. 건너뛴 T-ID 없음(모든 T-ID가 [강제] 규칙을 다룬다).
- 약정: QA=question-answer-contract, PM=probe-measurement, PT=plan-tree, TC=teaching-cycle.
- 추가로 [강제] R-ID 단독 테스트를 넣었다: QA R-02,03,04,05,07,08,09,10,12,13,14,15,16,17,19,20 / PM R-02,03,06,07,13(+목록 도구 서식) / PT R-01,02,03,04,06,08,09,10,11 / TC R-01,02,07.

## 3. R-ID별 구현 현황
(질문·답 계약 = QA, 프로버 = PM, 계획 = PT, 교사 = TC)

| 스펙 | 구현함 | 구현하지 않음 (이유) |
|---|---|---|
| QA | R-01(도구 구성, 아래 추측 1), R-02~R-20 중 R-03,04,05,06,07(종료·훅),08,09,10,11,12,13,14,15(전송 칸),16(필드 채우기),17,18,19,20 | R-07의 "자리표시를 저장하지 않는다"(저장 필터 본문이 스펙에서도 미열람), R-14의 화면 렌더링, R-15의 "서버가 정수만 받아들인다"(코드에는 검증이 없음, 추측 9), R-21·R-22 (권고라서 제외) |
| PM | R-01,02(조립 순서 함수),03,04,05,06,07,08,09,11,12(스펙 해석대로),13(추출 필터) | R-10(발화 시점은 wake 파이프라인 본문 미열람, `추론` 등급), R-14~R-21(권고라서 제외) |
| PT | R-01~R-12 | R-13~R-18(권고라서 제외) |
| TC | R-01,02,03,04,05(질문 순차·게이트는 QA R-08/R-18로 구현),06(`explanation`/`committed` 스냅샷은 QA R-13),07,08 | R-09~R-18(권고라서 제외) |

권고라서 구현·테스트하지 않은 R-ID: QA R-21, R-22 / PM R-14~R-21 / PT R-13~R-18 / TC R-09~R-18.

## 4. 추측·모호했던 부분 (R-ID 또는 T-ID, 스펙이 말하지 않은 것, 내 선택)

1. **QA R-01, PM R-04, PT R-01 (토글 불가 주장)**: 스펙은 `quiz`/`explain`/`probe`/`recall`을 "개별로 끌 수 없다", `plan_init`을 "설정 토글로 끌 수 없다"고 쓴다. 1.5 범위의 코드(`createProberTools`/`createTeacherTools`)에서는 `withoutMechanics`가 `quiz`·`explain` 키만 지우고, `filterEnabledTools`는 이름이 `false`인 도구를 모두 지운다(그 함수는 `pending.ts:98`로 C-14 범위 밖). 따라서 팩토리 수준에서는 `probe`, `recall`, `ask_user_question`, `plan_init`, 파일 도구도 `enabled[name]===false`면 빠진다. "끌 수 없다"는 쓰기 쪽 검증(`TOGGLEABLE_TOOLS`, `settings-body.ts`는 읽지 않음)에 있다. 나는 팩토리 코드대로 구현했고 `test_PT_R01`이 "팩토리에서는 plan_init이 빠진다"를 못박는다. 스펙 문구와 코드가 어긋난 사례다.
2. **PM R-12 (research 등록)**: 스펙은 `jobTools`가 조건 없이 만든다고 하지만 `tools.ts:333`은 `jobs.research ? {research} : {}`로 조건부다. `tools/jobs.ts`는 1.5 표에 없어 열지 않았고 스펙 해석(무조건 등록)대로 구현했다. 결과가 스펙의 주장과 코드의 조건문 중 어느 쪽인지는 이 재구현으로 판정할 수 없다.
3. **QA R-09, R-19 (`resultIdsFrom`)**: 심볼이 1.5 범위 밖이다. "assistant 메시지 이후 `toolResult`의 `toolCallId` 집합"으로 추정했다.
4. **QA R-18/R-20 처리 순서**: 코드(`chat-handler.ts:280-303`)는 병렬 게이트(저장 후 종료)를 409 검사보다 먼저 한다. 그래서 턴이 도는 중에도 형제 질문이 남는 `answer`는 저장되고 409가 나지 않는다. 스펙 R-20은 "이미 턴이 실행 중이면 새 입력은 409"라고만 써서 이 순서를 말하지 않는다. 나는 코드 순서를 따랐고(게이트 → 409 → 쓰기 선행 저장 → 턴), 409일 때는 아무것도 저장하지 않는다고 가정했다.
5. **QA T-09, T-16 (400/409 매핑)**: `ChatInputError` → HTTP 상태 매핑 코드가 범위에 없다. 스펙이 400이라 했으므로 예외 객체에 `status`를 달았다.
6. **QA R-14, T-13 (섞기 재현성)**: 스펙은 "FNV-1a 계열 해시 + mulberry32"만 쓰고 시험 벡터가 없다. 나는 `seededRandom` 코드를 읽고 UTF-16 코드 단위 기준으로 이식했지만, 실제 JS와 같은 순서가 나오는지는 확인하지 못했다(테스트는 "같은 id → 같은 순서", "순서의 순열성", "`correctIndices`가 섞은 뒤 위치"만 확인한다).
7. **QA R-14 (QuestionData 구성)**: 스펙에는 `QuestionData`를 만드는 규칙이 없고(`question-dock.tsx:262-306`을 읽어서 안다) 그 코드에서 `questionType`은 `kind==="quiz"`일 때만 `normalizeQuizType(input.type)`이다. 교사 `explain`의 `type`은 답 객체에 스냅샷되지 않는다고 구현했다. 스펙 1.3 표의 "quiz 교사 호출만"과는 일치하지만 `explain`의 `type`이 답에 남는지 여부를 스펙이 직접 말하지는 않는다.
8. **QA R-02 / TC T-03 (heal의 범위)**: 스펙의 "공통 인자 복구"는 `argument-heal.ts`의 본문(1.5가 가리키는 건 `:1-24`와 `:58` 한 줄)을 읽어야 구현할 수 있다. 본문은 `:25-57`(헬퍼)과 `:59-`에 있어서 범위 밖을 열었다(5절). `type:"\"predict\""`는 그 본문에서 literal union 복구로 풀린다. 단 `correctAnswer`(string|array 합집합)는 heal 대상이 아니다(최상위 `type`이 없음). 배열 문자열 복구는 `coerceCorrectAnswer`가 한다.
9. **QA R-15 ("서버 기록은 0~100 정수라면 칸 밖 값도 받는다")**: `parseChatInput`에는 `answer` 객체 검증이 없어서 서버는 어떤 값이든 저장한다(R-10과 같음). "정수라면"이라는 조건에 해당하는 코드를 찾지 못했다. 서버 검증은 구현하지 않았다.
10. **QA R-16**: "`thinking`은 객관식·ask 답에서만 보낸다"는 코드(`question-dock.tsx:381-394`)로는 `qd.mode !== "text"`일 때다. 즉 선택지 없는 ask(글 모드)에서도 `thinking`은 안 간다. 스펙 문구("객관식·ask")만으로는 ask 글 모드가 어느 쪽인지 모호하다. 코드대로 구현했다.
11. **스키마 검증의 세부(QA/PM/PT/TC 전반)**: 스펙은 "에이전트 루프가 스키마로 거절한다"만 말하고 (a) 알 수 없는 키를 허용하는지, (b) 거절 결과의 모양·문구, (c) `quizOptionProps`/`askOptionProps`의 정확한 필드 정의(`question-core.ts:158` 앞쪽, 범위 밖)는 말하지 않는다. 나는 알 수 없는 키는 허용(`additionalProperties` 미지정으로 추정), 거절 결과는 `invalid_input_result` 모양을 빌려 쓰고, 선택지 필드는 스펙 1.3 표(label 필수, value 선택, ask만 description)대로 정했다. `test_TC_R02`는 "퀴즈 선택지의 `description`이 거절되지 않는다"는 이 추측을 못박은 것일 뿐, 원본이 그렇다는 근거는 없다.
12. **PM R-05~R-09, PT R-07 (`serverExecute` 변환)**: `execute`가 돌려주는 `{ok:false,error}`/`{text,details}`를 도구 결과 메시지로 바꾸는 `serverExecute`는 범위 밖이다. 나는 그 안쪽 객체를 그대로 반환값으로 삼았다. 스펙이 "`isError`로 표시되지는 않는다"고 쓴 것과 맞는다.
13. **PM T-01 (재현 가능성 문제)**: 스펙의 시나리오는 "마지막 assistant 메시지에 결과 없는 `probe` 호출이 있고 `probe_done` 호출"이다. 그러나 `probe_done`의 `execute`가 읽는 것은 저장소의 `getChat` 기록이다. 진행 중인 턴의 assistant 메시지(방금 낸 `probe_done` 호출 자신 포함)가 `execute` 시점에 이미 기록에 들어 있는지를 스펙이 말하지 않는다. 들어 있다면 R-06 검사(`hasProbeDone`)가 항상 "이미 끝났다"가 되므로 들어 있지 않아야 하는데, 그러면 "같은 배치의 `probe` + `probe_done`"은 기록에 안 보여 R-05가 어떤 상황에서 발동하는지 불분명하다. 나는 `getChat`이 돌려준 기록을 그대로 믿는 방식으로 구현했다(테스트는 기록에 질문이 이미 있는 상태를 직접 만든다). 어느 상황에서 R-05가 실제로 걸리는지는 확인하지 못했다.
14. **PM T-11, R-08 (steer 멱등)**: `steerDelivered`는 도우미일 뿐 어디서 호출하는지(wake 파이프라인, 범위 밖)를 스펙이 말하지 않는다. 내 `make_wake_deliver`(테스트 더블)가 호출한다. 이 테스트는 "도우미 + 내 더블이 중복을 거른다"만 확인한다. 원본이 어디서 거르는지는 모른다.
15. **PM R-02, TC R-01, T-07 (프롬프트 조립)**: 스펙은 순서만 쓰고, 코드는 각 조각을 `trim()`하고 빈 조각을 버린 뒤 `"\n\n---\n\n"`로 잇는다(스펙에는 "사이는 `---` 줄로 잇는다"만 있음). 디렉터리를 읽는 대신 `{dir: [파일명]}`을 입력으로 받게 했다. 정렬은 파일명 문자열 정렬(JS 기본 정렬)로 구현했다. `practice` 에이전트 분기는 범위 밖이라 뺐다.
16. **PM T-10 / 그래프 도구 (정렬·데이터)**: 스펙 1.3은 "most recent first"만 쓰는데 코드의 정렬 키는 `updatedAt` 내림 → `createdAt` 내림 → `id` 오름이고 `localeCompare`를 쓴다. 나는 일반 문자열 비교로 근사했다. 세션 목록의 데이터 파생(`birthSessionPartition`, 파일 이름 대체 규칙)은 입력으로 받았다. 각 입력의 `list_*` 도구 입력 스키마(`listSessionsInput`/`listPropositionsInput`)는 범위 밖이라 구현하지 않았다.
17. **TC T-08 / PM R-13 (추출기 입력)**: 필터(교사 텍스트 블록만)는 구현했지만 줄 서식 `TEACHER [id] text`는 `proseView` 주석에서 가져온 추측이다. `messageViewLines`(`core/coverage.ts`)는 범위 밖이다. 테스트는 "무엇이 들어가고 안 들어가는가"만 본다.
18. **QA 1.3 `continue` 입력**: 스펙은 표에 한 줄로만 설명하고 R-ID와 T-ID가 없다. 판정 조건은 `native-messages.ts` 주석(파일 끝 근처, 범위 안)에 일부만 있고 `inputAppends`의 `continue` 분기는 범위 밖(`:211-`)이라 구현하지 않았다.
19. **QA T-04**: "유효 값 목록 포함"의 서식은 스펙에 없고 코드 문자열(`Valid values: "a", "b", "c".`)을 그대로 썼다.
20. **JSON 직렬화**: 모델에게 보이는 압축 JSON 문자열의 공백·키 순서는 스펙에 정의가 없다(T-01은 키를 나열만 함). 나는 JS `JSON.stringify` 스타일(공백 없음)과 코드의 키 삽입 순서(`kind, dontKnow, answers, text, other, correct, confidence, thinking, thinkingWhileReading`)를 썼다. 문자열 동일성으로 비교하는 구현자는 이 순서를 알 길이 없다.
21. **R-ID 간 모순·T-ID와 규칙 불일치**: 위 1번(토글) 외에는 T-ID 기대값과 스펙 규칙이 어긋난 곳을 찾지 못했다. PT R-05의 "5–15 노드"(도구 설명)와 "상한 없음"은 스펙이 직접 구별해서 적었고 T-15가 맞는다.

## 5. 1.5 범위 밖으로 추가로 연 원본 파일 (스펙의 코드 참조 누락 후보)
- `src/core/pending.ts:60-125` (`TOGGLEABLE_TOOLS`, `EnabledTools`, `filterEnabledTools`): QA C-14는 `:45-58`만 가리킨다. 추측 1을 풀려고 열었다. C-14/C-10/C-11에 `:60-111`을 더해야 R-01(토글)을 구현할 수 있다.
- `src/core/argument-heal.ts:25-57`, `:59-140` (헬퍼와 `healEncodedArguments` 본문): QA C-09와 TC C-11은 `:1-24`와 `:58`만 가리켜서 본문이 빠진다. 같은 이유로 `src/agent/tools/heal.ts:28-60`은 범위 안이었다.
- 사고(스펙 외 읽기 아님): zsh가 `$S:src/...`의 `:s`를 치환 수정자로 해석해 `git show`가 SHA의 커밋 자체(HEAD 쪽 `tests/chatgpt-auth.test.ts` 변경 diff)를 출력한 적이 있다. 의도한 열람이 아니고 내용은 쓰지 않았다. 이후 `${S}:`로 고쳐 읽었다.
- 그 외는 모두 1.5 표의 파일·줄 범위 안이다. 범위 안이지만 읽지 않은 것: `question-core.ts:158` 앞쪽(`quizOptionProps`/`askOptionProps` 정의), `serverExecute`, `resultIdsFrom`, `inputAppends`의 `continue`와 `dismissalConclusion`(범위 밖이라 읽지 않음), `tools/jobs.ts`.

## 6. 스펙 개선 제안
1. 토글 불가 주장(QA R-01, PM R-04, PT R-01)을 "팩토리 수준에서는 이름이 false이면 빠진다(`quiz`/`explain` 키만 제외), 쓰기 검증(`TOGGLEABLE_TOOLS`)이 사실상 막는다"로 고치거나 코드 참조에 `pending.ts:60-111`을 넣는다.
2. QA C-09/TC C-11에 `argument-heal.ts:25-100`(본문)을 넣는다. 지금 범위로는 heal을 구현할 수 없다.
3. 모델에게 보이는 압축 JSON의 직렬화 규칙(공백 없음, 키 순서)과, 시드 섞기의 시험 벡터(예: seed "abc" + 3개 선택지 → 순서)를 1.6에 넣는다. 지금 T-13은 같은 입력 재현성만 말한다.
4. PM R-05/R-06이 읽는 "기록"이 진행 중인 턴의 assistant 메시지를 포함하는지 시점을 적고, R-05가 실제로 발동하는 시나리오(같은 배치? 중단 뒤 재시도?)를 T-01에 명시한다.
5. 스키마 검증의 계약(알 수 없는 키 허용 여부, 거절 결과 모양)과 `serverExecute`의 변환 규칙을 스펙의 공통 계약 한 곳에 적는다. 모든 T-ID의 "스키마가 거절"이 이 계약에 기댄다.
6. QA R-20에 "게이트가 409보다 먼저 평가된다"를 넣거나 R-18/R-20의 순서를 명시한다.
7. `continue` 입력에 R-ID와 T-ID를 붙인다(지금은 표 한 줄).
8. QA R-15의 "정수라면 칸 밖 값도"가 가리키는 서버 검증 코드가 실제로 있는지 확인해 문구를 고친다(내가 읽은 범위에는 없다).
9. PM 1.3 `list_sessions`에 정렬 키(`updatedAt` 내림 → `createdAt` 내림 → `id` 오름)를 적는다.
10. PM T-11에 "누가" 중복을 거르는지(deliver 쪽인지 큐 쪽인지)를 적거나 해당 코드를 1.5에 넣는다.
11. TC T-08과 PM R-13은 "교사 텍스트만"이라는 필터만 정해져 있으므로, 줄 서식을 검증하려면 `coverage.ts`의 `messageViewLines`를 1.5에 포함해야 한다.
