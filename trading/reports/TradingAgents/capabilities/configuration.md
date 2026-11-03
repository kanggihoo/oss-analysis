---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/__init__.py
  - tradingagents/default_config.py
  - tradingagents/dataflows/config.py
  - tradingagents/llm_clients/factory.py
  - tradingagents/agents/context.py
  - tradingagents/graph/trading_graph.py
  - tradingagents/llm_clients/base_client.py
  - tradingagents/llm_clients/openai_client.py
depends: []
status: ready
---

# 실행 설정·모델 계층

> 기본값·환경변수·실행별 데이터 설정과 quick/deep 모델 공급자 선택 계약을 제공한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 패키지 import 때 작업 디렉터리에서 찾은 .env, .env.enterprise를 순서대로 읽도록 dotenv를 호출한 뒤 기본 설정 map에 대응 환경변수를 적용한다. 이미 설정된 환경값은 덮어쓰지 않는다.
2. 호출자가 config 또는 기본값으로 그래프를 생성한다.
3. dataflow 전역 설정은 기본값 위에 한 단계 병합한다. 실행 구간에서는 graph 설정이 우선한다.
4. 각 모델 계층은 전용 provider/endpoint가 있으면 선택하고 모델 인자를 만든다.
5. 공급자 어댑터에서 get_llm으로 모델을 받아 역할에 전달한다.
6. 언어 지시를 prompt에 붙이되 기계가 읽는 등급·거래제안 라벨은 영어를 유지한다.

### 1.2 범위·통합 지점

- 제공: 기본값·환경변수·설정 병합/격리·계층 선택·factory 전달 인자·언어 지시.
- 제외: 개별 공급자 SDK wire-format·키 인증·모델 카탈로그 내부는 외부 어댑터 경계. 로그인 수명주기는 부속 행16이며 승인 범위 밖. 이 스펙은 모든 SDK 어댑터의 독립 재구현을 약속하지 않는다.
- 외부 경계: provider/model/base_url/kwargs를 받는 client 생성기와 get_llm()이 필요. 반환 모델은 invoke·bind_tools·with_structured_output을 제공하며 unsupported 구조화는 S2에 맞게 실패한다. 어댑터 생성·get_llm 예외는 이 계층이 잡지 않는다. 실제 모델 존재·인증·서버 호환성은 미확인.
- 소유 상태: import 시 DEFAULT_CONFIG, process 전역 dataflow 설정, ContextVar 실행 설정. 그래프는 config를 복사·병합하지 않고 참조한다. 생성 시 cache/results 디렉터리 생성·client 생성·메모리 초기화 부작용이 있다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| build_default_config / DEFAULT_CONFIG | 환경 → map | 매 호출 새 기본 map. import에 한 번 생성된 DEFAULT_CONFIG는 환경이 바뀌어도 자동 갱신하지 않음 |
| graph config | optional map | config or DEFAULT_CONFIG. 빈 map은 기본값 사용; nonempty partial map은 graph가 보충하지 않아 필수 키 누락 시 KeyError 가능 |
| 기본값·환경변수 | C-01·C-02의 정확한 키/값 | openai, deep gpt-6-sol, quick gpt-6-luna, 토론1/리스크1/도구20/재귀100, checkpoint false, English. 그 외 기본값은 C-02 그대로 |
| dataflow set_config/run_config/get_config | map → context / 복사 map | dict값은 한 단계 update; scalar는 치환. get_config는 deepcopy 반환, 실행 컨텍스트 우선 |
| tier_provider/create_tier_client | tier=quick/deep + config → provider/client | 전용 provider가 truthy면 선택, lower. 모델은 해당 tier_think_llm 필수 |
| LLM kwargs | temperature, llm_max_retries, max_tokens, provider thinking 옵션 | null/빈 값은 미전달, SDK 자체 기본값 사용. retries/token 변환·거부는 C-05 |
| get_language_instruction | get_config().output_language → string | strip/lower가 english면 빈 문자열, 아니면 전체 응답 언어 지시 + Rating·FINAL TRANSACTION PROPOSAL 영어 유지 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 환경 덮어쓰기 | C-01 등록 환경변수의 unset/빈 문자열은 무시한다. 기본값 타입을 기준으로 bool/int/float 변환하며 실패는 환경변수 이름이 붙은 ValueError. 기본 null인 설정은 문자열을 유지하고 소비 단계에서 변환한다. | 코드 확인 |
| R-02 | 기본 경로·값 | 패키지 import는 C-09의 dotenv 로딩을 먼저 수행한다. C-02의 기본값을 사용한다. 경로는 ~/.tradingagents 아래이며 전용 RESULTS_DIR/CACHE_DIR/MEMORY_LOG_PATH 환경변수로 대체한다. import 후 환경 변화는 build_default_config를 다시 호출해야 반영된다. | 코드 확인 |
| R-03 | 전역/실행 설정 | C-03 병합은 dict값 한 단계이며 깊은 재귀 병합이 아니다. set_config는 기존 process 설정을 갱신한다. run_config는 DEFAULT_CONFIG 위에 실행 설정을 병합하고 finally에서 이전 컨텍스트를 복원한다. get_config는 실행 컨텍스트 우선이며 반환값 수정은 저장 설정에 영향을 주지 않는다. | 코드 확인 |
| R-04 | graph의 설정 수용 | graph는 config or DEFAULT_CONFIG를 참조하며 graph용 partial merge는 하지 않는다. dataflow set_config 병합이 성공해도 graph 직접 키 접근은 실패할 수 있다. 외부에서 같은 map을 수정하면 후속 graph 설정 읽기에 반영될 수 있다. | 코드 확인 |
| R-05 | 계층 endpoint 선택 | tier provider가 기본 provider와 같으면 전용 endpoint or 공통 backend_url. 다르면 전용 endpoint만 전달한다. 그 뒤 kwargs를 실제 계층 provider 기준으로 만든다. 다른 공급자에게 공통 URL을 유출하지 않는다. | 코드 확인 |
| R-06 | 인자 변환·factory 경계 | C-05의 provider별 thinking/reasoning·temperature·max retry/token 규칙을 따른다. retries bool/음수·token bool/0이하 거부. factory는 provider 이름을 lower하여 native4종과 OpenAI 호환 등록부 중 선택, 미지원은 ValueError. 실제 클라이언트 내부 변환·인증은 외부 어댑터 책임. | 코드 확인 |
| R-07 | 언어 지정 | C-07의 언어 지시를 반환한다. English는 공백·대소문자 무시, 그 외는 원문 언어 문자열을 prompt에 넣는다. 주석의 내부 토론 영어 고정 설명과 달리 모든 출력 역할이 helper를 사용할 수 있다. | 코드 확인 |

