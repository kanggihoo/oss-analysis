---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/skills/context_manager.py
  - gpt_researcher/skills/writer.py
  - gpt_researcher/agent.py
  - gpt_researcher/document/__init__.py
  - gpt_researcher/document/document.py
  - gpt_researcher/document/online_document.py
  - gpt_researcher/document/azure_document_loader.py
  - gpt_researcher/document/langchain_document.py
  - gpt_researcher/utils/enum.py
  - gpt_researcher/utils/url_security.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/default.py
  - gpt_researcher/prompts.py
  - gpt_researcher/context/select.py
  - gpt_researcher/actions/query_processing.py
  - gpt_researcher/skills/deep_research.py
  - backend/report_type/detailed_report/detailed_report.py
  - backend/server/app.py
  - cli.py
  - frontend/index.html
  - frontend/scripts.js
  - frontend/nextjs/components/Task/ResearchForm.tsx
  - pyproject.toml
  - requirements.txt
  - docs/docs/gpt-researcher/gptr/config.md
  - docs/docs/gpt-researcher/context/local-docs.md
  - docs/docs/gpt-researcher/context/azure-storage.md
  - docs/docs/examples/hybrid_research.md
  - docs/docs/examples/sample_sources_only.py
  - docs/docs/examples/detailed_report.md
depends:
  - ../capabilities/research-pipeline.md
status: ready
reimplementation: 미실행
---

# 소스 모드

> `report_source`(`web` / `local` / `hybrid` / `azure` / `langchain_documents`)와 `source_urls`, `document_urls`, `documents`, `complement_source_urls` 인자에 따라, 조사가 참고할 자료를 웹 검색 결과 · 로컬 폴더 문서 · 다운로드한 문서 · Azure Blob 문서 · LangChain 문서 객체 · 지정한 URL 중에서 고르고, 문서는 `{raw_content, url}` 목록으로 바꿔 웹 검색 경로에 넘겨 컨텍스트 문자열을 만든다.

<!-- 용어: 소스 모드 = 조사가 어디서 자료를 가져올지 고르는 분기(`ResearchConductor.conduct_research`의 if 사슬). 문서 = `{raw_content: 본문 문자열, url: 출처 이름}` dict(웹 페이지 dict와 같은 모양에서 `title`·`image_urls`가 없는 것). 서브쿼리·컨텍스트·visited_urls는 research-pipeline.md의 정의를 따른다. 이 스펙의 근거는 기준 SHA 소스를 읽은 것이고, 일부 동작은 오프라인 실행 실험(스텁 사용)으로도 관찰했다(2.1 끝). -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

`GPTResearcher(query=..., report_source="local")`를 만들고 `await conduct_research()`를 부르는 경우다. 에이전트 선택과 deep 분기는 [research-pipeline.md](research-pipeline.md)가 먼저 처리하고, 그 다음 `ResearchConductor.conduct_research`가 아래 순서로 자료 경로를 고른다.

1. `source_urls`가 비어 있지 않으면 그 경로(5번)로 간다. 아니면 `report_source`를 `web`, `local`, `hybrid`, `azure`, `langchain_documents`, `langchain_vectorstore` 순서로 `==` 비교해 처음 맞는 하나만 탄다. 어느 것에도 맞지 않으면 아무것도 하지 않고 컨텍스트가 `[]`가 된다(R-01~R-03).
2. 문서 모드(`local`, `hybrid`의 문서 패스, `azure`, `langchain_documents`)는 먼저 문서 목록 D를 만든다. `local`은 `DOC_PATH` 폴더, `hybrid`는 `document_urls`(있으면) 또는 `DOC_PATH`, `azure`는 Blob 컨테이너를 내려받은 파일, `langchain_documents`는 호출자가 준 `Document` 객체가 출처다. 문서를 하나도 못 얻으면 `ValueError`가 호출자까지 올라간다(R-10~R-15, R-19~R-22).
3. D를 웹 검색 경로 `_get_context_by_web_search(query, D, query_domains)`에 넘긴다. 이 경로는 D가 있어도 초기 웹 검색과 서브쿼리 계획은 그대로 하지만, 서브쿼리마다 검색·스크랩을 하는 대신 D 전체를 선별 입력으로 쓴다(R-06~R-09).
4. `hybrid`는 3번을 "문서를 넘긴 패스"와 "문서 없이 웹으로 하는 패스"로 동시에 돌리고, 두 결과를 `prompt_family.join_local_web_documents`로 한 문자열에 이어 붙인다(R-17, R-18).
5. `source_urls` 경로는 서브쿼리 계획 없이, 새 URL만 스크랩해 원 질문 하나로 선별한다. `complement_source_urls`가 참이면 그 뒤에 웹 검색 경로를 한 번 더 돌려 이어 붙인다(R-24~R-26).
6. 결과(`research_data`)는 `researcher.context`가 되고, `CURATE_SOURCES` 후처리와 반환은 모든 경로가 [research-pipeline.md](research-pipeline.md) R-26·R-27로 공유한다.

경로별 차이를 한 표로 보면 다음과 같다(자세한 규칙은 1.4).

| 경로 | 자료 출처 | 초기 웹 검색·서브쿼리 계획 | 서브쿼리마다 하는 일 | 결과 타입 |
|---|---|---|---|---|
| `web` | 웹 | 함 | 검색 → 스크랩 → 선별 | 문자열 또는 `[]` |
| `local` | `DOC_PATH` 폴더 문서 | 함(계획 재료로만 쓰임) | D 전체를 선별 | 문자열 또는 `[]` |
| `hybrid` | 문서 패스와 웹 패스 | 패스마다 각각 함 | 문서 패스는 D 선별, 웹 패스는 `web`과 같음 | 항상 문자열 |
| `azure` | Blob 문서 | 함 | D 전체를 선별 | 문자열 또는 `[]` |
| `langchain_documents` | `documents` 인자 | 함 | D 전체를 선별(D가 비면 `web`과 같음) | 문자열 또는 `[]` |
| `source_urls` | 지정한 URL | 하지 않음 | 서브쿼리 자체가 없음. 원 질문 하나로 선별 | 문자열(빈 문자열 가능) |

### 1.2 범위·통합 지점

- 제공: `conduct_research`의 자료 경로 분기 규칙, 문서 로더 네 가지(폴더·URL·Azure·LangChain 객체)의 입력·출력·실패 처리, 문서를 넘겼을 때 웹 검색 경로가 달라지는 점, `hybrid`의 병렬 처리와 결합 형식, `source_urls` 경로와 `complement_source_urls` 보완, 어디에도 맞지 않는 `report_source` 값의 결과.
- 제외:
  - 자체 벡터스토어(사용자 제외): `langchain_vectorstore` 모드, `vector_store`·`vector_store_filter` 인자, `VectorStoreWrapper`. 이 스펙이 아는 것은 "`report_source`가 `"langchain_vectorstore"`이고 `source_urls`가 비어 있으면 `_get_context_by_vectorstore(query, vector_store_filter)`로 간다"는 사실 하나뿐이다(R-23). 문서를 로드한 뒤 `if vector_store: vector_store.load(...)`가 나오는 자리(로컬·하이브리드·LangChain 문서·URL 경로)는 "벡터스토어가 있으면 문서를 적재한다(제외)"로만 표시하고 `vector_store`는 없다고 가정한다.
  - 서브쿼리 계획, 병렬 처리, `visited_urls`, 결과 합치기는 [research-pipeline.md](research-pipeline.md), 스크랩과 URL 안전 검사의 내부는 [scrapers.md](scrapers.md), 컨텍스트 선별은 context-selection.md(아직 없음)의 몫이다. 이 스펙은 입력 모양과 호출 시점까지만 정한다.
  - LLM 제공자·`Config` 로딩·임베딩은 사용자 제외다. 설정 키는 원문 이름만 쓴다(`REPORT_SOURCE`, `DOC_PATH`, `PROMPT_FAMILY`).
  - 문서 파서 라이브러리(`langchain_community`의 로더들)의 내부, Azure SDK, HTTP 클라이언트 내부는 외부 의존이다.
  - 서버·CLI·웹 프런트엔드가 `report_source`를 어떻게 받아 넘기는지는 사용자 제외 범위이고, 값 이름이 어긋나는 곳만 2.1에 적었다.
