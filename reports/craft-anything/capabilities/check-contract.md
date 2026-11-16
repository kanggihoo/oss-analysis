---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/ai/src/rebuild/kinds/mod.rs
  - crates/ai/src/rebuild/check.rs
  - crates/ai/src/rebuild/kinds/website.rs
  - crates/ai/src/rebuild/kinds/game.rs
  - crates/ai/src/rebuild/kinds/app.rs
  - crates/ai/src/rebuild/kinds/own.rs
  - crates/ai/src/rebuild/kinds/screenshot.rs
  - crates/ai/src/rebuild/kinds/self_test.rs
  - crates/ai/src/rebuild/kinds/mechanics.rs
  - crates/ai/src/rebuild/kinds/runs.rs
  - crates/ai/src/rebuild/kinds/plugin_check.rs
  - crates/engine/src/workspace.rs
  - crates/engine/src/outputs.rs
  - crates/platform/src/cancel.rs
  - crates/ai/src/rebuild/mod.rs
  - crates/ai/src/rebuild/self_check.rs
  - crates/ai/src/rebuild/kept_check.rs
  - crates/ai/src/rebuild/tests.rs
  - docs/extending.md
depends: []
status: ready
---

# 대상 종류·검사·재시도 계약

> 요청문·대상·스택을 받아 만들 것의 종류(`TargetKind`)와 스택을 고르고, 한 라운드의 빌드를 종류별 검사(`Check`) 목록으로 차례로 판정해 `CheckResult` 목록을 돌려주며, 각 결과가 "작동함(`passed`)", "충분히 같음(`good`)", "빌더가 한 턴 더 하면 고칠 수 있음(`can_refine`)" 중 어디에 해당하는지를 리빌드 루프에 약속하는 계약.

<!-- 용어
- 라운드(round): 검사를 한 번 도는 단위. 실제 라운드는 1부터, 빌더가 작업 중에 `rebuild_check`로 스스로 요청한 검사는 0번 라운드(`SELF_CHECK_ROUND`)로 돈다.
- 빌더(builder): `app/`에 코드를 쓰는 코딩 에이전트(Claude Code 등) 또는 내장 API 루프.
- 오라클(oracle): 검사가 "원본과 같은지"를 판정하는 데 쓰는 기준 자료. `Check::can_refine` 주석의 용어를 그대로 쓴다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 새 프로젝트를 만들 때 `KindRegistry::choose(request, target, deep)`가 등록된 종류마다 점수를 매겨 가장 높은 종류를 고르고, 스택을 "종류가 아는 이름 → 스택 표의 `asked_by` 문구 → 종류의 기본 스택" 순으로 정한다(R-02, R-03).
2. 루프가 라운드 번호를 정해 `Worker::run_checks`(실제 라운드, 시간 제한 없음) 또는 `run_checks_within`(0번 라운드, 30분 제한)을 부른다(R-11).
3. 검사 목록을 만든다: 사람의 기존 프로젝트면 `own::checks()`, 아니면 `kind.checks(ws)`. 그 뒤에 이 종류에 해당하는 WASM 플러그인 검사를 붙이고, `applies`가 거짓인 검사는 뺀다(R-06).
4. 검사를 순서대로 돌린다. 각 검사 직전에 일시정지·시간 제한을 보고, 검사마다 진행 이벤트를 하나 낸다. `passed=false`인 결과가 나오면 거기서 멈추고 뒤 검사는 결과를 남기지 않는다(R-09, R-10).
5. 결과 목록을 루프에 돌려준다. 루프는 `CheckResult::good(bar)`와 `kinds::can_refine`으로 "고칠 대상"을 고르고, 고칠 수 있는 대상이 없으면 미검증 항목을 남긴 채 끝낸다(R-14~R-16). 그 대상의 재다듬기 문구는 `TargetKind::refine`이 만든다(R-17).

### 1.2 범위·통합 지점

- 제공: `TargetKind`·`Check` 트레이트와 그 기본 동작, 종류 등록·판별·스택 선택, 한 라운드의 검사 목록 구성과 순차 실행 규칙, 일시정지·시간 제한(`CheckStop`), `CheckResult`의 판정 의미(`passed`/`good`/`can_refine`), 내장 검사 9종의 id·적용 조건·`can_refine`·통과 조건, 기본 재다듬기 문구.
- 제외:
  - 라운드를 몇 번 돌지, 정체 감지, `not_working_checks` 상한(10), 검사 오류 시 한 번 재시도, 결과 저장·이벤트 전달: 리빌드 루프(feature map 7행). 이 스펙은 루프가 결과를 어떻게 읽는지만 경계로 적는다(R-15).
  - 바뀐 것이 없으면 직전 라운드 결과를 재사용하는 `checks_unless_unchanged`(`kept_check.rs`): 루프 소유. 결과가 모두 `passed`일 때만 재사용 대상이 된다는 점만 이 계약과 닿는다.
  - 브리프에 들어가는 종류별 절(`brief_sections`, `follow_up_sections`)의 내용: [빌더 브리프](./builder-brief.md). 이 스펙은 메서드의 존재와 호출 시점만 정의한다.
  - 각 검사의 내부 측정 알고리즘(그림 유사도, 페이지 구조·텍스트·디자인 비교, 콘솔 출력 비교, UI 트리 비교, 시험 보고서 파싱 세부): 이 스펙은 판정 기준과 결과 필드만 정하고 계산은 C-ID로 넘긴다.
  - 종류 판별의 언어별 단어 목록(에스토니아어 격 어미 등): C-ID로만 준다.
- 외부 의존·선행 계약(경계만 정의):
  - 엔진 도구 호출 `Worker::call(tool, params)`: 이 스펙이 쓰는 도구는 `web_site_open`, `web_site_capture`(웹사이트 검사), `native_window_capture`(스크린샷 검사의 실행 화면), `runtime_walkthrough_record`(콘솔 실행 검사). 정상이면 `ToolOutput`, 실패면 `ToolError`.
  - 프로세스 실행 `craft_anything_platform::Process`: `timeout`, `idle_timeout`, `stdout_cap`, `cancel_when`을 받고 성공 여부·표준 출력·표준 오류를 돌려준다. 시작 실패·시간 초과는 오류 메시지 문자열이 된다.
  - 엔진 헬퍼: `outputs::launch(app, godot)`(실행할 프로그램과 인자, 없으면 None), `outputs::site_dir(app)`(정적 사이트 폴더), `toolchains::found_in(app)`(사람의 프로젝트의 빌드·테스트 명령 표), `Workspace::references()`(`reference/`의 사람 그림), `wasm_plugins::checks(session)`(플러그인 검사 목록).
  - 취소 토큰 `CancelToken::check()`: 취소됐으면 `ToolError::cancelled()`(코드 `Cancelled`).
