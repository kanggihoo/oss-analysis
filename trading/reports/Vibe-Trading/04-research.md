# Vibe-Trading — 실시간 리서치

- 분석 SHA: `e532650b527ba3fb146ef00d533f6fc5040d5d2d` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q5
- 검증 수준 요약: 코드 확인 13 / 추론 0 / 미확인 0

> 한 줄 결론: 별도의 "리서치 루프"(plan → gather → assess)는 **없다.** 리서치는 메인 ReAct 루프가 그대로 한다. LLM이 `web_search`/`read_url`/뉴스·공시 도구를 자유롭게 부르고, 루프 상한(50회)과 중복 호출 차단, grounding 게이트가 품질을 잡는다.

<a id="q5"></a>
## Q5. 실시간 리서치

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 판단 도중 웹·뉴스·공시 조회 | 한다. 도구 `web_search`, `read_url`, `get_stock_news`, `get_research_reports`, `get_sec_filings`, `get_institutional_holdings`, `research_papers` 등을 LLM이 선택 호출 | `agent/src/tools/web_search_tool.py:134-170`, `agent/src/tools/web_reader_tool.py:60`, `agent/src/tools/stock_news_tool.py:251-267`, `agent/src/tools/sec_filings_tool.py:1-20` | 코드 확인 |
| 웹 검색 제공자 | 순서: ① `ALIYUN_IQS_API_KEY`가 있으면 Aliyun IQS 우선 ② `ddgs` 메타검색기(기본 백엔드 `duckduckgo, google, bing, brave, mojeek, yahoo`, 키 불필요, `VIBE_TRADING_SEARCH_BACKENDS`로 고정 가능, 최대 3회) ③ 네트워크 오류로 ddgs가 막히면 sogou → cn.bing 스크레이핑 폴백 | `agent/src/tools/web_search_tool.py:25-30,205-250,313` | 코드 확인 |
| 검색어 생성 | **LLM이 직접 만든다.** 고정 검색어 목록·차원 분해 없음. 입력은 `query`, `max_results`(기본 5, 최대 10) | `agent/src/tools/web_search_tool.py:155-169,191-196` | 코드 확인 |
| 재시도 | 3회, 백오프 기준 0.8초 | `agent/src/tools/web_search_tool.py:29-30` | 코드 확인 |
| 페이지 읽기 | Jina Reader(`r.jina.ai`)에 URL을 **제3자로 전달**해 마크다운 변환. 타임아웃 30초, 본문 8000자에서 자르고 "(truncated, total N chars)" 표기, SSRF 방어(localhost·사설 IP·`user:pass@` 거부) | `agent/src/tools/web_reader_tool.py:18-20,24-60,77-80,109-110` | 코드 확인 |
| 결과 처리 | 요약기 없음. 잘라내기와 보안 경고 메타 추가만 수행. 출처 URL·게시 시각은 도구가 JSON 필드로 돌려줌(뉴스: title/url/source/published/snippet) | `agent/src/tools/stock_news_tool.py:251-256` | 코드 확인 |
| 프롬프트 인젝션 대응 | 외부 콘텐츠에서 "이전 지시 무시", 시스템 프롬프트 유출, 역할 사칭, 비밀 유출, 도구 남용 패턴을 **정규식으로 탐지해 경고 메타만 붙임**(내용은 지우지 않음). 채팅 템플릿 제어 토큰도 처리 | `agent/src/security/scanner.py:1-60`, `agent/src/tools/web_reader_tool.py:121` | 코드 확인 |
| 숫자 신뢰성 | "숫자는 도구 결과에서만" 원칙 + figures 선언 검증. 웹 검색 결과의 숫자는 `cited` 역할로 **같은 문장에 출처를 명시**해야 하고, 그 출처가 줄에 보이지 않으면 거절 | `agent/src/agent/context.py:41-44,228-229`, `agent/src/agent/grounding/release.py:94`, `agent/src/agent/grounding/policies.py:2029`(`citation_not_visible`) | 코드 확인 |
| 반복 검색 방지 | ① 같은 호출이 2회 실패하면 3회째부터 `skipped`로 차단("전략을 바꾸거나 사용자에게 도움을 요청") ② 결정적(deterministic) 도구의 동일 호출은 캐시에서 응답 ③ 8회 연속 진전 없음이면 중단 | `agent/src/agent/tool_progress.py:9,18,128-138`, `agent/src/agent/loop.py:2354-2372,2480-2494` | 코드 확인 |
| 종료 조건 | 반복 상한 `max_iterations=50`(80% 지점에 마무리 넛지, 마지막 반복은 도구 없음), 도구 타임아웃·LLM 타임아웃·정지 감시(stall watchdog), "충분한 증거가 있으면 멈춰라" 프롬프트 | `agent/src/agent/loop.py:175-206,1212,1277-1285,1395-1400`, `agent/src/agent/context.py:60-66` | 코드 확인 |
| swarm 내 리서치 | 워커별 도구 화이트리스트와 스킬 화이트리스트로 범위를 제한. 프롬프트에 "20회 도구 호출 하드 리밋"이라 적혀 있으나 코드로 집행되지 않음(Q4-5 참조) | `agent/src/swarm/worker.py:343,361,586-600` | 코드 확인 |
| 한국 관련 리서치 | 한국 뉴스·공시 도구 **없음**(DART 없음). 한국 종목은 `web_search`/`read_url` 일반 웹 검색에만 의존 | `agent/src/tools/stock_news_tool.py:356-358` | 코드 확인 (없음) |
| 스케줄 리서치의 리서치 | 플레이북은 도구 이름 없이 "수집할 데이터"를 서술하고(예: "발행 시각이 붙은 헤드라인"), 누락은 `Data gaps`에 기록. 뉴스에 대해 "원인은 검색된 출처가 명시한 경우에만 단정" | `agent/src/scheduled_research/playbooks/premarket-brief.md:35-59` | 코드 확인 |

## 리서치 관련 메모 (판단 근거 UI)

- 도구 호출 타임라인과 grounding 진행 상태(`revising`, `released_redacted`)가 이벤트로 UI에 전달된다 (`frontend/src/pages/Agent.tsx:782-790`, `frontend/src/pages/agentToolTimeline.ts`).
- grounding 증거 파일 `grounding_evidence.json`에 검증 시도와 발동한 검사 이름이 남는다 (`agent/src/agent/grounding/ledger.py:46,364-380`).
