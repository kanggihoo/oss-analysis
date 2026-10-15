# Next Session Plan: teamai-cli

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `7ba8bcc374cfa11e85da54cb75c572f54c687fab`
- **작성/갱신 일자**: `2026-10-15`

---

## 1. 이번 세션에서 확인한 범위

- [x] clone, 메타데이터 기록 (`artifacts/teamai-cli/repo-metadata.txt`)
- [x] README, `docs/product-overview.md`, `package.json`, `src/index.ts` 명령 목록, `ResourceType`, `resources/index.ts`, `hook-dispatch` 진입부 읽음
- [ ] 실행 / 테스트 / archify 다이어그램은 하지 않음

---

## 2. 해결되지 않은 남은 질문

- [ ] `pull`은 원하는 상태를 어떻게 계산하고(`resources/desired.ts`), 사용자가 수정한 복사본을 어떻게 보호하는가 (`delivered-copies.ts`)
- [ ] 훅 주입은 도구별로 어떻게 다른가 (Claude/Codex/Cursor/Pi 어댑터)
- [ ] namespace·role·project·tag 배포 대상 해석 규칙
- [ ] recall 검색 인덱스와 codebase 지식 그래프 추출 파이프라인
- [ ] skills-manager / cc-switch와 비교 시 "팀 배포" 관점의 차이

---

## 3. 다음에 볼 파일 및 함수

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/pull.ts` | pull 본체 | 대표 실행 흐름 추적 |
| `src/resources/desired.ts` | `resolveDesiredSkills` 등 | 배포 대상 계산 |
| `src/hook-dispatch-cli.ts`, `src/hook-handlers.ts` | `hookDispatchCli` | SessionStart에서 pull이 호출되는 경로 |
| `src/recall.ts`, `src/utils/search-index.ts` | `search` | recall 점수화 |

---

## 4. 참고 사항

- `scripts/analyze-repo.sh`는 기본 ROOT가 `/Users/kkh/...`라 Windows에서는 `OSS_LAB_ROOT=$(pwd)`를 지정해 실행했다.
- 스크립트가 만든 `repo-metadata.txt`는 절대경로라서 다른 repo 형식(상대경로 + `commit_date`)에 맞춰 고쳤다.
