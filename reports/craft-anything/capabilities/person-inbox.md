---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/engine/src/inbox.rs
  - crates/engine/src/questions.rs
  - crates/engine/src/tools/interaction_tools.rs
  - crates/engine/src/tools/project_tools.rs
  - crates/engine/src/workspace.rs
  - crates/engine/src/settings.rs
  - crates/engine/src/clean_room.rs
  - crates/ai/src/cli_agents/acp.rs
  - crates/ai/src/cli_agents/adapters/copilot.rs
  - crates/ai/src/cli_agents/adapters/grok.rs
  - crates/engine/src/feed.rs
  - crates/engine/src/tool.rs
  - crates/platform/src/fs.rs
  - crates/ai/src/rebuild/question.rs
  - crates/ai/src/rebuild/notes.rs
  - crates/ai/src/rebuild/mod.rs
  - crates/ai/src/rebuild/tools.rs
  - crates/ai/src/rebuild/brief.rs
  - crates/ai/src/rebuild/feed.rs
  - crates/ai/src/cli_agents/adapters.rs
  - crates/ai/src/cli_agents/mod.rs
  - apps/craft-anything-cli/src/main.rs
depends: []
status: ready
---

# 질문·승인·중간 노트 인박스 (person inbox)

> 빌더 에이전트가 사람에게 묻는 질문과 행동 승인 요청, 사람이 빌드 중에 추가하는 노트, 사람이 빌드에 대해 묻는 "Just ask" 질문을 프로젝트 폴더의 파일로 주고받고, 답이 없거나 취소되면 어떻게 계속할지까지 정한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

세 갈래이고 서로 순서가 없다. 아래는 갈래별 대표 흐름이다.

**A. 에이전트가 사람에게 묻는다 (질문·승인)**
1. 빌더 에이전트가 MCP 도구 `core_person_ask`(질문) 또는 `core_action_approve`(Claude Code의 `--permission-prompt-tool`로 지정된 권한 확인)를 호출한다. 이 도구들은 `craft-anything-cli mcp --inbox <project>/inbox`로 뜬 도구 서버 안에서 돈다.
2. `core_person_ask`는 프로젝트의 질문 정책이 `Decide`면 인박스를 거치지 않고 "스스로 결정하라"는 안내를 돌려준다. `core_action_approve`는 정책(`decide`)·프로젝트 선택·Auto mode로 허용·거절·질문을 먼저 정한다.
3. 사람에게 물어야 하면 `Inbox::post`가 `<id>.request.json`을 원자적으로 쓰고 호출은 200ms 간격으로 `<id>.answer.json`을 기다린다(`Inbox::wait`).
4. 앱(또는 다른 프로세스)이 `pending()`으로 요청을 보여 주고, 사람의 답을 `<id>.answer.json`으로 원자적으로 쓴다. 도구 `project_inbox_answer`도 같은 일을 하며 답을 프로젝트 대화(`feed.json`)에도 남긴다.
5. `wait`가 답을 읽으면 두 파일을 지우고 `Answer`를 돌려준다. 시간 초과·취소면 request만 지우고 `None`이다.
6. 질문은 `{answered, answer, choice, text}`, 승인은 `{behavior: allow|deny, ...}`로 에이전트에 돌아간다.

**B. 사람이 빌드 중에 노트를 추가한다**
1. `RebuildRun::add_note`(도구 `rebuild_note`)가 노트 id(프로세스 안 카운터)를 만들고 `inbox/notes/<id>.json`을 쓴 뒤 메모리 목록에도 넣는다.
2. Claude Code 빌더는 `--settings`로 받은 PostToolUse 훅이 도구 호출마다 `craft-anything-cli builder-notes <dir>`를 실행한다. 이 명령이 대기 중인 노트를 `<id>.read.json`으로 이름을 바꿔 가져가고(`claim`) 그 텍스트를 훅 JSON `additionalContext`로 출력한다.
3. 실행 루프는 `<id>.read.json`을 보고 노트를 "읽힘"으로 처리해 대화에 싣고 파일을 지운다(`relay_read_notes`).
4. 가져가기 전이면 `rebuild_note_withdraw`가 파일을 지워 철회한다. 이름 변경이 일어난 뒤에는 철회할 수 없다.
5. 훅이 가져가지 못한 노트(훅이 없는 에이전트, 턴 종료)는 턴이 끝난 뒤 다음 메시지에 붙어 간다(`added`).
6. 앱이 닫혀 대기 중이던 노트는 파일에 사람의 원문(`left`)이 있어 다음 실행이 시작할 때 자기 대기 노트로 이어받는다(`take_left`).

**C. 사람이 빌드에 대해 묻는다 (Just ask)**
1. `rebuild_question_ask`가 질문(1~4000자)을 받아 `question::ask`를 부른다. 빌더 세션의 복사본·파일 읽기 전용 새 대화·읽기 전용 API 루프 중 하나가 답한다. 파일은 바꾸지 않는다.
2. 답을 `questions.json`에 덧붙인다(최대 200개).
3. 다음에 빌더에 가는 메시지(노트 또는 턴 메시지)가 아직 안 알려 준 질문·답을 앞에 붙이고, 턴이 끝나거나 노트가 읽힌 뒤 `told`로 표시한다.

### 1.2 범위·통합 지점
- 제공: 인박스 파일 프로토콜(요청·답), 질문·승인 도구 두 개와 승인 정책, 사람 쪽 응답 도구, 중간 노트의 전달·철회·이월, 훅 서브명령 `builder-notes`, Just ask 질문의 기록과 빌더 전달 표시.
- 제외:
  - 코딩 에이전트를 서브프로세스로 띄우고 이벤트를 받는 부분(feature map 13행). 이 스펙은 "`CliSpec`의 `question: true` 대화가 텍스트를 스트림으로 돌려주고 `TurnDone`/`Error` 이벤트로 끝난다"는 경계만 쓴다(R-29).
  - 앱 화면(카드·버튼)의 모양. 앱이 `pending()`을 보여 주고 `answer`를 쓴다는 데이터 계약만 쓴다.
  - 도구 레지스트리·동의 체계(`ToolSpec` 일반, 12행)와 Clean room의 도구 허용 목록(11행)은 아래 R-27처럼 이 기능의 도구가 목록에 있다는 사실만 쓴다.
- 외부 의존·선행 계약: 파일 시스템(원자적 쓰기는 `craft_anything_platform::fs::write_atomic`: 같은 폴더의 임시 파일에 쓰고 `sync_all` 뒤 이름 변경), 프로젝트 폴더 구조(`<project>/inbox`, `craft.json`의 `questions`·`approvals`·`allowed_actions`), `Settings`(`auto_mode`, `questions`), 세션의 `InboxDir`. 에이전트 구동은 위 제외 항목대로 경계만 쓴다.
- 소유 상태·부작용: `<project>/inbox/*.request.json`·`*.answer.json`(요청 하나의 수명 동안), `inbox/activity/*.txt`(도구가 기다리는 중임을 앱에 알리는 한 줄, 대기가 끝나면 삭제), `inbox/notes/*.json`, `<project>/questions.json`, 프로젝트 `feed.json`(답 기록), `craft.json`(승인 "항상 허용" 기록).

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 요청 파일 `<id>.request.json` | `Request{id: string, kind: "question"\|"approval", title: string, detail: string(기본 ""), choices: list<string>(기본 []), allow_text: bool(기본 false), action: optional string, created_ms: int}` | 질문자가 쓴다. `title`은 질문 또는 행동 한 줄 설명, `detail`은 부가 설명, `action`은 승인에서 "항상 허용"을 기억할 때 쓰는 태그. pretty JSON. |
| 답 파일 `<id>.answer.json` | `Answer{choice: optional string, text: optional string, allow: optional bool, always: bool(기본 false)}` | 앱 쪽이 쓴다. 질문은 `choice`/`text`, 승인은 `allow`/`always`. 모든 필드가 생략 가능하다. 선택지와 `choice`의 일치, `kind`와 필드의 일치는 검사하지 않는다(R-06). |
| id | `<now_ms>-<pid>-<프로세스 내 카운터>` | 허용 문자 `[0-9a-z-]`, 1~64바이트. 파일 경로를 만드는 모든 곳(`path`)에서 검증하고 어긋나면 `ToolError::invalid`. |
| `Answer.as_text()` | → string | `choice`와 비지 않은 `text`(앞뒤 공백 제거)가 둘 다 있으면 `"<choice> — <text>"`(em dash 양옆 공백), 하나만 있으면 그 값, 없으면 빈 문자열. `allow`·`always`는 반영하지 않는다. |
| `Inbox::post(kind, title, detail, choices, allow_text, action)` | → id | 폴더가 없으면 만든다. request를 원자적으로 쓴다. |
| `Inbox::pending()` | → list<Request> | 폴더의 `*.request.json` 중 id가 유효하고 같은 id의 `answer.json`이 **없는** 것. 읽거나 파싱할 수 없는 파일은 건너뛴다. `created_ms` 오름차순(같으면 순서 불명). 폴더가 없으면 빈 목록. |
| `Inbox::answer(id, answer)` | → ok / ToolError | 답을 원자적으로 쓴다. request의 존재를 확인하지 않는다. |
| `Inbox::wait(id, timeout, cancelled)` | → optional Answer | 200ms 간격 폴링. R-04. |
| `core_person_ask` | in: `question`(string, 1~2000바이트), `choices`(list, 기본 []), `allow_text`(bool, 기본 true), `context`(string, 기본 ""); 알 수 없는 필드는 거부. out: `{answered: true, answer, choice, text}` 또는 `{answered: false, note}` | 토셋 Core, effects `CHANGES_UI_STATE`. 최대 대기 30분. |
| `core_action_approve` | in: `tool_name`(string), `input`(JSON, 기본 null), `tool_use_id`(optional string, 사용하지 않음). out: `{behavior:"allow", updatedInput: <input 그대로>}` 또는 `{behavior:"deny", message}` | 토셋 Core, effects `CHANGES_UI_STATE`. 도구 id는 상수 `APPROVE_TOOL`. 호출 자체는 거절이어도 성공(`Ok`)이고 거절은 `behavior`로 전한다. |
| `project_inbox_answer` | in: `project`(경로), `id`(string), `choice`·`text`(optional string), `allow`(optional bool), `always`(bool, 기본 false). out: `{answered: <id>, shown: string}` | 토셋 Projects, effects `WRITES_FILESYSTEM ∪ CHANGES_UI_STATE`. `shown`: `allow=true&always` → `"Always allowed"`, `allow=true` → `"Allowed"`, `allow=false` → `"Not allowed"`, `allow` 없음 → `as_text()`. |
| `rebuild_note` | in: `project`(경로), `text`(string). out: `{id: int, queued: int}` | 토셋 Projects. 이 세션에서 실행 중인 빌드가 있을 때만. |
| `rebuild_note_withdraw` | in: `project`, `id`(int). out: `{withdrawn: <text>}` | 토셋 Projects. |
| `rebuild_question_ask` | in: `project`, `question`(string). out: `{project, question, answered: Answered, not_kept: optional string}` | 토셋 Projects, effects `LAUNCHES_PROCESS ∪ ACCESSES_NETWORK`. |
| `Answered` | `{answer: string, from: "builders_session"\|"the_files", backend: string, cost_usd: optional float, cost_is_estimate: bool, builder_notice: optional string}` | `builder_notice`는 저장된 빌더가 꺼졌거나 사라져 다른 AI가 답했을 때만. |
| 노트 파일 `notes/<id>.json` | `{id: int, text: string, left: optional {text, shown, pictures: list<path>}}` | `id`는 프로세스 안 카운터(1부터, 재시작하면 처음부터). 가져가면 `<id>.read.json`. |
| 훅 출력 | stdout 한 줄 JSON `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext": <문구>}}` | 가져간 노트가 없으면 아무것도 출력하지 않는다. 문구와 목록 형식은 C-02. |
| CLI `builder-notes <dir>` | in: 폴더 경로. out: 위 훅 출력 또는 없음, 종료 코드 0 | 숨김 서브명령. 엔진을 만들지 않는다. |
| `questions.json` | `{version: 1, items: list<AskedQuestion>}` | `AskedQuestion{question, answer, from_session, backend, cost_usd?, after, at_ms, deep(기본 true), told(기본 false)}`. 최대 200개, 넘치면 오래된 것부터 버린다. |

