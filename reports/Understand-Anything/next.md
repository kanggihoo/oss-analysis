# Next Session Plan: Understand-Anything

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `b05cc3b20990afca537b4fc0a49b4d7fbdc65bb0`
- **작성/갱신 일자**: 2026-09-30

## 1. 이번 세션에서 확인한 범위
- [x] 레포 최신화(origin을 Egonex-AI로 교정), 메타데이터 기록
- [x] CodeWiki 생성 (`artifacts/Understand-Anything/codewiki/`, 로그 `codewiki-generate.log`)
- [x] 증분 분류·데이터 디렉터리·대시보드 보안·core 서브패스·병합 스크립트 코드 확인

## 2. 남은 질문
- [x] archify 구조도 `diagrams/structure.html`
- [x] `/understand` 실행 흐름도 `diagrams/flow.html`
- [x] 에이전트별 호출 Phase (overview 표). 남은 것: 각 에이전트의 입출력 JSON 계약(`agents/*.md`)
- [ ] `merge-batch-graphs.py`의 병합·중복 제거·검증 규칙
- [ ] 노드/엣지 타입과 `schema` 검증 (`packages/core/src/schema`, `types`)
- [ ] fingerprint 기반 증분 갱신 전체 경로 (`build-fingerprints.mjs` → `change-classifier.ts` → `finalize-incremental.mjs`)
- [ ] WASM tree-sitter 선택 이유 (네이티브 실패 주장 검증)

## 3. 다음에 볼 파일
| 파일 | 대상 | 목적 |
|---|---|---|
| `understand-anything-plugin/skills/understand/SKILL.md` | Phase 0~7 | 실행 흐름 다이어그램 |
| `packages/core/src/change-classifier.ts` | classifier | 증분 임계값 |
| `skills/understand/merge-batch-graphs.py` | 병합 | 그래프 조립 규칙 |
| `packages/dashboard/vite.config.ts` | `readSourceFile` | 경로 허용 목록 |

## 4. 참고
- DeepWiki/Gemini 결과는 이전 SHA 기준이라 최신과 차이가 있을 수 있음.
