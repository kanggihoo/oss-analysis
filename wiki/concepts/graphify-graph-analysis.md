---
title: graphify Graph Analysis
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [graphify, knowledge-graph, architecture, code-map, inference, workflow, reporting, evidence]
sources:
  - artifacts/graphify/deepwiki/pages-md/2.4-graph-analysis.md
  - repos/graphify/graphify/analyze.py
  - repos/graphify/graphify/affected.py
  - repos/graphify/graphify/report.py
  - repos/graphify/graphify/__main__.py
  - repos/graphify/tests/test_analyze.py
  - repos/graphify/tests/test_affected_cli.py
confidence: high
---

# graphify Graph Analysis

이 페이지는 [[graphify]]가 `graph.json`을 만든 뒤, 그 NetworkX graph를 어떻게 `GRAPH_REPORT.md`와 CLI 질의 결과로 바꾸는지 정리한다. DeepWiki의 `2.4 Graph Analysis`를 baseline으로 삼되, 실제 `graphify/analyze.py`, `graphify/affected.py`, `graphify/report.py`, `graphify/__main__.py`와 테스트로 검증했다.

## 분석 단계의 위치

[[graphify-knowledge-graph-pipeline]]에서 graph analysis는 build/dedup/cluster 이후에 온다.

```text
extraction dicts → build/dedup → NetworkX graph → cluster/community → graph analysis → report/export
```

실제 `cluster-only` 흐름에서는 `communities`, cohesion scores, `god_nodes`, `surprising_connections`, community labels, `suggested_questions`가 만들어지고 `report.generate()`로 전달된다. 즉 이 단계는 graph를 재추출하는 것이 아니라, 이미 만들어진 graph를 사람이 읽을 수 있는 architecture insight로 바꾸는 단계다.

## 핵심 출력

| 출력 | 실제 코드 | 의미 |
|---|---|---|
| God nodes | `analyze.py:god_nodes()` | 연결 수가 많은 핵심 abstraction 후보 |
| Surprising connections | `analyze.py:surprising_connections()` | 파일/커뮤니티 경계를 넘는 비자명한 연결 |
| Suggested questions | `analyze.py:suggest_questions()` | 검증·탐색 가치가 높은 질문 |
| Graph diff | `analyze.py:graph_diff()` | 이전 graph와 새 graph의 node/edge 차이 |
| Import cycles | `analyze.py:find_import_cycles()` | file-level circular import/re-export cycle |
| Affected nodes | `affected.py:affected_nodes()` | 특정 node 변경 시 역방향 영향 범위 |

## God nodes: 중심 abstraction 찾기

`god_nodes()`는 `G.degree()`가 높은 node를 고른다. degree가 높다는 것은 많은 entity와 연결되어 있다는 뜻이므로 architecture 중심 후보가 될 수 있다. 다만 실제 구현은 연결이 많지만 의미 없는 node를 강하게 필터링한다.

| 필터 | 실제 코드 | 제거 대상 |
|---|---|---|
| File hub | `_is_file_node()` | label이 `source_file`의 파일명과 같은 node |
| Method/function stub | `_is_file_node()` | `.method()` 또는 degree ≤ 1인 `function()` |
| Concept node | `_is_concept_node()` | `source_file`이 비어 있거나 실제 파일 경로처럼 보이지 않는 semantic concept |
| JSON key noise | `_is_json_key_node()` | `id`, `type`, `name`, `dependencies` 등 JSON key |
| Builtin/mock noise | `_BUILTIN_NOISE_LABELS` | `str`, `int`, `Mock`, `MagicMock` 등 |

이 필터 때문에 `package.json`의 `dependencies`처럼 mechanical하게 연결이 많은 node가 god node로 잘못 올라오는 일을 줄인다. `tests/test_analyze.py`는 npm dependency block key와 JSON key noise가 god node에서 제외되는지 검증한다.

## Surprising connections: 의외의 연결 찾기

`surprising_connections()`는 source file 수에 따라 전략을 바꾼다.

```text
source_file이 2개 이상 → cross-file surprise
source_file이 1개 이하 → cross-community surprise
```

Multi-file graph에서는 서로 다른 `source_file`의 node를 잇는 edge를 후보로 보되, `imports`, `imports_from`, `contains`, `method`는 제외한다. 이 relation들은 대체로 AST나 파일 구조에서 생기는 mechanical edge라서 architecture insight라기보다 graph의 뼈대에 가깝다.

남은 후보는 `_surprise_score()`로 점수화된다.

| 신호 | 실제 점수/처리 | 해석 |
|---|---|---|
| Confidence | `AMBIGUOUS +3`, `INFERRED +2`, `EXTRACTED +1` | 명시적이지 않을수록 검토 가치가 높음 |
| Cross file type | `+2` | code↔paper, code↔image 등은 비자명함 |
| Cross top-level dir | `+2` | 서로 다른 repo/상위 디렉터리 연결 |
| Cross community | `+1` | Leiden/community 관점에서도 떨어진 영역 연결 |
| Semantic similarity | score `x1.5` | `semantically_similar_to`는 개념적 link에 가까움 |
| Peripheral→hub | `+1` | 작은 node가 큰 hub에 닿는 연결 |

중요한 실제 구현 보정: 다음 edge는 구조적 bonus를 억제한다.

```text
confidence == INFERRED
relation in calls, uses
그리고 cross-language 이거나 code↔doc 연결
```

