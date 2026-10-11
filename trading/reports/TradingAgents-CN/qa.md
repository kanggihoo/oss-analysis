# TradingAgents-CN — 질문·답변 검증 기록

- 분석 SHA: `51060a7682cf51810b4bc3a704829438d18cd8dc`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 2
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | 운영에서 기본으로 실행되는 워크플로가 코드 템플릿인가 DB `6ede3bc3-…`인가 | Q1 / Q4-2 | 해소 | R1 |
| R1-Q2 | DB 워크플로의 `valuation_analyst_v1` 노드(합류 간선 없음)를 빌더가 어떻게 처리하는가 | Q1 / Q4-2 | 해소 | R1 |
| R1-Q3 | 시장 분석가에 바인딩된 `mcp_tdx-mcp_get_stock_info`의 실체와 데이터 출처 | Q1 / Q2 | 해소 | R1 |
| R1-Q4 | DB 바인딩이 있을 때 `agent_configs.default_tools`는 무시되는가, 합쳐지는가 | Q1 | 해소 | R1 |
| R1-Q5 | 재무 데이터 로드에 공시일 기준(look-ahead) 필터가 있는가 | Q2 | 없음 확정 | R1 |
| R1-Q6 | 섹터 보고서 캐시가 실제로 읽기·쓰기 되는가 | Q2 | 없음 확정 | R1 |
| R1-Q7 | `IM_TOPIC_DIGEST_*` 작업이 어디에서 스케줄러에 등록되는가 | Q3 | 없음 확정 | R1 |
| R1-Q8 | `format_decision` → `SignalProcessor` 재추출 경로가 운영 경로에서 호출되는가 | Q4-6 | 없음 확정 | R1 |
| R1-Q9 | `agent_assertions` 단언이 기본 설치에서 비어 있는가 | Q4-5 | 해소 | R1 |
| R1-Q10 | `weight_calculator.py`가 운영 경로에서 분석가 신호 가중에 쓰이는가 | Q4-5 | 없음 확정 | R1 |
| R1-Q11 | 에이전트 벡터 메모리의 실제 구현체와 임베딩 모델 | Q4-7 | 해소 (새 질문 → R2-Q1) | R1 |
| R1-Q12 | 반성(reflection) LLM 호출이 실행되는 정확한 조건 | Q4-8 / Q4-7 | 해소 | R1 |
| R2-Q1 | mem0 LLM·임베더 API 키가 분석 LLM과 같은 경로(환경변수 폴백 포함)로 해석되는가 | Q4-7 | 해소 | R2 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. 운영 기본 워크플로는 코드 템플릿인가 DB 워크플로인가
- GUIDE 항목: Q1 / Q4-2 (TradingAgents-CN 중점: 판단 흐름 순서, 분석가 추가)
- 왜 묻는가: `03-decision.md` 4-2-a 아래 첫 글머리에서 "운영에서 어느 것이 선택되는지는 … 사용자 설정에 달렸다"로 끝나고, `next.md` 미확인 체크리스트 1번과 "분석 중 생긴 질문" 1번도 같은 내용이다. 어느 쪽이냐에 따라 칩 분포·밸류에이션 분석가가 데이터 인벤토리(01-data 1-1)와 호출 수(03-decision 4-8)에 들어가는지가 달라진다.
- 질문: 사용자가 워크플로를 따로 지정하지 않은 커뮤니티판 첫 설치 상태에서, `_resolve_workflow_id`(`app/services/unified_analysis_engine.py:66-130`)와 `DefaultWorkflowProvider.get_active_workflow_id`/`load_workflow`(`core/workflow/default_workflow_provider.py`)를 거쳐 최종으로 실행되는 워크플로 정의는 코드 템플릿 `v2_stock_analysis_workflow.py`인가, 부트스트랩 DB 워크플로 `6ede3bc3-66e3-4204-a304-dcbe8b327258`인가?
- 답변 완료 조건: 4단계 우선순위 각각에서 어떤 값이 반환되는지를 `파일:라인`과 원문으로 추적하고, 첫 설치 시 활성 워크플로 ID가 어디서 읽히는지(DB 컬렉션·키 또는 하드코딩 상수) 명시. DB에 저장된 값에 의존해 정적으로 정할 수 없다면, 부트스트랩 시드에 그 값이 무엇으로 들어 있는지까지 확인.

#### R1-Q2. `valuation_analyst_v1` 노드는 그래프에서 어떻게 처리되는가
- GUIDE 항목: Q1 / Q4-2
- 왜 묻는가: `01-data.md` 1-2 표 마지막 행이 "고아 노드로 보인다 (추론)"이고, `next.md` 미확인 2번이 같은 내용이다. 이 노드가 실행되는지, 결과가 하류로 가는지, 그래프 빌드가 실패하는지가 정해지지 않았다.
- 질문: 부트스트랩 DB 워크플로를 `core/workflow/builder.py`가 빌드할 때, `valuation_analyst_v1` 노드(`parallel_analysts -> analyst_1783504388585` 간선만 있고 출구 간선 없음)는 (a) 선택 분석가 필터(`builder.py:1187-1254`, `ANALYST_ID_TO_TYPE`)로 제거되는가, (b) 남는다면 출구 없는 노드에 빌더가 END 또는 MERGE 간선을 자동으로 붙이는가, (c) 아무 처리 없이 그대로 두는가?
- 답변 완료 조건: 이 노드의 에이전트 ID가 필터에서 어떻게 분류되는지와, 빌더가 출구 없는 노드를 처리하는 코드(또는 그런 코드가 없다는 조사 범위)를 `파일:라인`과 원문으로 제시. LangGraph 런타임 동작에 따라 갈린다면 갈리는 지점과 경우의 수.

#### R1-Q3. `mcp_tdx-mcp_get_stock_info` 도구의 실체
- GUIDE 항목: Q1 / Q2
- 왜 묻는가: `01-data.md` 1-0 표에서 `market_analyst_v2`의 활성 바인딩에 `mcp_tdx-mcp_get_stock_info`가 있지만 1-1 인벤토리 표에는 이 도구가 제공하는 데이터·제공자가 없다. `*.py`에서 `tdx-mcp`/`tdx_mcp` 문자열이 검색되지 않아 외부 MCP 서버로 보이며, `04-research.md` 5-3도 외부 Skill/MCP 경로를 미확인으로 남겼다.
- 질문: 운영 경로에서 `mcp_tdx-mcp_get_stock_info` 이름이 어떤 코드로 실제 도구 객체로 해석되는가(MCP 서버 등록 위치, 설정 파일, 기본 활성 여부), 그리고 기본 설치에서 MCP 서버가 없으면 이 바인딩은 어떻게 처리되는가(건너뜀/오류/LLM에 노출)?
- 답변 완료 조건: `mcp_` 접두사 도구 이름을 해석하는 함수의 `파일:라인`과 원문, 부트스트랩 또는 설정에서 `tdx-mcp` 서버 정의 위치(키 경로), 서버가 없을 때의 분기 코드. 서버가 반환하는 데이터 내용이 외부에 있어 정적으로 알 수 없다면 그 사실과 근거.

#### R1-Q4. 바인딩이 있을 때 `default_tools`는 버려지는가
- GUIDE 항목: Q1
- 왜 묻는가: `01-data.md` 1-0 마지막 글머리가 "바인딩이 있으면 바인딩이 이기므로 운영에는 영향이 없다고 본다 (추론)"로 끝난다. `get_weather`, `test_heartbeat` 같은 시험용 도구가 분석가 LLM에 노출되는지가 확정되지 않았다.
- 질문: 운영 경로에서 분석가가 LLM에 `bind_tools`로 넘기는 최종 도구 목록은 DB 바인딩만인가, 아니면 `agent_configs[*].default_tools`와 합쳐지는가?
- 답변 완료 조건: 에이전트 생성부터 `bind_tools` 직전까지 도구 목록을 만드는 호출 순서(`binding_manager.py:105-120` 포함)를 `파일:라인`과 원문으로 제시하고, `default_tools`가 읽히는 모든 위치를 grep으로 확인.

#### R1-Q5. 재무 데이터에 공시일 기준 필터가 있는가
- GUIDE 항목: Q2 (미래 데이터 차단)
- 왜 묻는가: `01-data.md` 2-5 표 마지막 행이 "추론(… 하위 `_get_cached_raw_financial_data` 내부는 열어보지 않음)"이고, `next.md` 미확인 3번도 같다. 과거 일자 분석에서 아직 공시되지 않은 분기 재무가 들어가는지가 정해지지 않았다.
- 질문: 운영 경로의 A주 재무 로드(`core/tools/implementations/fundamentals/stock_fundamentals.py:110-165`의 `_load_recent_financial_data`와 그 하위 `tradingagents/dataflows/optimized_china_data.py`의 `_get_cached_raw_financial_data`, 그리고 MongoDB `stock_financial_data` 조회)에서 분석일 또는 공시일(`ann_date` 등)로 행을 거르는 조건이 있는가?
- 답변 완료 조건: 호출 체인 각 단계의 조회 조건 원문(MongoDB 쿼리 필터, 정렬, limit)과 `파일:라인`. 없으면 확인한 함수 목록과 grep 패턴(`ann_date`, `f_ann_date`, `end_date`, `report_date`, `as_of`, `analysis_date` 등).

#### R1-Q6. 섹터 보고서 캐시는 실제로 쓰이는가
- GUIDE 항목: Q2 (캐시)
- 왜 묻는가: `01-data.md` 2-4 표 "섹터 보고서 캐시" 행이 "추론(주석과 코드가 상충)"이고, `next.md` 미확인 8번도 같다. 대시보드 보고서처럼 다른 종목 분석끼리 섹터 LLM 산출물을 공유하는지가 정해지지 않았다.
- 질문: `core/agents/adapters/sector_analyst_v2.py`에서 상수(`:21`, "已废弃，不再使用")와 캐시 읽기·쓰기 코드(`:60-147`)가 있을 때, 운영 실행 시 섹터 보고서 캐시 읽기와 쓰기 함수가 실제로 호출되는가? 호출된다면 키와 만료는 무엇인가?
- 답변 완료 조건: 캐시 읽기·쓰기 함수의 호출처 `파일:라인`과 분기 조건 원문, 키 구성과 TTL 값(상수가 쓰이지 않는다면 실제 쓰이는 값의 위치).

#### R1-Q7. `IM_TOPIC_DIGEST_*` 작업 등록 위치
- GUIDE 항목: Q3
- 왜 묻는가: `02-schedule.md` 3-2 "공통 사실" 마지막 글머리가 "등록 위치는 찾지 못했다 (미확인)"이고 `next.md` 미확인 9번도 같다. 설정은 `app/core/config.py:282-285`(기본 ON, `30 22 * * *`)에 있다.
- 질문: `IM_TOPIC_DIGEST_ENABLED`/`IM_TOPIC_DIGEST_CRON`을 읽어 작업을 등록하거나 실행하는 코드가 저장소 어디에 있는가? 없다면 이 설정은 정의만 있는 것인가?
- 답변 완료 조건: 등록 코드의 `파일:라인`과 원문(작업 id, 트리거). 없다면 `app/`, `core/`, `tradingagents/`, `cli/` 전체에 대한 grep 패턴(`IM_TOPIC_DIGEST`, `topic_digest`, `digest` 등 변형 포함)과 결과.

#### R1-Q8. `format_decision`의 `SignalProcessor` 재추출은 운영에서 실행되는가
- GUIDE 항목: Q4-6 (실패 처리), Q4-8 (비용)
- 왜 묻는가: `03-decision.md` 4-6 표 마지막 행이 "운영 경로 호출 여부는 미확인"이고, `next.md` 미확인 5번(`format_analysis_result` 경로와 `UnifiedAnalysisService._format_result`의 관계)과 같다. 4-3-b "용어 사전" 행은 이 경로가 결정 필드 부재 시 호출된다고 적었다. 운영에서 실행된다면 추가 LLM 호출과 `买入/持有/卖出` 경유 어휘가 결과에 영향을 준다.
- 질문: 웹 UI → 워커 → `UnifiedAnalysisEngine` 운영 경로에서 결과 정규화 시 `app/utils/report_formatter.py`의 `format_analysis_result` 또는 `format_decision`이 호출되는 지점이 있는가?
- 답변 완료 조건: 두 함수의 호출처 전체 목록(grep 결과)과, 각 호출처가 운영 경로(`task_analysis_service.execute_task` 이후)에서 도달 가능한지 호출 체인 `파일:라인`. 도달 불가면 "없음 확정"에 필요한 조사 범위.

#### R1-Q9. `agent_assertions`는 기본 설치에서 비어 있는가
- GUIDE 항목: Q4-5 (코드가 LLM 결과를 제한하는 장치)
- 왜 묻는가: `03-decision.md` 4-5 표 "규칙 기반 단언" 행이 "시드 비어 있음은 추론: 부트스트랩 컬렉션 목록에 `agent_assertions`가 없음"으로 남아 있다. 단언이 있으면 코드 가드레일이 실제로 동작하는 것이 된다.
- 질문: 기본 설치 후 `agent_assertions` 컬렉션에 단언 문서를 넣는 코드(부트스트랩, 마이그레이션, 앱 시작 시 시드, 코드 내 기본 단언)가 있는가? 그리고 컬렉션이 비어 있을 때 `assertion_executor`가 코드 기본 단언을 대신 쓰는가?
- 답변 완료 조건: `install/`, `migrations/`, `app/`, `core/`에서 `agent_assertions` 쓰기 위치 grep 결과, `assertion_executor.py`의 로드 함수 원문(비어 있을 때 분기 포함)과 `파일:라인`, `app/core/config.py:178-181`의 활성 플래그 기본값.

#### R1-Q10. `weight_calculator.py`는 운영에서 쓰이지 않는가
- GUIDE 항목: Q4-5 (신호 합산 방식)
- 왜 묻는가: `03-decision.md` 4-5 표 "신호 합산" 행이 "추론"이고 `next.md` 미확인 6번이 같다. 분석가 신호를 코드가 가중 합산하는지에 따라 "최종 판단은 LLM만" 결론(00-overview 2절)이 바뀔 수 있다.
- 질문: `core/agents/utils/weight_calculator.py`의 공개 함수·클래스가 동적 import(`importlib`, 문자열 경로, 레지스트리, DB 설정 포함)를 포함해 운영 경로 어디서든 호출되는가?
- 답변 완료 조건: 모듈이 정의하는 이름 목록, 각 이름에 대한 저장소 전체 grep 결과(`*.py`, `*.json`, `*.yaml` 포함), 호출처가 있으면 `파일:라인`과 운영 경로 도달 여부.

#### R1-Q11. 에이전트 벡터 메모리 구현체와 임베딩 모델
- GUIDE 항목: Q4-7 (메모리)
- 왜 묻는가: `03-decision.md` 4-7 표 첫 행은 `ResearcherAgent._save_to_memory`와 `search_memories(n_results=3)`, 유사도 > 0.7까지만 적었고, `next.md` 미확인 4번에서 구현체(chromadb/mongodb vector/qdrant)와 임베딩 모델이 미확인이다. 임베딩 키가 없을 때 메모리가 꺼지는지도 판단 입력에 영향을 준다.
- 질문: 기본 설치에서 `memory_manager.get_agent_memory`가 반환하는 저장소 구현체는 무엇이며, 임베딩은 어떤 제공자·모델로 만드는가? 임베딩 키나 서비스가 없으면 저장·검색은 어떻게 동작하는가?
- 답변 완료 조건: 구현체 선택 분기(설정 키와 기본값)의 `파일:라인`과 원문, 임베딩 생성 함수와 기본 모델명, 실패 시 분기 코드. 선택이 환경변수에 의존하면 기본값과 경우의 수.

#### R1-Q12. 반성(reflection) LLM 호출의 실행 조건
- GUIDE 항목: Q4-8 (비용), Q4-7 (교훈 생성)
- 왜 묻는가: `03-decision.md` 4-8의 호출 수 표가 "(추론)"이고, 그 중 반성 호출은 "연구 매니저·리스크 매니저 직후 각 1회 가능(`builder.py:2607-2650`)"으로 "가능"에 머문다. 4-2-b 표는 快速만 메모리 끔이라고 적었다. 반성이 언제 실제로 돌아가는지가 비용과 교훈 생성 빈도를 정한다.
- 질문: 운영 경로에서 `analysis_lesson`/`debate_lesson` 반성 LLM 호출은 어느 노드 직후에, 어떤 조건(깊이별 메모리 플래그, 환경변수, 사용자 ID 유무, 비동기·백그라운드 여부)을 모두 만족할 때 실행되는가?
- 답변 완료 조건: 반성 트리거 코드와 각 조건의 원문 `파일:라인`(`builder.py:2607-2650`, `unified_analysis_service.py:317-323` 포함), 조건 플래그의 기본값 위치, 반성 1건당 LLM 호출 횟수.

