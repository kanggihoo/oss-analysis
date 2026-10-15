# [Q] skills-manager의 핵심 개념(설치·라이브러리·동기화·Preset·Workspace·백업·프록시·자동 업데이트)은 무엇을 뜻하는가

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `e6dcedf968f3f0ebf62e24edf5d90ec8cbf23509` (2026-10-15, v1.42.0)
- **분석 일자**: 2026-10-16
- **검증 수준**: `코드 확인`(읽기만) + README 기준 + `추론`. 실행·테스트는 하지 않았다. 항목마다 근거를 표기한다.
- **분석 목적**: 이 앱을 커스텀(에이전트 2~4종으로 축소, 백업을 GitHub만 남기기)하기 전에 용어와 동작을 이해한다.

> 경로 표기: 모든 코드 경로는 `repos/skills-manager/` 기준이다. `core/…`, `commands/…`, `bin/…`은 `src-tauri/src/` 아래다. 행 번호는 위 SHA 기준이며 파일이 바뀌면 어긋난다.

## 1. 큰 그림: 사본은 라이브러리에 1개, 에이전트 폴더에는 연결

```
~/.skills-manager/skills/react-tips/     ← 진짜 파일 (1개, "중앙 라이브러리")
~/.claude/skills/react-tips   → 위를 가리키는 symlink
~/.codex/skills/react-tips    → 위를 가리키는 symlink
```

"설치"는 라이브러리에 넣는 것, "동기화/배포"는 에이전트 폴더에 연결하는 것이다. 둘은 별개 단계다.

## 2. 질문별 답과 근거

### 2.1 "설치"와 "라이브러리"는 무엇인가

- **결론**: 라이브러리(중앙 라이브러리)는 기본 `~/.skills-manager`이고, 설치는 Git·로컬·zip·skills.sh에서 받은 스킬을 그 안에 저장하는 것이다. 설치만으로는 어느 에이전트에도 배포되지 않는다.
- **근거 (README 기준)**:
  - `README.md:67` — 모든 설치 경로가 "one central repo"로 들어가고 기본값이 `~/.skills-manager`.
  - `README.md:192` — CLI 예시 주석 `Install into the library (does NOT deploy to any agent by itself)`.
- **근거 (코드 확인)**: 배포 때 원본은 항상 `skill.central_path`다. `core/scenario_service.rs:880` (`let source = PathBuf::from(&skill.central_path);`).
- **검증 수준**: 코드 확인(원본 경로), README 기준(설치 경로 종류). 설치 코드 자체(`installer.rs`, `git_fetcher.rs`)는 이번에 읽지 않았다.

### 2.2 "동기화(sync)"는 무엇이고, symlink는 어떻게 거는가

- **결론**: 이 앱에서 동기화는 "라이브러리의 스킬을 에이전트 폴더에 연결(또는 복사)하는 동작"이다. 실시간 양방향 동기화가 아니다.
- **근거 (코드 확인)**:
  - symlink 생성: `core/sync_engine.rs:332` — `std::os::unix::fs::symlink(source, target)`. target은 에이전트 폴더 안 경로, source는 라이브러리 폴더.
  - Windows 폴백: `core/sync_engine.rs:339`(`symlink_dir`) → `:357`(실패 시 junction) → `:365`(둘 다 실패 시 copy).
  - 기본 모드는 symlink, `sync_mode` 설정이 `"copy"`일 때만 복사: `core/sync_engine.rs:275-281` (`sync_mode_for_tool`), 설정 읽기 `core/scenario_service.rs:899`.
  - 진입점: `commands/sync.rs:35-45` (`sync_skill_to_tool_internal`) → `core/scenario_service.rs:852` (`sync_single_skill_to_tool`). 에이전트가 설치돼 있지 않으면(`:861`) 또는 비활성이면(`:868`) 거부한다.
- **검증 수준**: 코드 확인.

### 2.3 Preset은 무엇인가

- **결론**: 스킬 묶음에 이름을 붙인 것. 예를 들어 "프런트엔드" Preset에 스킬 5개를 넣고, 에이전트에서 버튼 하나로 5개를 한꺼번에 켠다.
- **근거**: `README.md:70` — "Applying a preset is a one-time copy, not a live sync."
- **미확인**: "한 번 복사"가 코드에서 정확히 무엇인지(Preset 수정이 이미 켠 에이전트에 반영되는지)는 읽지 않았다. DB 테이블은 `scenarios`, 에이전트별 토글은 `scenario_skill_tools`(overview 기준). → 남은 질문으로 `next.md`의 Q2.
- **검증 수준**: README 기준, 코드 미확인.

