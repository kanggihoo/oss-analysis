---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
sources:
  - gpt_researcher/context/select.py
  - gpt_researcher/context/lexical.py
  - gpt_researcher/context/jev_filter.py
  - gpt_researcher/context/compression.py
  - gpt_researcher/context/retriever.py
  - gpt_researcher/skills/context_manager.py
  - gpt_researcher/skills/researcher.py
  - gpt_researcher/prompts.py
  - gpt_researcher/agent.py
  - gpt_researcher/config/config.py
  - gpt_researcher/config/variables/default.py
  - gpt_researcher/utils/costs.py
  - gpt_researcher/memory/embeddings.py
  - backend/chat/chat.py
  - .env.example
  - docs/docs/gpt-researcher/gptr/context-filter.md
depends:
  - ../capabilities/scrapers.md
status: draft
reimplementation: 미실행
---

# 컨텍스트 선별

> 스크랩한 페이지 목록(`url`·`title`·`raw_content`)과 서브쿼리 문자열을 받아, `CONTEXT_FILTER` 설정(auto / jev / keyword / embeddings / none)에 따라 서브쿼리와 관련된 조각(청크)만 골라 `Source/Title/Content` 형식의 컨텍스트 문자열 하나로 돌려주고, 선별이 실패하면 keyword(BM25) 순위로 내려간다.

<!--
이 스펙의 범위: 기준 SHA의 원본 동작. 우리가 바꾸고 싶은 점은 맨 끝 "적용 메모"에만 둔다.
읽은 코드: context/ 전체(select, lexical, jev_filter, compression 중 ContextCompressor, retriever), skills/context_manager.py, chat.py의 호출부, prompts.py의 pretty_print_docs.
실행한 것: keyword·jev·select_context를 소스 그대로 불러 오프라인으로 돌림(대체물은 2.1 끝에 적음). embeddings 모드 본체와 실제 Jev 서버는 실행하지 못함.
-->

## 1부. 동작 설명

용어를 먼저 정리한다.

- **청크**: 페이지 본문을 잘라 만든 조각. 선별은 페이지가 아니라 청크 단위로 한다.
- **BM25**: 질의 단어가 청크에 몇 번, 얼마나 드문 단어로 나오는지로 점수를 매기는 검색 순위 공식이다. 외부 호출이 필요 없다.
- **Jev**: TypeSafe 사가 제공하는 외부 API(`https://api.typesafe.ai/v1/systemone`). 청크가 질문에 얼마나 쓸모 있는지 0~3 점수로 돌려주는 서비스로, 코드는 그렇게 쓴다고 가정한다(R-06).
- **지름길**: 내용이 적으면 선별을 건너뛰고 페이지를 그대로 쓰는 경로(R-04).
- **폴백**: 선택한 방법이 실패했을 때 keyword 방법으로 대신 처리하는 것.

### 1.1 한눈에 보는 흐름

1. 호출자가 `select_context(query, pages, cfg, ...)`를 부른다. `pages`는 [스크래퍼 패밀리](scrapers.md)의 성공 결과 항목 목록이다(`url`, `title`, `raw_content`를 쓰고 `image_urls`는 쓰지 않는다).
2. `cfg.context_filter`를 소문자로 바꿔 모드를 정한다. 값이 없거나 `auto`이면 환경변수 `TYPESAFE_API_KEY`가 있을 때 `jev`, 없으면 `keyword`다. 모르는 값은 경고 후 `auto`로 본다(R-01).
3. 모드가 `none`이면 모든 페이지를 선별 없이 포맷해 돌려주고 끝난다(R-03).
4. 아니면 전체 본문 길이가 8000자 미만이고 페이지가 10개 이하일 때 선별 없이 포맷해 돌려준다. 이 지름길은 `jev`·`embeddings`·`keyword` 모두에 똑같이 적용되어 외부 호출을 하지 않는다(R-04).
5. 모드별로 청크를 고른다.
   - `jev`: 청크마다 Jev API를 한 번씩 불러 점수를 받고, 1.5점 이상인 것만 점수 순으로 최대 10개(R-05~R-09).
   - `embeddings`: 호출자가 준 임베딩 객체로 청크와 질의의 유사도를 구해 임계값(기본 0.42)을 넘는 것(R-11).
   - `keyword`: 청크를 BM25로 점수 매겨 최고점의 절반 이상인 것만 점수 순으로 최대 25개(R-14). 겹치는 단어가 하나도 없으면 앞쪽 25개 청크(R-15).
6. `jev`가 `JevError`로, `embeddings`가 어떤 예외로든 실패하면 경고를 남기고 keyword 순위로 다시 고른다(R-10, R-12). keyword 단계에서는 더 내려갈 곳이 없다.
7. 고른 청크를 `Source: <url>\nTitle: <제목>\nContent: <청크>\n` 블록으로 만들어 빈 줄로 이은 문자열을 돌려준다(R-19).

### 1.2 범위·통합 지점

- 제공: 서브쿼리 하나에 대해 스크랩한 페이지에서 관련 청크만 골라 컨텍스트 문자열로 만든다. 모드 선택 규칙, 모드별 입출력과 상수, 청크 분할, 출력 개수 한도, 반환 문자열 형식, 실패 시 keyword 폴백을 포함한다.
- 제외:
  - 임베딩 모델을 만드는 일(`memory/embeddings.py`)은 사용자가 LLM·임베딩·설정을 제외했으므로 이 스펙 밖이다. `embeddings` 모드는 "호출자가 임베딩 객체를 만들어 주는 함수를 공급하면 그 객체로 유사도를 구해 거른다"는 경계로만 쓴다.
  - 같은 `context/` 폴더에 있어도 보고서 작성 중 이전 섹션을 찾는 `WrittenContentCompressor`, `rank_written_sections`, `ContextManager.get_similar_written_contents_by_draft_section_titles`는 상세 보고서 스펙([detailed-report.md](detailed-report.md))이 맡는다. 여기서는 이름과 경계만 적는다.
  - 벡터 스토어 경로(`VectorstoreCompressor`, `get_similar_content_by_query_with_vectorstore`)는 `vector_store` 경로 제외(사용자 제외)에 따라 쓰지 않는다.
  - 서브쿼리를 만들고 이 기능을 부르는 순서, 여러 서브쿼리의 컨텍스트를 합치는 일은 `research-pipeline.md`(아직 없음)의 일이다. 보고서 채팅(`report-chat.md`, 아직 없음)은 같은 함수를 부르는 호출자이며 경계만 R-21에 쓴다.
  - Jev 서비스가 실제로 점수를 어떻게 매기는지, 서버가 이 요청 형식을 받아 주는지는 확인하지 못했다(확인 한계).
  - `evals/context_filter`(필터 비교 실험)는 읽지 않았다.
