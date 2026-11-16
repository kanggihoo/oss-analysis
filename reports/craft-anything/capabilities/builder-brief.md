---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/ai/src/rebuild/brief.rs
  - crates/ai/src/rebuild/stacks.rs
  - crates/ai/src/rebuild/stacks.toml
  - crates/ai/src/rebuild/kinds/mod.rs
  - crates/ai/src/rebuild/kinds/app.rs
  - crates/ai/src/rebuild/kinds/game.rs
  - crates/ai/src/rebuild/kinds/website.rs
  - crates/ai/src/rebuild/kinds/screenshot.rs
  - crates/ai/src/rebuild/kinds/self_test.rs
  - crates/ai/src/rebuild/kinds/mechanics.rs
  - crates/ai/src/rebuild/mod.rs
  - crates/ai/src/rebuild/self_check.rs
  - crates/engine/src/clean_room.rs
  - crates/ai/src/rebuild/tests.rs
depends:
  - ../capabilities/check-contract.md
  - ../capabilities/unknown-ledger.md
status: ready
---

# 빌더 브리프·행동 규칙

> 프로젝트 매니페스트(요청·대상·스택), 실행 모드(Clean room/Deep), 빌더가 그림을 볼 수 있는지와 대상 종류를 받아, 코딩 에이전트에게 보낼 첫 브리프와 이후 턴의 메시지(후속 요청·이어 하기·중간 추가·재다듬기)를 조립하고, 모든 빌더에게 같은 고정 규칙(`RULES`)과 작업 단계(`steps`)를 준다.

<!-- 용어
- 브리프(brief): 빌더의 세션에 처음 보내는 긴 메시지. 함수 `brief::brief`가 만든다.
- 빌더(builder): `app/`에 코드를 쓰는 에이전트. 코딩 에이전트 앱(Claude Code 등, 자기 세션을 이어 감)과 내장 API 루프(`api_loop`, 이 엔진이 대화 기록을 들고 있음) 두 갈래가 있다.
- 그림을 볼 수 있음(`sees_pictures`): 빌더가 Read 도구로 PNG를 열어 볼 수 있는지. 이 SHA에서는 `!api_loop`와 같다.
- 스택 표: `crates/ai/src/rebuild/stacks.toml`. `[[stack]]`과 `[[library]]` 항목의 목록.
- 이 문서에서 "규칙 원문"은 영어 프롬프트 문자열이다. 원문을 옮기지 않고 의미와 위치(C-ID)만 적는다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 루프가 이번 빌드 턴의 메시지 종류를 고른다: 이어 갈 세션이 있고 새 요청이 있으면 후속 메시지, 요청 없이 멈춘 빌드를 이어 하면 이어 하기 메시지, 그 밖은 첫 브리프(API 루프면 앞에 도구 안내를 붙임)(R-17).
2. 첫 브리프는 고정 순서로 조립된다: 역할 문장 → 요청·대상·작업 폴더 → 증거(capture/) 안내(대상×모드×그림 가능 여부) → 만들 것(종류의 `goal`) → 스택 단계(스택 표 + 요청한 라이브러리) → 작업 단계 `steps(deep)` → 규칙 `RULES` → 종류의 `brief_sections` → 사람 그림 안내 → 시작 파일 안내 → 사람이 덧붙인 말(R-01).
3. 앞에 "Just ask" 대화 요약을 붙이고, 첫 턴이고 원본 파일 추출본이 있으면 뒤에 그 안내를 붙인다(R-17, R-22).
4. 턴이 끝난 뒤 루프는 상황에 따라 다음 메시지를 만든다: 사람이 작업 중에 남긴 노트(R-19), Deep 모드에서 디컴파일을 안 했을 때의 한 번짜리 독촉(R-20), 검사가 고칠 대상을 찾았을 때의 재다듬기 메시지(R-21).
5. 빌더는 이 메시지들의 지시에 따라 `core_unknown_add`/`core_unknown_edit`/`core_unknowns_show`로 모르는 것을 기록·종결하고, `rebuild_check`로 스스로 검사한다(R-10, 경계).

### 1.2 범위·통합 지점

- 제공: 첫 브리프와 이후 턴 메시지의 조립 순서·조건, 고정 규칙 7개와 작업 단계 5개의 의미, 대상×모드×그림 가능 여부에 따른 증거 안내 분기, 스택 표의 의미(스택 선택 문구 매칭, 단계 문구 치환, 라이브러리 추가), 종류별 브리프 절(`brief_sections`·`follow_up_sections`)의 내용, 게임 규칙·디컴파일 안내·생성 에셋 안내·원본 파일 추출기 브리프.
- 제외:
  - 종류 판별과 스택 결정 순서(`KindRegistry::choose`), `TargetKind`·`refine`의 계약, 검사가 빌더에게 요구하는 계약 문구가 검사 판정과 맞물리는 방식: [대상 종류·검사·재시도 계약](./check-contract.md). 이 스펙은 그 메서드가 돌려준 문자열을 어디에 넣는지만 정한다.
  - 메시지를 언제 보내는지(라운드, 첫 턴 여부 `first`, 이어 하기 여부 `carrying_on`, 세션 유무 `has_history`의 계산), 세션 복원·`handoff` 문자열을 만드는 일: 리빌드 루프(7행)와 에이전트 구동(13행). 이 스펙은 이 값들을 입력으로 받는다.
  - `core_person_ask`, 노트(`notes`), "Just ask" 질문 저장·`untold` 계산: 인박스(10행). 이 스펙은 `AskedQuestion{question, answer}` 목록을 입력으로 받는다.
  - Clean room에서 어떤 도구가 실제로 거부되는지: Clean room 모드(11행). 이 스펙은 브리프가 빌더에게 하는 말만 정한다.
  - 스택 표의 `uses`·`needs`·`found_by`·`site`·`program`을 쓰는 기능(빌드에 쓰인 스택 기록 `used_in`, 사람 프로젝트 판별 `found_in`, 이름으로 고르기 `resolve`, 프로그램 누락 안내 `missing_program`): 브리프 문장에 들어가지 않으므로 필드 의미만 1.3에 적는다.
