# Overview

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [LICENSE.md](LICENSE.md)
- [README.md](README.md)
- [samples/README.md](samples/README.md)
- [toolbox/README.md](toolbox/README.md)
- [toolbox/mdcode/src/libts/gcp/context.ts](toolbox/mdcode/src/libts/gcp/context.ts)
- [toolbox/mdcode/src/libts/tsconfig.json](toolbox/mdcode/src/libts/tsconfig.json)

</details>



[Knowledge Catalog](https://cloud.google.com/products/knowledge-catalog) (formerly Dataplex) is an AI-powered data catalog and metadata management platform [README.md:1-3](). It provides a dynamic knowledge graph of structured and unstructured data to provide business context for AI agents [README.md:3-5]().

This repository contains tools, agents, and samples designed to demonstrate Knowledge Catalog features and facilitate building context management, enrichment, and retrieval solutions [README.md:5-6]().

## Purpose and Scope

The repository serves as a technical foundation for implementing **Metadata as Code (MaC)** and **Agentic Enrichment** workflows. It enables engineers to:
*   Manage metadata as version-controlled source code artifacts [toolbox/README.md:5-7]().
*   Automate the generation and maintenance of documentation for data assets using LLMs [toolbox/README.md:9-12]().
*   Synchronize local metadata workspaces with the Google Cloud Knowledge Catalog service [toolbox/README.md:6-7]().

For foundational definitions and a guide to the data model, see [Core Concepts: Metadata as Code and Knowledge Catalog](#1.2).

## System Architecture

The repository is divided into several major components that bridge the gap between raw data assets (like BigQuery tables) and enriched, AI-ready metadata.

### High-Level Component Relationship

The following diagram illustrates how the core tools interact with Google Cloud and the local development environment.

**System Component Map**
```mermaid
graph TD
    subgraph "LocalWorkspace" ["Local Workspace (Code Entity Space)"]
        [kcmd_CLI] --> [CatalogSnapshot]
        [CatalogSnapshot] --> [Local_YAML_Files]
        [Local_YAML_Files] -.-> [Git_VCS]
    end

    subgraph "EnrichmentLayer" ["Enrichment Layer"]
        [Enrichment_Agents] -- "Updates" --> [Local_YAML_Files]
    end

    subgraph "GoogleCloud" ["Google Cloud (Service Space)"]
        [CatalogClient] -- "gRPC/REST" --> [Dataplex_API]
        [Dataplex_API] -- "Indexes" --> [BigQuery_Assets]
    end

    [kcmd_CLI] -- "Uses" --> [CatalogClient]
    [ApiContext] -- "Provides_Auth" --> [CatalogClient]
```
Sources: [README.md:1-6](), [toolbox/README.md:1-13](), [toolbox/mdcode/src/libts/gcp/context.ts:10-47]()

### Data and Metadata Flow

The diagram below shows how the `ApiContext` and `CatalogClient` bridge the local environment to the cloud services.

**Service Integration Diagram**
```mermaid
graph LR
    subgraph "Local_Runtime" ["Local Runtime"]
        [ApiContext_default] -- "execSync" --> [gcloud_CLI]
        [ApiContext_default] -- "populates" --> [ApiContext_instance]
    end

    subgraph "Metadata_Pipeline" ["Metadata Pipeline"]
        [kcmd] -- "calls" --> [CatalogClient]
        [ApiContext_instance] -- "auth_token" --> [CatalogClient]
        [CatalogClient] -- "HTTPS_Request" --> [Dataplex_Service]
    end
```
Sources: [toolbox/mdcode/src/libts/gcp/context.ts:31-47](), [toolbox/README.md:5-7]()

## Major Components

### 1. kcmd: Metadata as Code
The `kcmd` tool (located in `toolbox/mdcode`) is the primary interface for managing metadata. It treats catalog entries (like table descriptions and schemas) as code artifacts.
*   **Synchronization:** Supports pulling metadata from GCP to local YAML files and pushing local changes back to the catalog [toolbox/README.md:5-7]().
*   **Authentication:** Uses `ApiContext` to wrap `gcloud` commands for project, location, and token management via `cp.execSync` [toolbox/mdcode/src/libts/gcp/context.ts:10-47]().

### 2. Enrichment Agents
The repository provides ready-to-use agents to produce and evolve metadata. These agents use LLMs to analyze data assets and generate semantic descriptions [toolbox/README.md:9-12]().
*   **Python Agent:** Located in `agents/enrichment`, it supports multi-stage pipelines for summarization and relevance routing.
*   **TypeScript Agent:** Located in `toolbox/enrichment`, providing a harness for metadata maintenance [toolbox/README.md:9-12]().

### 3. Open Knowledge Format (OKF)
A vendor-neutral specification for structuring knowledge bundles, located in `okf/`. It defines how documentation, concepts, and logs should be organized to ensure interoperability between different AI agents and catalogs.

### 4. Samples and Demos
Practical implementations of the tools:
*   **Discovery:** Building search and discovery agents on top of the Search APIs offered by the catalog [samples/README.md:6-9]().
*   **Enrichment Workflow:** Demonstrates agents that generate and enrich documentation for assets managed in the catalog [samples/README.md:11-14]().

## Repository Structure

The codebase is organized by language and functional area. For a detailed breakdown of the directory layout and instructions on how to set up your environment, see [Repository Structure and Getting Started](#1.1).

| Directory | Description |
| :--- | :--- |
| `agents/` | Python-based enrichment agents and LLM pipelines. |
| `toolbox/` | TypeScript tools including `kcmd` (Metadata as Code) and the `kcagent` [toolbox/README.md:1-13](). |
| `okf/` | Open Knowledge Format specification and reference agents. |
| `samples/` | Demonstrations of search, discovery, and enrichment workflows [samples/README.md:1-15](). |

Sources: [toolbox/README.md:1-13](), [samples/README.md:1-15](), [README.md:5-6]()

## Getting Started

To begin working with the repository:
1.  **Authentication:** Ensure the Google Cloud CLI is configured. The `ApiContext` class relies on `gcloud config get-value` and `gcloud auth application-default print-access-token` [toolbox/mdcode/src/libts/gcp/context.ts:6-42]().
2.  **Environment:** Follow the setup steps in the specific tool directories (e.g., `toolbox/mdcode` for TypeScript or `agents/enrichment` for Python).
3.  **Contribution:** Review the [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests. All submissions require review via GitHub pull requests [CONTRIBUTING.md:27-32]().

For detailed setup instructions, see [Repository Structure and Getting Started](#1.1).