- 외부 의존·선행 계약:

  | 대상 | 이 스펙이 주는 입력 | 정상 결과 | 실패 시 이 스펙이 보는 것 | 상세 |
  |---|---|---|---|---|
  | 웹 검색 경로 `_get_context_by_web_search(query, scraped_data, query_domains)` | 질문, 문서 목록(없으면 `[]`), 도메인 목록 | 문자열 또는 `[]` | 초기 검색·계획 예외는 호출자로 전파, 서브쿼리 실패는 빈 문자열(pipeline R-09~R-11, R-24) | [research-pipeline.md](research-pipeline.md) |
  | 스크랩 `browse_urls(list[str])` | 새 URL 목록 | 본문을 얻은 페이지 dict 목록(실패 URL은 빠짐) | 예외 없이 빈 목록 | [scrapers.md](scrapers.md) |
  | 컨텍스트 선별 `get_similar_content_by_query(query, pages)` | 질문, 페이지·문서 dict 목록(`raw_content`, `url`) | 문자열 | 선별 모드 실패는 내부에서 keyword로 낮춤. 그래도 예외면 호출자 규칙(서브쿼리는 빈 문자열) | context-selection.md(아직 없음) |
  | 문서 파서 로더(`langchain_community.document_loaders`) | 파일 경로 하나로 만든 로더 객체 | `.load()` → 페이지 객체 목록(`page_content: string`, `metadata: map`) | 생성자 또는 `.load()` 예외 | 범위 밖. 분할 단위·`metadata` 키는 라이브러리 몫 |
  | URL 안전 검사 `validate_url(url)` | URL 문자열 | 입력을 그대로 반환 | `UnsafeURLError` | R-29, [scrapers.md](scrapers.md) R-04·R-05 |
  | HTTP 다운로드(`aiohttp`) | URL, `User-Agent: Mozilla/5.0`, `timeout=6` | 응답 상태와 본문 바이트 | `aiohttp.ClientError` 또는 그 밖의 예외 | 범위 밖 |
  | Azure Blob SDK(`azure.storage.blob`) | 연결 문자열, 컨테이너 이름 | blob 목록과 바이트 | 예외는 그대로 전파 | 범위 밖. 모드를 쓸 때만 import한다(R-19) |
  | 프롬프트 패밀리 `prompt_family.join_local_web_documents` | 두 패스의 결과 | 문자열 | 인자가 리스트면 일부 패밀리는 `TypeError`(R-18) | R-18, C-09 |

  MCP retriever가 설정된 경우 `_process_sub_query`가 문서 유무와 무관하게 MCP 컨텍스트를 덧붙이는 점은 R-08에 경계만 적었고, 규칙은 mcp-client.md(아직 없음)가 맡는다.
- 소유 상태·부작용:
  - `researcher.context`: 결과 문자열 또는 `[]`로 덮어쓴다(pipeline R-27). 로드 실패의 `ValueError`는 이 대입 전에 일어나므로 `context`는 그대로다.
  - `visited_urls`: URL 경로(`source_urls`, `complement_source_urls`의 웹 보완, `hybrid`의 웹 패스)만 바꾼다. 문서 패스는 건드리지 않는다(R-07).
  - 파일 시스템: `azure`는 `tempfile.mkdtemp()` 폴더를 만들고 지우지 않는다(R-20). `document_urls`는 다운로드마다 임시 파일을 만들고 로드 직후 지운다(R-27). `Config`는 설정 dict의 `REPORT_SOURCE`가 `web`이 아니면 `DOC_PATH` 폴더를 만든다(R-11).
  - 표준 출력: 문서 로더는 건너뛴 파일·URL과 예외 메시지를 `print`로 낸다(로거가 아니다).
  - 로더 객체는 호출마다 새로 만들어지고 상태를 남기지 않는다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `GPTResearcher(...)` 관련 인자 | `report_source: string = "web"`, `source_urls: list[string]?`, `document_urls: list[string]?`, `complement_source_urls: bool = False`, `documents: list[LangChain Document]?`, `query_domains: list[string]?`, `vector_store`·`vector_store_filter`(제외) | 인자는 그대로 필드에 저장된다. `report_source`가 거짓이면 `cfg.report_source`로 대체된다(R-04). 값 검증은 없다. |
| `report_source` 값 | string. 대소문자 구분 | `"web"`, `"local"`, `"hybrid"`, `"azure"`, `"langchain_documents"`, `"langchain_vectorstore"`(제외), 그리고 열거형에는 있지만 분기가 없는 `"static"`(C-08). 그 밖의 값도 오류 없이 받아들이고 결과는 `[]`다(R-02). |
| 문서(document) | `{raw_content: string, url: string?}` | `raw_content`는 문서 본문이고 `url`은 출처 이름이다. 로컬은 파일명, Azure는 blob 파일명, LangChain은 `metadata["title"]`, 온라인은 로더가 준 `metadata["source"]`(R-30). 웹 페이지 dict와 달리 `title`·`image_urls`가 없다. |
| `DocumentLoader(path).load()` | `path: string \| bytes \| PathLike \| list[string]` → 비동기, `list[문서]` | 폴더는 재귀 순회, 리스트는 파일만(R-12). 문서가 하나도 없으면 `ValueError("🤷 Failed to load any documents!")`. 잘못된 `path` 타입은 `ValueError`. |
| `OnlineDocumentLoader(urls).load()` | `urls: list[string]` → 비동기, `list[문서]` | URL을 순서대로 하나씩 내려받는다(R-27). 문서가 없으면 위와 같은 `ValueError`. |
| `AzureDocumentLoader(container_name, connection_string).load()` | → 비동기, `list[string]`(로컬 파일 경로) | 문서가 아니라 내려받은 파일 경로 목록을 준다. 다시 `DocumentLoader`에 넣는다(R-21). |
| `LangChainDocumentLoader(documents).load(metadata_source_index="title")` | `list[Document]` → 비동기, `list[문서]` | `Document`에서 `page_content`와 `metadata`만 읽는다. 분기는 인자 없이 호출하므로 키는 항상 `"title"`(R-22). |
| `_get_context_by_urls(urls)` | `urls: list[string]` → `string` | R-24. |
| 설정·환경변수 | `REPORT_SOURCE`(기본 `"web"`), `DOC_PATH`(기본 `"./my-docs"`), `AZURE_CONTAINER_NAME`, `AZURE_CONNECTION_STRING`, `ALLOW_PRIVATE_URLS`, `PROMPT_FAMILY`(기본 `"default"`) | `AZURE_*`는 `Config`가 아니라 분기 안에서 `os.getenv`로 직접 읽는다(R-19). `ALLOW_PRIVATE_URLS`는 URL 검사의 환경변수다(scrapers.md). `PROMPT_FAMILY`는 R-18. |
| 경로별 반환값(`research_data`) | 아래 | `web`, `local`, `azure`, `langchain_documents`: 비어 있지 않은 문자열 또는 `[]`. `hybrid`: 항상 문자열. `source_urls`: 문자열(비어 있을 수 있음). 어느 것에도 맞지 않는 값: `[]`. |

### 1.4 행동 규칙과 남은 질문

실행 확인이라고 적은 것은 실제 소스를 불러와 오프라인으로 돌린 결과이며, 문서 파서·`aiohttp`·Azure SDK·검색·스크랩·선별은 대체물이다(2.1 끝 참고). "실행 확인(스텁)"은 대체물 아래에서 관찰했다는 뜻이다.

**분기와 값**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `conduct_research` 분기 | `source_urls`가 truthy(비어 있지 않은 리스트)면 URL 경로(R-24)로 간다. 아니면 `report_source`를 `"web"`, `"local"`, `"hybrid"`, `"azure"`, `"langchain_documents"`, `"langchain_vectorstore"`와 이 순서로 `==` 비교해 처음 맞는 한 경로만 탄다. 값 검증·정규화(대소문자, 공백)는 없다. `source_urls=[]`는 거짓이라 `report_source`로 넘어간다. 문서 로더는 해당 분기에 들어간 뒤에만 불린다. | 코드 확인 (C-01, C-08), 실행 확인(스텁, §6) |
| R-02 | 어떤 분기에도 맞지 않는 `report_source`(예: `"static"`, `"doc"`, `"web_search"`, `"online"`, `"Local"`, `None`)이고 `source_urls`가 없음 | 아무 로드·검색도 하지 않고 `research_data = []`로 끝난다. 예외나 경고가 없다. 이후 `CURATE_SOURCES` 후처리와 반환은 공통이라 컨텍스트는 `[]`다(`CURATE_SOURCES`가 켜져 있으면 pipeline R-26대로 curation에 `[]`가 들어간다). `static`은 열거형(`ReportSource.Static`)에는 있지만 이 분기 사슬에 대응이 없다. | 코드 확인 (C-01), 실행 확인(스텁, §6) |
| R-03 | `source_urls`가 truthy | `report_source` 값(`static`, `local`, `hybrid` 등 무엇이든)과 `document_urls`, `DOC_PATH`를 읽지 않는다. `local`이어도 문서를 로드하지 않고, `DOC_PATH`가 없는 폴더여도 오류가 나지 않는다. | 코드 확인 (C-01), 실행 확인(스텁, §6) |
| R-04 | `GPTResearcher` 생성자의 `report_source` 결정 | 인자가 truthy면 그 값을, 거짓(`None`, `""`)이면 `cfg.report_source`(`REPORT_SOURCE`, 기본 `"web"`, `None`일 수도 있음)를 쓴다. 인자 기본값이 이미 `"web"`이라서 `REPORT_SOURCE` 환경변수·설정은 호출자가 `report_source=""`나 `None`을 명시적으로 넘길 때만 효과가 있다. 이 필드가 R-01의 비교 대상이다. | 코드 확인 (C-11) |
| R-05 | `report_source`를 읽는 그 밖의 곳 | 보고서 프롬프트 생성이 `report_source == "web"`인지로 참고문헌 지시를 가른다. `"web"`이면 URL 하이퍼링크 참고문헌, 그 밖의 값(`local`, `hybrid`, `azure`, `langchain_documents` 등)이면 "문서 이름"을 참고문헌으로 쓰라는 지시가 들어간다(prompts.py:278, :367, :440). 따라서 `report_source="web"`로 `source_urls`를 주면 URL 참고문헌 지시가 간다. `report_type="deep"`는 이 분기에 오지 않고 하위 연구자를 항상 `"web"`으로 만든다(deep_research.py:445). 두 동작의 상세는 보고서 작성·Deep Research 스펙의 몫이다. | 코드 확인 |