- 외부 의존·선행 계약:
  - [check-contract](./check-contract.md): `TargetKind::{goal, brief_sections, follow_up_sections, self_screenshots, rebuild_words, refine}`와 `BriefCx`. 이 스펙은 이 메서드의 반환값을 넣는 자리를 정한다.
  - [unknown-ledger](./unknown-ledger.md) (경계만 정의): 브리프는 다음을 **빌더에게 지시**만 한다. (a) 증거가 답하지 못한 질문마다 `core_unknown_add`에 질문(`question`), 그것을 해결할 확인 방법(`probes`), 중요도(`severity`)를 넣는다. (b) 나중에 답을 찾으면 `core_unknown_edit`로 상태 `resolved`, 해결 설명(`resolution`), 근거 증거 id(도구 쪽 칸은 `evidence_for`)를 넣어 닫는다. (c) 답하기 전까지는 그 항목에 대신 한 것(추정·자리표시·사람에게 질문)을 적는다. (d) 회신 전, 이어 하기 시작 시, 다른 컴퓨터에서 이어 받을 때 `core_unknowns_show`로 열린 질문을 본다. 브리프는 `domain`, `unknown_id`, `based_on_revision`을 말하지 않는다(빌더는 도구 스키마에서 알아야 한다). 저장 형식, 상태 전이, revision 검사는 unknown-ledger가 정한다. 특히 브리프가 "증거 id를 넣어 닫으라"고 해도 도구는 증거 없는 `resolved`를 거부하지 않는다(unknown-ledger R-07). 즉 이 요구는 지시일 뿐 강제가 아니다. 반대 방향으로, 0번 라운드 검사 보고(`self_check::report`)는 프로젝트 조사 폴더에서 `status != resolved`인 항목을 중요도 내림차순·질문 오름차순으로 읽어 최대 8개를 "Your open questions: … (id)"로 보여 주고 `core_unknown_edit`로 닫으라고 다시 지시한다. 세 도구는 Clean room 허용 목록에 있다.
  - `Workspace`/`Manifest`(엔진): `request`, `target`, `stack`, `own_project()`, `app_in_root`, `start_files`, `generate_assets`, `asset_budget_usd`, `decompiled`, `last_reply`, `references()`(`reference/`의 그림 경로 목록), `assets_spent()`, `capture_dir()`, `root`.
  - 에셋 가격 표 `assets::Catalogue::built_in()`: 그림·3D 모델 가격. 모르는 그림 모델이면 기본 모델 가격을 쓴다.
- 소유 상태·부작용: 없음. 모든 함수는 문자열을 만들 뿐이다. 읽는 것은 `capture/`에 `.har` 파일이 있는지, `capture/routes.json`, 열린 상태 목록, `capture/runs/` 기록, `reference/` 목록, `app/Original/MANIFEST.md` 존재 여부다. 스택 표는 바이너리에 포함된 TOML을 처음 쓸 때 한 번 파싱해 프로세스 끝까지 둔다.

### 1.3 인터페이스와 데이터 의미

**조립 함수**

| 연산 | 입력 → 출력 | 의미·제약 |
|---|---|---|
| `brief(kind, cx, extra)` | `TargetKind`, `BriefCx`, optional string → string | 첫 브리프. `extra`는 사람이 이번에 한 말. 트림 후 요청과 같으면 넣지 않는다 |
| `steps(deep)` | bool → string | 작업 단계 5개. Deep 여부로 1단계의 "추가로 물어볼 수 있는 것"만 다르다 |
| `RULES` | 상수 string | 규칙 7개. 모든 브리프에 같은 글로 들어간다 |
| `follow_up(message, kind, api_loop)` | → string | 세션이 있는 빌더에게 새 요청을 전한다 |
| `continue_prompt(kind, api_loop)` | → string | 멈춘 빌드를 이어 하라는 메시지 |
| `resumed_elsewhere(brief, last_reply, handoff)` | → string | 세션이 이 컴퓨터에 없을 때: 전체 브리프 + 이어 받기 안내 + 이전 대화(있으면) 또는 마지막 회신(최대 2,000자) |
| `added_prompt(notes)` | list<string> → string | 작업 중 사람이 추가한 노트 목록 |
| `just_asked(asked)` | list<`AskedQuestion`> → string | "Just ask" 대화 요약. 비어 있으면 빈 문자열 |
| `pictures_note(ws, kind, sees)` / `pictures_reminder(ws, sees)` | → optional string / string | 사람 그림 안내(첫 브리프) / 이후 턴의 짧은 상기 |
| `start_files_note(manifest)` | → optional string | 시작 폴더에 사람 파일이 있었을 때 |
| `game_steps(deep, ghidra, has_target, generated, sees)` | → string | 게임을 원본처럼 플레이되게 만드는 규칙 |
| `decompile_note(game, ghidra)` | → string | Deep 모드 디컴파일 의무 |
| `assets_note(ws, image_model)` | → string | 생성 에셋 도구·가격·예산·저장 위치 |
| `extract_brief(folder)` | path → string | 원본 게임 파일 추출기(빌더와 다른 역할)의 브리프 |
| `stacks::steps(stack, editor)` | string, optional path → string | 스택 표의 `steps`, 자리표시자 치환 |
| `stacks::asked_for(words)` / `stacks::libraries_for(request, stack)` | → optional stack / list<library> | 요청이 이름으로 부른 스택 / 라이브러리 |