- 외부 의존·선행 계약:
  - 입력 항목 형식은 [scrapers.md](scrapers.md) 1.3의 "결과 dict(성공)"이다. 이 기능이 읽는 키는 `raw_content`(문자열), `url`, `title`뿐이다. 누락·`None`의 처리는 R-18.
  - 호출자가 공급하는 것: 설정 객체 `cfg`(속성 `context_filter`, `similarity_threshold`), 포맷 객체 `prompt_family`(메서드 `pretty_print_docs(docs, top_n)`), 비용 보고 함수 `cost_callback(float)`, 임베딩 객체 공급 함수 `embeddings()`(인자 없음).
  - 네트워크: `jev` 모드만 HTTPS POST를 한다(`httpx`). `keyword`는 순수 계산이다.
  - 외부 라이브러리: 청크 분할은 `langchain-text-splitters`의 `RecursiveCharacterTextSplitter`, `embeddings` 모드의 유사도 필터는 `langchain-classic`의 `EmbeddingsFilter`를 쓴다. 두 라이브러리 안의 동작은 이 스펙이 정의하지 않는다(확인 한계).
- 소유 상태·부작용:
  - 영속 상태는 없다. 입력 `pages`를 바꾸지 않는다.
  - Jev 동시성 세마포어(한 번에 날릴 수 있는 요청 수를 세는 장치)가 이벤트 루프마다 하나씩 프로세스 안에 남는다(R-08).
  - `cost_callback`을 호출해 비용을 호출자에게 알린다(R-09, R-13).
  - 로그(`logging.warning`)만 남기고 사용자에게 보이는 이벤트는 없다. 진행 로그(`verbose`)는 호출자 `ContextManager`가 보낸다(R-20).

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `select_context(query, pages, cfg, *, max_results, prompt_family, cost_callback, embeddings)` | 비동기. `query`: string, `pages`: list of 페이지 dict, `cfg`: 속성을 가진 객체, `max_results`: int 기본 10, `prompt_family`: 포맷 객체(없으면 기본 `PromptFamily`), `cost_callback`: optional callable(float), `embeddings`: optional callable(인자 없음 → 임베딩 객체). 출력: string | `max_results`는 지름길·jev·embeddings의 개수 한도이고, keyword 경로에서는 쓰이지 않는다(R-14). `embeddings` 함수는 embeddings 모드가 실제 필터 단계에 들어갈 때만 호출된다. 입력 `pages` 안 항목을 수정하지 않는다 |
| 페이지 dict | `{url: string, title: string, raw_content: string \| None, ...}` | `raw_content`가 없거나 `None`이면 빈 문자열로 본다. `title`·`url` 키가 없으면 빈 문자열. 그 밖의 키(`image_urls` 등)는 무시 |
| `cfg` 속성 | `context_filter`: string, `similarity_threshold`: float | `context_filter` 속성이 없으면 `None`으로 보고 `auto`다. 호출 때마다 읽는다. Config 쪽 기본값은 `"auto"`와 `0.42`(C-13) |
| 청크(내부 데이터) | `{page_content: string, metadata: {title, source}}` | `source`는 페이지의 `url`. 공백뿐인 청크는 버린다. 페이지 순서 다음 청크 순서가 위치(position)다 |
| 반환 문자열 | string | 기본 형식은 R-19. 선별된 청크가 없으면 빈 문자열 `""` |
| `CONTEXT_FILTER` | string. 기본 `auto`. Config 키로 환경변수 또는 설정 파일에서 옴 | 앞뒤 공백·대소문자 무시. `auto`, `jev`, `keyword`, `embeddings`, `none` 외의 값은 경고 후 `auto` |
| `TYPESAFE_API_KEY` | 환경변수 string. Config 키가 아님 | `os.environ`에서 직접 읽는다. 비어 있지 않은 문자열이면 있는 것으로 본다(`""`는 없음). `jev`일 때 Bearer 토큰 |
| `JEV_MODEL` | string. 기본 `jev-latest` | Jev 요청 본문의 `model`. `JevClient` 생성 시 읽음 |
| `JEV_CHUNK_SIZE` | int. 기본 1000 | jev의 청크 길이(문자 수). 겹침은 `JEV_CHUNK_SIZE // 10`. `JevContextCompressor` 생성 시 읽음. 정수가 아니면 `ValueError`(R-10) |
| `JEV_MIN_SCORE` | float. 기본 1.5 | jev가 청크를 남기는 최소 점수(0~3 척도). 생성 시 읽음. 숫자가 아니면 `ValueError`(R-10) |
| `JEV_CONCURRENCY` | int. 기본 64 | 이벤트 루프당 동시에 날릴 수 있는 Jev 요청 수. 그 루프에서 처음 요청할 때 한 번 읽는다(R-08) |
| `KEYWORD_RELATIVE_THRESHOLD` | float. 기본 0.5 | keyword가 최고점의 이 비율 이상인 청크만 남김. 모듈을 처음 불러올 때 한 번 읽음. 숫자가 아니면 모듈 로드가 `ValueError`(R-22) |
| `KEYWORD_MAX_RESULTS` | int. 기본 25 | keyword가 남기는 청크 수 상한. 모듈 로드 시 한 번 읽음 |
| `COMPRESSION_THRESHOLD` | int. 기본 8000 | 지름길 기준 문자 수. 호출마다 읽음. 숫자가 아니면 `ValueError`(R-22) |
| `MAX_CONTENT_CHARS` | int. 기본 50000 | 페이지 하나에서 청크 분할 전에 쓰는 앞쪽 문자 수 상한. `retriever.py` 로드 시 한 번 읽음 |
| `SIMILARITY_THRESHOLD` | float. Config 기본 0.42 | embeddings 모드의 유사도 임계값. Config가 환경변수로 덮어 `cfg.similarity_threshold`가 된다 |
| Jev 요청 | `POST https://api.typesafe.ai/v1/systemone`, 헤더 `Authorization: Bearer <키>`, JSON 본문 `{state: <청크>, model: <JEV_MODEL>, questions: {usefulness: {type: "score", instructions: "How useful is this passage for answering the question: <query>", criteria: [4개 문장]}}}`, 요청 제한 시간 30초 | `criteria` 4개 문장은 C-05의 `RELEVANCE_LEVELS`. 청크 하나가 요청 하나다 |
| Jev 응답 | 상태 200, JSON `{answers: {usefulness: {score: number}}, usage: {input_tokens: int}}` | `score`를 float로 읽는다. 범위 검사는 없다(문서는 0~3). `usage`가 없으면 토큰 0 |
| `JevError` | 예외 | Jev를 쓸 수 없다는 뜻(키 없음, HTTP 오류, 응답 형식 오류, 재시도 소진). `select_context`가 이것만 잡는다 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 모드 결정 | `(cfg.context_filter 또는 "auto")`를 공백 제거·소문자화한다. `""`와 `None`은 `auto`. 다섯 값에 없으면 경고를 남기고 `auto`로 본다. `auto`는 `TYPESAFE_API_KEY`가 비어 있지 않으면 `jev`, 아니면 `keyword`. 그 밖의 값은 그대로 모드가 된다(`jev`는 키가 없어도 `jev`로 결정되고, 키 없음은 R-10에서 폴백으로 처리된다). | 코드 확인 (C-01), 실행 확인(T-01) |
| R-02 | `context_filter`·`TYPESAFE_API_KEY`를 읽는 위치 | `context_filter`는 `cfg` 속성에서, `TYPESAFE_API_KEY`는 환경변수에서 `select_context` 호출 때마다 읽는다. 호출이 진행되는 동안 환경이 바뀌면 다음 호출부터 달라진다 | 코드 확인 (C-01, C-02) |
| R-03 | 모드 `none` | 지름길 판정 없이, 모든 페이지를 입력 순서대로 문서 하나씩으로 바꿔 포맷한다. 개수 상한이 없고 청크로 자르지도 않는다. 단, 페이지마다 `raw_content` 앞 `MAX_CONTENT_CHARS`(50000)자만 쓴다. 페이지 목록이 비면 `""` | 코드 확인 (C-02, C-08), 실행 확인(T-05) |
| R-04 | 지름길: 모드가 `none`이 아니고, 전체 `raw_content` 길이 합(없으면 0, 절단 전 길이)이 `COMPRESSION_THRESHOLD`(8000) **미만**이고, 페이지 수가 `max_results`(호출자 기본 10) **이하** | 선별과 외부 호출 없이 앞 `max_results`개 페이지를 문서로 바꿔 포맷해 돌려준다(청크 분할 없음, 입력 순서). `jev`에서 키가 없어도, `embeddings`에서 `embeddings()` 함수가 없거나 실패할 상황에서도 이 경로면 실패하지 않는다. 합이 정확히 8000이거나 페이지가 11개 이상이면 지름길이 아니다 | 코드 확인 (C-02), 실행 확인(T-02) |
| R-05 | 모드 `jev`이고 지름길이 아님 | `JevClient`를 만들고(R-10), 페이지를 문서로 바꾼 뒤 `JEV_CHUNK_SIZE`(겹침 `//10`)로 분할해 공백뿐인 청크를 버린다. 모든 청크를 동시에 점수 요청하고(R-07, R-08), 점수 내림차순(동점은 위치 순)으로 정렬해 `JEV_MIN_SCORE` 이상인 것만 앞 `max_results`(10)개 남겨 포맷한다. 기준을 넘는 청크가 하나도 없으면 `""`를 돌려주며 keyword로 내려가지 않는다. 청크 수에 상한이 없으므로 요청 수는 청크 수와 같다 | 코드 확인 (C-07), 실행 확인(T-06, 스텁 서버) |
| R-06 | Jev 요청 한 건 | 형식은 1.3의 "Jev 요청". 모델은 `JEV_MODEL`, 제한 시간 30초, 키는 `Authorization: Bearer`. 서버가 이 요청을 이렇게 받아 점수를 준다는 것은 클라이언트의 가정이다 | 코드 확인 (C-05, C-06), 실행 확인(T-07, 스텁이 요청을 기록). 서버 수락 여부는 미확인 |
| R-07 | Jev 응답 처리와 재시도 | 상태 200이고 `answers.usefulness.score`를 float로 읽을 수 있으면 그 값이 점수다(`usage.input_tokens`는 합산). 200인데 JSON이 아니거나 키가 없거나 숫자가 아니면 재시도 없이 `JevError`. 상태 429·529이거나 `httpx.HTTPError`(연결·시간 초과 포함)면 재시도 대상이고, 총 4번(최초 1 + 재시도 3)까지 시도하며 시도 사이에 0.5, 1, 2초를 쉰다(쉬는 동안 동시성 슬롯은 반납). 마지막 시도까지 실패하면 `JevError`. 그 밖의 상태 코드는 재시도 없이 즉시 `JevError`. 한 청크라도 `JevError`가 나면 jev 선별 전체가 `JevError`로 끝난다 | 코드 확인 (C-06), 실행 확인(T-08, 스텁 서버). 실패한 청크 외의 진행 중 요청이 어떻게 정리되는지는 미확인 |
| R-08 | Jev 동시성 | 요청 시도 하나가 시작될 때마다 이벤트 루프별로 공유되는 세마포어의 슬롯 하나를 쓴다. 세마포어는 그 루프에서 처음 필요할 때 `JEV_CONCURRENCY`(64)로 만들어지고, 같은 루프의 모든 서브쿼리·모든 `JevContextCompressor`가 같은 것을 쓴다. 이후 환경변수를 바꿔도 그 루프에서는 바뀌지 않는다 | 코드 확인 (C-05), 실행 확인(T-09: 동시 진행 최대 4). 루프별 공유·고정은 코드 확인만 |
| R-09 | Jev 비용 보고 | 점수 계산이 모두 끝나면(선별 전) `cost_callback`이 있을 때 한 번 `입력 토큰 합 / 1,000,000 × 0.042`(USD)를 넘긴다. 점수 계산이 실패하면 호출하지 않는다. 지름길·`none`에서도 호출하지 않는다 | 코드 확인 (C-06, C-07), 실행 확인(T-06, T-10) |
| R-10 | jev 실패 처리 | `select_context`는 `JevError`만 잡아 경고(`Jev context filter unavailable (...)`)를 남기고 keyword(R-14)로 계속한다. 키가 없으면 `JevClient` 생성이 `JevError`를 내므로 요청을 한 번도 보내지 않고 keyword로 간다. `JevError`가 아닌 예외(`JEV_MIN_SCORE`·`JEV_CHUNK_SIZE`·`JEV_CONCURRENCY` 값이 숫자가 아니어서 생기는 `ValueError`, 응답의 `usage`가 `null`일 때의 `AttributeError` 등)는 잡히지 않고 `select_context` 밖으로 전파된다 | 코드 확인 (C-02, C-06, C-07), 실행 확인(T-10). `usage: null`은 코드만 읽음 |
| R-11 | 모드 `embeddings`이고 지름길이 아님 | 임베딩 선별 모듈을 불러오고, `embeddings` 함수가 있으면 호출해 임베딩 객체를 얻는다(없으면 `None`). `ContextCompressor`를 `similarity_threshold=cfg.similarity_threshold`로 만든다(Config 기본 0.42). 비용을 먼저 보고하고(R-13) 별도 스레드에서 다음을 실행한다: 페이지를 문서로 바꾸고, 1000자·겹침 100자로 분할하고, `EmbeddingsFilter`(임베딩 객체, 임계값)로 질의와 청크의 유사도를 비교해 걸러낸다. 결과 앞 `max_results`(10)개를 포맷한다. `EmbeddingsFilter`가 개수를 얼마로 제한하고 임계값을 `>`로 비교하는지, 결과 순서가 점수순인지는 이 레포 안에 없어 확인하지 못했다(미결정) | 코드 확인 (C-09). 실행하지 못함. 필터 내부 동작은 미확인 |
| R-12 | embeddings 실패 처리 | 위 R-11 안의 어떤 `Exception`이든(모듈 import 실패, `embeddings()` 함수 예외, 필터 생성·실행 예외) 잡아 경고(`Embedding context filter unavailable (...)`)를 남기고 keyword로 간다. 임베딩 객체를 공급하지 않은 호출(`embeddings` 함수가 `None`)은 `None` 임베딩으로 `ContextCompressor`를 만들고, 어느 단계에서든 예외가 나면 같은 폴백이 된다 | 코드 확인 (C-02). 실행 확인(T-11: `langchain_classic` 미설치로 import 실패해 폴백). `None` 임베딩이 예외가 된다는 점은 추론 |
| R-13 | embeddings 비용 보고 | `cost_callback`이 있으면 유사도 필터를 돌리기 **전에** `estimate_embedding_cost(OPENAI_EMBEDDING_MODEL, docs=pages)`를 한 번 보고한다. 모델 이름은 실제 설정된 임베딩 모델이 아니라 환경변수 `OPENAI_EMBEDDING_MODEL`(기본 `text-embedding-3-small`)이고 단가는 100만 토큰당 0.02 USD다. 토큰은 페이지 dict의 `str()` 전체로 센다. 이후 필터가 실패해 keyword로 내려가도 이 보고는 이미 일어난 뒤다. 이 계산이 예외를 내도 R-12로 폴백한다 | 코드 확인 (C-09, C-14) |
| R-14 | 모드 `keyword`(또는 폴백) | `LexicalContextCompressor`를 `relative_threshold=KEYWORD_RELATIVE_THRESHOLD`(0.5)로 만들고 `KEYWORD_MAX_RESULTS`(25)를 상한으로 준다. 청크 분할은 1000자·겹침 100자 고정(환경변수 없음). BM25 점수(R-16)를 청크마다 구해, `점수 >= 임계값 × 최고점`인 청크를(최고점 청크 자신 포함) 점수 내림차순(동점은 위치 순)으로 앞 25개 고른다. `select_context`의 `max_results`(10)는 이 경로에서 쓰이지 않고, 포맷의 `top_n`도 25다 | 코드 확인 (C-02, C-04), 실행 확인(T-03, 스텁 분할기) |
| R-15 | keyword 점수가 전부 0 | 최고점이 0 이하이면(질의의 의미 있는 단어가 어느 청크에도 없음, 질의가 비었거나 불용어뿐, 청크가 없음 모두 포함) 점수를 쓰지 않고 전체 청크 목록의 앞 25개를 페이지 순서·청크 순서 그대로 돌려준다. 페이지마다 첫 청크를 하나씩 뽑는 것이 아니므로 앞 페이지가 25개를 채우면 뒤 페이지는 하나도 들어가지 않는다. 청크가 없으면 `""` | 코드 확인 (C-04), 실행 확인(T-04) |
| R-16 | BM25 점수 | 토큰화·불용어·어간 처리·IDF·점수식은 C-03이 정의한다(소문자, `\w+`, 영어 불용어 제거, 한 글자 제외, 복수형 간단 제거). IDF는 이번 호출의 청크 집합(모든 페이지)에서 계산하고 질의 단어는 중복을 없앤다. 한국어 등 영어가 아닌 글자도 토큰이 되지만 불용어 제거와 어간 처리는 영어 기준이다 | 코드 확인 (C-03), 실행 확인(T-03, T-04의 값) |
| R-17 | keyword는 외부 호출 없는 로컬 계산이다 | 이벤트 루프 안에서 직접 계산한다(스레드로 넘기지 않음). 마지막 단계이므로 여기서 예외가 나면 폴백 없이 `select_context` 밖으로 전파된다 | 코드 확인 (C-02, C-04) |
| R-18 | 청크 입력 준비(모든 모드) | 페이지 → 문서: `page_content = (raw_content 또는 "")[:MAX_CONTENT_CHARS]`, `metadata.title = page.get("title", "")`, `metadata.source = page.get("url", "")`. 이 변환이 없는 페이지 키는 쓰지 않는다. 분할은 `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)`의 기본 구분자 그대로이고 공백뿐인 청크는 버린다. 메타데이터는 청크로 이어진다. 즉 한 페이지에서 50000자 뒤의 내용은 어떤 모드에서도 선별 대상이 아니다 | 코드 확인 (C-08, C-04, C-07), 실행 확인(T-05). 분할기 내부 동작은 라이브러리(확인 한계) |
| R-19 | 반환 문자열 형식 | 기본 `prompt_family`: 문서 하나가 `Source: <source>\nTitle: <title>\nContent: <내용>\n`이고, 문서들을 `"\n"`으로 이어 문서 사이에 빈 줄이 하나 생기며 끝은 `\n`이다. `top_n`보다 뒤의 문서는 버린다. 문서가 없으면 `""`. 순서는 선별 순서(점수순)이며 페이지 순서가 아니다. `prompt_family`가 Granite 계열이면 형식이 다르다(C-10) | 코드 확인 (C-10), 실행 확인(T-13, 기본 형식) |
| R-20 | 호출 경계: 연구의 서브쿼리 | `ContextManager.get_similar_content_by_query(query, pages)`는 `researcher.verbose`이면 진행 로그 한 건을 스트리밍한 뒤, `select_context(query, pages, researcher.cfg, max_results=10, prompt_family=researcher.prompt_family, cost_callback=researcher.add_costs, embeddings=lambda: researcher.memory.get_embeddings())`를 부르고 결과 문자열을 그대로 돌려준다. `researcher.memory`는 처음 접근할 때 임베딩 모델을 만드는 게으른 속성이라, embeddings 모드가 필터 단계에 들어가기 전에는 임베딩 모델이 만들어지지 않는다. 이 메서드에는 예외 처리가 없다 | 코드 확인 (C-11, C-15) |
| R-21 | 호출 경계: 보고서 채팅 | 보고서 채팅은 `vector_store`가 없을 때 같은 `select_context(최신 사용자 메시지, [{"url": "report", "title": "Research report", "raw_content": 보고서}], 채팅용 Config)`를 부른다(`max_results` 기본 10, `embeddings` 없음, 기본 `prompt_family`). 예외가 나거나 결과가 빈 문자열이면 보고서 전체를 쓴다. 보고서가 8000자 미만이면 지름길로 보고서 전체가 `Source: report` 블록으로 돌아온다 | 코드 확인 (C-12). 지름길 결과 형식은 R-04·R-19에서 도출 |
| R-22 | 설정 값 오류 | `COMPRESSION_THRESHOLD`가 정수가 아니면 `select_context`가 지름길 판정에서 `ValueError`를 낸다(모드가 `none`일 때는 그 판정 전에 반환하므로 영향 없음). `KEYWORD_RELATIVE_THRESHOLD`·`KEYWORD_MAX_RESULTS`가 숫자가 아니면 `context/select.py` 모듈을 불러오는 시점에 `ValueError`다. 이 예외들은 폴백으로 처리되지 않는다 | 코드 확인 (C-01, C-02), 실행 확인(T-12) |

