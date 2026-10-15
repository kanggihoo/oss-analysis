# [Q] Skills/MCP는 어떻게 관리되고, 앱마다 다른 같은 이름 스킬은 어떻게 처리되는가

- **상위 개요**: [overview.md](../overview.md)
- **분석 Commit SHA**: `d35726e`
- **검증 수준**: `코드 확인` + `실행 확인` (스킬 중복/덮어쓰기는 실제 `SkillService`를 격리 홈에서 실행)

## 1. 질문 및 결론

- **질문**: Skills/MCP 활성·비활성·삭제는 어떤 원리인가? 앱(Claude/Codex 등)마다 내용이 다른 같은 이름 스킬(frontmatter 차이, Codex의 `agents/openai.yaml`)은 어떻게 되는가?
- **핵심 결론**
  - 스킬은 `~/.cc-switch/skills/`(SSOT) 한 곳에 원본을 두고 앱 폴더에 symlink/복사로 배포한다. 비활성화는 앱 폴더의 링크/사본만 지우고 원본은 남는다.
  - MCP는 정의를 DB에 두고, 켠 항목만 각 CLI 설정 파일(`~/.claude.json`의 `mcpServers` 등)에 추가/제거한다.
  - **앱별 변형은 보존되지 않는다.** 같은 이름이 앱마다 다르면 먼저 발견된 쪽(Claude)이 원본이 되고, 이후 재동기화/토글 때 다른 앱 폴더가 그 원본으로 **통째로 교체**된다. Codex 쪽에만 있던 `agents/openai.yaml`은 사라진다.

## 2. 동작 설명

### 스킬
```
~/.cc-switch/skills/<dir>/      ← SSOT (설정에서 ~/.agents/skills 로 변경 가능), 상태는 SQLite
   │ 활성화: sync_to_app_dir  (Auto: symlink 시도 → 실패/기존 폴더면 복사)
   ▼
~/.claude/skills/<dir>, ~/.codex/skills/<dir>, ...   (get_app_skills_dir: 앱별 경로)
```

| UI 동작 | 함수 | 효과 |
|---|---|---|
| 활성화 | `toggle_app(true)` → `sync_to_app_dir` | 앱 폴더에 링크/복사 |
| 비활성화 | `toggle_app(false)` → `remove_from_app` | 앱 폴더의 것만 삭제, 원본 유지 |
| 삭제 | `uninstall` | 원본+모든 앱 사본+DB 삭제, 전에 `skill-backups/`에 백업 |

- 파일은 변환하지 않고 폴더째 옮긴다 (`copy_dir_recursive`, 파일 종류별 처리 없음). `SKILL.md` 존재만 검사.
- 앱별 예외: Claude Desktop은 동기화/제거 건너뜀. Pi/Mcode는 이름이 같고 내용이 다르면 덮어쓰기/삭제를 거부(`inspect_pi_skill_destination`). Claude/Codex 등에는 이 보호가 없다.
- 같은 스킬이 여러 앱에 켜져 있어도 DB 행은 하나(`InstalledSkill.apps`에 앱별 플래그). 설치 경로는 폴더명이 같고 저장소가 다르면 `SKILL_DIRECTORY_CONFLICT`로 거부(`reuse_existing_install`).

### MCP
- 상세(앱별 포맷 변환, 가져오기 규칙, plugin)는 [q6](./q6-mcp-per-app-conversion.md)로 분리. 요약: 정의는 DB, 켠 항목만 각 CLI 설정 파일에서 id 단위로 추가/제거.

## 3. 코드 근거

| 구분 | 파일 | 식별자 |
|---|---|---|
| 앱별 경로 | `src-tauri/src/services/skill.rs:650` | `get_app_skills_dir` |
| 배포 | 같은 파일 `:2580` | `sync_to_app_dir`, `replace_dest_with_copy` |
| 토글/제거/삭제 | `:2100`, `:2759`, `:1038` | `toggle_app`, `remove_from_app`, `uninstall` |
| 가져오기 | `:2131`, `:2195` | `scan_unmanaged`, `import_from_apps` (첫 발견 우선) |
| 재동기화 | `:2817` | `resync_all_apps` (주석: provider 전환 시 호출) |
| 중복/충돌 | `reuse_existing_install` | 같은 repo면 재사용, 다르면 에러 |

