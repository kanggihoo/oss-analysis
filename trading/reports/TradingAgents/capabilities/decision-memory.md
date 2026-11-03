---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/memory/log.py
  - tradingagents/memory/settlement.py
  - tradingagents/memory/reflection.py
  - tradingagents/graph/trading_graph.py
  - tradingagents/agents/managers/portfolio_manager.py
  - tradingagents/default_config.py
  - tradingagents/dataflows/files.py
  - tradingagents/dataflows/vendors/yahoo/market.py
  - tradingagents/dataflows/vendors/yahoo/common.py
  - tradingagents/dataflows/date_window.py
depends:
  - configuration.md
  - run-state.md
  - decision-contract.md
  - run-input.md
status: ready
---

# 판단 기록·정산·교훈

> 종목·분석일의 최종 판단을 Markdown 로그에 기록하고, 보유 기간이 지난 판단의 성과·교훈을 다음 PM 판단 문맥으로 돌려준다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 그래프 시작 시 메모리 단계를 분석가와 나란히 실행한다.
2. 로그 전체의 pending 종목을 찾아 정산한다. 다른 정산이 락을 잡고 있으면 기다리지 않고 기존 교훈 읽기로 넘어간다.
3. 분석일 이후 첫 완결 종가를 진입가로, 설정된 거래 봉 수 뒤 종가를 종료가로 삼아 종목 수익률과 벤치마크 대비 초과수익률을 계산한다.
4. 각 성과를 quick 모델에 전달해 교훈을 생성하고 해당 pending 항목을 즉시 resolved 항목으로 바꾼다.
5. 현재 종목 과거 판단과 다른 종목 교훈을 선택한다. 과거 날짜 분석은 그 날짜까지 성과가 확정된 항목만 받는다.
6. `past_context`와 실패 안내 `memory_note`를 상태에 쓰며, 판단 에이전트 중 PM이 교훈을 읽는다.
7. 이번 그래프가 끝나면 실행 상태 JSON을 먼저 저장하고, 최종 판단이 있으면 새로운 pending 결정을 기록한다.

### 1.2 범위·통합 지점

