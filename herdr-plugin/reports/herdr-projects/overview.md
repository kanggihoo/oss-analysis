---
sha: "8258d965c179f9297e96879f9a17680c3eacb49f"
created: 2026-10-22
updated: 2026-10-22
sources:
  - herdr-plugin.toml
  - bin/run.sh
  - README.md
  - AGENTS.md
  - LICENSE
  - Cargo.toml
  - package.json
  - docs/crates.md
  - docs/checked-on-herdr.md
  - docs/agents.md
  - src/main.rs
  - src/cli/mod.rs
  - src/cli/tasks.rs
  - crates/core/src/lib.rs
  - crates/core/src/herdr/mod.rs
  - crates/core/src/herdr/cli.rs
  - crates/core/src/herdr/api.rs
  - crates/core/src/herdr/socket.rs
  - crates/core/src/agents/kinds.rs
  - crates/core/src/agents/adapter.rs
  - crates/core/src/store/files.rs
  - crates/core/src/store/tasks.rs
  - crates/core/src/gate.rs
  - crates/flow/src/lib.rs
  - crates/flow/src/hook.rs
  - crates/flow/src/turn.rs
  - crates/flow/src/runner.rs
  - crates/flow/src/jobs.rs
  - crates/flow/src/keeper.rs
  - crates/flow/src/housekeeping.rs
  - crates/flow/src/watcher.rs
  - crates/flow/src/submit.rs
  - crates/flow/src/delegate/jobs.rs
  - crates/flow/src/delegate/launch.rs
  - crates/flow/src/delegate/worktree.rs
  - crates/flow/src/coordinator/co.rs
  - crates/flow/src/coordinator/look.rs
  - crates/flow/src/coordinator/place.rs
  - crates/flow/src/coordinator/pump.rs
  - crates/flow/src/coordinator/rules.rs
  - crates/flow/src/finish/pipeline.rs
  - crates/flow/src/finish/pipeline_end.rs
  - crates/flow/src/finish/review_once.rs
  - crates/flow/src/finish/turn_ended.rs
  - crates/flow/src/finish/hand_over.rs
  - crates/flow/src/finish/auto_merge.rs
  - crates/flow/src/finish/line.rs
  - crates/flow/src/finish/sync_job.rs
  - crates/flow/src/actions/mod.rs
  - crates/flow/src/actions/start.rs
  - crates/flow/src/actions/finish_line.rs
  - crates/flow/src/land/merge.rs
  - crates/flow/src/land/checks.rs
  - crates/flow/src/land/cleanup.rs
  - crates/flow/src/flow/sidebar.rs
  - crates/flow/src/flow/pane_owner.rs
  - crates/flow/src/flow/send.rs
  - crates/flow/src/sync.rs
  - crates/flow/src/plan.rs
  - crates/flow/src/attempts.rs
  - crates/flow/src/after.rs
  - crates/flow/src/automations.rs
  - crates/flow/src/autopilot/mod.rs
  - crates/flow/src/remote.rs
  - crates/flow/src/review_page.rs
  - crates/flow/src/install.rs
  - crates/flow/src/extras.rs
  - crates/flow/src/doctor.rs
  - crates/flow/src/take_over.rs
  - crates/flow/src/calls/mod.rs
  - crates/flow/src/notify.rs
  - crates/flow/src/webui/keep.rs
  - crates/board/src/lib.rs
  - crates/board/src/board/run/place.rs
  - crates/web/src/lib.rs
  - crates/web/src/webui/door.rs
  - crates/web/src/webui/door_loop.rs
---

# herdr-projects Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/eliasstravik/herdr-projects` (`herdr-plugin/artifacts/herdr-projects/repo-metadata.txt`, branch `main`, 커밋일 2026-10-21)
- **작업트리 상태**: Clean (`git clone --depth 50`, 2026-10-22)
- **분석 목적**: 학습 · 도입 검토. (1) herdr 플러그인이 매니페스트(`herdr-plugin.toml`)를 통해 herdr와 어떻게 연동하는지, (2) 에이전트를 태스크별로 위임·조율하는 방식을 본다.
- **라이선스**: MIT — `LICENSE`(1~3행 "MIT License / Copyright (c) 2026 Elias Stravik"). `git ls-files | grep -i licen` 결과는 이 파일 하나뿐이라 하위 LICENSE는 없다. 워크스페이스 `Cargo.toml`의 `[workspace.package] license = "MIT"`를 네 크레이트가 상속한다(`crates/*/Cargo.toml`의 `license.workspace = true`). (코드 확인)
- **분석 대상 제품**: 추적 파일 930개. 배포 단위는 하나, 즉 플러그인 매니페스트 + 실행 래퍼 `bin/run.sh` + Rust 바이너리 `herdr-projects`(루트 패키지, 버전 1.2.16, `herdr-plugin.toml:3`). 바이너리는 크레이트 5개를 위로 쌓아 만든다(`docs/crates.md:3-12`, `AGENTS.md:14-19`).

  | 영역 | 추적 파일 수 | 맡은 일 |
  |---|---|---|
  | `crates/core` (sw-core) | 105 | 데이터(`store/`), herdr 호출(`herdr/`), 에이전트 종류(`agents/`), 음성 |
  | `crates/flow` (sw-flow) | 239 | 태스크 흐름: 위임·마감선·병합·keeper·원격·자동화·오토파일럿·리뷰 페이지 |
  | `crates/board` (sw-board) | 81 | 터미널 보드 화면(상태·키 처리·그리기) |
  | `crates/web` (sw-web) | 55 | herdr 웹 UI 앞단(front door)과 웹 보드 |
  | `src/` (패키지 `herdr-projects`, 라이브러리 `sw`) | 11 | 명령줄(`cli/`)과 생성 문서(`docs.rs`, `docs/`) |
  | `tests/` | 354 | 테스트 프로그램 하나(`tests/main.rs`)의 모듈들 — 열지 않음 |
  | `docs/` | 57 | 사용자 문서 — 일부만 열어 봄 |
  | `scripts/`, `bin/`, `assets/`, `.github/` | 11, 1, 3, 2 | 빌드 캐시·검사 스크립트, 실행 래퍼, 이미지, CI — `bin/run.sh`만 열어 봄 |

  (규모는 `git ls-files | cut -d/ -f1-2 | sort | uniq -c`로 센 값. 코드 확인)
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지) · 제외: 없음(승인 전)

