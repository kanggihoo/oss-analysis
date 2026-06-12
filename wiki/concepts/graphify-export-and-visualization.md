---
title: graphify Export and Visualization
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [graphify, knowledge-graph, architecture, workflow, tooling, evidence]
sources:
  - deepwiki-ko/graphify/3-export-and-visualization.md
  - artifacts/graphify/deepwiki/pages-md/3-export-and-visualization.md
  - repos/graphify/graphify/export.py
  - repos/graphify/graphify/tree_html.py
  - repos/graphify/graphify/callflow_html.py
  - repos/graphify/graphify/wiki.py
  - repos/graphify/graphify/__main__.py
confidence: high
---

# graphify Export and Visualization

이 페이지는 [[graphify]]가 만든 `NetworkX` graph와 `graph.json`을 사람이 탐색하거나 다른 도구가 재사용할 수 있는 형식으로 바꾸는 방식을 정리한다. 원문 DeepWiki 번역은 export 종류를 잘 나열하지만, 아래 내용은 현재 local source의 함수명과 CLI 흐름을 기준으로 보정했다.

## 핵심 관점

`export` 단계는 그래프를 새로 해석하는 단계라기보다 **같은 graph를 목적별 view로 바꾸는 단계**다.

```text
graph.json / NetworkX graph
→ 관계망 보기: graph.html, graph.svg
→ 파일 계층 보기: GRAPH_TREE.html
→ architecture flow 보기: callflow HTML
→ 지식 관리: Obsidian vault, wiki articles
→ 외부 도구/DB: JSON, GraphML, Cypher/Neo4j
```

각 output은 “무엇을 node로 보여줄지”가 다르다. `graph.html`과 `graph.svg`는 graph node 자체를 보여주고, `GRAPH_TREE.html`은 `source_file` 기준 파일/폴더 계층을 보여주며, Obsidian/wiki는 graph node와 community를 markdown article로 바꾼다.

## 선택 기준 요약

| 상황 | 적합한 output | 이유 |
|---|---|---|
| 전체 관계망 탐색 | `graph.html` | 검색, 클릭 inspection, community filter가 있는 interactive graph |
| README/보고서 삽입 | `graph.svg` | JavaScript 없는 정적 vector graphic |
| 폴더/파일/symbol 계층 파악 | `GRAPH_TREE.html` | D3 collapsible tree로 module hierarchy를 보여줌 |
| architecture 흐름 설명 | `callflow-html` | Mermaid flowchart와 call detail table 중심 |
| Obsidian 장기 탐색 | Obsidian vault + canvas | node별 note, community note, tags, Dataview, Canvas |
| LLM/agent용 요약 KB | Wiki export | community/god node 중심 article set |
| 외부 graph tool | GraphML | Gephi/yEd 호환 |
| graph DB 질의 | Neo4j/Cypher | Cypher relation query 가능 |
| 자동화/재가공 원본 | `graph.json` | canonical persistent graph artifact |

## Interactive HTML: `graph.html`

실제 구현은 `repos/graphify/graphify/export.py:to_html()`이다. DeepWiki의 설명대로 브라우저 기반 interactive graph지만, D3가 아니라 `vis-network`를 사용한다.

보여주는 것:

- node = graph entity, 색상 = community, 크기 = degree 또는 aggregated community member count.
- edge label = `relation`; `EXTRACTED`는 진한 solid, 그 외 confidence는 얇은 dashed.
- sidebar = node search, node metadata, community legend/filter.
- hyperedges = 여러 node를 묶는 의미적 group을 반투명 영역으로 표시.

기본 graph 규모 제한은 `MAX_NODES_FOR_VIZ = 5000`이고, `GRAPHIFY_VIZ_NODE_LIMIT` 또는 CLI `--node-limit`으로 조절한다. limit을 초과하면서 `node_limit`이 주어진 경우 source는 community를 node로 하는 aggregated meta-graph를 만들 수 있다.

적합한 상황: repo의 전체 연결 구조, community 간 관계, god node 주변 관계를 클릭하면서 확인할 때. 주의점: 큰 graph는 브라우저에서 무겁고, 파일 계층은 `GRAPH_TREE.html`이 더 적합하다. `INFERRED`, `AMBIGUOUS` edge는 [[evidence-backed-analysis]] 기준으로 source path 재확인이 필요하다.

```bash
graphify export html
graphify export html --graph graphify-out/graph.json --node-limit 5000
```

## SVG: `graph.svg`

실제 구현은 `repos/graphify/graphify/export.py:to_svg()`이다. `matplotlib`과 `networkx.spring_layout()`으로 정적 vector graphic을 만든다. node 색상은 community, 크기는 degree, edge는 confidence에 따라 solid/dashed이고, legend에는 community label과 member count가 들어간다.

적합한 상황: README, Notion, Obsidian note, 보고서에 한 장짜리 overview를 삽입할 때. 주의점: node가 많으면 label이 겹치고, 검색/필터/클릭 탐색은 없다.

```bash
graphify export svg
```

## D3 Tree HTML: `GRAPH_TREE.html`

실제 구현은 `repos/graphify/graphify/tree_html.py`이고 CLI는 `graphify tree`다. 이 output은 일반 관계망이 아니라 `source_file`을 기준으로 **프로젝트 파일 계층과 파일 안의 symbol**을 보여준다.

