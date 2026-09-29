# Next Session Plan: claude-devtools

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `1486f2042c87bb547a4e34808ab54ab34a33f132`
- **작성/갱신 일자**: `2026-09-29`

---

## 1. 이번 세션에서 확인한 범위

- [x] clone을 `16cc3c8` → `1486f20`로 fast-forward, 이전 metadata 보존
- [x] `scripts/analyze-repo.sh` 재실행 (tokei, GitHub 메타데이터 갱신)
- [x] baseline 이후 변경 범위 확인 (8 commits, 소규모 UI/배포 변경)
- [x] repos/claude-devtools 삭제 후 fresh clone (HEAD 동일 `1486f20`)
- [x] archify 전체 아키텍처 구조도 작성 (`diagrams/structure.*`, showcase 통과)

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 분석 목적 확정 (학습 / 설계 참고 / 도입 검토)
- [ ] 대표 실행 흐름(sequence) 미작성 — 후보: 세션 선택 → `sessions.ts` getSessionDetail → cache/parse/chunk → renderer
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