- 제공: 영속 판단 원장, 사후 성과·교훈 생성, 시점별 문맥 선택, 동일 결정 중복 방지.
- 제외: 주문 체결·실제 보유 잔고·전략별 수익곡선. 아래 수익률은 실제 거래 손익이 아니라 결정별 가격 변화다. 별도 주기 실행기는 이 범위에 없다.
- 선행: 설정, 실행 상태, 등급, 종목 정규화는 각 선행 스펙을 따른다. 모델은 메시지 목록을 받아 content를 반환하거나 예외를 올리는 quick 모델이다.
- 직접 가격 의존: Yahoo 일별 `history(start,end)`에서 Close 시계열을 받는다. end는 제외 경계이고 결과 없음은 빈 실수 시계열이다. 벤더 라우터·데이터 벤더 설정을 거치지 않는다. 원본의 재시도는 C-10을 따른다. 시계열 정렬·인덱스·수정주가 성질은 외부 라이브러리 응답에 의존한다.
- 소유 상태: Markdown 파일과 쓰기 락·정산 락, 정산 시 `.tmp`, 실행별 상태 JSON. 로그를 읽는 작업은 쓰기 락을 잡지 않는다. 실시간 원장은 여러 종목이 함께 쓰며, 백테스트는 별도 경로를 사용한다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 | 의미·제약 |
|---|---|---|
| `TradingMemoryLog(config)` | optional `memory_log_path`, `memory_log_max_entries` | 경로가 없으면 읽기는 빈 목록·쓰기 무동작. 기본 경로와 초기 환경 적용은 설정 스펙 참조. 최대 resolved 항목 수 기본 null, null/0/음수는 회전 비활성 |
| `store_decision(ticker,trade_date,final_trade_decision,rating=null)` | strings → 반환 없음 | 동일 원문 종목·날짜로 이미 기록돼 있으면 새 판단을 덮어쓰지 않는다. rating 누락·빈 문자열은 S2 파서 사용 |
| pending 태그 | `[YYYY-MM-DD \| TICKER \| RATING \| pending]` | 다음에 빈 줄과 `DECISION:\n<판단>`; 항목 구분자는 `\n\n<!-- ENTRY_END -->\n\n` |
| resolved 태그 | `[date \| ticker \| rating \| +r.r% \| +a.a% \| Nd \| resolved:YYYY-MM-DD]` | raw·alpha는 부호 포함 소수점 한 자리 백분율 문자열. 마지막 resolved 필드는 legacy 항목에서 생략 가능. `REFLECTION:` 구간 추가 |
| 파싱 결과 | `date,ticker,rating,pending,raw,alpha,holding,resolved,decision,reflection` | pending의 raw는 null. 날짜·수익률 필드를 여기서 엄격히 검증하지 않으며 C-06 문법을 그대로 적용 |
| `get_past_context(ticker,n_same=5,n_cross=3,as_of=null)` | string | 동일 종목 최대5건의 판단·교훈과 다른 종목 최대3건의 교훈. 심볼 동등성 비교가 아니라 기록 문자열 equality |
| `fetch_returns(ticker,trade_date,holding_days=5,benchmark="SPY")` | `(raw,alpha,days,resolution_date)` 또는 전부 null | 수익률은 비율(0.05=5%). days는 진입 봉 이후 거래 봉 수. resolution은 종료 봉 날짜 |
| `Settlement` | `settled[(ticker,date)]`, `failed[(ticker,date,reason)]` | 미성숙 항목·락 미획득은 실패 목록에 추가하지 않는다 |
| `_memory_step(state)` | `{past_context:string,memory_note:string}` | 실패가 없으면 note는 빈 문자열. 정산 실패와 읽기 실패를 별개로 처리 |
| `batch_update_with_outcomes(updates)` | 목록 → 반환 없음 | 각 요소는 `ticker,trade_date,raw_return,alpha_return,holding_days,reflection`, optional `resolution_date`; 같은 키 중 마지막 입력 사용 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 새 최종 판단 저장 | 상태 JSON 저장 후 판단이 비어 있지 않을 때만 pending 추가. 동일 ticker·date의 pending 또는 resolved가 존재하면 추가하지 않는다. `REVIEW`도 기록 대상이다 | 코드 확인 |
| R-02 | 로그 로드·결과 갱신 | 문법·직렬화는 C-01·C-03·C-06. 개별 갱신은 첫 일치 pending만 바꾸고 성공 여부 반환. 배치는 키별 한 항목만 갱신한다. 실패한 파일 I/O는 호출자에게 올라간다 | 코드 확인 |
| R-03 | 동시 저장·정산 | 파일 쓰기는 `<log>.lock`, 정산 pass는 `<log>.settle.lock`으로 직렬화한다. wait=false로 정산 락을 못 잡으면 빈 Settlement. 결과를 하나씩 즉시 기록하므로 후속 중단 전에 끝낸 결과는 남는다 | 코드 확인 |
| R-04 | 회전 활성, resolved 개수 초과 | resolved만 결정일 오래된 순, 같은 날짜면 앞쪽 항목부터 제거한다. pending은 보존. 회전은 결과 갱신 시점에 적용하며 단순 append 시에는 하지 않는다 | 코드 확인 |
| R-05 | 성과 계산 | C-07의 시계·봉 필터·진입/종료 선택·벤치마크 asof·단순 차감 alpha 알고리즘을 적용한다. 현재 시각에 창이 미성숙하거나 벤치마크가 양 끝을 덮지 못하면 전부 null | 코드 확인 |
| R-06 | 벤치마크 선택 | 명시적 `benchmark_ticker` 우선, 없으면 정규화 종목의 접미사 지도 순서, 없으면 빈 접미사 기본값 또는 SPY. `.KS`→`^KS11`, `.KQ`→`^KQ11`도 기본 지도에 있다. 환율 변환 없이 각 통화의 수익률끼리 비교한다 | 코드 확인 |
| R-07 | 정산할 pending 존재 | 가격 예외는 `prices unavailable`, 교훈 LLM 예외는 `reflection failed`로 기록하고 그 항목은 pending 유지, 다음 항목 계속. `REVIEW`를 별도 건너뛰지 않는다. 결과 갱신 파일 I/O 예외는 이 per-entry catch 밖으로 전파한다 | 코드 확인 |
| R-08 | 성과 확보 | quick 모델에 최종 판단·raw·alpha·벤치마크·기간을 전달해 교훈을 만든다. 2~4문장·단기 성과의 판단 한계는 프롬프트 지시이며 문장 수를 코드로 강제하지 않는다 | 코드 확인 |
| R-09 | 문맥 읽기 | pending 제외 후 결정일 내림차순·같은 날짜는 나중 기록 우선. as_of 지정 시 resolved가 존재하고 <=as_of인 항목만 남긴다. 동일 종목은 전체 판단, 교차 종목은 교훈(없으면 판단 앞300자)을 사용 | 코드 확인 |
| R-10 | 과거 날짜의 그래프 메모리 단계 | as_of=trade_date. 오늘 분석이면 as_of=null로 legacy도 포함 가능. 정산 계산은 현재 시계로 하지만 미래에 확정된 교훈은 과거 PM 입력에서 제외된다 | 코드 확인 |
| R-11 | 메모리 단계 실패 | 정산 예외를 잡아 note 기록 후 기존 교훈 읽기 시도. 읽기 예외도 잡고 빈 문맥 반환. PM은 note가 아닌 past_context를 교훈 입력으로 읽는다 | 코드 확인 |

