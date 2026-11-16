---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-15
updated: 2026-11-15
sources:
  - crates/setup/src/skill.md
  - crates/setup/src/skill_recovery.md
  - crates/setup/src/skill.rs
  - crates/setup/src/doctor.rs
  - crates/mcp/src/prompts.rs
  - crates/mcp/src/lib.rs
  - crates/engine/src/clean_room.rs
  - crates/engine/src/tool.rs
  - crates/analysis/src/native.rs
  - crates/disasm/src/program.rs
  - crates/evidence/src/unknown.rs
  - crates/ai/src/prompt.rs
depends:
  - ./investigation-memory.md
status: ready
---

# 조사 방법 지침 (설치 스킬 + MCP instructions + 가이드 프롬프트 6개)

> 에이전트에게 "근거 있는 조사 방법"을 지시문으로 전달하는 세 경로를 정의한다. (1) 코딩 에이전트 앱의 skills 폴더에 설치하는 `craft-anything` 스킬 2개 파일, (2) MCP `initialize` 응답의 `instructions` 문자열, (3) MCP 프롬프트 6개(`prompts/list`·`prompts/get`·인자 완성). 입력은 설치 대상 폴더 또는 프롬프트 이름과 인자이고, 출력은 설치된 파일 또는 렌더된 사용자 메시지 한 개다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 사용자가 `setup`으로 에이전트 앱(Claude Code 등)에 MCP 서버를 등록하면, 같은 계획에 skills 폴더별로 `craft-anything/SKILL.md`와 `craft-anything/references/recovery.md`의 생성·갱신이 들어간다(R-01, R-04, R-05). 계획·적용을 묶는 쪽은 행 13의 범위다.
2. 에이전트 앱은 작업 중 스킬을 불러온다. 스킬은 "도구가 보이면 바로 일하고, 새 질문이면 brief·plan부터 쓰고, 끝날 때 handoff를 쓴다"를 지시한다(R-08 ~ R-13).
3. MCP 서버에 연결하면 `initialize` 응답의 `instructions`가 같은 요지를 한 단락으로 다시 전달한다(R-20).
4. 클라이언트는 `prompts/list`로 프롬프트 6개를 얻고, 사용자가 하나를 고르면 `prompts/get`이 인자를 끼워 넣은 메시지 한 개를 만든다. 모든 프롬프트 끝에는 같은 규칙 6줄이 붙는다(R-21 ~ R-24).
5. 인자 입력 중에는 `completion/complete`가 열린 대상 경로·id·증거 id를 접두사로 걸러 돌려준다(R-30).
6. 이 지시문이 코드로 강제되는 것은 도구 쪽 검사(예: finding의 증거 id 존재)뿐이고, 나머지는 에이전트가 따르는지 검사하지 않는다(R-31).

### 1.2 범위·통합 지점
- 제공: 스킬 파일 구성·식별·설치 상태 판정·설치/제거 규칙, 스킬 본문과 `instructions`와 프롬프트가 "무엇을 하라고 지시하는지"의 규칙화, 프롬프트 6개의 인자·목표·단계, 렌더 형식, 인자 완성.
- 제외:
  - 스킬을 어느 앱의 어느 폴더에 둘지 고르는 코드, MCP 등록 계획·적용·백업(행 13 `agent-drivers-and-setup`). 이 스펙은 `skill.rs`의 함수가 한 폴더에서 하는 일만 정의한다.
  - 내장 에이전트와 에이전트 CLI에 주는 시스템 프롬프트·preamble(`crates/ai/src/prompt.rs`의 `METHOD`·`MEMORY`, 행 14). 같은 방법론을 세 번째·네 번째 경로로 전달하지만 문구가 따로다(R-31 참고).
  - 지시문이 호출하라고 이름을 대는 도구들의 동작. brief·plan·hypothesis·finding·handoff·journal은 [investigation-memory.md](investigation-memory.md), `core_unknown_*`는 행 2 `unknown-ledger`, 빌더에 주는 모드별 문구는 행 8 `builder-brief` R-03·R-09가 정의한다.
  - Clean room 허용 목록과 거부 방식(행 11 `clean-room-mode`).
- 외부 의존·선행 계약: 선행 [investigation-memory.md](investigation-memory.md)의 도구 9개 이름과 `stale_revision` 오류. MCP 클라이언트가 프로토콜 메서드 이름(`prompts/list`, `prompts/get`, `completion/complete`)을 보낸다는 가정.
- 소유 상태·부작용: 스킬 설치는 파일 시스템에만 쓴다(`SKILL.md`, `references/recovery.md`, 그리고 기존 파일이 있으면 `<파일>.craft-anything.backup`). 프롬프트 6개와 규칙 문구는 컴파일된 상수라서 서버가 상태를 갖지 않고, 인자 완성만 세션을 읽는다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| 스킬 파일 | `SKILL.md`(본문 `skill.md`), `references/recovery.md`(본문 `skill_recovery.md`) | 폴더 이름 `craft-anything`. 두 본문은 바이너리에 컴파일된 상수다. |
| `SkillState` | enum `missing` / `current` / `outdated` / `foreign` (snake_case로 직렬화) | 한 skills 폴더에 설치된 상태. |
| `SkillFileAction` | `{path, action: "create"\|"update"\|"already_current", backup?: path}` | 설치 계획 한 줄. `backup`은 `update`일 때만 있다. |
| `skill::inspect(dir)` | skills 폴더 → `SkillState` | R-03. |
| `skill::plan(dir)` | skills 폴더 → `SkillFileAction` 2개 | 아무것도 쓰지 않는다. |
| `skill::install(dir)` | skills 폴더 → 실제로 쓴 경로 목록 또는 `ToolError` | 이미 같은 파일은 건너뛰어 목록에 없다. R-05. |
| `skill::uninstall(dir)` | skills 폴더 → 지운 경로 목록 | R-06. |
| `initialize` 응답의 `instructions` | string | R-20. 같은 응답의 `capabilities`는 `prompts.listChanged: false`, `completions: {}`를 선언한다. |
| `prompts/list` | `{}` → `{prompts: [{name, title, description, arguments: [{name, description, required}]}]}` | 6개. 서버 상태·모드와 무관한 고정 목록. |
| `prompts/get` | `{name, arguments?: map<string,string>}` → `{description, messages: [{role: "user", content: {type: "text", text}}]}` | 문자열이 아닌 인자 값은 무시된다. R-22. |
| 프롬프트 인자 | `name`, `description`, `required` | 목록은 C-02 표(코드)가 기준. |
| `completion/complete` | `{ref: {type: "ref/prompt", name}, argument: {name, value}}` → `{completion: {values, total, hasMore}}` | R-30. |

