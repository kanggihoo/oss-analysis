---
title: graphify Extract and Query Mechanics
created: 2026-06-10
updated: 2026-06-15
type: concept
tags: [graphify, knowledge-graph, developer-tools, tooling, workflow, evidence]
sources:
  - repos/graphify/graphify/__main__.py
  - repos/graphify/graphify/serve.py
  - repos/graphify/graphify/llm.py
  - repos/graphify/graphify/extract.py
  - artifacts/graphify/deepwiki/pages-md/4.1-cli-reference.md
confidence: high
---

# graphify Extract and Query Mechanics

이 페이지는 [[graphify-cli-reference]]의 세부 보강이다. 직접 CLI로 `graphify extract . → graphify cluster-only . → graphify export ...`를 사용할 때, `extract`가 LLM 없이 어디까지 동작하는지와 `graphify query "..."`가 backend 없이 자연어처럼 보이는 질문을 어떻게 처리하는지 정리한다.

## 핵심 결론

- `graphify extract <path>`는 code-only corpus에서는 LLM 없이 AST 기반으로 graph를 만든다.
- AST가 만드는 것은 tree가 아니라 file/class/function/import/call/reference 등의 node/edge를 담은 관계 graph다.
- `GRAPH_TREE.html`은 `graphify tree`가 `graph.json`의 `source_file` 정보를 기준으로 나중에 만든 tree view다.
- docs/papers/images가 있거나 `--dedup-llm`을 쓰면 LLM backend가 필요하다. backend/API key가 없으면 현재 source 기준 오류로 중단된다.
- `graphify query "..."`는 LLM 호출이 아니라 lexical scoring + BFS/DFS graph traversal이다.
- query 출력은 최종 자연어 답변이 아니라 `NODE` / `EDGE` 형태의 subgraph text context다. agent가 있으면 agent LLM이 이를 읽고 답변으로 재작성한다.

## `extract`의 실제 흐름

현재 `repos/graphify/graphify/__main__.py` 기준 `graphify extract <path>`는 다음 흐름으로 동작한다.

```text
1. output root 결정: <out-or-target>/graphify-out/
2. detect 또는 detect_incremental로 파일 스캔
3. code/document/paper/image로 분류
4. semantic_files = docs + papers + images 계산
5. needs_llm = semantic_files 존재 여부 또는 --dedup-llm 여부로 판단
6. code files는 graphify.extract.extract()로 AST extraction
7. semantic files는 cache 확인 후 LLM semantic extraction
8. AST + semantic + PostgreSQL introspection 결과 merge
9. build 또는 build_merge로 NetworkX graph 구성
10. dedup, cluster, cohesion, god nodes, surprising connections 계산
11. graph.json, .graphify_analysis.json, manifest.json 저장
12. 다음 단계로 cluster-only 실행 안내
```

`extract`는 의도적으로 `GRAPH_REPORT.md`까지 완성하지 않는다. report와 community labels는 `cluster-only` 또는 agent step에서 생성하는 단계로 분리되어 있다.

## LLM 사용 여부 결정

핵심 조건은 다음이다.

```text
semantic_files = document + paper + image files
needs_llm = bool(semantic_files) or dedup_llm
```

따라서 code-only repo에서 `--dedup-llm`을 주지 않으면 API key 없이도 동작한다. 반대로 docs/papers/images가 detection되거나 `--dedup-llm`을 쓰면 backend가 필요하다. backend를 명시하지 않으면 `llm.py:detect_backend()`가 gemini, kimi, claude, openai, deepseek, azure, bedrock, ollama, custom providers 순서로 환경변수를 확인한다.

| 명령/상황 | backend 없음 |
|---|---|
| code-only `extract` | 가능 |
| docs/papers/images 포함 `extract` | 실패 |
| `cluster-only` report 생성 | 가능 |
| `cluster-only` community naming | `Community N` placeholder로 degrade |
| `query/path/explain/affected` | 가능 |

## AST extraction은 tree가 아니라 graph를 만든다

`extract.py`는 source AST에서 code entity와 relation을 추출해 표준 dict schema를 만든다.

| 범주 | 예 |
|---|---|
| node | file/module, class/type, function/method, imported module, referenced symbol |
| edge | `contains`, `imports`, `imports_from`, `re_exports`, `calls`, `references`, `inherits`, `implements`, `method` |
| edge metadata | `relation`, `context`, `confidence`, `source_file`, `source_location` |

따라서 엄밀한 표현은 다음이다.

```text
graphify extract .
→ AST 기반 code entity graph 생성

graphify tree
→ graph.json을 source_file 기준 파일/모듈/symbol tree view로 변환
```

기본 산출물은 `graphify-out/graph.json`, `graphify-out/.graphify_analysis.json`, `graphify-out/manifest.json`이다. `--no-cluster`를 주면 NetworkX build/cluster/analysis를 생략하고 raw merged extraction dict를 `graph.json`으로 쓴다.

## `cluster-only`와 backend 없는 label