- 소유 상태·부작용: 검사는 프로젝트의 `checks/round-N/` 아래에 스크린샷·실행 기록·시험 보고서를 쓴다. 웹사이트 검사는 시작 시 `checks/round-N/`을 지우고 다시 만들며, 빌드 폴더를 loopback으로 서빙하고 실행의 미리보기 서버를 교체한다. 빌드 검사는 `app/`에서 빌드 명령을 실행한다(빌드 산출물이 생긴다). `CheckResult` 자체는 저장하지 않는다(루프가 `craft.json`에 덧붙인다).

### 1.3 인터페이스와 데이터 의미

**`TargetKind` (만들 것의 종류)**

| 메서드 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `id()` | → string | 프로젝트에 저장되는 고정 id. 내장: `"website"`, `"game"`, `"app"` |
| `words()` | → `KindWords{button, icon, ready, change_hint}` | UI 문구. 판정에는 쓰지 않는다 |
| `detect(cx)` | `DetectCx` → optional int | 이 종류라고 말하는 정도. 높을수록 이김. None이면 이 종류가 아님 (R-02, R-04) |
| `default_stack(cx)` | `DetectCx` → string | 요청이 스택을 말하지 않을 때의 스택 이름(스택 표의 `name`) (R-05) |
| `named_stack(cx)` | `DetectCx` → optional string | 이 종류만 아는 스택 이름 요청("in Godot"). 기본 None |
| `studies_folder()` | → bool | 폴더 대상일 때 프로그램 주변 폴더도 조사할지. 기본 false, game만 true |
| `goal()` | → string | 브리프의 "What to build" 문장 |
| `brief_sections(cx)` / `follow_up_sections(cx)` | `BriefCx` → list<string> | 브리프·후속 메시지에 붙일 절. 기본 빈 목록 |
| `self_screenshots()` | → bool | 결과를 밖에서 찍을 수 없어 빌더가 스스로 찍는지. 기본 true, website만 false |
| `rebuild_words()` | → string | 후속 메시지의 "다시 빌드" 문구. 기본 `"build it again"`(내장 종류는 모두 기본값) |
| `checks(ws)` | `Workspace` → list<`Check`> | 이 프로젝트의 빌드를 판정할 검사, 실행 순서대로 (R-07) |
| `refine(check, sees_pictures)` | `CheckResult`, bool → string | 고칠 대상 결과로 다음 라운드 메시지를 만든다 (R-17) |

`DetectCx`: `request` = 소문자 요청 앞뒤에 공백 하나씩(`" clone this website "`), `words` = 영숫자 외 문자를 공백으로 바꾼 소문자 단어열 앞뒤 공백(`stacks::words`), `target`(`TargetRef`: `Website{url}` / `Local{path}` / `None`), `stack`(선택 전이면 빈 문자열), `deep`(Deep 모드에서 로컬 대상 파일을 들여다봐도 되는지. `DetectCx::new`는 false로 만든다).

**`Check` (빌드를 판정하는 방법 하나)**

| 메서드 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `id()` | → string | 결과의 `check` 필드에 저장되는 고정 id |
| `applies(cx)` | `CheckCx` → bool | 이 실행에서 돌릴지. 거짓이면 결과를 남기지 않고 번호도 매기지 않는다. 기본 true |
| `can_refine(result)` | `CheckResult` → bool | 빌더가 한 턴 더 하면 이 결과를 고칠 수 있는지. 기본 true. 측정 수단(오라클)이 없는 것은 빌더가 코드를 바꿔도 생기지 않으므로 false로 둔다 |
| `run(cx)` | `&mut CheckCx` → `CheckResult` 또는 `ToolError` | 판정. 오류는 라운드 전체를 오류로 만든다 (R-10) |

**`CheckCx` (검사가 쓰는 것)**: `ws`, `round`, 그리고 연산 `call(tool, params)`(시간 제한이 지났으면 `TimedOut` 거부, 아니면 엔진 도구 호출), `serve_preview(dir)`(폴더를 loopback으로 서빙해 주소를 돌려주고, 실행의 미리보기 서버를 이것으로 바꾸고 `RunEvent::Preview(url)`를 낸다), `editor()`(게임 엔진 편집기 경로), `stop()`(`CheckStop`), `build_settings()`(설정의 `[build]`), `deep()`(= 세션이 Clean room이 아님), `godot()`(설치된 Godot).

**`CheckStop` (검사 안의 긴 단계를 멈추는 신호)**: `paused()`(사람이 일시정지·중지함), `expired()`(라운드 제한 시각이 지남), `cancelled()`(둘 중 하나), `time_left()`(남은 시간, 제한 없으면 None, 0 아래로 내려가지 않음), `check()`(일시정지면 `Cancelled` 오류를 먼저, 아니면 제한이 지났을 때 `TimedOut` 오류 "The check ran past its time limit, so it was stopped."). 제한 없는 `CheckStop`은 `From<&CancelToken>`로 만든다.

**`CheckResult` (검사 결과 하나, `crates/engine/src/workspace.rs`)**

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `round` | int | 라운드 번호. 0은 빌더 자신의 검사 |
| `check` | string | 검사 id. 상수: `CheckResult::BUILD = "build"`, `CheckResult::WEB_VISUAL = "web-visual"` |
| `passed` | bool | 빌드가 작동함(빌드됐거나, 서빙되어 비교됨). "원본과 같음"이 아니다 |
| `similarity` | optional float 0..=100 | 원본과 얼마나 닮았는지. 비교하지 않았으면 None |
| `note` | string | 사람이 읽는 설명. 판정은 이 텍스트를 읽지 않는다 |
| `artifacts` | list<path> | 검사가 만든 파일, 프로젝트 폴더 기준 상대 경로 |
| `at_ms` | int | 만든 시각(ms) |
| `good_enough` | optional float | 이 검사만의 `similarity` 기준. None이면 실행의 기준(`RunOptions::good_enough`, 기본 90.0) |
| `pages` | list<`PageLikeness{name, dir, similarity}`> | 페이지가 여럿인 웹사이트의 페이지별 닮음. 하나면 비운다 |
| `unknowns` | list<string> | 비교하려 했지만 못 한 것. 하나라도 있으면 `good`이 아니다 |
| `claims` | list<`Claim{title, passed, detail}`> | 빌드가 해야 하는 일을 하나씩 따로 판정한 것. 하나라도 실패면 `good`이 아니다. `detail`은 실패 때만 채운다 |

