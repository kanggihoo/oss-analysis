---
sha: "3af3e8ef774c4d67ee57e1306d9256d08c9ee1bf"
created: 2026-11-17
updated: 2026-11-17
sources:
  - skills/ppt-master/references/confirm-surface.md
  - skills/ppt-master/scripts/docs/confirm_ui.md
  - skills/ppt-master/scripts/confirm_ui/server.py
  - skills/ppt-master/scripts/confirm_ui/static/app.js
  - skills/ppt-master/scripts/apply_template.py
  - skills/ppt-master/scripts/server_common.py
  - skills/ppt-master/scripts/docs/svg_editor.md
  - skills/ppt-master/workflows/stages/live-preview.md
  - skills/ppt-master/scripts/svg_editor/server.py
  - skills/ppt-master/scripts/svg_editor/annotations.py
  - skills/ppt-master/scripts/svg_editor/static/app.js
  - skills/ppt-master/scripts/check_annotations.py
  - skills/ppt-master/scripts/slide_roster.py
  - skills/ppt-master/scripts/docs/spec_review.md
  - skills/ppt-master/scripts/spec_review/server.py
  - skills/ppt-master/scripts/check_spec_annotations.py
  - skills/ppt-master/workflows/stages/refine-spec.md
  - skills/ppt-master/workflows/generate-pptx.md
  - skills/ppt-master/scripts/tests/test_local_server_security.py
  - skills/ppt-master/requirements.txt
depends:
  - ../capabilities/generate-default-pipeline.md
status: ready
---

# 확정·미리보기 화면 (confirm_ui, svg_editor, spec_review)

> agent가 로컬 웹 서버를 띄우고(`--daemon`), 파일 계약(`recommendations.stage*.json` → `result.json`·`template_selection.json`)으로 사용자의 Stage 1·2 확정을 기다린 뒤 끄고, 생성 중에는 라이브 미리보기·편집기(Direct edit, Annotate)를 곁가지로 제공하며, 필요하면 spec 리뷰 화면을 띄우는 실행 계약과 파일 계약이다.

<!--
읽는 법
- 목적은 agent 환경에 이 화면들을 "그대로" 연동하는 것이다. 화면 내부(Flask 라우트 전부, 프론트엔드 JS, 후보 카탈로그)는 풀지 않는다. 서버 코드는 어디를 보면 되는지만 2.2에 둔다.
- 선행 스펙(`generate-default-pipeline.md`)의 R-17~R-20은 Step 4 gate 전체(지시문 순서, 실패 시 chat 대체)를 이미 쓴다. 이 문서는 그 규칙을 다시 쓰지 않고, 그 아래에서 서버가 실제로 하는 일(종료 코드, 라운드, 진행 가드, 파일 필드)과 svg_editor·spec_review 계약을 쓴다. 선행 R-ID는 "선행 R-xx"로 부른다.
- 검증 수준 `코드 확인(문서 선언)`은 "문서를 직접 읽어 그렇게 선언돼 있음을 확인했다. agent가 따라야 하는 규칙이고 스크립트가 강제하지 않는다"는 뜻이다(선행 스펙과 같다). 스크립트·서버 동작은 `코드 확인`만 쓴다.
- 이 스펙은 서버를 실행하지 않았다. 브라우저 동작(JS)은 소스를 읽은 것이고 실제 브라우저에서 확인하지 않았다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

1. **표면 결정**: Step 4 시작 전에 agent가 "가장 최근의 명시적 확정 표면 지시"를 정한다. 위임이면 화면 없이 agent가 결정하고 요약 하나를 내고, chat이면 화면 없이 두 stage를 채팅으로 확정하고, 지시가 없으면 화면이 기본이다(R-01).
2. **Stage 1 (화면)**: agent가 `confirm_ui/recommendations.stage1.json`(+`template_options`)을 쓰고 `server.py <project> --daemon`으로 화면을 띄운 뒤 URL과 요약을 채팅에 올리고 `--wait-only --wait-stage stage1`로 기다린다. 사용자가 **Confirm contract & template choice**를 누르면 서버가 `result.json`(`stage1-confirmed`)과 `template_selection.json`을 한 번에 쓰고, 대기가 exit 0으로 풀린다. 이 exit 0은 중간 단계다(R-07, R-15).
3. **설치와 Stage 2**: agent가 선택에 따라 `apply-template-workspace`로 설치(→ 프로젝트 루트 `template_install.json`)하고, `recommendations.stage2.json`을 `selection_sha256`와 함께 쓴 뒤 `--wait-only`(final)로 기다린다. 서버는 설치 영수증을 직접 검증해야만 Stage 2를 연다(R-11, R-08).
4. **최종 확정과 종료**: 사용자가 **Confirm final plan**을 누르면 서버가 `result.json`을 `stage: final, status: confirmed`로 덮어쓰고, 브라우저가 `/api/shutdown`을 호출한다. agent는 `result.json`을 한 번 읽고 항상 `--shutdown`을 부른다(R-10, 선행 R-18·R-20).
5. **생성 중 미리보기**: Step 6 첫 SVG 전에 agent가 `svg_editor/server.py <project> --live --daemon`을 띄우고 URL을 보고한다. 기다리지 않는다. 브라우저는 2초마다 페이지 목록을 다시 읽는다(R-20, R-21).
6. **사용자 편집**: Direct edit는 AI 없이 **Apply changes** 때 `svg_output/`을 직접 고치고, Annotate는 같은 버튼으로 SVG 요소에 `data-edit-*` 마커를 쓴다. 내보내기는 편집기가 하지 않는다(R-23, R-24, R-27).
7. **주석 적용 (Step 7 이후)**: 사용자가 채팅으로 "apply my annotations"라고 하면 agent가 `check_annotations.py`로 목록을 얻고 SVG를 고치고 마커를 지우고 `annotations.jsonl`에 기록한 뒤 Step 7.2·7.3을 다시 돌린다(R-25).
8. **선택: spec 리뷰**: 사용자가 `refine_spec: true`를 골랐을 때만 Gate 1 뒤에 `spec_review/server.py <project> --daemon`을 띄우고, 승인은 채팅으로만 받는다(R-30).

### 1.2 범위·통합 지점 [필수]

- **제공**: 세 서버의 명령·종료 코드·포트·lock·idle timeout, Stage 1·2 파일 계약과 digest/round 규칙, 표면 결정 규칙과 "AI는 사용자 영수증을 쓰지 않는다" 규칙이 코드에서 어디까지 강제되는지, 라이브 미리보기의 자동 갱신 범위, 편집기가 디스크에 쓰는 것, 주석 적용 절차.
- **제외**: 확정 화면의 UI 구성·검증 규칙 전체(`confirm_ui.md` Field shapes, `_stage2_design_directions_error` 등), `static/catalogs.json`·템플릿 카탈로그 내부, 프론트엔드 JS, Flask 라우트 전부, spec_review의 블록 분할·렌더러 내부(`scripts/docs/spec_review.md`). 원격 접속은 `--no-browser`로 띄우고 포트를 SSH 등으로 포워딩한다(`svg_editor.md` Remote access, 한 줄만).
- **외부 의존·선행 계약**: 선행 스펙 `generate-default-pipeline.md`의 C1(프로젝트 디렉터리), Step 4 gate, 확정값 소비 경계(R-17~R-20). 템플릿 설치기 `apply_template.py`(서버가 `template_install.json`을 검증할 때 호출). Python 패키지 `flask>=3.0.0`(`skills/ppt-master/requirements.txt:122`). 서버는 `127.0.0.1`에만 바인드한다. 사용자 브라우저.
- **소유 상태·부작용**: `confirm_ui/`(agent 입력과 서버 영수증이 섞인 디렉터리), `<project>/.confirm_ui.lock`, `live_preview/`(lock·draft·로그), `spec_review/`(lock·sidecar). 서버는 `svg_output/`(편집기), `design_spec.md`(spec_review)를 직접 쓴다. `exports/`와 `svg_final/`은 쓰지 않는다.

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 서버 명령

"UI branch only"는 선행 R-18이 정한 순서를 따른다. 아래는 옵션과 관찰되는 의미다.

**`scripts/confirm_ui/server.py <project_path>`** (C-01, C-03, C-05, 코드 `:2755-2801`, `:2804-2960`)

