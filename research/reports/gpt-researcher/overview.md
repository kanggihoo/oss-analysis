---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
---

# GPT Researcher Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/assafelovic/gpt-researcher`
- **작업트리 상태**: Clean (shallow clone `--depth 50`, 2026-10-22, 마지막 커밋 2026-10-10)
- **분석 목적**: 학습 · 설계 참고. 특히 에이전트가 웹 검색 → 스크랩 → 컨텍스트 선별 → 보고서 작성을 어떻게 이어 붙이는지 본다.
- **라이선스**: LICENSE 파일은 Apache License 2.0 — `LICENSE`. README 맨 끝(`README.md:354`)도 "Apache 2 license"라고 쓴다. 반면 `pyproject.toml`(`license = "MIT"`)과 `setup.py:33`, `frontend/nextjs/package.json:102`는 MIT로 적는다. 같은 레포 안에서 표기가 어긋나 있고, 어느 쪽이 맞는지는 이 분석에서 판단하지 않는다. `frontend/vendor/`에는 bootstrap·dompurify·fontawesome·showdown의 LICENSE가 따로 있다. (코드 확인)
- **분석 대상 제품**: 루트 Python 패키지 `gpt-researcher`(`pyproject.toml` 0.16.0, 라이브러리 `gpt_researcher/` + FastAPI 서버 `backend/`). 같은 레포에 들어 있는 별도 배포 단위: `multi_agents/`(LangGraph, 자체 `langgraph.json`·`requirements.txt`), `deep_agents/`(deepagents 예제·벤치마크), `frontend/nextjs/`(npm `gpt-researcher-ui`), `docs/`(Docusaurus 사이트), `docs/npm/`(WebSocket 클라이언트 npm), `docs/discord-bot/`, `terraform/`, `evals/`.
- **스펙 범위**: 2026-10-22 승인 — 연구 파이프라인, 소스 모드, 검색 Retriever 패밀리, 스크래퍼 패밀리, 컨텍스트 선별, 보고서 작성, 상세 보고서, Deep Research, MCP 연동(9행). 소스 모드에서는 `langchain_vectorstore`와 `vector_store` 인자 경로를 쓰지 않는다(사용자 제외). 제외: LLM·임베딩·설정 (이유: 사용자 제외, 다른 스펙의 경계로만 다룸), 이미지 생성, 서버 API, 보고서 채팅, CLI, multi_agents, deep_agents, 웹 프런트엔드, 에이전트 통합 입구, 배포, 문서 사이트·클라이언트, 평가 (이유: 사용자 제외)

---

## 2. 프로젝트 개요

README는 GPT Researcher를 "웹과 로컬 문서로 조사하고 인용이 달린 보고서를 쓰는 오픈 deep research 에이전트"라고 소개한다(`README.md:25`). 계획(planner)이 조사 질문을 만들고, 실행 에이전트가 각 질문에 맞는 자료를 모으고, publisher가 모은 결과를 보고서로 합치는 구조를 내세운다(`README.md:54`).

코드에서는 이 구조가 `GPTResearcher` 클래스 하나로 모인다. `conduct_research()`가 서브쿼리 계획 → 검색 → 스크랩 → 컨텍스트 선별까지 하고, `write_report()`가 그 컨텍스트로 보고서를 쓴다(`gpt_researcher/agent.py:343`, `:463`). 서버, CLI, multi_agents가 모두 이 클래스를 쓴다. (코드 확인)

참고: 이 레포의 `memory`(`gpt_researcher/memory/embeddings.py`)는 에이전트의 장기 기억이 아니라 **임베딩 생성기**다. README의 "Maintains memory and context throughout research"는 한 번의 조사 안에서 컨텍스트를 모아 두는 것을 뜻한다. (코드 확인: `embeddings.py:57` `Memory`)

### 기능 지도

