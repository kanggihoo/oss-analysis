---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-15
updated: 2026-11-15
sources:
  - crates/ai/src/rebuild/mod.rs
  - crates/ai/src/rebuild/study.rs
  - crates/ai/src/rebuild/self_check.rs
  - crates/ai/src/rebuild/kept_check.rs
  - crates/ai/src/rebuild/runs.rs
  - crates/ai/src/rebuild/activity.rs
  - crates/ai/src/rebuild/feed.rs
  - crates/ai/src/rebuild/tools.rs
  - crates/ai/src/rebuild/kinds/mod.rs
  - crates/ai/src/rebuild/kinds/runs.rs
  - crates/ai/src/rebuild/stall_tests.rs
  - crates/ai/src/rebuild/tests.rs
  - crates/ai/src/lib.rs
  - crates/ai/src/failure.rs
  - crates/engine/src/workspace.rs
  - crates/engine/src/workspace/progress.rs
  - crates/engine/src/settings.rs
  - crates/evidence/src/error.rs
  - apps/craft-anything-cli/src/rebuild_cmd.rs
  - crates/ui-egui/src/project.rs
  - docs/pitfalls.md
depends:
  - ./check-contract.md
  - ./builder-brief.md
  - ./person-inbox.md
status: ready
---

# 리빌드 루프 (Study → Build → Check → Refine)

> 프로젝트 폴더(요청·대상·이전 기록)와 실행 옵션을 받아, 필요하면 대상을 조사하고, 빌더 에이전트에게 턴을 시키고, 턴이 끝날 때마다 검사 라운드를 돌려 고칠 대상이 남으면 그 결과를 다음 턴 메시지로 되돌리는 일을 정해진 멈춤 조건(라운드 수, 연속 실패, 연속 무변경)까지 반복하고, 마지막 상태(Ready·NeedsYou·Stopped)와 종료 이벤트를 남기는 기능.

<!-- 용어
- 실행(run): `RebuildRun::start` 한 번. 워커 스레드 하나가 `Worker::run`을 처음부터 끝까지 돈다. 사람이 "Try again"을 누르거나 새 요청을 보내면 새 실행이 시작된다.
- 턴(turn): 빌더 에이전트에게 메시지 하나를 보내고 그 턴이 끝날 때까지(`AgentEvent::TurnDone`) 기다리는 단위.
- 라운드(round): 검사 목록을 한 번 도는 단위(check-contract). 실제 라운드 번호는 프로젝트 기록에서 이어지고, 빌더가 `rebuild_check`로 요청한 검사는 0번 라운드다.
- 재다듬기(refinement): 검사 결과 하나를 다음 턴 메시지로 되돌린 횟수. 실행마다 0부터 센다.
- 진행 지문(fingerprint): `app/` 파일 이름·내용의 해시. 턴 전후 지문이 같으면 "바꾼 게 없는 턴"이다.
- Try again: 메시지 없이(`message = None`) 새 실행을 시작하는 것. 앱 버튼, CLI `--continue-in <dir> --resume`, 도구 `rebuild_start{project, resume:true}`가 여기에 해당한다(`resume`이면 `continuing=true`도 켠다).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 호출자(앱·CLI·`rebuild_start` 도구)가 `RunOptions`를 채워 `RebuildRun::start`를 부르거나 `RunSet::start`로 대기열에 넣는다. `start`는 빌더 백엔드를 고르고 실패하면 스레드를 만들기 전에 오류를 돌려준다. 성공하면 워커 스레드를 띄우고 바로 돌아온다(R-01~R-04).
2. 워커는 첫 턴 전에 시작 조건을 확인한다: 진행 기록 읽기, 에이전트 도구·로그인, 종류·스택·편집기·빌드 프로그램, 연속 실패 상한. 하나라도 걸리면 턴 없이 끝난다(R-06, R-09).
3. 조사가 필요하면(이 모드의 조사 결과가 없거나, 이어 갈 대화가 없는 새 실행) 대상을 조사해 `capture/`를 만든다. 아니면 조사한 프로그램만 다시 연다(R-07). 첫 턴 메시지는 builder-brief R-17이 고른다.
4. 반복: 턴 전에 진행 지문을 재고, 바꾼 게 없는 턴이 2번 쌓였으면 멈춘다 → 턴 → 턴 뒤 지문 기록 → 사람이 그사이 추가한 노트가 있으면 검사 없이 노트로 다음 턴 → 아니면 라운드 번호를 올려 검사(재사용 또는 한 번 재시도 포함) → 결과를 `craft.json`에 붙이고 연속 실패 수를 갱신 → 고칠 대상이 있으면 재다듬기 메시지로 다음 턴(R-11~R-21).
5. 고칠 대상이 없거나 재다듬기 수가 `max_rounds`에 닿으면 반복을 끝낸다. 마지막 검사 결과가 `passed`면 Ready와 요약, 아니면 "아직 작동하지 않음" 오류로 끝난다(R-22).
6. 어떤 경로로 끝나든 워커는 결과를 상태(Ready / Stopped / NeedsYou)로 저장하고 `RunEvent::Finished`를 마지막으로 낸다(R-04, R-05).

빌더가 턴 도중 `rebuild_check`를 부르면, 4번의 턴을 기다리는 폴링 안에서 같은 검사를 0번 라운드로 돌려 보고서를 돌려준다. 이 결과는 프로젝트 기록에도, 연속 실패 수에도 들어가지 않는다(R-24, R-25).

### 1.2 범위·통합 지점

- 제공: 실행 시작·대기열·중지, 시작 전 확인, 조사 여부 결정과 조사 단계의 실패 정책, 턴-검사 반복의 순서와 멈춤 조건(재다듬기 상한, 연속 실패 10, 연속 무변경 2), 검사 결과 재사용과 검사 오류 한 번 재시도, 턴 재시도 정책, 실행 간에 이어지는 카운트, 종료 상태와 이벤트, 빌더 자체 검사(0번 라운드)의 요청·응답 경로, 도구 `rebuild_start`·`rebuild_status`·`rebuild_stop`·`rebuild_check`, CLI `rebuild`의 입출력.
- 제외:
  - 검사 목록 구성·검사 순서·각 검사의 판정, `CheckResult::good`, `kinds::can_refine`, `TargetKind::refine` 문구, 0번 라운드 보고서(`self_check::report`) 문구: [check-contract](./check-contract.md). 이 스펙은 루프가 그것을 언제 부르고 결과를 어디로 보내는지만 쓴다.
  - 턴 메시지의 내용(첫 브리프, `follow_up`, `continue_prompt`, `resumed_elsewhere`, 노트 메시지, `DECOMPILE_FIRST`, `NO_PROJECT_PROMPT` 이외의 재다듬기 문구, `CHECK_BEFORE_REPLYING`): [builder-brief](./builder-brief.md) R-17~R-21. 이 스펙은 "어느 시점에 어느 종류의 메시지로 바꾸는가"만 쓴다.
  - 질문·승인 카드, 노트 파일의 대기·가져감·철회, Just ask: [person-inbox](./person-inbox.md). 루프는 `inbox.pending()`을 `RunEvent::Ask`로 내보내고(person-inbox R-05), 노트를 턴 중(`relay_read_notes`, person-inbox R-33)과 턴 뒤(`added`, R-35)에 거둔다. 이 스펙은 노트가 루프의 카운트와 순서에 미치는 영향만 쓴다(R-15, R-19).
  - 코딩 에이전트 구동(feature map 13행)과 내장 API 에이전트 루프(14행). 아래 "에이전트 경계"로만 정의한다.
  - 조사 단계 안의 개별 도구(`web_site_capture`, `core_target_triage`, Ghidra 분석, 콘솔 실행 기록 등)의 동작. 어떤 실패가 실행을 멈추고 어떤 실패가 노트에만 남는지만 쓴다(R-07).
  - 세션 보존(`keep_session`·`restore_session`, Claude Code의 Deep 세션 재사용 거부), 사용량 기록(`usage.json`), 자산 키 로딩: 루프가 부르는 부수 작업이고 실패해도 루프 흐름을 바꾸지 않는다(상태 줄만 남김). 예외는 R-06의 Deep 세션 재사용 거부(시작 전 오류)다.