- 불변식:
  - `select_context`는 항상 문자열을 돌려주거나 예외를 던진다. `None`은 돌려주지 않는다.
  - `none`이 아닌 모드에서 `jev`·`embeddings`의 실패(R-10, R-12)는 호출자에게 예외로 전달되지 않는다. 지름길은 모든 모드에서 선별 코드를 부르지 않는다.
  - 결과의 각 `Content:`는 원본 페이지의 앞 `MAX_CONTENT_CHARS`자 안에서 잘린 부분 문자열이다(청크 분할 겹침 때문에 인접 청크는 일부가 겹칠 수 있다). 페이지에 없는 문자열이 만들어지지는 않는다(추론: 분할기가 문자열을 자르기만 한다는 가정).
- 미결정:
  - R-11 · 설치된 `langchain-classic`(`pyproject.toml`은 `>=1.0.0`)의 `EmbeddingsFilter`가 청크를 몇 개까지 돌려주는지, 임계값 비교가 `>`인지 `>=`인지, 결과가 점수순인지 입력순인지는 이 레포에서 확인하지 못했다. 같은 라이브러리·클래스를 쓰면 원본과 같다. 직접 구현한다면 제3자 자료(langchain master의 소스를 웹으로 요약해 본 것, 기준 버전과 다를 수 있음)의 값(최대 20개, 임계값 초과만 `>`, 점수 내림차순)을 임시 가정으로 쓰되 미확인이다. 구현에 미치는 영향: embeddings 모드의 결과 청크 수와 순서.
