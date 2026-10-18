---
sha: "f8d46390613f068f232eb14ad91804841c64bdfa"
created: 2026-10-16
updated: 2026-10-17
---

# context-mode Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/mksglu/context-mode.git`
- **분석 Commit SHA**: `f8d46390613f068f232eb14ad91804841c64bdfa` (`v1.0.136-1-gf8d4639`)
- **작업트리 상태**: `Clean`
- **분석 목적**: `학습` — Claude Code hook을 언제·어떻게 트리거해 동작을 강제하는지 (특히 `PreToolUse` 차단·라우팅)
- **메타데이터**: [`artifacts/context-mode/repo-metadata.txt`](../../artifacts/context-mode/repo-metadata.txt)

---

## 2. 프로젝트 개요

README 요약: MCP 도구 호출이 원본 데이터를 context window에 그대로 쌓는 문제(예: Playwright 스냅샷 56KB)를 줄이는 MCP 서버 + hook 플러그인. 라이선스 Elastic-2.0 (`package.json`, `LICENSE`: 코드 확인). 버전 1.0.136.

### 소스 구성

| 위치 | 역할 | 검증 수준 |
|---|---|---|
| `src/server.ts` | MCP 서버. `ctx_execute`, `ctx_execute_file`, `ctx_batch_execute` 등 도구 등록 | 코드 확인 (도구 전체 목록 `미확인`) |
| `src/store.ts` | SQLite FTS5 + BM25 기반 지식 저장소 (`ContentStore`) | 코드 확인 |
| `src/executor.ts`, `security.ts` | 샌드박스 실행, 경로 deny 정책(`checkFilePathDenyPolicy`) | 존재만 확인 |
| `hooks/hooks.json` | Claude Code 등록: `PreToolUse`, `PostToolUse`, `PreCompact`, `UserPromptSubmit`, `SessionStart` | 코드 확인 |
| `hooks/*.mjs`, `hooks/core/` | 이벤트별 스크립트, 공통 라우팅(`core/routing.mjs`), 출력 형식(`core/formatters.mjs`) | 코드 확인 |
| `hooks/<platform>/` | codex, cursor, gemini-cli, kiro, vscode-copilot 등 플랫폼별 어댑터 | 존재만 확인 |

### 주요 기능

| 기능 | 설명 (README 기준) | 코드 근거 | 검증 수준 |
|---|---|---|---|
| Context Saving | 큰 원본 데이터를 샌드박스에서 처리하고 요약만 context에 반환 (README: 315KB → 5.4KB) | `src/server.ts` `ctx_execute*` | 코드 확인(도구 존재) / 수치 `미확인` |
| 도구 호출 라우팅·차단 | `PreToolUse`에서 Bash·WebFetch·Read·Grep 등을 가로채 deny / ask / allow 결정 또는 context-mode 도구로 유도 | `hooks/pretooluse.mjs`, `hooks/core/formatters.mjs` (`permissionDecision`) | 코드 확인 (분기 규칙 `미확인`) |
| Session Continuity | 파일 수정·git·오류·결정을 SQLite에 기록하고, 압축(compact) 후 FTS5/BM25로 필요한 것만 다시 검색 | `hooks/posttooluse.mjs`, `precompact.mjs`, `sessionstart.mjs`, `src/store.ts` | 코드 확인(구성) / 동작 `미확인` |
| 지식 색인·검색 | 문서·URL을 색인하고 BM25로 검색 | `src/store.ts`, `ctx_index`·`ctx_search`·`ctx_fetch_and_index`(README) | 코드 확인(store) / 도구 `미확인` |
| 다중 플랫폼 | Claude Code 외 Codex, Cursor, Gemini CLI, Kiro 등 지원 | `hooks/<platform>/`, `.codex-plugin/`, `.cursor-plugin/` | 존재만 확인 |
| 진단·통계 | `ctx-stats`, `ctx-doctor`, `ctx-upgrade`, `ctx-purge`, `ctx-insight` | README | `미확인` |

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

`미작성`

---

## 4. 질문과 조사 기록 (Questions)

- [Q1: Claude Code hook은 어떻게 정의하는가](./questions/q1-claude-code-hook-definition.md) - *`hooks/hooks.json`에 이벤트 → matcher → command로 정의. `plugin.json`에는 hook 항목 없음*

---

## 5. 다음 작업 및 연계 링크

- **기능 스펙**: 없음