## 4. 검증 과정 및 실행 결과 (같은 이름, 다른 내용)

- **방법**: 레포 복사본(스크래치)에 통합 테스트 추가, `CC_SWITCH_TEST_HOME`으로 격리된 임시 홈에서 실제 `SkillService` 호출. 실제 `~/.claude`, `~/.cc-switch`는 건드리지 않음. 테스트 소스와 출력은 `artifacts/cc-switch/skill-dup-probe/`.
- **세팅**: `~/.claude/skills/dup-skill/SKILL.md`(description `CLAUDE-VERSION`)와 `~/.codex/skills/dup-skill/`(description `CODEX-VERSION` + `agents/openai.yaml`).

| 단계 | 결과 |
|---|---|
| `scan_unmanaged` | 한 항목으로 합침: `found_in=["claude","codex"]`, 내용 비교 없음, path는 claude 쪽 |
| `import_from_apps`(claude+codex 켬) | SSOT = **Claude 버전**. Codex 폴더는 그대로 (CODEX-VERSION + openai.yaml 유지) |
| `resync_all_apps` | Codex 폴더가 **Claude 버전으로 교체**됨. `agents/openai.yaml` 삭제 |
| codex 끄기→켜기 | 끄면 폴더 삭제, 켜면 Claude 버전 사본(복사, symlink 아님)으로 재생성 |

- 이 Windows 환경에서는 최종 상태가 모두 symlink가 아닌 복사였다. symlink 생성 실패 후 복사 폴백일 가능성이 있으나 실패 원인은 확인하지 않았다.
- **판단 근거**: 가설(첫 발견 우선 + 재동기화 시 교체)이 실행 결과와 일치한다.

### 동기화 관련 문제점 정리
1. **충돌 미해결**: 같은 이름이면 내용 비교 없이 한 스킬로 취급한다. 먼저 발견된 앱(순서: Claude → Codex → …)의 버전이 원본이 된다.
2. **조용한 덮어쓰기**: 이후 재동기화/토글(provider 전환 때도 호출됨)에서 다른 앱 폴더가 원본으로 통째로 교체된다. 병합이 없어 앱 전용 파일(예: Codex의 `agents/openai.yaml`)이 삭제된다. 덮어쓰기 전 경고나 백업은 확인하지 못했다 (`skill-backups/`는 uninstall/update 때만).
3. **한 앱에서 가져온 스킬을 다른 앱에 켜는 경우** (코드 읽기, 미실행): 원본 폴더가 통째로 복사되므로 파일 구성이 첫 앱 기준 그대로 간다. 두 번째 앱 전용 파일(예: Codex용 yaml)을 CC Switch가 만들어 주지 않는다. 그 상태가 문제인지는 해당 CLI의 규칙에 달려 있어 이 레포로는 알 수 없다.
4. **보호는 Pi/Mcode만**: 내용이 다르면 덮어쓰기/삭제를 거부하는 검사(`inspect_pi_skill_destination`)가 이 둘에만 있다.
5. **Windows 복사 폴백** (실행 관찰): 이 환경에서는 최종 상태가 symlink가 아닌 복사였다. 복사본은 원본 수정이 자동 반영되지 않고 재동기화 때만 맞춰진다. symlink 모드에서의 동작은 미확인.
6. **권장 운용**: 앱별로 필요한 파일은 `~/.cc-switch/skills/<스킬>/`에 처음부터 함께 둔다. 앱마다 `SKILL.md` 내용이 달라야 하면 이름을 다르게 하거나 CC Switch 관리 밖에 둔다.

## 5. 남은 질문 및 추가 조사 사항

- [ ] 가져오기 시 충돌을 사용자에게 알리는지 (프론트엔드 미확인). 백엔드에는 내용 비교/경고/덮어쓰기 전 백업이 없음
- [ ] 사용자가 SSOT를 먼저 편집해 두었을 때 가져오기 선택 UI가 어떻게 안내하는지 (프론트엔드 미확인)
- [ ] Symlink 모드(개발자 모드 켠 Windows/macOS)에서 같은 시나리오 결과
- [ ] `~/.agents/skills`를 SSOT로 쓸 때의 차이
- [ ] MCP에서 앱 설정 파일에 이미 같은 id가 다른 내용으로 있을 때의 충돌 처리 (`import_from_*`)
