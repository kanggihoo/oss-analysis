# Development

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [CLAUDE.md](CLAUDE.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [agent_reach/__init__.py](agent_reach/__init__.py)
- [docs/wechat-group-qr.jpg](docs/wechat-group-qr.jpg)
- [llms.txt](llms.txt)
- [pyproject.toml](pyproject.toml)
- [tests/test_cli.py](tests/test_cli.py)

</details>



This page is a contributor-oriented overview of how the `agent-reach` package is structured, built, tested, and kept up to date with upstream dependencies. It covers the build system configuration, the included data directories, the test suite, and the development conventions defined in `CLAUDE.md`.

For end-user installation steps, see the Getting Started page ([Getting Started](#1.2)). For detailed dependency and extras documentation, see [Package and Dependencies](#6.1). For the test suite specifics, see [Testing](#6.2). For upstream sync details, see [Upstream Sync](#6.3).

---

## Repository Layout

The repository contains the following top-level directories and files relevant to contributors:

| Path | Purpose |
|---|---|
| `agent_reach/` | Main Python package source [pyproject.toml:65]() |
| `agent_reach/channels/` | All platform implementations inheriting from `BaseChannel` [CLAUDE.md:21-22]() |
| `agent_reach/guides/` | Bundled documentation included in the wheel [pyproject.toml:68]() |
| `agent_reach/skill/` | `SKILL.md` bundled for AI agent skill registration [pyproject.toml:69]() |
| `scripts/sync-upstream.sh` | Shell script to diff channel files against upstream `runesleo/x-reader` [CLAUDE.md:16-28]() |
| `test.sh` | End-to-end integration test script [CLAUDE.md:12]() |
| `tests/` | Pytest suite (CLI, config, channels, doctor) [CLAUDE.md:26]() |
| `pyproject.toml` | Package metadata, dependencies, and build configuration [pyproject.toml:1-63]() |
| `CLAUDE.md` | Developer guide: commands, structure, and rules [CLAUDE.md:1-45]() |

Sources: [pyproject.toml:65-70](), [CLAUDE.md:16-28](), [CONTRIBUTING.md:52-59]()

---

## Package Build

**Build system diagram — `pyproject.toml` to wheel contents**

```mermaid
flowchart TD
    pyproject["pyproject.toml"]
    hatchling["hatchling\n(build-backend)"]
    pkg["agent_reach/\n(Python source)"]
    guides["agent_reach/guides/\n(force-included)"]
    skill["agent_reach/skill/\n(force-included)"]
    wheel["agent-reach-*.whl"]
    entrypoint["console_scripts:\nagent-reach = agent_reach.cli:main"]

    pyproject --> hatchling
    hatchling --> pkg
    hatchling --> guides
    hatchling --> skill
    hatchling --> wheel
    wheel --> entrypoint
```

Sources: [pyproject.toml:53-63](), [pyproject.toml:67-70]()

The build backend is `hatchling` [pyproject.toml:61-62](). The `packages` directive includes the core `agent_reach` directory [pyproject.toml:65](). Three data directories—`agent_reach/guides/`, `agent_reach/skill/`, and `agent_reach/scripts/`—are force-included via the `[tool.hatch.build.targets.wheel.force-include]` table [pyproject.toml:67-70]() to ensure they are present in the installed wheel.

The console script entrypoint maps the `agent-reach` command to the `main` function in `agent_reach.cli` [pyproject.toml:52-53]().

### Runtime Dependencies

| Dependency | Minimum Version | Role |
|---|---|---|
| `requests` | 2.28 | HTTP requests and GitHub API updates [pyproject.toml:31]() |
| `feedparser` | 6.0 | RSS channel backend [pyproject.toml:32]() |
| `python-dotenv` | 1.0 | Environment variable management [pyproject.toml:33]() |
| `loguru` | 0.7 | Structured logging across the package [pyproject.toml:34]() |
| `pyyaml` | 6.0 | `config.yaml` parsing and storage [pyproject.toml:35]() |
| `rich` | 13.0 | CLI formatting and "doctor" reports [pyproject.toml:36]() |
| `yt-dlp` | 2024.0 | YouTube/Bilibili transcript and info extraction [pyproject.toml:37]() |

Sources: [pyproject.toml:30-38]()

### Optional Extras

| Extra | Packages Added | Enables |
|---|---|---|
| `[browser]` | `playwright>=1.40` | Headless browser for WeChat/Camoufox [pyproject.toml:41]() |
| `[cookies]` | `browser-cookie3>=0.19` | `agent-reach configure --from-browser` [pyproject.toml:42]() |
| `[all]` | `playwright`, `mcp[cli]`, `browser-cookie3` | Full feature set including MCP [pyproject.toml:43]() |
| `[dev]` | `pytest`, `ruff`, `mypy` | Linting, type checking, and testing [pyproject.toml:44-50]() |

Sources: [pyproject.toml:40-50]()

---

## Developer Conventions (`CLAUDE.md`)

The `CLAUDE.md` file defines the primary rules and conventions for the project to maintain consistency:

- **Channel Contract**: Every platform must implement `can_handle(url)`, `read(url)`, `search(query)`, and `check()` [CLAUDE.md:32]().
- **Glue Layer Philosophy**: Agent Reach is a "glue layer" that routes and calls existing tools; it does not reimplement their internals [CLAUDE.md:39]().
- **Version Synchronization**: The version string must match exactly in `pyproject.toml`, `agent_reach/__init__.py`, and `tests/test_cli.py` [CLAUDE.md:40]().
- **Authentication**: For XHS and Twitter, only cookie-based exports are supported to avoid hanging on QR scans [CLAUDE.md:43-44]().

Sources: [CLAUDE.md:29-45](), [agent_reach/__init__.py:4]()

---

## Testing

The test suite consists of automated unit tests and a manual integration script.

| Component | File | Type | What it tests |
|---|---|---|---|
| Integration | `test.sh` | Shell script | Full CLI commands (install, doctor, read, search) [CLAUDE.md:12]() |
| CLI Logic | `tests/test_cli.py` | Pytest | Arg parsing, version output, and cookie parsing [tests/test_cli.py:11-45]() |
| Update Logic | `tests/test_cli.py` | Pytest | GitHub API retry logic and error classification [tests/test_cli.py:46-127]() |
| Diagnostics | `tests/test_doctor.py` | Pytest | Health check logic and report formatting [CLAUDE.md:20]() |

### Integration Test Flow

**`test.sh` execution flow**

```mermaid
flowchart TD
    start["bash test.sh"]
    venv["Create temp venv\npython3 -m venv"]
    install["pip install -e ."]
    run_doctor["agent-reach doctor"]
    
    subgraph read_tests["Read Tests"]
        web_read["agent-reach read example.com"]
        gh_read["agent-reach read github.com/..."]
        yt_read["agent-reach read youtube.com/..."]
    end
    
    subgraph search_tests["Search Tests"]
        web_search["agent-reach search '...'"]
        gh_search["agent-reach search-github '...'"]
        tw_search["agent-reach search-twitter '...'"]
    end
    
    validate{"Output contains\n✅ / 📖 / 🔗?"}
    pass["PASS ✅"]
    fail["FAIL ❌"]
    
    start --> venv --> install --> run_doctor
    run_doctor --> read_tests --> search_tests
    search_tests --> validate
    validate -->|yes| pass
    validate -->|no| fail
```

Sources: [CLAUDE.md:8-15](), [tests/test_cli.py:26-32]()

For full details on the test suite and how to run specific platform tests, see [Testing](#6.2).

---

## Upstream Sync

Channel implementations in `agent_reach/channels/` are tracked against the `runesleo/x-reader` repository. The script `scripts/sync-upstream.sh` automates the comparison.

**Upstream sync workflow**

```mermaid
flowchart TD
    upstream["github.com/runesleo/x-reader\nx_reader/fetchers/"]
    local["agent_reach/channels/"]
    
    diff["diff with path rewrite\nx_reader.fetchers\n→ agent_reach.channels"]
    
    result_changed["📝 CHANGED: diff output"]
    result_ok["✅ All up to date"]
    
    manual["Manual Review:\n1. cp file\n2. sed path rewrite\n3. pytest"]

    upstream --> diff
    local --> diff
    diff -->|"files differ"| result_changed
    diff -->|"no diffs"| result_ok
    result_changed --> manual
```

Sources: [CLAUDE.md:21-22](), [CONTRIBUTING.md:52-59]()

For details on the path rewriting logic and manual merge workflow, see [Upstream Sync](#6.3).