<!--
OSS_ANALYSIS_WORKFLOW.md 2장 4번. 한 행 = 스펙 하나의 작업 단위(디렉터리가 아니라 사용 목적과 검증 경계로 묶은 동작).
- 같은 계약을 구현한 플러그인·추출기류는 한 행(패밀리)으로 묶는다.
- 구분: 핵심 / 부속(라이브러리 본체와 별개인 호스팅 서비스·결제·관리 도구 등). 부속은 스펙으로 쓸지 사용자에게 따로 묻는다.
- 선행: 재구현에 필요한 다른 행의 계약(런타임 호출 관계가 아니다).
- 상태: 미작성(파일 없음, 경로는 코드 표기) / draft / ready. 스펙의 status를 요약하며 스펙을 고칠 때 같이 고친다.
- 분할과 경로는 제안이다. 4장에서 병합·분리하면 고치고 이유를 적는다.
-->

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 연구 파이프라인 | 질문 → 에이전트 역할 선택 → 첫 retriever로 초기 검색 → 서브쿼리 계획 → 서브쿼리별 검색·스크랩·선별(병렬) → 컨텍스트 반환. 보고서 작성은 포함하지 않음. MCP 사전 실행·출처 curation·소스 분기는 경계만 | `gpt_researcher/agent.py` `GPTResearcher.conduct_research`(:343), `gpt_researcher/skills/researcher.py` `ResearchConductor.conduct_research`(:97), `_get_context_by_web_search`(:298), `_process_sub_query`(:520), `actions/query_processing.py`, `actions/agent_creator.py` | 설정·LLM 호출(스펙 안에서 경계만 정의) | 핵심 | [research-pipeline](capabilities/research-pipeline.md) · ready | 코드 확인(진입점·호출 경로·서브쿼리 계획 프롬프트) |
| 소스 모드 | `report_source`가 web / local / hybrid / azure / langchain_documents이거나 `source_urls`를 주면 검색 대상이 바뀜. `langchain_vectorstore`와 `vector_store` 경로는 사용자 제외 | `skills/researcher.py:144-209`(분기), `gpt_researcher/document/document.py` `DocumentLoader`(:19), `document/online_document.py`, `document/azure_document_loader.py`, `document/langchain_document.py` | 연구 파이프라인 | 핵심 | [source-modes](capabilities/source-modes.md) · ready | 코드 확인(분기) + 실행 확인(외부 문서 로더를 스텁으로 바꾼 상태) |
| 검색 Retriever 패밀리 | `RETRIEVER` 설정(쉼표 구분)에 따라 검색 엔진을 고름. 결과는 URL+snippet이고 대부분 이후 스크랩이 필요 | `gpt_researcher/actions/retriever.py` `get_retriever`(:16)·`get_retrievers`(:150), `retrievers/base.py`(`requires_scraping` 계약), 호출부 `skills/researcher.py` `_search_relevant_source_urls`(:851)와 `actions/query_processing.py` `get_search_results`(:44). `_search`(:975)는 호출처 없음 | 없음 | 핵심 | [retrievers](capabilities/retrievers.md) · draft | 코드 확인(등록부·공통 계약·호출부) / 어댑터 17개의 요청 변환은 미결정 |
| 스크래퍼 패밀리 | URL 목록을 받아 본문과 이미지를 추출. `SCRAPER` 설정(bs, browser, nodriver, firecrawl, tavily_extract, web_base_loader)과 URL 형태(pdf, arxiv)로 구현을 고름. 차단 페이지·단어 목록·미추출 PDF는 거름 | `gpt_researcher/skills/browser.py` `BrowserManager.browse_urls`(:37), `actions/web_scraping.py` `scrape_urls`(:12), `scraper/scraper.py` `Scraper`(:109)·`get_scraper`(:307), `utils/url_security.py`. `filter_urls`·`process_scraped_data`는 테스트 밖 호출처 없음 | 없음 | 핵심 | [scrapers](capabilities/scrapers.md) · draft | 코드 확인 + 실행 확인(URL 검증·판정 함수·이미지 선별) / firecrawl·tavily_extract·web_base_loader는 미확인 |
| 컨텍스트 선별 | 스크랩한 페이지에서 서브쿼리와 관련된 조각만 골라 컨텍스트로 만듦. `CONTEXT_FILTER`가 auto / jev / keyword / embeddings / none 중 하나를 고르고 실패하면 keyword로 내려감. `WrittenContentCompressor`·`VectorstoreCompressor`는 제외(상세 보고서·벡터스토어 몫) | `gpt_researcher/context/select.py` `resolve_context_filter`(:38)·`select_context`(:53), `context/jev_filter.py`, `context/lexical.py`, `skills/context_manager.py:38` | 스크래퍼 패밀리(입력 형식) | 핵심 | [context-selection](capabilities/context-selection.md) · draft | 코드 확인 + 실행 확인(keyword·jev, 라이브러리는 대체물) / embeddings 모드의 `EmbeddingsFilter` 동작은 미결정 |
| 보고서 작성 | 컨텍스트 → 보고서 마크다운. 보고서 타입, 톤, 언어, 분량, 인용 형식, 서론·결론, 목차·참고문헌·헤더 추출 순수 함수를 다룸 | `gpt_researcher/agent.py:463` `write_report`, `skills/writer.py` `ReportGenerator`(:20)·`write_report`(:49), `actions/report_generation.py` `generate_report`(:209), `actions/markdown_processing.py`, `gpt_researcher/prompts.py` | 연구 파이프라인 | 핵심 | [report-writing](capabilities/report-writing.md) · ready | 코드 확인 + 실행 확인(순수 함수·프롬프트 선택, LLM은 대체물) / LLM이 프롬프트 규칙을 지키는지는 미확인 |
| 상세 보고서 | 하위 주제를 정하고 주제별로 별도 `GPTResearcher`를 순차로 돌려 서론·목차·본문·결론·참고문헌을 이어 붙임. 공유 상태는 `visited_urls`·`existing_headers`·`global_written_sections` | `backend/report_type/detailed_report/detailed_report.py` `DetailedReport.run`(:84), `_get_subtopic_report`(:138), `_construct_detailed_report`(:197) | 연구 파이프라인, 보고서 작성 | 핵심 | [detailed-report](capabilities/detailed-report.md) · ready | 코드 확인 + 실행 확인(`GPTResearcher`를 대체물로 바꾼 상태) / 서브토픽 초안 제목은 사실상 미사용 |
| Deep Research | `report_type=deep`일 때 쿼리 트리를 재귀 탐색하고 learnings와 출처를 모아 컨텍스트로 돌려줌. breadth·depth는 설정 키 `DEEP_RESEARCH_*` | `gpt_researcher/skills/deep_research.py` `DeepResearchSkill`(:250)·`run`(:586), `agent.py:363`(분기)·`:415` `_handle_deep_research` | 검색 Retriever 패밀리, 연구 파이프라인, LLM 호출 | 핵심 | [deep-research](capabilities/deep-research.md) · draft | 코드 확인 + 실행 확인(LLM·검색을 대체물로 바꾼 상태) / `json_repair` 동작은 미결정 |
| MCP 연동 | `RETRIEVER`에 `mcp`를 넣고 `mcp_configs`를 주면 MCP 서버 도구로 조사. 전략 fast / deep / disabled | `gpt_researcher/mcp/client.py` `MCPClientManager`, `mcp/tool_selector.py`, `mcp/research.py`, `retrievers/mcp/retriever.py:27`, `skills/researcher.py:410` `_get_mcp_strategy`, `agent.py:217`·`:295` | 연구 파이프라인 | 핵심 | [mcp-client](capabilities/mcp-client.md) · ready | 코드 확인 + 실행 확인(MCP 서버·LLM은 대체물) / `langchain-mcp-adapters` 내부는 확인 한계 |
| LLM·임베딩·설정 | `provider:model` 문자열로 27개 제공자(`_SUPPORTED_PROVIDERS`) 중 하나를 고르고, FAST/SMART/STRATEGIC 모델·토큰 한도·환경변수 기본값을 관리. 비용을 집계 | `gpt_researcher/llm_provider/generic/base.py` `GenericLLMProvider.from_provider`(:146), `utils/llm.py` `create_chat_completion`(:41), `config/config.py`, `config/variables/default.py`, `memory/embeddings.py`, `utils/costs.py` | 없음 | 핵심 | `capabilities/llm-config.md` · 미작성 | 코드 확인(제공자 분기·기본값) / 비용 계산은 미확인 |
| 이미지 생성 | `IMAGE_GENERATION_ENABLED`이면 조사 뒤 보고서에 넣을 이미지를 계획·생성(google / modelslab). 기본은 꺼짐 | `gpt_researcher/skills/image_generator.py` `ImageGenerator`(:35)·`plan_and_generate_images`(:79), `agent.py:400` | 연구 파이프라인 | 핵심 | `capabilities/image-generation.md` · 미작성 | 코드 확인(활성 조건·호출 위치) / 계획·생성 세부는 미확인 |
| 서버 API | REST(`/report/`, `/api/reports*`, `/files/`, `/upload/`, `/api/chat`, `/api/multi_agents`), WebSocket `/ws`, `/.well-known/agent-discovery.json`. 보고서 생성, 이력 저장, 파일 업로드 | `backend/server/app.py`(라우트 :147-464), `server/websocket_manager.py`(:101 `start_streaming`, :134 분기), `server/server_utils.py`(:134 `handle_start_command`), `server/report_store.py`(:7) | 연구 파이프라인, 상세 보고서 | 핵심 | `capabilities/server-api.md` · 미작성 | 코드 확인(라우트·분기·저장 경로) / 파일 생성(PDF·DOCX)은 미확인 |
| 보고서 채팅 | 완성된 보고서와 대화 이력을 받아 답함. 필요하면 `quick_search` 도구로 웹 검색 | `backend/chat/chat.py` `ChatAgentWithMemory`(:55), `chat`(:197), `select_context` 호출(:187), 라우트 `app.py:263`·`:421` | 컨텍스트 선별, LLM 호출 | 핵심 | `capabilities/report-chat.md` · 미작성 | 코드 확인(진입점·도구) |
| CLI | `python cli.py "<질문>" --report_type ...`로 보고서 생성. `detailed_report`는 `DetailedReport`, 나머지는 `GPTResearcher` 직접 호출 | `cli.py:274`(상세 분기), `:306`(직접 호출) | 연구 파이프라인, 보고서 작성 | 부속 | `capabilities/cli.md` · 미작성 | 코드 확인(분기) |
| multi_agents (LangGraph) | 편집장·연구자·검토자·작가·발행자 등 에이전트 팀이 계획 → 병렬 조사 → 작성 → 사실 검토 → 발행. 사람 검토 단계 포함. 서버의 `report_type=multi_agents`로도 실행 | `multi_agents/agents/orchestrator.py` `ChiefEditorAgent`(:30)·`_create_workflow`(:65), `multi_agents/agent.py`, `backend/server/multi_agent_runner.py:31`, `multi_agents/ag2/`(AG2 변형) | 연구 파이프라인 | 부속 | `capabilities/multi-agents.md` · 미작성 | 코드 확인(그래프 노드·간선) / 각 에이전트 내부는 미확인 |
| deep_agents | LangChain `deepagents`로 같은 조사 흐름을 만들고 `quick_search`·`deep_research` 도구를 하위 에이전트에 줌. 벤치마크 포함 | `deep_agents/agent.py` `build_agent`(:63), `deep_agents/tools.py` `build_research_tools`(:9) | 연구 파이프라인 | 부속 | `capabilities/deep-agents.md` · 미작성 | 코드 확인(진입점) / 벤치마크 코드는 미확인 |
| 웹 프런트엔드 | 경량 정적 UI(`frontend/index.html`, `scripts.js`)와 Next.js UI(npm `gpt-researcher-ui`). WebSocket·`/api/reports`로 서버와 통신 | `frontend/scripts.js:854`, `frontend/nextjs/hooks/useWebSocket.ts:66`, `frontend/nextjs/hooks/useResearchHistory.ts` | 서버 API | 부속 | `capabilities/frontend.md` · 미작성 | 코드 확인(통신 진입점) / 화면·컴포넌트는 미확인 |
| 에이전트 통합 입구 | Claude Skill(`skills/`), 개발용 스킬(`.claude/SKILL.md`와 `references/`), Codex 플러그인(`.codex-plugin/plugin.json`, `.mcp.json`은 `uvx gpt-researcher`), MCP 서버 안내(`mcp-server/README.md`는 별도 레포 gptr-mcp로 이전했다고 안내) | `skills/gpt-researcher/SKILL.md`, `.codex-plugin/plugin.json`, `.mcp.json`, `mcp-server/README.md` | 없음 | 부속 | `capabilities/agent-integration.md` · 미작성 | 코드 확인(파일 내용) / MCP 서버 본체는 이 레포에 없음 |
| 배포 | Dockerfile(서버, 전체 스택), docker-compose, Procfile, terraform(ECR·GitHub Actions 설정), GitHub Actions | `Dockerfile:64`(uvicorn CMD), `Dockerfile.fullstack`, `docker-compose.yml`, `terraform/`, `.github/workflows/` | 서버 API | 부속 | `capabilities/deployment.md` · 미작성 | 추론(Dockerfile CMD만 확인) / terraform·워크플로 본문은 미확인 |
| 문서 사이트·클라이언트 | Docusaurus 문서(`docs/docs/`, `docs/blog/`), WebSocket 클라이언트 npm(`docs/npm/`), Discord 봇(`docs/discord-bot/`) | `docs/docusaurus.config.mjs`, `docs/npm/index.js`, `docs/discord-bot/package.json` | 서버 API | 부속 | `capabilities/docs-and-clients.md` · 미작성 | 추론(매니페스트만 확인) / 미확인 |
| 평가(evals) | 사실 정확도(simple_evals), 보고서 품질(quality_eval), 환각 탐지(hallucination_eval), 컨텍스트 필터 비교(context_filter) | `evals/README.md`, `evals/context_filter/` | 연구 파이프라인 | 부속 | `capabilities/evals.md` · 미작성 | 추론(README만 확인) / 미확인 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 데이터·프로토콜. 있을 때만, 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| 설정 `Config`와 환경변수 기본값 | 거의 모든 기능 | `gpt_researcher/config/config.py`, `config/variables/default.py:3`(`DEFAULT_CONFIG`) | `LLM·임베딩·설정` 행에 포함 | 코드 확인(기본값 목록) |
| `ReportType` / `ReportSource` / `Tone` 열거형 | 연구 파이프라인, 소스 모드, 보고서 작성, 서버, CLI | `gpt_researcher/utils/enum.py` | 각 기능 스펙에 나눠 적음 | 코드 확인 |
| Retriever 반환 계약 (`requires_scraping`, `url`+`raw_content`) | 검색 Retriever 패밀리, 연구 파이프라인, 스크래퍼 패밀리 | `gpt_researcher/retrievers/base.py`, `skills/researcher.py:851` `_search_relevant_source_urls` | [retrievers](capabilities/retrievers.md) R-10~R-15 | 코드 확인(계약·호출부 분기) |
| URL 안전성 (`validate_url`, 환경변수 `ALLOW_PRIVATE_URLS`) | 스크래퍼 패밀리, 소스 모드(`document_urls`) | `gpt_researcher/utils/url_security.py:60` | [scrapers](capabilities/scrapers.md) R-04·R-05 | 코드 확인 + 실행 확인 |

