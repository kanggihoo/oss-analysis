# Worked Examples & Benchmarks

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [worked/example/README.md](worked/example/README.md)
- [worked/httpx/GRAPH_REPORT.md](worked/httpx/GRAPH_REPORT.md)
- [worked/httpx/README.md](worked/httpx/README.md)
- [worked/httpx/review.md](worked/httpx/review.md)
- [worked/karpathy-repos/GRAPH_REPORT.md](worked/karpathy-repos/GRAPH_REPORT.md)
- [worked/karpathy-repos/README.md](worked/karpathy-repos/README.md)
- [worked/karpathy-repos/graph.json](worked/karpathy-repos/graph.json)
- [worked/karpathy-repos/review.md](worked/karpathy-repos/review.md)
- [worked/mixed-corpus/README.md](worked/mixed-corpus/README.md)
- [worked/mixed-corpus/review.md](worked/mixed-corpus/review.md)

</details>



This section provides an overview of the reference corpora located in the `worked/` directory. These examples serve as both functional tests for the `graphify` pipeline and benchmarks for measuring extraction accuracy, community detection quality, and token reduction performance.

Each example demonstrates a specific capability of the system, ranging from simple AST-based code analysis to complex, multi-modal ingestion of research papers and images.

## Reference Corpora Overview

The `worked/` directory contains five distinct scenarios designed to exercise different parts of the `graphify` engine.

| Example | Primary Focus | Key Metrics |
|:---|:---|:---|
| **Simple Example** | Document & Code Pipeline | 7 files, 2 languages, clear call hierarchy |
| **httpx Benchmark** | Library Codebase Analysis | 144 nodes, 330 edges, 6 communities |
| **Karpathy Repos** | Large-scale Cross-Repo | 52 files, 71.5x token reduction |
| **Mixed Corpus** | Multi-modal Ingestion | Python + Markdown + ArXiv + Images |
| **rsl-siege-manager** | Full-stack Monorepo | Cross-language (TS/PY), migration docs |

### System Data Flow: From Source to Graph

The following diagram illustrates how these worked examples move through the `graphify` pipeline, transforming raw files into the structured entities found in the benchmark reports.

**Diagram: Worked Example Transformation Flow**
```mermaid
graph TD
    subgraph "Natural_Language_&_File_Space"
        [RAW] -- "raw/ directory" --> [DIR]
        [PY_FILES] -- "*.py" --> [CODE]
        [MD_FILES] -- "*.md" --> [DOCS]
        [PDF_FILES] -- "*.pdf" --> [PAPERS]
        [IMG_FILES] -- "*.png/*.svg" --> [IMAGES]
    end

    subgraph "Code_Entity_&_Graph_Space"
        [EXTRACTOR] -- "graphify/extract.py" --> [EXT]
        [BUILDER] -- "graphify/build.py" --> [BLD]
        [CLUSTER] -- "graphify/cluster.py" --> [CLU]
        
        [GOD_NODES] -- "God Nodes" --> [GN]
        [COMMUNITIES] -- "Leiden Communities" --> [COMM]
        [SURPRISES] -- "Surprising Connections" --> [SURP]
    end

    [DIR] --> [CODE]
    [DIR] --> [DOCS]
    [DIR] --> [PAPERS]
    [DIR] --> [IMAGES]

    [CODE] -- "tree-sitter AST" --> [EXT]
    [DOCS] -- "Markdown Parsing" --> [EXT]
    [PAPERS] -- "Vision/Text Extraction" --> [EXT]
    [IMAGES] -- "Claude Vision" --> [EXT]

    [EXT] -- "Extraction Dicts" --> [BLD]
    [BLD] -- "NetworkX Graph" --> [CLU]
    [CLU] -- "Community IDs" --> [GN]
    [CLU] -- "Cohesion Scores" --> [COMM]
    [BLD] -- "Edge Analysis" --> [SURP]
```
Sources: [worked/example/README.md:9-18](), [worked/httpx/README.md:8-15](), [worked/karpathy-repos/README.md:32-47](), [worked/mixed-corpus/README.md:8-13](), [ARCHITECTURE.md:7-9]()

---

## [Simple Example (document pipeline)](#7.1)
The `worked/example` corpus represents a standard micro-service architecture consisting of 5 Python modules (`api.py`, `storage.py`, `parser.py`, `validator.py`, `processor.py`) and 2 Markdown files (`architecture.md`, `notes.md`). It demonstrates how `graphify` identifies `api.py` as a central hub and `storage.py` as a "God Node" due to its high inward connectivity from other modules. This example runs entirely on AST and markdown with zero token cost for semantic extraction.

