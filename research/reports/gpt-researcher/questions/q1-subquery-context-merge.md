---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/skills/context_manager.py
  - gpt_researcher/skills/curator.py
  - gpt_researcher/context/select.py
  - gpt_researcher/context/lexical.py
  - gpt_researcher/context/retriever.py
  - gpt_researcher/prompts.py
  - gpt_researcher/agent.py
  - gpt_researcher/skills/writer.py
  - gpt_researcher/actions/report_generation.py
  - gpt_researcher/utils/llm.py
  - gpt_researcher/skills/deep_research.py
  - backend/report_type/detailed_report/detailed_report.py
---

# [Q] 서브쿼리 결과는 어떻게 하나의 컨텍스트로 합쳐지는가

- **상위 개요**: [overview.md](../overview.md)
- **검증 수준**: 코드 확인 + 실행 확인(가짜 검색·스크래퍼, 실제 합치기 소스). 실제 스크래퍼·LLM·네트워크, keyword 조각 분할 라이브러리는 실행하지 않음

---

## 1. 질문 및 결론

- **질문**: 서브쿼리(세부 검색어)마다 얻은 조사 결과가 하나의 컨텍스트(조사 메모 묶음)로 합쳐질 때 중복 제거, 순서, 길이 제한, 실패 처리는 어떻게 되는가?
- **핵심 결론**: 별도의 병합 로직은 없다. 서브쿼리마다 `Source / Title / Content` 형식의 문자열이 하나씩 만들어지고, 비어 있지 않은 것만 공백 한 칸으로 이어 붙인다. 중복은 "같은 URL을 두 번 읽지 않는 것"으로만 막고, 합친 뒤 전체 길이를 줄이는 코드는 없다.

---

## 2. 동작 설명

### 2.1 순서대로 보기

1. **서브쿼리 목록을 만든다.** 첫 검색 결과를 참고해 LLM이 서브쿼리를 만들고, `report_type`이 `subtopic_report`가 아니면 원 질문을 목록 끝에 붙인다. 이 두 호출은 `try` 바깥이라 실패하면 예외가 그대로 나간다.
2. **초기 컨텍스트를 먼저 만든다.** 서브쿼리가 시작되기 전에 첫 검색 결과의 URL을 읽고 선별해서 `initial_context`를 만든다. 실패하면 `""`다. 이 URL들은 `visited_urls`에 들어가므로 이후 서브쿼리가 같은 URL을 받지 못한다.
3. **서브쿼리 하나를 처리한다(`_process_sub_query`).** 반환 타입은 항상 문자열이다.
   - MCP 사전 결과(있다면)를 준비한다.
   - 검색 → `_get_new_urls`로 이미 본 URL 제거 → `random.shuffle` → 스크랩한다. 검색기가 본문을 직접 준 항목(prefetched)은 뒤에 붙는다.
   - `select_context`로 관련 조각을 골라 `Source/Title/Content` 문자열을 만든다.
   - MCP 결과가 있으면 웹 문자열 뒤에 붙인다.
   - 이 전체가 `try/except Exception` 안에 있어서, 어떤 예외든 로그를 남기고 `""`를 반환한다.
4. **서브쿼리를 병렬로 돌리고 합친다.** `asyncio.gather`가 입력 순서를 지키므로 순서는 "초기 컨텍스트 → 서브쿼리 목록 순서 → 원 질문"이다. 끝난 순서와는 무관하다. `[초기, *서브쿼리 결과]` 중 비어 있는 것을 빼고 `" "`(공백 한 칸)로 이어 붙인다. 전부 비면 빈 문자열이 아니라 빈 리스트 `[]`를 반환한다. 이 합치기 전체가 `try/except Exception`이라 예외가 나면 이미 만든 결과까지 버리고 `[]`를 돌려준다.
5. **`researcher.context`에 저장한다.** `CURATE_SOURCES`가 꺼져 있으면(기본값) 가공 없이 그대로 쓴다. 켜면 LLM이 출처를 고르고 `Title/Content/Source` 블록으로 다시 만든다(LLM이나 JSON 파싱이 실패하면 원본을 그대로 돌려준다).
6. **보고서 작성 쪽.** `ext_context or self.context`를 쓰고, 비었는지만 검사한 뒤 컨텍스트를 `f"{context}"`로 프롬프트에 그대로 넣는다.

### 2.2 서브쿼리 문자열의 안쪽 모양