- 확인 한계:
  - `jev` 모드는 실제 TypeSafe 서버를 부르지 않았다(9장). 스텁 서버로 클라이언트 쪽 요청 형식·재시도·점수 선별만 확인했다. 서버가 실제로 이 요청을 받아 어떤 점수를 주는지, 429·529 외의 상태 코드를 어떻게 돌려주는지는 미확인이다. 점수 의미(0~3)는 `RELEVANCE_LEVELS`와 docstring에서 온 클라이언트 쪽 설명이다.
  - `langchain_core`, `langchain_text_splitters`, `httpx`, `langchain_classic`이 이 환경에 설치돼 있지 않아 실제 라이브러리로 돌리지 못했다. 청크 분할 결과(경계·겹침)와 `embeddings` 모드의 정상 경로는 실행 확인이 없다. 실험은 분할기를 "빈 줄로만 나누는 대체물"로 바꿨고, 문단이 500~900자라서 실제 분할기도 문단마다 청크 하나를 만들 것이라는 가정으로 입력을 골랐다(가정이며 확인하지 않음).
  - jev 선별 중 한 청크가 `JevError`를 내면 `asyncio.gather`가 바로 예외를 올리고 나머지 요청이 어떻게 되는지(그 시점에 HTTP 세션이 닫힘)는 실제 `httpx`로 확인하지 못했다. 스텁에서는 영향이 없었다.

