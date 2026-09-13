# Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.devcontainer/Dockerfile](.devcontainer/Dockerfile)
- [.github/workflows/ci.yml.template](.github/workflows/ci.yml.template)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [README.cn.md](README.cn.md)
- [README.ja.md](README.ja.md)
- [README.kr.md](README.kr.md)
- [README.md](README.md)
- [ee/package.json](ee/package.json)
- [package.json](package.json)
- [packages/config-eslint/package.json](packages/config-eslint/package.json)
- [packages/shared/package.json](packages/shared/package.json)
- [packages/shared/src/constants/VERSION.ts](packages/shared/src/constants/VERSION.ts)
- [packages/shared/src/features/analytics-integrations/blob-export-gate.ts](packages/shared/src/features/analytics-integrations/blob-export-gate.ts)
- [pnpm-lock.yaml](pnpm-lock.yaml)
- [pnpm-workspace.yaml](pnpm-workspace.yaml)
- [scripts/codex/maintenance.sh](scripts/codex/maintenance.sh)
- [scripts/codex/setup.sh](scripts/codex/setup.sh)
- [turbo.json](turbo.json)
- [web/Dockerfile](web/Dockerfile)
- [web/package.json](web/package.json)
- [web/src/__tests__/server/unit/assertLegacyBlobExportSourceAllowed.servertest.ts](web/src/__tests__/server/unit/assertLegacyBlobExportSourceAllowed.servertest.ts)
- [web/src/components/layouts/routes.tsx](web/src/components/layouts/routes.tsx)
- [web/src/components/nav/book-a-call-button.tsx](web/src/components/nav/book-a-call-button.tsx)
- [web/src/components/nav/sidebar-notifications.clienttest.tsx](web/src/components/nav/sidebar-notifications.clienttest.tsx)
- [web/src/components/nav/sidebar-notifications.tsx](web/src/components/nav/sidebar-notifications.tsx)
- [web/src/constants/VERSION.ts](web/src/constants/VERSION.ts)
- [web/src/features/command-k-menu/CommandMenu.tsx](web/src/features/command-k-menu/CommandMenu.tsx)
- [web/src/features/command-k-menu/CommandMenuProvider.tsx](web/src/features/command-k-menu/CommandMenuProvider.tsx)
- [web/src/features/telemetry/README.md](web/src/features/telemetry/README.md)
- [worker/Dockerfile](worker/Dockerfile)
- [worker/package.json](worker/package.json)
- [worker/src/constants/VERSION.ts](worker/src/constants/VERSION.ts)
- [worker/src/index.ts](worker/src/index.ts)

</details>



Langfuse is an open-source LLM (Large Language Model) engineering platform designed to help teams collaboratively develop, monitor, evaluate, and debug AI applications. It provides a unified interface for capturing traces of LLM interactions, managing prompts, performing automated evaluations (LLM-as-a-judge), and tracking costs and latency across complex LLM chains. [README.md:80-98]()