| 옵션 | 의미 |
|---|---|
| (없음) | 포그라운드로 서버 실행. 포트와 lock은 아래와 같다 |
| `--daemon` | 백그라운드 자식 서버를 띄우고 `GET /api/health`가 이 서비스·프로젝트·pid와 맞는 것을 확인한 뒤 브라우저를 연다. 반환은 exit 0. 이미 살아 있는 서버가 있으면 재사용하지 않고 **exit 1**(R-06) |
| `--wait-only` | 이미 뜬 서버에 붙어 `result.json`의 목표 stage가 쓰일 때까지 막힌다(R-07). 서버를 새로 띄우는 옵션이 아니다. 단, lock의 pid가 죽어 있으면 기록된(없으면 기본) 포트로 서버를 되살린다 |
| `--wait-stage {stage1,final}` | `--wait-only`가 기다릴 stage. 기본 `final`. 다른 값은 exit 2 |
| `--wait-timeout N` | `--wait-only`가 막히는 최대 초. 기본 **590**, `0`은 무제한. 서버는 계속 살아 있다 |
| `--timeout N` | 서버 idle 자동 종료 초. 기본 **900**, `0`은 끔. 브라우저 poll 요청도 idle 시계를 갱신한다(R-06) |
| `--port N` | 정확히 이 포트. 쓸 수 없으면 실패. 범위 밖이면 exit 2. 생략하면 `5050`부터 첫 빈 포트 |
| `--no-browser` | 브라우저 자동 열기를 막는다(원격 호스트) |
| `--shutdown` | 이 프로젝트의 확정 서버를 끈다. 멱등(R-10) |
| `--wait` | `--daemon`과 함께 쓰면 launch 직후 대기하는 변형. workflow 문서는 쓰지 않는다 |

| 종료 코드 | 의미 (확정 서버) |
|---|---|
| 0 | `--daemon` 성공, `--wait-only` 목표 stage 도착, `--shutdown` 성공(할 일이 없어도 0) |
| 1 | 프로젝트 경로가 디렉터리가 아님, 실행 전 Stage 1 파일 오류(R-05), 이미 실행 중, 서버 기동 실패, `--wait-only` 준비 오류, 대기 중 서버가 죽음 |
| 2 | `--port` 범위 오류, `--wait-stage` 값 오류, 대기 중 다른 stage로 건너뜀 또는 Stage 1 결과에 유효한 `template_selection.json`이 없음 |
| **124** | `--wait-only`가 `--wait-timeout` 안에 확정을 못 받음. 서버는 살아 있다 |

- lock: `<project>/.confirm_ui.lock`, 내용 `{"pid", "port"}`(`server_common.py:282-296`). 죽은 pid의 lock은 덮어쓴다.
- health: `GET /api/health`가 `service: "confirm_ui"`, `project`(절대경로), `pid`, `recommendations`(현재 active 파일 유효 여부), `session`을 돌려준다.
- 서버 로그: `confirm_ui/server.log`(자식 프로세스 stdout·stderr).
- 서버는 `Host`가 loopback이 아니거나 `Origin`이 loopback이 아니면 403(C-02 아래 R-04).

**`scripts/svg_editor/server.py <project_path>`** (코드 `:1466-1500`, `:1503-1678`, `svg_editor.md` Commands·Lifecycle)

| 옵션 | 의미 |
|---|---|
| `--daemon` | 백그라운드로 띄우고 `/api/health` 확인 후 반환. 이미 살아 있으면 재사용하고 **exit 0**(R-20) |
| `--live` | Executor 라이브 미리보기. `svg_output/`이 비어 있거나 없어도 시작(없으면 만든다), 주석을 제출해도 계속 서비스. idle 기본 **7200 s**(plain은 900) |
| `--port N` | 정확히 이 포트(범위 밖 exit 2). 생략하면 `6060`부터 첫 빈 포트. 실제 URL은 출력이나 `live_preview/lock.json`에서 읽는다 |
| `--timeout N` | idle 초. `0`은 끔 |
| `--no-browser` | 브라우저를 열지 않는다 |
| `--shutdown` | 서버를 끈다. 멱등이지만 health로 소유권을 확인하지 못하면 **exit 1**로 아무것도 건드리지 않는다 |

- lock: `<project>/live_preview/lock.json` `{"pid","port"}`. 옛 `<project>/.live_preview.lock`도 살아 있으면 인식한다.
- `--live` 없이 `svg_output/`이 없으면 exit 1. 서버가 죽은 뒤 재기동할 때 draft가 복원된다(R-22).

**`scripts/spec_review/server.py <project_path>`** (선택, R-30; 코드 `:233-240`, `spec_review.md` Commands·Lifecycle)

| 옵션 | 의미 |
|---|---|
| `--daemon` | 백그라운드로 띄우고 실제 URL·pid·port를 담은 JSON 한 줄을 stdout에 낸다. 이미 살아 있으면 재사용, 다른 명시 포트면 실패 |
| `--shutdown` | 서버 종료(할 일이 없으면 `{"status":"stopped"}`, exit 0) |
| `--hold on|off` | 리뷰 중 agent가 파일을 고치는 동안 화면의 Apply를 막는다(423). 서버가 안 떠 있을 때 `on`은 오류 |
| `--port N` / `--timeout N` / `--no-browser` | 기본 `6060`부터 50개 포트 스캔 / idle 기본 `7200`(`0`은 끔) / 브라우저 안 엶 |

- lock: `<project>/spec_review/lock.json`. 서버 로그 `spec_review/server.log`.
- `check_spec_annotations.py <project> [--applied ID | --ack-edits]`는 compact JSON 한 줄(해야 할 주석, 사용자가 직접 고친 블록 요약)을 낸다. 성공 0, 오류 1.

#### 1.3.2 `confirm_ui/` 파일 계약

모든 파일은 `<project>/confirm_ui/` 아래다(`template_install.json`만 프로젝트 루트). 필드 전체는 옮기지 않는다. 필드 문법은 `references/confirm-surface.md` §2~§4와 `scripts/docs/confirm_ui.md`(Stage-1 sidecar 계약 `:71-259`, Field shapes `:261-280`, Output `result.json` `:498-559`)가 소유한다.

| 파일 | 쓰는 쪽 | 읽는 쪽 | 연동자가 반드시 알아야 할 것 |
|---|---|---|---|
| `recommendations.stage1.json` | **agent** | 서버(화면, digest) | `stage: "stage1"`, 필수 `primary_language`(BCP-47, `und` 거부), `recommend.canvas`, 산문 7개(`audience`, `communication_intent`, `audience_outcome`, `core_message`, `delivery_context`, `artifact_afterlife`, `content_divergence`: 각 `{ "value": ... }`, 비어도 됨), **`template_options`**(`schema_version: 1`, `phase: "template"`, `default_mode: free_design|templates`, `explicit_workspace_roots: [절대경로...]`가 필수. 빈 배열도 필수). `revision`은 선택(R-12). 문서 위치: `confirm-surface.md` §2, `confirm_ui.md:344-388` |
| `recommendations.stage2.json` | **agent** | 서버(화면) | `stage: "stage2"`, **최상위 `selection_sha256`**(서버가 쓴 `template_selection.json`에서 복사), `recommend.generation_mode`, boolean `refine_spec.value`, `design_spec_depth.value`(`brief`\|`complete`; `split`이나 `refine_spec: true`이면 `brief` 거부), `image_usage`에 `ai`가 있으면 `recommend.image_ai_path`(`auto|api|host-native|manual`), `design_directions`(정확히 3개 후보, `selected` 0~2), templates 모드면 `template_application.value`. 문서 위치: `confirm-surface.md` §3, `confirm_ui.md:390-496` |
| `template_selection.json` | **서버**(Stage 1 제출 때) | agent, 서버, `apply_template.py` | `mode`(`free_design`는 `selections: []`, `templates`는 1개 이상), `selections[]`, `root_snapshots[]`(선택한 root의 파일 SHA-256), `options_sha256`, **`selection_sha256`**, `confirmed_at`. agent는 이 중 `selections`의 `workspace_root`로 설치하고 `selection_sha256`를 stage2에 복사한다. 문서 위치: `confirm_ui.md:164-237` |
| `result.json` | **서버**(제출 때마다 원자적 덮어쓰기) | agent(한 번), 서버 | Stage 1 제출 후: `stage: "stage1"`, `status: "stage1-confirmed"`. Stage 2 제출 후: `stage: "final"`, `status: "confirmed"`. 둘 다 서버가 붙이는 `stage1_sha256`, `selection_sha256`, `confirmed_at`과 사용자 확정값. final 필드 목록: `confirm_ui.md:498-534`. 오래된 `design_spec_depth` 없는 결과는 `complete`로 읽는다 |
| `session.json` | **서버**(상태가 바뀔 때만) | 화면 poll, agent(선택) | 서버가 디스크 파일에서 유도한 상태(`status`: `ready_user` / `waiting_agent` / `done` / `error`, `current_stage`, `result_stage` 등). 사용자 영수증이 아니고 권위가 없다. 확정 증거로 쓰지 않는다 |
| `server.log` | 서버(자식 프로세스 출력) | — | 디버깅용 |
| `template_install.json` (**프로젝트 루트**) | **설치기**(`apply_template.py`) | 서버 | 서버는 Stage 2 직전에 `read_template_install`로 roots, `selection_sha256`, 설치된 spec 목록, roster, 파일 해시를 `template_selection.json`과 맞춰 본다. `free_design`은 영수증이 필요 없다 |