### 답변 (답변자)

> 표기 규칙: 경로는 모두 `repos/TradingAgents-CN/` 기준이다. 부트스트랩 JSON(`install/community_bootstrap.json`)은 한 줄 파일이라 라인 대신 JSON 키 경로(`data.<컬렉션>[인덱스].<키>`)로 인용한다. 모든 `파일:라인`은 직접 열어 확인한 값이다.

#### R1-Q1 답변
- 결론: **확정**. 첫 설치(부트스트랩 적용, `MONGODB_CONNECTION_STRING` 설정)에서 단일 종목 분석이 실제로 실행하는 워크플로는 코드 템플릿 `v2_stock_analysis`가 아니라 부트스트랩 DB 워크플로 `6ede3bc3-66e3-4204-a304-dcbe8b327258`("v2.0 完整分析流 - 我的版本", version 2.0.5)이다. 웹 UI는 이 ID를 `workflow_id`로 명시 전송해 우선순위 1에서 선택되고, ID 없이 호출하는 경로도 우선순위 2의 DB `is_default=true` 조회로 같은 문서에 도달한다. 코드 템플릿은 DB 연결 불가나 UI 목록 조회 실패 때만 쓰이는 대체 경로다. **보고서 정정 필요**: `03-decision.md` 4-2-a의 "운영에서 어느 것이 선택되는지는 … 사용자 설정에 달렸다"와 `next.md` 미확인 1번은 "기본 설치 = 6ede3bc3(DB)"로 확정할 수 있다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `app/services/unified_analysis_engine.py:81-86` | `_resolve_workflow_id` 우선순위 1 | `explicit_workflow_id = task.workflow_id or task.task_params.get("workflow_id")` → 존재하면 `return explicit_workflow_id` (작업이 명시한 ID) | 코드 확인 |
  | `app/services/unified_analysis_engine.py:99-104` | 우선순위 2 | `active_workflow_id = workflow_provider.get_active_workflow_id(workflow_type)` → `_workflow_exists`이면 반환 ("我的分析流配置" = 내 분석 흐름 설정) | 코드 확인 |
  | `app/services/unified_analysis_engine.py:121-130` | 우선순위 3, 4 | 3: `if self._workflow_exists(config.workflow_id): return config.workflow_id`; 4: `get_default_workflow_id_for_type(workflow_type)` ("所有配置均无效，回退到系统默认工作流" = 모든 설정이 무효여서 시스템 기본 워크플로로 대체) | 코드 확인 |
  | `core/workflow/default_workflow_provider.py:221-224` | `get_active_workflow_id` 1단계 | `db.workflows.find_one({"workflow_type": cache_key, "is_default": True}, sort=[("updated_at", -1)])` → 있으면 `workflow["id"]` 반환(230-235) | 코드 확인 |
  | `core/workflow/default_workflow_provider.py:239-291` | 같은 함수 2~4단계 | `system_configs`의 `default_workflows` → `config/settings.json` → 마지막 `get_default_workflow_id_for_type(cache_key)` (`WORKFLOW_TYPE_DEFAULTS`, 27-32: `"stock_analysis": "v2_stock_analysis"`) | 코드 확인 |
  | `install/community_bootstrap.json` `data.workflows[9]` | 부트스트랩 워크플로 | `id: "6ede3bc3-66e3-4204-a304-dcbe8b327258"`, `is_default: true`, `workflow_type: "stock_analysis"`, `version: "2.0.5"`. 같은 `workflows` 배열에서 `is_default: true`는 `[9]`(stock)와 `[10]`(`d22a96c9-…`, etf)뿐. `v2_stock_analysis`(`[7]`)는 `is_default: false` | JSON 확인 |
  | `install/community_bootstrap.json` `data.system_configs[93]` | 활성 시스템 설정 | `is_active: true`, `default_workflows.stock_analysis.workflow_id = "6ede3bc3-66e3-4204-a304-dcbe8b327258"` (등록 위치 보강 근거) | JSON 확인 |
  | `app/services/community_bootstrap_service.py:115-124`, `app/main.py:276-281` | 부트스트랩 적용 | `if await db[collection_name].count_documents({}) > 0: continue` 후 `insert_many` (컬렉션이 비었을 때만 삽입). `main.py`에서 `import_bootstrap_config()` 호출 | 코드 확인 |
  | `frontend/src/views/Analysis/SingleAnalysis.vue:1003, 2946-2951, 1623` | 웹 UI 전송값 | `const selectedWorkflowId = ref<string>('v2_stock_analysis')` → 마운트 시 `workflowsSorted.value.find(w => w.is_default)`의 `id`로 교체 → 요청 파라미터 `workflow_id: selectedWorkflowId.value` | 코드 확인 |
  | `frontend/src/api/workflow.ts:104-113` | UI 목록 필터 | `workflow_type === expectedType`, 주버전 `>= 2`, 이름에 "快速"(빠른)/"空白"(공백) 제외 → 6ede3bc3(2.0.5)는 통과, `is_default`도 6ede3bc3뿐 | 코드 확인 |
  | `core/api/workflow_api.py:622-645`, `app/routers/workflows.py:131-133`, `core/licensing/community_stub.py:173-181` | UI 목록 API | `list_all()`이 DB 문서의 `is_default`, `workflow_type`을 그대로 반환. `require_pro`는 커뮤니티 스텁에서 "放行透传"(통과) | 코드 확인 |
  | `app/models/analysis.py:73-76` | `AnalysisParameters.workflow_id` | `description="工作流 ID (仅 unified 引擎有效)…"` ("unified 엔진에서만 유효"). 그러나 위 `unified_analysis_engine.py:82`는 엔진 종류와 무관하게 `task_params["workflow_id"]`를 읽는다 | 코드 확인 (설명과 코드 불일치) |

- 동작 설명:
  1. 서버 시작 시 `app/main.py:279-280`이 `import_bootstrap_config()`를 호출하고, `workflows` 컬렉션이 비어 있으면 `data.workflows` 12건을 삽입한다(`community_bootstrap_service.py:119-122`).
  2. 웹 UI(`SingleAnalysis.vue`)는 마운트 시 `GET /api/workflows`로 목록을 받아 `is_default`인 6ede3bc3을 선택하고, 분석 제출 시 `parameters.workflow_id`에 실어 보낸다(1623). `routers/analysis.py`가 `request.parameters.model_dump()`를 `task_params`에 합치므로 엔진의 `task.task_params.get("workflow_id")`가 값을 얻는다.
  3. `_resolve_workflow_id`는 우선순위 1에서 `_workflow_exists("6ede3bc3-…")`(DB 조회, `unified_analysis_engine.py:36-51`)가 참이므로 그 ID를 반환한다.
  4. 제3자가 API로 `workflow_id` 없이 호출해도 우선순위 2에서 `get_active_workflow_id("stock_analysis")`가 `db.workflows`의 `is_default: true` 문서를 찾아 같은 ID를 얻는다.
  5. 코드 템플릿 `V2_STOCK_ANALYSIS_WORKFLOW`가 선택되는 경우: (가) UI 목록 호출이 실패해 `selectedWorkflowId`가 초기값 `'v2_stock_analysis'`로 남을 때(`SingleAnalysis.vue:1003`, `workflowApi.listAll` 예외 처리 `console.debug('… 加载工作流失败，保留当前默认模板')` 2959), (나) `MONGODB_CONNECTION_STRING` 미설정으로 `DefaultWorkflowProvider._get_db()`가 `None`(`default_workflow_provider.py:72-78`)이 되어 우선순위 2를 건너뛰고 3~4로 내려갈 때, (다) 사용자가 UI에서 다른 흐름을 고르거나 `is_default`를 바꿨을 때. `.env.example:19`는 이 환경변수를 필수 항목으로 둔다.
  6. 코드 템플릿(`core/workflow/templates/v2_stock_analysis_workflow.py:48-205`)의 분석가는 6종(index, sector, market, fundamentals, news, social)이고 칩 분포·밸류에이션 분석가는 없다. DB 워크플로 6ede3bc3(`data.workflows[9].nodes[20]`, `[21]`)에는 `chip_distribution_analyst_v2`와 `valuation_analyst_v1`이 추가되어 있다. 따라서 기본 설치의 실제 분석가는 8종이며, 이는 `01-data.md` 1-1 인벤토리와 `03-decision.md` 4-8 호출 수 계산에 포함되어야 한다.
- 조사 범위: `app/services/unified_analysis_engine.py` 전체 `_resolve_workflow_id`, `core/workflow/default_workflow_provider.py` 전체, `app/services/community_bootstrap_service.py`, `app/main.py` 부트스트랩 호출부, `install/community_bootstrap.json`의 `data.workflows`/`data.system_configs`, `frontend/src/views/Analysis/SingleAnalysis.vue`, `frontend/src/api/workflow.ts`, `core/api/workflow_api.py` `list_all`, `app/routers/workflows.py`, `app/router_registry.py:100-104`, `core/licensing/community_stub.py`. grep 패턴: `6ede3bc3`, `get_active_workflow_id`, `is_default`, `workflow_id`, `ensure_system_workflows_exist`(호출처는 `core/api/workflow_api.py:725` 템플릿 목록 API뿐이며 `is_default`를 `setdefault(False)`로만 둠, `default_workflow_provider.py:159`).

#### R1-Q2 답변
- 결론: **확정**(빌더 코드 범위). `valuation_analyst_v1` 노드는 (a) 선택 분석가 필터로 제거되지 않고, (b) 출구 없는 노드에 END/MERGE 간선을 자동으로 붙이는 코드는 없으며, (c) 그대로 그래프에 추가되어 `parallel_analysts`에서 오는 간선만 가진 말단 노드가 된다. 또한 이 노드의 산출물 `valuation_report`는 하류 에이전트 코드가 읽지 않고 최종 보고서 필드 목록에만 포함된다. 단 LangGraph `compile()`이 말단 노드를 허용하는지는 외부 라이브러리 동작이라 **정적 확인 불가**(아래 경우의 수). 보고서 `01-data.md` 1-2의 "고아 노드로 보인다 (추론)"는 "합류 간선이 없는 말단 노드(코드로 확인)"로 정정할 수 있다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `install/community_bootstrap.json` `data.workflows[9].nodes[21]` | 노드 정의 | `id: "analyst_1783504388585"`, `type: "analyst"`, `agent_id: "valuation_analyst_v1"`, `label: "多维度估值分析助手"`(다차원 밸류에이션 분석 도우미) | JSON 확인 |
  | `install/community_bootstrap.json` `data.workflows[9].edges[31]` | 유일한 간선 | `source: "parallel_analysts"`, `target: "analyst_1783504388585"`. 이 노드가 `source`인 간선은 `edges[0..31]` 전체에 없음. 비교: 칩 노드는 `edges[29]`(parallel→chip)와 `edges[30]`(chip→`merge_analysts`)를 모두 가짐 | JSON 확인 |
  | `core/workflow/builder.py:918-932` | `ANALYST_ID_TO_TYPE` | 키는 `market_analyst`, `news_analyst`, `fundamentals_analyst`, `social_analyst`, `*_v2`, `etf_analyst_v2`, `index_analyst(_v2)`, `sector_analyst(_v2)`뿐. `valuation_analyst_v1`, `chip_distribution_analyst_v2` 없음 | 코드 확인 |
  | `core/workflow/builder.py:1006-1033` | `_is_analyst_selected` | `# 未知类型的分析师，保留` / `return True` (알 수 없는 유형의 분석가는 유지) | 코드 확인 |
  | `core/workflow/builder.py:1187-1253`, 1229-1231 | `_filter_analyst_nodes` | 제거 대상은 `_is_analyst_selected`가 False인 노드와 그 노드에 닿는 간선뿐: `if edge.source in nodes_to_remove or edge.target in nodes_to_remove: continue`. 출구 보정 코드 없음 | 코드 확인 |
  | `core/workflow/builder.py:1077, 187-197` | `ANALYST_TOOL_MAPPING` | 도구 루프 노드(`tools_*`, `msg_clear_*`)는 이 맵에 있는 agent_id만 생성. valuation/chip은 해당 없음 | 코드 확인 |
  | `core/workflow/builder.py:1112` | 노드 추가 | `graph.add_node(node.id, node_func)` (START/END만 건너뜀, 1091-1092) | 코드 확인 |
  | `core/workflow/builder.py:2883-2918` | `_add_edges` 3단계 | 일반 간선: `elif target_node.type == NodeType.MERGE and merge_waits_all(target_node): add_merge_predecessor(...)` / `else: graph.add_edge(edge.source, edge.target)`(2917). `parallel_analysts → analyst_1783504388585`는 마지막 `else`로 일반 간선이 된다. 출구 없는 노드에 `END`를 붙이는 분기는 `target_node.type == NodeType.END`(2910-2911)뿐이며 이는 JSON에 명시된 END 간선에만 적용 | 코드 확인 |
  | `core/workflow/builder.py:1185` | 컴파일 | `return graph.compile()` (`_add_edges` 이후 자동 보정 없음) | 코드 확인 |
  | `core/workflow/validator.py:175-210` | 연결성 검사 | START에서 BFS로 도달 불가 노드만 경고(`UNREACHABLE_NODE`). 출구 없는 노드 검사는 없고, 실행 경로의 `WorkflowAPI`는 저장·검증 API에서만 validator를 호출(`core/api/workflow_api.py:431, 556, 1113`) | 코드 확인 |
  | `core/workflow/engine.py:62-108`, 1185-1187 | 보고서 필드 | `_get_dynamic_report_fields(agent_ids)`가 `agent_configs`의 `output_field`를 모아 최종 보고서 필드에 넣음 → `valuation_report` 포함. `core/workflow/builder.py:1597-1624`는 스키마에 `valuation_report`를 동적 선언("否则 Agent 返回的输出会被 LangGraph 丢掉" = 선언하지 않으면 에이전트 출력이 LangGraph에서 버려진다) | 코드 확인 |
  | `core/agents/adapters/research_manager_v2.py:723` | 하류 소비 비교 | `"chip_report"`는 연구 매니저 입력 목록에 있으나, `valuation_report`는 `core/agents/` 어디에도 읽는 코드 없음(`config.py:936-941` 메타데이터 정의 외) | grep 확인 |

- 동작 설명:
  1. `build()`는 `_filter_analyst_nodes`(1062)를 먼저 호출한다. `selected_analysts`가 있어도(`unified_analysis_engine.py:664-666`) valuation/chip 노드는 `ANALYST_ID_TO_TYPE`에 없어 항상 유지된다(1032-1033).
  2. 노드 추가 루프(1090-1112)에서 `valuation_analyst_v1`은 `_create_agent_node`(1634-1641 → 1692 이하)로 생성된다. 이 ID는 레지스트리에 없고 `agent_configs`에 `metadata.source == "agent_workshop"`, `version_status/runtime_status == "active"`로 있으므로 `_has_agent_config_in_db`(1809-1829)가 참이고, `AgentFactory.create`가 `UniversalAgent`를 만든다(`core/agents/factory.py:82-91`, 196-259). 도구는 R1-Q4 참조.
  3. 간선 단계: 도구 루프 대상이 아니므로 2단계(2846-2881)를 타지 않고 3단계에서 `parallel_analysts → valuation`이 일반 간선(2917)이 된다. valuation에서 나가는 간선이 JSON에 없으므로 추가되는 간선도 없다. `merge_analysts` 장벽(4단계, 2920-2934)에는 valuation이 포함되지 않는다.
  4. 따라서 이 노드는 `parallel_analysts` 다음 슈퍼스텝에서 다른 분석가와 병렬로 실행되고, 출력 `valuation_report`는 상태에 기록된다. 장벽이 이를 기다리지 않으므로 합류 이후 `debate` 단계 입력에는 영향을 주지 않으며, 최종 결과의 보고서 필드(`engine.py:1185-1187`)에만 나타난다.
  5. LangGraph 쪽 경우의 수(저장소에 `langgraph` 소스가 없고 요구사항은 `pyproject.toml:60`의 `langgraph>=0.4.8`뿐이라 정적으로 확정 불가): (A) `compile()`이 출구 없는 노드를 허용하면 위 4번대로 동작한다. (B) 허용하지 않으면 `build()`가 예외를 던져 해당 워크플로 실행 전체가 실패한다. 실패 시 `core/workflow/engine.py:325` 이후 처리는 호출자 예외로 전파된다. 부트스트랩 워크플로가 `updated_at 2026-07-08`까지 UI에서 저장된 것으로 보아 (A)를 전제로 배포된 것이지만, 이는 코드로 증명되는 사실이 아니다.
