---
sha: "34f519533bc175d2fe287ab8316b0dd99bb9cc43"
created: 2026-11-18
updated: 2026-11-18
---

# CLI-Anything Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/HKUDS/CLI-Anything`
- **작업트리 상태**: Clean (`git status --short` 0줄). shallow clone(`--depth 50`)
- **분석 목적**: 방법론 이해. 에이전트가 앱 하나를 CLI 하니스로 만들 때 따르는 **공통 형식**, 지원하는 **패밀리(하니스 분류)와 그 위치·역할**, 결과를 **하나의 skill(`SKILL.md`)로 패키징**하는 경로까지 본다. 개별 하니스의 내부 구현은 필요할 때만 연다. 스펙은 Claude Code에서 비슷한 "앱 → CLI + skill" 생성 절차를 설계할 때의 참고 재료로 쓴다.
- **라이선스**: Apache License 2.0 — `LICENSE`, `cli-anything-plugin/LICENSE`(같은 Apache 2.0). 앱별 `agent-harness/setup.py` classifier는 69개 중 51개가 `MIT License`, 2개가 `Apache`로 적혀 있어 루트 라이선스와 다르다(`grep` 확인). 각 하니스에 별도 LICENSE 파일은 없다(`git ls-files | grep -i license` 2건).
- **분석 대상 제품**: 한 레포 안의 여러 배포 단위다. ① `cli-anything-plugin/`(제작 방법론과 도구), ② `<software>/agent-harness/`(앱별 CLI 69개, 각각 PyPI 패키지 `cli-anything-<software>`), ③ `skills/`(앱별 `SKILL.md` 카탈로그, 디렉터리 70개 + `README.md`), ④ `cli-hub/`(설치 관리자 `cli-anything-hub`), ⑤ 에이전트별 어댑터(`codex-skill/`, `hermes-skill/`, `reasonix-skill/`, `cursor-plugin/`, `opencode-commands/`, `qoder-plugin/`).
- **스펙 범위**: 2026-11-18 승인: 행 1~5(기존 제안 8행을 5행으로 합침) · 제외: 행 6~9(이유: 부속, 요청 범위 공통 형식·패밀리·skill 패키징 밖)

---

## 2. 프로젝트 개요

CLI-Anything은 GUI 앱이나 웹 서비스를 코딩 에이전트가 쓸 수 있는 CLI로 바꾸는 **방법**을 모은 레포다. 하나의 통합 CLI가 아니고, 앱마다 별도 CLI(`cli-anything-gimp`, `cli-anything-blender` 등)를 만들되 같은 규약을 따르게 한다. 규약의 원본은 `cli-anything-plugin/HARNESS.md`(747줄)이고, 에이전트가 `/cli-anything <소스 경로 또는 URL>` 명령으로 이 문서를 읽고 7단계(분석 → 설계 → 구현 → 테스트 계획 → 테스트 → 테스트 문서 → PyPI 배포)를 따라 하니스를 만든다. 각 하니스가 만든 `SKILL.md`는 `skills/`에 모이고, `npx skills add HKUDS/CLI-Anything --skill <id>`로 설치된다.

사용자가 처음 가정한 "`skills/`만 보면 된다"는 절반만 맞다. `skills/`는 산출물 카탈로그이고, 같은 형식으로 만드는 방법은 `cli-anything-plugin/`에 있다(코드 확인: `skills/README.md`, `.github/scripts/sync_root_skills.py:_discover_sources`).

### Feature map