**대조한 범위와 미탐색 영역**
- 대조: README 기능 목록(`README.md:74`), 서버 라우트 전체(`backend/server/app.py` 데코레이터), `get_retriever` 등록부와 docstring의 지원 목록, 스크래퍼 `SCRAPER_CLASSES`, `ReportType`·`ReportSource` 열거형, `ChiefEditorAgent`의 그래프 노드·간선, 최상위 매니페스트·Dockerfile 목록.
- 문서와 구현의 차이: ① 라이선스 표기가 Apache 2.0과 MIT로 갈린다(1절). ② `get_retriever`의 docstring 지원 목록에는 `bocha`, `groundroute`가 없지만 `match`에는 있다(`actions/retriever.py`). ③ `.codex-plugin/plugin.json`의 `mcpServers`가 가리키는 `.mcp.json`은 `uvx gpt-researcher`를 실행하는데, 이 레포의 `mcp-server/README.md`는 MCP 서버가 별도 레포로 옮겨졌다고 안내한다. `uvx gpt-researcher`가 실제로 무엇을 띄우는지는 확인하지 못했다. ④ `docker-compose.yml`의 `IMAGE_GENERATION_MODEL` 기본값(`gemini-2.0-flash-preview-image-generation`)과 `config/variables/default.py`의 기본값(`models/gemini-2.5-flash-image`)이 다르다. ⑤ 구현 확인 결과(스펙에서 확인): `ResearchConductor._search`(:975)·`filter_urls`·`process_scraped_data`는 호출처가 없고, 서브쿼리 계획 전에 첫 retriever로 원 질문을 한 번 검색하는 초기 검색이 있으며, 요약 프롬프트(`generate_summary_prompt`)는 쓰이지 않는다. ⑥ Deep Research의 실제 기본값은 breadth 3 · depth 2 · concurrency 4인데 공식 문서와 README는 breadth 4(4/2/2)라고 쓴다. ⑦ `REPORT_SOURCE=doc`(config.md), CLI 상세 보고서의 `report_source="web_search"`는 분기에 없는 값이라 컨텍스트가 `[]`가 된다. ⑧ `MCP_AUTO_TOOL_SELECTION`·`MCP_ALLOWED_ROOT_PATHS`·`MCP_SERVERS`는 읽는 코드가 없고, `pyproject.toml`에는 `langchain-mcp-adapters`가 없다. ⑨ `GPTResearcher(report_format=...)`·`max_subtopics=...` 인자는 저장만 하고 읽히지 않는다. ⑩ `none` 컨텍스트 모드는 전체 페이지가 아니라 페이지당 50,000자까지이고, jev 실패는 `JevError`만 keyword로 폴백한다.
- 미탐색: `tests/`(150개 파일) 전체, `docs/` 문서 본문, `frontend/nextjs/components/`, `evals/` 코드, `terraform/` 본문, `.github/workflows/` 본문, retriever 어댑터 17개의 요청 변환(searx, arxiv, google 등)과 firecrawl·tavily_extract·web_base_loader 스크래퍼 내부, `utils/` 중 costs·rate_limiter, `multi_agents/agents/` 각 에이전트 내부, `deep_agents/benchmark*`와 `benchmark_results/`, 임베딩 모드의 `langchain-classic` `EmbeddingsFilter` 동작, `json_repair` 동작. 이유: 지도 단계는 진입점·호출 연결을 설명할 수 있으면 멈추는 규칙(워크플로 2장 3번)을 따랐고 세부는 기능 스펙 단계에서 읽었다. 승인 범위 밖 행(이미지 생성, 서버 API 등)은 스펙에서 경계만 다뤘다.