**문서를 넘겼을 때의 웹 검색 경로**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-06 | 문서 목록 D가 비어 있지 않고 `_get_context_by_web_search(query, D, query_domains)`가 불림 | (a) 초기 웹 검색(`retrievers[0]`)과 서브쿼리 계획은 D가 없을 때와 똑같이 한다. 즉 문서 모드에서도 검색 API가 필요하고, 초기 검색 예외는 `conduct_research` 밖으로 전파된다(pipeline R-09). 초기 결과는 서브쿼리 계획의 참고 자료로만 쓰인다. (b) `scraped_data`(=D)가 비어 있지 않으므로 초기 결과를 스크랩해 만드는 초기 컨텍스트 단계(pipeline R-16)는 건너뛴다. (c) 원 질문을 덧붙인 서브쿼리마다(`subtopic_report`는 덧붙이지 않음) 검색·스크랩 없이 D 전체를 그대로 선별 입력으로 `get_similar_content_by_query(sub_query, D)`를 부른다. 같은 D가 서브쿼리 수만큼 선별에 들어간다. (d) 서브쿼리 결과를 pipeline R-25대로 비어 있지 않은 것만 공백 한 칸으로 이어 붙인다. 서브쿼리 사이의 중복 제거는 없다. | 코드 확인 (C-03), 실행 확인(스텁, §7) |
| R-07 | R-06 경로 | 문서 패스는 `_get_new_urls`·`browse_urls`를 부르지 않으므로 `visited_urls`, `research_sources`, `research_images`를 바꾸지 않는다. 그래서 `local`·`azure`·`langchain_documents` 실행만으로는 `get_source_urls()`가 빈 목록이다. | 코드 확인 (C-03), 실행 확인(스텁, §7: `visited_urls` 변화 없음) |
| R-08 | R-06 경로에서 MCP retriever가 설정됨 | `_process_sub_query`는 문서 유무와 무관하게 MCP 컨텍스트를 모아 선별 결과 뒤에 덧붙인다(pipeline R-24). 규칙은 mcp-client.md(아직 없음)의 몫이다. | 코드 확인 (researcher.py:563-616) |
| R-09 | `scraped_data`로 빈 목록(또는 `None`)이 넘어옴 | `if not scraped_data`로 판정하므로 문서 유무가 아니라 목록이 비었는지가 기준이다. 비면 서브쿼리마다 검색·스크랩이 일어나고 초기 컨텍스트 단계도 실행된다. 곧 `web`과 같은 경로가 된다. 결과: `langchain_documents`에서 `documents=[]`는 오류 없이 웹 검색과 같은 동작이 되고(R-22), `documents=None`은 `TypeError`다. 문서 로더가 `ValueError`를 내는 `local`·`hybrid`·`azure`는 이 상태가 되지 않는다. | 코드 확인 (C-03), 실행 확인(스텁, §6, §7) |

**local**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-10 | `report_source == "local"`, `source_urls` 없음 | `DocumentLoader(cfg.doc_path).load()`로 D를 만든다(R-12~R-15). `vector_store`가 있으면 D를 적재한다(제외). 그 뒤 `_get_context_by_web_search(query, D, query_domains)`를 부르고 결과가 `research_data`다. `document_urls`는 무시한다. 로더가 던진 예외는 잡히지 않고 `conduct_research` 밖으로 나가며, 웹 검색으로 대체하지 않는다. | 코드 확인 (C-01), 실행 확인(스텁, §6) |
| R-11 | `cfg.doc_path`의 결정 | 기본 설정 dict의 `REPORT_SOURCE`가 `"web"`이면 `DOC_PATH` 환경변수가 있으면 그 값, 없으면 설정값(기본 `"./my-docs"`)이 `doc_path`이고 폴더는 만들지 않는다. 설정 dict(기본값에 `config_path`/`CONFIG_PATH`의 JSON 파일을 덮어쓴 것)의 `REPORT_SOURCE`가 `"web"`이 아니면 `Config` 생성자가 `doc_path`를 그 dict의 `DOC_PATH`로 다시 덮어쓰고(이때 `DOC_PATH` 환경변수는 무시된다), 값이 비어 있지 않으면 `os.makedirs(doc_path, exist_ok=True)`로 폴더를 만든다. 만들다 예외가 나면 경고를 출력하고 `doc_path`를 기본값 `"./my-docs"`로 되돌린다(그 폴더를 만들지는 않는다). 이 조건은 `REPORT_SOURCE` 환경변수나 `report_source` 인자가 아니라 dict 값만 보므로, 환경변수나 인자로만 `local`을 준 경우에는 폴더가 만들어지지 않아 없는 폴더에 대해 R-15가 일어날 수 있다. 상대 경로는 프로세스 작업 디렉터리 기준이다. | 코드 확인 (C-12), 실행 확인(스텁, §9: 실제 `Config`, 보조 모듈 스텁) |
| R-12 | `DocumentLoader(path).load()`의 `path` | `str`·`bytes`·`PathLike`면 `os.walk`로 하위 폴더까지 모든 파일을 훑는다(파일 종류 필터 없음, 순회 순서는 `os.walk`와 파일 시스템이 정한다). `list`면 각 항목 중 `os.path.isfile`인 것만 쓰고 폴더나 없는 경로는 조용히 건너뛰며 하위 순회도 하지 않는다. 그 밖의 타입은 `ValueError("Invalid type for path. ...")`. 확장자는 `os.path.splitext`로 구한 뒤 앞뒤 `.`를 지우고 소문자로 바꾼 값이다. | 코드 확인 (C-04), 실행 확인(스텁, §1, §1b, §1c) |
| R-13 | 파일별 로더 선택과 실패 | 확장자로 C-04의 로더를 고른다(`pdf`, `epub`, `txt`, `doc`, `docx`, `pptx`, `csv`, `xls`, `xlsx`, `md`, `html`, `htm`, 총 12개). 지원하지 않는 확장자나 확장자 없는 파일은 메시지 없이 빈 결과다. 로더의 `.load()`가 예외를 내면 `Failed to load <확장자> document: <경로>`와 예외를 출력하고 그 파일만 빈 결과로 두며 다른 파일은 계속한다. 로더 사전은 파일마다 12개 로더를 모두 생성하므로, 어느 로더든 생성자가 예외를 내면(예: 선택 의존 패키지 누락) 확장자와 상관없이 그 파일이 `Failed to load document : <경로>`로 빈 결과가 된다. 모든 파일이 이렇게 되면 R-15다. 로더 생성자가 실제로 패키지 누락에 예외를 내는지는 확인하지 못했다. | 코드 확인 (C-04), 실행 확인(스텁, §1, §1c). 실제 로더의 생성자 동작은 미확인 |
| R-14 | 로더가 돌려준 페이지를 문서로 변환 | 각 페이지 중 `page_content`가 truthy인 것만 `{raw_content: page_content, url: basename(metadata["source"] 또는 metadata["file_path"] 또는 "")}`로 만든다. 한 파일에서 여러 페이지가 나오면 같은 `url`의 별도 문서가 된다. 폴더가 다른 같은 파일명(`a.txt`와 `sub/a.txt`)도 구분되지 않는다. 중복 제거도 없다. 문서 순서는 파일 순서에 페이지 순서를 이은 것이다. 파일 하나를 읽는 동안 이벤트 루프가 막히고(await가 없다) 파일은 차례로 읽힌다. | 코드 확인 (C-04), 실행 확인(스텁, §1) |
| R-15 | 위 규칙을 거친 문서가 하나도 없음(없는 폴더, 빈 폴더, 모두 미지원·실패·빈 내용, 유효한 파일 없는 리스트) | `ValueError("🤷 Failed to load any documents!")`가 나고 잡히지 않아 `conduct_research` 호출자까지 전파된다. 이때 `researcher.context`는 바뀌지 않는다. | 코드 확인 (C-04), 실행 확인(스텁, §1c, §6) |