프롬프트 6개의 이름·필수 인자: `core_feature_explain`(`what`), `app_graphs_compare`(`older_path`, `newer_path`), `app_rebuild_claim_check`(`goal`), `native_crash_explain`(`symptom`), `core_unknowns_review`(`scope`), `runtime_run_plan`(`question`, `program`, `folder`). 선택 인자와 문구는 C-02.

### 1.4 행동 규칙과 남은 질문

규칙의 "지시한다"는 말은 해당 문구가 원문에 있다는 뜻이다(원문 위치는 C-ID). 에이전트가 따르는지는 이 표의 검증 대상이 아니다(R-31).

**설치된 스킬 파일**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 스킬 파일 구성 | 관리 대상은 정확히 2개다: `<skills 폴더>/craft-anything/SKILL.md`(`skill.md` 본문)와 `<skills 폴더>/craft-anything/references/recovery.md`(`skill_recovery.md` 본문). | 코드 확인 |
| R-02 | "우리 것" 식별 | `SKILL.md`는 줄바꿈 `\r\n`을 `\n`으로 바꾼 텍스트가 정확히 `---\nname: craft-anything\n`로 시작하면 우리 것이다. `references/recovery.md`는 `<!-- craft-anything skill reference -->`로 시작하면 우리 것이다(제거할 때만 쓴다). | 코드 확인 |
| R-03 | `inspect` | `SKILL.md`를 읽을 수 없으면 `missing`. 읽었는데 R-02 접두사가 아니면 `foreign`. 우리 것이면서 두 파일이 모두 번들 본문과 바이트 단위로 같을 때만 `current`(두 번째 파일이 없거나 다르면 `outdated`). `current` 판정은 본문 전체 비교이고 `metadata.version` 값은 보지 않는다. | 코드 확인 |
| R-04 | `plan` | 파일마다 읽기 실패 → `create`, 내용이 같음 → `already_current`, 다름 → `update`(+ `backup` 경로 `<파일>.craft-anything.backup`). 파일은 쓰지 않는다. `foreign` 여부는 보지 않는다. | 코드 확인 |
| R-05 | `install` | 파일마다: 이미 같으면 건너뜀. 기존 파일이 있으면 `backup_once`로 `.craft-anything.backup`을 만든다(백업이 이미 있으면 덮어쓰지 않고 그대로 둔다). 새 내용을 비공개 권한으로 원자적으로 쓰고, 다시 읽어 바이트가 같은지 확인한다(다르면 `file_error` "<경로> did not read back correctly"). 어느 파일에서든 실패하면 이번 호출에서 쓴 파일을 역순으로 되돌린다(기존 내용을 다시 쓰거나, 새로 만든 파일은 삭제). 되돌리기 실패는 경고 로그만 남긴다. 반환은 실제로 쓴 경로 목록이다. `foreign` 파일이 같은 경로에 있어도 검사 없이 백업한 뒤 덮어쓴다. | 코드 확인 |
| R-06 | `uninstall` | `SKILL.md`는 R-02 접두사일 때만, `references/recovery.md`는 마커로 시작할 때만 지운다. 이어서 `references/`와 `craft-anything/` 폴더를 비어 있을 때만 지운다(비어 있지 않으면 남는다). 사용자가 같은 폴더에 둔 다른 파일은 남는다. 반환은 지운 경로(파일·폴더) 목록이다. | 코드 확인 |
| R-07 | 버전 값 | `SKILL_VERSION = "2"`와 `skill.md` 머리의 `metadata.version: "2"`는 같아야 한다(테스트가 확인). `inspect`·`plan`·`install`은 이 값을 읽지 않는다. 구버전 판정은 R-03의 본문 비교뿐이다. `foreign`은 `doctor`가 경고(`Another skill uses the craft-anything folder name.`)만 하고 고치는 명령을 제안하지 않는다. | 코드 확인 |