- 조사 범위: `core/workflow/builder.py`(`ANALYST_ID_TO_TYPE`, `_is_analyst_selected`, `build`, `_filter_analyst_nodes`, `_add_edges` 전부, `_create_node_function`), `core/workflow/validator.py`, `core/workflow/engine.py`. grep 패턴: `孤立|孤儿|dangling|dead.end|无出边|没有出边|orphan|unreachable|get_edges_from`(builder에서 출구 보정 코드 없음), `valuation_report|valuation_analyst_v1`(전체 `*.py`), `add_edge(.*END`.

#### R1-Q3 답변
- 결론: **확정**. `mcp_tdx-mcp_get_stock_info`는 이 저장소 안에서 도구 객체로 해석되지 않는다. `mcp_` 접두사를 해석하는 함수도, `tdx-mcp` 서버 정의도 없고, MCP 서버 도구를 `ToolRegistry`에 등록하는 `MCPService`는 커뮤니티 스냅샷에 존재하지 않는 `app.pro` 패키지에 있다. 기본 설치에서 이 바인딩은 `BindingManager._normalize_tool_ids`가 "无效工具绑定"으로 판정해 **건너뛴다**(LLM에 노출되지 않음, 오류 없음, 경고 로그만). 서버가 돌려줄 데이터 내용은 저장소 밖이라 알 수 없으나 기본 설치에서는 호출 자체가 일어나지 않는다. 따라서 `01-data.md` 1-0 표의 활성 바인딩 중 `mcp_tdx-mcp_get_stock_info`는 "운영에서 동작하지 않는 항목"으로 정정해야 한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `install/community_bootstrap.json` `data.tool_agent_bindings[34]` | 바인딩 | `agent_id: "market_analyst_v2"`, `tool_id: "mcp_tdx-mcp_get_stock_info"`, `priority: 2`, `is_active: true` (`[33]`은 `get_stock_market_data_unified`, priority 1). `workflow_id`/`node_id` 키는 82건 전부 없음 | JSON 확인 |
  | `install/community_bootstrap.json` `data.agent_configs[0].default_tools[1]`, `.tools[1]` | 에이전트 설정 | 같은 문자열 `mcp_tdx-mcp_get_stock_info`. `data.tool_configs`에는 `mcp` 카테고리/`mcp_` ID 항목 없음, `mcp_server_configs` 컬렉션은 부트스트랩 `data` 키 목록에 없음 | JSON 확인 |
  | `core/config/binding_manager.py:343-408` | `get_tools_for_node` | 노드 → 워크플로 → "Priority 3: Agent-level default" → `return self.get_tools_for_agent(agent_id)` (모든 바인딩에 `workflow_id`가 없으므로 3순위) | 코드 확인 |
  | `core/config/binding_manager.py:100-123` | `get_tools_for_agent` | DB `tool_agent_bindings.find({"agent_id": agent_id, "is_active": {"$ne": False}}, sort=[("priority", -1)])` → `tool_ids = [b["tool_id"] for b in bindings]` → `tool_ids = self._normalize_tool_ids(agent_id, tool_ids)` | 코드 확인 |
  | `core/config/binding_manager.py:146-160` | `_normalize_tool_ids` | `if registry is not None and not registry.has_tool(tool_id): invalid_tools.append(tool_id); continue` / `"检测到无效工具绑定，已自动忽略"`(유효하지 않은 도구 바인딩을 감지해 자동으로 무시) | 코드 확인 |
  | `core/tools/registry.py:96-98` | `has_tool` | `return tool_id in self._tools` (내장 도구 `BUILTIN_TOOLS`와 `@register_tool`로 등록된 것만) | 코드 확인 |
  | `app/main.py:329-336` | MCP 복원 | `from app.pro.services.mcp_service import MCPService` / `await mcp_service.restore_enabled_servers()` / 실패 시 `logger.error("❌ MCP 服务器工具恢复失败…")`(MCP 서버 도구 복원 실패) | 코드 확인 |
  | `app/` 디렉터리 목록 | `app/pro` 부재 | `__init__.py, __main__.py, constants, core, main.py, middleware, models, router_registry.py, routers, schemas, scripts, services, utils, worker, worker.py` — `pro` 없음. `app/router_registry.py:150-154`도 `except ImportError: PRO_ROUTERS = []` | 디렉터리 확인 |
  | `core/tools/mcp/client_manager.py:18-189`, `core/skills/executor.py:260-278` | MCP 클라이언트 | `MCPClientManager`는 스킬 실행기(`impl_type == mcp`)가 호출하는 용도뿐이며 `ToolRegistry.register`를 부르지 않음 | 코드 확인 |

- 동작 설명:
  1. 노드 생성 시 `builder.py:1697`이 `get_tools_for_node("market_analyst_v2", workflow_id, node_id)`를 호출 → 바인딩이 DB 3순위에서 조회되어 우선순위 내림차순으로 `['mcp_tdx-mcp_get_stock_info', 'get_stock_market_data_unified']`가 된다.
  2. `_normalize_tool_ids`(132-160)가 `ToolRegistry().has_tool(...)`로 검증한다. `mcp_tdx-mcp_get_stock_info`는 레지스트리에 없으므로 `invalid_tools`로 분류되어 최종 목록에서 빠지고 경고만 남는다. 결과는 `['get_stock_market_data_unified']`.
  3. 이 목록이 `AgentFactory.create(..., tool_ids=...)` → `BaseAgent._load_tools_v2` → `invoke_with_tools`의 `bind_tools`(`core/agents/base.py:733-734`)로 이어지므로 `mcp_…` 도구는 LLM 도구 목록에 들어가지 않는다.
  4. MCP 서버를 등록하는 경로는 `app.pro.services.mcp_service`뿐인데 이 모듈은 커뮤니티 스냅샷에 없어 `ImportError`가 잡힌다(`main.py:335-336`). 서버 정의가 저장되는 `mcp_server_configs`(읽는 곳: `app/services/analysis_profile_service.py:264`, `prompt_assembly_service.py:617`)도 부트스트랩에 없다. 즉 `tdx-mcp` 서버 정의의 위치는 "저장소 내 어디에도 없음(운영자가 Pro 쪽 UI로 등록해야 하는 외부 설정)"이다.
- 조사 범위: `install/community_bootstrap.json` 전체(`tdx`, `mcp` 문자열 위치를 JSON 경로로 나열), `core/config/binding_manager.py`, `core/tools/registry.py`, `core/tools/mcp/`, `core/skills/executor.py`, `app/main.py:270-340`, `app/router_registry.py`. grep 패턴: `tdx-mcp|tdx_mcp|mcp_tdx`(`*.py` 0건), `"mcp_|'mcp_|startswith("mcp`, `category="mcp"|ToolCategory.MCP|register_mcp`, `MCPService|restore_enabled_servers`, `mcp_server_configs`, `app\.pro`(19건: 모두 `ImportError` 처리되는 선택적 import).

#### R1-Q4 답변
- 결론: **확정**. 등록된 에이전트 클래스(예: `market_analyst_v2`)가 LLM에 `bind_tools`로 넘기는 최종 도구는 "DB `tool_agent_bindings`(레지스트리 검증 통과분)"만이며, DB `agent_configs[*].default_tools`와 합쳐지지 않는다. DB 바인딩이 비어 있으면 코드의 `BUILTIN_AGENTS`/클래스 `metadata.default_tools`로 대체되고, DB `agent_configs.default_tools`는 오직 레지스트리에 없는 DB 전용 에이전트(`UniversalAgent`)를 만들 때, 위 두 단계 결과가 빈 목록인 경우에 한해 읽힌다. 따라서 `news_analyst_v2`의 `get_weather`, `sector_analyst_v2`의 `test_heartbeat`는 기본 설치의 분석가 LLM에 노출되지 않는다. `01-data.md` 1-0 마지막 글머리 "(추론)"은 코드로 확정된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/workflow/builder.py:1692-1706` | `_create_agent_node` | `tool_ids = self.binding_manager.get_tools_for_node(agent_id=agent_id, workflow_id=self._workflow_id, node_id=node_id)` ("三层优先级工具查询：node > workflow > agent默认") | 코드 확인 |
  | `core/workflow/builder.py:1736-1741` | 에이전트 생성 | `agent = self.factory.create(agent_id, config, llm=llm, tool_ids=tool_ids, memory=agent_memory)` | 코드 확인 |
  | `core/config/binding_manager.py:100-123, 199-206` | `get_tools_for_agent` | DB 바인딩 → 없으면 `_get_default_tools_for_agent`: `from core.agents.config import BUILTIN_AGENTS` … `return agent.default_tools` (코드 상수) → `_normalize_tool_ids` | 코드 확인 |
  | `core/agents/factory.py:137-138, 147` | `create` | `if tool_ids is not None and supports_llm: init_kwargs["tool_ids"] = tool_ids` → `agent_class(**init_kwargs)` | 코드 확인 |
  | `core/agents/base.py:99-101` | `BaseAgent.__init__` | `if tool_ids is not None: … self._load_tools_v2(tool_ids)` | 코드 확인 |
  | `core/agents/base.py:733-735` | `invoke_with_tools` | `llm_with_tools = self._llm.bind_tools(self._langchain_tools)` | 코드 확인 |
  | `core/agents/factory.py:243-246` | `_try_create_universal_agent` | `resolved_tool_ids = tool_ids` / `if not resolved_tool_ids:` / `resolved_tool_ids = doc.get("default_tools") or doc.get("tools") or []` ("否则读取 agent_configs 的 default_tools" = 아니면 agent_configs의 default_tools를 읽는다). 호출 조건: `agent_class is None`(82-91) | 코드 확인 |
  | `install/community_bootstrap.json` `data.agent_configs[64]` | `valuation_analyst_v1` | `default_tools: ['get_historical_valuation_percentile_tool', 'get_dcf_valuation', 'get_current_valuation_snapshot_tool', 'get_peer_comparison']`. `data.tool_agent_bindings`에 이 에이전트 항목 0건, `BUILTIN_AGENTS`에도 `valuation_analyst_v1` 없음(`core/agents/config.py:917`은 `valuation_analyst_v2`) → 위 `factory.py:245-246`로 DB `default_tools`가 쓰임 | JSON/코드 확인 |
  | `install/community_bootstrap.json` `data.agent_configs[30]`, `[31]` | 시험용 도구 | `news_analyst_v2.default_tools = ['get_stock_news_unified', 'get_weather']`, `sector_analyst_v2.default_tools = ['get_china_market_overview', …, 'test_heartbeat']` | JSON 확인 |

- 동작 설명:
  1. `builder.py:1692`: 에이전트가 레지스트리에 등록됐거나 `agent_configs`에 활성 문서가 있으면 새 아키텍처로 생성한다.
  2. 도구 목록은 `get_tools_for_node` → (바인딩에 `workflow_id`/`node_id` 키가 없어) 3순위 `get_tools_for_agent`: DB 바인딩이 있으면 그것(예: `market_analyst_v2`는 `data.tool_agent_bindings[33], [34]` 중 R1-Q3로 `[34]`가 탈락해 1개), 없으면 코드 `BUILTIN_AGENTS`의 `default_tools`.
  3. 등록된 클래스(`MarketAnalystV2` 등)는 `tool_ids`가 `None`이 아니므로 `BaseAgent.__init__`에서 곧바로 `_load_tools_v2(tool_ids)`로 로드하고, 이후 `invoke_with_tools`가 그 목록만 `bind_tools`한다. `agent_configs.default_tools`를 다시 읽는 코드는 이 경로에 없다. 빌더가 `AgentConfigManager.get_agent_config`로 얻는 DB 문서도 `config` 필드(`db_agent_config.get('config', {})`)만 쓴다(`builder.py:1654-1657`, `default_tools` 미사용).
  4. 예외: 레지스트리에 없는 DB 전용 에이전트(기본 설치에서는 `valuation_analyst_v1`)는 바인딩과 코드 기본값이 모두 비어 `tool_ids == []`이므로 `factory.py:245-246`에서 DB `default_tools`를 사용한다. 이 경로는 `_normalize_tool_ids`를 거치지 않으므로 레지스트리에 없는 도구가 섞이면 `BaseAgent._load_tools_v2`(`base.py:229-275`)가 "工具未找到"(도구를 찾지 못함) 경고 후 건너뛴다.
- 조사 범위: `core/workflow/builder.py:1685-1760`, `core/config/binding_manager.py` 전체, `core/agents/factory.py` 전체, `core/agents/base.py:66-135, 215-275, 670-740`, `core/agents/analyst.py`, `core/agents/universal.py`, `core/config/agent_config_manager.py:60-140`. grep 패턴: `default_tools`(`core app tradingagents cli`의 `*.py` 전부). 읽는 위치 분류: 런타임 도구 결정에 쓰이는 곳은 `factory.py:246`과 코드 상수(`binding_manager.py:205`, `base.py:353-363`)뿐이고, 나머지는 표시·인덱싱(`app/services/capability_index_service.py:448,475`, `core/api/agent_api.py:191`, `core/workflow/generator/resource_collector.py:185,223`, `core/workflow/engine.py:933-934`는 `AgentMetadata` 표시용, `core/tools/implementations/agent_builder/nanobot_agent_builder_tools.py`는 에이전트 공방 도구)이다.

#### R1-Q5 답변
- 결론: **없음 확정**. 운영 경로의 A주 재무 로드에는 분석일 또는 공시일(`ann_date`/`f_ann_date`)로 행을 거르는 조건이 없다. 모든 단계가 "가장 최근에 갱신된 문서/가장 최근 보고기간"을 고르고, 호출 함수 시그니처에 분석일 인자가 아예 없다. 과거 일자로 분석해도 DB에 이미 들어 있는 최신 분기 재무가 그대로 들어갈 수 있다(look-ahead 차단 없음). `01-data.md` 2-5 마지막 행의 "추론"은 "없음 확정"으로 바꿀 수 있다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/tools/implementations/fundamentals/stock_fundamentals.py:803-805, 944-946` | 도구 시그니처 | `def get_financial_statements(ticker, limit=4)` / `def get_cash_flow_statement(ticker, limit=4)` — 날짜 인자 없음 | 코드 확인 |
  | `core/tools/implementations/fundamentals/stock_fundamentals.py:110-163` | `_load_recent_financial_data(ticker, limit=4)` | 1) `provider._get_cached_raw_financial_data(normalized_ticker)`(123-124) → 2) Tushare `get_financial_data(normalized_ticker, report_type='quarterly', limit=limit)`(135-137) → 3) AKShare `get_financial_data(normalized_ticker)`(149) → `_sort_and_trim_records(records, limit)`(157-158). 분석일 비교 없음 | 코드 확인 |
  | `core/tools/implementations/fundamentals/stock_fundamentals.py:86-107` | 정렬 | `_period_token`이 `('end_date', 'report_period', 'period', 'ann_date', 'f_ann_date')` 순서로 보고기간 토큰을 만들고 `sorted(..., reverse=True)[:limit]`로 최신 N개 선택. 기준일 상한 없음 | 코드 확인 |
  | `tradingagents/dataflows/optimized_china_data.py:2215, 2230-2235` | `_get_cached_raw_financial_data(self, symbol)` | `stock_financial_collection.find_one({'$or': [{'symbol': symbol}, {'code': symbol}]}, sort=[('updated_at', -1)])` — 필터는 종목 키뿐, 정렬은 `updated_at` 내림차순, limit 1 | 코드 확인 |
  | `tradingagents/dataflows/optimized_china_data.py:2293-2303` | 2차 캐시 | `collection.find_one({'symbol': symbol, 'cache_type': 'raw_financial_data'}, sort=[('updated_at', -1)])` + `datetime.now() - cache_time < timedelta(hours=24)` (벽시계 24시간 만료, 분석일 무관) | 코드 확인 |
  | `tradingagents/dataflows/cache/mongodb_cache_adapter.py:271-294` | `get_financial_data(symbol, report_period=None)` | `query = {"code": code6, "data_source": data_source}` / `collection.find_one(query, {"_id": 0}, sort=[("report_period", -1)])` (가장 최근 보고기간) | 코드 확인 |
  | `tradingagents/dataflows/providers/china/tushare.py:718-749` | `get_financial_data(symbol, report_type, period=None, limit=None)` | `query_params = {'ts_code': ts_code}`에 `limit`, `period`만 추가. 공시일 필터 없음 | 코드 확인 |
  | `tradingagents/dataflows/providers/china/tushare.py:1600-1622` | `_pick_latest_disclosed_record` | `today = datetime.utcnow().strftime('%Y%m%d')` / `if not ann_date or ann_date <= today:` — 공시일 필터가 있으나 기준이 "오늘(UTC)"이고 `_standardize_tushare_financial_data`(1440 이하, 동기화 표준화) 내부이므로 분석일 기준이 아님 | 코드 확인 |
  | `core/tools/implementations/fundamentals/stock_fundamentals.py:630-720` | `get_stock_fundamentals_unified` | `curr_date`는 `apply_stable_data_cutoff`(가격·밸류에이션 안정 구간)와 `_get_historical_valuation_summary(normalized_ticker, curr_date)`에만 쓰이고, 재무 본문은 `analyzer._generate_fundamentals_report(normalized_ticker, company_profile_data, "standard")`(720; 정의 `optimized_china_data.py:349`, 분석일 인자 없음) | 코드 확인 |