**hybrid**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-16 | `report_source == "hybrid"`, `source_urls` 없음 | `document_urls`가 truthy면 `OnlineDocumentLoader(document_urls).load()`, 아니면 `DocumentLoader(cfg.doc_path).load()`로 D를 만든다. `document_urls`가 있으면 `DOC_PATH`는 읽지 않는다. `vector_store`가 있으면 D를 적재한다(제외). 어느 로더든 `ValueError`는 그대로 전파되고 웹 패스는 시작하지도 않는다(웹만으로 대체하지 않는다). | 코드 확인 (C-01), 실행 확인(스텁, §6) |
| R-17 | hybrid 두 패스 | `asyncio.gather`로 두 패스를 동시에 실행한다: 문서 패스 `_get_context_by_web_search(query, D, query_domains)`와 웹 패스 `_get_context_by_web_search(query, [], query_domains)`. 각 패스가 초기 웹 검색, 서브쿼리 계획, 서브쿼리 처리를 따로 하므로 검색 호출과 계획용 LLM 호출이 패스마다 있다. 문서 패스는 `visited_urls`를 쓰지 않아(R-07) 코드 주석의 "visited_urls가 두 패스를 걸쳐 중복을 거른다"와 달리 `visited_urls`는 웹 패스만 바꾼다. 한 패스에서 예외가 나면 `gather`의 표준 동작대로 첫 예외가 호출자로 전파된다. 각 패스의 결과는 문자열 또는 `[]`다. | 코드 확인 (C-01, C-03), 실행 확인(스텁, §6) |
| R-18 | hybrid 결합 | `research_data = prompt_family.join_local_web_documents(docs_context, web_context)`. 기본 패밀리(`PROMPT_FAMILY="default"`)는 `"Context from local documents: {docs}\n\nContext from web sources: {web}"`라서 항상 비어 있지 않은 문자열이다. 두 패스가 모두 `[]`면 문자열 `[]`가 그대로 들어간 `Context from local documents: []\n\nContext from web sources: []`가 된다. Granite 계열은 다르다: `granite3`·`3.1`·`3.2`는 `<|start_of_role|>documents<|end_of_role|>\n` 접두와 `\n<|end_of_text|>` 접미로 감싸고 앞 문서 컨텍스트의 접두·뒤 웹 컨텍스트의 접미를 먼저 떼며, `granite3.3`은 `"\n\n".join`만 한다. 둘 다 인자가 리스트(`[]`)면 `TypeError`다. `granite`는 `SMART_LLM` 문자열에 `"3.3"`이 들어 있는지를 보고 고른다. | 코드 확인 (C-09), 실행 확인(`join` 함수만 추출, §5) |

**azure**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-19 | `report_source == "azure"`, `source_urls` 없음 | 분기 안에서 `azure_document_loader` 모듈을 import한다(이 모듈이 `azure.storage.blob`을 import하는 지연 import). 이어서 `AzureDocumentLoader(container_name=os.getenv("AZURE_CONTAINER_NAME"), connection_string=os.getenv("AZURE_CONNECTION_STRING"))`를 만든다. 두 환경변수는 `Config`가 아니라 여기서 바로 읽고, 없으면 `None`이 SDK에 그대로 간다(그 결과는 외부 SDK 동작이라 미확인). `azure-storage-blob`은 `requirements.txt`에 없고 `pyproject.toml`의 선택 의존(`requirements-txt` extra)이라, azure 모드를 쓰지 않으면 필요 없다. | 코드 확인 (C-01), 실행 확인(스텁, §6: 환경변수 값이 SDK 호출에 들어감). SDK 동작은 미확인 |
| R-20 | `AzureDocumentLoader.load()` | `tempfile.mkdtemp()`로 새 폴더를 만들고 컨테이너의 모든 blob을 내려받아 그 안의 경로로 저장한 뒤 경로 문자열 목록을 돌려준다. blob 이름의 하위 폴더 구조는 유지한다. 이름에서 `\`를 `/`로 바꾼 뒤 절대 경로이거나 `..` 요소가 있거나 해석 결과가 임시 폴더 밖이면 `ValueError("Unsafe blob name: ...")`를 내고, 이미 내려받은 파일은 남은 채 전체 로드가 중단되어 호출자까지 전파된다. 임시 폴더는 지우지 않는다. SDK 호출은 동기다. | 코드 확인 (C-06), 실행 확인(스텁, §3) |
| R-21 | azure 문서 변환과 컨텍스트 | 경로 목록을 `DocumentLoader(paths).load()`에 넣어 R-12~R-15의 규칙으로 D를 만든다(리스트 입력이므로 파일만, 컨테이너가 비면 R-15의 `ValueError`). `url`은 blob 파일의 basename이라 폴더 접두가 사라진다. 이어서 `_get_context_by_web_search(query, D)`를 부르는데 `query_domains`를 넘기지 않아 `None`(→`[]`)이다(`local`·`hybrid`·`langchain_documents`는 넘긴다). 이 분기에는 `vector_store` 적재가 없다. | 코드 확인 (C-01, C-04), 실행 확인(스텁, §3, §6) |

**langchain_documents**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-22 | `report_source == "langchain_documents"`, `source_urls` 없음 | `LangChainDocumentLoader(documents).load()`가 문서마다 `{raw_content: page_content, url: metadata.get("title", "")}`를 만든다. 분기는 `metadata_source_index` 없이 호출하므로 키는 항상 `"title"`이고 없으면 `""`다. 파일 로더와 달리 빈 `page_content`를 거르지 않고, 문서가 0개여도 오류가 없어 빈 목록을 돌려준다(그러면 R-09대로 웹 검색과 같은 동작). `documents`가 `None`이면 반복에서 `TypeError`가 나 호출자까지 전파된다. `vector_store`가 있으면 D를 적재한다(제외). 이어서 R-06 경로(`query_domains` 포함)로 간다. | 코드 확인 (C-01, C-07), 실행 확인(스텁, §4, §6) |
| R-23 | `report_source == "langchain_vectorstore"`, `source_urls` 없음 (제외 경계) | `_get_context_by_vectorstore(query, vector_store_filter)`로 간다. 이 스펙은 그 안을 다루지 않는다(사용자 제외: 자체 벡터스토어). 결과 타입은 문자열이 아니라 서브쿼리별 결과 리스트다. | 코드 확인 (C-01), 실행 확인(스텁, §6: 분기만) |

**source_urls**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-24 | `source_urls`가 truthy → `_get_context_by_urls(urls)` | ① `visited_urls`에 없는 URL만 입력 순서대로 남기고, 남기는 즉시 `visited_urls`에 추가한다(섞지 않는다). ② 그 목록을 `browse_urls`에 넘긴다(목록이 비어도 호출). ③ `vector_store`가 있으면 스크랩 결과를 적재한다(제외). ④ 원 질문(`researcher.query`) 하나로 `get_similar_content_by_query(query, scraped_content)`를 불러 그 문자열을 돌려준다. 서브쿼리 계획, LLM 호출, 초기 웹 검색, 병렬 처리는 없다. 스크랩에 실패한 URL도 ①에서 `visited_urls`에 들어가 같은 연구 안에서는 다시 시도되지 않는다. | 코드 확인 (C-02), 실행 확인(스텁, §8) |
| R-25 | 새 URL이 없거나 모두 스크랩 실패 | 선별에는 빈 목록이 들어간다. 기본 프롬프트 패밀리에서는 선별 결과가 빈 문자열이라 `research_data`가 `""`이며, 웹 경로의 `[]`와 다르다. `verbose`이면 이때 "unable to find relevant context in the provided sources" 로그(`answering_from_memory`)가 나가고 그 뒤 처리는 그대로 이어진다. | 코드 확인 (C-01, C-02, select.py:71-77, prompts.py:555-561). 빈 문자열이라는 결과는 `select_context`(경계)와 기본 패밀리 읽기로 도출, 미실행 |
| R-26 | `source_urls`가 truthy이고 `complement_source_urls`가 truthy | R-24가 끝난 뒤 순차로 `_get_context_by_web_search(query, [], query_domains)`(문서 없는 웹 전체 파이프라인)를 부른다. `source_urls`는 이미 `visited_urls`에 들어 있어 웹 검색이 같은 URL을 다시 가져가지 않는다. 두 결과 중 truthy인 것만 `" "`로 이어 붙인 문자열이 `research_data`다(둘 다 비면 `""`). `complement_source_urls`가 거짓이면 이 단계는 없다. `source_urls`가 비어 있으면 URL 분기 자체가 안 타므로 `complement_source_urls`는 무시된다. | 코드 확인 (C-01), 실행 확인(스텁, §6) |

**document_urls (온라인 문서)**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-27 | `OnlineDocumentLoader.load()` | `urls`를 목록 순서대로 하나씩(병렬이 아님) 처리한다. URL마다: `validate_url`이 `UnsafeURLError`면 `Skipping unsafe document URL ...`을 출력하고 요청 없이 건너뛴다. 통과하면 `User-Agent: Mozilla/5.0`, `timeout=6`으로 GET하고, 상태가 200이 아니면 `Failed to download <url>: HTTP <상태>` 후 건너뛴다. 200이면 본문 전체를 메모리로 읽어(크기 상한 없음) `NamedTemporaryFile(delete=False, suffix=확장자)`에 쓰고 R-28의 로더로 읽으며, 읽기가 실패해도 `finally`에서 임시 파일을 지운다. `aiohttp.ClientError`와 그 밖의 예외는 출력 후 그 URL만 건너뛴다. | 코드 확인 (C-05), 실행 확인(스텁, §2) |
| R-28 | 온라인 문서의 확장자와 로더 | 확장자는 URL에서 `?` 앞부분만 잘라 `os.path.splitext`한 뒤 소문자로 바꾼 값이다. `#fragment`는 자르지 않아 `a.txt#frag`의 확장자는 `.txt#frag`가 되어 로더가 없다. 로더는 C-05의 9개(`pdf`, `txt`, `doc`, `docx`, `pptx`, `csv`, `xls`, `xlsx`, `md`)로, 로컬 로더의 부분집합이다(`epub`, `html`, `htm` 없음). 확장자가 없거나 지원하지 않으면 다운로드까지는 하고 결과는 빈 목록이다. 이 로더는 로더 생성도 `try` 안이라 생성자 예외는 그 URL의 빈 결과가 된다. | 코드 확인 (C-05), 실행 확인(스텁, §2) |
| R-29 | URL 안전 검사 경계 | `validate_url`(scrapers.md R-04·R-05와 같은 함수): 스킴은 `http`·`https`만, 호스트가 있어야 하고, 호스트를 풀어 얻은 모든 주소가 private·loopback·link-local·reserved·multicast·unspecified가 아니어야 통과한다. 환경변수 `ALLOW_PRIVATE_URLS`가 `1`/`true`/`yes`/`on`이면 DNS·주소 검사를 건너뛴다. 거절한 URL에는 요청을 보내지 않는다. 리다이렉트로 옮겨 간 주소를 다시 검사하는 코드는 없다(scrapers.md의 확인 한계와 같다). 스킴이 `file`이거나 사설 주소인 URL은 `document_urls`에서는 조용한 `print` 후 건너뛰기이고, `source_urls`에서는 스크랩 내부에서 URL 하나가 결과에서 빠지는 것이다. | 코드 확인 (C-10), 실행 확인(스텁, §2: `file://`, 127.0.0.1 거절과 `ALLOW_PRIVATE_URLS=true` 허용) |
| R-30 | 온라인 문서 결과 | `page_content`가 truthy인 페이지만 `{raw_content, url: page.metadata.get("source")}`로 만든다. 로더에는 원 URL이 아니라 임시 파일 경로를 주므로, 로더가 `source`를 입력 경로로 채우면 `url`은 (이미 지워진) 임시 파일 경로가 되어 원 URL이 아니다. 이 경우 `hybrid`에서 문서 출처 이름이 임시 경로로 보인다. 문서가 하나도 없으면(모든 URL이 안전하지 않거나 실패, 미지원 확장자) `ValueError("🤷 Failed to load any documents!")`이고 R-16대로 `hybrid` 전체가 실패한다. | 코드 확인(`source`를 그대로 옮기는 규칙), 추론(실제 로더가 `source`를 입력 경로로 채움), 실행 확인(스텁: 스텁이 입력 경로를 `source`로 채우도록 만든 가정, §2) |