**스펙을 가로지르는 대표 흐름** (`GPTResearcher(query, report_type="research_report", report_source="web")`를 쓰고 MCP·문서 모드 없이 웹만 쓰는 경우. 승인한 9개 스펙이 이어지는 순서이고, 단계마다 근거는 해당 스펙에 있다)

1. `conduct_research()`가 에이전트 역할을 고른다. → [research-pipeline](capabilities/research-pipeline.md)
2. 소스 분기에서 `source_urls`가 없고 `report_source="web"`이면 웹 검색 경로로 간다. → [source-modes](capabilities/source-modes.md)
3. 첫 retriever(기본 Tavily)로 원 질문을 한 번 검색하고, 그 결과로 서브쿼리를 계획한다. → [retrievers](capabilities/retrievers.md), research-pipeline
4. 서브쿼리마다(원 질문 포함) 병렬로: retriever가 URL을 주고 → 스크래퍼가 본문을 가져오고(차단 페이지 등은 거름) → 컨텍스트 선별이 관련 조각만 고른다. → retrievers, [scrapers](capabilities/scrapers.md), [context-selection](capabilities/context-selection.md)
5. 서브쿼리 결과를 이어 붙인 컨텍스트가 `write_report()`로 넘어가 `report_type`에 맞는 프롬프트로 보고서가 된다. → [report-writing](capabilities/report-writing.md)
6. 변형: `report_type="deep"`이면 3~4단계 대신 breadth·depth로 쿼리 트리를 재귀 탐색한다([deep-research](capabilities/deep-research.md)). `detailed_report`이면 하위 주제마다 `subtopic_report` 연구기를 순차로 돌려 서론·목차·본문·결론·참고문헌을 조립한다([detailed-report](capabilities/detailed-report.md)). `mcp_configs`가 있으면 MCP 서버 도구가 조사에 더해진다([mcp-client](capabilities/mcp-client.md)).