- 동작 설명: LLM이 `get_financial_statements`/`get_cash_flow_statement`를 호출하면 `_load_recent_financial_data`가 (1) MongoDB `stock_financial_data`에서 종목 키로 `updated_at` 최신 문서 1건, 없으면 (2) `financial_data_cache` 24시간 캐시, 없으면 (3) Tushare 최근 보고기간 `limit`개, 없으면 (4) AKShare 순으로 가져온다. 어느 단계에도 분석일/공시일 조건이 없으므로, 과거 분석일에 대해서도 호출 시점의 최신 공시분이 포함될 수 있다. `get_stock_fundamentals_unified`의 재무 본문도 같은 계열의 "현재 최신" 데이터를 쓰며 `curr_date`는 가격·밸류에이션 쪽 안정화(`apply_stable_data_cutoff`)에만 적용된다. 단, 이 `limit`는 도구가 받는 파라미터라서 LLM이 임의로 바꿀 수 있고(1~8로 절단, 830), 이는 날짜 필터와 무관하다.
- 조사 범위: 위 표의 함수 체인 전부와 `tradingagents/dataflows/optimized_china_data.py` 전체, `tradingagents/dataflows/cache/mongodb_cache_adapter.py`, `tradingagents/dataflows/providers/china/tushare.py`(재무 관련), `core/tools/implementations/fundamentals/`. grep 패턴: `ann_date|f_ann_date|as_of|analysis_date|trade_date|curr_date|end_date|report_date|report_period`(`optimized_china_data.py`에서 날짜 필터 0건: 일치 항목은 `_get_cached_raw_financial_data`가 아니라 보고서 문자열 쪽만), `stock_financial_data`(읽는 위치 전부: `app/routers/stocks.py:672,873-892`, `app/routers/financial_data.py:355`, `tradingagents/dataflows/realtime_metrics.py:254`는 API/지표 조회용으로 분석 체인 밖).

#### R1-Q6 답변
- 결론: **없음 확정**. `core/agents/adapters/sector_analyst_v2.py`의 섹터 보고서 캐시 읽기·쓰기 함수 `_get_cached_sector_report`(60)와 `_save_sector_report_to_cache`(109)는 저장소 전체에서 호출처가 없다. 즉 운영에서 실행되지 않고, 키(`sector_{板块名}`)와 TTL(`SECTOR_REPORT_CACHE_TTL_HOURS = 1`)은 정의만 있다. 주석("已废弃，不再使用")이 코드 현실과 일치한다. `01-data.md` 2-4 "섹터 보고서 캐시" 행의 "(주석과 코드가 상충)" 추론은 "미사용 확정"으로 정정한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/agents/adapters/sector_analyst_v2.py:18-21` | 상수 | `# ==================== 缓存配置（已废弃） ====================` / `# ⚠️ 行业报告不支持缓存：行业报告包含具体股票的代码和名称，缓存会导致同行业其他股票分析时出现错误信息`(업종 보고서는 캐시를 지원하지 않는다. 구체 종목 코드·이름이 들어 있어 같은 업종의 다른 종목 분석에 잘못된 정보가 나온다) / `SECTOR_REPORT_CACHE_TTL_HOURS = 1  # … 已废弃，不再使用` | 코드 확인 |
  | `core/agents/adapters/sector_analyst_v2.py:60-106` | `_get_cached_sector_report(ticker, trade_date)` | 키 `cache_symbol = f"sector_{sector_name}"`, `cache.find_cached_analysis_report(report_type="sector_report", symbol=cache_symbol, trade_date=trade_date, max_age_hours=max_age_hours)` | 코드 확인 |
  | `core/agents/adapters/sector_analyst_v2.py:109-154` | `_save_sector_report_to_cache` | `cache.save_analysis_report(report_type="sector_report", report_data=report, symbol=cache_symbol, trade_date=trade_date)` | 코드 확인 |
  | 저장소 전체 grep | 호출처 | `_get_cached_sector_report`, `_save_sector_report_to_cache`, `SECTOR_REPORT_CACHE_TTL_HOURS`는 위 정의 줄과 `tradingagents/agents/analysts/sector_analyst.py:26,39,73`(동명의 레거시 정의)에서만 등장. 두 파일 모두 자기 파일 안에서 호출하지 않음 | grep 확인 |
  | `core/agents/adapters/sector_analyst_v2.py:253` | `execute` | 실행 본문에 캐시 함수 호출 없음 | 코드 확인 |
  | `core/workflow/builder.py:2306` | 레거시 참조 | `"sector_analyst": ("tradingagents.agents.analysts.sector_analyst", "create_sector_analyst", "toolkit")` — 레거시 `sector_analyst`(v1)용이며 v2 워크플로의 `sector_analyst_v2`는 아님 | 코드 확인 |

- 동작 설명: 운영 워크플로(6ede3bc3)의 노드는 `sector_analyst_v2`이고 `SectorAnalystV2.execute`(253)는 캐시 읽기·쓰기를 부르지 않는다. 캐시 함수 2개는 정의만 있는 죽은 코드라서 `integrated.py`의 `find_cached_analysis_report`/`save_analysis_report`도 이 경로에서는 불리지 않는다. 대시보드 보고서와 달리 종목 간 섹터 LLM 산출물 공유는 없다. (섹터 데이터 도구 쪽 캐시 `core/tools/sector_tools.py:39-124`의 `_read_sector_cache`/`_write_sector_cache`는 섹터 목록·구성종목 DataFrame 캐시로 이 질문과 별개다.)
- 조사 범위: 저장소 전체 `grep -rn "_get_cached_sector_report|_save_sector_report_to_cache|SECTOR_REPORT_CACHE_TTL_HOURS"`(`.py` 외 파일 포함, `node_modules` 제외), `grep -rn '"sector_report"'`(캐시 관련 `report_type` 사용처: `sector_analyst_v2.py:93,142`, `tradingagents/agents/analysts/sector_analyst.py:57,92`뿐), `core/agents/adapters/sector_analyst_v2.py` 전체, `tradingagents/agents/analysts/sector_analyst.py`(함수 정의만, 호출 없음).

#### R1-Q7 답변
- 결론: **없음 확정**. `IM_TOPIC_DIGEST_ENABLED`/`IM_TOPIC_DIGEST_CRON`(및 `MIN_MESSAGES`, `LOOKBACK_LIMIT`)을 읽어 작업을 등록·실행하는 코드는 저장소에 없다. 이 설정은 `app/core/config.py`에 정의만 있고, `IMTopicDigestService.run_once`는 테스트(`tests/unit/app/test_im_topic_digest_service.py`) 외에 호출처가 없다. 따라서 `02-schedule.md` 3-2의 "등록 위치는 찾지 못했다 (미확인)"은 "등록 코드 없음(커뮤니티 스냅샷 기준 미연결)"으로 확정된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `app/core/config.py:282-285` | 설정 정의 | `IM_TOPIC_DIGEST_ENABLED: bool = Field(default=True, description="启用外部会话定期沉淀到研究主题")` / `IM_TOPIC_DIGEST_CRON … default="30 22 * * *", description="外部会话沉淀CRON表达式，默认每日22:30"` / `…MIN_MESSAGES default=6` / `…LOOKBACK_LIMIT default=20` | 코드 확인 |
  | `app/services/im_topic_digest_service.py:18-58` | 서비스 | `class IMTopicDigestService:` `async def run_once(self, min_messages: int = 6, lookback_limit: int = 20)` — `assistant_threads`에서 `topic_type == "im_session"` 스레드를 스캔해 주제로 정리 | 코드 확인 |
  | 저장소 전체 grep | 참조 | `IM_TOPIC_DIGEST`는 `app/core/config.py` 4줄에만 있고, `IMTopicDigestService`/`im_topic_digest_service`는 정의 파일과 `tests/unit/app/test_im_topic_digest_service.py:3,35`에서만 등장 | grep 확인 |
  | `app/main.py:588-662` 외 `add_job` 27건 | 스케줄 등록 패턴 | 다른 크론은 `CronTrigger.from_crontab(settings.XXX_CRON, timezone=settings.TIMEZONE)`로 `app/main.py`나 `app/services/scheduler_service.py`에서 등록. `IM_*`를 쓰는 등록 코드는 없음 | 코드 확인 |

- 동작 설명: 설정 4개와 서비스 클래스는 존재하지만 이를 연결하는 `scheduler.add_job(...)`이 어디에도 없어, 기본값이 "켜짐(`True`, 매일 22:30)"이어도 실제로는 아무 작업도 돌지 않는다. 즉 "정의만 있는 설정"이다. Pro 쪽(`app/pro`)에서 등록했을 가능성은 이 스냅샷에서 확인할 수 없지만, 커뮤니티 스냅샷의 실행 경로에는 없다.
- 조사 범위: `app/`, `core/`, `tradingagents/`, `cli/`, `scripts/`, `install/` 전체. grep 패턴(대소문자 무시 포함): `IM_TOPIC_DIGEST|topic_digest|topic-digest|TopicDigest|im_topic_digest|digest`(`hexdigest`는 무관 일치: `app/services/update_service.py:387`, `core/tools/implementations/news/stock_news.py:1145`), `settings\.IM_|IM_[A-Z_]+_CRON|getattr\(settings`, `run_once\(`(다른 서비스 것만 있음), `app/services/scheduler_service.py`·`app/worker/` 내 `digest|im_|assistant_threads`(0건).

#### R1-Q8 답변
- 결론: **없음 확정**. 기본 운영 경로(웹 UI → 큐 → 워커 `engine == "v2"` → `TaskAnalysisService.execute_task` → `UnifiedAnalysisEngine`)에서는 `app/utils/report_formatter.py`의 `format_analysis_result`도 `format_decision`도 호출되지 않는다. 결과 정규화는 `TaskAnalysisService._format_analysis_result`/`_format_decision_dict`가 자체 처리한다. 따라서 `SignalProcessor` 재추출(추가 LLM 호출)은 이 경로에서 일어나지 않는다. 두 함수는 `UnifiedAnalysisService._format_result`(opt-in "unified" 엔진 경로)에서만 호출된다. **보고서 정정 필요**: (가) `03-decision.md` 4-6 "운영 경로 호출 여부는 미확인"은 "기본(v2) 경로 호출 없음, `engine=unified`일 때만"으로, (나) 4-3-b "용어 사전" 행의 "결정 필드 부재 시 호출"은 실제 조건이 "`decision_raw`에 `reasoning`/`rationale`이 없고 `fallback_text` 길이 > 50"이므로 그 조건으로 정정한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `app/utils/report_formatter.py:792, 1181, 1307` | 정의와 유일한 내부 호출 | `def format_decision(`, `def format_analysis_result(`, `formatted_decision = format_decision(final_decision, fallback_for_reasoning, quick_model=quick_model, stock_code=stock_code)` | 코드 확인 |
  | `app/utils/report_formatter.py:818-827` | `SignalProcessor` 호출 조건 | `needs_signal_processing = (fallback_text and len(fallback_text) > 50 and (not decision_raw.get('reasoning') and not decision_raw.get('rationale')))` → `from tradingagents.graph.signal_processing import SignalProcessor`; 889-893: `SignalProcessor(quick_llm)` / `signal_processor.process_signal(fallback_text, stock_code)` | 코드 확인 |
  | `app/services/unified_analysis_service.py:590, 607` | `format_analysis_result`의 유일한 호출처 | `from app.utils.report_formatter import format_analysis_result` / `result = format_analysis_result(raw_result=raw_result, …)` (`_format_result`, 573) | 코드 확인 |
  | `app/services/unified_analysis_service.py:482, 562` | `_format_result` 호출 | `return self._format_result(result, stock_code, analysis_date, task_id, parameters)` — `analyze`(382)와 `analyze_sync`(493) 안 | 코드 확인 |
  | `app/services/unified_analysis_service.py:677, 828, 996` | `analyze`의 호출처 | `analyze_batch`(623), `execute_analysis_for_ab_test`(711), `execute_analysis_for_v2_engine`(891) 안의 `await self.analyze(…)` | 코드 확인 |
  | `app/worker/analysis_worker.py:846-866` | 도달 가능한 유일한 외부 진입 | `elif engine_type == "unified":` … `await unified_service.execute_analysis_for_ab_test(task_id=task_id, user_id=user_id, request=single_req)` (큐 파라미터 `engine == "unified"`일 때만) | 코드 확인 |
  | `app/worker/analysis_worker.py:746, 818, 842` | 기본 경로 | `engine_type = parameters_dict.get("engine", "v2")` / `if engine_type == "v2":` / `await task_service.execute_task(task, progress_callback=self._progress_callback)` (`TaskAnalysisService`) | 코드 확인 |
  | `frontend/src/views/Analysis/SingleAnalysis.vue:1025, 1622` | UI 고정값 | `engine: 'v2',  // 固定使用 v2.0 引擎`(v2.0 엔진 고정), `// 🔥 固定使用 v2.0 引擎（旧版引擎已隐藏）`(구 엔진은 숨김) | 코드 확인 |
  | `app/services/task_analysis_service.py:272-273, 769` | 기본 경로 정규화 | `result = await self.engine.execute_task(task, wrapped_progress_callback)` → `formatted_result = self._format_analysis_result(result, task)`. 이 파일의 `report_formatter` 사용은 `_convert_json_to_markdown`(1089)과 `extract_reports_from_state`(2327)뿐 | 코드 확인 |
  | `app/services/unified_analysis_engine.py` 전체 | 엔진 | `report_formatter`/`format_` 호출 0건 (grep) | grep 확인 |
  | `app/services/thread_worker.py:279, 311` | 스레드 워커 | v2는 `self.task_service.execute_task(existing_task)`(279). unified는 `unified_service.analyze_stock(…)`(311)이나 `UnifiedAnalysisService`에는 `analyze_stock` 메서드가 정의되어 있지 않다(`core/mcp/server.py:78`의 동명 함수는 별개) → 도달해도 `AttributeError` | 코드 확인 |

- 동작 설명:
  1. `POST /api/analysis/single`(`app/routers/analysis.py:248`)은 `engine` 기본값 `AnalysisEngine.V2`(`app/models/analysis.py:68-71`)로 `TaskAnalysisService.create_task` → 큐 적재(`routers/analysis.py:340-395`).
  2. 워커(`analysis_worker.py:818-842`)가 `TaskAnalysisService.execute_task`를 호출하고, 이는 `UnifiedAnalysisEngine.execute_task`로 결과를 얻은 뒤(`task_analysis_service.py:272`) 자체 `_format_analysis_result`(769)로 정규화한다. 여기에는 `report_formatter.format_*`와 `SignalProcessor` 호출이 없다.
  3. `engine == "unified"`(워커 846) 또는 `/batch`의 unified 분기를 타는 경우에만 `UnifiedAnalysisService.analyze` → `_format_result` → `format_analysis_result` → `format_decision`이 실행되고, 조건(818-823)이 맞을 때 `SignalProcessor`가 빠른 모델로 LLM 1회를 추가 호출한다. 웹 UI는 `engine: 'v2'`를 고정 전송한다.
  4. `analyze_sync`(493), `analyze_batch`(623), `execute_analysis_for_v2_engine`(891)은 저장소에 호출처가 없다.
  5. 레거시 `tradingagents/core/engine/phase_executors/risk_assessment.py:269-278`도 `SignalProcessor()`를 쓰지만 이는 `StockAnalysisEngine` 경로이고, 그 호출부 `app/services/portfolio_service.py:4291-4293`는 "v3.0 起旧版 StockAnalysisEngine 已停用（死代码，无调用者）"(v3.0부터 구 StockAnalysisEngine은 사용 중단된 죽은 코드)로 명시되어 있다.
