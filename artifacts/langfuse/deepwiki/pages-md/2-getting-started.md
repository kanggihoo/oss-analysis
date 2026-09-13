# Getting Started

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [.devcontainer/Dockerfile](.devcontainer/Dockerfile)
- [.dockerignore](.dockerignore)
- [.github/workflows/ci.yml.template](.github/workflows/ci.yml.template)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docker-compose.build.yml](docker-compose.build.yml)
- [docker-compose.dev-azure.yml](docker-compose.dev-azure.yml)
- [docker-compose.dev-redis-cluster.yml](docker-compose.dev-redis-cluster.yml)
- [docker-compose.dev.yml](docker-compose.dev.yml)
- [docker-compose.yml](docker-compose.yml)
- [packages/shared/clickhouse/scripts/down.sh](packages/shared/clickhouse/scripts/down.sh)
- [packages/shared/clickhouse/scripts/drop.sh](packages/shared/clickhouse/scripts/drop.sh)
- [packages/shared/clickhouse/scripts/up.sh](packages/shared/clickhouse/scripts/up.sh)
- [packages/shared/src/features/analytics-integrations/blob-export-gate.ts](packages/shared/src/features/analytics-integrations/blob-export-gate.ts)
- [scripts/codex/maintenance.sh](scripts/codex/maintenance.sh)
- [scripts/codex/setup.sh](scripts/codex/setup.sh)
- [turbo.json](turbo.json)
- [web/entrypoint.sh](web/entrypoint.sh)
- [web/src/__tests__/server/unit/assertLegacyBlobExportSourceAllowed.servertest.ts](web/src/__tests__/server/unit/assertLegacyBlobExportSourceAllowed.servertest.ts)
- [worker/entrypoint.sh](worker/entrypoint.sh)

</details>