---

## 2. 프로젝트 개요

**용어 먼저.** *herdr*는 코딩 에이전트용 터미널 멀티플렉서다. *space(workspace)*는 herdr의 작업 공간 단위, *pane*은 그 안의 터미널, *tab*은 pane을 묶는 탭이다. *Coordinator*는 보드의 채팅용 에이전트(오래 사는 에이전트 대화 하나)로, 사람이 적은 말을 태스크로 바꾼다. *task*는 보드 목록의 한 항목, *worker*는 태스크 하나를 맡은 에이전트, *reviewer*는 끝난 작업을 검토하는 두 번째 에이전트다. *마감선(finish line)*은 에이전트 턴이 끝난 뒤 커밋 → main 합치기 → 검사 → push·PR → 리뷰 → 승인 대기로 이어지는 단계들이다. *keeper*는 보드가 닫혀 있어도 주기 작업을 돌리는 상주 프로세스다.

README는 이 레포를 "herdr용 작업 보드: 사람이 쓴 태스크 목록 하나, 위임한 태스크마다 일반 herdr 에이전트가 자기 space와 worktree에서 돌고, 끝나면 두 번째 에이전트가 검토하며, 사람은 승인만 한다"로 소개한다(`README.md:5`, `:17`). 코드와 맞춘 결과는 아래와 같다.

- **herdr가 엔진, 보드는 리모컨**이라는 구조는 코드에서 확인된다. 플러그인은 herdr의 CLI(`herdr workspace/tab/pane/agent/worktree ...`)를 자식 프로세스로 실행해 JSON을 주고받고(`crates/core/src/herdr/cli.rs:47-102`, `herdr/api.rs:10-210`), 소켓은 `popup.close`와 `events.subscribe` 두 가지에만 직접 쓴다(`herdr/socket.rs:1-4`, `:26-44`). 에이전트는 herdr가 `herdr agent start --kind ...`로 띄운다(`herdr/api.rs:148-165`). (코드 확인)
- **태스크는 파일**이다. 태스크 하나는 `~/.herdr-projects/data/tasks/<repo>/<n>/task.json`이고(`store/files.rs:29-46`, `store/tasks.rs:33-61`), 상태는 `stage` 문자열 22종(`files.rs:16-17`)이다. DB도 서버도 없다. (코드 확인)
- **위임**은 태스크마다 herdr worktree space를 만들고 그 root pane에서 에이전트를 시작해 첫 프롬프트를 넣는 일이다(`delegate/jobs.rs:59-120`). **Coordinator**는 사람이 쓴 말을 그대로 받는 일반 에이전트이며, 보드 사용법은 자기 폴더의 `AGENTS.md` 규칙 블록으로 받는다(`coordinator/rules.rs:22-56`, `:61-78`). Coordinator가 하는 일은 에이전트 셸에서 `herdr-projects add/delegate/approve ...` 명령을 실행하는 것이다(규칙 본문 `rules.rs:29-52`, 명령 처리 `src/cli/tasks.rs:45-170`). (코드 확인)
- **approve**(승인)는 `stage == "approval"`인 태스크를 `merging`으로 바꾸고 `land` 러너를 띄운다. 마지막 리뷰가 실패했거나 GitHub 검사가 실패했으면 `--anyway` 없이는 거절한다(`actions/finish_line.rs:28-65`). (코드 확인)
- README가 주장하는 "마감선 끝에 draft PR을 열고", "다섯 묶음(needs you / ready to approve / working / to do / done)으로 보여 준다", "Watcher가 에이전트당 분 단위로 모델을 호출한다"는 이 분석에서 해당 구현의 본문을 열지 않았다(PR 단계는 `finish/pipeline.rs` 120행 이후, 묶음 판정은 `state.rs`, Watcher 주기는 설정 목록). 근거는 모듈 머리 주석 수준이라 `추론`으로 둔다(`pipeline.rs:1-2`, `files.rs:12`, `watcher.rs:1-6`).

### 기능 지도