### 1.4 행동 규칙과 남은 질문

**인박스 파일 프로토콜**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 인박스 경로를 만드는 모든 연산에 id가 들어온다 | id가 `[0-9a-z-]`가 아니거나 비었거나 64바이트를 넘으면 `ToolError::invalid("<id> is not an inbox id")`. 경로 이탈(`../escape`)·대문자(`A`)는 거절된다. `pending()`도 유효하지 않은 id의 파일은 목록에서 뺀다. `wait`는 id가 잘못되면 오류가 아니라 `None`을 돌려준다. | 코드 확인 |
| R-02 | `post` | `<now_ms>-<pid>-<카운터>` id로 request를 원자적으로 쓰고 id를 돌려준다. 같은 밀리초의 두 요청도 카운터로 구별된다. 카운터는 프로세스 안에서만 유일하고 프로세스 사이 구별은 `pid`가 맡는다. 폴더가 없으면 만든다. `created_ms`는 id의 시각과 별도로 `now_ms()`를 한 번 더 읽은 값이다. | 코드 확인 |
| R-03 | request·answer·노트·활동 파일을 쓴다 | 모두 임시 파일에 쓰고 `sync_all` 뒤 이름 변경으로 바꿔, 읽는 쪽이 쓰다 만 파일을 보지 않는다. 쓰기에 실패하면 임시 파일을 지운다. | 코드 확인 |
| R-04 | `wait(id, timeout, cancelled)` | 루프마다 먼저 answer 파일을 읽어 `Answer`로 파싱되면 answer와 request를 지우고 `Some`을 돌려준다. 파싱이 실패하는 answer 파일은 지우지 않고 계속 기다린다. answer가 없고 `cancelled()`이거나 `timeout`이 지났으면 request만 지우고 `None`. 다음 폴링까지 200ms 잔다. 답이 이미 있으면 취소·시간 초과보다 답이 우선한다. | 코드 확인 |
| R-05 | 대기 중 요청이 `pending()`에 보이는 기간 | request가 있고 answer가 없는 동안만 보인다. 답이 쓰이면 `wait`가 읽기 전에도 이미 목록에서 빠진다. 시간 초과·취소로 request가 지워지면 목록에서 사라진다. | 코드 확인 |
| R-06 | 답을 쓴다 (`Inbox::answer`) | 요청이 존재하는지, `kind`가 질문인지 승인인지, `choice`가 `choices` 안인지 검사하지 않고 파일만 쓴다. 존재 확인은 호출자(`project_inbox_answer`, R-12)가 한다. 시간 초과로 request가 지워진 id에 `Inbox::answer`로 직접 쓰면 짝 없는 answer 파일이 남는다(`pending()`·`wait`가 다시 보지 않으므로 지워 줄 곳이 코드에서 확인되지 않는다). | 코드 확인(검사 없음) · 추론(짝 없는 파일이 영구 잔존) |
| R-07 | 도구가 오래 걸리는 대기를 한다 (`Activity`) | `inbox/activity/<pid>-<카운터>.txt`에 한 줄을 원자적으로 쓰고, 같은 객체의 `say`는 이전 줄을 대체한다. `Activity`가 drop되면 파일을 지운다. `activity(inbox)`는 비지 않은 줄만 `(파일명에서 .txt 뗀 이름, 줄)`로 이름순 반환한다. 쓰기 실패는 경고 로그만 남기고 호출을 실패시키지 않는다. 실행이 시작될 때 `clear_activity`로 폴더 전체를 지워 중단된 도구의 줄이 남지 않게 한다. | 코드 확인 |

**질문 도구 `core_person_ask`**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | `question`이 앞뒤 공백 제거 후 비었거나 2000바이트(문자 수 아님)를 넘는다 | `ToolError::invalid("question must be 1..=2000 characters")`. | 코드 확인 |
| R-09 | 선택지 정리 | 각 선택지를 앞뒤 공백 제거 후 최대 120**문자**로 자르고, 빈 것을 버리고, 앞에서 6개만 남긴다. 카드의 `allow_text`는 `p.allow_text \|\| p.choices.is_empty()`다. 뒤쪽 식은 정리 **전** 목록으로 판정하므로 선택지가 전부 공백뿐이고 `allow_text=false`면 선택지도 입력칸도 없는 카드가 만들어질 수 있다(코드 확인: 식, 추론: 그 카드가 그대로 앱에 노출됨). | 코드 확인 · 추론 |
| R-10 | 이 프로젝트의 질문 정책이 `Decide` (프로젝트 `Manifest.questions`가 있으면 그 값, 없으면 앱 `Settings::questions`, 이것도 `None`이면 `auto_mode`가 켜졌을 때 `Decide`, 꺼졌을 때 `Ask`) | 인박스 존재 여부와 상관없이 사람에게 묻지 않고 `{answered:false, note: DECIDE_ANSWER}`를 돌려준다. `DECIDE_ANSWER`는 "다음 메시지를 `I decided:`로 시작해 질문·선택·이유를 쓰고 계속하라"는 지시이고 원문은 C-04. 정책 확인이 인박스 확인보다 먼저다. | 코드 확인 |
| R-11 | `Ask` 정책인데 세션에 `InboxDir`이 없다 | `ErrorCode::FeatureMissing`, 메시지 "nobody is available to answer questions in this session", 안내(remediation) "Make a sensible choice, say which one you made and why, and continue." | 코드 확인 |
| R-12a | `Ask` 정책이고 인박스가 있다 | `kind=question`, `action=None`으로 `post`하고 진행 표시 "Waiting for your answer…"를 보고한 뒤 최대 30분, 호출 취소를 `cancelled`로 넘겨 `wait`한다. 답이 오면 `{answered:true, answer: as_text(), choice, text}`. 답이 없거나 취소·시간 초과면 `{answered:false, note:"No answer came. Continue with your best judgement and state the assumption you made."}`로 성공한다(취소도 오류가 아니라 이 응답). | 코드 확인 |

**사람 쪽 응답 도구 `project_inbox_answer`**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | `project`가 프로젝트 폴더가 아니다 | `ErrorCode::NotFound`, "`<path>` isn't a project folder: ...", remediation "Pass a folder from project_list". | 코드 확인 |
| R-13 | `id`가 이 프로젝트의 `pending()`에 없다 (이미 답했거나, 시간 초과로 사라졌거나, 없는 id) | `ErrorCode::NotFound` "No question <id> is waiting in this project.", remediation "Use project_show to see the questions still waiting." 같은 요청에 두 번째 답은 이 오류다. | 코드 확인 |
| R-14 | 정상 | 요청을 **먼저** 읽어 두고(답을 쓰면 질문자가 바로 파일을 지울 수 있으므로) `Answer`를 쓴 뒤 `feed::record_answer`로 프로젝트 대화에 `Ask{request, answer: shown}`을 남긴다. 대화에 이미 그 id가 있으면 새로 넣지 않고 답만 채우며, 이미 답이 있는 항목은 덮지 않는다. 대화 저장에 실패해도 도구는 성공하고 경고 로그만 남는다. | 코드 확인 |
| R-15 | 실행 중인 빌드가 같은 대화 파일을 저장한다 | 다른 곳(CLI, 에이전트의 `project_inbox_answer`)이 쓴 `Ask`의 답은 저장 직전에 디스크 `feed.json`에서 읽어 메모리 대화에 옮겨 보존한다. | 코드 확인 |