직렬화: `good_enough`·`pages`·`unknowns`·`claims`는 비어 있으면 쓰지 않는다. 읽을 때 `check`·`passed`가 없는 옛 기록은 `similarity`가 있으면 `web-visual`·`passed=true`, 없으면 `build`·`passed = note.starts_with("Build succeeded")`로 채운다(R-18).

**`KindRegistry`**: `built_in()`(website, game, app 순), `register(kind)`, `get(id)`, `ids()`, `detect(request, target, stack)`, `choose(request, target, deep)` → (kind, stack), `named(request, target)` → optional stack.

**내장 종류별 검사 목록 (R-07)**

| 프로젝트 | 검사 순서 |
|---|---|
| 사람의 기존 프로젝트(`manifest.own_project()`, 종류 무관) | `build`(`OwnBuildCheck`) → `own-tests` |
| website, 대상이 `Website` | `web-visual` |
| website, 대상이 그 밖 | `build` |
| app | `build` → `app-runs` → `app-screenshot` → `DeepOnly(mechanics)` |
| game, 대상이 `Website` | `build` → `app-screenshot` → `game-self-test` |
| game, 대상이 그 밖 | `build` → `app-screenshot` → `game-self-test` → `mechanics` → `DeepOnly(credits)` |
| 모든 경우 뒤에 | WASM 플러그인 검사(이 종류 id를 대상으로 하거나 대상 목록이 빈 것), 플러그인 목록 순 |

### 1.4 행동 규칙과 남은 질문

**종류와 스택 선택**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `KindRegistry::built_in()`, `register(kind)` | 기본 목록은 [website, game, app]. `register`는 같은 id의 종류를 지우고 새 종류를 목록 끝에 붙인다(같은 id를 바꾸면 동점 우선순위가 맨 뒤로 간다) | 코드 확인 |
| R-02 | `detect(request, target, stack)` | 목록 순서대로 `detect`를 불러 점수가 이전 최고보다 **엄격히 클 때만** 바꾼다. 동점이면 먼저 등록된 종류. 아무도 점수를 내지 않으면 None(내장 목록에서는 app이 항상 1을 내므로 None이 나오지 않는다) | 코드 확인 |
| R-03 | `choose(request, target, deep)` | 종류는 `stack=""`로 판별한다. 스택은 `kind.named_stack(cx)` → 스택 표의 `asked_for(words)`(표 순서상 첫 일치) → `kind.default_stack(cx)` 순. 앞의 두 단계는 `deep`과 무관하고, `default_stack`만 `deep`을 본다. `named(request, target)`은 어느 종류든 처음 답한 `named_stack`, 없으면 표 | 코드 확인 |
| R-04 | 내장 종류의 `detect` | website: 대상이 `Website`면 100, 요청에 사이트 단어(영어 외 여러 언어 포함)가 있으면 50, 대상이 없고 스택이 `site=true`면 30. game: 스택이 게임 엔진이면 200, 게임 단어·인원수 표현 등이면 60. app: 항상 1. 단어 목록은 C-03 | 코드 확인 |
| R-05 | 내장 종류의 `default_stack` | website: `"Builder's choice"`. app: Deep이고 `Local` 대상이 콘솔 프로그램이면 `"Rust (console)"`, 아니면 `"Rust + egui (eframe)"`. game: Deep이고 `Local` 대상의 게임 폴더에서 엔진을 찾으면 그 엔진의 스택, 아니면 `Builder::for_game(None)`의 스택(주석상 Unity) | 코드 확인 · game의 기본 엔진이 Unity라는 것은 `default_stack` 주석 기준 추론 |

**검사 목록과 실행**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | 라운드의 검사 목록 구성 | `own_project()`면 `own::checks()`, 아니면 `kind.checks(ws)`. 그 뒤에 플러그인 검사 중 `kinds`가 비었거나 이 종류 id를 포함하는 것을 `PluginJudge`로 감싸 붙인다. 그 다음 `applies(cx)`가 거짓인 검사를 모두 뺀다. 뺀 검사는 결과·번호·진행 이벤트가 없다 | 코드 확인 |
| R-07 | 내장 종류의 `checks` | 1.3 "내장 종류별 검사 목록" 표와 같다 | 코드 확인 |
| R-08 | `DeepOnly(c)` | `applies` = 대상이 `Local` 이고 `cx.deep()`이고 `c.applies(cx)`. `id`·`can_refine`·`run`은 안쪽 검사로 넘긴다 | 코드 확인 |
| R-09 | 각 검사 시작 직전 | `cx.stop().check()`를 본다. 오류 코드가 `Cancelled`면 라운드 전체가 그 오류로 끝난다(그때까지의 결과도 돌려주지 않는다). 그 밖의 오류(`TimedOut`)면 그 검사 id로 `passed=false`, `note="Not run: <오류 메시지>"`인 결과를 붙이고 멈춘다. 통과하면 진행 이벤트 `RunEvent::Step`을 먼저 낸다: 0번 라운드는 (`Step::Build`, `"Checking its work (i of n): <id>…"`), 그 밖은 (`Step::Check`, `"Checking the build (i of n): <id>…"`). n은 R-06으로 남은 검사 수 | 코드 확인 |
| R-10 | `c.run(cx)`의 결과 | `Err`면 라운드 전체가 그 오류로 끝난다(앞 결과는 버려짐). `Ok`면 결과를 붙이고, `passed=false`면 멈춘다. `passed=true`이지만 `good`이 아닌 결과는 멈추지 않는다. 즉 "뒤 검사는 앞 검사가 증명한 것(빌드가 있다)을 필요로 한다"는 순서 규칙은 `passed` 기준이다 | 코드 확인 |
| R-11 | 라운드 시간 제한 | 실제 라운드(`run_checks`)는 제한이 없다. 0번 라운드는 `SELF_CHECK_LIMIT` = 30분을 라운드 전체 마감 시각으로 쓴다. 마감은 (1) 각 검사 시작 전(R-09), (2) `cx.call`마다, (3) 검사 안의 프로그램 실행 마감을 `min(단계 자체 마감, time_left)`로 줄이는 방식으로 닿는다 | 코드 확인 |
| R-12 | `CheckStop` | `paused()`=취소 토큰, `expired()`=now ≥ until, `cancelled()`=둘 중 하나, `time_left()`=남은 시간(음수 없음), `check()`=취소 먼저 `Cancelled`, 그 다음 마감 `TimedOut` | 코드 확인 |
| R-13 | `CheckCx::call(tool, params)` | 마감이 지났으면 도구를 부르지 않고 `TimedOut` 오류. 일시정지는 여기서 보지 않는다(도구 호출 자체가 취소 토큰을 보는지는 이 스펙 범위 밖) | 코드 확인 · 도구 쪽 취소 처리는 미확인 |