### 1.5 필수 코드 참조

라이선스: 인용 허용 여부는 overview 1절(Apache 2.0 LICENSE와 MIT 표기가 어긋남)을 따른다. 이 스펙은 코드를 옮겨 적지 않고 위치만 가리킨다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `gpt_researcher/context/select.py:29-46` `CONTEXT_FILTERS`, `KEYWORD_RELATIVE_THRESHOLD`, `KEYWORD_MAX_RESULTS`, `resolve_context_filter` | 모드 5개, keyword 상수와 기본값, 모드 결정 함수 전체 | R-01, R-02, R-22 |
| C-02 | `select.py:49-101` `_as_documents`, `select_context` | 모드별 분기 순서(none → 지름길 → jev → embeddings → keyword), 잡는 예외 종류, 각 경로가 부르는 인자(keyword는 `KEYWORD_MAX_RESULTS`, 다른 모드는 `max_results`) | R-02~R-05, R-10~R-12, R-14, R-17, R-22 |
| C-03 | `gpt_researcher/context/lexical.py:19-66` `_TOKEN`, `_STOPWORDS`, `_stem`, `tokenize`, `bm25_scores` | 토큰 정규식, 영어 불용어 목록, 어간 규칙, BM25(k1=1.5, b=0.75, IDF 식) | R-16 |
| C-04 | `lexical.py:69-107` `LexicalContextCompressor` | 청크 분할(기본 1000/100), 점수 0일 때 폴백, 정렬 키 `(-점수, 위치)`, 임계값·상한 적용, 포맷 호출 | R-14, R-15, R-17, R-18 |
| C-05 | `gpt_researcher/context/jev_filter.py:32-53` `JEV_API_URL`, `JEV_INPUT_PRICE_PER_MTOK`, `RELEVANCE_LEVELS`, `_SEMAPHORES`, `_concurrency` | API 주소, 단가 0.042, 평가 기준 4문장, 루프별 세마포어 | R-06, R-08, R-09 |
| C-06 | `jev_filter.py:56-123` `JevError`, `JevClient` | 키·모델 읽기, 요청 본문·헤더, 재시도 상태 코드와 대기 시간, 응답 파싱, 비용 식 | R-06, R-07, R-09, R-10 |
| C-07 | `jev_filter.py:126-184` `JevContextCompressor` | 청크 크기·최소 점수 환경변수, 동시 요청, 점수 정렬·선별·비용 보고 순서. 안의 지름길(`:169-178`)은 `select_context`를 거치면 도달하지 않는다 | R-05, R-09, R-10, R-18 |
| C-08 | `gpt_researcher/context/retriever.py:9-38` `_MAX_CONTENT_CHARS`, `SearchAPIRetriever` | 페이지 → 문서 변환(`raw_content` 절단, 메타데이터 키) | R-03, R-18 |
| C-09 | `gpt_researcher/context/compression.py:85-188` `ContextCompressor` | embeddings 모드의 분할·`EmbeddingsFilter` 구성, 임계값 폴백(env 0.35), 비용 보고 시점, 스레드 실행. 안의 지름길(`:162-181`)은 `select_context`를 거치면 도달하지 않는다 | R-11, R-12, R-13 |
| C-10 | `gpt_researcher/prompts.py:555-562` `PromptFamily.pretty_print_docs`; 형식 변형 `:769-770`, `:776-833` | 기본 반환 문자열 형식과 `top_n` 처리, Granite 계열 형식 | R-19 |
| C-11 | `gpt_researcher/skills/context_manager.py:38-64` `ContextManager.get_similar_content_by_query` | `select_context` 호출 인자 전체 | R-20 |
| C-12 | `backend/chat/chat.py:186-195` | 보고서 채팅의 호출 인자와 예외·빈 결과 처리 | R-21 |
| C-13 | `gpt_researcher/config/variables/default.py:6-7`; `config/config.py:54-67` `_set_attributes` | `SIMILARITY_THRESHOLD` 0.42, `CONTEXT_FILTER` `auto` 기본값, 환경변수가 Config 값을 덮고 키가 소문자 속성이 됨 | R-01, R-11, 1.3 |
| C-14 | `gpt_researcher/utils/costs.py:12-16`, `:319-337` `estimate_embedding_cost`; `gpt_researcher/memory/embeddings.py:28-30` `OPENAI_EMBEDDING_MODEL` | 임베딩 비용 추정 식과 모델 이름 | R-13 |
| C-15 | `gpt_researcher/agent.py:283-289` `GPTResearcher.memory` | 임베딩 객체를 처음 접근할 때 만드는 게으른 속성 | R-20 |