This document introduces the system architecture, monorepo organization, and technology stack. For detailed technical deep-dives, see the following child pages:
- [System Architecture](#1.1) — Details on the web/worker dual-service model and data persistence layers.
- [Monorepo Structure](#1.2) — Overview of the `pnpm` workspace, shared internal packages, and the AI agent skills system.
- [Technology Stack](#1.3) — Comprehensive list of core frameworks and libraries.

---

## System Architecture

Langfuse follows a distributed architecture centered around two primary services and a specialized data layer designed for both transactional and analytical workloads.

1.  **Web Service** (`web/`): A Next.js application that handles the user interface, internal tRPC APIs, and the public REST API for SDK ingestion. [web/package.json:2-130]()
2.  **Worker Service** (`worker/`): A dedicated Node.js service for background tasks, including ingestion processing, evaluation execution, and data maintenance jobs using BullMQ. [worker/package.json:2-50]()

### High-Level Architecture Diagram

This diagram maps system components to their respective code entities and data stores.

```mermaid
graph TB
    subgraph "External"
        SDK["Langfuse SDKs<br/>(Python/JS)"]
        Browser["Web UI<br/>(React/Next.js)"]
    end
    
    subgraph "Web_Service_[web/]"
        NextSrv["next_start<br/>(web/package.json)"]
        PublicAPI["/api/public/*<br/>(REST_API)"]
        InternalAPI["appRouter<br/>(tRPC)"]
        Auth["NextAuth.js<br/>(next-auth)"]
    end
    
    subgraph "Worker_Service_[worker/]"
        WorkerSrv["node_dist/index.js<br/>(worker/src/index.ts)"]
        QueueProcessor["BullMQ_Workers<br/>(bullmq)"]
    end
    
    subgraph "Persistence_Layer"
        Postgres[("PostgreSQL<br/>(@prisma/client)")]
        ClickHouse[("ClickHouse<br/>(@clickhouse/client)")]
        Redis[("Redis<br/>(ioredis)")]
        S3[("S3_/_Blob_Storage<br/>(@aws-sdk/client-s3)")]
    end

    SDK -->|Ingestion| PublicAPI
    Browser -->|UI_Interaction| InternalAPI
    InternalAPI --> Auth
    
    PublicAPI --> S3
    PublicAPI --> Redis
    
    Redis --> QueueProcessor
    QueueProcessor --> ClickHouse
    QueueProcessor --> Postgres
    
    InternalAPI --> ClickHouse
    InternalAPI --> Postgres
```

**Sources**: [web/package.json:1-170](), [worker/package.json:1-92](), [packages/shared/package.json:1-122](), [web/Dockerfile:141-171]()

For more details on service interaction and data flow, see [System Architecture](#1.1).

---

## Monorepo Structure

Langfuse is organized as a monorepo using `pnpm` workspaces and `turbo` for build orchestration. This allows for shared logic and type definitions across the web and worker services. [package.json:100-101](), [package.json:51]()

### Workspace Organization

| Package | Path | Role |
| :--- | :--- | :--- |
| **Web** | `web/` | Next.js frontend and API server. [web/package.json:2-3]() |
| **Worker** | `worker/` | Background task processor using BullMQ. [worker/package.json:2-3]() |
| **Shared** | `packages/shared/` | Core logic, Prisma schemas, and ClickHouse scripts. [packages/shared/package.json:2-3]() |
| **EE** | `ee/` | Enterprise features (e.g., advanced SSO, ingestion masking). [ee/package.json:2-3]() |

### Code Dependency Diagram

This diagram illustrates the internal dependency graph between workspace members.

```mermaid
graph LR
    subgraph "Applications"
        Web["web/"]
        Worker["worker/"]
    end
    
    subgraph "Core_Packages"
        Shared["@langfuse/shared"]
        EE["@langfuse/ee"]
    end
    
    subgraph "Config_Packages"
        ESLint["@repo/eslint-config"]
        TSConfig["@repo/typescript-config"]
    end

    Web --> Shared
    Web --> EE
    Worker --> Shared
    EE --> Shared
    
    Web -.-> ESLint
    Worker -.-> ESLint
    Shared -.-> ESLint
    Web -.-> TSConfig
    Worker -.-> TSConfig
```

**Sources**: [package.json:1-51](), [web/package.json:51-52](), [worker/package.json:35](), [packages/shared/package.json:1-3](), [pnpm-lock.yaml:52-163]()

For a detailed breakdown of shared packages and the `.agents/` AI agent skills system, see [Monorepo Structure](#1.2).

---

## Technology Stack

Langfuse utilizes a modern TypeScript stack optimized for high-throughput data ingestion and complex analytical queries.

### Core Technologies

*   **Runtime**: Node.js 24 [package.json:8]()
*   **Frontend**: Next.js 16.2.6, React 19.2.4, Tailwind CSS [web/package.json:133-146]()
*   **API**: tRPC (internal), REST (public), Model Context Protocol (MCP) [web/package.json:102-105](), [web/package.json:54]()
*   **Database (Transactional)**: PostgreSQL with Prisma ORM 6.19.3 [packages/shared/package.json:104]()
*   **Database (Analytical)**: ClickHouse for trace and observation storage [packages/shared/package.json:95]()
*   **Queuing**: BullMQ 5.76.3 backed by Redis [packages/shared/package.json:114]()
*   **Observability**: OpenTelemetry, Sentry, and Datadog (optional) [web/package.json:56-69](), [web/package.json:95]()

**Sources**: [web/package.json:30-169](), [worker/package.json:31-69](), [packages/shared/package.json:87-135]()

For the full list of libraries and tools, see [Technology Stack](#1.3).

---

## Version Information

Langfuse maintains synchronized versions across its core services.

*   **Current Version**: `v3.175.0` [web/src/constants/VERSION.ts:1](), [worker/src/constants/VERSION.ts:1]()
*   **Release Tooling**: `release-it` is used to manage versioning and GitHub releases, updating files across `packages/shared`, `web`, and `worker`. [package.json:53-95]()

**Sources**: [package.json:3](), [web/src/constants/VERSION.ts:1](), [worker/src/constants/VERSION.ts:1]()
