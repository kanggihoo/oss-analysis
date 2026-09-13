# Ecosystem & Integrations

<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

- [docs/assets/images/RagFlow_01.png](docs/assets/images/RagFlow_01.png)
- [docs/assets/images/RagFlow_02.png](docs/assets/images/RagFlow_02.png)
- [docs/zh/usage/plugin/BISHENG.md](docs/zh/usage/plugin/BISHENG.md)
- [docs/zh/usage/plugin/Cherry_Studio.md](docs/zh/usage/plugin/Cherry_Studio.md)
- [docs/zh/usage/plugin/Coze.md](docs/zh/usage/plugin/Coze.md)
- [docs/zh/usage/plugin/DataFlow.md](docs/zh/usage/plugin/DataFlow.md)
- [docs/zh/usage/plugin/Dify.md](docs/zh/usage/plugin/Dify.md)
- [docs/zh/usage/plugin/DingTalk.md](docs/zh/usage/plugin/DingTalk.md)
- [docs/zh/usage/plugin/FastGPT.md](docs/zh/usage/plugin/FastGPT.md)
- [docs/zh/usage/plugin/ModelWhale.md](docs/zh/usage/plugin/ModelWhale.md)
- [docs/zh/usage/plugin/RagFlow.md](docs/zh/usage/plugin/RagFlow.md)
- [docs/zh/usage/plugin/Sider.md](docs/zh/usage/plugin/Sider.md)

</details>



MinerU is designed as an open and extensible platform, serving as the foundational document parsing layer for a broad ecosystem of AI applications. This ecosystem spans from low-level protocol implementations like the **Model Context Protocol (MCP)** to high-level **Retrieval-Augmented Generation (RAG)** frameworks and user-facing **Web Interfaces**.

The primary goal of MinerU's integration strategy is to bridge the gap between complex unstructured documents (PDFs, images, Office files) and the structured Markdown/JSON formats required by Large Language Models (LLMs).

## Ecosystem Overview

The following diagram illustrates how MinerU connects various external clients and frameworks to its core parsing capabilities, highlighting the transition from high-level "Natural Language Space" (where users interact with Agents) to the "Code Entity Space" (where MinerU processes data).

**MinerU Integration Architecture**
```mermaid
graph TD
    subgraph "Natural_Language_Space_(User_Interactions)"
        ["RAG_Frameworks"] -- "Includes" --> ["RagFlow"]
        ["RAG_Frameworks"] -- "Includes" --> ["Dify"]
        ["RAG_Frameworks"] -- "Includes" --> ["FastGPT"]
        ["RAG_Frameworks"] -- "Includes" --> ["BISHENG"]
        ["AI_Assistants"] -- "Includes" --> ["Coze"]
        ["AI_Assistants"] -- "Includes" --> ["Cherry_Studio"]
        ["AI_Assistants"] -- "Includes" --> ["ModelWhale"]
        ["AI_Assistants"] -- "Includes" --> ["Sider"]
    end

    subgraph "Code_Entity_Space_(Integration_Layer)"
        ["MCP_Server"] -- "Entry" --> ["mineru-mcp"]
        ["Web_API"] -- "Entry" --> ["mineru-api"]
        ["Frontend"] -- "Logic" --> ["gradio_app.py"]
    end

    subgraph "Core_Engine_(Processing)"
        ["Orchestrator"] -- "API" --> ["do_parse"]
        ["Async_Orchestrator"] -- "API" --> ["aio_do_parse"]
        ["Backends"] -- "Logic" --> ["Pipeline/VLM/Hybrid"]
    end

    ["RAG_Frameworks"] -- "HTTP_POST" --> ["Web_API"]
    ["AI_Assistants"] -- "stdio/SSE" --> ["MCP_Server"]
    ["Frontend"] -- "Fetch" --> ["Web_API"]
    ["MCP_Server"] -- "calls" --> ["Web_API"]
    ["Web_API"] -- "invokes" --> ["Async_Orchestrator"]
    ["Orchestrator"] -- "orchestrates" --> ["Backends"]
```
**Sources:** [docs/zh/usage/plugin/RagFlow.md:1-10](), [docs/zh/usage/plugin/Cherry_Studio.md:1-7](), [docs/zh/usage/plugin/Coze.md:1-5]()

---

## 7.1 Office Document Support (DOCX & PPTX)
MinerU provides specialized support for Microsoft Office formats, offering a high-speed alternative to the standard PDF processing path. By leveraging native OpenXML parsing, it achieves significant performance improvements.

- **DocxConverter**: The central orchestration class for Word documents, handling XML namespace mapping for DrawingML (`a:`), WordprocessingML (`w:`), and VML (`v:`) [mineru/model/docx/docx_converter.py:42-54]().
- **MagicModel (Office)**: A specialized version of the `MagicModel` class that classifies Office blocks into types such as `IMAGE_BODY`, `TABLE_BODY`, and `INTERLINE_EQUATION` [mineru/backend/office/office_magic_model.py:11-66]().
- **Office Math**: Preserves mathematical integrity by converting OMML (Office Math Markup Language) directly to LaTeX via the `oMath2Latex` utility [mineru/model/docx/docx_converter.py:21-21]().
- **Content Generation**: The `office_middle_json_mkcontent` module exports functions like `union_make` and `mk_blocks_to_markdown` to generate final outputs from the Office pipeline [mineru/backend/office/office_middle_json_mkcontent.py:10-19]().
- **Performance**: Office documents bypass the heavy vision-based PDF rendering path, utilizing direct XML parsing via `lxml`, `python-docx`, and `pypptx-with-oxml` for 10x faster processing.

