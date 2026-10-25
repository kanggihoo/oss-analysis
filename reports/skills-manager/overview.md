---
sha: "7a2219219287f4ef4c543fc169ebcc5b0bff085c"
created: 2026-10-15
updated: 2026-10-24
---

# Skills Manager Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/xingkongliang/skills-manager`
- **기준 SHA**: `7a22192` (2026-10-22, `v1.43.0` 뒤 2커밋). 이전 기준 `e6dcedf`(2026-10-15, v1.42.0)에서 갱신했다.
- **작업트리 상태**: `Clean`
- **분석 목적**: 학습. cc-switch(`reports/cc-switch/questions/q5-skills-mcp-management.md`)의 스킬 관리 방식과 비교
- **라이선스**: MIT (`LICENSE`, "Copyright (c) 2026 Tianliang Zhang"). 하위 디렉터리에 다른 LICENSE 없음 (`find . -name 'LICENSE*'`로 확인)
- **분석 대상 제품**: Tauri 2 데스크톱 앱(`src/` React 19 + `src-tauri/` Rust) 한 개와, 같은 Rust crate의 두 번째 바이너리 `skills-manager-cli`(`src-tauri/src/bin/skills-manager-cli.rs`). 중첩 패키지·별도 서버 없음. 에이전트용 스킬 `skills/manage-skills/SKILL.md` 하나가 같이 배포된다.
- **스펙 범위**: 2026-10-24 사용자 승인 — 외부 스킬 설치(Git·skills.sh·well-known), 스킬 출처 메타데이터(공유 계약에서 분리), 변경 확인, 원본 diff 4개. 제외: 위 4개 밖의 모든 행 — 사용자 범위 제한(요청: 외부 스킬 설치와 원본 변경 확인에 한정). 배경: 개인 스킬 저장소 `my-skills`가 남의 스킬을 래핑하므로 "원본이 바뀌었는지, 무엇이 바뀌었는지"가 필요하다. 이전 단계(지도만)는 같은 날 먼저 끝냈다.

> 이번 갱신은 기능 지도를 새로 쓴 것이다. 읽은 것은 README, `package.json`, `src-tauri/src/lib.rs`의 명령 등록부, CLI의 clap 정의, 어댑터 표, 각 `core/` 모듈의 머리 주석과 공개 함수 목록이며, 동작 본문은 배포 경로(`sync_engine.rs`, `scenario_service.rs`)만 다시 읽었다. 빌드·실행·테스트는 하지 않았다.

### 이전 기준(`e6dcedf`) 대비 달라진 점

`git diff e6dcedf..7a22192`: 52개 파일, +4189/−400. 추가 파일은 `core/git_command.rs`, `src/lib/skillSource.ts`, `src/components/PresetBar.test.tsx`, `REVIEW.md`, `public/agent-icons/minimax_code.png` 다섯 개다.