**`BriefCx`** (check-contract 1.3 정의를 그대로 씀): `ws`, `deep`(Deep 모드), `ghidra`(Ghidra 설치), `editor`(게임 엔진 편집기 경로), `assets`(에셋 제공자 키가 있음), `image_model`(설정의 그림 모델 id, None이면 표 기본), `sees_pictures`.

**스택 표 `stacks.toml`** (외부 계약: 키 이름 원문)

| 키 | 타입 | 의미 |
|---|---|---|
| `[[stack]].name` | string | 표시·저장되는 스택 이름. 종류의 `default_stack`이 이 이름을 쓴다 |
| `asked_by` | list<string> | 요청을 `words()`로 바꾼 문자열(소문자, 영숫자 외를 공백으로, 앞뒤 공백)에 **부분 문자열로** 들어 있으면 이 스택을 부른 것. 표 순서상 첫 스택이 이긴다 |
| `steps` | optional string | 빌더에게 줄 단계. `{editor}`, `{player}`, `{ext}`를 치환. 없으면 일반 문구 |
| `engine` | optional string | `unity`/`unreal`/`godot`/`rust` |
| `uses` / `needs` / `found_by` / `site` / `program` / `program_from` | | 브리프 밖에서 쓰임(1.2 제외) |
| `[[library]].name`·`asked_by`·`stacks`·`steps` | | 요청이 부른 라이브러리. `stacks`가 비면 모든 스택, 아니면 이름이 같은 스택에서만. `steps`는 스택 단계 뒤에 붙는다 |

현재 표: 스택 14개(Builder's choice, Phaser, Bevy, Electron, Next.js + TypeScript, Python, React + TypeScript (Vite), Plain HTML and CSS, Rust (console), Rust + macroquad, Rust + egui (eframe), Unity, Unreal Engine, Godot 중 Python은 `steps` 없음), 라이브러리 2개(shadcn/ui, Tailwind CSS). 실제 목록은 C-08.

### 1.4 행동 규칙과 남은 질문

**첫 브리프 조립**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `brief(kind, cx, extra)` | 다음 순서로 이어 붙인다(사이는 빈 줄). ① 역할 문장("You are the builder inside Craft Anything, rebuilding software for a person who doesn't code.") ② `Their request: "<request>"`, `Target: <R-02>`, 작업 폴더 = 워크스페이스 루트 ③ 증거 안내(R-03) ④ `What to build: <R-04>.` ⑤ `How to build it, unless their request says otherwise: <R-05>` ⑥ `steps(deep)`(R-09) ⑦ `RULES`(R-08) ⑧ `kind.brief_sections(cx)` 각각(R-11) ⑨ `pictures_note`(R-14) ⑩ `start_files_note`(R-15) ⑪ `The person also said: "<extra>"`(R-16). 규칙이 요청·스택보다 **뒤**에 오고, 스택 단계 앞에 "요청이 달리 말하지 않으면"이 붙는다 | 코드 확인 |
| R-02 | 대상 줄 | `Website{url}` → "the website <url>", `Local{path}` → "the program at <path>", `None` → "nothing specific (build from the request)" | 코드 확인 |
| R-03 | 증거 안내 분기 | (대상, 모드)별 5가지: Website+Clean room = 방문자가 보는 것만 기록된 capture/ 파일 목록과 "HTML·CSS·스크립트를 읽지 않았고 읽으면 안 됨", 정확한 값으로 맞추라는 지시. Local+Clean room = "capture/README.md는 밖에서 본 것뿐, 안을 열거나 실행·디컴파일하지 말 것", 사람 설명·그림으로 만들고 모르면 `core_person_ask`. Website+Deep = 위 파일 목록에 `breakpoints`·폰트 파일·`page.html`이 더해지고, 동작을 먼저 배우라는 지시와 쓸 도구 목록, "원본 코드를 `app/`에 붙여 넣지 말 것", `capture/`에 `.har`가 있으면 대역 백엔드 도구 안내 추가. Local+Deep = 정적 조사 결과와 게임 파일 목록, "그 폴더는 바꾸지 말 것", 대상 유형별 도구 목록. None = "There is no target to study." 각 분기에서 그림을 볼 수 없는 빌더는 "스크린샷을 열어 보라" 대신 `capture.json`의 `layouts` 측정값을 쓰라는 문구를 받는다(C-02) | 코드 확인 |
| R-04 | 만들 것 | `own_project()`면 "what their request asks of the project in this folder", 아니면 `kind.goal()`(website: "a website that looks and behaves like the original", app: "a desktop app with the same core features", game: "a playable game that plays like the original: the same rules, controls, numbers and feel") | 코드 확인 |
| R-05 | 스택 단계 | `own_project()`면 "keep to what the project already uses." + 편집기가 있으면 " The editor is <path>." 아니면 `stacks::steps(stack, editor)`. 두 경우 모두 그 뒤에 `libraries_for(request, stack)`의 `steps`를 공백 하나로 이어 붙인다 | 코드 확인 |
| R-06 | `stacks::steps` | 표에 그 이름의 스택이 없거나 `steps`가 없으면 `"Use <stack>. Create the project in app/ and make sure it builds or runs without errors."`. 있으면 `{editor}` → 편집기 경로(없으면 빈 문자열), `{player}`/`{ext}` → Windows `StandaloneWindows64`/`exe`, macOS `StandaloneOSX`/`app`, 그 밖 `StandaloneLinux64`/`x86_64` | 코드 확인 |
| R-07 | 스택 표 로딩·매칭 | 포함된 `stacks.toml`을 처음 쓸 때 파싱한다. **파싱이 실패하면 빈 표**가 되어 모든 스택이 일반 문구를 받고 `asked_for`·`libraries_for`는 아무것도 찾지 않는다(앱은 실패하지 않음). `asked_for`: 표 순서상 `asked_by` 문구 중 하나가 `words`에 부분 문자열로 들어 있는 첫 스택. `libraries_for`: 표 순서대로, 문구가 맞고 `stacks`가 비었거나 이 스택 이름을 포함하는 모든 라이브러리 | 코드 확인 |

**고정 규칙과 작업 단계** (원문은 C-01. 아래는 의미)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | `RULES` (모든 첫 브리프) | 7개 규칙. ① 요청이 먼저다. 요청이 언어·프레임워크·엔진·라이브러리·플랫폼을 말하면 이 지시가 다른 것을 말해도 그것으로 만든다. 여기 적힌 스택은 요청이 비워 둔 부분의 기본값일 뿐이다. 빌드·검사가 실패한다고 요청한 것에서 벗어나지 말고 빌드를 고친다(`brief.rs:9`). ② `app/` 안의 파일만 바꾼다. 나머지는 읽기 전용 증거이고, Craft Anything 자신의 기록(`craft.json`, `feed.json`, `inbox/` 전체)을 다른 것이 쓰면 빌드가 멈춘다. 진행 상황은 체크리스트에 두고 그 자리에 자기 파일을 만들지 않는다(`:10`). ③ 레이아웃·스타일·동작은 증거로부터 직접 다시 만든다. 로고·사진·브랜드 이름·긴 글은 사람이 소유나 허가를 확인하지 않으면 복사하지 않고(중요하면 `core_person_ask`로 한 번 묻는다) 중립적인 자리표시(도형·그라데이션, 짧은 예시 글)를 쓴다(`:11`). ④ `core_person_ask`는 결과를 실제로 바꾸는 선택에만, 선택지 2~4개로 쓴다. 스스로 정할 수 있는 기술 세부는 묻지 않는다(`:12`). ⑤ 요청한 것을 만든다. 일부가 이번 버전에 맞지 않으면(온라인 협동, 게임 모드 전체, 다른 플랫폼 등) 빼기 전에 `core_person_ask`로 묻고, 작은 버전을 선택지 하나로 넣는다. 조용히 빼지 않는다(`:13`). ⑥ 개발 서버·감시자 등 끝나지 않는 것을 시작하지 않는다. 서빙과 검사는 Craft Anything이 한다(`:14`). ⑦ 끝에 사람에게 3~5문장 평문: 무엇을 만들었는지, 원본과 무엇이 다르거나 아직 모르는지, 다음에 요청할 만한 것 하나. 코드·파일 경로 금지(`:15`) | 코드 확인 |
| R-09 | `steps(deep)` | "당신이 조사를 이끌고, 도구는 증거로 답한다"로 시작하는 5단계. 1) 증거를 개요부터 읽고(README·요약 먼저), 결과에 중요한 빈틈은 추측 대신 도구로 좁게 묻는다. 같은 답을 받은 호출을 반복하지 않는다. 증거가 답하지 못한 질문은 unknown으로 기록·종결한다(R-10). 증거가 없는 것은 증명이 아니므로 추정한 것은 표시한다. 물어볼 수 있는 것: Deep = 다른 폭·열린 상태 캡처, 페이지·번들 검사, 프로그램 문자열·함수 조회, 게임 설정·파일 읽기. Clean room = 웹사이트의 다른 폭·열린 상태 캡처 또는 `core_person_ask`, 그리고 원본의 파일·폴더·페이지 코드·프로그램을 어떤 도구로도 열기·읽기·나열·가져오기·실행·디컴파일하지 말 것. 2) `TodoWrite`로 3~7단계 체크리스트(사람이 따라갈 평문, 짧은 `activeForm`), 계속 갱신. 3) `app/`에서 만들고 빌드가 성공할 때까지 고친다. 4) `rebuild_check`로 원본과 비교하고, "다른 턴이 고칠 수 있다"는 결과는 고쳐서 다시 검사하고, "다른 턴이 고칠 수 없다"는 비교는 재시도를 멈추고 미검증으로 둔 채 회신에 한계를 적는다. 5) 회신 전 체크리스트와 `core_unknowns_show`를 다시 보고, 한 번 더 보면 정리되는 것은 정리하고 남은 것은 요약에 적는다 | 코드 확인 |
| R-10 | unknown 기록 지시(경계) | 1.2 "외부 의존"의 (a)~(d)와 같다. 지시가 들어가는 곳: `steps` 1단계·5단계(모든 첫 브리프), `continue_prompt`, `resumed_elsewhere`, 0번 라운드 검사 보고 | 코드 확인 · 도구 쪽 동작은 unknown-ledger 소관 |

