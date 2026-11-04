---
sha: "3582a6841fe7dc801e2a34e34ee408641aea9bce"
created: 2026-10-22
updated: 2026-10-22
---

# Next Session Plan: GPT Researcher

- **상위 개요**: [overview.md](./overview.md)

---

## 1. 이번 세션에서 확인한 범위

- [x] 기준 고정, 기능 지도 21행, 공유 계약 4개, 구조도 1개
- [x] 승인한 9행의 기능 스펙 작성: research-pipeline, source-modes, retrievers, scrapers, context-selection, report-writing, detailed-report, deep-research, mcp-client (`ready` 5 / `draft` 4)
- [x] 오프라인 실행 확인(`artifacts/gpt-researcher/*-demos/`): URL 검증·스크랩 판정, keyword·jev 선별, 마크다운 순수 함수, 상세 보고서 조립, Deep Research 재귀, MCP 설정 변환. LLM·네트워크·패키지 설치는 하지 않음

---

## 2. 해결되지 않은 남은 질문 (Unresolved Questions)

- [ ] 라이선스가 Apache 2.0인지 MIT인지: LICENSE·README는 Apache, `pyproject.toml`·`setup.py`는 MIT
- [ ] `retrievers.md` M-01: 어댑터 17개(searx, arxiv, google 등)의 요청·응답 변환을 어디까지 재현할지
- [ ] `scrapers.md` R-22: firecrawl·tavily_extract·web_base_loader 내부, arxiv id 추출·selenium 단계 미확인
- [ ] `context-selection.md` R-11: `langchain-classic` `EmbeddingsFilter`의 청크 수·임계값 비교·정렬(제3자 자료만 있음)
- [ ] `deep-research.md` M-01: `json_repair.loads`가 JSON이 아닌 입력에서 무엇을 돌려주는지
- [ ] `.mcp.json`의 `uvx gpt-researcher`가 무엇을 실행하는지(MCP 서버 본체는 별도 레포 gptr-mcp)
- [ ] `source-modes.md`가 `ready`인데 `langchain_community` 문서 로더의 출력 분할·metadata는 미설치로 확인하지 못함(확인 한계로 둠)

---

## 3. 기능 스펙 후보

지도에서 승인하지 않은 행입니다. 필요하면 사용자에게 다시 묻고 씁니다.

| 기능 | 근거 | 상태 |
|---|---|---|
| LLM·임베딩·설정 | 다른 스펙이 경계로만 다룸. `MCP_*` 설정 3개는 동작 없음, `report_format`·`max_subtopics` 인자는 읽히지 않음 | 사용자 제외 |
| 서버 API | 상세 보고서 스펙 R-29(비용 누락)·R-32(호출 인자), mcp-client R-31(WebSocket 필드) | 사용자 제외 |
| 보고서 채팅, CLI, multi_agents, deep_agents, 프런트엔드 외 | 지도 참조 | 사용자 제외 |
| 이미지 생성 | report-writing이 입력(`available_images`) 경계만 다룸 | 사용자 제외 |
| `SourceCurator` 출처 curation | `CURATE_SOURCES` 켜면 LLM으로 출처를 고름(`skills/curator.py:38-114`). 연구 파이프라인 스펙이 경계만 정의 | 지도에 행 없음, 보류 |

---

## 4. 다음에 볼 파일 및 함수 (Next Entry Points)

다음에 쓸 기능 스펙이 있으면 먼저 적는다: 없음 (승인 범위 9행 작성 끝). `draft` 4개를 `ready`로 올리려면 위 미결정 4건을 정해야 한다.

| 대상 파일 경로 | 함수 / 클래스 | 확인 목적 |
|---|---|---|
| `gpt_researcher/retrievers/<이름>/` | 어댑터 17개의 `search` | `retrievers.md` M-01 해소 여부 결정 |
| `gpt_researcher/scraper/{firecrawl,tavily_extract,web_base_loader,arxiv}/` | 각 스크래퍼 | `scrapers.md` R-22 |
| (외부) `langchain-classic` `EmbeddingsFilter` | — | `context-selection.md` R-11, 라이브러리 설치가 필요해 실행 실험은 새 의존성 설치 허락이 있어야 함 |
| `gpt_researcher/skills/curator.py` | `SourceCurator.curate_sources` | 지도에 행을 추가할지 결정 |

---

## 5. 참고 사항 및 후속 제안

- 이 레포의 `memory`는 에이전트 장기 기억이 아니라 임베딩 생성기다. 에이전트 메모리 비교용이라면 mem0 쪽이 더 가깝다.
- 파이썬 3.12 이상이 필요하고(`pyproject.toml`) 기본 모델은 `openai:gpt-5.4` 계열이라 실제 실행 실험은 API 키가 필요하다. 이번에는 LLM·네트워크 없이 소스를 대체물과 함께 실행했다.
- 재구현 검증(워크플로 4장 6번)은 아직 하지 않았다. 사용자가 요청할 때 한다.
