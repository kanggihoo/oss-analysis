---
title: graphify Report Generation
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [graphify, knowledge-graph, reporting, architecture, workflow, evidence]
sources:
  - artifacts/graphify/deepwiki/pages-md/2.5-report-generation.md
  - repos/graphify/graphify/report.py
  - repos/graphify/graphify/analyze.py
  - repos/graphify/graphify/__main__.py
  - repos/graphify/tests/test_report.py
  - repos/graphify/tests/test_analyze.py
confidence: high
---

# graphify Report Generation

이 페이지는 [[graphify]]가 graph analysis 결과를 어떻게 `GRAPH_REPORT.md`라는 사람이 읽는 Markdown 보고서로 바꾸는지 정리한다. DeepWiki의 `2.5 Report Generation`을 baseline으로 삼되, 실제 `graphify/report.py`, `graphify/__main__.py`, `tests/test_report.py` 기준으로 보정했다.

## 보고서 생성 단계의 위치

보고서 생성은 [[graphify-graph-analysis]] 다음 단계다. 이 단계는 graph를 새로 분석하지 않고, 앞 단계에서 계산된 결과를 모아 Markdown 문자열로 조립한다.

```text
NetworkX graph
+ communities / cohesion
+ god nodes / surprises / questions
+ detection stats / token cost / commit
→ report.generate()
→ graphify-out/GRAPH_REPORT.md
```

현재 `cluster-only`/`label` CLI 흐름에서는 `god_nodes()`, `surprising_connections()`, `suggest_questions()`를 호출한 뒤 `report.generate()`의 반환 문자열을 `graphify-out/GRAPH_REPORT.md`에 쓴다.

## `generate()` 입력

실제 entry point는 `graphify/report.py:generate()`다.

| 입력 | 의미 | 보고서 사용처 |
|---|---|---|
| `G` | build된 NetworkX graph | node/edge 수, confidence 분포, ambiguous edge, isolated node, import cycle |
| `communities` | community id → node ids | community hub와 community summary |
| `cohesion_scores` | community별 cohesion | community summary |
| `community_labels` | LLM 또는 placeholder label | community 이름, Obsidian wikilink |
| `god_node_list` | `analyze.god_nodes()` 결과 | God Nodes 섹션 |
| `surprise_list` | `analyze.surprising_connections()` 결과 | Surprising Connections 섹션 |
| `detection_result` | detect 결과 또는 warning | Corpus Check 섹션 |
| `token_cost` | semantic extraction token usage | Summary 섹션 |
| `root` | 분석 root 표시용 문자열 | 보고서 제목 |
| `suggested_questions` | `analyze.suggest_questions()` 결과 | Suggested Questions 섹션 |
| `built_at_commit` | git commit SHA | Graph Freshness 섹션 |

## 생성되는 섹션

`GRAPH_REPORT.md`는 대략 다음 구조를 가진다. 일부 섹션은 조건부다.

```markdown
# Graph Report - <root> (<date>)

## Corpus Check
## Summary
## Graph Freshness
## Community Hubs (Navigation)
## God Nodes (most connected - your core abstractions)
## Surprising Connections (you probably didn't know these)
## Import Cycles
## Hyperedges (group relationships)
## Communities
## Ambiguous Edges - Review These
## Knowledge Gaps
## Suggested Questions
```

조건부 섹션 예:

- `Graph Freshness`: `built_at_commit`이 있을 때만.
- `Hyperedges`: `G.graph["hyperedges"]`가 있을 때만.
- `Ambiguous Edges`: `AMBIGUOUS` edge가 있을 때만.
- `Knowledge Gaps`: isolated node/thin community가 있거나 ambiguity 비율이 높을 때만.
- `Suggested Questions`: `suggested_questions`가 전달될 때만.

## Corpus Check와 Summary

`Corpus Check`는 입력 corpus가 graph analysis에 충분한지 보여준다. 일반 detect 결과가 있으면 파일 수와 단어 수를 표시하고, `cluster-only`처럼 detect 통계가 없으면 warning을 표시한다.

`Summary`는 graph 규모와 신뢰도 분포를 보여준다.

```text
nodes · edges · communities
EXTRACTED / INFERRED / AMBIGUOUS 비율
INFERRED edge 수와 평균 confidence_score
token input/output cost
```

이 부분은 보고서의 신뢰도 해석에 중요하다. `INFERRED`나 `AMBIGUOUS` 비율이 높으면 결과를 더 강하게 검증해야 한다.

## Graph Freshness

`built_at_commit`이 전달되면 보고서는 graph가 어떤 commit에서 만들어졌는지 표시한다.

```markdown
## Graph Freshness
- Built from commit: `8a04560`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).
```

즉 `GRAPH_REPORT.md`를 읽을 때 현재 checkout과 graph가 같은 commit 기준인지 확인할 수 있다.

