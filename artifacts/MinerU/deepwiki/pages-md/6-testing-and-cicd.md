# Testing & CI/CD

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.github/workflows/cla.yml](.github/workflows/cla.yml)
- [.github/workflows/cli.yml](.github/workflows/cli.yml)
- [.github/workflows/mkdocs.yml](.github/workflows/mkdocs.yml)
- [.github/workflows/python-package.yml](.github/workflows/python-package.yml)
- [tests/clean_coverage.py](tests/clean_coverage.py)
- [update_version.py](update_version.py)

</details>



This page provides a high-level overview of the testing strategy and Continuous Integration/Continuous Deployment (CI/CD) pipelines for the MinerU project. The codebase employs a multi-layered testing approach, ranging from unit tests to end-to-end CLI validation, all orchestrated through GitHub Actions.

## Testing Strategy Overview

MinerU's testing infrastructure is designed to ensure the reliability of document parsing across various backends and hardware configurations. The suite includes traditional unit tests, integration tests for the CLI and SDK, and specialized benchmark scripts to evaluate model performance and extraction accuracy. 

The testing strategy validates the flow from raw PDF bytes to the final `middle_json` and Markdown outputs. The CI environment uses `uv` for high-speed dependency installation of the `[test]` extra [[.github/workflows/cli.yml:28-36]()] and executes tests with Python 3.12 [[.github/workflows/cli.yml:34]()]. Automated coverage reporting is integrated into the workflow, utilizing `clean_coverage.py` to prepare the environment and `get_coverage.py` to aggregate results [[.github/workflows/cli.yml:37-39](), [tests/clean_coverage.py:24-27]()].

The following diagram illustrates the relationship between the testing tools and the core codebase entities:

**Testing Entity Map**
```mermaid
graph TD
    subgraph "Testing_Tools"
        T1["test_unit.py"]
        T2["test_e2e.py"]
        T3["benchmark.py"]
        T4["get_coverage.py"]
        T5["clean_coverage.py"]
    end

    subgraph "Core_Codebase"
        C1["mineru_CLI"]
        C2["middle_json"]
        C3["pipeline_doc_analyze_streaming"]
        C4["union_make"]
        C5["FileBasedDataWriter"]
    end

    T2 -->| "calls" | C3
    T2 -->| "converts_output_via" | C4
    T2 -->| "validates" | C2
    T2 -->| "writes_results" | C5
    T4 -->| "measures" | C3
    T5 -->| "deletes" | H["htmlcov/"]
```
Sources: [.github/workflows/cli.yml:37-39](), [tests/clean_coverage.py:8-25]()

For a detailed breakdown of the test files (including `test_table.py` and `test_metascan_classify.py`), CLI integration tests (`test_cli_sdk.py`), benchmark scoring (`calculate_score.py`), and coverage reporting, see **[Test Suite](#6.1)**.

## CI/CD Pipelines

MinerU utilizes GitHub Actions to automate testing, documentation deployment, and the release process. There are four primary workflows:

1.  **CLI Test Workflow**: Triggered on pushes to `master` and `dev` branches [[.github/workflows/cli.yml:5-9]()]. It uses `uv` for fast dependency management [[.github/workflows/cli.yml:28-29]()] and executes the test suite with coverage reporting via `coverage run` [[.github/workflows/cli.yml:38-39]()].
2.  **Documentation Workflow**: Automatically deploys the MkDocs-based documentation to GitHub Pages whenever changes are pushed to the main branches [[.github/workflows/mkdocs.yml:1-7]()]. It uses `mkdocs-deploy-gh-pages` to manage the deployment lifecycle [[.github/workflows/mkdocs.yml:17-22]()].
3.  **Release Workflow**: A complex pipeline triggered by specific release tags (e.g., `*released`) [[.github/workflows/python-package.yml:7-9]()]. It handles version synchronization, cross-version installation checks (Python 3.10 to 3.13), and publishing to PyPI [[.github/workflows/python-package.yml:57-63](), [.github/workflows/python-package.yml:140-144]()].
4.  **CLA Assistant**: Manages Contributor License Agreements for pull requests via the `CLAAssistant` job [[.github/workflows/cla.yml:15-16]()]. It ensures contributors have signed the document at `MinerU_CLA.md` [[.github/workflows/cla.yml:29]()] before code is merged, tracking signatures in `signatures/version1/cla.json` [[.github/workflows/cla.yml:28]()].

### Release and Versioning Lifecycle

The release process is governed by `update_version.py`, which extracts version information from Git tags using `git describe --tags` via the `get_version()` function [[update_version.py:6-17]()] and updates the internal `mineru/version.py` file using `write_version_to_commons()` [[update_version.py:20-23]()]. This ensures that the `__version__` string remains consistent across the CLI, API, and PyPI package. The `build` job generates the wheel file which is then uploaded as a GitHub artifact before being published [[.github/workflows/python-package.yml:108-117]()].

**Release Pipeline Flow**
```mermaid
graph LR
    Tag["Git_Tag_(*released)"] --> UV["update_version.py"]
    UV --> CI["check-install_Job"]
    CI --> Build["build_Job_(wheel)"]
    Build --> Release["GitHub_Release"]
    Release --> PyPI["twine_upload"]

    subgraph "Code_Entities"
        UV_File["mineru/version.py"]
        Dist["dist/*.whl"]
        V_Func["get_version()"]
        V_Write["write_version_to_commons()"]
    end

    UV -.->| "calls" | V_Func
    UV -.->| "calls" | V_Write
    V_Write -.->| "updates" | UV_File
    Build -.->| "generates" | Dist
```
Sources: [.github/workflows/python-package.yml:15-144](), [update_version.py:6-28]()

For details on the release jobs, PyPI publishing via `twine`, and the automated versioning logic, see **[Release Pipeline & Versioning](#6.2)**.

## Summary Table of CI Components

| Component | File / Tool | Purpose |
| :--- | :--- | :--- |
| **Dependency Manager** | `uv` | High-speed installation of `.[test]` and `.[core]` extras [[.github/workflows/cli.yml:28-36]()]. |
| **Coverage** | `coverage.py` | Measures test execution paths; managed via `clean_coverage.py` [[.github/workflows/cli.yml:38-39](), [tests/clean_coverage.py:24-25]()]. |
| **Versioning** | `update_version.py` | Syncs `mineru/version.py` with Git tags via `get_version()` [[update_version.py:6-17]()]. |
| **Publishing** | `twine` | Validates and uploads wheels to PyPI using `PYPI_TOKEN` [[.github/workflows/python-package.yml:142-144]()]. |
| **Docs** | `mkdocs` | Builds and deploys the technical documentation to GitHub Pages via `mkdocs-deploy-gh-pages` [[.github/workflows/mkdocs.yml:17-22]()]. |
| **Compatibility** | `check-install` | Verifies installation across Python 3.10, 3.11, 3.12, and 3.13 [[.github/workflows/python-package.yml:57-63]()]. |
| **Legal/CLA** | `cla.yml` | Tracks contributor signatures in `signatures/version1/cla.json` [[.github/workflows/cla.yml:28]()]. |

Sources: [.github/workflows/cli.yml:28-39](), [.github/workflows/python-package.yml:57-145](), [update_version.py:6-28](), [tests/clean_coverage.py:8-25](), [.github/workflows/cla.yml:1-32]()