This page is the entry point for developers setting up a local Langfuse development environment. It covers the prerequisites, the overall service topology, and points to sub-pages for detailed installation ([Installation & Setup](#2.1)), environment configuration ([Environment Configuration](#2.2)), and running services ([Running Services](#2.3)).

For background on what Langfuse is and how the system is architected, see [Overview](#1) and [System Architecture](#1.1). For the monorepo layout and package structure, see [Monorepo Structure](#1.2).

---

## Prerequisites

Before starting, ensure the following tools are installed and at the correct versions:

| Tool | Required Version | Notes |
|------|-----------------|-------|
| Node.js | 24 | Specified in `.nvmrc` and `CONTRIBUTING.md` [CONTRIBUTING.md:113]() |
| pnpm | 11.1.3 | Pinned version for the workspace [CONTRIBUTING.md:114](), [scripts/codex/setup.sh:22]() |
| Docker | Any recent version | Required to run the database and infrastructure locally [CONTRIBUTING.md:115]() |
| Clickhouse client | Latest | Required for manual database interaction [CONTRIBUTING.md:116]() |

The repository uses [pnpm](https://pnpm.io/) workspaces to manage dependencies [CONTRIBUTING.md:99](). You can also run the environment in a **GitHub Codespace** via the provided `.devcontainer` [CONTRIBUTING.md:118](), or an **OpenAI Codex** cloud environment using the provided bootstrap scripts `scripts/codex/setup.sh` [CONTRIBUTING.md:120-124]().

Sources: [CONTRIBUTING.md:111-124](), [scripts/codex/setup.sh:22](), [.devcontainer/Dockerfile:19]()

---

## Repository Overview

The codebase is a monorepo managed with `pnpm` and `turbo` [CONTRIBUTING.md:99]().

**Monorepo Package Dependency Graph:**

```mermaid
graph TB
    ["web"] -- "depends on" --> ["@langfuse/shared"]
    ["web"] -- "depends on" --> ["@langfuse/ee"]
    ["worker"] -- "depends on" --> ["@langfuse/shared"]
    ["@langfuse/ee"] -- "depends on" --> ["@langfuse/shared"]
    
    subgraph "Packages"
        ["@langfuse/shared"]
        ["@langfuse/ee"]
    end
    
    subgraph "Applications"
        ["web"]
        ["worker"]
    end
```

**Package Roles:**

| Package | Purpose | Key Technologies |
|---------|---------|------------------|
| `web` | Main application: Frontend, tRPC, and Public REST APIs [CONTRIBUTING.md:101]() | Next.js, NextAuth.js, tRPC, Prisma [CONTRIBUTING.md:45-48]() |
| `worker` | Asynchronous task processing and queue consumption [CONTRIBUTING.md:102]() | BullMQ, Node.js [CONTRIBUTING.md:69,71]() |
| `packages/shared` | Shared domain logic, Prisma schema, and DB contracts [CONTRIBUTING.md:104]() | Prisma, ClickHouse migrations [CONTRIBUTING.md:95,104]() |
| `ee` | Enterprise Edition features [CONTRIBUTING.md:107]() | Consumed by `web` and `worker` |

Sources: [CONTRIBUTING.md:45-52, 99-107](), [turbo.json:57-70]()

---

## Infrastructure Services

A local environment requires several infrastructure services. The dual-service architecture (Web and Worker) communicates with transactional and analytical databases.

**Development Environment Topology:**

```mermaid
flowchart TB
    subgraph "Local Node Processes"
        ["web_Next.js_Server"]
        ["worker_BullMQ_Processor"]
    end

    subgraph "Infrastructure (Docker Containers)"
        ["postgres_OLTP"]
        ["clickhouse_OLAP"]
        ["redis_Queue_Cache"]
        ["minio_S3_Storage"]
    end

    ["web_Next.js_Server"] --> ["postgres_OLTP"]
    ["web_Next.js_Server"] --> ["clickhouse_OLAP"]
    ["web_Next.js_Server"] --> ["redis_Queue_Cache"]
    ["web_Next.js_Server"] --> ["minio_S3_Storage"]
    
    ["worker_BullMQ_Processor"] --> ["postgres_OLTP"]
    ["worker_BullMQ_Processor"] --> ["clickhouse_OLAP"]
    ["worker_BullMQ_Processor"] --> ["redis_Queue_Cache"]
    ["worker_BullMQ_Processor"] --> ["minio_S3_Storage"]
```

**Service Details:**

| Service | Environment Variable | Purpose |
|---------|--------------------------|---------|
| `Postgres` | `DATABASE_URL` | OLTP: Transactional data (Users, Organizations, Projects) [CONTRIBUTING.md:70](), [docker-compose.yml:23]() |
| `Clickhouse` | `CLICKHOUSE_URL` | OLAP: Observability data (Traces, Observations, Scores) [CONTRIBUTING.md:72](), [docker-compose.yml:29]() |
| `Redis` | `REDIS_HOST` | Cache and `BullMQ` Queue management [CONTRIBUTING.md:71](), [docker-compose.yml:61]() |
| `Minio` | `LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT` | S3-compatible storage for raw events and media [CONTRIBUTING.md:73](), [docker-compose.yml:40]() |

Sources: [CONTRIBUTING.md:64-89](), [docker-compose.yml:6-154]()

---

## First-Run Quickstart

To initialize the development environment from scratch:

```bash
# 1. Install dependencies
pnpm install

# 2. Bootstrap infrastructure and databases
pnpm run dx
```

**What `pnpm run dx` Does:**
The `dx` script performs a full reset and bootstrap of the local environment. It prunes existing containers, resets PostgreSQL and ClickHouse databases, and seeds example data.

For subsequent sessions, use:
- `pnpm run dev`: Starts all services (Web + Worker) [turbo.json:35]().
- `pnpm run dev:web`: Starts only the Next.js application [turbo.json:45]().
- `pnpm run dev:worker`: Starts only the background worker [turbo.json:40]().

Sources: [turbo.json:35-49](), [CONTRIBUTING.md:155]()

---

## Key Scripts Reference

Orchestrated by Turbo, these scripts manage the lifecycle of the monorepo:

| Command | Action |
|---------|--------|
| `pnpm run db:generate` | Regenerates Prisma client based on the shared schema [turbo.json:52-56]() |
| `pnpm run db:migrate` | Deploys PostgreSQL migrations [turbo.json:17-19]() |
| `pnpm run db:seed` | Seeds the database with default data [turbo.json:29-31]() |
| `pnpm run typecheck` | Runs `tsc` across all packages in the workspace [turbo.json:77-82]() |
| `pnpm run lint` | Executes ESLint across the monorepo [turbo.json:71-76]() |

Sources: [turbo.json:1-104]()

---

## Sub-pages

| Page | Contents |
|------|----------|
| [Installation & Setup](#2.1) | Detailed prerequisites, dependency installation with pnpm, and initial database setup. |
| [Environment Configuration](#2.2) | Full documentation of environment variables for web and worker services, including DB URLs, Redis, and S3. |
| [Running Services](#2.3) | Instructions for starting services, running migrations, and seeding data. |
