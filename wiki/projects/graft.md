---
title: graft
created: 2026-09-15
updated: 2026-09-15
type: project
tags: [open-source, project, architecture, knowledge-graph, graft, cli, mcp, developer-tools, tooling, evidence]
sources:
  - repos/Graft/README.md
  - repos/Graft/package.json
  - repos/Graft/src/cli.ts
  - repos/Graft/src/engine.ts
  - repos/Graft/src/graph/build.ts
  - repos/Graft/src/graph/extract.ts
  - repos/Graft/src/graph/refresh.ts
  - repos/Graft/src/ask/ask.ts
  - repos/Graft/src/mcp/server.ts
  - repos/Graft/src/mcp/tools.ts
  - reports/Graft/overview.md
confidence: high
---

# graft

`@nanonets/graft` (repo `trailhq/Graft`). 레포의 컨텍스트 그래프를 **로컬 마크다운 폴더**로 만들어 두고,
코딩 에이전트가 매 턴 필요한 노드만 프롬프트로 끌어오게 하는 컨텍스트 레이어.
TypeScript(strict, ESM, Node ≥20), MIT, `src/` 139 파일 / `test/` 122 테스트 파일.

분석 기준: commit `f9e65396e638e517aecae0d731017f53084d70ed` (2026-09-15, clean).
상세 보고서·다이어그램: [reports/Graft/overview.md](../../reports/Graft/overview.md).

## 한 줄 요약

**그래프를 DB가 아니라 재생성 가능한 파일 캐시로 두고, 비싼 층(LLM)과 싼 층(tree-sitter)을 물리적으로 분리한 설계.**

## 핵심 설계 결정 (모두 `코드 확인`)

1. **산출물이 파일이다.** `graft/*.md`(노드) + `graft/.graph/wiring.json`(심볼 단위 코드 그래프).
   데몬도, 인덱스 서버도, 재인덱싱 스케줄도 없다. `graft build`가 `graft/`를 `.gitignore`에 자동 추가한다 —
   그래프는 `node_modules`처럼 재생성 가능한 캐시이고, 팀이 공유하는 건 `.claude/`에 심긴 배선뿐이다.
2. **2티어 파이프라인, LLM은 선택.**
   - Tier 1(`src/graph/extract.ts`, tree-sitter): 모든 함수·클래스·호출 엣지. 결정론적, 키 불필요, 네트워크 불필요.
   - `--deep`(`src/ai/summarize.ts` → `synthesize` → `crux`): 파일 요약 → 개념 노드 합성 + 심볼별 한 줄 요약.
   `build` / `check` / `ask`는 **모델을 전혀 호출하지 않는다.**
3. **질의마다 갱신(refresh-on-query).** `src/graph/refresh.ts:150 ensureFreshGraph()` →
   `fingerprint.probeDrift()`가 워킹트리 **바이트**를 지문과 비교(git 커밋/인덱스 상태가 아님) →
   drift가 있을 때만 변경 파일만 재파싱. 구조적이고 비용이 0이라 "항상 최신"을 기본값으로 둘 수 있다.
   uncommitted / unstaged / staged 편집이 전부 동일하게 보이는 이유도 여기에 있다.
4. **모든 패스가 content hash로 캐시된다.** LLM 패스도 tree-sitter 파싱도 같은 규칙. `--no-reuse`로 콜드 재파싱.
5. **벤더 중립.** `src/ai/llm/factory.ts`가 anthropic / openai-compatible / litellm / orcarouter를 교체.
   `GRAFT_PROVIDER` · `GRAFT_API_KEY` · `GRAFT_MODEL` · `GRAFT_BASE_URL`.
6. **통합 표면이 둘.** `src/cli.ts`(24 command)와 `src/mcp/server.ts`(stdio JSON-RPC).
   `src/mcp/tools.ts`는 CLI를 거치지 않고 `Graft` 엔진과 `ask()`를 직접 호출한다.
   `src/hosts/registry.ts` + `src/claude/*`가 Claude Code·Cursor·Codex에 hook과 statusline을 심는다(`graft init`).

