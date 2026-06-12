---
title: graphify Agent Skill Integration
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [graphify, agent-framework, knowledge-graph, developer-tools, workflow, tooling, evidence]
sources:
  - deepwiki-ko/graphify/4.4-claude-code-skill-integration.md
  - repos/graphify/graphify/__main__.py
  - repos/graphify/graphify/skill-codex.md
  - repos/graphify/graphify/skills/codex/references/query.md
  - repos/graphify/graphify/skills/codex/references/extraction-spec.md
  - repos/graphify/graphify/always_on/agents-md.md
confidence: high
---

# graphify Agent Skill Integration

`graphify`의 agent 통합은 CLI를 대체하지 않는다. CLI는 실행 엔진이고, skill/always-on instruction은 Codex/Claude Code/Hermes 같은 agent에게 **언제 `graphify`를 쓰고 어떤 순서로 graph를 만들고 질의할지** 알려주는 운영 매뉴얼이다.

관련 CLI lifecycle은 [[graphify-cli-reference]], `extract`/`query`의 backend 없는 동작은 [[graphify-extract-query-mechanics]], graphify LLM backend 의미는 [[graphify-llm-semantic-extraction]]에 있다.

## 기본 동작 모델

```text
User question
→ Agent reads AGENTS.md / CLAUDE.md / skill rules
→ If graphify-out/graph.json exists, use graphify query/path/explain first
→ If graph is missing or user asks /graphify, load graphify skill
→ Skill runs detect/extract/build/cluster/report/export steps
→ Persistent state is written to graphify-out/
→ Later sessions reuse graphify-out/graph.json
```

핵심은 repo 전체를 agent context에 넣는 것이 아니라, `graphify-out/graph.json`을 durable codebase memory로 두고 필요한 subgraph만 꺼내 쓰는 것이다.

## Codex 설치 산출물

현재 source 기준 Codex platform은 `repos/graphify/graphify/__main__.py`의 `_PLATFORM_CONFIG`에 정의되어 있다.

전역 skill 설치:

```bash
graphify install --platform codex
```

산출물:

```text
~/.codex/skills/graphify/SKILL.md
~/.codex/skills/graphify/references/
~/.codex/skills/graphify/.graphify_version
```

Project-scope 통합:

```bash
graphify install --project --platform codex
```

산출물:

```text
.codex/skills/graphify/SKILL.md
.codex/skills/graphify/references/
.codex/skills/graphify/.graphify_version
AGENTS.md
.codex/hooks.json
```

DeepWiki 번역본은 Codex target을 `.agents/skills` 계열로 설명하지만, 현재 local source 기준 Codex target은 `.codex/skills/graphify/SKILL.md`이다. `.agents`는 Amp/Antigravity 계열에서 더 직접적으로 쓰인다.

## Skill file, references, AGENTS.md

Codex용 core skill은 `repos/graphify/graphify/skill-codex.md`이다. `/graphify` 요청을 받으면 agent가 이 파일의 build/update/query/export 절차를 따른다.

`references/`는 progressive disclosure용 sidecar다. 주요 파일은 `query.md`, `extraction-spec.md`, `update.md`, `exports.md`, `transcribe.md`, `github-and-merge.md`, `hooks.md`, `add-watch.md`이다. agent는 query가 필요하면 `query.md`, semantic extraction이 필요하면 `extraction-spec.md`, export가 필요하면 `exports.md`만 읽는다.

Project-scope install은 `AGENTS.md`에 query-first 정책도 쓴다.

```text
When the user types /graphify, invoke the graphify skill first.
For codebase questions, first run graphify query when graphify-out/graph.json exists.
Use graphify path for relationship questions.
Use graphify explain for focused concept questions.
Read GRAPH_REPORT.md only for broad architecture review or when query/path/explain is insufficient.
After modifying code, run graphify update .
```

이 정책 때문에 agent는 전체 source나 `GRAPH_REPORT.md`를 먼저 읽기보다 `graphify query "<question>"`로 작은 subgraph context를 먼저 가져온다.

## CLI backend vs host agent LLM

`graphify`의 LLM backend와 host agent의 LLM은 다르다.

