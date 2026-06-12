---
title: graphify Knowledge Graph Pipeline
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [knowledge-graph, graphify, architecture, code-map, workflow, reporting, evidence]
sources:
  - artifacts/graphify/deepwiki/pages-md/2-core-architecture.md
  - repos/graphify/ARCHITECTURE.md
  - repos/graphify/graphify/detect.py
  - repos/graphify/graphify/extract.py
  - repos/graphify/graphify/build.py
  - repos/graphify/graphify/dedup.py
  - repos/graphify/graphify/cluster.py
  - repos/graphify/graphify/analyze.py
  - repos/graphify/graphify/affected.py
  - repos/graphify/graphify/report.py
  - repos/graphify/graphify/export.py
confidence: high
---

# graphify Knowledge Graph Pipeline

이 페이지는 [[graphify]]의 핵심 아키텍처를 Obsidian에서 다시 읽기 쉽게 정리한 것이다. 핵심 아이디어는 파일과 자연어 자료를 `nodes`와 `edges`로 표현한 뒤, 분석 가능한 지식 그래프로 바꾸는 것이다.

## 전체 흐름

```text
파일/문서/이미지/영상
→ detect
→ extract
→ build
→ dedup
→ cluster
→ analyze
→ report/export
→ graphify-out/
```

쉽게 말하면 다음과 같다.

1. 무엇을 읽을지 고른다.
2. 각 파일에서 의미 있는 entity와 관계를 추출한다.
3. 추출 결과를 하나의 graph로 합친다.
4. 중복 node를 줄인다.
5. 서로 가까운 node를 community로 묶는다.
6. 중요한 연결과 빈틈을 분석한다.
7. `graph.json`, `GRAPH_REPORT.md`, HTML, Obsidian 등으로 내보낸다.

## 단계별 역할

| 단계 | 실제 코드 기준 | 역할 |
|---|---|---|
| detect | `graphify/detect.py:detect()` | 파일 탐색, 타입 분류, ignore/sensitive skip, Office/Google Workspace 변환 |
| extract | `graphify/extract.py:extract()` + `graphify/llm.py` | code는 AST로, document/paper/image는 [[graphify-llm-semantic-extraction]] 경로로 `{nodes, edges}`를 생성 |
| build | `graphify/build.py:build()` | 여러 extraction dict를 합쳐 `NetworkX` graph 생성 |
| dedup | `graphify/dedup.py:deduplicate_entities()` | 같은 ID, 같은 source 내 label, fuzzy-similar entity 병합 |
| cluster | `graphify/cluster.py:cluster()` | Leiden/Louvain 계열 community detection |
| analyze | `graphify/analyze.py`, `graphify/affected.py` | god nodes, surprising connections, impact/affected nodes, suggested questions, import cycles 분석; 상세는 [[graphify-graph-analysis]] |
| report | `graphify/report.py:generate()` | `GRAPH_REPORT.md` 문자열 생성; 상세는 [[graphify-report-generation]] |
| export | `graphify/export.py`, `graphify/tree_html.py`, `graphify/callflow_html.py`, `graphify/wiki.py` | `graph.json`, HTML, SVG, D3 tree, Obsidian, wiki, GraphML, Neo4j 등 출력; 선택 기준은 [[graphify-export-and-visualization]] |

## Extraction schema

각 extractor는 graph assembly가 이해할 수 있는 공통 구조를 만든다.

```json
{
  "nodes": [
    {"id": "...", "label": "...", "file_type": "code", "source_file": "..."}
  ],
  "edges": [
    {"source": "...", "target": "...", "relation": "calls", "confidence": "EXTRACTED", "source_file": "..."}
  ]
}
```

현재 `graphify/validate.py` 기준 필수 node field는 `id`, `label`, `file_type`, `source_file`이고, 필수 edge field는 `source`, `target`, `relation`, `confidence`, `source_file`이다. DeepWiki 문서에 언급된 `source_location`은 유용한 provenance field지만 현재 validator 기준 필수는 아니다.

## Confidence labels

`graphify`는 edge를 만들 때 관계의 확실성을 함께 기록한다.