`graphify cluster-only <path>`는 기존 `graph.json`을 다시 읽어 community detection, cohesion, god nodes, surprising connections, suggested questions, report generation, HTML refresh를 수행한다. community label을 사람이 읽기 좋은 이름으로 붙일 때는 LLM backend를 시도할 수 있지만, backend가 없거나 실패하면 `llm.py:generate_community_labels()`가 `Community 0`, `Community 1` 같은 placeholder를 반환한다.

## `query`는 LLM query가 아니다

`graphify query "..."`는 `serve.py:_query_graph_text()`를 사용한다. 이 함수는 LLM이나 embedding을 호출하지 않고 다음을 수행한다.

```text
1. graph.json load
2. 질문 문자열을 searchable term으로 분해
3. 각 node label/source path에 lexical score 부여
4. score 상위 node를 seed로 선택
5. 질문 또는 --context에서 edge context filter 결정
6. seed에서 BFS 또는 DFS traversal
7. 탐색된 nodes/edges를 text로 렌더링
8. token_budget 기준으로 출력 truncation
9. querylog에 JSONL 기록
```

## query matching과 traversal

질문은 `_query_terms()`에서 검색 가능한 token으로 바뀐다. 영어 2글자 이하 단어는 대체로 제외되고, 중국어는 `jieba`가 있으면 segmentation을 사용한다. 한국어 형태소 분석은 별도 구조가 아니므로 실제 code identifier와 겹치는 영어 keyword나 symbol name이 더 잘 맞는다.

`_score_nodes()`는 exact match, prefix match, substring match, `source_file` path match, IDF weight를 조합한다. 그 다음 `_pick_seeds()`가 상위 seed를 고른다. 최대 3개 정도를 고르지만, 1등과 점수 차이가 너무 크면 낮은 후보를 버려 흔한 단어가 seed를 오염시키지 않게 한다.

traversal은 기본 BFS이며 `--dfs`를 주면 DFS를 쓴다. context filter는 `--context call`처럼 명시하거나, 질문 안의 `call`, `import`, `field`, `parameter`, `return`, `generic` 같은 단어로 heuristic 추론된다. filter가 있으면 해당 `context`를 가진 edge만 남긴 graph에서 탐색한다. BFS/DFS 모두 high-degree hub를 transit expansion에서 제한해 graph 전체로 폭발하는 것을 줄인다.

## query 반환 형식

반환값은 최종 prose answer가 아니라 subgraph context text다.

```text
Traversal: BFS depth=2 | Start: ['AuthService'] | 23 nodes found

NODE AuthService [src=src/auth.py loc=L10 community=2]
NODE TokenVerifier [src=src/token.py loc=L7 community=2]

EDGE AuthService --calls [EXTRACTED context=call]--> TokenVerifier
EDGE AuthService --uses [INFERRED]--> UserRepository
```

node line은 label, source file, source location, community를 담고, edge line은 source label, relation, confidence, context, target label을 담는다. `--budget N`은 대략적인 char budget으로 출력을 자른다.

## 왜 자연어처럼 보이나?

CLI가 자연어 답변을 생성해서가 아니라, 질문 문장을 lexical search query로 바꾸기 때문이다.

```text
"how does authentication work?"
→ authentication, work 같은 term 추출
→ node label/source_file과 매칭
→ seed 주변 subgraph 반환
```

따라서 직접 CLI 결과는 “관련 graph context”이고, Claude/Codex/Hermes 같은 agent가 이 출력을 읽으면 그 agent LLM이 자연어 설명으로 바꾼다. Agent skill 기반의 query-first 정책은 [[graphify-agent-skill-integration]], 이 구분과 “LLM을 쓰는 단계”는 [[graphify-llm-semantic-extraction]]에 정리되어 있다. 코딩 작업에서 사용자의 한국어/추상 의도를 실제 node label/source_file vocabulary query로 바꾸는 절차는 [[graphify-query-practices-for-coding]]에 따로 정리했다.

## 실무적 사용 팁

- code-only repo에서는 먼저 `graphify extract .`를 backend 없이 실행해도 된다.
- docs/papers/images까지 포함하려면 backend/API key를 먼저 준비한다.
- query는 embedding search가 아니므로 실제 symbol name, module name, file path 단어를 섞으면 더 잘 맞는다.
- 한국어 설명형 질문만 넣기보다 `AuthService token verification`처럼 code identifier를 포함하는 편이 낫다.
- 넓은 overview는 `GRAPH_REPORT.md`, 특정 질문은 `graphify query`, 특정 node는 `graphify explain`, 두 entity 연결은 `graphify path`, 변경 영향은 `graphify affected`를 쓴다.

## 관련 페이지

- [[graphify]]
- [[graphify-cli-reference]]
- [[graphify-query-practices-for-coding]]
- [[graphify-knowledge-graph-pipeline]]
- [[graphify-llm-semantic-extraction]]
- [[graphify-graph-analysis]]
- [[graphify-report-generation]]
