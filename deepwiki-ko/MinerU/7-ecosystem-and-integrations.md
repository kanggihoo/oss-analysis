# 생태계 및 통합

<details>
<summary>관련 소스 파일</summary>

이 위키 페이지를 생성하는 데 컨텍스트로 사용된 파일은 다음과 같습니다:

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



MinerU는 개방적이고 확장 가능한 플랫폼으로 설계되어, 광범위한 AI 애플리케이션 생태계를 위한 기초적인 문서 파싱 레이어 역할을 합니다. 이 생태계는 **모델 컨텍스트 프로토콜 (Model Context Protocol, MCP)**과 같은 로우레벨 프로토콜 구현부터 하이레벨 **검색 증강 생성 (Retrieval-Augmented Generation, RAG)** 프레임워크 및 사용자용 **웹 인터페이스**에 이르기까지 다양하게 걸쳐 있습니다.

MinerU 통합 전략의 주요 목표는 복잡한 비정형 문서(PDF, 이미지, Office 파일)와 대규모 언어 모델(LLM)에 필요한 정형 Markdown/JSON 형식 간의 격차를 해소하는 것입니다.

## 생태계 개요

다음 다이어그램은 MinerU가 어떻게 다양한 외부 클라이언트 및 프레임워크를 핵심 파싱 기능에 연결하는지 설명하며, 사용자가 에이전트와 상호 작용하는 하이레벨 "자연어 공간(Natural Language Space)"에서 MinerU가 데이터를 처리하는 "코드 엔티티 공간(Code Entity Space)"으로의 전환을 강조합니다.

**MinerU 통합 아키텍처**
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

## 7.1 오피스 문서 지원 (DOCX 및 PPTX)
MinerU는 Microsoft Office 형식에 대한 특화된 지원을 제공하여 표준 PDF 처리 경로를 대체하는 고속 대안을 제공합니다. 네이티브 OpenXML 파싱을 활용함으로써 상당한 성능 향상을 이뤄냅니다.

- **DocxConverter**: Word 문서를 오케스트레이션하는 중심 클래스로, DrawingML(`a:`), WordprocessingML(`w:`), VML(`v:`)에 대한 XML 네임스페이스 매핑을 처리합니다 [mineru/model/docx/docx_converter.py:42-54]().
- **MagicModel (Office)**: 오피스 블록을 `IMAGE_BODY`, `TABLE_BODY`, `INTERLINE_EQUATION` 등의 유형으로 분류하는 `MagicModel` 클래스의 특화된 버전입니다 [mineru/backend/office/office_magic_model.py:11-66]().
- **Office Math**: `oMath2Latex` 유틸리티를 사용하여 OMML (Office Math Markup Language)을 LaTeX로 직접 변환함으로써 수학 수식의 완전성을 보존합니다 [mineru/model/docx/docx_converter.py:21-21]().
- **콘텐츠 생성 (Content Generation)**: `office_middle_json_mkcontent` 모듈은 오피스 파이프라인에서 최종 출력을 생성하기 위해 `union_make` 및 `mk_blocks_to_markdown`과 같은 함수를 내보냅니다 [mineru/backend/office/office_middle_json_mkcontent.py:10-19]().
- **성능**: 오피스 문서는 무거운 비전 기반 PDF 렌더링 경로를 우회하고, `lxml`, `python-docx`, `pypptx-with-oxml`을 통한 직접 XML 파싱을 활용하여 10배 빠른 처리 속도를 달성합니다.

