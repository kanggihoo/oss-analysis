# Next Session Plan: pi

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `4259686d9290c0d73ae7192b796aee3e530a9779`
- **작성/갱신 일자**: `2026-09-29`

---

## 1. 이번 세션에서 확인한 범위

- [x] 초기셋팅: clone, 메타데이터, tokei 통계, GitHub 정보 수집 (`scripts/analyze-repo.sh`)
- [x] 패키지 목록과 DeepWiki baseline(`406a221`)과의 차이 확인
- [x] archify 패키지 구조도 (`diagrams/structure.*`)
- [ ] 대표 실행 흐름 다이어그램 — 아직 안 함

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 분석 목적 (학습 / 설계 참고 / 도입 검토)
- [x] 패키지 간 의존 방향 → overview §3
- [ ] chord의 실제 역할 (agent-core가 32회 import — 무엇을 가져다 쓰나)
- [ ] pi-durable의 소비자와 용도
- [ ] 대표 실행 흐름으로 무엇을 고를지 (예: `pi` CLI에서 프롬프트 1회 → tool 호출 → 응답)

---

## 3. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `packages/*/package.json` | `dependencies` | 패키지 의존 그래프 → 구조도 뼈대 |
| `packages/coding-agent/` | CLI entry (`bin`) | 대표 실행 흐름의 시작점 |
| `packages/agent/` | agent loop | DeepWiki 2.1과 대조 검증 |
| `packages/agent/src/agent-loop.ts` | `runLoop`, `streamFn` 사용 | 완료 (Q5) |
| `packages/ai/src/api/openai-completions.ts` | compat 자동 감지 | OpenAI 호환 벤더 차이 흡수 방식 |
| `packages/agent/src/agent.ts` | `processEvents`, `handleRunFailure` | 완료 (Q6) |
| `packages/coding-agent/src/core/agent-session.ts` | hook 주입 | 완료 (Q7) |
| `packages/coding-agent/src/core/session-manager.ts` | `buildSessionProjection` | 완료 (Q8) |
| `packages/coding-agent/src/core/compaction/` | `prepareCompaction`(Q8 완료), `compact`/`generateSummary` | 요약 prompt와 fileOps 사용 |

---

## 4. 참고 사항 및 후속 제안

- DeepWiki(`artifacts/pi/deepwiki/`)는 2069 commits 전 기준 — second opinion으로만 사용하고 코드로 재확인.
- 레포 크기가 커서(~348k LOC TS) archify는 패키지 단위로 시작하고 점진적으로 세분화.
- 이전 분석 존재: `reports/pi/agent/package-file-roles.md` (commit `ff6181f`, baseline `406a221` 기준 `packages/agent` 파일 역할). 이번 세션 시작 전부터 작업트리에서 삭제된 상태 — 필요하면 `git restore reports/pi/agent/package-file-roles.md`로 복원.