**스킬 본문이 지시하는 것** (원문: C-03 ~ C-08)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | 스킬을 쓸 때 | 질문의 답이 "만들어져 배포된 것"(실행 파일, 라이브러리, 앱 번들, APK, Electron 앱, WebAssembly, 펌웨어, 크래시 덤프, 네트워크 캡처)에 달려 있을 때 쓰라고 한다. 소스 코드가 있고 질문이 소스에 관한 것이면 스킬을 쓰지 말고 소스를 읽으라고 한다. | 코드 확인 |
| R-09 | `craft-anything` 도구가 이미 도구 목록에 있음 | setup·doctor를 먼저 돌리지 말고 바로 일하라고 지시한다. 지시문보다 실시간 도구 목록과 스키마를 믿으라고 한다(서버가 더 새롭거나 오래됐을 수 있음). | 코드 확인 |
| R-10 | 도구가 없거나 시작에 실패함 | `craft-anything-cli doctor` → `craft-anything-cli setup --dry-run`을 돌리고 계획을 사용자에게 보여 준 뒤에만 적용하라고 한다. 적용 후에는 사용자가 앱을 재시작·재연결해야 한다고 한다. 이미 모든 도구를 나열하는 항목(`args`가 `--all-tools`로 끝남)에는 `setup --yes`나 `--client`를 돌리지 말라고 한다(setup이 일반 `mcp` 명령을 써서 `--all-tools`가 빠지고 작은 core 도구 집합으로 돌아가기 때문). `doctor`가 같은 항목을 "다른 사본·모양"이라며 그 명령을 권해도 경고가 이유가 되지 않는다고 한다. 클라이언트 추가는 `--all-tools`를 넣어 손으로 쓰라고 한다. | 코드 확인 |
| R-11 | 도구 집합 | 처음에는 작은 core 집합만 보인다고 알리고, `list_toolsets`로 다른 집합을 보고 `enable_toolset`으로 켜라고 한다(native, Android, Apple, web, runtime 등). | 코드 확인 |
| R-12 | Clean room(Deep 꺼짐, 기본) | 대상 안쪽은 읽지 않고, 밖에서 보는 도구만 목록에 나오며 나머지는 `details.reason` = `clean_room`으로 거부된다고 알린다. 그 질문에 Deep 모드가 필요하다고 사용자에게 말하라고 한다(앱의 스위치, `settings_set deep_mode true`, 서버를 `--deep`으로 시작). 돌아가서 우회하지 말라고 한다. | 코드 확인 |
| R-13 | 작업 기억 루프 | 번호 순서로 지시한다. (1) 시작·재개: `core_investigation_show`를 먼저 호출, handoff가 있으면 처음부터 다시 하지 말고 그 handoff와 plan에서 이어간다. `core_session_show`로 열린 것을 본다. (2) 새 질문: 분석 호출 전에 `core_brief_write`(질문, 이유, 대상, "프로그램을 실행하지 말 것" 같은 제약, 끝난 답의 모양)와 `core_plan_update`(짧은 번호 단계, 각 `todo`/`doing`/`done`/`blocked`와 이유). (3) 도구 호출 묶음마다 plan 단계 상태를 갱신. 검증할 주장이 생기면 확인/반증할 예측과 함께 `core_hypothesis_record`, 증거가 오면 `core_hypothesis_update`(supported/refuted/abandoned)와 증거 id. (4) 확정되면 진술과 증거 id 1개 이상으로 `core_finding_record`. 보고서는 채팅 글이 아니라 finding에서 만든다. (5) 매 턴 끝에 `core_handoff_write`: 현재 위치, 다음 할 일, 피할 함정(막다른 길, 느린 도구, 오해를 부르는 문자열). "낯선 사람이 이어받는다고 생각하고" 쓴다. (6) 이전에 무엇을 시도했는지 알아야 하면 `core_journal_read`. | 코드 확인 |
| R-14 | 방법 6항목 | (a) 관찰/도출/추론을 구분해 각 주장에 표기한다(관찰 = 바이트·캡처에서 직접, 도출 = 관찰에서 계산한 것(제어 흐름 그래프, 호출 그래프), 추론 = 판단(이름, 의도, 모델의 해석)). (b) 모든 주장에 증거 id(`ev_…`)를 인용한다. 증거 id가 없는 주장은 가설이다. (c) 부재는 증거가 아니다: "문자열 없음"·"호출자 없음"은 검색한 범위만 덮는다. 검색 경계와 도구가 보고한 coverage를 적고, 중요한데 열려 있는 것은 `core_unknown_add`로 기록한다. (d) 예측 후 검증: 가설을 시험하는 도구를 돌리기 전에 기대하는 결과를 적고, 결과가 다르면 결과를 둘러대지 말고 가설을 고친다. (e) 요약 먼저 후 페이지: 큰 결과는 요약과 증거 id로 오니 `offset`/`limit`으로 쪽을 요청하고, 이미 성공했거나 거부된 동일 호출을 반복하지 않는다. (f) 파일 이름이 아니라 형식을 본다: 파서가 파일 종류를 알려 주게 한다. | 코드 확인 |
| R-15 | 대상 종류별 첫 단계 | 7개 행의 표로 지시한다(원문 표가 기준, C-05). 요지: 네이티브·Electron·APK 등 `core_target_open`으로 대상을 연 뒤 종류별 도구 집합, 웹페이지·Electron 창은 browser 집합(관찰 전용), 두 버전은 둘 다 열고 application 집합의 비교 도구. 사용자가 "my app"처럼 이름 없이 말하면 어느 것인지 묻고, 예시 파일로 추측하지 말라고 한다. | 코드 확인 |
| R-16 | 동의와 안전 | 대상의 코드를 실행하거나 연결된 기기를 바꾸는 도구는 사용자의 명시적 OK가 필요하다. 호출이 `consent_required`를 돌려주면 무엇을 할지 설명하고 묻되, 우회할 방법을 찾지 말라고 한다. 정적 분석은 대상을 실행하지 않으므로 정적 증거만으로 런타임 동작을 주장하지 말고 추론이라고 표기한다. 비밀·쿠키·개인정보를 노트·finding·handoff에 넣지 않는다. | 코드 확인 |
| R-17 | 오류 코드별 대응 | 5개 코드를 지시한다. `not_found`: 대상을 먼저 열거나 경로·이름 확인. `feature_missing`/`engine_missing`: remediation을 읽기(필요한 도구 집합·엔진·설정을 알려 줌). `over_limit`: 결과가 너무 커서 보내지 못했으니 쪽으로 나누거나 증거 id로 `evidence://<id>` 리소스를 읽기. `stale_revision`: `core_investigation_show`로 다시 읽고 병합해 재시도. `consent_required`: 사용자에게 묻기. | 코드 확인 |
| R-18 | 끝내기 전 점검 | 각 plan 단계를 done 또는 blocked로 표시하고, 답의 모든 결론이 기록된 finding과 일치하는지 확인하고, 아직 모르는 것을 나열하고, handoff를 쓰라고 지시한다. | 코드 확인 |
| R-19 | recovery 참고 파일 | 증상 5개와 대응을 표로 준다(앱에 도구가 없음 → `doctor`, 등록이 없거나 낡았으면 `setup --client <id> --dry-run` → 계획 제시 → 사용자 동의 후 `--yes`; 등록은 맞는데 도구가 없음 → 앱 재시작·재연결; 셸에서 `craft-anything-cli`를 못 찾음 → `PATH`에 없을 뿐 등록은 절대 경로라 앱은 될 수 있음; 앱이 도구마다 승인을 물음 → 앱 자체 정책이니 사용자 허락 없이 바꾸지 않음; 엔진이 없다는 도구 오류 → remediation을 따름). setup은 `craft-anything` 항목만 더하거나 고치고, 주석과 다른 서버를 보존하고, 원본의 `.craft-anything.backup`을 먼저 쓰고(기존 백업은 덮어쓰지 않음), 결과가 다시 읽히지 않으면 원본으로 되돌리고, `uninstall`은 Craft Anything가 만든 항목·스킬 파일만 지운다고 설명한다. 앱이 연결되지 않았을 때의 대안으로 모든 도구가 CLI 하위 명령이라고 알리고 예시 2개(`triage`, `core-target-open --json '{"path": …}'`)를 준다. | 코드 확인 |

