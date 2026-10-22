---
sha: "3ca867153baad10d658f731ad8dcdd1d4a1fc1c2"
created: 2026-10-22
updated: 2026-10-22
sources:
  - herdr-plugin.toml
  - README.md
  - doc/herdr-nvim.txt
  - LICENSE
  - .gitignore
  - Cargo.toml
  - herdr/install.sh
  - herdr/install.ps1
  - src/main.rs
  - src/maneuver.rs
  - src/layout.rs
  - src/state.rs
  - src/herdr.rs
  - src/config.rs
  - src/bridge.rs
  - src/openlink.rs
  - src/picker.rs
  - src/sessions.rs
  - src/daemon/mod.rs
  - src/daemon/events.rs
  - src/daemon/registry.rs
  - src/daemon/inventory.rs
  - src/doctor.rs
  - lua/herdr-nvim/init.lua
  - lua/herdr-nvim/agents.lua
  - lua/herdr-nvim/dispatch.lua
  - lua/herdr-nvim/exec.lua
  - lua/herdr-nvim/commands.lua
  - lua/herdr-nvim/comments.lua
  - lua/herdr-nvim/prompt.lua
  - lua/herdr-nvim/ui.lua
  - plugin/herdr-nvim.lua
---

# herdr-nvim Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/ChmaraX/herdr-nvim` (`artifacts/herdr-nvim/repo-metadata.txt`: branch main, 마지막 커밋 2026-10-20, 2026-10-22에 `--depth 50`으로 clone)
- **작업트리 상태**: Clean (repo-metadata.txt)
- **분석 목적**: 학습 · 도입 검토. (1) herdr 플러그인이 매니페스트(`herdr-plugin.toml`)로 herdr와 어떻게 연동하는지, (2) Rust 바이너리와 Neovim Lua 플러그인이 어떻게 맞물리는지 본다.
- **라이선스**: MIT License, Copyright (c) 2026 Adam Chmara — 루트 `LICENSE` 하나. 하위 디렉터리의 다른 LICENSE는 찾지 못했다(추적 파일 목록에서 `LICENSE`는 루트뿐). (코드 확인: `LICENSE:1-3`)
- **분석 대상 제품**: 한 레포에서 나오는 두 조각.
  - Rust 바이너리 `herdr-nvim`(`Cargo.toml` 1.2.1, `src/`). herdr가 매니페스트의 명령으로 호출한다.
  - Neovim Lua 플러그인(`lua/herdr-nvim/`, `plugin/herdr-nvim.lua`, `doc/herdr-nvim.txt`). 사용자의 nvim과 사이드바 nvim 양쪽에서 로드된다.
  - 설치 스크립트 `herdr/install.sh`, `herdr/install.ps1`(매니페스트 `[[build]]`가 호출). 나머지는 기본으로 열지 않은 테스트·e2e·CI·CHANGELOG·`.agents/`다.
  - 빌드 산출물 `bin/herdr-nvim`은 `.gitignore`의 `/bin/`이라 clone에 없다. (코드 확인: `.gitignore:7`)
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지). 3절 구조도(archify)는 사용자 지시로 만들지 않고 글 해설로 대체했다.

**용어**: *herdr* = 코딩 에이전트용 터미널 멀티플렉서(외부 프로그램, 이 레포에 없음). *pane/tab/workspace* = herdr의 화면 조각/탭/작업공간. *daemon* = 탭마다 하나씩 띄우는 헤드리스(`--headless`) nvim 프로세스. *sidebar* = 그 daemon에 `nvim --remote-ui`로 붙은 herdr pane.

---

## 2. 프로젝트 개요