**다른 호출자와의 경계**

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-31 | 상세 보고서(`DetailedReport`) 경유 | 초기 연구자에게는 `report_source`, `source_urls`, `document_urls`, `complement_source_urls`를 넘기지만 `documents`는 받지도 넘기지도 않는다. 서브토픽 연구자에게는 `report_source`, `source_urls`, `complement_source_urls`만 넘기고 `document_urls`는 넘기지 않는다. 그래서 상세 보고서에서 `langchain_documents`는 `documents=None`의 `TypeError`가 되고, `hybrid`의 `document_urls`는 서브토픽에서 `DOC_PATH` 폴더로 바뀐다. 상세 보고서 스펙(아직 없음)의 몫이므로 이 스펙은 사실만 적는다. | 코드 확인 (detailed_report.py:47-59, :140-158), 실행 확인(스텁, §6: `documents=None`의 `TypeError`는 conduct 쪽만) |

- 불변식:
  - `source_urls`가 truthy인 한 `report_source`, `document_urls`, `DOC_PATH`, 문서 로더는 쓰이지 않는다.
  - 문서 로더(`DocumentLoader`, `OnlineDocumentLoader`)는 문서를 하나도 얻지 못하면 항상 `ValueError`이고 빈 목록을 돌려주지 않는다. `LangChainDocumentLoader`만 빈 목록을 돌려줄 수 있다.
  - 문서 패스는 `visited_urls`·`research_sources`·`research_images`를 바꾸지 않는다.
  - 문서를 넘긴 웹 검색 경로에서도 초기 웹 검색은 정확히 한 번(패스당) 일어난다.
  - 전제: 문서 순서는 `os.walk`의 파일 시스템 순서에 의존하므로 같은 폴더라도 OS에 따라 달라질 수 있다.
- 미결정: 없음
- 확인 한계:
  - `langchain_community`, `aiohttp`, `azure-storage-blob` 등이 설치되어 있지 않아 실제 문서 로더·HTTP 클라이언트·Azure SDK의 동작은 실행하지 못했다. 코드가 쓰는 속성(`page_content`, `metadata`)과 호출 순서만 대체물로 확인했다. 그래서 pdf가 쪽 단위 문서로 나뉘는지, `csv`·`xls`·`xlsx`가 항목 단위인지(`mode="elements"` 인자에서 짐작할 뿐), `docx`·`md`·`html`이 문서 하나로 나오는지 같은 분할 단위, `metadata`의 `source`·`title` 키, 생성자의 선택 패키지 검사는 미확인이다. 이 스펙은 이를 "문서 파서 라이브러리의 계약"(1.2 표)으로 두고, 분할 단위가 선별 결과에 미치는 영향은 context-selection.md가 다룰 때 다시 본다.
  - `timeout=6`을 총 시간 6초로 해석하는지, 리다이렉트를 따라가는지는 `aiohttp`의 동작이라 미확인이다(리다이렉트를 따른다고 보는 것은 추론).
  - `AZURE_*` 환경변수가 없을 때 SDK가 어떻게 실패하는지, Blob 개수·크기가 큰 경우의 동작은 확인하지 못했다.
  - `select_context`의 출력 형식과 `source`/`url` 표기는 context-selection.md(아직 없음)가 정한다. R-25의 빈 문자열은 기본 프롬프트 패밀리 기준이다.
  - 원본 테스트는 열지 않았다. 이름만 확인했다: `tests/test_document_loader_error_message.py`, `test_document_loader_metadata_source.py`, `test_online_document_extension.py`, `test_azure_document_loader.py`, `test_empty_source_urls_notification.py`, `test_planning_sources.py`, `documents-report-source.py`.

### 1.5 필수 코드 참조

