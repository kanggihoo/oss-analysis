---
sha: "7a215a179acb4e098dd1c2971332497806309360"
created: 2026-11-06
updated: 2026-11-06
sources:
  - herdr-plugin.toml
  - Cargo.toml
  - README.md
  - AGENTS.md
  - schema.sql
  - SCHEMA-DIFF-0.9.0.md
  - skill/SKILL.md
  - docs/README.md
  - docs/protocol.md
  - docs/herdr.md
  - docs/releasing.md
  - docs/sandbox.md
  - scripts/build.sh
  - scripts/install-cli.sh
  - scripts/install.sh
  - scripts/open-board.sh
  - .github/workflows/release.yml
  - .agents/skills/development-workflow/SKILL.md
  - docker/Dockerfile
  - e2e/README.md
  - crates/board-cli/src/main.rs
  - crates/board-cli/src/daemon.rs
  - crates/board-cli/src/scope.rs
  - crates/board-cli/src/helpers.rs
  - crates/board-cli/src/commands/run.rs
  - crates/board-cli/src/args/mod.rs
  - crates/board-cli/src/args/board.rs
  - crates/board-cli/src/args/project.rs
  - crates/board-cli/src/args/run.rs
  - crates/board-core/src/protocol.rs
  - crates/board-core/src/paths.rs
  - crates/board-core/src/scope.rs
  - crates/board-core/src/config.rs
  - crates/board-core/src/prompt.rs
  - crates/board-core/src/harness/mod.rs
  - crates/board-core/src/engine/signals.rs
  - crates/board-core/src/engine/transitions.rs
  - crates/board-core/src/client/unix.rs
  - crates/board-core/src/db/migrations.rs
  - crates/board-herdr/src/lib.rs
  - crates/board-herdr/src/client.rs
  - crates/board-herdr/src/transport.rs
  - crates/board-herdr/src/events/mod.rs
  - crates/board-herdr/src/events/parse.rs
  - crates/board-herdr/src/events/stream.rs
  - crates/board-daemon/src/lib.rs
  - crates/board-daemon/src/server.rs
  - crates/board-daemon/src/session.rs
  - crates/board-daemon/src/settings.rs
  - crates/board-daemon/src/herdr_conn.rs
  - crates/board-daemon/src/state.rs
  - crates/board-daemon/src/ops/mod.rs
  - crates/board-daemon/src/ops/boards.rs
  - crates/board-daemon/src/ops/cards.rs
  - crates/board-daemon/src/ops/runs.rs
  - crates/board-daemon/src/ops/panes.rs
  - crates/board-daemon/src/ops/discovery.rs
  - crates/board-daemon/src/dispatch/pass.rs
  - crates/board-daemon/src/dispatch/enqueue.rs
  - crates/board-daemon/src/dispatch/launch_plan.rs
  - crates/board-daemon/src/dispatch/finalize.rs
  - crates/board-daemon/src/spawner/herdr/mod.rs
  - crates/board-daemon/src/spawner/herdr/managed.rs
  - crates/board-daemon/src/spawner/herdr/configured.rs
  - crates/board-daemon/src/watchers/herdr.rs
  - crates/board-daemon/src/watchers/signals.rs
  - crates/board-tui/src/lib.rs
  - crates/board-tui/src/runtime.rs
  - crates/board-tui/src/origin.rs
  - crates/board-tui/src/driver/dispatch.rs
---

# herdr-board Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/nelsonPires5/herdr-board` (`herdr-plugin/artifacts/herdr-board/repo-metadata.txt`, branch `main`, 커밋일 2026-10-14)
- **작업트리 상태**: Clean (`git clone --depth 50`, 2026-11-06)
- **분석 목적**: 학습 · 도입 검토. (1) herdr 플러그인이 매니페스트(`herdr-plugin.toml`)와 herdr 소켓·CLI·환경변수로 herdr와 어떻게 연동하는지, (2) 카드(프롬프트)를 컬럼(파이프라인 단계)으로 옮기면 에이전트가 실행되는 칸반 보드의 기능, (3) 같은 태스크 보드 계열인 [herdr-projects](../herdr-projects/overview.md)와의 차이를 본다.
- **라이선스**: **LICENSE 파일이 없다.** `git ls-files | grep -iE 'licen|copying'` 결과가 비어 있고(루트·하위 크레이트 모두), 선언은 `Cargo.toml:14`의 `[workspace.package] license = "MIT"` 한 줄뿐이다. 다섯 크레이트가 이를 상속한다(`crates/*/Cargo.toml:5` `license.workspace = true`). README·`docs/`·`skill/`·`herdr-plugin.toml`에는 라이선스 문구가 없다(추적 파일에서 `MIT`·`license`를 찾은 결과는 `Cargo.toml` 계열, 아래 두 곳, 테스트 픽스처 `scripts/tests/test_prepare_release.py:51`뿐이고 `Cargo.lock`·`docs/herdr-0.9.0-schema.json`은 제외했다). 아래 두 곳은 "LICENSE 파일이 있으면 릴리스 tarball에 넣는다"는 처리일 뿐 파일이 있다는 뜻이 아니다: `.github/workflows/release.yml:182-184`(LICENSE·LICENSE.md·LICENSE-MIT·LICENSE.txt가 있으면 복사), `docs/releasing.md:157`("any license file present at build time"). 따라서 MIT는 **Cargo.toml이 선언한 값**이지 저작권자·연도·조건 전문이 확인된 라이선스가 아니다. 코드를 가져다 쓰려면 저장소 주인에게 확인해야 한다. (코드 확인)
- **분석 대상 제품**: 추적 파일 493개. 배포 단위는 하나, 즉 매니페스트 `herdr-plugin.toml`(버전 0.19.1, `:13`) + 빌드 스크립트 + Rust 바이너리 `board`(TUI·데몬·CLI를 한 파일로 묶음, `crates/board-cli/src/main.rs:88-116`)다. 워크스페이스 버전도 0.19.1(`Cargo.toml` `[workspace.package]`)이다.

  | 영역 | 추적 파일 수 | 맡은 일 |
  |---|---|---|
  | `crates/board-core` | 67 (소스 37 · 테스트 29) | 모델, `protocol.rs`(데몬 소켓 프로토콜 타입), SQLite 접근·마이그레이션(`db/`), 순수 컬럼 엔진(`engine/`), 프롬프트 조립, 하니스 어댑터(`harness/`), 설정, 데몬 클라이언트(`client/`) |
  | `crates/board-herdr` | 20 (소스 11 · 테스트 8) | herdr 유닉스 소켓 클라이언트: 요청·응답 호출 24종, 이벤트 스트림 |
  | `crates/board-daemon` | 89 (소스 47 · 테스트 41) | `boardd`: 소켓 서버, 실행 대기열·디스패치, pane 배치(spawner), 감시(watchers), 복구 |
  | `crates/board-tui` | 141 (소스 35 · 테스트 105) | ratatui 칸반 화면: 순수 상태기계 `app/`, 효과 실행 `driver/`, 그리기 `view/`, 폼 `forms/` |
  | `crates/board-cli` | 42 (소스 22 · 테스트 19) | `board` 바이너리: clap 서브커맨드, 데몬 자동 시작 |
  | `schema.sql`, `SCHEMA-DIFF-0.9.0.md` | 1, 1 | 새 DB의 SQLite 스키마(v15). `SCHEMA-DIFF-0.9.0.md`는 DB가 아니라 **herdr 소켓 API 스키마**의 0.8.2→0.9.0 차이 기록이다 |
  | `docs/` | 19 (이미지 5) | 설계·프로토콜·설정·설치·릴리스·테스트 문서, herdr 소켓 스키마 덤프 `herdr-0.9.0-schema.json` |
  | `skill/SKILL.md` | 1 | `board skill`이 그대로 출력하는, 에이전트·사람용 사용법 (3절 참고) |
  | `e2e/` | 60 | 실제 herdr를 띄워 보는 시나리오 40개(`01-core.sh`~`40-installed-harnesses.sh`)와 보조 파일 |
  | `docker/`, `scripts/sandbox.sh` | 13, (scripts 19 중 1) | 개발용 격리 컨테이너 |
  | `scripts/`, `.github/`, `.agents/` | 19, 8, 4 | 빌드·설치·launcher·릴리스 스크립트, CI·릴리스 워크플로, 개발자용 스킬 |
  | 루트 문서·설정 | 10 | README, AGENTS, CONTRIBUTING, CHANGELOG, Cargo.toml/lock, .gitignore 등 |

  (파일 수는 `git ls-files`를 디렉터리별로 센 값이고, 소스/테스트 구분은 파일 이름 규칙 `tests/`·`tests.rs`·`testkit`·`examples/`로 나눈 근사값이다. 합계 493. 코드 확인)
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지) · 제외: 없음(승인 전)