`select_context`가 모드에 따라 다르게 만든다.

- 총 8,000자 미만이고 페이지가 10개 이하이면 모드와 상관없이 고르지 않고 받은 순서대로 넣는다.
- 그 이상이면 기본(`auto`, `TYPESAFE_API_KEY` 없음)은 keyword 방식이다. 1,000자 조각(100자 겹침)으로 나누고 BM25 점수로 순위를 매겨, 최고점의 50% 이상인 조각을 최대 25개 점수순으로 낸다. 점수가 전부 0이면 앞쪽 25개를 문서 순서대로 낸다.
- jev와 embeddings 모드는 최대 10개를 쓴다.
- 출력 형식은 조각마다 `Source: ...\nTitle: ...\nContent: ...\n`이고 `"\n"`으로 이어진다.

### 2.3 실험으로 본 합쳐진 모습

초기 결과 `[u1, u9]`, 서브쿼리 `A=[u1,u2]`, `B=[u2,u3]`(u3 스크랩 실패), `C`(스크랩 호출이 예외), 원 질문 `Q=[u1,u4]`로 돌린 결과다.

```text
Source: u9 ... Content: PAGE-U9 ...      (초기 컨텍스트, 끝에 줄바꿈이 남음)
<공백>Source: u1 ... Content: PAGE-U1 ...
<공백>Source: u2 ... Content: PAGE-U2 ...Source: u4 ... Content: PAGE-U4 ...
```

- u1은 초기 컨텍스트가 먼저 가져가서 서브쿼리 A와 Q에는 안 들어갔다. u2는 A가 가져가서 B에는 안 들어갔다.
- 실패한 URL(u3, C의 URL)도 `visited_urls`에 남았다.
- 서브쿼리 결과들은 `strip()` 되어 있어서 경계에 줄바꿈이 없다. 앞 결과의 끝과 다음 `Source:`가 한 줄에 붙는다(`...PAGE-U2 <f>Source: u4`).

---

## 3. 항목별 동작

| 항목 | 원본 동작 | 검증 수준 |
|---|---|---|
| 구분자·순서 | `" "`로 이음. 초기 컨텍스트 → 서브쿼리 순서 → 원 질문. 한 서브쿼리 안의 페이지 순서는 `random.shuffle` 때문에 매번 달라질 수 있음 | 코드 확인, 실행 확인 |
| 빈 값 | 빈 문자열은 제외. 전부 비면 `[]` | 코드 확인, 실행 확인 |
| 서브쿼리 간 URL 중복 | `_get_new_urls`가 스크랩 전에 `visited_urls`에 넣고 이미 있으면 건너뜀. 먼저 요청한 서브쿼리 하나만 그 URL을 가져감. 확인과 추가 사이에 `await`가 없어서 두 서브쿼리가 같은 URL을 동시에 읽는 경쟁은 없음 | 코드 확인, 실행 확인 |
| 스크랩 실패한 URL | 이미 `visited_urls`에 있어서 다른 서브쿼리도 재시도하지 못함. 컨텍스트에서는 빠지고 `visited_urls`에는 남음 | 코드 확인, 실행 확인 |
| 검색기가 본문을 직접 준 경우(`requires_scraping=False`) | 같은 URL이 서브쿼리마다 또 들어감 | 코드 확인, 실행 확인 |
| MCP 결과 | `fast`(기본)에서는 같은 캐시 결과가 서브쿼리마다 붙어 최종 문자열에 서브쿼리 수만큼 반복됨. MCP만 쓰면 원 질문이 두 번 실행되어 2번 들어감 | 코드 확인, 실행 확인 |
| 서로 다른 URL의 같은 내용 | 다루지 않음. 내용 해시나 문장 단위 중복 제거를 찾지 못함 | 코드 확인(없음 확인, 전수 검색은 하지 않음) |
| 서브쿼리 안 길이 제한 | 페이지당 50,000자, keyword 25조각, jev·embeddings 10개 | 코드 확인 |
| 합친 뒤 길이 제한 | 없음. `conduct_research` → `write_report` → `generate_report`에서 컨텍스트를 자르지 않음. 컨텍스트에 쓰이는 자르기는 Deep Research의 `trim_context_to_word_limit`뿐 | 코드 확인(Grep) |
| 서브쿼리 하나의 실패 | `""`로 삼켜짐, 나머지는 영향 없음 | 코드 확인, 실행 확인 |
| 서브쿼리 계획 단계 실패 | 예외가 `_get_context_by_web_search` 밖으로 나감 | 코드 확인, 실행 확인 |
| 컨텍스트가 너무 길어 LLM 호출이 실패 | 길이 초과를 구분하는 처리가 없음. 호출은 웹소켓 스트리밍이 아니면 최대 10번 재시도(대기 1, 2, 4, 8초, 상한 8초) 후 `RuntimeError`, `generate_report`가 한 번 더(다시 최대 10번) 시도하고 실패하면 `""` | 코드 확인(실행 안 함) |