**MCP instructions와 프롬프트**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | `initialize` | 응답의 `instructions`(C-09)가 R-08 ~ R-16의 요지를 한 단락으로 준다: `core_investigation_show`·`core_session_show`로 시작; `core_target_open`(절대 경로)으로 연 뒤 집중된 도구, 요약 먼저·쪽 단위; 처음엔 Essentials 도구 집합만 보이니 `list_toolsets`·`enable_toolset`; 작업 기억 도구 목록과 "턴이 끝날 때마다 handoff"; 증거 id 인용·관찰과 추론 구분·열린 질문은 unknown으로; 코드 실행·기기 변경은 사용자 승인; Clean room이면 밖에서 보는 도구만 나열되고 거부된 도구는 Deep 모드 켜는 법을 알려 준다. | 코드 확인 |
| R-21 | `prompts/list` | 항상 같은 6개를 `PROMPTS` 선언 순서(`core_feature_explain`, `app_graphs_compare`, `app_rebuild_claim_check`, `native_crash_explain`, `core_unknowns_review`, `runtime_run_plan`)로 준다. 모드(Clean room/Deep), 열린 대상, 켜진 도구 집합과 무관하다. | 코드 확인 |
| R-22 | `prompts/get` 검증 | 처음에 `arguments` 객체에서 값이 문자열인 항목만 모은다(숫자·객체·null 값은 없는 것으로 친다). 이름이 없으면 오류 코드 -32602 메시지 `No prompt named <name>`. 필수 인자가 없거나 trim하면 빈 문자열이면 -32602 `Missing required argument <인자>`(선언 순서로 처음 걸린 하나만). 선택 인자는 비어도 된다. | 코드 확인 |
| R-23 | `prompts/get` 렌더 | 하나의 `user` 텍스트 메시지를 만든다. 형식은 C-02 `render`: 제목 줄, `**Objective:**`, 값이 비어 있지 않은 선언된 인자만 선언 순서대로 `- 이름: 값(trim)`인 `**Inputs:**`(없으면 절 자체를 생략), 번호 붙은 `**Steps:**`, `**Rules:**`. 선언에 없는 인자 이름은 무시된다. 응답의 `description`은 프롬프트 설명이다. 인자 값은 escape하지 않고 그대로 들어간다. | 코드 확인 |
| R-24 | 모든 프롬프트의 규칙 6줄 | `**Rules:**`에 항상 같은 6줄(`DISCIPLINE`)이 붙는다. (1) 작업 기억을 최신으로: `core_investigation_show` 먼저, 새 질문엔 분석 전에 brief·plan, 주장이 바뀌면 가설 도구, finding은 증거 id와 함께만, 멈추기 전에 handoff. (2) 관찰/도출/추론을 구분하고 모든 주장에 증거 id. (3) 부재는 증거가 아니다: 검색에서 못 찾으면 무엇을 얼마나 검색했는지 말한다. (4) 보기 전에 예측하고 증거와 대조한다. (5) 요약 먼저, 상세는 `offset`/`limit`. (6) 열린 질문은 추측하지 말고 `core_unknown_add`로 기록. | 코드 확인 |
| R-25 | `core_feature_explain` | 목표: 기능이 시작되는 곳(UI 동작·명령·진입점)에서 만지는 데이터를 거쳐 결과까지를 증거와 함께 설명. 단계 6개: 대상 열기(이미 열려 있으면 생략, `core_session_show` 확인) → brief(기능 질문과 완결된 답의 모양)와 짧은 plan → 진입점 찾기(기능을 가리키는 문자열·심볼·라우트·IPC 채널) → 경로 따라가기(호출자·피호출자, 데이터 흐름, 파일·네트워크 끝점) → 주장마다 예측이 달린 가설로 기록·시험 후 증거 id가 달린 finding → 요약(단계별 경로, 단계별 증거, 남은 unknown). | 코드 확인 |
| R-26 | `app_graphs_compare` | 목표: 두 버전의 행동 차이와 각 차이의 확신 정도. 핵심 지시: "추가됐다/삭제됐다"는 양쪽을 모두 완전히 덮었을 때만 말한다. 차이마다 양쪽 증거 id를 단 finding. 비교하지 못한 것과 이유를 나열. | 코드 확인 |
| R-27 | `app_rebuild_claim_check` | 목표: 재구현이 원본과 맞는지 기대 동작별로 판정하고 입증되지 않은 것을 말한다. 단계: investigation finding을 읽어 맞춰야 할 행동 목록으로 삼음 → finding마다 그것을 정의하는 증거가 달린 검사 가능한 기대로 바꿈 → 재구현에 대해 검사해 met / not met / not yet testable로 표시 → 기대마다 finding, 틈마다 unknown. | 코드 확인 |
| R-28 | `native_crash_explain` | 목표: 크래시로 이어지는 코드 경로와 발동 조건. 단계: 대상을 열고 크래시 신호를 만들거나 처리하는 코드(문자열, 핸들러, assert) 찾기 → 발동 조건 가설을 예측과 함께 쓰기 → 크래시 지점에서 호출자를 거슬러 이름 붙일 수 있는 입력까지 걷기 → 정적 증거로 결정되지 않을 때만, 그리고 사용자 동의가 있을 때만 프로그램을 실행 → 경로·발동 조건·고리마다의 증거를 보고. | 코드 확인 |
| R-29 | `core_unknowns_review`, `runtime_run_plan` | `core_unknowns_review` 목표: 범위 안 모든 unknown을 증거와 함께 해결, 다음 확인 방법과 함께 좁힘, 또는 이유와 함께 blocked로 남김. 단계: `core_unknowns_show`로 범위 안 unknown과 현재 finding 읽기 → 각각 무엇이 증거가 될지·도구로 만들 수 있는지 서술 → 가장 싼 결정적 확인을 돌려 결과로 unknown 갱신 → "증거 id 없이는 resolved로 표시하지 않는다". `runtime_run_plan` 목표: 질문에 답하는 가장 작은 실행을 한계와 함께 설계하되 실행 전에. 단계: 정적 증거가 이미 답하면 거기서 멈춤 → 계획(입력, 시간·출력 한계, 관찰할 것, 잘못될 수 있는 것) 작성 → 사용자에게 계획을 보여 줌(실행에는 명시 동의 필요) → 실행 후 일어난 일을 예측과 비교하고 캡처 증거 id로 finding 기록. | 코드 확인 |
| R-30 | `completion/complete` | `ref.type`이 `ref/prompt`가 아니거나, 프롬프트 이름이 없거나, 그 프롬프트에 없는 인자 이름이면 `{values: [], total: 0, hasMore: false}`. 아니면 인자 이름으로 후보를 정한다: `path`·`older_path`·`newer_path`·`original_path`·`program` = 열린 대상들의 경로 + 설정의 최근 경로 목록; `target_id` = 열린 대상 id; `unknown` = 기록된 unknown id; `function` = 활성 대상의 이름표(annotation) 값 중 이름(주소는 아님); `evidence` 또는 `_evidence`로 끝나는 이름 = 원장 모든 증거 id; 그 밖의 인자(`what`, `goal`, `symptom`, `scope`, `question`, `folder`)는 후보 없음. 입력값을 소문자로 바꿔 후보의 소문자 접두사와 비교해 거르고, 중복을 없애 문자열 정렬 순으로 둔다. `total`은 자르기 전 개수, 값은 앞 100개, `hasMore`는 `total > 100`. 대상이 없으면 `function` 후보는 비어 있다. | 코드 확인 |
| R-31 | 지시와 강제의 경계 | 위 R-08 ~ R-29는 텍스트이고 에이전트가 따르는지를 검사하는 코드는 없다. 지시와 같은 내용이 코드로 강제되는 곳은 도구 쪽에 따로 있다. (a) "증거 id 없는 finding 금지" = 증거 id가 없거나 원장에 없으면 기록 거부([investigation-memory.md](investigation-memory.md) R-11, R-16). 그러나 증거 내용이 진술을 뒷받침하는지는 보지 않는다. (b) "증거 id 없이는 unknown을 resolved로 하지 않는다" = 쓰기 시점에는 강제하지 않고(`Unknown::resolution_is_valid`는 정의만 있고 호출처가 없음), `core_unknown_verify`로 사후 점검할 수 있을 뿐이다. (c) "부재는 증거가 아니다" = 분석 도구가 결과에 같은 취지의 한계 문구를 직접 넣는다(C-10). (d) "동의 없이 실행하지 않는다" = 엔진이 `consent_required`로 막는다(`tool.rs`의 `Effects::needs_consent`). (e) Clean room 안내 = 엔진이 거부한다(행 11). 세 번째·네 번째 경로(`crates/ai/src/prompt.rs`)는 같은 방법을 다른 문구로 준다: 예를 들어 `core_finding_edit`·`based_on_revision` 사용을 지시하지만 스킬·MCP 프롬프트는 `core_finding_edit`을 언급하지 않는다. | 코드 확인 |