---

## 2. 프로젝트 개요

**용어 먼저.**
- *herdr*는 코딩 에이전트용 터미널 멀티플렉서다. *workspace*는 작업 공간, *tab*은 그 안의 탭, *pane*은 탭 안의 터미널 하나다. herdr는 이름 붙은 *session*을 여러 개 띄울 수 있고, session마다 소켓 파일이 따로 있다. 이름 붙은 session의 소켓이 `.../sessions/<이름>/herdr.sock`이라는 것은 board 코드의 가정이다(`crates/board-core/src/paths.rs:57-69`).
- *herdr 소켓*은 herdr 서버가 여는 유닉스 소켓이다. 한 줄 JSON `{"id","method","params"}`를 보내면 한 줄 JSON `{"id","result"}` 또는 `{"id","error"}`가 돌아온다. 이 줄 단위 JSON 형식을 *NDJSON*이라 한다(`crates/board-herdr/src/lib.rs:1-6`). herdr *CLI*는 같은 서버를 셸 명령(`herdr pane list` 등)으로 부르는 방법이다.
- *하니스(harness)*는 카드 하나를 실제로 수행하는 코딩 에이전트 프로그램이다(`pi`, `claude`, `codex`, `opencode`, `antigravity`가 내장, `crates/board-core/src/harness/mod.rs:23`).
- *카드*는 제목·프롬프트(description)·하니스 설정·대상 herdr session/workspace를 가진 보드의 항목이다. *컬럼*은 파이프라인 단계로, 진입 방식이 `auto`(들어오면 에이전트 실행)와 `manual`(사람이 기다림) 중 하나다(`schema.sql:71-88`). *run*은 카드가 `auto` 컬럼에서 에이전트를 한 번 실행한 기록이다(`schema.sql:155-176`).
- *`boardd`*는 이 플러그인의 상주 데몬이다. 단일 SQLite 쓰기 주체이자 실행 대기열 소유자이며, TUI와 CLI는 이 데몬의 소켓에 NDJSON으로 요청한다(`crates/board-daemon/src/lib.rs:1-5`). *board 소켓*은 데몬의 소켓, *herdr 소켓*은 위의 herdr 소켓이다. 아래에서 두 소켓을 이 이름으로 구분한다.

README는 이 레포를 "칸반 카드를 보이는 herdr pane에서 도는 실제 AI 코딩 에이전트로 바꾼다"고 소개한다(`README.md:8-10`). 코드와 맞춘 결과는 아래와 같다.

- **세 인터페이스가 한 바이너리**다. `board tui`는 TUI, `board daemon`은 데몬, 나머지 서브커맨드는 CLI이고, 모두 `board-cli`의 `main.rs`가 갈라 준다(`main.rs:88-116`). TUI와 CLI는 데몬에 board 소켓으로 요청하고, **데몬이 herdr 쪽 호출을 전부 맡는다**(`docs/protocol.md`의 "Client boundary" 절의 주장이고, 코드로는 TUI가 herdr 연결을 직접 열지 않고 `pane.set_title`·`run.focus` 요청으로 데몬에 위임함을 확인: `board-tui/src/driver/dispatch.rs:270-291`, `:293-322`). (코드 확인)
- **herdr와의 연동은 소켓이 중심**이다. `board-herdr` 크레이트가 herdr 소켓 호출 24종(`ping`, `workspace.*`, `tab.*`, `agent.*`, `pane.*`, `notification.show`, `session.snapshot`, `integration.list`; `crates/board-herdr/src/client.rs:41-69`)과 이벤트 스트림 `events.subscribe`를 감싼다. herdr CLI를 부르는 곳은 `herdr session list --json`(`board-daemon/src/session.rs:141-148`)과 `herdr pane run`(`spawner/herdr/configured.rs:83-95`) 둘이고, 나머지 CLI 호출은 launcher·설치 스크립트에 있다. (코드 확인)
- **매니페스트에 이벤트 훅이 없다.** `herdr-plugin.toml`에는 `[[build]]` 2개, `[[panes]]` 1개, `[[actions]]` 1개만 있고 `[[events]]`·`[[startup]]`은 없다(`herdr-plugin.toml:20-45`). 에이전트 상태 변화는 데몬이 `events.subscribe`로 herdr 소켓에 직접 구독해 받는다(`board-herdr/src/events/stream.rs:61-91`, `board-daemon/src/watchers/herdr.rs:267-277`). (코드 확인)
- **상태는 SQLite에 있다.** `~/.local/share/herdr-board/board.db`와 `boardd.sock`(`board-core/src/paths.rs:8-37`)이고, 스키마는 11개 테이블이다(`schema.sql`). 머리 주석(`schema.sql:1-4`)과 상수 `SCHEMA_VERSION`(`migrations.rs:11`)이 모두 v15를 가리킨다. (코드 확인)
- **완료의 기준은 에이전트의 `board done`**이다. 데몬이 에이전트 프롬프트에 "`board comment`를 쓰고 `board done --outcome ok`로 끝내라"는 규칙을 항상 덧붙이고(`harness/mod.rs:322-330`, `prompt.rs:13-18`), herdr가 알려 주는 `idle`·`done` 상태는 힌트일 뿐 run을 `ok`로 끝내지 않는다(`engine/signals.rs:6-9`, `:45-103`). `board done` 없이 에이전트가 끝나면 카드는 `awaiting`(사람 확인 대기)이 된다. (코드 확인)
- README가 말하는 "하나의 데몬이 여러 herdr session에 걸쳐 디스패치"는 `herdr session list --json` 결과를 캐시해 session 이름을 소켓 경로로 바꾸는 `SessionRegistry`로 구현돼 있다(`session.rs:120-133`, `:212-248`). (코드 확인)

### 기능 지도 (feature map)