README는 "herdr 작업공간 안의 nvim 사이드바, 에이전트가 만진 파일로 바로 가기"라고 소개한다(`README.md:7-8`). 코드로 보면 이 레포는 **herdr CLI를 감싸는 Rust 바이너리**(레이아웃 재배치, daemon 관리, 파일 피커)와 **그 daemon 안에서 도는 Lua 플러그인**(댓글·에이전트 전송)으로 나뉜다. 둘은 서로 함수를 부르지 않고, Rust가 nvim의 원격 인터페이스(`--remote-expr`, `--remote`, `--remote-send`)로 daemon을 조작하는 방식으로만 만난다. (코드 확인: `src/daemon/mod.rs`, `src/bridge.rs:312-346`, 읽은 Lua 파일에서 `herdr-nvim` 바이너리를 부르는 곳 없음)

### 기능 지도

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 사이드바 토글(레이아웃 재배치) | 키 → 현재 탭의 pane들을 임시 탭으로 치우고 사이드바 pane을 끼운 뒤 원래 배치를 복원. 다시 누르면 사이드바만 닫음. nvim 내용은 포함하지 않음 | 매니페스트 `[[actions]] toggle`(:8-12) → `src/main.rs:30` → `src/maneuver.rs` `toggle`(:80), `open`(:124), `recover`(:252), `src/layout.rs` `plan_rebuild`(:133), `src/state.rs` | herdr CLI·컨텍스트 환경변수(공유 계약) | 핵심 | `capabilities/sidebar-toggle.md` · 미작성 | 코드 확인(상태 기계·위치별 분기). 실제 herdr 배치 결과는 미확인 |
| 탭별 nvim daemon 기동·부착 | 사이드바 pane이 `sidebar`로 시작 → 탭 daemon 보장(없으면 spawn, 10초 건강검진) → pane id 갱신 → `nvim --remote-ui` 부착 | 매니페스트 `[[panes]] sidebar`(:29-33) → `src/daemon/mod.rs` `sidebar_cmd`(:245), `ensure_daemon`(:50), `spawn_daemon`(:97) | 탭 키·소켓 규칙(공유 계약) | 핵심 | `capabilities/nvim-daemon.md` · 미작성 | 코드 확인 |
| daemon 자동 정리 | tab/workspace 닫힘 이벤트와 herdr 시작 시 gc가 고아 daemon을 `qa!`로 종료하고 소켓·상태 파일 삭제. 토글 때도 best-effort gc | 매니페스트 `[[events]]`(:71-77), `[[startup]]`(:81-82) → `src/daemon/events.rs` `on_event_cmd`(:57), `src/daemon/registry.rs` `gc_cmd`(:126), `gc`(:136), `stop_tab_key`(:182) | 탭 키·소켓 규칙, 이벤트 JSON | 핵심 | `capabilities/daemon-cleanup.md` · 미작성 | 코드 확인. 이벤트를 실제 herdr가 이 형식으로 보내는지는 미확인 |
| 댓글(주석) 편집 | nvim에서 줄·선택에 댓글을 달고 목록(float)에서 이동·수정·삭제. 메모리 안에서만 유지(extmark 추적). 전송은 포함하지 않음 | `lua/herdr-nvim/init.lua` `comment_range`(:58), `edit_comment`(:74), `list_comments`(:94), `comments.lua` `add`(:8), `ui.lua` `decorate`(:131), `comment_list`(:177), `commands.lua` `run`(:40) | 없음 | 핵심 | `capabilities/annotations.md` · 미작성 | 코드 확인 |
| 에이전트 전송·참조 | 댓글 전체를 에이전트 입력에 붙여넣기(`send`)·자동 제출(`submit`), 또는 `path:12-20` 참조만 삽입(`ref`, 제출 안 함). 대상 에이전트 자동 해석, 모호하면 선택창 | `init.lua` `deliver_to_agent`(:122), `send_all`(:150), `ref_range`(:179), `agents.lua` `list`(:4)·`resolve`(:38), `dispatch.lua` `send`(:4), `prompt.lua` `format`(:3)·`format_ref`(:53) | 댓글 편집(전송 대상 데이터), herdr CLI(공유 계약) | 핵심 | `capabilities/agent-send.md` · 미작성 | 코드 확인. 에이전트 쪽에 실제로 어떻게 보이는지는 미확인 |
| 파일 피커: 후보 수집 | `pick-file` 액션 → 대상 에이전트 pane 선택, 세션 로그·git·화면 스크랩 세 층에서 후보 파일을 모아 handoff 파일로 저장하고 팝업을 엶. 후보가 없으면 알림 | 매니페스트 `[[actions]] pick-file`(:35-39) → `src/bridge.rs` `pick_file_cmd`(:41), `start_pick`(:104), `target_agent_pane`(:81), `gather_candidates`(:144) → `sessions.rs`, `gitscan.rs`, `extract.rs`, `candidates.rs` `build_candidates` | Handoff 계약 | 핵심 | `capabilities/picker-candidates.md` · 미작성 | 코드 확인(`bridge.rs`·`sessions.rs:39-105`). `candidates/gitscan/extract` 내부 규칙은 함수 이름·모듈 주석 수준 |
| 파일 피커: 오버레이·선택 | 팝업 pane에서 crossterm 오버레이로 기본 뷰(세션 파일)와 입력 시 저장소 전체 퍼지 검색, Enter로 선택을 handoff에 쓰고 detach된 finisher 실행 | 매니페스트 `[[panes]] picker`(:17-21) → `src/picker.rs` `picker_cmd`(:329), `fuzzy_match`(:91), `spawn_finish`(:762), `src/fff.rs` | Handoff 계약 | 핵심 | `capabilities/picker-overlay.md` · 미작성 | 코드 확인(진입·종료 경로). 렌더·키 처리·fff 순위는 미확인 |
| 링크 클릭으로 파일 열기 | 에이전트 출력의 경로·`file://`를 Ctrl+클릭 → 경로 해석(pane cwd → git toplevel) → 사이드바 열고 해당 줄로 이동. 해석 실패는 조용히 무시 | 매니페스트 `[[link_handlers]]`(:54-66), `[[actions]] open-link`(:43-46) → `src/openlink.rs` `open_link_cmd`(:141), `parse_clicked`(:85), `resolve_click`(:98) → `bridge.rs` `open_in_sidebar`(:264) | 사이드바 토글, daemon 기동 | 핵심 | `capabilities/open-link.md` · 미작성 | 코드 확인. 정규식이 실제 출력에서 매치하는 범위는 미확인(매니페스트 주석의 의도만 읽음) |
| 설정·환경 보강 | `~/.config/herdr-nvim/config.toml`(sidebar·picker), PATH 보강, 홈 디렉터리 탐색. 잘못된 설정은 기본값 | `src/config.rs` `load`(:145), `src/path.rs` `augment_path`, `src/home.rs` `home_dir` | 없음 | 핵심 | `capabilities/config-env.md` · 미작성 | 코드 확인(`config.rs`). `path.rs`·`home.rs`는 모듈 주석만 확인 |
| 설치·빌드 훅 | herdr 설치 때 `[[build]]`가 실행: Unix는 릴리스 바이너리 다운로드 → 실행 검사 → 실패 시 `cargo build`, Windows는 소스 빌드만 | 매니페스트 `[[build]]`(:84-90), `herdr/install.sh`, `herdr/install.ps1` | 없음 | 부속 | `capabilities/install-hooks.md` · 미작성 | 코드 확인(스크립트 본문). 실행하지 않음 |
| daemon 점검 CLI | `herdr-nvim daemons`로 탭별 daemon 목록·메모리·상태, `daemons stop`으로 수동 종료. 저장 안 된 버퍼·댓글이 있으면 `--force` 필요 | `src/daemon/inventory.rs` `daemons_cmd`, `probe_expr`(:192), 정지는 `registry::stop_keys` | 탭 키·소켓 규칙, daemon 자동 정리(정지 경로 공유) | 부속 | `capabilities/daemons-cli.md` · 미작성 | 코드 확인(상태 정의·probe). 출력 형식·OS별 메모리 측정은 미확인 |
| 자가 진단 `doctor` | 스크래치 workspace를 만들어 분할·토글·daemon·원격 UI를 실제 herdr로 점검 후 정리 | `src/doctor.rs` `doctor_cmd`(:38), `run_checks`(:106) | 사이드바 토글, daemon 기동 | 부속 | `capabilities/doctor.md` · 미작성 | 코드 확인(앞부분 120줄). 개별 점검 항목은 미확인 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| herdr가 플러그인 프로세스에 주는 환경변수: `HERDR_PLUGIN_CONTEXT_JSON`(액션; `tab_id`·`workspace_cwd`·`focused_pane_cwd`), `HERDR_PLUGIN_EVENT_JSON`(이벤트), `HERDR_PLUGIN_CLICKED_URL`·`HERDR_PANE_ID`·`HERDR_WORKSPACE_ID`·`HERDR_TAB_ID`(링크 클릭), `HERDR_TAB_ID`·`HERDR_PANE_ID`(plugin pane) | 토글, 후보 수집, 링크 열기, 사이드바, 자동 정리 | `maneuver.rs` `read_ctx`(:33), `daemon/events.rs:58`, `openlink.rs` `read_click_env`(:129), `daemon/mod.rs:246-249` | `capabilities/herdr-env.md` · 미작성 | 코드 확인(받는 쪽 가정). herdr가 실제로 이 값을 주는지는 미확인 |
| herdr CLI 호출(Rust): `pane list/layout/get/move/close/resize/read/split/run`, `tab create`, `plugin pane open`, `agent list/focus`, `api snapshot`, `notification show` | 토글, 후보 수집, 정리, 점검, 링크 열기 | `src/herdr.rs` `trait Herdr`(:188), `CliHerdr`(:246-513), JSON 경로 `/result/...` | `capabilities/herdr-cli.md` · 미작성 | 코드 확인(호출 측). 응답 스키마 원본은 herdr 쪽이라 미확인 |
| herdr CLI 호출(Lua): `herdr agent list`(JSON `result.agents[]`), `herdr agent prompt <pane> <text>`(제출), `herdr pane send-text <pane> <text>`(비제출) | 에이전트 전송·참조 | `agents.lua:6-11`, `dispatch.lua:9,15` | 위와 합침 | 코드 확인(호출 측) |
| 탭 키·소켓·상태 파일 규칙: 탭 id `w26:t2` → 키 `w26_t2`(`:`→`_`). daemon 소켓 `<runtime>/<key>.sock`(Windows는 `\\.\pipe\herdr-nvim-<key>` + `<key>.pipe` 마커), 상태 `<state>/<key>.json`, 준비 마커 `<key>.<nonce>.ready` | 토글, daemon 기동, 정리, 점검, 링크 열기 | `state.rs` `tab_key`(:33)·`state_dir`(:93)·`ready_marker_path`(:115), `registry.rs` `socket_dir`(:39)·`socket_path_for_key`(:59) | `capabilities/tab-key-registry.md` · 미작성 | 코드 확인 |
| Rust→nvim daemon 원격 조작: `--headless --listen <sock>`로 기동, `--remote-expr 1+1`(건강검진), `--remote <path>`+`cursor(<line>,1)`(파일 열기), `--remote-send <cmd>qa!<cr>`(종료), `--remote-ui`(부착), `luaeval` probe | daemon 기동, 정리, 점검, 파일 피커·링크 열기 | `daemon/mod.rs:188-209`, `bridge.rs:312-346`, `registry.rs:202-226`, `inventory.rs:192-196` | `capabilities/daemon-remote.md` · 미작성 | 코드 확인 |
| Rust→Lua 암묵 계약: daemon 시작 시 `rtp+=<plugin_root>`와 VimEnter에서 `require('herdr-nvim').setup()`. 환경 `HERDR_WORKSPACE_ID`·`HERDR_TAB_ID`를 daemon에 주입, `HERDR_PANE_ID`는 `setenv`로 갱신. Lua가 읽는 것은 앞의 둘뿐 | daemon 기동 ↔ 에이전트 전송 | `daemon/mod.rs:112-115,126-139,221-227`, `agents.lua:14,40` | 위와 합침 | 코드 확인 |
| Handoff JSON(`candidates`, `chosen`, `workspace`, `tab`, `focused_pane`, `cwd`, `max_files`)을 임시 파일(`herdr-nvim-handoff-<pid>-<nanos>.json`)로 주고받음. 경로는 `HERDR_NVIM_HANDOFF` | 후보 수집 ↔ 피커 오버레이 | `picker.rs` `Handoff`(:50-65), `bridge.rs` `write_handoff`(:410), `finish_pick`(:227) | `capabilities/handoff.md` · 미작성 | 코드 확인 |
| 사이드바 열기 공통 경로 `open_in_sidebar`(daemon 보장 → 사이드바 보장 → 파일 열기 → `herdr agent focus`) | 후보 수집(finisher), 링크 열기 | `bridge.rs:264-283` | 위 기능 행에 흡수 | 코드 확인 |

