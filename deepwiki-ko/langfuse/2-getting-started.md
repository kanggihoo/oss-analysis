---
type: deepwiki-translation
repo: langfuse
source: artifacts/langfuse/deepwiki/pages-md/2-getting-started.md
deepwiki_url: https://deepwiki.com/langfuse/langfuse/2-getting-started
section: "2"
order: 5
---

# 시작하기

<details>
<summary>관련 소스 파일</summary>

다음 파일들은 이 위키 페이지를 생성하기 위한 컨텍스트로 사용되었습니다.

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



이 페이지는 로컬 Langfuse 개발 환경을 설정하는 개발자를 위한 진입점입니다. prerequisite, 전체 service topology를 다루며, 자세한 설치([Installation & Setup](#2.1)), 환경 구성([Environment Configuration](#2.2)), 서비스 실행([Running Services](#2.3)을 위한 하위 페이지를 안내합니다.

Langfuse가 무엇인지와 시스템이 어떻게 설계되었는지에 대한 배경은 [Overview](#1)와 [System Architecture](#1.1)를 참조하세요. monorepo layout과 package structure는 [Monorepo Structure](#1.2)를 참조하세요.

---

## Prerequisites

시작하기 전에 다음 tool이 설치되어 있고 올바른 version인지 확인하세요.

| Tool | Required Version | Notes |
|------|-----------------|-------|
| Node.js | 24 | `.nvmrc`와 `CONTRIBUTING.md`에 명시됨 [CONTRIBUTING.md:113]() |
| pnpm | 11.1.3 | workspace에 고정된 version [CONTRIBUTING.md:114](), [scripts/codex/setup.sh:22]() |
| Docker | 최신 version이면 무관 | database와 infrastructure를 로컬에서 실행하는 데 필요 [CONTRIBUTING.md:115]() |
| Clickhouse client | Latest | 수동 database 상호작용에 필요 [CONTRIBUTING.md:116]() |

repository는 dependency 관리를 위해 [pnpm](https://pnpm.io/) workspace를 사용합니다 [CONTRIBUTING.md:99](). 제공된 `.devcontainer`를 통해 **GitHub Codespace**에서 환경을 실행할 수도 있고 [CONTRIBUTING.md:118](), 제공된 bootstrap script `scripts/codex/setup.sh`를 사용해 **OpenAI Codex** cloud environment에서 실행할 수도 있습니다 [CONTRIBUTING.md:120-124]().

출처: [CONTRIBUTING.md:111-124](), [scripts/codex/setup.sh:22](), [.devcontainer/Dockerfile:19]()

---

## Repository Overview

codebase는 `pnpm`과 `turbo`로 관리되는 monorepo입니다 [CONTRIBUTING.md:99]().

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

**Package 역할:**

| Package | Purpose | Key Technologies |
|---------|---------|------------------|
| `web` | Main application: Frontend, tRPC, Public REST API [CONTRIBUTING.md:101]() | Next.js, NextAuth.js, tRPC, Prisma [CONTRIBUTING.md:45-48]() |
| `worker` | 비동기 task processing 및 queue consumption [CONTRIBUTING.md:102]() | BullMQ, Node.js [CONTRIBUTING.md:69,71]() |
| `packages/shared` | 공유 domain logic, Prisma schema, DB contract [CONTRIBUTING.md:104]() | Prisma, ClickHouse migrations [CONTRIBUTING.md:95,104]() |
| `ee` | Enterprise Edition 기능 [CONTRIBUTING.md:107]() | `web` 및 `worker`에서 사용됨 |

출처: [CONTRIBUTING.md:45-52, 99-107](), [turbo.json:57-70]()

---

## Infrastructure Services

로컬 환경에는 여러 infrastructure service가 필요합니다. 이중 서비스 아키텍처(Web 및 Worker)는 transactional database 및 analytical database와 통신합니다.

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
| `Postgres` | `DATABASE_URL` | OLTP: Transactional data(User, Organization, Project) [CONTRIBUTING.md:70](), [docker-compose.yml:23]() |
| `Clickhouse` | `CLICKHOUSE_URL` | OLAP: Observability data(Trace, Observation, Score) [CONTRIBUTING.md:72](), [docker-compose.yml:29]() |
| `Redis` | `REDIS_HOST` | Cache 및 `BullMQ` Queue management [CONTRIBUTING.md:71](), [docker-compose.yml:61]() |
| `Minio` | `LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT` | raw event와 media를 위한 S3-compatible storage [CONTRIBUTING.md:73](), [docker-compose.yml:40]() |

출처: [CONTRIBUTING.md:64-89](), [docker-compose.yml:6-154]()

---

## First-Run Quickstart

개발 환경을 처음부터 초기화하려면:

```bash
# 1. Install dependencies
pnpm install

# 2. Bootstrap infrastructure and databases
pnpm run dx
```

**`pnpm run dx`가 수행하는 작업:**
`dx` script는 로컬 환경의 full reset 및 bootstrap을 수행합니다. 기존 container를 prune하고 PostgreSQL 및 ClickHouse database를 reset하며 example data를 seed합니다.

이후 session에서는 다음을 사용하세요.
- `pnpm run dev`: 모든 service(Web + Worker)를 시작합니다 [turbo.json:35]().
- `pnpm run dev:web`: Next.js application만 시작합니다 [turbo.json:45]().
- `pnpm run dev:worker`: background worker만 시작합니다 [turbo.json:40]().

출처: [turbo.json:35-49](), [CONTRIBUTING.md:155]()

---

## Key Scripts Reference

Turbo로 orchestrate되는 이 script들은 monorepo의 lifecycle을 관리합니다.

| Command | Action |
|---------|--------|
| `pnpm run db:generate` | 공유 schema를 기반으로 Prisma client를 재생성합니다 [turbo.json:52-56]() |
| `pnpm run db:migrate` | PostgreSQL migration을 배포합니다 [turbo.json:17-19]() |
| `pnpm run db:seed` | database에 default data를 seed합니다 [turbo.json:29-31]() |
| `pnpm run typecheck` | workspace의 모든 package에서 `tsc`를 실행합니다 [turbo.json:77-82]() |
| `pnpm run lint` | monorepo 전체에서 ESLint를 실행합니다 [turbo.json:71-76]() |

출처: [turbo.json:1-104]()

---

## 하위 페이지

| Page | Contents |
|------|----------|
| [Installation & Setup](#2.1) | 자세한 prerequisite, pnpm을 사용한 dependency installation, initial database setup. |
| [Environment Configuration](#2.2) | DB URL, Redis, S3를 포함한 web 및 worker service용 environment variable 전체 문서. |
| [Running Services](#2.3) | service 시작, migration 실행, data seeding에 대한 instruction. |