<!--
OSS_ANALYSIS_WORKFLOW.md 2장 4번. 한 행 = 스펙 하나의 작업 단위. 이번에는 지도만(스펙 미작성).
상태는 전부 "미작성"(파일 없음, 경로는 코드 표기).
검증 수준: 진입점·호출을 읽었으면 "코드 확인", 머리 주석·문서만 봤으면 "추론", 열지 않았으면 "미확인".
-->

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 플러그인 입구 (매니페스트 → 빌드 → 오버레이 pane·launcher) | 설치 때 herdr가 `[[build]]` 두 명령을 실행하고, 사용자는 `open-board` 액션이나 키바인딩으로 오버레이 pane을 연다. launcher는 pane 목록을 보고 열기·포커스·닫기를 고른다(같은 키를 다시 누르면 닫힘). 제외: herdr가 매니페스트를 읽는 쪽 | `herdr-plugin.toml:20-45`, `scripts/open-board.sh:19-77`(`open_pane` :21, 결정 :31-63), `scripts/build.sh:20-34`, `scripts/install-cli.sh:14-26`, `:74-77` | 없음 | 핵심 | `capabilities/plugin-entry.md` · 미작성 | 코드 확인(매니페스트·스크립트 3개). herdr가 이렇게 실행하는지는 미확인 |
| 데몬 수명과 소켓 서버 | 아무 `board` 명령이나 board 소켓에 못 붙으면 데몬을 자동으로 띄우고 3초간 재시도한다. `board daemon start/stop/status`, `board version`. 같은 DB를 쓰는 데몬은 하나만 산다(`flock`). 소켓 권한 0600 | `board-cli/src/daemon.rs` `connect_or_start`(:16), `spawn_daemon`(:37), `daemon_command`(:63), `stop_daemon`(:143), `board-daemon/src/lib.rs` `run`(:60), `async_main`(:81), `bind_secured_socket`(:281; 권한 :217-219), `singleton.rs`, `server.rs` `serve`(:167), `handle_conn`(:193), `dispatch_request`(:282) | 없음 | 핵심 | `capabilities/daemon-lifecycle.md` · 미작성 | 코드 확인(자동 시작·서버·종료). 시작 시 복구 `recovery.rs`는 머리 주석만(추론) |
| boardd 프로토콜 (요청 라우팅·이벤트 구독·오류 코드) | NDJSON 요청 44종과 `events.subscribe`. 요청 하나가 응답 하나, 구독 연결은 `board_changed`·`run_ended` 이벤트를 받고 느리면 끊김. 오류 코드 1~5 | `board-daemon/src/ops/mod.rs` `routes!`(:31, 표 :51-101), `board-core/src/protocol.rs`(`Request`/`Response` :246-, `Event` :336-, `DaemonStatus` :361), `server.rs` `Outbox`(:106), `spawn_event_forwarder`(:348), `board-core/src/client/unix.rs` `subscribe`(:162) | 데몬 수명 | 핵심 | `capabilities/daemon-protocol.md` · 미작성 | 코드 확인(라우팅 표 전체·서버·구독 핸드셰이크). 메서드별 파라미터 타입은 일부만 읽음 |
| 데이터 모델·저장소 | project(Git 루트 또는 현재 디렉터리) 아래에 이름 있는 board 여러 개, board 아래 column·card·comment·run. 댓글 수정 이력, 카드당 열린 run 하나 | `schema.sql:13-184`(제약 `idx_runs_one_open_per_card` :182), `board-core/src/db/migrations.rs` `SCHEMA_VERSION`(:11), `migrate`(:314), `board-core/src/scope.rs` `select_scope_candidate`(:21), `resolve_scope_path`(:44) | 없음 | 핵심 | `capabilities/data-model.md` · 미작성 | 코드 확인(`schema.sql` 전체·마이그레이션 진입). `db/*.rs` 쿼리 본문과 v1~v14 단계는 미확인 |
| 보드·카드·컬럼·코멘트 조작 (CLI ↔ RPC) | `board board/project/card/column/harness/space/session ...`, 카드 생성·이동·복제·보관·삭제, 코멘트 추가·수정·이력, `board template apply pipeline`, `--json` 출력과 종료 코드. 레거시 최상위 명령(`comment`, `done`, `move`, `cancel`, `retry`)은 같은 핸들러로 다시 들어감 | `board-cli/src/main.rs` `dispatch`(:84-151), `args/mod.rs` `Cmd`(:47-), `args/card.rs`·`column.rs`·`board.rs`·`project.rs`, `board-daemon/src/ops/{boards,projects,cards,columns,comments}.rs`, `ops/boards.rs` `template_apply`(:135), `ops/cards.rs` `card_create`(:68), `card_move`(:264), `board-cli/src/scope.rs` `current_scope_path`(:6), `context_board`(:33) | 데이터 모델, 데몬 프로토콜 | 핵심 | `capabilities/board-commands.md` · 미작성 | 코드 확인(명령 목록·카드 생성/이동 경로·템플릿). 컬럼·코멘트·보드 핸들러 본문은 미확인 |
| 컬럼 엔진 (진입·전이·신호 결정) | 카드가 컬럼에 들어올 때 큐에 넣을지, run이 끝나면 `on_success`/`on_fail` 중 어디로 보낼지, herdr 상태 신호로 카드 상태를 어떻게 바꿀지를 순수 함수로 결정 | `board-core/src/engine/transitions.rs` `decide_entry`(:148), `decide_transition`(:85), `decide_auto_hop`(:19), `engine/signals.rs` `decide_signal`(:45), `engine/lifecycle.rs` `decide_lifecycle`(:67), `engine/validation.rs` | 데이터 모델 | 핵심 | `capabilities/column-engine.md` · 미작성 | 코드 확인(`transitions.rs` 60~200행, `signals.rs` 전체). `lifecycle.rs`·`validation.rs`·`archive.rs` 본문은 미확인 |
| 실행 대기열·디스패치 | `auto` 컬럼에 들어온 카드의 run이 큐에 쌓이고, 전체 동시 실행 수(기본 3)와 공간(workspace)별 FIFO를 지켜 하나씩 꺼내 실행. run은 enqueue 시점의 argv·env·프롬프트를 스냅샷으로 저장 | `dispatch/pass.rs` `dispatch_pass`(:16), `dispatch/enqueue.rs` `enqueue_run`(:35), `prepare_enqueue_values`(:97), `dispatch/launch_plan.rs` `spawn_one`(:72), `board_env`(:33), `dispatch/space.rs` `resolve_space`, `board-core/src/launch.rs`, `board-core/src/config.rs`(`max_concurrent` 기본값 :9-11) | 컬럼 엔진, 하니스 어댑터 | 핵심 | `capabilities/dispatch-queue.md` · 미작성 | 코드 확인(pass·enqueue·spawn_one 앞 330행). 실패 처리 후반·`space.rs` 본문·`ownership.rs`는 미확인 |
| herdr 소켓 클라이언트와 호환 게이트 | herdr 소켓의 프로토콜 번호가 22가 아니면 배치·실행·알림·포커스 전에 거절하고, 버전이 0.9.0과 다르면 경고만. 연결은 요청마다 새로 열고, 이벤트 구독만 별도 연결 | `board-herdr/src/lib.rs`(`SUPPORTED_HERDR_PROTOCOL` :37), `client.rs` `call_inner`(:154), `require_supported_protocol`(:239), `transport.rs` `default_socket_path`(:28), `events/stream.rs` `watch_subscriptions`(:87), `HerdrEvents::connect`(:110), `events/parse.rs` `parse_event_line`(:48), `board-daemon/src/herdr_conn.rs` `connect_checked`(:20) | 없음 | 핵심 | `capabilities/herdr-client.md` · 미작성 | 코드 확인(전송·요청·게이트·구독·파서). `types.rs`·`params.rs` 필드는 미확인, herdr 서버 쪽 동작은 미확인 |
| 에이전트 pane 배치·실행 (spawner) | 카드마다 `card-<id>` 탭을 만들고 그 안에서 에이전트를 시작한다. 관리형(`pi`·`claude`·`codex`·`opencode`·`antigravity`)은 `agent.start`+`agent.prompt`, 설정으로 정의한 하니스는 `herdr pane run`으로 셸 스크립트를 실행. 같은 대화를 잇는 단계는 이전 pane에 프롬프트만 다시 보냄. 로컬 자식 프로세스 spawner(`BOARD_SPAWNER=local`)는 경계만 | `spawner/herdr/mod.rs` `spawn_inner`(:110), `spawner/herdr/managed.rs` `launch_managed`(:57), `launch_managed_prompt_file`(:466), `spawner/herdr/configured.rs` `launch_configured`(:43), `configured_script`(:121), `spawner/placement/alloc.rs` `allocate_owned_pane`(:83), `allocate_card_pane`(:171), `create_card_tab`(:449), `spawner/card_tabs.rs`, `spawner/local.rs` | 디스패치, herdr 클라이언트 | 핵심 | `capabilities/pane-launch.md` · 미작성 | 코드 확인(`spawn_inner`·관리형 pi/claude 경로·configured 경로). codex·opencode·agy 세션 캡처와 `alloc.rs` 본문은 미확인 |
| herdr 이벤트 관찰·상태 반영 | herdr의 에이전트 상태(`working`·`blocked`·`done`·`idle`)와 pane 종료 이벤트를 받아 카드 상태를 바꾸고, 정해진 시간 넘기면 실패, idle이 90초(기본) 이어지면 `awaiting`. 놓친 이벤트는 주기적 스냅샷으로 보정. 사람이 볼 알림은 `notification.show` | `watchers/herdr.rs` `herdr_event_thread`(:267), `handle_event_from_socket`(:352-431), `watchers/signals.rs` `apply_signal`(:28), `watchers/timeout.rs` `timeout_ticker`(:19), `state.rs` `refresh_watch`(:315), `notify`(:289), `supervisor.rs`, `recovery.rs` | herdr 클라이언트, 컬럼 엔진 | 핵심 | `capabilities/event-watch.md` · 미작성 | 코드 확인(이벤트 처리·신호 적용·감시 목록). `supervisor.rs`·`recovery.rs` 본문과 타이머 세부는 미확인 |
| 에이전트 보고 채널 (`board comment`·`board done`) | 데몬이 에이전트 환경에 `BOARD_CARD_ID`·`BOARD_RUN_ID`·`BOARD_SOCKET`·`BOARD_BIN`을 넣고, 에이전트는 `board comment`로 결과를 남긴 뒤 `board done --outcome ok/fail`로 run을 닫는다. 같은 pane을 단계 사이에 재사용하면 `HERDR_PANE_ID`로 호출자를 확인. 닫히면 `on_success`/`on_fail` 컬럼으로 이동 | `board-cli/src/commands/run.rs` `cmd_done`(:64), `cmd_comment`(:16), `board-cli/src/helpers.rs` `env_card_id`(:39), `actor_run_id`(:46), `actor_pane_id`(:67), `board-daemon/src/ops/runs.rs` `run_done`(:9), `dispatch/finalize.rs` `finalize_run`(:25), `board-core/src/harness/mod.rs` `BOARD_PROTOCOL_TRAILER`(:322), `prompt.rs` `PROMPT_CLOSEOUT`(:13) | 디스패치, 컬럼 엔진 | 핵심 | `capabilities/agent-reporting.md` · 미작성 | 코드 확인(CLI 쪽·`run_done`·`finalize_run` 전이 호출). `finalize_run_inner` 후반과 `comments.rs` 권한 검사는 미확인 |
| 하니스 어댑터 패밀리 (pi·claude·codex·opencode·antigravity + 설정 정의) | 카드·컬럼 설정(하니스·모델·effort·권한)을 합쳐(컬럼 override 우선) 하니스별 시작 인자와 프롬프트로 바꾼다. 세션은 새로 만들기·이어가기·재시도 때 갈라 쓰기 중 하나. 모델 목록은 하니스별 카탈로그(일부는 라이브 조회). `herdr integration.list`로 설치된 하니스만 선택지에 | `board-core/src/harness/mod.rs` `plan_session`(:44), `build_invocation_for_card`(:465), `pi_argv`(:391), `claude_argv`(:352), `harness/{codex,opencode,agy}.rs`, `prompt.rs` `effective_settings`(:54), `board-core/src/{pi,codex,opencode,agy}_catalog.rs`, `capability.rs`, `board-daemon/src/ops/discovery.rs`(:10-20) | 데이터 모델 | 핵심 | `capabilities/harness-adapters.md` · 미작성 | 코드 확인(`plan_session`·`protocol_system_prompt`·`installed_targets`). 하니스별 인자 조립과 카탈로그 본문은 미확인(추론: `claude_argv` 문서 주석) |
| 터미널 칸반 (TUI) | `board tui`(오버레이 pane의 명령). 컬럼·카드 보기, 폼으로 카드·컬럼 만들기·수정, 이동 선택·드래그, 상세·코멘트·run 이력, 프로젝트·보드 전환, 3단계 레이아웃(좁은 화면 Compact). 데몬 이벤트가 오면 다시 불러옴. 키·화면은 경계만 | `board-tui/src/lib.rs`(계층 표 :11-20), `runtime.rs` `run_with_board`(:57), `event_loop`(:112), `supervise_subscription`(:182), `origin.rs` `OriginContext`(:9-32), `driver/dispatch.rs` `set_pane_title`(:279), `focus_run`(:293), `app/effect.rs` `Effect`, `view/mod.rs` `LayoutMode`(:80) | 데몬 프로토콜 | 핵심 | `capabilities/terminal-board.md` · 미작성 | 코드 확인(진입·구독 감독·origin·pane 위임). `app/`(16파일)·`view/`·`forms/` 본문은 미확인 |
| run 포커스·죽은 pane 되살리기 (`run.focus`) | `o` 키·`board card run focus`로 run의 pane에 포커스. pane이 사라졌으면 같은 대화를 새 pane에서 이어 열되 DB에는 아무것도 쓰지 않음(추적 안 되는 임시 pane) | `board-daemon/src/rescue.rs` `focus_run`(:26), `spawner/rescue.rs`, `board-cli/src/commands/run.rs`(:105-139), `board-core/src/protocol.rs` `RunFocusAction`(:888) | 에이전트 pane 배치 | 부속 | `capabilities/run-focus-rescue.md` · 미작성 | 추론(머리 주석)과 CLI 출력 문구만 읽음 |
| 진단 로그 | 데몬이 일 단위 NDJSON 로그를 쓰고 오래된 파일을 정리. 요청·herdr 호출은 메서드명·소요 시간·결과 코드만 기록 | `board-daemon/src/logging.rs`(머리 주석 :1-14), `board-core/src/paths.rs` `log_dir`(:40), `board-herdr/src/client.rs` `call_decoded`(:130-152) | 데몬 수명 | 부속 | `capabilities/diagnostics.md` · 미작성 | 코드 확인(herdr 호출 로그 필드). 보존·회전 로직은 추론 |
| 에이전트용 사용법 문서 (`skill/SKILL.md`) | `board skill`이 `skill/SKILL.md`의 바이트를 그대로 출력(컴파일 때 포함). 카드·run·코멘트·컬럼 사용법과 종료 코드 규칙. 개발자용 `.agents/skills/development-workflow`와는 별개 | `board-cli/src/main.rs` `print_skill`(:176-179), `skill/SKILL.md`(frontmatter :1-10, 목차 :12-330), `scripts/install.sh:68-69`(`~/.claude/skills`로 복사) | 보드 조작 | 부속 | `capabilities/agent-skill-doc.md` · 미작성 | 코드 확인(출력 경로). 문서 본문은 CLI 목록과 대조한 항목만 확인 |
| 설치·릴리스 도구 | CLI를 `~/.local/bin/board`로 안전하게 복사(소유 마커+SHA-256), 개발용 `install.sh`(플러그인 링크·스킬 복사·키바인딩 추가), Prepare Release → Promote → Release 워크플로 | `scripts/install-cli.sh:74-243`, `scripts/install.sh:64-92`, `.github/workflows/release.yml:176-184`, `docs/releasing.md` | 플러그인 입구 | 부속 | `capabilities/install-release.md` · 미작성 | 코드 확인(`install-cli.sh`·`install.sh`). 워크플로 나머지·릴리스 절차는 추론(문서 기준) |
| 개발 샌드박스·e2e | Docker 컨테이너(네트워크 끔, 비루트, 저장소는 읽기 전용)에서 모든 게이트와 실제 herdr를 띄우는 e2e 시나리오 40개를 가짜 에이전트로 실행. 호스트의 herdr·데몬·DB는 건드리지 않음 | `scripts/sandbox.sh`(서브커맨드 :628-640), `docker/Dockerfile:1-30`, `docker/gates.sh`, `e2e/README.md`, `e2e/lib.sh`, `.agents/skills/development-workflow/SKILL.md` | 없음 | 부속 | `capabilities/dev-sandbox-e2e.md` · 미작성 | 추론(문서·머리 주석). 스크립트 본문과 시나리오는 열지 않음 |

