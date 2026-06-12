---
title: graphify CLI Reference
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [graphify, knowledge-graph, developer-tools, tooling, workflow, evidence]
sources:
  - artifacts/graphify/deepwiki/pages-md/4.1-cli-reference.md
  - repos/graphify/graphify/__main__.py
  - repos/graphify/graphify/skill.md
  - repos/graphify/graphify/querylog.py
  - repos/graphify/graphify/benchmark.py
  - actual command: python3 -m graphify --help
confidence: high
---

# graphify CLI Reference

이 페이지는 [[graphify]]의 CLI를 “knowledge graph lifecycle을 운영하는 컨트롤 패널”로 정리한다. DeepWiki의 CLI Reference는 큰 방향은 맞지만 `/graphify` assistant command와 실제 terminal CLI `graphify`가 섞여 있으므로, 현재 local source와 실제 `python3 -m graphify --help` 출력 기준으로 보정한다.

## 핵심 역할

`graphify` CLI는 다음 네 가지 일을 한다.

```text
install        → AI coding assistant에 graphify skill/rule 설치
extract/update → graph.json 생성 및 갱신
query/analyze  → query, path, explain, affected로 graph 탐색
export/auto    → HTML, tree, wiki, Obsidian, hook, watch, benchmark
```

즉 CLI는 단순 실행 wrapper가 아니라, `graph.json`을 만들고 유지하고 질문하는 운영 인터페이스다. `GRAPH_REPORT.md`가 넓은 architecture summary라면, `query/path/explain/affected`는 특정 질문에 맞는 작은 subgraph를 꺼내는 인터페이스다. Agent가 이 CLI를 skill/always-on instruction으로 사용하는 방식은 [[graphify-agent-skill-integration]], `extract`와 `query`의 backend 없는 동작은 [[graphify-extract-query-mechanics]]에 정리했다.

## `/graphify`와 `graphify` 구분

| 형태 | 의미 | 예 |
|---|---|---|
| `/graphify ...` | Claude Code/Codex/Hermes 같은 assistant skill 표현 | `/graphify <path> --update` |
| `graphify ...` | terminal에서 실행하는 실제 CLI | `graphify update <path>` |

DeepWiki 문서의 `/graphify --wiki`, `/graphify --cluster-only` 같은 표현은 assistant skill 사용법에 가깝다. 직접 CLI에서는 현재 source 기준으로 `graphify export wiki`, `graphify cluster-only <path>`처럼 command/subcommand 형태를 쓴다.

## 설치와 agent 연동

`graphify install [--platform P]`는 graph를 만드는 명령이 아니라, graphify skill을 AI assistant config에 등록하는 명령이다. 실제 help 기준 platform은 `claude`, `windows`, `codebuddy`, `codex`, `opencode`, `aider`, `amp`, `claw`, `droid`, `trae`, `trae-cn`, `gemini`, `cursor`, `antigravity`, `hermes`, `kiro`, `pi`, `devin` 등을 포함한다.

```bash
graphify install --platform claude
graphify install --platform codex
graphify install --platform hermes
graphify install --platform cursor
```

이 명령은 platform별 skill/rule 파일, hook 설정, version marker 등을 설치해 agent가 “codebase 질문이면 먼저 graphify graph를 써라”는 규칙을 알게 한다.

## graph 생성과 갱신

| 명령 | 역할 | 언제 쓰나 |
|---|---|---|
| `graphify extract <path>` | detect → AST/semantic extraction → build → cluster → output | 첫 graph 생성, CI/script, headless 분석 |
| `graphify update <path>` | code files 재추출 및 graph 갱신, LLM 불필요 | 코드 변경 후 빠른 갱신 |
| `graphify cluster-only <path>` | 기존 `graph.json` 재클러스터링, report/json/html 갱신 | `GRAPH_REPORT.md` 재생성, community label 갱신 |
| `graphify label <path>` | community label 강제 재생성 | community 이름을 다시 붙이고 싶을 때 |

기본 흐름은 다음이 가장 안전하다.

```bash
graphify extract .
graphify cluster-only .
```

`extract`는 `graph.json`과 `.graphify_analysis.json`을 만들고, `cluster-only`는 기존 graph를 다시 읽어 `GRAPH_REPORT.md`, community labels, `graph.html`까지 정리한다. 큰 graph나 CI에서는 `cluster-only --no-viz`로 HTML 생성을 생략할 수 있다.

`extract`의 주요 옵션:

- `--backend gemini|kimi|claude|openai|deepseek|ollama`: semantic extraction backend.
- `--model M`: backend model override.
- `--mode deep`: richer semantic extraction과 aggressive inferred edge.
- `--out DIR`: `<DIR>/graphify-out/`에 출력.
- `--no-cluster`: raw extraction 중심, clustering 생략.
- `--postgres DSN`: PostgreSQL schema를 graph로 추출.
- `--global --as <tag>`: global graph에도 merge.

`update`는 code 변경에는 빠르지만, docs/papers/images 같은 semantic corpus 변경은 별도 semantic re-extraction이 필요할 수 있다.

## graph 질의 명령

