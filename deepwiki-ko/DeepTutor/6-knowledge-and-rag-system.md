---
type: deepwiki-translation
repo: DeepTutor
source: artifacts/DeepTutor/deepwiki/pages-md/6-knowledge-and-rag-system.md
deepwiki_url: https://deepwiki.com/HKUDS/DeepTutor/6-knowledge-and-rag-system
section: "6"
order: 27
---

# 지식 및 RAG 시스템

<details>
<summary>관련 소스 파일</summary>

다음 파일들이 이 wiki 페이지를 생성할 때 맥락으로 사용되었습니다:

- [deeptutor/knowledge/initializer.py](deeptutor/knowledge/initializer.py)
- [deeptutor/knowledge/manager.py](deeptutor/knowledge/manager.py)
- [deeptutor/services/rag/service.py](deeptutor/services/rag/service.py)
- [tests/knowledge/test_manager_get_info_status.py](tests/knowledge/test_manager_get_info_status.py)

</details>



DeepTutor의 Knowledge and Retrieval-Augmented Generation (RAG) 시스템은 지속적인 교육 콘텐츠를 관리하고 LLM 추론을 보강하기 위해 관련 정보를 검색하는 인프라를 제공합니다. 이 시스템은 인덱싱, 질의, 지식 베이스 관리를 위한 통합 인터페이스를 제공함으로써 정적 문서(PDF, 텍스트, 코드)와 에이전트 워크플로 사이의 간극을 메웁니다.

### 시스템 개요

이 시스템은 디스크에 저장된 여러 knowledge base(KB)를 조정하는 `KnowledgeBaseManager`를 중심으로 구축됩니다 [deeptutor/knowledge/manager.py:196-201](). 메타데이터와 구성은 중앙 `kb_config.json` 파일을 통해 관리합니다 [deeptutor/knowledge/manager.py:204-205](). 검색 작업은 `RAGService`를 통해 추상화되며, 초기화, 문서 추가, 검색을 위한 고수준 API를 제공합니다 [deeptutor/services/rag/service.py:18-47]().

#### 고수준 아키텍처

다음 다이어그램은 Knowledge and RAG 시스템이 자연어 질의를 기반 코드 엔터티와 저장소에 어떻게 연결하는지 보여줍니다.

**지식 검색 흐름**
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

## 6.1 RAG 시스템

RAG 시스템은 인덱싱된 knowledge base를 질의해 에이전트에게 근거 있는 context를 제공합니다. 주요 진입점은 `RAGService`이며, 기본값으로 LlamaIndex를 사용하는 특정 backend pipeline에 작업을 위임합니다 [deeptutor/services/rag/service.py:18-21]().

핵심 기능은 다음과 같습니다:
*   **Unified Search API**: `_emit_tool_event`를 통해 logging과 tool event emission을 처리하는 knowledge base 질의를 위한 표준 인터페이스입니다 [deeptutor/services/rag/service.py:61-87]().
*   **Smart Retrieval**: `smart_retrieve` 메서드는 LLM이 생성한 query hint를 사용해 복잡한 context에 대해 다중 패스 검색을 수행함으로써 기본 검색을 강화합니다 [deeptutor/services/rag/service.py:195-201]().
*   **Memory Integration**: 검색 작업은 `TraceEvent.new("kb", "query", ...)`를 사용해 L1 memory trace event를 자동으로 발생시켜 지식 사용을 추적합니다 [deeptutor/services/rag/service.py:126-140]().
*   **Pipeline Factory**: 시스템은 환경 구성에 따라 특정 RAG provider를 인스턴스화하기 위해 `get_pipeline`을 사용합니다 [deeptutor/services/rag/factory.py:13-20]().

자세한 내용은 [RAG System](#6.1)을 참조하세요.

**Sources:** [deeptutor/services/rag/service.py:18-144](), [deeptutor/services/rag/service.py:195-201](), [deeptutor/services/rag/factory.py:13-20]()

---

## 6.2 Knowledge Base Management

Knowledge Base Management는 초기화, 상태 추적, 재색인화를 포함한 문서 컬렉션의 수명 주기를 처리합니다. `KnowledgeBaseInitializer`는 디렉터리 구조와 메타데이터를 설정하고 [deeptutor/knowledge/initializer.py:107-128](), `KnowledgeBaseManager`는 디스크 상 KB의 일관성을 유지합니다 [deeptutor/knowledge/manager.py:196-201]().

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

시스템은 임베딩 모델이나 차원의 변경으로 인해 인덱스가 오래된 상태인지 감지하기 위해 `_reconcile_embedding_flags`에 강력한 reconciliation 로직을 구현합니다 [deeptutor/knowledge/manager.py:108-133](). 또한 하위 인덱스는 완료되었지만 구성(config)이 업데이트되지 않은 경우, `processing` 또는 `initializing` 상태의 KB를 `ready`로 복구하는 status promotion 메커니즘도 갖추고 있습니다 [tests/knowledge/test_manager_get_info_status.py:8-11](). 오래된 orphan은 `_ORPHAN_PRUNE_GRACE_SECONDS`로 정의된 유예 기간 후 제거됩니다 [deeptutor/knowledge/manager.py:31]().

자세한 내용은 [Knowledge Base Management](#6.2)를 참조하세요.

**Sources:** [deeptutor/knowledge/manager.py:31-193](), [deeptutor/knowledge/initializer.py:25-47](), [tests/knowledge/test_manager_get_info_status.py:68-97]()

---

## 6.3 웹 검색 및 기타 도구

지식 시스템은 로컬 문서 인덱스를 넘어 외부 정보원과 플랫폼 간 파일 처리까지 포함하도록 확장됩니다.

*   **File Routing**: `FileTypeRouter`는 KB 초기화 중 지원되는 파일을 수집하고 라우팅하는 데 사용되며, 호환되는 확장자만 처리되도록 보장합니다 [deeptutor/knowledge/initializer.py:156-157]().
*   **Cross-Platform Locking**: 관리자는 `file_lock_shared`와 `file_lock_exclusive`를 활용해 Windows(`msvcrt`)와 Unix(`fcntl`) 시스템 모두에서 구성 파일에 대한 안전한 동시 접근을 보장합니다 [deeptutor/knowledge/manager.py:53-95]().
*   **External Search**: `RAGService`는 `get_pipeline` factory를 통해 다양한 retrieval provider를 포함하도록 확장할 수 있는 통합 진입점을 제공합니다 [deeptutor/services/rag/service.py:13-15]().
*   **Embedding Fingerprints**: 시스템은 `_get_embedding_fingerprint`를 사용해 활성 embedding 구성을 추적하고 벡터 인덱스가 현재 모델과 일치하도록 보장합니다 [deeptutor/knowledge/manager.py:97-105]().

자세한 내용은 [Web Search and Other Tools](#6.3)를 참조하세요.

**Sources:** [deeptutor/knowledge/manager.py:53-105](), [deeptutor/knowledge/initializer.py:156-171](), [deeptutor/services/rag/service.py:13-15]()