(핵심 13 · 부속 5, 합 18행)

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| **매니페스트 선언**: `[[build]]` 2개, `[[panes]]` `board`(`placement = "overlay"`, 명령 `./target/release/board tui`), `[[actions]]` `open-board`(`bash scripts/open-board.sh`). `[[events]]`·`[[startup]]` 없음. `min_herdr_version = "0.9.0"`, `platforms = ["linux","macos"]` | 플러그인 입구, TUI, 설치 도구 | `herdr-plugin.toml:11-45` | `plugin-entry` 행에 포함 · 미작성 | 코드 확인 |
| **boardd 소켓 프로토콜 v1**: NDJSON, 요청 `{"id","method","params"}`, 응답 `{"id","result"|"error":{code,kind?,message,details?}}`. 오류 코드 1 잘못된 요청, 2 없음, 3 잘못된 상태, 4 herdr 불가, 5 내부(`docs/protocol.md:8-30`의 서술. 코드로는 `server.rs:21-23`의 코드 5와 `main.rs:190-204`의 종료 코드 매핑만 대조했고, 코드 1~4를 만드는 `board_core::Error::code`는 열지 않아 미확인). 구독 연결은 `{"subscribed":true}` 응답 뒤 `id` 없는 이벤트 줄 | CLI, TUI, 데몬, 에이전트 보고 | `board-core/src/protocol.rs:246-380`, `server.rs:193-271`, `board-core/src/client/unix.rs:162-` | `daemon-protocol` 행에 포함 · 미작성 | 코드 확인 |
| **herdr 소켓 프로토콜 22 (소비 쪽)**: 프로토콜 번호 22만 허용(`ping` 응답 `protocol`과 비교), 요청마다 새 연결(herdr가 응답 뒤 연결을 닫는다고 가정, `client.rs:73-79`), 이벤트는 별도 지속 연결. 구독 이벤트 이름은 점 표기(`pane.agent_status_changed`), 발행 이벤트는 밑줄 표기 | 데몬 전체(디스패치·spawner·watchers·rescue·알림) | `board-herdr/src/lib.rs:27-37`, `client.rs:239-265`, `events/mod.rs:7-19` | `herdr-client` 행에 포함 · 미작성 | 코드 확인(클라이언트가 가정한 계약). herdr 서버가 실제로 그렇게 동작하는지는 미확인 |
| **herdr CLI 호출 (소비 쪽)**: 데몬 `herdr session list --json`(10초 제한을 둔 자식 프로세스, `session.rs:60`, `:141-191`)과 `herdr pane run <pane> <script>`(`HERDR_SOCKET_PATH`를 그 session 소켓으로 지정, `configured.rs:26-41`). 바이너리는 `$HERDR_BIN_PATH` 없으면 PATH의 `herdr`. launcher: `herdr pane list`, `plugin pane open/focus`, `pane close`(`open-board.sh`). 설치: `herdr plugin link`, `server reload-config`(`install.sh:67`, `:83`) | spawner(configured), session 해석, launcher, 개발 설치 | `board-daemon/src/session.rs:81`, `spawner/herdr/configured.rs:27-34`, `scripts/open-board.sh:19-77` | 각 행에 나눔 · 미작성 | 코드 확인(호출 쪽). `session list --json` 출력 모양은 `session.rs`의 `parse_session_list`를 열지 않아 미확인 |
| **환경변수**. herdr가 주는 값(읽는 쪽): `HERDR_SOCKET_PATH`(TUI `origin.rs:19`, `transport.rs:28-30`), `HERDR_PLUGIN_ID`(`origin.rs:25`), `HERDR_PANE_ID`(`origin.rs:28`, CLI `helpers.rs:67`), `HERDR_PLUGIN_CONTEXT_JSON`(`focused_pane_cwd`·`workspace_cwd`만 읽음, `board-cli/src/scope.rs:9`, `board-core/src/scope.rs:8-13`, `:26-39`), `HERDR_BIN_PATH`(`session.rs:81`, `configured.rs:27`, `open-board.sh:19`). 소켓 경로 철자가 세 가지다: `HERDR_SOCKET_PATH`(우선), `HERDR_SOCKET`(`transport.rs:29`), `HERDR_SOCK`(CLI `helpers.rs:157`). board가 쓰는 값: `BOARD_DB`·`BOARD_SOCKET`·`BOARD_LOG_DIR`·`HERDR_BOARD_CONFIG`(`paths.rs`), `BOARD_SPAWNER`(`settings.rs:76`), `BOARD_SCOPE_PATH`, 에이전트에 주는 `BOARD_CARD_ID`·`BOARD_CARD_TITLE`·`BOARD_CARD_SHORT_NAME`·`BOARD_RUN_ID`·`BOARD_SOCKET`·`BOARD_BIN`(`launch_plan.rs:33-60`) | TUI, CLI, 데몬, 에이전트 | 위 줄번호 | 각 행에 나눔 · 미작성 | 코드 확인(읽는 쪽). herdr가 실제로 이 변수를 주입하는지는 미확인(`transport.rs:24-27` 주석과 README 주장뿐) |
| **SQLite 스키마 v15**: projects·boards·selection·board_selection·project_recents·board_recents·columns·cards·comments·comment_history·runs | 데이터 모델 이하 거의 전부 | `schema.sql`, `migrations.rs:11` | `data-model` 행에 포함 · 미작성 | 코드 확인 |
| **카드·run 상태기계**: `CardStatus` 7종(`idle`·`queued`·`running`·`blocked`·`failed`·`awaiting`·`done`), `AwaitingReason` 2종, `RunOutcome` 4종(`ok`·`fail`·`cancelled`·`lost`), `Trigger` 2종 | 컬럼 엔진, 이벤트 관찰, 보고 채널, TUI | `protocol.rs:111-175`, `engine/signals.rs`, `engine/transitions.rs` | `column-engine` 행에 포함 · 미작성 | 코드 확인 |
| **설정**: `~/.config/herdr-board/config.toml`, 하나만 읽고 데몬 시작 때 한 번 파싱. `max_concurrent`(기본 3), `idle_grace_seconds`(기본 90), `[daemon] spawner`·`timeout_unit_secs`(60)·`local_poll_ms`(2000)·`tick_ms`(1000), `[harness.NAME]` | 디스패치, 이벤트 관찰, 하니스 | `board-core/src/config.rs:9-76`, `board-daemon/src/settings.rs:41-80`, `lib.rs:81-113` | `dispatch-queue` 행에 포함 · 미작성 | 코드 확인(기본값·로딩 순서) |

