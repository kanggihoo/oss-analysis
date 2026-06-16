---
repo: Understand-Anything
local_checkout: /Users/kkh/Desktop/oss-analysis/repos/Understand-Anything
verification_commit: 7a3b7511b26a1816be3b6cc5683b34779e0abce9
baseline_artifacts:
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/2-understand-anything-pipeline.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/3-understand-anything-core.md
  - /Users/kkh/Desktop/oss-analysis/artifacts/Understand-Anything/gemini/4-understand-anything-dashboard.md
---

# Understand-Anything analysis pipeline verification

## Baseline 취급

Gemini pipeline 문서는 `/understand`, `/understand-domain`, `/understand-knowledge`, project scan, batch analysis, assemble review, architecture analysis, tour builder, graph validation을 설명했다. 현재 checkout에서는 대체로 맞지만, 실제 구현은 `understand-anything-plugin/skills/*/SKILL.md`와 bundled scripts 기준으로 더 구체적이다.

## `/understand` 실제 단계

### Phase 0 / preflight

`/understand`는 `understand-anything-plugin/skills/understand/SKILL.md`에 정의된다. 옵션은 `--auto-update`, `--no-auto-update`, `--review`, `--language <lang>`, directory path를 포함한다(`SKILL.md:15-19`). Plugin root resolution은 Claude/Copilot/Codex/OpenCode/Pi 등 여러 install path를 검사한다(`SKILL.md:73-121`).

Preflight는 commit hash를 `git rev-parse HEAD`로 얻고(`SKILL.md:123-126`), `.understand-anything/intermediate`와 `tmp`를 만든다(`127-131`). 언어 설정은 `--language`/저장 config/대화 언어 detection을 통해 `config.json`에 저장한다(`137-153`).

### Phase 0.5 ignore configuration

Gemini baseline에는 약하게만 언급됐지만 현재 source에는 명시적인 ignore gate가 있다. `.understand-anything/.understandignore`가 없으면 `.gitignore`와 built-in defaults를 바탕으로 starter file을 생성하고 사용자 확인을 기다린다(`SKILL.md:194-231`). 이 단계는 scan 전에 노이즈를 줄이는 별도 단계다.

### Phase 1 scan

Phase 1은 `project-scanner` agent dispatch 후 `scan-result.json`을 읽는다(`SKILL.md:235-270`). 하지만 실제 file enumeration/language/category/line-count/complexity의 deterministic 부분은 `scan-project.mjs`가 담당한다. 이 script는 `git ls-files` 우선, recursive fallback, `.understandignore`, category/language detection, line counting, complexity estimation을 소유한다고 명시한다(`scan-project.mjs:5-24`).

Import map은 별도 script `extract-import-map.mjs`가 담당한다. 주석은 `PluginRegistry(TreeSitterPlugin + non-code parsers)`를 사용해 raw import를 뽑고 project-internal file path로 resolve한다고 설명한다(`extract-import-map.mjs:5-13`). Script 실제 import도 `TreeSitterPlugin`, `PluginRegistry`, `registerAllParsers`를 사용한다(`extract-import-map.mjs:61`).

### Phase 1.5 semantic batching

Gemini baseline의 `compute-batches.mjs` claim은 확인됐다. `/understand`는 `node <SKILL_DIR>/compute-batches.mjs $PROJECT_ROOT`를 실행하고 `.understand-anything/intermediate/batches.json`을 만든다(`SKILL.md:280-293`). Script 주석도 scan-result를 읽어 import graph에서 Louvain community detection과 neighborMap을 만든다고 한다(`compute-batches.mjs:3-12`).

현재 source에서 추가 확인된 부분: non-code 파일도 Dockerfile cluster, GitHub workflows, CI files, SQL migrations, parent directory catch-all로 batching된다(`compute-batches.mjs:90-180`).

### Phase 2 file analysis

Full analysis에서는 batches 배열을 돌며 최대 5개 `file-analyzer` subagent를 병렬 dispatch한다(`SKILL.md:297-339`). 각 agent는 `batch-<index>.json` 또는 `batch-<index>-part-<k>.json`을 `.understand-anything/intermediate`에 써야 하며, fused batch라도 원래 batchIndex별 파일명이 필요하다고 강하게 경고한다(`SKILL.md:320-339`).

`extract-structure.mjs`는 file-analyzer용 deterministic skeleton extractor다. `TreeSitterPlugin + PluginRegistry + registerAllParsers`를 초기화하고(`extract-structure.mjs:65-73`), 각 파일에 대해 `registry.analyzeFile`과 code/script callgraph extraction을 수행한다(`97-123`).

### Merge and normalize

Phase 2 완료 후 `python <SKILL_DIR>/merge-batch-graphs.py $PROJECT_ROOT`를 실행한다(`SKILL.md:343-346`). 현재 source의 merge 단계는 다음을 수행한다.

- `batch-*.json`, `batch-<i>-part-<k>.json` 읽기(`SKILL.md:348-349`)
- node ID normalization, complexity normalization, edge rewrite, dedupe, dangling edge drop(`350-355`)
- `tested_by` edge canonicalization and supplementation; final direction은 production → test(`357`)
- output은 `.understand-anything/intermediate/assembled-graph.json`(`359`)

Python script도 valid node prefixes에 code/non-code/domain/knowledge node types를 포함한다(`merge-batch-graphs.py:32-39`), `func`→`function`과 complexity alias를 처리한다(`42-76`).

### Phase 3 assemble review

현재 source는 merge 후 `assemble-reviewer` agent를 dispatch한다(`SKILL.md:391-414`). 이 단계는 merge stderr와 importMap을 context로 받아 semantic gap/cross-batch edge issue를 검토한다. Gemini baseline의 assemble-reviewer claim은 confirmed다.