<!--
OSS_ANALYSIS_WORKFLOW.md 2장 4번. 한 행 = 스펙 하나의 작업 단위. 이번에는 지도만(스펙 미작성).
상태는 전부 "미작성"(파일 없음, 경로는 코드 표기).
검증 수준: 진입점·호출을 읽었으면 "코드 확인", 모듈 머리 주석만 봤으면 "추론(머리 주석)", 열지 않았으면 "미확인".
-->

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 플러그인 입구 (매니페스트 → 래퍼 → 서브커맨드) | herdr가 매니페스트의 build/startup/actions/events/panes 명령을 `sh bin/run.sh <서브커맨드>`로 실행 → 래퍼가 바이너리를 찾거나 내려받아 `exec`. 설치·갱신·진단 서브커맨드는 제외 | `herdr-plugin.toml:13-58`, `bin/run.sh:15-24`, `:62-94`, `src/main.rs:2-5`, `src/cli/mod.rs` `main`(:48), `run`(:56) | 없음 | 핵심 | `capabilities/plugin-entry.md` · 미작성 | 코드 확인(매니페스트·래퍼·디스패치). 릴리스 다운로드 성공 여부는 미확인 |
| 태스크 저장소와 보드 명령 | `add/list/report/delegate/tell/stop/approve/review/fix/retry/finish/pick/archive/set/show` 등. 태스크는 `task.json`, 같은 명령을 에이전트도 셸에서 실행. 원격 머신·오토파일럿 허용 판정은 경계만 | `src/cli/tasks.rs` `command`(:33-174), `crates/core/src/store/tasks.rs` `get`(:35), `list`(:44), `store/files.rs` `STAGES`(:16), `caller`(`src/cli/mod.rs:40-45`) | 없음 | 핵심 | `capabilities/task-store.md` · 미작성 | 코드 확인(명령 분기·저장 경로). 잠금·`update_wait`·설정 조회는 미확인 |
| Coordinator | 사람이 보드 입력창에 적으면 Coordinator 에이전트가 태스크를 만들거나 위임. 최상위·머신·프로젝트 세 단계. 규칙은 폴더의 `AGENTS.md` 블록 | `coordinator/rules.rs` `rules_of`(:22), `write_rules`(:72), `coordinator/pump.rs` `tick`(:46), `ensure`(:77), `coordinator/co.rs`(:1-4), `src/cli/tasks.rs` `coordinator`(:186-217) | 태스크 저장소 | 핵심 | `capabilities/coordinator.md` · 미작성 | 코드 확인(규칙·pump 시작부·CLI). pump 후반(메시지 입력·재시도)은 미확인 |
| 위임 (worktree space + 에이전트 시작) | 태스크 위임 → 디스크 확보 → worktree space 생성(저장소 아니면 일반 space) → 레포 setup → 에이전트 시작 → 첫 프롬프트. 큐·슬롯, 재시작·재열기 포함 | `delegate/jobs.rs` `delegate_job`(:59), `delegate_steps`(:69), `delegate/worktree.rs` `free_branch`(:20), `delegate/launch.rs` `start_agent`(:45), `actions/start.rs`(:1-17) | 태스크 저장소, 에이전트 종류 | 핵심 | `capabilities/delegate.md` · 미작성 | 코드 확인(`delegate_steps` 120행까지). 120행 이후(setup·프롬프트 전달)와 큐 시작은 미확인 |
| 에이전트 종류 패밀리 | `worker/reviewer/coordinator.agent` 설정으로 프로그램을 고름(claude, codex, pi 외 15종). 시작 인자·모델·effort·재개·턴 종료 읽기 방식을 표 하나로 선언 | `agents/kinds.rs` 머리 표(:1-33), `agents/kinds/herdr.rs`, `kinds/own.rs`, `agents/adapter.rs` `hook_args`(:27) | 없음 | 핵심 | `capabilities/agent-kinds.md` · 미작성 | 코드 확인(`Kind` 구조·`hook_args`). 개별 종류 항목 값과 대화 파일 파서는 미확인 |
| 이벤트 훅·상태 반영 | herdr 이벤트(`pane.agent_status_changed`, `pane.agent_detected`, `pane.closed`, `worktree.removed`)를 받아 태스크 상태를 갱신하고 턴 종료를 판정해 러너를 띄움 | `flow/hook.rs` `hook_main`(:26), `on_pane`(:49), `apply`(:72-200), `hook/reconcile.rs`, `flow/pane_owner.rs` `whose`(:31) | 태스크 저장소 | 핵심 | `capabilities/event-hook.md` · 미작성 | 코드 확인(`hook.rs` 전체). `reconcile`은 미확인 |
| 에이전트 턴 종료 보고 | 에이전트 자신의 훅이 `herdr-projects turn-ended`를 호출 → 토큰 검증 후 이벤트를 task.json에 적고 `finish` 러너를 띄움 | `flow/turn.rs` `turn_ended`(:30-59), `agents/adapter.rs` `hook_args`(:27-75), `delegate/launch.rs` `launch_extras`(:32) | 에이전트 종류 | 핵심 | `capabilities/turn-ended.md` · 미작성 | 코드 확인. 종류별 대화 파일 해석(`why_stopped` 이후)은 미확인 |
| 마감선 (커밋·sync·검사·리뷰 루프) | 턴 종료 후 커밋 → main 합치기 → setup → 검사 명령 → push·PR → reviewer 에이전트 → 실패 시 에이전트에 되돌림 → 승인 대기 또는 자동 병합 | `finish/turn_ended.rs`(:1-5), `finish/pipeline.rs` `pipeline`(:46), `finish/pipeline_end.rs` `after_review`(:39), `finish/review_once.rs` `review_once`(:29), `core/gate.rs`(:1-4) | 위임, 턴 종료 보고 | 핵심 | `capabilities/finish-line.md` · 미작성 | 코드 확인(`pipeline` 120행까지, `after_review` 70행까지, `review_once` 110행까지). PR·리뷰 재시도·fallback·한도는 미확인 |
| 승인과 병합 | `approve`(사람의 yes) → `merging` → PR 또는 로컬 squash 병합 → 정리(space·worktree·브랜치) | `actions/finish_line.rs` `approve`(:28), `land/merge.rs` `land_job`(:20), `landed`(:48), `land/cleanup.rs`(:1-5), `finish/line.rs`(:1-4), `finish/auto_merge.rs`(:1-4), `cli/mod.rs` `approve_current`(:122) | 마감선 | 핵심 | `capabilities/approve-and-land.md` · 미작성 | 코드 확인(`approve`, `land_job` 서두). 병합 본문(90행 이후)·checks·cleanup은 추론(머리 주석) |
| 터미널 보드 | `open` 액션·`board` 서브커맨드로 TUI를 연다. 탭 배치 또는 herdr 팝업. 키·그리기는 경계만 | `src/cli/mod.rs:84`, `:105-109`, `board/run/place.rs`(:1-5, :60-80), `herdr/api.rs` `open_board`(:188), `open_board_popup`(:193), `board/` 하위 `update/`(26파일), `view/`(31파일) | 태스크 저장소 | 핵심 | `capabilities/terminal-board.md` · 미작성 | 코드 확인(열기·배치). 화면·키 처리는 미확인(파일 수만 셈) |
| herdr 사이드바·Watcher | 에이전트 pane에 `pane report-metadata`로 표시 이름·진행률·한 줄 상태를 써 넣음. Watcher는 숨은 모델 호출로 진행 상황 한 줄을 만듦 | `flow/sidebar.rs`(:1-8, :20-31), `herdr/api.rs` `metadata`(:122), `flow/watcher.rs`(:1-6) | 에이전트 종류 | 부속 | `capabilities/sidebar-watcher.md` · 미작성 | 코드 확인(메타데이터 인자). Watcher 호출·주기는 추론(머리 주석) |
| keeper·housekeeping | 훅·시작 이벤트마다 상주 keeper를 확인해 띄우고, 한 패스로 대기 태스크 시작·herdr와 동기화·main 갱신·PR 폴링 | `flow/keeper.rs` `ensure_keeper`(:28), `keeper_main`(:42), `flow/housekeeping.rs` `housekeeping`(:26), `flow/jobs.rs` `run_job`(:8) | 이벤트 훅 | 핵심 | `capabilities/keeper.md` · 미작성 | 코드 확인(시작·잡 분기·패스 시작부). 패스 후반·PR 폴링은 미확인 |
| 확장 워크플로 패밀리: plan·attempts·after·limits·fallback | 계획 먼저, 여러 시도 중 하나 선택, 다른 태스크 완료 후 시작, 시간·토큰 한도, 에이전트 인수인계. 설정값 하나씩으로 켬 | `flow/plan.rs`(:1-5), `attempts.rs`(:1-6), `after.rs`(:1-6), `finish/hand_over.rs`(:1-5), `plan/`, `attempts/`, `after/`, `limits/` | 위임, 마감선 | 부속 | `capabilities/workflow-extras.md` · 미작성 | 추론(머리 주석만) |
| 자동화·오토파일럿 | 일정 또는 보드 이벤트로 태스크를 자동 생성(automations). Coordinator를 깨워 목표를 추진(autopilot) | `flow/automations.rs`(:1-4), `flow/autopilot/mod.rs`(:1-6), `automations/triggers.rs`, `autopilot/tick.rs` | Coordinator, 위임 | 부속 | `capabilities/automations-autopilot.md` · 미작성 | 추론(머리 주석만) |
| 다른 머신 | 머신마다 자기 태스크를 갖고, 홈 보드가 SSH로 `herdr-projects remote ...`를 불러 목록·액션을 중계. 작업은 머신 사이를 옮겨 가지 않음 | `flow/remote.rs`(:1-5), `src/cli/mod.rs:89`, `remote/act.rs`, `herdr/api.rs` `machines`(:205) | 태스크 저장소 | 부속 | `capabilities/remote-machines.md` · 미작성 | 추론(머리 주석만) |
| 웹 UI 보드와 리뷰 페이지 | herdr 웹 UI 앞에 front door 서버를 세워 요청을 그대로 통과시키고 `/herdr-projects/` 아래에 보드 페이지·호출을 추가. 리뷰 증거 페이지는 127.0.0.1(선택적으로 tailnet)에 게시 | `web/webui/door.rs`(:1-12, :21-33), `web/webui/door_loop.rs` `run_door`(:89), `flow/webui/keep.rs`(:1-6), `flow/review_page.rs`(:1-6), `cli/mod.rs:88` | 태스크 저장소 | 부속 | `capabilities/web-ui.md` · 미작성 | 코드 확인(door 서두·hook의 `ensure_door` 호출 `hook.rs:32`). 페이지·API는 미확인 |
| 음성 통화 | 터미널 보드에서 ElevenLabs 통화(WebSocket)를 걸고 사람 쪽 컴퓨터의 마이크·스피커로 연결 | `flow/calls/mod.rs`(:1-6), `src/cli/mod.rs:92-93`, `core/src/voice/` | 태스크 저장소 | 부속 | `capabilities/voice.md` · 미작성 | 추론(머리 주석만) |
| 설치·갱신·진단·이전 | `install`/`update`(릴리스 파일 교체), `doctor`(점검), 옛 설치 인수(`take_over`), 에이전트 스킬 문서 기록(`extras`) | `flow/install.rs`(:1-4), `flow/doctor.rs`(:1-5), `flow/take_over.rs`(:1-5), `flow/extras.rs`(:1-4), `src/cli/mod.rs:97-99` | 플러그인 입구 | 부속 | `capabilities/install-doctor.md` · 미작성 | 추론(머리 주석만) |
| 레포 자체 개발 도구 | `docs --guard`(파일 크기·머리 주석·키 표 규칙), 생성 문서 표, 테스트·빌드 캐시 스크립트 | `src/docs.rs`, `src/docs/guard.rs`, `src/cli/mod.rs:100-104`, `scripts/check.sh`, `AGENTS.md:58-97` | 없음 | 부속 | `capabilities/dev-tooling.md` · 미작성 | 추론(`AGENTS.md`·CLI 분기만). 스크립트 본문 미열람 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| **매니페스트 선언**: `[[build]]`, `[[startup]]`, `[[actions]]`(open, coordinator, approve-current), `[[events]]`(4종), `[[panes]]`(board, placement=tab) | 플러그인 입구, 이벤트 훅, 터미널 보드 | `herdr-plugin.toml:13-58`(전 항목 명령은 `sh bin/run.sh <sub>`) | `plugin-entry` 행에 포함 · 미작성 | 코드 확인 |
| **플러그인 환경변수**: `HERDR_PLUGIN_EVENT`(`startup` 등), `HERDR_PLUGIN_EVENT_JSON`(`{event,data:{pane_id,workspace_id,agent_status,agent}}`), `HERDR_PLUGIN_CONTEXT_JSON`(`focused_pane_id`, `focused_pane_cwd`, `tab_id`, `worktree.repo_root` 등), `HERDR_PLUGIN_ID`, `HERDR_PANE_ID`, `HERDR_SOCKET_PATH`, `HERDR_ENV` | 이벤트 훅, 터미널 보드, 승인 액션, 위임 | `hook.rs:30-37`, `cli/mod.rs:16-45`, `:122-131`, `herdr/cli.rs:33-37`, `:43`, `board/run/place.rs:19-27` | 각 행에 나눔 · 미작성 | 코드 확인(읽는 쪽). herdr가 실제로 주는 값은 미확인(문서 `checked-on-herdr.md:14-18` 주장만) |
| **herdr CLI 호출**: 자식 프로세스 `herdr <명령> ...`, 결과는 JSON의 `result`(또는 `error.{code,message}`). `HERDR_PANE_ID` 등 암묵 대상을 지우고 `HERDR_SOCKET_PATH`로 세션을 지정 | 위임, 훅, 사이드바, Coordinator, 리뷰, 정리 | `herdr/cli.rs` `launch`(:47-59), `run`(:81-102), `herdr/api.rs`(:10-239) | `herdr-calls` · 미작성(필요 시 별도) | 코드 확인 |
| **herdr 소켓 직접 호출**: 한 줄 JSON `{"id","method","params"}`. `popup.close`, `events.subscribe`(`tab.focused`) | 터미널 보드(팝업) | `herdr/socket.rs`(:10-44) | `terminal-board` 행에 포함 · 미작성 | 코드 확인 |
| **에이전트 상태 필드**: `agent get`의 `agent_status`, `state_change_seq`, `completion_seq`, `terminal_id`, `agent_session`. 오래된 읽기는 seq로 거름 | 이벤트 훅, 마감선, 위임 | `hook.rs:72-139`, `:218-226` | `event-hook` 행에 포함 · 미작성 | 코드 확인(소비 쪽). herdr 쪽 의미는 미확인 |
| **에이전트 훅 콜백**: 시작 인자로 훅을 주입(claude `--settings` 파일의 Stop/StopFailure, codex `-c notify=`, pi `-e` 확장) → `herdr-projects turn-ended --id --role --token [--round]`. 토큰은 시작 때 새로 만들어 `task.json`에 저장 | 위임, 턴 종료 보고, 리뷰 | `adapter.rs:13-19`, `:27-75`, `launch.rs:32-43`, `turn.rs:35` | `turn-ended` 행에 포함 · 미작성 | 코드 확인 |
| **task.json 스키마**: `stage`, `link{socket,workspace,tab,pane,terminal,reviewer}`, `runner{pid,job}`, `last`, `handled`, `armedAt` 등 | 거의 모든 기능 | `store/files.rs:16-21`, `hook.rs:91-97`, `delegate/jobs.rs:48-53`, `runner.rs:75-86` | `task-store` 행에 포함 · 미작성 | 코드 확인(쓰는 키 일부). 전체 필드 목록은 미확인 |
| **러너·잠금**: 긴 작업은 `herdr-projects run <job> <id>`로 분리된 프로세스(`setsid`)에서 실행, `task.json`의 `runner` 마커로 한 번에 하나 | 위임, 마감선, 병합, Coordinator pump | `runner.rs:22-51`, `:75-86`, `jobs.rs:8-39` | `keeper` 행에 포함 · 미작성 | 코드 확인 |
| **pane 메타데이터 출처**: `--source plugin:herdr-projects`로 `pane report-metadata`·`workspace report-metadata` | 사이드바 | `herdr/api.rs:122-126`, `flow/sidebar.rs:20`, `:24-31` | `sidebar-watcher` 행에 포함 · 미작성 | 코드 확인(쓰는 쪽) |

