---
repo: Understand-Anything
local_checkout: /Users/kkh/Desktop/oss-analysis/repos/Understand-Anything
verification_commit: 7a3b7511b26a1816be3b6cc5683b34779e0abce9
baseline_artifacts:
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/2-understand-anything-pipeline.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/3-understand-anything-core.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/4-understand-anything-dashboard.md
---

# Understand-Anything source-verified overview

## 검증 범위

Gemini 산출물 3개를 baseline/hypothesis로 읽고, 현재 로컬 checkout의 실제 source path와 명령 출력으로 검증했다. 이 보고서의 source-of-truth는 `repos/Understand-Anything`이며 Gemini 문서는 권위가 아니라 비교 기준이다.

## 현재 checkout 상태

- Commit: `7a3b7511b26a1816be3b6cc5683b34779e0abce9` (`git rev-parse HEAD`)
- 작업트리: clean (`git status --short` 출력 없음)
- Repo URL/설명: root `package.json`은 `git+https://github.com/Lum1104/Understand-Anything.git`와 “LLM intelligence + static analysis” dashboard 설명을 가진다 (`package.json:5-10`).
- Node/pnpm: `node --version` → `v26.0.0`, `pnpm --version` → `10.6.2`.

## 실제 프로젝트 구조와 패키지 경계

현재 checkout은 monorepo이며 root workspace가 실제 배포 plugin과 homepage를 포함한다.

| 영역 | 현재 source evidence | 역할 |
|---|---|---|
| Root workspace | `package.json:2-35`, `pnpm-workspace.yaml:1-4` | pnpm workspace, root build/test/lint/dev:dashboard script |
| Plugin package | `understand-anything-plugin/package.json:2-15` | slash skill/agent package `@understand-anything/skill`; core workspace dependency와 graphology dependency |
| Core package | `understand-anything-plugin/packages/core/package.json:2-55` | graph schema, validation, persistence, search, language registry, tree-sitter/plugin/parser layer |
| Dashboard package | `understand-anything-plugin/packages/dashboard/package.json:2-42` | Vite/React dashboard; ReactFlow, ELK, D3 force, Zustand, prism source viewer |
| Homepage | `homepage/package.json` | 별도 웹사이트 패키지(이번 pipeline/core/dashboard 분석 대상은 아님) |
| Platform plugin manifests | `.claude-plugin/plugin.json:2-18`, `.cursor-plugin/plugin.json:13-14` | marketplace metadata 및 skills/agents 설치 경로 선언. Cursor manifest는 `skills`/`agents`를 root-relative로 지정 |

주요 디렉터리는 다음과 같다.

- Slash skills: `understand-anything-plugin/skills/understand`, `understand-dashboard`, `understand-domain`, `understand-knowledge`, `understand-chat`, `understand-diff`, `understand-explain`, `understand-onboard`.
- Agents: `understand-anything-plugin/agents/project-scanner.md`, `file-analyzer.md`, `assemble-reviewer.md`, `architecture-analyzer.md`, `tour-builder.md`, `graph-reviewer.md`, `domain-analyzer.md`, `article-analyzer.md`, `knowledge-graph-guide.md`.
- Core source: `understand-anything-plugin/packages/core/src/` with `schema.ts`, `types.ts`, `persistence/`, `plugins/`, `languages/`, `analyzer/`.
- Dashboard source: `understand-anything-plugin/packages/dashboard/src/` with `App.tsx`, `store.ts`, `components/`, `utils/`, `themes/`, `locales/`, plus `vite.config.ts`.
- Hook/prompt: `understand-anything-plugin/hooks/hooks.json`, `understand-anything-plugin/hooks/auto-update-prompt.md`.
- Repo-level helper: `scripts/generate-large-graph.mjs` only; production pipeline scripts live under the `understand` skill directory, not root `scripts/`.

## 실행 검증 결과

처음에는 `node_modules`가 없어서 build/test가 dependency missing으로 실패했다. 이후 `pnpm install --frozen-lockfile`를 실행했고 성공했다. 설치 후 작업트리는 여전히 clean이다(의존성 디렉터리는 git ignore).

| 명령 | 결과 | 핵심 출력 |
|---|---:|---|
| `pnpm install --frozen-lockfile` | 성공 | 5 workspace projects, 572 packages added, prepare에서 core build 성공 |
| `pnpm --filter @understand-anything/core build` | 성공 | `tsc` exit 0 |
| `pnpm --filter @understand-anything/core test` | 성공 | 33 files / 670 tests passed |
| `pnpm --filter @understand-anything/skill build` | 성공 | `tsc` exit 0 |
| `pnpm --filter @understand-anything/dashboard build` | 성공(경고 있음) | Vite build success, `elk` chunk 1,438.65 kB로 500 kB chunk warning |
| `pnpm test` | 성공 | 16 files / 200 tests passed |
| `pnpm lint` | 성공 | `eslint .` exit 0 |

## 현재 소스 기준 핵심 결론

1. Understand-Anything은 터미널 CLI 중심 프로젝트라기보다 multi-platform AI coding-agent plugin이다. `/understand` 같은 명령은 `.claude/commands`가 아니라 `understand-anything-plugin/skills/*/SKILL.md`와 plugin manifest의 skills/agents 경로로 제공된다.
2. 핵심 pipeline은 Gemini가 말한 “정적 분석 + LLM agent” 하이브리드가 맞다. 다만 현재 소스의 실제 단계는 `/understand` SKILL.md의 Phase 0.5 ignore setup, Phase 1.5 batching, default inline deterministic validation, fingerprint baseline, dashboard auto-launch 조건까지 포함한다.
3. Core schema의 node/edge type 수는 현재 `types.ts`와 `schema.ts` 기준으로 NodeType 21개, EdgeType 35개가 맞다.
4. Dashboard 보안 claim은 대체로 확인됐다. `vite.config.ts`는 localhost bind, access token, protected endpoint, graph-derived allowlist, traversal/null-byte/absolute-path/size/binary guard를 구현한다.
5. Auto-update는 일반 git hook shell script가 아니라 plugin hook 설정(`hooks.json`)이 `SessionStart`와 Claude `PostToolUse` Bash matcher에서 prompt 실행을 요구하는 구조다.

## 하위 보고서

- `reports/Understand-Anything/architecture.md` — 패키지/책임 경계
- `reports/Understand-Anything/pipeline.md` — `/understand`, domain/knowledge, batch/review/update 흐름
- `reports/Understand-Anything/core.md` — schema, validation, builder, tree-sitter, parser, plugin, persistence
- `reports/Understand-Anything/dashboard.md` — Vite middleware, token/file security, ReactFlow/ELK/D3/Zustand/theme/i18n
- `reports/Understand-Anything/gemini-baseline-comparison.md` — Gemini baseline vs current source verdict