## Community Hubs와 Communities

`Community Hubs (Navigation)`는 Obsidian/wiki 탐색용 링크다. `_safe_community_name()`이 label에서 파일명에 위험한 문자를 제거하고 다음 형식으로 링크를 만든다.

예: `- _COMMUNITY_<safe-name> alias <label>`에 해당하는 Obsidian community link를 만든다. 실제 wiki lint가 예시를 broken link로 해석하지 않도록 여기서는 bracket 문법 없이 placeholder로만 기록한다.

`Communities` 섹션은 각 community의 label, cohesion score, 대표 node를 보여준다. 이때 `analyze._is_file_node()`를 사용해 파일 허브나 method/function stub 같은 structural noise를 제외한다. 실제 테스트는 cohesion이 `✓`, `⚠` 같은 기호가 아니라 raw numeric score로 표시되는지 확인한다.

## God Nodes와 Surprising Connections

`God Nodes` 섹션은 `god_node_list`를 그대로 사람이 읽는 순위 목록으로 출력한다.

```markdown
1. `AuthService` - 38 edges
```

`Surprising Connections` 섹션은 `surprise_list`의 source, relation, target, confidence, source file pair를 출력한다.

```markdown
- `AuthService` --references--> `OAuth RFC`  [INFERRED 0.82]
  src/auth.py → docs/oauth.md  _crosses file types_
```

`relation == semantically_similar_to`이면 `[semantically similar]` tag가 추가된다. 중요한 점은 `report.py`가 surprising connection을 새로 계산하지 않고, [[graphify-graph-analysis]]에서 만들어진 결과를 formatting한다는 것이다.

## Import Cycles와 Hyperedges

`Import Cycles`는 `generate()` 내부에서 `analyze.find_import_cycles(G)`를 직접 호출해 만든다. 순환 dependency가 있으면 다음처럼 표시된다.

```markdown
- 2-file cycle: `src/a.ts -> src/b.ts -> src/a.ts`
```

없으면 `None detected.`로 표시된다.

`Hyperedges`는 `G.graph.get("hyperedges", [])`가 있을 때만 나온다. 일반 edge가 1:1 관계라면 hyperedge는 여러 node가 함께 묶이는 group relationship이다.

```markdown
- **Auth Flow** — LoginForm, AuthService, SessionStore [INFERRED 0.78]
```

## Ambiguous Edges와 Knowledge Gaps

`Ambiguous Edges - Review These`는 `confidence == AMBIGUOUS` edge를 별도 audit list로 보여준다.

```markdown
- `AuthService` → `SessionStore`  [AMBIGUOUS]
  src/auth.py · relation: uses
```

`Knowledge Gaps`는 graph의 약한 부분을 보여준다.

- degree ≤ 1인 isolated node.
- node 수가 너무 적어 보고서에서 생략된 thin community.
- `AMBIGUOUS` 비율이 20%를 넘는 경우.

즉 이 섹션은 “이 graph에서 아직 믿기 어렵거나 설명이 부족한 부분”을 알려준다.

## Suggested Questions

`suggested_questions`가 전달되면 보고서 마지막에 “이 graph가 답하기 좋은 질문”을 보여준다.

```markdown
- **Why does `Router` connect `API Layer` to `Auth Middleware`?**
  _High betweenness centrality - this node is a cross-community bridge._
```

`no_signal`만 있으면 질문 목록 대신 why 메시지만 표시한다.

## 테스트와 보장 범위

`tests/test_report.py`는 주요 섹션이 생성되는지 확인하는 smoke test에 가깝다. header, Corpus Check, God Nodes, Surprising Connections, Communities, Ambiguous Edges, Token cost 표시를 검증하고, cohesion은 `✓`, `⚠` 기호가 아니라 raw numeric score로 표시되는지 확인한다. 즉 보고서의 주요 뼈대는 보장하지만 전체 snapshot이나 모든 문구를 고정하지는 않는다.

## 해석 원칙

`GRAPH_REPORT.md`는 최종 정답이 아니라 **graphify 분석의 audit trail + architecture summary + 다음 탐색 가이드**다. 넓은 architecture review에는 보고서가 좋지만, 특정 질문에는 `graphify query`, `graphify path`, `graphify explain`이 더 작고 정확한 context를 줄 수 있다. `INFERRED`, `AMBIGUOUS`, Knowledge Gaps는 [[evidence-backed-analysis]] 원칙에 따라 source file로 재검증해야 한다.

## 관련 페이지

- [[graphify]]
- [[graphify-cli-reference]]
- [[graphify-knowledge-graph-pipeline]]
- [[graphify-export-and-visualization]]
- [[graphify-graph-analysis]]
- [[graphify-llm-semantic-extraction]]
- [[evidence-backed-analysis]]
