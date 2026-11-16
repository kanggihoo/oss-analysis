---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-15
updated: 2026-11-15
sources:
  - crates/engine/src/clean_room.rs
  - crates/engine/src/lib.rs
  - crates/engine/src/session.rs
  - crates/engine/src/settings.rs
  - crates/engine/src/target.rs
  - crates/engine/src/tool.rs
  - crates/engine/src/registry.rs
  - crates/engine/src/plugins.rs
  - crates/engine/src/tools/website_tools.rs
  - crates/engine/src/tools/interaction_tools.rs
  - crates/engine/src/tools/setup_tools.rs
  - crates/engine/src/tools/deep.rs
  - crates/engine/src/tools/android_tools.rs
  - crates/engine/src/tools/report_tools.rs
  - crates/evidence/src/lib.rs
  - crates/mcp/src/lib.rs
  - crates/ai/src/agent.rs
  - crates/ai/src/cli_agents/mod.rs
  - crates/ai/src/cli_agents/acp.rs
  - apps/craft-anything-cli/src/main.rs
depends:
  - ./evidence-record.md
status: ready
---

# Clean room / Deep 모드

> 세션이 Clean room(대상 안쪽을 읽지 않음)인지 Deep(모든 도구 허용)인지 정하고(설정, 또는 CLI 실행 한 번의 `--deep`/`--clean-room`), Clean room에서는 도구 id 허용 목록(`TOOLS`)에 없는 도구를 호출 시점에 `clean_room` 이유로 거부하고 목록에서 숨기며, 그 모드를 증거의 `environment.clean_room`과 보고서의 "Mode" 줄에 남긴다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 모드 값 정하기: `deep_for_run`(CLI의 `--deep`/`--clean-room`, 저장되지 않음)이 있으면 그 값, 없으면 저장된 설정 `deep_mode`(기본 false). `session.clean_room()`이 이 결과의 부정이다(R-01).
2. 도구 목록 만들기: MCP `tools/list`, 내장 에이전트의 도구 목록, CLI 도구 목록은 Clean room이면 `allows(id)`가 아닌 도구를 뺀다(R-06, R-07).
3. 호출: `Engine::call`이 도구 id를 찾은 뒤 세션 잠금 안에서, 동의 검사와 사용 가능성 검사보다 먼저 `Clean room && !allows(id)`이면 `feature_missing` 오류를 돌려준다. 호출 결과는 거부도 저널에 남는다(R-03).
4. 허용된 도구 중 일부는 Clean room에서 결과를 스스로 줄인다(예: `web_site_capture`가 페이지 HTML·스크립트·요청을 남기지 않음, R-12). 빌더가 쓰는 도구(`build_*`, `core_action_approve`)는 원본 폴더·호스트를 건드리는 동작을 따로 거부한다(R-13).
5. 도구가 증거를 만들 때 `Environment.clean_room`에 세션 모드를 적는다(R-14). 보고서는 쓰는 시점의 모드를 문구로 적는다(R-15).
6. 거부를 받은 클라이언트는 `is_refusal`로 알아보고 Deep 켜기를 제안한다(R-05). 에이전트 스킬은 이 경우 우회하지 말고 사용자에게 Deep이 필요하다고 말하라고 지시한다([method-guidance.md](method-guidance.md) R-12).

### 1.2 범위·통합 지점
- 제공: 모드 판정, 허용 목록과 `allows`·`availability`·`refusal`·`is_refusal`·`mode_words`, 호출·목록 양쪽의 강제 지점, CLI 플래그, 플러그인 도구의 거부 방식, `web_site_capture`의 Clean room 축소, 빌더용 `off_limits` 거부, `Environment.clean_room` 기록 규칙, 목록의 기준과 실제가 어긋난 도구.
- 제외:
  - 도구 각각이 하는 일(행 12, 15). 이 스펙은 허용 여부만 정한다.
  - Clean room 빌더에게 주는 브리프 문구(행 8 [builder-brief.md](builder-brief.md) R-03·R-09가 정의). 이 스펙은 문구를 다시 쓰지 않는다.
  - 에이전트 CLI 구동 중 "에이전트 자신의 파일·명령 도구"를 막는 방식과 Deep 세션 재사용 거부(행 13. `crates/ai/src/cli_agents/mod.rs:636-646`, `acp.rs:98-104`, `rebuild/mod.rs:604`)와 리빌드 연구 단계가 Deep 때 남긴 파일을 지우는 일(행 7, `rebuild/tests.rs:1678-1704`). 경계만 R-17에 적는다.
  - UI의 Deep 스위치·모달·Ghidra 안내(행 18). 거부 시 모달을 연다는 사실만 R-05에 적는다.