**승인 도구 `core_action_approve`와 정책**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-16 | 승인 판정 순서 (`approve_with`) | ① Clean room이면 `off_limits`가 원본 접근을 거절한다(이후 단계보다 우선, 자동 허용도 이를 못 뚫는다). ② `outcome`: 기본 정책 `decide` → 프로젝트가 "항상 허용"한 행동(`allowed_actions`) → 프로젝트의 종류별 선택(`approvals`) → 선택이 없으면 Auto mode 기본. 결과는 허용/거절/질문 셋 중 하나. ③ 질문이면 인박스가 없을 때 거절("Nobody is available to approve this. Stay inside the project folder and use the build commands."), 있으면 카드를 올리고 최대 30분 기다린다. 승인 도구 호출은 어느 경우에도 `Ok`이고 거절은 `behavior: deny`다. | 코드 확인 |
| R-17 | 기본 정책 `decide` (도구별) | `Read`·`Glob`·`Grep`·`LS`·`TodoWrite` → 허용. `Write`·`Edit`·`MultiEdit`·`NotebookEdit` → 대상이 `app/` 또는 `checks/` 안(링크를 따라간 실제 경로, 가능한 시작 폴더 둘 모두에서)이고 Craft Anything 자신의 기록(manifest·feed·inbox·사람 사진 등, `is_own_record`)이 아니면 허용, 아니면 질문("Change a file outside the project: <경로>"). `Bash` → R-18. `WebFetch`·`WebSearch`·그 밖의 도구 → 질문(제목 "Read a web page: <url>"/"Search the web: <query>"/"Use <tool>"). 워크스페이스를 모르면 `Bash`는 질문. | 코드 확인 |
| R-18 | `Bash` 명령(워크스페이스 있음) | 빈 명령 → 거절 "Empty command." `&&`로 나눈 부분 중 하나라도 끝나지 않는 명령(서버 목록 `SERVER_COMMANDS`에 해당하고 안전 목록에 없는 것, 또는 `--watch` 단어 포함)이면 거절하며 `npm run build`/`cargo build`를 쓰라는 안내를 준다. 쉘 제어 문자(`\| ; < > \` $` 개행)나 단독 `&`가 있으면 질문. 각 부분은 `cd`(결과가 `app/` 안), 안전 명령(`SAFE_COMMANDS`, 단어 경계 일치), 게임 엔진 자체 빌드(`engine_build`), 또는 `app/` 안에 실제로 있는 빌더 자신의 프로그램(`own_program`)이면 통과하고 하나라도 아니면 질문한다. 전부 통과하면 허용. 질문 제목은 "Run a command: `<명령 300자까지>`", 태그는 `bash:<첫 단어>`. | 코드 확인 |
| R-19 | 종류 분류 (`kinds_of`, `kind_of`) | 파일 쓰기 도구는 `System`(시스템 폴더 또는 자기 기록) 또는 `OutsideFiles`, 웹 도구는 `Web`, `Bash`/`PowerShell`은 `Publish`(push·publish 계열), `System`(`SYSTEM_COMMANDS` 포함 또는 manifest·`approvals-set`·인박스·`CRAFT_ANYTHING_AGENT`를 이름으로 또는 경로로 가리키는 명령), `DeleteOutside`(삭제 명령이 프로젝트·temp 밖을 가리킴)의 해당하는 전부, 하나도 없으면 `Commands`, 그 밖의 도구는 `OtherTools`. 한 명령이 여러 종류일 수 있고 가장 엄격한 선택이 적용된다(`allow`<`ask`<`refuse`, 동률이면 앞 종류). | 코드 확인 |
| R-20 | 종류별 기본 (프로젝트가 안 골랐을 때) | 표는 C-05(`ACTION_KINDS`): Auto mode 켜짐 → `Web`·`Commands`·`OutsideFiles` 허용, `Publish`·`DeleteOutside`·`System`·`OtherTools` 거절. Auto mode 꺼짐 → `Web` 허용, 나머지 질문. 거절 문구는 프로젝트가 고른 거절이면 "This project refuses <what> ("<name>" in its approvals)...", 기본 거절이면 "Auto mode never allows <what> without the person..."(원문 C-05 근처 `refusal`). 프로젝트가 `refuse`로 고른 종류는 이전 "항상 허용" 기록이 있어도 거절이다. | 코드 확인 |
| R-21 | `allowed_actions` 기록 | 모든 종류가 `Web`·`Commands`·`OutsideFiles`·`OtherTools`(행동 단위로 기억하는 종류)인 명령이고, 프로젝트가 그 종류를 `refuse`로 고르지 않았으며, 행동 태그가 `allowed_actions`에 있으면 허용한다. `Publish`·`DeleteOutside`·`System`은 "항상 허용"이 그 종류 전체의 `approvals=Allow`로 기록되므로 같은 명령 앞부분이 같은 다른 행동으로 번지지 않는다. | 코드 확인 |
| R-22 | 카드 내용 | `kind=approval`, `title`은 R-17/R-18의 제목, `detail`은 `input`의 pretty JSON을 4000**문자**까지 자른 것, 선택지 없음, `allow_text=false`, `action`은 기억 태그(행동 단위면 `bash:npm` 같은 행동 태그, 종류 단위면 종류 이름 `web` 등). 카드를 올리기 직전 "Waiting for your OK…"를 보고한다(ACP 승인 경로는 보고하지 않는다). | 코드 확인 |
| R-23 | 사람의 답을 해석한다 | `allow == Some(true)`이면 허용, `always`가 true이고 워크스페이스를 알면 기억한다(행동 단위는 `allowed_actions`에 태그 추가(중복 없이), 종류 단위는 `approvals[종류]=Allow`; 저장 실패는 무시). 그 밖의 모든 답(`allow`가 false이거나 **없음**)은 거절이고 `text`가 있으면 이유로 쓴다. 거절 문구: "The person said no[: <text>]. Find another way or ask them with core_person_ask." 답 없음·취소·시간 초과: "No answer came in time, so this wasn't done. Continue without it if you can." | 코드 확인 |
| R-24 | 예산 초과 에셋 생성도 같은 인박스를 쓴다 | `ask_approval`이 같은 승인 카드로 "Spend about $X more…"를 묻고 `assets:over-budget` 태그로 기억한다. Auto mode에서는 묻지 않고 거절. | 코드 확인 |
| R-25 | ACP 계열 빌더의 권한 요청 | 실행 루프가 같은 `approve_with`를 인박스·`auto_mode`·`clean_room`·중지 신호와 함께 부르고, 결과 `Ok(Ok(()))`만 허용(bool)으로 전한다. 거절 사유나 오류는 에이전트에 전달되지 않고 거절 하나로 합쳐진다. | 코드 확인 |
| R-26 | `never_unasked` | "Auto mode 기본이 거절인 종류"인지 판정해 거절 문구를 주는 공개 함수로, 이 크레이트 안의 본 코드에서는 호출되지 않고 테스트에서만 쓰인다(검색 결과). 승인 흐름의 동작은 R-16~R-21이 정한다. | 코드 확인(호출처 검색) |
| R-27 | Clean room의 도구 허용 목록 | `core_person_ask`, `core_action_approve`, `project_inbox_answer`, `rebuild_note`, `rebuild_note_withdraw`, `rebuild_question_ask`, `rebuild_questions_list`가 Clean room 허용 목록(`TOOLS`)에 있다. `core_person_ask`·`core_action_approve`도 같은 목록(`clean_room.rs:28-29`)에 있다. 즉 Clean room에서도 일곱 도구 모두 호출된다. | 코드 확인 |

