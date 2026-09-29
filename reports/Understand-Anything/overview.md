# Understand-Anything Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/Egonex-AI/Understand-Anything.git` (이전 clone origin은 `Lum1104/…`, 같은 레포의 이전 주소)
- **분석 Commit SHA**: `b05cc3b20990afca537b4fc0a49b4d7fbdc65bb0`
- **분석 일자**: 2026-09-30
- **작업트리 상태**: Clean
- **분석 목적**: 학습 / 설계 참고
- **분석 방식**: CodeWiki 1차 생성(`artifacts/Understand-Anything/codewiki/`, second opinion) → 핵심 주장 코드 검증. archify 구조도 작성 완료(`diagrams/structure.html`).
- **기존 자료**: `artifacts/Understand-Anything/deepwiki`, `gemini` (2026-06 생성, 이전 SHA 기준)

---

## 2. 프로젝트 개요

Claude Code 플러그인으로 코드베이스를 `KnowledgeGraph`(노드·엣지·레이어·투어) JSON으로 만들고 React 대시보드로 탐색하게 하는 도구다. 분석 대상 프로젝트의 `.ua/`(레거시 `.understand-anything/`가 있으면 그쪽)에 `knowledge-graph.json`을 저장한다. 모노레포 구성: `understand-anything-plugin/`(`packages/core`, `dashboard`, `viewer`, tree-sitter WASM 2종, `skills/`, `agents/`, `src/`) + `homepage/`.

## 3. CodeWiki 결과 (후보) 요약

- 890개 컴포넌트, 5개 최상위 모듈, 36개 문서. 시작점: `artifacts/Understand-Anything/codewiki/overview.md` (`index.html`로도 열람 가능).
- 최상위 모듈: `knowledge_graph_core_engine`, `source_code_parsing_plugins`, `interactive_dashboard_ui`, `skill_commands_and_graph_assembly`, `workspace_build_and_delivery`.
- CodeWiki의 Mermaid는 복제하지 않고 archify 지도로 대체했다.

### archify 구조도

| 다이어그램 | 원본 JSON | 시각화 HTML |
|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) |

읽는 순서: ① 윗줄 `사용자 → /understand 스킬 → 스크립트 → 에이전트 → 병합`이 생성 경로, ② `knowledge-graph.json` 아래가 소비 경로(대시보드·질의 빌더), ③ 점선은 보조 관계(core import, 자동 갱신 훅). 미확인: 에이전트별 호출 Phase, 질의 빌더와 스킬의 연결 상세. 

### 대표 실행 흐름: `/understand` 전체 분석

| 다이어그램 | 원본 JSON | 시각화 HTML |
|---|---|---|
| `/understand` 실행 흐름 | [flow.json](./diagrams/flow.json) | [flow.html](./diagrams/flow.html) |

읽는 순서: 위→아래 레인(오케스트레이터 / 스크립트 / 에이전트)을 오가며 왼쪽→오른쪽으로 Phase 0→7. 점선은 증분 갱신 분기.
workflow 유형은 소스 근거 자동 검증(`--repo-root`)을 지원하지 않아, 아래 Phase별 근거 줄을 표로 남긴다.

| Phase | 담당 | 근거 (`understand-anything-plugin/skills/understand/SKILL.md`) |
|---|---|---|
| 0 Pre-flight / 0.5 ignore | 오케스트레이터 + `generate-ignore.mjs` | L43, L240. 증분이면 `prepare-incremental.mjs`가 `SKIP/PARTIAL/ARCHITECTURE/FULL` 계획 산출 (L195-224) |
| 1 SCAN (전체 분석만) | 에이전트 `project-scanner` (내부에서 `scan-project.mjs`) | L259-263 |
| 1.5 BATCH | `compute-batches.mjs` | L306-312 |
| 2 ANALYZE | 에이전트 `file-analyzer`, 동시 5개 → `merge-batch-graphs.py` | L333-381 |
| 3 ASSEMBLE REVIEW (전체 분석만) | 에이전트 `assemble-reviewer` | L441-447 |
| 4 ARCHITECTURE | 에이전트 `architecture-analyzer` (`rerunArchitecture`일 때) | L470-477 |
| 5 TOUR | 에이전트 `tour-builder` (`rerunTour`일 때) | L555-561 |
| 6 REVIEW | 기본은 결정적 인라인 검증, `--review`면 `graph-reviewer` | L643, L767-769 |
| 7 SAVE | `build-fingerprints.mjs` → `meta.json` → 대시보드 자동 실행(검증 통과 시) | L807-876 |

- `agents/`의 나머지 4종(`domain-analyzer`, `article-analyzer`, `design-analyzer`, `knowledge-graph-guide`)은 `/understand`가 아니라 `understand-domain`·`understand-knowledge`·`understand-figma` 스킬 소속 (grep 확인).
- 증분 `SKIP`은 `finalize-incremental.mjs`만 실행, `PARTIAL/ARCHITECTURE`는 Phase 1 SCAN을 건너뜀 (L221-223).

## 4. 코드 검증 결과

| 주장 (CodeWiki) | 결과 | 근거 |
|---|---|---|
| 증분 갱신은 `SKIP/PARTIAL/ARCHITECTURE/FULL_UPDATE` 4단계로 분류 | 코드 확인 | `packages/core/src/change-classifier.ts:5,17-19` (ARCH: 새/삭제 디렉터리 또는 구조 변경 파일 >10, FULL: >30 또는 >50%) |
| 데이터 디렉터리는 `.ua/`, 레거시 `.understand-anything/` 우선 | 코드 확인 | `skills/understand/SKILL.md:126` |
| 대시보드는 core의 `search/types/schema`만 import | 코드 확인 | dashboard `src` import: types 16, schema 6, search 2. core `exports`에는 `./languages`, `./figma`도 있지만 대시보드는 안 씀 |
| 토큰 인증 + `/file-content.json` 보호 | 코드 확인 | `packages/dashboard/vite.config.ts:15,272,371,385` (일회용 토큰, 없으면 403) |
| WASM tree-sitter 사용 | 코드 확인 (이유는 추론) | `web-tree-sitter ^0.26.6` (`packages/core/package.json:60`). "darwin/arm64+Node 24 네이티브 실패"는 CodeWiki 서술이며 미확인 |
| 그래프 병합은 Python 스크립트 | 코드 확인 | `skills/understand/merge-batch-graphs.py`(1369줄), `merge-subdomain-graphs.py` |
| "에이전트 파이프라인이 project-scanner 등을 실행" | **부분 정정** | 실제 오케스트레이션은 `skills/understand/SKILL.md`의 7단계(Phase 0~7, 0.5·1.5 포함). 배치·병합·지문 생성은 **결정적 스크립트**, LLM 에이전트는 Phase 1(`project-scanner`, 내부에서 `scan-project.mjs`)·2·3·4·5(+`--review` 시 6)에서 호출됨 (Phase별 표는 §3 참조) |
| Worktree면 메인 레포 루트로 출력 리다이렉트 | 코드 확인 | `SKILL.md:53` (issue #133) — CodeWiki가 놓친 세부 |

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/Understand-Anything.md](../../wiki/projects/Understand-Anything.md)