**결과 판정과 루프에 대한 약속**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-14 | `CheckResult::good(bar)` | `passed` 이고 `unknowns`가 비었고 모든 `claims.passed`이고, `similarity`가 None이거나 `similarity ≥ (good_enough 또는 bar)`일 때만 참 | 코드 확인 |
| R-15 | `kinds::can_refine(kind_checks, result)` | `kind_checks`(= `kind.checks(ws)`, 플러그인·`own::checks()` 미포함)에서 `id == result.check`인 **첫** 검사를 찾아 그 `can_refine(result)`를 돌려준다. 찾지 못하면 true. 내장 검사 중 `can_refine`을 바꾸는 것은 `MechanicsCheck`(`!result.passed`)뿐이다. 따라서 이 SHA에서 "고칠 수 없는 결과"는 읽을 수 있는 메카닉스 시트(`unknowns` 1개)뿐이다 | 코드 확인 |
| R-16 | 루프가 결과를 읽는 방식(경계) | (a) 재다듬기 대상 = 라운드 결과 중 `!good(opts.good_enough) && can_refine`인 첫 결과. 없으면 재다듬기 없이 끝낸다(남은 `unknowns`는 Ready 요약에 "n comparisons remain unverified"로 남는다). (b) 연속 실패 수 `not_working_checks`는 라운드의 모든 결과가 `passed`면 0, 아니면 +1(상한 10에서 루프가 멈춤). (c) 끝난 빌드가 "쓸 수 있음"인지는 마지막 결과의 `passed`. (d) 0번 라운드 보고(`self_check::report`)는 `!good && !can_refine`인 결과에 "(incomplete; another builder turn cannot resolve this)"를 붙이고, 마지막 줄을 "This would pass…" / "Not good enough yet…" / "These checks remain incomplete; another builder turn cannot resolve them…" 중 하나로 고른다. (e) `run_checks`가 `Cancelled`가 아닌 오류면 루프가 한 번 더 돌리고, 두 번째도 실패하면 "The build is finished, but it couldn't be checked: …" 오류로 끝난다 | 코드 확인(소비 측 `mod.rs`·`self_check.rs`) |
| R-17 | `TargetKind::refine` 기본 | `"Check {round}: {note}\n\nFix this in app/, build again until it succeeds, and reply with 1-2 plain sentences on what you changed."`. website는 `similarity`가 있으면 그림을 볼 수 있는 빌더용 / 볼 수 없는 빌더용 두 문구(닮음 %, `checks/round-N/`과 `capture/` 위치, 고칠 순서), 없으면 기본 문구와 같다(C-04). 루프는 `app/`이 비어 있으면 `refine` 대신 `NO_PROJECT_PROMPT`를 쓴다(경계) | 코드 확인 |
| R-18 | 저장된 결과 읽기 | `CheckRecord`로 읽고 1.3 "직렬화"의 옛 기록 보정을 한다 | 코드 확인 |

**내장 검사별 통과 조건** (모두 `can_refine` 기본 true, 예외는 표에 적음)