**종류별 절과 부속 안내**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | `brief_sections` | website: 조사한 다른 페이지가 있으면 경로 목록과 "같은 경로·같은 탐색으로 다시 만들라, 함께 비교된다", 촬영된 열린 상태가 있으면 목록과 "폭마다 같은 방식으로 열리고 같아 보이게", 기존 프로젝트가 아니면 `HOW_TO_RUN`(`app/README.md`에 빌드 명령과 서빙할 폴더를 적으라). app: 기존 프로젝트면 없음. Deep이고 대상이 `Local`이면 `decompile_note(false)`와 `MECHANICS_CONTRACT`. 그 다음 `capture/runs/` 기록이 없으면 스크린샷 계약(`screenshot::contract`), 있으면 `RUNS_BRIEF`. game: 대상이 `Website`면 스크린샷 계약 + `SELF_TEST_CONTRACT`만. 기존 프로젝트면 생성 에셋이 켜졌을 때(`cx.assets && manifest.generate_assets`) `assets_note`만. 그 밖은 `game_steps` → (생성 에셋이면 `assets_note`) → 스크린샷 계약 → `SELF_TEST_CONTRACT` | 코드 확인 |
| R-12 | `game_steps` | 항상: `app/MECHANICS.md`에 플레이를 정하는 모든 수치와 출처(파일·함수 주소·증거 id) 또는 "estimated", 조작·HUD·모드 규칙 맞추기, `MECHANICS_CONTRACT`. 대상이 있을 때: Deep이면 `decompile_note(true)`, Clean room이면 원본 파일·코드를 열지 말고 추정은 표시, 정확한 값이 필요하면 Deep 모드를 권하라. 그리고 "원본 실행을 아직 볼 수 없다"는 문장(그림 가능 여부별). Clean room이면 원본 파일에서 아무것도 가져오지 말고 스타일만 맞춰 직접 만든다(생성 에셋이면 생성 도구로)로 끝. Deep이면 원본 설치본의 파일을 1:1로 쓰라(생성 에셋이면 모델·텍스처·UI 그림만 새로 생성), 게임 아카이브 도구 사용 순서, 암호화·복제 방지 우회 금지, `app/CREDITS.md` 목록과 `app/README.md` 첫 줄 `PRIVATE_USE_NOTE`(이 두 가지는 검사가 본다) | 코드 확인 |
| R-13 | `decompile_note(game, ghidra)` | "Deep 모드: 추정 전에 디컴파일하라", 찾을 대상(게임: 이동·조준·발사·피해·적 행동, 앱: 요청한 기능), 결과를 `app/MECHANICS.md`에 주소와 함께, "estimated"는 코드에서 찾아본 뒤에만, 디컴파일 코드를 `app/`에 붙여 넣지 말 것. Ghidra가 있으면 "느려도 기다려라", 없으면 "내장 디컴파일러는 거치니 다른 함수나 파일로 교차 확인하라" | 코드 확인 |
| R-14 | `pictures_note` | `reference/`에 그림이 없으면 None. 그림을 볼 수 있으면 "계획 전에 모두 Read로 열고 시점·화면 배치·색·질감·비율을 맞추되 로고·캐릭터를 베끼지 말 것", 볼 수 없으면 "그림을 열지 말고 `core_person_ask`로 무엇을 보여 주는지 물어라". `kind.self_screenshots()`이고 기존 프로젝트가 아니면(= website가 아니면) 볼 수 있는 빌더에게는 "빌드 후 `--screenshot`으로 찍어 비교하라", 볼 수 없는 빌더에게는 "검사가 닮음을 알려 준다"를 덧붙인다 | 코드 확인 |
| R-15 | `start_files_note` | `start_files`가 비고 `app_in_root`도 아니면 None. `app_in_root`면 "`app/` 대신 워크스페이스 자체(./)에서 사람 파일을 제자리 수정, 다시 시작·삭제·교체 금지, `app/` 폴더를 만들지 말 것, Craft Anything 기록 파일(`OWN_NAMES`)은 건드리지 말 것"(기존 프로젝트면 "자체 빌드·테스트로 검사되니 우리를 위해 아무것도 추가하지 말 것"). 아니면 "시작 파일은 재료이니 먼저 읽고 필요한 것을 `app/`으로 가져오되 원본은 그대로 둘 것" | 코드 확인 |
| R-16 | 덧붙인 말 | `extra`가 있고 트림한 값이 트림한 요청과 다를 때만 `The person also said: "<extra>"` | 코드 확인 |

