# Graft Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/trailhq/Graft` (npm: `@nanonets/graft` v0.18.0)
- **분석 Commit SHA**: `f9e65396e638e517aecae0d731017f53084d70ed`
- **분석 일자**: `2026-09-15`
- **작업트리 상태**: `Clean` (`git status --porcelain` 무출력)
- **분석 목적**: `학습 / 설계 참고` — 코드 컨텍스트 그래프 파이프라인과 에이전트 통합 방식
- **원본 메타데이터**: [artifacts/Graft/repo-metadata.txt](../../artifacts/Graft/repo-metadata.txt)
- **규모**: TypeScript(strict, ESM, Node ≥20) `src/` 139개 파일, `test/` 122개 테스트 파일

> 참고: `package.json`의 `repository.url`은 `NanoNets/context-graph-engine`, README 배지는 `NanoNets/Graft`를 가리킨다.
> 실제 clone 대상은 `trailhq/Graft`이며 세 이름이 같은 패키지를 가리키는 것으로 보인다. (`검증 수준: 코드 확인` — package.json/README 문자열 확인, 리다이렉트 관계 자체는 `추론`)

---

## 2. 프로젝트 개요

Graft는 **레포의 컨텍스트 그래프를 "링크된 마크다운 파일 폴더"로 만들어 두는 로컬 캐시**다.
`graft/` 디렉터리에 노드(`*.md`)와 심볼 단위 코드 그래프(`.graph/wiring.json`)를 생성하고,
코딩 에이전트(Claude Code, Cursor, Codex, Gemini 등)가 매 턴 이 그래프에서 필요한 조각만 프롬프트에 끌어오게 한다.

핵심 주장(README 기준, 본 세션에서 재측정하지 않음 — `검증 수준: 미확인`):
tool call −46%, 토큰 −42%, 시간 −60%, 정확도 54% → 66%.

설계상 특징으로 확인한 것(`검증 수준: 코드 확인`):

1. **그래프는 커밋 대상이 아니다.** `graft build`가 `graft/`를 `.gitignore`에 자동 추가한다 (`src/context/node-file.ts:ensureGitignored`를 `src/graph/build.ts:19`에서 import). 공유하는 것은 `graft init`이 `.claude/`에 심은 배선뿐이다.
2. **LLM 없이도 동작한다.** Tier 1은 순수 tree-sitter다. `src/graph/extract.ts`가 tree-sitter 문법을 직접 import하고(9~17행), `build`/`check`/`ask` 경로에는 LLM 호출이 없다. 키가 필요한 것은 `--deep` 뿐이다.
3. **모든 질의가 먼저 그래프를 갱신한다.** `src/graph/refresh.ts:150 ensureFreshGraph()`가 fingerprint와 워킹트리 바이트를 비교해(`probeDrift`) 변한 파일만 다시 파싱한다. 구조적 갱신이므로 모델 호출이 없다.
4. **벤더 중립.** `src/ai/llm/factory.ts`가 anthropic / openai-compatible / litellm / orcarouter를 갈아끼운다.

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | CLI/MCP 진입면 → 엔진 → 결정론적 그래프 코어 → LLM 경계 |
| 대표 실행 흐름 | [flow.json](./diagrams/flow.json) | [flow.html](./diagrams/flow.html) | `graft ask "<query>"` 한 번의 호출 전체 |
| 전체 시스템 아키텍처 | [system.json](./diagrams/system.json) | [system.html](./diagrams/system.html) | 로컬 CLI 런타임 + GitHub App 런타임 + 외부 서비스 경계 |

### 그림 읽는 가이드 (structure)