| # | 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|---|
| 1 | 하니스 제작 절차 (SOP·규칙·제작 명령) | 에이전트가 앱 소스를 받아 7단계로 하니스를 만든다. 지켜야 할 규칙(실제 앱 필수 의존, `--json`, REPL 기본, E2E 필수 등)과 명령 5종(`/cli-anything` build, `refine`, `test`, `validate`, `list`)을 정한다. 코드가 아니라 문서 계약이다 | `cli-anything-plugin/HARNESS.md` "General SOP", "Principles & Rules"(480줄~), `cli-anything-plugin/commands/*.md` | 없음 | 핵심 | [`capabilities/harness-sop.md`](./capabilities/harness-sop.md) · draft | 코드 확인(HARNESS.md와 명령 문서 5개 전부). 문서 규칙 대 구현 차이는 스펙 2.1. 미결정 5(실행 기록이 있어야 닫힘) |
| 2 | 하니스 계약 (CLI 표면 + 패키지 레이아웃) | 모든 하니스가 같은 방식으로 호출된다: `cli-anything-<sw> [--json] <group> <cmd>`, 하위 명령 없이 실행하면 REPL, 프로젝트는 JSON 세션 파일(undo/redo는 파일이 아니라 프로세스 메모리), 오류 JSON 형식은 하니스마다 갈린다(`error`+`type` 35 외 변형 다수). 패키지는 `<sw>/agent-harness/` 아래 `setup.py`, PEP 420 namespace(`cli_anything/`에 `__init__.py` 금지), `core/`·`utils/<sw>_backend.py`·`tests/`·`skills/SKILL.md`, `console_scripts`로 `cli-anything-<sw>` 등록 | 대표 `gimp/agent-harness/cli_anything/gimp/gimp_cli.py:117-141`, `gimp/agent-harness/setup.py`, `cli-anything-plugin/repl_skin.py:106 ReplSkin`, `HARNESS.md:672-` | 1 | 핵심 | [`capabilities/harness-contract.md`](./capabilities/harness-contract.md) · draft | 코드 확인(gimp 정독 + gimp·firefly-iii·jumpserver를 scratchpad에서 실행). 69개 일괄 수치는 스펙 2.1에서 재해석: `console_scripts` 67(setup.py 기준, unimol_tools는 pyproject.toml), `ReplSkin(` 실제 호출 57, REPL 진입 패턴(`ctx.invoke(...repl...)`) 49. 미결정 0 |
| 3 | 하니스 카탈로그(패밀리) | 어떤 앱이 어떤 방식으로 연결되는지의 분류표. 백엔드 방식 7종(AST 스캔 69개 전수): `exec`(실행 파일 호출) 30, `http` 20, `sdk` 7, `file`(파일 직접 조작) 5, `mcp` 2, `mixed` 2, `solo` 3. 앱별 위치·역할은 스펙 2.1과 [harness-catalog.tsv](../../artifacts/CLI-Anything/harness-catalog.tsv)(TSV의 문자열 휴리스틱은 24행이 틀려 스펙이 정정안을 제시, TSV는 미수정) | `registry.json`(79항목, `category` 31종), `<sw>/agent-harness/cli_anything/<sw>/utils/<sw>_backend.py`, `cli-anything-plugin/guides/mcp-backend.md` | 2 | 핵심 | [`capabilities/harness-families.md`](./capabilities/harness-families.md) · draft | 코드 확인(표본: `exec` 13·`http` 7 열람, 나머지 5개 패밀리는 전부 열람) + AST 스캔 / 열람하지 않은 하니스의 소속은 추론. 미결정 3(분류 기준 등) |
| 4 | SKILL.md 생성·루트 `skills/` 동기화 | 하니스 디렉터리에서 `SKILL.md`를 자동 생성한다(README 첫 문단→소개, `setup.py`→버전, Click 데코레이터→명령 그룹 표, Jinja2 템플릿). 이어서 하니스 안 `SKILL.md`를 `skills/cli-anything-<id>/SKILL.md`로 복사하며 `name` frontmatter를 정규화하고, CI가 일치를 검사한다 | `cli-anything-plugin/skill_generator.py:116 extract_cli_metadata`, `:248 extract_commands_from_cli`, `:377 generate_skill_md`, `templates/SKILL.md.template`, `.github/scripts/sync_root_skills.py:_discover_sources,_canonical_skill_id`, `cli-anything-plugin/repl_skin.py:131-156`, `validate_root_skills.py`, `.github/workflows/check-root-skills.yml`, `skills/README.md` | 2 | 핵심 | [`capabilities/skill-packaging.md`](./capabilities/skill-packaging.md) · draft | 코드 확인(생성기·sync·validate 전체) / 생성기와 validate는 실행하지 않음. skill id 규칙이 생성기·sync·`ReplSkin` 세 곳이고 하니스 4개(`3MF`, `QGIS`, `cc-switch`, `iterm2`)에서 결과가 다름. 미결정 1 |
| 5 | 레지스트리 항목 형식 | 하니스·외부 CLI를 한 목록으로 기술한다: `name`, `entry_point`, `install_cmd`, `skill_md`, `category`, `requires`, `contributors` 등. 외부 CLI는 `package_manager`·`npm_package` 추가. `generate_meta_skill.py`는 추적되지 않는 `cli-hub-skill/SKILL.md`를 만들고(`:12`), 추적되는 `cli-hub-meta-skill/SKILL.md`는 수기 문서다 | `registry.json`(하니스 79), `public_registry.json`(외부 CLI 24), `.github/scripts/generate_meta_skill.py`, `.github/scripts/update_registry_dates.py` | 2, 3, 4 | 핵심 | [`capabilities/registry-schema.md`](./capabilities/registry-schema.md) · draft | 코드 확인(JSON 키 분포, 항목 전수 점검, `generate_meta_skill.py` 읽고 scratchpad 실행). 미결정 2 |
| 6 | 프리뷰 번들 프로토콜 | 중간 결과를 `manifest.json`+`summary.json`+산출물 디렉터리로 내보내는 선택 계약(`preview-bundle/v1`), 라이브 프리뷰는 `session.json`+`trajectory.json` | `docs/PREVIEW_PROTOCOL.md`, `cli-anything-plugin/guides/preview-methodology.md`, `cli-anything-plugin/preview_bundle.py` | 2 | 부속 | — · 미작성 | 코드 확인(문서 앞부분) / 하니스 중 `preview` 언급 16개(문자열 점검) |
| 7 | cli-hub (설치·검색·매트릭스·프리뷰 뷰어) | `cli-hub install/list/search/info/launch`, `matrix preflight/install`, `previews open` | `cli-hub/cli_hub/cli.py`(1,048줄), `installer.py:106 _install_strategy`, `matrix.py`, `preview.py`(1,839줄) | 5 | 부속 | — · 미작성 | 코드 확인(명령 등록부·설치 전략 분기) / 본문 미탐색 |
| 8 | 에이전트별 어댑터 | `HARNESS.md`를 각 에이전트(Codex, Hermes, Reasonix, Cursor, OpenCode, Qoder)용 SKILL·명령으로 이식한다. 설치 스크립트가 `cli-anything-plugin/` 자원을 복사한다 | `codex-skill/SKILL.md`, `codex-skill/scripts/install.sh`, `hermes-skill/`, `reasonix-skill/`, `cursor-plugin/`, `opencode-commands/`, `qoder-plugin/setup-qodercli.sh`, `.pi-extension/cli-anything/` | 1 | 부속 | — · 미작성 | 코드 확인(`codex-skill/SKILL.md` 앞부분) / 나머지는 디렉터리 목록만 |
| 9 | 문서 사이트·워크플로 번들 | `docs/hub/`(허브 웹사이트, `llms.txt`, `openapi.json`), `cli-hub-matrix/<워크플로>/SKILL.md` 5종, `cli-hub-meta-skill/SKILL.md` | `docs/hub/`, `cli-hub-matrix/`, `cli-hub-meta-skill/SKILL.md`(수기 문서) | 5, 7 | 부속 | — · 미작성 | 미확인(목록과 meta-skill 앞부분만) |