| 항목 | 이전 문서 | 지금 (코드 확인) |
|---|---|---|
| 내장 에이전트 수 | 54 ("직접 셈") | **58** (Coding 49 + Lobster 9, `tool_adapters.rs` `default_tool_adapters`). 이전 SHA에서도 `category: ToolCategory::` 줄이 56개라 이전 문서의 54는 틀렸다. |
| 에이전트 추가 | — | MiniMax Code, WorkBuddy AI(해외판, `~/.workbuddy-ai/skills`)가 새 어댑터 (`CHANGELOG.md` 1.43.0, 어댑터 코드 확인) |
| Tauri 명령 수 | 모듈별 개수만 | `generate_handler!`에 **124개** (settings 19, skills 26, git_backup 24, projects 17, presets 13, tools 11, agent_workspace 5, sync 4, scan 3, browse 2). 이전 문서의 모듈별 개수(`presets` 13, `projects` 17, `git_backup` 24, `settings` 19)와 같다. |
| 배포 정책 | `ReplacePolicy` 3종 | 그대로 `NoClobber` / `Recorded{mode}` / `UserConfirmed` (`sync_engine.rs:111`). 다만 `sync_desired_targets`가 "다른 에이전트가 같은 경로에 살아 있는 배포를 갖고 있으면 그 폴더를 지우지 않는다"는 처리를 갖는다 (`scenario_service.rs:388`~). `CHANGELOG.md` 1.43.0에 따르면 `sync_skill_to_active_scenario`에도 같은 처리가 추가됐다 (#595, 문서 근거). |
| 에이전트 폴더가 옮겨질 때 | 미기록 | 옛 경로의 복사본을 지우지 않고 보존 폴더로 옮긴다 (`scenario_service.rs` `move_into_kept_copies`, 이름만 확인. 동작 본문은 미확인) |
| git 자식 프로세스 | `git_fetcher.rs`·`git_backup.rs`에 각각 | `core/git_command.rs` 하나로 합침. Linux AppImage에서는 `LD_LIBRARY_PATH`를 상속하지 않는다 (`CHANGELOG.md` 1.42.2, 문서 근거) |
| My Skills | 태그·검색 | 출처(source)별 필터·그룹 추가 (`src/lib/skillSource.ts`, `MySkills.tsx`, 1.43.0) |
| 앱 버전 | 1.42.0 | 1.43.0 |

**기존 질문 문서 재확인 필요**: [Q1](./questions/q1-same-name-conflict-and-overwrite.md)과 [Q2](./questions/q2-core-concepts-and-auto-update.md)가 인용한 `scenario_service.rs`, `installer.rs`, `agent_workspace.rs`, `git_backup.rs` 등이 이번 구간에서 바뀌었다(Q2는 `skills.rs`, `sync.rs`, `git_fetcher.rs`, `tool_adapters.rs`, `skill_store.rs`, `browse.rs`도). 두 문서는 `e6dcedf` 기준 사실로 읽고, 다시 볼 때 새 SHA에서 확인한다 (워크플로 5장).

---

## 2. 프로젝트 개요

Claude Code, Codex, Cursor 등 AI 코딩 에이전트의 **스킬(`SKILL.md`가 든 폴더)을 하나의 중앙 라이브러리에 모아 두고 각 에이전트 폴더로 배포**하는 Tauri 2 데스크톱 앱과 CLI다. 상태는 SQLite(`rusqlite`)에 있고, 앱·CLI·트레이가 같은 Rust `core/`를 호출한다.

- **중앙 라이브러리**: 기본 `~/.skills-manager`. 에이전트 폴더에는 symlink로 배포하고 Windows에서 실패하면 junction, 그다음 copy로 폴백한다 (코드 확인: `core/sync_engine.rs:292` `sync_skill`, Windows 분기).
- **앱 시작 때 도는 백그라운드 일**: CLI 브리지 게시 `cli_bridge::ensure_bridge`(`lib.rs:904`), 파일 감시 `file_watcher::start_file_watcher`(`:923`), 자동 업데이트 `skill_auto_updater::start`(`:930`), 병합 복구 `merge::recover_on_startup`(`:941`), 자동 백업 `auto_backup::start`(`:950`) (코드 확인: 호출 줄).
- **프런트엔드 라우트**: `/`(Dashboard), `/my-skills`, `/global-workspace[/:agentKey]`, `/lobster-workspace[/:agentKey]`, `/install`, `/backup`, `/project/:id`, `/settings` (코드 확인: `src/App.tsx`).
- 규모: `wc -l`로 센 `commands/*.rs`, `core/*.rs`, `bin/*.rs`, `lib.rs` 합계가 43,801줄이다(`core/merge/`와 `main.rs`는 합계에 없음). 가장 큰 파일은 `commands/skills.rs` 4,745줄, `bin/skills-manager-cli.rs` 3,727줄, `core/git_backup.rs` 3,450줄.

### 기능 지도

<!-- 한 행 = 스펙 하나의 작업 단위. 분할과 경로는 제안이다. -->

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 외부 스킬 설치 (Git · skills.sh · well-known) | Git URL·`owner/repo`·skills.sh 항목·skills.sh 사이트 URL(`https://skills.sh/site/<domain>/<skill>` 형태만) → 임시 폴더로 받아 미리보기 후 확정 → 중앙 라이브러리 입고, 출처 기록. 배포는 포함하지 않음 | `commands/skills.rs` `install_git`, `preview_git_install`, `confirm_git_install`, `install_from_skillssh`, `install_site_skill_dir`, `cancel_install`; `core/git_fetcher.rs`, `well_known.rs`, `installer.rs`; CLI `skills install` | 스킬 출처 메타데이터 | 핵심 | [skill-install-external](capabilities/skill-install-external.md) · ready | 코드 확인(R-01~R-26). 실행 안 함 |
| 로컬 설치·폴더 일괄 가져오기·압축 | 로컬 폴더·`.zip`/`.skill`을 라이브러리로 입고 | `commands/skills.rs` `install_local`, `batch_import_folder`; `core/installer.rs` `PreparedSource` | 스킬 출처 메타데이터 | 핵심 | `capabilities/skill-install-local.md` · 미작성 (제외: 사용자 범위) | 구조 |
| skills.sh 리더보드·검색 | 마켓플레이스 목록과 키워드 검색(설치 경로는 목록이 준 `(source, skill_id)`만 받는다) | `commands/browse.rs` `fetch_leaderboard`, `search_skillssh`; `core/skillssh_api.rs`; UI `views/InstallSkills.tsx` | 없음 | 부속 | `capabilities/skills-sh-browse.md` · 미작성 (제외: 사용자 범위) | 구조 |
| 에이전트 배포·덮어쓰기 보호 | 스킬을 에이전트마다 켜고 끄기 → 에이전트 skills 폴더에 symlink/junction/copy. 기록 없는 사용자 파일은 덮어쓰지 않고 충돌로 보고. 한 폴더를 여러 에이전트가 공유할 때 | `commands/sync.rs` `sync_skill_to_tool`, `unsync_skill_from_tool`, `get_skill_tool_toggles`, `set_skill_tool_toggle`; `core/scenario_service.rs` `sync_desired_targets`, `sync_single_skill_to_tool`; `core/sync_engine.rs` `sync_skill`, `ReplacePolicy` | 중앙 라이브러리·상태, 에이전트 어댑터 | 핵심 | `capabilities/agent-deploy.md` · 미작성 | 코드 확인(정책 enum, `sync_skill`, `sync_desired_targets` 앞부분) / 미확인(나머지 분기, copy 모드 해시 비교, 실행) |
| Preset(scenario) | 스킬 묶음을 이름 붙여 만들고(`create`), 에이전트 범위에 적용·해제. 부분 적용 표시. 트레이에서 켜고 끄기. DB 이름은 `scenarios` | `commands/presets.rs`(13개 명령); `core/scenario_service.rs` `apply_scenario_to_default`, `set_active_preset_tool_toggles`, `apply_skills_to_tools`; `lib.rs` `TRAY_PRESET_ADD_PREFIX`; UI `components/PresetBar.tsx` | 에이전트 배포 | 핵심 | `capabilities/presets.md` · 미작성 | 구조(등록부·함수 목록) / 미확인(적용 의미: README는 "한 번 복사, 실시간 아님") |
| Global·Agent Workspace | 에이전트별 전역 폴더의 스킬 전체(앱 밖 설치분 포함) 보기, 라이브러리와 비교, 라이브러리로 올리기·라이브러리에서 갱신·삭제. Coding·Lobster 두 분류 | `commands/agent_workspace.rs`(5개 명령); UI `views/WorkspaceView.tsx`, `views/workspaceConfigs.ts` | 에이전트 어댑터, 에이전트 배포 | 핵심 | `capabilities/global-workspace.md` · 미작성 | 구조(명령·라우트 확인) / 미확인(본문) |
| Project·Linked Workspace | 프로젝트 폴더의 `.claude/skills` 등 에이전트별 프로젝트 경로를 라이브러리와 비교·양방향 동기화. 임의 폴더를 skills 루트로 연결 | `commands/projects.rs`(17개 명령); `core/project_scanner.rs` `read_project_skills`, `read_linked_workspace_skills`, `scan_projects_in_dir`; UI `views/ProjectDetail.tsx` | 에이전트 어댑터, 에이전트 배포 | 핵심 | `capabilities/project-workspace.md` · 미작성 | 구조 / 미확인(본문) |
| 스캔·adopt | 에이전트 폴더에 이미 있는 스킬을 찾아(`scan`) 라이브러리로 편입(`adopt`), 같은 이름 충돌 처리 | `commands/scan.rs` `scan_local_skills`, `import_existing_skill`, `import_all_discovered`; `core/scanner.rs` `scan_local_skills`, `group_discovered`; CLI `skills adopt` | 에이전트 어댑터, 중앙 라이브러리·상태 | 핵심 | `capabilities/scan-adopt.md` · 미작성 | 구조 / 이전 SHA에서 [Q1](./questions/q1-same-name-conflict-and-overwrite.md)이 일부를 읽음(재확인 필요) |
| 라이브러리 관리 | My Skills 목록, 태그 부여·이름 변경·삭제, 검색, 출처·태그 필터와 그룹, 다중 선택 일괄 작업, `SKILL.md`·`README.md` 미리보기 | `commands/skills.rs` `get_managed_skills`, `get_skill_document`, `set_skill_tags`, `rename_tag`, `delete_tag`, `delete_managed_skills`; UI `views/MySkills.tsx`, `lib/skillTags.ts`, `lib/skillSource.ts`, `lib/skillSearch.ts`, `components/CommandPalette.tsx` | 중앙 라이브러리·상태 | 핵심 | `capabilities/library-management.md` · 미작성 | 구조 / 미확인(본문) |
| 스킬 원본 변경 확인 | 스킬마다 "원본이 바뀌었나"를 판정해 `update_status` 등을 기록. git·skillssh는 원격 head와 `source_revision` 비교(모노레포 하위 폴더는 자기 폴더 변경만), local·import는 원본 폴더 해시 비교, well-known은 확인하지 않음. 한 스킬·전체, TTL·`force`, CLI `skills check` | `commands/skills.rs` `check_skill_update`, `check_all_skill_updates`, `prefetch_skill_remote`, `check_skill_update_internal_with_remote`; `core/git_fetcher.rs` `resolve_remote_revision`, `unchanged_subtrees`; CLI `run_check` | 스킬 출처 메타데이터 | 핵심 | [skill-update-check](capabilities/skill-update-check.md) · ready | 코드 확인(R-01~R-28), 순수 git 동작 하나 실행 확인(R-21). 앱 실행 안 함 |
| 스킬 원본과 사본의 차이 (source diff) | 라이브러리 스킬의 원본 문서를 보여 주고(`get_source_skill_document`), 원본과 사본의 파일 단위 추가·삭제·변경을 돌려준다(`get_skill_source_diff`). git·skillssh·local·import 가능, well-known 거절. UI 전용(CLI diff 없음) | `commands/skills.rs` `get_skill_source_diff`, `get_source_skill_document`, `build_source_diff_entries`; `core/content_hash.rs`; UI `components/SkillSourceDiffViewer.tsx`, `DocumentDiffViewer.tsx` | 스킬 출처 메타데이터 | 핵심 | [skill-source-diff](capabilities/skill-source-diff.md) · ready | 코드 확인(R-01~R-24), 순수 git 동작 하나 실행 확인(R-19). 앱 실행 안 함 |
| 갱신 적용·출처 재연결 | 변경을 가져와 라이브러리 사본을 통째로 교체(`update_skill`, `batch_update_skills`), 로컬 폴더 재가져오기, `set-source`(local→git, `--dry-run`·`--force`), relink·detach, 교체로 사라질 파일 확인과 승인 토큰. 병합·충돌 감지는 없다 | `commands/skills.rs` `update_git_skill_internal`, `set_git_source_internal`, `reimport_local_skill_internal`, `relink_local_skill_source`, `detach_local_skill_source`, `pending_removals_for`, `swap_skill_directory`; `core/removals.rs`; UI `views/MySkills.tsx` `ConfirmDialog`; CLI `update`·`set-source` | 스킬 출처 메타데이터, 변경 확인, 외부 스킬 설치(임시 체크아웃 계약), 에이전트 배포·덮어쓰기 보호(copy 모드 사본 재동기화 경계), Git 체크아웃 획득 | 핵심 | [skill-update-apply](capabilities/skill-update-apply.md) · ready | 코드 확인(R-01~R-42), 판단 규칙을 파이썬으로 옮겨 실행 확인(T-01~T-10, 소스 대체 범위는 스펙 2.3). 앱 실행 안 함 |
| 주기적 자동 확인·트레이 확인 | 앱 시작 후 15분 주기 스케줄러와 트레이 메뉴가 변경 확인을 호출, 옵트인이면 적용 | `core/skill_auto_updater.rs` `start`; `lib.rs` 트레이 확인 | 변경 확인, 갱신 적용(R-42) | 핵심 | `capabilities/skill-auto-update.md` · 미작성 (제외: 사용자 범위) | 구조 + 변경 확인 R-24, R-25가 호출 입구를 기술 |
| 백업·스냅샷 (Git remote) | 비공개 GitHub 저장소(디바이스 플로 로그인) 또는 임의 Git remote에 라이브러리를 커밋·푸시·풀, 스냅샷 태그·복원, 자동 백업, 첫 실행 복원 선택, 자격증명은 OS 키체인 | `commands/git_backup.rs`(24개 명령); `core/git_backup.rs` `init_repo`, `set_remote`, `commit_all`, `push`, `pull`, `create_snapshot_tag`, `restore_snapshot_version`; `core/auto_backup.rs`; `core/git_credentials.rs`; `core/git_command.rs`; UI `views/Backup.tsx`; CLI `git` | 중앙 라이브러리·상태, skill 단위 병합 엔진 | 핵심 | `capabilities/git-backup.md` · 미작성 | 구조 + 모듈 머리 주석(자격증명 정책, 자동 백업 설계) 확인 / 미확인(본문) |
| skill 단위 병합 엔진 | 두 기기의 라이브러리를 skill(객체) 단위로 3-way 병합, 충돌은 keep mine/remote/both, 대기 항목(`pending`) 관리, 시작 때 복구. `merge_engine=system`이면 줄 단위 git 병합으로 되돌림 | `core/merge/mod.rs` `object_merge_pull_unlocked`, `recover_on_startup`, `SETTING_MERGE_ENGINE`; `merge/protocol.rs`, `decision.rs`, `resolve.rs`, `snapshot.rs`, `treebuild.rs`, `pending.rs`, `validate.rs` | 중앙 라이브러리·상태 | 핵심 | `capabilities/merge-engine.md` · 미작성 | 구조(모듈 목록, `mod.rs` 주석·상수) / 미확인(알고리즘) |
| CLI | `skills-manager-cli [--json] [--skills-root]` 아래 `repo`, `agents`(별칭 `tools`), `skills`, `presets`(별칭 `scenarios`), `git`. 앱과 같은 core·DB 사용 | `src-tauri/src/bin/skills-manager-cli.rs` `Commands`, `SkillsCommand`(list/show/export/install/update/check/remove/enable/disable/deploy/undeploy/status/sync/search/set-source/adopt/tag), `PresetCommand`, `GitCommand`, `ToolsCommand`, `RepoCommand` | 스킬 설치, 에이전트 배포, Preset, 스캔·adopt, 업데이트 추적, 백업·스냅샷 | 핵심 | `capabilities/cli.md` · 미작성 | 코드 확인(clap 서브커맨드 열거) / 미확인(각 핸들러, 앱과 동시 실행 시 잠금 동작) |
| 에이전트 자기 관리 | Dashboard에서 한 번 설정하면 `manage-skills` 스킬을 고른 에이전트에 배포하고, CLI 복사본을 `~/.skills-manager/bin`에 게시. 에이전트는 이 CLI로만 설치·배포·조회 | `core/cli_bridge.rs` `ensure_bridge`(`lib.rs:904`에서 호출); `skills/manage-skills/SKILL.md`; UI `components/AgentControlSetupCard.tsx`, `views/Dashboard.tsx` | CLI, 에이전트 배포 | 핵심 | `capabilities/agent-self-management.md` · 미작성 | 코드 확인(호출 지점, 모듈 머리 주석, SKILL.md의 CLI 해석 절차) / 미확인(`ensure_bridge` 본문) |
| 외부 변경 감시 | 에이전트 폴더·라이브러리 변경을 감지해 UI에 알림. 앱이 방금 쓴 경로는 일정 시간 알림 억제 | `core/file_watcher.rs` `start_file_watcher`, `mute_self_writes`(`sync_engine.rs`에서 호출) | 중앙 라이브러리·상태 | 핵심 | `capabilities/file-watcher.md` · 미작성 | 코드 확인(시작 호출, `mute_self_writes` 호출) / 미확인(재스캔 본문) |
| 앱 설정·트레이·중앙 저장소 이동 | 저장소 경로 이동(다음 실행에 적용, 이동 못 하는 경로는 설정 때 거부), 동기화 모드, 테마·글자 크기·언어, 프록시, 트레이 메뉴(Preset 토글·업데이트 확인), 에이전트 순서, 닫기 동작 | `commands/settings.rs`(19개 명령); `lib.rs` 트레이 상수·메뉴 구성; `core/central_repo.rs`; `core/migrations.rs`; UI `views/Settings.tsx` | 중앙 라이브러리·상태 | 부속 | `capabilities/app-settings.md` · 미작성 | 구조 / 미확인(본문) |
| 활동 로그·진단 | 설치·삭제·업데이트·동기화 기록, 로그 zip 내보내기(민감값 제거), 마지막 패닉 기록 | `core/audit_log.rs`, `core/log_sanitize.rs`, `core/panic_log.rs`; `commands/settings.rs` `export_logs_zip`, `get_diagnostic_info`, `check_last_panic` | 중앙 라이브러리·상태 | 부속 | `capabilities/audit-diagnostics.md` · 미작성 | 구조(파일·명령 이름) / 미확인(본문) |
| UI 셸·i18n | 사이드바·레이아웃, 명령 팔레트, 테마, 5개 언어(en/es/ko/zh-TW/zh) | `src/App.tsx`, `src/components/Layout.tsx`, `Sidebar.tsx`, `src/context/*`, `src/i18n/*.json`, `scripts/check-i18n.mjs` | 없음 | 부속 | `capabilities/ui-shell.md` · 미작성 | 코드 확인(라우트, 언어 파일 5개) / 미확인(나머지) |
| 릴리스·인앱 업데이트 | 앱 새 버전 확인·설치(알림만, 설치·재시작은 사용자 확인). 설치 파일 배포(brew cask, scoop, `.dmg`/`.exe`/`.msi`/`.AppImage`/`.deb`/`.rpm`) | `commands/settings.rs` `check_app_update`, `update_install_blocker`; `src-tauri/tauri.conf.json` `updater`; `.github/workflows/release.yml`, `prepare-release.yml`; `scripts/prepare-release.mjs` | 없음 | 부속 | `capabilities/app-release.md` · 미작성 | 구조(설정 키·파일 존재) / 미확인(워크플로 본문은 기본 제외 영역) |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| **스킬 출처 메타데이터** (`skills` 행의 출처 필드 11개의 의미, `source_type` 5값, `update_status` 값, 값을 쓰는 연산, 메타데이터 파일로 나가는 부분집합과 reindex 복원 규칙, 내용 해시 범위) | 외부 스킬 설치, 변경 확인, 원본 diff, 갱신 적용, 스캔·adopt | `core/skill_store.rs` `SkillRecord`; `core/sync_metadata.rs` `write_skill_file`, reindex; `core/content_hash.rs` | [skill-source-metadata](capabilities/skill-source-metadata.md) · ready | 코드 확인(R-01~R-18). 실행 안 함 |
| 중앙 라이브러리·상태 (나머지: SQLite 다른 테이블, 라이브러리 폴더 레이아웃, 저장소 락 `repo_lock.rs`, 프리셋·멤버십 메타데이터 파일) | 지도의 거의 모든 행 | `core/central_repo.rs`, `core/migrations.rs`, `core/repo_lock.rs`, `core/sync_metadata.rs` | `capabilities/library-and-state.md` · 미작성 | 구조 |
| Git 체크아웃 획득 (clone·캐시·sparse·정리, `resolve_skill_dir`, `find_skill_dir`, `parse_git_source`) — 신규 후보 | 외부 스킬 설치, 원본 diff, 갱신 적용 (세 소비자. 변경 확인은 `resolve_remote_revision`·`unchanged_subtrees`만) | `core/git_fetcher.rs`; `commands/skills.rs` `resolve_skill_dir` | `capabilities/git-checkout.md` · 미작성. 지금은 설치 스펙 R-04, R-05가 설치 관점으로, 원본 diff 스펙이 "입력·정상 결과·오류 종류" 경계로 다룬다 | 구조(호출 지점은 서브에이전트 보고) |
| 에이전트 어댑터 레지스트리 (58개 내장, 사용자 정의, 경로 재지정, 설치 감지, 프로젝트 경로) | 에이전트 배포, 두 Workspace, 스캔, Preset, CLI, 설정 | `core/tool_adapters.rs` `default_tool_adapters`, `ToolAdapter`, `ToolCategory`; `core/tool_service.rs`; `commands/tools.rs`(11개 명령) | `capabilities/agent-adapters.md` · 미작성 | 코드 확인(개수·분류), 항목별 경로는 하드코딩 표라 패밀리로 묶을 수 있음(추론) |

**대조한 범위와 미탐색 영역**
- 대조: README의 Features 목록 18개 항목, `lib.rs`의 `generate_handler!` 124개 명령, CLI clap 열거(`Commands`·`SkillsCommand`·`PresetCommand`·`GitCommand`·`ToolsCommand`·`RepoCommand`), `src/App.tsx` 라우트, `src/views/*`, `core/*.rs` 파일 목록 전부.
- 문서와 구현의 차이: 이전 overview의 "에이전트 54개"는 틀렸다(이전 SHA에서도 56). README는 에이전트 수를 숫자로 적지 않는다(`CHANGELOG.md` 1.43.0이 MiniMax Code, WorkBuddy AI 추가를 설명). README의 "Applying a preset is a one-time copy"는 코드로 확인하지 않았다.
- 문서와 구현의 차이(이번 스펙 4개에서 새로 발견, 근거는 각 스펙 2.1): ① README의 "Git-based skills 확인, local은 re-import"와 달리 변경 확인은 local·import의 원본 폴더 해시 비교까지 한다. ② `manage-skills/SKILL.md`의 "check는 dry-run"은 틀리다(상태 열을 쓴다). ③ 주석 `lib.rs:544`(트레이 확인은 status 열만 바꾼다)는 틀리다(확인이 `source_ref_resolved`·`source_subpath`·`source_branch`·조건부 `source_revision`도 쓴다). ④ 주석 `git_fetcher.rs:1233`(옛 revision 하나가 없으면 그 쌍만 빠진다)는 틀리다(fetch 한 번이 실패하면 그 원격의 모든 쌍이 빠진다, 실행 확인). ⑤ DTO 주석(`skills.rs:255-257`)의 "update 배지가 뜨면 diff가 비지 않는다"는 성립하지 않는다(확인은 줄바꿈 차이를 무시하고 diff는 무시하지 않음, 실행 비트 비교 방식도 다름, git 배지는 해시가 아니라 리비전 기준). ⑥ `manage-skills/SKILL.md:88`의 Git 설치 예시와 달리 `install_git`(앱)과 CLI `--git`은 스킬 목록을 열거하지 않고 폴더 하나를 한 스킬로 복사한다(루트에 `SKILL.md`가 없으면 `skills/` 폴더 전체가 한 스킬). 경로를 읽어 도출했고 실행하지 않았다. ⑦ 갱신 적용 쪽: `content_changed` 주석(`skills.rs:29-30`)·`SetSourceResult` 주석·`SKILL.md:238`은 재시작 전에만 참이다(저장 해시는 앱·CLI 시작 reindex가 디스크 해시로 덮는다). `SKILL.md`의 "refreshed: true vs already up-to-date"는 local·import에서 성립하지 않는다.
- 미탐색: `core/merge/` 본문, `git_backup.rs`·`git_fetcher.rs`·`git2_engine.rs` 본문, `installer.rs` 압축 처리, `file_watcher.rs` 재스캔, `cli_bridge.rs` 본문, `crypto.rs`, `app_state.rs`, 프런트엔드 컴포넌트 본문. 기본 제외 영역(CI 설정, `*.test.*`, 번역·변경 이력, `docs/`)은 열지 않았다. `CHANGELOG.md`는 이번 갱신 대비표에 한해 읽었고 그 내용은 `문서 근거`로 표시했다.
- 이전 diagrams(`diagrams/structure.*`, `deploy-flow.*`)는 `e6dcedf` 기준이며 이번에 다시 만들지 않았다.


### 스펙 통합 검토 (2026-10-24)

승인 범위 5개(외부 설치, 출처 메타데이터, 변경 확인, 원본 diff, 갱신 적용·출처 재연결)는 모두 `ready`다. `ready`는 "선언한 범위에서 행동 규칙이 정해졌고 구현을 막는 모순·미결정이 없다"는 뜻이며, 재구현으로 원본과 같은지 검증한 것은 아니다(재구현 검증 미실행). 보고: **재현 준비 완료(승인 범위 한정) — ready 5 / draft 0 / 미작성은 범위 밖 행 전부**.

1. **지도에서 빠진 행**: 없다. 승인 범위에서 쓰지 않은 행은 모두 `미작성`이고, 이번에 새로 쪼갠 행(로컬 설치, skills.sh 탐색, 자동 확인)과 새 공유 계약 후보(Git 체크아웃 획득)는 "제외: 사용자 범위"로 표시했다.
2. **경계·상태 소유자·공유 정의**: `skills` 행의 출처 필드는 `skill-source-metadata`가 소유하고 나머지 넷이 읽거나 쓰는 규칙만 둔다. `source_type` 5값(`git`, `skillssh`, `well-known`, `local`, `import`), `update_status` 값, 내용 해시 범위(무시 목록·실행 비트)가 다섯 문서에서 같다. 조율하며 고친 것: ① 변경 확인이 상태 4열만 쓴다고 쓴 메타데이터 문서의 서술을 고쳤다(정규화·`source_revision` 이동도 씀). ② 설치 스펙의 미결정(메타데이터 파일 규칙)을 메타데이터 문서 R-11, R-18로 해소했다. ③ well-known 설치의 직접 경로와 미리보기 확정 경로의 값 차이를 메타데이터 문서에 반영했다. ④ 갱신 적용 스펙이 발견한 누락을 반영했다: 메타데이터 R-08에 relink·detach를 추가하고 `update_status` 표에 재가져오기·relink의 보류 복원과 `updating` 잔존 경로를 적었으며, 변경 확인에 R-29(재시작 뒤 reindex가 `content_hash`를 디스크 해시로 덮으므로 손 수정한 local·import 사본이 `update_available`이 될 수 있음)를 추가했다. 스펙 사이 모순이 아니라 **원본 자체의 불일치**로 남긴 것: 변경 확인의 줄바꿈 무시 vs diff의 비무시(변경 확인 R-09, 원본 diff R-17), 배지(리비전 기준, 변경 확인 R-01·R-14)와 diff(내용 기준, 원본 diff R-13~R-17)의 어긋남.
3. **선행 스펙과 C-ID**: `depends`는 메타데이터 `[]`, 설치·변경 확인·diff는 메타데이터, 갱신 적용은 메타데이터·변경 확인·설치 셋이다(순환 없음). C-ID는 110개(설치 32, 출처 메타데이터 12, 변경 확인 18, 원본 diff 20, 갱신 적용 28), `경로:줄 범위` 쌍 113개의 시작·끝 줄을 `git show 7a22192:<path>`로 열어 범위 안인지 확인했다(스크립트. 메타데이터 문서의 축약 표기는 직접). 설치 스펙은 경로 접두사 `src-tauri/src/`를 생략한다고 적었다. R-ID는 각 문서 안에서 고유하다(원본 diff의 중복 R-02는 합쳤다).
4. **대표 흐름 하나**: 사용자가 GitHub URL을 준다 → `preview_git_install`이 임시 체크아웃으로 스킬 목록을 보여 주고 `confirm_git_install`이 고른 스킬을 라이브러리에 복사해 행을 쓴다(설치 R-07·R-09·R-13·R-16, 값은 출처 메타데이터 R-03, R-05) → 같은 호출 끝에서 `.skills-manager/skills/<id>.json`이 다시 쓰인다(출처 메타데이터 R-11, R-18) → 앱 시작 때 `check_all_skill_updates`가 같은 원격을 한 번만 조회해 `remote_revision`을 얻고 `source_revision`과 다르면 `update_available`을 기록한다(변경 확인 R-17·R-18·R-22·R-01, 모노레포 하위 폴더가 안 바뀌었으면 `source_revision`만 옮기고 `up_to_date`, R-14·R-20) → 사용자가 My Skills에서 스킬을 열어 Diff 탭을 누르면 원격 최신 head를 체크아웃해 사본과 파일 단위로 비교한다(원본 diff R-05~R-09, R-13~R-16) → 사용자가 갱신을 누르면 `update_git_skill_internal`이 원격 head를 다시 확인하고 임시 체크아웃을 받아 스테이징한 뒤, 교체로 사라질 파일이 있으면 아무것도 바꾸지 않고 목록과 승인 토큰을 돌려주고, 없거나 승인되면 폴더를 통째로 교체하고 `source_revision`·`remote_revision`·`content_hash`를 새 값으로 쓴다(갱신 적용 R-01~R-13, 출처 메타데이터 R-08). 다른 기기에서는 리비전이 메타데이터 파일에 없어 첫 확인이 `unknown`에 머문다(출처 메타데이터 R-12, R-13).

**`my-skills`에 중요한 점 (갱신 적용 R-01~R-08)**: 갱신은 **병합이 아니라 통째 교체**다. 라이브러리 사본에 내가 직접 고친 내용은, 같은 경로의 파일이면 경고 없이 덮인다(경고가 잡는 것은 "새 버전에 없는 파일"뿐). 또 변경 여부 판정(`content_changed`)은 저장된 해시와 원격 새 해시를 비교하는데, 저장 해시는 앱·CLI를 시작할 때마다 디스크 해시로 다시 쓰이므로 재시작 뒤에는 수정이 포함된 해시가 기준이 되어 업스트림이 안 바뀌어도 교체가 일어날 수 있다. 로컬 수정 감지·보존은 원본에 없는 기능이다.

---

## 3. 구조도

이번 갱신에서는 archify 구조도를 만들지 않았다(사용자 지시). `diagrams/`의 `structure.html`, `deploy-flow.html`은 `e6dcedf` 기준이고, 배포 경로의 큰 줄기(UI/CLI → `commands/sync.rs` → `scenario_service` → `sync_engine` → 에이전트 폴더)는 새 SHA에서도 같다(코드 확인: 위 지도의 진입점 행). 다만 `scenario_service.rs`가 이번 구간에서 374줄 바뀌어(`git diff --stat`) 그림의 세부는 새 SHA에서 확인하지 않았다.

### 글로 쓴 구조 해설

**읽는 순서**
1. `src-tauri/src/lib.rs` — `generate_handler!`(`:1002`)로 앱이 여는 명령 124개를 보고, `setup` 안의 시작 작업(`:904`~`:950`)을 본다. (코드 확인)
2. `commands/sync.rs` → `core/scenario_service.rs` → `core/sync_engine.rs` — 배포의 결정(어디에·어떤 모드로·덮어써도 되는가)과 파일 변경이 나뉜 경로. (코드 확인)
3. `bin/skills-manager-cli.rs` — 같은 core를 부르는 다른 입구. (구조)
4. `core/tool_adapters.rs`, `core/skill_store.rs`, `core/central_repo.rs` — 모든 기능이 쓰는 공유 계약. (구조)

**모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 | 검증 수준 |
|---|---|---|---|---|
| `commands/*` | 프런트엔드가 `invoke`로 부르는 Tauri 명령 | UI 입력 → core 호출 → 결과 | `lib.rs:1002` `generate_handler!` | 코드 확인(등록부) |
| `core/scenario_service.rs` | 어느 스킬을 어느 에이전트의 어느 경로에 어떤 모드로 배포할지 결정하고 기록 | 스킬·Preset·어댑터 → `skill_targets` 행 | `sync_desired_targets` | 코드 확인(앞부분) |
| `core/sync_engine.rs` | 한 경로에 symlink/junction/copy를 실제로 만들고, `ReplacePolicy`가 허용한 것만 지움 | 원본·대상 경로·정책 → 적용된 모드 | `sync_skill`, `ReplacePolicy` | 코드 확인 |
| `core/tool_adapters.rs` | 에이전트 58개의 skills 폴더·감지 폴더·분류를 하드코딩한 표 | 키 → 상대 경로 | `default_tool_adapters` | 코드 확인(개수) |
| `core/skill_store.rs`, `central_repo.rs`, `sync_metadata.rs` | SQLite와 라이브러리 폴더, 폴더 안 메타데이터 | 스킬·Preset·태그·배포 기록 | 모듈 파일 | 구조 |
| `core/installer.rs`, `git_fetcher.rs`, `skillssh_api.rs`, `well_known.rs` | 스킬을 가져오는 네 가지 원천 | 경로·URL → 임시 폴더 → 라이브러리 | 파일의 `pub fn` 목록 | 구조 |
| `core/git_backup.rs`, `auto_backup.rs`, `merge/` | 라이브러리의 Git 백업과 기기 간 병합 | 라이브러리 폴더 ↔ remote | `mod.rs` 머리 주석 | 구조 |
| `core/cli_bridge.rs` | 앱에 든 CLI를 에이전트가 찾는 곳(`~/.skills-manager/bin`)에 게시 | 앱 버전 → 복사본 + `.version` | 머리 주석, `manage-skills/SKILL.md` | 구조 + 코드 확인(SKILL.md) |
| `core/file_watcher.rs`, `skill_auto_updater.rs` | 외부 변경 감지, 주기적 업데이트 확인 | 파일 이벤트·타이머 → UI 이벤트 | `lib.rs:923`, `:930` | 구조 |

**미확인 영역**: 위 표의 "구조" 행의 동작 본문, 프런트엔드 상태 흐름, 앱과 CLI가 동시에 같은 DB를 쓸 때의 잠금 동작.

---

## 4. 질문 (Questions)

기능 스펙으로 확정된 동작은 스펙에 반영하고 여기서는 결론만 적는다. 아래 두 문서는 `e6dcedf` 기준이다(1절 재확인 필요 목록 참고).

- [Q1: 같은 이름·다른 내용 스킬과 덮어쓰기 처리 (cc-switch 비교)](./questions/q1-same-name-conflict-and-overwrite.md) - *해시로 별개 스킬 구분, 소유권 기록 없으면 덮어쓰기 거부 후 충돌 보고. 코드 읽기만, 실행 검증은 아직.*
- [Q2: 핵심 개념(설치·라이브러리·동기화·Preset·Workspace·백업·프록시·자동 업데이트)](./questions/q2-core-concepts-and-auto-update.md) - *설치=라이브러리 입고, 동기화=에이전트 폴더 연결(symlink/복사), 자동 업데이트는 옵트인 적용·복사 모드만 재복사. 코드 읽기 기준, 일부 README 기준.*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸. 작성된 것: [skill-source-metadata](capabilities/skill-source-metadata.md), [skill-install-external](capabilities/skill-install-external.md), [skill-update-check](capabilities/skill-update-check.md), [skill-source-diff](capabilities/skill-source-diff.md) [skill-update-apply](capabilities/skill-update-apply.md) (모두 ready). 나머지 행은 사용자 범위 밖이라 미작성.
- **이전 wiki 요약**: 2026-10-16 삭제. 원문은 `git show b52364d:wiki/projects/skills-manager.md`
