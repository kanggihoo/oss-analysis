---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/agent.py
  - gpt_researcher/prompts.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/skills/curator.py
  - gpt_researcher/skills/writer.py
  - gpt_researcher/skills/deep_research.py
  - gpt_researcher/context/lexical.py
  - gpt_researcher/mcp/research.py
  - gpt_researcher/mcp/tool_selector.py
  - gpt_researcher/utils/tools.py
  - backend/chat/chat.py
  - deep_agents/tools.py
---

# [Q] 합친 뒤 보고서를 쓰기 전까지의 과정, LLM 프롬프트와 도구의 위치

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 코드 확인. 실행하지 않았다(합친 뒤 단계는 [q1](./q1-subquery-context-merge.md)의 실험에서 일부 실행 확인)

---

## 1. 질문 및 결론

- **질문**: 서브쿼리 결과를 합친 뒤 중복 제거나 전처리가 있는가, 최종 몇 개를 골라 보고서를 쓰는가, 보고서를 쓰기 전까지의 과정은 무엇인가, LLM 지시문(프롬프트)과 도구(function calling)는 어디에 있는가?
- **핵심 결론**:
  - 합친 뒤에 하는 일은 선택 사항인 출처 선별(`CURATE_SOURCES`, 기본 꺼짐)뿐이다. 중복 제거나 전처리는 없다.
  - "최종 N개"로 자르는 단계는 없다. 개수 제한은 서브쿼리 안에서만 걸린다(keyword 모드는 서브쿼리당 최대 25조각).
  - 프롬프트는 대부분 `gpt_researcher/prompts.py` 한 파일의 `PromptFamily` 클래스에 있다. 예외로 Deep Research는 프롬프트가 `deep_research.py` 안에 직접 쓰여 있다.
  - 기본 조사 흐름은 도구 호출(function calling)을 쓰지 않는다. 도구를 쓰는 곳은 MCP, 보고서 채팅, `deep_agents`뿐이다.

---

## 2. 합친 뒤 보고서를 쓰기 전까지

1. **컨텍스트 저장.** 합쳐진 문자열(또는 비어 있으면 `[]`)을 `self.researcher.context`에 넣는다. `researcher.py:212`
2. **출처 선별(선택).** `CURATE_SOURCES`가 켜져 있을 때만 LLM이 출처를 고르고 `Title/Content/Source` 블록으로 다시 만든다. LLM이나 JSON 파싱이 실패하면 원본을 그대로 돌려준다. `researcher.py:213-229`, `skills/curator.py:38-114`. 프롬프트가 "최대 10개"를 요청하지만 코드가 강제하지는 않는다.
3. **로그와 비용 출력(verbose일 때).** `researcher.py:231-240`
4. **`GPTResearcher`로 반환.** `self.context = await self.research_conductor.conduct_research()`로 받는다. 이미지 생성이 켜져 있으면 보고서 작성 전에 이미지를 먼저 만든다(기본 꺼짐). `agent.py:343-413`
5. **`write_report()`.** `ext_context or self.context`를 컨텍스트로 쓴다. 비어 있으면 LLM을 부르지 않고 고정 문장("I could not gather any source material...")을 돌려주고, 아니면 프롬프트에 컨텍스트를 `f"{context}"`로 그대로 넣는다. `agent.py:463`, `skills/writer.py:77-88`, `prompts.py:294`

**개수와 길이.** 합친 뒤 전체 길이를 자르는 코드는 없다. 서브쿼리 안의 제한만 있다: 페이지당 50,000자, keyword 모드 25조각(조각 크기는 `lexical.py:77-79`의 값 기준 1,000자), jev·embeddings 모드 10개. 서브쿼리 3개 + 원 질문 + 초기 컨텍스트로 5묶음이고 keyword 모드가 가득 찼다고 가정하면 컨텍스트가 최대 약 125,000자까지 커질 수 있다(조각 크기를 곱한 추정이고, 분할 라이브러리는 실행하지 못했다). 출력 쪽 한도(`SMART_TOKEN_LIMIT` 12,000)와 분량 지시(`TOTAL_WORDS` 1,200단어)는 따로 있다.

---

## 3. LLM 프롬프트 위치