| 명령 | 의미 | 적합한 질문 |
|---|---|---|
| `graphify query "<question>"` | 자연어 질문에 맞는 BFS subgraph context 추출 | “인증 흐름이 어떻게 동작하지?” |
| `graphify query "<question>" --dfs` | DFS로 더 path-like 흐름 추적 | “request가 어디를 거쳐 DB까지 가나?” |
| `graphify path "A" "B"` | 두 entity 사이 shortest path | “AuthService와 Database가 연결되나?” |
| `graphify explain "X"` | 특정 node와 neighbor를 설명 | “이 class/function이 graph에서 무슨 역할인가?” |
| `graphify affected "X"` | incoming relation을 역방향 BFS로 따라 영향 범위 탐색 | “이 node를 바꾸면 어디가 영향받나?” |

`query`는 기본 budget이 2000 token이며 `--budget N`, `--context C`, `--graph <path>`를 지원한다. `affected`는 `--depth N`, repeatable `--relation R`, `--graph <path>`를 지원한다.

실전에서는 전체 repo를 다시 읽기 전에 다음을 먼저 실행한다.

```bash
graphify query "what are the core abstractions?"
graphify explain "AuthService"
graphify path "EntryPoint" "Database"
graphify affected "AuthService" --depth 3
```

이 원칙은 [[graphify-report-generation]]의 해석 원칙과 이어진다. 넓은 architecture review는 report가 좋지만, 특정 질문에는 graph query가 더 작고 정확한 context를 준다.

## 출력과 시각화 명령

시각화와 지식 관리 export는 [[graphify-export-and-visualization]]에 자세히 정리되어 있다.

| 명령 | 결과 | 용도 |
|---|---|---|
| `graphify export html` | `graph.html` | interactive 관계망 |
| `graphify tree` | `GRAPH_TREE.html` | D3 파일/모듈/symbol 계층 |
| `graphify export svg` | `graph.svg` | README/보고서용 정적 그림 |
| `graphify export callflow-html` | Mermaid architecture HTML | review/발표용 flow |
| `graphify export obsidian` | notes + canvas | Obsidian 장기 탐색 |
| `graphify export wiki` | community/god-node article set | LLM/agent용 요약 KB |
| `graphify export graphml` | GraphML | Gephi/yEd |
| `graphify export neo4j` | Cypher 또는 push | Neo4j graph DB |

## 자동화와 유지보수

| 명령 | 역할 |
|---|---|
| `graphify watch <path>` | code 변경 감시 후 graph rebuild |
| `graphify hook install` | post-commit/post-checkout git hook 설치 |
| `graphify hook status` | hook 설치 상태 확인 |
| `graphify hook uninstall` | hook 제거 |
| `graphify check-update <path>` | cron-safe update 필요성 확인 |
| `graphify benchmark [graph.json]` | naive full-corpus 대비 graph query token 절감 추정 |

`benchmark.py`는 sample question을 대상으로 matching node 주변을 BFS depth 3으로 탐색해 query context token을 추정하고, corpus token estimate와 비교해 reduction ratio를 계산한다.

## query logging

`repos/graphify/graphify/querylog.py`는 `query/path/explain` 계열 사용을 append-only JSONL로 기록한다. 기본 위치는 `~/.cache/graphify-queries.log`다.

| 환경변수 | 의미 |
|---|---|
| `GRAPHIFY_QUERY_LOG` | log path override |
| `GRAPHIFY_QUERY_LOG_DISABLE=1` | query logging 비활성화 |
| `GRAPHIFY_QUERY_LOG_RESPONSES=1` | response 본문까지 저장 |

`log_query()`는 fail-silent로 설계되어 logging 실패가 main CLI 실행을 깨지 않는다.

## 보조 명령과 source 기준 보정

- `graphify add <url>`: URL을 `./raw`에 저장하고 graph update를 수행한다.
- `graphify save-result`: 질문/답변 결과를 `graphify-out/memory/`에 저장해 feedback loop 자료로 남긴다.
- `graphify global add/list/remove/path`: 여러 repo graph를 `~/.graphify/global-graph.json`에 통합/관리한다.
- DeepWiki 문서의 `remember <file>`은 현재 `python3 -m graphify --help`와 `__main__.py`에서는 command로 보이지 않는다. 현재 source 기준 실제 Q&A 저장 명령은 `save-result`다.
- DeepWiki의 `tree_html.py:to_tree_html()` 표현은 현재 source 기준 `write_tree_html()`/`build_tree()` 중심으로 보정해야 한다.

## 권장 운영 흐름

repo 분석에서 실무적으로는 다음 순서를 우선한다.

```bash
# 1. graph 생성
graphify extract .
graphify cluster-only .

# 2. 특정 질문에 답하기
graphify query "질문"
graphify explain "노드"
graphify path "A" "B"
graphify affected "X"

# 3. 시각화와 장기 탐색
graphify export html
graphify tree
graphify export wiki

# 4. 변경 후 갱신
graphify update .
graphify cluster-only .
```

핵심은 `graphify` CLI가 repo를 매번 통째로 LLM context에 넣는 대신, persistent graph를 만들고 그 위에서 필요한 subgraph만 꺼내 쓰게 해준다는 점이다.

## 관련 페이지

- [[graphify]]
- [[graphify-agent-skill-integration]]
- [[graphify-knowledge-graph-pipeline]]
- [[graphify-extract-query-mechanics]]
- [[graphify-graph-analysis]]
- [[graphify-report-generation]]
- [[graphify-export-and-visualization]]
- [[graphify-llm-semantic-extraction]]
- [[evidence-backed-analysis]]