- 미결정: 없음(선언한 범위의 원본 경계).
- 확인 한계: 외부 API·모델·LangGraph를 실행하지 않았다. 아래 사례는 구현에서 도출했으며 테스트 실행 결과가 아니다.

### 1.5 필수 코드 참조

기준은 frontmatter의 SHA이며 원본 레포 루트 상대 경로다. C-ID가 지시하는 표·포맷·분기·알고리즘은 해당 범위를 함께 읽는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/default_config.py:3-74` · 환경 매핑·_coerce·_apply_env_overrides | bool 허용 토큰까지 포함한 환경 계약 | R-01 |
| C-02 | `tradingagents/default_config.py:77-209` · build_default_config·DEFAULT_CONFIG | 설정 키 전체·중첩 map·벤치마크·뉴스 쿼리 기본값 | R-02 |
| C-03 | `tradingagents/dataflows/config.py:8-75` · _merge·set_config·run_config·run_config_context·get_config | ContextVar·전역 초기화·복사/복원까지 | R-03 |
| C-04 | `tradingagents/graph/trading_graph.py:54-113` · __init__ | config 참조·모델 생성·폴더 생성·호출 경계 | R-04 |
| C-05 | `tradingagents/llm_clients/factory.py:59-156` · coercers·kwargs·tier selection | REASONING_EFFORT_PROVIDERS 상수 포함 | R-05, R-06 |
| C-06 | `tradingagents/llm_clients/factory.py:7-56` · create_llm_client; `tradingagents/llm_clients/openai_client.py:263-306` · 등록부·is_openai_compatible | 호환 provider 이름은 등록부 키만 사용. 값의 class·credential 구현은 공급자 어댑터 경계이며 복사 대상으로 삼지 않음 | R-06 |
| C-07 | `tradingagents/agents/context.py:14-34` · get_language_instruction | 언어 지시·영어 라벨 보존; get_config C-03 | R-07 |
| C-08 | `tradingagents/llm_clients/base_client.py:25-62` · BaseLLMClient | 공급자 adapter의 get_llm 인터페이스. 모델 검증 경고는 adapter 책임 | R-06 |
| C-09 | `tradingagents/__init__.py:5-13` · dotenv 초기화 | cwd부터 .env 탐색·로드 후 .env.enterprise 로드(override=False), 외부 dotenv의 실제 탐색/파싱 동작은 라이브러리 경계 | R-02 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 외부 모델·SDK·네트워크는 정상/오류를 반환하는 대체물로 가정하며 실제 서비스 호환성을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | TRADINGAGENTS_CHECKPOINT_ENABLED=treu | 이름이 포함된 ValueError, false로 숨기지 않음 |
| T-02 | R-01, R-06 | TRADINGAGENTS_LLM_MAX_RETRIES="3" | 환경 단계 string 유지, kwargs 단계 int3 전달 |
| T-03 | R-03 | run_config 안에서 data_vendors.core_stock_apis만 변경 | 나머지 기본 카테고리 유지, 구간 종료 시 이전 컨텍스트 복원 |
| T-04 | R-04 | config={"llm_provider":"openai"}로 graph 생성 | 필수 data_cache_dir 직접 접근에서 KeyError 가능; 자동 full merge하지 않음 |
| T-05 | R-05 | 기본 provider=openai, backend_url=A; deep provider=google, deep endpoint 없음 | deep base_url=null, A 전달하지 않음 |
| T-06 | R-06 | provider=google,max_tokens="128" / max_tokens=0 | max_output_tokens=128 / ValueError |
| T-07 | R-07 | output_language=Korean | 응답 한국어 지시와 영어 Rating·제안 라벨 보존 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-01 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-02 | C-02, C-09 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-03 | C-03 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-04 | C-04 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-05, R-06 | C-05 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-06 | C-06 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-07 | C-07 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |
| R-06 | C-08 | 기준 SHA 코드 본문 정적 확인. 사례는 해당 규칙에서 도출. |

## 적용 메모

의견: 국장 경로를 추가해도 미국주식 기본 설정은 유지하고 별도 config를 주입할 수 있다. 벤더 설정 외에도 종목 식별·스냅샷 직접 경로와 뉴스 기본 쿼리·벤치마크를 함께 검토해야 한다.