```text
project root
├── src/
│   ├── auth.py
│   │   ├── AuthService
│   │   └── login()
│   └── db.py
└── docs/
```

주요 동작: D3 v7 collapsible tree, expand/collapse/reset, click-to-toggle subtree, `total_count` descendant count, `--max-children` 제한과 `(+N more)` leaf.

적합한 상황: package/module/file 구조를 먼저 이해할 때, onboarding용 code map을 만들 때, force-directed graph가 복잡해서 계층 구조부터 보고 싶을 때. 주의점: runtime call relation이나 community 간 cross-edge를 설명하는 도구는 아니다.

```bash
graphify tree
graphify tree --graph graphify-out/graph.json --output graphify-out/GRAPH_TREE.html --max-children 100
```

## Callflow HTML

실제 구현은 `repos/graphify/graphify/callflow_html.py`이고 CLI는 `graphify export callflow-html`이다. graph 전체를 그대로 그리기보다 architecture review용 HTML 문서를 만든다.

보여주는 것: dark-themed self-contained HTML, navigation bar, architecture overview Mermaid flowchart, section별 representative flowchart, call detail table, section intro와 key-file cards.

적합한 상황: subsystem 간 흐름을 발표/리뷰 문서로 설명할 때, force graph보다 narrative architecture flow가 필요할 때, section-level dependency와 대표 call path를 보여주고 싶을 때.

```bash
graphify export callflow-html
graphify export callflow-html --graph graphify-out/graph.json --report graphify-out/GRAPH_REPORT.md --output docs/architecture.html
```

## Obsidian vault와 Canvas

실제 구현은 `repos/graphify/graphify/export.py:to_obsidian()`과 `to_canvas()`다. CLI는 `graphify export obsidian`이다.

`to_obsidian()`은 graph node 하나를 markdown note 하나로 만들고, community별 overview note를 만든다. 각 note에는 YAML frontmatter, `source_file`, `type`, `community`, confidence/community tag, outgoing connection 목록이 들어간다. community note에는 cohesion, members, Dataview query, 다른 community와의 연결, top bridge nodes가 들어간다.

`to_canvas()`는 Obsidian Canvas 파일을 만든다. community는 group box, node는 file card, edge는 card 사이 연결로 표현하며, community는 grid로 배치되고 edge는 weight 기준 상위 200개만 포함된다.

적합한 상황: Obsidian에서 장기적으로 graph를 읽고 메모할 때, node별 source path와 confidence를 따라 검증할 때, community note/tag/Dataview/Canvas를 함께 쓰고 싶을 때. 주의점: node가 매우 많으면 note 수도 매우 많아진다.

```bash
graphify export obsidian
graphify export obsidian --dir graphify-out/obsidian
```

## Wiki export

실제 구현은 `repos/graphify/graphify/wiki.py:to_wiki()`이고 CLI는 `graphify export wiki`다. Obsidian export가 node별 note라면, wiki export는 더 요약된 Wikipedia-style article set이다.

생성물: `index.md`는 community와 god node entry point이고, community article은 key concepts/relationships/source files/audit trail을 담으며, god node article은 relation별 연결 목록을 담는다.

적합한 상황: LLM/agent가 읽기 좋은 요약 KB가 필요할 때, 모든 node note보다 community/god node 중심 요약이 중요할 때, `index.md → community article → god node article` 순서로 탐색하고 싶을 때.

주의점: 현재 CLI는 community 정보가 없으면 wiki export를 거부한다. `graphify extract .` 또는 `graphify cluster-only .`로 `.graphify_analysis.json`을 먼저 만들어야 한다. 이 workspace의 `wiki/`와 graphify가 생성하는 `graphify-out/wiki/`는 다르다. 전자는 [[llm-wiki-operating-model]]에 따른 장기 synthesis layer이고, 후자는 analyzer artifact다.

## JSON, GraphML, Neo4j

`graph.json`은 graphify의 canonical persistent artifact다. `to_json()`은 `node_link_data`를 저장하면서 node에 `community`, `norm_label`을 추가하고, edge에 `confidence_score`를 보강하며, 원래 edge 방향을 `_src`/`_tgt`에서 `source`/`target`으로 복원한다.

`to_graphml()`은 Gephi, yEd 같은 외부 graph tool용이다. community와 edge confidence를 보존하되 내부 marker는 제거한다. `to_cypher()`와 `push_to_neo4j()`는 Neo4j에 넣고 Cypher로 relation query를 하고 싶을 때 적합하다.

## 추천 사용 순서

1. `GRAPH_REPORT.md`로 community, god node, surprising connection을 먼저 읽는다. 자세한 해석은 [[graphify-report-generation]]과 [[graphify-graph-analysis]]를 참고한다.
2. `graph.html`로 전체 관계망과 community 연결을 눈으로 본다.
3. `GRAPH_TREE.html`로 파일/모듈/symbol 계층을 본다.
4. 장기 탐색이 필요하면 Obsidian export나 wiki export를 만든다.
5. 외부 graph 분석이 필요하면 GraphML 또는 Neo4j로 넘긴다.

## 관련 페이지

- [[graphify]]
- [[graphify-cli-reference]]
- [[graphify-knowledge-graph-pipeline]]
- [[graphify-report-generation]]
- [[graphify-graph-analysis]]
- [[evidence-backed-analysis]]
- [[llm-wiki-operating-model]]
