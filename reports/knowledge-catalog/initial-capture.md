# GoogleCloudPlatform/knowledge-catalog initial capture

Generated: 2026-06-28

## Scope

Initial DeepWiki-first capture plus source-verified repository surface check for `GoogleCloudPlatform/knowledge-catalog`.

This is **not** a full architecture report. DeepWiki content below is treated as an external baseline until individual claims are checked against `repos/knowledge-catalog/`.

## Completed capture work

### DeepWiki baseline

- Input: `GoogleCloudPlatform/knowledge-catalog`
- Output root: `artifacts/knowledge-catalog/deepwiki/`
- Extraction command output:
  - `[start] GoogleCloudPlatform/knowledge-catalog`
  - `[index] OK`
  - `[toc] 26`
  - `[match] 25/26`
  - `[page 1/1] MISS`
  - `[write] OK`
  - `Done: 25/26 missing=1`
- Manual repair: `4.1-okf-specification` was not absent; the page payload H1 was `4.1. OKF Specification` while the TOC title was `OKF Specification`. I copied the original `self.__next_f.push` Markdown payload into `pages-md/4.1-okf-specification.md` and recorded the title drift in `pages-meta/4.1-okf-specification.json`.
- Completeness verification: `artifacts/knowledge-catalog/deepwiki/completeness-check.json`
  - `toc_count`: 26
  - `pages_md_count`: 26
  - `pages_meta_count`: 26
  - `manifest_missing_pages_count`: 0
  - `missing_md`: `[]`
  - `missing_meta`: `[]`

Key DeepWiki files:

- `artifacts/knowledge-catalog/deepwiki/raw/index.html`
- `artifacts/knowledge-catalog/deepwiki/toc.json`
- `artifacts/knowledge-catalog/deepwiki/toc.md`
- `artifacts/knowledge-catalog/deepwiki/manifest.json`
- `artifacts/knowledge-catalog/deepwiki/pages-md/`
- `artifacts/knowledge-catalog/deepwiki/pages-meta/`

### Local checkout and metadata

- Checkout: `repos/knowledge-catalog/`
- Metadata: `artifacts/knowledge-catalog/repo-metadata.txt`
- GitHub REST metadata: `artifacts/knowledge-catalog/github-metadata.json`
- Current source snapshot:
  - branch: `main`
  - HEAD: `d44368c15e38e7c92481c5992e4f9b5b421a801d`
  - describe: `d44368c`
  - working tree: clean (`0 dirty entries`)
  - latest commit: `okf: refocus README title and intro on the format (#130)`

### Static artifact capture

- Tracked file inventory: `artifacts/knowledge-catalog/static-analysis/tracked-files.txt`
- Top-level tracked counts: `artifacts/knowledge-catalog/static-analysis/top-level-file-counts.txt`
  - `okf`: 127
  - `toolbox`: 92
  - `samples`: 38
  - root files: 5
  - total tracked files: 262
- Shallow subtree counts: `artifacts/knowledge-catalog/static-analysis/source-tree-counts.txt`
  - `okf/bundles`: 81
  - `okf/src`: 27
  - `okf/tests`: 8
  - `toolbox/mdcode`: 77
  - `toolbox/enrichment`: 14
  - `samples/enrichment`: 31
  - `samples/discovery`: 6
- Language summary: `artifacts/knowledge-catalog/static-analysis/tokei.txt`
  - total: 256 files, 33,018 lines, 24,776 code lines
  - large surfaces: Markdown 131 files, TypeScript 40 files, Python 47 files, JSON 8 files
- Tool availability: `artifacts/knowledge-catalog/static-analysis/tool-availability.txt`
  - `python3`, `node`, `npm`, `tokei`, `pygount` found
  - `bun` not found as a standalone CLI in the Hermes tool shell

### Test/verification run

Python OKF package tests were run in an artifact-scoped virtual environment:

- venv: `artifacts/knowledge-catalog/static-analysis/okf-venv/`
- install log: `artifacts/knowledge-catalog/static-analysis/okf-pip-install-dev.log`
- test log: `artifacts/knowledge-catalog/static-analysis/okf-pytest-q.log`
- result: `33 passed in 3.17s`

Install context: pip emitted cache-deserialization warnings and dependency-conflict warnings referring to the outer `hermes-agent` package. The install and test command still completed successfully inside the artifact venv. TypeScript package tests were not run in this initial pass because their package scripts invoke `npx bun test` / Bun-based builds, and `bun` was not present as a standalone CLI in the Hermes tool shell.