---

## 3. 핵심 아키텍처 지도 (archify Diagrams)

archify로 도출한 주요 구조도(필수)입니다. 실행 흐름도는 그리지 않았습니다.

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 입구(UI·CLI·서버) → `GPTResearcher` → 검색·스크랩·컨텍스트 선별 → 보고서 작성 |

검증: archify `finalize`의 validate·deliver·check·browser-check 4개 게이트 통과(`structure.finalize.json`). 화면 캡처를 사람이 눈으로 확인하지는 않았다(visual review 미실시).

### 그림 해설

**읽는 순서**
1. 왼쪽 가운데 줄: 웹 UI → FastAPI 서버 → 리포트 타입 → `GPTResearcher` → `ReportGenerator` → LLM 제공자. 요청이 들어와 보고서가 나가는 큰 줄기다.
2. `GPTResearcher` 아래: `ResearchConductor`가 검색, 스크랩, 컨텍스트 선별을 차례로 부른다. 조사의 실제 일은 여기서 한다.
3. 위쪽 두 점선: `multi_agents`와 `Deep Research`는 선택 경로다.

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 웹 UI | 사용자 입력을 서버로 보내고 진행 로그·결과를 보여 줌 | WebSocket 연결, `/api/reports` 호출 | `frontend/scripts.js:854`, `frontend/nextjs/hooks/useWebSocket.ts:66`, `frontend/nextjs/hooks/useResearchHistory.ts:35` | 코드 확인(연결 생성) / 메시지 형식은 미확인 |
| FastAPI 서버 | REST·WebSocket 입구. `report_type`에 따라 실행 대상을 고르고 결과를 저장 | 입력: 질문·report_type·report_source·MCP 설정 등. 출력: 진행 로그, 파일 경로 | `backend/server/app.py:371`·`:408`, `server/server_utils.py:134` `handle_start_command` | 코드 확인 |
| 리포트 타입 | `BasicReport`(조사 후 바로 작성)와 `DetailedReport`(주제별 반복)를 감싸 `GPTResearcher`를 구동 | 입력: 질문·옵션. 출력: 보고서 문자열 | `backend/server/websocket_manager.py:144`·`:163`, `backend/report_type/basic_report/basic_report.py:72`, `detailed_report/detailed_report.py:84` | 코드 확인 |
| multi_agents | 서버가 `report_type=multi_agents`일 때 `run_research_task`를 불러 LangGraph 에이전트 팀을 실행 | 입력: 질문·톤·헤더. 출력: `report` 키가 있는 딕셔너리 | `backend/server/multi_agent_runner.py:31`, `websocket_manager.py:134`, `multi_agents/agents/orchestrator.py:30` | 코드 확인(서버 쪽 호출) / 팀 내부는 기능 지도의 multi_agents 행에서 따로 다룸 |
| CLI | 명령줄 인자로 보고서를 생성 | 입력: 질문과 옵션. 출력: md·pdf·docx 파일 | `cli.py:274`·`:306` | 코드 확인(분기) / 파일 출력은 미확인 |
| GPTResearcher | 하위 구성요소를 만들고(`ResearchConductor`, `ReportGenerator`, `ContextManager`, `BrowserManager`, `SourceCurator`, `DeepResearchSkill`, `ImageGenerator`) `conduct_research`·`write_report`를 노출 | 입력: query, report_type, report_source 등. 출력: context, 보고서 | `gpt_researcher/agent.py:186-196`, `:343`, `:463` | 코드 확인 |
| Deep Research | `report_type=deep`일 때 `conduct_research`가 이 스킬로 분기해 쿼리 트리를 조사하고 컨텍스트를 돌려줌 | 입력: query(breadth·depth·concurrency는 호출자 입력이 아니라 설정 키 `DEEP_RESEARCH_*`). 출력: 출처가 붙은 learnings 컨텍스트 | `gpt_researcher/agent.py:363`, `:415`, `gpt_researcher/skills/deep_research.py:586` | 코드 확인 + 실행 확인(LLM·검색은 대체물) |
| ReportGenerator | 컨텍스트로 보고서·서론·결론을 작성 | 입력: context, 기존 헤더. 출력: 마크다운 | `gpt_researcher/skills/writer.py:49`, `gpt_researcher/agent.py:463` | 코드 확인(진입점) |
| LLM 제공자 | 제공자 이름으로 langchain 채팅 모델을 만들어 호출 | 입력: provider, model, kwargs | `gpt_researcher/llm_provider/generic/base.py:146` | 코드 확인(분기) |
| 서버 로컬 저장 | `data/reports.json`(환경변수 `REPORT_STORE_PATH`)에 이력을 JSON으로 저장하고, 보고서 파일을 `outputs/`에 씀 | 입력: 보고서 문서. 출력: 파일 경로 | `backend/server/app.py:135`, `backend/server/report_store.py:7`, `server/server_utils.py:264` | 코드 확인(저장 경로·생성 함수 호출) / PDF·DOCX 변환 내부는 미확인 |
| 리포트 채팅 | 완성된 보고서에서 `select_context`로 관련 부분을 고르고 LLM에 물음. 필요하면 `quick_search` 도구를 씀 | 입력: 보고서, 메시지 이력. 출력: 답과 도구 사용 메타데이터 | `backend/chat/chat.py:55`·`:187`, `backend/server/app.py:263` | 코드 확인 |
| Retriever | 설정된 이름마다 검색 어댑터 클래스를 돌려줌. `_search_relevant_source_urls`(웹 경로)와 `get_search_results`(계획용 초기 검색)가 호출. `_search`는 호출처 없음 | 입력: 쿼리. 출력: URL과 snippet(일부는 본문 포함) | `gpt_researcher/actions/retriever.py:16`, `:150`, `skills/researcher.py:851`, `actions/query_processing.py:44` | 코드 확인(등록부·호출부) / 개별 어댑터는 일부만 읽음 |
| ResearchConductor | 서브쿼리를 만들고 서브쿼리마다 검색→스크랩→선별을 `asyncio.gather`로 병렬 실행. 출처 curation은 설정에 따라 선택 | 입력: query, source 설정. 출력: 합쳐진 컨텍스트 | `gpt_researcher/skills/researcher.py:97`, `:298`, `:520` | 코드 확인 |
| 검색 API · MCP | Retriever가 부르는 외부 서비스(Tavily 등)와 MCP 서버 | — | `gpt_researcher/actions/retriever.py:16` | 코드 확인(지원 목록) / 호출 세부는 미확인 |
| Scraper | URL 목록을 받아 본문·이미지를 추출하고 차단 페이지 등을 거름 | 입력: URL 목록. 출력: 페이지 본문과 이미지 | `gpt_researcher/skills/browser.py:37`, `gpt_researcher/scraper/scraper.py:109`·`:194`·`:307` | 코드 확인(선택·거름 규칙) |
| 컨텍스트 선별 | `CONTEXT_FILTER`에 따라 jev·keyword·embeddings·none 중 하나로 관련 조각을 고름 | 입력: 서브쿼리, 페이지 목록. 출력: 컨텍스트 문자열 | `gpt_researcher/context/select.py:38`·`:53`, `skills/context_manager.py:38` | 코드 확인(모드 선택) / 점수 계산은 미확인 |
| 웹 페이지 | 스크랩 대상 | — | `gpt_researcher/scraper/scraper.py:194` | 코드 확인 |