| ID | 검사 id · 적용 조건 | 통과 조건과 결과 필드 | 검증 수준 |
|---|---|---|---|
| R-19 | `build` (`BuildCheck`) · 항상 | `build_check`가 정한 (passed, note). 실패이고 `app/`이 비어 있으면(`!app_in_root` 이고 폴더가 비었거나 없음) note 앞에 `"<place> has no files yet, so the builder hasn't written the project."`를 붙인다 | 코드 확인 |
| R-20 | `build_check`의 판단 순서 | ① `engine_for`: `app/`이 정적 사이트면 엔진 없음. 스택이 게임 엔진이어도 `app/`에 다른 도구체인 프로젝트가 있고 그 엔진의 프로젝트 파일이 없으면 엔진 없음. ② 엔진+편집기: Unity(`Assets/` 필요, `CraftBuild.Build` 실행, 마감 4시간, 성공 = 종료 성공 이고 `Build/`에 패키징된 프로그램 있음, 라이선스 문구가 출력에 있으면 실패와 안내), Unreal(`.uproject` 필요, `RunUAT BuildCookRun`, 8시간, 성공 = 종료 성공 이고 패키징됨), Godot(`project.godot` 필요, `--import` 60분 후 `--quit-after 120` 10분, 성공 = 종료 성공 이고 출력에 `SCRIPT ERROR`·`Parse Error`·줄 머리 `ERROR:`가 없음). ③ `Cargo.toml` → `cargo build --quiet`(2시간). ④ `package.json` → `npm run build`(Windows는 `npm.cmd`, 2시간). ⑤ 엔진 없음: 도구체인 표가 있으면 그 빌드 명령(2시간), 없고 정적 사이트면 통과 `"Nothing to build: a static site."`, 아니면 실패 "No project to build found in <place> yet." ⑥ 엔진은 있는데 편집기가 없고 ③④도 아니면 실패 "No project to build found…". 결과 문구: 성공 `"Build succeeded."`, 실패 `"Build failed: <error_lines>"`, 실행 불가 `"Couldn't run the build: <이유>"`. 없는 프로젝트 문구에는 한 단계 아래 폴더의 `Cargo.toml`/`package.json`을 찾아 위치를 덧붙인다 | 코드 확인 |
| R-21 | 빌드 단계 실행(`run_in`) | 마감 = `min(단계 분 × 60초, time_left)`. 시작 전에 `stop.check()`가 오류면 시작하지 않고 실행 불가로 처리(검사는 실패 결과를 낸다, 라운드 오류가 아님). 유휴 마감 60분, 표준 출력 상한 8 MiB, 일시정지 시 즉시 중단. 성공이면 전체 출력, 실패면 출력의 끝부분을 돌려준다. `error_lines`: 빈 줄 제외 후 "error"(대소문자 무시) 또는 "licen"을 포함한 줄 최대 12개, 없으면 마지막 12줄 | 코드 확인 |
| R-22 | `build`(`OwnBuildCheck`), `own-tests` · 사람의 기존 프로젝트 | 빌드: 편집기 있는 Unity 프로젝트는 배치 모드로 열기만 한다(스크립트 컴파일), 엔진이 아니면 도구체인 빌드, 엔진이거나 정적 사이트면 R-20, 아무것도 모르면 **통과** `"Nothing was built: Craft Anything doesn't know how to build this kind of project."`. 테스트: 도구체인 없음·`test_script`가 비었거나 `no_tests` 문구와 같음·실패 출력에 `no_tests` 문구가 있음(스크립트 없는 도구체인만)이면 **통과** `"No tests ran: …"`, 테스트 실패면 실패와 마지막 20줄, 마감 30분 | 코드 확인 |
| R-23 | `web-visual` (`WebVisualCheck`) · website이고 대상이 `Website` | 빌드된 사이트 폴더(`site_dir`)가 없으면 실패(찾은 위치를 안내, `app/`이 비면 그 사실을 먼저). 있으면 서빙하고 `checks/round-N/`을 새로 만든 뒤, 시작 페이지와 조사한 다른 페이지마다 `web_site_open`·`web_site_capture` 호출(**도구 오류는 라운드 오류**). 폭(설정 `build.widths()`)마다 원본 스크린샷과 비교. 원본은 있는데 비교 못 한 폭은 `unknowns`, 원본이 없는 폭은 무시. 비교된 폭이 없는 페이지는 note만. 비교된 페이지가 하나도 없으면 실패 "The build couldn't be compared with the original." 그 밖은 **통과**, `similarity` = 페이지별 평균의 평균, `claims` = 페이지 비교(`page_claims`)와 열린 상태 비교, `pages`는 페이지가 2개 이상일 때만. 텍스트·구조·디자인 비교는 note만 바꾸고 점수에 넣지 않는다 | 코드 확인 |
| R-24 | `app-screenshot` (`ScreenshotCheck`) · `capture/runs/`에 원본 실행 기록이 없을 때 | 실행할 프로그램이 없으면 실패 `"There's no built program to start yet."`. 프로그램을 `--screenshot <절대 경로>`로 실행(이전 파일 먼저 삭제, 마감 `min(90초, time_left)`, 출력 상한 256 KiB). 파일이 없으면 실패(종료 코드와 마지막 줄, 계약 문구 포함). PNG가 아니면 실패. 64×36으로 줄인 밝기의 표준편차가 2.0 미만(한 색)이면 실패. 그 밖은 **통과**. `reference/` 그림과 `capture/window.png` 중 가장 닮은 것을 note에 적고, 설정 `build.picture_good_enough`가 있을 때만 `similarity`와 `good_enough`를 채운다(없으면 note에만). `capture/window.png`가 있으면 프로그램을 보통으로 실행해 창을 찍고, `capture/ui-tree.json`이 있으면 원본의 상호작용 컨트롤(라벨 있는 것, 최대 20개)마다 `claim`을 만든다. 실행 화면 촬영 실패는 note만 바꾼다 | 코드 확인 |
| R-25 | `app-runs` (`RunsCheck`) · `capture/runs/`에 `CASES`(인자 없음, `--help`, `--version`) 중 하나 이상의 원본 기록이 있을 때 | 실행할 프로그램이 없으면 실패. 있으면 **통과**이고, 원본 기록마다 `runtime_walkthrough_record`(마감 8초)로 실행해 `checks/round-N/runs/<slug>.json`에 쓰고, 입력마다 claim 2개: "종료 방식이 같다", "출력 단어의 80% 이상이 같고 숫자 비교가 맞는다". 도구 오류는 note에 쓰고 그 입력의 claim이 실패한다(라운드 오류 아님). `CreateDir` 실패는 라운드 오류 | 코드 확인 · 숫자 비교 세부는 C-11 |
| R-26 | `game-self-test` (`SelfTestCheck`) · 항상(game) | 프로그램을 `--self-test <file.json>`으로 실행(R-24와 같은 실행 규칙). 프로그램 없음·파일 없음·JSON을 못 읽음·`version`이 1보다 큼이면 실패. 읽히면 `verdict`가 `passed`를 정하는데, **이 SHA의 구현은 핵심 단계(`move`·`act`·`hud`) 중 하나라도 통과하지 못하면 `passed=true`, 셋 다 통과하면 `passed=false`**(문서·테스트와 반대, 2.1). `claims`는 핵심 3단계 각각(보고서에 없으면 "not tested"로 실패) + 게임이 더한 단계 최대 20개. 결과적으로 셋 다 통과하면 검사 실패로 멈추고, 하나라도 실패하면 `passed`이지만 claim 실패로 `good`이 아니다 | 코드 확인 |
| R-27 | `mechanics` (`MechanicsCheck`) · app은 `DeepOnly`, game은 대상이 `Website`가 아닐 때 항상 | `app/mechanics.json`이 없음·너무 큼·못 읽음·더 새 버전·값 없음이면 실패(계약 문구 포함) → `can_refine=true`. 읽히면 **통과**, note에 값 수·출처 있는 수·추정 수·둘 다 없는 이름(최대 8개)을 적고, `unknowns`에 "Mechanics behavior has not been measured against app/mechanics.json." 하나를 넣는다 → `good`이 아니고 `can_refine=false`. 출처도 추정 표시도 없는 값은 실패 사유가 아니다 | 코드 확인 |
| R-28 | `credits` (`CreditsCheck`) · game, 대상이 `Website`가 아니고 `DeepOnly` | 공백을 하나로 접은 `app/README.md`가 `PRIVATE_USE_NOTE` 문장을 그대로 포함하고, `app/CREDITS.md`가 공백 외 내용을 가지면 통과. 아니면 빠진 것을 나열해 실패 | 코드 확인 |
| R-29 | 플러그인 검사 (`PluginJudge`) · 플러그인이 지정한 종류 | id는 플러그인 검사의 id. 빌드를 JSON(요청·종류·스택·라운드·파일 목록, 요청한 확장자의 텍스트, 상한 표시)으로 넘긴다. 응답의 `passed`(없으면 false), `summary`, `similarity`(유한값만, 0..100으로 자름). **플러그인 실행 자체가 실패하면 `passed=true`**와 note "The <title> check couldn't run: …"(빌더를 고치러 보내지 않으려는 것). `can_refine`은 R-15에 따라 true | 코드 확인 |
| R-30 | 검사 안 프로그램 실행(`run_with`, R-24·R-26 공통)의 시작 거부 | 시작 직전 `stop.check()`가 오류면 그 오류가 `run`의 `Err`가 되어 **라운드 오류**가 된다(R-09의 "Not run" 결과와 다름, 빌드 단계 R-21과도 다름) | 코드 확인 |