### 2.4 Global / Agent / Project Workspace의 관계

- **결론**: 같은 라이브러리를 놓는 위치만 다르다. Global은 에이전트 전역 폴더(예: `~/.claude/skills`), Project는 프로젝트 안의 폴더(`.claude/skills`). Preset은 이 둘 어디에든 적용하는 스킬 묶음이다.
- **근거 (README 기준)**: `README.md:71`(Global Workspace), `:72`(Project Workspaces). 코드로는 `commands/agent_workspace.rs`(전역), `commands/projects.rs`(프로젝트)가 각각 담당함을 확인했으나 동작 전체는 읽지 않았다.
- **검증 수준**: README 기준 + 구조 확인.

### 2.5 프로젝트 스킬을 전역/다른 에이전트로 옮길 수 있나

- **결론**: 한 번에 "이동"하는 명령은 없고, 라이브러리를 거치는 2단계로 가능하다. 반대 방향도 있다.
  1. 프로젝트 스킬 → 라이브러리로 가져오기: `commands/projects.rs:955` (`import_project_skill_to_center`).
     - 같은 스킬이 이미 라이브러리에 있으면(`find_best_center_match`, `:982`) 그 항목을 덮어써 갱신하고(`install_from_local_to_destination`, `:983`), 없으면 새 항목을 만든다(`install_from_local` `:1017`, `insert_skill` `:1044`).
  2. 라이브러리 → 전역 에이전트로 배포: 2.2의 경로(`sync_single_skill_to_tool`).
  - 라이브러리 → 프로젝트: `commands/projects.rs:1067` (`export_skill_to_project`, `agents` 인자로 에이전트 지정).
  - 전역 폴더에서 가져오기도 같은 구조: `commands/agent_workspace.rs:219` (`import_global_local_skill_to_center`).
- **검증 수준**: 코드 확인(함수 존재와 분기). 동작 실행은 하지 않았다.

### 2.6 에이전트가 스킬을 관리한다는 기능(manage-skills)은 무엇인가

- **결론**: Claude Code 등이 에이전트 폴더에 파일을 직접 쓰면 앱이 모른다(출처·Preset·업데이트 추적이 끊김). 대신 앱이 CLI를 `~/.skills-manager/bin`에 게시하고 `manage-skills` 스킬을 에이전트에 배포해, 에이전트가 CLI로 설치·배포·조회하게 한다.
- **근거**:
  - `README.md:69`, `:113`부터 ("Let your agents manage skills" 절).
  - CLI 게시: `core/cli_bridge.rs:175` (`ensure_bridge`).
  - 스킬 내용: `skills/manage-skills/SKILL.md:2-3`(설명), `:13`(CLI 위치 탐색).
- **검증 수준**: 구조 확인. CLI 복사 로직(`ensure_bridge_inner`)은 읽지 않았다.

### 2.7 백업은 무엇을 담나 (Preset·전역·프로젝트가 섞일 때)

- **결론**: 백업 대상은 **라이브러리**다. 스킬, 태그, Preset, 에이전트별 토글이 들어가고, 키·토큰·프록시 설정과 "기기별 연결 정보"는 제외된다. SQLite DB 자체는 Git에 넣지 않는다(스킬 파일에서 재구성).
- **근거 (README 기준)**: `README.md:142-144`.
- **추론(미확인)**: 프로젝트 폴더 경로는 기기마다 달라서 백업에 포함되지 않을 것으로 보인다. 프로젝트 안의 스킬 파일은 그 프로젝트의 git이 별도로 관리한다. 코드로 확인하지 않았다.
- **GitHub 인증**: 기기 코드 방식(device flow). `core/github_api.rs:175`(`device_flow_start`), `:204`(`device_flow_poll`). README는 임의 Git remote도 지원한다고 한다(`README.md:81`).
- **검증 수준**: README 기준, 인증 코드는 존재만 확인.

### 2.8 프록시는 왜 있나