For details, see [Office Document Support (DOCX & PPTX)](#7.1).

**Sources:** [mineru/model/docx/docx_converter.py:42-90](), [mineru/backend/office/office_magic_model.py:11-84](), [mineru/backend/office/office_middle_json_mkcontent.py:1-36]()

---

## 7.2 RAG & Plugin Integrations
MinerU is a preferred document parser for many RAG (Retrieval-Augmented Generation) platforms due to its high-quality Markdown output, which preserves tables and formulas.

| Category | Integrated Frameworks |
| :--- | :--- |
| **RAG Engines** | **RagFlow** (native), **Dify**, **FastGPT**, **BISHENG**, **DataFlow (ADP)** |
| **Agent Platforms** | **Coze**, **ModelWhale**, **Sider**, **Cherry Studio** |
| **Enterprise Tools** | **DingTalk**, **ModelWhale**, **n8n** |

### Key Integration Patterns
1.  **Native Integration**: **RagFlow** (v0.21.1+) uses MinerU as a built-in PDF parser. Users configure the `MINERU_EXECUTABLE` environment variable in their `.env` file [docs/zh/usage/plugin/RagFlow.md:19-30]().
2.  **MCP Server**: **Cherry Studio** integrates MinerU via the Model Context Protocol (MCP). Users configure the `mineru-mcp` server using `uvx` to enable tools like `parse_documents` [docs/zh/usage/plugin/Cherry_Studio.md:24-48]().
3.  **Marketplace Plugins**: Platforms like **Coze**, **Dify**, and **FastGPT** offer MinerU as a selectable tool. In Dify, the plugin (v0.4.0) supports both official online APIs and local deployments [docs/zh/usage/plugin/Dify.md:14-20](). In Coze, users can add the `MinerU` plugin and the `parse_file` tool to workflows [docs/zh/usage/plugin/Coze.md:26-32]().
4.  **Workflow Nodes**: In **Coze**, MinerU can be used in a "Workflow" to parse file inputs into `parse_file.text` outputs (Markdown format) [docs/zh/usage/plugin/Coze.md:66-74]().
5.  **Browser Extensions**: **Sider** integrates MinerU into its "Wisebase" module, allowing users to build personal libraries from parsed PDFs [docs/zh/usage/plugin/Sider.md:1-7]().
6.  **Enterprise Ecosystems**: **DingTalk** has integrated MinerU capabilities into its AI Tables and document products [docs/zh/usage/plugin/DingTalk.md:7-7]().

For details, see [RAG & Plugin Integrations](#7.2).

**Sources:** [docs/zh/usage/plugin/RagFlow.md:11-30](), [docs/zh/usage/plugin/Cherry_Studio.md:24-48](), [docs/zh/usage/plugin/Coze.md:1-92](), [docs/zh/usage/plugin/Dify.md:1-20](), [docs/zh/usage/plugin/Sider.md:1-7](), [docs/zh/usage/plugin/DingTalk.md:1-7](), [docs/zh/usage/plugin/DataFlow.md:1-5](), [docs/zh/usage/plugin/FastGPT.md:1-5]()

---

## 7.3 Web Demo & Frontend
For users requiring a visual interface, MinerU provides several web-based interaction modes.

- **Gradio Interface**: A local web UI that allows users to upload documents and view extracted Markdown in real-time.
- **FastAPI Backend**: The `mineru-api` server provides the RESTful interface used by external integrations to submit tasks and retrieve results.
- **Middle JSON Mapping**: The `result_to_middle_json` function in the office backend ensures that converted Office documents are standardized into the common MinerU intermediate format [mineru/backend/office/model_output_to_middle_json.py:126-131]().

For details, see [FastAPI & Gradio Web Interfaces](#4.2).

**Sources:** [mineru/backend/office/model_output_to_middle_json.py:126-131]()

---

## Integration Entity Mapping

This diagram bridges the integration concepts to specific code projects and API endpoints, mapping high-level user tools to the underlying code identifiers.

**Ecosystem Entity Map**
```mermaid
graph LR
    subgraph "Natural_Language_/_User_Interface"
        ["Dify_Workflow"]
        ["Coze_Bot"]
        ["RagFlow_Parser"]
        ["Cherry_Studio_MCP"]
    end

    subgraph "Code_Entity_Space_(Integration_Projects)"
        ["DocxConverter"] -- "File" --> ["docx_converter.py"]
        ["MagicModel_Office"] -- "File" --> ["office_magic_model.py"]
        ["Middle_JSON_Maker"] -- "File" --> ["model_output_to_middle_json.py"]
    end

    subgraph "Core_System_Entrypoints"
        ["PARSE_FUNC"] -- "Function" --> ["do_parse"]
        ["ASYNC_FUNC"] -- "Function" --> ["aio_do_parse"]
        ["OFFICE_RESULT"] -- "Function" --> ["result_to_middle_json"]
        ["MCP_TOOL"] -- "Identifier" --> ["parse_documents"]
    end

    ["Dify_Workflow"] -- "REST_API" --> ["ASYNC_FUNC"]
    ["Coze_Bot"] -- "REST_API" --> ["ASYNC_FUNC"]
    ["RagFlow_Parser"] -- "subprocess" --> ["PARSE_FUNC"]
    ["Cherry_Studio_MCP"] -- "stdio" --> ["MCP_TOOL"]
    ["DocxConverter"] -- "feeds" --> ["MagicModel_Office"]
    ["MagicModel_Office"] -- "standardizes" --> ["OFFICE_RESULT"]
    ["OFFICE_RESULT"] -- "produces" --> ["Middle_JSON_Maker"]
```
**Sources:** [mineru/model/docx/docx_converter.py:42-43](), [mineru/backend/office/office_magic_model.py:11-12](), [mineru/backend/office/model_output_to_middle_json.py:126-127](), [docs/zh/usage/plugin/Cherry_Studio.md:72-75]()