- 불변식: 6개 프롬프트의 `**Rules:**` 절은 항상 동일하다(R-24). 같은 바이너리가 내놓는 스킬 본문과 `SKILL_VERSION`의 값은 같다(테스트로 확인).
- 미결정: 없음.
- 확인 한계: 정적 읽기만 했다. 스킬·프롬프트를 받은 실제 에이전트(Claude Code 등)가 지시를 어느 정도 따르는지, 에이전트 앱이 skills 폴더의 `SKILL.md`를 언제 불러오는지는 외부 시스템의 동작이라 확인하지 않았다(`미확인`). `skill.rs`가 쓰는 skills 폴더 경로 선택과 MCP 등록은 행 13이다.

### 1.5 필수 코드 참조

원문은 지시문이 곧 사양이므로 C-ID로 넘긴다. 규칙 표는 의미 요약이고 문구가 필요하면 원문을 쓴다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/setup/src/skill.rs:7-21`, `:35-45` `SKILL_DIR`·`SKILL_VERSION`·`SKILL_PREFIX`·`REFERENCE_MARKER`·`SKILL_MD`·`RECOVERY_MD`·`files`·`inspect` | 상수, 관리 파일 2개, 상태 판정 | R-01 ~ R-03, R-07 |
| C-02 | `crates/mcp/src/prompts.rs:7-38`, `:40-153` `Arg`·`PromptDef`·`req`·`opt`·`DISCIPLINE`·`PROMPTS`, `:155-203` `find`·`list_json`·`render` | 프롬프트 6개의 이름·제목·설명·인자(이름·설명·필수)·목표·단계 원문, 규칙 6줄 원문, 렌더 형식 | R-21 ~ R-29 |
| C-03 | `crates/setup/src/skill.md:1-57` | 머리(name·description·`metadata.version`), 사용 시점, 연결·Clean room 지시, 작업 기억 루프 6단계 원문 | R-08 ~ R-13 |
| C-04 | `crates/setup/src/skill.md:59-73` | 방법 6항목 원문 | R-14 |
| C-05 | `crates/setup/src/skill.md:75-87` | 대상 종류별 첫 단계 표 원문 | R-15 |
| C-06 | `crates/setup/src/skill.md:89-95` | 동의·안전 원문 | R-16 |
| C-07 | `crates/setup/src/skill.md:97-108` | 오류 코드 표와 끝내기 전 점검 원문 | R-17, R-18 |
| C-08 | `crates/setup/src/skill_recovery.md:1-19` | recovery 참고 파일 전문 | R-19 |
| C-09 | `crates/mcp/src/lib.rs:46-52` `INSTRUCTIONS`, `:315-322` 메서드 분기, `:338-346` `initialize`의 capabilities | MCP instructions 원문, 프롬프트 관련 메서드 이름, 선언한 capabilities | R-20, R-21 |
| C-10 | `crates/analysis/src/native.rs:683`, `:783`, `:1021`; `crates/disasm/src/program.rs:534`; `crates/engine/src/tools/byte_search.rs:232` | 도구가 결과에 직접 넣는 "absence is not proof" 한계 문구의 위치 | R-31 |
| C-11 | `crates/mcp/src/lib.rs:686-733` `prompts_get`·`complete` | 인자 수집(문자열만), 오류 코드 -32602, 인자별 후보 출처, 접두사 필터, 상한 100 | R-22, R-30 |
| C-12 | `crates/setup/src/skill.rs:57-142` `backup_path`·`plan`·`install`·`rollback`·`uninstall`, `crates/platform/src/fs.rs:152-165` `backup_once` | 계획·설치·되돌리기·제거 절차, 백업을 한 번만 만드는 규칙 | R-04 ~ R-06 |

### 1.6 수락 사례
출처: 구현에서 도출. 사례 T-01·T-03·T-04는 원본 테스트(`prompts.rs`·`skill.rs`의 `tests`)와 같은 경계를 확인한다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-21 ~ R-24 | `core_feature_explain`을 인자 없이, `what`을 공백으로, `what` = "saving files"로 차례로 `prompts/get`. 없는 이름 `nope` | 처음 둘은 -32602 `Missing required argument what`, 셋째는 성공하며 메시지 텍스트에 "saving files"와 `core_handoff_write`가 있고 `**Inputs:**`에 `- what: saving files`, 없는 이름은 -32602 `No prompt named nope` |
| T-02 | R-22 | `app_graphs_compare`에 `older_path`는 문자열, `newer_path`는 숫자 `3` | `newer_path`가 없는 것으로 치므로 -32602 `Missing required argument newer_path` |
| T-03 | R-03, R-05 | 빈 폴더 `inspect` → `missing`. `install` → 2개 경로. 다시 `inspect` → `current`. 다시 `install` → 빈 목록. `SKILL.md`를 `---\nname: craft-anything\nold\n`으로 바꾸고 `inspect` | `outdated`. `install`은 1개만 쓰고 `SKILL.md.craft-anything.backup`이 생긴다 |
| T-04 | R-02, R-06 | `SKILL.md`가 `---\nname: something-else\n---\n`인 폴더에서 `inspect`와 `uninstall` | `foreign`, 지운 경로 없음, 파일 그대로 |
| T-05 | R-06 | 설치 후 같은 폴더에 `notes.md`를 두고 `uninstall` | `SKILL.md`는 지워지고 `notes.md`와 `craft-anything/` 폴더는 남는다 |
| T-06 | R-30 | 대상 하나가 `/a/prog`로 열려 있을 때 `app_graphs_compare`의 `older_path`에 `/A` 입력 완성 | 값 `["/a/prog"]`, `total` 1, `hasMore` false(소문자 접두사 비교) |
| T-07 | R-30 | `core_feature_explain`의 `what` 인자 완성 | `{values: [], total: 0, hasMore: false}` |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad71 `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01 | `skill.rs:15-21` `files` | 전문 읽음 |
| R-02, R-06 | `skill.rs:12-13`, `:39`, `:123-142` `uninstall` | 전문 읽음 |
| R-03 | `skill.rs:35-45` `inspect` | 문서 차이: `skill.rs:9` 주석 "Bumped whenever the skill text changes"와 달리 구버전 판정은 `SKILL_VERSION`이 아니라 본문 바이트 비교(`:41`). 버전은 테스트 `content_is_ours_and_teaches_the_loop`(`:152`)에서만 `metadata.version`과 비교된다 |
| R-04 | `skill.rs:63-75` `plan` | 전문 읽음. `foreign`을 보지 않는 것은 `grep -n Foreign crates/setup/src/*.rs` 결과가 `doctor.rs:161`과 `skill.rs`뿐임을 확인 |
| R-05 | C-12, `crates/platform/src/fs.rs:152-165` | `backup_once`는 대상 백업이 있으면 쓰지 않음(`:153-155`). `write_atomic_private`의 세부(임시 파일 방식 등)는 읽지 않았고 "원자적·비공개"는 함수 이름과 호출 맥락에 따른 해석이다(추론) |
| R-07 | `skill.rs:9-10`, `:152`, `doctor.rs:157-163` | `grep -rn SKILL_VERSION crates apps` 결과 `skill.rs`뿐 |
| R-08 ~ R-18 | C-03 ~ C-07 | 전문 읽음. 규칙은 문구의 의미 요약이다 |
| R-12 | C-03(`skill.md:33-36`), `clean_room.rs:140-141` `REASON`·`REMEDIATION`, `:149-151` `refusal` | 문서와 구현은 일치: 거부의 `details.reason`이 `clean_room`이고 remediation에 `settings_set deep_mode true`와 `--deep`이 있다. 실제 거부 동작은 [clean-room-mode.md](clean-room-mode.md)가 정의한다 |
| R-15 | C-05 | 문서와 구현의 차이: 표의 첫 단계 `core_target_open`은 Clean room 허용 목록에 없어(`clean_room.rs:14-133`에 없음, 테스트 `:181`이 거부를 확인) Clean room에서는 표의 첫 단계가 거부된다. 스킬은 Clean room 절(`skill.md:33-36`)에서 "Deep이 필요하다고 말하라"고 하지만 이 표에는 모드 구분이 없다 |
| R-19 | C-08 | 전문 읽음. "setup은 원본을 백업하고 되돌린다"는 서술은 문서 주장이고 구현은 행 13 범위라 확인하지 않았다(`미확인`) |
| R-20 | C-09 | 전문 읽음. 표기 차이: `skill.md:31`은 "small core toolset", `INSTRUCTIONS`는 "Essentials toolset"이고 같은 집합(`tool.rs:163` `Toolset::Core` 제목 "Essentials") |
| R-21 | `prompts.rs:159-172` `list_json`, `lib.rs:315`, `:340` | `list_json`은 인자 없이 호출되어 상태를 읽지 않음. 문서와 구현의 차이: 모드와 무관하게 6개가 나오지만 대상을 여는 첫 단계를 가진 프롬프트(`core_feature_explain`은 `core_target_open`을 이름으로 지시, `app_graphs_compare`·`native_crash_explain`은 "Open the target(s)")는 Clean room에서 `core_target_open`이 거부되므로 그대로 따를 수 없다. 프롬프트 본문에는 Clean room 분기가 없다 |
| R-22 | C-11(`lib.rs:688-698`), `prompts.rs:175-181` | 전문 읽음. 오류 코드 -32602는 `.map_err(\|m\| (-32602, m))` |
| R-23 | `prompts.rs:182-203` | 전문 읽음. T-01 ~ T-02 |
| R-24 | `prompts.rs:30-38`, `:195-198` | 전문 읽음 |
| R-25 ~ R-29 | `prompts.rs:40-153` | 전문 읽음. 문서와 구현의 차이: `function` 인자 설명은 "A function name or address"이지만 완성 후보는 이름 값만(`lib.rs:724`) |
| R-30 | C-11(`lib.rs:701-733`) | 전문 읽음. T-06·T-07은 구현에서 도출했고 실행하지 않았다 |
| R-31 | (a) investigation-memory R-11·R-16; (b) `unknown.rs:86-89`, [unknown-ledger.md](unknown-ledger.md) R-07·R-11; (c) C-10; (d) `tool.rs:56-58`; (e) `clean_room.rs:136-138` | (b)의 "호출처 없음"은 unknown-ledger 2.1의 `grep -rn resolution_is_valid crates apps` 기록을 따랐고 이번에 다시 실행하지는 않았다. 에이전트 쪽 준수 여부는 `미확인` |
| T-01 ~ T-07 | `prompts.rs:205-222`, `skill.rs:144-202`, `lib.rs:701-733` | 원본 테스트 열람은 T-01·T-03·T-04·T-05의 기대값 확인에 한정. T-02·T-06·T-07은 구현에서 도출 |