**herdr 연동 지점 한눈에** (매니페스트 → `bin/run.sh` → 코드)

| 매니페스트 항목 | 실행되는 서브커맨드 | 코드 진입 | 하는 일 |
|---|---|---|---|
| `[[build]]` (`herdr-plugin.toml:13-14`) | `run.sh --fetch` | `bin/run.sh:19-20`, `:101-104` | 릴리스 바이너리 다운로드, 실패하면 `cargo build --release --locked` |
| `[[startup]]`, `[[events]]` 4종 (`:16-17`, `:35-50`) | `hook` | `cli/mod.rs:75` → `flow/hook.rs` `hook_main`(:26) | keeper 보장, startup이면 web front door·스킬 문서·사이드바 갱신, 이벤트면 해당 태스크 반영 |
| 액션 `open` (`:19-22`) | `open` | `cli/mod.rs:84` → `board::place::show` | 보드를 탭(또는 팝업)에서 열기 |
| 액션 `coordinator` (`:24-27`) | `open-coordinator` | `cli/mod.rs:86` → `coordinator::look::go_in` | Coordinator 채팅 pane으로 이동 |
| 액션 `approve-current` (`:29-33`, `contexts=["pane"]`) | `approve-current` | `cli/mod.rs:87`, `:122-131` | 포커스 pane의 태스크가 `approval`이면 보드를 열어 승인 질문을 띄움(바로 병합하지 않음) |
| 패널 `board` (`:52-58`, `placement="tab"`) | `board` | `cli/mod.rs:105-109` → `board::open_board` | stdin·stdout이 TTY일 때만 TUI, 아니면 도움말 출력 |