라이선스: 인용 허용 여부는 overview 1절을 따른다. Apache License 2.0(`LICENSE`)이고 `pyproject.toml`은 MIT로 적어 표기가 어긋난다. 이 스펙은 코드를 옮겨 적지 않고 위치만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/skills/researcher.py:144-209` `ResearchConductor.conduct_research`의 소스 분기 | 분기 순서(`source_urls` → `web` → `local` → `hybrid` → `azure` → `langchain_documents` → `langchain_vectorstore`), 각 분기가 부르는 로더·경로, `asyncio.gather` 병렬 호출, 보완 결합 `" ".join`, 맞는 분기가 없으면 `research_data = []`. 벡터스토어 줄(`:170-171`, `:180-181`, `:203-204`, `:208-209`)은 제외 | R-01~R-03, R-10, R-16~R-18, R-21~R-23, R-26 |
| C-02 | `researcher.py:245-261` `_get_context_by_urls` | 새 URL만 스크랩하고 원 질문 하나로 선별하는 순서(`vector_store` 줄 `:255-256`은 제외). `_get_new_urls`(`:813-834`)는 R-24 글로 풀었고 pipeline C-08과 같다 | R-24, R-25 |
| C-03 | `researcher.py:387-397`, `:605-613` `_get_context_by_web_search`·`_process_sub_query` | `scraped_data`가 비어 있지 않으면 초기 컨텍스트와 서브쿼리별 검색·스크랩을 생략하고 D로 선별하는 규칙. 나머지 흐름은 pipeline C-11·C-12 | R-06, R-07, R-09, R-17 |
| C-04 | `gpt_researcher/document/document.py:17-101` `DocumentLoader.load`, `_load_document` | 경로 순회(폴더·리스트), 확장자 추출, 확장자→로더 사전 12개(`pdf`→PyMuPDFLoader, `epub`→UnstructuredEPubLoader, `txt`→TextLoader, `doc`·`docx`→UnstructuredWordDocumentLoader, `pptx`→UnstructuredPowerPointLoader, `csv`→UnstructuredCSVLoader(`mode="elements"`), `xls`·`xlsx`→UnstructuredExcelLoader(`mode="elements"`), `md`→UnstructuredMarkdownLoader, `html`·`htm`→BSHTMLLoader), 실패 처리, 페이지→문서 변환, 빈 결과 `ValueError` | R-12~R-15, R-21 |
| C-05 | `gpt_researcher/document/online_document.py:17-104` `OnlineDocumentLoader` | 순차 다운로드, 검증·상태·예외 처리, 임시 파일 생성과 삭제, 확장자 추출(`_get_extension`), 로더 사전 9개(`pdf`, `txt`, `doc`, `docx`, `pptx`, `csv`, `xls`, `xlsx`, `md`), 결과 변환(`metadata["source"]`), 빈 결과 `ValueError` | R-27, R-28, R-30 |
| C-06 | `gpt_researcher/document/azure_document_loader.py:6-37` `AzureDocumentLoader.load`, `_get_blob_path` | 임시 폴더에 blob 저장, 안전한 경로 규칙과 `ValueError` | R-20 |
| C-07 | `gpt_researcher/document/langchain_document.py:10-24` `LangChainDocumentLoader.load` | `Document`→`{raw_content, url}` 변환과 기본 키 `"title"` | R-22 |
| C-08 | `gpt_researcher/utils/enum.py:30-51` `ReportSource` | 값 목록 7개와 문자열 값 | R-01, R-02 |
| C-09 | `gpt_researcher/prompts.py:563-566`, `:756-775`, `:795-803`, `:831-834`, `:879-886` `join_local_web_documents`와 `prompt_family_mapping` | 기본·Granite 패밀리별 결합 문자열과 이름→패밀리 매핑 | R-18 |
| C-10 | `gpt_researcher/utils/url_security.py:35-116` `ALLOWED_SCHEMES`, `_private_urls_allowed`, `_is_disallowed_ip`, `validate_url` | 스킴·호스트·주소 범주 검사와 `ALLOW_PRIVATE_URLS` | R-29 |
| C-11 | `gpt_researcher/agent.py:143-155` `GPTResearcher.__init__` | `report_source` 대체 규칙과 인자 저장(`source_urls`, `document_urls`, `complement_source_urls`, `documents`) | R-04 |
| C-12 | `gpt_researcher/config/config.py:51-52`, `:63-67`, `:139-146`, `:248-250` `Config.__init__`, `_set_attributes`, `_set_doc_path`, `validate_doc_path`와 `config/variables/default.py:33-34` | `DOC_PATH` 환경변수 덮어쓰기, 폴더 생성 조건과 실패 시 기본값 복귀, 기본값 `REPORT_SOURCE="web"`·`DOC_PATH="./my-docs"` | R-11 |

### 1.6 수락 사례

출처: T-ID마다 표기한다. "실행 §N"은 `artifacts/gpt-researcher/source-modes-demos/demo_source_modes.out`의 해당 절을 실제로 관찰한 사례이고(대체물은 2.1 끝 참고), "도출"은 구현에서 도출했고 실행하지 않았다. 문서 파서·HTTP·Azure·검색·스크랩·선별은 대체물이라 그 실제 결과(분할 단위, 선별 품질 등)는 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 | 출처 |
|---|---|---|---|---|
| T-01 | R-01, R-03 | `report_source="local"`, `source_urls=["u1","u2"]`, `DOC_PATH`가 없는 폴더 | URL 경로만 호출된다. 문서 로드·`ValueError`가 없다 | 실행 §6 |
| T-02 | R-01 | `report_source="web"`, `source_urls=[]` | 웹 검색 경로(문서 없음)가 호출된다 | 실행 §6 |
| T-03 | R-02 | `source_urls` 없이 `report_source`가 `"static"`, `"doc"`, `"web_search"`, `"online"`, `"Local"`, `None` 각각 | 어떤 경로도 호출되지 않고 `[]`가 반환된다. 예외 없음 | 실행 §6 |
| T-04 | R-02, R-03 | `report_source="static"`, `source_urls=["u1"]` | URL 경로로 간다(`static`이어도) | 도출 (T-01과 같은 분기) |
| T-05 | R-04 | `GPTResearcher(report_source="")`, 환경변수 `REPORT_SOURCE=local` | 필드 `report_source`는 `"local"`(`cfg.report_source`가 `"local"`임은 §9 D에서 관찰). 인자를 생략하면 `"web"`이다 | 도출 + 실행 §9 |
| T-05a | R-11 | 기본 설정에서 `DOC_PATH=E`(없는 폴더) / JSON 설정 `{"REPORT_SOURCE":"local","DOC_PATH":J}`와 환경변수 `DOC_PATH=E` / JSON 설정의 `DOC_PATH`가 일반 파일 아래 경로 / 환경변수 `REPORT_SOURCE=local`만 | `doc_path=E`, 폴더 안 만듦 / `doc_path=J`, `J`만 만들어지고 `E`는 만들어지지 않음 / 경고 출력 후 `doc_path="./my-docs"` / `cfg.report_source="local"`이지만 폴더는 안 만들어짐 | 실행 §9 (스텁) |
| T-06 | R-12~R-14 | 폴더에 `a.txt`, `B.TXT`, `notes.md`, `page.html`, `data.xyz`, `README`(확장자 없음), `empty.txt`(빈 파일), `doc.pdf`, `sub/c.txt`, `sub/a.txt` | 문서 8개: `B.TXT`, `a.txt`(둘), `c.txt`, `doc.pdf`(2쪽이라 2개), `notes.md`, `page.html`. `data.xyz`·`README`는 조용히 빠지고 `empty.txt`도 빠진다. `url`은 basename이라 `a.txt` 두 개가 구분되지 않는다. 로더 생성자는 파일마다 12번 불린다 | 실행 §1 (스텁: 쪽 수는 스텁이 정한 값) |
| T-07 | R-12 | 리스트 `[a.txt, 폴더, 없는 파일, sub/c.txt, data.xyz]` | `a.txt`, `c.txt`만 로드. 폴더·없는 파일·미지원은 조용히 건너뜀 | 실행 §1b |
| T-08 | R-15 | 없는 폴더 / 빈 폴더 / 유효 파일 없는 리스트 | 각각 `ValueError("🤷 Failed to load any documents!")`. 정수 `path`는 `ValueError("Invalid type for path. ...")` | 실행 §1b, §1c |
| T-09 | R-13 | `.md` 로더의 `.load()`가 예외 | `Failed to load md document: <경로>`와 예외 출력, 나머지 파일은 정상 로드 | 실행 §1c (스텁) |
| T-10 | R-13 | 어느 로더 하나의 생성자가 예외(예: epub) | 모든 파일이 `Failed to load document : <경로>`로 실패하고 `ValueError`. 실제 로더가 그렇게 예외를 내는지는 미검증 | 실행 §1c (스텁 가정) |
| T-11 | R-06, R-07 | `local`, D=2개, 서브쿼리 `sq1`·`sq2`(원 질문 `Q`가 덧붙음) | 초기 검색 1회, 계획 1회, 선별은 `sq1`, `sq2`, `Q` 세 번(각각 D 2개 전체). 서브쿼리 스크랩 없음. `visited_urls` 변화 없음. 결과는 세 선별 결과를 공백으로 이은 문자열 | 실행 §7 |
| T-12 | R-09 | 같은 입력에서 D=`[]` | 초기 결과 스크랩·선별(초기 컨텍스트) 후 서브쿼리마다 스크랩·선별. 곧 웹 경로 | 실행 §7 |
| T-13 | R-16 | `hybrid`, `document_urls` 있음, `DOC_PATH`는 없는 폴더 / `document_urls` 없음 | 앞의 것은 온라인 로더로 D를 만들고 `DOC_PATH`를 읽지 않는다. 뒤의 것은 `DOC_PATH`에서 만든다 | 실행 §6 |
| T-14 | R-17, R-18 | `hybrid`, 두 패스 정상 | 문서 패스(D 있음)와 웹 패스(`[]`) 두 번 호출되고 결과는 `Context from local documents: <문서 패스>\n\nContext from web sources: <웹 패스>` | 실행 §6 |
| T-15 | R-16 | `hybrid`, `DOC_PATH`가 빈 폴더 | `ValueError`가 전파되고 웹 패스는 호출되지 않는다 | 실행 §6 |
| T-16 | R-18 | 두 패스 결과가 모두 `[]`, 기본 패밀리 / `granite3.3`·`granite3` | `"Context from local documents: []\n\nContext from web sources: []"` / `TypeError` | 실행 §5 (join 함수만) |
| T-17 | R-27, R-29 | `document_urls=[file:///etc/passwd, http://127.0.0.1/x.txt, 정상 pdf, 404 txt, 확장자 없는 URL, html URL, 연결 오류 txt, 정상 txt]` | 앞 두 URL은 요청 없이 `Skipping unsafe document URL ...`. 나머지 6개는 요청이 나간다. 문서: pdf(스텁 2쪽)와 정상 txt. 404·연결 오류·확장자 없음·html은 건너뜀. 요청 헤더는 `{'User-Agent': 'Mozilla/5.0'}`, `timeout=6` | 실행 §2 (aiohttp·로더 스텁) |
| T-18 | R-28 | URL `https://h.example/Report.PDF?sig=1`, `http://h/a`, `http://h/a.tar.gz`, `http://h/a.txt#frag`, `http://h/a.TXT` | 확장자 `.pdf`, `""`, `.gz`, `.txt#frag`, `.txt` | 실행 §2 |
| T-19 | R-29 | `ALLOW_PRIVATE_URLS=true`, `http://127.0.0.1/x.txt` | 요청이 나가고 문서가 만들어진다 | 실행 §2 |
| T-20 | R-30 | 온라인 pdf·txt 성공(스텁 로더가 `source`를 입력 경로로 채움) | 문서의 `url`이 원 URL이 아니라 임시 파일 경로이고 그 파일은 이미 없다 | 실행 §2 (스텁 가정) |
| T-21 | R-27, R-30 | `document_urls`의 모든 URL이 안전하지 않거나 미지원 | `ValueError("🤷 Failed to load any documents!")` | 실행 §2 |
| T-22 | R-19~R-21 | `azure`, `AZURE_CONTAINER_NAME`·`AZURE_CONNECTION_STRING` 설정, blob `report.txt`, `sub/dir/note.md` | SDK 호출에 환경변수 값이 들어간다. 임시 폴더에 하위 폴더 구조대로 저장. 문서 `url`은 `report.txt`, `note.md`. 선별 호출은 `query_domains` 없음. 임시 폴더는 남는다 | 실행 §3, §6 (SDK 스텁) |
| T-23 | R-20 | blob 이름 `../escape.txt`, `/abs.txt`, `a/../b.txt`, `a\..\b.txt` | 모두 `ValueError("Unsafe blob name: ...")`. `ok.txt`와 `../escape.txt`가 함께 있으면 전체 로드가 중단된다. 빈 컨테이너는 경로 `[]`이고 `DocumentLoader`에서 `ValueError` | 실행 §3 |
| T-24 | R-22 | `Document`: `title`이 `T1`, `title` 없음, 빈 본문에 `title`이 `T3` | url `T1`, `""`, `T3`. 빈 본문도 남는다. `[]`는 오류 없이 `[]`, `None`은 `TypeError` | 실행 §4 |
| T-25 | R-09, R-22 | `langchain_documents`, `documents` 2개 / `[]` / `None` | D 2개로 R-06 경로 / 문서 없는 웹 경로 / `TypeError` 전파 | 실행 §6 |
| T-26 | R-23 | `langchain_vectorstore`, `vector_store_filter={"k":"v"}`, `source_urls` 없음 | `_get_context_by_vectorstore(query, {"k":"v"})` 결과가 반환된다(제외 경계) | 실행 §6 (분기만) |
| T-27 | R-24 | `source_urls=[u1,u2]`, `visited_urls`에 `u1` 있음 | `browse_urls([u2])`, 원 질문 하나로 선별(`u2` 페이지만). `visited_urls`에 `u2`가 추가된다 | 실행 §8 |
| T-28 | R-24 | 새 URL이 없음(모두 방문) / 모두 스크랩 실패 | `browse_urls([])` 또는 실패 URL로 호출, 선별에는 빈 목록. `visited_urls`에 실패 URL이 남는다 | 실행 §8 (빈 문자열 결과는 R-25 도출) |
| T-29 | R-26 | `source_urls=[u1]`, `complement_source_urls=True` | URL 경로 뒤에 웹 검색 경로(문서 없음)가 호출되고 결과는 `"<URL 결과> <웹 결과>"` | 실행 §6 |
| T-30 | R-31 | 상세 보고서에서 `langchain_documents` | `DetailedReport`에 `documents` 인자가 없어 연구기가 `documents=None`으로 만들어지고 `TypeError` | 도출 (T-25의 `None` 사례와 detailed_report.py:47-59) |

## 2부. 근거

### 2.1 요구사항별 근거 지도

문서와 구현의 차이(구현을 사실로 썼다):
- `docs/docs/gpt-researcher/gptr/config.md:128`은 `REPORT_SOURCE`를 `doc`으로 설정할 수 있다고 안내하지만 `doc`에 대응하는 분기가 없어 `[]`가 된다(R-02). 열거형(`utils/enum.py:30-51`)의 값은 `web`, `local`, `azure`, `langchain_documents`, `langchain_vectorstore`, `static`, `hybrid`다.
- `docs/docs/gpt-researcher/context/local-docs.md:5`는 로컬 문서 형식을 PDF, 텍스트, CSV, Excel, Markdown, PowerPoint, Word로 적지만 코드는 `epub`, `html`, `htm`도 로드한다(R-13). `docs/docs/examples/hybrid_research.md:55`는 온라인 문서도 PDF, TXT, DOCX 등을 지원한다고 쓰는데, 온라인 로더는 `epub`·`html`·`htm`을 로드하지 않는다(R-28).
- `static`은 열거형 docstring이 "미리 정한 정적 콘텐츠"라고 설명하지만 분기 사슬에 대응이 없다. `docs/docs/examples/sample_sources_only.py:12`, CLI 선택지(`cli.py:112-119`)에 있는 `static`은 단독으로는 `[]`이고, `source_urls`와 함께 줄 때만 URL 경로가 돌아서 동작한다(R-02, R-03).
- `cli.py:279`와 `docs/docs/examples/detailed_report.md:58`은 상세 보고서에 `report_source="web_search"`를 준다. 이 값은 분기에 없으므로(실행 §6 `web_search` 사례) 그 `report_source`를 받는 연구기의 컨텍스트는 `[]`가 된다. `DetailedReport`가 이 값을 초기·서브토픽 연구기에 그대로 넘기는 것(detailed_report.py:51, :144)까지가 코드 확인이고, 보고서 전체가 빈 컨텍스트로 쓰이는지는 확인하지 않았다(추론).
- `docs/docs/gpt-researcher/handling-logs/simple-logs-example.md:25`의 `report_source = "online"`도 분기에 없는 값이다(R-02).
- 프런트엔드 값 이름: `frontend/index.html:214-219`는 `web`/`local`/`hybrid`/`azure`, `frontend/nextjs/components/Task/ResearchForm.tsx:138-147`은 `web`/`local`/`hybrid`를 제공하고 둘 다 `langchain_*`는 제공하지 않는다. `frontend/scripts.js:972`는 `report_source !== 'sources'`를 비교하지만 `sources`는 열거형에도 선택지에도 없는 값이다. 서버 요청 모델의 `report_source`는 `str`일 뿐 검증이 없다(`backend/server/app.py:56`).
- `researcher.py:182-183`의 주석은 `visited_urls`가 hybrid의 두 패스를 걸쳐 중복을 거른다고 하지만, 문서 패스는 URL을 스크랩하지 않아 `visited_urls`를 쓰지 않는다(R-17, 실행 §7).
- `docs/docs/examples/hybrid_research.md:47`의 "REPORT_SOURCE를 default.py에서 빈 문자열로 설정"의 의도는 확인하지 못했다. 코드에서 설정의 `REPORT_SOURCE`가 쓰이는 곳은 생성자의 `report_source` 대체(R-04)와 `Config`의 `DOC_PATH` 폴더 생성 조건(R-11)뿐이다.
- `docs/docs/gpt-researcher/context/azure-storage.md`는 `azure-storage-blob`을 `requirements.txt`에 추가하라고 안내하고, 실제로 `requirements.txt`에는 azure 줄이 없으며 `pyproject.toml:185`에서 선택 의존(extra)이다. 분기 안의 지연 import와 일치한다(R-19).

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `researcher.py:145`, `:163`, `:166`, `:175`, `:189`, `:199`, `:208`; C-08 | 코드를 읽고 `conduct_research`를 실제로 불러 분기별 호출을 기록(실행 §6). 하위 메서드는 기록기로 대체 |
| R-02 | C-01 `researcher.py:112`, `:208-212`; `utils/enum.py:50`; `ReportSource.Static` 사용처 없음(grep) | 코드를 읽음. 실행 §6의 6개 값 사례 |
| R-03 | C-01 `researcher.py:145-162` | 실행 §6 (`local` + `source_urls`, 없는 폴더) |
| R-04 | C-11 `agent.py:58`, `:143`, `config/variables/default.py:33` | 코드를 읽음. `GPTResearcher` 생성자는 전체 임포트가 무거워 실행하지 않았다. `cfg.report_source`가 환경변수 값을 따르는 부분만 §9 D로 관찰 |
| R-05 | `prompts.py:278`, `:367`, `:440`; `skills/writer.py:42`; `skills/deep_research.py:442-447` | 코드를 읽음. 세 줄의 `if report_source == ReportSource.Web.value` 존재와 deep의 `Web` 고정만 확인하고 프롬프트 본문은 읽지 않음 |
| R-06 | C-03 `researcher.py:365-366`, `:387-397`, `:605-613`; `actions/query_processing.py:44-81`(초기 검색 호출) | 코드를 읽고 실제 `_get_context_by_web_search`·`_process_sub_query`를 대체물로 둘러싸 실행(실행 §7): 초기 검색 1회, 계획, 서브쿼리별 선별 입력이 D 전체임을 관찰. 검색·스크랩·선별 내부는 대체 |
| R-07 | C-03, `researcher.py:813-834`(문서 패스에서 불리지 않음), `agent.py:684-698`(`research_sources` 변경은 `browse_urls` 쪽) | 코드를 읽음. 실행 §7에서 `visited_urls`가 변하지 않음을 관찰 |
| R-08 | `researcher.py:536-616` | 코드를 읽음. MCP 대체 실행은 하지 않음 |
| R-09 | C-03, `researcher.py:306-307`, `:606-607`; C-07 | 코드를 읽음. 실행 §6(`documents=[]`, `None`), §7(D=`[]`) |
| R-10 | C-01 `researcher.py:166-173` | 실행 §6 (`local`, 로더는 실제 `DocumentLoader`+스텁) |
| R-11 | C-12 `config.py:51-52`, `:63-67`, `:139-146`, `:248-250`, `default.py:33-34` | 코드를 읽고 실제 `Config()`를 환경변수·JSON 조합 다섯 가지로 실행(실행 §9). LLM·임베딩 검증용 보조 모듈(`json_repair`, 제공자 목록, 검색기 이름, `typing_extensions`)만 스텁 |
| R-12 | C-04 `document.py:22-41` | 실행 §1, §1b, §1c (스텁 로더) |
| R-13 | C-04 `document.py:69-101`, `:72-85` | 실행 §1, §1c. 로더는 스텁이라 실제 생성자·`load()`는 미검증. 로컬 로더 12개와 온라인 9개는 사전의 키를 센 것 |
| R-14 | C-04 `document.py:50-62` | 실행 §1 (스텁 로더가 `source`에 경로를 넣음) |
| R-15 | C-04 `document.py:64-65` | 실행 §1c, §6 |
| R-16 | C-01 `researcher.py:175-181` | 실행 §6 (`document_urls`는 실제 `OnlineDocumentLoader`+aiohttp 스텁) |
| R-17 | C-01 `researcher.py:182-187`, C-03 | 실행 §6(호출 두 번), §7(`visited_urls`). `gather` 예외 전파는 asyncio 표준 동작이라 실행하지 않음 |
| R-18 | C-09 `prompts.py:563-566`, `:772-773`, `:795-803`, `:831-834`, `:762-767` | 세 `join` 함수를 `ast`로 소스에서 꺼내 실행(실행 §5). 클래스 전체와 `prompt_family` 생성은 실행하지 않음 |
| R-19 | C-01 `researcher.py:189-197`; `pyproject.toml:177-185`; `requirements.txt` | 실행 §6(환경변수가 SDK 호출에 들어감, SDK는 스텁). 선택 의존은 grep으로 확인 |
| R-20 | C-06 `azure_document_loader.py:11-37` | 실행 §3(SDK 스텁, 실제 파일 쓰기). 임시 폴더 비삭제는 코드에 삭제가 없는 것과 실행 §3의 존재 확인 |
| R-21 | C-01 `researcher.py:195-197`, C-04 | 실행 §3, §6 |
| R-22 | C-07 `langchain_document.py:15-24`, C-01 `researcher.py:199-207` | 실행 §4, §6 (`Document`는 스텁) |
| R-23 | C-01 `researcher.py:208-209` | 실행 §6 (분기만, 기록기) |
| R-24 | C-02 `researcher.py:245-261`, `:813-834` | 실행 §8 (스크랩·선별은 기록기). 선별 호출이 `context_manager.py:38-64`의 `get_similar_content_by_query`임은 코드로 확인 |
| R-25 | C-01 `researcher.py:150-156`; `context/select.py:71-77`; `prompts.py:555-561` | 코드를 읽음. 빈 목록이 `select_context`의 "내용이 적으면 필터 없이" 분기(`total_chars=0`, 페이지 0개)를 타고 `pretty_print_docs`가 빈 문자열을 돌려준다는 추적. 실행하지 않음 |
| R-26 | C-01 `researcher.py:157-162` | 실행 §6 |
| R-27 | C-05 `online_document.py:22-69` | 실행 §2 (aiohttp·로더 스텁, `validate_url`은 실제 소스). 실제 `getaddrinfo`는 IP 리터럴만 거쳤다 |
| R-28 | C-05 `online_document.py:71-96`, `:98-104` | 실행 §2 (`_get_extension`은 실제 소스). 로더 사전 키는 코드에서 셈 |
| R-29 | C-10 `url_security.py:35-116`; `online_document.py:5`, `:41-45` | 실행 §2. scrapers.md R-04·R-05(같은 함수)와 일치 |
| R-30 | C-05 `online_document.py:26-31`, `:57-61`, `:93-94` | 규칙(`metadata.get("source")`)은 코드 확인과 실행 §2. 실제 로더가 `source`에 임시 경로를 넣는지는 미설치로 확인하지 못해 추론 |
| R-31 | `detailed_report.py:47-59`, `:140-158` | 코드를 읽음. 실행 §6의 `documents=None` 사례로 `TypeError` 경로를 확인(상세 보고서 자체는 실행하지 않음) |
| T-01~T-03, T-05a, T-06~T-29 | 해당 R-ID의 근거 | 위 표의 "출처" 열대로 실행 관찰. 출력은 [demo_source_modes.out](../../../artifacts/gpt-researcher/source-modes-demos/demo_source_modes.out) |
| T-04, T-05, T-30 | 해당 R-ID의 근거 | 도출(T-05는 `cfg.report_source` 부분만 실행 §9). `GPTResearcher` 생성자와 상세 보고서는 실행하지 않았다 |

**실행 기록**(2026-10-22, Python 3.12.13, `python -I demo_source_modes.py`): 스크립트와 출력은 `artifacts/gpt-researcher/source-modes-demos/`의 [demo_source_modes.py](../../../artifacts/gpt-researcher/source-modes-demos/demo_source_modes.py), [demo_source_modes.out](../../../artifacts/gpt-researcher/source-modes-demos/demo_source_modes.out)이다. 새 패키지를 설치하지 않았고 네트워크를 쓰지 않았으며 `repos/` 안 파일을 고치지 않았다.
- 실제 소스 그대로 실행한 것: `skills/researcher.py`의 `ResearchConductor`(`conduct_research`, `_get_context_by_web_search`, `_process_sub_query`, `_get_context_from_initial_results`, `_combine_mcp_and_web_context`, `_get_new_urls`, `_get_context_by_urls`), `document/document.py`, `online_document.py`, `azure_document_loader.py`, `langchain_document.py`, `utils/url_security.py`, `utils/enum.py`, `config/config.py`의 `Config()` 생성(DOC_PATH 관련만 관찰), `prompts.py`의 `join_local_web_documents` 세 함수(`ast`로 추출). `gpt_researcher/__init__.py`·`skills/__init__.py`·`utils/__init__.py`는 건너뛰었다. `GPTResearcher` 생성자(`agent.py`)는 실행하지 않았다(R-04는 코드 확인).
- 대체물과 검증하지 않은 것: `langchain_community.document_loaders`의 로더 9종은 생성자와 `.load()`만 흉내 낸 스텁이다(`txt`·`md`·`html`은 파일 원문을 그대로, pdf는 아무 파일이나 2쪽을 돌려주고, 나머지는 파일명을 담은 한 줄). 그래서 실제 파서의 분할 단위, `metadata` 키, 생성자의 의존 패키지 검사는 검증하지 않았다. `langchain_core.documents.Document`, `aiohttp`(스크립트로 정한 응답, 소켓 없음), `azure.storage.blob`(메모리 가짜)도 스텁이다. `retrievers`, 스크랩, LLM 계획, `select_context`는 기록기로 바꿨고, 연구기 객체는 코드가 읽는 필드만 가진 `SimpleNamespace`다. `choose_agent`는 에이전트·역할을 미리 채워 호출되지 않게 했다. 출력의 경로는 세션 스크래치 폴더 안이다.

### 2.2 코드 읽는 순서

1. `skills/researcher.py:97-243` `conduct_research`: 분기 사슬(`:144-209`)과 후처리. 이 스펙의 중심이다.
2. `skills/researcher.py:298-408` → `:520-663`: 웹 검색 경로에 문서(`scraped_data`)가 들어올 때의 차이(`:387-397`, `:606-613`).
3. `document/document.py` → `online_document.py` → `azure_document_loader.py` → `langchain_document.py`: 로더 네 개. 로컬 로더가 기준이고 Azure는 그것에 경로만 넘긴다.
4. `skills/researcher.py:245-261`, `:813-834`: `source_urls` 경로.
5. `prompts.py:563-566`: `hybrid` 결합.

원본의 구현 전략은 "문서를 웹 페이지와 같은 모양의 dict(`raw_content`, `url`)로 바꿔 기존 선별 경로에 그대로 넣는 것"이다. 그래서 새 로더는 모양만 맞추면 되고 서브쿼리 계획과 선별 코드는 재사용된다. 대가로 문서 모드에서도 초기 웹 검색과 계획용 LLM 호출이 남는다(R-06). 이것이 의도인지는 코드 주석에 없어 추론이다.

### 2.3 비교·재사용 출처

없음.

## 적용 메모

없음.