- **digest와 round (C-02)**: `stage1_sha256`은 `recommendations.stage1.json` 전체(`template_options` 포함)의 정규 JSON(`sort_keys`, 공백 없음) SHA-256이다. `options_sha256`은 여기에 템플릿 index 4개와 해석된 후보를 더해 묶는다. `result.json.stage1_sha256`이 현재 stage1 파일 digest와 다르면 그 결과는 이미 "새 라운드"라 무효다(R-12).
- **누가 어디서 읽나**: agent는 `result.json`과 `template_selection.json`을 각 경계에서 한 번 읽는다(선행 R-18·R-20). 이후 단계는 `design_spec.md`를 읽는다(C2).

#### 1.3.3 `live_preview/` 파일 계약 (svg_editor)

| 파일 | 쓰는 쪽 | 의미 |
|---|---|---|
| `live_preview/lock.json` | 서버 | `{"pid","port"}`. agent가 URL을 찾는 곳. 직접 지우지 않는다(소유권 불일치 시 서버가 거부하고 안내) |
| `live_preview/draft.json` | 서버 | 아직 Apply하지 않은 staged 편집·주석(`version: 1`, `pages`). 변경마다 응답 전에 다시 쓰고, 남은 것이 없으면 삭제 |
| `live_preview/draft_conflict_<timestamp>.json` | 서버 | 재시작 때 SVG가 바뀌어 복원하지 못한 페이지나 읽을 수 없는 draft를 옮겨 둔 파일 |
| `live_preview/edits.jsonl` | 서버 | Apply된 Direct edit 기록(`ts`, `file`, `element_id`, `action: "edit"`, `kind`, `key`, `old`, `new`) |
| `live_preview/annotations.jsonl` | **서버와 agent 둘 다** | 서버는 `annotation_saved` / `annotation_updated` / `annotation_removed`(`ts`, `file`, `element_id`, `action`, `old`, `new`)를 쓴다. agent는 주석을 처리한 뒤 `annotation_applied` 한 줄을 덧붙인다(R-25) |
| `live_preview/server.log` | 서버 | 자식 출력 |
| `svg_output/<page>.svg` | 서버(Apply) / agent | SVG 요소 마커 `data-edit-target="true"`, `data-edit-annotation="<text>"`(R-24) |

주석 한도: `element_id` 200자, 주석 본문 10,000자(`svg_editor/server.py:944-975`). 편집 가능 속성 값은 256자, 텍스트는 5,000자(`:285-286`).

#### 1.3.4 `spec_review/` 파일 계약 (선택)

`spec_review/lock.json`, `spec_review/annotations.json`(주석 sidecar), `spec_review/annotations.jsonl`, `spec_review/edits.jsonl`, `spec_review/server.log`. 서버는 `design_spec.md`의 한 블록을 Apply 때 직접 다시 쓰고 `spec_lock.md`는 읽지도 쓰지도 않는다(`spec_review.md:1-5`, `:96-111`). 필드와 hash 규칙은 `spec_review.md:111-130`에 있다.

