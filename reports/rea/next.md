# Next Session Plan: REA

- **상위 개요**: [overview.md](./overview.md)
- **현재 기준 Commit SHA**: `60c08802a7b6d2195121114a9e4224492f138185`
- **작성/갱신 일자**: `2026-10-14`

## 1. 이번 세션에서 확인한 범위
- [x] clone, README/AGENTS.md/docs/architecture.mermaid 읽기
- [x] `scripts/rea.mjs` 분기, `src/main.ts` 시작부 확인
- [x] `analyze_javascript_application` 서비스 계층(`JavaScriptApplicationService.ts`) 코드 확인
- [x] 구조도/흐름도 archify 작성 (deliver 통과; 브라우저 visual-check는 미실행)

## 2. 남은 질문
- [ ] 개요 4절 질문 1~5

## 3. 다음에 볼 파일 및 함수

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `src/server/registerElectronTools.ts` | `runElectronTool` | MCP 입력 → application 호출 바인딩 |
| `src/application/javascript/JavaScriptArtifactReconstruction.ts` | `reconstructJavaScriptArtifact` | 실제 분석 단계 |
| `src/domain/evidence.ts` | `Evidence` | Evidence 모델 |
| `src/application/` | `SessionProviderRouter`, `AnalysisProviderRegistry` | provider 선택 규칙 |

## 4. 참고
- 빌드/실행 안 함 (`npm ci && npm run build:cached` 필요). 외부 분석기(CodeWiki 등) 미사용.