> 2026-11-18 사용자 결정으로 처음 제안한 핵심 8행을 5행으로 합쳤다. 같은 문서·같은 파일을 읽는 행끼리 묶었다(제작 SOP+명령, CLI 표면+패키지 레이아웃, SKILL.md 생성+루트 동기화).

**공유 계약** (여러 기능이 같이 쓰는 형식. 별도 스펙 없이 소유 행에 둔다는 제안)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| C1. 하니스 디렉터리 → SKILL.md 위치 규칙 (패키지 안 `skills/SKILL.md`는 행 2, 루트 `skills/<id>/SKILL.md`와 `name` 정규화는 행 4가 소유) | 2, 4 | `sync_root_skills.py:_canonical_skill_id`, `HARNESS.md` Phase 6.5 | 소유 행 2·4(나눠 소유) | 코드 확인 |
| C2. 세션 JSON·`--json` 오류 형식 | 2, 4(예시 생성), 6 | `gimp_cli.py`, `guides/session-locking.md` | 소유 행 2 | 코드 확인(gimp) |

**대조한 범위와 미탐색 영역**

- 대조: README, `HARNESS.md` 전체 절 제목과 Phase 6.5·Directory Structure·Principles, `commands/cli-anything.md` 앞부분, `skill_generator.py` 함수 목록과 핵심 3함수, `skills/README.md`, `sync_root_skills.py`, `registry.json`·`public_registry.json`·`matrix_registry.json` 키 분포, `cli-hub` 명령 등록부, `gimp` 하니스 구조와 `gimp_cli.py` 공통 옵션, 69개 하니스 일괄 문자열 점검(임시 스크립트로 실행, 결과만 `artifacts/CLI-Anything/harness-catalog.tsv`에 보관. 스크립트는 레포에 두지 않음).
- 문서와 구현의 차이(코드 확인. 상세와 검색 범위는 각 스펙 2.1):
  - `HARNESS.md`는 `cli_anything/__init__.py`를 두지 말라고 하지만 8개 하니스(chromadb, comfyui, godot, intelwatch, obsidian, pm2, seaclip, videocaptioner)에는 0바이트 파일이 있다. godot wheel에는 들어가지 않았다(빌드 확인), 나머지 7개는 추론.
  - "실제 앱 필수, fallback 금지"는 코드에서도 어겨진다: gimp `core/export.py:67-84`는 GIMP 예외를 삼키고 Pillow로 렌더, drawio `core/export.py:110-130`은 CLI가 없으면 `.drawio` 파일만 저장, freecad 테스트는 앱이 없으면 skip.
  - `HARNESS.md`와 `guides/auto-save-dry-run.md:61-67`은 "REPL은 자동 저장하지 않는다"고 쓰지만 REPL 종료 시 자동 저장이 돈다(gimp 실행 확인).
  - 세션 파일에 undo/redo가 들어간다는 `save_session` docstring과 달리 실제로는 저장하지 않는다(`gimp/.../core/session.py:129-144`, 실행 확인).
  - `validate.md`가 요구하는 파일을 대부분의 하니스가 갖추지 못했다(`core/session.py` 40, `core/export.py` 21, `core/project.py` 23개).
  - `skills/README.md`는 루트 `skills/`가 canonical이라 하지만 `sync_root_skills.py`는 하니스 안 파일을 소스로, 루트를 생성물로 덮어쓴다.
  - skill id를 정하는 규칙이 생성기·sync·`ReplSkin` 세 곳에 따로 있다(하니스 4개에서 결과가 다름).
  - `registry.json`: `category`는 31종 자유 문자열(`science`/`scientific` 등 중복 후보), freecad는 registry `1.1.0`인데 `setup.py`는 `1.0.0`, `skill_md` 형태 4종 혼재, registry 항목을 검증하는 자동 검사 없음.
  - 이전 문자열 점검 수치(`--json` 65, `invoke_without_command=True` 64, `ReplSkin` 62)는 의미가 달랐다. 위 행 2의 재해석을 따른다.
- 미탐색: 개별 하니스의 `core/` 구현 69개(목적상 제외, 필요할 때 연다), `tests/`·CI 설정, 번역본 README, `cli-hub/cli_hub/preview.py`와 `analytics.py` 본문, 이미지·데모 자산.
- 구조도(archify)는 아직 그리지 않았다.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

미작성. 범위 승인 뒤 그린다.

---

## 4. 질문 (Questions)

- [q1-cli-hub](./questions/q1-cli-hub.md): `cli-hub`는 무엇이고 README 설치 흐름은 실제와 같은가 (코드 확인 + 실행 확인)
- [q2-hub-catalog](./questions/q2-hub-catalog.md): `cli-hub list`의 103개(harness 79 + public 24)는 각각 무엇을 지원하는가 (registry 확인, 개별 CLI 동작은 미확인)

### 범위 승인 기록

2026-11-18 사용자가 "5개로 해도 될 것 같다"고 답해 행 1~5를 승인했다. 행 6~9는 제외(부속).

**다음 작업**: [next.md](./next.md)