| # | 용도 | 프롬프트 위치 | 호출부 | 정리된 스펙(`capabilities/`) |
|---|---|---|---|---|
| 1 | 에이전트 역할 고르기 | `gpt_researcher/prompts.py:490-515` `auto_agent_instructions` | `actions/agent_creator.py:18` `choose_agent` (temperature 0.15) | `research-pipeline.md:168` C-05, `:120` R-03 |
| 2 | 서브쿼리 생성 | `prompts.py:213-259` `generate_search_queries_prompt` | `actions/query_processing.py:83` `generate_sub_queries` | `research-pipeline.md:167` C-04, `:236` R-12 |
| 3 | 출처 선별(기본 꺼짐) | `prompts.py:319-350` `curate_sources` | `skills/curator.py:67-77` (temperature 0.2, `max_tokens` 8000) | `research-pipeline.md:143` R-26, `:177` C-14 (경계만, 프롬프트 문구는 스펙에 없음) |
| 4 | 보고서 본문 (타입별) | `prompts.py:262-316` research, `:353-390` resource, `:393-396` custom, `:399-415` outline, `:418-487` deep, `:596-670` subtopic. 타입→함수 매핑 `:852-876` | `actions/report_generation.py:209` `generate_report` | `report-writing.md:205-211` C-01~C-07 |
| 5 | 서론·결론 | `prompts.py:707-753` | `actions/report_generation.py:12`, `:63` | `report-writing.md:213` C-09, `:215` C-11 |
| 6 | 서브토픽 초안 소제목 | `prompts.py:673-704` | `actions/report_generation.py:160` | `report-writing.md:212` C-08, `:216` C-12 |
| 7 | 하위 주제 만들기(상세 보고서) | `prompts.py:573-593` `generate_subtopics_prompt` | `utils/llm.py:165` `construct_subtopics` | `detailed-report.md:208` C-08, `:135` R-07 |
| 8 | Deep Research 질의 생성·계획·학습 추출 | `skills/deep_research.py:265-296`, `:298-350`, `:352-384` (프롬프트가 코드 안에 직접 있음) | 같은 파일 | `deep-research.md:176`, `:177`, `:178` C-09~C-11 |
| 9 | MCP 도구 선택 | `prompts.py:40-83` `generate_mcp_tool_selection_prompt` | `mcp/tool_selector.py:37` | `mcp-client.md:267` C-18 |
| 10 | MCP 도구 호출 지시 | `prompts.py:86-118` `generate_mcp_research_prompt` | `mcp/research.py:34` | `mcp-client.md:268` C-19 |
| 11 | `quick_search` 결과 요약 | `prompts.py:532` `generate_quick_summary_prompt` | `agent.py:531-583` `quick_search` (`:571`) | 스펙 없음(승인 범위 밖) |
| 12 | 이미지 계획·생성 | `prompts.py:122-210`, `skills/image_generator.py:202-305` | `skills/image_generator.py` | 스펙 없음(제외) |
| 13 | 보고서 채팅 시스템 프롬프트 | `backend/chat/chat.py:217-245` | `backend/chat/chat.py` `chat` | 스펙 없음(제외) |
| - | 쓰이지 않음 | `prompts.py:518` `generate_summary_prompt` | 호출처 없음 | `research-pipeline.md:216` |

granite 계열 `prompt_family`는 `pretty_print_docs`와 `join_local_web_documents`만 덮어쓰고(`prompts.py:756-834`) 보고서 프롬프트는 바꾸지 않는다(`report-writing.md:272`).

---

## 4. 도구(function calling) 정의 위치

기본 조사 흐름의 LLM 호출은 모두 일반 채팅 호출이고, 결과를 JSON으로 받아 코드가 파싱한다. 도구를 `bind_tools`로 붙이는 곳은 아래 셋이다.

| # | 도구 | 코드 위치 | 설명 | 정리된 스펙 |
|---|---|---|---|---|
| 1 | MCP 서버의 도구들 | `gpt_researcher/mcp/research.py:34` `conduct_research_with_tools` (`bind_tools` `:66`), 도구 선택 `mcp/tool_selector.py:37` | 도구 정의는 MCP 서버가 제공하고 이 레포에는 없다. LLM이 도구를 고르고 호출한다 | `mcp-client.md:198` R-22, `:267`~`:268` C-18~C-19 |
| 2 | 보고서 채팅의 `quick_search` | `backend/chat/chat.py:32-53` `get_tools`(함수 스키마), `gpt_researcher/utils/tools.py:46` `create_chat_completion_with_tools`(`bind_tools` `:107`), `:230` `create_search_tool` | 보고서와 대화하다 최신 정보가 필요하면 웹 검색을 부르는 도구 하나 | 스펙 없음(보고서 채팅은 승인 범위 밖) |
| 3 | `deep_agents`의 `quick_search`, `deep_research` | `deep_agents/tools.py:9` `build_research_tools` (`:26`, `:47`) | LangChain deepagents의 하위 에이전트에게 주는 도구 | 스펙 없음(부속, 제외) |

---

## 5. 남은 질문 및 추가 조사 사항

- [ ] 서브쿼리 생성 프롬프트(#2), 보고서 본문 프롬프트(#4)의 실제 문구가 LLM 출력에 미치는 영향은 확인하지 못했다(실행 없음)
- [ ] 출처 선별 프롬프트(#3) 문구는 스펙에 정리하지 않았다
- [ ] 보고서 채팅과 `quick_search`는 스펙 범위 밖이라 동작 확인을 하지 않았다