**대조한 범위와 미탐색 영역**
- 대조: 매니페스트 전체(58행), 래퍼 `bin/run.sh` 전체(107행), README 전체, 저장소 `AGENTS.md`, 서브커맨드 디스패치 `src/cli/mod.rs`·`src/cli/tasks.rs` 전체, `crates/core/src/herdr/{cli,api,socket}.rs` 전체, `flow/hook.rs` 전체, `flow/runner.rs`·`jobs.rs`·`turn.rs` 앞부분, `coordinator/rules.rs` 전체, `agents/adapter.rs` 앞 80행. 사용자 문서는 `docs/crates.md`, `docs/checked-on-herdr.md`, `docs/agents.md`를 읽었다(herdr가 실제로 그렇게 동작한다는 주장은 코드가 아니라 문서 측정값이므로 `미확인`).
- 문서와 구현의 차이·주의: ① README는 "Node 없음"이라 하고 `package.json`이 있지만, 그 안은 테스트 명령 하나뿐이다(`package.json:6-9`, `AGENTS.md:19`). ② 매니페스트 `description`은 "delegated one an ordinary herdr agent"로 문장이 깨져 있다(`herdr-plugin.toml:6`, 기능과는 무관). ③ `platforms = ["linux","macos"]`(`:7`)와 코드의 `std::os::unix` 사용(`herdr/cli.rs:44`, `store/files.rs:9`)은 일치한다. ④ `src/cli/tasks.rs:84`는 `suggest/accept/dismiss`를 "더는 없다"는 오류로 남겨 두어, 옛 문서·에이전트 지시가 있을 수 있음을 시사한다(추론). ⑤ `README.md:93`의 `doctor`가 점검한다는 항목은 `doctor/` 본문을 열지 않아 대조하지 않았다.
- 미탐색(솔직히 대부분): `crates/board/`의 `update/`·`view/`·`textbox/`(약 80파일), `crates/web/`의 `page/`·`model/`·`voice/`(약 55파일), `crates/flow/`의 `finish/`·`land/` 후반부(PR 생성·checks·cleanup), `plan/`, `attempts/`, `autopilot/`, `automations/`, `remote/`, `calls/`, `limits/`, `leftovers/`, `doctor/`, `take_over/`, `shown/`, `store/settings*`(설정 목록·조회), `core/src/agents/` 대부분(대화 파일 파서), `core/src/voice/`, `tests/`(354, 규칙에 따라 열지 않음), `.github/`(CI, 열지 않음), `scripts/`, `assets/`, `docs/` 55개. 이유는 레포가 크고(추적 930개) 이번 범위가 지도(2장)까지이기 때문이다.