**이후 턴 메시지**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-17 | 턴 메시지 선택(`mod.rs`) | 메시지가 있고 첫 턴이 아니고 이어 갈 기록이 있으면 `follow_up(message)` + `now()`. 메시지가 없고 이어 하기이고 첫 턴이 아니고 기록이 있으면 `continue_prompt` + `now()`. 그 밖은 `brief(kind, cx, message)`이며, API 루프면 그 앞에 `API_BUILDER`(파일·명령 도구 이름, 체크리스트 도구, "`rebuild_check`는 이 루프에 없고 턴마다 검사한다")와 `BLIND_BUILDER`를 붙인다. `now()` = `kind.follow_up_sections(cx)` 각 절 + `pictures_reminder`. 첫 턴이고 `app/Original/MANIFEST.md`가 있으면 끝에 `ORIGINALS_READY`. 세션을 복원했는데 이 컴퓨터에 없을 때 쓸 대체 메시지는 `resumed_elsewhere(brief(...), last_reply, handoff)`. 새 요청이 있으면 아직 전하지 않은 "Just ask" 질문으로 만든 `just_asked`를 메시지(와 대체 메시지) 맨 앞에 붙인다 | 코드 확인 · `first`·`has_history`·`carrying_on` 계산은 루프 소관 |
| R-18 | `follow_up`, `continue_prompt` | `follow_up`: `The person asks: "<message>"` + "`app/`에서 바꾸고 <rebuild_words>, 오류를 고쳐라" + 검사 문장 + "1~3문장으로 무엇이 바뀌었는지". `continue_prompt`: "지난 실행이 끝나기 전에 멈췄다, 만든 것은 `app/`에 있다, 체크리스트와 `core_unknowns_show`로 남은 것을 보고 마친 뒤 <rebuild_words>". 검사 문장은 API 루프면 "Craft Anything checks your build after your turn.", 아니면 "Check it with rebuild_check." game의 `follow_up_sections`: 생성 에셋이 켜져 있으면 `assets_note`, 꺼졌는데 이미 만든 에셋이 있으면 `ASSETS_NOW_OFF`(더 만들지 말고 있는 것은 둘 것) | 코드 확인 |
| R-19 | 작업 중 노트 | 노트가 남아 있으면 빈 노트를 빼고, `just_asked`(노트에 딸린 질문 + 아직 전하지 않은 질문) + `added_prompt`("작업 중 사람이 추가했다" 목록, "지금 반영해 다시 빌드하고 1~3문장") + `pictures_reminder`를 다음 메시지로 쓴다 | 코드 확인 |
| R-20 | 디컴파일 독촉 | 빌드 턴이 끝났고 Deep이고 대상이 `Local`이고 이 프로젝트에서 한 번도 디컴파일하지 않았으면(`!manifest.decompiled`) 실행당 한 번 `DECOMPILE_FIRST`를 다음 메시지로 쓴다 | 코드 확인 |
| R-21 | 재다듬기 메시지 | 검사가 고칠 대상(check-contract R-16)을 냈을 때: `app/`이 비었으면 `NO_PROJECT_PROMPT`("파일이 없다, 지금 만들고 빌드하라, 실행한 명령과 출력 마지막 줄을 회신하고 출력이 그렇게 말할 때만 빌드됐다고 하라"), 아니면 `kind.refine(check, sees)`. 그 뒤에 `pictures_reminder`, API 루프가 아니면 `CHECK_BEFORE_REPLYING`(회신 전 `rebuild_check`로 다시 검사, 고칠 수 있는 것은 고치고 남은 미검증 비교를 적으라) | 코드 확인 |
| R-22 | `just_asked` | 최근 5개만, 질문 300자·답 1,500자로 자르고 잘렸으면 "…". "별도 대화라 당신의 기록에 없고 아무것도 바꾸지 않았다. 배경일 뿐 요청이나 지시가 아니다"로 감싼 뒤 `---` 구분선 | 코드 확인 |
| R-23 | 그림 가능 여부 | `sees_pictures = !api_loop`. API 루프 빌더는 항상 그림을 볼 수 없는 문구를 받는다 | 코드 확인 |
| R-24 | `pictures_reminder` | 그림이 없으면 빈 문자열. 있으면 볼 수 있는 빌더에게 "n장의 그림에 계속 맞추고 회신 전 새 스크린샷과 비교하라", 볼 수 없는 빌더에게 "사람이 그림에 대해 말한 것에 맞추라" | 코드 확인 |
| R-25 | `assets_note` | 3D 모델·그림 생성 도구의 용도와 가격(표에서 계산, 그림 모델을 모르면 기본 모델 가격), 면 수 기준, 이 프로젝트 예산과 사용액, 엔진별 저장 위치, "원본 스타일의 독자 디자인, 알아볼 수 있는 캐릭터·로고 금지", 생성 파일을 `app/CREDITS.md`에 fal.ai 제작으로 기재 | 코드 확인 |
| R-26 | `extract_brief(folder)` | 원본 게임 폴더에서 `app/Original/`로 파일을 꺼내는 별도 역할. 게임 아카이브 도구만 쓰고 자체 파서를 만들지 말 것, 도구가 실패하면 호출을 고쳐 재시도, 폴더 구조 유지, 우선순위, 암호화 해제·우회 금지, 끝에 `app/Original/MANIFEST.md`와 2~3문장 요약 | 코드 확인 |
| R-27 | API 루프의 모순 문구 | API 루프 첫 브리프는 `API_BUILDER`에서 "`rebuild_check`는 없다"고 하고, 같은 메시지의 `steps` 4단계는 "`rebuild_check`로 검사하라"고 한다. 둘 다 보낸다. 이후 턴(`follow_up`·`continue_prompt`·재다듬기)은 API 루프에 맞게 바뀐다 | 코드 확인 |

