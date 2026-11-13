---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - README.md
  - api/app.py
  - data_provider/akshare_fetcher.py
  - data_provider/base.py
  - data_provider/us_index_mapping.py
  - docs/full-guide_EN.md
  - src/data/stock_index_loader.py
  - src/services/market_symbol_utils.py
  - src/services/stock_code_utils.py
  - src/services/stock_index_remote_service.py
  - src/services/stock_list_parser.py
  - main.py
  - src/scheduler.py
  - src/services/runtime_scheduler.py
  - src/services/scheduled_analysis_claim.py
  - src/core/trading_calendar.py
  - src/config.py
  - .github/workflows/00-daily-analysis.yml
depends: []
status: ready
---

# 트리거·스케줄·시장 달력

> CLI 단발 실행, 일일 스케줄 및 Actions 트리거에서 시장별 거래일을 거쳐 분석을 호출한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름

1. CLI 단발 실행 또는 일일 scheduler, API runtime scheduler, Actions가 분석을 요청한다(R-01~R-03).
2. 스케줄러는 등록 시각 또는 즉시 실행을 선택하고 최신 설정과 watchlist를 읽는다(R-02, R-04).
3. 정시 발생분은 실행 예정 시각과 작업 스냅샷을 SQLite에 원자적으로 claim한다(R-05).
4. 시장별 현지 날짜의 거래일 여부로 종목과 시장 복기 지역을 걸러낸다(R-06~R-07).
5. 남은 작업을 분석 pipeline 경계에 전달하고 결과·실패를 호출 경로별로 처리한다(R-08~R-09).

### 1.2 범위·통합 지점

