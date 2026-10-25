---
sha: "a44493f6ec20e32197a1bca4c3e000be2cd6fe70"
created: 2026-10-15
updated: 2026-10-24
---

# Next Session Plan: teamai-cli

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] `repos/teamai-cli`를 `a44493f`로 pull. `git diff 7ba8bcc..a44493f` 변경 요약과 달라진 점 표를 overview 1절에 기록
- [x] 기능 지도 29행(Execution 15, Context 6, Improvement 5, 부속 3) + 공유 계약 6개 작성. `index.ts` 명령 등록부, `ResourceType` 14종, `KNOWN_AGENTS` 38개, provider 6종, 세션·워크플로 하위 명령을 코드로 확인
- [ ] 구조도(archify)는 사용자 지시로 생략. 기능 본문은 읽지 않았고 빌드·테스트·실행 안 함

---

## 2. 해결되지 않은 남은 질문

- [ ] **Q1 재확인**: `7ba8bcc` 기준이다. `init.ts`, `projects.ts`, `resource-namespaces.ts`가 이번 구간에서 바뀌었다.
- [ ] `pull`은 원하는 상태를 어떻게 계산하고(`resources/desired.ts`), 사용자가 수정한 복사본을 어떻게 보호하는가 (`resources/delivered-copies.ts`)
- [x] `packages`·`mcp`의 변경 감지(업스트림 감지 없음) → [q2](./questions/q2-packages-and-mcp-sync.md). 남은 것: `claude plugin install` 재실행 시 갱신되는지, 마켓플레이스 `ref` 적용, 손으로 고친 MCP 항목의 pull 후 유지 여부(모두 미확인)
- [ ] 훅 주입은 도구별로 어떻게 다른가 (Claude/Codex/Cursor/Pi 어댑터) / `hook-dispatch`가 호스트 훅 타임아웃을 어떻게 피하나
- [ ] namespace·role·project·tag 배포 대상 해석 규칙
- [ ] recall 검색 인덱스와 codebase 지식 그래프 추출 파이프라인
- [ ] 워크플로 엔진: 임대(lease)·재시도·취소가 run 상태에 미치는 규칙 (`docs/dev/workflow-engine.md`를 코드로 검증)
- [ ] skills-manager / cc-switch와 비교 시 "팀 배포" 관점의 차이

---

## 3. 기능 스펙 후보

범위 승인 전이다. 사용자가 고르면 지도의 행 단위로 쓴다. 질문으로 확정된 후보는 아직 없다.

| 기능 | 근거 질문 문서 | 상태 |
|---|---|---|
| 배포 대상 제어 | [q1](./questions/q1-solo-per-project-management.md) (새 SHA 재확인 필요) | 승인 대기 |
| 멀티 소스·패키지(`packages`) | [q2](./questions/q2-packages-and-mcp-sync.md): 선언 → 어댑터 설치 → 락 스냅샷 → 해시 알림 | 승인 대기 |
| MCP 동기화(소유 매니페스트 기반 reconcile) | [q2](./questions/q2-packages-and-mcp-sync.md): 엔트리 해시, 기록 없는 항목의 소유 판정, 평문 시크릿의 git 제외 | 승인 대기. 참고 설계: `plugin-lifecycle.ts`의 명령 지문 비교 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음에 쓸 기능 스펙이 있으면: 사용자가 범위를 승인한 뒤 공유 계약(팀 repo 레이아웃, 리소스 핸들러, 도구 경로) → `배포 pull` 순서를 제안한다.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/pull.ts` | pull 본체(4,022줄) | 대표 실행 흐름 추적 |
| `src/resources/desired.ts` | `resolveDesiredSkills` 등 | 배포 대상 계산 |
| `src/hook-dispatch-cli.ts`, `src/hook-handlers.ts` | `hookDispatchCli` | SessionStart에서 pull이 호출되는 경로 |
| `src/recall.ts`, `src/utils/search-index.ts` | `search` | recall 점수화 |
| `src/workflow/engine.ts` | `startRun`, `leaseNext`, `reportAttempt` | 워크플로 스펙 |

---

## 5. 참고 사항 및 후속 제안

- `scripts/analyze-repo.sh`는 기본 ROOT가 `/Users/kkh/...`이므로 다른 경로에서 돌릴 때는 `OSS_LAB_ROOT=$(pwd)`를 지정한다.
- `repos/teamai-cli/AGENTS.md`는 그 레포 기여자용 규칙(워크트리 사용, PR 규칙 등)이다. 이 작업 공간은 읽기만 하므로 적용하지 않는다.