**herdr 연동 지점 한눈에** (매니페스트 → 실행되는 명령 → 코드 진입 → 하는 일)

| 매니페스트 항목 | 실행되는 명령 | 코드 진입 | 하는 일 |
|---|---|---|---|
| `[[build]]` (`herdr-plugin.toml:20-21`) | `./scripts/build.sh` | `scripts/build.sh:20-22`, `:34` | `board`가 PATH에 있으면 먼저 `board daemon --stop`(실패 무시)으로 옛 데몬을 멈추고, `cargo build --release -p board-cli`로 `target/release/board`를 만든다. 설치 때 herdr가 실행한다는 서술은 스크립트 주석(`build.sh:3-4`)뿐 |
| `[[build]]` (`:26-27`) | `./scripts/install-cli.sh` | `install-cli.sh:14-26`, `:74-77`, `:132-137` | `target/release/board`를 `$HERDR_BOARD_CLI_INSTALL_DIR`(없으면 `~/.local/bin`)에 복사하고 옆에 `.herdr-board-cli-managed` 마커(SHA-256)를 둔다. 마커가 없는 기존 `board`는 덮어쓰지 않는다. 에이전트가 이름으로 `board`를 부를 수 있게 하려는 것(`install.sh:70-71` 주석과 같은 이유는 추론) |
| `[[panes]]` `board` (`:32-36`, `placement = "overlay"`) | `./target/release/board tui` | `main.rs:102-106` → `ctx.board()`가 `connect_or_start`(`daemon.rs:16`)로 데몬을 필요하면 띄움 → `board_tui::run_with_board`(`runtime.rs:57`) | 오버레이 pane에서 칸반 TUI를 연다. 이 pane의 환경(`HERDR_SOCKET_PATH`·`HERDR_PLUGIN_ID`·`HERDR_PANE_ID`)을 TUI가 읽어(`origin.rs:18-32`) 자기 pane 제목을 데몬의 `pane.set_title`로 바꾸고(`dispatch.rs:279-290`, `HERDR_PLUGIN_ID == "herdr-board"`일 때만), 선택한 run의 pane으로 `run.focus`를 요청한다(`dispatch.rs:293-322`) |
| `[[actions]]` `open-board` (`:41-45`) | `bash scripts/open-board.sh` | `open-board.sh:33-77` | `herdr pane list` 결과에서 제목이 `Board` 또는 `Board [... · ACTIVE\|ALL\|ARCHIVED]`인 pane을 찾아, 없으면 `herdr plugin pane open --plugin herdr-board --entrypoint board --placement overlay --focus`, 있고 포커스 아니면 `herdr plugin pane focus <id>`, 포커스 중이면 `herdr pane close <id>`. python3가 없거나 실패하면 열기로 폴백. TUI가 pane 제목을 맞추는 쪽(`pane_title` 본문)은 열지 않아 정규식과 같은 형식인지는 미확인 |
| (매니페스트에 없음) 이벤트 훅 | 데몬이 직접 `events.subscribe` | `watchers/herdr.rs:267`, `board-herdr/src/events/stream.rs:61-91` | active run의 pane마다 `pane.agent_status_changed`, 전역으로 `pane.exited`·`pane.closed`를 구독해 카드 상태에 반영한다. 구독 직후 `session.snapshot`으로 놓친 이벤트를 보정한다(`watchers/herdr.rs:85-95`, `:264-266` 주석) |
| (키바인딩, 매니페스트 밖) | herdr 설정 `[[keys.command]]`, `herdr plugin action invoke open-board --plugin herdr-board` | `README.md:109-119`, `install.sh:74-92` | 자동 설정되지 않는다. 사용자가 herdr 설정에 직접 넣거나 개발용 `install.sh --yes`가 추가한다 |

**데몬이 herdr 소켓으로 호출하는 것** (board-herdr 24종 중 비테스트 소스에서 호출처를 확인한 것)

| 목적 | herdr 메서드 | 호출처 |
|---|---|---|
| 호환 게이트 | `ping` | `herdr_conn.rs:20-24`, `client.rs:239` |
| workspace 해석·생성 | `workspace.list`, `workspace.create` | `dispatch/space.rs` `resolve_space`(`workspace.list` 호출 확인 :44. `workspace.create`는 같은 함수의 문서 주석 기준이라 추론), 정리용 `workspace.close`는 `spawner/rescue.rs` |
| pane 배치 | `tab.list`, `tab.create`, `tab.rename`, `pane.list`, `pane.layout`, `pane.split`, `pane.rename`, `pane.get` | `spawner/placement/alloc.rs`, `rescue.rs` |
| 에이전트 시작·프롬프트 | `agent.start`(`name`·`kind`·`pane_id`·`args`·`timeout_ms`), `agent.get`, `agent.prompt` | `spawner/herdr/managed.rs:508-523`, `:556`, `:720` |
| 정리·존재 확인 | `pane.close`, `session.snapshot` | `spawner/herdr/mod.rs:297-320`, `watchers/herdr.rs:85` |
| 이벤트 | `events.subscribe` | `events/stream.rs:61-91` |
| 알림 | `notification.show` | `state.rs:289-302` |
| 하니스 설치 여부 | `integration.list` | `ops/discovery.rs:10-20` |
| 포커스·제목 | `pane.focus`, `pane.rename` | `rescue.rs`, `ops/panes.rs:29-45` |