- 제공: 발생 시점, 시장별 필터, 중복 claim 및 실행 제어. 시장 복기와 종목 pipeline은 실행 요청과 성공/실패 결과만 다룬다.
- 제외: 수집·판단·보고서 내부, 배포와 알림, 이벤트 모니터 자체. Actions 파일은 배포 설정이 아니라 실행 트리거를 정의하므로 예외로 포함한다.
- 선행: `depends: []`. 수집 기능의 자료형을 직접 소비하지 않고 실행 함수와 성공/실패 경계만 필요하다. 호출자는 설정·시계·거래소 calendar·SQLite·분석 실행기를 제공한다.
- 상태: 일일 job과 runtime 상태는 프로세스 메모리, claim은 설정된 SQLite에 저장된다. 재시작 시 메모리 상태는 소멸한다. 설정은 reload될 수 있다(R-04~R-05, R-09).

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| CLI | `--schedule`, `--no-run-immediately`, `--stocks`, `--market-review`, `--no-market-review`, `--force-run` | 일일 모드, 기동 즉시 실행 억제, 쉼표 종목 목록, 시장 복기만, 복기 제외, 거래일 검사 우회. 스케줄 모드의 `--stocks`는 무시한다(R-01~R-04). |
| 설정 | `SCHEDULE_ENABLED=false`, `SCHEDULE_TIME=18:00`, `SCHEDULE_TIMES` 빈 값, `SCHEDULE_RUN_IMMEDIATELY`·`RUN_IMMEDIATELY` 기본 true | 시간은 `HH:MM` 24시간제. 다중 시각은 쉼표로 분리, 유효 항목 중복 제거·정렬; 없으면 단일 시간, 그것도 유효하지 않으면 18:00. 실행 즉시 설정 우선순위는 C-02(R-02). |
| 필터 | `TRADING_DAY_CHECK_ENABLED=true`; `MARKET_REVIEW_ENABLED=true`; `MARKET_REVIEW_REGION=cn` | `false` 또는 `--force-run`은 거래일 필터 우회. `effective_region`의 `None`은 설정 기본값 사용, 빈 문자열은 복기 생략(R-06~R-07). |
| Runtime | `run_now()` → `{accepted, running, reason?}`; `status()` → enabled, running, schedule_times, next_run_at, last_run_at, last_success_at, last_error, last_skipped_at, last_skip_reason | 비동기 접수이며 성공 완료 응답이 아니다. 시각은 ISO 문자열 또는 null. 상태는 프로세스 수명에 한정(R-09). |
| claim | 예정 `datetime`, workload → bool/예외 | naive datetime은 프로세스 시간대로 UTC 변환. DB 기본 `./data/stock_analysis.db`; occurrence와 workload hash가 복합 키(R-05). |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 일반 CLI | `RUN_IMMEDIATELY`가 true면 단발 분석을 실행한다. 명시적 `--market-review`는 설정상 복기 비활성 여부와 별개로 시장 필터를 적용하고 결과 없으면 exit 1, 휴장이면 exit 0이다. 일반 단발 실패의 exit 처리에는 C-03의 분기 제한이 있다. | 코드 확인 |
| R-02 | `--schedule` 또는 `SCHEDULE_ENABLED=true` | 로컬 scheduler는 매일 프로세스 로컬 시간에 등록하며 30초 간격으로 poll한다. 시작 즉시 실행 기본 true, `--no-run-immediately`가 끈다. 시각 provider 갱신 때 이전 job을 교체하고 provider 오류면 기존을 유지한다. 종료 신호는 현재 작업을 마치고 루프를 끝낸다. | 코드 확인 |
| R-03 | Actions | 월~금 `0 10 * * 1-5` UTC(베이징 18:00), 수동 `full` 기본·`market-only`·`stocks-only`, `force_run=false`. 동시성 그룹 `stock-analysis`, 진행 중 작업 취소 false, job timeout 기본 30분, 시작 전 난수 0~59초 지연. 각 모드는 CLI 단발 호출이며 scheduler occurrence claim이 아니다. 외부 Actions 서비스의 실제 보장은 미확인. | 코드 확인 |
| R-04 | 정기 실행 | 스케줄 시각 provider는 설정 파일 또는 시작 시 process 환경값을 읽는다(C-04). 정기 발생분은 설정 reload 후 watchlist를 refresh해 스냅샷으로 고정한다. 즉시 실행은 예정 시각이 없어 claim하지 않는다. | 코드 확인 |
| R-05 | 같은 DB의 같은 예정 시각·동일 workload | stock 목록은 trim·대문자·중복 제거·정렬해 hash한다. portfolio가 있으면 종목 목록 대신 portfolio를 쓴다. 옵션과 복기·언어·보고서 종류도 hash에 포함한다(C-05). SQLite `INSERT OR IGNORE`로 최초 1개만 실행하고 나머지는 `ScheduledAnalysisSkipped`; DB 오류는 실행하지 않고 전파한다. 성공 claim 때 7일보다 오래된 claim을 삭제하며 실패·timeout 뒤에도 해당 claim을 남긴다. 따라서 자동 재시도 보장은 없다. | 코드 확인 |
| R-06 | 거래일 검사 활성 | 시장별 현지 날짜를 사용해 cn/hk/us/jp/kr/tw에 대해 거래소 session 여부를 확인한다. 달력 미설치·미지원 시장·예외는 열린 것으로 간주한다. 종목은 시장 인식 후 닫힌 시장만 제거하고 미인식은 유지한다. 시장 미인식 코드가 registry에 등록된 중국 지수이면 cn으로 취급한다. bare 6자리 코드는 지수 충돌이 있어도 stock이며 시장 판정에서 cn이다. HK는 `hk` 접두 또는 `.hk` 접미 숫자 1~5자리, bare 숫자 4~5자리다. | 코드 확인 |
| R-07 | 종목·복기 지역 필터 | 복기 지역 `both`는 cn,hk,us,jp,kr 전체, 쉼표 목록은 같은 순서의 열린 시장만 남긴다. 유효 토큰이 없으면 cn; tw는 종목 필터에 있으나 복기 지역 집합에는 없다. 남은 종목과 복기 지역이 모두 없으면 성공으로 skip. 검사 우회 시 원래 종목과 region `None`을 반환한다. | 코드 확인 |
| R-08 | 분석 결과·예외 | 정기 분석의 `False`는 실패로 바뀌며 claim 오류·실행 예외도 실패다. CLI scheduler의 안전 래퍼는 예외를 기록하고 다음 poll을 계속한다. 빈 설정 watchlist와 복기가 모두 없으면 dry-run이 아닌 경우 실패, 예상 보고서가 전혀 없을 때 실패다. 실제 pipeline 내부의 부분 성공은 해당 기능 경계에 위임한다. | 코드 확인 |
| R-09 | API runtime scheduler | owner이고 활성일 때만 시작, 설정 재조정은 stop 후 재시작. 즉시 실행 또는 `run_now()`는 별도 watchdog thread와 spawn process로 접수하며 프로세스 내 공유 lock이 바쁘면 skip/거절하고 claim하지 않는다. 기본 timeout 2700초, 환경 `DSA_RUNTIME_SCHEDULER_TIMEOUT_SECONDS` 정수는 최소 60초, 잘못된 값은 기본값. timeout이면 자식 프로세스 트리를 종료하고 last_error 기록, lock 해제. 결과 없는 종료·자식 미종료도 실패로 기록한다. stop은 job 해제와 자식 종료를 수행한다. | 코드 확인 |