### 1.4 행동 규칙과 남은 질문 [필수]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | Step 4 전 확정 표면 결정 (`confirm-surface.md` §1) | 가장 최근의 명시적 확정 표면 지시를 따른다. 사용자가 확정을 명시적으로 **위임**하면 화면을 띄우지 않고, agent가 Stage 1 결정·설치를 하고 최종 요약 하나를 낸다(해결안 3개는 여전히 쓰고 고른 이유를 기록). 사용자가 chat 확정을 요청·동의하거나 화면을 거절하면 화면·`--wait-only`·UI 영수증 없이 두 stage를 채팅으로 확정한다. 지시가 없으면 **화면이 기본**이다. 관련 없는 이후 메시지는 분기를 바꾸지 않고, 채팅으로 시작했거나 UI에서 chat으로 바꾼 뒤에는 남은 run 동안 chat을 유지한다. 의미로 판단한다("여기서 확정할게", "확인 페이지 열지 마" 등). chat-question 도구를 쓴 것만으로는 아무것도 선택되지 않는다 | 코드 확인(문서 선언). 서버·스크립트가 분기를 강제하지 않는다(agent 판단) |
| R-02 | 화면 띄운 뒤 사용자가 명시적으로 chat을 고름 (UI → chat 전환) | agent는 진행 중인 대기를 중단하고 그 프로세스가 끝난 것을 확인한다(이 의도적 중단이 예상되는 유일한 non-zero다). `server.py <project> --shutdown`을 부르고 성공을 요구한다. active 영수증을 한 번 다시 본다(Stage 1: `result.json`과 같은 제출의 `template_selection.json`, Stage 2: `result.json`. 제출하지 않은 브라우저 draft는 확정이 아니다). 이후는 다시 띄우지 않고 chat으로 끝낸다. 실행 실패·대기 timeout 뒤에도 영수증을 한 번 다시 보고 같은 항목을 열린 chat 질문으로 제시한다 | 코드 확인(문서 선언). 선행 R-19와 같은 규칙의 절차 상세 |
| R-03 | agent가 확정 값을 대신 정하거나 제출을 자동화하거나 사용자 결과 상태(`result.json`·`template_selection.json`)를 씀 | 금지(규칙). agent가 쓰는 것은 `recommendations.stage1/2.json`, 서버 운영, 설치뿐이다. 침묵은 확정이 아니다. 위임 시에도 UI receipt를 위조하지 않는다. 제출된 값(공백·특이한 덮어쓰기 포함)이 권위를 가진다 | 코드 확인(문서 선언: `generate-pptx.md:128-134`, `confirm-surface.md` §1, 선행 R-17) |
| R-04 | R-03이 코드로 강제되는가 (선행 U-02) | **강제되지 않는다. 막는 것은 stale·불일치 검사뿐이다.** (a) 서버가 `result.json`을 신뢰하는 조건은 `stage`/`status` 값 쌍과 `stage1_sha256 == 현재 stage1.json의 정규 JSON digest`뿐이고(`_result_stage`, `_fresh_template_restart`), 이 digest는 누구나 stage1 파일에서 다시 계산할 수 있다. 서명·비밀값·작성자 표시는 없다. (b) Stage 2는 추가로 `result.selection_sha256`이 현재 선택과 같고 설치 영수증이 맞아야 하지만, 그것도 파일 내용에서 계산 가능한 값이다. (c) `/api/confirm`은 `Host`가 loopback이고 `Origin`이 없거나 loopback이면 받는다. `Origin` 없는 요청 허용은 테스트가 명시한다. 즉 같은 머신의 비브라우저 클라이언트(curl 등)도 제출할 수 있다. (d) 서버 밖에서 `result.json`을 읽는 스크립트는 없다(`apply_template.py`는 `template_selection.json`만 읽는다). `--wait-only`와 session은 같은 두 검사만 쓴다. 따라서 agent가 직접 쓴 `result.json`을 서버·설치기·`project_manager.py validate`·후속 gate가 거부하는 코드는 이 검색 범위에서 찾지 못했다. 예외로 **우연한 실수는 막힌다**: stage1 파일을 확정 뒤에 고치면 digest가 달라져 결과가 무효(R-12)이고, `--wait-only`는 아직 안 쓰인 결과를 기다린다 | 코드 확인(검색 범위 2.1) |
| R-05 | `--daemon` 또는 인자 없는 실행 전 | `recommendations.stage1.json`이 유효해야 한다(`stage: "stage1"`, `template_options` 구조, 유효한 `primary_language`). 아니면 오류를 로그하고 **exit 1**. 이전 run의 `result.json`이 이미 `final`이고 stage1 내용이 같으면 "이전 run 완료, `revision`으로 새 라운드" 오류로 exit 1. Stage 1 결과가 있으면 `template_selection.json`도 유효해야 한다 | 코드 확인 |
| R-06 | `--daemon` | 포트는 `--port` 없으면 `5050`부터 첫 빈 포트, 있으면 정확히 그 포트. `GET /api/health`가 `confirm_ui`, 이 프로젝트 경로, lock의 pid와 일치할 때만 성공(10초 한도). 이미 살아 있는 서버가 있으면 pid·포트를 알리고 **exit 1**(재사용 안 함). 죽은 pid의 lock은 덮어쓴다. idle 기본 900 s이고 모든 요청이 시계를 갱신하므로 브라우저가 열려 poll하는 동안은 끝나지 않는다. 한 서버가 Stage 1부터 final까지 같은 프로세스로 산다 | 코드 확인 |
| R-07 | `--wait-only --wait-stage stage1` | (1) 이미 `result.json`이 `stage1-confirmed`이고 digest가 맞으면 서버 복구 전에 바로 반환(그 사이 빠른 제출을 놓치지 않는다). 이때 유효한 `template_selection.json`이 없으면 **exit 2**. (2) 아니면 준비 오류가 있으면 exit 1. (3) lock의 서버가 죽었으면 기록된 포트에서 되살린다. (4) 0.5초 간격으로 기다리며 서버가 죽으면 exit 1, `--wait-timeout`을 넘기면 **exit 124**. 도착하면 **exit 0**이고 stdout/log에 "Stage 1 is intermediate" 안내가 나온다. 결과가 이미 `final`이면 stage를 건너뛴 것이라 exit 2 | 코드 확인 |
| R-08 | `--wait-only`(final, 기본) | 호출 순간 `_stage2_ready_error`가 통과해야 한다. 즉 **그 전에** `template_selection.json`이 유효하고, templates 모드면 설치 영수증이 검증되고, `result.json`이 현재 `stage1-confirmed`이고, `recommendations.stage2.json`이 있고 `selection_sha256`이 일치해야 한다. 하나라도 안 맞으면 기다리지 않고 **즉시 exit 1**. 통과하면 `stage: final, status: confirmed`가 쓰일 때까지 R-07과 같은 방식으로 기다린다(124 포함). 제출은 서버가 `result.json`을 쓴 뒤 브라우저가 `/api/shutdown`을 호출해 서버가 꺼지는 순서다. **주의**: `--wait-only`는 stage2 파일의 production 필드·후보 검증(R-14)을 하지 않는다. stage2 파일이 구조는 맞아도 production 검증에서 거부되면 화면은 오류를 보이고 `--wait-only`는 막힌 채 exit 124로 끝난다 | 코드 확인 |
| R-09 | 확정 서버의 시계·체크 | `--wait-only`는 시간 비교(mtime)를 쓰지 않는다. 판단은 stage/status와 digest뿐이다(R-12). 이전 stage가 이미 끝난 뒤 시작한 대기도 놓치지 않는다 | 코드 확인 |
| R-10 | `--shutdown` | lock이 없으면 아무것도 안 하고 exit 0. pid가 죽었으면 lock을 지우고 exit 0. 살아 있으면 `POST /api/shutdown`(3초) → 최대 약 2초 대기 → 아직 살아 있으면 기록된 pid에 SIGTERM → lock 삭제 → exit 0. **health로 소유권을 확인하지 않는다**(svg_editor와 다르다). 최종 확정 시 브라우저가 이미 `/api/shutdown`을 부르지만, 사용자가 창을 닫았거나 확정하지 않은 run이 있으므로 agent는 모든 경로에서 `--shutdown`을 부른다(선행 R-18·R-19). 서버가 떠 있는 동안 5050 포트가 점유되므로 라이브 미리보기 전에 끈다 | 코드 확인 |
| R-11 | 진행 가드: Stage 2를 열거나 제출 | Stage 2의 `GET /api/recommendations`와 `POST /api/confirm`은 `template_selection.json` 검증(원본 root 바이트와 index drift 포함), templates 모드의 설치 영수증 검증(`read_template_install`), `result.json`이 현재 `stage1-confirmed`이고 `selection_sha256`이 현재 선택과 같음, stage2 파일의 `selection_sha256` 일치를 모두 요구하고 아니면 409. 제출 stage는 active 파일의 stage와 같아야 하고(Stage 1 파일이면 `stage1`, Stage 2 파일이면 `final`) 선행 결과(stage1은 선행 결과 없음, final은 `stage1-confirmed`)가 있어야 한다. 파일 timestamp는 진행을 허가하지 않는다. active stage는 서버가 `result.json`에서 유도한다. 화면은 선택·설치가 끝날 때까지 `waiting_agent`로 poll한다 | 코드 확인 |
| R-12 | 라운드 무효화 | `recommendations.stage1.json`의 **내용**(정규 JSON)이 바뀌면 이전 `result.json`·`template_selection.json`·stage2 파일·설치 영수증 어느 것도 새 입력을 인증하지 못한다. 파일은 지워지지 않고 그냥 무효다. 같은 선택을 새 라운드로 반복하려면 최상위 `revision` 값을 바꾼다. 공백·키 순서·timestamp는 digest를 바꾸지 않는다. 따라서 **Stage 1 확정 뒤 stage1 파일을 고치면 안 된다**(Stage 2 작성 중에도). 또한 템플릿 index 4개나 선택한 외부 root 파일이 확정 뒤에 바뀌어도 `options_sha256`/snapshot 검사로 선택이 무효가 된다. 완료된 run(`final`)은 새 라운드를 시작하기 전까지 다시 열리지 않는다(`GET /api/recommendations` 409) | 코드 확인 |
| R-13 | active 파일 덮어쓰기 | 아직 확정되지 않은 **active stage 파일만** 같은 경로에 여러 번 덮어쓸 수 있다(새 추천을 요청받았을 때, 화면은 새로고침). 확정된 stage의 파일을 다른 stage payload나 `-v2` 같은 접미사 파일로 쓰지 않는다. 서버는 active 파일을 `result.json`에서 유도하므로 접미사 파일은 읽히지 않는다 | 코드 확인(active 유도), 코드 확인(문서 선언: 덮어쓰기 규칙) |
| R-14 | `recommendations.stage2.json` 내용 검증 | `GET /api/health`·`/api/recommendations`·`/api/confirm`이 active 파일을 읽을 때 stage 선언, `selection_sha256`, production 필드(`recommend.generation_mode`, boolean `refine_spec.value`, `design_spec_depth`, 조건부 `image_ai_path`, `brief` 금지 조건), 후보 구조를 검사한다. 어긋나면 화면은 400/409 오류를 보이고 health의 `recommendations`는 false다. 이 오류는 agent에게 exit code로 전달되지 않는다(R-08 주의) | 코드 확인 |
| R-15 | 사용자 제출 | Stage 1: 서버가 `options_sha256`(화면이 렌더한 catalog의 digest)이 현재와 같은지 보고(아니면 409 "reload"), 브라우저가 보낸 `mode`와 `selection_keys`를 서버 후보에 대조해 `template_selection.json`을 만들고(`free_design`이면 선택 없음, `templates`면 1개 이상), 같은 요청에서 `result.json`(`stage1-confirmed`)과 `template_selection.json`을 원자적 교체로 쓴다. 화면은 열린 채 poll한다. Stage 2: `result.json`을 `final/confirmed`로 쓰고 이전 Stage 1 값을 합쳐 담는다. 서버는 `stage1_sha256`·`selection_sha256`·`confirmed_at`을 붙이고 구형 `template_reuse_scope`·`template_adherence`·`formula_policy`를 지운다. 브라우저는 성공 응답 뒤 `/api/shutdown`을 호출한다. 사용자가 보낸 산문은 빈 문자열도 그대로 보존한다 | 코드 확인 |
| R-16 | 설치와 `template_install.json` | 설치기는 `confirm_ui/template_selection.json`이 있으면 선택한 roots·snapshot과 같은지 확인하고 `selection_sha256`을 영수증에 적는다. 영수증은 프로젝트 **루트**에 있다(문서는 `confirm_ui/` 파일과 함께 나열하지만 코드는 루트). 서버 검증은 Stage 2를 열 때와 제출 때 모두 다시 한다. 추가 이미지·아이콘은 허용하고 선택한 자산·roster가 어긋나면 거부한다 | 코드 확인 |
| R-17 | 의존성 | 세 서버 모두 모듈 최상단에서 `flask`를 import하므로 `pip install flask`(`requirements.txt`는 `flask>=3.0.0`)가 없으면 `--shutdown`과 `--wait-only`를 포함한 모든 명령이 시작 전에 import 오류로 실패한다 | 코드 확인 |
| R-20 | Step 6 첫 SVG 전, `svg_editor/server.py <project> --live --daemon` | 첫 SVG 전에 띄우고 실제 URL(출력 또는 `live_preview/lock.json`)이나 실패 사실을 보고한다. 곁가지 프로세스라 기다리지 않고, 사용자가 **Exit preview**를 누르거나 채팅으로 요청할 때까지 Step 7까지 유지한다. 실패해도 생성은 막히지 않는다(선행 1.1). 이미 살아 있는 서버가 있으면 재사용하고 exit 0이다(다시 띄우지 않는다). 다른 명시 `--port`는 exit 1이고 `--shutdown` 후 재시작해야 한다. health가 프로젝트·`live_preview`·lock pid와 맞지 않으면 재사용도 종료도 하지 않고 exit 1이다. 브라우저를 연다(`--no-browser` 아니면). 한 프로젝트에 인스턴스 하나다 | 코드 확인 |
| R-21 | **라이브 미리보기 자동 갱신** | `--live`일 때만 브라우저가 2초마다 `/api/slides`를 다시 읽는다. (a) **새 페이지(SVG 파일)가 `svg_output/`에 생기면 목록에 약 2초 안에 나타난다**(`*.svg` 직접 자식, 번호순). 목록이 비어 있으면 "대기 중" 안내를 보이고, 처음 열린 뒤 목록이 채워지면 첫 페이지(또는 주소에 기억된 페이지)를 자동 선택한다. 이미 어떤 페이지를 보고 있으면 새 페이지로 **자동 이동하지 않는다**. (b) 보고 있는 페이지가 디스크에서 바뀌면(mtime 변화) 자동 재렌더하지 않고 **"reload" 배너**를 띄우며 클릭하면 다시 읽는다. (c) 보고 있는 페이지가 파싱 불가(쓰는 중)였다가 읽을 수 있게 되면 자동으로 다시 렌더한다. (d) plain 모드(`--live` 없이)는 polling이 없다. 서버 쪽 push(SSE·WebSocket)는 없다. 요약: 새 페이지는 자동으로 목록에 뜨고, 이미 열린 페이지의 변경은 배너 한 번 클릭이 필요하다 | 코드 확인(정적 소스 읽기). 실제 브라우저에서 실행하지 않음(확인 한계) |
| R-22 | staged 상태와 draft | 모든 staging 변경(주석 추가·삭제, Direct edit, undo)은 응답하기 전에 `live_preview/draft.json`을 다시 쓰고, 남은 것이 없으면 지운다. 다음 서버 시작 때 staging 당시의 SVG digest가 그대로인 페이지만 복원하고, 바뀐 페이지는 `draft_conflict_<timestamp>.json`으로 옮긴다. **Apply changes**는 staging 이후 SVG가 디스크에서 바뀌었으면(digest 불일치, 예: agent가 그 페이지를 다시 썼다) 그 페이지를 실패로 보고하고 staged로 남긴다. 주석 대상 요소가 사라졌어도 실패하고 staged로 남는다. 따라서 사용자가 staged 작업을 가진 페이지를 agent가 다시 쓰면 그 staged 작업은 적용되지 못한다 | 코드 확인 |
| R-23 | Direct edit (AI 없음) | 사용자가 요소를 골라 속성·텍스트·위치를 바꾸면 미리보기는 즉시 바뀌고 디스크는 **Apply changes** 때까지 안 바뀐다. Apply가 `svg_output/<file>`을 제자리에 쓰고 `live_preview/edits.jsonl`에 기록한다. 서버는 서비스를 유지한다. **Exit preview**만 Flask를 끈다(미적용 작업은 draft에 남는다). agent는 이 동작에 개입하지 않는다 | 코드 확인 |
| R-24 | Annotate (AI 필요) | **Add annotation**은 메모리와 draft에만 쌓고 **Apply changes**가 대상 요소에 `data-edit-target="true"`와 `data-edit-annotation="<본문>"`을 쓴다. 대상 요소의 `id`는 유지하고 주석이 없는 요소의 임시 `_edit_N` id는 지운다. 서버는 `annotation_saved`/`annotation_updated`/`annotation_removed`를 `live_preview/annotations.jsonl`에 쓴다. 다 지우면 마커도 지워진다 | 코드 확인 |
| R-25 | 주석 적용 (`live-preview.md` Step 2) | **게이트**: `exports/`에 `*.pptx`가 하나 이상 있어야 한다(없으면 주 파이프라인을 먼저 끝내라고 안내). 순서: (1) `check_annotations.py <project>`로 목록(`파일 → element_id → 주석 → 내용 미리보기`)을 얻고 없으면 사용자에게 알리고 멈춘다. (2) 주석마다 `svg_output/<file>`의 해당 요소를 고치고 그 요소에서 `data-edit-target`·`data-edit-annotation`을 지우고 `live_preview/annotations.jsonl`에 `annotation_applied` 한 줄(`ts`, `file`, `element_id`, 원래 주석 본문)을 덧붙인다. (3) `generate-pptx.md` Step 7.2를 다시 돌리고 성공 기준을 확인한 뒤 7.3을 돌린다. 발표 노트가 바뀐 때만 7.1도 다시 한다. (4) 사용자에게 적용·새 PPTX·미리보기가 계속 도는 것을 알리고(브라우저가 옛 슬라이드를 보이면 새로고침이나 페이지 재선택), 주석이 더 있으면 반복하고 "done"이면 끝낸다. 트리거는 사용자가 채팅에서 브라우저 안내 문구를 인용하거나 같은 뜻을 말하는 것이다. 정확한 채팅 수정("3페이지 제목을 X로")은 이 절차 없이 SVG를 직접 고친다. 서버나 스크립트는 마커 제거나 `annotation_applied` 기록을 확인하지 않는다 | 코드 확인(문서 선언). `check_annotations.py`는 코드 확인 |
| R-26 | 생성 중 주석 | Step 6 중에는 제출된 주석을 읽거나 적용하지 않는다. 그 창은 Step 7 이후에 열린다(선행 R-41) | 코드 확인(문서 선언) |
| R-27 | 재내보내기 | `Apply changes`는 `svg_output/`만 바꾼다. `finalize_svg.py`와 `svg_to_pptx.py`는 편집기가 돌리지 않으며, 새 PPTX가 필요하면 채팅에서 agent가 Step 7.2·7.3을 다시 돌린다("re-export"). Direct edit만 한 경우도 같다 | 코드 확인(서버 코드가 export를 호출하지 않음, 2.1) |
| R-28 | `check_annotations.py <project 또는 .svg>` | `svg_output/`의 모든 SVG를 훑어 `data-edit-target="true"` 요소를 `element_id`, 태그, 주석, (text 요소면) 50자 미리보기로 출력한다. 주석이 없으면 `[OK] No annotations found.`와 exit 0. 파싱할 수 없는 SVG가 하나라도 있으면 stderr에 `[ERROR] Failed to parse SVG ...`를 내고 **exit 1**(주석 없음으로 오인하지 않게). 경로가 없거나 디렉터리·`.svg`가 아니면 exit 1 | 코드 확인 |
| R-30 | spec 리뷰 (`refine_spec: true`일 때만) | Gate 1(완전한 `design_spec.md`) 뒤에 `spec_review/server.py <project> --daemon`을 띄우고 URL을 보고하고 **기다리지 않는다**. 승인은 채팅으로만 받는다. 사용자가 돌아오면 `--hold on`, `check_spec_annotations.py`(할 일), 주석 반영 후 `--applied <id>`, `--ack-edits`, `--hold off` 순서이고, 승인 시에는 `--hold off` 대신 `--shutdown`으로 끝낸 뒤 Gate 2(lock 작성)로 간다. 리뷰 중 `spec_lock.md`는 만들지도 쓰지도 검증하지도 않는다. 화면은 chat 분기·UI→chat 전환·실패 시 쓰지 않고 파일을 채팅으로 제시한다. 화면의 Direct edit는 `design_spec.md`의 한 블록을 직접 다시 쓰고(스키마 오류는 보여 주되 저장은 막지 않음), 외부 변경은 2초 poll hash로 감지한다. idle 7200 s에서 `/api/state` poll은 시계를 갱신하지 않아 열린 탭만으로는 timeout을 막지 못한다 | 코드 확인(문서 선언: 흐름), 코드 확인(서버 옵션·lock 경로) |

