# Testing

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/workflows/ci.yml](.github/workflows/ci.yml)
- [LICENSE](LICENSE)
- [tests/test_backend_extras.py](tests/test_backend_extras.py)
- [tests/test_pipeline.py](tests/test_pipeline.py)
- [uv.lock](uv.lock)

</details>



The `graphify` test suite ensures the integrity of the knowledge graph construction pipeline and the accuracy of its extraction, analysis, and export modules. The suite follows a modular structure where each core functional script has a corresponding test file, complemented by an end-to-end pipeline test that validates the integration of all stages.

### Test Architecture

The testing strategy is bifurcated into granular unit tests and high-level integration tests. All tests are designed to run without LLM dependencies by utilizing AST-based extraction and local file fixtures [tests/test_pipeline.py:1-5](). The CI environment uses `uv` to manage dependencies and run tests across multiple Python versions (3.10 and 3.12) [.github/workflows/ci.yml:49-75]().

| Test Category | Purpose | Key Files |
| :--- | :--- | :--- |
| **Unit Tests** | Validates individual module logic (e.g., detection, language-specific extraction, clustering). | `test_detect.py`, `test_languages.py`, `test_extract.py`, `test_cluster.py`, `test_hooks.py`, `test_build.py`. |
| **Integration (E2E)** | Exercises the full linear pipeline from raw files to final exports. | `tests/test_pipeline.py` |
| **Fixtures** | Static code and document samples used to generate predictable graphs. | `tests/fixtures/` |
| **Backend/Env** | Guards installation paths, extras, and tool hints. | `tests/test_backend_extras.py`, `tests/test_install.py`. |

The following diagram illustrates how the test suite maps to the system's core modules and the flow of data during a test run:

**Test Suite to Module Mapping**
```mermaid
graph TD
    subgraph "Test Space"
        [TP "test_pipeline.py"]
        [TU "Unit Tests (test_*.py)"]
        [FIX "tests/fixtures/"]
    end

    subgraph "Code Entity Space"
        [DET "graphify/detect.py"]
        [EXT "graphify/extract.py"]
        [BLD "graphify/build.py"]
        [CLU "graphify/cluster.py"]
        [ANZ "graphify/analyze.py"]
        [REP "graphify/report.py"]
        [EXP "graphify/export.py"]
    end

    FIX --> TP
    TP --> DET
    TP --> EXT
    TP --> BLD
    TP --> CLU
    TP --> ANZ
    TP --> REP
    TP --> EXP

    TU -.->|"Targeted Tests"| DET
    TU -.->|"Targeted Tests"| EXT
    TU -.->|"Targeted Tests"| BLD
```
Sources: [tests/test_pipeline.py:12-18](), [tests/test_pipeline.py:20-20](), [tests/test_pipeline.py:23-104]()

---

### End-to-End Pipeline Test

The primary integration test is defined in `tests/test_pipeline.py`. It utilizes a helper function, `run_pipeline()`, which orchestrates the nine stages of the graphify workflow, including `detect`, `extract`, `build_from_json`, `cluster`, `god_nodes`, and various `export` functions [tests/test_pipeline.py:23-104]().

Key validations performed during the E2E test include:
*   **Graph Integrity**: Ensuring the resulting `NetworkX` graph contains nodes and edges [tests/test_pipeline.py:107-115]().
*   **Community Assignment**: Verifying that every node is assigned to a community via the `cluster` module [tests/test_pipeline.py:117-124]().
*   **Analysis Accuracy**: Checking that "God Nodes" (high-centrality entities) are correctly identified and included in the final report [tests/test_pipeline.py:126-130]().
*   **Confidence Labels**: Validating that all edges are assigned valid confidence levels (`EXTRACTED`, `INFERRED`, or `AMBIGUOUS`) [tests/test_pipeline.py:146-152]().
*   **Idempotency**: Running the pipeline twice on an identical corpus to ensure node and edge counts remain identical [tests/test_pipeline.py:138-144]().
*   **Self-Loop Prevention**: Ensuring no node has an edge to itself [tests/test_pipeline.py:154-159]().

For a detailed breakdown of the integration tests, see **[End-to-End Pipeline Test](#6.1)**.

---

### Unit Tests & Fixtures

Each module in the `graphify/` directory is paired with a specific test file in `tests/`. These tests focus on edge cases and specific logic within the modules:
*   **Language Extractors**: `tests/test_languages.py` and `tests/test_multilang.py` verify that `tree-sitter` correctly identifies classes, methods, and calls across Java, C++, Go, Rust, PHP, SQL, TypeScript, and .NET project files.
*   **Extraction Logic**: `tests/test_extract.py` validates symbol ID generation, disambiguation of duplicate symbols by source path, and the rewiring of inheritance stubs to real definitions.
*   **Installation & Extras**: `tests/test_backend_extras.py` ensures that backend-specific packages (like `anthropic`) are correctly listed in `pyproject.toml` extras and that the `_backend_pkg_hint` function provides correct `uv tool` installation instructions [tests/test_backend_extras.py:1-42]().
*   **Graph Assembly**: `tests/test_build.py` validates that extraction dictionaries are correctly merged into `NetworkX` objects and that legacy keys (like `from`/`to`) are canonicalized.
*   **Export Formats**: `tests/test_export.py` ensures that `to_json`, `to_cypher`, `to_graphml`, `to_canvas`, and `to_html` generate valid files with expected attributes like `community`.
*   **Git Hooks**: `tests/test_hooks.py` tests the idempotent installation and removal of `post-commit` and `post-checkout` hooks, including Python interpreter detection.

**Testing Data Flow**
```mermaid
graph LR
    subgraph "Natural Language Space"
        [MD "Markdown Docs"]
        [PY "Python Source"]
        [JS "JS Source"]
        [CS "C# Source"]
    end

    subgraph "Code Entity Space"
        [FIXTURES "tests/fixtures/"]
        [EXTRACT "graphify/extract.py:extract()"]
        [BUILD "graphify/build.py:build_from_json()"]
        [G "networkx.Graph"]
    end

    MD & PY & JS & CS --> FIXTURES
    FIXTURES --> EXTRACT
    EXTRACT -->|"extraction dict"| BUILD
    BUILD --> G
```
Sources: [tests/test_pipeline.py:20-20](), [tests/test_pipeline.py:34-39](), [tests/test_pipeline.py:149-152](), [tests/test_backend_extras.py:11-11]()

For details on individual module tests and the structure of the fixture directory, see **[Unit Tests & Fixtures](#6.2)**.

---

### Running Tests

Tests are executed using `pytest`. The suite is integrated into the CI workflow using `uv run` [.github/workflows/ci.yml:73-75](). Developers can run the suite locally using the following commands:

```bash
# Run all tests (recommended)
uv run pytest tests/ -q --tb=short

# Run only specific module tests (e.g., Language extractors)
uv run pytest tests/test_languages.py

# Run only the pipeline integration tests
uv run pytest tests/test_pipeline.py
```
Sources: [tests/test_pipeline.py:1-5](), [.github/workflows/ci.yml:74-74](), [uv.lock:1-12]()