다른 보고서 유형과의 차이는 한 가지만 적는다. Deep Research는 컨텍스트를 항목 리스트로 모으고 뒤쪽 항목부터 거꾸로 채워 25,000단어까지만 남긴다. 일반 웹 조사에는 이런 총량 제한이 없다.

---

## 4. 코드 근거

| 구분 | 파일 경로 | 식별자 | 설명 |
|---|---|---|---|
| 합치기 | `gpt_researcher/skills/researcher.py:385-408` | `_get_context_by_web_search` | 초기 컨텍스트, `gather`, 빈 값 제거, `" ".join`, 예외 시 `[]` |
| 서브쿼리 하나 | `researcher.py:520-663` | `_process_sub_query` | 반환 `str`, 예외 시 `""` |
| URL 중복 | `researcher.py:813-834`, `:936-973` | `_get_new_urls`, `_scrape_data_by_urls` | 스크랩 전에 `visited_urls`에 추가, 섞기, prefetched를 뒤에 붙임 |
| MCP 결합 | `researcher.py:739-791` | `_combine_mcp_and_web_context` | 웹 문자열 뒤에 MCP 항목 |
| 컨텍스트 저장·출처 선별 | `researcher.py:212-229`, `skills/curator.py` | `conduct_research`, `curate_sources` | 기본은 선별 안 함 |
| 선별·형식 | `gpt_researcher/context/select.py:53-101`, `context/lexical.py`, `prompts.py:555-561` | `select_context`, `pretty_print_docs` | 모드별 조각 선택, 출력 형식 |
| 보고서 쪽 소비 | `writer.py:77-88`, `prompts.py:294` | `ReportGenerator.write_report` | 비었는지만 검사, 프롬프트에 그대로 삽입 |
| 재시도 | `gpt_researcher/utils/llm.py:120-162`, `actions/report_generation.py:291-326` | `create_chat_completion`, `generate_report` | 입력 길이 초과를 구분하지 않음 |

---

## 5. 검증 과정 및 실행 결과

- **수행한 것**: 서브에이전트가 `ResearchConductor`의 메서드들, `ContextManager.get_similar_content_by_query`, `select_context`, `SearchAPIRetriever`, `PromptFamily.pretty_print_docs`의 원본 소스를 `ast`로 잘라 `exec`했고, 검색·스크래퍼·서브쿼리 계획·langchain 클래스는 가짜로 바꿔 시나리오 S1~S8을 돌렸다. 결과는 `artifacts/gpt-researcher/context-merge-demos/demo_context_merge.out`.
- **메인 세션이 직접 다시 확인한 것**: `_get_new_urls`(URL을 추가한 뒤 새 목록에 넣음), 합치기 코드(`[c for c in [initial_context, *context] if c]`, `" ".join`), `gpt_researcher/` 전체에서 컨텍스트를 자르는 코드가 `deep_research.py`뿐이라는 Grep.
- **판단 근거**: 합치기 규칙과 URL 선점은 코드를 읽고 가짜 객체로 실행해 같은 결과를 얻었다. 길이 제한이 없다는 것은 검색한 범위 안에서 확인한 것이다.

---

## 6. 남은 질문 및 추가 조사 사항

- [ ] keyword 모드의 실제 조각 겹침과 순서(`langchain_text_splitters` 미설치로 실행하지 못함)
- [ ] 컨텍스트가 모델 입력 한도를 넘을 때의 실제 동작(코드만 읽음)
- [ ] `CURATE_SOURCES`가 켜졌을 때의 흐름(LLM이 필요해 실행하지 않음)
- [ ] 같은 내용의 서로 다른 URL을 걸러내는 곳이 정말 없는지(전수 검색은 하지 않음)
- [ ] 범위 밖으로 둔 것: 서브쿼리 생성 방식과 개수 제한, hybrid 모드의 두 패스 사이 `visited_urls`, 벡터스토어 경로