- 불변식:
  - 한 라운드의 결과 목록에서 `passed=false`는 많아야 하나이고, 있으면 마지막이다(R-09·R-10).
  - `unknowns`나 실패한 `claims`가 있는 결과는 `similarity`와 무관하게 `good`이 아니다(R-14). 측정하지 못한 것은 "닮음"으로 치지 않는다.
  - `note`는 판정에 쓰이지 않는다. 판정은 `passed`·`similarity`·`good_enough`·`unknowns`·`claims`만 읽는다(옛 기록 보정 R-18만 예외).
- 미결정: 없음.
- 확인 한계:
  - 실행·빌드·테스트를 하지 않았다. R-26의 반전은 코드와 테스트 본문을 대조한 것이고, 테스트가 실제로 실패하는지는 돌려 보지 않았다.
  - 엔진 도구(`web_site_capture` 등)와 `Process`, 엔진 헬퍼(`launch`, `site_dir`, `toolchains::found_in`)의 내부는 경계로만 읽었다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/ai/src/rebuild/kinds/mod.rs:96-143` `TargetKind` | 메서드 목록과 기본값, 기본 `refine` 문구 | R-17, 1.3 |
| C-02 | `crates/ai/src/rebuild/kinds/mod.rs:258-356` `plugin_ids`·`run_checks_within`·`Check`·`can_refine`·`DeepOnly` | 목록 구성·순차 실행·멈춤·이벤트 문구·`can_refine` 조회 | R-06, R-08~R-10, R-15 |
| C-03 | `crates/ai/src/rebuild/kinds/website.rs:146-182` `detect`, `kinds/game.rs:11-49`·`74-112` `says_play`·`detect`·`:204-270` 에스토니아어·스페인어 판별, `kinds/mod.rs:53-66` | 종류 판별 단어 목록과 점수 | R-04 |
| C-04 | `crates/ai/src/rebuild/kinds/website.rs:219-246` `checks`·`refine` | website 검사 선택과 재다듬기 문구 3종 | R-07, R-17 |
| C-05 | `crates/ai/src/rebuild/kinds/mod.rs:145-256` `CheckCx`·`within_limit`·`CheckStop` | 시간 제한·일시정지 의미 | R-11~R-13 |
| C-06 | `crates/engine/src/workspace.rs:247-388` `CheckResult`·`Claim`·`PageLikeness`·`good`·`CheckRecord`·`From<CheckRecord>` | 결과 필드, `good` 공식, 옛 기록 보정 | R-14, R-18 |
| C-07 | `crates/ai/src/rebuild/check.rs:7-262` `run_in`·`own_build_check`·`own_tests_check`·`build_check`·`engine_for`·`static_site`·`missing`·`nested_project`·`error_lines` | 빌드 판단 순서·마감·출력 처리·문구 | R-19~R-22 |
| C-08 | `crates/ai/src/rebuild/kinds/mod.rs:358-371` `BuildCheck`, `crates/ai/src/rebuild/mod.rs:1539-1552` `app_is_empty`·`no_files_yet` | 빈 `app/` 문구 접두 | R-19 |
| C-09 | `crates/ai/src/rebuild/kinds/website.rs:764-875` `missing_site_note`·`WebVisualCheck::run` (계산 helper `page_claims` `:484`, `picture_likeness` `:694`, `states_note` `:719`) | 페이지·폭 반복, unknown/claim 수집, 실패 조건 | R-23 |
| C-10 | `crates/ai/src/rebuild/kinds/screenshot.rs:15-106` `SCREENSHOT_CONTRACT`·`RUN_LIMIT`·`ScreenshotCheck`, `:148-213` `running_note`·`INTERACTIVE`·`control_claims`, `:289-348` `OwnRun`·`NO_PROGRAM`·`run_with`·`is_blank`, `:362-393` `picture_likeness` | 실행 규칙, 빈 그림 판정, 닮음 계산, 컨트롤 claim | R-24, R-26, R-30 |
| C-11 | `crates/ai/src/rebuild/kinds/runs.rs:10-18` `CASES`·`RUN_MS`·`OUTPUT_ALIKE`, `:81-86` `captured`, `:238-307` `run_comparison`, `:309-375` `RunsCheck` | 입력 목록, 적용 조건, 입력별 claim | R-25 |
| C-12 | `crates/ai/src/rebuild/kinds/self_test.rs:12-101` `SELF_TEST_CONTRACT`·`CORE_LOOP`·`SelfTestCheck`·`claims`·`verdict` | 보고서 판정(반전 포함)과 claim | R-26 |
| C-13 | `crates/ai/src/rebuild/kinds/mechanics.rs:8-57` `MECHANICS_CONTRACT`·`MechanicsCheck`·`problem_note` | 시트 문제별 실패, 읽힘 = 통과+unknown, `can_refine` | R-15, R-27 |
| C-14 | `crates/ai/src/rebuild/kinds/game.rs:175-202`·`272-288` `checks`·`CreditsCheck`·`credits`, `crates/ai/src/rebuild/brief.rs:260` `PRIVATE_USE_NOTE` | game 검사 목록, 크레딧 판정 | R-07, R-28 |
| C-15 | `crates/ai/src/rebuild/kinds/app.rs:29-41`·`67-70`, `kinds/own.rs:8-42` | app 판별·기본 스택·검사 목록, 기존 프로젝트 검사 | R-04, R-05, R-07, R-22 |
| C-16 | `crates/ai/src/rebuild/kinds/plugin_check.rs:10-117` `PluginJudge`·`build_json` | 플러그인 입력 JSON과 응답 해석, 실행 실패 = 통과 | R-29 |
| C-17 | `crates/ai/src/rebuild/kinds/mod.rs:373-444` `KindRegistry`·`named_stack` | 등록·판별·선택 | R-01~R-03 |

### 1.6 수락 사례

출처: 사례별 표기("구현"= 구현에서 도출, "테스트"= 원본 테스트 열람)

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-27, R-15 | 검사가 `mechanics` 하나인 종류. ① `app/mechanics.json` 없음 ② `{ not json` ③ 값 4개(출처 1, 추정 2, 둘 다 없음 1) | ① `passed=false`, note에 "no app/mechanics.json"과 `"version": 1`, `can_refine=true` ② `passed=false` ③ `passed=true`, note에 "4 values (1 with a source, 2 estimated)"와 "neither a source nor \"estimated\": crouch.", `claims` 비고 `unknowns` 1개, `good(0.0)=false`, `can_refine=false` (`DeepOnly`로 감싸도 같음) | 테스트 |
| T-02 | R-10 | app 프로젝트, 빌드 실패 | 결과 1개(`build`, `passed=false`). `app-runs`/`app-screenshot`/`mechanics`는 결과 없음 | 구현 |
| T-03 | R-09 | 0번 라운드, 첫 검사가 마감 뒤에 끝나 두 번째 검사 시작 전 마감 지남 | 결과 2개. 두 번째는 그 검사 id, `passed=false`, note `"Not run: The check ran past its time limit, so it was stopped."`. 이후 검사 없음 | 구현 |
| T-04 | R-09 | 검사 시작 전 사람이 일시정지 | `run_checks`가 `Cancelled` 오류. 결과 목록 없음 | 구현 |
| T-05 | R-29 | 플러그인 응답 `{"passed": false, "similarity": 140, "summary": "No title screen."}`, 제목 "Style" / 플러그인 실행 오류 "boom" | (`passed=false`, `similarity=100.0`, note "Style: No title screen.") / (`passed=true`, `similarity=None`, note에 "couldn't run: boom") | 테스트 |
| T-06 | R-14 | `passed=true`, `similarity=85`, `good_enough=None`, 기준 90 / 같은 결과에 `good_enough=80` / `unknowns=["x"]`, `similarity=None` | false / true / false | 구현 |
| T-07 | R-26 | 보고서 `{"version":1,"steps":[move 통과, act 통과, hud 통과]}` | 이 SHA 구현: `passed=false`, note가 "The self-test doesn't show the core loop working yet: 0 of 3 steps don't pass ()…"로 시작, claim 3개 모두 통과. 원본 테스트 `the_core_loop_passes_only_when_every_step_does`는 `passed=true`를 기대한다(2.1) | 구현 · 테스트와 불일치 |
| T-08 | R-26 | 보고서 `move` 실패, `hud` 통과, `act` 없음 | 이 SHA 구현: `passed=true`, note "The self-test plays the core loop: hud." claim: move 실패, act "not tested" 실패, hud 통과 → `good=false`, `can_refine=true` | 구현 |
| T-09 | R-20 | `app/index.html`에 공백 아닌 내용, 매니페스트 없음, 스택 "Plain HTML and CSS" 또는 "Unity" / `index.html`이 공백뿐 | (true, `"Nothing to build: a static site."`) / 실패 | 테스트(`a_static_site_has_nothing_to_build`) |
| T-10 | R-20 | `app/`에 아무것도 없고 `app/app/Cargo.toml`이 있음, place `"app/"` | (false, "No project to build found in app/ yet. There's a Cargo.toml one folder down, in app/app/, but the build runs in app/ itself: its files belong there.") | 테스트(`a_project_one_folder_down_is_named`) |
| T-11 | R-07 | website 종류, 대상 `None` | 검사 목록 `[build]` 하나 | 구현 |
| T-12 | R-15 | 결과 `check="plugin-check"`, kind 목록에 그 id 없음 | `can_refine=true` | 구현 |
| T-13 | R-01, R-02 | 같은 점수를 내는 종류 A·B가 이 순서로 등록된 뒤 A를 다시 `register` | 판별 결과 B(A가 목록 끝으로 감) | 구현 |
| T-14 | R-18 | 저장 기록 `{"round":1,"similarity":null,"note":"Build succeeded.","artifacts":[],"at_ms":0}` | `check="build"`, `passed=true` | 구현 |
| T-15 | R-24 | `--screenshot` 결과 PNG가 한 색 | `passed=false`, note "The program's screenshot is blank (one colour)…", `artifacts`에 그 파일 | 구현 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01~R-03 | C-17 | 전문 읽음 |
| R-04 | C-03, C-15 | `detect` 본문 읽음. 단어 목록은 옮기지 않음 |
| R-05 | `kinds/website.rs:184-186`, C-15, `kinds/game.rs:114-121` | `Builder::for_game(None)`이 Unity라는 것은 주석("else Unity")만 봤다 |
| R-06~R-10 | C-02 | 전문 읽음 |
| R-11 | C-02, `crates/ai/src/rebuild/self_check.rs:8-13` `SELF_CHECK_ROUND`·`SELF_CHECK_LIMIT`, `:164-168` | 0번 라운드만 `run_checks_within(.., Some(SELF_CHECK_LIMIT))` |
| R-12, R-13 | C-05, `crates/platform/src/cancel.rs:22-24` `CancelToken::check` | `ToolError::cancelled()`의 코드가 `Cancelled`라는 것은 R-09 분기와 함께 읽음 |
| R-14, R-18 | C-06 | 전문 읽음 |
| R-15 | C-02 `can_refine`, C-13, `tests.rs:1548-1606` `the_mechanics_sheet_is_required_without_claiming_effective_behavior` | `fn can_refine` 구현은 레포 전체에서 `MechanicsCheck` 한 곳(grep) |
| R-16 | `crates/ai/src/rebuild/mod.rs:1045-1101`(재다듬기 대상·연속 실패·쓸 수 있음), `:1102-1125`(Ready 요약), `:1192-1209` `checks_with_a_retry_now`, `self_check.rs:95-146` `report`, `:73-92` `summary` | 루프 본문은 7행 범위라 소비하는 줄만 읽었다 |
| R-17 | C-01, C-04, `mod.rs:1092` | |
| R-19~R-22 | C-07, C-08, C-15 | `check.rs` 전문, 테스트는 사례명 확인 후 T-09·T-10만 열람 |
| R-23 | C-09 | 계산 helper 내부는 읽지 않음 |
| R-24, R-30 | C-10 | `running_note` 이후 계산(`controls_likeness`)은 note만 바꾼다는 것까지만 확인 |
| R-25 | C-11 | `run_comparison`의 숫자 비교 분기는 C-ID로 넘김 |
| R-26, T-07, T-08 | C-12 | **문서·테스트와 구현이 다르다.** 모듈 주석(`self_test.rs:1-5` "the game isn't ready until every step of the core loop passes"), `SELF_TEST_CONTRACT`, 테스트 `self_test.rs:105-125` `the_core_loop_passes_only_when_every_step_does`(모두 통과 → `ok` 기대)는 "모두 통과해야 통과"를 말하지만, `verdict`(`:87-101`)는 `if not.is_empty() { return (true, …) }`로 반대다. git 이력은 squash 1개(`f64ae3bf`)라 언제 바뀌었는지는 알 수 없다. 테스트를 실행하지 않았다 |
| R-27 | C-13 | `extending.md`는 "측정 못 한 비교는 `unknowns`에, 빌더가 못 고치면 `can_refine`이 false일 수 있다"고 쓰지만, `unknowns`를 내는 다른 검사(`web-visual`의 비교 못 한 폭·상태)는 `can_refine`을 바꾸지 않아 재다듬기 대상이 된다. 문서와 모순은 아니고 적용 범위 차이다 |
| R-28 | C-14 | |
| R-29, T-05 | C-16, `plugin_check.rs:138-150` `a_plugin_that_fails_to_run_doesnt_fail_the_build` | 테스트 열람 |
| R-24 | C-10 | 모듈 주석(`screenshot.rs:1-8`)은 사람 그림과의 닮음이 "advisory for now: it doesn't decide when to stop refining"이라 하지만, 구현은 `build.picture_good_enough`가 설정되면 `similarity`·`good_enough`를 채워 판정에 쓴다(`:85-93`). 설정이 없을 때만 주석과 같다 |
| T-01 | `tests.rs:1548-1606` | 테스트 열람 |
| T-09, T-10 | `check.rs:443-470`, `:506-550` | 테스트 열람 |

### 2.2 코드 읽는 순서

`kinds/mod.rs`(트레이트 → `run_checks_within` → `can_refine` → `KindRegistry`) → `crates/engine/src/workspace.rs:247-388` → 종류 하나(`kinds/app.rs`)의 `checks` → 검사 하나(`check.rs` `build_check`) → 소비 측 `mod.rs:1045-1101`·`self_check.rs:95-146`. 나머지 검사는 같은 틀에서 통과 조건만 다르다.

## 적용 메모

우리 절차(`OSS_ANALYSIS_WORKFLOW.md`, `templates/capability-request-template.md`)와 비교한 보완 후보다. 원본 동작이 아니다.

| 관련 R-ID | 원본과 다르게 할 점(우리 절차에 들일 것) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-14, R-16 | 재구현 검증 결과를 R-ID마다 "작동(passed)"과 "일치(good)" 두 칸으로 적는다 | 원본은 "빌드가 돈다"와 "원본과 같다"를 다른 필드로 판정하고, 쓸 수 있음(마지막 `passed`)과 끝냄(`good`)을 따로 쓴다. 우리 4장 6번은 재구현 검증 결과의 형식을 정하지 않았다 | 재구현 검증 보고에 R-ID별 표(작동/일치/미검증 사유) 추가 |
| R-14, R-27 | "비교하지 못한 항목은 통과로 치지 않는다"를 재구현 검증 규칙으로 둔다. 비교 못 한 R-ID는 `미검증`으로 세고 보고에 개수를 적는다 | 원본은 `unknowns`가 하나라도 있으면 `good`이 아니고, Ready 요약에 "n comparisons remain unverified"를 남긴다 | 재구현 검증 보고 끝에 "미검증 n개" 줄 |
| R-15, R-27 | 차이를 "재구현자가 다시 하면 고칠 수 있음"과 "검증 수단이 없음(재시도해도 안 생김)"으로 나누고, 뒤쪽은 재작업을 요청하지 않고 미검증으로 닫는다 | 원본의 `can_refine=false`는 "스펙 결함 vs 환경 한계"가 아니라 "오라클 없음"을 뜻한다. 이 SHA에서는 메카닉스 시트 하나에만 적용되고, `web-visual`의 비교 못 한 폭은 여전히 재시도 대상이다. overview 후보 표의 "스펙 결함 vs 환경 한계" 문구를 이 기준으로 고칠 것 | overview 2절 후보 표 7·9행 문구 |
| R-29 | 검증 도구(우리 쪽 `scripts/check.py` 등)가 실행에 실패하면 스펙 결함으로 보고하지 않고 "도구 실패"로 따로 적는다 | 원본은 플러그인 실행 실패를 통과+note로 처리해 빌더를 잘못된 수정으로 보내지 않는다 | 재구현 검증 보고에 "도구 실패" 칸 |
| R-10 | 재구현 검증을 "빌드 → 핵심 동작 → 세부 비교" 순으로 하고, 앞 단계가 실패하면 뒤 단계 결과를 만들지 않는다 | 원본은 `passed=false`에서 멈춰 뒤 검사가 의미 없는 실패를 쌓지 않게 한다 | 재구현 검증 절차 순서 |
| R-26 | 테스트 본문과 구현이 다를 때 구현을 사실로 쓰는 우리 규칙(4장 2번)이 이 레포에서 실제로 필요한 사례다. 스펙 작성 시 "주석·테스트가 주장하는 판정"과 "구현의 판정"을 C-ID 범위 안에서 한 번 대조하는 점검을 4장 3번 완료 조건에 넣을 것을 검토 | `self_test.rs`는 주석·계약 문구·테스트가 모두 같은 말을 하는데 구현만 반대다. 주석만 읽고 스펙을 쓰면 틀린다 | 4장 3번 완료 조건 문장 |
