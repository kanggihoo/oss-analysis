# CodeWiki Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/FSoft-AI4Code/CodeWiki`
- **분석 Commit SHA**: `3e3d848698c7bf1a0ce2e0b49e66841acd0248aa`
- **분석 일자**: `2026-09-30`
- **작업트리 상태**: `Clean` (`.venv`는 gitignore)
- **분석 목적**: `도입 검토` — 우리 워크스페이스의 보조 분석기(second opinion)로 쓸 수 있는지, 결과 신뢰도는 어느 정도인지

---

## 2. 프로젝트 개요

레포의 dependency graph(tree-sitter 11개 언어 + 빌드/CI 같은 artifact)를 만들고, LLM으로 모듈 트리를 클러스터링한 뒤, 모듈마다 agent가 페이지를 쓰는 **저장소 단위 문서 자동 생성기**다. leaf 모듈부터 쓰고 상위 페이지·`overview.md`는 자식 문서로 작성한다. 진입점은 CLI / Web(FastAPI) / MCP 서버 세 가지이며, API 키 없이 `claude`·`codex` CLI 구독으로도 돌릴 수 있다 (`codewiki/src/be/caw_backend.py`, 코드 확인).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 진입점 3개 → 생성 엔진 → LLM 백엔드·도구 → 출력, `--update`·MCP 경로 view 포함 |

### 그림 읽는 가이드
1. 왼쪽 **진입점** 영역부터: `codewiki CLI`가 주 경로, Web은 `DocumentationGenerator.run()`, MCP는 분석 도구만 제공.
2. 주 경로: `CLIDocumentationGenerator` → `DocumentationGenerator` → `LLMBackend`(`get_backend`가 provider로 Pydantic/Caw 선택) → Agent tools(`str_replace_editor`) → docs 폴더. 아래 행이 그래프 빌드와 클러스터링.
3. 주의: CLI 경로에서는 adapter가 클러스터링을 직접 호출한다(`codewiki/cli/adapters/doc_generator.py:302`). 그림은 이를 단순화했다. Mermaid 검증은 외부 `mermaid.ink`로 나간다.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

- [Q1: CodeWiki가 생성한 문서는 얼마나 정확한가?](./questions/q1-output-quality.md) - *표본 정확도 2.0: 88~95%, 1.0.1: 68%. 식별자·상수는 신뢰, 호출 주체와 CLI 사용법은 재검증 필요. `max_depth`는 세분화 레버가 아님.*

---

## 5. 운영 메모

- 설치: `repos/CodeWiki/.venv` (uv, Python 3.12), 설정 `~/.codewiki/config.json` (claude-code, `claude-sonnet-5-5`). 사용법은 루트 `AGENTS.md`의 CodeWiki 섹션.
- 생성 산출물: `artifacts/CodeWiki/codewiki/` (depth 2), `artifacts/CodeWiki/codewiki-depth4/` (depth 4). 레포 동봉 `docs/`는 업스트림 1.0.1 결과(commit `3c4b4c2`).

## 6. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/codewiki.md](../../wiki/projects/codewiki.md)