자세한 내용은 [오피스 문서 지원 (DOCX 및 PPTX)](#7.1)을 참조하세요.

**Sources:** [mineru/model/docx/docx_converter.py:42-90](), [mineru/backend/office/office_magic_model.py:11-84](), [mineru/backend/office/office_middle_json_mkcontent.py:1-36]()

---

## 7.2 RAG 및 플러그인 통합
MinerU는 표와 수식을 보존하는 고품질 Markdown 출력을 제공하므로 많은 RAG(검색 증강 생성) 플랫폼에서 선호하는 문서 파서입니다.

| 카테고리 | 통합된 프레임워크 |
| :--- | :--- |
| **RAG 엔진** | **RagFlow** (내장 지원), **Dify**, **FastGPT**, **BISHENG**, **DataFlow (ADP)** |
| **에이전트 플랫폼** | **Coze**, **ModelWhale**, **Sider**, **Cherry Studio** |
| **기업용 도구** | **DingTalk**, **ModelWhale**, **n8n** |

### 주요 통합 패턴
1.  **내장 통합 (Native Integration)**: **RagFlow** (v0.21.1+)는 MinerU를 기본 내장 PDF 파서로 사용합니다. 사용자는 `.env` 파일에 `MINERU_EXECUTABLE` 환경 변수를 설정하여 구성합니다 [docs/zh/usage/plugin/RagFlow.md:19-30]().
2.  **MCP 서버**: **Cherry Studio**는 모델 컨텍스트 프로토콜 (Model Context Protocol, MCP)을 통해 MinerU를 통합합니다. 사용자는 `uvx`를 사용하여 `mineru-mcp` 서버를 구성하고 `parse_documents`와 같은 도구를 활성화합니다 [docs/zh/usage/plugin/Cherry_Studio.md:24-48]().
3.  **마켓플레이스 플러그인**: **Coze**, **Dify**, **FastGPT**와 같은 플랫폼은 MinerU를 선택 가능한 도구로 제공합니다. Dify에서 플러그인(v0.4.0)은 공식 온라인 API와 로컬 배포를 모두 지원합니다 [docs/zh/usage/plugin/Dify.md:14-20](). Coze에서 사용자는 `MinerU` 플러그인과 `parse_file` 도구를 워크플로우에 추가할 수 있습니다 [docs/zh/usage/plugin/Coze.md:26-32]().
4.  **워크플로우 노드**: **Coze**에서 MinerU는 파일 입력을 `parse_file.text` 출력(Markdown 형식)으로 파싱하기 위해 "워크플로우(Workflow)" 내에서 사용될 수 있습니다 [docs/zh/usage/plugin/Coze.md:66-74]().
5.  **브라우저 확장 프로그램**: **Sider**는 MinerU를 자사의 "Wisebase" 모듈에 통합하여 사용자가 파싱된 PDF로부터 개인 라이브러리를 구축할 수 있도록 합니다 [docs/zh/usage/plugin/Sider.md:1-7]().
6.  **기업 생태계**: **DingTalk**은 자사의 AI Tables 및 문서 제품에 MinerU 기능을 통합했습니다 [docs/zh/usage/plugin/DingTalk.md:7-7]().

자세한 내용은 [RAG 및 플러그인 통합](#7.2)을 참조하세요.

**Sources:** [docs/zh/usage/plugin/RagFlow.md:11-30](), [docs/zh/usage/plugin/Cherry_Studio.md:24-48](), [docs/zh/usage/plugin/Coze.md:1-92](), [docs/zh/usage/plugin/Dify.md:1-20](), [docs/zh/usage/plugin/Sider.md:1-7](), [docs/zh/usage/plugin/DingTalk.md:1-7](), [docs/zh/usage/plugin/DataFlow.md:1-5](), [docs/zh/usage/plugin/FastGPT.md:1-5]()

---

## 7.3 웹 데모 및 프론트엔드
시각적인 인터페이스가 필요한 사용자를 위해 MinerU는 몇 가지 웹 기반 상호 작용 모드를 제공합니다.

- **Gradio 인터페이스**: 사용자가 문서를 업로드하고 추출된 Markdown을 실시간으로 확인할 수 있는 로컬 웹 UI입니다.
- **FastAPI 백엔드**: `mineru-api` 서버는 외부 통합 시스템이 작업을 제출하고 결과를 가져오는 데 사용하는 RESTful 인터페이스를 제공합니다.
- **중간 JSON 매핑 (Middle JSON Mapping)**: 오피스 백엔드의 `result_to_middle_json` 함수는 변환된 Office 문서가 공통 MinerU 중간 형식으로 표준화되도록 보장합니다 [mineru/backend/office/model_output_to_middle_json.py:126-131]().

자세한 내용은 [FastAPI 및 Gradio 웹 인터페이스](#4.2)를 참조하세요.

**Sources:** [mineru/backend/office/model_output_to_middle_json.py:126-131]()

---

## 통합 엔티티 매핑

이 다이어그램은 통합 개념을 특정 코드 프로젝트 및 API 엔드포인트와 연결하여, 하이레벨 사용자 도구를 기저의 코드 식별자에 매핑합니다.

**생태계 엔티티 맵**
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
