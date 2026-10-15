# Skills Manager Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/xingkongliang/skills-manager`
- **분석 Commit SHA**: `e6dcedf968f3f0ebf62e24edf5d90ec8cbf23509` (2026-10-15, 앱 v1.42.0)
- **분석 일자**: `2026-10-15`
- **작업트리 상태**: `Clean`
- **분석 목적**: 학습. cc-switch(`reports/cc-switch/questions/q5-skills-mcp-management.md`)의 스킬 관리 방식과 비교하기 위한 초기 파악

> 초기 작업(1차)이다. README, 디렉터리 구조, 스킬 배포 경로 하나(`sync_skill_to_tool`)만 코드로 읽었다. 그 외 영역은 `미확인`. 테스트와 앱 실행은 하지 않았다.

---

## 2. 프로젝트 개요

Claude Code, Codex, Cursor 등 AI 코딩 에이전트의 **스킬(SKILL.md 폴더)을 한 곳(중앙 라이브러리)에서 관리하고 각 에이전트 폴더로 배포**하는 Tauri 2 데스크톱 앱 + CLI. React 19 프런트엔드, Rust 백엔드(`src-tauri`), 상태는 SQLite(`rusqlite`).

- **중앙 라이브러리**: 기본 `~/.skills-manager` (설정으로 이동 가능). 에이전트 폴더에는 symlink로 배포하고, Windows에서 실패하면 junction, 그것도 안 되면 copy로 폴백한다. (코드 확인: `core/sync_engine.rs:292`)
- **에이전트 54개**: `default_tool_adapters()`가 각 에이전트의 skills 폴더 상대경로를 하드코딩한다 (코드 확인: `core/tool_adapters.rs:147-876`, 항목 수 직접 셈). 사용자 정의 에이전트도 가능.
- **Preset(scenario)**: 스킬 묶음. DB 테이블명은 `scenarios`. 적용은 한 번 복사하는 방식이지 실시간 동기화가 아니라고 README가 설명한다 (README 기준, 미검증).
- **에이전트가 직접 관리**: 앱이 `manage-skills` 스킬을 설치하고 CLI 복사본을 `~/.skills-manager/bin`에 둔다. 에이전트가 폴더를 몰래 만지는 대신 CLI를 쓰게 해 메타데이터를 유지한다 (`skills/manage-skills/SKILL.md`, `core/cli_bridge.rs:175`).
- **앱과 CLI가 같은 core 공유**: CLI(`bin/skills-manager-cli.rs`)도 `scenario_service`/`sync_engine`을 직접 호출한다 (코드 확인: 같은 파일 1254, 1368행).
- 그 밖: git 기반 백업·다기기 동기화(`git_backup.rs`, `merge/`), skills.sh 마켓플레이스, 프로젝트 단위 workspace. 규모는 `src` + `src-tauri/src` 약 7.2만 줄(i18n JSON 5개 포함).

### 주요 기능

근거 표기: **README**는 README 설명, **구조**는 코드의 모듈·명령·CLI 서브커맨드 존재만 확인(동작은 미검증), **코드 확인**은 동작 코드까지 읽음. 이번 세션에서 동작까지 읽은 것은 "에이전트 배포"와 "덮어쓰기 보호"뿐이다.