**대조한 범위와 미탐색 영역**
- 대조: 매니페스트의 모든 항목(actions 3, panes 2, link_handlers 2, events 2, startup 1, build 2)과 `main.rs`의 서브커맨드 9개(`toggle`, `sidebar`, `daemon-gc`, `on-event`, `daemons`, `doctor`, `pick-file`, `picker`, `open-link`)가 일대일로 대응함을 확인했다(`main.rs:29-38`). README의 기능 4개(사이드바, 피커, 주석, 참조)와 `doc/herdr-nvim.txt`의 `:Herdr` 하위 명령 5개(`commands.lua:5`)도 대조했다.
- 문서와 구현의 차이:
  - `doc/herdr-nvim.txt:326-329`는 `:checkhealth herdr-nvim`을 안내하지만, 추적 파일에 `health.lua` 등 health 모듈이 없고 `lua/`·`src/` 어디에도 `checkhealth`가 없다. README는 `herdr-nvim doctor`(`README.md:223-226`)를 안내한다. 코드 확인(파일 목록·검색).
  - `README.md:238`은 `test`라는 한 줄로 끝나는데 의미가 없는 잔여 텍스트로 보인다(추론).
  - README의 사이드바 위치 설명은 "오른쪽"이지만 `position`으로 left/top/bottom도 구현돼 있다(`maneuver.rs:164-215`, `config.rs:76-84`). 반대로 README 설치절은 Windows 지원(`herdr-plugin.toml:5`)과 소스 빌드 전용 경로(`install.ps1`)를 언급하지 않는다.
  - "에이전트가 하나면 선택창을 생략" 규칙은 Lua 쪽(`agents.lua` `resolve`:38-49: 목록 1개, 아니면 같은 탭 1개)과 Rust 쪽 `target_agent_pane`(`bridge.rs:81-99`: 포커스된 에이전트 → 같은 탭 → 첫 에이전트)가 서로 다른 규칙이다. 각각 다른 기능의 규칙이라 모순은 아니다.
  - Lua 쪽은 `HERDR_PANE_ID`를 읽지 않는데 Rust는 매 부착마다 daemon에 그 값을 설정한다(`daemon/mod.rs:221-227`). 이 값을 소비하는 코드는 읽은 범위에서 못 찾았다(`ui.lua` 일부 미열람). 코드 확인(부재는 읽은 범위 기준).
  - 매니페스트 주석은 "`tab.closed`" 표기인데 이벤트 JSON 파서는 `tab_closed`(밑줄)를 받는다(`events.rs:34-35`). herdr가 양쪽을 어떻게 쓰는지는 미확인.
