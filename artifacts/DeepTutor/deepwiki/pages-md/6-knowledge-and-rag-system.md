# Knowledge and RAG System

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [deeptutor/knowledge/initializer.py](deeptutor/knowledge/initializer.py)
- [deeptutor/knowledge/manager.py](deeptutor/knowledge/manager.py)
- [deeptutor/services/rag/service.py](deeptutor/services/rag/service.py)
- [tests/knowledge/test_manager_get_info_status.py](tests/knowledge/test_manager_get_info_status.py)

</details>



The Knowledge and Retrieval-Augmented Generation (RAG) system in DeepTutor provides the infrastructure for managing persistent educational content and retrieving relevant information to augment LLM reasoning. It bridges the gap between static documents (PDFs, text, code) and agentic workflows by providing a unified interface for indexing, querying, and managing knowledge bases.

### System Overview

The system is built around the `KnowledgeBaseManager`, which coordinates multiple knowledge bases (KBs) stored on disk [deeptutor/knowledge/manager.py:196-201](). It manages metadata and configuration through a central `kb_config.json` file [deeptutor/knowledge/manager.py:204-205](). Retrieval operations are abstracted through the `RAGService`, which provides a high-level API for initialization, document addition, and searching [deeptutor/services/rag/service.py:18-47]().

#### High-Level Architecture

The following diagram illustrates how the Knowledge and RAG system connects Natural Language queries to the underlying Code Entities and storage.

**Knowledge Retrieval Flow**
```mermaid
graph TD
    subgraph "Natural Language Space"
        UserQuery["User Query / Agent Prompt"]
        RetrievedContext["Ranked Context Chunks"]
    end

    subgraph "Code Entity Space"
        [KBM]KnowledgeBaseManager
        [RAGS]RAGService
        [LIP]LlamaIndexPipeline
        [SR]SmartRetriever
        [KBI]KnowledgeBaseInitializer
    end

    subgraph "Storage Layer"
        [KB_CONFIG]kb_config.json
        [DOCSTORE]docstore.json
        [VERSION_DIR]version-N/
        [RAW_DIR]raw/
    end

    UserQuery --> RAGS
    RAGS --> LIP
    RAGS --> SR
    LIP --> VERSION_DIR
    VERSION_DIR --> DOCSTORE
    DOCSTORE --> RetrievedContext
    KBI --> RAW_DIR
    KBM -.-> KB_CONFIG
    VERSION_DIR -.-> KB_CONFIG
```
**Sources:** [deeptutor/knowledge/manager.py:196-205](), [deeptutor/services/rag/service.py:18-47](), [deeptutor/knowledge/initializer.py:37-47](), [deeptutor/services/rag/service.py:195-201]()

---

## 6.1 RAG System

The RAG system provides grounded context to agents by querying indexed knowledge bases. The primary entry point is the `RAGService`, which delegates operations to a specific backend pipeline, defaulting to LlamaIndex [deeptutor/services/rag/service.py:18-21]().

Key features include:
*   **Unified Search API**: A standard interface for querying knowledge bases that handles logging and tool event emission via `_emit_tool_event` [deeptutor/services/rag/service.py:61-87]().
*   **Smart Retrieval**: The `smart_retrieve` method enhances basic search by using LLM-generated query hints to perform multi-pass retrieval for complex contexts [deeptutor/services/rag/service.py:195-201]().
*   **Memory Integration**: Search operations automatically emit L1 memory trace events using `TraceEvent.new("kb", "query", ...)` to track knowledge usage [deeptutor/services/rag/service.py:126-140]().
*   **Pipeline Factory**: The system uses `get_pipeline` to instantiate specific RAG providers based on the environment configuration [deeptutor/services/rag/factory.py:13-20]().

For details, see [RAG System](#6.1).

**Sources:** [deeptutor/services/rag/service.py:18-144](), [deeptutor/services/rag/service.py:195-201](), [deeptutor/services/rag/factory.py:13-20]()

---

## 6.2 Knowledge Base Management

Knowledge Base Management handles the lifecycle of document collections, including initialization, status tracking, and re-indexing. The `KnowledgeBaseInitializer` sets up the directory structure and metadata [deeptutor/knowledge/initializer.py:107-128](), while the `KnowledgeBaseManager` maintains the consistency of KBs on disk [deeptutor/knowledge/manager.py:196-201]().

**KB Processing Pipeline**
```mermaid
graph LR
    [Files]Input_Files --> [KBI_CD]KnowledgeBaseInitializer.copy_documents
    [KBI_CD] --> [RAGS_I]RAGService.initialize
    [RAGS_I] --> [LIP_I]LlamaIndexPipeline.initialize
    [LIP_I] --> [KBM_U]KnowledgeBaseManager.update_kb_status
    [KBM_U] --> [KB_CONFIG]kb_config.json
    [KBM_U] --> [KB_DIR]/data/knowledge_bases/kb_name/
```
**Sources:** [deeptutor/knowledge/initializer.py:130-141](), [deeptutor/services/rag/service.py:49-52](), [deeptutor/knowledge/manager.py:196-205](), [tests/knowledge/test_manager_get_info_status.py:77-86]()

The system implements robust reconciliation logic in `_reconcile_embedding_flags` to detect when an index is stale due to changes in embedding models or dimensions [deeptutor/knowledge/manager.py:108-133](). It also features a status promotion mechanism that recovers KBs from `processing` or `initializing` to `ready` if the underlying index is finalized but the config was not updated [tests/knowledge/test_manager_get_info_status.py:8-11](). Stale orphans are pruned after a grace period defined by `_ORPHAN_PRUNE_GRACE_SECONDS` [deeptutor/knowledge/manager.py:31]().

For details, see [Knowledge Base Management](#6.2).

**Sources:** [deeptutor/knowledge/manager.py:31-193](), [deeptutor/knowledge/initializer.py:25-47](), [tests/knowledge/test_manager_get_info_status.py:68-97]()

---

## 6.3 Web Search and Other Tools

The knowledge system extends beyond local document indices to include external information sources and cross-platform file handling.

*   **File Routing**: The `FileTypeRouter` is used to collect and route supported files during KB initialization, ensuring only compatible extensions are processed [deeptutor/knowledge/initializer.py:156-157]().
*   **Cross-Platform Locking**: The manager utilizes `file_lock_shared` and `file_lock_exclusive` to ensure safe concurrent access to configuration files on both Windows (via `msvcrt`) and Unix (via `fcntl`) systems [deeptutor/knowledge/manager.py:53-95]().
*   **External Search**: The `RAGService` provides a unified entry point that can be extended via the `get_pipeline` factory to include various retrieval providers [deeptutor/services/rag/service.py:13-15]().
*   **Embedding Fingerprints**: The system tracks active embedding configurations using `_get_embedding_fingerprint` to ensure the vector index matches the current model [deeptutor/knowledge/manager.py:97-105]().

For details, see [Web Search and Other Tools](#6.3).

**Sources:** [deeptutor/knowledge/manager.py:53-105](), [deeptutor/knowledge/initializer.py:156-171](), [deeptutor/services/rag/service.py:13-15]()