- 미결정: 없음. R-06의 index 판정은 C-10~C-12의 registry·parser를 사용한다. 명시 canonical/alias를 먼저 조회하고, 미등록 CSI 형태는 unsupported다. SH/SZ 접두 판정은 정규화 후 registry에 일치해야 하며, bare 숫자는 index로 승격하지 않는다. registry 후보는 remote cache·bundled·static을 수정 시각순으로 검사하고 semantic 검증 및 bundled 활성 index canonical의 비퇴행 조건을 적용한다. 모든 후보가 실패하면 빈 registry를 캐시한다.
- 확인 한계: 원본 실행·설치 없이 코드를 읽었다. 거래소 calendar의 실제 데이터 정확성, 외부 scheduler의 지연·재시도와 다중 호스트에서 같은 SQLite 파일을 공유하는 환경은 검증하지 않았다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `src/scheduler.py:27-48, 92-146, 149-178, 223-309, 402-487` `Scheduler`, `normalize_schedule_times`, `run_with_schedule`; `src/scheduler.py:51-79` `GracefulShutdown` | 정규화·등록·갱신·poll·오류 포착. 같은 이름의 앞선 `_refresh_daily_schedule_if_needed`는 뒤의 정의가 덮어쓴다. | R-02, R-04, R-08 |
| C-02 | `src/config.py:1258-1270, 1798-1839, 2259-2279` `Config` | 설정 기본값과 legacy 즉시 실행 우선순위. `_resolve_env_value`와 bootstrap 환경 판정은 해당 config helper 계약에 따른다. | R-02, R-06 |
| C-03 | `main.py:367-395, 478-526, 805-888, 1133-1152, 1227-1259, 1262-1299, 1773-1805, 1807-1860, 1882-1920` | CLI 분기, 필터, pipeline 경계·실패 전달. | R-01, R-04, R-06~R-08 |
| C-04 | `main.py:1436-1442, 1471-1546` | 스케줄 watchlist 및 설정 reload·provider 우선순위. | R-04 |
| C-05 | `src/services/scheduled_analysis_claim.py:17-91` | 스냅샷, workload hash, SQLite 스키마·원자적 claim·보존. | R-05 |
| C-06 | `src/core/trading_calendar.py:29-51, 125-175, 618-687` | 거래소·시간대 매핑, 시장 판정과 fail-open, 복기 지역 계산. | R-06~R-07 |
| C-07 | `src/services/market_symbol_utils.py:15-64`; `data_provider/us_index_mapping.py:16-43, 46-94`; `data_provider/akshare_fetcher.py:212-224` | suffix·미국 코드·홍콩 코드 판단. 홍콩 판정의 `_is_hk_code`는 `data_provider/akshare_fetcher.py:130-159`이다. | R-06 |
| C-08 | `src/services/runtime_scheduler.py:24-87, 247-355, 367-380, 483-643, 698-790, 809-835`; `api/app.py:260-287, 297-309` | 소유권, 기본 인자, watchdog·상태·lifecycle. 종료 helper는 `src/services/runtime_scheduler.py:90-216`을 함께 읽는다. | R-09 |
| C-09 | `.github/workflows/00-daily-analysis.yml:3-29, 32-42, 465, 536-549` | cron, 수동 선택 및 CLI dispatch. | R-03 |
| C-10 | `src/services/stock_list_parser.py:52-87, 127-157, 176-188, 191-253, 257-287, 290-407, 465-520, 526-583, 586-626, 632-727, 729-815, 855-980, 981-1005, 1037-1136` | registry·지수 판정, 키 정규화, parser 분기. `matched_index`는 bare 숫자의 충돌 정보이지 지수 승격이 아니다. | R-06 |
| C-11 | `src/data/stock_index_loader.py:23-53, 56-67, 106-114, 203-230, 404-517, 520-651`; `src/services/stock_index_remote_service.py:68-70, 91-135` | registry 원본 후보·캐시·검증과 fallback. remote cache 경로 상수 및 payload 지원 시장은 `src/services/stock_index_remote_service.py:20-29` 참조. | R-06 |
| C-12 | `src/services/stock_code_utils.py:21-35, 39-81, 121-195, 226-247`; `src/services/market_symbol_utils.py:15-64, 88-97`; `data_provider/base.py:273-291` | parser가 사용하는 stock 코드 정규화·명시 거래소·suffix·BSE 판정. | R-06 |

