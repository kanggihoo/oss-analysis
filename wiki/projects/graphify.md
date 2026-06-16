---
title: graphify
created: 2026-06-10
updated: 2026-06-15
type: project
tags: [open-source, project, architecture, knowledge-graph, graphify, developer-tools, tooling, evidence]
sources:
  - artifacts/graphify/deepwiki/pages-md/2-core-architecture.md
  - repos/graphify/ARCHITECTURE.md
  - repos/graphify/graphify/__main__.py
  - repos/graphify/graphify/detect.py
  - repos/graphify/graphify/extract.py
  - repos/graphify/graphify/build.py
  - repos/graphify/graphify/dedup.py
  - repos/graphify/graphify/cluster.py
  - repos/graphify/graphify/analyze.py
  - repos/graphify/graphify/report.py
  - repos/graphify/graphify/export.py
confidence: high
---

# graphify

`graphify`는 코드, 문서, PDF, 이미지, 영상, 설정 파일 같은 비정형/반정형 입력을 지식 그래프로 바꾸는 오픈소스 개발자 도구다. `/Users/kkh/Desktop/oss-analysis/repos/graphify`의 local checkout 기준으로 핵심 구조를 확인했으며, 2026-06-10 기준 확인 commit은 `8a04560`이다.

## 한 줄 요약

`graphify`는 프로젝트를 단순 파일 목록이 아니라 **노드와 엣지로 연결된 구조 지도**로 변환한다. 결과물은 `graph.json`, `GRAPH_REPORT.md`, `graph.html`, Obsidian vault/export 등으로 사용된다.

## 핵심 파이프라인

자세한 단계별 구조는 [[graphify-knowledge-graph-pipeline]]에 정리되어 있고, 실제 운영 CLI는 [[graphify-cli-reference]], `extract`/`query` 세부 동작은 [[graphify-extract-query-mechanics]], 코딩 작업에서 query 문자열을 만드는 실전 규칙은 [[graphify-query-practices-for-coding]], Codex/Claude Code 같은 agent skill 통합은 [[graphify-agent-skill-integration]]에 정리되어 있다.

```text
detect → extract → build → dedup → cluster → analyze → report/export
```

- `detect`: 읽을 파일을 찾고 `code`, `document`, `paper`, `image`, `video`로 분류한다.
- `extract`: AST, 문서/이미지 semantic extraction, PostgreSQL schema 등에서 `{nodes, edges}` 형태의 추출 결과를 만든다. 문서/PDF/이미지 semantic extraction과 community labeling의 LLM 경로는 [[graphify-llm-semantic-extraction]]에 정리되어 있다.
- `build`: 여러 extraction dict를 합쳐 `NetworkX` graph로 만든다.
- `dedup`: 동일하거나 매우 유사한 entity node를 보수적으로 병합한다.
- `cluster`: 관련 노드를 커뮤니티로 묶는다.
- `analyze`: god nodes, surprising connections, affected nodes, suggested questions, import cycles 등을 찾는다. 분석 세부 흐름은 [[graphify-graph-analysis]]에 정리되어 있다.
- `report/export`: 사람이 읽는 `GRAPH_REPORT.md`와 `graph.json`, HTML, Obsidian, Cypher 등으로 출력한다. 보고서 조립 과정은 [[graphify-report-generation]], export/시각화 선택 기준은 [[graphify-export-and-visualization]]에 정리되어 있다.

## 실제 소스 기준으로 확인된 구현 포인트