### 1.6 수락 사례

출처: T-01~T-13은 구현에서 도출하고, 실제 소스를 불러 오프라인으로 실행해 관찰했다(스크립트·출력은 2.1 끝). 단 `langchain_core`·`langchain_text_splitters`·`httpx`는 대체물이므로 jev 사례의 서버 응답은 가짜(형식을 보이려는 예시)이고, 청크는 빈 줄 기준 문단이다(문단 500~900자). T-14, T-15는 구현에서 도출했고 실행하지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | `TYPESAFE_API_KEY` 없음, 설정값 `None`, `""`, `auto`, `" JEV "`, `Keyword`, `foo`. 이어서 키 있음으로 같은 값. 키가 빈 문자열 `""` | 키 없음: keyword, keyword, keyword, jev, keyword, keyword(경고). 키 있음: jev, jev, jev, jev, keyword, jev(경고). 빈 문자열 키는 `auto`에서 keyword. `embeddings`·`none`은 키와 무관하게 그대로 |
| T-02 | R-04 | 모드 keyword. 짧은 페이지 2개(합 8000자 미만). 짧은 페이지 11개(질의와 겹치는 단어 없음). `COMPRESSION_THRESHOLD=0`에 짧은 페이지 2개(질의 `q`) | 첫째: 질의와 상관없이 두 페이지가 입력 순서로 모두 나옴(`Source: http://s1\nTitle: S1\nContent: tiny one\n\nSource: http://s2\nTitle: S2\nContent: tiny two battery\n`). 둘째: 지름길이 아니므로 keyword 경로로 가고 R-15에 따라 청크 11개. 셋째: 지름길이 꺼져 keyword 경로로 가지만 질의 `q`는 의미 있는 단어가 없어(한 글자) R-15에 따라 청크 2개가 같은 형식으로 나옴 |
| T-03 | R-14, R-16 | 한 페이지에 문단 5개(질의 `battery cost`: 문단 1은 두 단어가 여러 번, 문단 2는 두 단어 한 번씩, 3은 무관, 4는 `cost`만, 5는 `battery`만). 임계값 0.0 / 0.5 / 0.9와 `max_results` 2 | 청크 점수 [1.794, 1.075, 0.0, 0.538, 0.542]. 임계값 0.5: 청크 0, 1. 0.9: 청크 0. 0.0: 0, 1, 4, 3, 2(점수 순). 0.0에 상한 2: 0, 1. 토큰화 결과 `batteries`→`battery`, `costs`→`cost`, `movies`→`movy`, `classes`→`class`, `cars`→`cars`(길이 4 이하), 한국어 단어는 그대로 토큰 |
| T-04 | R-15, R-16 | 페이지 A(문단 5개)와 B(문단 1개). 질의 `quantum zebra`, `the of and`, `""`, 상한 3 | 세 질의 모두 청크 3개가 전부 A 출처다(B의 청크는 하나도 없음) |
| T-05 | R-03, R-18 | 모드 none. `MAX_CONTENT_CHARS=50`에 120자 페이지 하나. 기본값에 15개 짧은 페이지 | 첫째: `Content`가 50자. 둘째: 15개 모두 나옴(상한 없음) |
| T-06 | R-05, R-09 | `TYPESAFE_API_KEY` 있음, 모드 `auto`. 청크 15개, 스텁 서버 점수: `ANSWER` 포함 3.0, `partial` 포함 1.6, 나머지 0.4, 청크당 `input_tokens` 200. `JEV_MIN_SCORE` 기본 / 3.0 / 9 / 0 | 요청 15번. 기본: ANSWER 청크 둘(문서 순), partial 청크 하나 순으로 3개. 3.0: 2개. 9: `""`(keyword로 내려가지 않음). 0: 15개 중 10개이고 앞 둘이 ANSWER 청크. 비용 보고 한 번, 값 0.000126 |
| T-07 | R-06 | 위 T-06의 첫 요청 | URL `https://api.typesafe.ai/v1/systemone`, 헤더 `{'Authorization': 'Bearer sk-demo'}`, 제한 시간 30.0, 본문 키 `model`·`questions`·`state`, `model` `jev-latest`, `questions.usefulness`는 `type: score`, `instructions: How useful is this passage for answering the question: battery cost`, `criteria` 4개 |
| T-08 | R-07, R-10 | 스텁 서버: 모든 응답 401 / 429, 429, 200 / 429 연속 / 529 연속 / `HTTPError` 연속 / 200이나 `answers` 키 없음·JSON 아님·점수가 `"abc"` | 401: 청크마다 1번만 시도하고 경고 후 keyword(3개). 429,429,200: 3번 시도 뒤 점수 3.0, 약 1.5초. 429 연속: 4번 뒤 `JevError`(약 3.6초). 529·`HTTPError`: 4번 시도. 200이나 형식 오류: 1번 만에 `JevError` |
| T-09 | R-08 | `JEV_CONCURRENCY=4`, 청크 15개 | 동시에 진행 중인 요청이 최대 4. 기본값이면 한 루프의 세마포어가 64 |
| T-10 | R-10, R-09 | 청크 하나만 HTTP 500. `jev`인데 키 없음. `JEV_MIN_SCORE=high`. `JEV_CONCURRENCY=x` | 500: jev 전체가 버려지고 keyword 결과(3개), `cost_callback` 호출 0번. 키 없음: 요청 0번, keyword 결과. `high`·`x`: `ValueError`가 `select_context` 밖으로 나옴 |
| T-11 | R-12, R-04 | 모드 embeddings, `langchain_classic` 미설치, 큰 입력과 `embeddings` 함수(호출 횟수를 셈) / 같은 모드에 작은 입력 | 큰 입력: 경고 `Embedding context filter unavailable (No module named 'langchain_classic'); using keyword ranking`을 남기고 keyword 결과, 함수는 호출되지 않음(import가 먼저 실패하므로). 작은 입력: 지름길이라 함수 호출 0번 |
| T-12 | R-22, R-14 | `COMPRESSION_THRESHOLD=abc` / `KEYWORD_MAX_RESULTS=ten` / `KEYWORD_RELATIVE_THRESHOLD=half`로 모듈 로드 / `KEYWORD_MAX_RESULTS=2`, `max_results=10` | 첫째: 호출이 `ValueError`. 둘째·셋째: 모듈 로드가 `ValueError`. 넷째: keyword 결과 청크 2개(`max_results`는 무시) |
| T-13 | R-19 | 기본 `prompt_family`, 페이지 `{url: u, title: t, raw_content: None}` / `{url: u, raw_content: "x"}` / 페이지 없음 / 두 페이지 | `Source: u\nTitle: t\nContent: \n` / `Source: u\nTitle: \nContent: x\n` / `""` / 두 블록이 `\n`으로 이어짐(블록 사이 빈 줄 하나, 끝 `\n`) |
| T-14 | R-21 | 보고서 채팅. 보고서 500자, 사용자 메시지 `질문`, `CONTEXT_FILTER` 기본 | 지름길(500 < 8000, 페이지 1개)이라 `Source: report\nTitle: Research report\nContent: <보고서 500자>\n`. `select_context`가 예외를 내거나 `""`를 돌려주면 보고서 전체 |
| T-15 | R-11, R-13, R-20 | 연구 호출, 모드 embeddings, 8000자 이상의 페이지, `cfg.similarity_threshold`=0.42, 사용 가능한 임베딩 객체 | `embeddings()`가 한 번 호출되고, `cost_callback`이 필터 전에 한 번 비용을 받고, `EmbeddingsFilter`가 임계값 0.42로 걸러 낸 청크 중 앞 10개가 포맷된다(청크 수·순서는 R-11의 미결정). 미실행 |