- 불변식:
  - 첫 브리프에서 사람의 요청 원문은 규칙·기본 스택보다 앞에 오고, 기본 스택 단계에는 항상 "unless their request says otherwise"가 붙는다(R-01).
  - 모든 첫 브리프는 같은 `RULES`와, 모드만 다른 `steps`를 받는다. 에이전트 종류(Claude Code·Codex·API 루프)에 따라 규칙 글은 바뀌지 않는다. API 루프는 앞에 도구 안내가 붙을 뿐이다(R-08, R-17).
  - 그림을 볼 수 없는 빌더에게는 그림을 열라는 지시가 가지 않는다(R-03, R-14, R-24). 단 R-27처럼 `rebuild_check` 지시는 남는다.
- 미결정: 없음.
- 확인 한계: 프롬프트가 실제 에이전트 행동을 얼마나 바꾸는지는 실행하지 않아 모른다. `stacks.toml`이 파싱되는지는 원본 테스트 `the_table_parses_and_covers_every_engine`가 있다는 것까지만 확인했다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/ai/src/rebuild/brief.rs:7-35` `RULES`·`steps` | 규칙 7개·단계 5개 원문 | R-08~R-10 |
| C-02 | `crates/ai/src/rebuild/brief.rs:59-111` `sight`·`SHOTS_*`·`NOISE_*`·`website_from_outside`·`standin_words`·`program_from_outside` | 대상·모드·그림 가능 여부별 증거 안내 원문 | R-03 |
| C-03 | `crates/ai/src/rebuild/brief.rs:113-167` `brief` | 조립 순서, Deep 분기 원문 | R-01~R-05, R-16 |
| C-04 | `crates/ai/src/rebuild/brief.rs:169-260` `start_files_note`·`assets_note`·`DECOMPILE_FIRST`·`decompile_note`·`extract_brief`·`ORIGINALS_READY`·`PRIVATE_USE_NOTE` | 부속 안내 원문 | R-13, R-15, R-20, R-25, R-26 |
| C-05 | `crates/ai/src/rebuild/brief.rs:262-317` `game_steps` | 게임 규칙 분기 | R-12 |
| C-06 | `crates/ai/src/rebuild/brief.rs:319-437` `pictures_note`·`pictures_reminder`·`added_prompt`·`continue_prompt`·`resumed_elsewhere`·`JUST_ASKED_*`·`clipped`·`just_asked`·`next_check`·`follow_up` | 이후 턴 메시지 원문과 길이 상한 | R-14, R-17~R-19, R-22, R-24 |
| C-07 | `crates/ai/src/rebuild/stacks.rs:73-166` `table`·`words`·`get`·`asked_for`·`libraries_for`·`steps` | 표 로딩 실패 처리, 매칭, 치환 | R-05~R-07 |
| C-08 | `crates/ai/src/rebuild/stacks.toml:1-126` | 스택·라이브러리 목록, 각 `asked_by`·`steps` 원문 | R-05~R-07 |
| C-09 | `crates/ai/src/rebuild/kinds/website.rs:24`·`:196-217` `HOW_TO_RUN`·`brief_sections`, `kinds/app.rs:8-9`·`:47-65` `RUNS_BRIEF`·`brief_sections`, `kinds/game.rs:7-8`·`:142-173` `ASSETS_NOW_OFF`·`brief_sections`·`follow_up_sections` | 종류별 절 | R-11, R-18 |
| C-10 | `crates/ai/src/rebuild/kinds/screenshot.rs:15-31` `SCREENSHOT_CONTRACT`·`contract`, `kinds/self_test.rs:12-13` `SELF_TEST_CONTRACT`, `kinds/mechanics.rs:8-9` `MECHANICS_CONTRACT` | 검사가 요구하는 빌드 계약 원문(판정은 check-contract) | R-11, R-12 |
| C-11 | `crates/ai/src/rebuild/mod.rs:876-944` 턴 메시지 선택, `:700-728` 노트, `:528-532`·`:1039-1042` 디컴파일 독촉, `:1088-1096` 재다듬기, `:1523` `NO_PROJECT_PROMPT`, `:1581-1587` `API_BUILDER`·`BLIND_BUILDER`·`CHECK_BEFORE_REPLYING` | 메시지 선택 조건과 루프 쪽 상수 | R-17, R-19~R-21, R-23, R-27 |
| C-12 | `crates/ai/src/rebuild/self_check.rs:59-71` `open_questions`, `:125-131` 열린 질문 줄 | 0번 라운드 보고의 unknown 표시 | R-10 |

### 1.6 수락 사례

출처: 사례별 표기("구현"/"테스트")

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-08~R-10 | website(대상 `Website`, Builder's choice), app(대상 없음, Rust + egui), game(대상 없음, Godot) 각각 Clean room 첫 브리프 | 모두 "you lead the investigation", "Don't repeat a call that already answered", `core_unknown_add`, `core_unknown_edit`, "Missing evidence is never proof", "go through your checklist and core_unknowns_show", "Test it against the original with rebuild_check" 포함. website는 "Work from these pictures and measurements.\n\nMatch it exactly"(빈 줄 하나), Deep은 "(the rendered HTML).\n\nMatch it exactly" | 테스트(`every_kind_leads_tests_its_own_build_and_keeps_its_unknowns`) |
| T-02 | R-09, R-21 | `steps(false)`, `steps(true)`, `CHECK_BEFORE_REPLYING` | 두 `steps` 모두 "another builder turn cannot resolve" 포함, "until it says it would pass" 미포함. `CHECK_BEFORE_REPLYING`은 "unverified comparisons" 포함 | 테스트(`builder_instructions_allow_an_unverified_comparison_to_remain_open`) |
| T-03 | R-06 | `stacks::steps("Python", None)` | `"Use Python. Create the project in app/ and make sure it builds or runs without errors."` | 구현 |
| T-04 | R-05, R-07 | 요청 "Use Next.js, shadcn/ui", 스택 "Next.js + TypeScript" / 같은 요청, 스택 "Unity" | 스택 단계 뒤에 shadcn/ui 단계가 붙음 / 붙지 않음 | 구현 |
| T-05 | R-06 | macOS, 스택 "Unity", 편집기 `/E/Unity` | 단계 안의 `{editor}`→`/E/Unity`, `{player}`→`StandaloneOSX`, `{ext}`→`app` | 구현 |
| T-06 | R-17, R-23, R-27 | API 루프, 첫 턴 | 메시지 = `API_BUILDER` + `BLIND_BUILDER` + 빈 줄 2개 + 브리프. 브리프의 증거 안내는 그림 불가 문구, `steps` 4단계에는 `rebuild_check` 지시가 그대로 있음 | 구현 |
| T-07 | R-16 | 요청 "Clone it", `extra` = " Clone it " | "The person also said" 없음 | 구현 |
| T-08 | R-22 | 질문 7개, 마지막 것의 질문이 301자 | 최근 5개만 들어가고 그 질문은 300자 + "…" | 구현 |
| T-09 | R-21 | 코딩 에이전트, 검사 후 `app/`이 비어 있음, 그림 없음 | 메시지 = `NO_PROJECT_PROMPT` + `CHECK_BEFORE_REPLYING` | 구현 |
| T-10 | R-04, R-05, R-11 | 기존 프로젝트(`own_project()`), app 종류, 편집기 없음 | "What to build: what their request asks of the project in this folder.", 스택 줄 "keep to what the project already uses.", app의 종류 절 없음 | 구현 |
| T-11 | R-14 | website 종류, 그림 2장, 볼 수 있는 빌더 | 그림 안내에 `--screenshot` 문장이 없음(`self_screenshots=false`) | 구현 |
| T-12 | R-07 | `stacks.toml`이 파싱되지 않는다고 가정 | 모든 스택이 일반 문구, `asked_for`·`libraries_for` 결과 없음, 오류 없이 브리프 생성 | 구현 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01~R-05, R-16 | C-03 | 전문 읽음 |
| R-03 | C-02 | |
| R-06, R-07 | C-07, C-08 | 표 전문 읽음 |
| R-08 | C-01 `RULES` (`brief.rs:9`~`:15` 규칙별 한 줄) | overview 8행 요약("요청 우선, `app/`만 수정, 로고·문구 복사 금지, 2~4지선다, 빼기 전에 묻기, 평문 요약")은 구현과 맞는다. 7번째 "개발 서버 금지"는 overview에 없다 |
| R-09 | C-01 `steps` (`brief.rs:29`~`:33` 단계별 한 줄) | |
| R-10 | C-01, C-06 `continue_prompt`·`resumed_elsewhere`, C-12, `crates/engine/src/clean_room.rs:24-26` | 도구 구현은 읽지 않음(선행 스펙 소관) |
| R-11 | C-09, C-10 | |
| R-12, R-13 | C-04, C-05 | |
| R-14, R-15, R-24 | C-04, C-06 | |
| R-17~R-21, R-23, R-27 | C-11 | 루프 본문 중 메시지를 만드는 줄만 읽었다 |
| R-22 | C-06 | |
| R-25, R-26 | C-04 | 가격 계산(`Catalogue`)은 읽지 않음 |
| T-01 | `tests.rs:3655-3675` | 테스트 열람 |
| T-02 | `tests.rs:1538-1546` | 테스트 열람 |
| 문서 차이 | `brief.rs:17-20` | `steps`의 문서 주석이 두 덩어리로 겹쳐 있다("How the builder works…"와 "How to work…"). 동작에는 영향 없음 |

### 2.3 비교·재사용 출처

우리 쪽 대응물: `templates/capability-request-template.md`(작업자 지시문)와 `OSS_ANALYSIS_WORKFLOW.md` 4장(작업 규칙). 대조 결과는 아래 적용 메모에 적는다.

## 적용 메모

우리 스펙 작업 지시(`capability-request-template.md` + 4장)와 대조한 보완 후보다. 원본 동작이 아니다.

| 관련 R-ID | 원본과 다르게 할 점(우리 절차에 들일 것) | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-08 ②, R-15 | 지시문의 "공용 파일은 고치지 마"를 그대로 두되, 메인 세션이 작업자 결과를 받을 때 `git status`로 출력 파일 2개 밖의 변경이 없는지 확인하는 단계를 4장 5번(통합 검토)에 넣는다 | 우리 지시문에도 같은 규칙이 있지만 글로만 있다. 원본도 "규칙은 가드가 아니다"를 겪었다(`docs/pitfalls.md` "A rule in the brief taken for a guard"). 원본은 기록 파일을 엄격히 읽어 위반을 잡는다 | 4장 5번에 점검 한 줄 |
| R-08 ⑤ | 범위를 줄일 때 "이유"만 적게 하지 않고, 사용자 결정이 필요한 축소는 작은 버전을 선택지로 넣어 `handoff.md`에 올리게 한다 | 원본은 조용한 축소를 금지하고 선택지를 강제한다. 우리 4장 3번은 "범위 밖으로 빼는 것도 이유가 있어야"까지만 있다. 병렬 작업자는 사용자에게 직접 물을 수 없으므로 handoff가 대응 경로다 | 지시문 보고 항목에 "사용자 결정이 필요한 축소" 추가 |
| R-09 1), R-10 | 지시문에 "증거가 답하지 못한 질문은 확인 방법과 중요도를 붙여 미결정에 적고, 해결하면 근거 위치와 함께 닫는다"를 넣는다 | 원본은 unknown마다 `probes`·`severity`를 요구하고 해결 시 증거 id를 요구한다. 우리 미결정은 자유 서술이다. overview 후보 표 2행(근거 행 2)과 같은 제안이므로 unknown-ledger 스펙(R-07: 증거 없는 resolved도 허용)과 함께 형식을 확정 | 템플릿 1.4 "미결정" 형식 |
| R-09 1) | "없음은 증거가 아니다, 추정한 것은 표시하라"를 지시문에 직접 둔다 | 4장 3번의 "코드를 못 찾아 결과를 하나 고른 것은 확정형으로 써도 미결정"이 같은 뜻이지만, 지시문에는 없고 4장에만 있다. 원본은 모든 브리프에 같은 문장을 넣는다 | 지시문 본문 한 줄 |
| R-09 4), R-21 | 작업자가 보고 전에 스스로 돌릴 수 있는 기계 점검(`python scripts/check.py <repo>`의 해당 스펙 부분 또는 C-ID 줄 범위 존재 확인)을 지시문에 넣고, "고칠 수 있는 지적은 고치고, 못 고치는 것은 보고에 남겨라"를 붙인다 | 원본은 빌더가 회신 전에 같은 검사를 스스로 돌리고, 고칠 수 없는 비교는 재시도하지 않고 회신에 적게 한다. 우리 지시문은 공용 파일 수정을 막느라 작업자가 `check.py`를 돌리지 않는다 | 지시문에 "출력 파일만 대상으로 점검" 한 줄. `check.py`에 단일 파일 모드가 필요할 수 있음 |
| R-08 ⑦ | 작업자 보고 형식에 "원본과 다르거나 아직 모르는 것"을 따로 둔다 | 원본 회신 규칙은 "무엇을 만들었나 / 무엇이 다르거나 모르나 / 다음 요청 하나"다. 우리 보고는 status·미결정·feature map 보정으로, "모르는 것"은 미결정과 겹치니 새 칸은 필요 없고 "다음 요청 하나"에 해당하는 것만 빠져 있다 | 보고 항목 3번 "다음 스펙 작업에 대한 제안"(선택) |
| R-01, R-17 | 지시문을 코드처럼 고정 블록 + 상황별 블록(모드·대상 종류)으로 나눠 관리한다 | 원본은 규칙·단계가 상수·함수로 고정되어 에이전트마다 같고, 상황 차이는 분기 문구로만 넣는다. 우리 템플릿도 고정 블록 하나지만 레포별 목적(예: overview 1절의 "설계 참고")을 끼울 자리가 없어 이번처럼 지시마다 손으로 덧붙인다 | 템플릿에 "분석 목적" 칸 추가 |
| R-27 | (반면교사) 고정 블록과 상황별 블록이 서로 모순되지 않는지 점검한다 | 원본 API 루프는 "`rebuild_check` 없음"과 "`rebuild_check`로 검사하라"를 한 메시지에 같이 받는다 | 템플릿 수정 시 점검 항목 |