- 불변식: (1) `confirm_ui/` 안의 `result.json`·`template_selection.json`은 사용자 확정을 나타내는 영수증으로 취급하며 agent가 쓰지 않는다. 이것은 문서 규칙이고 코드가 강제하지 않는다(R-04). (2) 서버가 인증하는 것은 "현재 stage1 입력에 묶인 파일이다"까지다. 누가 썼는지는 아니다. (3) `--wait-only` exit 0(stage1)은 항상 중간 단계다.
- 미결정: 없음. 원본이 정하지 않은 값은 아래 "원본이 정하지 않은 것"에 두고 연동자가 정한다.

- 원본이 정하지 않은 것(연동자가 정하는 값, 구현을 막지 않음):
  - `annotations.jsonl`에 agent가 쓰는 `annotation_applied` 줄의 필드 이름. `live-preview.md:38`은 `ts`, `file`, `element_id`, 원래 텍스트만 말한다. 서버가 쓰는 줄은 키 `action`(`svg_editor/server.py:328-350`), spec_review는 키 `event`(`spec_review/store.py:301-318`)를 쓴다. 이 파일을 읽는 코드는 없고(`grep -rn "annotations\.jsonl" skills/ppt-master docs`: 쓰기 `svg_editor/server.py:328`·`spec_review/store.py:301,317`, 생성 `project_management/cli.py:387`, 문서 3곳뿐) 감사 기록이므로 형식은 자유다.
  - `session.json`의 `recommendation_error`를 agent가 읽어야 하는 규칙은 문서에 없다(`grep -rn "recommendation_error" skills/ppt-master docs`: `confirm_ui/server.py:1651-1665, 1858`만). stage2 파일이 검증에서 거부되어도 `--wait-only`는 124까지 기다린다(R-08, R-14). 124가 사용자 미응답인지 stage2 파일 오류인지 구분하는 방법은 `GET /api/health`의 `recommendations`와 `session.json`의 `recommendation_error`를 읽는 것이고, 이 읽기를 agent 절차로 둘지는 연동자가 정한다(적용 메모).