- 외부 의존·선행 계약:
  - **에이전트 경계(`Conversation`)**: `send(text)`/`retry(text)`로 턴을 시작하고, `poll()`로 `AgentEvent`를 비차단으로 꺼낸다. 턴은 `TurnDone` 이벤트로 끝난다. 그 전에 `Error{message, remediation, log}`가 올 수 있다. `stop()`은 턴을 멈추게 하며, 루프는 멈춘 뒤에도 `TurnDone`이 올 때까지 계속 `poll()`한다(종료 이벤트를 내는 것은 에이전트 쪽 책임). `session_id()`(이어 갈 세션), `session_lost()`(이어 가려던 세션이 이 컴퓨터에 없음), `last_failure()`(`TurnFailure`, `retryable`·`retry_after_secs`), `answer_consent(call_id, allow)`. 루프가 읽는 이벤트: `TextDelta`(답 텍스트 누적), `ToolStarted`/`ToolFinished`, `ConsentNeeded`, `Error`, `TurnDone{input_tokens, output_tokens, tokens_unknown, cost_usd, ...}`, `Status`, `Output`.
  - check-contract: `Worker::run_checks(ws, kind, round)`(제한 없음), `run_checks_within(.., Some(SELF_CHECK_LIMIT))`(0번 라운드, 30분), `CheckResult::good(bar)`, `kinds::can_refine(kind.checks(ws), result)`, `TargetKind::refine(check, sees_pictures)`, `self_check::report`·`summary`.
  - builder-brief: 턴 메시지를 만드는 함수들(`brief`, `follow_up`, `continue_prompt`, `resumed_elsewhere`, `added_prompt`, `pictures_reminder`, `just_asked`)과 `API_BUILDER`·`BLIND_BUILDER`·`CHECK_BEFORE_REPLYING`·`DECOMPILE_FIRST`.
  - person-inbox: `Inbox::post`/`wait`/`pending`/`answer`(0번 라운드 요청도 같은 파일 프로토콜을 `checks/asks/` 폴더에서 쓴다), 노트 함수(`take_left`, `hand_over`, `was_read`, `forget`, `take_back`).
  - 엔진 도구 호출 `Engine::call(tool, params, opts)`(조사·재오픈에 씀, 정상이면 `ToolOutput`, 실패면 `ToolError`), 취소 토큰 `CancelToken`(`check()`가 취소면 `ErrorCode::Cancelled` 오류).
  - 프로젝트 저장소 `Workspace`(feature map 17행, 스펙 범위 밖): `open`, `save`, `set_status(status, note)`(상태·한 줄 메모·`updated_ms`를 쓰고 저장), `manifest`의 필드(1.3), `app_dir()`·`capture_dir()`·`inbox_dir()`·`investigation_dir()`.
  - 미해결 질문 원장(unknown-ledger, 경계만): Ready 요약은 조사 폴더의 unknown 중 `status != resolved`인 개수를 센다(`self_check::open_questions`).
- 소유 상태·부작용(1.3 "저장되는 상태" 표): `craft.json`의 `status`·`note`·`checks`·`not_working_checks`·`awaiting_check`·`last_reply`·`stack`·`capture_deep`·`decompiled`·세션 필드, `inbox/build-progress.json`, `checks/asks/`, `feed.json`, `build-activity.log`, `capture/`(조사), `app/` 폴더 생성. 실행 중 컴퓨터 절전을 막고(`keep_awake`) 끝나면 푼다. 0번 라운드 응답을 위해 "이 프로세스에서 빌드 중" 표시(`BUILDING_HERE`)를 실행 동안 둔다.

### 1.3 인터페이스와 데이터 의미

**`RunOptions` (실행 하나의 옵션)**

| 필드 | 타입·기본값 | 의미·제약 |
|---|---|---|
| `backend` | optional string · None | 빌더 백엔드 이름. None이면 프로젝트가 저장한 빌더(켜져 있을 때) → Builder 역할 → 첫 에이전트 앱 → 켜진 아무 백엔드 순(`builder_backend`). 이름을 줬는데 없거나 꺼져 있으면 오류이고 대체하지 않는다 |
| `message` | optional string · None | 후속 요청. 있으면 조사를 건너뛸 수 있고(R-07) 연속 실패 수를 0으로 한다(R-09). None이면 Try again |
| `shown`, `shown_pictures` | optional string, list<path> | 대화(`feed.json`)에 사람 메시지로 넣을 표시 문구와 그림. None이면 넣지 않는다 |
| `continuing` | bool · false | "멈춘 곳에서 이어 하기". 메시지 없는 실행은 이 값과 무관하게 이어 하기로 판정될 수 있다(`is_carrying_on`) |
| `max_rounds` | u32 · 6 | 첫 검사 뒤 재다듬기 상한(실행마다 0부터) |
| `good_enough` | float · 90.0 | `CheckResult::good`의 기준(%) |
| `beginner` | bool · true | 에이전트 구동에 넘김(범위 밖) |
| `kinds` | `KindRegistry` · `built_in()` | 판별할 종류 목록(check-contract) |
| `adapters` | 에이전트 어댑터 목록 | 범위 밖 |
| `wake` | 콜백 · 없음 | 이벤트마다 부른다(창 다시 그리기) |
| `clean_room` | optional bool · None | 세션이 바쁠 때 쓸 모드. 모드 결정 순서: 세션을 바로 잡을 수 있으면 세션의 `clean_room()` → 이 값 → 저장된 설정의 `deep_mode` 반대 |

호출자별 값(R-02): 앱 = 설정 `build.max_rounds`(기본 6)·`build.good_enough`(기본 90). CLI = `--rounds`(기본 2)·설정 `build.good_enough`. 도구 `rebuild_start` = `rounds`(기본 2)·`good_enough`는 `RunOptions` 기본 90(설정을 읽지 않음).

**`RunEvent` (실행이 내는 이벤트, 순서대로)**

| 변형 | 필드 | 의미 |
|---|---|---|
| `Step` | `step: Study\|Build\|Check\|Done`, `text` | 단계 시작과 평문 한 줄. 상태를 바꾸는 `step()`가 낸다 |
| `Agent` | `AgentEvent` | 에이전트 이벤트를 그대로 전달. 루프가 엔진 도구를 부를 때도 `ToolStarted`/`ToolFinished`(call_id `run-<tool>`)를, 부수 알림은 `Status`를 낸다 |
| `Note` | `shown`, `pictures` | 빌더가 읽은 사람 노트 |
| `Ask` | `Request` | 사람을 기다리는 질문·승인(같은 id는 실행당 한 번) |
| `Checked` | `CheckResult` | 실제 라운드의 검사 결과 하나(0번 라운드는 내지 않음) |
| `Preview` | url | 미리보기 주소(검사가 서버를 띄웠을 때, 정상 종료 직전) |
| `Finished` | `ok`, `message`, `paused` | 마지막 이벤트. `paused=true`는 사람이 멈춘 것이며 실패가 아니다 |

**`RebuildRun` (실행 핸들)**: `poll()`(쌓인 이벤트를 모두 꺼냄, 비차단), `stop()`(취소 토큰을 켬. drop도 같음), `is_running()`(워커가 `Finished`를 낸 뒤 false), `answer`/`answer_as`(카드에 답, person-inbox), `add_note`/`unsend`/`waiting`/`queued`/`take_notes`(person-inbox), `feed_now()`(현재 대화. 아직 꺼내지 않은 이벤트는 대기열에서 버린다), `started()`, `quiet_for()`(마지막 이벤트 이후 경과), `activity_now()`/`activity_lines(range)`/`activity_len()`/`activity_log()`, `preview_url()`.

**`RunSet` (여러 실행)**: `new(limit)`(최소 1), `start(hub, ws, opts)` → `Started::Running | Queued{position}`(1이 다음), `poll(hub)` → `(폴더, RunEvent)` 목록, `stop(root)` → `Stopped::Stopping | Unqueued | Nothing`, `stop_all()`, `is_running`, `position`, `is_busy`, `active`, `waiting`, `busy`, `set_limit`, `get`/`get_mut`(끝난 실행도 보관). `keep_queue_moving(set, engine, settings_path, every)`: 대기열이 비지 않았으면 백그라운드 스레드가 `every`마다 `poll`한다.

**저장되는 상태**

| 위치 | 필드 | 루프가 쓰는 의미 |
|---|---|---|
| `craft.json` | `status`, `note` | `Status`: `New`·`Inspecting`(조사)·`Building`(턴·노트·자체 검사)·`Checking`(라운드)·`NeedsYou`(오류)·`Ready`·`Stopped`(멈춤) |
| `craft.json` | `checks: list<CheckResult>` | 실제 라운드 결과를 덧붙인다. 다음 실행의 라운드 번호 = 이 목록의 최대 `round` |
| `craft.json` | `not_working_checks: u32` | 실행을 넘어 이어지는 "모든 검사가 `passed`가 아닌 라운드"의 연속 수. 비어 있으면(0) 쓰지 않는다 |
| `craft.json` | `awaiting_check: bool` | 빌더 턴은 끝났고 그 턴의 검사가 아직 보고되지 않음. 다음 Try again은 검사만 한다 |
| `craft.json` | `last_reply` | 빌더의 마지막 비어 있지 않은 답(공백 제거) |
| `craft.json` | `capture_deep` | 현재 `capture/`를 만든 모드. 조사를 시작할 때 None으로 지우고 끝나면 채운다 |
| `inbox/build-progress.json` | `version`(2), `fingerprint`, `unchanged_turns`, `checked{key, round}` | 진행 지문·연속 무변경 턴 수·재사용할 검사 라운드. 16 KiB 상한, `deny_unknown_fields` |
| `checks/asks/` | `<id>.request.json`, `<id>.answer.json`, `<id>.taken` | 0번 라운드 요청·응답·"가져감" 표시 |
| `feed.json`, `build-activity.log` | 대화 항목, 활동 줄 | 이벤트 기록(R-27) |

**도구**

