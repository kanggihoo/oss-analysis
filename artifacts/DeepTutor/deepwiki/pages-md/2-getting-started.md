# Getting Started

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.gitattributes](.gitattributes)
- [.github/pull_request_template.md](.github/pull_request_template.md)
- [.github/workflows/pypi-release.yml](.github/workflows/pypi-release.yml)
- [.gitignore](.gitignore)
- [.secrets.baseline](.secrets.baseline)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [Dockerfile](Dockerfile)
- [deeptutor/api/run_server.py](deeptutor/api/run_server.py)
- [deeptutor_cli/main.py](deeptutor_cli/main.py)
- [requirements.txt](requirements.txt)
- [requirements/dev.txt](requirements/dev.txt)
- [requirements/math-animator.txt](requirements/math-animator.txt)
- [web/app/(workspace)/page.tsx](web/app/(workspace)/page.tsx)

</details>



This document provides a high-level guide for installing, deploying, and performing initial configuration of DeepTutor. It covers prerequisites, the primary installation methods (Docker and CLI-driven), and essential environment setup using the built-in initialization and launcher scripts.

For detailed Docker deployment instructions including multi-stage builds and supervisord configuration, see [Docker Deployment](#2.1). For a comprehensive guide to environment variables, YAML configs, and LLM provider setup, see [Configuration Guide](#2.2).

---

## Prerequisites

DeepTutor requires different dependencies depending on your deployment method. The system includes a `deeptutor init` command to help configure runtime files [deeptutor_cli/main.py:16-16]().

### Docker Deployment (Recommended)

| Requirement | Minimum Version | Purpose |
|------------|-----------------|---------|
| Docker | 20.10+ | Container runtime |
| Docker Compose | 2.0+ | Multi-container orchestration |
| Available Memory | 4GB+ | Running both frontend and backend |

### Manual Installation

| Requirement | Minimum Version | Purpose |
|------------|-----------------|---------|
| Python | 3.11 | Backend runtime [Dockerfile:63-63](), [requirements.txt:4-4]() |
| Node.js | 22 | Frontend build and runtime [Dockerfile:23-23](), [Dockerfile:58-58]() |
| npm | Latest | Frontend package management [Dockerfile:143-145]() |
| Rust/Cargo | Latest | Required for building `tiktoken` and vision packages [Dockerfile:89-92]() |
| System Libs | - | `libgl1`, `libglib2.0-0` for OpenCV and vision [Dockerfile:127-138]() |

**Sources:** [Dockerfile:23-138](), [requirements.txt:4-4](), [deeptutor_cli/main.py:16-16]()

---

## Installation Architecture Overview

The following diagram maps the installation and startup process to the scripts and entities within the codebase.

### Deployment Flow: Natural Language to Code Entity

```mermaid
graph TB
    subgraph "Configuration_Layer"
        ["deeptutor_init"] -- "register_init" --> ["deeptutor_cli.init_cmd"]
        ["pyproject.toml"] -- "defines_extras" --> ["pip_install"]
    end

    subgraph "Docker_Deployment"
        ["Dockerfile"] -- "multi_stage_build" --> ["production_stage"]
        ["supervisord"] -- "spawn" --> ["start-backend.sh"]
        ["supervisord"] -- "spawn" --> ["web/server.js"]
    end

    subgraph "CLI_Runtime"
        ["deeptutor_start"] -- "calls" --> ["deeptutor.runtime.launcher:start"]
        ["deeptutor_serve"] -- "calls" --> ["deeptutor.api.main:app"]
        ["deeptutor_chat"] -- "REPL" --> ["deeptutor_cli.chat:register"]
    end

    subgraph "Data_Persistence"
        ["data/user/workspace"]
        ["data/knowledge_bases"]
        ["data/memory"]
    end

    ["start-backend.sh"] -- "exec" --> ["deeptutor.api.main:app"]
    ["deeptutor.api.main:app"] -- "io" --> ["data/user/workspace"]
```

**Sources:** [deeptutor_cli/main.py:113-162](), [Dockerfile:103-187](), [requirements.txt:1-20](), [deeptutor_cli/main.py:12-24]()

---

## Step 1: Repository Setup

Clone the repository and prepare the environment. The `deeptutor` CLI provides a unified interface for setup and execution via `typer` [deeptutor_cli/main.py:29-34]().

```bash
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Recommended: Setup virtual environment and install
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[all]"
```

The system uses `RunMode` to distinguish between `CLI` and `SERVER` execution paths [deeptutor_cli/main.py:26-26](), [deeptutor/api/run_server.py:40-40](). For contributors, ensure you follow the branching strategy, targeting `dev` for general features and `multi-user` for tenant-related isolation [CONTRIBUTING.md:32-60]().

**Sources:** [deeptutor_cli/main.py:26-34](), [CONTRIBUTING.md:32-60](), [CONTRIBUTING.md:98-109](), [requirements.txt:11-18]()

---

## Step 2: Essential Configuration

DeepTutor requires configuration for LLM and Embedding providers. Initial runtime settings are created under `data/user/settings` on the first start [Dockerfile:13-13]().

### Directory Structure and Persistence

The system initializes a structured `data/` directory for persistence, which is typically excluded from version control [Dockerfile:167-181](), [.gitignore:8-13]().

| Directory | Code Reference | Purpose |
|-----------|----------------|---------|
| `data/user/settings` | [Dockerfile:168-168]() | Configuration and provider profiles |
| `data/knowledge_bases` | [Dockerfile:181-181]() | Vector stores and RAG documents |
| `data/memory` | [Dockerfile:169-169]() | Lightweight persistent memory |
| `data/user/workspace/chat` | [Dockerfile:174-174]() | Session-specific chat data |

**Sources:** [Dockerfile:167-181](), [.gitignore:8-13]()

---

## Step 3: Deployment Methods

### Option A: Docker (Production)
The `Dockerfile` uses a multi-stage build to produce a production-ready image [Dockerfile:1-15]().
1. **frontend-builder**: Builds Next.js in `standalone` mode [Dockerfile:23-50]().
2. **python-base**: Installs system dependencies (OpenCV, Rust) and Python requirements [Dockerfile:63-98]().
3. **production**: Combines the platform-matched Node runtime with the Python environment, managed by `supervisord` [Dockerfile:103-187]().

To start:
```bash
docker build -t deeptutor:local .
docker run -p 3782:3782 -p 8001:8001 -v deeptutor-data:/app/data deeptutor:local
```
**Sources:** [Dockerfile:1-187]()

### Option B: Manual / CLI (Development)
For development, you can start the backend and frontend together using the CLI `start` command [deeptutor_cli/main.py:113-121]().

```bash
# Launch both backend and frontend
deeptutor start

# Or start just the API server
deeptutor serve --reload
```

The `serve` command automatically switches the system to `RunMode.SERVER` [deeptutor_cli/main.py:133-133]() and launches `uvicorn` [deeptutor_cli/main.py:154-160]().

**Sources:** [deeptutor_cli/main.py:113-160](), [deeptutor/api/run_server.py:30-69]()

---

## System Component Mapping

```mermaid
graph LR
    subgraph "Client_Space"
        ["Browser_UI"]
        ["deeptutor_chat_REPL"]
    end

    subgraph "Application_Runtime"
        ["Next.js_Frontend"]
        ["FastAPI_Backend"]
        ["RunMode_SERVER"]
        ["RunMode_CLI"]
    end

    subgraph "Data_Persistence"
        ["data/memory"]
        ["data/knowledge_bases"]
        ["data/user/workspace/chat"]
    end

    ["Browser_UI"] -- "HTTP" --> ["Next.js_Frontend"]
    ["Next.js_Frontend"] -- "API" --> ["FastAPI_Backend"]
    ["deeptutor_chat_REPL"] -- "Local_Invoke" --> ["RunMode_CLI"]
    ["FastAPI_Backend"] -- "Storage" --> ["data/user/workspace/chat"]
```

**Sources:** [deeptutor_cli/main.py:26-27](), [deeptutor/api/run_server.py:40-41](), [Dockerfile:167-181](), [web/app/(workspace)/page.tsx:10-30]()