- 미탐색:
  - 기본으로 열지 않음(2장 3번 규칙): `tests/`, `tests/e2e/`, `.github/`, `CHANGELOG.md`, `.agents/`, `.githooks/`, `release-please-config.json`, `justfile`. 예외로 연 것 없음.
  - 이 분석에서 본문을 열지 않은 소스: `src/candidates.rs`, `src/extract.rs`, `src/gitscan.rs`, `src/fff.rs`, `src/path.rs`, `src/pathkey.rs`, `src/home.rs`, `src/test_support.rs`, `examples/fff_cold.rs`. 모듈 맨 위 주석과 함수 목록만 봤다.
  - 부분만 읽음: `src/picker.rs`(1-120, 320-410, 735-775), `src/maneuver.rs`(앞 330줄, 이후는 테스트), `src/herdr.rs`(앞 560줄), `src/daemon/inventory.rs`(앞 120줄, 186-215), `src/doctor.rs`(앞 120줄), `lua/herdr-nvim/ui.lua`(112-182, 296-314).
  - 외부 시스템 herdr의 실제 동작(CLI 응답 스키마, 환경변수 주입, 이벤트 이름, 링크 정규식 적용 방식)은 코드가 없어 `미확인`이다. 빌드·설치·실행은 하지 않았다(`실행 확인` 없음).