미결정: 없음. 선행 스펙의 상태·경계와 대조 완료.

확인 한계: 원본 설치·실행·모델·Yahoo 실응답 검증 없음. 날짜가 붙은 정보만 시간 필터를 통과시키는 원본 규칙이며 외부 LLM의 사전학습 정보나 교훈 내용의 사실성까지 차단하는 장치는 아니다.

### 1.5 필수 코드 참조

모든 경로는 고정 SHA의 레포 상대 경로다. 내부 `normalize_symbol`·등급 파싱·설정 값은 선행 스펙으로 닫고, Yahoo 함수는 C-09·10의 경계로 닫는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/memory/log.py:14-60` `_SEPARATOR`, 정규식, 초기화, `store_decision` | 태그·구분자·경로 비활성·중복 검사 | R-01,02 |
| C-02 | `tradingagents/memory/log.py:62-133` `settling`, `load_entries`, `get_pending_entries`, `get_past_context` | 정산 락·항목 선택·문맥 정렬 | R-03,09 |
| C-03 | `tradingagents/memory/log.py:137-257` `update_with_outcome`, `batch_update_with_outcomes` | pending 교체·일괄 키 규칙·tmp 교체 | R-02,04,07 |
| C-04 | `tradingagents/memory/log.py:262-309` `_resolved_tag`, `_apply_rotation` | 결과 태그·오래된 resolved 제거 | R-02,04 |
| C-05 | `tradingagents/dataflows/files.py:36-88` `locked`, `_hold_posix`, `_hold_windows` | OS별 파일 락·wait=false 반환·해제 | R-03 |
| C-06 | `tradingagents/memory/log.py:311-360` `_parse_entry`, `_format_full`, `_format_reflection_only` | legacy·필드 파싱과 출력·300자 경계 | R-02,09 |
| C-07 | `tradingagents/memory/settlement.py:16-125` `resolve_benchmark`, `_now`, `_by_day`, `fetch_returns` | 봉 필터·기간 확장·벤치마크·수익률 산식 | R-05,06 |
| C-08 | `tradingagents/memory/settlement.py:128-196` `Settlement`, `settle_pending`, `settle_all_pending` | 정산 순회·예외 정책·비용 중복 억제 | R-03,07 |
| C-09 | `tradingagents/dataflows/vendors/yahoo/market.py:266-270` `get_closes` | 정규화 후 Yahoo history에서 Close 획득 | R-05 |
| C-10 | `tradingagents/dataflows/vendors/yahoo/common.py:43-91` `_answered_empty`, `yf_retry` | 429 최대3회 재시도(2/4/8초), 무데이터면 null, 다른 예외는 VendorUnavailableError | R-05,07 |
| C-11 | `tradingagents/memory/reflection.py:6-63` `Reflector` | 교훈 프롬프트·입력·quick 호출1회 | R-08 |
| C-12 | `tradingagents/graph/trading_graph.py:130-138,309-371` `_memory_as_of`, `_memory_step`, 정산·기록 메서드 | 날짜별 주입·note·기록 순서 | R-01,10,11 |
| C-13 | `tradingagents/graph/trading_graph.py:438-476` `_log_state` | JSON 필드·경로·UTF-8 저장 | R-01 |

`VendorUnavailableError`는 여기서는 단지 가격 요청 실패 예외이며 정산의 일반 Exception 경계에서 failed로 바뀐다. 모듈/파일 라이브러리를 이식할 필요는 없으나 이 전파 의미는 보존한다.

### 1.6 수락 사례

출처: 모두 구현에서 도출. 외부 종가·모델을 고정 대체물로 놓은 사례이며 실제 Yahoo·모델 호환성은 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 동일 ticker·date pending 저장 후 다른 텍스트로 재저장 | 원래 항목1개 유지; resolved 뒤 재저장도 추가 없음 |
| T-02 | R-05 | 진입 봉100, 5봉 뒤110; 같은 날짜의 benchmark 200→210; 현재는 두 종료 봉 이후 | raw=0.10, alpha=0.05, days=5, resolved=종목 종료일 |
| T-03 | R-05,07 | 진입 포함 완결 종목 봉이5개뿐이고 holding_days=5 | 전부 null, pending 유지·failed 추가 없음 |
| T-04 | R-09,10 | pending A, resolved 없는 legacy B, resolved=10월20일 C; as_of=10월19일 | 모두 문맥에서 제외. as_of=null이면 B·C 포함 가능 |
| T-05 | R-03,11 | 다른 pass가 정산 락 보유, 그래프 wait=false | 정산을 기다리지 않고 기존 문맥 반환; 실패 note는 락 충돌만으로 생성하지 않음 |
| T-06 | R-07 | 첫 pending 교훈 모델 예외, 둘째 성공 | 첫 pending+failed, 둘째 resolved+settled; pass 전체는 계속 |
| T-07 | R-04 | resolved 3개·pending2개, cap=2에서 결과 갱신 | 가장 오래된 결정일의 resolved 제거, pending2개 보존 |
| T-08 | R-07 | REVIEW 판단에 정산 가능한 가격·교훈 응답 제공 | REVIEW도 resolved로 전환. 백테스트 집계에서는 별도 unscored |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 / T-01 | C-01,12,13 | 소스 직접 열람; JSON 저장 예외가 pending 기록보다 먼저 전파됨 |
| R-02 | C-01,03,04,06 | 결과 파일 형식·파서와 write 경로 대조 |
| R-03 / T-05 | C-02,05,08 | 락별 수명·반환값과 그래프 wait=false 호출 대조 |
| R-04 / T-07 | C-03,04 | 회전 호출 지점 및 정렬 기준 확인 |
| R-05 / T-02,03 | C-07,09,10 | 가격 계산 정적 확인, 네트워크/시계 실행 확인 없음 |
| R-06 | C-07; `tradingagents/default_config.py:172-204` | 기본 지역 지도와 명시 override 대조 |
| R-07 / T-06,08 | C-08 | REVIEW 제외 분기가 없음을 순회 전체에서 확인 |
| R-08 | C-11 | 원문 “Write exactly 2-4 sentences of plain prose” — “일반 문장으로 정확히 2~4문장을 작성하라.” 출력 검사 코드는 없음 |
| R-09 / T-04 | C-02,06 | legacy·resolved 비교·ticker 문자열 동등성 확인 |
| R-10 | C-12; `tradingagents/dataflows/date_window.py:35-42` | 오늘은 로컬 date.today(), 정산 시계는 UTC Timestamp임을 구분 |
| R-11 | C-12; `tradingagents/agents/managers/portfolio_manager.py:35-40,60` | past_context만 프롬프트로 연결. note는 주입되지 않음 |

원본 docstring은 append-only라 부르지만 결과 갱신·회전은 파일을 다시 쓰므로 영구 불변 원장으로 해석하지 않는다(C-03·04, 코드 확인).

핵심 원본: [성과 계산](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/memory/settlement.py#L60-L125), [시점별 교훈 선택](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/memory/log.py#L93-L133).

## 적용 메모

의견: 미국 주식 분석에서는 원본 Yahoo/SPY 경로를 유지할 수 있다. 국장용 데이터 공급자를 추가하더라도 정산 `get_closes`는 라우터 밖이므로 별도로 교체해야 한다. 원본 지역 벤치마크 지도에는 한국 지수가 이미 있으나 데이터 공급 가능성까지 보장하지 않는다. 원본 스펙에는 이 변경을 반영하지 않았다.