---

## 3. 구조 해설

구조도(archify)는 사용자 지시로 만들지 않았다. 아래는 글만으로 읽는 순서와 크레이트별 역할이다.

**읽는 순서**
1. `herdr-plugin.toml` 전체(58행) — herdr가 무엇을 언제 실행하는지. 모든 명령이 `sh bin/run.sh <서브커맨드>`다(`:13-58`). (코드 확인)
2. `bin/run.sh` — 바이너리 선택 순서: 이 체크아웃에서 빌드한 `target/release/herdr-projects`(소스가 더 새롭지 않을 때) → 내려받아 둔 `bin/herdr-projects-<os>-<arch>`(버전 ≥ `Cargo.toml`) → 지금 릴리스에서 다운로드(체크섬 검증) → 오래된 빌드·다운로드 순으로 `exec`(`run.sh:2-13`, `:22-24`, `:62-94`, `:105-107`). herdr 서버의 PATH에 사용자 PATH가 없을 수 있어 PATH를 보강한다(`:17`). (코드 확인)
3. `src/main.rs` → `src/cli/mod.rs` `run`(:56) — 서브커맨드 분기. herdr가 부르는 가벼운 입구(`hook`, `turn-ended`, `open`, `approve-current` 등)가 위쪽, 사람·에이전트가 쓰는 명령이 `src/cli/tasks.rs`다(`mod.rs:69-111`, `:112`). (코드 확인)
4. `crates/flow/src/hook.rs` — 이벤트가 상태로 바뀌는 곳. herdr 연동을 이해하는 핵심. (코드 확인)
5. `crates/core/src/herdr/{cli,api,socket}.rs` — herdr를 부르는 유일한 층(`cli.rs:1`: "The only file that runs the herdr program"). (코드 확인)
6. `crates/flow/src/delegate/` → `finish/` → `land/` — 위임부터 병합까지 태스크 한 개의 일생.
7. `crates/flow/src/coordinator/rules.rs` — Coordinator에게 주는 규칙 전문. 보드의 개념이 가장 압축된 곳.
8. 나머지(`board/`, `web/`, 확장 기능)는 필요할 때.