For details, see [Simple Example (document pipeline)](#7.1).
Sources: [worked/example/README.md:9-18](), [worked/example/README.md:39-45]()

## [httpx Benchmark (library codebase)](#7.2)
Based on a synthetic version of the `httpx` library, this benchmark tests the extraction of complex class hierarchies and asynchronous patterns across 6 Python files. It produces a dense graph of 144 nodes and 330 edges. Key findings include the identification of `Client`, `AsyncClient`, and `Response` as major architectural bridges across 6 detected communities. It highlights "surprising connections" such as `DigestAuth` linked to `Response` for header parsing.

For details, see [httpx Benchmark (library codebase)](#7.2).
Sources: [worked/httpx/README.md:8-15](), [worked/httpx/README.md:36-39](), [worked/httpx/GRAPH_REPORT.md:12-23]()

## [Karpathy Repos Benchmark (71.5x token reduction)](#7.3)
This is the flagship performance benchmark. It ingests 52 files across three independent repositories (`nanoGPT`, `minGPT`, `micrograd`), alongside 5 ArXiv PDFs and 4 images. It demonstrates `graphify`'s ability to find cross-repo connections (e.g., linking `Block` implementations in `nanoGPT` and `minGPT`) and achieves a **71.5x reduction** in tokens required for an LLM to reason about the entire corpus.

For details, see [Karpathy Repos Benchmark (71.5x token reduction)](#7.3).
Sources: [worked/karpathy-repos/README.md:5-29](), [worked/karpathy-repos/README.md:68-71](), [worked/karpathy-repos/review.md:11-27]()

## [Mixed Corpus Benchmark (multi-modal)](#7.4)
The `worked/mixed-corpus` focuses on multi-modal integration. It utilizes ArXiv ID patterns (e.g., `1706.03762`) to classify files as "papers" and demonstrates how technical diagrams (like `attention_arabic.png`) are integrated via vision extraction. This example produces 3 distinct communities: Graph Analysis, Clustering/Scoring, and Graph Building.

For details, see [Mixed Corpus Benchmark (multi-modal)](#7.4).
Sources: [worked/mixed-corpus/README.md:7-15](), [worked/mixed-corpus/README.md:36-41](), [worked/mixed-corpus/review.md:19-21]()

## [rsl-siege-manager Case Study (full-stack monorepo)](#7.5)
This case study examines a real-world monorepo containing Python (FastAPI) and TypeScript (React) components. It highlights how the presence of test factories can dominate "God Node" lists and demonstrates the impact of `.graphifyignore` on community quality. It also documents the handling of 17 Alembic migration docstrings and cross-language inference behavior.

For details, see [rsl-siege-manager Case Study (full-stack monorepo)](#7.5).
Sources: [worked/rsl-siege-manager/review.md:1-20]()

---

### Entity Mapping: Benchmark Report to Code
This diagram maps the high-level concepts found in a `GRAPH_REPORT.md` (like the ones in `worked/`) to the specific Python functions that generate them.

**Diagram: Report-to-Code Mapping**
```mermaid
graph LR
    subgraph "GRAPH_REPORT.md_Section"
        [GN] -- "God Nodes" --> [R_GN]
        [SC] -- "Surprising Connections" --> [R_SC]
        [CS] -- "Community Summary" --> [R_CS]
        [SQ] -- "Suggested Questions" --> [R_SQ]
    end

    subgraph "graphify/analyze.py"
        [F_GN] -- "analyze()" --> [A_GN]
        [F_SC] -- "analyze()" --> [A_SC]
        [F_SQ] -- "analyze()" --> [A_SQ]
    end

    subgraph "graphify/cluster.py"
        [F_CL] -- "cluster()" --> [C_CL]
    end

    subgraph "graphify/report.py"
        [F_RR] -- "render_report()" --> [RE_REP]
    end

    [A_GN] --> [RE_REP]
    [A_SC] --> [RE_REP]
    [A_SQ] --> [RE_REP]
    [C_CL] --> [RE_REP]
    [RE_REP] --> [R_GN]
    [RE_REP] --> [R_SC]
    [RE_REP] --> [R_CS]
    [RE_REP] --> [R_SQ]
```
Sources: [worked/httpx/README.md:36-39](), [worked/mixed-corpus/README.md:9-11](), [worked/karpathy-repos/README.md:68-70](), [ARCHITECTURE.md:21-22]()