- 외부 의존·선행 계약: 선행 [evidence-record.md](evidence-record.md)의 `Environment` 필드와 id 계산(환경이 id에 들어간다, R-03). `ToolError`·`ErrorCode::FeatureMissing`. 세션(`Session`)과 레지스트리의 도구 id 목록.
- 소유 상태·부작용: `Session.deep_for_run`(프로세스 메모리, 저장 안 됨), `Settings.deep_mode`(`config.toml`, `settings_set`으로 변경), 증거의 `environment.clean_room`. 허용 목록은 컴파일된 상수다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `Settings.deep_mode` | bool, 기본 false, `config.toml` 최상위 키 `deep_mode` | true = Deep. false = Clean room(기본). 구 설정의 Ghidra 켜짐 값은 불러올 때 이 키로 옮겨진다. |
| `Session.deep_for_run` | optional bool | 이 프로세스에만 적용되는 덮어쓰기. 저장되지 않는다. |
| `Session::clean_room()` | → bool | `!deep_for_run.unwrap_or(settings.deep_mode)`. |
| CLI `--deep` / `--clean-room` | 전역 플래그(서브명령 앞뒤 어디든), 서로 배타 | 이 실행의 모드. 둘 다 없으면 `deep_for_run`은 없음. |
| `clean_room::TOOLS` | 문자열 id 109개(정적 목록) | 목록은 C-01. |
| `clean_room::allows(id)` | string → bool | `TOOLS`에 정확히 같은 문자열이 있으면 true. |
| `clean_room::availability(id, clean_room)` | → optional `Availability` | Clean room이고 허용되지 않으면 불가(이유·해결 문구 포함, `details` 없음). 그 밖에는 없음. |
| `clean_room::refusal(id)` | → `ToolError` | 코드 `feature_missing`, 메시지 = 이유 문구, remediation = Deep 켜는 법, `details = {"reason": "clean_room", "tool": id}`. 문구는 C-01. |
| `clean_room::is_refusal(e)` | `ToolError` → bool | `details.reason == "clean_room"`이면 true. |
| `clean_room::mode_words(clean_room)` | bool → string | Clean room = "Clean room (nothing inside the original was read)", Deep = "Deep (the original's code and files could be read)". |
| `Environment.clean_room` | bool(증거 필드) | R-14. 선행 스펙의 id 계산에 들어간다. |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 모드 판정 | `Session::clean_room()` = `!deep_for_run.unwrap_or(settings.deep_mode)`. `deep_for_run`이 있으면 설정을 무시한다. `settings.deep_mode`의 기본값은 false이므로 아무것도 안 하면 Clean room이다. `deep_for_run`은 저장되지 않아 설정 파일을 바꾸지 않는다. | 코드 확인 |
| R-02 | `allows(id)` | `TOOLS`에 id가 문자열로 정확히 있을 때만 true. 이름 패턴·접두사·툴셋은 보지 않는다. 목록에 없는 모든 도구(앞으로 추가되는 도구, 플러그인 도구 포함)는 Deep 전용이다(모듈 주석: "a new tool is Deep-only until it's added here"). 허용 목록은 109개이며 그룹은 C-01의 주석을 따른다(세션·증거·unknown·조사 기억·보고서·사람에게 묻기, 생성 에셋과 키, 프로젝트·리빌드, 빌더 자신의 프로젝트, 설정·엔진·플러그인·setup, 웹사이트 방문자 관점, 밖에서 본 프로그램, 휴대전화 화면·앱 목록). | 코드 확인 |
| R-03 | `Engine::call`로 도구 호출 | 순서: (1) id가 레지스트리에 없으면 `invalid`(입력 오류) "No tool named <id>" — 모드를 보기 전이다. (2) 세션 잠금(취소·정체면 `cancelled`·`timed_out`). (3) Clean room이고 `!allows(id)`이면 `refusal(id)`(R-05 형태)를 돌려주고 끝낸다. (4) 사용 가능성 검사(`availability`, 같은 모드 검사가 한 번 더 있고 필요한 엔진·OS·열린 대상을 본다). (5) 동의 검사(`consent_required`). (6) 실행. (3)은 (4)·(5)보다 앞이므로 Clean room 거부는 사용자 동의나 엔진 설치 여부와 무관하게 먼저 나오고, 거부된 도구의 입력 검증(`parse_params`)은 실행되지 않는다. 호출 전체(거부 포함)가 프로젝트가 열려 있으면 저널 `tool_call` 항목 `ok: false, error_code: "feature_missing"`으로 남는다([investigation-memory.md](investigation-memory.md) R-20). | 코드 확인 |
| R-04 | `Engine::availability(spec, session)` | 첫 검사가 `clean_room::availability(spec.id, session.clean_room())`이고 불가이면 즉시 그 결과를 돌려준다(`Availability::no(이유, 해결)`, `details` 없음). UI·CLI의 도구 목록·"쓸 수 있나" 표시가 쓴다. `Requires::Ghidra`인 도구는 Clean room이면 "This needs Deep mode (with Ghidra), and you're in Clean room mode."로 불가이고 Deep이면 사용 가능으로 친다(Ghidra 설치 여부는 보지 않음). | 코드 확인 |
| R-05 | 거부 오류 형태와 클라이언트 반응 | `ToolError { code: feature_missing, message: "This looks inside the original (its code, files or page source), which Clean room never does.", remediation: "Turn on Deep mode: the switch in the title bar or Settings, `settings_set deep_mode true`, or `--deep` on the CLI.", details: {reason: "clean_room", tool: <id>} }`. `is_refusal`은 `details.reason`만 본다. 데스크톱 UI는 도구 호출·화면 채우기 결과가 `is_refusal`이면 Deep 모드 모달을 연다. R-04의 `Availability` 경로에는 `details`가 없어 `is_refusal`이 되지 않는다. | 코드 확인 |
| R-06 | MCP 서버의 목록 | `tools/list`는 도구 집합이 보이고(`--all-tools`이거나 켠 집합) 제한 모드가 아니며, 그리고 Clean room이면 `allows(id)`인 도구만 나열한다. `enable_toolset` 응답의 `visible_tools`는 같은 기준(Clean room이면 허용 도구만)으로 센 수다. 보이지 않는 도구를 호출해도 R-03에서 거부된다(서버가 별도 판정하지 않고 `Engine::call`로 넘김). | 코드 확인 |
| R-07 | 내장 에이전트와 CLI 목록 | 내장 에이전트의 `ToolHost::tools`는 Clean room이면 `allows`가 아닌 도구 정의를 모델에 주지 않는다. CLI `commands`는 Clean room에서 거부될 도구에 "대상 필요" 면제를 주지 않고(도구 이름 옆 `available`을 `Availability` 기준으로 둠) JSON에 `analysis_mode: "clean-room"` 또는 `"deep"`를 적는다. | 코드 확인 |
| R-08 | CLI 플래그 | `--deep`과 `--clean-room`은 전역 플래그이고 clap 수준에서 동시 지정이 막힌다. `deep_for_run()` = 둘 중 하나가 있으면 `Some(deep)`, 아니면 `None`. 도구를 직접 실행하는 서브명령은 도구 이름 뒤에 쓴 `--deep`/`--clean-room`도 받아 합치고, 둘 다 있으면 usage 오류 "--deep and --clean-room can't be used together". `make_engine`이 `Session::deep_for_run`에 이 값을 넣고, `mcp` 서브명령도 같은 `make_engine(cli.deep_for_run())`을 쓴다. | 코드 확인 |
| R-09 | 에이전트가 모드를 바꿀 수 있나 | `settings_set`은 허용 목록에 있고 동의가 필요 없는 효과(파일 쓰기+세션 변경)다. `deep_mode` 키에 true를 주면 설정 전체를 새로 만들어 `config.toml`에 저장하고 세션 설정을 교체한다. 그 세션에 `deep_for_run`이 없으면 다음 호출부터 `clean_room()`이 false가 되어 R-03의 거부가 풀린다. `deep_for_run`이 있으면(CLI 플래그, 에이전트 CLI가 띄우는 MCP 서버가 붙이는 `--deep`/`--clean-room`) 저장된 설정만 바뀌고 이 프로세스의 모드는 그대로다. MCP 제한 모드(`--restricted`)도 이 도구를 막지 않는다(동의가 필요한 효과·네트워크·`adb_`·`ACTS_ON_MACHINE` 3개 중 어디에도 해당하지 않음). | 코드 확인 |
| R-10 | 공유 대상 열기 | 에이전트 CLI가 띄우는 자식 MCP 프로세스는 `--target`으로 대상 메타(`path`, `sha256`, `kind`, `raw`)를 받는다. Clean room이면 `TargetContext::open`은 파일을 읽지 않고 id `t_<sha256 앞 12자>`, 경로·이름·sha256·종류·raw만 채우고 `bytes`는 빈 배열인 `Target`을 만든다. Deep이면 파일을 읽고 해시가 다르면 `invalid` "The shared target changed after it was opened." 세션 복원 때 모드 값은 `clean_room()`에서 가져온다. 형식이 틀린 메타(상대 경로, 64자 16진 아님)는 두 모드 모두 `invalid`. | 코드 확인 |
| R-11 | Ghidra 공급자 | `provider_for_active`는 Clean room이면 Ghidra를 띄우지 않고 `Err(None)`을 돌려 호출자가 내장 엔진을 쓰게 한다. Deep이어도 Ghidra가 없으면 `Err(Some(이유))`로 내장 엔진 폴백이다. | 코드 확인 |
| R-12 | `web_site_capture`가 Clean room에서 남기는 것 | (a) 인자 `include_html`은 `false`로 강제되어 `page.html`을 쓰지 않는다(증거 `params.include_html`은 강제된 값). (b) `blueprint`에서 `meta`·`breakpoints`·`unreadable_stylesheets`·`health`를 지우고, `outline` 항목의 `class`를 지우고 `src`·`href`와 `links[].href`의 `?`·`#` 뒤를 자르고, `a11y.unnamed_examples`의 `.클래스` 부분을 자르고, `design`의 `css_variables`·`font_faces`를 지우고, `assets`는 이미지 크기 `{w, h}` 목록만 남긴다. (c) 스크린샷·보이는 글·측정된 레이아웃과 스타일·링크·폼(값 아님)은 남는다. (d) README는 방문자 시점 문구, 증거 `params.visitor_view: true`, `Limitation` 코드 `visitor_view`("Clean room: only what a visitor sees was kept …"), Deep은 `cross_origin_css`. (e) 페이지를 열 때(`web_site_open`)와 캡처 동안 브라우저는 사이트 스크립트를 실행하고 DOM·레이아웃 측정 스크립트가 페이지 안에서 돈다. 걸러내기는 측정 뒤에 적용된다. | 코드 확인 |
| R-13 | 빌더용 도구의 원본 접근 거부(`off_limits`) | `core_action_approve`(MCP를 통해 에이전트 CLI의 권한 요청을 판정)와 `build_command_run` 등 `approve`를 거치는 빌더 도구는 Clean room일 때 승인 정책·Auto 모드보다 먼저 `off_limits`로 검사한다. 로컬 대상(`TargetRef::Local`): 원본 폴더(대상이 파일이면 그 파일이 든 폴더, 프로젝트 자신의 폴더는 제외, 링크는 따라간 실제 위치)에 닿는 `Read`/`Write`/`Edit`/`MultiEdit`의 `file_path`, `NotebookRead`/`NotebookEdit`의 `notebook_path`, `Glob`/`Grep`/`LS`의 `path`(그리고 `pattern`·`glob`이 폴더 경로를 언급), `Bash`/`PowerShell`의 `command`에 폴더 경로가 문자열로 들어 있음(대소문자 무시, 슬래시 방향 무시, Git Bash `/c/…` 형식 포함)이면 거부한다. 웹사이트 대상: 같은 사이트(호스트가 같거나 한쪽이 다른 쪽의 하위 도메인)의 `WebFetch`, 명령에 호스트 문자열이 있는 `Bash`/`PowerShell`. 거부는 "Clean room: the original (its files, its folder, its pages and its code) is off limits. …" 메시지의 `deny`이고 `core_action_approve`의 결과 `behavior: "deny"`. 이 검사는 작업 폴더(워크스페이스) 안에서 일하는 빌더에만 적용되고(워크스페이스가 없으면 검사 없음) 워크스페이스 매니페스트의 대상을 기준으로 한다. | 코드 확인 |
| R-14 | 증거의 `environment.clean_room` | 각 도구가 증거를 만들 때 직접 채운다(`Engine::call`이 일괄로 덮어쓰지 않는다). 내장 엔진·CDP·플러그인·adb 등은 `Environment::builtin(session.clean_room())` 또는 같은 값을 넣은 `Environment { clean_room: session.clean_room(), … }`/`cdp_env(session.clean_room(), …)`다. 제3자 디컴파일러 결과(Ghidra, JADX를 함께 쓴 안드로이드 클래스, JEB)는 `clean_room: false`를 고정한다. 따라서 값 의미는 "기록한 세션이 Clean room이었다"이고, `evidence/src/lib.rs`의 필드 주석 "True when only Craft Anything's own engines ran (no Ghidra or other third-party decompiler)"과 다르다: Deep에서 내장 엔진만 돌아도 false다. 값은 선행 스펙 R-03대로 증거 id에 들어가므로 모드가 다르면 같은 관찰도 id가 다르다. | 코드 확인 |
| R-15 | 보고서의 모드 표기 | 보고서(`core_report_write`·`core_report_save`)는 보고서를 만드는 시점의 `session.clean_room()` 한 값으로 `mode_words`를 "Mode" 줄에 적는다(Markdown·HTML 동일). 각 증거의 `environment.clean_room`은 이 줄에 쓰이지 않는다. 데스크톱 UI의 증거 보기는 증거별 `environment.clean_room`을 "(clean room)" 표시로 쓴다. | 코드 확인 |
| R-16 | 플러그인 도구 | MCP 플러그인(`[[plugins.mcp]]`)과 WASM 플러그인의 도구는 실행 시점에 `<플러그인 id>_<도구 이름>`(소문자·숫자·`_`, 64자 이하) id로 레지스트리에 들어간다. 이미 등록된 id와 같거나 유효하지 않으면 건너뛴다(로그). `TOOLS`에 있는 어떤 id도 아니므로 Clean room에서는 R-03으로 거부되고 R-06·R-07로 목록에서도 빠진다. 플러그인 서버는 그 호출 전에는 시작되지 않는다. Deep에서 실행되면 증거 `environment`는 `{clean_room: <세션 모드>, engine: "plugin:<id>"}`, 권위는 "외부 서비스"다. 플러그인을 관리하는 도구(`plugins_list`·`plugins_refresh`·`plugins_add`·`plugins_remove`)는 허용 목록에 있다. | 코드 확인(MCP 플러그인) · 추론(WASM 플러그인은 같은 `RuntimeTool` 목록에 들어간다는 시그니처로 판단) |
| R-17 | 이 스펙 밖에서 같은 모드를 강제하는 곳(경계) | 에이전트 CLI를 띄울 때 자식 MCP 서버에 `--deep` 또는 `--clean-room`을 붙여 설정과 무관하게 실행 모드를 고정한다(빌더의 Deep는 `--all-tools`도 붙임). Clean room 채팅(프로젝트 없음)의 ACP 승인자는 에이전트 자신의 `Read`·`Write`·`Bash`·`WebFetch`를 모두 거부한다. 리빌드 실행의 모드는 세션의 모드(없으면 옵션, 그것도 없으면 저장 설정)를 따른다. 상세는 행 7·13. | 코드 확인(위치만) |