**크레이트·모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| `herdr-projects` (루트 패키지, 라이브러리 `sw`) | 서브커맨드 디스패치. herdr 진입점과 에이전트·사람용 명령을 한 바이너리로 묶음 | 입력: argv, 환경변수(`HERDR_PLUGIN_*`). 출력: stdout 텍스트/JSON, 종료코드. 아래 크레이트 호출 | `src/main.rs:2-5`, `src/cli/mod.rs` `main`(:48), `run`(:56), `src/cli/tasks.rs` `command`(:33) | 코드 확인 |
| sw-core (`crates/core`) | 데이터(`store/`), herdr 호출(`herdr/`), 에이전트 종류 표(`agents/`), 게이트 규칙(`gate.rs`), 음성 | herdr CLI·소켓 ↔ JSON, `~/.herdr-projects/` 아래 파일 | `crates/core/src/lib.rs:4-22`, `herdr/cli.rs:47-102`, `store/files.rs:29-46`, `agents/kinds.rs:33` | 코드 확인(목차·herdr 층·경로). `store/` 대부분과 `agents/` 파서는 미확인 |
| sw-flow (`crates/flow`) | 태스크 흐름 전부: 위임, 훅, 마감선, 병합, keeper, 원격, 자동화, 오토파일럿, 리뷰 페이지. 키 표·테마·웹 UI 위치 탐색도 여기(아래 크레이트가 쓰므로 내려 둠) | 입력: herdr 이벤트·사용자 명령·에이전트 턴 종료 보고. 출력: `task.json` 변경, herdr 호출, git/gh 명령, 러너 프로세스 | `crates/flow/src/lib.rs:1-59`, `docs/crates.md:29-43` | 코드 확인(목차). 하위 모듈 대부분은 위 지도의 수준을 따름 |
| sw-board (`crates/board`) | 터미널 보드 화면: 상태 `state.rs`, 키 반응 `update/`, 그리기 `view/`, 배치 `run/` | 입력: 키·마우스, `task.json`. 출력: 터미널 그림, 보드가 부르는 명령 | `crates/board/src/lib.rs:1-5`, `board/run/place.rs:1-5`, `docs/crates.md:11`, `AGENTS.md:33-36`(레포가 말하는 배치) | 코드 확인(크레이트 선언·배치). 화면 로직은 미확인 |
| sw-web (`crates/web`) | herdr 웹 UI 앞 front door와 웹 보드 | HTTP 요청 ↔ herdr 웹 UI로 통과, `/herdr-projects/` 아래 자체 페이지·호출 | `crates/web/src/lib.rs:1-5`, `webui/door.rs:1-12`, `door_loop.rs:89` | 코드 확인(door 서두). 페이지·모델은 미확인 |
| `herdr/` (core) | herdr CLI 실행·응답 해석(`run`), 세션 지정(`HERDR_SOCKET_PATH`), 소켓 직접 호출, 테스트용 가짜 herdr(`set_fake`) | CLI 인자 ↔ JSON `result`/`error` | `herdr/cli.rs:13-27`, `:47-59`, `:81-102`, `herdr/socket.rs:12-24`, `herdr/api.rs` `Herdr`(:6-239) | 코드 확인 |
| `flow/hook.rs` (flow) | herdr 이벤트를 받아 `task.json`을 갱신하고 마감선 러너를 띄움. 잠금 안에서는 herdr 호출·프로세스 시작을 하지 않고 `Then` 값으로 잠금 밖에서 실행 | 입력: `HERDR_PLUGIN_EVENT(_JSON)`, `agent get`. 출력: `finish`/`recover` 러너, 인박스 전달, 사이드바 갱신 | `hook.rs:26-42`, `:49-61`, `:72-200` | 코드 확인 |
| `flow/runner.rs`·`jobs.rs` (flow) | 긴 작업을 분리된 `herdr-projects run <job> <id>` 프로세스로 실행하고, `task.json`의 `runner` 마커로 중복을 막음 | 입력: job 이름·id. 출력: 로그 파일, `task.json` 갱신 | `runner.rs:38-51`, `:75-86`, `jobs.rs:8-39` | 코드 확인 |
| `flow/delegate/` (flow) | 위임 작업: worktree space 생성, 브랜치 이름 확정, 에이전트 시작 인자 구성, 첫 프롬프트 | herdr `worktree create`/`workspace create`/`agent start`, git `rev-parse`·`commit-tree` | `delegate/jobs.rs:59-120`, `worktree.rs:20-30`, `launch.rs:32-80`, `herdr/api.rs:40-46`, `:148-165` | 코드 확인(앞 120행). 이후 단계 미확인 |
| `flow/finish/`·`land/` (flow) | 턴 종료 판정 → 마감선 → 리뷰 → 승인 → 병합·정리 | 입력: 턴 종료 이벤트, 설정(`check.command`, `review.*`, `merge.*`). 출력: git·gh 명령, reviewer 에이전트 탭, 검증 파일 `verdict.json` | `pipeline.rs:46-120`, `pipeline_end.rs:39-70`, `review_once.rs:29-91`, `actions/finish_line.rs:28-65`, `land/merge.rs:20-62` | 코드 확인(앞부분). 후반부·재시도·한도는 미확인 |
| `flow/coordinator/` (flow) | Coordinator 상태 파일, 규칙 파일 기록, 시작·메시지 입력 pump, herdr 탭 배치 | 입력: 사람이 적은 말(`requests.rs`). 출력: 폴더의 `AGENTS.md` 블록, 에이전트 시작, pane 입력 | `rules.rs:22-78`, `pump.rs:46-110`, `co.rs:1-4`, `place.rs:1-5` | 코드 확인(규칙·pump 앞부분) |
| `core/agents/` (core) | 에이전트 종류별 시작 인자·훅·재개·대화 파일 위치를 한 표로 선언 | 입력: 종류 이름. 출력: 인자 배열, 훅 설정 파일 | `kinds.rs:1-33`, `adapter.rs:13-75` | 코드 확인(표 구조·`hook_args`). 종류별 값은 `docs/agents.md` 표를 후보로만 봄 |
| `store/` (core) | 태스크·설정·리뷰·인박스 등을 파일로 저장·잠금 | `~/.herdr-projects/{data,settings,reports}` | `store/files.rs:29-46`, `store/tasks.rs:33-61` | 코드 확인(경로·목록). 잠금·마이그레이션은 미확인 |