### 1.6 수락 사례

출처: 모두 구현에서 도출. 분석 실행기·calendar·시계 및 SQLite는 제어 가능한 대체물로 가정하며 외부 서비스나 실제 거래소 휴일을 검증하지 않는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | `SCHEDULE_TIMES=18:00,09:30,18:00`, 즉시 실행 false | 09:30과 18:00 두 daily job, 기동 즉시 실행 없음. |
| T-02 | R-05 | 동일 DB, 동일 workload·예정 UTC 시각으로 두 번 claim | 첫 번째만 실행, 두 번째 skip. 첫 실행 실패 후에도 claim은 남음. |
| T-03 | R-06~R-07 | 열린 시장이 kr뿐이고 `005930.KS`, `AAPL`, 복기 `both` | 한국 종목과 `kr` 복기만 전달. |
| T-04 | R-06~R-07 | calendar 사용 불가, cn 종목과 cn 복기 | fail-open으로 모두 유지한다. |
| T-05 | R-06~R-07 | 닫힌 cn만 대상, 복기 cn; 이후 `--force-run` | 첫 실행은 성공 skip; 강제 실행은 원래 목록과 기본 region 전달. |
| T-06 | R-09 | runtime 분석 lock 보유 중 `run_now()` | accepted false, running true, reason `analysis_already_running`; claim 없음. |
| T-07 | R-09 | 자식이 timeout까지 응답하지 않음 | 자식 트리 종료, last_error 기록, lock 해제. |
| T-08 | R-06 | bundled registry를 사용하는 입력 `sh000300`, `000300.CSI`, `000300`, 미등록 CSI | 앞의 둘은 index로 cn, bare 코드는 stock으로 cn, 미등록 CSI는 parser상 unsupported이며 시장 미인식 시 fail-open 유지. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 | 확인 방법·한계 |
|---|---|---|
| R-01 | C-03; `main.py:1896-1920` | 모드 dispatch·반환 분기 직접 확인. |
| R-02 | C-01, C-02, C-03, C-04 | schedule 라이브러리 동작 자체는 실행하지 않음. |
| R-03 | C-09 | workflow는 실행 동작 정의이므로 CI 제외의 예외로 열람. 외부 서비스 보장은 확인하지 않음. |
| R-04 | C-01, C-03~C-05 | 예정 시각과 즉시 실행의 차이 직접 확인. |
| R-05 | C-05 | SQLite 트랜잭션·키·보존 정책 확인. |
| R-06 | C-03, C-06~C-07, C-10~C-12 | 코드·registry helper closure 확인. 핵심 근거 [calendar](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/core/trading_calendar.py#L125-L175). |
| R-07 | C-03, C-06 | 필터와 지역 계산 확인. |
| R-08 | C-01, C-03, C-05 | 오류가 CLI scheduler wrapper에서 포착됨. |
| R-09 | C-08 | watchdog·상태 확인. [runtime scheduler](https://github.com/ZhuLinsen/daily_stock_analysis/blob/ce364e457aab288863a5707e7b3df79786ad07f2/src/services/runtime_scheduler.py#L483-L601). |
| T-01~T-08 | 대응 R-ID의 C-ID | 코드로 기대값을 도출했으며 테스트 실행 아님. |

README `README.md:151`은 비거래일에 실행하지 않는다고 요약하지만, 코드는 미인식 종목·달력 오류를 fail-open하고 시장별로 부분 실행한다. 또한 그 문장의 평일 18:00은 Actions cron이며 내장 scheduler는 매일 프로세스 현지 시각에 등록된다(C-01, C-06, C-09). `docs/full-guide_EN.md:202, 791-801`도 Actions 기본과 로컬 scheduler를 나누어 읽어야 한다.