**미확인 영역**
- 그림에 넣지 않은 것: `deep_agents`, MCP 클라이언트 내부(`gpt_researcher/mcp/`), 이미지 생성(`ImageGenerator`), 로컬 문서 로더와 벡터 스토어, 비용 집계, `SourceCurator`.
- LLM 호출은 그림에서 `ReportGenerator`와 `ResearchConductor` 두 줄만 그렸다. 에이전트 역할 선택(`choose_agent`), Deep Research, 리포트 채팅, 컨텍스트 선별 중 일부도 LLM을 부르지만 줄을 모두 그리면 읽기 어려워 생략했다.
- `multi_agents`가 안에서 `GPTResearcher`를 다시 쓰는 줄은 그리지 않았다(`multi_agents/agents/researcher.py:17`에서 확인).
- 리포트 타입 → `GPTResearcher` 줄과 CLI → `GPTResearcher` 줄은 서로 다른 경로이고, CLI는 `detailed_report`일 때만 `DetailedReport`를 거친다.

---

## 4. 질문 (Questions)

사용자 질문의 답입니다. 확정된 동작은 기능 스펙에 반영하고 여기서는 결론만 적습니다.

- [Q1: 서브쿼리 결과는 어떻게 하나의 컨텍스트로 합쳐지는가](./questions/q1-subquery-context-merge.md) - *별도 병합 로직 없이 비어 있지 않은 서브쿼리 결과를 공백 한 칸으로 이어 붙이고, 중복은 같은 URL을 두 번 읽지 않는 것으로만 막으며, 합친 뒤 전체 길이를 줄이는 코드는 없다.*
- [Q2: 합친 뒤 보고서를 쓰기 전까지의 과정, LLM 프롬프트와 도구의 위치](./questions/q2-prompts-tools-and-pre-report-flow.md) - *합친 뒤에는 선택 사항인 출처 선별(기본 꺼짐)뿐이고 최종 N개로 자르는 단계는 없다. 프롬프트는 대부분 `prompts.py`의 `PromptFamily`에 있고(Deep Research만 코드 안), 도구 호출은 MCP·보고서 채팅·deep_agents에서만 쓴다.*

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 기능 지도의 "스펙·상태" 칸. 범위 승인 전이라 모두 미작성이다.
