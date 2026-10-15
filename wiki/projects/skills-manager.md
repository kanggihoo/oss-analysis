---
title: skills-manager
created: 2026-10-15
updated: 2026-10-15
type: project
tags: [open-source, project, skills, claude-code, tauri, rust]
sources:
  - reports/skills-manager/overview.md
  - repos/skills-manager/README.md
  - repos/skills-manager/src-tauri/src/core/sync_engine.rs
  - repos/skills-manager/src-tauri/src/core/scenario_service.rs
  - repos/skills-manager/src-tauri/src/core/tool_adapters.rs
confidence: medium
---

# skills-manager

AI 코딩 에이전트 54종(Claude Code, Codex, Cursor 등)의 **스킬을 중앙 라이브러리(`~/.skills-manager`) 한 곳에서 관리하고 에이전트 폴더로 배포**하는 Tauri 2(Rust + React) 앱·CLI. 분석 SHA `e6dcedf` (v1.42.0). 상세: `reports/skills-manager/overview.md`. 1차 분석이라 배포 경로 하나만 코드로 확인했다.

## 핵심 (코드 확인)

- **구조**: UI/CLI → 공유 Rust core(`scenario_service` 결정 → `sync_engine` 실행) → 에이전트 skills 폴더. 상태는 SQLite(`skills`, `skill_targets`, `scenarios` 등).
- **배포 방식**: 기본 symlink, Windows에서 실패하면 junction, 그것도 안 되면 copy.
- **데이터 보호**: `ReplacePolicy`(NoClobber / Recorded / UserConfirmed). DB에 배포 기록이 없는 기존 폴더는 덮어쓰지 않고 거부한다. 같은 폴더를 공유하는 에이전트가 있으면 지우지 않는다.
- **에이전트도 관리자**: 앱이 `manage-skills` 스킬과 CLI 복사본(`~/.skills-manager/bin`)을 배포해 에이전트가 폴더를 직접 만지지 않고 CLI로 관리하게 한다.
- 앱과 CLI가 같은 core를 호출한다.

## 미확인

- Preset 적용 의미, file_watcher 재동기화, git 백업 병합, 마켓플레이스·업데이트 경로
- 테스트·실행 안 함

관련: [[cc-switch]] (스킬 SSOT 배포 방식이 비슷하나 덮어쓰기 정책이 다를 것으로 보임, 미검증)

## 같은 이름·다른 내용 스킬 (코드 읽기, [[cc-switch]]와 비교)

- 스캔은 이름+내용 해시로 그룹화하므로 같은 이름이라도 내용이 다르면 별개 항목이고, 가져오기에서 중앙에 같은 이름이 있으면 `<name>-2`를 할당한다(`unique_skill_dest`). cc-switch는 폴더명만 보고 첫 발견 버전으로 합친다.
- 덮어쓰기는 `skill_targets` 기록이 그 경로를 가리킬 때만 허용하고, 거부는 `TargetConflict`로 사용자에게 보고한다. cc-switch의 조용한 덮어쓰기에 해당하는 문제는 설계로 막혀 있다.
- 한계: 앱 전용 파일(예: Codex `agents/openai.yaml`)을 만들거나 변환하지 않는다. 복사 모드에서 배포본을 사용자가 수정하고 원본이 바뀌면 덮어쓰일 수 있다(추론, 미실행). 상세: `reports/skills-manager/questions/q1-same-name-conflict-and-overwrite.md`