---

## 3. 구조 해설

구조도 없이 글만으로 구조를 읽도록 쓴 절이다(archify 구조도는 사용자 지시로 생략). 각 항목에 `파일:심볼`과 검증 수준을 붙였다.

**읽는 순서**
1. `herdr-plugin.toml`: herdr가 무엇을 언제 호출하는지의 전체 목록이다. 항목 하나가 `bin/herdr-nvim <서브커맨드>`가 된다.
2. `src/main.rs`: 서브커맨드 → 함수 분기표(:29-38). 시작 전에 `path::augment_path()`로 PATH를 넓힌다(:26).
3. 토글 흐름: `maneuver.rs` `toggle`(:80) → `layout.rs` `plan_rebuild`(:133) → `herdr.rs` `open_sidebar_pane`(:379) → 사이드바 pane의 `daemon::sidebar_cmd`(:245).
4. daemon 생명주기: `daemon/mod.rs` `ensure_daemon`(:50) → `registry.rs`(정지·gc) → `events.rs`(이벤트 훅).
5. nvim 쪽: `plugin/herdr-nvim.lua`(명령 등록) → `init.lua` `setup`(:29) → `comments.lua`·`ui.lua`(표시) → `init.lua` `deliver_to_agent`(:122) → `dispatch.lua`.
6. 파일 피커·링크: `bridge.rs` `start_pick`(:104) → `picker.rs` `picker_cmd`(:329) → `bridge.rs` `finish_pick`(:227) → `open_in_sidebar`(:264); 링크는 `openlink.rs` `open_link_cmd`(:141)에서 같은 `open_in_sidebar`로 합류.