## Source-verified initial facts

1. Repository positioning: the root README describes Knowledge Catalog as an AI-powered data catalog / metadata management platform and says this repo contains tools, agents, and samples for context management, enrichment, and retrieval solutions. Evidence: `repos/knowledge-catalog/README.md:1-5`.

2. OKF is currently the central emphasized subproject. `okf/README.md` says the repository is primarily about Open Knowledge Format, a vendor-neutral Markdown + YAML-frontmatter format, and describes the included reference agent and visualizer as proof-of-concept producer/consumer pieces rather than the format itself. Evidence: `repos/knowledge-catalog/okf/README.md:1-25`, `repos/knowledge-catalog/okf/README.md:37-74`.

3. The OKF Python package is named `reference-agent`, version `0.1.0`, requires Python `>=3.11`, depends on Google ADK, BigQuery, PyYAML, Pydantic, and Markdownify, and exposes a console script `reference-agent = reference_agent.cli:main`. Evidence: `repos/knowledge-catalog/okf/pyproject.toml:5-22`.

4. The OKF CLI has two top-level subcommands in current source: `enrich` and `visualize`. `enrich` accepts source/dataset/output/model/web-crawl controls; `visualize` generates a self-contained HTML view for an OKF bundle. Evidence: `repos/knowledge-catalog/okf/src/reference_agent/cli.py:59-161`, `repos/knowledge-catalog/okf/src/reference_agent/cli.py:176-214`.

5. The OKF reference agent builds two Google ADK agents: a BigQuery reference agent with concept/source/bundle tools, and a web-ingestion agent with similar bundle/source tools plus `fetch_url`. Evidence: `repos/knowledge-catalog/okf/src/reference_agent/agent.py:27-54`.

6. The OKF runner executes concept enrichment per source concept, optionally runs a bounded web pass, then regenerates `index.md` files in the bundle. Evidence: `repos/knowledge-catalog/okf/src/reference_agent/runner.py:155-205`, `repos/knowledge-catalog/okf/src/reference_agent/runner.py:217-280`.

7. The TypeScript `toolbox/mdcode` package is named `kcmd`, exposes a `kcmd` binary, and describes itself as a Knowledge Catalog Metadata-as-Code library, CLI, and MCP server. Evidence: `repos/knowledge-catalog/toolbox/mdcode/package.json:1-20`.

8. Current `kcmd` CLI source registers `init`, `pull`, `push`, and `mcp` commands. The command handlers construct manifests/snapshots and sync through a Dataplex catalog client. Evidence: `repos/knowledge-catalog/toolbox/mdcode/src/tool/main.ts:9-79`, `repos/knowledge-catalog/toolbox/mdcode/src/tool/commands.ts:25-100`.

9. The TypeScript `toolbox/enrichment` package is named `kcagent`, exposes `kcagent` and `md-fileset` binaries, depends on Google ADK and local `kcmd`, and registers an `enrich` CLI command. Evidence: `repos/knowledge-catalog/toolbox/enrichment/package.json:1-28`, `repos/knowledge-catalog/toolbox/enrichment/src/agent/main.ts:15-20`.

10. There is no `.github/` directory in the current checkout, so no GitHub Actions workflow was available for CI-based test-command discovery in this initial pass. Evidence: filesystem search under `repos/knowledge-catalog/.github` returned path-not-found.

## DeepWiki baseline claims captured but not yet fully source-verified

DeepWiki TOC divides the repo into these major areas:

- `kcmd: Metadata as Code CLI and Library`
- `Enrichment Agents`
- `Open Knowledge Format (OKF)`
- `Samples and Demos`
- `Glossary`

These labels are useful navigation hypotheses. The initial source pass confirmed the broad presence of OKF, `kcmd`, `kcagent`, samples, package manifests, CLI entrypoints, and OKF tests, but it did **not** yet verify every DeepWiki claim about internal synchronization semantics, GCP API behavior, evaluation framework details, or sample/demo runtime behavior.

## Recommended next steps

1. Produce a source-verified architecture report for the three active surfaces: `okf/`, `toolbox/mdcode/`, and `toolbox/enrichment/`.
2. Run TypeScript builds/tests after installing or enabling Bun in the Hermes tool shell, and save logs under `artifacts/knowledge-catalog/static-analysis/`.
3. Compare DeepWiki pages against current source for drift, especially the `CatalogSync`, MCP server, and OKF reference-agent sections.
4. If the goal is reusable design extraction, update `wiki/projects/knowledge-catalog.md` and OKF concept notes only after the above source verification.