- 불변식: Clean room(`session.clean_room()`)에서는 `Engine::call`이 `allows(id)`가 아닌 도구를 실행하지 않는다. 예외 경로는 이 스펙이 읽은 범위에서 없었다(`call_inner`가 모든 호출의 공통 경로). 단, 허용된 도구가 대상 안쪽 정보를 되돌려주지 않는다는 보장은 허용 목록이 아니라 도구별 구현에 달려 있다(R-12, R-13, 2.1의 어긋남 표).
- 미결정: 없음.
- 확인 한계: 정적 읽기만 했고 도구를 실행하지 않았다. 허용 목록 109개 중 `runtime_ui_read`·`native_window_capture`·`runtime_walkthrough_record`·`web_page_states_capture`·`rebuild_*`·`project_play` 등 "밖에서 본다"고 분류된 도구의 반환 필드는 하나하나 읽지 않아, 그 도구들이 대상 내부 정보를 되돌려주는지는 `미확인`이다. 플러그인 id가 상위 계층 도구 id(`ai_*`·`setup_*` 등 레지스트리가 아닌 곳에서 등록되는 id)와 겹칠 때의 등록 순서는 확인하지 못했다(`registry.rs:89-95`는 이미 등록된 id만 막는다). 에이전트 CLI·UI 쪽의 강제는 행 13·18이다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/engine/src/clean_room.rs:13-161` `TOOLS`·`allows`·`REASON`·`REMEDIATION`·`availability`·`refusal`·`mode_words`·`is_refusal` | 허용 목록 109개 전체와 그룹 주석, 거부 문구·오류 형태, 모드 문구 | R-02 ~ R-05, R-15 |
| C-02 | `crates/engine/src/lib.rs:166-186`, `:213-229`, `:240-283` `Engine::availability`·`Engine::call`·`call_inner` | 검사 순서(도구 조회 → 세션 잠금 → Clean room 거부 → 사용 가능성 → 동의 → 실행)와 저널 기록 | R-03, R-04 |
| C-03 | `crates/engine/src/session.rs:86-90`, `:124-127`, `:143-147` `deep_for_run`·`clean_room()`·공유 대상 복원 | 모드 판정식 | R-01, R-10 |
| C-04 | `crates/engine/src/target.rs:29-60` `TargetContext::open` | Clean room의 빈 `bytes` 대상, Deep의 해시 검사 | R-10 |
| C-05 | `apps/craft-anything-cli/src/main.rs:44-48`, `:128-131`, `:208-212`, `:365-368`, `:386`, `:489-510` `Cli`·`deep_for_run`·`make_engine`·`tool` | 플래그 정의·합치기·usage 오류, `commands` 출력 | R-07, R-08 |
| C-06 | `crates/engine/src/tools/website_tools.rs:787-870` `web_site_capture`, `:976-1016` `visitor_view` | Clean room 축소(강제 `include_html=false`, 지우는 키 목록, 한계 문구) | R-12 |
| C-07 | `crates/engine/src/tools/interaction_tools.rs:409-452` `approve`·`approve_with`, `:500-548` `off_limits`·`mentions` | 원본 접근 거부 판정, 거부 전 순서 | R-13 |
| C-08 | `crates/engine/src/tools/setup_tools.rs:484-521` `with_setting`·`settings_set` | `deep_mode` 변경의 저장·세션 교체 | R-09 |
| C-09 | `crates/engine/src/plugins.rs:188-227`, `crates/engine/src/registry.rs:89-95` `install`·`with_runtime` | 플러그인 도구 id 구성과 중복 건너뛰기 | R-16 |
| C-10 | `crates/evidence/src/lib.rs:76-98` `Environment`·`builtin`, `crates/engine/src/tools/deep.rs:361-363`, `android_tools.rs:997-1004`, `android_tools/jeb.rs:507` | 필드 정의와 `clean_room: false` 고정 위치 | R-14 |

### 1.6 수락 사례
출처: 사례별 표기

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `deep_mode` false, `deep_for_run` 없음 / 이어서 `deep_for_run = Some(true)` / `deep_mode` true로 두고 `deep_for_run = Some(false)` (원본 테스트 `a_run_picks_its_mode_without_changing_the_settings`) | 첫 경우 `clean_room()` true, 둘째 false이고 저장된 설정은 그대로, 셋째 true |
| T-02 | R-02 ~ R-05 | Clean room에서 `core_target_open`, `core_target_triage`, `native_function_pseudocode`, `native_strings_browse`, `js_app_map`, `web_page_show`, `game_archives_list`의 `allows`와 `availability`, Deep에서의 `availability`, `web_site_capture`의 Clean room `availability`, `refusal("native_functions_list")`의 `is_refusal` (원본 테스트 `looking_inside_needs_deep_mode`) | 일곱 도구 모두 불허·불가(Deep에서는 막지 않음), `web_site_capture`는 막지 않음, `is_refusal` true |
| T-03 | R-03 | Clean room 세션에서 `core_text_read`(허용 목록에 없음)를 `Engine::call`로 호출 (원본 테스트 `text_tools.rs`의 `clean_room_refuses_it`) | `details.reason == "clean_room"`, `TOOLS`에 `core_text_read` 없음 |
| T-04 | R-03 | Clean room에서 `settings_set`(허용), `native_functions_list`(비허용)를 차례로 호출하고 도구 id `no_such_tool` 호출 (구현에서 도출) | 둘째는 `feature_missing`+`details.reason: "clean_room"`, 셋째는 `invalid` "No tool named no_such_tool", 각각 저널에 `ok: false`로 남음(프로젝트가 열려 있을 때) |
| T-05 | R-06 | Clean room MCP 세션에서 `enable_toolset {toolset: "all"}` (원본 테스트 `enabling_a_toolset_counts_the_tools_listed`) | `visible_tools` = 레지스트리 도구 중 `allows`인 수 |
| T-06 | R-09 | `deep_for_run` 없음, `deep_mode` false인 세션(MCP 일반 등록)에서 `settings_set {key: "deep_mode", value: true}` 뒤 `native_functions_list` 호출 / 같은 순서를 `--clean-room`으로 시작한 세션에서 (구현에서 도출) | 앞 세션은 `settings_set`이 성공하고 다음 호출이 Clean room 거부 없이 진행(대상이 열려 있지 않으면 `not_found`), 뒤 세션은 `config.toml`만 바뀌고 다음 호출이 여전히 `clean_room` 거부 |
| T-07 | R-12 | `web_site_capture`를 Clean room에서 실행 (원본 테스트 `a_visitors_view_keeps_what_shows_and_drops_the_pages_code`, 열람은 `visitor_view`에 한정) | `page.html` 없음, `capture.json`에 `meta`·`breakpoints`·`design.css_variables`·`design.font_faces` 없음, `outline[].class` 없음, 주소에서 쿼리 문자열 제거, 증거 `limitations`에 코드 `visitor_view` |
| T-08 | R-13 | Clean room(Auto 모드 켜짐), 로컬 대상 폴더가 `<G>`인 워크스페이스에서 `Read {file_path: "<G>/data.ini"}`, `Glob {path: <G>}`, `Grep {path: <G>}`, `Bash {command: "strings \"<G>/Game.exe\" | head"}`, `Bash`에 `<G>`를 대문자·슬래시로 바꿔 쓴 `cat`, 프로젝트의 `app/` 폴더 안 `Read` 승인 요청 (원본 테스트 `clean_room_keeps_the_builder_away_from_the_original`) | 앞 다섯은 `Err(OFF_LIMITS 메시지)`(Auto 모드여도), `app/` 안 읽기는 거부되지 않는다. 같은 `Read`를 Deep(`clean_room=false`)으로 하면 허용 |
| T-09 | R-14 | Deep 세션에서 내장 엔진 도구 한 번, Clean room에서 같은 도구(허용 목록 안의 것) 한 번 (구현에서 도출) | 증거 `environment.clean_room`이 각각 false·true, 증거 id가 서로 다름 |
| T-10 | R-16 | 플러그인 id `docs`의 도구 `search`가 등록된 세션을 Clean room에서 `docs_search` 호출 (구현에서 도출) | `feature_missing`+`details.reason: "clean_room"`, 플러그인 서버는 시작되지 않음(호출 전에 거부), `tools/list`에도 없음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad71 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-03(`session.rs:86-90`, `:124-127`), `settings.rs:93-96`, `:207` | 전문 읽음 |
| R-02 | C-01 | 목록 109개는 `awk '/pub const TOOLS/,/^];/' crates/engine/src/clean_room.rs \| grep -c '^    "'`로 센 값. 그룹 이름은 목록 주석. 허용 기준 어긋남은 아래 표 |
| R-03 | C-02(`lib.rs:240-262`, `:276-283`, `:213-229`) | `grep -n 'clean_room' crates/engine/src/lib.rs`로 `Engine::call` 경로의 모드 검사가 `:167`·`:180`·`:257`뿐임을 확인. 거부된 호출이 저널에 남는 것은 `call`이 `call_inner` 결과를 항상 저널에 쓰는 구조(`:213-229`) |
| R-04 | `lib.rs:166-186` | 전문 읽음 |
| R-05 | C-01(`clean_room.rs:140-161`), `ui-egui/src/lib.rs:1099`, `:1596`, `:1807`, `:1844` | UI 쪽은 호출 위치와 분기만 읽음(동작 실행 안 함) |
| R-06 | `mcp/src/lib.rs:379-391` `visible`·`listed`, `:393-400` `tools_list`, `:508-513` `enable_toolset` 응답, `:355-377` `restricted_refusal` | 전문 읽음. 테스트 `mcp/src/tests.rs:80-95`(T-05)는 기대값 확인만 |
| R-07 | `ai/src/agent.rs:110-114`, C-05(`main.rs:365-368`, `:386`) | 전문 읽음 |
| R-08 | C-05 | 전문 읽음. `main.rs:44-48`의 `conflicts_with`는 전역 플래그 정의 |
| R-09 | C-08, `session.rs:124-127`, `tool.rs:56-58` `Effects::needs_consent`, `mcp/src/lib.rs:75`, `:355-377` | 문서와 구현의 어긋남 1: 모듈 주석은 허용 기준이 "대상을 건드리지 않거나 밖에서 보는 것"인데 `settings_set`은 대상을 건드리지 않지만 모드 경계 자체를 바꾼다. `clean_room.rs:140-141`의 거부 문구와 스킬이 `settings_set deep_mode true`를 사용자에게 안내하라고 하지만, 코드에는 그 호출자가 사용자인지 에이전트인지 구분하는 곳이 없다(`call_inner`는 호출자를 `Caller`로 받지만 모드·허용 목록에 쓰지 않는다). `--clean-room`을 붙이면 막히는 것은 `session.rs:126`의 우선순위에서 도출. T-06은 실행하지 않았다 |
| R-10 | C-04, `session.rs:143-147` | 전문 읽음 |
| R-11 | `tools/deep.rs:46-52`, `lib.rs:176-186` | 전문 읽음. Deep에서 Ghidra 없음 처리는 `deep.rs:40-45` 주석과 반환 형태만 읽음 |
| R-12 | C-06 | 전문 읽음. 걸러내기 순서는 `capture_into`(`website_tools.rs:892-960`)가 측정을 모두 마친 뒤 `visitor_view`가 적용되는 호출 순서(`:825-826`)에서 도출. 문서와 구현의 어긋남 2: `clean_room.rs:107`의 "web_site_capture keeps only that" 주석 외에 `web_page_states_capture`(허용 목록에 있음)는 같은 걸러내기가 없고, 사이트 코드가 클릭으로 실행되며(`website_tools.rs:52`의 도구 설명) 결과 필드가 방문자에게 보이는 것만인지는 읽지 않았다(`미확인`) |
| R-13 | C-07, 테스트 `interaction_tools.rs:936-956`(T-08) | 전문 읽음. `mentions`는 문자열 포함 검사라 경로를 쪼개거나 변수로 조립한 명령은 걸리지 않는다(추론: 코드가 문자열 검사만 한다). 파일 도구는 `resolve_as_opened`로 해석한 실제 경로를 비교하므로 링크를 따라간다 |
| R-14 | C-10, `grep -rnE 'Environment::builtin\\((true\|false)\\)\|clean_room: (true\|false)' crates --include='*.rs'`에서 테스트·데모를 뺀 결과 | 프로덕션 코드에서 리터럴 값은 `deep.rs:362`, `android_tools.rs:1002`, `jeb.rs:507`(모두 false). 나머지는 `ctx.session.clean_room()`. `Engine::call`·`Session::record`가 `environment`를 바꾸는 코드는 `grep -n clean_room crates/engine/src/session.rs`로 찾지 못했다. 문서와 구현의 어긋남 3: 필드 주석 vs 실제(위 R-14) |
| R-15 | `tools/report_tools.rs:123-125`, `:316`, `:468`, `ui-egui/src/evidence_ui.rs:28`, `ui-egui/src/report.rs:20`, `:34` | 전문 읽음. 한 보고서에 Deep·Clean room 증거가 섞이면 "Mode" 줄은 보고서 작성 시점의 모드 하나뿐이다(코드로 확인, 섞였을 때를 감지하는 코드는 찾지 못함) |
| R-16 | C-09, `plugins.rs:246-286` `call_plugin`, `wasm_plugins.rs:101-113` | `call_plugin`은 모드를 보지 않고(모드 검사가 `Engine::call`에 한 곳) 거부는 그 이전에 일어난다. WASM 부분은 시그니처(`install(session, &mut Vec<RuntimeTool>)`)로만 확인 |
| R-17 | `cli_agents/mod.rs:636-646`, `acp.rs:98-104`, `rebuild/mod.rs:233-239`, `:604` | 위치만 읽음. 상세는 행 7·13 |
| T-01 ~ T-03, T-05, T-07, T-08 | `clean_room.rs:163-207`, `text_tools.rs:372-381`, `mcp/src/tests.rs:80-95`, `website_tools.rs:1312-1330`, `interaction_tools.rs:936-956` | 원본 테스트 열람은 해당 사례의 기대값 확인에 한정, 실행하지 않았다 |
| T-04, T-06, T-09, T-10 | R-03, R-09, R-14, R-16 | 구현에서 도출, 실행하지 않았다 |

**허용 기준(모듈 주석)과 실제 목록이 어긋난 항목.** 모듈 주석(`clean_room.rs:3-8`)은 허용 기준을 "대상을 건드리지 않는 것(세션, 증거, unknown, 프로젝트, 설정, 엔진, 빌더 자신의 프로젝트, 생성 에셋)" 또는 "밖에서 보는 것(웹사이트 스크린샷·보이는 레이아웃, 창 사진, 화면의 컨트롤, 기록된 실행, 휴대전화 화면)"이라고 쓴다. 아래는 이 기준에서 어긋나거나 기준만으로 안쪽 접근이 막히는지 판단하기 어려운 도구다. 모두 코드 확인으로 목록 포함 여부를 확인했고, 효과는 읽은 범위의 추론이다.

| 도구 | 어긋남 | 근거 |
|---|---|---|
| `settings_set` | 대상은 건드리지 않지만 모드 경계 자체를 풀 수 있다(R-09). 실행 모드가 `--clean-room`으로 고정된 프로세스에서만 막힌다 | `clean_room.rs:89`, `setup_tools.rs:514-521`, `session.rs:126` |
| `core_evidence_show`·`core_evidence_browse`·`core_evidence_export`·`core_evidence_import` | 대상은 건드리지 않지만 Deep에서 기록한 증거와 그 `result`(대상 안쪽 정보)를 Clean room에서도 열람·내보내기·가져오기 한다. 증거 저장소가 모드로 걸러지는 코드를 찾지 못했다 | `clean_room.rs:20-23`, `session_tools.rs`의 이 도구들에 `clean_room` 참조 없음(`grep -n clean session_tools.rs`는 `:269-270` `core_session_show`의 표시뿐) |
| `build_command_run` | 허용 이유는 "빌더 자신의 프로젝트"이지만 임의 셸 명령을 실행한다. 원본 접근 차단은 목록이 아니라 `approve` → `off_limits`의 문자열 검사에 의존한다(R-13) | `clean_room.rs:86`, `build_tools.rs:366-385`, `interaction_tools.rs:506-548` |
| `adb_app_install`·`adb_app_remove`·`adb_app_force_stop`·`adb_app_launch` | 주석은 "휴대전화의 화면과 앱 목록을 안쪽을 읽지 않고"라고 하지만 이 넷은 기기를 바꾸거나 앱을 실행하는 동작이다(동의 필요 효과를 가진 도구들, 호출은 `consent_required`로 따로 막힘) | `clean_room.rs:129-132`, `adb_tools.rs:1140`, `:1161`, `:1183`, `:1280` |
| `runtime_walkthrough_record`·`runtime_ui_walkthrough_record` | 주석의 "기록된 실행"에 해당하나 효과가 `EXECUTES_FOREIGN_CODE`(대상 프로그램 실행)라 "안쪽을 읽지 않는다"는 모드 정의(`mode_words`)와 거리가 있다. 결과 필드가 화면·출력 밖의 정보를 담는지는 읽지 않았다 | `clean_room.rs:119-120`, `process_tools.rs:19-25` |
| `web_page_states_capture` | R-12 참고: 허용되지만 `web_site_capture`와 같은 걸러내기가 있는지 확인하지 못했다 | `clean_room.rs:110`, `website_tools.rs:50-58` |

### 2.2 코드 읽는 순서
`clean_room.rs`(목록과 거부 형태) → `session.rs` `clean_room()` → `lib.rs` `Engine::call`·`call_inner` → `mcp/src/lib.rs` `listed` → CLI `main.rs`의 플래그 → `website_tools.rs` `web_site_capture`·`visitor_view` → `interaction_tools.rs` `off_limits`. 원본의 전략은 두 층이다: 도구 id 단위의 정적 허용 목록(`TOOLS`)을 호출 경로의 한 곳(`call_inner`)에서 강제하고, 그 안에서 허용된 도구가 스스로 결과를 줄이거나(R-12) 원본 폴더를 가리키는 동작을 개별 판정(R-13)한다.

## 적용 메모

원본의 미결정을 여기서 해소한 것은 없다. 우리 절차와 맞대어 본 보완 후보다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-02, R-03 | **수정(overview 후보 표 10행).** "코드 없이 외부 관찰만으로 쓴 스펙과 비교"를 곧바로 도입하기보다, 먼저 스펙 작성자/구현자 분리의 현재 구멍을 표로 적는다: 구현자는 "1부·선행 스펙·C-ID만 읽는다"(4장 4번)고 가정하지만 그 가정을 어기는 것(레포 코드를 읽는 것)을 막는 장치가 없고, 4장 4번의 "구현자 입장에서 막힐 질문"은 작성자가 구현자 역할을 흉내 내는 한 사람 작업이다 | 원본은 분리를 규칙 문구가 아니라 도구 허용 목록으로 강제한다(R-02, R-03). 우리 쪽에서 같은 강제가 되려면 구현 검증을 별도 세션에서 "레포 접근 도구가 없는 에이전트"로 돌려야 한다(추론). 이것은 4장 6번의 사용자 요청형 재구현 검증과 연결된다 | 4장 6번 "재구현 검증"에 "레포를 읽을 수 없는 별도 세션에서 스펙만 입력한다"를 조건으로 적는다. 사례: 구현 세션의 도구 목록에 `repos/`·`artifacts/` 읽기가 없음 |
| R-02(목록이 정적, 기본 거부) | **확정.** "새 도구는 허용 목록에 넣기 전까지 막힌다"는 기본 거부 방식은 우리 구현 검증 세션에 그대로 적용할 수 있다 | 원본 모듈 주석이 이 방침을 명시하고(`clean_room.rs:7-8`) 플러그인 도구도 같은 규칙으로 막힌다(R-16). 우리 쪽은 "읽기 허용 경로 목록(스펙, 템플릿)만 두고 나머지는 거부"로 같은 구조를 가진다 | 구현 검증 세션 지시문에 허용 경로 목록 |
| R-09, R-13 | **보완 후보(반면교사).** 모드를 경계로 삼는 자리에서 그 경계를 푸는 동작은 허용 목록에서 빼거나 사람 승인으로만 둔다. 원본에서는 `settings_set`이 허용되고 문자열 포함 검사(R-13)에 의존하는 부분이 있다 | 우리 구현 검증 세션에서 "스펙만 읽는다"는 경계를 에이전트가 스스로 풀 수 있으면(예: 레포 경로를 읽는 명령 허용) 분리가 지침에 그친다. 원본이 같은 위험을 두 곳(R-09, R-13)에 남겼다 | 구현 검증 지시문에 "읽기 범위를 바꾸는 요청은 사용자에게만"을 명시 |
| R-14, R-15 | **후보.** 우리 reports에서 각 주장의 검증 수준과 별개로 "어떤 방식으로 읽었나"(코드를 읽음 / 도구로 계산 / 외부 자료)를 구분하는 칸을 둘지 검토한다. 단 원본의 `environment.clean_room`은 필드 주석과 실제 의미가 달라(R-14) 값이 오해를 부르므로, 우리 쪽은 값의 정의를 먼저 한 줄로 고정해야 한다 | overview 후보 표 1행("직접 읽은 것인지 도구로 계산한 것인지")과 연결. 원본 사례는 필드 의미를 정의 없이 쓰면 읽는 사람이 다른 뜻으로 읽는다는 것을 보여 준다. 또 보고서 한 줄이 쓰는 시점의 모드 하나만 적어(R-15) 증거가 섞였는지를 숨긴다 | `SCHEMA.md` 또는 7장에 칸 이름·정의 한 줄. 사례: 한 문서에 `코드 확인`과 `추론`이 섞여도 R-ID별로 표기 |
| R-12 | 확인만 함(분석 대상의 "방문자 관점" 축소는 우리 대상 아님) | 원본은 허용 도구가 결과를 걸러 안쪽 정보를 빼는 방식을 쓴다. 우리 절차는 레포 코드를 읽는 것이 목적이라 대응 개념이 없다 | 없음 |
