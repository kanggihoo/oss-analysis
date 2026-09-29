---
title: codewiki
created: 2026-09-30
updated: 2026-09-30
type: project
tags: [open-source, project, documentation, code-analysis, llm, agent-framework, mcp, tooling, evidence]
sources:
  - repos/CodeWiki/codewiki/src/be/caw_backend.py
  - repos/CodeWiki/codewiki/src/be/backend.py
  - repos/CodeWiki/codewiki/src/be/documentation_generator.py
  - repos/CodeWiki/codewiki/cli/adapters/doc_generator.py
  - repos/CodeWiki/codewiki/src/be/utils.py
  - reports/CodeWiki/overview.md
  - reports/CodeWiki/questions/q1-output-quality.md
confidence: high
---

# CodeWiki

AI agent가 dependency graph를 기반으로 저장소 단위 문서를 생성하는 도구 (FSoft-AI4Code, MIT). 분석 commit `3e3d848`, 상세는 [reports/CodeWiki/overview.md](../../reports/CodeWiki/overview.md).

## 핵심 설계
- **그래프 → 클러스터 → 재귀 agent**: tree-sitter(11개 언어) + artifact(빌드/CI/설정)로 그래프를 만들고, cluster model이 모듈 트리를 JSON으로 정한 뒤, main model agent가 leaf부터 페이지를 쓴다. 상위 페이지는 자식 문서로 쓴다.
- **백엔드 추상화**: `get_backend()` 한 곳에서 provider로 `PydanticAIBackend`(API 키) / `CawBackend`(`claude`·`codex` CLI 구독)를 고른다. 구독 모드는 CodeWiki 도구를 caw MCP로 노출하고 CLI 자체의 Write/Edit/Bash를 막아 모든 쓰기를 Mermaid 검증 경로로 보낸다.
- **세분화 조건**: 모듈 위임은 복잡도 AND 깊이 < `max_depth` AND 토큰 ≥ `max_token_per_leaf_module`. `max_depth`는 상한일 뿐이다.
- **재개 가능성**: 출력 폴더에 `.md`가 있으면 그 모듈을 건너뛴다 → 설정을 바꿔 재생성하려면 새 폴더.

## 도구로서의 신뢰도 (표본 팩트체크, 코드 확인)
- 2.0 결과 정확도 88~95%, 업스트림 동봉 1.0.1 문서 68%.
- 식별자·상수·기본값은 거의 정확, 존재하지 않는 식별자 생성은 드묾.
- 반복되는 오류 유형은 **호출 주체**(모듈 경계를 넘는 누가-누구를-부르나)와 **CLI 사용법**.
- 클래스가 없는 함수 위주 진입점 파일(CLI 명령, MCP 서버)이 누락되기 쉽다.
- 클러스터링이 LLM 기반이라 실행마다 모듈 트리와 커버리지가 달라진다.
- 활용 원칙은 [[evidence-backed-analysis]]와 같다: 지도·조회용으로 쓰고 흐름은 코드로 검증.

## 운영 주의
- Mermaid 검증이 다이어그램을 외부 `mermaid.ink`로 보낸다(`MERMAID_VALIDATE=0`으로 끔). 서비스 503도 "syntax errors"로 보고된다.
- 워크스페이스 사용법(설치 위치, 출력 경로 규칙)은 루트 `AGENTS.md` CodeWiki 섹션.

## 관련
- [[deepwiki-first-baseline]] — 외부 baseline을 second opinion으로 다루는 방식
- [[Understand-Anything]]