| 실행 방식 | graphify backend 필요 여부 | LLM 사용 위치 |
|---|---:|---|
| 순수 CLI + code-only | 필요 없음 | 없음. AST extraction만 수행 |
| 순수 CLI + docs/papers/images | 필요 | graphify Python이 Gemini/OpenAI/Claude 등 backend 호출 |
| Codex/Claude skill + code-only | graphify backend 필요 없음 | agent는 orchestration, extraction은 AST |
| Codex/Claude skill + docs/papers/images | graphify backend가 없어도 가능 | host agent/subagent가 semantic extraction 수행 |
| 순수 CLI `cluster-only` + backend 없음 | 필요 없음 | label은 `Community N` placeholder |
| Codex/Claude skill community naming | graphify backend 필요 없음 | host agent가 `.graphify_analysis.json`을 읽고 이름 지정 |

Agent skill 기반은 “LLM을 안 쓰는 모드”가 아니다. **graphify Python backend를 쓰지 않고, 실행 중인 Codex/Claude agent LLM이 semantic work를 대신하는 모드**다. Code-only AST extraction만 진짜 LLM-free다.

## Codex semantic extraction flow

Codex skill은 extraction을 두 부분으로 나눈다.

```text
Part A: code files → graphify.extract.extract() AST extraction
Part B: docs/papers/images → Codex subagents semantic extraction
```

Code-only corpus는 Part B를 skip한다. Docs/papers/images가 있으면 Codex는 `references/extraction-spec.md`의 compact prompt를 worker에게 주고 JSON graph fragment를 받는다.

Codex에서는 Claude Code의 Agent tool 대신 `spawn_agent`, `wait_agent`, `close_agent`를 사용하도록 되어 있다. 이를 위해 Codex 설정에 multi-agent feature가 필요하다.

```toml
# ~/.codex/config.toml
[features]
multi_agent = true
```

Subagent는 파일 chunk를 읽고 `nodes`, `edges`, `hyperedges`, token counts를 반환한다. Host Codex는 이를 `.graphify_semantic_new.json`, `.graphify_semantic.json`으로 병합한 뒤 AST 결과와 합쳐 `.graphify_extract.json`을 만든다.

## Agent 기반 community naming

Codex skill Step 4는 graph build/cluster/report를 먼저 placeholder label로 수행한다.

```text
Community 0
Community 1
Community 2
```

그 다음 Step 5에서 agent가 `graphify-out/.graphify_analysis.json`을 읽고 각 community의 node labels를 보고 2~5단어 이름을 붙인다. 순수 CLI에서는 backend가 없으면 placeholder가 남지만, agent skill flow에서는 host agent가 naming을 수행할 수 있다.

## `.codex/hooks.json`의 현재 역할

Codex project install은 `.codex/hooks.json`에 PreToolUse hook을 등록한다. 의미는 “Codex가 Bash tool을 실행하기 직전에 `graphify hook-check`를 실행하라”이다. 하지만 현재 source 기준 `graphify hook-check`는 no-op이다.

```text
graphify hook-check
→ output 없음
→ exit 0
→ Bash tool execution continues
```

`__main__.py` 주석은 Codex Desktop이 `PreToolUse`에서 `additionalContext`를 거부하기 때문에 hook을 no-op으로 유지한다고 설명한다. graph guidance는 hook이 아니라 `AGENTS.md`와 skill file을 통해 전달된다.

중요도는 다음 순서다.

```text
1. AGENTS.md: 항상 켜져 있는 query-first 행동 정책
2. .codex/skills/graphify/SKILL.md: /graphify 실행 절차
3. .codex/skills/graphify/references/: 상황별 상세 매뉴얼
4. .codex/hooks.json: 현재는 Bash를 깨지 않게 하는 no-op compatibility hook
```

`.codex/hooks.json`만 있고 `AGENTS.md`/skill이 없으면 현재 source 기준 실질 효과는 거의 없다. 반대로 hook이 없어도 `AGENTS.md`와 skill을 Codex가 읽으면 graphify 사용 자체는 가능하다.

## 실전 패턴

처음 graph 생성은 `/graphify .`로 시작한다. 기존 graph에 질문할 때는 `graphify query "authentication flow"`, `graphify explain "AuthService"`, `graphify path "AuthService" "UserRepository"`처럼 작은 subgraph를 먼저 가져온다. 코드 수정 후에는 `graphify update .`로 AST graph를 갱신한다.

## 관련 페이지

- [[graphify]]
- [[graphify-cli-reference]]
- [[graphify-extract-query-mechanics]]
- [[graphify-llm-semantic-extraction]]