**중간 노트**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-28 | `rebuild_note` | 이 세션에서 실행 중인 빌드가 있으면 `add_note`로 노트를 만든다. 실행 중인 빌드가 없으면 `ErrorCode::BadInput` "No build is running for this project in this session.", remediation "Start a follow-up with rebuild_start". 응답 `queued`는 아직 안 읽힌 노트 수. | 코드 확인 |
| R-29 | `add_note(text, shown, pictures)` | 프로세스 전역 카운터(1부터 증가)로 `id`를 만든다. 텍스트가 비지 않으면 `note_with_just_asked`로 이 모드가 보여 줄 수 있는 **아직 안 알려 준** Just ask 질문·답(`untold(ws, !clean_room)`, 같은 실행의 먼저 대기 중인 노트가 이미 실은 것은 제외)을 앞에 붙인 `file_text`를 만든다. `notes/<id>.json`에 `{id, text: file_text, left: {text: 원문, shown, pictures}}`를 쓰고, 메모리 목록에도 원문·`shown`·사진·붙인 질문과 함께 넣는다. 파일 쓰기가 실패해도 경고만 남기고 노트는 메모리에 남아 턴 종료 후 경로로 간다. 붙이는 Just ask 본문 형식은 `just_asked`(최근 5개, 질문 300자, 답 1500자로 자름). | 코드 확인 |
| R-30 | 훅이 도는 시점 | Claude Code 빌더이고 노트 폴더가 있고 원격 실행이 아닐 때만 `--settings`로 PostToolUse 훅(`matcher:"*"`, `timeout:10`)이 달린다. 명령은 `"<cli>" builder-notes "<dir>"`(경로는 `\`를 `/`로). 훅이 없는 어댑터(ACP 계열 포함)는 중간 전달이 없다. | 코드 확인(Claude Code 인자) · 코드 확인(ACP 중간 노트 없음 선언은 어댑터 표 테스트) |
| R-31 | `claim(dir)` | 폴더의 `<숫자>.json`(그 형식이 아닌 `<숫자>.read.json` 포함 이름은 제외)을 id 오름차순으로 훑어 각 파일을 읽고 JSON으로 파싱되면 `<id>.read.json`으로 이름을 바꾼 뒤 `text`(문자열)를 돌려준다. 파싱되지 않거나 읽을 수 없거나 이름 변경이 실패한(다른 쪽이 먼저 가져갔거나 철회됨) 파일은 건너뛴다. 이름 변경이 성공했는데 `text` 필드가 문자열이 아니면 가져가기만 되고 반환 목록에는 없다. 폴더가 없으면 빈 목록. 각 노트는 한 번만 넘겨진다. 이름 변경이 노트가 손을 바꾸는 유일한 순간이다. | 코드 확인 |
| R-32 | `hook_output(texts)` | 비었으면 출력 없음. 아니면 `additionalContext`에 "The person added this while you were working:\n- <t>...\nIt applies to the work from here on, and your reply can say how you took it into account."를 담은 JSON 한 줄. 에이전트가 도구의 명령이 아니라 사실로 읽도록 서술형이다. 사진 경로는 훅 출력에 없다. | 코드 확인 |
| R-33 | 실행 루프가 읽힘을 감지한다 (`relay_read_notes`, 약 120ms 폴링 루프 안) | `<id>.read.json`이 있는 메모리 노트를 읽힘으로 분리한다. 노트에 붙어 간 Just ask 질문은 `mark_told`로 `told` 표시, 노트 파일(둘 다)을 지우고, `RunEvent::Note{shown, pictures}`로 대화에 싣는다. 읽힌 노트 중 텍스트가 비지 않은 것이 있으면 "변화 없는 턴 수" 진행 카운트를 재설정할 표시를 켠다. | 코드 확인 |
| R-34 | `unsend(id)` (`rebuild_note_withdraw`) | 메모리 목록에 있는 id만 대상이다. 먼저 `take_back`(대기 파일 삭제)을 시도하고, 삭제에 실패했는데 읽힘 파일이 있으면 `None`. 삭제에 성공하면(또는 실패했지만 읽힘 파일도 없으면) 메모리에서 빼서 노트를 돌려주고 도구는 `{withdrawn: text}`. `None`이면 `ErrorCode::BadInput` "Note <id> isn't waiting: the agent has read it, or it isn't from this session." 다른 세션이 만든 노트는 이 세션의 실행 객체에 없어 철회할 수 없다. | 코드 확인 |
| R-35 | 턴이 끝났는데 안 가져간 노트 (`added`) | 메모리의 노트를 전부 꺼내 노트 파일을 지우고(훅이 같은 노트를 또 주지 않게), 텍스트가 빈 노트를 버리고, 남은 노트마다 `RunEvent::Note`를 내보낸 뒤, 붙일 Just ask 문맥 + `added_prompt`("While you were working, the person added:\n- ...\n\nTake this into account now: ... Reply with 1-3 plain sentences on what you changed.") + 사진 안내를 다음 메시지로 보낸다. | 코드 확인 |
| R-36 | 새 실행이 시작된다 (`take_left`) | 노트 폴더에서 `left`가 있고 `text`가 공백뿐이 아닌 대기 노트(읽힘 파일·`left` 없는 옛 파일·노트가 아닌 파일 제외)를 id 오름차순으로 모은 뒤 폴더를 통째로 지운다(id가 프로세스마다 1부터 시작해 충돌하므로). 이 실행이 자기 메시지를 갖고 있으면(`message` 있음) 모은 것을 버린다. 폴더를 읽는 중 오류(읽을 수 없는 항목)가 나면 폴더를 지우지 않고 `notes-unread-<ms>`로 옮기고(이동도 실패하면 경고만) 빈 목록을 돌려준다. 이어받은 노트가 있으면 새 요청으로 간주해 "변화 없는 턴 수"와 "작동하는 빌드가 없다는 검사 수" 카운트를 0으로 재설정한다(저장 실패는 로그만). | 코드 확인 |

**Just ask 질문**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-37 | `ask(question)` 입력 검사 | 앞뒤 공백 제거 후 비었거나 4000바이트를 넘으면 `ToolError::invalid("A question is 1 to 4000 characters.")`. | 코드 확인 |
| R-38 | 누가 답하는가 | 코딩 에이전트(`AgentCli`) 빌더: 프로젝트에 이 모드(Deep/Clean room)의 세션이 저장돼 있고 어댑터가 이어받기(`resumes`)를 지원하면 빌더 세션의 복사본이 답하고(`from=builders_session`), 아니면 새 대화(`the_files`). 질문을 받지 않는 어댑터(`!answers_questions()`)는 거절된다(`cannot_answer`가 앱에 미리 알린다). API 키 AI: 변경 없는 도구만 가진 `ReadOnlyHost`에 별도 엔진을 붙인 에이전트 루프, `the_files`. 모든 경우 프롬프트에 프로젝트 이름·요청·폴더·상태·스택·최근 바뀐 파일 25개(깊이 12, 20,000개까지 스캔, `node_modules` 등 제외)가 붙는다. 읽기만 하고 아무것도 바꾸거나 실행하지 말라는 `PREAMBLE`은 새 대화에 프롬프트 앞에, 세션 복사본에는 시스템 프롬프트 인자로 간다. | 코드 확인(구조) · 미확인(Claude Code·Copilot 플래그의 실제 효과는 실행하지 않음) |
| R-39 | 세션 복사본 답변이 "세션이 이 컴퓨터에 없음"으로 실패 | 프로젝트의 저장된 세션 id를 (그때도 같은 id일 때만) 잊게 하고, 파일로 새 대화를 만들어 같은 질문을 한 번 더 한다. 잊는 데 실패해도 질문은 계속된다. | 코드 확인 |
| R-40 | 답 수집 (`collect`) | 텍스트 조각을 모으다 `TurnDone`이면 모은 텍스트(공백 제거)와 비용을 돌려준다. `Error` 이벤트 → `ErrorCode::ProgramFailed`(+remediation). 취소 → `ErrorCode::Cancelled` "The question was stopped." 10분 초과 → `ErrorCode::TimedOut` "No answer came in time."(remediation "Ask again, or ask something shorter."). 에이전트가 바쁘지 않게 된 지 2초가 지나도 완료 이벤트가 없으면: 텍스트가 있으면 그것을 답으로, 비었으면 `ProgramFailed` "The AI stopped without answering." 취소·시간 초과 시 대화를 멈춘다. | 코드 확인 |
| R-41 | 비용 | 세션 복사본은 세션 전체 누적 비용을 보고하므로 `claude-code`는 질문 시작 전 빌더 합계와의 차이를 질문 비용으로 쓰고(추정치로 표시), 다른 어댑터는 비용을 표시하지 않는다. 새 대화·API 경로는 보고된 비용 그대로. 프로젝트 사용량에 비용이 더해진다(0보다 큰 유한값만). | 코드 확인 |
| R-42 | 질문 기록 (`questions::add`) | `questions.json`에 덧붙이고 200개를 넘으면 오래된 것부터 버린다. 읽고 쓰는 전체가 프로세스 안 뮤텍스 하나로 직렬화된다. 파일을 읽을 수 없거나 JSON이 깨졌으면 빈 목록으로 보고 경고를 남기며, 이때 `add`는 그 파일을 새 항목 하나로 덮어쓴다(`mark_told`는 해당 항목이 없으면 쓰지 않으므로 깨진 파일을 보존한다). 저장 실패는 도구 결과의 `not_kept`로 전달되고 답은 그대로 돌려준다. | 코드 확인 |
| R-43 | 전달 대상 모드 (`untold(ws, deep)`) | 아직 `told`가 아니고, 빌더가 Deep이면 모두, Clean room이면 `deep=false`로 기록된 것만. 모드가 기록되지 않은 옛 항목은 Deep으로 간주한다. Clean room 빌더에 못 간 항목은 Deep 실행을 위해 남는다. | 코드 확인 |
| R-44 | `told` 표시 시점 | 질문이 붙은 노트가 읽혔을 때(R-33), 또는 붙인 메시지로 한 턴이 정상 종료했을 때만(실패한 턴은 표시하지 않아 같은 질문이 다시 갈 수 있다). 식별은 `(at_ms, question)` 쌍. | 코드 확인 |
| R-45 | Just ask 본문이 빌더에 어떻게 전달되나 | "별도 대화에서 한 질문이고 기록에 없으며 아무것도 바꾸지 않았다, 배경일 뿐이고 요청이나 지시가 아니다"라는 안내와 `Q:`/`A:` 쌍을 앞에 붙이고 `---`로 구분한다. | 코드 확인 |

**승인 정책의 명령 분류 상세** (R-18·R-19의 판정을 구현자가 재현하기 위한 규칙. 입력 문자열은 `Bash`/`PowerShell`의 `command`다.)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-46 | `Publish` 판정 (`publishes`) | 소문자로 바꾼 명령을 `; & \| 개행 ( ) \` { } < >` 문자에서 잘라 조각으로 만든다. 조각마다 공백으로 단어를 나누고 단어 양끝의 `"` `'` `$`를 떼고 빈 단어를 버린다. 조각의 **모든 단어**를 프로그램 후보로 보고 뒤따르는 나머지 단어와 함께 `publishes_with`(C-10)에 넘겨 하나라도 참이면 `Publish`다. 단어 위치를 제한하지 않으므로 `echo git push`도 참이다. 프로그램 이름은 폴더(`/`·`\`까지)와 확장자(`.exe .cmd .bat .ps1`)를 뗀 것이다. 규칙표는 C-10. | 코드 확인 |
| R-47 | `System` 판정 (`kinds_of`의 두 번째 조건) | 소문자 명령이 `SYSTEM_COMMANDS`(C-11)의 항목 중 하나라도 **부분 문자열로** 포함하거나 `names_records`(R-48)가 참이면 `System`이다. | 코드 확인 |
| R-48 | `names_records(c, ws)` (`c`는 소문자 명령) | `joined`=`c`에서 `"` `'` `\` `` ` ``를 모두 뺀 것, `path`=`c`에서 `"` `'` `` ` ``만 뺀 것. 다음 중 하나면 참: ① `joined`가 `craft.json`, `approvals_set`, `approvals-set`, 소문자로 바꾼 `CRAFT_ANYTHING_AGENT` 중 하나를 포함. ② 워크스페이스를 알 때, `c`·`path`·`joined` 중 하나가 `mentions(text, inbox_dir)` 참. ③ 워크스페이스를 알 때 `reaches_inbox`(R-49) 참. 워크스페이스를 모르면 ①만 본다. `mentions`: 양쪽을 소문자로 하고 `\`를 `/`로 바꾼 뒤, 인박스 경로(끝 `/` 제거, 비면 거짓)가 텍스트에 포함되거나, 경로가 `X:/rest` 꼴이면 Git Bash 형 `/x/rest`가 포함되면 참. | 코드 확인 |
| R-49 | `reaches_inbox(c, ws)` | 명령을 `shell_words`(R-52)로 단어로 나누고 각 단어를 `= > < \| ; &`에서 다시 잘라 조각을 만든다. 조각마다 읽는 방식 후보를 만든다: 조각 그대로, `\`를 `/`로 바꾼 것, `\`를 지운 것, 그리고 조각이 `-`로 시작하고 `:`를 가지면 첫 `:` 뒤 값(`\`→`/`)(PowerShell `-Path:inbox/x`). 후보 중 `inbox`를 포함하는 것을, 시작 폴더 둘(프로젝트 폴더, `app_dir`) 각각에서 `resolve`(경로를 구문상으로만 해석하고 `..`가 뿌리를 넘으면 `None`)한 결과가 `inbox_dir` 안(`inside`)이면 참. 이름이 `inbox`를 포함해도 해석 결과가 인박스 밖이면(앱 자신의 `src/inbox/`) 거짓. 명령 전체가 소문자라 대문자 절대 경로는 이 함수 대신 `mentions`(대소문자 무시)가 잡는다. | 코드 확인 |
| R-50 | `DeleteOutside` 판정 | 소문자 명령이 `DELETES`(C-11)의 항목을 부분 문자열로 포함하고(`rm `은 `confirm ` 같은 단어에도 걸린다) `deletes_outside(원문 명령, ws)`가 참이면 `DeleteOutside`. `deletes_outside`: 허용 뿌리 = 프로젝트 폴더(있을 때), 시스템 temp 폴더, `/tmp`, `c:/tmp`. `shell_words`로 나눈 단어 중 하나라도 ① `..`를 포함, ② `~`로 시작, ③ 소문자로 `$home`·`%userprofile%`·`$env:`를 포함하면 참. 아니면 단어가 `/c/`·`/C/`로 시작하면 `c:/`로 바꾼 뒤, 절대 경로(`/`로 시작하거나 둘째~셋째 글자가 `:/` 또는 `:\`)이면서 허용 뿌리 어느 것 안(`inside`, 링크 미추적)에도 없으면 참. 상대 경로(`..` 없음)는 거짓. | 코드 확인 |
| R-51 | 파일 경로 안전 판정에 쓰는 보조 규칙 | `inside(dir, p)`: `p`가 `dir`이거나 그 안(Unix: `Path::starts_with`; Windows: 소문자·`/` 통일 후 접두 비교). `real_path(p)`: 존재하는 가장 깊은 부분을 링크 따라 정규화하고 없는 나머지는 그대로 붙인다. 존재하나 따라갈 수 없는 부분(끊긴 링크)이 있으면 `None`. `really_inside(dir, p)`: 둘 다 `real_path` 성공이고 `inside`(허용 방향). `may_reach(dir, p)`: `inside(dir,p)`이거나, `real_path(p)`가 없으면 참(막는 방향), 있으면 `dir`·`real_path(dir)` 안인지. `resolve(base, p)`: 절대 경로는 그대로, 상대 경로는 `base`에 붙여 `.`을 없애고 `..`로 한 단계씩 올라가되 뿌리 위로 가면 `None`. `resolve_as_opened`: 같으나 Unix에서 `..` 앞의 링크를 먼저 실제 경로로 바꾸고, 뿌리의 `..`는 뿌리에 머문다. `opened_at`: 상대 경로는 [프로젝트 폴더, `app_dir`] 둘 모두에서, 절대 경로는 `app_dir`만 기준으로(워크스페이스 없으면 `/`) `resolve_as_opened`한 목록이고, 파일 쓰기 허용은 그 목록 **전부**가 허용돼야 한다. | 코드 확인 |
| R-52 | `shell_words` | 따옴표(`"`·`'`) 안은 한 단어로 묶고(따옴표 문자는 버림), 따옴표 밖의 `\`+공백은 공백 하나로 이어 붙이고, 그 밖의 `\`는 그대로 둔다(Windows 경로). 따옴표 밖 공백이 단어를 가른다. 빈 따옴표 `""`도 빈 단어로 남는다. 구현 C-12. | 코드 확인 |
| R-53 | `is_own_record(p)`와 `OWN_NAMES` | 프로젝트 폴더 아래 이름 `craft.json`, `feed.json`, `questions.json`, `usage.json`, `build-activity.log`, `build-activity.old.log`, `assets.json`, `transcript.json`, `extract-transcript.json`, `agent-session.jsonl`, `inbox`, `capture`, `reference`, `attachments`, `investigation.cany`, `pinned` 안에 `p`가 있으면 자기 기록이다(`checks`는 `OWN_NAMES`에 있으나 제외: 빌더의 노트 자리). 링크를 따라간 실제 경로 기준 판정도 함께 본다. `app_in_root`(앱이 프로젝트 폴더 자체)여도 이 이름들은 쓰기 허용에서 빠진다. | 코드 확인 |

**Just ask의 "읽기만" 보장이 구현되는 방식**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-54 | 질문 접근 등급 | `CliSpec.question=true`이면 `access_for`가 Deep이면 `Question`, Clean room이면 `CleanRoomQuestion`으로 정한다(빌더 여부 무관). 질문 대화는 `builder=None`, 알림·승인 경로·노트 훅 없이 만들어진다(`CliSpec::new(..., false, project)`, `question: true`, `resume`, `preamble`). `reads_checked`는 `CleanRoomQuestion`에서 참. | 코드 확인 |
| R-55 | Claude Code 질문 인자 (`question_args`) | 인자 순서: 백엔드의 추가 인자(`options.args`) → `-p --output-format stream-json --verbose --append-system-prompt <PREAMBLE> --model <cli_model 또는 기본 모델>` → (`resume`이 있을 때만) `--resume <session> --fork-session` → `--no-session-persistence --strict-mcp-config --disallowedTools` + `CHANGING_TOOLS`(`Write Edit MultiEdit NotebookEdit Bash PowerShell WebFetch WebSearch Task TodoWrite AskUserQuestion`) → Deep(`reads_checked`가 거짓)이면 `--allowedTools Read Glob Grep`, Clean room이면 `READING_TOOLS`(`Read Glob Grep LS NotebookRead`)를 `--disallowedTools` 목록에 이어 붙이고 `--allowedTools`는 주지 않는다. `--mcp-config`, `--permission-prompt-tool`, `--settings`(노트 훅)는 없다. 복사본은 `--fork-session`과 `--no-session-persistence`로 저장되지 않아 빌더 세션과 파일이 그대로다. 프롬프트는 이 어댑터가 stdin으로 받는다. | 코드 확인 · 미확인(Claude Code 플래그의 실제 효과는 외부 프로그램 동작) |
| R-56 | 세션 이어받기 조건 | 일반 CLI 경로는 어댑터가 `resumes()`일 때만 저장된 세션 id를 넘기고(Claude Code만 참), ACP 질문 대화는 `resume`을 항상 버려 새 세션을 연다. | 코드 확인 |
| R-57 | `answers_questions()`가 거짓인 어댑터 | 일반 CLI 경로는 질문 대신 `AgentEvent::Error{"<name> can't be kept to only reading here, so it isn't asked questions about a build.", remediation "Ask with Claude Code, or with an AI that has an API key."}`를 내고 아무것도 실행하지 않는다. ACP 경로는 `acp_for`가 `None`. `answers_questions()`가 참인 어댑터는 Claude Code, Copilot, Grok(그 밖은 `Plain`처럼 기본 거짓; 기본 거짓 확인 사례: codex, gemini-cli, aider). | 코드 확인 |
| R-58 | ACP 질문 세션 (Copilot) | MCP 서버를 하나도 붙이지 않고(`mcp_servers=[]`) 모든 `session/request_permission`을 `cancelled`로 응답한다(승인 카드를 만들지 않는다). 지원하지 않는 다른 요청은 `-32601` 오류. 시작 인자(`copilot`의 `acp_options`): `--disable-builtin-mcps --no-ask-user --no-auto-update --no-custom-instructions --secret-env-vars=GH_TOKEN`, `--available-tools=view,glob,grep`(Deep) 또는 `--available-tools=ask_user`(Clean room, 이미 `--no-ask-user`로 꺼져 있어 도구가 없는 상태), `--allow-tool=<server>`는 질문에서 붙이지 않는다. 모델·context·effort는 선택 시 추가. | 코드 확인 · 미확인(Copilot CLI가 이를 지키는지) |
| R-59 | ACP 질문을 거절하는 어댑터 (Grok) | `answers_questions()`는 참이지만 `validate_access`가 `Question`·`CleanRoomQuestion`을 포함해 `Build`를 제외한 모든 접근에 `invalid` 오류("Grok Build reads and edits without asking, so a Clean room run, a deep chat, or a question can't hold it back.", remediation "Use a deep build. ...")를 준다. 질문은 `access_error`로 실패한다. 즉 문서(`question.rs` 머리 주석의 "any other agent is refused")와 달리 Grok은 어댑터 표에서 질문 가능으로 선언되지만 실제 실행에서 거절된다. | 코드 확인 |
| R-60 | API 키 AI의 질문 | `ReadOnlyHost`가 엔진 도구 중 `effects`가 `IDEMPOTENT ∪ MUTATES_SESSION ∪ CARRIES_TARGET_CONTENT` 안에 드는 것만 목록에 올리고(`Toolset::Core`, `Build`), 그 밖의 호출은 `ErrorCode::NoPermission` "<id> changes something, and this is only a question." + remediation "Answer from what you can read."로 거절한다. 동의가 필요한 도구는 목록에 없고 동의는 항상 거짓으로 넘긴다. 질문용 엔진은 별도 `Session`(호출자 설정 복제)이라 진행 중인 빌드의 엔진을 건드리지 않는다. | 코드 확인 |

- 불변식:
  - id는 항상 `[0-9a-z-]`이고 64바이트 이하이며 이 조건을 통과하지 못한 id로는 파일이 만들어지거나 읽히지 않는다(R-01).
  - 노트는 이름 변경 하나로 대기→읽힘이 되며 한 노트가 두 번 가져가지지 않는다(R-31). 철회는 대기 파일 삭제가 성공한 경우에만 성공한다(R-34).
  - 질문·승인에서 사람의 답이 없으면 에이전트는 오류가 아니라 성공 응답(`answered:false`/`behavior:deny`)과 계속하라는 문구를 받는다(R-12a, R-23). 예외는 인박스 자체가 없을 때의 질문(R-11)이다.
- 미결정:
  - 없음. (이전 U-1은 R-46~R-53과 C-10~C-13으로, U-2는 R-27로, U-3은 R-54~R-60으로 닫았다.)
- 확인 한계: 정적 읽기만 했고 실행·테스트하지 않았다. 폴링·원자적 이름 변경의 동시성 동작(Windows의 `rename_retrying` 포함)은 코드 구조로만 확인했다. Claude Code가 `additionalContext` 훅 출력을 모델에 실제로 전달하는 동작과 `--permission-prompt-tool` 규약은 외부 프로그램의 동작이라 이 레포의 가정만 확인했다(미확인).

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/engine/src/inbox.rs:21-77` `RequestKind`·`Request`·`Answer`·`as_text`, `:96-99` `valid_id` | 요청·답 JSON 필드, `serde` 기본값, 한 줄 텍스트 규칙, id 허용 집합 | R-01, R-02, R-04 |
| C-02 | `crates/ai/src/rebuild/notes.rs:114-141` `claim`·`hook_output` | 노트 가져가기(정렬·이름 변경·건너뛰기)와 훅 JSON·`additionalContext` 문구 | R-31, R-32 |
| C-03 | `crates/ai/src/cli_agents/adapters.rs:348-354` `notes_hook_settings` | PostToolUse 훅 설정 JSON(`matcher`, `timeout`, 명령 형식) | R-30 |
| C-04 | `crates/engine/src/tools/interaction_tools.rs:27-35` `DECIDE_ANSWER`·`WAIT`·`APPROVE_TOOL` | "스스로 결정" 응답 문구, 대기 30분, 승인 도구 id | R-10, R-12a |
| C-05 | `crates/engine/src/workspace.rs:1098-1106` `Questions`, `:1167-1193` `ACTION_KINDS`, `:1216-1237` `default_in`·`strictness`·`Manifest::approval` | 종류 7개의 이름·설명·Auto/수동 기본 승인, 엄격도 | R-19, R-20 |
| C-06 | `crates/engine/src/tools/interaction_tools.rs:150-236` `SAFE_COMMANDS`·`SERVER_COMMANDS`·`safe_command`·`never_exits`, `:321-348` `decide_command` | 안전·서버 명령 목록과 `&&` 분해·쉘 문자·`cd` 판정 | R-18 |
| C-07 | `crates/engine/src/tools/interaction_tools.rs:365-403` `decide`, `:469-497` `outcome`, `:629-639` `refusal` | 도구별 기본 정책, 정책→항상 허용→종류 선택→Auto 순서, 거절 문구 | R-16, R-17, R-20, R-21 |
| C-08 | `crates/engine/src/tools/interaction_tools.rs:875-909` `wait_for_approval`·`Remember` 처리 | 승인 카드 post, 답 해석, "항상" 기록 방식 | R-22, R-23 |
| C-09 | `crates/ai/src/rebuild/brief.rs:362-367` `added_prompt`, `:404-427` `just_asked` | 턴 종료 후 노트 메시지와 Just ask 문맥의 정확한 문구·상한 | R-35, R-45 |

| C-10 | `crates/engine/src/tools/interaction_tools.rs:700-754` `program_name`, `publishes_with`, `GH_LOCAL`, `GH_READS`, `gh_publishes` | 프로그램별 push/publish 판정표와 `gh` 읽기/쓰기 구분 | R-46 |
| C-11 | `crates/engine/src/tools/interaction_tools.rs:756-789` `SYSTEM_DIRS`·`SYSTEM_COMMANDS`·`DELETES` | 시스템 폴더·시스템 명령·삭제 명령 목록 | R-47, R-50 |
| C-12 | `crates/engine/src/tools/interaction_tools.rs:793-845` `deletes_outside`·`shell_words`, `:538-548` `mentions` | 삭제 범위 판정, 단어 나누기, 인박스 경로 언급 판정 | R-48, R-50, R-52 |
| C-13 | `crates/engine/src/workspace.rs:1019-1037` `OWN_NAMES`, `:1040-1081` `inside`·`real_path`·`really_inside`·`may_reach`, `:905-909` `is_own_record`, `crates/engine/src/tools/interaction_tools.rs:238-286` `resolve`·`resolve_as_opened` | 자기 기록 이름 목록과 경로 포함 판정 | R-51, R-53 |
| C-14 | `crates/ai/src/cli_agents/adapters.rs:356-392` `CHANGING_TOOLS`·`READING_TOOLS`·`question_args`, `adapters/copilot.rs:77-93` `acp_options`, `acp.rs:299-306, 515-525` | 질문 모드 CLI 인자와 ACP 질문 세션 제한 | R-55, R-58 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 원본 테스트는 `inbox.rs`·`notes.rs`·`interaction_tools.rs`에 같은 시나리오가 있으나 열지 않았다(사례명만 확인).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02, R-04, R-05, R-06 | 같은 폴더를 가리키는 인박스 두 핸들. 질문자가 `post(question, "Which colour?", choices=[Blue, Red], allow_text=true)`. 앱 핸들이 `pending()` 호출 후 `answer(id, {choice: Red, text: " darker "})` | 답 전: `pending()` 1건 `choices=[Blue,Red]`. 답 후: `pending()` 비어 있음. 질문자 `wait(2초)` → `Some`, `as_text()=="Red — darker"`. 인박스 폴더는 빈 상태. |
| T-02 | R-01, R-04, R-05 | `post(approval, "Run npm install", action="bash")` 뒤 답 없이 `wait(50ms)`. 이어 `answer("../escape")`, `answer("A")` | `wait`가 `None`, `pending()` 비어 있음(request 삭제). 두 `answer`는 오류. |
| T-03 | R-10 | 프로젝트 `questions=Decide`, 세션에 `InboxDir` 없음. `core_person_ask{question:"A?"}` | `{answered:false, note:<DECIDE_ANSWER>}` 성공. 인박스 파일 없음. |
| T-04 | R-11 | `Ask` 정책, `InboxDir` 없음 | `FeatureMissing` 오류. |
| T-05 | R-08 | `question:"   "` 또는 2001바이트 | `invalid` 오류. 2000바이트는 통과. 한글 700자(2100바이트)는 거절된다. |
| T-06 | R-09 | `choices` 8개, 각 130자 | 카드의 선택지 6개, 각 120자. |
| T-07 | R-13, R-14 | `core_person_ask`가 대기 중일 때 `project_inbox_answer{id, choice:"Blue"}`; 이어 같은 id로 다시 호출 | 첫 호출 `{answered:id, shown:"Blue"}`, 질문자 쪽 `answered:true`, `feed.json`에 `Ask{answer:"Blue"}`. 둘째 호출은 `NotFound`. |
| T-08 | R-23 | 승인 카드에 `allow` 없이 `text:"no"` 응답 | `behavior:"deny"`, message `The person said no: no. Find another way or ask them with core_person_ask.` |
| T-09 | R-23, R-21 | `Bash "curl x"`(Auto 꺼짐, 안전 목록에 없음)에 `allow:true, always:true` | 허용. `allowed_actions`에 `bash:curl` 추가. 같은 명령을 다시 호출하면 질문 없이 허용. |
| T-10 | R-18 | `Bash "npm run dev"` | 거절, 안내에 `npm run build`. |
| T-11 | R-17 | `Write file_path=<app>/src/a.rs` / `<project>/craft.json` / `/tmp/x` | 허용 / 질문(자기 기록) / 질문. |
| T-12 | R-20 | Auto 켜짐, 프로젝트 선택 없음, `Bash "git push"` | 질문 없이 거절(`Publish`), "Auto mode never allows pushing or publishing anything without the person." |
| T-13 | R-31, R-34 | 노트 id 2·10·3 대기. `rebuild_note_withdraw(3)`. 훅이 `claim` | 철회 성공. `claim`은 2→10 순서(숫자 순)로 텍스트 두 개. 이후 2·10은 읽힘이고 철회하면 `BadInput`. 다시 `claim`하면 빈 목록. |
| T-14 | R-32 | `hook_output([])` / `hook_output(["make it blue"])` | 없음 / `additionalContext`에 `- make it blue`와 `applies to the work from here on` 포함. |
| T-15 | R-36 | 노트 폴더에 `left` 있는 노트 id 10·2, 읽힘 3, `left` 없는 4, 공백 5, 깨진 6 | `take_left(wanted=true)`는 id 2, 10 순서로 두 노트의 원문만 돌려주고 폴더를 지운다. `wanted=false`면 빈 목록에 폴더 삭제. 읽을 수 없는 항목(디렉터리 `2.json` 등)이 있으면 폴더는 `notes-unread-*`로 이동. |
| T-16 | R-43, R-44 | `questions.json`에 `deep=true` 항목 "inside"(at 20), `deep=false` "outside"(at 30) | `untold(deep=true)` → [inside, outside], `untold(false)` → [outside]. Clean room으로 `outside`를 `mark_told`하면 `untold(false)`는 비고 `untold(true)`는 [inside]. 두 항목 모두 `load`에 남는다. |
| T-17 | R-42 | `questions.json`이 `"not json"`일 때 `mark_told` | 파일 내용 그대로 유지. 같은 상태에서 `add`는 파일을 새 항목 1개로 덮어쓴다. |
| T-18 | R-42 | 202개 추가 | 200개 유지, 첫 항목 `q2`. |
| T-19 | R-40 | 대화가 텍스트 조각 후 이벤트 없이 2초 넘게 쉬고 텍스트가 비었다 | `ProgramFailed` "The AI stopped without answering." |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

문서와 구현의 차이:
- 모듈 머리 주석(`inbox.rs:6-7`)은 "asker가 답을 읽으면 두 파일을 지운다"고만 하나 구현은 시간 초과·취소 때 request만 지운다(R-04, R-06).
- feature map(overview 행 10)은 `questions.rs`·`question.rs`를 "에이전트→사람 질문·승인" 계열로 묶었으나, 두 파일은 **사람→빌더 방향의 Just ask**이고 인박스 파일 프로토콜을 쓰지 않는다(`questions.json`을 쓴다). 이 스펙은 같은 행의 범위로 두되 갈래 C로 분리했다(보고에 경계 제안).
- `AskedQuestion.deep`의 기본값은 문서 주석대로 `true`이다.
- `question.rs:11`은 "다른 에이전트는 거절"이라 하나 Grok은 `answers_questions()`가 참인데 `validate_access`에서 질문이 거절된다(R-59).

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `inbox.rs:96-99` `valid_id`, `:110-115` `Inbox::path`, `:137-148` `pending`, `:158-160` `wait` | 코드 읽기. `wait`의 `.ok()?`가 오류 대신 `None`. |
| R-02 | `inbox.rs:84-94` `COUNTER`·`next_counter`, `:117-134` `Inbox::post` | 코드 읽기. |
| R-03 | `platform/src/fs.rs:54-90` `write_atomic`·`write_impl`, `engine/src/project.rs:217` re-export, `inbox.rs:132,153,197` | 코드 읽기. |
| R-04 | `inbox.rs:156-175` `Inbox::wait` | 코드 읽기. 파싱 실패 시 `if let ... && let` 조건이 거짓이라 삭제 없이 다음 분기로 가는 것은 코드 구조로 확인. |
| R-05 | `inbox.rs:137-148` `pending`(`answer.json` 존재 여부 필터) | 코드 읽기. |
| R-06 | `inbox.rs:150-154` `answer`, `project_tools.rs:587-596` | 코드 읽기. 짝 없는 answer의 정리 코드를 `inbox.rs`·`project_tools.rs`·`rebuild/mod.rs`의 인박스 사용처에서 찾지 못함(추론, 전체 검색은 하지 않음). |
| R-07 | `inbox.rs:178-231` `Activity`·`activity`·`clear_activity`, `rebuild/mod.rs:323` | 코드 읽기. 도구 쪽 호출처(Ghidra 대기)는 읽지 않음. |
| R-08 | `interaction_tools.rs:95-100` | 코드 읽기. `str::len`은 바이트. |
| R-09 | `interaction_tools.rs:101,111` | 코드 읽기. 뒤의 "카드가 앱에 노출"은 앱 쪽을 읽지 않은 추론. |
| R-10 | `interaction_tools.rs:104-106`, `settings.rs:318-327` `questions`·`questions_in`, `workspace.rs:1098-1106` | 코드 읽기. `project_questions_set`(`project_tools.rs:377-396`)이 프로젝트 값을 쓴다. |
| R-11 | `interaction_tools.rs:107-110` | 코드 읽기. |
| R-12a | `interaction_tools.rs:111-119` | 코드 읽기. 취소는 `cancel.is_cancelled()`를 `cancelled`로 넘김. |
| R-12 | `project_tools.rs:530-540` `open` | 코드 일부(앞쪽)만 읽음, 메시지 일부는 `rebuild/tools.rs`의 같은 모양과 대조. |
| R-13 | `project_tools.rs:587-596` | 코드 읽기. 테스트 `project_tools.rs:724-727`(두 번째 답)은 사례명만 확인. |
| R-14 | `project_tools.rs:587-612`, `feed.rs:227-234` `record_answer`, `:150-158` `answered` | 코드 읽기. |
| R-15 | `rebuild/feed.rs:163-175` `FeedLog::save` | 코드 읽기. |
| R-16 | `interaction_tools.rs:409-452` `approve`·`approve_with`, `:469-497` `outcome` | 코드 읽기. |
| R-17 | `interaction_tools.rs:365-403` `decide` | 코드 읽기. `opened_at`(`:354-361`)와 `workspace::really_inside`는 R-51에서 읽음. |
| R-18 | `interaction_tools.rs:150-236, 321-348` | 코드 읽기. `engine_build`·`own_program` 본문은 읽었으나 `shell_words`는 읽지 않음. |
| R-19 | `interaction_tools.rs:596-616` `kinds_of`, `:573-594` `kind_of`, `:655-700` `publishes`·`names_records`·`reaches_inbox` | 코드 읽기. 세부 규칙은 R-46~R-53. |
| R-20 | `workspace.rs:1167-1193, 1216-1237`, `interaction_tools.rs:629-639` | 코드 읽기. |
| R-21 | `interaction_tools.rs:481-497, 623-625` | 코드 읽기. |
| R-22 | `interaction_tools.rs:430-441, 875-887` | 코드 읽기. ACP 경로는 `rebuild/mod.rs:740-749`에서 `waiting`을 빈 클로저로 넘김. |
| R-23 | `interaction_tools.rs:427-451, 888-909`, `workspace.rs:859-865` `set_person` | 코드 읽기. |
| R-24 | `asset_tools.rs:35, 179-196` | 코드 읽기(해당 구간만). |
| R-25 | `rebuild/mod.rs:730-752` `approver` | 코드 읽기. `acp.rs`의 호출 쪽은 읽지 않음(그 결과 처리는 경계 밖). |
| R-26 | 호출처 검색: `grep never_unasked` 결과가 `interaction_tools.rs` 안의 정의·테스트뿐 | 검색으로 확인, 매크로·cfg 경유 호출은 확인 못 함. |
| R-27 | `engine/src/clean_room.rs:28-29, 45-80` | 해당 구간 읽음. `core_person_ask`·`core_action_approve`는 `:28-29`(메인 세션이 확인). |
| R-28 | `rebuild/tools.rs:492-506` `rebuild_note` | 코드 읽기. |
| R-29 | `rebuild/mod.rs:392-419` `add_note`, `:195-206` `note_with_just_asked`, `brief.rs:404-427` | 코드 읽기. |
| R-30 | `adapters.rs:348-354, 471-474`, `cli_agents/mod.rs:270-273`, `mod.rs` 테스트 `declared_notes_and_approvals_match_the_arguments`(어댑터 표 `mid_turn_notes`, ACP는 No) | Claude Code 인자 코드 확인. 다른 어댑터의 선언은 테스트 사례명으로만 확인. |
| R-31 | `notes.rs:114-128` `claim`, `:19-25` 경로 helper | 코드 읽기. `3.read.json`이 `parse::<u64>` 실패로 빠지는 것은 `strip_suffix(".json")` 결과가 `3.read`이기 때문(코드 확인). |
| R-32 | `notes.rs:130-141` `hook_output` | 코드 읽기. 훅 JSON을 Claude Code가 소비하는 방식은 미확인(외부). |
| R-33 | `rebuild/mod.rs:1409-1428` `relay_read_notes`, `:1395-1405` 루프 | 코드 읽기. |
| R-34 | `rebuild/mod.rs:424-435` `unsend`, `notes.rs:93-101`, `rebuild/tools.rs:508-518` | 코드 읽기. "삭제 실패이면서 읽힘도 아님"이 성공으로 처리되는 분기는 코드로 확인. |
| R-35 | `rebuild/mod.rs:699-727` `added`, `brief.rs:362-367` | `added`의 앞부분(699-727)만 읽음. |
| R-36 | `notes.rs:46-91` `left`·`take_left`, `rebuild/mod.rs:322-326, 1446-1458` | 코드 읽기. `left_notes_are_a_request`의 뒷부분(1458 이후)은 읽지 않음. |
| R-37 | `question.rs:23-31, 89-92` | 코드 읽기. |
| R-38 | `question.rs:1-14, 35, 63-75, 93-146, 261-283`, `adapters.rs:367-` `question_args`(앞부분만) | 코드 읽기. `question_args`·ACP 질문 모드는 R-54~R-60에서 읽음. |
| R-39 | `question.rs:157-170, 190-217` | 코드 읽기. |
| R-40 | `question.rs:221-259` `collect` | 코드 읽기. |
| R-41 | `question.rs:147-186`, `rebuild/tools.rs:299-328` `record_question_usage` | 코드 읽기. `claude_cost`의 계산은 읽지 않음. |
| R-42 | `questions.rs:58-106`, `rebuild/tools.rs:313-325` | 코드 읽기. |
| R-43 | `questions.rs:33-56` | 코드 읽기. |
| R-44 | `questions.rs:66-77`, `rebuild/mod.rs:1000-1008, 1419-1424` | 코드 읽기. |
| R-45 | `brief.rs:404-427` | 코드 읽기. |
| R-46 | `interaction_tools.rs:655-666` `publishes`, `:700-754` C-10 | 코드 읽기. 단어마다 프로그램 후보로 시도하는 점은 `words.iter().enumerate().any(...)`로 확인. |
| R-47 | `interaction_tools.rs:596-616` `kinds_of`, `:756-789` | 코드 읽기. |
| R-48 | `interaction_tools.rs:668-681` `names_records`, `:538-548` `mentions`, `tool.rs:213` `AGENT_ENV` | 코드 읽기. |
| R-49 | `interaction_tools.rs:683-698` `reaches_inbox`, `:238-246` `resolve` | 코드 읽기. |
| R-50 | `interaction_tools.rs:605-608` `kinds_of`, `:789-810` | 코드 읽기. `rm `이 `confirm `에 걸리는 것은 `contains` 부분 문자열 검사라는 구조에서 도출. |
| R-51 | `workspace.rs:1040-1081`, `interaction_tools.rs:238-286, 354-361` | 코드 읽기. |
| R-52 | `interaction_tools.rs:812-845` `shell_words` | 코드 읽기. 빈 따옴표가 빈 단어로 남는 것은 `started=true` 설정에서 도출. |
| R-53 | `workspace.rs:905-909`, `:1019-1037`, `:567`, `:593-598`, `feed.rs:14`, `pins.rs:34` | 코드 읽기. 이름 상수는 각 정의에서 값 확인. |
| R-54 | `cli_agents/mod.rs:343-348, 363-374` `Access`·`build_args`·`access_for`, `rebuild/question.rs:98-109, 121-129` | 코드 읽기. |
| R-55 | `adapters.rs:356-392, 417-425, 586-589`, `cli_agents/mod.rs:1010-1018` | 코드 읽기. 외부 CLI 플래그의 실제 효과는 미확인(레포 주석 "flags checked against claude --help"만 있음). |
| R-56 | `cli_agents/mod.rs:1007, 1019`, `:729` `AcpConversation::new`(`question`이면 `None` 전달) | 코드 읽기. |
| R-57 | `cli_agents/mod.rs:702-707, 1008-1018, 2284-2285`(테스트 사례 확인) | 코드 읽기. |
| R-58 | `acp.rs:299-306, 515-525, 775-781`, `adapters/copilot.rs:56, 77-93`, `cli_agents/mod.rs:714-723` | 코드 읽기. 테스트 `a_read_only_question_opens_a_fresh_session_without_mcp_and_refuses_permissions`(사례명만 확인). |
| R-59 | `adapters/grok.rs:59-61, 106-114`, `cli_agents/mod.rs:731` | 코드 읽기. 문서(`question.rs:11`)와 구현 차이는 위에 남김. |
| R-60 | `agent.rs:153-185` `ReadOnlyHost`, `question.rs:131-141` | 코드 읽기. |
| T-01~T-19 | 위 R-ID 근거에서 도출. 원본 테스트 대응(사례명만 확인): `question_round_trip_across_handles`, `timeout_withdraws_and_bad_ids_are_refused`, `a_note_changes_hands_once_and_can_be_taken_back_until_then`, `notes_nobody_took_are_left_for_the_next_run`, `a_run_takes_the_left_notes_and_starts_with_an_empty_folder`, `the_hook_hands_the_notes_to_the_model_as_context`, `a_clean_room_builder_is_told_only_what_was_asked_in_clean_room`, `marking_nothing_leaves_a_file_it_could_not_read`, `questions_are_kept_in_order_and_the_oldest_go_first` | T-05, T-06, T-09~T-12, T-19는 구현에서 도출한 사례로, 원본 테스트와의 일치는 확인하지 않았다. |

### 2.2 코드 읽는 순서
`inbox.rs`(프로토콜 전체, 284줄) → `interaction_tools.rs:27-120`(질문 도구) → `:409-497`(승인 흐름) → `:875-909`(카드·답 해석) → `project_tools.rs:587-612`(사람 쪽 응답) → `notes.rs`(전체, 훅·이름 변경 설계) → `rebuild/mod.rs:392-435, 699-727, 1409-1428`(노트의 실행 루프 쪽) → `adapters.rs:348-354, 471-474`(훅 배선) → `question.rs`·`questions.rs`(Just ask). 구현 전략: 프로세스 사이 통신을 소켓이 아닌 폴더 + 폴링 + 원자적 쓰기/이름 변경으로 하고, 승인 정책을 "안전 목록 → 항상 허용 기록 → 프로젝트 선택 → Auto 기본" 순으로 쌓는다.

### 2.3 비교·재사용 출처
다른 레포의 같은 기능 스펙 없음. 원본 코드를 복사하지 않았다(MIT OR Apache-2.0, overview 1절).

## 적용 메모

우리 절차: 사용자 결정 대기는 `handoff.md`, 범위 승인은 대화(AGENTS.md "항상", workflow 4장 1번). 이 레포의 인박스는 "에이전트가 돌아가는 동안 사람이 실시간으로 답하는" 구조라 전제가 다르다. 우리는 에이전트가 대화창에서 사람과 직접 말하고, 사람이 없으면 세션을 끝내고 `handoff.md`에 남긴다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-04, R-12a, R-10 | 질문 파일 프로토콜·폴링 대기는 채택하지 않는다(필요성 낮음). | 우리 에이전트는 사람과 같은 대화 세션 안에 있어 프로세스 간 중계가 없다. 사람이 자리에 없는 경우는 `handoff.md`가 같은 역할(결정 대기 항목 보관)을 한다. | 변경 없음. |
| R-12a(`answered:false` + "추정을 밝히고 계속") | 참고할 만하다: 답이 없을 때 막히지 않고 "가정을 적고 계속"하게 하는 문구. 우리 `handoff.md` 항목에는 "응답 전까지 이렇게 가정하고 진행했다"를 적는 칸이 규칙에 없다. | 사용자 결정을 기다리는 동안 에이전트가 다른 작업을 계속할 때, 가정이 문서에 남지 않으면 나중에 결정이 달라졌을 때 어느 문서를 고칠지 추적하기 어렵다. 이 레포는 가정을 다음 메시지에 `I decided:`로 적게 해 사람이 볼 수 있게 한다(R-10). | `handoff.md` 항목에 "임시 가정"과 "이 가정에 기대어 쓴 문서" 칸을 두는 안을 검토(우리 쪽 규칙 변경 후보, 미결정). |
| R-16~R-21 | 승인 정책(허용/질문/거절 3단계, 종류별 기본, "항상 허용" 기억)은 채택하지 않는다(필요성 낮음). | 우리 작업은 코드를 읽고 문서를 쓰는 것이라 위험 행동 종류가 적고, 권한은 Claude Code 자체 권한 설정이 맡는다. 단 "서브에이전트에 맡길 때 공용 파일을 못 고치게 한다"(workflow 4장 1번)는 지금 지시문의 문장 규칙이라, 원본처럼 도구 수준에서 `is_own_record`로 막는 방식과 비교할 수 있다(참고만). | 변경 없음. |
| R-31~R-34 | 중간 노트(훅으로 다음 도구 호출 직후 주입, 이름 변경으로 한 번만 전달, 가져가기 전 철회)는 지금은 불필요하다. 다만 병렬 서브에이전트 실행 중 사용자의 추가 지시를 전달하는 경로가 생기면 "한 번만 전달·전달 전 철회" 규칙은 그대로 참고할 수 있다. | 우리 서브에이전트는 시작 시 지시문(request 템플릿)으로 받고 도중 추가 입력 경로가 없다. 사용자가 실행 중에 지시를 바꾸고 싶을 때는 취소 후 재지시가 현재 방식이다. | 변경 없음. |
| R-36 | 참고: 앱이 닫혀도 대기 노트가 유실되지 않게 사람의 원문을 파일에 같이 남긴다. 우리의 `handoff.md`·`next.md`가 세션 사이 이월을 맡는 것과 같은 목적이다. | 이월 대상을 "사람이 한 말 원문"으로 못 박은 점이 다르다. 우리 handoff 항목은 요약이라 사용자의 원래 표현이 사라질 수 있다. | 항목에 사용자 원문을 한 줄 인용하는 규칙을 검토(미결정). |
| R-42~R-45 | Just ask(작업과 분리된 질문, 답을 기록하되 빌더에는 "지시가 아닌 배경"으로 한 번만 전달)는 우리의 "레포에 대한 질문"(3장)과 비슷하다. 차이: 우리는 질문과 답을 `reports/<repo>/questions/`에 문서로 남기고 이후 스펙 트리거를 확인하지만, 후속 작업자(다른 세션)에 "배경일 뿐 지시가 아님"을 표시해 주지는 않는다. | 질문 문서를 다른 세션이 읽을 때 그 답을 요구사항으로 오해할 수 있다는 점은 확인되지 않은 우려라 낮은 우선순위로 둔다. | 변경 없음(관찰만). |