| 도구 | 입력 | 출력·오류 |
|---|---|---|
| `rebuild_start` | `request`(필수), `target`(새 프로젝트: URL·절대 경로·`-`, 기본 `-`), `project`(기존 폴더), `resume`(project와 함께: 이어 하기, `request` 무시), `projects_dir`/`project_folder`(둘 중 하나), `existing`(`edit`\|`start_from`), `build_with`·`generate_assets`(새 프로젝트만), `backend`, `rounds`(기본 2), `pictures`(절대 경로) | `{project, started:true}` 또는 `{project, started:false, queued:n}`, 저장 빌더가 대체됐으면 `builder_notice`. 이미 빌드 중·대기 중이면 `BadInput` "This project is already building." |
| `rebuild_status` | `project` | `{project, running, queued, status, status_label, note, last_check, waiting}` |
| `rebuild_stop` | `project` | `{stopping}` / `{unqueued}`, 없으면 `BadInput` |
| `rebuild_check` | `project`(기본: 도구 서버의 인박스 부모 폴더), `wait_minutes`(1..=60, 기본 35) | `{project, report}`. 오류는 R-25 |

CLI `craft-anything-cli rebuild <target> <request>`: `--projects-dir`, `--project-folder`, `--existing edit|start-from`, `--continue-in <dir>`, `--resume`(`--continue-in` 필요), `--backend`, `--rounds`(기본 2), `--unattended`, `--build-with`, `--generate-assets`. 출력: `[Study|Build|Check|Done] <text>`, 빌더 텍스트, `  · <도구 설명>`, `  ! <오류>`, `  + <노트>`, `[Check N] <s>% alike — <note>` 또는 `[Check N] <note>`, `Preview: <url>`, 끝 줄 `Done. <msg>` / `<msg>`(멈춤) / `Stopped: <msg>`. 종료 코드: `Finished.ok`면 0, 그 밖 1. `--unattended`면 질문은 첫 선택지(선택지 없으면 "No preference; use your best judgement."), 승인은 거절. Ctrl-C는 `run.stop()`.

### 1.4 행동 규칙과 남은 질문

**실행 시작·대기열·끝**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `RebuildRun::start(hub, ws, opts)` | 프로젝트를 디스크에서 다시 연다(실패하면 받은 사본). 다음이 실패하면 스레드 없이 `Err`를 돌려준다: 빌더 백엔드 선택, API 백엔드 빌더 시작, 추출기 시작(새 조사·Deep·API 추출기일 때만), 스레드 생성. 그 뒤 앞 실행이 남긴 노트를 가져오고(`take_left`, 남은 노트가 있으면 연속 무변경·연속 실패 수를 0으로, R-09), 활동 파일을 지우고, `shown`이 있으면 대화에 넣고, 워커 스레드를 띄우고, 남은 노트를 `add_note`로 다시 건다. 실제 작업은 모두 워커에서 한다 | 코드 확인 |
| R-02 | 호출자별 `max_rounds`·`good_enough` | 1.3의 표와 같다. 같은 프로젝트도 앱에서는 재다듬기 6번·설정의 기준, CLI·도구에서는 2번이고, 도구는 설정의 `good_enough`를 무시하고 90을 쓴다 | 코드 확인 |
| R-03 | `RunSet::start` | 같은 폴더가 실행 중이거나 대기 중이면 `BadInput` 거절. "혼자 일해야 함"(빌더가 API 백엔드, 또는 새 조사이고 추출기가 API 백엔드)을 계산한다. 대기열이 비었고 자리가 있으면(실행 중 수 < limit, 혼자여야 하면 실행 중 0, 혼자 일하는 실행이 돌고 있지 않음) 바로 시작한다. 아니면 빌더 백엔드를 먼저 확인해(없으면 오류, 대기열에 넣지 않음) 뒤에 넣는다. 대기열을 앞지르는 실행은 없다 | 코드 확인 |
| R-04 | `RunSet::poll` | 모든 실행의 이벤트를 폴더와 함께 모은 뒤, 맨 앞 대기 실행부터 자리가 있는 동안 시작한다. 시작 직전에 프로젝트를 다시 읽고 "혼자" 여부를 다시 계산한다(자리가 없어졌으면 맨 앞으로 되돌리고 멈춤). 시작이 실패하면 `NeedsYou` 상태와 `Finished{ok:false, message: e.for_people(), paused:false}`를 그 폴더 이벤트로 낸다 | 코드 확인 |
| R-05 | 워커 종료(`run_outcome`) | `Ok(summary)` → (`ok=true`, summary). `Err(Cancelled)` → 상태 `Stopped`·메모 "Paused. Send a message to continue.", (`ok=false`, "Paused.", `paused=true`). 그 밖 `Err(e)` → 상태 `NeedsYou`·메모 `e.for_people()`(메시지 + 끝에 마침표가 없으면 "." + 공백 + 해결 안내), (`ok=false`, 같은 문구). 패닉 → `NeedsYou`, "The workflow hit a bug and stopped safely. Your files are untouched.". 상태 저장 실패는 무시한다. 그 뒤 사용량을 기록하고 절전 방지를 풀고 `Finished`를 내고 `is_running`을 false로 한다(순서 그대로) | 코드 확인 |
| R-06 | 멈춤(`stop()` 또는 핸들 drop) | 취소 토큰을 켠다. 워커는 다음 지점에서 `Cancelled`로 빠져나온다: 모든 `step()` 시작, 루프의 엔진 도구 호출, 진행 지문 스캔, 검사 시작마다(check-contract R-09), 턴 재시도 대기(1초 간격), 조사의 Ghidra 대기(30초 간격). 턴 중이면 폴링마다 `agent.stop()`을 부르고 `TurnDone`을 받은 뒤 `Cancelled`를 낸다. 결과는 R-05의 멈춤이다. 0번 라운드 검사 도중이면 요청에 `STOPPED_ANSWER`를 먼저 답한다 | 코드 확인 · 에이전트가 `stop()` 뒤 `TurnDone`을 반드시 낸다는 것은 경계 가정 |

**첫 턴 전**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | 시작 확인 순서 | ① `build-progress.json` 읽기(깨졌거나 더 새 버전이면 오류: R-23). 재사용 검사를 복원(R-17). ② `message`가 공백 아닌 문자가 있으면 연속 무변경 수를 0으로 저장. ③ 에이전트 앱이면 도구 서버·프로그램·로그인 확인(원격이면 원격 도구 서버 확인). 로그인이 안 됐으면 `BadSettings`. ④ 조사 폴더·인박스를 세션에 붙이고 `app/`을 만든다. ⑤ 스택이 비었으면 정해 저장하고 종류를 판별한다. 없으면 `BadSettings` "No kind of project matches this request.". ⑥ 게임 엔진 스택의 편집기가 준비 안 됐으면 `BadSettings`. ⑦ 원격이 아니고 `app/`에 도구체인 프로젝트가 아직 없으면 스택의 빌드 프로그램이 이 컴퓨터에 있어야 한다(없으면 `BadSettings`). ⑧ 조사 또는 재오픈(R-08). ⑨ 다른 에이전트가 저장한 세션은 버린다. Clean room에서 Claude Code의 저장 인자가 Deep 세션을 이어 가려 하면 `BadSettings`. ⑩ `Step::Build` "Getting the builder ready…". ⑪ 첫 메시지 선택(builder-brief R-17). ⑫ 라운드 번호와 연속 실패 상한(R-09). 어느 단계든 오류면 턴 없이 끝난다 | 코드 확인 |
| R-08 | 조사 여부(`starts_with_study`) | 조사한다 ⇔ 이 모드의 `capture/`가 없음(`capture/`가 없거나 `capture_deep != 현재 모드`) 또는 (이 모드로 이어 갈 대화가 없고 (`message`가 None이거나 다른 모드의 대화가 있음)). 조사하지 않으면 Deep·`Local` 대상의 프로그램이 아직 열려 있지 않을 때 `core_target_open`으로 다시 연다(실패는 `Step` 줄만, 취소는 오류). 원격 에이전트 빌더면 다시 열지 않는다 | 코드 확인 |
| R-09 | 조사 단계의 실패 정책 | 시작할 때 `capture_deep=None`을 저장하고 Clean room이면 Deep 전용 파일을 지운다. 끝나면 `capture_deep=모드`를 저장한다. 실행을 멈추는 실패: 취소, 파일 쓰기 오류, 웹사이트 대상의 시작 페이지 `web_site_open`·`web_site_capture` 오류. 노트·`Step` 줄에만 남고 계속하는 실패: 열린 상태 캡처, 다른 페이지 캡처(빠진 페이지는 목록에서 뺌), Deep의 JS 분석·관찰·트래픽 기록, 트리아지, Ghidra 분석, 콘솔 실행 기록의 개별 입력, 창 촬영. 조사가 중간에 실패하면 `capture_deep`이 None으로 남아 다음 실행이 다시 조사한다. 추출(Deep·게임·`Local`·API 추출기)은 실패해도 계속하되 취소는 오류 | 코드 확인 |
| R-10 | 라운드 번호와 연속 실패 상한(실행 시작) | `round` = `craft.json` `checks`의 최대 `round`(없으면 0). `message`가 `Some`(공백뿐이어도)이면 `not_working_checks`를 0으로 저장한다. `None`이고 `not_working_checks ≥ 10`(`NOT_WORKING_CHECK_LIMIT`)이면 턴도 검사도 없이 `OverLimit` "The build still isn't working after N checks in a row, so it stopped." (해결 안내: 구체적인 수정을 담은 새 요청)로 끝난다. 앞 실행이 남긴 노트를 가져온 실행은 시작 때 이미 0이다(R-01) | 코드 확인 |
| R-11 | 검사만 하는 재개(`only_check`) | 이어 하기이고 조사하지 않았고 `message`가 None이고 `awaiting_check`이면, 반복의 첫 차례는 턴 전 지문 확인(R-12)과 턴을 건너뛰고 바로 검사로 간다. 빌더에게 메시지를 보내지 않는다 | 코드 확인 |