## 네트워크 경계 (`코드 확인`)

기본값은 완전 로컬이고, 밖으로 나가는 경로는 넷뿐이다 — 각각 별도의 트리거를 가진다.

| 경로 | 트리거 | 대상 | 근거 |
|---|---|---|---|
| Deep pass | `graft build --deep` | 사용자가 설정한 LLM 엔드포인트 | `src/ai/providers.ts`, `src/ai/llm/factory.ts` |
| Brain rules | opt-in (`graft connect`) | `/api/public/brains/<id>/rules/anchors` | `src/brain/link.ts:133 baseUrlFor()` |
| GitHub App | 별도 배포물 실행 시 | `https://api.github.com` | `src/app/identity.ts:115` |
| 텔레메트리 | 기본 on, opt-out | `https://events.nanonets.com` (baked host) | `src/telemetry/key.ts:44` |

brain rules 조회는 `AbortSignal.timeout(5000)`으로 묶여 있다 — 주석에 "`ask`는 절대 여기서 블록되면 안 된다"고 명시.
규칙 캐시 TTL 6시간(`RULES_TTL_MS`), 프롬프트에 붙는 규칙은 최대 6개(`MAX_ATTACHED_RULES`).

`src/app/*`는 CLI와 별개의 런타임이다: webhook HTTP 서버(`server.ts:73 createApp`) + `WorkQueue` + `fork()`한 자식 워커
(`review-process.ts:179 childReviewer`, `brain-build-process.ts`). CLI를 거치지 않고 같은 Graph Core를 재사용한다.

## Taste Notes

- **Responsibility Boundaries**: `engine.ts`는 얇은 파사드(160줄)이고 실제 로직은 `graph/`·`ask/`·`ai/`에 있다.
  진입면(cli / mcp / hosts)과 코어가 깨끗하게 갈라져 있어, MCP가 CLI를 재사용하지 않고 엔진을 직접 부를 수 있다.
- **비용 경계를 타입이 아니라 디렉터리로 표현했다.** `src/ai/` 바깥은 전부 $0 경로다.
  "어디부터 돈이 나가는가"를 import 그래프만 봐도 알 수 있는 구조 — 훔칠 만한 패턴.
  → [[stealable-pattern-learning-ai-agent-modules]]
- **재생성 가능성을 커밋 정책으로 강제.** 캐시를 절대 커밋하지 않게 만들어, stale 그래프로 인한 팀 단위 오염을 원천 차단.
- **가장 큰 파일이 제품의 심장.** `src/ask/ask.ts` 1,588줄. 랭킹·융합·컨텍스트 조립이 여기 모여 있고
  아직 읽지 않았다 — 다음 분석의 1순위.

## 비교 메모

- [[graphify]]: 둘 다 코드 → 지식 그래프지만, graphify는 LLM 의미 추출을 파이프라인 중심에 두고
  graft는 tree-sitter 결정론 층을 기본값으로 두고 LLM을 선택 계층으로 밀어냈다. (`추론` — graphify 쪽 재확인 필요)
- [[Understand-Anything]]: 그래프/위키 생성이라는 목표는 겹치나, graft는 "에이전트 프롬프트에 주입"이 최종 소비처다.

## 아직 확인하지 않은 것

- `ask()` 랭킹 내부(`index-file` / `graphrank` / `fuse` 가중치)
- `src/brain/attach.ts:37 rulesForPointers()` — 어떤 규칙이 선택되어 프롬프트에 붙는가
- `src/app/*` 실행 의미론 — 큐잉/중복 제거, 자식 프로세스 메시지 프로토콜, PR 게시 경로
- README 벤치마크(tool call −46%, 토큰 −42%, 시간 −60%, 정확도 54%→66%)의 재현 절차. 레포 내 미발견 (`미확인`).
- 실행 검증 전무. `npm test`(122 파일) 미실행.

관련: [[evidence-backed-analysis]] · [[open-source-analysis-judgment-model]]