### Phase 4 architecture analysis

Architecture phase는 `architecture-analyzer.md` agent definition을 쓰며, language context, framework addendum, output locale guidance를 prompt에 주입한다(`SKILL.md:418-426`). File-level nodes는 code뿐 아니라 config/document/service/pipeline/table/schema/resource/endpoint까지 포함된다(`450-463`). LLM output은 legacy field rename, ID synthesis, raw filepath conversion, dangling ref drop 규칙으로 normalize된다(`465-488`).

Gemini baseline은 “구조적 지표/디렉토리/import density”를 강조했지만 현재 source의 `/understand` skill 자체에는 별도 deterministic architecture metric script 경로가 보이지 않았다. 이 claim은 agent prompt 내부에서 수행될 수 있으나, 현재 확인된 primary evidence는 LLM architecture-analyzer dispatch와 normalization 규칙이다.

### Phase 5 tour builder

Tour phase는 `tour-builder` agent를 dispatch하고 README, entry point, language directive를 추가 context로 넣는다(`SKILL.md:501-518`). Nodes/layers/all edges를 전달하고(`520-540`), output은 `steps` envelope unwrap, legacy fields rename, file path conversion, dangling ref drop, order sort를 거친다(`543-570`).

### Phase 6 review/validation

Gemini baseline은 graph-reviewer를 최종 gate처럼 설명했지만 현재 source는 기본 경로와 `--review` 경로가 다르다.

- Default path: inline deterministic validation Node.js script를 작성/실행한다(`SKILL.md:613-680`). 이 script는 node/edge array, required fields, duplicate node IDs, dangling edges, layer refs, tour refs, file node layer assignment, orphan warnings, stats를 검사한다(`623-679`).
- `--review` path: `graph-reviewer` LLM subagent를 dispatch한다(`SKILL.md:694-718`).

따라서 “graph-reviewer가 항상 최종 gate”라는 claim은 current source 기준 corrected다.

### Phase 7 save/dashboard

Final graph는 `.understand-anything/knowledge-graph.json`에 저장되고(`SKILL.md:736-741`), 먼저 structural fingerprints baseline을 `build-fingerprints.mjs`로 생성해야 한다(`742-763`). `meta.json`은 fingerprints 성공 후 기록된다(`765-773`). Intermediate cleanup은 `scan-result.json`만 보존하고 나머지를 삭제한다(`775-785`). Dashboard auto-launch는 final validation 통과 시 `/understand-dashboard`를 호출한다(`798-799`).

## Incremental update / auto-update

일반 `/understand` incremental path는 changed files를 `git diff <lastCommitHash>..HEAD --name-only`로 얻고(`SKILL.md:176-179`), `compute-batches.mjs --changed-files`를 실행한다(`370-376`). 기존 graph에서 changed file node/edge를 prune하고 `batch-existing.json`과 fresh batches를 merge한다(`380-387`).

Auto-update hook은 `understand-anything-plugin/hooks/hooks.json`에 있다. `PostToolUse` Bash matcher는 `git commit|merge|cherry-pick|rebase`를 감지하고 `autoUpdate: true` config와 graph 존재 시 `auto-update-prompt.md`를 읽으라고 출력한다(`hooks.json:3-10`). `SessionStart`도 stale commit hash를 감지한다(`hooks.json:14-20`).

`auto-update-prompt.md`는 zero-token fingerprint check와 decision matrix를 설명한다. `SKIP`, `PARTIAL_UPDATE`, `ARCHITECTURE_UPDATE`, `FULL_UPDATE` 기준은 `auto-update-prompt.md:116-120`, gate는 `141-149`에서 확인된다. Core에도 `classifyUpdate` 함수가 있으며 action union과 matrix는 `change-classifier.ts:4-21`, FULL/ARCH/PARTIAL return은 `55-84`에서 확인된다.

## `/understand-domain`

`/understand-domain`은 existing `knowledge-graph.json`이 있으면 graph에서 derive하고, 없거나 `--full`이면 lightweight scan을 수행한다(`understand-domain/SKILL.md:11-15`, `89-93`). Lightweight path는 `extract-domain-context.py`를 실행해 `domain-context.json`을 만들며 file tree, entry points, file signatures, snippets, metadata를 포함한다(`95-110`). Domain analysis는 `agents/domain-analyzer.md`를 dispatch하고(`123-128`), 표준 graph validation 후 `.understand-anything/domain-graph.json`에 저장한다(`129-135`). Dashboard는 domain graph를 감지해 domain view를 보여준다(`137-140`).

## `/understand-knowledge`

`/understand-knowledge`는 Karpathy-pattern LLM wiki를 대상으로 한다. Detection signal은 `index.md`와 wikilink가 있는 여러 `.md` 파일, 선택적으로 `raw/`와 schema file이다(`understand-knowledge/SKILL.md:11-20`).

Deterministic parse는 `python3 <SKILL_DIR>/parse-knowledge-base.py <TARGET_DIR>`로 수행하고, `scan-manifest.json`을 생성한다(`30-36`). 이 manifest는 article/source/topic nodes, wikilink `related` edges, index category `categorized_under` edges를 포함한다(`41-50`). 이후 `article-analyzer` batch가 implicit knowledge를 추가하고(`52-70`), `merge-knowledge-graph.py`가 dedupe/normalize/layers/tour/assembled graph를 만든다(`72-90`). Final graph는 target wiki의 `.understand-anything/knowledge-graph.json`에 저장되고 dashboard를 auto-trigger한다(`91-125`).