**반복 한 차례**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | 턴 전 | 진행 기록을 다시 읽고 지문을 잰다(R-23). `before_turn(지문)` 뒤 `stalled()`면 `OverLimit` "The build stopped after two builder turns changed no files in <place>."로 끝난다(`app/`이 비었으면 "<place> has no files yet, so the builder hasn't written the project."를 붙이고 해결 안내가 "app/에 프로젝트 파일을 요청하는 새 요청, 또는 다른 빌더"로 바뀜). 아니면 저장하고 `Step::Build` 문구를 낸다: 라운드 0이고 이어 하기 아님 "Building the first version…", 라운드 0이고 이어 하기 "Carrying on with the build…", 그 밖 "Improving the build…". `awaiting_check=false`(메모리) | 코드 확인 |
| R-13 | 턴(`turn_with_wait`) | 보낸 턴이 오류이고 `session_lost()`이면 저장된 세션을 지우고, 대체 메시지(`fresh`)가 아직 있으면 한 번 그 메시지로 새로 시작한다("The builder's earlier conversation isn't on this computer…"). 오류가 `ProgramFailed`이고 세션 분실이 아니고 `last_failure().retryable`이고 재시도가 3번 미만이면 기다린 뒤 `retry`로 이어 간다: 제공자가 준 `retry_after_secs`(없으면 메시지에서 읽은 대기)가 있으면 그 초+1(최대 15분), 없으면 30×시도 횟수 초. 대기는 1초마다 취소를 본다. 그 밖의 오류는 그대로 돌려준다. 성공·실패와 무관하게 에이전트가 알려 준 세션 id를 모드와 함께 저장한다 | 코드 확인 |
| R-14 | 턴 안의 폴링(120ms) | 이벤트를 전달하고(세션 분실로 생긴 `Error`는 전달하지 않음), `ConsentNeeded`는 Build 툴셋 도구만 허용, 의사코드 도구(`native_function::PSEUDOCODE_TOOL`, 정식 id로 비교)가 시작되면 `decompiled=true`(메모리, 다음 저장 때 씀), `TurnDone`이면 사용량을 기록하고 읽힌 노트를 거두고 취소를 본 뒤, 턴 중 `Error`가 있었으면 `ProgramFailed`(그 메시지·안내), 없으면 누적 텍스트를 답으로 돌려준다. `TurnDone` 전에는 매 폴링마다 인박스 대기 요청을 `Ask`로(id당 한 번), 읽힌 노트를 `Note`로, 도구의 대기 줄을 `Step`으로 내고, 0번 라운드 요청에 답하고(R-24), 60초마다 사용량을 기록한다 | 코드 확인 |
| R-15 | 턴 실패 | 에이전트를 멈추고 버린다. 이 턴 중 훅으로 읽힌 노트가 있었으면 연속 무변경 수 0을 저장한다(실패하면 `Status` 줄만, 원래 오류 유지). 원래 오류로 실행이 끝난다(R-05). 이 턴에 붙여 보낸 Just ask는 "전함"으로 표시하지 않는다. `awaiting_check`는 이전 저장값 그대로다 | 코드 확인 |
| R-16 | 턴 성공 뒤 | 붙여 보낸 Just ask를 "전함"으로 표시(실패는 로그). 답이 비어 있지 않으면 `last_reply`. 게임 엔진 스택이 아니면 `app/`에서 실제 쓰인 스택으로 `stack`을 바꾼다. `awaiting_check=true`를 저장한다. 훅으로 읽힌 노트가 있었으면 무변경 수를 0으로 저장한 뒤, 지문을 재서 `after_turn`을 저장한다 | 코드 확인 |
| R-17 | 턴 뒤 남은 노트·디컴파일 독촉 | 턴 뒤 아직 가져가지 않은 노트가 있으면(빈 노트 제외) 무변경 수를 0으로 저장하고, `not_working_checks=0`(메모리, 다음 저장 때 씀), 노트 메시지(builder-brief R-19)를 다음 메시지로 하고 **검사 없이** 다음 턴으로 간다. 노트가 없고, 이 실행에서 아직 독촉하지 않았고, Deep·`Local` 대상이고 `decompiled=false`이면 `DECOMPILE_FIRST`로 **검사 없이** 다음 턴(실행당 한 번). 두 경우 모두 재다듬기 수를 쓰지 않는다 | 코드 확인 |

**검사 라운드와 재다듬기**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | 라운드 실행 | `round += 1`. `Step::Check`(`Status::Checking`), 문구는 대상이 없으면 "Checking the build…", 있으면 "Checking the build against the original…". 결과 = R-19(재사용) 또는 R-20(재시도 포함 실행). 오류면 실행이 그 오류로 끝난다. 결과를 `checks`에 덧붙이고, `awaiting_check=false`, `not_working_checks` = (모든 결과가 `passed`면 0, 아니면 +1(포화)), 저장. 그다음 재사용 표시(`checked`)를 진행 기록에 저장하고, 결과마다 `Checked` 이벤트를 낸다 | 코드 확인 |
| R-19 | 검사 결과 재사용(`checks_unless_unchanged`) | 검사 입력 지문 = `app/` 내용 지문 + `reference/`·`capture/`의 이름·크기·종류·수정 시각 + (프로젝트 폴더 경로, 종류 id, 스택, `clean_room=<bool>`, 적용되는 플러그인 검사 id들). 보관된 라운드가 있고 지문이 같으면 검사를 돌리지 않고 보관 결과의 `round`만 이번 번호로 바꿔 돌려주고 `Status` "Nothing the check looks at has changed since it last worked, so its results stand."를 낸다. 아니면 검사를 돌리고, 결과가 비지 않았고 모두 `passed`면 검사 **뒤** 지문과 함께 보관, 아니면 보관을 지운다. 지문을 못 재면 다시 검사한다. 보관은 0번 라운드와 실제 라운드가 함께 쓴다. 다음 실행은 진행 기록의 `checked`가 `craft.json`의 마지막 라운드와 같고 그 라운드가 모두 `passed`일 때만 보관을 복원한다. 판정 기준은 `passed`이며 `good`이 아니다 | 코드 확인 |
| R-20 | 검사 오류 한 번 재시도(`checks_with_a_retry_now`) | `run_checks`가 `Cancelled`가 아닌 오류면 `Status` "The check couldn't finish (<msg>). Trying it once more…"를 내고 한 번 더 돌린다. 두 번째도 `Cancelled`가 아닌 오류면 같은 오류 코드로 "The build is finished, but it couldn't be checked: <msg>", 해결 안내 "Press Try again to check it again. Nothing needs building again."로 실행이 끝난다. 이때 결과는 `checks`에 들어가지 않고 `not_working_checks`도 바뀌지 않으며 `awaiting_check=true`가 남아 다음 Try again은 R-11로 검사만 한다 | 코드 확인 |
| R-21 | 검사 뒤 노트 | R-18 뒤 가져가지 않은 노트가 있으면 R-17과 같이 처리하고 재다듬기 없이 노트 메시지로 다음 턴 | 코드 확인 |
| R-22 | 고칠 대상 고르기와 정체 재확인 | 고칠 대상 = 이번 라운드 결과 중 `!good(opts.good_enough) && can_refine(kind.checks(ws), c)`인 **첫** 결과(check-contract R-16 (a)). 고칠 대상이 있고 지문 스캔이 가능하고 이미 `stalled()`면 지문을 다시 재서 `before_turn` 후 저장하고, 여전히 `stalled()`면 R-12의 무변경 오류로 끝난다(검사만 하는 재개 중 사람이 직접 고친 경우를 잡기 위함) | 코드 확인 |
| R-23 | 반복 종료 판단(순서대로) | ① 고칠 대상이 없으면 반복 종료. ② `not_working_checks ≥ 10`이면 R-10의 `OverLimit`으로 끝남. ③ `refinements ≥ max_rounds`면 반복 종료. ④ `refinements += 1`, 다음 메시지 = `app/`이 비었으면 `NO_PROJECT_PROMPT`, 아니면 `kind.refine(check, sees_pictures)`, 그 뒤 `pictures_reminder`, API 루프가 아니면 `CHECK_BEFORE_REPLYING` | 코드 확인 |
| R-24 | 반복 종료 뒤 최종 판정 | 미리보기 서버가 있으면 `Preview(url)`. `last` = `craft.json` `checks`의 마지막 결과. `last`가 없거나 `passed=false`면 `ProgramFailed` "The build isn't working yet. <last.note>"(해결 안내 "Ask for a fix in the box below, or press Try again.")로 끝난다. 아니면 마지막 라운드(같은 `round`인 결과 모두)로 `self_check::summary`를 만들어 "Ready: <요약>."(결과가 없으면 "Ready."), 열린 unknown이 1개면 " 1 question about the original is still open.", n개면 " n questions about the original are still open."을 붙이고, `Status::Ready`와 그 문구를 저장하고, `Step::Done`을 낸 뒤 그 문구로 성공한다. 즉 `good`이 아니어도 `passed`면 Ready다 | 코드 확인 |
| R-25 | 이번 라운드 결과가 빈 목록 | 검사 목록이 비면(내장 종류에는 없음) "모두 `passed`"로 쳐서 `not_working_checks=0`, 고칠 대상 없음 → 종료. 최종 판정의 `last`는 이전 라운드의 마지막 결과이거나 없음(없으면 "isn't working yet") | 코드 확인 |

