# Samples and Demos

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [samples/enrichment/README.md](samples/enrichment/README.md)
- [toolbox/mdcode/demo/README.md](toolbox/mdcode/demo/README.md)

</details>



This section provides an overview of the practical applications, demonstration scripts, and sample workflows available in the Knowledge Catalog repository. These resources are designed to showcase the "Metadata as Code" (MaC) philosophy and the capabilities of the enrichment agents.

The repository organizes these resources into four primary areas:
1.  **Python Enrichment Samples**: End-to-end workflows for data asset augmentation using Python.
2.  **Discovery Agent Sample**: A semantic search agent implementation over Knowledge Catalog.
3.  **Toolbox Demos**: Scripted scenarios for the TypeScript-based `kcmd` tool.
4.  **Agent Demos**: Specialized scenarios for agent-integrated metadata management.

## Repository Demo Landscape

The following diagram maps the high-level demo components to their respective directories and the core `kcmd` functionality they exercise.

### Demo to Code Entity Mapping
```mermaid
graph TD
  subgraph "Samples Space"
    S1["samples/enrichment"]
    S2["samples/discovery"]
  end

  subgraph "Toolbox Space (TypeScript)"
    T1["toolbox/mdcode/demo/setup.ts"]
    T2["toolbox/mdcode/demo/update.ts"]
    T3["toolbox/mdcode/demo/cleanup.ts"]
  end

  subgraph "Code Entity Space"
    KCMD["kcmd CLI"]
    DS["BigQueryDatasetSource"]
    KB["KnowledgeBase / EntryGroupSource"]
    DL["DocumentsLayout"]
    SL["StandardLayout"]
    KCS["knowledge_catalog_search tool"]
  end

  S1 -- "Uses" --> KCMD
  S2 -- "Uses" --> KCS
  T1 -- "Prepares" --> DS
  T1 -- "Prepares" --> KB
  T2 -- "Exercises" --> SL
  T2 -- "Exercises" --> DL
```
**Sources:** [toolbox/mdcode/demo/README.md:1-172](), [samples/enrichment/README.md:1-90]()

---

## Python Enrichment Sample
The `samples/enrichment` directory contains a complete demonstration of how an agentic approach can be used to augment Knowledge Catalog metadata [samples/enrichment/README.md:8-12](). This sample focuses on BigQuery data assets and utilizes a multi-step workflow:

1.  **Environment Setup**: Configuration of GCP projects and Python virtual environments [samples/enrichment/README.md:21-45]().
2.  **Data Creation**: Scripted generation of sample BigQuery datasets using `create_data.py` [samples/enrichment/README.md:47-54]().
3.  **Lifecycle**: Execution of the `enrichment.download`, `enrichment.enrich`, and `enrichment.publish` modules to move metadata between the cloud and local YAML snapshots [samples/enrichment/README.md:56-89]().

For details, see [samples/enrichment: Python Enrichment Sample](#5.1).

**Sources:** [samples/enrichment/README.md:1-90]()

---

## Knowledge Catalog Discovery Agent
The `samples/discovery` agent demonstrates how to build a semantic search interface over Knowledge Catalog. It uses a specialized `knowledge_catalog_search` tool to query entries and predicates. This sample illustrates how to configure an agent with a `SKILL.md` file to interpret natural language queries about data governance and cataloged assets.

For details, see [samples/discovery: Knowledge Catalog Discovery Agent](#5.2).

---

## Toolbox kcmd Demos
Located in `toolbox/mdcode/demo/`, these scripts demonstrate the core functionality of the `kcmd` CLI tool [toolbox/mdcode/demo/README.md:1-2](). They provide a "batteries-included" way to test the Metadata as Code workflow across different resource types.

| Demo Scenario | Key Components Tested | Description |
| :--- | :--- | :--- |
| **BigQuery Dataset** | `StandardLayout`, `BigQueryDatasetSource` | Syncing BigQuery table metadata to local YAML files [toolbox/mdcode/demo/README.md:19-22](). |
| **Knowledge Base** | `DocumentsLayout`, `EntryGroupSource` | Managing Dataplex EntryGroups as a collection of Markdown files [toolbox/mdcode/demo/README.md:70-73](). |
| **OKF Wiki** | `DocumentsLayout`, `okf/catalog/` | Publishing an Open Knowledge Format bundle into a Knowledge Catalog [toolbox/mdcode/demo/README.md:121-130](). |

### kcmd Demo Workflow
```mermaid
sequenceDiagram
  participant Dev as Developer
  participant Local as Local Workspace (catalog.yaml)
  participant GCP as Knowledge Catalog (Dataplex)

  Note over Dev, GCP: Setup Phase (setup.ts)
  Dev->>GCP: Create Resources (BQ/EntryGroup) [toolbox/mdcode/demo/README.md:25-30]()
  Dev->>Local: Initialize catalog.yaml [toolbox/mdcode/demo/README.md:31-32]()

  Note over Dev, GCP: Sync Phase (kcmd)
  Dev->>Local: kcmd pull [toolbox/mdcode/demo/README.md:39-40]()
  GCP-->>Local: Download Metadata
  Dev->>Local: update.ts (Modify local files) [toolbox/mdcode/demo/README.md:50-51]()
  Dev->>Local: kcmd push [toolbox/mdcode/demo/README.md:59-60]()
  Local->>GCP: Update Cloud Metadata
```
**Sources:** [toolbox/mdcode/demo/README.md:1-172]()

For details, see [toolbox/mdcode Demos: BigQuery and Knowledge Base](#5.3).

---

## Agent mdcode Demos
The `agents/mdcode/demo/` directory contains demos specifically tailored for use with the agent-integrated build of the metadata tools. These demos highlight the interaction between the `kcmd` core and the enrichment agents, often showcasing how agents can automatically generate the updates that are then pushed via the CLI. These differ from toolbox demos by utilizing the Python-based agent runner environment.

For details, see [agents/mdcode Demos](#5.4).

**Sources:** [toolbox/mdcode/demo/README.md:1-172]()
