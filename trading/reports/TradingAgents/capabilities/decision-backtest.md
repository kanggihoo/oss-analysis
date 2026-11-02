---
sha: "c4544913a14ed3df5f1ed7b9e8483270ce20682a"
created: 2026-11-02
updated: 2026-11-02
sources:
  - tradingagents/backtest.py
  - tradingagents/graph/trading_graph.py
  - tradingagents/memory/log.py
  - tradingagents/dataflows/symbols.py
  - tradingagents/dataflows/date_window.py
depends:
  - configuration.md
  - run-input.md
  - run-state.md
  - decision-contract.md
  - analysis-orchestration.md
  - decision-memory.md
status: ready
---

# 판단 품질 백테스트

 > 종목×분석일의 판단을 실행별 전용 원장에 모으고, 정산된 등급별 초과수익률과 방향 적중률을 집계한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. 날짜 그리드를 만들 때 시작·종료 날짜와 간격을 검증하고 오늘을 넘지 않는 달력 날짜 목록을 만든다.
2. 새 run_id 폴더를 원자적으로 확보하거나 지정 run_id 폴더를 다시 사용한다.
3. 복사한 설정의 results_dir와 memory_log_path만 백테스트 전용 경로로 바꿔 그래프를 만든다.
4. 종목과 날짜를 각각 입력 순서대로 중복 제거하고, 그 Cartesian product에서 원장에 이미 있는 셀은 건너뛴다.
5. 남은 셀을 순차 실행하며 셀별 실패를 기록하고 계속한다. 모든 셀에 같은 portfolio 객체를 전달한다.
6. 전체 실행 뒤 종목마다 다시 정산해 마지막 셀까지 처리 가능한 결과를 기록한다.
7. 원장을 다시 읽어 등급별 mean_alpha와 방향 적중률을 계산한다. REVIEW·pending은 성과 평균에 넣지 않는다.

### 1.2 범위·통합 지점