**정체(연속 무변경) 판정**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-26 | 진행 지문(`AppFingerprintCache::scan`) | `app/`(사람 프로젝트 제자리 편집이면 프로젝트 폴더) 아래 파일 이름·내용의 SHA-256. `.git`, 제자리 편집일 때 루트의 Craft Anything 기록 파일(`OWN_NAMES`), 빌드 캐시 폴더(`node_modules`, `target`, `.godot`, `Library`, `Temp`, `.venv`, `__pycache__`, `.next`, `.turbo`, 관리 프로젝트 옆의 `obj`)를 뺀다. 링크는 따라가지 않고 링크로 기록한다. 100,000개·깊이 64를 넘으면 오류. 시각이 아닌 내용으로 비교하므로 같은 바이트를 다시 쓴 것은 변화가 아니다 | 코드 확인 |
| R-27 | `before_turn`·`after_turn`·`stalled` | `before_turn(f)`: 저장된 지문과 다르면 `unchanged_turns=0`, 지문을 f로. `after_turn(f)`: 저장된 지문과 같으면 +1, 다르면 0, 지문을 f로. `stalled()` ⇔ `unchanged_turns ≥ 2`(`UNCHANGED_TURN_LIMIT`). 턴만 센다(검사·대화 기록은 세지 않음). 턴 사이·프로젝트를 닫은 동안의 편집도 `before_turn`에서 진행으로 친다 | 코드 확인 |
| R-28 | 무변경 수를 0으로 하는 것 | 공백 아닌 `message`(R-07 ②), 앞 실행이 남긴 노트(R-01), 턴 중 훅으로 읽힌 노트(R-15·R-16), 턴·검사 뒤 노트(R-17·R-21). Try again·빈 메시지는 0으로 하지 않는다. 앱 재시작·멈춘 실행 재개도 저장된 수를 유지한다 | 코드 확인 |
| R-29 | 지문 스캔 실패 | 취소면 오류. 그 밖 오류면 이 실행에서 스캔을 끄고(`progress_available=false`), 기록을 무효화(`fingerprint=None`, 수 0)해 저장하고, `Status` "Build progress couldn't be checked (<msg>). Continuing without the unchanged-turn limit for this run."를 낸다. 이후 이 실행은 무변경 검사 없이 진행한다 | 코드 확인 |
| R-30 | `build-progress.json` 읽기·쓰기 | 없으면 기본값. 16 KiB 초과 → `OverLimit`. JSON이 아니거나 모르는 필드·잘못된 버전 → `BadInput` "… something else changed it …"와 "파일 이름을 바꾸거나 지우고 다시 하라" 안내. 버전 > 2 → `NotSupported`("더 새 Craft Anything"). 쓰기 전에 디스크의 기록을 다시 읽어 위 오류면 쓰지 않는다. 원자적으로 쓴다 | 코드 확인 |

**빌더 자체 검사(0번 라운드)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-31 | 실행이 0번 라운드 요청에 답한다(`answer_self_checks`, 턴 폴링마다) | 종류가 정해진 뒤부터만 답한다. `checks/asks/`의 대기 요청마다 `<id>.taken` 표시를 쓰고(실패는 로그), `Step::Build`("The builder is checking its work…" / "… against the original…") 뒤 R-19 재사용을 거쳐 `run_checks_within(.., 0, Some(30분))`. 성공 → 답 = `self_check::report(결과, good_enough, 열린 unknown, can_refine)`, `Step` "The builder checked its work: <summary>.". 취소 → 답 `STOPPED_ANSWER`를 쓰고 `Cancelled`로 턴을 끝냄. 그 밖 오류 → 답 "The check couldn't run: <msg>", `Step` "The builder's check couldn't run.". 답 쓰기가 실패하면 그 오류로 턴이 실패한다(R-15). 결과는 `checks`·`not_working_checks`·`Checked` 이벤트 어디에도 들어가지 않는다 | 코드 확인 |
| R-32 | 도구 `rebuild_check` | `wait_minutes`가 1..=60 밖이면 `BadInput`. 프로젝트가 이 프로세스에서 빌드 중(`building_here`, 즉 API 루프 빌더)이면 `FeatureMissing` "This builder can't check its own work while it builds.". 아니면 `checks/asks/`에 질문 요청을 올리고 `wait_minutes`분 기다린다. 답이 오면 `{project, report}`. 호출이 취소되면 `Cancelled` "Stopped.". 시간이 다 됐는데 `.taken`이 있었으면 `TimedOut`("가져갔지만 안 끝남, 다시 묻지 말고 턴을 끝내라"), 없었으면 `NotFound`("실행 중인 빌드가 없다"). `.taken`은 기다림 뒤 도구가 지운다 | 코드 확인 |

**기록·표면**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-33 | 이벤트 하나를 낼 때(`emit_event`) | 대화 잠금 안에서 ① 활동 기록에 넣고(줄을 `build-activity.log`에 덧붙임, 비밀 가림, 600자) ② 대화 항목으로 접고 ③ 대화를 저장(2초에 한 번, `Finished`면 즉시, 저장 전에 디스크에서 다른 곳이 쓴 답을 합침) ④ 채널로 보내고, 잠금을 푼 뒤 `wake`. 그래서 `feed_now`와 `poll`이 같은 이벤트를 두 번 보지 않는다. `Finished`가 멈춤이면 대화에 `Paused`, 실패이고 직전 항목이 오류가 아니면 오류 항목을 넣고, 진행 중이던 체크리스트 단계를 `Stopped`로 바꾼다 | 코드 확인 |
| R-34 | "Try again" 사이에 이어지는 것과 새로 시작하는 것 | 이어짐: 라운드 번호(`checks` 최대값), `not_working_checks`, `unchanged_turns`와 지문, `awaiting_check`, 보관 검사(R-19), `decompiled`, 이어 갈 세션. 실행마다 새로: `refinements`(0), 디컴파일 독촉 여부, 지문 스캔 가능 여부. 따라서 빌드는 되지만 기준에 못 미치는 프로젝트는 Try again마다 최대 `max_rounds`번의 재다듬기를 더 받고, 이를 막는 것은 빌더가 파일을 바꾸지 않을 때의 무변경 상한뿐이다 | 코드 확인 |

- 불변식:
  - 워커가 시작된 실행은 `Finished`를 정확히 한 번, 마지막으로 낸다(패닉 포함). 그 뒤 `is_running()`이 false가 된다(R-05).
  - 실제 라운드의 결과는 `craft.json`에 저장된 뒤에 `Checked`로 나가고, 그 뒤에야 재다듬기 메시지가 만들어진다(R-18).
  - `not_working_checks`는 실제 라운드만 센다. 0번 라운드, 검사 오류로 끝난 라운드, 재사용으로 판정한 라운드 중 앞의 둘은 세지 않는다(재사용은 결과가 모두 `passed`인 라운드만 해당하므로 0이 된다).
  - 한 실행에서 재다듬기 메시지로 보낸 턴은 `max_rounds`를 넘지 않는다. 노트·디컴파일 독촉으로 생긴 턴은 이 수에 들지 않는다.
  - Ready로 끝난 실행의 마지막 결과는 `passed=true`다(R-24). `good`은 보장하지 않는다.