### 2.2 코드 읽는 순서
`skill.md` 전문(스킬이 모델에게 말하는 방법론의 원문) → `prompts.rs`의 `DISCIPLINE`·`PromptDef`·`render`(같은 방법론이 프롬프트로 나올 때의 모양) → `mcp/src/lib.rs`의 `INSTRUCTIONS`와 `prompts_get`·`complete` → `skill.rs`의 `inspect`·`install`. 원본의 전략은 "방법론 한 벌을 세 경로에 다른 길이로 복제"하는 것이다(스킬 108줄, instructions 7줄, 프롬프트마다 규칙 6줄). 복제본들 사이에 단일 원천은 없고 `include_str!`로 스킬만 한 파일을 쓴다.

## 적용 메모

원본의 미결정을 여기서 해소한 것은 없다. 아래는 우리 절차(7·8장, 스펙 작성자/구현자 분리)와 맞대어 본 보완 후보다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-14(c), R-31(c) | **확정(수정 포함).** 7장에 "없다·호출처 없다·구현이 없다 같은 부재 주장은 검색 범위(명령·경로·키워드)와 함께 적는다"를 추가한다. overview 후보 표 2행 "7장에 '없음' 규칙 추가"는 맞지만, 원본이 지침만이 아니라 도구 출력의 한계 문구와 짝을 이룬다는 점(C-10)을 반영해 두 곳에 둔다: 7장 규칙과 스펙 템플릿 2.1 열("확인 방법·한계")의 필수 기재 | 원본은 지침(`skill.md:65-67`)만 믿지 않고 분석기 출력에도 같은 문구를 박는다(추론: 에이전트가 지침을 놓쳐도 결과에서 마주치게 하려는 구조). 우리 스펙은 이미 unknown-ledger 2.1처럼 `grep -rn ...`을 적는 경우가 있으나 규칙이 아니라 습관이다 | 7장 한 줄, `capability-spec-template.md` 2.1 주석 한 줄. `check.py`가 "없다"를 판별하기는 어려워 사람 검토 항목으로 남는다 |
| R-13, R-18 | 세션 마무리·스펙 완료 점검에 "보고한 결론이 기록된 R-ID·finding과 일치하는가"를 명시한다 | 원본의 끝내기 점검(`skill.md:107-108`)은 결론 ↔ 기록 일치를 요구한다. 우리 4장 4·5번은 근거 존재·통합은 보지만 "대화 보고의 결론이 스펙 본문과 같은가"를 항목으로 두지 않는다 | 6장 세션 마무리에 한 줄 |
| R-24, R-25 ~ R-29 | `capability-request-template.md`를 "작업별 목표·단계" + "모든 요청에 같은 규칙 블록"으로 나눈다 | 원본은 프롬프트마다 목표·단계만 다르고 규칙 6줄은 공통 상수다(R-24). 우리 요청 템플릿은 한 덩어리라 규칙을 고칠 때 요청마다 고쳐야 한다(추론) | 요청 템플릿 구조, 사례: 규칙 변경 시 한 곳만 수정 |
| R-15 | `oss-repo-spec` 스킬·2장에 "레포 종류별 첫 읽기 표"(예: CLI, 라이브러리, 서버)를 둘지 검토한다 | 원본의 대상별 첫 단계 표(C-05)는 "어디서 시작할지"를 고정해 에이전트마다 다른 출발을 줄인다. 우리 feature map의 "진입점·처음 읽을 코드" 칸이 레포별로 같은 일을 하므로 표가 필요한지는 불확실하다(추론) | 선택 사항. 근거 없이 도입하지 않는다 |
| R-31 | 우리 규칙을 "check.py가 강제하는 것"과 "지침뿐인 것"으로 나눠 문서에 적는다 | 원본에서 코드로 강제되는 것은 finding의 증거 id 존재 같은 일부뿐이고 나머지는 텍스트다. 우리도 검증 수준 표기 여부·SHA·링크는 `check.py`가 보지만 "근거가 주장을 뒷받침하는지"는 사람이다. 어디까지 자동인지 기록해 두면 지침 수정 시 영향이 보인다(추론) | 1장(저장 위치·점검 항목)에 표 하나 |
| R-07 | 기각: 스킬 버전 번호 | 원본도 버전 값을 판정에 쓰지 않고 본문 비교로 구버전을 가른다(R-03, R-07). 우리 `AGENTS.md`·WORKFLOW는 git이 이력을 갖고 `log.md`에 `workflow` 종류로 남기므로 별도 버전이 필요 없다 | 없음 |
| R-09 | 확인만 함: "지시문보다 실시간 목록이 우선" | 원본은 스킬 자신의 한계를 선언한다(`skill.md:19`). 우리는 `AGENTS.md`가 "절차 원본은 WORKFLOW"라고 가리켜 같은 구조다 | 없음 |