## 2부. 근거

### 2.1 요구사항별 근거 지도

| R-ID / T-ID | 근거 (repo@3582a68 `파일:줄` `심볼`, 실행 기록) | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 `select.py:38-46`; 기본값 C-13 | 코드를 읽고 `resolve_context_filter`를 소스 그대로 실행(T-01) |
| R-02 | `select.py:68`, `:45` | 코드를 읽음 |
| R-03 | `select.py:71-72`, `retriever.py:13`, `:29` | 코드를 읽고 실행(T-05) |
| R-04 | `select.py:74-77` | 코드를 읽고 실행(T-02). 문자 수 합은 `str(p.get("raw_content") or "")`의 길이라 `None`은 0 |
| R-05 | `select.py:79-82`, `jev_filter.py:144-155`, `:157-184` | 스텁 서버로 실행(T-06) |
| R-06 | `jev_filter.py:32`, `:72-75`, `:84-101` | 실행으로 요청 인자를 기록(T-07). 서버 쪽은 미확인 |
| R-07 | `jev_filter.py:98-119` | 스텁 서버로 실행(T-08). 실제 `httpx` 예외 계층은 실행하지 못함(스텁의 `HTTPError`가 `except httpx.HTTPError`에 잡힘) |
| R-08 | `jev_filter.py:43-53`, `:99` | 실행(T-09). 루프별 `WeakKeyDictionary` 키잉은 코드만 읽음 |
| R-09 | `jev_filter.py:111`, `:121-123`, `:181-182` | 실행(T-06) |
| R-10 | `select.py:83-84`, `jev_filter.py:73-74`, `:111`, `:144-150` | 실행(T-10). `usage: null`은 `body.get("usage", {})`가 `None`을 돌려줄 수 있다는 코드 읽기 |
| R-11 | `select.py:86-95`, C-09 `compression.py:98-146`, `:183-188` | 코드만 읽음. 필터 내부는 langchain-classic: 로컬 미설치. 웹으로 langchain master의 `embeddings_filter.py`를 요약해 본 값(k 기본 20, 임계값 `>`, k가 있으면 점수 내림차순)은 제3자 자료이며 설치 버전과의 일치는 미확인 |
| R-12 | `select.py:96-97` | 실행(T-11: import 실패 사례만). `None` 임베딩은 `EmbeddingsFilter`가 필수 필드로 받으므로 생성에서 실패하거나, 만들어져도 `invoke`의 임베딩 호출에서 실패해 둘 다 `try` 안이라 폴백이 된다는 추론 |
| R-13 | `compression.py:185-186`, `costs.py:319-337`, `embeddings.py:28-30` | 코드를 읽음. 실제 토큰 수는 계산하지 않음(`tiktoken` 미실행) |
| R-14 | `select.py:99-101`, `lexical.py:90-107` | 스텁 분할기로 실행(T-03, T-12) |
| R-15 | `lexical.py:98-101` | 실행(T-04) |
| R-16 | C-03 | 실행(T-03: 토큰화·어간·점수 값) |
| R-17 | `lexical.py:106-107` | 코드를 읽음 |
| R-18 | `retriever.py:16-38`, `lexical.py:90-93`, `jev_filter.py:152-155`, `compression.py:134`, `:140-142` | 실행(T-05, T-13). 분할기 동작은 대체물 |
| R-19 | `prompts.py:555-562` | `ast`로 원본 함수를 꺼내 실행(T-13). Granite 변형은 읽기만 |
| R-20 | `context_manager.py:38-64`, `agent.py:283-289`; 호출 위치 `skills/researcher.py:258`, `:612`, `:845`, `:1120` | 코드를 읽음. 호출 관계는 경계 설명용 |
| R-21 | `backend/chat/chat.py:186-195` | 코드를 읽음. 실행하지 않음 |
| R-22 | `select.py:34-35`, `:76` | 실행(T-12) |
| T-01~T-13 | 위 R-ID의 근거 | `artifacts/gpt-researcher/context-selection-demos/demo_context_selection.py`의 출력(절 1~9) |
| T-14, T-15 | 위 R-ID의 근거 | 구현에서 도출. 미실행 |