- 미결정: 없음.
- 확인 한계:
  - 실행·빌드·테스트를 하지 않았다. 테스트 본문은 T-ID에 표시한 사례만 열었다.
  - 에이전트가 `stop()` 뒤 반드시 `TurnDone`을 내는지는 13·14행 구현 소관이라 확인하지 않았다. 내지 않으면 멈춤이 끝나지 않는다(이 레포의 `docs/pitfalls.md` "An early error without a terminal event"·"A turn's own process outlived its answer"가 같은 요구를 말한다).
  - 빌드 산출물 중 R-26 제외 목록에 없는 폴더(`dist/`, Unity `Build/` 등)는 진행 지문에 들어간다. 검사 라운드의 빌드가 그 폴더를 다른 바이트로 다시 쓰면 다음 `before_turn`에서 무변경 수가 0이 된다(추론: 빌드 산출물이 실행마다 같은 바이트인지는 도구체인에 달려 있고 실행해 보지 않았다).

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/ai/src/rebuild/mod.rs:76-174` `RunEvent`·`Wake`·`RunOptions`·`Default` | 이벤트 변형과 옵션 기본값 | 1.3, R-02 |
| C-02 | `crates/ai/src/rebuild/mod.rs:208-247` `KeptHistory`·`is_carrying_on`·`capture_in_mode`·`run_deep_mode`·`starts_with_study` | 이어 하기·조사 여부·모드 결정 식 | R-08, R-11 |
| C-03 | `crates/ai/src/rebuild/mod.rs:269-382` `RebuildRun::start`, `:446-517` `poll`·`stop`·`Drop` | 시작 순서·동기 실패·스레드 끝 처리 | R-01, R-05, R-06 |
| C-04 | `crates/ai/src/rebuild/mod.rs:800-944` `Worker::run` 앞부분 | 시작 확인 순서(메시지 선택 876-944는 builder-brief C-11) | R-07 |
| C-05 | `crates/ai/src/rebuild/mod.rs:945-1122` `Worker::run` 반복·종료 | 라운드 번호, 상한, `only_check`, 반복 본문, 종료 판정 순서, 최종 판정 | R-10~R-12, R-16~R-25 |
| C-06 | `crates/ai/src/rebuild/mod.rs:1124-1163` `progress_after_notes`·`progress_fingerprint` | 노트 뒤 무변경 수 초기화, 스캔 실패 처리 | R-16, R-29 |
| C-07 | `crates/ai/src/rebuild/mod.rs:1189-1209` `checks_with_a_retry`·`checks_with_a_retry_now` | 검사 오류 한 번 재시도와 오류 문구 | R-20 |
| C-08 | `crates/ai/src/rebuild/mod.rs:1244-1322` `turn`·`remember_session`·`turn_with_wait`, `crates/ai/src/failure.rs:28` `MAX_RETRY_WAIT` | 턴 재시도 조건·대기 시간·세션 분실 처리 | R-13 |
| C-09 | `crates/ai/src/rebuild/mod.rs:1330-1437` `converse_turn`·`relay_read_notes`·`relay_inbox` | 턴 폴링 순서, 이벤트 전달 예외, 오류 판정 | R-06, R-14 |
| C-10 | `crates/ai/src/rebuild/mod.rs:1440-1462` `left_notes_are_a_request`, `:1488-1552` `run_outcome`·`NOT_WORKING_CHECK_LIMIT`·`not_working`·`NO_PROJECT_PROMPT`·`no_build_progress`·`app_is_empty`·`no_files_yet` | 종료 매핑, 상한 상수, 멈춤 오류 문구 | R-05, R-10, R-12, R-23 |
| C-11 | `crates/engine/src/workspace/progress.rs:16-142` `UNCHANGED_TURN_LIMIT`·`BuildProgress`·`CheckedBuild`·`load`·`save`·`before_turn`·`after_turn`·`stalled`·`not_ours`, `:163-231` `check_fingerprint`·`stamp_tree`, `:282-397` `scan`·`fingerprint_tree`, `crates/engine/src/workspace.rs:36-58` `REBUILT`·`rebuilt` | 진행 기록 형식·검증, 지문 계산과 제외 목록 | R-19, R-26~R-30 |
| C-12 | `crates/ai/src/rebuild/kept_check.rs:1-80` `KeptChecks`·`all_worked`·`checks_unless_unchanged` | 검사 재사용 조건과 지문 입력 | R-19 |
| C-13 | `crates/ai/src/rebuild/self_check.rs:8-57` `SELF_CHECK_ROUND`·`SELF_CHECK_LIMIT`·`asks_dir`·`STOPPED_ANSWER`·`taken_mark`·`BuildingHere`·`building_here`, `:59-93` `open_questions`·`summary`, `:147-193` `answer_self_checks` | 0번 라운드 요청 처리, Ready 요약 | R-24, R-31 |
| C-14 | `crates/ai/src/rebuild/tools.rs:15-197` `specs`·`StartParams`·`CheckParams`·`d_wait_minutes`, `:365-578` `rebuild_start`·`rebuild_status`·`rebuild_stop`·`rebuild_check`·`unanswered` | 도구 입력 스키마·기본값·오류 | R-02, R-32, 1.3 |
| C-15 | `crates/ai/src/rebuild/runs.rs:11-260` `Started`·`Stopped`·`RunSet`·`must_work_alone`·`keep_queue_moving` | 동시 실행·대기열 규칙 | R-03, R-04 |
| C-16 | `crates/ai/src/rebuild/study.rs:14-28` `program_to_reopen`·`tools_run_remotely`, `:37-317` `reopen_target`·`study`·`how_it_works`·`study_from_outside`·`picture_window`·`capture_routes`·`capture_pages`, `crates/ai/src/rebuild/kinds/runs.rs:121-150` `capture_runs`, `crates/ai/src/rebuild/mod.rs:1170-1187` `extract` | 조사 단계별 치명/비치명 실패 | R-08, R-09 |
| C-17 | `crates/ai/src/rebuild/mod.rs:571-578` `emit_event`, `crates/ai/src/rebuild/feed.rs:9-95` `apply`, `:117-175` `FeedLog`, `crates/ai/src/rebuild/activity.rs:155-240` `Activity::record`·`lines_for` | 이벤트 기록 순서, 대화 항목 변환, 활동 줄 | R-33 |
| C-18 | `apps/craft-anything-cli/src/rebuild_cmd.rs:17-62` `RebuildArgs`, `:99-248` `run`, `:257-305` `auto_answer`·`prompt_answer` | CLI 옵션·출력·종료 코드 | 1.3 |
| C-19 | `crates/engine/src/workspace.rs:196-232` `Status`·`Step`, `:393-476` `Manifest`(`checks`·`awaiting_check`·`not_working_checks`·`decompiled`·`capture_deep`·`last_reply`), `:880-885` `set_status`, `crates/engine/src/settings.rs:144-166` `BuildSettings`, `crates/evidence/src/error.rs:154-159` `for_people` | 저장 필드 의미, 설정 기본값, 사람용 오류 문구 | 1.3, R-05 |
| C-20 | `crates/ai/src/lib.rs:306-390` `AgentEvent`·`Conversation` | 에이전트 경계의 이벤트·메서드 | 1.2, R-13, R-14 |

### 1.6 수락 사례

출처: 사례별 표기("구현" = 구현에서 도출, "테스트" = 원본 테스트 열람). 테스트 사례는 원본에서 API 루프 대역 모델·대역 검사 종류로 에이전트와 검사를 대체했으므로 실제 에이전트·실제 검사는 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-12, R-27 | 빌더가 매 턴 파일을 하나도 쓰지 않고, 검사는 항상 고칠 대상을 낸다(`app/` 폴더가 있음/없음 둘 다) | 빌더 요청 3번 이하에서 무변경 오류로 끝남, 메시지에 "has no files yet" | 테스트(`stall_tests.rs` `an_idle_builder_with_an_empty_app_stops_after_two_turns`) |
| T-02 | R-12, R-23 | T-01과 같고 `app/`이 빔 | 두 번째 메시지에 "app/ has no files"와 "exact command you ran", "Fix this in app/"는 없음. 해결 안내에 "asks for the project's files" | 테스트(`an_empty_app_is_said_to_have_no_project`) |
| T-03 | R-10, R-34 | 빌더는 매 턴 새 파일을 쓰지만 검사는 항상 `passed=false`. 새 요청 1번 + Try again 5번 | 전체 `checks` ≤ 10, `not_working_checks = 10`. 그다음 Try again은 턴·검사 없이 "in a row" 오류. 새 요청을 보내면 다시 검사가 돈다 | 테스트(`try_again_does_not_restart_a_build_that_never_works`) |
| T-04 | R-11, R-20 | `awaiting_check=true`로 저장된 프로젝트에 Try again | 빌더에게 메시지 0번, 조사 없음, 검사 1라운드, 끝나면 `awaiting_check=false` | 테스트(`try_again_after_a_check_that_could_not_run_only_checks`) |
| T-05 | R-20 | 검사가 한 번 오류 / 두 번 연속 오류 | 한 번: 성공으로 끝남. 두 번: 실패, 대화에 "The build is finished, but it couldn't be checked", `awaiting_check=true` 유지, 다음 Try again은 빌더 요청 없이 성공 | 테스트(`a_check_that_could_not_run_gets_a_second_go_and_the_build_is_not_blamed`) |
| T-06 | R-27, R-28, R-34 | 검사가 계속 실패하고 빌더가 아무것도 바꾸지 않음 → Try again | 첫 실행: 빌더 요청 2번 후 "two builder turns" 오류. 다시 연 프로젝트에서 Try again: 빌더 요청 없이 실패 | 테스트(`unchanged_builder_turns_stop_after_two_and_stay_stopped_when_reopened`) |
| T-07 | R-28 | T-06 상태에서 ① 사람이 `app/index.html`을 직접 바꿈 → Try again ② 공백 아닌 새 요청 ③ 메시지 `"   "` | ① 빌더 요청 2번 더 ② 2번 더 ③ 요청 없음(빈 메시지는 저장된 수를 지우지 못함) | 테스트(`a_real_edit_or_nonempty_new_request_starts_another_attempt`) |
| T-08 | R-22, R-27 | 첫 검사만 실패하고 두 번째 검사는 통과, 빌더는 파일을 안 바꿈 | 성공. 빌더 요청 2번, 저장된 `unchanged_turns = 2`(무변경이어도 통과한 검사로 끝날 수 있음) | 테스트(`a_successful_check_can_finish_the_second_unchanged_turn`) |
| T-09 | R-11, R-22 | `awaiting_check=true`, `unchanged_turns=2`, 지문 같음, 검사 통과 | 성공, 빌더 요청 0번 | 테스트(`a_saved_check_only_run_is_not_blocked_by_the_progress_limit`) |
| T-10 | R-27 | `max_rounds=0`, 검사 항상 실패, 빌더 무변경, 3번 연속 실행 | 빌더 요청 누계 1, 2, 2 | 테스트(`single_turn_runs_share_the_same_unchanged_turn_limit`) |
| T-11 | R-23, R-24 | `max_rounds=2`, 빌더는 매번 파일을 바꾸고 검사는 `passed=true`, `similarity=80`, 기준 90 | 라운드 3번(첫 검사 + 재다듬기 2번) 뒤 반복 종료, `Ready: about 80% like the original.`, 상태 Ready, `ok=true` | 구현 |
| T-12 | R-23, R-24 | `max_rounds=1`, 매 라운드 `build`가 `passed=false`, 빌더는 파일을 바꿈 | 라운드 2번, `not_working_checks` +2, `ProgramFailed` "The build isn't working yet. Build failed: …", 상태 NeedsYou | 구현 |
| T-13 | R-17, R-23 | 첫 턴 직후 사람이 노트 1개를 남김(훅 없음) | 검사 없이 노트 메시지로 두 번째 턴, 그 뒤 첫 검사(라운드 번호 1). 재다듬기 수 0 | 구현 |
| T-14 | R-06, R-05 | 턴 중 `stop()` | 에이전트에 `stop()`, `TurnDone` 수신 후 실행 종료, 상태 Stopped "Paused. Send a message to continue.", `Finished{ok:false, message:"Paused.", paused:true}` | 구현 |
| T-15 | R-03, R-04 | `RunSet::new(2)`, A·B 시작, C 시작, A 끝남 후 `poll` | A·B `Running`, C `Queued{1}`, C 재시작 시도는 거절, `poll`이 A의 `Finished`를 내고 C 시작. 대기 중 A는 `stop` → `Unqueued`, 실행 중 B는 `Stopping`, 다시 A는 `Nothing` | 테스트(`runs.rs` `runs_past_the_limit_wait_and_start_in_order`) |
| T-16 | R-04 | 대기 중 실행의 시작이 실패(빌더 없음) | 그 폴더로 `Finished{ok:false, message:"No coding agent.", paused:false}`, 프로젝트 상태 NeedsYou | 테스트(`a_queued_run_that_cannot_start_says_why`) |
| T-17 | R-32 | 실행이 없는 프로젝트에 `rebuild_check{wait_minutes:1}` | 1분 뒤 `NotFound` "No build is running for this project: nothing took the check in 1 minutes." | 구현 |
| T-18 | R-31 | 0번 라운드 결과가 모두 `passed`, 이어서 빌더가 파일을 바꾸지 않고 턴 종료 | 실제 라운드는 검사를 돌리지 않고 0번 결과를 라운드 N으로 바꿔 씀, `Status` "Nothing the check looks at has changed…" | 구현 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-03, `mod.rs:322-326` `take_left`·`left_notes_are_a_request` | 전문 읽음. **원본 결함 후보**: 남은 노트 폴더는 `take_left`가 스레드 생성(`:353-373`, 실패 시 `?`) **전에** 지우므로, 스레드 생성이 실패하면 가져온 노트는 다시 걸리지 않고 사라진다(`:378-380`는 성공 뒤에만 실행). 카운트 초기화도 이미 저장된 뒤다. 스레드 생성 실패는 드물다 |
| R-02 | C-01, C-14 `StartParams.rounds`·`rebuild_start` `:432-441`, C-18 `:161-172`, `crates/ui-egui/src/project.rs:173-174`, C-19 `BuildSettings` | **문서와 구현 차이**: overview 7행은 "기본 `max_rounds` 6"이라 했으나 6은 `RunOptions`·앱 설정 기본값이고 CLI `--rounds`·도구 `rounds`는 2다. `BuildSettings.max_rounds` 주석은 "the CLI's `--rounds` sets its own"만 말하고 도구도 따로 2를 쓴다는 것은 없다. 도구 경로는 `good_enough`를 `..RunOptions::default()`로 채워 설정값을 쓰지 않는다(앱·CLI는 설정을 읽음) |
| R-03, R-04 | C-15 | 전문 읽음. 테스트 T-15·T-16 열람 |
| R-05 | C-03 `:361-372`, C-10 `run_outcome`, C-19 `for_people` | |
| R-06 | C-03 `stop`·`Drop`, `mod.rs:653-670` `step`·`call`, C-09 `:1344-1346`·`:1381`, C-08 `:1245-1251`, C-16 `study.rs:119-125`, C-13 `:176-183` | 취소 관찰 지점은 루프 쪽 코드만 확인. 에이전트의 종료 이벤트 보장은 1.4 확인 한계 |
| R-07 | C-04 | 전문 읽음. 도구 서버·로그인 확인(`check_builder_tools`·`signed_in`)과 `refuse_deep_session_reuse_in_clean_room`(`mod.rs:604-626`)은 오류가 나는 조건만 읽음 |
| R-08 | C-02, C-16 `reopen_target` | |
| R-09 | C-16 | `study` 본문과 `how_it_works`·`capture_pages`·`capture_runs`의 오류 분기만 읽었다. `prepare_ghidra`·`inventory`·`locate` 내부는 읽지 않음(실패가 노트로만 간다는 것은 호출부 `match`로 확인) |
| R-10 | C-05 `:945-955`, C-10 | **문서와 구현 차이**: 주석 `:946`과 `Manifest.not_working_checks` 문서는 "새 요청(a new request)이 수를 다시 시작한다"고 하지만 구현 조건은 `opts.message.is_some()`이라 공백뿐인 메시지도 `not_working_checks`를 0으로 만든다. 같은 실행에서 무변경 수는 공백 아닌 메시지일 때만 0이 되고(`:815`), 테스트 `a_real_edit_or_nonempty_new_request_starts_another_attempt`가 "an empty message cannot erase the saved count"를 확인한다. 두 카운트의 초기화 조건이 다르다. CLI·도구 모두 빈 `request`를 막지 않으므로 공백 메시지로 연속 실패 상한을 지울 수 있다(추론: 앱 입력창이 빈 메시지를 보내는지는 확인 안 함) |
| R-11 | C-05 `:959-961` | T-04·T-09 열람 |
| R-12 | C-05 `:961-976`, C-10 `no_build_progress` | |
| R-13 | C-08 | `TurnFailure::retryable`의 판정과 `failure::retry_after` 문자열 파싱은 읽지 않음(13·14행 경계). 테스트 사례명 `transient_failures_retry_without_requiring_an_external_session`, `setup_errors_do_not_retry_even_with_a_wait_in_the_message`, `a_local_self_check_write_error_is_not_retried_as_a_backend_rate_limit`, `an_untyped_opencode_exit_keeps_its_error_and_the_three_retry_cap` 확인(본문 미열람) |
| R-14 | C-09 | |
| R-15, R-16 | C-05 `:977-1029`, C-06 | `docs/pitfalls.md` "A deferred request reset lost on failure"와 구현이 맞음 |
| R-17, R-21 | C-05 `:1030-1043`·`:1061-1068`, `mod.rs:699-728` `added`, `:527-532` `needs_decompile_reminder` | 테스트 사례명 `new_notes_during_a_turn_or_check_get_their_own_attempt_but_empty_notes_do_not` 확인(본문 미열람) |
| R-18 | C-05 `:1045-1060` | |
| R-19, T-18 | C-12, C-11 `check_fingerprint`, `kinds/mod.rs` `plugin_ids` | 모듈 주석(`kept_check.rs:1-5`)과 구현이 맞다. 테스트 사례명 `a_check_that_worked_stands_while_nothing_it_looks_at_changes` 확인(본문 미열람) |
| R-20, T-05 | C-07 | T-05 테스트 열람. `docs/pitfalls.md` "A retry that took 'no message' for 'brand new'"와 맞음 |
| R-22 | C-05 `:1069-1081` | T-08·T-09로 의도 확인. 테스트 `a_failed_check_only_resume_detects_manual_edits_before_refusing_more_build_turns`는 앞부분만 열람 |
| R-23, R-24, R-25 | C-05 `:1082-1121`, C-13 `summary`·`open_questions` | R-25는 코드 구조로 도출(빈 목록의 `all`은 참) |
| R-26~R-30 | C-11 | `progress.rs` 앞 260줄과 `scan`·`fingerprint_tree`의 제외 분기 읽음. 해시 세부(`special_type`, 실행 비트 반영)는 C-ID로 넘김 |
| R-31 | C-13 | T-18은 R-19와 공유 보관(`kept_checks`)을 같은 `Worker`가 쓰는 것으로 도출 |
| R-32 | C-14 `rebuild_check`·`unanswered` | 테스트 사례명 `the_builder_asks_the_running_build_for_a_check_and_gets_its_report`, `a_check_still_going_is_told_apart_from_no_build` 확인(본문 미열람) |
| R-33 | C-17 | |
| R-34, T-03 | C-05 `:956-957`, `stall_tests.rs:152-180` | **문서와 구현 차이**: `docs/pitfalls.md` "A per-run budget that a retry resets"는 "`max_rounds`가 실행마다 0부터 세어 Try again마다 6번을 더 샀다(#736). 실행을 넘어 지켜야 할 상한은 프로젝트에 저장한 수로 두고 새 요청으로만 초기화한다"고 쓴다. 구현은 "작동하지 않는 라운드"(`not_working_checks`, 10)와 "무변경 턴"(2)만 저장하고 `refinements`는 여전히 실행마다 0(`:956`)이다. 그래서 빌드는 되지만 닮음이 모자란 프로젝트는 빌더가 매번 파일을 바꾸는 한 Try again마다 `max_rounds`번을 더 받는다. pitfall이 말한 #736 사례(작동하지 않는 빌드)는 막혔으나 규칙 문장 전체가 구현되지는 않았다 |
| — | `mod.rs:1-13` 모듈 주석 | **문서와 구현 차이**: 주석의 Check 줄은 "website: 스크린샷 비교, 그 밖 스택: 빌드 성공"이고 Refine 줄은 "`max_rounds`까지"만 말한다. 구현은 종류별 검사 목록(check-contract R-07)과 세 가지 멈춤 조건(R-10, R-12, R-23)을 쓴다. README "refined until it's close"(`README.md:85`)도 상한·정체 멈춤을 말하지 않는다 |
| T-01, T-02 | `stall_tests.rs:42-102` | 테스트 열람 |
| T-03 | `stall_tests.rs:126-180` | 테스트 열람 |
| T-04, T-06~T-10 | `tests.rs:1928-1940`, `:2016-2085` | 테스트 열람 |
| T-15, T-16 | `runs.rs:275-303`, `:430-445` | 테스트 열람 |

### 2.2 코드 읽는 순서

`mod.rs:800-1122` `Worker::run`을 위에서 아래로 읽는다(시작 확인 → 조사 결정 → 메시지 선택 → 라운드·상한 → 반복 → 최종 판정). 반복 안의 함수는 `turn_with_wait`(`:1263`) → `converse_turn`(`:1330`) → `checks_with_a_retry`(`:1192`) → `kept_check.rs` → `progress.rs`의 `before_turn`/`after_turn`/`stalled` 순. 그다음 `start`(`:269`)와 `run_outcome`(`:1491`)으로 스레드 경계를, `runs.rs`로 대기열을, `self_check.rs` `answer_self_checks`와 `tools.rs` `rebuild_check`로 0번 라운드 왕복을 본다. 원본 구현 전략: 모든 작업이 워커 스레드 하나에서 돌고, 화면은 채널만 읽는다. 실행을 넘어 지켜야 하는 수는 `craft.json`·`build-progress.json`에 저장하고, 실행마다 새로 세는 수는 지역 변수로 둔다.

## 적용 메모

우리 절차(`OSS_ANALYSIS_WORKFLOW.md`, `.claude/skills/oss-repo-spec/SKILL.md:41` "재구현 검증(4장 6번)은 사용자가 요청할 때만 한다")와 비교한 보완 후보다. 원본 동작이 아니다. 우리 쪽 대응: "빌더 턴" = 스펙만 읽고 재구현하는 작업자 한 번, "검사 라운드" = 재구현 결과를 원본과 비교하는 검증 한 번, "재다듬기" = 검증에서 나온 차이를 스펙 수정 또는 재구현 수정으로 되돌리는 것.

| 관련 R-ID | 원본과 다르게 할 점(우리 절차에 들일 것) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-23, R-34 | 재구현 검증을 4장에 단계로 두고, 한 번 요청에 "검증 → 차이 되돌림"을 최대 N번(예: 2) 반복하는 상한을 정한다. 상한에 닿으면 남은 차이를 그대로 보고하고 끝낸다 | 원본은 재다듬기 상한(`max_rounds`)으로 비용을 묶고, 상한에 닿아도 작동하면 Ready로 끝낸다. 우리 절차는 검증 단계 자체가 본문에 없어 반복 횟수도 종료 조건도 없다 | 4장에 "재구현 검증" 절 추가: 입력(스펙·재구현 위치), 반복 상한, 종료 보고 형식 |
| R-10, R-34 | 상한을 세션을 넘어 지켜야 하는 수와 세션마다 새로 세는 수로 나누고, 넘어 지켜야 할 수(예: "같은 R-ID가 연속으로 검증 실패한 횟수")는 `next.md`의 해당 스펙 항목에 숫자로 남긴다. 사용자의 새 지시로만 초기화한다 | 원본이 #736 뒤 연속 실패 수를 프로젝트에 저장한 이유가 "다시 시도가 상한을 초기화"였다. 반대로 원본도 재다듬기 수는 아직 실행마다 초기화해 같은 문제가 남아 있다(2.1 R-34). 우리 세션은 끊겼다 이어지므로 같은 일이 생긴다 | `next.md` 항목에 "검증 시도 n회(마지막 결과)" 칸 |
| R-12, R-26~R-28 | "정체"를 결과물의 내용 변화로 정의한다: 재구현 차이를 되돌렸는데 두 번 연속으로 스펙 본문(1부)과 재구현 파일이 모두 바뀌지 않았으면 반복을 멈추고 사용자에게 넘긴다(`handoff.md`). 작업자의 답("고쳤다")은 판단에 쓰지 않는다 | 원본은 빌더의 답이 아니라 `app/` 파일 내용 해시로 진행을 판단하고, 시각이 아닌 바이트로 비교한다(#736: 빌더가 "빌드했다"고 했지만 `app/`이 비어 있었음). 우리도 작업자 보고만 보고 "보완됨"으로 칠 위험이 같다 | 반복 종료 조건에 "두 번 연속 무변경" 추가. 확인 방법: `git diff --stat`이 스펙·재구현 경로에서 0줄 |
| R-20 | 검증 도구 자체가 실패한 경우(재구현이 빌드되지 않는 환경 문제, 도구 오류)는 한 번만 다시 돌리고, 두 번째도 실패하면 "검증 불가"로 보고하고 스펙 결함으로 세지 않는다. 다음 시도는 재구현을 다시 하지 않고 검증만 다시 한다 | 원본은 "검사가 볼 수 없었던 것은 빌드에 대해 아무것도 말하지 않는다"며 검사 오류를 빌드 실패와 구분하고, `awaiting_check`로 다음 시도를 검사만으로 줄인다 | 재구현 검증 보고의 결과 분류에 "검증 불가(도구)" 추가. 사례: 같은 검증이 두 번 오류 → 결과 "검증 불가", 연속 실패 수 증가 없음 |
| R-18, R-23, R-24 | 검증 결과를 "작동"(재구현이 돈다)과 "일치"(원본과 같다)로 나누고, 연속 실패 상한은 "작동하지 않음"에만 적용한다. 작동은 하지만 일치하지 않는 것은 반복 상한까지 되돌리고, 상한 뒤에는 "부분 일치"로 보고한다 | 원본은 `not_working_checks`를 `passed` 기준으로만 세고, 끝 판정도 마지막 `passed`로 Ready/실패를 가른다. `good`이 아닌 것은 재다듬기 대상일 뿐 실패가 아니다. check-contract 적용 메모의 "작동/일치 두 칸"과 같은 축이다 | 재구현 검증 보고 표에 R-ID별 작동·일치·미검증 칸 |
| R-17, R-21 | 반복 중 사용자가 추가 지시를 주면 그 지시를 다음 차례로 바로 넣고, 그 차례는 반복 횟수에 세지 않으며 정체·연속 실패 수를 0으로 한다 | 원본은 사람 노트를 "새 요청"으로 보고 검사 없이 다음 턴으로 보내며 두 카운트를 초기화한다. 우리 메인 세션이 서브에이전트 반복을 돌릴 때 사용자 개입을 같은 방식으로 다뤄야 상한이 사용자 지시를 막지 않는다 | 반복 절차에 "사용자 개입 = 횟수 초기화" 한 줄 |
| R-31, R-32 | 재구현 작업자가 보고 전에 스스로 돌릴 수 있는 검증(예: 재구현의 테스트, C-ID 범위 존재 확인)을 주고, 그 결과는 공식 검증 횟수에 넣지 않는다. 결과가 바뀌지 않았으면 공식 검증에서 다시 돌리지 않고 그 결과를 쓴다 | 원본의 0번 라운드는 같은 검사를 돌리되 기록·카운트에 넣지 않고, 결과가 모두 작동하면 같은 입력의 다음 라운드에서 재사용한다(R-19). 비용을 줄이면서 판정 기준은 하나로 유지한다 | 작업자 지시문에 "자체 검증" 단계, 메인 세션 검증의 "입력 같으면 재사용" 규칙 |
| R-02 | 재구현 검증의 반복 상한·판정 기준은 호출 경로(대화 요청, 스킬 실행)와 무관하게 한 곳(워크플로 본문)에서 정한다 | 원본은 같은 루프가 앱 6번·CLI/도구 2번, 도구만 `good_enough` 설정 무시로 경로마다 결과가 달라진다(2.1 R-02). 경로마다 기본값을 따로 두면 같은 스펙의 검증 결과가 달라진다 | 워크플로에 기본값 표 한 곳 |