**대표 흐름 하나: 사용자가 `prefix+e`를 누를 때(첫 토글, 오른쪽 사이드바)**
1. herdr가 `bin/herdr-nvim toggle`을 실행하며 `HERDR_PLUGIN_CONTEXT_JSON`을 넘긴다 → `read_ctx`가 탭 id와 cwd를 꺼낸다(`maneuver.rs:33-53`). 코드 확인.
2. 사이드바가 이미 `Open`이고 pane이 살아 있으면 그 pane만 닫고 상태 파일을 지운다(:93-97). 아니면 `recover`로 중단된 이전 시도를 복구한 뒤 `open`(:99-100). 코드 확인.
3. `open`은 pane 사각형을 읽어 분할 계획을 만들고, pane이 둘 이상이면 임시 탭으로 옮긴 뒤(`Evacuating` 상태 저장) 사이드바 pane을 `herdr plugin pane open --entrypoint sidebar`로 연다(:129-186). 계획대로 pane을 되돌리고 `ready_marker` 파일을 만든 뒤 `Open`으로 저장한다(:217-249). 코드 확인.
4. 새 pane에서 `bin/herdr-nvim sidebar`가 돌고, 준비 마커를 최대 2초 기다린 뒤 daemon을 보장하고 `nvim --remote-ui`로 부착한다(`daemon/mod.rs:245-258`, `:289-303`). 코드 확인.
5. 이후 사용자가 `<leader>ac`로 댓글을 달면 Lua가 daemon 안에서 처리하고(`init.lua:50-56`), `<leader>aS`면 `herdr agent prompt`를 불러 에이전트에 보낸다(`dispatch.lua:9`). 코드 확인.