| label | 의미 | 해석 |
|---|---|---|
| `EXTRACTED` | source에 명시된 관계 | import, direct call 등 강한 근거 |
| `INFERRED` | 합리적 추론 | cross-file call/name resolution, co-occurrence 등 |
| `AMBIGUOUS` | 불확실한 관계 | 사람 검토 필요 |

이 구조 덕분에 graph output은 “정답”이 아니라 검증 가능한 hypothesis가 된다. 이 원칙은 [[evidence-backed-analysis]]와 연결된다.

## Build와 dedup

`build()`는 extraction 결과를 합치고 기본적으로 dedup을 수행한다. `deduplicate_entities()`는 다음처럼 보수적으로 작동한다.

- 여러 node가 같은 `id`를 가지면 첫 node를 유지한다.
- 같은 파일 안에서 normalized label이 같은 node를 병합한다.
- high-entropy label만 MinHash/LSH와 Jaro-Winkler로 fuzzy candidate를 만든다.
- 서로 다른 repo의 node가 섞이면 cross-project dedup을 막기 위해 에러를 낸다.

즉 graph가 너무 지저분해지는 것을 막되, 서로 다른 파일의 우연히 같은 이름까지 무리하게 합치지 않도록 설계되어 있다.

## Cluster와 analysis

`cluster()`는 graph를 관련 노드 묶음으로 나눈다. 너무 큰 community는 재분할하고, isolate node는 별도 community로 다루며, community id가 run마다 크게 흔들리지 않도록 stable ordering/remapping 로직을 둔다.

`analyze.py`와 `affected.py`는 다음을 찾는다. 세부 scoring, false-positive 억제, affected reverse traversal, suggested questions, import-cycle detection은 [[graphify-graph-analysis]]에 별도로 정리했다.

- `god_nodes`: 가장 많이 연결된 핵심 abstraction.
- `surprising_connections`: 파일/커뮤니티 경계를 넘는 예상 밖 연결.
- import cycles, knowledge gaps, suggested questions.

`affected.py`의 `affected_nodes()`는 특정 node를 기준으로 incoming relation을 따라가며 “이 node가 바뀌면 누가 영향을 받을 수 있는가?”를 BFS로 찾는다.

## Report/export 산출물

주요 산출물은 다음이다.

- `graph.json`: node, edge, community, `norm_label`, confidence score 등이 들어가는 persistent graph.
- `GRAPH_REPORT.md`: corpus summary, god nodes, surprising connections, communities, ambiguous edges, knowledge gaps를 담은 audit report. 생성 방식은 [[graphify-report-generation]]에 정리되어 있다.
- `graph.html`, `graph.svg`, `GRAPH_TREE.html`, callflow HTML: 시각적 탐색/리뷰용 산출물. 어떤 view를 언제 쓰는지는 [[graphify-export-and-visualization]]에 정리되어 있다.
- Obsidian export와 wiki export: node/community를 markdown note나 article set으로 탐색할 수 있게 만드는 지식 관리형 출력.

## CLI 주의점

현재 source 기준으로 `graphify extract <path>`는 `graph.json`과 `.graphify_analysis.json`까지 만들고, `GRAPH_REPORT.md`는 보통 `cluster-only`가 생성한다. CLI 전체 운영 흐름은 [[graphify-cli-reference]], `extract`/`query`의 backend 없는 세부 동작은 [[graphify-extract-query-mechanics]]에 별도로 정리했다.

```bash
graphify extract .
graphify cluster-only .
```

따라서 분석 자동화에서는 `extract`만 실행하고 보고서가 없다고 판단하면 안 된다. `cluster-only` 또는 report generation 단계까지 확인해야 한다. 또한 code-only corpus는 로컬 AST만으로 처리되지만, document/paper/image semantic extraction이나 `--dedup-llm`은 [[graphify-llm-semantic-extraction]]의 backend 설정이 필요하다.

## Obsidian에서 읽는 관점

이 pipeline은 [[workspace-boundaries]]의 `artifacts/<repo>/graphify/`에 저장되는 analyzer output을 만든다. 이후 사람이 읽기 좋은 검증 결과는 `reports/<repo>/`에 쓰고, 장기적으로 재사용할 요약은 이 wiki의 [[graphify]] 같은 project/concept page로 유지한다.