`pane.read`·`pane.send_text`·`pane.send_keys`·`agent.wait`는 클라이언트에 정의돼 있지만 `board-daemon`·`board-cli`·`board-tui`의 비테스트 소스에서 호출처를 찾지 못했다(`grep '\.pane_read(' …`). (코드 확인)

**대조한 범위와 미탐색 영역**
- 대조: 매니페스트 전체, README 전체, `AGENTS.md`, `schema.sql` 전체, `SCHEMA-DIFF-0.9.0.md`, `skill/SKILL.md` 앞 30행과 목차, 스크립트 3개(`build.sh`·`install-cli.sh`·`open-board.sh`)와 `install.sh` 앞 92행, `board-cli/src/main.rs`·`daemon.rs`·`scope.rs` 전체, `args/*.rs`의 서브커맨드 선언(선언 이름만), `board-herdr/src/{lib,client,transport}.rs` 전체와 `events/{mod,parse}.rs` 전체·`stream.rs` 앞 140행, `board-daemon/src/{lib,server,herdr_conn,session,settings}.rs`·`ops/mod.rs`·`ops/panes.rs`·`ops/runs.rs`·`ops/cards.rs`(card_move), `dispatch/{pass,enqueue}.rs`·`launch_plan.rs` 앞 330행, `spawner/herdr/mod.rs` 전체·`configured.rs`·`managed.rs` 앞 110행과 `launch_managed_prompt_file`, `watchers/{herdr 350~440행, signals, mod}.rs`, `board-core/src/engine/signals.rs` 전체·`transitions.rs` 60~200행, `board-tui/src/{lib,origin,runtime}.rs`·`driver/dispatch.rs` 262~330행. 문서는 `docs/README.md`, `docs/protocol.md` 8~110행, `docs/herdr.md` 1~80행을 읽었다.
- **README·문서와 코드의 대조 결과**
  1. README 명령 표(`README.md:257-258`)는 `board board`·`board project`의 동사에 `archive`·`restore`를 적지 않았지만 코드에는 있다(`args/board.rs:43-45`, `args/project.rs:30-32`). 숨겨진 내부 명령 `__pane-exited`(설정 정의 하니스가 끝났을 때 pane 래퍼 스크립트가 호출, `args/mod.rs:101`, `configured.rs:129-132`)도 표에 없다.
  2. 템플릿은 이름 `pipeline` 하나뿐이다(`ops/boards.rs:136`). 빈 보드(시드 컬럼 `Todo`만 있고 카드 없음)에만 적용된다(`:162-167`). 만들어지는 컬럼은 Plan(auto)→Execute(auto)→Review(auto, 모델 override `opus` 고정)→Human Review(manual)→Done(manual)이고, Plan 실패는 `Todo`로, Review 실패는 Execute로 돌아간다(`:170-221`). README는 템플릿 구성을 말하지 않는다.
  3. `board-herdr/src/lib.rs:3-4` 머리 주석은 소켓 경로를 `$HERDR_SOCKET`이라 하지만 코드는 `HERDR_SOCKET_PATH`를 먼저 읽는다(`transport.rs:28-30`). CLI의 origin 해석은 또 다른 철자 `HERDR_SOCK`을 쓴다(`helpers.rs:157`).
  4. `docs/README.md`는 "worktree API는 `board-herdr`에 일부러 없다"고 하고 코드에도 worktree 호출이 없다(`board-core/src/db/migrations.rs`의 옛 `space_kind` 값 언급 말고는 `worktree`가 소스에 안 나온다, grep). herdr-projects와 가장 크게 갈리는 지점이다.
  5. README는 "mobile-first TUI"라 한다. 코드에는 폭 기준으로 `Compact`·`Regular`·`Wide`를 나누는 레이아웃이 있다(`view/mod.rs:79-88`, `view/layout.rs:80-83`). 폰에서 실제로 쓸 만한지는 확인하지 않았다(미확인).
- **미탐색**(이유): `crates/*/tests/`와 `*tests.rs`·`testkit` 등 테스트·픽스처 약 200개(기본으로 열지 않음), `e2e/`의 시나리오 본문 40개와 `herdr-proxy.py` 등(기본으로 열지 않음, 용도 확인용으로 `e2e/README.md` 앞부분·`lib.sh`·`test-harness.sh`·`herdr-proxy.py` 머리만 훑음), `.github/workflows/`(CI, 열지 않음, `release.yml:176-190`은 라이선스 처리 확인 때문에 열었다), `CONTRIBUTING.md`·이슈/PR 템플릿·`CHANGELOG.md`(버전 확인용 앞 20행만), `docs/design.md`·`implementation.md`·`research.md`·`testing.md`·`configuration.md`·`install.md`·`operations.md`·`releasing.md`(범위 밖, 필요한 줄만 검색), `docs/herdr-0.9.0-schema.json`(269KB 덤프, 열지 않음), `board-tui`의 `app/`·`view/`·`forms/`·`widgets/` 본문(키·화면 로직), `board-core/src/db/*.rs` 쿼리 본문, `harness/{codex,opencode,agy}.rs`와 `*_catalog.rs`, `engine/{lifecycle,validation,archive}.rs`, `dispatch/{space,ownership,finalize 후반}.rs`, `spawner/placement/alloc.rs` 본문·`spawner/rescue.rs`·`rescue.rs`·`recovery.rs`·`supervisor.rs`·`logging.rs` 본문, `scripts/sandbox.sh` 본문(641줄, 서브커맨드 목록만), `docker/` 나머지(`Dockerfile` 앞 40행만), `.agents/skills/development-workflow/references/`. 이유는 이번 범위가 지도(2장)까지이고 레포가 큰 편이기 때문이다.

### herdr-projects와의 차이

| 축 | herdr-board (이 문서, SHA 7a215a1) | herdr-projects ([overview](../herdr-projects/overview.md), SHA 8258d96) |
|---|---|---|
| 매니페스트 | `[[build]]` 2, `[[panes]]` 1(overlay), `[[actions]]` 1. 이벤트·시작 훅 없음 (`herdr-plugin.toml:20-45`) | `[[build]]`, `[[startup]]`, `[[actions]]` 3, `[[events]]` 4, `[[panes]]` 1(tab) (herdr-projects overview 기준) |
| herdr 호출 방식 | 소켓 중심(24종 + 이벤트 구독). CLI는 `session list --json`·`pane run`뿐 | herdr CLI 자식 프로세스 중심, 소켓은 `popup.close`·`events.subscribe`만 |
| 상태 반영 | 상주 데몬이 이벤트 스트림을 직접 구독 | herdr가 매니페스트 이벤트마다 `hook` 프로세스를 띄움 + keeper |
| 저장소 | SQLite 한 파일(`board.db`), 데몬만 씀 | 태스크별 `task.json` 파일 |
| 작업 단위 | 카드가 컬럼(파이프라인 단계)을 따라 이동. 단계마다 run, 컬럼이 시스템 프롬프트·전이 대상·타임아웃을 가짐 | 태스크 하나가 worktree space 하나를 받고 마감선(커밋→병합→검사→리뷰→승인)을 지남 |
| 실행 위치 | 카드가 고른 기존/새 workspace의 `card-<id>` 탭. worktree API 없음 | 태스크마다 herdr worktree space |
| 완료 신호 | 에이전트가 부르는 `board done` | 에이전트 훅의 `turn-ended` + herdr 상태 |
| 사람의 게이트 | `manual` 컬럼(Human Review 등)에서 멈춤 | `approve` |

(herdr-projects 쪽 칸은 그 문서의 기록을 옮긴 것이고 이번에 다시 열지 않았다.)

---

## 3. 구조 해설

구조도(archify)는 사용자 지시로 만들지 않았다. 아래는 글만으로 읽는 순서, 모듈별 역할, 대표 흐름이다.

**읽는 순서**
1. `herdr-plugin.toml` 전체(45행)와 `scripts/open-board.sh` — herdr가 무엇을 언제 실행하는지. 이벤트 훅이 없다는 점을 먼저 확인한다. (코드 확인)
2. `crates/board-cli/src/main.rs` `dispatch`(:84-151) → `daemon.rs` `connect_or_start`(:16) — 모든 진입이 어떻게 데몬 소켓으로 모이는지. (코드 확인)
3. `crates/board-daemon/src/lib.rs` `async_main`(:81-235) — 데몬 시작 시 만드는 것: DB, 설정, herdr 핸들, `SessionRegistry`, spawner, 디스패치 루프, 감시 스레드, 복구, 소켓 바인드. (코드 확인)
4. `ops/mod.rs` `routes!` 표(:51-101)와 `server.rs` — 요청이 어디로 가는지. (코드 확인)
5. `board-core/src/engine/`(`transitions.rs`, `signals.rs`) — 상태 결정 규칙. 부작용 없는 함수라 짧다. (코드 확인)
6. `dispatch/pass.rs` → `enqueue.rs` → `launch_plan.rs` → `spawner/herdr/` — 카드가 pane의 에이전트가 되는 길. (코드 확인)
7. `board-herdr/src/{client,transport,events}` — herdr와 실제로 주고받는 줄. (코드 확인)
8. `watchers/herdr.rs`, `watchers/signals.rs`, `dispatch/finalize.rs` — 실행 중·종료 후 상태 반영. (코드 확인)
9. `board-tui`는 `lib.rs`의 계층 표(:11-20)와 `runtime.rs`부터. 화면 로직은 필요할 때. (코드 확인: 위 파일, 나머지 미확인)