- 제공: 반복 가능한 실행 단위 식별과 skip, 셀별 부분 실패, 원장 기준 요약.
- 제외: 주문 수량·체결가·수수료·잔고 변화·비중별 포트폴리오 손익·실거래 성능 보장. 각 셀은 동일 portfolio를 받으며 이전 셀 결과로 현황을 갱신하지 않는다.
- 선행: 설정·입력/등급·분석 그래프·메모리의 저장·정산 계약. 그래프 인스턴스는 해당 설정과 분석가로 조립되고 propagate가 최종 결과를 원장에 남긴다. 투자·리스크 판단 내용은 해당 스펙으로 이어지며 이 문서는 스윕과 평가를 소유한다.
- 소유 상태: `results_dir/backtest/run_id/`의 상태 로그와 `trading_memory.md`, 메모리 원장의 resolved/pending. 원본 live 원장의 경로는 덮어쓰지 않는다. cache/checkpoint 설정은 복사본에서 변경하지 않아 라이브 실행과 공유될 수 있다.
- 공개 함수 실행은 내부 스케줄러가 아니다. CLI의 `--every`는 분석일 그리드 간격이며 실행 시간 간격이 아니다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 | 의미·제약 |
|---|---|---|
| `iter_grid(start_date,end_date,every_n_days=1)` | YYYY-MM-DD string2개·integer → list[string] | 양 끝 포함, 달력일 간격. 휴장일 필터 없음. 오늘 뒤 날짜는 제외. CLI는 별도로 간격 기본7을 전달하지만 함수 기본은1 |
| `run_backtest(tickers,dates,config,asset_type="stock",portfolio=null,selected_analysts=(market,social,news,fundamentals),run_id=null,progress=null)` | list[string]·list[string]·map → BacktestResult | 날짜 목록을 함수 안에서 정렬/그리드 검증하지 않음. 각 셀 날짜 검증은 propagate의 run-input 경계 |
| `run_id` | optional string | 없거나 빈 문자열이면 로컬 현재시각 `YYYYMMDD_HHMMSS`; 충돌 시 `_2`, `_3`… 새 폴더 확보. 주면 경로 안전 검사 후 기존 폴더 재사용(정확 max32자 규칙은 C-05) |
| `progress(done,total,ticker,date)` | callback | 남은 셀 실행 바로 전 1부터 호출. 이미 skip한 셀은 분모·분자에서 제외. callback 예외는 셀 try 밖이라 스윕을 중단 |
| `BacktestResult` | run_id:string, log_path:path, cells_run:int, skipped:int, failures:list, settlement_failures:list | failures=(ticker,date,reason), settlement_failures=(ticker,reason)이며 정산 항목별 reason 앞에 날짜가 붙음 |
| `summarize(source)` | BacktestResult 또는 기존 파일 경로 → BacktestSummary | Result의 로그가 없어도 빈 결과를 만들 수 있으나 경로 입력 파일이 없으면 FileNotFoundError |
| `RatingScore` | count:int, hit_rate:optional float, mean_alpha:float | count는 해당 등급의 scored 항목 수. hit_rate 0~1, mean_alpha는 비율 |
| `BacktestSummary` | resolved:int,pending:int,by_rating:map,unscored:int,holding:string | 등급 순서는 원장에 처음 등장한 scored 등급 순서. holding은 정산된 항목의 Nd에서 수집한 기간 문자열 정렬/결합 |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 날짜 그리드 생성 | canonical YYYY-MM-DD만 허용, 간격>=1, 종료>=시작. 끝은 min(종료,로컬 오늘). 시작이 오늘 뒤면 빈 목록. 휴일도 간격에 맞으면 들어간다 | 코드 확인 |
| R-02 | 스윕 시작 | 새 폴더는 mkdir 성공으로 동시 생성과 분리. 지정 ID는 안전 검사 후 재사용. graph 생성·설정 오류는 셀별 catch 이전이므로 전파한다 | 코드 확인 |
| R-03 | 전용 원장 분리 | 복사 설정에서 `results_dir=<base>/backtest/<id>`, `memory_log_path=<run>/trading_memory.md` 두 키 변경. 원본 map은 직접 수정하지 않는다. 같은 run_id를 다른 모델/설정으로 재사용해도 기존 셀을 config별 구분하지 않는다 | 코드 확인 |
| R-04 | 셀 목록·skip | exact ticker/date string 중복을 먼저 제거. 종목 외부 루프·날짜 내부 루프, 정렬 안 함. pending/resolved/REVIEW 여부와 무관하게 같은 tuple이 원장에 있으면 skip | 코드 확인 |
| R-05 | 남은 셀 실행 | progress 후 propagate. 정상 반환만 cells_run+1. Exception은 failures 추가 후 다음 셀. portfolio는 전 셀에 같은 객체이며 자동 체결/재투자 없음 | 코드 확인 |
| R-06 | 스윕 끝 | 중복 제거한 각 종목 settle_pending. 정산 failed를 settlement_failures로 옮기고, 종목 정산 전체 예외도 추가한 후 다음 종목 계속. 미성숙 창은 failed가 아니라 pending 유지 | 코드 확인 |
| R-07 | 요약 입력 | Result면 log_path를 사용해 없을 때 빈 원장. 직접 경로는 파일 존재 검사 후 읽기. 저장 alpha 문자열을100으로 나눠 비율로 복원하므로 소수점0.1%p 수준으로 반올림된 성과를 집계 | 코드 확인 |
| R-08 | scored 항목 선택 | non-pending이고 rating!=REVIEW이며 alpha 파싱 가능한 항목만 resolved에 포함. REVIEW는 pending 여부와 관계없이 unscored에 집계. 나머지 개수는 pending=len(entries)-resolved-unscored | 코드 확인 |
| R-09 | 등급별 적중률·평균 | Buy/Overweight direction=+1, Sell/Underweight=-1. alpha*direction>0인 비율, alpha=0은 적중 아님. Hold 또는 알 수 없는 rating direction=0은 hit_rate=null. mean_alpha는 매도 등급도 원래 alpha의 산술평균이며 숏 수익으로 뒤집지 않음 | 코드 확인 |
| R-10 | 출력 설명 | 실제 정산 로그의 기간들을 표시. 단일 모델 샘플과 미보관 텍스트 피드 때문에 indicative이며 동일 결과 반복 보장 아님을 render에 적는다 | 코드 확인 |

미결정: 없음. 선행 스펙의 상태·경계와 대조 완료.

확인 한계: 원본·외부 서비스 실행 없음. 코드의 시점 필터는 메모리 교훈 주입 제한이며 언어모델 사전학습 지식까지 막지 않는다. 같은 run_id에서 설정을 바꾸는 실험은 기존 셀 skip과 메모리 공유 때문에 순수 설정 비교를 보장하지 않는다(R-03).

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `tradingagents/backtest.py:35-76` `iter_grid`, `_canonical`, `_alpha` | canonical 날짜·오늘 상한·alpha 문자열 복원 | R-01,07 |
| C-02 | `tradingagents/backtest.py:79-127` 결과 dataclass·`_DIRECTION`, `render` | 결과 필드·방향 지도·표시 포맷·해석 한계 | R-07~10 |
| C-03 | `tradingagents/backtest.py:130-203` `_new_run`, `run_backtest` | run 폴더·dedup/skip·순회·진행/실패·마지막 정산 | R-02~06 |
| C-04 | `tradingagents/backtest.py:206-236` `summarize` | 입력 구분·scored 선택·집계·기간 | R-07~10 |
| C-05 | `tradingagents/dataflows/symbols.py:147-180` `_TICKER_PATH_RE`, `safe_ticker_component` | run_id 안전 문자·길이·점-only 거부 | R-02 |
| C-06 | `tradingagents/dataflows/date_window.py:35-37` `get_current_date` | 로컬 date.today() 날짜 문자열 | R-01 |