예를 들어 Python node와 TypeScript node가 이름이 비슷하다는 이유로 `INFERRED calls`로 이어지면 실제 호출 관계가 아닐 가능성이 크다. 반대로 `semantically_similar_to`는 억제하지 않는다. cross-language/code↔doc 사이에서도 “실제 call”은 아닐 수 있지만 “의미적으로 유사하다”는 insight는 유효할 수 있기 때문이다. 이 정책은 `tests/test_analyze.py`의 cross-language, code-doc, semantic similarity 테스트들로 검증된다.

Single-file graph에서는 `_cross_community_surprises()`가 서로 다른 community를 잇는 edge를 찾는다. community 정보가 없으면 `nx.edge_betweenness_centrality()`를 fallback으로 쓰지만, node 수가 5000개를 넘으면 비용을 피하기 위해 빈 결과를 반환한다.

## Affected nodes: 변경 영향 범위

`graphify affected` CLI는 `graphify/affected.py`에 구현되어 있다. 핵심은 seed node에서 outgoing edge가 아니라 **incoming edge를 역방향으로 따라가는 BFS**다.

```text
caller_fn --calls--> target_fn
```

`target_fn`을 바꿀 때 영향을 받을 가능성이 있는 쪽은 `caller_fn`이다. 그래서 `affected_nodes()`는 `graph.in_edges(current, data=True)`를 따라간다.

기본 traversal relation:

```text
calls, references, imports, imports_from, re_exports,
inherits, extends, implements, uses, mixes_in, embeds
```

CLI 예시:

```bash
graphify affected "AuthService"
graphify affected "AuthService" --depth 3
graphify affected "AuthService" --relation calls
```

중요한 구현 보정: `load_graph()`는 저장된 graph JSON이 `directed=false`여도 affected 분석에서는 `directed=True`로 강제한다. 변경 영향 분석은 edge 방향을 잃으면 caller→callee 관계를 복원할 수 없기 때문이다. 이 동작은 `tests/test_affected_cli.py`에서 검증된다.

## Suggested questions: 그래프가 던지는 검증 질문

DeepWiki는 suggested questions를 hub/surprise/community 중심으로 설명하지만, 실제 `suggest_questions()`는 다음 5가지 신호를 쓴다.

| 질문 타입 | 트리거 | 목적 |
|---|---|---|
| `ambiguous_edge` | `confidence == AMBIGUOUS` edge | 불확실한 관계 검증 |
| `bridge_node` | betweenness centrality가 높은 node | community 사이를 잇는 cross-cutting concern 확인 |
| `verify_inferred` | INFERRED edge가 2개 이상인 high-degree node | 모델/휴리스틱 추론 edge 검증 |
| `isolated_nodes` | degree ≤ 1 node | 누락된 문서/edge 또는 고립 구조 탐색 |
| `low_cohesion` | cohesion score < 0.15이고 node ≥ 5인 community | community 분리/구조 개선 검토 |

신호가 없으면 `no_signal` 결과를 반환하고, 더 풍부한 edge를 얻으려면 파일을 더 추가하거나 `--mode deep`을 사용하라는 설명을 낸다.

## Graph diff와 import cycle

`graph_diff(G_old, G_new)`는 두 graph snapshot의 `new_nodes`, `removed_nodes`, `new_edges`, `removed_edges`, `summary`를 계산한다. edge key는 directed graph에서는 `(source, target, relation)`이고, undirected graph에서는 endpoint를 정렬해 비교한다. 현재 source checkout에서는 정의와 테스트는 확인되지만, active CLI 경로에서 직접 호출되는 부분은 확인되지 않았다.

`find_import_cycles()`는 전체 symbol graph에서 `imports_from`, `re_exports` edge만 골라 file-level directed graph를 만들고 `nx.simple_cycles()`로 순환 dependency를 찾는다. 반환 예시는 다음과 같다.

```json
{"cycle": ["src/a.ts", "src/b.ts"], "length": 2, "why": "circular dependency"}
```

테스트는 2-cycle, 3-cycle, self-loop, max length, source_file 없는 node skip, undirected input 처리, non-import relation 무시를 검증한다.

## Report와 연결

분석 결과는 `graphify/report.py:generate()`로 전달되어 `GRAPH_REPORT.md`를 만든다. 이 함수는 god nodes, surprises, community cohesion, suggested questions, token/file stats 등을 받아 사람이 읽는 보고서로 렌더링한다.

주의할 점: DeepWiki 문서나 오래된 설명에서 `render_report()` 같은 이름이 보일 수 있지만, 현재 source 기준 보고서 생성 함수명은 `generate()`다.

## 해석 원칙

Graph analysis 결과는 정답이 아니라 **검증 우선순위가 붙은 후보 목록**이다.

- God nodes는 중심 abstraction 후보지만 degree 기반 휴리스틱이다.
- Surprising connections는 진짜 architecture insight일 수도 있고 추론 artifact일 수도 있다.
- `INFERRED`, `AMBIGUOUS` edge는 [[evidence-backed-analysis]] 원칙에 따라 source file에서 재검증해야 한다.
- Affected nodes는 relation과 depth 설정에 따라 결과가 달라진다.
- Graph diff는 node/edge ID 안정성에 의존한다.

## 관련 페이지

- [[graphify]]
- [[graphify-cli-reference]]
- [[graphify-knowledge-graph-pipeline]]
- [[graphify-report-generation]]
- [[graphify-export-and-visualization]]
- [[graphify-llm-semantic-extraction]]
- [[evidence-backed-analysis]]