**모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 매니페스트 | herdr에 액션·pane·링크 핸들러·이벤트·시작 훅·빌드 훅을 선언. 모두 `bin/herdr-nvim <서브커맨드>`를 가리킴 | herdr → 환경변수와 함께 명령 실행 | `herdr-plugin.toml:8-90` | 코드 확인(선언). herdr의 해석은 미확인 |
| 진입점 | 서브커맨드 분기, 종료 코드(성공 0, 오류 1, 사용법 2) | argv → 각 모듈 함수 | `src/main.rs` `main`(:22), `run`(:49) | 코드 확인 |
| 레이아웃 maneuver | 토글 상태 기계(`Evacuating`/`Open`), 복구, 위치(left/right/top/bottom) 처리 | herdr CLI(`Herdr` trait), 상태 파일, 준비 마커 | `maneuver.rs` `toggle`·`open`·`recover`, `state.rs` `Phase`(:11-15)·`StateFile`(:17-27) | 코드 확인 |
| 레이아웃 계획 | pane 사각형을 "길로틴 분할"(한 번에 한 직선으로 자르는 분할)로 나눠 복원 단계(`MoveStep`)를 계산. 겹치면 오류 | `Vec<PaneRect>` → `RebuildPlan` | `layout.rs` `plan_rebuild`(:133), `partition`(:85), `cut`(:57) | 코드 확인 |
| herdr 어댑터 | herdr CLI를 서브프로세스로 호출하고 JSON 응답에서 필요한 값만 포인터로 꺼냄. `Herdr` trait이라 테스트에서 교체 가능 | `herdr <args>` → JSON/텍스트 | `herdr.rs` `trait Herdr`(:188), `CliHerdr::output`(:252) | 코드 확인 |
| daemon 관리 | 탭별 nvim spawn(세션 분리·detach), 건강검진, 원격 UI 부착, 플러그인 루트 탐색 | nvim CLI 원격 옵션, 소켓/파이프 | `daemon/mod.rs` `ensure_daemon`(:50), `spawn_daemon`(:97), `plugin_root`(:308) | 코드 확인 |
| daemon 레지스트리 | 소켓 디렉터리를 레지스트리로 써서 daemon 열거, 고아 판정, 종료(`qa!`) 후 파일 정리. 정지 경로는 하나(`stop_keys`) | 런타임 디렉터리, herdr `api snapshot` | `registry.rs` `daemon_keys`(:90), `gc`(:136), `stop_tab_key`(:182) | 코드 확인 |
| 이벤트 훅 | 닫힌 tab/workspace의 daemon 종료. workspace 닫힘은 그 workspace의 모든 daemon | `HERDR_PLUGIN_EVENT_JSON` → 정지 | `events.rs` `parse_close_event`(:24), `on_event_cmd`(:57) | 코드 확인 |
| 파일 브리지 | 후보 수집 1단계와 finisher 2단계, 사이드바 열기·파일 열기 공통 경로 | herdr 응답, Handoff 파일, nvim 원격 | `bridge.rs` `start_pick`(:104), `finish_pick`(:227), `open_in_sidebar`(:264) | 코드 확인 |
| 피커 오버레이 | 터미널 오버레이 UI, 퍼지 매칭, 선택을 Handoff에 기록하고 finisher를 detach 실행 | Handoff 파일 | `picker.rs` `picker_cmd`(:329), `spawn_finish`(:762) | 코드 확인(진입·종료). UI 세부는 미확인 |
| 링크 열기 | 클릭 문자열을 `(path, line)`으로 파싱(`file://` 해제, 퍼센트 디코딩, 문장부호 제거), 경로 해석 후 `open_in_sidebar` | 환경변수 → 사이드바·nvim | `openlink.rs` `parse_clicked`(:85), `resolve_click`(:98) | 코드 확인 |
| Lua 코어 | 댓글 저장(extmark 추적), 장식, 전송 깔때기(에이전트 해석 → 페이로드 → 전송 → 성공 시 정리) | nvim API, `herdr` CLI, `git rev-parse` | `init.lua`, `comments.lua` `store`(:3), `ui.lua` | 코드 확인 |
| Lua 에이전트·전송 | `herdr agent list`를 workspace로 거르고 정렬, 모호하지 않으면 자동 선택, `prompt`/`send-text` 구분 | JSON 문자열 ↔ 테이블, `argv` 실행 | `agents.lua` `list`·`resolve`, `dispatch.lua` `send`, `exec.lua` `default_exec`(:3) | 코드 확인 |
| Lua 명령·프롬프트 | `:Herdr` 하위 명령 등록·완성, 에이전트에 보낼 텍스트 형식과 경로 단축 | 명령 인자 → 함수 호출, 댓글 → 문자열 | `commands.lua` `register`(:8)·`run`(:40), `prompt.lua` `format`(:3)·`location`(:38) | 코드 확인 |
| 설정 | herdr 쪽 TOML(`sidebar`, `picker`)과 nvim 쪽 `setup{}` 옵션(`init.lua:8`)이 별개 | 파일 → 구조체 | `config.rs` `Config`(:22), `load`(:145) | 코드 확인 |
| 설치 스크립트 | 릴리스 바이너리를 받아 인자 없이 실행해 종료 코드 2인지로 호환 검사, 아니면 소스 빌드. Windows는 VS 2022 개발자 프롬프트로 빌드 | 네트워크, cargo, `bin/` | `install.sh:30-55`, `install.ps1:15-45` | 코드 확인(읽기만) |