C-03의 graph 조립·실행은 configuration/run-input/run-state/analysis-orchestration, 완료 기록·정산·load_entries는 decision-memory 계약이다. C-04의 REVIEW 상수는 decision-contract. 내부 규칙의 중복 사본은 만들지 않는다.

### 1.6 수락 사례

출처: 모두 구현에서 도출. 그래프·시계를 고정 대체한 사례이며 모델 판단 품질과 실응답 검증을 포함하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01 | 오늘=2026-11-02, 시작10-31·종료11-10·간격1 | 10-31,11-01,11-02. 주말 제외 없음 |
| T-02 | R-01 | 시작 `2026-1-2` 또는 간격0 | ValueError |
| T-03 | R-02 | 같은 초 신규 스윕2개, 첫 stamp 폴더 존재 | 둘째 `_2` 폴더 사용. run_id=`../a`는 거부 |
| T-04 | R-03,04 | 기존 원장 (AAPL,10-01) pending. 같은 run_id에서 모델 변경 후 해당 셀과 새 날짜 요청 | 기존 셀은 skip, 새 날짜만 변경 설정으로 실행 |
| T-05 | R-04,05 | tickers=[A,A], dates=[d,d], 원장은 비어 있음 | 셀1개만 실행·종목1회만 마지막 정산 |
| T-06 | R-05,06 | 첫 셀 propagate 실패, 둘째 성공. 첫 종목 정산 실패 | cells_run=1·failures1건, 정산 실패 별도 기록 후 남은 종목 정산 |
| T-07 | R-08,09 | resolved Buy alpha=+2%, Sell=-3%, Hold=0%, REVIEW=+1%, pending Buy | resolved=3, unscored=1, pending=1. Buy/Sell hit_rate=1, Hold=null; Sell mean_alpha=-0.03 |
| T-08 | R-07 | 전 셀 실패하여 로그 없음. Result 직접 요약 / 없는 파일 경로 직접 요약 | Result는 빈 요약, 경로는 FileNotFoundError |
| T-09 | R-05 | progress callback이 예외 | 해당 셀 propagate·실패 집계까지 가지 않고 호출자가 예외 받음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 / T-01,02 | C-01,06 | canonical 비교와 달력 timedelta 직접 확인 |
| R-02 / T-03 | C-03,05 | mkdir 성공 기반 ID 확보·문자 검사 확인 |
| R-03 / T-04 | C-03; `tradingagents/graph/trading_graph.py:69-82` | shallow config 복사·별도 원장·같은 cache 유지 대조 |
| R-04 / T-05 | C-03; decision-memory C-01·02 | skip key에 설정·평가 상태가 없음을 확인 |
| R-05 / T-06,09 | C-03 | progress가 try 밖임을 확인. 순회 부분은 실제 graph 실행 없음 |
| R-06 | C-03; decision-memory C-08 | 정산 항목별 failed와 전체 예외를 나눔 |
| R-07 / T-08 | C-01,04 | 파일 경로 입력과 Result 입력 분기 대조 |
| R-08 / T-07 | C-04 | resolved/pending은 실제 parser pending 값과 완전히 같은 집합 이름이 아님 |
| R-09 / T-07 | C-02,04 | 방향0·alpha0·매도 부호 처리 확인 |
| R-10 | C-02 | render 설명 원문을 확인 |

원본은 이 도구를 포트폴리오 시뮬레이터로 정의하지 않는다(`tradingagents/backtest.py:9-14`, 코드 확인). 텍스트 피드가 과거 시점에 완전히 재현된다는 주장은 하지 않는다.

핵심 원본: [실행·재개](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/backtest.py#L143-L203), [등급별 평가](https://github.com/TauricResearch/TradingAgents/blob/c4544913a14ed3df5f1ed7b9e8483270ce20682a/tradingagents/backtest.py#L206-L236).

## 적용 메모

의견: 미국/한국 시장 성과 비교 시 새 run_id와 데이터 기준을 각각 고정하고, 지역 벤치마크와 평가 기간을 명시하는 편이 좋다. 원본 집계는 종목별 각 통화의 수익률이며 원화 환산 포트폴리오 성과가 아니다. 이 변경이나 비교 실험은 아직 수행하지 않았다.