**문서와 구현의 차이**
- `select.py` docstring(`:10`)과 `docs/docs/gpt-researcher/gptr/context-filter.md`는 `none`을 "모든 페이지를 통째로"라고 쓰지만, 구현은 페이지마다 앞 `MAX_CONTENT_CHARS`(50000)자만 쓴다(R-03). 구현을 사실로 썼다.
- 같은 문서는 "`jev`는 어떤 실패에서도 keyword로 내려간다"고 쓰지만, `select_context`는 `JevError`만 잡는다. 환경변수 값 오류의 `ValueError` 등은 전파된다(R-10). embeddings는 `Exception` 전체를 잡는다(R-12).
- `lexical.py:100`의 주석과 `context-filter.md`는 겹치는 단어가 없으면 "페이지들의 첫 청크를 쓴다"고 하지만, 구현은 전체 청크 목록의 앞 25개를 쓰므로 한 페이지가 앞을 채울 수 있다(R-15, T-04). 구현을 사실로 썼다.
- `ContextCompressor`의 임계값 기본값은 환경변수 `SIMILARITY_THRESHOLD`가 없을 때 0.35이고 Config 기본값은 0.42다. `select_context`는 항상 `cfg.similarity_threshold`(Config 기본 0.42)를 넘기므로 0.35는 `select_context`를 거치면 쓰이지 않는다(`compression.py:122-123`, `default.py:6`). `docs/docs/gpt-researcher/gptr/config.md:86`은 0.42로 맞다.
- `JevContextCompressor.async_get_context`와 `ContextCompressor.async_get_context`는 자체 지름길을 갖고 있지만 `select_context`가 같은 조건을 먼저 검사하므로 도달하지 않는다. 두 클래스를 직접 쓰는 호출자(이 레포에서는 `evals/context_filter/replay.py`만 확인)에서는 `ContextCompressor`가 `raw_content`가 `None`인 페이지를 `str(None)`, 즉 4자로 센다는 차이가 있다(`compression.py:163`).
- `JevContextCompressor.__init__`·`ContextCompressor.__init__`의 `max_results=5` 인자는 `async_get_context`가 쓰지 않는 값이다. 실제 한도는 `async_get_context`의 `max_results` 인자다.

**실행 기록**: `artifacts/gpt-researcher/context-selection-demos/demo_context_selection.py`(출력 `demo_context_selection.out`, 2026-10-22, Python 3.12.13, `python -I`). `repos/` 안 파일은 고치지 않고 읽기만 했다.
- 실제 소스: `context/select.py`, `lexical.py`, `jev_filter.py`, `retriever.py`를 가짜 패키지 객체(`gpt_researcher/__init__.py`는 실행하지 않음)로 불러 그대로 실행했다. `compression.py`는 실제 파일이 로드를 시도하다 `langchain_classic` 미설치로 실패한다. `prompts.py`는 `PromptFamily.pretty_print_docs` 함수 하나만 `ast`로 꺼내 실행했다.
- 대체물: `langchain_core`(`Document`, `BaseRetriever` 최소 구현), `langchain_text_splitters`(빈 줄 분할기, 인자 기록), `httpx`(스크립트가 응답을 정하는 가짜 클라이언트, 소켓 없음). 가짜 입력(문단 텍스트, 점수 규칙)은 형식을 보이려는 예시다.
- 검증하지 않은 것: 실제 청크 분할 경계·겹침, `embeddings` 모드의 정상 경로와 `EmbeddingsFilter`, 실제 Jev 서버, 실제 `httpx` 예외·세션 닫힘 동작, 토큰 계산(`tiktoken`).

### 2.2 코드 읽는 순서

1. `skills/context_manager.py:38-64`(호출 경계) → `context/select.py`(전체 101줄, 모드 분기).
2. `context/retriever.py:16-38`(페이지 → 문서) → `context/lexical.py`(keyword, 가장 단순한 경로).
3. `context/jev_filter.py`(`JevClient` → `JevContextCompressor`) → `context/compression.py:85-188`(embeddings).
4. 포맷: `prompts.py:555-562`.

원본의 전략: 모든 모드가 같은 후보(페이지당 50000자 절단 + 1000자 청크)를 만들고 "어떤 청크를 남길지"만 다르게 한다. 외부 호출을 하는 단계는 모두 `try`로 감싸 keyword로 내려가므로 선별 방법이 틀어져도 컨텍스트가 비지 않게 하려는 설계로 읽힌다(추론, docstring `select.py:12`). 임계값(상대 점수·최소 점수)을 쓰고 개수를 채우지 않는 것은 `docs/.../context-filter.md`가 벤치마크 근거로 설명한다(미확인: 벤치마크 재현은 하지 않음).

### 2.3 비교·재사용 출처

없음.

## 적용 메모

없음.
