---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-15
---

# Next Session Plan: craft-anything

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 목적 확정(2026-11-14): 우리 절차(AI 코드 분석 → 스펙 문서 → 재구현 가능성) 보완·개선 설계 참고
- [x] feature map 20행, 승인 범위 행 1~11 → 스펙 11개 모두 ready (코드만 읽음, 실행 없음)
- [x] 통합 검토와 "우리 절차와 맞대어 본 결과" 표 A~M 확정(overview 2절)
- [ ] 구조도(archify)는 요청이 없어 그리지 않았다

## 2. 해결되지 않은 남은 질문

- [ ] README "320 tools" vs `docs/tools.md` "303 engine tools" 차이 (`cargo xtask tools` 실행 허용 필요)
- [ ] Claude Code·Copilot CLI가 질문 모드 플래그를 실제로 지키는지(외부 프로그램 동작, person-inbox R-55·R-58 미확인)

## 3. 기능 스펙 후보

| 기능 | 근거 | 상태 |
|---|---|---|
| 승인 정책(허용/질문/거절 3단계, 종류 7개) | [person-inbox](./capabilities/person-inbox.md) R-16~R-26, R-46~R-53 | 사용자 결정으로 분리하지 않음(2026-11-15) |
| 행 12~14(도구 계약·MCP, 에이전트 구동, 내장 에이전트 루프) | overview 2절 | 범위 제외(사용자 결정, 2026-11-15). 빌더 턴 재시도·세션 이어받기(`mod.rs:1211-1322`)가 7행과 13행 사이에 걸림 |

## 4. 다음 작업

1. 사용자 결정(2026-11-15): P0·P1과 P2 중 E(막힌 경로)만 우리 절차에 반영했고 J·M은 반영하지 않는다. 범위는 넓히지 않는다(행 12~14, 승인 정책 분리 제외). 결정 대기 없음.
2. 범위를 넓힐 때 쓸 진입 코드: `crates/ai/src/cli_agents/mod.rs`(13행), `crates/ai/src/agent.rs`·`prompt.rs`(14행), `crates/mcp/src/lib.rs`(12행).

## 5. 참고 사항

- 원본 버그·문서-구현 차이는 각 스펙 2.1에 있다(예: `kinds/self_test.rs:87-101` 판정 반대, `rebuild/mod.rs:956` 상한 미보존).
- 이 레포의 `AGENTS.md`는 그쪽 기여 규칙이라 분석과 무관하다.