- **결론**: 외부 네트워크를 쓰는 곳에 같은 프록시 설정(`proxy_url`)을 붙이기 위해서다. GitHub·skills.sh에 직접 못 가는 환경(회사망 등)을 위한 옵션으로 보인다(목적은 추론).
- **근거 (코드 확인)**: 설정 읽기 `core/skill_store.rs:626` (`proxy_url`, 빈 문자열은 None). 사용처: 스킬 설치·확인·업데이트(`commands/skills.rs` 다수, 예 `:408`, `:605`, `:1006`), 마켓플레이스(`commands/browse.rs:26`, `:47`), 백업(`commands/git_backup.rs:33`, `:198`), 자동 업데이트(`core/skill_auto_updater.rs:147`), git2(`core/git2_engine.rs:37`).
- **검증 수준**: 코드 확인(사용처), 추론(목적).

### 2.9 자동 업데이트는 어떻게 동작하나

- **결론**: 앱이 켜져 있는 동안 주기적으로 상류 변경을 확인하고, "자동 적용"을 켠 경우에만 라이브러리를 갱신한다. symlink로 연결된 에이전트는 라이브러리를 가리키므로 별도 작업 없이 새 내용을 보고, 복사 모드는 앱이 다시 복사한다.
- **근거 (코드 확인)**:
  1. 스케줄러: 앱 시작 60초 후 첫 실행, 이후 15분마다 깨어 "주기가 되었나" 판단. `core/skill_auto_updater.rs:22`(`INITIAL_DELAY`), `:28`(`POLL_INTERVAL`), `:42`(`start`).
  2. 주기 값은 `off`/`1h`/`6h`/`24h`만 인식한다. `core/skill_auto_updater.rs:88-96` (`parse_interval`). 설정 키 `:14-16`.
  3. 자동 적용은 별도 옵트인(`auto_update_apply == "on"`). `core/skill_auto_updater.rs:139-144`. 꺼져 있으면 확인(배지 표시)만 한다. 적용 분기는 `:200`.
  4. 확인 대상 종류: `git`, `skillssh`는 상류 revision을 비교(`commands/skills.rs:2738`). `local`/`import`는 원본 경로 해시만 비교한다(`:2805`). `well-known`은 비교 대상이 없다(`:2829`, 위 주석). 자동 적용은 git 업데이트 함수만 호출한다(`core/skill_auto_updater.rs:201` → `commands/skills.rs:2068`).
  5. 갱신은 라이브러리 폴더 교체: `swap_skill_directory(&staged_path, central_path)` `commands/skills.rs:2179`(구현 `:3151`).
  6. 이후 **복사 모드로 배포된 대상만** 다시 복사: `resync_copy_targets` 호출 `commands/skills.rs:2204`, `:2219`, 구현 `:3177`(`if target.mode != "copy" { continue; }` `:3188`). symlink 대상은 건너뛴다(이미 라이브러리를 보므로).
  7. 안전장치: 새 버전에서 기존 경로가 사라지는 경우(`pending_removals`)는 자동 적용하지 않고 보류한다. `core/skill_auto_updater.rs:202-209`, `commands/skills.rs:2175` (`UpdateOutcome::Held`). 사용자가 직접 검토해야 한다.
- **검증 수준**: 코드 확인(읽기). 실제 주기 실행은 하지 않았다.

## 3. 커스텀 관련 메모 (이번 답과 연결되는 것만)

- **에이전트 축소**: 목록은 `core/tool_adapters.rs:147` (`default_tool_adapters`). 이 목록 외에 UI·CLI·i18n이 54종을 가정하는 곳이 있는지는 **미확인**. 변경 전에 `tool_adapters` 참조처를 먼저 확인해야 한다.
- **백업 GitHub 한정**: GitHub 전용 코드(`core/github_api.rs`, `core/git_credentials.rs`)와 일반 git remote 경로가 공존한다. 일반 remote 경로를 걷어 내려면 `core/git_backup.rs`(3,461줄)와 `core/merge/`와의 의존을 먼저 읽어야 한다. **미확인**.

## 4. 이 문서에서 확인하지 못한 것

- Preset 적용·해제의 실제 의미(2.3), 백업에 프로젝트가 포함되는지(2.7), 설치 코드(2.1), `ensure_bridge_inner`(2.6), 프록시의 정확한 의도(2.8).
- 앱 실행, `cargo test`, 자동 업데이트 라운드 실행은 하지 않았다.