- 확인 한계: 라이브 미리보기의 자동 갱신(R-21)은 소스만 읽었고 브라우저에서 확인하지 않았다. 서버(세 개)를 실행하지 않았고 flask를 설치하지 않았다. 프론트엔드 JS는 `submitStage`·`/api/shutdown` 호출부와 `startSlidePolling`/`loadSlides` 주변만 읽었다(`confirm_ui/static/app.js:4296-4311`, `:4415-4437`, `svg_editor/static/app.js:618-709`, `:2028-2033`, `:3199-3202`). Windows·WSL의 브라우저 열기·프로세스 생존 판정(`server_common.py`)은 읽지 않았다. 화면 필드 검증 규칙 전체(`_stage2_design_directions_error` 등 `server.py:1469-1700`)는 읽지 않았다. 원격 접속은 문서 한 줄만 읽었다.

### 1.5 필수 코드 참조 [필수]

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `skills/ppt-master/scripts/confirm_ui/server.py:84-96`, `:136-145` | `.confirm_ui.lock`, `confirm_ui/` 디렉터리, `recommendations.stage1.json`/`stage2.json`, `result.json`, `session.json`, `template_selection.json` 이름, 기본 포트 5050, `WAIT_TIMEOUT_DEFAULT = 590` | R-05~R-08, R-13 |
| C-02 | `skills/ppt-master/scripts/confirm_ui/server.py:189-197` `_json_sha256`, `:1030-1044` `_result_stage`, `:1101-1121` `_stage1_sha256`·`_fresh_template_restart`·`_active_recommendations_path` | 정규 JSON digest 정의, 결과 유효 조건(`stage1`+`stage1-confirmed` 또는 `final`+`confirmed`), 라운드 무효화 조건, active stage 파일 유도 | R-04, R-11~R-13 |
| C-03 | `skills/ppt-master/scripts/confirm_ui/server.py:2079-2167` `_wait_only_for_result`·`_wait_result_status`, `:2755-2801` `build_parser`, `:2804-2960` `main` | `--wait-only` 종료 코드(0/1/2/124)와 기다림 루프, 옵션 기본값, `--daemon` 중복 거부 | R-06~R-08 |
| C-04 | `skills/ppt-master/scripts/confirm_ui/server.py:742-786` `_read_template_installation`·`_stage1_ready_error`·`_stage2_ready_error`, `:2563-2752` `confirm` | 진행 가드(Stage 2 직접 검증), 제출 시 stage·선행 검사, 서버가 영수증을 쓰는 순서 | R-11, R-15, R-16 |
| C-05 | `skills/ppt-master/scripts/confirm_ui/server.py:2170-2210` `_shutdown_existing` | `--shutdown` 순서(graceful → SIGTERM → lock 삭제)와 멱등 | R-10 |
| C-06 | `skills/ppt-master/scripts/svg_editor/annotations.py:241-257`, `:228-238`, `skills/ppt-master/scripts/check_annotations.py:31-60` | 주석 마커 `data-edit-target="true"`·`data-edit-annotation` 쓰기·지우기·스캔 정의 | R-24, R-25, R-28 |
| C-07 | `skills/ppt-master/scripts/svg_editor/static/app.js:618-709`, `:2028-2033`, `:3199-3202` | 라이브 미리보기 자동 갱신(2초 poll, 새 페이지 목록 반영, mtime 배너, 쓰는 중 페이지 재선택) | R-21 |
| C-08 | `skills/ppt-master/scripts/server_common.py:282-296` `claim_lock` | lock 파일 `{"pid","port"}`와 죽은 pid 덮어쓰기 | R-06, R-20 |
| C-09 | `skills/ppt-master/scripts/svg_editor/server.py:1136-1272` `save_all` | Apply changes가 SVG를 쓰는 순서: digest 검사, 편집 적용, 마커 쓰기, 임시 id 제거, 원자적 교체, `edits.jsonl`·`annotations.jsonl` 기록, 실패 시 staged 유지 | R-22~R-24 |

### 1.6 수락 사례 [필수]

