# TradingAgents-CN — 확인한 범위와 다음에 볼 것

- 분석 SHA: `51060a7682cf51810b4bc3a704829438d18cd8dc` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q1~Q7 전체
- 검증 수준 요약: 코드 확인 1 / 추론 2 / 미확인 4

## 확인한 범위

- 방법: 코드를 **읽기만** 했다(설치·빌드·실행 없음). 라인 번호는 고정 SHA 체크아웃에서 파일을 직접 열어 확인했다. 프롬프트 본문은 `install/community_bootstrap.json`을 파이썬 JSON 로더로 읽어(`-I`, 코드 실행 아님) 내용을 확인했다.
- 읽은 경로(진입 → 결정): `app/routers/analysis.py` → `app/services/task_analysis_service.py` → `unified_analysis_engine.py` → `core/api/workflow_api.py` → `core/workflow/{builder,engine,stage_aggregator}.py` + 템플릿 `v2_stock_analysis_workflow.py` → `core/agents/{base,analyst,researcher,manager,quality_gate}.py` + `adapters/{market,fundamentals,index,research_manager,risk_manager,trader,risk_self_debate}_v2.py` → `app/utils/{report_formatter,compliance}.py`.
- 데이터: `core/tools/implementations/{market,news,social,fundamentals}/*`, `tradingagents/dataflows/{data_source_manager,interface}.py`, `app/core/{config,data_source_priority}.py`, `app/main.py`(스케줄러).
- 리서치: `core/tools/implementations/assistant_ops/{web_search,recent_search,fetch_url}.py`, `core/agents/{planner,plan_executor}.py`, `core/assistant/defense.py`, `app/services/{intelligent_assistant_service,planned_analysis_service}.py`.
- 비교용 원본: `repos/TradingAgents`(SHA `1394a3f7…`)는 `graph/setup.py`, `agents/rating.py`, `default_config.py`, `memory/settlement.py`만 읽었고 수정하지 않았다.
- 레거시: `tradingagents/graph/{setup,conditional_logic,signal_processing}.py`, `agents/utils/compliance_prompting.py`.

## 미확인 항목 체크리스트

- [ ] 운영에서 실제로 어떤 워크플로(코드 템플릿 vs DB `6ede3bc3-…` 사용자 버전)가 선택되는지. `_resolve_workflow_id`의 사용자 설정 경로(`workflow_provider.get_active_workflow_id`)가 DB 값을 어떻게 읽는지 미확인 (`core/workflow/default_workflow_provider.py`)
- [ ] 부트스트랩 워크플로의 `valuation_analyst_v1` 고아 노드(합류 간선 없음)가 LangGraph에서 어떻게 컴파일·실행되는지 (실행 미확인)
- [ ] `tradingagents/dataflows/optimized_china_data.py`의 `_get_cached_raw_financial_data` 내부에 공시일 기준 필터가 있는지 (look-ahead 판단 보류: 01-data.md 2-5 "추론")
- [ ] 벡터 메모리(`memory_manager.get_agent_memory`)의 실제 구현체와 임베딩 모델: `core/memory/*`(chromadb/mongodb vector/qdrant)
- [ ] `app/utils/report_formatter.format_analysis_result` 경로가 운영에서 호출되는지. 운영 결과 정규화는 `task_analysis_service._format_analysis_result`로 확인했으나 `UnifiedAnalysisService._format_result` 경로와의 관계는 미확인
- [ ] `core/agents/utils/weight_calculator.py`의 용도(분석가 가중치?)와 사용처 (재노출 외 호출 grep 0건)
- [ ] 외부 Skill/MCP 도구(`core/tools/external/*`, `skills/ifind-*`)로 분석이 웹 정보를 끌어오는 경로
- [ ] 섹터 보고서 캐시 TTL 상수 "已废弃，不再使用"(`sector_analyst_v2.py:21`)과 실제 읽기·쓰기 코드(`:60-147`)가 어느 쪽이 맞는지
- [ ] `IM_TOPIC_DIGEST_*` 스케줄 등록 위치 (`app/main.py`에는 없음)
- [ ] 프런트의 상승=빨강 같은 한국과 반대되는 색 규칙 (표시 관련, 판단과 무관)
- [ ] 실제 LLM 출력이 프롬프트 규칙(예: "口径不一致 시 confidence 하향")을 지키는지 — 실행 검증 필요(사용자와 합의 후)

## README와 코드가 다른 곳 (기록)