**크레이트·모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| `board-cli` | 서브커맨드 해석, 데몬 자동 시작·정지, 출력(`--json`, 종료 코드) | 입력: argv, `BOARD_*`·`HERDR_*` 환경변수. 출력: stdout, 종료 코드 0·1~5·64·70. 데몬에 NDJSON 요청 | `main.rs` `dispatch`(:84), `exit_code`(:196), `daemon.rs` `connect_or_start`(:16), `daemon_command`(:63), `commands/run.rs` `cmd_done`(:64) | 코드 확인. `commands/{card,column,board,project}.rs` 본문은 미확인 |
| `board-core` | 도메인 모델, 프로토콜 타입, DB, 순수 엔진, 프롬프트·하니스 조립, 설정, 데몬 클라이언트 | 입력: 카드·컬럼·run 값. 출력: 결정 구조체, SQL 결과, argv/env | `protocol.rs`(타입 전부), `engine/transitions.rs` `decide_entry`(:148), `decide_transition`(:85), `engine/signals.rs` `decide_signal`(:45), `prompt.rs` `assemble_prompt`(:22), `client/unix.rs` `UnixClient`(:98) | 코드 확인(엔진·클라이언트·프롬프트). `db/`·`harness/` 본문은 미확인 |
| `board-herdr` | herdr 소켓의 타입드 클라이언트와 이벤트 스트림. 보드 상태는 모름 | 입력: 소켓 경로, 요청 파라미터. 출력: 타입 결과, `HerdrEvent` | `client.rs` `HerdrClient`(:80), `call_inner`(:154), `events/stream.rs` `HerdrEvents`(:95), `events/parse.rs` `parse_event_line`(:48) | 코드 확인 |
| `board-daemon` `server.rs`·`ops/` | 연결 처리, 요청 한 건씩 blocking 풀에서 실행, 라우팅, 이벤트 방송 | 입력: NDJSON 요청. 출력: 응답, `board_changed`·`run_ended` 이벤트 | `server.rs` `handle_conn`(:193), `dispatch_request`(:282-324), `ops/mod.rs` `handle_request` | 코드 확인(서버·라우팅). 핸들러 대부분은 미확인 |
| `board-daemon` `dispatch/` | run 대기열 → 실행 승격 → 종료 처리 | 입력: queued run. 출력: `HerdrLaunchPlan`, DB 갱신, 이벤트 | `pass.rs` `dispatch_pass`(:16), `launch_plan.rs` `spawn_one`(:72), `finalize.rs` `finalize_run`(:25) | 코드 확인(앞부분). 실패 경로·`finalize` 후반은 미확인 |
| `board-daemon` `spawner/` | herdr pane 배치와 에이전트 시작, 로컬 spawner | 입력: `HerdrLaunchPlan`. 출력: `RuntimeHandle`(pane·workspace·anchor id) | `herdr/mod.rs` `HerdrSpawner`(:39), `spawn_inner`(:110), `managed.rs` `launch_managed`(:57) | 코드 확인(pi/claude 관리형·configured). 나머지 하니스 캡처는 미확인 |
| `board-daemon` `watchers/` | herdr 이벤트·타임아웃·idle 감시 | 입력: `HerdrEvent`. 출력: `AgentSignal` 적용, run 종료 | `watchers/herdr.rs` `handle_event_from_socket`(:352), `signals.rs` `apply_signal`(:28) | 코드 확인 |
| `board-daemon` `session.rs`·`herdr_conn.rs` | session 이름→소켓 해석(`herdr session list --json`, 캐시), 게이트된 연결 | 입력: session 이름. 출력: 소켓 경로 | `session.rs` `SessionRegistry`(:120-248), `herdr_conn.rs` `connect_checked`(:20) | 코드 확인 |
| `board-tui` | 순수 상태기계(`app::update`)와 순수 렌더러(`view`), I/O는 `driver`·`runtime`에만 | 입력: 키·마우스, 데몬 이벤트. 출력: 화면, 데몬 요청 | `lib.rs:11-20`, `runtime.rs` `event_loop`(:112), `driver/dispatch.rs`(`Effect` 실행) | 코드 확인(계층·실행 루프). `app/`·`view/` 본문은 미확인 |
| `skill/SKILL.md` | `board skill` 출력 원문 | 입력 없음. 출력: 문서 바이트 | `main.rs` `print_skill`(:176-179) | 코드 확인 |

**`skill/SKILL.md`와 `.agents/skills/`는 무엇인가.** `skill/SKILL.md`는 frontmatter `name: herdr-board`와 "카드에 진행을 보고하거나 run을 닫거나 코멘트를 쓸 때 쓴다"는 설명(`skill/SKILL.md:1-10`)을 가진, **에이전트와 사람이 읽는 보드 사용법**이다. 본문은 Inside a run, TUI, CLI taxonomy, 종료 코드, Creating work를 다룬다(`:26`, `:49`, `:64`, `:292`, `:317`). 바이너리에 `include_bytes!`로 들어가 `board skill`이 그대로 출력하므로 디스패치된 에이전트가 자신이 따라야 할 계약을 읽을 수 있다(`main.rs:176-179`, `README.md:236-238`). 이것과 별개로 `.agents/skills/development-workflow/SKILL.md`는 **이 레포를 개발하는 에이전트용** 규칙이다. 테스트와 TUI 실행을 호스트가 아닌 샌드박스로만 하라는 정책과 절차를 담는다(`.agents/skills/development-workflow/SKILL.md:1-40`, `AGENTS.md:9-20`). (코드 확인)

**`docker/`와 `e2e/`는 무엇을 위한 것인가.** 둘 다 개발·검증용이고 플러그인 실행에는 쓰이지 않는다. `e2e/`는 **실제 herdr를 띄워** `HerdrSpawner`를 가짜 에이전트(`fake-agent.sh`, `fake-bin/{pi,claude,codex,opencode,agy}`)로 끝까지 돌려 보는 시나리오 40개로, herdr 연동을 종단으로 검증하는 유일한 계층이다(`e2e/README.md:1-9`). `docker/`는 그 e2e와 모든 게이트를 호스트의 herdr·데몬·DB와 격리해 돌리기 위한 고정 이미지(Rust 1.97.0, herdr 0.9.0 릴리스 자산을 SHA-256으로 고정, 프로토콜 22 확인)다(`docker/Dockerfile:1-30`, `docs/sandbox.md:1-14`). `scripts/sandbox.sh`가 진입점이다(서브커맨드 `gates`·`prepare`·`shell`·`board`·`tui`·`agent` 등, `sandbox.sh:628-640`). 본문은 열지 않았다. (추론: 머리 주석·문서)

**대표 흐름: 카드를 `auto` 컬럼으로 옮겨 에이전트를 실행하고 상태가 반영되기까지** (코드 확인 구간과 미확인 구간 구분)