출처: 모두 구현에서 도출(서버를 실행하지 않고 코드를 읽어 도출. 원본 테스트는 R-04의 Origin 허용 한 곳만 열었다).

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-05, R-06 | `confirm_ui/recommendations.stage1.json`에 `template_options`가 없다. `--daemon` | 오류 로그, exit 1, 서버 안 뜸 |
| T-02 | R-06 | 같은 프로젝트에 확정 서버가 이미 살아 있다. `--daemon` 다시 | exit 1(pid·포트 안내). 기존 서버는 그대로 |
| T-03 | R-07 | 사용자가 Stage 1을 제출한 뒤에 agent가 `--wait-only --wait-stage stage1` 시작 | 서버 복구나 대기 없이 즉시 exit 0 |
| T-04 | R-07 | Stage 1을 590초 안에 제출하지 않는다 | exit 124, 서버는 살아 있음. agent는 `result.json`을 한 번 확인한 뒤 chat 대체와 `--shutdown`(선행 R-19) |
| T-05 | R-08 | Stage 1 확정 직후 설치를 하지 않고(templates 모드) `--wait-only` | `template_install.json` 검증 실패로 즉시 exit 1 |
| T-06 | R-08 | `recommendations.stage2.json`의 `selection_sha256`가 `template_selection.json`과 다르다. `--wait-only` | 즉시 exit 1 |
| T-07 | R-12 | Stage 1 확정 뒤 agent가 `recommendations.stage1.json`의 `audience` 값을 고친다 | `result.json.stage1_sha256`이 불일치해 결과가 무효. Stage 2가 열리지 않고 화면은 새 Stage 1을 다시 보여 준다 |
| T-08 | R-12 | 같은 선택으로 새 라운드를 원한다 | stage1 파일의 `revision`만 바꾼다. 서식만 바꾸면 digest가 같아 라운드가 시작되지 않는다 |
| T-09 | R-04 | agent가 stage1 파일에서 digest를 계산해 `result.json`을 `stage: final, status: confirmed`로 직접 쓴다 | 서버는 stage1 digest만 맞으면 `--wait-only`를 exit 0으로 풀어 준다(서명 없음). 이것은 규칙 위반이지만 코드가 막지 않는다 |
| T-10 | R-10 | 서버가 없는데 `--shutdown` | "nothing to stop" 로그, exit 0 |
| T-11 | R-20 | 같은 프로젝트에서 `--live --daemon`을 두 번 | 두 번째는 기존 서버를 재사용하고 URL을 알리며 exit 0 |
| T-12 | R-21 | live 모드에서 agent가 `svg_output/slide_06.svg`를 새로 쓴다 | 열린 브라우저의 페이지 목록에 약 2초 안에 나타난다. 보고 있는 페이지는 바뀌지 않는다 |
| T-13 | R-21 | 사용자가 slide_03을 보는 중 agent가 slide_03.svg를 고친다 | reload 배너가 뜨고 클릭하면 새 내용을 읽는다 |
| T-14 | R-22 | 사용자가 slide_03에 Direct edit를 staged로 둔 채 agent가 slide_03.svg를 다시 쓴 뒤 사용자가 Apply | slide_03은 "SVG changed on disk after these changes were staged" 실패로 staged에 남는다 |
| T-15 | R-24, R-28 | 사용자가 slide_02의 요소 `title`에 주석 후 Apply, agent가 `check_annotations.py` | `slide_02.svg` 아래에 `<text id="title">`과 주석이 출력되고 exit 0 |
| T-16 | R-28 | `svg_output/`의 slide_04.svg가 XML 오류 | stderr에 `[ERROR] Failed to parse SVG ...`, exit 1 |
| T-17 | R-25 | `exports/`에 `.pptx`가 없는 상태에서 주석 적용 요청 | 적용하지 않고 주 파이프라인을 먼저 끝내라고 안내 |
| T-18 | R-25, R-27 | 주석을 모두 적용했다 | 마커 제거, `annotation_applied` 기록 뒤 7.2 → 7.3을 다시 돌려 새 timestamp의 PPTX가 생기고 이전 PPTX는 남는다(선행 R-47) |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`, 실행 기록 링크) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | `skills/ppt-master/references/confirm-surface.md:5-21`, `workflows/generate-pptx.md:128-152` | 문서 선언. 분기를 강제하는 코드는 찾지 못했다(R-04의 검색 범위와 같다) |
| R-03 | `workflows/generate-pptx.md:130`, `references/confirm-surface.md:11-13` | 문서 선언 |
| R-04 | C-02 `server.py:189-197`, `:1030-1044`, `:1106-1112`; `server.py:766-786`; `server.py:2327-2343` `_update_activity`(Host/Origin); `server.py:2563-2752` `confirm`(인증 없음); 테스트 `scripts/tests/test_local_server_security.py:53-59`(`Origin` 없음 허용) | **검색**: `grep -rniE "hmac\|secrets\.\|token\|nonce\|signature" scripts/confirm_ui/server.py`는 `_typography_signature`뿐이라 인증 코드가 없다. `grep -rn "result\.json\|RESULT_NAME\|confirm_ui" --include='*.py' skills/ppt-master/scripts`에서 tests와 `confirm_ui/server.py`를 제외하면 `apply_template.py:645`(`template_selection.json`만 읽음), `server_common.py:6`(주석), `svg_editor/server.py:172`(주석)뿐이다. **범위**: `skills/ppt-master/scripts`의 `*.py`. **놓쳤을 가능성**: 다른 디렉터리의 gate, 비Python 스크립트, OS 파일 권한 같은 코드 밖 보호, `.json`/`.md` 안의 검사 지시. **결론**: 검색 범위 안에서 agent의 직접 쓰기를 거부하는 코드는 없다 → **선행 U-02를 닫는다**(닫는 근거는 이 행, 선행 스펙은 이 결론을 반영하도록 고치는 것을 제안) |
| R-05 | `server.py:856-870` `_confirmation_launch_error`, `:754-763` `_stage1_ready_error`, `:2896-2900`(`--daemon`·포그라운드 경로에서만 호출), `:2826-2829` | `--wait-only` 분기는 이 검사 앞에서 반환하므로 R-05는 launch에만 적용 |
| R-06 | `server.py:879-924` `_wait_for_server_ready`, `:927-969` `_launch_background_server`, `:2902-2935`, `:2327-2362`, `server_common.py:282-296`, `confirm_ui.md:45-54` | `--daemon`의 중복 거부는 `:2902-2915`. idle 시계는 `before_request`가 모든 요청에서 갱신(`:2343`) |
| R-07 | C-03 `server.py:2133-2167`, `:2838-2899` | 종료 코드는 `return` 문 직접 확인(`:2128` 124, `:2152`·`:2166` 2, 준비 오류와 서버 사망 1) |
| R-08 | `server.py:766-786`, `:2079-2130`, `:2838-2870`; 브라우저 쪽 `confirm_ui/static/app.js:4428-4437` | `_stage2_ready_error`가 파일 없음(OSError)과 `ApplyTemplateError`(`apply_template.py:63`, `ValueError` 하위)를 모두 오류 문자열로 바꾼다. production 검증은 `_read_active_recommendations`(`:1124-1149`)에만 있고 wait 경로는 부르지 않는다(`grep -n "_stage2_production_recommendations_error" server.py`: `:1145`, `:1197` 정의뿐) |
| R-09 | `server.py:2133-2167` | `grep -n "mtime\|st_mtime" confirm_ui/server.py`는 `_file_version`(session 표시용)만 쓴다(`:1788`) |
| R-10 | C-05 `server.py:2170-2210`, `:2833-2835`, `confirm_ui.md:51`, 비교: `svg_editor/server.py:1295-1343`(health 소유권 검사 있음) | 선행 R-18·R-19의 "항상 `--shutdown`"과 같은 규칙 |
| R-11 | `server.py:742-786`, `:1124-1149`, `:1616-1695`, `:2460-2560`, `:2563-2752`, `apply_template.py:460-500` `read_template_install`, `confirm_ui.md:334-342` | `confirm_ui.md`는 "File timestamps do not authorize progression"을 선언하고 코드에도 시간 비교가 없다 |
| R-12 | C-02, `server.py:453-530`(`options_sha256` 구성), `:714-740`(`_read_template_selection`), `:2460-2475`(`final` 후 409), `confirm_ui.md:52`, `:305-308` | `revision`이 digest를 바꾸는 것은 digest가 stage1 파일 전체이기 때문이며 `_json_sha256`은 `sort_keys`·공백 없음으로 서식을 무시한다(`:189-197`) |
| R-13 | `server.py:1115-1121`, `workflows/generate-pptx.md:132`, `confirm_ui.md:296-303` | 접미사 파일이 읽히지 않는 것은 `RECOMMENDATION_STAGE_NAMES`가 두 이름만 가진 것(`:88-91`)에서 추론 |
| R-14 | `server.py:1124-1149`, `:1197-1280`, `:2380-2410`(health), `:2460-2560` | production 필드 목록은 `confirm_ui.md:392-405`. 화면에서 오류가 어떻게 보이는지는 소스에서 도출 |
| R-15 | C-04 `server.py:2563-2752`, `:789-853`, `confirm_ui/static/app.js:4296-4311`, `:4415-4437` | `formula_policy` 제거는 `:2717-2718`. 구형 필드 제거는 `:2722-2723` |
| R-16 | `apply_template.py:57`, `:460-500`, `:635-650`, `server.py:742-751`(검증), `:1868`(session이 `template_install.json` 버전만 표시), `reports/.../generate-default-pipeline.md` R-18 | 문서의 위치 불일치(`references/artifact-ownership.md:43`)는 선행 스펙 2.1에 이미 기록 |
| R-17 | `server.py:47`, `svg_editor/server.py:41`, `spec_review/server.py:42`, `skills/ppt-master/requirements.txt:122` | 세 파일이 모듈 최상단에서 `from flask import ...`를 한다. import 실패 시 `main`까지 가지 않으므로 `--shutdown`도 막힌다는 것은 코드 구조에서 도출(실행 안 함) |
| R-20 | `svg_editor/server.py:1295-1343`, `:1346-1454`, `:1503-1678`, `workflows/generate-pptx.md:253-259`, `svg_editor.md:5-26`, `server_common.py:282-296` | `--live`에서 `svg_output/` 자동 생성은 `:1526-1530`. 실패해도 막히지 않음은 `generate-pptx.md:259`의 "side process: never wait" 선언 |
| R-21 | C-07; 서버 쪽 `svg_editor/server.py:761-848` `get_slides`(mtime 포함), `scripts/slide_roster.py:45-47` `discover_slide_svgs`; 서버 `/api/config`의 `live` 플래그 `:710-722` | **확인한 것**: 폴링 간격 2000 ms(`app.js:2028-2033`), `startSlidePolling`은 `liveMode`가 아니면 즉시 반환(`:2029`). 목록 재렌더와 자동 선택·배너 분기(`:620-709`). **"SSE·WebSocket 없음"**: `grep -n "EventSource\|WebSocket" svg_editor/static/app.js svg_editor/static/index.html`와 `grep -n "stream\|sse" svg_editor/server.py`(범위: svg_editor 디렉터리)에서 못 찾았다. 놓쳤을 가능성: 다른 이름의 push 구현, 외부 라이브러리 |
| R-22 | `svg_editor/server.py:535-640`(`_persist_draft`·`_restore_draft`), C-09 `:1136-1272`, `svg_editor.md:21-23`, `:39` | 복원 규칙의 digest 조건은 `svg_editor.md`와 `_restore_draft` 구조에서 읽음. `_restore_page` 내부는 읽지 않음 |
| R-23 | C-09, `svg_editor/server.py:990-1115`(`/edit`), `svg_editor.md:12`, `:19`, `:36-38` | 속성별 검증 규칙은 읽지 않음 |
| R-24 | C-06, C-09, `svg_editor/server.py:944-987`, `:327-350`, `:1231-1246`, `svg_editor/annotations.py:345-363` | `annotation_*` 로그 기록 위치는 `:1231-1246` |
| R-25 | `workflows/stages/live-preview.md:24-41`, `workflows/generate-pptx.md:320-340` | 문서 선언. `annotation_applied` 줄을 쓰거나 읽는 코드는 `svg_editor`에 없다: `grep -rn "annotation_applied" --include='*.py' --include='*.md' --include='*.js' skills/ppt-master`(tests 제외)에서 `live-preview.md:38`, `spec_review/store.py:318`, `spec_review.md:114`만 나온다 |
| R-26 | `workflows/generate-pptx.md:259` | 문서 선언 |
| R-27 | `svg_editor/server.py` 전체, `svg_editor.md:25` | **검색**: `grep -n "subprocess\.\|finalize\|svg_to_pptx" svg_editor/server.py`에서 `svg_editor/server.py:105`(`svg_to_pptx.geometry_properties` import, 기하 도우미)와 서버 자신을 띄우는 `_popen_detached`(`:1586`)뿐이다. **범위**: `svg_editor/server.py`. **놓쳤을 가능성**: `annotations.py`·정적 JS에서의 외부 호출(서버 API가 없으면 JS도 export를 부를 수 없다) |
| R-28 | C-06 `check_annotations.py:31-146` | 종료 코드는 `main` 직접 확인(`:117-146`) |
| R-30 | `workflows/stages/refine-spec.md:1-54`, `scripts/docs/spec_review.md:1-130`, `spec_review/server.py:63`, `:200-231`, `:233-240`, `:244-352`, `check_spec_annotations.py:1-62`, `generate-pptx.md:154` | 흐름은 문서 선언. 옵션·lock·idle 기본값은 `build_parser`·`main` 직접 확인. 블록 분할·렌더러·Apply 내부는 읽지 않음 |
| T-01~T-18 | 위 근거 행 | 모두 코드 읽기에서 도출. 서버를 실행하지 않았다 |

**문서와 구현 차이**
- `references/artifact-ownership.md:43`은 `template_install.json`을 `confirm_ui/`와 같은 행에 두지만 코드는 프로젝트 루트다(선행 스펙 2.1과 동일).
- `confirm_ui.md:51`(`--shutdown` "Tries a graceful /api/shutdown")은 소유권 확인을 말하지 않는다. 코드도 확인하지 않아 일치하지만, `svg_editor.md:19`는 health 소유권을 확인한다고 선언하고 코드도 그렇다. 두 서버의 `--shutdown` 안전성이 다르다는 점은 문서 어디에도 한 줄로 정리돼 있지 않다.
- 선행 스펙 `generate-default-pipeline.md` 1.3.5(`:136`)는 "`--wait-only`는 준비 오류나 서버 종료는 1"이라고 쓴다. 코드는 stage 건너뜀과 Stage 1 영수증 오류에 **exit 2**를 쓴다(`server.py:2152`, `:2166`). 선행 스펙은 2를 말하지 않는다.

### 2.2 코드 읽는 순서 [선택]

1. 연동자가 가장 먼저: `references/confirm-surface.md`(§1 표면, §2~§4 payload) → `scripts/docs/confirm_ui.md` "`confirm_ui/server.py`"(`:31-69`, 명령·포트·lock)와 "Current two-stage flow"(`:294-342`) → `confirm_ui/server.py`의 `main`(`:2804`)·`_wait_only_for_result`(`:2079`)·`_stage2_ready_error`(`:766`)·`confirm`(`:2563`). 약 3,000줄 중 위 구간이면 실행 계약이 정해진다. 나머지(`:200-740` 템플릿 후보 빌더, `:1172-1760` Stage 2 검증)는 화면 내부다.
2. 미리보기: `scripts/docs/svg_editor.md`와 `workflows/stages/live-preview.md`(둘 다 40줄대) → `svg_editor/server.py`의 `main`(`:1503`)·`save_all`(`:1136`) → `static/app.js`의 `loadSlides`(`:620`)·`startSlidePolling`(`:2028`). 서버의 편집 검증·SVG 정제(`:136-330`)와 `app.js`의 나머지 약 2,500줄은 화면 내부다.
3. 주석: `check_annotations.py`(150줄, 전부)와 `svg_editor/annotations.py`의 마커 함수(`:228-257`).
4. spec 리뷰(선택): `scripts/docs/spec_review.md`(220줄)와 `workflows/stages/refine-spec.md`(54줄)와 `spec_review/server.py`의 `build_parser`·`main`(`:233-352`).

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 점검만. 이 스펙에 `depends`로 의존하는 스펙이 없다.
- 대조한 R-ID: R-04(`result.json` 신뢰 조건이 `stage`·`status`와 stage1 digest뿐이고 작성자 구분 없음, `confirm_ui/server.py:189-197`, `:1030-1044`, `tests/test_local_server_security.py:53-59`, `result.json`을 읽는 비테스트 코드는 `confirm_ui/server.py`뿐), R-21(폴링 2초, `svg_editor/static/app.js:2028-2033`), R-07의 종료 코드 2(`server.py:2152`, `:2166`), R-10(`--shutdown`이 소유권 확인 없이 SIGTERM, `server.py:2196-2208`), 템플릿 설치 검증 위치(`server.py:742-751`). 선행 스펙 U-02는 R-04로 닫혔고, 이 스펙의 U-01~U-03은 "원본이 정하지 않은 것"으로 옮겼다(`annotations.jsonl`을 읽는 코드와 `recommendation_error`를 설명하는 문서가 없음을 grep으로 확인).
- 대조하지 않은 R-ID: 그 외 전부. 특히 R-01~R-03, R-25, R-26, R-30은 문서 선언(agent 규칙)이고, R-11·R-12·R-15의 진행 가드·라운드 무효화·영수증 쓰기 순서와 R-22·R-28은 작성자 확인만 있다. 라이브 미리보기 자동 갱신은 브라우저에서 실행해 보지 않았다.
- 재구현: 미수행

## 적용 메모 [선택]

연동 환경에서 정할 점이다. 원본의 미결정을 여기서 해소한 것으로 치지 않는다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-04 | (제안, 미확정) agent 환경에서 `confirm_ui/result.json`과 `template_selection.json`을 agent 프로세스의 쓰기 권한 밖에 두거나(읽기 전용 마운트, 별도 사용자), agent가 쓴 적이 없다는 증거(서버 `confirm_ui/server.log`의 `... confirmation written to ...` 로그 줄과 파일 mtime 대조)를 후속 gate가 확인 | 서버는 작성자를 인증하지 않으므로 신뢰 경계는 환경이 정해야 한다 | Step 4 gate에 한 단계가 늘어난다. 원본 동작은 바뀌지 않는다 |
| R-08 | (제안, 미확정) `--wait-only`가 124로 끝나면 agent가 `GET /api/health`의 `recommendations`와 `confirm_ui/session.json`의 `recommendation_error`를 읽어, 타임아웃이 사용자 미응답인지 stage2 파일 오류인지 구분 | 원본은 둘을 같은 124로 돌려준다(위 "원본이 정하지 않은 것") | 선행 R-19의 chat 대체 전에 확인 한 번 |
| R-21 | (제안) 사용자 안내 문구를 "새 페이지는 자동으로 목록에 뜨고, 보던 페이지가 바뀌면 배너를 눌러 새로고침"으로 쓴다 | 소스상 보던 페이지는 자동 재렌더되지 않는다(확인 한계) | 안내 문구 |
