---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/graph/checkpointer.py
  - tradingagents/graph/trading_graph.py
  - tradingagents/portfolio.py
  - tradingagents/dataflows/symbols.py
  - tradingagents/default_config.py
  - cli/run.py
depends:
  - configuration.md
  - run-state.md
  - run-input.md
status: ready
---

# 중단 실행 재개

 > 종목·날짜·분석 설정·보유 현황이 같은 중단 실행을 SQLite 체크포인트에서 재개하고 성공 후 해당 실행 기록을 지운다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 기본 비활성인 `checkpoint_enabled`를 실행 설정에서 읽는다.
2. 활성화됐으면 실행 설정·분석가 선택·자산 유형·보유 현황을 실행 시그니처로 만든다.
3. 종목별 SQLite를 열고 checkpointer를 붙여 그래프를 다시 compile한다.
4. 해당 thread의 최신 step 존재를 조회한다. 있으면 `None`, 없으면 초기 상태를 그래프 입력으로 준다.
5. 실제 호출 config에 thread_id를 넣고 실행한다.
6. 그래프 완료 후 결정 기록까지 성공하면 thread의 checkpoint/write 행을 삭제한다. 실패 시 삭제 단계까지 가지 않아 재개 기록이 남는다.
7. 종료 경로에서 SQLite 연결을 닫고 checkpointer 없는 그래프로 되돌린다.

### 1.2 범위·통합 지점

- 제공: 종목별 checkpoint 저장소 수명, 호환되는 실행 식별, 실패 재개·성공 정리, 전체 초기화.
- 제외: LangGraph 자체의 checkpoint wire schema·node replay 알고리즘. 원본도 외부 `SqliteSaver`·그래프에 맡긴다. 이 스펙은 호환 graph/saver가 제공될 때의 호출 계약이다.
- 외부 graph 계약: `compile(checkpointer=saver)`로 saver를 붙이고, `config.configurable.thread_id`로 스레드 선택. 같은 thread에 입력 null을 주면 기존 상태를 이어가는 방식으로 호출한다. saver는 `setup()`, `get_tuple(config)`를 제공하며 결과 metadata.step이 있으면 중단점이 있다고 판단한다. 이 외부 라이브러리의 실제 보장은 실행 검증하지 않았다.
- 소유 상태: 그래프 객체의 `_checkpointer_ctx`, `_resuming`, `graph`; 종목별 DB와 SQLite 부속 파일. 서로 다른 종목 파일은 분리되지만 같은 graph 객체의 중첩·동시 실행을 보호하는 자체 락은 없다.
- 선행: 설정과 초기 상태·종목 경로 안전 검사·보유 fingerprint. 새 입력 검증 자체는 run-input, 결정 저장 자체는 decision-memory의 책임이며 여기서는 성공 완료 경계만 정의한다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 | 의미·제약 |
|---|---|---|
| `checkpoint_enabled` | boolean, 기본 false | 비활성 `begin_checkpoint`는 null, `_resuming=false`. DB 열지 않음 |
| 저장 경로 | `<data_cache_dir>/checkpoints/<safe_ticker.upper()>.db` | 원문 종목 spelling 기반. normalize_symbol로 시장 별칭을 합치지 않는다. 안전 검사 최대32자·허용문자·점-only 거부는 run-input 계약 |
| `thread_id(ticker,date,signature="")` | string → string | 대문자 ticker·date·optional signature를 결합한 SHA256 앞16자리. 정확 결합 규칙 C-01 |
| `_run_signature(asset_type,portfolio=null)` | string | 분석가 순서·토론 깊이·리스크 깊이·자산·보유 fingerprint·병렬 그래프 버전 표식·설정 digest 포함 |
| `begin_checkpoint(company_name,trade_date,asset_type="stock",portfolio=null)` | string 또는 null | 활성화 시 SQLite 연결을 잡아 둔 채 thread_id 반환. 호출자는 반드시 end와 짝지어야 함 |
| `checkpoint_input(init_state)` | 초기 map 또는 null | `_resuming=true`일 때 null. 초기 상태를 다시 append하지 않도록 함 |
| `end_checkpoint()` / `checkpoint_scope(...)` | 반환 없음 / context manager | 연결 정리와 기본 그래프 복원. scope는 finally에서 end 호출 |
| `clear_checkpoint_on_success(...)` | 반환 없음 | 활성일 때만 해당 ticker/date/signature 행 삭제 |
| `clear_all_checkpoints(data_dir)` | integer | `.db` 수를 반환하고 각 db와 그 이름에 `-`가 붙는 부속 파일 삭제 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | checkpoint 비활성 | begin은 `_resuming=false`, null 반환. 입력은 초기 상태, 성공 삭제는 무동작 | 코드 확인 |
| R-02 | 활성 실행의 식별 | C-01·03의 경로·시그니처·해시를 사용. 시그니처는 분석가 순서까지 반영, portfolio=null과 빈 객체를 구분. 설정 해시 제외 키는 `results_dir,data_cache_dir,memory_log_path,checkpoint_enabled,llm_max_retries`뿐 | 코드 확인 |
| R-03 | DB와 같은 thread의 metadata.step이 존재 | `_resuming=true`, graph input=null. step=0도 재개 대상으로 보고 음수 등 step 값의 의미를 별도 검사하지 않는다. DB만 있고 해당 tuple/step이 없으면 fresh | 코드 확인 |
| R-04 | begin 활성 | 연결은 `check_same_thread=false`, saver.setup 후 checkpointer 부착 compile. 연결 생성·setup·compile·조회 예외는 삼키지 않는다 | 코드 확인 |
| R-05 | Python propagate 실행 | 날짜 검증 후 checkpoint_scope 안에서 실행. thread_id를 config에 넣고 결정 기록 성공 뒤 해당 thread를 지운다. 실행·기록 예외 시 삭제하지 않고 finally end로 자원을 정리한다 | 코드 확인 |
| R-06 | end 실행 | 보유 context가 있으면 닫고 null로 바꾸고 plain workflow compile; `_resuming=false`. 성공 완료해도 DB 파일 자체는 남고 thread 행만 지운다 | 코드 확인 |
| R-07 | 특정 실행 삭제 | `writes`, `checkpoints` 테이블에서 thread_id 행 삭제·commit. 파일 없으면 무동작. sqlite OperationalError는 삼키고 연결 닫음; 다른 예외는 전파 | 코드 확인 |
| R-08 | 전체 삭제 요청 | checkpoints 폴더 없으면0. `*.db`와 각 `<db.name>-*` 파일 제거. 파일 삭제 권한/사용 중 오류를 포괄적으로 무시하지 않는다 | 코드 확인 |
| R-09 | CLI streaming | create_run_state → begin → thread config → checkpoint_input → stream. stream·결정 저장 성공 후 clear, stream 구간 finally에서 end | 코드 확인 |