- 조사 범위: 저장소 전체 `.py`(tests·docs 제외) grep 패턴: `(^|[^_a-zA-Z])format_analysis_result\b`, `(^|[^_a-zA-Z])format_decision\b`, `report_formatter`(import 위치 전부), `SignalProcessor|signal_processing|process_signal`, `analyze_sync|execute_analysis_for_v2_engine|execute_analysis_for_ab_test|unified_service\.[a-z_]+\(`, `\.analyze\(`, `analyze_batch`, `def analyze_stock`. 진입점: `app/routers/analysis.py`(single/batch/analyze), `app/worker/analysis_worker.py`, `app/services/thread_worker.py`, `app/services/task_analysis_service.py`, `app/services/unified_analysis_service.py`. (테스트 `tests/test_research_brief_runtime.py:63,96`은 `format_decision` 직접 호출이나 운영 경로 아님.)

#### R1-Q9 답변
- 결론: **확정**. 기본 설치(이 커뮤니티 스냅샷)에서 `agent_assertions` 단언 체계는 "비어 있는" 정도가 아니라 **아예 동작하지 않는다**. 단언 모델·서비스가 들어 있는 `app/pro/` 패키지가 저장소에 없어 `_run_assertions`가 `ImportError`를 잡고 "ran=False, violations=[]" 자리표시 결과를 반환하기 때문이다. `agent_assertions`에 문서를 쓰는 코드(부트스트랩, 마이그레이션, 시드, 코드 기본 단언)는 저장소 어디에도 없고(없음 확정), 코드 기본 단언으로 대체하는 분기도 없다. **보고서 정정 필요**: `03-decision.md` 4-5 "규칙 기반 단언" 행의 "시드 비어 있음은 추론"은 "Pro 전용 모듈 부재로 항상 건너뜀(코드로 확정)"으로 정정한다. `AGENT_ASSERTION_ENABLED` 기본값 `True`(`app/core/config.py:178-181`)는 이 상황에서 의미가 없다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/agents/manager.py:317-340` | `ManagerAgent._run_assertions` | `from app.pro.models.agent_assertion import AssertionRunResult` / `except ImportError:` `# 社区版无断言体系（app/models/agent_assertion 等已随 Pro 开源分离剔除）` / `return SimpleNamespace(ran=False, violations=[], has_error_violation=False, error_count=0)` ("断言功能整体静默跳过" = 단언 기능 전체를 조용히 건너뜀) | 코드 확인 |
  | `app/` 디렉터리 | `app/pro` 부재 | R1-Q3 표의 목록과 동일. `find . -type d -name pro`(node_modules 제외) 결과 없음, `*assertion*` 파일명은 `core/agents/assertion_executor.py` 1개뿐 | 디렉터리 확인 |
  | `core/agents/assertion_executor.py:31-45, 84-91` | 실행기 | `from app.pro.models.agent_assertion import (AgentAssertion, …)` / `from app.pro.services.agent_assertion_service import agent_assertion_service` / `except ImportError: _ASSERTION_BACKEND_AVAILABLE = False`; `if not _ASSERTION_BACKEND_AVAILABLE: raise ImportError("断言后端不可用（社区版无 agent_assertion 体系）")` (단언 백엔드 사용 불가) | 코드 확인 |
  | `core/agents/assertion_executor.py:88-91` | 컬렉션이 비었을 때 | `assertions = agent_assertion_service.load_enabled_assertions_sync(agent_id)` / `if not assertions: return AssertionRunResult(ran=False)` — 코드 기본 단언으로 대체하지 않고 "미실행" 반환 | 코드 확인 |
  | `app/core/database.py:444-449` | 인덱스 생성 | `from app.pro.services.agent_assertion_service import agent_assertion_service` / `await agent_assertion_service.create_indexes()` / `except Exception … "断言索引初始化失败（不影响应用启动）"` | 코드 확인 |
  | `app/core/config.py:177-185` | 플래그 | `AGENT_ASSERTION_ENABLED: bool = Field(default=True, description="启用 Agent 断言执行（从 agent_assertions 集合加载并执行断言）")`, `AGENT_ASSERTION_CACHE_TTL_SECONDS … default=60` | 코드 확인 |
  | `install/community_bootstrap.json` `data` 키 | 부트스트랩 컬렉션 | `system_configs, platform_configs, llm_providers, model_catalog, datasource_groupings, market_categories, stock_industry_mappings, workflows, agent_configs, tool_configs, tool_agent_bindings, prompt_templates, paper_market_rules` — `agent_assertions` 없음 | JSON 확인 |
  | `core/agents/adapters/research_manager_v2.py:296, 340`, `risk_manager_v2.py:498, 543` | 호출부 | `assertion_result = self._run_assertions(raw_text=…, parsed=validated_dict)` → `[v.model_dump() for v in assertion_result.violations]`(빈 목록) → `if assertion_result.has_error_violation:`(False) | 코드 확인 |

- 동작 설명: 연구 매니저/리스크 매니저가 LLM 출력을 검증한 뒤 `_run_assertions`를 호출한다. 이 함수는 첫 줄의 `app.pro.models.agent_assertion` import에서 `ImportError`가 나므로 항상 `SimpleNamespace(ran=False, violations=[], …)`를 돌려주고, 호출부의 `violations`/`has_error_violation` 접근이 모두 안전하게 빈 값이 되어 `validation_status`에 아무 변화도 없다. `agent_assertions` 컬렉션 자체를 읽는 코드(`agent_assertion_service`)가 이 스냅샷에 없으므로, 사용자가 컬렉션에 문서를 직접 넣어도 읽히지 않는다. 즉 "코드가 LLM 결과를 제한하는 장치"로서의 단언은 커뮤니티 스냅샷에서는 없다.
- 조사 범위: `install/`, `migrations/`, `app/`, `core/`, `tradingagents/`, `scripts/` 전체 grep `agent_assertions`(비문서·비테스트 일치는 `app/core/config.py:180`의 설명 문자열 1건뿐), `agent_assertion|AgentAssertion|AssertionRunResult|assertion_executor|AGENT_ASSERTION_ENABLED|assertion_store`, `app\.pro`(19건 모두 선택적 import), 파일명 `find . -iname "*assertion*"`. 진입점에서 `ManagerAgent._run_assertions` 호출부 4곳까지 추적.

