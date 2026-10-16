# Next Session Plan: claude-devtools

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `1486f2042c87bb547a4e34808ab54ab34a33f132`
- **작성/갱신 일자**: `2026-10-16`

---

## 1. 이번 세션에서 확인한 범위

- [x] clone을 `16cc3c8` → `1486f20`로 fast-forward, 이전 metadata 보존
- [x] `scripts/analyze-repo.sh` 재실행 (tokei, GitHub 메타데이터 갱신)
- [x] baseline 이후 변경 범위 확인 (8 commits, 소규모 UI/배포 변경)
- [x] repos/claude-devtools 삭제 후 fresh clone (HEAD 동일 `1486f20`)
- [x] archify 전체 아키텍처 구조도 작성 (`diagrams/structure.*`, showcase 통과)
- [x] 2026-10-16: 세션 탐색·JSONL 파싱을 `1486f20`에서 코드로 확인하고 [Q1](./questions/q1-session-discovery-and-jsonl-parsing.md) 작성, 실제 로그 형식 확인(`artifacts/claude-devtools/log-format-demos/`), 기능 스펙 [claude-code-session-log-reading](./capabilities/claude-code-session-log-reading.md) 작성(draft)
- [x] 2026-10-15: 다른 PC에서 `repos/claude-devtools` 재clone, upstream HEAD가 `1486f20`과 동일(신규 commit 0, worktree clean) 확인 (검증 수준: 실행 확인)

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 분석 목적 확정 (학습 / 설계 참고 / 도입 검토)
- [ ] 대표 실행 흐름(sequence) 미작성 — 후보: 세션 선택 → `sessions.ts` getSessionDetail → cache/parse/chunk → renderer
- [ ] 기능 스펙 미결정 2건: 디렉터리 이름 규칙의 정확한 형태(macOS·Linux 미확인), 나뉜 프로젝트에서 `cwd` 없는 세션의 소속
- [ ] 레포 테스트 실행(`pnpm install` 필요, 허락 후): pathDecoder, ProjectScanner.cwdSplit, jsonl, SessionParser
- [ ] `encodePath` 때문에 Windows에서 `MEMORY.md`를 못 찾는지 실행 확인
- [ ] SSH context 전환(`handleModeSwitch`, `contextRegistry.switch`) 시 FileWatcher 재배선 동작

---

## 3. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/main/index.ts` | main 초기화 | 서비스 초기화 → IPC 등록 순서 (구조도 진입점) |
| `src/main/services/infrastructure/ServiceContext.ts` | `ServiceContext`, `ServiceContextRegistry` | local/SSH context 경계 |
| `src/main/ipc/sessions.ts` | 세션 상세 IPC | 대표 흐름: 세션 선택 → JSONL 파싱 → chunk → renderer |
| `src/main/standalone.ts`, `src/main/http/` | standalone 서버 | Electron 없이 도는 경로 (baseline 이후 변경 포함) |

---

## 4. 참고 사항 및 후속 제안

- DeepWiki snapshot은 `16cc3c8` 기준이지만 이후 변경이 작아 second opinion으로 계속 사용 가능.
- 기존 wiki 3개 concept 페이지가 이미 `코드 확인` 수준이므로 구조도는 이를 출발점으로 삼고 `1486f20`에서 재확인.