미결정: 없음. 선행 스펙의 상태·경계와 대조 완료.

확인 한계: 원본·LangGraph/SQLite 조합을 실행하지 않았다. 저장된 step이 실제로 재개 가능함과 외부 라이브러리 버전 간 호환성은 미확인. R-09에서 CLI의 begin 자체는 stream try/finally 앞에 있으므로 begin 예외까지 CLI가 항상 end로 정리한다고 확대하지 않는다. Python scope는 begin도 finally 범위에 있다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/graph/checkpointer.py:19-65` `_db_path`, `thread_id`, `get_checkpointer`, `checkpoint_step` | 저장 경로·해시·saver 연결/조회 | R-02,03,04 |
| C-02 | `tradingagents/graph/checkpointer.py:68-99` `clear_all_checkpoints`, `clear_checkpoint` | 삭제 대상·SQL·예외 범위 | R-07,08 |
| C-03 | `tradingagents/graph/trading_graph.py:44-48,140-165` `_NOT_IN_SIGNATURE`, `_run_signature` | 제외 설정·필드별 결합·12자리 settings digest | R-02 |
| C-04 | `tradingagents/graph/trading_graph.py:167-253` `propagate`, `begin_checkpoint`, `checkpoint_input`, `end_checkpoint`, `checkpoint_scope`, `clear_checkpoint_on_success` | 수명·재개 판정·정리와 활성 분기 | R-01,03~07 |
| C-05 | `tradingagents/graph/trading_graph.py:373-405` `_run_graph` | thread config, 입력 선택, 기록→clear→반환 순서 | R-05 |
| C-06 | `cli/run.py:219-241,344-359` `run_analysis` 일부 | streaming 경로의 begin·성공·finally | R-09 |

C-01에서 쓰는 경로 안전 검사와 C-03의 portfolio.fingerprint는 run-input의 코드 계약이다. `_run_graph`의 propagator·graph 실행은 S1의 초기 상태 및 graph의 config 입출력 경계, record_decision은 결정 저장이 성공하거나 예외를 올리는 경계로 취급한다. S2의 run_rating은 최종 반환 신호 결정용이며 체크포인트 식별/저장에는 쓰이지 않는다.

### 1.6 수락 사례

출처: 모두 구현에서 도출. graph/saver의 고정 대체 응답을 전제로 하며 node 실행·외부 라이브러리 persistence를 실증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 비활성 begin 후 checkpoint_input(initial) | begin=null, input=initial; DB 생성 없음 |
| T-02 | R-02 | 동일 ticker/date에서 분석가 순서를 바꾸거나 portfolio=null을 빈 객체로 변경 | 시그니처·thread_id 달라짐 |
| T-03 | R-02 | 같은 설정에서 llm_max_retries만 변경 | 시그니처 동일. 단 cache dir를 바꾸면 같은 해시여도 조회 파일 위치는 달라짐 |
| T-04 | R-03 | get_tuple.metadata.step=0 | 재개 true, input=null |
| T-05 | R-05,06 | graph 실행 예외 | 성공 삭제 호출 없음. Python scope는 end 후 plain graph·resuming=false |
| T-06 | R-05,07 | graph와 record_decision 성공 | 해당 thread rows 삭제 후 자원 닫음. 다른 thread와 DB 파일은 유지 |
| T-07 | R-08 | A.db,A.db-wal,A.db-shm가 존재 | 전체 삭제 count=1, 세 파일 제거 |
| T-08 | R-07 | 특정 삭제 시 테이블 없어 OperationalError | 에러를 전파하지 않고 연결 닫음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 / T-01 | C-04 | 활성 분기 직접 열람 |
| R-02 / T-02,03 | C-01,03; `tradingagents/portfolio.py:70-72`; `tradingagents/dataflows/symbols.py:147-180` | fingerprint·경로 검사와 시그니처 연결 대조 |
| R-03 / T-04 | C-01,04 | tuple step 없음을 null로 반환, is not None으로 resume 판정 |
| R-04 | C-01,04 | 외부 saver 호출 코드를 확인, 라이브러리 실행 없음 |
| R-05 / T-05,06 | C-04,05 | 성공 시점과 finally 경계 대조 |
| R-06 | C-01,02,04 | close와 plain compile 순서 확인 |
| R-07 / T-08 | C-02 | OperationalError만 catch |
| R-08 / T-07 | C-02 | DB 수와 sidecar glob 확인 |
| R-09 | C-06 | CLI의 begin이 stream try 밖임을 확인 |

핵심 원본: [실행 시그니처·수명](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/graph/trading_graph.py#L140-L253).