| 기능 | 하는 일 | 근거 |
|---|---|---|
| **스킬 설치(수집)** | Git 저장소, 로컬 폴더, `.zip`/`.skill` 압축, skills.sh 마켓플레이스에서 가져와 중앙 라이브러리에 저장. CLI는 `skills install <경로·URL·owner/repo@skill>` | README, 구조(`installer.rs`, `git_fetcher.rs`, `skillssh_api.rs`, `InstallSkills.tsx`) |
| **에이전트 배포(동기화)** | 스킬별로 에이전트를 켜고 끈다. 카드의 에이전트 배지를 눌러 설치/제거. symlink → junction → copy 폴백 | **코드 확인**(`sync_engine.rs:292`, `scenario_service.rs:852`) |
| **덮어쓰기 보호** | 앱이 만들지 않은 폴더는 덮어쓰지 않고 충돌로 보고 | **코드 확인**(`ReplacePolicy`, `sync_engine.rs:111`) |
| **에이전트 54종 지원** | 에이전트별 skills 폴더 경로 내장. 사용자 정의 에이전트와 경로 재지정 가능. 설치 여부 감지 | **코드 확인**(`tool_adapters.rs:147`) |
| **Preset(scenario)** | 스킬 묶음을 이름 붙여 두고 한 번에 켜고 끈다. 에이전트별 토글 기록(`scenario_skill_tools`) | README, 구조(`presets.rs` 명령 13개, `scenario_service.rs`). "한 번 복사" 의미는 미검증 |
| **Global / Agent Workspace** | 에이전트별 전역 폴더의 스킬 전체를 보여 준다(앱 밖에서 설치한 것 포함). All Agents 개요 | README, 구조(`agent_workspace.rs`, `WorkspaceView.tsx`) |
| **Project Workspace / Linked Workspace** | 프로젝트 폴더의 `.claude/skills` 등을 중앙 라이브러리와 비교·양방향 동기화. 임의 디렉터리를 skills 루트로 연결 | README, 구조(`projects.rs` 명령 17개, `project_scanner.rs`, `ProjectDetail.tsx`) |
| **가져오기(adopt)·스캔** | 이미 에이전트 폴더에 있는 스킬을 라이브러리로 편입. CLI `skills adopt <경로> --dry-run` | README, 구조(`scanner.rs`, `commands/scan.rs`). 같은 이름 충돌은 [Q1](./questions/q1-same-name-conflict-and-overwrite.md) |
| **태그·검색·일괄 작업** | 태그 부여, 소스·태그 필터, 다중 선택 후 일괄 활성/비활성·내보내기·삭제, 명령 팔레트 | README, 구조(`skill_tags` 테이블, `skillTags.ts`, `CommandPalette.tsx`) |
| **업데이트 추적** | Git 기반 스킬의 상류 변경 확인, 로컬 스킬 재가져오기, 원본과 diff 비교 | README, 구조(`skill_auto_updater.rs`, `SkillSourceDiffViewer.tsx`, CLI `skills check/update`) |
| **미리보기·출처 확인** | `SKILL.md`/`README.md` 렌더링, 소스 메타데이터 | README, 구조(`SkillMarkdown.tsx`, `skill_metadata.rs`) |
| **백업·다기기 동기화** | 비공개 GitHub 저장소(또는 임의 git remote)에 자동 백업, skill 단위 병합, 충돌 시 keep mine/remote/both, 스냅샷 복원 | README, 구조(`git_backup.rs`, `core/merge/`, `commands/git_backup.rs` 명령 24개, CLI `git`) |
| **CLI** | `repo` · `tools` · `skills`(list/show/install/deploy/status/sync/adopt/check/update/tag…) · `presets` · `git`. 앱과 같은 core·DB 사용 | **구조**(`skills-manager-cli.rs`의 clap 서브커맨드), README |
| **에이전트 자기 관리** | Dashboard 한 번 설정으로 `manage-skills` 스킬을 설치하고 CLI를 `~/.skills-manager/bin`에 게시. 에이전트가 CLI로 설치·배포·조회 | README, 구조(`skills/manage-skills/SKILL.md`, `cli_bridge.rs`) |
| **활동 로그·로그 내보내기** | 설치/삭제/업데이트/동기화 기록, Settings에서 로그 zip 내보내기 | README, 구조(`audit_log.rs`, `log_sanitize.rs`) |
| **앱 설정·편의** | 저장소 경로 이동, 동기화 모드(symlink/copy), 테마·글자 크기·언어(영/중/한/스페인어), 트레이, 프록시, 에이전트 순서, 인앱 업데이트 | README, 구조(`settings.rs` 명령 19개, `src/i18n` 5개 언어) |

README가 밝힌 한계: Windows 앱은 WSL 안에 링크를 만들 수 없어 복사만 가능하다. WSL 쪽 에이전트는 Linux CLI를 WSL 안에서 따로 돌려야 한다 (README 기준).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 구조 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | UI/CLI → 공유 Rust core → 에이전트 폴더 |
| 대표 흐름 | [deploy-flow.json](./diagrams/deploy-flow.json) | [deploy-flow.html](./diagrams/deploy-flow.html) | 스킬을 에이전트에 켜는 `sync_skill_to_tool` |

검증: archify `finalize` 자동 게이트(validate/deliver/check/browser-check) 통과. 시각 검토는 하지 않음.

### 그림 읽는 가이드
1. 구조도는 왼쪽 UI → `commands/sync.rs` → `scenario_service`(배포 결정) → `sync_engine`(파일 변경) → 에이전트 폴더 순.
2. `scenario_service`가 "어디에, 어떤 모드로, 덮어써도 되는가"를 결정하고, `sync_engine`은 실행만 한다. 결과는 `skill_targets` 테이블에 기록된다.
3. 미확인: git 백업/병합, 마켓플레이스 설치, file_watcher의 재스캔은 그림에 없다.

### 코드로 확인한 핵심 (deploy 경로)
- 에이전트 미설치·비활성이면 배포를 거부한다 (`scenario_service.rs:852` 이하).
- **덮어쓰기 정책 `ReplacePolicy`** (`sync_engine.rs:111`): 배포 기록(`skill_targets`)이 없으면 `NoClobber`(사용자 파일을 지워야 하면 거부), 기록이 있으면 `Recorded{mode}`(기록한 mode와 현재 타입이 같은 것만 삭제), 사용자 확인(adopt/--force)은 `UserConfirmed`. 코드 주석이 이슈 #363(데이터 유실)을 언급한다.
- 같은 skills 폴더를 여러 에이전트가 공유하면 `target_path`를 참조하는 행이 남아 있는 한 파일을 지우지 않는다 (`commands/sync.rs` `unsync_skill_for_tool_in_preset`).
- **cc-switch와 비교(가설)**: cc-switch는 재동기화 때 다른 앱 폴더가 원본으로 덮어써진다(q5, 실행 확인). skills-manager는 소유권 기록이 없으면 거부하는 쪽이다. 같은 시나리오 실행은 후속 질문 Q1.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

- [Q1: 같은 이름·다른 내용 스킬과 덮어쓰기 처리 (cc-switch 비교)](./questions/q1-same-name-conflict-and-overwrite.md) - *해시로 별개 스킬 구분, 소유권 기록 없으면 덮어쓰기 거부 후 충돌 보고. 코드 읽기만, 실행 검증은 아직.*

나머지 제안 질문은 [next.md](./next.md) 참고.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/skills-manager.md](../../wiki/projects/skills-manager.md)