- `repos/graphify/ARCHITECTURE.md`는 각 단계가 plain Python dict와 `NetworkX` graph로 통신한다고 설명한다.
- `repos/graphify/graphify/detect.py`의 `detect()`는 파일 탐색, `.graphifyignore`, sensitive file skip, Office/Google Workspace 변환, 파일 타입 분류를 담당한다.
- `repos/graphify/graphify/extract.py`의 `extract()`는 파일별 AST extraction 결과를 모은 뒤 cross-file import/call resolution을 수행한다. import 증거가 있으면 `EXTRACTED`, 이름/문맥 기반이면 `INFERRED`로 confidence를 구분한다.
- `repos/graphify/graphify/build.py`의 `build()`는 extraction 결과들을 합치고 기본적으로 `deduplicate_entities()`를 실행한 뒤 graph를 만든다.
- `repos/graphify/graphify/cluster.py`의 `cluster()`는 community id → node id 목록을 반환하며, export 시 각 node에 `community`가 기록된다.
- `repos/graphify/graphify/report.py`의 현재 보고서 생성 함수명은 DeepWiki 문서의 `render_report()`가 아니라 `generate()`다.

## DeepWiki 문서와 현재 소스의 차이

`artifacts/graphify/deepwiki/pages-md/2-core-architecture.md`는 전체 개념을 이해하는 baseline으로 유용하지만, 현재 source checkout과 비교하면 일부 함수명/책임 경계가 다르다.

| DeepWiki 표현 | 현재 소스 기준 보정 |
|---|---|
| `detect.py:collect_files()` | 현재 rich scanner는 `detect.py:detect()`이고, `collect_files()`는 `extract.py`에도 있다. |
| `build_graph()` | 현재 핵심 함수명은 `build()`이다. |
| `report.py:render_report()` | 현재 보고서 생성 함수명은 `generate()`이다. |
| `export.py:export()` | 현재는 `to_json()`, `to_html()`, `to_obsidian()` 등 개별 export 함수 중심이다. |
| node 필수 field에 `source_location` 포함 | 현재 `validate.py` 필수 node field는 `id`, `label`, `file_type`, `source_file`이다. |

이 차이는 [[evidence-backed-analysis]]의 좋은 사례다. DeepWiki는 baseline/second opinion으로 쓰고, 최종 wiki 사실은 local source로 검증해야 한다.

## CLI 흐름상 주의점

현재 `graphify extract <path>`는 detection, AST/semantic extraction, build, cluster, `graph.json`, `.graphify_analysis.json` 작성까지 수행한다. 하지만 소스 주석상 `GRAPH_REPORT.md`와 community label 생성은 보통 다음 단계인 `cluster-only`가 담당한다.

```bash
graphify extract .
graphify cluster-only .
```

따라서 `graphify` 분석 산출물을 이 workspace에 저장할 때는 [[workspace-boundaries]]에 따라 raw output은 `artifacts/<repo>/graphify/`, 사람이 읽는 검증 보고서는 `reports/<repo>/`, 장기 요약은 `wiki/`에 둔다.

## 분석 시 해석 원칙

`graphify`의 edge에는 `EXTRACTED`, `INFERRED`, `AMBIGUOUS` confidence가 붙는다. `EXTRACTED`는 import나 직접 호출처럼 source에 명시된 관계이고, `INFERRED`는 cross-file name/call resolution처럼 합리적 추론이며, `AMBIGUOUS`는 사람 검토가 필요한 관계다.

그러므로 `GRAPH_REPORT.md`의 god nodes, surprising connections, knowledge gaps는 그대로 결론이 아니라 **검증 후보**로 다룬다. 특히 `INFERRED`와 `AMBIGUOUS` edge는 source path를 다시 확인한 뒤 reports/wiki에 반영한다.

## 관련 페이지

- [[graphify-knowledge-graph-pipeline]]
- [[graphify-cli-reference]]
- [[graphify-agent-skill-integration]]
- [[graphify-extract-query-mechanics]]
- [[graphify-query-practices-for-coding]]
- [[graphify-export-and-visualization]]
- [[graphify-graph-analysis]]
- [[graphify-report-generation]]
- [[graphify-llm-semantic-extraction]]
- [[evidence-backed-analysis]]
- [[workspace-boundaries]]
- [[deepwiki-first-baseline]]