1. 사용자가 TUI에서 카드를 옮기거나 `board move <id> Execute`(README 예시, `README.md:181-189`)를 실행한다. CLI는 `Cmd::Move`를 `cmd_move`로 보내(`main.rs:135-148`) `card.move` 요청을 만들고, 데몬이 `card_move`(`ops/cards.rs:264`)에서 보관·archived 검사 후 `decide_entry`(`:377`, 규칙 `transitions.rs:148-180`: `auto` 컬럼 + 카드 상태가 `idle`·`failed`·`done`이면 큐에 넣음)로 enqueue 여부를 정한다. 코드 확인.
2. enqueue면 `prepare_enqueue_values`(`dispatch/enqueue.rs:97`)가 설정을 합치고(`effective_settings`), 프롬프트(카드 description + 최근 코멘트 20개 + 닫기 안내)를 조립하고, 하니스 argv·env·시스템 프롬프트를 만들어 run 행에 스냅샷으로 저장한다(`:162-180`). DB에서는 카드 이동과 run 추가가 한 트랜잭션(`move_card_and_enqueue_uow`)이다. 카드 상태는 `queued`가 된다. 이어서 `wake_dispatch`(`ops/cards.rs:436`)가 디스패치 루프를 깨운다. 코드 확인(`move_card_and_enqueue_uow` 본문은 미확인).
3. 디스패치 루프(`lib.rs:161-167`)가 `dispatch_pass`(`pass.rs:16`)를 돈다. 열린 run 수가 `max_concurrent`(기본 3) 미만이고 같은 공간(workspace)에 이미 실행 중인 run이 없으면 큐 맨 앞부터 꺼낸다(`:20-56`). 코드 확인.
4. `spawn_one`(`launch_plan.rs:72`)이 `HerdrLaunchPlan`을 만든다. pane 이름 `card-<id>-<컬럼 slug>`, 탭 이름 `card-<id> <제목 slug>`(`:137-156`), env에 `BOARD_CARD_ID` 등 추가(`:120-125`). session 이름을 소켓으로 풀고(`session.rs:212`, 내부에서 `herdr session list --json`), `resolve_space`가 `workspace.list`(`new_workspace`면 없을 때 `workspace.create`, 후자는 문서 주석 기준)로 workspace와 cwd를 정한다(`launch_plan.rs:175-322`, `space.rs:7-44`). 코드 확인(`workspace.list`까지). `workspace.create` 호출 본문은 미확인.
5. `HerdrSpawner.spawn_inner`(`spawner/herdr/mod.rs:110`)가 `ping`으로 프로토콜 22를 확인하고(`:116`), `allocate_owned_pane`이 카드 탭과 anchor(셸 pane) 아래 pane을 `tab.create`·`pane.split`로 만들면서 cwd·env를 준다(`:166-191`; 이유는 `AGENTS.md:152-154`: pane은 workspace의 env·cwd를 상속하지 않는다). 관리형 `pi`·`claude`면 시스템 프롬프트를 0600 임시 파일에 쓰고(`managed.rs:488-504`) `agent.start {name, kind, pane_id, args}`를 보낸 뒤(`:508-517`) 에이전트가 입력 가능해지면 `agent.prompt`로 첫 프롬프트를 넣는다(`:519-524`). 설정 정의 하니스면 pane 이름을 바꾸고 생성한 셸 스크립트를 `herdr pane run <pane> <script>`로 실행한다(`configured.rs:53-95`). 성공하면 관리형은 anchor pane을 닫는다(`mod.rs:243-258`). 코드 확인(pi·claude·configured). codex·opencode·antigravity는 미확인.
6. `register_spawned_run`(`launch_plan.rs:435-`)이 run을 승격한다(DB에서 카드가 `running`, `db/runs.rs:118`). 이어서 `refresh_watch`(`:416`)로 감시할 pane 목록을 다시 계산하고 `board_changed`(`RunStarted`)를 방송한다(`:417-418`). 코드 확인.
7. 에이전트가 일하는 동안 감시 스레드(`herdr_event_thread`, `watchers/herdr.rs:267`)가 구독한 pane의 상태 이벤트를 받는다. `Working`→카드 `running`, `Blocked`→`blocked`+알림, `Done`→`awaiting`(`agent_done`), `Idle`→유예 타이머만 시작(만료는 `timeout_ticker`가 `awaiting`(`idle_expired`)으로 바꿈)이다(`:368-401`, 결정 `engine/signals.rs:45-102`). pane이 사라지면 run을 `fail`로 닫는다(`:403-428`). 코드 확인.
8. 에이전트는 시스템 프롬프트의 규칙대로 `board comment "<결과>"`를 쓰고 `board done --outcome ok`를 실행한다. CLI는 `BOARD_CARD_ID`·`BOARD_RUN_ID`·`HERDR_PANE_ID`를 읽어(`commands/run.rs:71-84`, `helpers.rs:39-70`) `run.done`을 요청하고, 데몬 `run_done`(`ops/runs.rs:9`)이 호출자가 이 run의 pane인지 확인한 뒤 `decide_lifecycle`로 종료 계획을 만들고 `finalize_run`(`finalize.rs:25`)을 부른다. `decide_transition`(`finalize.rs:128`, 규칙 `transitions.rs:85-131`)이 `ok`면 `on_success`, `fail`이면 `on_fail` 컬럼을 고르고, 대상이 `auto`면 카드를 `queued`로 두고 다음 run을 enqueue한다. 마지막에 `emit_run_ended`와 `wake_dispatch`(`finalize.rs:235-236`)로 다음 단계가 이어진다. 코드 확인(호출 연결). `decide_lifecycle` 본문과 `finalize_run_inner` 후반은 미확인.
9. 이 모든 변화는 `board_changed` 이벤트로 TUI에 간다. 데몬은 연결마다 이벤트 포워더를 두고(`server.rs:348-367`), TUI는 별도 연결로 `events.subscribe`한 뒤(`board-core/src/client/unix.rs:162-`) 이벤트가 올 때마다 `Msg::Refresh`로 다시 불러온다(`runtime.rs:112-163`, `:171-180`). 끊기면 지수 백오프로 다시 연결하고 전체를 새로 받는다(`:182-`). 코드 확인.
10. 에이전트가 `board done` 없이 끝나면(2번째 갈래) 카드는 `awaiting`이고 컬럼 타임아웃은 멈춘다(`protocol.rs:139-160`, `signals.rs`). 사람이 TUI 상세에서 Enter(확인)하거나 `board card run confirm`을 실행하면 같은 `cmd_done(… "ok" …)`로 닫힌다(`commands/run.rs:102`, `README.md:225`). 코드 확인(CLI 쪽).

**미확인 영역**
- 이 분석은 빌드·실행을 하지 않았다. 따라서 `실행 확인`은 없다. herdr 0.9.x와 실제로 맞물리는지, `herdr plugin install` 때 `[[build]]`가 어떤 작업 디렉터리·환경에서 실행되는지, 오버레이 pane에 환경변수가 실제로 주입되는지, `herdr pane run`·`agent.start`의 실제 동작은 코드·문서의 주장(클라이언트가 그렇게 가정했다는 증거)뿐이다(7장 규칙).
- herdr 쪽 동작: 요청마다 연결을 닫는다는 가정(`client.rs:73-79`), 구독이 `pane_id`를 요구하는 제약(`events/mod.rs:7-13`), 이벤트 이름의 점/밑줄 표기 차이(`events/mod.rs:15-19`)는 모두 코드 주석의 "verified live" 주장이다. herdr 서버를 열지 않았으므로 `미확인`.
- 하니스별 시작 인자와 세션 캡처(codex·opencode·antigravity), 하니스 카탈로그의 라이브 조회, 컬럼·보드·코멘트 핸들러, DB 쿼리와 v1~v14 마이그레이션, 시작 복구·감독자(`recovery.rs`·`supervisor.rs`), `run.focus` 복구 로직, TUI의 키·화면·폼, 진단 로그 회전.
- 도입 판단에 영향이 큰 것: **LICENSE 파일 부재**(1절), 호스트에서 `herdr integration install <하니스>`를 사용자가 직접 해야 정확한 상태 신호가 온다는 점(`docs/herdr.md:73-80`는 문서 주장, 보드는 설치·갱신을 하지 않는다), 정확히 프로토콜 22만 허용하는 정책(`client.rs:239-251`).

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음에 볼 곳**:
  1. `board-daemon/src/spawner/placement/alloc.rs`와 `card_tabs.rs` — `card-<id>` 탭·anchor·재사용 pane의 소유 판정(이름이 아니라 정확한 `tab_id`로만 소유를 인정한다는 `AGENTS.md:155`의 주장 확인).
  2. `board-daemon/src/supervisor.rs`·`recovery.rs`·`herdr_snapshot.rs` — 데몬 재시작·herdr 재시작 때 열린 run을 어떻게 보수적으로 다시 맞추는지.
  3. `board-core/src/engine/lifecycle.rs`·`board-daemon/src/dispatch/finalize.rs` 후반 — `board done`의 호출자 검증(`BOARD_RUN_ID`가 낡았을 때 `HERDR_PANE_ID`로 대체), 자동 전이 횟수 상한(`decide_auto_hop`, `transitions.rs:19`).
  4. `board-core/src/harness/`의 세 어댑터와 `board-daemon/src/spawner/herdr/managed.rs` 후반 — codex·opencode·antigravity가 스스로 만드는 대화 id를 캡처하는 방법.
  5. `board-tui/src/app/`·`view/` — 키 표와 상태기계, Compact 레이아웃. 오버레이 pane 제목 형식(`pane_title`)이 `open-board.sh`의 정규식과 같은지(1·4행의 미확인 해소).
- **다음 세션 계획**: next.md는 아직 없음(사용자 지시는 overview까지).
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(전부 미작성).
- **비교**: [herdr-projects overview](../herdr-projects/overview.md), [GUIDE](../../GUIDE.md).