#### R1-Q10 답변
- 결론: **없음 확정**. `core/agents/utils/weight_calculator.py`의 공개 함수(`calculate_report_weights`, `format_weighted_reports_prompt`)와 내부 함수 4개는 저장소 어디에서도 호출되지 않는다. 유일한 참조는 `core/agents/utils/__init__.py`의 재export 줄뿐이다. 동적 import(`importlib`, 문자열 경로, 레지스트리, DB 설정)에서도 이름이 나오지 않는다. 따라서 분석가 신호의 코드 가중 합산은 운영 경로에 없고, "최종 판단은 LLM만"(`00-overview.md` 2절)과 모순되지 않는다. 한 가지 정정: 이 모듈은 호출은 없지만 `core.agents.utils` 패키지가 import될 때 **로드**는 된다(아래).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/agents/utils/weight_calculator.py:10, 63, 89, 142, 195, 212` | 정의 이름 목록 | `calculate_report_weights`, `_infer_trading_style`, `_calculate_short_term_weights`, `_calculate_long_term_weights`, `_calculate_equal_weights`, `format_weighted_reports_prompt` (docstring: "根据用户选择的分析师，自动计算各报告的权重" = 사용자가 고른 분석가에 따라 각 보고서의 가중치를 자동 계산) | 코드 확인 |
  | `core/agents/utils/__init__.py:5-13` | 재export | `from .weight_calculator import (calculate_report_weights, format_weighted_reports_prompt,)` / `__all__ = ["calculate_report_weights", "format_weighted_reports_prompt"]` | 코드 확인 |
  | 저장소 전체 grep | 호출처 | 위 6개 이름 각각: `calculate_report_weights`는 `__init__.py` 6, 11행만, `format_weighted_reports_prompt`는 `__init__.py` 7, 12행만, 내부 `_…` 4개는 정의 파일 안 외에 0건 (`tests/`, `docs/` 포함 `.py/.json/.yaml/.md`) | grep 확인 |
  | `core/agents/adapters/sector_analyst_v2.py:14`, `index_analyst_v2.py:16` | 모듈 로드 경로 | `from core.agents.utils.data_source_mode import resolve_market_data_mode` — 하위 모듈 import가 패키지 `__init__`을 실행해 `weight_calculator`를 로드(함수 호출은 아님) | 코드 확인 |
  | `core/agents/researcher.py`, `core/agents/adapters/research_manager_v2.py`, `core/agents/manager.py`, `core/workflow/*.py` | 가중 로직 | `weights?|weighted|report_weight` grep 0건 (연구 매니저는 보고서를 프롬프트로 넘길 뿐 가중치를 계산하지 않음) | grep 확인 |

- 동작 설명: 분석가 보고서는 상태 필드로 연구원/매니저 프롬프트에 그대로 전달되고(`researcher.py:265-282` `_collect_reports`), 가중치를 계산해 합산하거나 프롬프트에 삽입하는 코드는 호출되지 않는다. `weight_calculator.py`는 과거 설계의 잔재(죽은 코드)이며 `import` 시점에 로드만 된다.
- 조사 범위: 저장소 전체(`*.py`, `*.json`, `*.yaml`, `*.md` 포함) grep: `weight_calculator`, `calculate_report_weights`, `format_weighted_reports_prompt`, `_infer_trading_style|_calculate_short_term_weights|_calculate_long_term_weights|_calculate_equal_weights`, `weighted_reports|report_weights|report_weight`, `importlib|import_module`(`core/tools/loader.py`, `core/skills/executor.py`, `core/workflow/builder.py` 등 동적 import는 고정 문자열 모듈만 대상), `install/community_bootstrap.json`에서 `weight_calc`(0건).

#### R1-Q11 답변
- 결론: **확정**. 기본 설치에서 `MemoryManager.get_agent_memory`가 돌려주는 구현체는 `Mem0AgentMemory`(`MEMORY_USE_MEM0_COMPAT` 기본 `true`)이며, 그 뒤는 `MemoryService`(mem0 `AsyncMemory`) + 커스텀 MongoDB 벡터 저장소(클라이언트 cosine)다. ChromaDB/Qdrant/`AgentMemory`(+`VectorStoreManager`)는 `MEMORY_USE_MEM0_COMPAT=false`일 때만 쓰이는 레거시 경로다. 임베딩은 시스템 설정 `default_embedding_model`로 정해지며 부트스트랩 값은 `dashscope:text-embedding-v4`(1024차원)이지만, 실제 사용은 DB에 저장된 API 키 유무에 달려 있다. LLM API 키가 없으면 mem0는 `_init_error`로 영구 비활성화되어 저장·검색이 조용히 무동작(빈 결과)이 된다. **보고서 정정 필요**: `next.md` 미확인 4번의 후보 "chromadb/mongodb vector/qdrant"는 기본값이 아니며 기본은 mem0 + MongoDB다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/workflow/builder.py:978-983, 1730-1733` | 메모리 주입 | `self.embedding_manager = EmbeddingManager(db=db)` / `self.memory_manager = MemoryManager(self.embedding_manager)`; 에이전트 생성 시 `agent_memory = self.memory_manager.get_agent_memory(agent_id)` → `factory.create(…, memory=agent_memory)`(1736-1741). 초기화 실패 시 "Agent 将在没有记忆功能的情况下运行"(에이전트는 메모리 없이 실행) | 코드 확인 |
  | `core/memory/memory_manager.py:589, 597-614` | 구현체 선택 | `self._use_mem0_compat = str(os.getenv("MEMORY_USE_MEM0_COMPAT", "true")).strip().lower() in {"1", "true", "yes", "on"}` / `if self._use_mem0_compat: … Mem0AgentMemory(agent_id)` / `else: … AgentMemory(agent_id, self.embedding_manager)` | 코드 확인 |
  | `core/memory/memory_manager.py:109-137, 139-185` | `Mem0AgentMemory` | `svc.store([{"role": "user", "content": …}], user_id=…, agent_id=self.agent_ids[0], session_id=ticker, scope="agent_experience", metadata=…, infer=False)`; 검색은 `svc.recall(query=…, agent_id=agent_id, scopes=["agent_experience"], metadata_filters=…, limit=n_results)`, 점수는 `"similarity": item.score`. 실패 시 `logger.warning` 후 `False`/`[]` | 코드 확인 |
  | `core/memory/memory_manager.py:214-243` | 레거시 `VectorStoreManager` | `backend = os.getenv("VECTOR_STORE_BACKEND", "mongodb").lower()` → `mongodb`/`qdrant`/`chromadb` 분기 (`MEMORY_USE_MEM0_COMPAT=false`일 때만 도달) | 코드 확인 |
  | `core/memory/service.py:51-53, 83-119, 187-192, 303-304` | `MemoryService` | `MEM0_ENABLED` 기본 `"true"`; `_ensure_init`: `from mem0 import AsyncMemory`, `register_mem0_mongodb_provider()`, `resolved_config = config or build_mem0_config(self._db)`; `if not resolved_config.get("llm", {}).get("config", {}).get("api_key"): self._init_error = "缺少 LLM API Key，mem0 记忆层不可用"`(LLM API 키 없음, mem0 메모리 계층 사용 불가); 임베더 검증 실패도 `_init_error`. `_init_error`가 한번 세팅되면 `_ensure_init`은 계속 `False`(87-88). `store`는 `StoreResult(success=False, …)`(187-192), `recall`은 `[]`(303-304) | 코드 확인 |
  | `core/memory/config.py:437-583` | `build_mem0_config` | `vector_store = {"provider": "mongodb", "config": {"mongo_uri": …, "db_name": …, "collection_name": collection_name, "embedding_model_dims": embedding_dims}}`(524-531); `embedder = _resolve_embedding_from_db(db_settings)`(513); LLM은 `get_system_llm_config_from_config_doc`로 `quick_analysis_model` → `deep_analysis_model` 순 | 코드 확인 |
  | `core/memory/mem0_mongodb_store.py:1-8` | 벡터 저장소 | "mem0 自定义 MongoDB 向量存储（客户端 cosine 相似度）… 替代 mem0 官方的 …MongoDB（依赖 Atlas $vectorSearch）" | 코드 확인 |
  | `core/memory/config.py:286-291, 294-305, 315-352, 391-433` | 임베더 결정 | `default_embedding_model`을 `"제공자:모델"`로 분해 → `llm_providers`에서 `{"supported_features": "embedding", "is_active": True}` 조회 → 선호 제공자의 문서로 임베더 구성. OpenAI 호환 제공자(`openai, dashscope, siliconflow, 302ai, openrouter, localai, lmstudio`, 21-29)는 `api_key`가 비면 `{}`(336-337), 비어 있으면 다른 활성 제공자로 폴백. `ollama`는 키 없이 `ollama_base_url`(기본 `http://localhost:11434`) | 코드 확인 |
  | `install/community_bootstrap.json` `data.system_configs[93].system_settings.default_embedding_model` | 부트스트랩 기본값 | `"dashscope:text-embedding-v4"`; `data.llm_providers[4]`(dashscope): `supported_features`에 `embedding`, `is_active: true`, `api_key: ""`, `embedding_model: "text-embedding-v4"`, `default_base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"`. `core/llm/embedding_manager.py:34`: `"text-embedding-v4": 1024` | JSON/코드 확인 |
  | `app/services/community_bootstrap_service.py:30-58` | 키 비움 | `_sanitize`가 `api_key` 등 비밀 필드를 빈 값으로 만들어 부트스트랩 문서에는 키가 없음 | 코드 확인 |

- 동작 설명:
  1. 워크플로 빌더 생성 시(`builder.py:978-983`) `EmbeddingManager`/`MemoryManager`가 만들어지고, 에이전트마다 `get_agent_memory(agent_id)`가 `Mem0AgentMemory`를 반환한다(기본). 연구원 `researcher.py:222-225`의 `self.memory`는 이 객체다.
  2. 저장(`add_memory`)과 검색(`search_memories`)은 `get_memory_service()` 싱글턴을 통해 `_ensure_init`에서 mem0 `AsyncMemory`를 만든다. 벡터 저장소는 MongoDB 컬렉션 `mem0_memories_{제공자}_{모델}_{차원}_{해시}`(`config.py:19, 59-68`)이며 코사인 유사도는 Python 쪽(numpy)에서 계산한다.
  3. 임베딩 모델: 시스템 설정 `default_embedding_model`(부트스트랩 값 `dashscope:text-embedding-v4`)을 우선 사용하고, 그 제공자에 API 키가 없으면 다른 활성 임베딩 제공자로 폴백한다. 키가 있는 제공자가 하나도 없으면 `ollama`(`nomic-embed-text`, 로컬 11434)가 마지막 후보이고, 해당 서버가 없으면 임베딩 호출 시점에 예외가 나서 저장·검색이 실패(경고 후 `False`/`[]`)한다.
  4. 가장 먼저 걸리는 관문은 LLM 키다: `service.py:110`이 mem0 LLM 설정(`quick_analysis_model` 해석 결과)의 `api_key`가 비면 `_init_error`를 세팅하고 이후 영구적으로 비활성이다. 키는 설치 후 "系统设置"에서 입력하는 값이므로(`community_bootstrap_service.py:130` 로그 "首次登录后请在「系统设置」中配置 LLM 与数据源密钥"), 키 입력 전/후 동작은 갈린다(키 입력 후 프로세스 재시작 없이도 첫 호출에서 초기화 시도하나, 실패하면 `_init_error`가 프로세스 수명 동안 남는다).
  5. 환경변수 경우의 수: `MEM0_ENABLED=false` → 즉시 비활성(`service.py:90-92`), `MEMORY_USE_MEM0_COMPAT=false` → `AgentMemory`(`VECTOR_STORE_BACKEND` 기본 `mongodb`, `EmbeddingManager.get_embedding` 사용). 저장 시 `infer=False`라 mem0의 LLM 사실 추출 호출은 없고, 저장·검색 각각 임베딩 호출 1회가 든다. 연구원의 기억 사용 조건은 R1-Q12 참조(유사도 `> 0.7`, `researcher.py:862`, `n_results=3`, 850-853).
- 조사 범위: `core/memory/` 전체(`memory_manager.py`, `service.py`, `config.py`, `mem0_mongodb_store.py`), `core/llm/embedding_manager.py`, `core/workflow/builder.py:960-1000, 1685-1745`, `core/agents/researcher.py:760-870`, `install/community_bootstrap.json`의 `system_configs`/`llm_providers`, `requirements.txt:42`/`pyproject.toml:37`(`mem0ai>=1.0.7`). grep 패턴: `MEMORY_USE_MEM0_COMPAT|MEM0_ENABLED|VECTOR_STORE_BACKEND|get_agent_memory|get_memory_service|default_embedding_model`.

#### R1-Q12 답변
- 결론: **확정**. 반성(reflection) LLM 호출은 세 곳에서 나가고, 기본(v2) 경로의 조건은 다음과 같다. (1) `analysis_lesson`: `bull_researcher_v2`/`bear_researcher_v2`가 `execute()`를 마칠 때마다 `self.memory`가 있으면 호출(연구 매니저 직후가 아님). (2) `debate_lesson`: `research_manager_v2`/`risk_manager_v2` 노드 실행 직후 1회씩(`builder.py`의 래퍼). (3) 연구원 내부 `_reflect_on_debate`는 호출처가 없는 죽은 코드. 어느 경우도 "깊이별 `memory_enabled`" 플래그로 막히지 않으며(그 플래그는 recall만 제어), 실제 LLM 호출은 `MemoryService`가 이미 초기화되어 `svc.available`일 때만 일어나고, 아니면 건너뛴다. 반성 1건은 LLM 1회(`achat`, 타임아웃 30초) + 임베딩 1회(저장, `infer=False`)이며, 노드 안에서 동기 블로킹으로 실행된다. **보고서 정정 필요**: `03-decision.md` 4-8의 "연구 매니저·리스크 매니저 직후 각 1회 가능"은 debate_lesson만 설명한 것이고 analysis_lesson이 bull/bear 실행마다 추가된다. 4-2-b 표의 "快速만 메모리 끔"은 기본 v2 경로가 아니라 `engine=unified`(`unified_analysis_service.py:317-323`)와 레거시 `simple_analysis_service.py:657-684`에만 해당한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/agents/researcher.py:222-225` | 연구원 실행 말미 | `# 6. 保存到记忆系统（如果有）` / `if self.memory:` / `self._save_to_memory(ticker, report, state=state)` (v3.5.0 项3 "同时触发反思提炼") | 코드 확인 |
  | `core/agents/researcher.py:346-389` | `_save_to_memory` | `success = self.memory.add_memory(content=content, metadata=metadata)` 후 `self._reflect_on_analysis(ticker, report, content, state=state)` | 코드 확인 |
  | `core/agents/researcher.py:394-475` | `_reflect_on_analysis` | `db = self._get_db_handle(state=state)`가 `None`이면 반환(446-448), `user_id = self._get_user_id(state=state) or "default_user"`, `run_reflection_sync(…, scope=MemoryScope.ANALYSIS_INSIGHT, memory_kind="analysis_lesson", …)`(453-458) | 코드 확인 |
  | `core/agents/researcher.py:477-540` | `_reflect_on_debate` | `run_reflection_sync(… memory_kind="debate_lesson" …)`(535). 이 메서드의 호출처는 저장소에 없음(`grep -rn "_reflect_on_debate"`: 정의 477행뿐) | 코드 확인 |
  | `core/agents/adapters/bull_researcher_v2.py:35`, `bear_researcher_v2.py:33` | 상속 | `class BullResearcherV2(ResearcherAgent):` / `class BearResearcherV2(ResearcherAgent):` — 둘 다 `execute` 재정의 없음 → 기반 `ResearcherAgent.execute`(80) 사용 | 코드 확인 |
  | `core/agents/adapters/risky_analyst_v2.py:306`, `safe_analyst_v2.py:306`, `neutral_analyst_v2.py:320`, `risk_self_debate_v2.py:305` | 리스크 분석가 | `def execute(self, state)` 재정의, `_save_to_memory`/`self.memory` 사용 없음(grep 0건) → `analysis_lesson` 없음 | 코드 확인 |
  | `core/workflow/builder.py:1095-1106, 162-168` | 매니저 래퍼 적용 | `if node.id in participant_debate_keys: …` / `elif _is_manager_agent(node.agent_id):` → `_create_manager_with_debate_reflection(node, debate_state_field=…)`; `_MANAGER_AGENT_PREFIXES = ("research_manager", "risk_manager")` | 코드 확인 |
  | `core/workflow/builder.py:2607-2650` | 래퍼 | `result = original_func(state)` 후 `_trigger_debate_reflection(state=state, result=result, debate_state_field=…, debate_type=…, agent_id=agent_id, node_id=node_id)`, 예외는 경고만 | 코드 확인 |
  | `core/workflow/builder.py:40-158` | `_trigger_debate_reflection` | 건너뛰는 조건: `debate_state`가 dict 아님(68-69), `if not debate_history and not conclusion:` (`"辩论历史和裁决均为空"`, 81-83), `db is None`(100-108), 빈 `user_prompt`(132-133). 조건을 통과하면 `run_reflection_sync(… scope=MemoryScope.AGENT_EXPERIENCE, memory_kind="debate_lesson" …)`(135-142). `memory_enabled`/`user_id` 유무로 막지 않음(`user_id`는 없으면 `"default_user"`) | 코드 확인 |
  | `core/agents/reflection_helper.py:160-163` | `run_reflection` 관문 | `svc = get_memory_service(db)` / `if not svc.available: logger.info("[Reflection] mem0 不可用，跳过反思节点…"); return False` (mem0 사용 불가면 반성 노드 건너뜀) — `core/memory/service.py:80-81`: `available`은 `self._mem is not None`으로 초기화를 시도하지 않음 | 코드 확인 |
  | `core/agents/reflection_helper.py:29, 165-201` | LLM 호출 | `_REFLECTION_LLM_TIMEOUT = 30`; `llm_client = _resolve_reflection_llm_client(db)`(시스템 설정의 `quick_analysis_model` → `deep_analysis_model` → 첫 활성 설정, 32-76); `None`이면 LLM 호출 없이 원문 저장으로 강등; 있으면 `resp = await asyncio.wait_for(llm_client.achat(messages), timeout=_REFLECTION_LLM_TIMEOUT)` (1회) | 코드 확인 |
  | `core/agents/reflection_helper.py:79-121, 218-225` | 동기/비동기 | `run_reflection_sync`: 이벤트 루프가 없으면 `asyncio.run`, 있으면 새 스레드에서 실행하고 `t.join(timeout=_REFLECTION_LLM_TIMEOUT + 10)`로 **대기**(백그라운드 방치 아님). 저장은 `svc.store(…, infer=False)`(LLM 사실추출 없음, 임베딩 1회) | 코드 확인 |
  | `core/agents/config.py:229`, `core/agents/researcher.py:841-844` | 깊이 플래그 | `memory_enabled: bool = True`(`AgentConfig` 기본). 연구원은 `memory_enabled = getattr(self.config, "memory_enabled", True)`가 거짓이면 `"记忆功能已禁用（快速分析模式）"`(메모리 기능 비활성) 후 **recall만** 반환 — 저장·반성 경로에는 이 검사가 없음 | 코드 확인 |
  | `core/api/workflow_api.py:979-1000` | 기본 v2 경로의 깊이 매핑 | `depth_mapping = {"快速": {"debate": 1, "risk": 1}, …}` → `prepared["_max_debate_rounds"]`, `["_max_risk_rounds"]`만 설정. `memory_enabled` 키 없음. `app/services/unified_analysis_engine.py`에도 `memory_enabled` 없음(grep 0건) | 코드 확인 |
  | `app/services/unified_analysis_service.py:317-323, 337` | 보고서가 인용한 맵 | `"快速": {"debate": 1, "risk": 1, "memory_enabled": False},  # 🔧 快速分析禁用记忆` … `"memory_enabled": depth_config["memory_enabled"]`. 이는 `UnifiedAnalysisService.analyze`(unified 엔진)에서만 `inputs`에 들어가며 사용처는 성장 메모리 recall(443, 541)뿐 | 코드 확인 |

- 동작 설명:
  1. 기본 경로의 노드: bull/bear는 `participant_debate_keys`에 속해 `_create_debate_participant_wrapper`로 감싸이고(`builder.py:1095-1097`), 실행되는 에이전트 객체는 기반 `ResearcherAgent.execute`를 쓴다. 매 호출마다 `self.memory`(`Mem0AgentMemory`, R1-Q11)가 있으면 `add_memory`(임베딩) → `_reflect_on_analysis`로 이어진다. bull/bear 호출 횟수는 `_max_debate_rounds × 참여자 2`(`builder.py:2973` `max_count = dynamic_rounds * _num_participants`)에 병렬 개국 노드 경로를 더한 만큼이며, 정확한 총수는 런타임 깊이 값에 달려 있다.
  2. `research_manager_v2`/`risk_manager_v2`는 `_is_manager_agent`가 참이라(`builder.py:1098`) 래퍼가 에이전트 실행 후 `_trigger_debate_reflection`을 1회 부른다.
  3. 두 경로 모두 `run_reflection_sync` → `run_reflection`: `svc.available`이 거짓이면 즉시 `False`로 건너뛴다. `available`은 같은 프로세스에서 앞선 `store`/`recall`이 `_ensure_init`을 성공시켰을 때만 참이다. analysis_lesson 경로는 직전 `add_memory`가 초기화를 시도하므로 mem0가 정상이면 곧바로 참이 된다. mem0 비활성 사유는 R1-Q11 4번(LLM 키 없음, `MEM0_ENABLED=false` 등).
  4. 통과하면 반성 LLM 1회(`quick_analysis_model` 기준, 30초 타임아웃, 초과/실패/비 JSON 시 원문 저장으로 강등) + `svc.store`(임베딩 1회). 즉 반성 1건당 LLM 호출 최대 1회, 임베딩 1회. 노드 실행 스레드에서 끝날 때까지(최대 약 40초) 블로킹한다.
  5. 환경변수·사용자 ID: `user_id`는 `state["user_id"]`가 없어도 `"default_user"`로 진행하므로 사용자 ID 유무는 조건이 아니다. `MEM0_ENABLED=false`면 `_ensure_init` 실패로 전부 건너뛴다. 딥 모드에서 `RISK_SELF_DEBATE`가 켜지면(`workflow_api.py:1004-1011`) 리스크 3인 대신 `risk_self_debate_v2`가 실행되지만 이 노드도 `analysis_lesson`을 만들지 않고 `risk_manager_v2` 래퍼의 `debate_lesson`만 남는다.
- 조사 범위: `core/agents/researcher.py`(`execute`, `_save_to_memory`, `_reflect_on_analysis`, `_reflect_on_debate`, `_get_memory_context`), `core/agents/reflection_helper.py` 전체, `core/workflow/builder.py:40-170, 1085-1110, 2485-2650, 2960-2995`, `core/agents/adapters/{bull,bear}_researcher_v2.py`, `risky/safe/neutral/risk_self_debate_v2.py`, `core/agents/manager.py:455-475`(`_save_to_memory`는 반성 호출 없음), `core/memory/service.py`, `core/api/workflow_api.py:979-1012`, `app/services/unified_analysis_engine.py`, `app/services/unified_analysis_service.py:310-340`. grep 패턴: `analysis_lesson|debate_lesson|run_reflection_sync|_reflect_on_|memory_enabled|_save_to_memory|reflection`(`core app tradingagents`, 테스트 제외).

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 해소 | `unified_analysis_engine.py:81-86`(우선순위 1 `task.task_params.get("workflow_id")`), `:99-104`(우선순위 2), `default_workflow_provider.py:221-235`(`is_default: True` 조회)를 열어 원문 일치 확인. 부트스트랩 JSON을 직접 파싱해 `data.workflows[9]`만 `stock_analysis`·`is_default: true`(id `6ede3bc3-…`, 2.0.5)이고 `[7] v2_stock_analysis`는 `false`, `data.system_configs[93].default_workflows.stock_analysis.workflow_id`도 `6ede3bc3-…`임을 확인. `community_bootstrap_service.py:119-122`(빈 컬렉션일 때만 `insert_many`), `SingleAnalysis.vue:1003, 2948-2959`(초기값 `'v2_stock_analysis'` → `is_default` 흐름으로 교체, 실패 시 유지) 확인. 완료 조건(4단계 각각의 반환값, 활성 ID 저장 위치, 부트스트랩 시드 값) 충족. 1차 보고서의 "사용자 설정에 달렸다"는 정정 대상 |
| R1-Q2 | 해소 | `builder.py:1032-1033`(`# 未知类型的分析师，保留` / `return True`), `:2910-2917`(END 간선은 JSON에 END 대상이 있을 때만, 나머지는 일반 `add_edge`), `:1185`(`return graph.compile()`, 보정 없음) 확인. JSON 파싱으로 `nodes[21]`이 `analyst_1783504388585`/`valuation_analyst_v1`이고 이 노드가 들어간 간선은 `parallel_analysts → analyst_1783504388585` 1개뿐임 확인. `valuation_report` grep 결과 `core/agents/config.py:936-946`, `builder.py:1603`, `binding_manager.py:539` 외 소비처 없음 확인. (a)(b)(c) 중 (c)로 코드상 확정되었고, 남은 "LangGraph `compile()`이 출구 없는 노드를 허용하는가"는 저장소 밖 라이브러리 동작이라 정적 확인 불가 부분으로 분리 기재된 점 수용 |
| R1-Q3 | 해소 | `binding_manager.py:150-160`(`not registry.has_tool(tool_id)` → `invalid_tools`, "检测到无效工具绑定，已自动忽略") 확인. JSON에서 `data.tool_agent_bindings[34]`가 `market_analyst_v2`/`mcp_tdx-mcp_get_stock_info`/priority 2이고 82건 모두 `workflow_id`·`node_id` 없음, 부트스트랩 키에 `mcp_server_configs` 없음 확인. `ls app` 결과 `pro` 없음, `main.py:330-336`이 `app.pro.services.mcp_service` import 확인. 사소한 표현 차이: `main.py`는 `except ImportError`가 아니라 `except Exception`으로 잡고 `logger.error`를 남긴다(결론에는 영향 없음) |
| R1-Q4 | 해소 | `builder.py:1692-1701`(`get_tools_for_node`), `factory.py:84-91`(`agent_class is None`일 때만 `_try_create_universal_agent`), `:243-246`(`if not resolved_tool_ids: … doc.get("default_tools")`) 확인. JSON에서 `valuation_analyst_v1` 바인딩 0건 확인. 완료 조건(생성→`bind_tools` 호출 순서, `default_tools` 읽기 위치 전수 분류) 충족 |
| R1-Q5 | 없음 확정 | `stock_fundamentals.py:118-160`(캐시 → Tushare `limit` → AKShare → `_sort_and_trim_records`, 날짜 인자 없음), `optimized_china_data.py:2230-2235`(`$or` 종목 키 + `sort=[('updated_at', -1)]`) 원문 일치 확인. 체인 각 단계의 조회 조건과 `ann_date|f_ann_date|as_of|analysis_date|…` grep 범위가 제시되어 조사 범위 충분. Tushare 동기화 쪽 `_pick_latest_disclosed_record`가 "오늘(UTC)" 기준이라 분석일 기준이 아니라는 구분도 명시됨 |
| R1-Q6 | 없음 확정 | 저장소 전체 grep 재실행: `_get_cached_sector_report`/`_save_sector_report_to_cache`/`SECTOR_REPORT_CACHE_TTL_HOURS`는 `sector_analyst_v2.py:21,60,90,109,147`와 레거시 `tradingagents/agents/analysts/sector_analyst.py:26,39,60,73`의 정의·자기 참조뿐, 호출처 0건 확인 |
| R1-Q7 | 없음 확정 | 저장소 전체 grep 재실행: `IM_TOPIC_DIGEST`는 `app/core/config.py:282-285` 4줄, `IMTopicDigestService`는 정의 파일과 `tests/unit/app/test_im_topic_digest_service.py:3,35`뿐 확인. 패턴 변형(`topic_digest`, `digest`, `settings\.IM_`)과 범위(`app/ core/ tradingagents/ cli/ scripts/ install/`) 충분 |
| R1-Q8 | 없음 확정 | grep 재실행: `format_analysis_result` 외부 호출은 `unified_analysis_service.py:590,607`뿐, `format_decision(` 호출은 `report_formatter.py:1307`뿐 확인. `analysis_worker.py:746`(`parameters_dict.get("engine", "v2")`), `:818`(`if engine_type == "v2":`), `:846`(`elif engine_type == "unified":`) 확인. 기본 v2 경로에서 도달 불가가 호출 체인으로 제시됨. `SignalProcessor` 실제 호출 조건 정정(`reasoning`/`rationale` 부재 + 길이 > 50)도 보고서 반영 대상 |
| R1-Q9 | 해소 | `core/agents/manager.py:317-340` 원문(`from app.pro.models.agent_assertion import AssertionRunResult` / `except ImportError:` → `SimpleNamespace(ran=False, violations=[], …)`) 확인, `app/pro` 부재와 부트스트랩 `data` 키 13개에 `agent_assertions` 없음 확인. 쓰기 위치 없음(grep 범위 제시) + 비어 있을 때 코드 기본 단언 대체 없음(`assertion_executor.py:88-91`) + 플래그 기본값 모두 충족. "단언은 커뮤니티판에서 비활성"이라는 1차 보고서 정정 사항 확정 |
| R1-Q10 | 없음 확정 | 저장소 전체 grep 재실행: `weight_calculator`/`calculate_report_weights`/`format_weighted_reports_prompt`는 `core/agents/utils/__init__.py:5-12` 재export 외 0건 확인. `.json`/`.yaml`/부트스트랩·동적 import 범위 포함 |
| R1-Q11 | 해소 | `memory_manager.py:589`(`MEMORY_USE_MEM0_COMPAT` 기본 `"true"`), `service.py:86-112`(`MEM0_ENABLED`, `if not resolved_config…get("api_key"): self._init_error = "缺少 LLM API Key，mem0 记忆层不可用"`) 원문 확인, JSON에서 `default_embedding_model = "dashscope:text-embedding-v4"` 확인. 완료 조건(구현체 선택 분기·기본값, 임베딩 기본 모델, 실패 분기) 충족. 다만 mem0 LLM 키를 해석하는 `get_system_llm_config_from_config_doc`(`app/services/intelligent_assistant_service.py:1736`)와 임베더 키(`config.py:332`)가 DB 문서만 보는지, 분석 LLM처럼 환경변수 키로 폴백하는지는 추적되지 않았다. "키를 넣고 분석이 돌면 메모리·반성도 켜지는가"를 정하는 정적 사실이므로 → R2-Q1 신규 |
| R1-Q12 | 해소 | `researcher.py:222-225`(`if self.memory:` → `_save_to_memory`), `:841-844`(`memory_enabled`은 recall만 차단), `reflection_helper.py:160-163`(`if not svc.available: … 跳过反思节点`), `builder.py:81-83`, `:1095-1106`(매니저 래퍼) 원문 확인. `_reflect_on_debate` grep 결과 정의(477)뿐, `workflow_api.py`·`unified_analysis_engine.py`에 `memory_enabled` 0건 확인. 노드·조건·기본값·1건당 호출 수(LLM 1 + 임베딩 1) 모두 제시됨. 1차 보고서 4-8, 4-2-b 정정 대상 |

---

## Round 2

### 질문 (질문자)

#### R2-Q1. mem0 LLM·임베더 API 키는 분석 LLM과 같은 경로로 해석되는가
- GUIDE 항목: Q4-7 (메모리), Q4-8 (비용)
- 왜 묻는가: R1-Q11 답변은 "mem0 LLM 설정의 `api_key`가 비면 `_init_error`로 영구 비활성"(`core/memory/service.py:110-112`)과 "키는 설치 후 系统设置에서 입력"까지만 확인했다. 그런데 mem0 LLM 키는 `core/memory/config.py:537-544`에서 `get_system_llm_config_from_config_doc`(`app/services/intelligent_assistant_service.py:1736`)로, 임베더 키는 `config.py:332`의 `provider_doc.get("api_key")`로 해석되며, 이 두 경로가 DB 문서만 보는지 환경변수(`.env`의 `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY` 등)로 폴백하는지가 추적되지 않았다. 분석 LLM이 환경변수 키로 정상 동작하는 설치에서 mem0만 꺼져 있다면, R1-Q11·R1-Q12의 "메모리 저장·반성 호출"은 그런 설치에서 0회가 되고 `03-decision.md` 4-7·4-8 정정 문구가 달라진다.
- 질문: 분석 노드의 LLM이 쓰는 API 키 해석 경로(빌더가 에이전트 LLM을 만들 때 키를 읽는 함수)와, mem0의 LLM 키(`get_system_llm_config_from_config_doc` → `_build_mem0_llm_config_from_unified_config`) 및 임베더 키(`config.py:315-352` 이하) 해석 경로는 같은 소스(DB `llm_providers`/`system_configs` 및 환경변수 폴백 여부)를 쓰는가? 다르다면 "분석 LLM은 동작하지만 mem0는 `_init_error`로 꺼지는" 설정 조합이 존재하는가?
- 답변 완료 조건: (1) 분석 에이전트 LLM 키 해석 함수와 (2) mem0 LLM 키, (3) mem0 임베더 키 해석 함수 각각의 `파일:라인`과 키를 읽는 원문(DB 필드명, `os.getenv`/`os.environ` 키 이름, 우선순위). 세 경로의 소스를 표로 비교하고, 서로 다르면 어긋나는 구체적 설정 조합 1개 이상을 코드 근거로 제시. 환경변수 폴백이 없으면 `os.getenv|os.environ|_API_KEY` grep 범위를 조사 범위에 적는다.

### 답변 (답변자)

#### R2-Q1 답변
- 결론: **확정**. 세 경로는 소스가 같지 않다. (1) 분석 LLM 키와 (2) mem0 LLM 키는 같은 함수 `get_provider_and_url_by_model_sync`(`app/services/simple_analysis_service.py:168`)로 수렴하므로 "DB 厂家(provider) 키 → DB 모델 키 → 환경변수" 순서와 9개 제공자 환경변수 맵을 공유한다. 그러나 분석 LLM은 그 뒤에 `create_llm_by_provider`(`tradingagents/graph/trading_graph.py:158`)에서 한 번 더 환경변수로 폴백하지만 mem0 LLM 경로에는 이 2차 폴백이 없다. (3) mem0 임베더 키는 DB `llm_providers` 문서의 `api_key`만 읽고 환경변수 폴백이 전혀 없다. 따라서 "분석은 돌지만 mem0는 `_init_error`로 꺼지는" 조합이 코드상 존재한다(아래 조합 A, B). **보고서 정정 필요**: R1-Q11 답변 동작 설명 4번의 "키 입력"은 DB(系统设置) 입력만이 아니라 환경변수(`DASHSCOPE_API_KEY` 등)도 mem0 LLM 관문(`service.py:110`)은 통과시킨다. 다만 임베더는 환경변수로 통과하지 못한다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `core/workflow/builder.py:348-350, 360-366` | 분석 LLM 키 해석 (기본 경로) | `quick_config = get_provider_and_url_by_model_sync(quick_model)` / `deep_config = get_provider_and_url_by_model_sync(deep_model)`; `quick_api_key = quick_api_key_from_config or quick_api_key_from_db`; `deep_api_key = deep_api_key_from_config or deep_api_key_from_db or quick_api_key` (사용자 명시 `self._config["quick_api_key"/"api_key"]` > DB 해석 결과). 개별 LLM 경로도 동일(`builder.py:471-480`) | 코드 확인 |
  | `app/services/simple_analysis_service.py:237-243` | 1순위: DB 厂家 키 | `if provider_doc and provider_doc.get("api_key"):` … `if is_valid_api_key(provider_api_key): api_key = provider_api_key.strip()` ("厂家配置", `llm_providers.find_one({"name": provider})`) | 코드 확인 |
  | `simple_analysis_service.py:249-253` | 2순위: DB 모델 키 | `if not api_key:` … `if is_valid_api_key(model_api_key): api_key = model_api_key.strip()` ("模型配置", `llm_configs[].api_key`) | 코드 확인 |
  | `simple_analysis_service.py:256-259` | 3순위: 환경변수 | `if not api_key:` / `env_api_key = _get_env_api_key_for_provider(provider)` / `api_key_source = "环境变量"` (환경변수) | 코드 확인 |
  | `simple_analysis_service.py:441-451, 455-459` | 환경변수 맵 | `"google": "GOOGLE_API_KEY"`, `"dashscope": "DASHSCOPE_API_KEY"`, `"openai": "OPENAI_API_KEY"`, `"deepseek": "DEEPSEEK_API_KEY"`, `"anthropic": "ANTHROPIC_API_KEY"`, `"openrouter": "OPENROUTER_API_KEY"`, `"siliconflow": "SILICONFLOW_API_KEY"`, `"qianfan": "QIANFAN_API_KEY"`, `"302ai": "AI302_API_KEY"` — 9개뿐(zhipu, aihubmix, kimi, xiaomi, volcengine 없음). `is_valid_api_key`는 길이 5 미만, `your_`/`your-` 접두, `_here`/`-here` 접미, `...` 포함이면 무효(`app/utils/api_key_utils.py:11-51`) | 코드 확인 |
  | `app/services/intelligent_assistant_service.py:1736-1766, 1676-1730` | mem0 LLM 키 해석 | `get_system_llm_config_from_config_doc(config_doc, *, model_keys)`: `if not config_doc or "llm_configs" not in config_doc: return None` → `quick_analysis_model`, `deep_analysis_model` 순으로 `resolve_llm_config_from_config_doc` → 거기서 `provider_info = get_provider_and_url_by_model_sync(resolved_model_name, preferred_provider=…, preferred_config_id=…)`(1701) → `LLMConfig(…, api_key=provider_info.get("api_key"), base_url=provider_info.get("backend_url"), …)`(1728). 즉 분석 LLM과 **같은 함수**를 같은 우선순위로 호출 | 코드 확인 |
  | `core/memory/config.py:537-544, 556-565` | mem0 LLM 구성 | `resolved_llm_config = get_system_llm_config_from_config_doc(config_doc, model_keys=["quick_analysis_model", "deep_analysis_model"])` → `_build_mem0_llm_config_from_unified_config`(355-): `api_key = str(getattr(llm_config, "api_key", "") or "").strip()`. 해석 실패(`None`)면 `llm = {"provider": "openai", "config": {"api_key": "", …}}`(562, 빈 키). 이 경로에는 자체 `os.getenv`가 없음 | 코드 확인 |
  | `core/memory/service.py:109-112` | LLM 키 관문 | `resolved_config = config or build_mem0_config(self._db)` / `if not resolved_config.get("llm", {}).get("config", {}).get("api_key"):` / `self._init_error = "缺少 LLM API Key，mem0 记忆层不可用"` | 코드 확인 |
  | `tradingagents/graph/trading_graph.py:232, 267, 288-299` | 분석 LLM의 2차 환경변수 폴백 | `dashscope_api_key = api_key or os.getenv('DASHSCOPE_API_KEY')`; `zhipu_api_key = api_key or os.getenv('ZHIPU_API_KEY')`; `if provider.lower() == "siliconflow": api_key = os.getenv('SILICONFLOW_API_KEY')` … `elif provider.lower() == "aihubmix": api_key = os.getenv('AIHUBMIX_API_KEY')` (그 외 google 213, deepseek 249도 `api_key or os.getenv(...)`). 독스트링: "api_key: API Key（可选，如果未提供则从环境变量读取）". `builder.py:370`의 로그도 "未配置（将使用环境变量）" | 코드 확인 |
  | `core/memory/config.py:294-305, 315-352` | mem0 임베더 키 | 후보: `sync_db.llm_providers.find({"supported_features": "embedding", "is_active": True}).sort("created_at", 1)`; 키: `api_key = str(provider_doc.get("api_key") or "").strip()`(332); `if mem0_provider == "openai": if not api_key: return {}`(335-337), `gemini`도 동일(340-342), `elif mem0_provider == "ollama": config["ollama_base_url"] = base_url or "http://localhost:11434"`(346-347, 키 불필요). 함수 안에 `os.getenv`/`os.environ` 없음, `is_valid_api_key`도 쓰지 않음 | 코드 확인 |
  | `core/memory/config.py:391-433` | 임베더 폴백 순서 | 선호 제공자(`default_embedding_model`의 앞부분) → 실패 시 `for provider_doc in provider_docs:`(422) `created_at` 순으로 다른 제공자 시도(`embedder = _build_embedder_config_from_provider_doc(provider_doc, "")`, 426) → 전부 `{}`이면 `return {}` | 코드 확인 |
  | `core/memory/service.py:31-48, 115-118` | 임베더 관문 | `_validate_embedder_config`: provider 없음 → "缺少可用的 Embedding 配置"; `openai/gemini/azure_openai/together`는 `api_key` 비면 "…缺少 API Key"; `ollama`는 키 검사 없음 → 통과. 실패 시 `self._init_error = f"{embedder_error}，mem0 记忆层不可用"` (영구) | 코드 확인 |
  | `install/community_bootstrap.json` `data.llm_providers[*]` | 부트스트랩 厂家 | 모든 제공자 `api_key: ""`. 임베딩 지원 + `is_active: true`: google(`created_at` 2025-08-18T08:56:05.451), dashscope(…456), siliconflow(2025-10-23), **ollama**(2026-01-16), zhipu, xiaomi, kimi, aihubmix. `system_configs[93].system_settings`: `quick_analysis_model: "qwen-plus"`, `deep_analysis_model: "deepseek-v4-flash"`, `default_provider: "dashscope"`, `default_embedding_model: "dashscope:text-embedding-v4"` | JSON 확인 |
  | `app/services/community_bootstrap_service.py:30-34` | 비밀 필드 제거 | `"api_key", "apikey", "api_secret", "secret",` 등을 `_sanitize`에서 비움. 환경변수를 DB 厂家 문서로 복사하는 코드는 이 서비스에 없음 | 코드 확인 |

- 세 경로 비교:

  | 항목 | (1) 분석 에이전트 LLM | (2) mem0 LLM | (3) mem0 임베더 |
  |---|---|---|---|
  | 진입 함수 | `builder.py:348-350` → `create_llm_by_provider` (`trading_graph.py:158`) | `config.py:537-544` → `intelligent_assistant_service.py:1736` | `config.py:391` `_resolve_embedding_from_db` → `:315` |
  | 모델 선택 | 요청의 `quick_think_llm`/`deep_think_llm` 또는 DB 기본 | 시스템 설정 `quick_analysis_model` → `deep_analysis_model` → 첫 enabled `llm_configs` | `default_embedding_model`(`"제공자:모델"`) → 다른 활성 임베딩 제공자 |
  | DB 소스 | `llm_providers[name].api_key` → `llm_configs[].api_key` | 동일(같은 `get_provider_and_url_by_model_sync`) | `llm_providers[name].api_key`만 |
  | 환경변수 폴백 | 있음: 1차 `_get_env_api_key_for_provider`(9개 제공자, `simple_analysis_service.py:441-451`) + 2차 `create_llm_by_provider`의 `os.getenv`(zhipu `ZHIPU_API_KEY`, aihubmix `AIHUBMIX_API_KEY`, `OPENAI_API_KEY` 등) | 1차만 있음(위 9개). 2차 없음 | 없음 |
  | 키 없을 때 | `ValueError`(예: `trading_graph.py:268`) 또는 키 없는 호출 | `api_key` 빈 문자열 → `service.py:110`에서 `_init_error` | openai 호환/gemini는 `{}` 반환 → 폴백 순회, 마지막에 ollama(키 불필요) 아니면 `_validate_embedder_config` 실패 |

- 어긋나는 설정 조합 (코드 근거):
  - **조합 A (zhipu 환경변수 전용)**: `quick_analysis_model`이 zhipu 모델이고 DB 厂家/모델 키는 비어 있으며 `ZHIPU_API_KEY`만 설정. 분석 LLM: `get_provider_and_url_by_model_sync`가 `_get_env_api_key_for_provider("zhipu")` → 맵에 없어 `None`을 돌려주지만(`simple_analysis_service.py:441-461`), `create_llm_by_provider`가 `api_key or os.getenv('ZHIPU_API_KEY')`(`trading_graph.py:267`)로 구제해 동작한다. mem0 LLM: 같은 `None`이 `LLMConfig.api_key`로 들어가 `""`가 되어 `service.py:110`에서 `_init_error`(영구). aihubmix도 같은 구조(`trading_graph.py:293-294` vs 맵에 없음).
  - **조합 B (기본 부트스트랩 + `DASHSCOPE_API_KEY` 환경변수만)**: 분석 LLM 동작(`quick_analysis_model: "qwen-plus"`, dashscope 厂家 키 `""` → 환경변수 3순위). mem0 LLM 키도 환경변수에서 얻어 `service.py:110`을 통과한다. 임베더는 DB 키가 없어 dashscope(선호)·google·siliconflow가 모두 `{}`이고 `created_at` 순서상 `ollama` 문서(키 불필요)가 폴백으로 선택되어(`config.py:346-347`) `_validate_embedder_config`도 통과한다. 즉 초기화는 성공하지만 임베더가 로컬 `http://localhost:11434`의 `nomic-embed-text`를 가리키므로, Ollama 서버가 없으면 저장·검색 시 임베딩 호출이 실패한다(R1-Q11 동작 3번, 경고 후 `False`/`[]`). `ollama` 厂家 문서를 비활성으로 바꾸거나 삭제한 설치에서는 `_init_error`("缺少可用的 Embedding 配置")로 영구 비활성이다.
  - **조합 C (`llm_configs` 없음)**: `system_configs` 문서에 `llm_configs`가 없으면 `get_system_llm_config_from_config_doc`가 `None`(`intelligent_assistant_service.py:1745-1746`) → mem0는 빈 키 LLM(`config.py:562`) → 비활성. 분석 LLM 경로는 모델 기본 매핑 + 환경변수로 계속 동작한다(`simple_analysis_service.py:355-358, 409-412`).
  - 반대로 환경변수가 아니라 DB에 DashScope 키를 넣으면 LLM·임베더(`dashscope:text-embedding-v4`) 모두 통과한다. 이것이 R1-Q11이 추적한 "키 입력 후 활성" 경로다.
- 영향(R1-Q11·Q12, `03-decision.md` 4-7·4-8): "키를 넣고 분석이 돌면 메모리·반성도 켜진다"는 항상 참이 아니다. DB에 키를 넣으면 켜지고, 환경변수만 쓰면 mem0 LLM 관문은 9개 제공자 한정으로 통과하나 임베더는 Ollama 폴백으로 흘러 실제 임베딩 성공 여부는 로컬 Ollama 존재에 달린다.
- 정적으로 남는 것(별도 사실): 임베더가 `ollama`로 선택됐을 때 mem0 라이브러리(`mem0ai`, 레포 밖)의 Ollama 임베더가 생성 시점에 서버 연결을 확인하는지, 첫 호출에서 실패하는지는 이 레포 코드로는 확인되지 않는다(외부 패키지 동작, `requirements.txt:42`의 `mem0ai>=1.0.7`). 어느 쪽이든 서버가 없으면 저장·검색은 성공하지 못한다(`add_memory`/`search_memories`는 예외를 `logger.warning`으로 삼키고 `False`/`[]`, R1-Q11 근거 `memory_manager.py:109-185`).
- 조사 범위: `core/memory/config.py`(1-583 전체: 21-47 상수, 218-255, 294-352, 355-388, 391-433, 437-583), `core/memory/service.py`(31-130), `app/services/intelligent_assistant_service.py`(1485-1580, 1640-1780), `app/services/simple_analysis_service.py`(168-462), `app/utils/api_key_utils.py`, `core/workflow/builder.py`(301-440, 443-530, 545-640), `tradingagents/graph/trading_graph.py`(158-300), `app/services/community_bootstrap_service.py`(30-60), `install/community_bootstrap.json`(`llm_providers`, `system_configs[93]`). grep 패턴: `get_provider_and_url_by_model_sync`, `_get_env_api_key_for_provider`, `_get_env_api_key`, `os.getenv|os.environ`(`core/memory/config.py`에서는 jdyun 모드 외 환경변수 키 읽기 없음; `core/memory/service.py`에서는 `MEM0_ENABLED`와 mem0 초기화용 `OPENAI_API_KEY` 등 백업/설정만), `api_key`. 참고: 별도 경로인 `core/llm/embedding_manager.py`(레거시 `AgentMemory` 경로)는 `os.getenv(config["env_key"])`(346), `EMBEDDING_API_KEY`/`OPENAI_API_KEY`(157-158) 폴백이 있으나 mem0 경로(`config.py`)는 이 파일에서 차원 표(`EMBEDDING_DIMENSIONS`)만 가져다 쓴다(`config.py:258-272`). 京东云 모드(`is_jdyun_mode()`, `config.py:450`)는 `get_jdyun_api_key()` 환경변수로 LLM·임베더 키를 동시에 채우므로 이 모드에서는 세 경로 모두 환경변수 기반이다(별도 분기, 기본 아님).

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R2-Q1 | 해소 | 고정 SHA(`51060a7`)에서 직접 확인. (1) 분석 LLM: `core/workflow/builder.py:348-350`(`get_provider_and_url_by_model_sync(quick_model)`), `:359`(주석 "用户显式指定 > 数据库配置 > 环境变量（在 create_llm_by_provider 中处理）"), `:413, 425`(`create_llm_by_provider` 호출), `tradingagents/graph/trading_graph.py:267`(`api_key or os.getenv('ZHIPU_API_KEY')`), `:288-296`(`siliconflow`/`openrouter`/`aihubmix`/`openai`/`jdyun` 별 `os.getenv`) 원문 일치. (2) mem0 LLM: `simple_analysis_service.py:237-260`(厂家 키 → 모델 키 → `_get_env_api_key_for_provider`), `:441-461`(환경변수 맵 9개, zhipu·aihubmix·kimi·xiaomi 없음), `intelligent_assistant_service.py:1745-1746`(`llm_configs` 없으면 `None`), `core/memory/config.py:537-544, 556-565`(실패 시 `api_key: ""`), `core/memory/service.py:109-112`(빈 키면 `_init_error`) 원문 일치. 즉 "2차 `os.getenv` 폴백은 분석 LLM의 `create_llm_by_provider`에만 있다"는 주장 맞음. (3) 임베더: `config.py:315-352`에서 키는 `provider_doc.get("api_key")`(332)만 읽고, `config.py`·`service.py`의 `os.environ` 사용처를 grep해 보니 `_env`(177, MongoDB 접속값 전용)·`MEM0_ENABLED`(service 52)·mem0 초기화용 환경변수 백업/주입(service 120-151, 이미 해석된 키를 `OPENAI_API_KEY`로 **쓰는** 쪽)뿐이라 임베더 환경변수 폴백 없음 확인. `config.py:391-433`(선호 제공자 → `created_at` 순 순회), `service.py:31-48`(`ollama`는 키 검사 없음) 확인. 부트스트랩 JSON을 직접 파싱해 임베딩 지원 제공자 순서 openai(`is_active: false`) → google → dashscope → siliconflow → **ollama**(2026-01-16, `embedding_model: "nomic-embed-text"`) → zhipu…, 모두 `api_key: ""` 확인 → 조합 B(환경변수만 쓰면 임베더가 ollama로 폴백) 코드상 성립. 사소한 차이 2건(결론 영향 없음): ① `intelligent_assistant_service.py:1700-1702`의 호출은 `get_provider_and_url_by_model_sync(resolved_model_name,)`로 `preferred_provider`/`preferred_config_id` 인자를 넘기지 않는다. ② ollama 문서에 `default_base_url: "http://localhost:11434/v1"`이 있으므로 조합 B의 실제 `ollama_base_url`은 기본값 `http://localhost:11434`가 아니라 이 값(`/v1` 포함)이다. mem0 라이브러리의 Ollama 연결 시점 확인은 레포 밖 동작이며 레포 쪽 경로(저장·검색 실패 시 경고 후 `False`/`[]`)는 R1-Q11에서 추적 완료라 외부 의존 잔여로 수용. 완료 조건(세 경로의 `파일:라인`·원문·우선순위, 비교 표, 어긋나는 조합 1개 이상, grep 범위) 충족. 새 질문 없음 |

---

## 최종 정리 (질문자)

- 총 라운드: 2 / 총 질문: 13 / 해소 8 · 없음 확정 5 · 정적 확인 불가 0 (미해결 0)
  - 해소: R1-Q1, Q2, Q3, Q4, Q9, Q11, Q12, R2-Q1 / 없음 확정: R1-Q5, Q6, Q7, Q8, Q10
  - 부분 외부 의존 잔여(종료 상태로 수용): LangGraph `compile()`의 출구 없는 노드 허용 여부(R1-Q2), mem0 Ollama 임베더의 연결 확인 시점(R2-Q1)
- 이 레포를 이해하는 데 핵심인 확정 사실:
  1. **기본 설치의 단일 종목 분석 워크플로는 DB 워크플로 `6ede3bc3-66e3-4204-a304-dcbe8b327258`(v2.0.5)이다.** 코드 템플릿 `v2_stock_analysis`는 DB 연결·UI 조회 실패 때만 쓰는 대체 경로다. (`unified_analysis_engine.py:81-86, 99-104`, `default_workflow_provider.py:221-235`, `install/community_bootstrap.json` `workflows[9]`·`system_configs[93]`) — R1-Q1
  2. **`valuation_analyst_v1` 노드는 합류 간선 없는 말단 노드로 그래프에 들어가고, 산출물 `valuation_report`는 하류 에이전트가 읽지 않는다.** (`builder.py:1032-1033, 2910-2917, 1185`) — R1-Q2
  3. **시장 분석가의 `mcp_tdx-mcp_get_stock_info` 바인딩은 `app/pro` 부재로 "无效工具绑定"이 되어 기본 설치에서 호출되지 않는다.** (`binding_manager.py:150-160`, `main.py:330-336`) — R1-Q3
  4. **재무 데이터 조회에는 공시일/분석일 기준 look-ahead 필터가 없다.** 최신 레코드를 `updated_at` 역순으로 가져온다. (`stock_fundamentals.py:118-160`, `optimized_china_data.py:2230-2235`) — R1-Q5
  5. **기본 v2 경로에는 `format_decision` → `SignalProcessor` 재추출 LLM 호출이 없다.** `engine=unified`일 때만 실행된다. (`analysis_worker.py:746, 818, 846`, `unified_analysis_service.py:590, 607`) — R1-Q8
  6. **`agent_assertions` 규칙 단언은 커뮤니티판에서 항상 건너뛴다.** `app.pro` import 실패 → `ran=False`. (`core/agents/manager.py:317-340`) — R1-Q9
  7. **분석가 신호의 코드 가중 합산(`weight_calculator.py`)은 운영 경로에 없다.** 최종 판단은 LLM만 한다. (`core/agents/utils/__init__.py:5-12` 재export 외 참조 0건) — R1-Q10
  8. **에이전트 메모리 기본 구현은 mem0 + 커스텀 MongoDB 벡터 저장소이며, LLM 키나 임베딩 구성이 없으면 `_init_error`로 영구 비활성(조용히 무동작)이다.** (`memory_manager.py:589`, `core/memory/service.py:31-48, 109-118`) — R1-Q11
  9. **반성 LLM 호출은 bull/bear 실행마다(`analysis_lesson`)와 연구·리스크 매니저 직후(`debate_lesson`)에 일어나며 `svc.available`일 때만 실행된다.** `memory_enabled`는 recall만 막는다. (`researcher.py:222-225, 841-844`, `reflection_helper.py:160-163`, `builder.py:1095-1106`) — R1-Q12
  10. **API 키 해석은 경로마다 다르다.** 분석 LLM은 DB 厂家 → DB 모델 → 환경변수(9개 맵) → `create_llm_by_provider`의 2차 `os.getenv` 폴백까지 있다. mem0 LLM은 1차 환경변수까지만, mem0 임베더는 DB `llm_providers.api_key`만 읽는다. 그래서 환경변수만 쓰는 설치에서는 분석은 돌아도 mem0가 꺼지거나(zhipu/aihubmix) 임베더가 로컬 Ollama로 폴백한다. (`simple_analysis_service.py:237-260, 441-461`, `trading_graph.py:267, 288-296`, `core/memory/config.py:315-352, 391-433`) — R2-Q1

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `03-decision.md` 4-2-a 첫 글머리, `next.md` 미확인 1번·"분석 중 생긴 질문" 1번 | 운영에서 어느 워크플로가 선택되는지는 사용자 설정에 달렸다 | 기본 설치는 DB 워크플로 `6ede3bc3-…`(v2.0.5)가 실행된다(UI가 `workflow_id`로 명시 전송, ID 없으면 DB `is_default`). 코드 템플릿은 DB·UI 조회 실패 시 대체 경로 | R1-Q1 |
| `01-data.md` 1-2 | `valuation_analyst_v1`은 고아 노드로 보인다 (추론) | 합류 간선이 없는 말단 노드(코드 확인). `valuation_report`는 하류 에이전트가 읽지 않고 최종 보고서 필드에만 포함 | R1-Q2 |
| `01-data.md` 1-0 표 (활성 바인딩) | `mcp_tdx-mcp_get_stock_info`를 활성 바인딩으로 기재 | `app/pro` 부재로 무효 바인딩 처리되어 기본 설치에서 동작하지 않는 항목 | R1-Q3 |
| `01-data.md` 2-4 "섹터 보고서 캐시" 행 | 주석과 코드가 상충 (추론) | 읽기·쓰기 함수 호출처 0건, 미사용 확정 | R1-Q6 |
| `03-decision.md` 4-6 | 운영 경로 호출 여부는 미확인 | 기본(v2) 경로에서 호출 없음, `engine=unified`일 때만 | R1-Q8 |
| `03-decision.md` 4-3-b "용어 사전" 행 | 결정 필드 부재 시 `SignalProcessor` 호출 | 실제 조건은 `decision_raw`에 `reasoning`/`rationale`이 없고 `fallback_text` 길이 > 50 | R1-Q8 |
| `03-decision.md` 4-5 "규칙 기반 단언" 행 | 시드가 비어 있음은 추론 | Pro 전용 모듈(`app.pro`) 부재로 항상 건너뜀(코드 확정). `AGENT_ASSERTION_ENABLED` 기본 `True`는 의미 없음 | R1-Q9 |
| `next.md` 미확인 4번 | 벡터 메모리 후보 chromadb/mongodb vector/qdrant | 기본은 mem0 + 커스텀 MongoDB 벡터 저장소(`MEMORY_USE_MEM0_COMPAT` 기본 `true`). ChromaDB/Qdrant는 `false`일 때의 레거시 경로 | R1-Q11 |
| `03-decision.md` 4-8 | 연구 매니저·리스크 매니저 직후 각 1회 반성 가능 | `debate_lesson`(매니저 직후 각 1회)에 더해 `analysis_lesson`이 bull/bear 실행마다 추가. 모두 `MemoryService.available`일 때만 실행, 1건 = LLM 1회 + 임베딩 1회 | R1-Q12 |
| `03-decision.md` 4-2-b 표 | 快速 깊이에서만 메모리 끔 | `memory_enabled`는 recall만 막고, 이 분기는 기본 v2 경로가 아니라 `engine=unified`와 레거시 `simple_analysis_service.py`에만 해당 | R1-Q12 |
| `03-decision.md` 4-7·4-8 (메모리 활성 조건) | 키를 넣으면 메모리·반성이 켜진다 (R1-Q11 기준 "系统设置에서 키 입력") | DB에 키를 넣으면 LLM·임베더 모두 켜진다. 환경변수만 쓰면 mem0 LLM은 9개 제공자(dashscope·deepseek 등)에 한해 통과하고 zhipu·aihubmix는 꺼진다. 임베더는 환경변수를 읽지 않아 부트스트랩 기본값에서는 로컬 Ollama(`http://localhost:11434/v1`, `nomic-embed-text`)로 폴백하므로, Ollama가 없으면 저장·검색이 조용히 실패한다 | R2-Q1 |