**미확인 영역**
- 3절의 모든 herdr 측 동작(manifest 해석, 환경변수 주입, 링크 매칭, 이벤트 전달)은 herdr 쪽 코드가 없어 확인하지 못했다. 이 레포는 "그렇게 가정하고 작성됨"의 증거만 준다.
- 후보 수집의 세부 규칙(세션 로그 파서 방언, git 필터, 스크랩 필터, 병합 순서), 피커 렌더링, fff 연동은 열지 않았다.
- `ui.lua` 중 `visual_region`·`comment_list` 본문, `maneuver.rs`·`picker.rs`·`doctor.rs`의 테스트와 나머지 구간은 읽지 않았다.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음에 볼 곳** (사용자 지시는 overview까지라 아래는 후보일 뿐):
  - 토글의 실패·복구 경로: `maneuver.rs` 테스트 구간 이전의 `recover`와 `Evacuating` 저장 시점, 그리고 `herdr.rs` 뒷부분(:560 이후).
  - 후보 수집 세 층의 병합 규칙: `candidates.rs` `build_candidates`, `sessions.rs`(:107 이후), `extract.rs`, `gitscan.rs`.
  - `HERDR_PANE_ID`를 daemon에 설정하는 목적: `ui.lua` 나머지와 `tests/`가 아니라 `daemon/mod.rs:217-227` 주석 기준으로 소비처가 있는지 재확인.
  - herdr 쪽 원본(별도 레포)과 매니페스트 스키마를 대조해 `미확인`으로 둔 항목 해소.
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸(전부 미작성).
