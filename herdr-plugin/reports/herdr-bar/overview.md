---
sha: "261de9b0441a6972941414bbf16eb4f5df27ac34"
created: 2026-10-22
updated: 2026-10-22
sources:
  - herdr-plugin.toml
  - README.md
  - Cargo.toml
  - LICENSE
  - scripts/install.sh
  - scripts/install.ps1
  - src/main.rs
  - src/cli.rs
  - src/opener.rs
  - src/client.rs
  - src/title_watcher.rs
  - src/renaming_guard.rs
  - src/tab_status.rs
  - src/auto_title.rs
  - src/items.rs
  - src/app.rs
  - src/config.rs
  - src/icons.rs
  - src/fuzzy.rs
---

# herdr-bar Analysis Overview

경로 표기: 이 문서의 `파일:줄`은 모두 `repos/herdr-bar/` 기준이다. 검증 수준은 `코드 확인` / `추론` / `미확인`만 쓴다(이번 분석은 실행하지 않았으므로 `실행 확인`은 없다).

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/jeffarese/herdr-bar` (`artifacts/herdr-bar/repo-metadata.txt`)
- **작업트리 상태**: Clean (shallow clone `--depth 50`, 2026-10-22, 마지막 커밋 2026-10-21, 브랜치 `main`)
- **분석 목적**: 학습 · 도입 검토. herdr 플러그인이 `herdr-plugin.toml`(매니페스트)을 통해 herdr와 어떻게 연동하는지 본다.
- **라이선스**: MIT — `LICENSE`(1줄 "MIT License", 3줄 "Copyright (c) 2026 Jeff Arese"). `Cargo.toml:7`의 `license = "MIT"`와 README 끝도 MIT. 하위 디렉터리에 다른 LICENSE는 없다(Glob 결과 루트 한 개). (코드 확인)
- **분석 대상 제품**: 단일 Rust 바이너리 `herdr-bar`(`Cargo.toml:10-12`, 버전 0.11.0, 최소 Rust 1.88). 같은 레포의 부속물: `scripts/install.{sh,ps1}`(설치 단계), `examples/record_demo/`(README 데모 녹화용, `demo` feature에서만 빌드. `Cargo.toml:14-21`), `tests/`, `assets/demo.gif`. (코드 확인)
- **스펙 범위**: 지도만(기능 스펙 미작성, 사용자 지시는 overview까지). 승인 전.

용어(처음 한 번만).
- **herdr**: 코딩 에이전트용 터미널 멀티플렉서. 이 문서의 "workspace > tab > pane" 계층과 "agent"(pane에서 돌아가는 에이전트)는 herdr의 개념이다.
- **매니페스트**: 플러그인 루트의 `herdr-plugin.toml`. herdr가 읽고 설치·실행 방법을 얻는 선언 파일.
- **스냅샷**: herdr 소켓의 `session.snapshot` 응답. 전체 workspace·tab·pane·agent 목록.

---

## 2. 프로젝트 개요

README는 herdr-bar를 "자동 탭 제목, 알아보기 쉬운 에이전트 아이콘, 빠른 세션 전환을 하는 herdr 플러그인"이라 소개한다(`README.md:5-8`). 코드로 보면 **두 종류의 프로세스**가 같은 바이너리 하나에 들어 있다.

1. **바 팝업**: 사용자가 키를 누르면 herdr가 팝업 pane으로 띄우는 짧은 TUI. 스냅샷을 읽어 tab·agent·pane·workspace를 한 목록으로 만들고, 퍼지 검색으로 고르면 herdr에 포커스 이동을 요청한다(`src/app.rs:1198-1213`, `src/items.rs:334-500`).
2. **백그라운드 watcher**: herdr 서버마다 하나 뜨는 장수 프로세스. 에이전트의 작업 제목으로 탭 이름을 바꾸고(옵션) 탭 이름에 상태 글리프를 붙인다(`src/title_watcher.rs:441-595`).

(코드 확인) 이름이 "Cmd+K"인 것은 README의 안내일 뿐이다. 매니페스트에는 키 바인딩이 없고 `open` 액션만 선언되어 있어, 키는 사용자가 herdr `config.toml`에서 연결한다(`herdr-plugin.toml:29-34`, `README.md:50-61`). (코드 확인: 매니페스트 / 추론: 바인딩은 herdr 쪽 규칙)

### 기능 지도

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 플러그인 설치·배포 | `herdr plugin install` 때 매니페스트의 `[[build]]`가 플랫폼별 스크립트를 실행: 릴리스 바이너리 내려받기 → SHA256SUMS 확인 → 실패 시 `cargo build --release`. 결과 `bin/herdr-bar` | `herdr-plugin.toml:17-23`, `scripts/install.sh:24-47`·`:106-134`·`:152-164` | 없음 | 핵심(연동 지점) | `capabilities/install-build.md` · 미작성 | 코드 확인(sh) / ps1은 머리 주석만 읽어 추론 |
| 팝업 열기 | 액션 `open` → `bin/herdr-bar --open` → herdr CLI `plugin pane open ... --entrypoint bar --placement popup`을 `exec`(Windows는 자식으로 실행). 키 바인딩·팝업 크기는 매니페스트 `[[panes]]` | `herdr-plugin.toml:29-52`, `src/main.rs:38-48`, `src/opener.rs:6-7`·`:46-69` | 설치 | 핵심(연동 지점) | `capabilities/open-popup.md` · 미작성 | 코드 확인 |
| 바 UI: 목록·퍼지 검색·필터 | 스냅샷에서 agent/tab/pane/workspace 행 생성, 공백 구분 AND 퍼지 매칭, `@ % $ !` 필터, 최근 방문·상태 순서, 미리보기, 실행 시간 | `src/cli.rs:162-288`(조립), `src/items.rs:73-122`·`:334-500`, `src/app.rs:23-44`·`:101-128`·`:1084-1130`, `src/fuzzy.rs:1-7` | 팝업 열기, herdr 소켓 클라이언트(공유 계약) | 핵심 | `capabilities/bar-search.md` · 미작성 | 코드 확인(행 생성·필터·점수 합산·루프) / 정렬 규칙 세부·렌더링은 미탐색 |
| 바 동작: 이동·탭 닫기·이름 변경 | Enter → `tab.focus` + `agent.focus`/`pane.focus` 또는 `workspace.focus`. 닫기는 확인 후 `tab.close`. `ctrl+r`은 `tab.rename` | `src/app.rs:1198-1213`(jump), `:745-753`(close), `:637-652`(rename), `src/cli.rs:273-287` | 바 UI | 핵심(연동 지점) | `capabilities/bar-actions.md` · 미작성 | 코드 확인 |
| 에이전트 아이콘 | Herdr Agent Icons Max 폰트가 있으면 vendor 로고 코드포인트(U+E1A0~)를 행·탭 이름에 씀. 없으면 텍스트 라벨 | `src/icons.rs:14-27`·`:59-85`, `src/config.rs:84`(`agent_icons` 키) | 없음 | 부속 | `capabilities/agent-icons.md` · 미작성 | 코드 확인(감지·코드포인트) / 터미널이 폰트를 실제로 그리는지는 미확인 |
| 자동 탭 제목 | 이름 없는 Claude/Codex 탭에 에이전트 작업 제목을 `tab.rename`으로 기록. 사용자·타 플러그인이 지은 이름은 건드리지 않음(소유 기록 `auto-titles.json`) | `src/auto_title.rs:539-650`(후보), `:735-812`(`apply_inner`), `:682-687`(활성 조건) | watcher 수명주기, 이름 충돌 방지 | 핵심 | `capabilities/auto-titles.md` · 미작성 | 코드 확인(후보 선정·재확인 후 쓰기) / Claude transcript 읽기(`src/auto_title.rs:229`의 `TranscriptReader`)는 미탐색 |
| 탭 상태 글리프 | `tab_status: true`이면 탭 이름 앞에 `로고 + ◉◐●✓○`를 붙임. 에이전트 상태 이벤트로 갱신, 소유한 접두어만 복원 | `src/tab_status.rs:33-34`·`:77-84`·`:203-289`·`:346-421`·`:483-502` | watcher 수명주기, 이름 충돌 방지 | 핵심(연동 지점) | `capabilities/tab-status.md` · 미작성 | 코드 확인 |
| watcher 수명주기 | `[[startup]]`·`pane.agent_detected` 이벤트·액션 `start-titles`/`stop-titles`가 같은 진입점을 부름. 서버당 싱글턴 잠금, 정지 표지 파일, 플러그인 교체 시 재실행, 백오프 재연결 | `herdr-plugin.toml:54-73`, `src/cli.rs:176-202`, `src/title_watcher.rs:126-260`·`:441-595` | 설치 | 핵심(연동 지점) | `capabilities/title-watcher.md` · 미작성 | 코드 확인 / Windows 스테이징 복사 경로는 읽기만(`:78-112`) |
| 이름 충돌 방지(renaming guard) | `plugin.list`로 활성 플러그인을 읽어 이름 변경 플러그인이 있으면 자동 쓰기를 전부 중단 | `src/renaming_guard.rs:10-16`·`:148-197`·`:199-225`, `src/title_watcher.rs:308-323` | herdr API 클라이언트 | 핵심(연동 지점) | `capabilities/renaming-guard.md` · 미작성 | 코드 확인 / `naming_search` 패턴 세부(`:122`)는 미탐색 |
| 설정·진단·상태 파일 | `config.json`(`HERDR_PLUGIN_CONFIG_DIR`)을 읽고 잘못되면 기본값. `--doctor`/`--list`/`--version`. 최근 방문 `recent.json` | `src/config.rs:14-35`·`:74-123`, `src/cli.rs:20-33`·`:41-51`·`:81-160`, `src/mru.rs` | 없음 | 부속 | `capabilities/config-diagnostics.md` · 미작성 | 코드 확인(config·CLI) / `mru.rs`는 열지 않음(미탐색) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 herdr 연동 규약)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| herdr 소켓 JSON 프로토콜(요청 한 줄 = 연결 하나, 줄바꿈 구분 JSON), CLI 대체 경로 | 바 UI·바 동작·watcher·guard | `src/client.rs:1-10`·`:138-155`·`:215-236` | `capabilities/herdr-client.md` · 미작성 | 코드 확인(클라이언트 쪽) / herdr 서버 쪽 동작은 미확인 |
| 이벤트 구독 `events.subscribe` | tab 상태 글리프, watcher | `src/client.rs:443-544`, `src/tab_status.rs:483-502` | `capabilities/herdr-client.md` | 코드 확인(클라이언트 쪽) |
| 환경변수 계약(herdr가 주입한다고 가정하는 값) | 전부 | 아래 표 | — | 코드 확인(사용처) / 주입 주체는 추론 |
| 플러그인 상태 파일(`recent.json`, `title-servers/<해시>/…`) | 바, watcher | `src/cli.rs:41-51`, `src/auto_title.rs:27-34` | — | 코드 확인 |

**herdr와 주고받는 것 정리** (herdr 쪽 정의는 이 레포에 없으므로 모두 "클라이언트가 그렇게 가정한다"는 근거)

| 방향 | 항목 | 코드 근거 | 검증 수준 |
|---|---|---|---|
| 매니페스트 → herdr | `[[build]]`(sh/ps1), `[[actions]]` 4개(`open`, `open-windows`, `start-titles`, `stop-titles`), `[[panes]]` `bar`(popup 74%×62%), `[[startup]]`, `[[events]] on="pane.agent_detected"` | `herdr-plugin.toml:17-73` | 코드 확인 |
| 소켓 요청 | `session.snapshot`, `pane.read`, `pane.process_info`, `tab.focus`, `tab.close`, `tab.rename`, `workspace.focus`, `agent.focus`, `pane.focus`, `plugin.list`, `events.subscribe` | `src/client.rs:240`·`:287`·`:302`·`:351`·`:355`·`:364`·`:373`·`:377`·`:385`, `src/renaming_guard.rs:149`, `src/client.rs:511-515` | 코드 확인 |
| CLI 대체 | `api snapshot`, `pane read`, `pane process-info`, `tab close/rename/focus`, `workspace focus`, `agent focus`, `plugin list`. `pane.focus`는 CLI 형태가 없어 소켓이 없으면 아무 일도 안 함 | `src/client.rs:241`·`:292`·`:306`·`:352`·`:359`·`:368`·`:374`·`:378`·`:381-397`, `src/renaming_guard.rs:149` | 코드 확인 |
| 이벤트 | `pane.agent_detected`, `pane.agent_status_changed`(pane별) 구독. 이벤트 내용은 해석하지 않고 깨우기 신호로만 씀 | `src/tab_status.rs:497-499`, `src/client.rs:443-449` | 코드 확인 |
| 환경변수 | `HERDR_SOCKET_PATH`, `HERDR_BIN_PATH`, `HERDR_PLUGIN_CONFIG_DIR`, `HERDR_PLUGIN_STATE_DIR`, `HERDR_PLUGIN_ROOT` | `src/client.rs:114`, `src/opener.rs:15`, `src/config.rs:108`, `src/cli.rs:42`, `src/title_watcher.rs:39` | 코드 확인(읽는 쪽) / herdr가 주입한다는 점은 추론 |
| herdr CLI 호출 | `herdr plugin pane open --plugin herdr-bar --entrypoint bar --placement popup` | `src/opener.rs:6-7` | 코드 확인 |

**대조한 범위와 미탐색 영역**
- 대조: `README.md` 전체(기능 목록, 설치, 동작 설명 "How it works"), `herdr-plugin.toml` 전체, `src/main.rs`·`cli.rs`·`opener.rs`·`client.rs`·`title_watcher.rs`·`renaming_guard.rs`·`tab_status.rs`·`config.rs`, `app.rs`·`items.rs`·`auto_title.rs`·`icons.rs`·`fuzzy.rs`의 해당 구간. 열어 본 이유: 매니페스트가 부르는 `install.sh`/`install.ps1`는 설치 동작을 정하므로 연 것이다(`install.ps1`은 머리 주석만 읽음).
- README와 코드가 일치한 점(코드 확인): watcher 주기 2초·플러그인 등록 확인 10초·재연결 백오프 최대 30초(`src/title_watcher.rs:17-19`, 백오프 `:579`), Windows는 이벤트 스트림 없이 폴링(`src/client.rs:443-449`·`:587-591`), 구독 이벤트 종류(`src/tab_status.rs:497-499`), 닫기·이동에 쓰는 API 이름(`src/client.rs`), 수동 `ctrl+r` 이름 변경은 guard를 거치지 않는 원시 클라이언트 사용(`src/renaming_guard.rs:199`, `src/app.rs:645`).
- 문서와 구현의 차이: ① README는 8개 에이전트에 아이콘이 있다고 쓰지만(`README.md:16-17`) 코드의 폰트 코드포인트 목록은 24종(`src/icons.rs:15-19`). ② `--help` 문구에 옛 Python 시절 이름 `run.py`가 남아 있다(`src/cli.rs:22`). ③ watcher 시작 코드에 Python 진입점(`python3 run.py`) 폴백이 남아 있다(`src/title_watcher.rs:116-123`)(README "0.8 이하 Python watcher" 업그레이드 안내와 대응, 추론).
- 미탐색: `tests/`, `.github/`, `CHANGELOG.md`, `assets/`, `examples/record_demo/`(기본 제외 규칙); `src/render.rs`·`theme.rs`·`term.rs`·`keys.rs`·`mru.rs`·`host.rs`·`pyjson.rs` 등 UI 렌더링·터미널·직렬화 보조(범위 밖); `auto_title.rs`의 transcript 읽기·제목 정리 helper; README 성능 수치(첫 프레임 24ms 등)는 미확인.

---

## 3. 구조 해설 (글로만 읽는 구조)

시각화는 사용자 지시로 만들지 않았다. 아래 글과 표만으로 구조를 따라갈 수 있게 쓴다.

**읽는 순서**
1. `herdr-plugin.toml` — herdr가 이 플러그인에서 무엇을 부르는지(액션 4개, 팝업 pane 1개, startup 1개, 이벤트 1개)를 먼저 본다.
2. `src/main.rs:38-48` → `src/cli.rs:162-288` — 모든 진입이 이 한 바이너리의 인자(`--open`, `--start-titles`, `--watch-titles`, `--stop-titles`, 인자 없음=바)로 갈라진다.
3. `src/client.rs` — herdr와의 유일한 통로. 바와 watcher가 같이 쓴다.
4. 바 경로: `src/items.rs` → `src/app.rs`(`Bar::run`, `jump`).
5. watcher 경로: `src/title_watcher.rs` → `src/auto_title.rs` + `src/tab_status.rs` → `src/renaming_guard.rs`.

**두 흐름 요약**

바(팝업): 사용자가 연결해 둔 키 → herdr가 액션 `open` 실행 → `bin/herdr-bar --open`이 herdr CLI로 팝업 pane 요청(`src/opener.rs:46-69`) → herdr가 `[[panes]] bar`의 `bin/herdr-bar`를 팝업으로 실행(`herdr-plugin.toml:45-52`) → 인자 없는 실행이 TTY 확인 후(`src/cli.rs:217-219`) 스냅샷을 읽고(`:235`) 행 목록을 만들어 TUI 루프를 돈다(`:270`, `src/app.rs:1084-1130`) → Enter 시 `jump`로 포커스 요청(`src/cli.rs:275`). 팝업이 열릴 때마다 watcher 시작도 시도한다(`src/cli.rs:254`, 정지 표지가 있으면 시작하지 않음 `src/title_watcher.rs:163-165`).

watcher: `[[startup]]`·`pane.agent_detected`가 `--start-titles`를 실행 → 잠금을 잡고 자기 자신을 `--watch-titles`로 분리 실행(`src/title_watcher.rs:126-251`) → 워커가 2초마다 스냅샷을 읽고, 설정을 다시 읽고, 제목 후보를 계산하고, 상태 접두어를 맞춘다(`:518-558`) → 이벤트 구독으로 상태 변화에 즉시 깨어난다(`:554`, `:589`).

**구조: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 매니페스트 | herdr에 빌드·액션·팝업 pane·startup·이벤트 훅을 선언 | herdr가 읽음. 모든 명령은 `bin/herdr-bar <인자>` | `herdr-plugin.toml:17-73` | 코드 확인(선언) / herdr가 이를 처리하는 방식은 미확인 |
| 디스패처 | 인자로 바·열기·watcher 시작/정지/워커·진단을 분기 | 인자 → 종료 코드 | `src/main.rs:38-48`, `src/cli.rs` `main` | 코드 확인 |
| opener | herdr CLI로 팝업 pane 열기 | `HERDR_BIN_PATH`(없거나 못 쓰면 PATH의 `herdr`) → CLI 인자 | `src/opener.rs` `popup_command`, `open_bar`, `herdr_bin` | 코드 확인 |
| herdr 클라이언트 | 소켓 JSON 한 줄 요청, 실패 시 CLI 폴백, 이벤트 스트림 | 메서드 이름+params → `result` 딕셔너리, 오류 → `HerdrError` | `src/client.rs` `HerdrClient::call`, `snapshot_since`, `EventStream` | 코드 확인 |
| 행 모델 | 스냅샷을 agent/tab/pane/workspace 행으로 변환, 검색 필드 구성 | 스냅샷 → `Item` 목록 | `src/items.rs` `build_items`, `build_pane_items`, `Item::new` | 코드 확인 |
| 바 앱 | 필터·검색·선택·미리보기·닫기 확인·이름 변경·이동 | 키 입력 → 소켓 호출(`pane.read`, `pane.process_info`, `tab.*`, `*.focus`) | `src/app.rs` `Bar::run`, `Bar::refresh`, `jump` | 코드 확인 |
| watcher 런처·워커 | 서버별 싱글턴, 정지 표지, 플러그인 교체 감지, 재연결 | 상태 디렉터리 파일(`*.lock`, `title-watcher.stopped`, `title-watcher.log`) | `src/title_watcher.rs` `start`, `launch`, `watch`, `replace`, `stop` | 코드 확인 |
| 자동 제목 | 이름 없는 Claude/Codex 탭의 후보 계산, 쓰기 직전 재검증 후 `tab.rename` | 스냅샷+소유 기록 → 이름 쓰기. 기록은 `auto-titles.json` | `src/auto_title.rs` `candidates`, `AutoTitles::apply_inner` | 코드 확인 |
| 탭 상태 | 탭 이름에 글리프 접두어 합성·제거, 소유 기록, 구독 목록 생성 | 스냅샷 → 접두어 붙은 `tab.rename`. 기록은 `tab-status.json` | `src/tab_status.rs` `TabStatus::sync`, `compose`, `subscriptions` | 코드 확인 |
| renaming guard | 다른 이름 변경 플러그인 감지, 자동 쓰기 차단 | `plugin.list` → 충돌 시 `Kind::Renaming` 오류 | `src/renaming_guard.rs` `check_plugins`, `AutomaticTabClient::rename_tab` | 코드 확인 |
| 설정 | `config.json` 읽기, 기본값 | `HERDR_PLUGIN_CONFIG_DIR` → `Config` | `src/config.rs` `Config::load`, `from_values` | 코드 확인 |
| 설치 스크립트 | 릴리스 바이너리 내려받기·체크섬·버전 확인·폴백 빌드 | 매니페스트 버전 → `bin/herdr-bar` | `scripts/install.sh` `download`, `build_from_source` | 코드 확인(sh) / ps1 추론 |

**미확인 영역**
- herdr 서버가 소켓 요청·이벤트·`plugin.list` 응답을 실제로 어떤 형태로 주는지(이 레포는 클라이언트일 뿐).
- 환경변수를 herdr가 주입하는 규칙과 `[[panes]]`/`[[events]]` 필드의 의미(herdr 문서 미열람).
- `install.ps1` 본문, Windows 경로 전반(명명 파이프·스테이징 복사).
- 실제 실행 결과(실행하지 않음).

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음에 볼 곳

- 지도의 어느 행을 스펙으로 쓸지 사용자 승인이 필요하다(특히 `부속` 행). 추천 시작점은 연동 지점이 몰린 `watcher 수명주기`와 `herdr 클라이언트`(공유 계약).
- herdr 쪽 정의 확인: herdr 플러그인 문서·소스에서 `[[events]]`, `[[panes]]`, `plugin_action`, 환경변수 주입을 확인하면 "미확인" 항목이 줄어든다.
- `install.ps1`과 Windows 경로, `auto_title.rs`의 Claude transcript 읽기(`TranscriptReader`)는 아직 안 읽었다.
- 매니페스트에 있는 `link_handlers` 등 다른 선언 항목은 이 레포의 `herdr-plugin.toml`에는 없다(`herdr-plugin.toml` 전체 73줄 확인). 사용된 항목은 build/actions/panes/startup/events뿐이다.