| 항목 | README/문서 | 코드 | 위치 |
|---|---|---|---|
| 정기·일괄 분석 | README 표에서 "定时分析 / 批量分析"은 Pro 전용 | 저장소에 `watchlist_analysis` 스케줄 작업(기본 비활성)과 일괄 분석 라우트가 있다 | `README.md`, `app/main.py:903-916`, `app/routers/analysis.py:1672-1841` |
| 시장 데이터 조회폭 | 도구 docstring "系统自动扩展到 365 天" | 기본 `MARKET_ANALYST_LOOKBACK_DAYS=60` | `core/tools/implementations/market/stock_market_data.py:280-303` vs `app/core/config.py:326` |
| Python 버전 | README "Python 3.11" | `.python-version`은 3.10, `pyproject.toml`은 `>=3.10` | `README.md`, `.python-version`, `pyproject.toml:10` |
| 패키지 이름 | "TradingAgents-CN 社区版" | `pyproject.toml`의 `name = "tradingagents-cn-pro"` | `pyproject.toml:6` |
| 라이선스 열거 | LICENSE가 `web/`를 Apache 영역으로 나열 | 저장소에 `web/` 디렉터리가 없다 | `LICENSE:9` |
| 연구 매니저 출력 | DB 템플릿 `output_format`: `看涨|中性|看跌`, `confidence 0-100` | 코드 스키마: `乐观|审慎|中性`, `confidence 0-1` (스키마 프롬프트를 앞에 붙여 충돌 흡수) | `install/community_bootstrap.json` → `PT[managers_v2, research_manager_v2, …]`, `research_manager_v2.py:27-79` |
| 가격 구간 | 글로벌 가드는 "価格分析区间 허용", 연구 매니저 프롬프트는 "价格区间 금지" | 둘 다 활성 | `core/agents/base.py:398`, DB 템플릿 |
| 컴플라이언스 가드 | GUIDE가 가리키는 `compliance_prompting.py` | 레거시 에이전트에서만 import됨. 운영 v2는 DB 템플릿+`base.py` 글로벌 가드 | `tradingagents/agents/utils/compliance_prompting.py:96-117` |
| 스케줄 "기술지표 물화" | 설정·서비스가 있음 | 스케줄러 등록 없음 | `app/core/config.py:278-279`, `app/main.py:593-977` |
| 성장 기억 recall | 서비스가 recall 텍스트를 만들어 `growth_memory_recall`에 담음 | 이 키를 읽는 에이전트 코드가 없다 | `app/services/unified_analysis_service.py:442-455`, `core/workflow/engine.py:156-157` |
| `sanitize_analysis_payload` | 정화 함수가 존재 | 운영 호출처 없음(테스트만) | `app/utils/compliance.py:1128` |

## 다음에 볼 파일과 함수

1. `core/workflow/default_workflow_provider.py` — 활성 워크플로 선택(`get_active_workflow_id`, `load_workflow`)
2. `core/memory/service.py`, `core/memory/memory_manager.py` — 벡터 메모리 구현
3. `core/workflow/engine.py:444-715` `execute`/`execute_async` — 실제 상태 스키마와 노드 오류 처리(`_node_errors`)
4. `core/agents/trader.py`, `core/agents/universal.py` — 설정형 에이전트(`UniversalAgent`)가 DB `agent_configs`로 동작하는 방식
5. `app/services/workflow_growth_service.py` — 성장 기억 추출·승인 흐름
6. `tradingagents/dataflows/optimized_china_data.py` — 재무 데이터 캐시, `_get_cached_raw_financial_data`
7. `core/skill_runtime/*`, `skills/*` — 사용자 정의 Skill(데이터 도구 확장)
8. `docs/` — 코드 주석이 가리키는 설계 문서 `docs/05-design/v3.0/assistant-quality-architecture-refactor.md`, `docs/99-archive/deprecated-features/legacy-agents-deprecation.md`는 이 체크아웃의 `docs/`에 없다(`02-user-guide`, `07-courses`만 있음, 코드 확인). 공개본에서 빠진 것으로 보이며 코드만이 근거다

## 분석 중 생긴 질문

- 부트스트랩의 DB 워크플로(`is_default=True`, 22노드)는 코드 템플릿(20노드)보다 "chip + valuation" 노드가 많은데, 어느 쪽이 UI 기본인가?
- `risk_exposure_ratio="5%"` 기본값이 왜 있는지(프런트 표시 호환용으로 보임, 추론)와 실제로 화면에 노출되는지
- 리스크 매니저가 `final_trade_decision`(dict)와 `risk_assessment`(JSON 문자열)를 둘 다 내보내는 이유(호환 필드로 보임)
- 위험 토론 3자의 반복 호출 비용 대비 self-debate 1회의 품질 차이는 측정되었나? (문서·테스트 확인 필요: `tests/`, `run_debate_tests.ps1`)