**실행 흐름: 위임한 태스크 하나의 일생** (코드 확인 구간과 미확인 구간을 구분)
1. 사람이 `add ... --delegate` 또는 보드에서 Tab → `start::delegate` → `stage: starting`(`src/cli/tasks.rs:46-73`, `actions/start.rs`). 코드 확인(호출 연결). 슬롯·큐 판정 본문은 미확인.
2. `delegate` 러너: 저장소면 `herdr worktree create --cwd <repo> --branch work/... --base <sha> --no-focus`, 아니면 `workspace create`; 링크 정보를 `task.json`의 `link`에 기록(`delegate/jobs.rs:94-120`, `:48-53`, `herdr/api.rs:40-46`). 코드 확인.
3. 에이전트 시작: 훅 인자·표준 규칙 파일 인자를 만들어 `herdr agent start <name> --kind <k> --pane <p> -- <인자>`(`delegate/launch.rs:32-80`, `herdr/api.rs:148-165`). 코드 확인. 첫 프롬프트 전달(`submit.rs`)은 머리 주석(:1-4)까지만 확인(추론).
4. 에이전트가 일하는 동안 herdr 이벤트마다 `hook`이 `last`·`workedAt` 등을 갱신한다(`hook.rs:91-139`). 코드 확인.
5. 에이전트 턴이 끝나면 두 경로가 `finish` 러너를 띄운다. 에이전트 자신의 훅(`turn-ended`, `turn.rs:30-59`) 또는 herdr의 idle/done 상태(`hook.rs:140-171`). 코드 확인.
6. `finish` → `pipeline`: 커밋(`pipeline.rs:64-67`) → main 합치기(`:72-85`) → setup(`:100-106`) → 검사 명령(`:112-`) → 리뷰(`pipeline_end.rs:62-63`, reviewer는 task space의 별도 탭에서 에이전트로 시작 `review_once.rs:73-91`, 결과는 `verdict.json` `:41`). 코드 확인(해당 줄까지). push·PR·리뷰 실패 시 되돌림 루프 본문은 미확인.
7. 통과하면 `approval` 대기, 설정이 `merge.by itself`면 자동 병합(`pipeline_end.rs:1-2` 머리 주석, `auto_merge.rs:1-4`). 추론.
8. 사람이 `approve` → `stage: merging` + `land` 러너(`finish_line.rs:54`, `:62`) → `land_job`(`land/merge.rs:20-31`) → `landed`에서 `stage: done`·정리(`:48-62`). 코드 확인.

**미확인 영역**
- 이 분석은 실행하지 않았다. 따라서 `실행 확인`은 없다. herdr 0.9.3과 실제로 맞물리는지, 릴리스 다운로드, 에이전트 시작, 리뷰·병합의 동작은 코드·문서 주장만 있다.
- `docs/checked-on-herdr.md`는 herdr 동작을 실측했다고 적은 표다. 그 값은 이 분석에서 재현하지 못했으므로 `미확인`(외부 시스템 동작, 7장 규칙).
- 보드 화면·웹 보드·확장 워크플로·원격·음성·자동화의 본문(위 미탐색 목록).

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음에 볼 곳**:
  1. `flow/finish/pipeline.rs` 120행 이후와 `finish/review.rs`·`pipeline_end.rs` 후반 — push·PR 생성, 리뷰 실패 시 에이전트에 되돌리는 루프, 한도·fallback. README의 "draft PR"·"둘째 에이전트 리뷰" 주장을 코드로 확정.
  2. `flow/hook/reconcile.rs`, `flow/live.rs`, `store/marks.rs` — herdr가 놓친 이벤트를 어떻게 보정하는지(`hook.rs:4-6`은 "herdr는 놓친 이벤트를 다시 보내지 않는다"고 적음).
  3. `store/settings_list.rs`·`store/settings/lookup.rs` — 설정 조회 순서(태스크 → 레포 개별 → 사용자 → 레포 파일 → 내장, `coordinator/rules.rs:41` 서술)를 코드로 확인.
  4. `board/update/`·`state.rs` — 다섯 묶음 판정과 키 표(`flow/board/keys.rs`)가 한 목록에서 갈라지는 구조.
- **다음 세션 계획**: next.md는 아직 없음(사용자 지시는 overview까지).
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(전부 미작성).
