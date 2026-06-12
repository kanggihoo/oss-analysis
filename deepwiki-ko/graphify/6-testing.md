---
type: deepwiki-translation
repo: graphify
source: artifacts/graphify/deepwiki/pages-md/6-testing.md
deepwiki_url: https://deepwiki.com/safishamsi/graphify/6-testing
section: "6"
order: 27
---

# Testing

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하기 위한 컨텍스트로 사용되었습니다.

- [.github/workflows/ci.yml](.github/workflows/ci.yml)
- [LICENSE](LICENSE)
- [tests/test_backend_extras.py](tests/test_backend_extras.py)
- [tests/test_pipeline.py](tests/test_pipeline.py)
- [uv.lock](uv.lock)

</details>



`graphify` test suite는 knowledge graph construction pipeline의 무결성과 extraction, analysis, export modules의 정확성을 보장한다. 이 suite는 각 core functional script에 대응하는 test file을 두는 modular structure를 따르며, 모든 stages의 integration을 validate하는 end-to-end pipeline test로 보완된다.

### Test Architecture

testing strategy는 granular unit tests와 high-level integration tests로 나뉜다. 모든 tests는 AST-based extraction과 local file fixtures를 사용해 LLM dependencies 없이 실행되도록 설계되어 있다 [tests/test_pipeline.py:1-5](). CI environment는 `uv`를 사용해 dependencies를 관리하고 여러 Python versions(3.10, 3.12)에서 tests를 실행한다 [.github/workflows/ci.yml:49-75]().

| Test Category | Purpose | Key Files |
| :--- | :--- | :--- |
| **Unit Tests** | individual module logic(예: detection, language-specific extraction, clustering)을 validate한다. | `test_detect.py`, `test_languages.py`, `test_extract.py`, `test_cluster.py`, `test_hooks.py`, `test_build.py`. |
| **Integration (E2E)** | raw files에서 final exports까지 전체 linear pipeline을 실행한다. | `tests/test_pipeline.py` |
| **Fixtures** | 예측 가능한 graphs를 생성하는 데 사용되는 static code와 document samples. | `tests/fixtures/` |
| **Backend/Env** | installation paths, extras, tool hints를 guard한다. | `tests/test_backend_extras.py`, `tests/test_install.py`. |

다음 다이어그램은 test suite가 system의 core modules에 어떻게 매핑되는지와 test run 중 data flow를 보여준다.

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
출처: [tests/test_pipeline.py:12-18](), [tests/test_pipeline.py:20-20](), [tests/test_pipeline.py:23-104]()

---

### End-to-End Pipeline Test

primary integration test는 `tests/test_pipeline.py`에 정의되어 있다. 이 test는 `detect`, `extract`, `build_from_json`, `cluster`, `god_nodes`, 여러 `export` functions를 포함해 graphify workflow의 아홉 stages를 orchestrate하는 helper function `run_pipeline()`을 사용한다 [tests/test_pipeline.py:23-104]().

E2E test 중 수행되는 주요 validations는 다음과 같다.
*   **Graph Integrity**: 결과 `NetworkX` graph에 nodes와 edges가 포함되어 있는지 보장한다 [tests/test_pipeline.py:107-115]().
*   **Community Assignment**: 모든 node가 `cluster` module을 통해 community에 할당되는지 verify한다 [tests/test_pipeline.py:117-124]().
*   **Analysis Accuracy**: "God Nodes"(high-centrality entities)가 올바르게 식별되고 final report에 포함되는지 확인한다 [tests/test_pipeline.py:126-130]().
*   **Confidence Labels**: 모든 edges에 valid confidence levels(`EXTRACTED`, `INFERRED`, `AMBIGUOUS`)가 할당되는지 validate한다 [tests/test_pipeline.py:146-152]().
*   **Idempotency**: 동일한 corpus에서 pipeline을 두 번 실행해 node와 edge counts가 동일하게 유지되는지 보장한다 [tests/test_pipeline.py:138-144]().
*   **Self-Loop Prevention**: 어떤 node도 자기 자신으로 향하는 edge를 갖지 않도록 보장한다 [tests/test_pipeline.py:154-159]().

integration tests의 자세한 breakdown은 **[End-to-End Pipeline Test](#6.1)**를 참조하라.

---

### Unit Tests와 Fixtures

`graphify/` directory의 각 module은 `tests/`의 특정 test file과 짝을 이룬다. 이 tests는 modules 안의 edge cases와 특정 logic에 집중한다.
*   **Language Extractors**: `tests/test_languages.py`와 `tests/test_multilang.py`는 `tree-sitter`가 Java, C++, Go, Rust, PHP, SQL, TypeScript, .NET project files 전반에서 classes, methods, calls를 올바르게 식별하는지 verify한다.
*   **Extraction Logic**: `tests/test_extract.py`는 symbol ID generation, source path에 따른 duplicate symbols disambiguation, inheritance stubs를 real definitions로 rewiring하는 동작을 validate한다.
*   **Installation & Extras**: `tests/test_backend_extras.py`는 backend-specific packages(예: `anthropic`)가 `pyproject.toml` extras에 올바르게 listed되어 있는지, 그리고 `_backend_pkg_hint` function이 올바른 `uv tool` installation instructions를 제공하는지 보장한다 [tests/test_backend_extras.py:1-42]().
*   **Graph Assembly**: `tests/test_build.py`는 extraction dictionaries가 `NetworkX` objects로 올바르게 merge되고 legacy keys(예: `from`/`to`)가 canonicalized되는지 validate한다.
*   **Export Formats**: `tests/test_export.py`는 `to_json`, `to_cypher`, `to_graphml`, `to_canvas`, `to_html`이 `community` 같은 expected attributes를 가진 valid files를 생성하는지 보장한다.
*   **Git Hooks**: `tests/test_hooks.py`는 Python interpreter detection을 포함해 `post-commit`과 `post-checkout` hooks의 idempotent installation과 removal을 test한다.

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
출처: [tests/test_pipeline.py:20-20](), [tests/test_pipeline.py:34-39](), [tests/test_pipeline.py:149-152](), [tests/test_backend_extras.py:11-11]()

개별 module tests와 fixture directory 구조에 대한 자세한 내용은 **[Unit Tests & Fixtures](#6.2)**를 참조하라.

---

### Running Tests

Tests는 `pytest`를 사용해 실행된다. suite는 `uv run`을 사용해 CI workflow에 통합되어 있다 [.github/workflows/ci.yml:73-75](). Developers는 다음 commands를 사용해 suite를 local에서 실행할 수 있다.

```bash
# Run all tests (recommended)
uv run pytest tests/ -q --tb=short

# Run only specific module tests (e.g., Language extractors)
uv run pytest tests/test_languages.py

# Run only the pipeline integration tests
uv run pytest tests/test_pipeline.py
```
출처: [tests/test_pipeline.py:1-5](), [.github/workflows/ci.yml:74-74](), [uv.lock:1-12]()
