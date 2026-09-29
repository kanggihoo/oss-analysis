# Next Session Plan: CodeWiki

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `3e3d848698c7bf1a0ce2e0b49e66841acd0248aa`
- **작성/갱신 일자**: `2026-09-30`

---

## 1. 이번 세션에서 확인한 범위

- [x] clone, uv venv(Python 3.12) 설치, claude-code 구독 모드 설정 (`claude-sonnet-5-5`)
- [x] 구독 모드 경로 코드 확인 (`caw_backend.py`, `get_backend`)
- [x] 자기 레포 대상 한국어 생성 2회 (depth 2, depth 4) — 각 약 17~18분
- [x] 1.0.1 동봉 문서 vs 2.0 결과 2종 표본 팩트체크 → [q1](./questions/q1-output-quality.md)
- [x] `max_depth`가 세분화 레버가 아님을 코드+로그로 확인 (`caw_backend.py:397-401`)
- [x] Mermaid 검증의 외부 호출(`mermaid.ink`)과 503이 "syntax errors"로 찍히는 동작 확인
- [x] archify 전체 구조도 (`diagrams/structure.*`, showcase 9/9, visual-check pass)

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] `--max-token-per-leaf-module`을 낮추면 분량·정확도가 어떻게 변하나
- [ ] 생성 중 Mermaid "syntax errors" 4건이 실제 문법 오류였나, 503이었나 (불필요한 수정 루프 여부)
- [ ] 1.0.1이 35페이지로 더 세분화된 원인 (클러스터링 로직 차이 추정)
- [ ] 다른 레포(비Python, 대형)에 적용했을 때의 정확도·비용
- [ ] 대표 실행 흐름(sequence) 미작성 — 후보: `codewiki generate` → adapter 5단계 → 모듈 agent 재귀

---

## 3. 다음에 볼 파일 및 함수 (Next Entry Points)

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `codewiki/cli/commands/generate.py` | `generate_command` | CodeWiki 자체 문서에서 빠진 플래그·rung 분기 직접 추적 |
| `codewiki/src/be/cluster_modules.py` | `cluster_modules`, `super_group_modules` | 클러스터링 알고리즘, 실행마다 트리가 달라지는 이유 |
| `codewiki/src/be/caw_backend.py` | `_run_module_agent_sync` | 구독 모드 권한 우회 플래그와 도구 제한 |
| `codewiki/src/be/utils.py` | `validate_single_diagram` | 503 등 서비스 오류를 문법 오류와 구분하는지 |

---

## 4. 참고 사항 및 후속 제안

- 생성 결과는 `artifacts/<repo>/codewiki*`에만 두고, 같은 `-o`에 재실행하면 기존 `.md`를 건너뛴다.
- 코드의 잠재 버그 후보 (CodeWiki 문서가 짚고 코드로 확인): 런타임 instructions 병합 시 `artifact_exclude` 누락 (`codewiki/cli/models/config.py:283-293`).