1. **왼쪽 진입면부터.** `graft CLI`(`src/cli.ts`, 24개 command)가 유일한 조립 지점이고, `MCP Server`는 `graft mcp`로 띄우는 별도 표면이다. `src/mcp/tools.ts`는 CLI를 거치지 않고 `Graft` 엔진과 `ask()`를 직접 호출한다(tools.ts 5~10행).
2. **가운데 주황 점선 박스가 경계선.** 그 안(`Graph Build`/`graft cache`/`Ask Retrieval`/`Freshness Refresh`/`tree-sitter Extract`)은 모델도 네트워크도 쓰지 않는다.
3. **위쪽 `Deep Pass → LLM Providers`만 키가 필요하다.** `--deep` 점선이 경계를 넘는 유일한 화살표다.
4. **미확인 영역**: `Side Commands`(blast · viz · grep · brain)는 존재와 진입점만 확인했고 내부 동작은 이번 세션에서 읽지 않았다. `src/app/*`(server, review-worker, queue 등 GitHub App 쪽)과 `src/telemetry/*`는 그림에서 제외했다.

### 그림 읽는 가이드 (flow)

1. `graft ask`는 답하기 전에 항상 `ensureFreshGraph()`를 먼저 호출한다.
2. `probeDrift()`는 워킹트리 바이트를 fingerprint와 비교한다 — git 커밋/인덱스 상태가 아니다. 그래서 uncommitted·unstaged·staged 편집이 전부 동일하게 보인다.
3. drift가 있을 때만 `buildGraph()`가 돌고, 그때도 content hash가 바뀐 파일만 재파싱한다.
4. 이후 경로(`loadGraphCached` → `ask()` 랭킹/융합 → brain rule 부착)는 전부 결정론적이며 비용이 0이다.

### 그림 읽는 가이드 (system)

1. **가운데 가로줄이 기본 경로다.** `Coding Agents → graft CLI + MCP → Graph Core → graft/ cache → Retrieval`.
   이 구간 전체가 주황 점선 박스(`Deterministic — no model, no network`) 안이거나 그 앞단이다.
2. **네트워크로 나가는 지점은 네 군데뿐이다.**
   - `Deep Pass → LLM Provider`: `--deep`일 때만, 사용자 키로 (`src/ai/providers.ts`)
   - `Brain Client → Trail Brain`: opt-in. `src/brain/link.ts:133 baseUrlFor()` → `/api/public/brains/<id>/rules/anchors`, 타임아웃 5초로 `ask`를 절대 블록하지 않음
   - `GitHub App → GitHub API`: 별도 배포물에서만 (`src/app/identity.ts:115`, 기본 `https://api.github.com`)
   - 텔레메트리: 그림에서 생략. `src/telemetry/key.ts:44`에 `https://events.nanonets.com`이 baked host로 박혀 있다
3. **아래쪽 박스는 다른 런타임이다.** `src/app/*`는 webhook HTTP 서버(`server.ts:73 createApp`) + `WorkQueue` + `fork()`한 자식 워커(`review-process.ts:179 childReviewer`) 구조이며,
   CLI를 거치지 않고 같은 `Graph Core`를 재사용한다. 이걸 돌리려면 GitHub App 자격증명이 따로 필요하다(`docs/github-app.md`).
4. **미확인 영역**: 각 박스 내부 동작은 이 그림에서 다루지 않는다. 모듈 수준은 [structure.html](./diagrams/structure.html), 질의 1회 흐름은 [flow.html](./diagrams/flow.html) 참고.
   `src/app/*`와 `src/brain/*`는 import 그래프와 시그니처까지만 확인했고 실행 의미론은 읽지 않았다.

> archify 검증 상태: 세 다이어그램 모두 `deliver` 9/9 artifact check 통과, composition showcase 0 errors / 0 warnings. 소스 근거는 structure 17건 · system 21건이 실제 checkout(`repos/Graft`)에 대해 검증됨. `visual-check`도 세 파일 모두 pass(1440×900 / 1600×1000 / 1920×1080 / 2048×1320). 시각적 검토는 세 다이어그램의 2048×1320 light 스크린샷을 직접 확인함. 검증 수신증은 [artifacts/Graft/](../../artifacts/Graft/)에 보관.

---

## 4. 핵심 질문 및 세부 답변 목록 (Questions)

아직 없음. 다음 세션 후보 질문은 [next.md](./next.md) 참고.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **축적된 위키 지식**: [wiki/projects/graft.md](../../wiki/projects/graft.md)
