# ai-hedge-fund — 경계 기록과 적용 의견

- 분석 SHA: `78b779c1389e2d1452dc29606d2c4126d859b964` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q6, Q7
- 검증 수준 요약: 코드 확인 11 / 추론 0 / 미확인 2

## Q6. 경계 기록 {#q6}

### 판단 → 주문 경계

| 항목 | 내용 | 근거 | 검증 |
|---|---|---|---|
| 판단 결과 형식 | `DecisionRecord.final_weights: dict[ticker, 부호 있는 비중]`(주문 없음). 체결 단계에서 `CycleRecord.orders/fills`가 생김 | `hedge_fund/pipeline/models.py:43-57`, `models.py:60-86` | 코드 확인 |
| 비중 → 주문 변환 | 있음(시뮬레이션용 순수 함수): `target_shares = int(weight x equity / mark)`, 델타만 주문, 매도 우선 | `hedge_fund/pipeline/execution.py:16-53` | 코드 확인 |
| 브로커 | `Broker` Protocol + `SimBroker`(전량 체결, 슬리피지·수수료·마진 없음) + `PaperBroker`(`broker.json`). **실계좌 브로커는 없음**(Interactive Brokers/Alpaca는 ⬜) | `hedge_fund/brokers/protocol.py`, `brokers/sim.py:1-60`, `brokers/paper.py:26-74`, `ROADMAP.md:92` | 코드 확인 |
| 사람 승인 | **TUI에서만 있음.** paper 펀드에서 Enter를 누르면 곧바로 실행하지 않고 `RunConfirmScreen`이 "이번 실행이 할 일"(체결될 결정, 목표 비중, 새 결정 여부)을 보여주고 Enter/Esc로 승인·취소. 승인 전에는 ledger·브로커를 건드리지 않음 | `hedge_fund/tui/app.py:1683-1760`, `app.py:1890-1913`, `README.md:57` | 코드 확인 |
| CLI 승인 | **없음.** `aihf paper tick`은 확인 없이 즉시 실행(자동화용). 승인 기본값이라는 개념도 없다 | `hedge_fund/run.py:255-267`, `paper/tick.py:55-86` | 코드 확인 |
| 킬스위치 | `control.json`의 `halted`. `advance`와 `tick`이 가장 먼저 확인. 수동(`halt/resume`, TUI `h`/`r`) + 어떤 예외든 발생하면 자동 halt | `paper/ledger.py:126-149`, `pipeline/session.py:125-126`, `paper/tick.py:136-142`, `run.py:283-289` | 코드 확인 |
| 하드 리스크 한도 | 종목당 `max_position_pct`, 총노출 `max_gross_exposure` (mandate 필수 필드, `extra="forbid"`). **일일 손실 한도, 최대 낙폭 중단, 거래대금 한도, 레버리지 통제 외 제한은 없음** | `hedge_fund/risk/limits.py:21-31`, `fund/spec.py:81-93` | 코드 확인 |
| 중복 방어 | 결정 시 클램프, `validate_targets`로 재검증, 체결 직전 예상 포지션 재검증, 장부 대조 | `portfolio/validation.py:16-80`, `pipeline/stages.py:143-153`, `session.py:185-198` | 코드 확인 |
| `allowAiTrading` 같은 라이브 플래그 | 없음(라이브 트레이딩 미구현). VISION은 "live is opt-in and off by default"라고 선언 | `VISION.md:167` | 코드 확인(미구현) / 문서 선언은 README 급 |

### 판단 근거를 보여주는 UI (3줄 요약)

- 실행 화면(`RunSessionScreen`): 분석가 1명당 1행의 라이브 보드에 토큰이 흘러들어오며 신호·확신도·논거가 타이핑되듯 표시(`tui/app.py:930-998`, `llm/watch.py:1-13`).
- 세션 보고서(`SessionReportScreen`): 좌측 레일에 모든 신호/결정/체결, 우측에 선택 항목의 전체 논거·포트폴리오·클램프 내역(`tui/app.py:2101-2140`, `app.py:1092-1110`).
- 승인 모달(`RunConfirmScreen`): 체결할 목표 비중 요약(`tui/app.py:1623-1680`).
(모두 `코드 확인`. 화면 렌더링은 실행하지 않아 `미확인`)

## Q7. 우리 시스템에 적용 (분석자 의견) {#q7}

> 이 절은 코드 근거가 아니라 **분석자 의견**이다. 인용된 위치는 의견의 전제가 되는 코드 사실이다.

### 가져갈 것

| 요소 | 이유(의견) | 코드 사실 위치 |
|---|---|---|
| "LLM은 의견, 결정은 코드" 분리 구조 | LLM 출력을 `[-1,+1]` 단일 숫자로 제한하고 비중·한도·주문을 결정적 코드가 만든다. 우리 키움/업비트 주문 계층 앞에 그대로 둘 수 있는 가장 중요한 설계 | `signals/llm_agent.py:167-176`, `portfolio/construction.py:29-104`, `risk/limits.py:1-11` |
| 분석가 권한 메타데이터(`long_only`/`long_short`) | 프롬프트가 아니라 클래스 선언으로 숏 가능 여부를 제한. 현물 코인·국내 주식(공매도 제한)에 맞춰 `long_only` 강제하기 쉽다 | `signals/base.py:20-22`, `signals/__init__.py:28-39`, `portfolio/construction.py:72-75` |
| 기권(abstain) 규약 | LLM 실패를 "중립 투표"가 아니라 "투표 제외"로 처리해 신호가 조용히 왜곡되지 않게 한다. 단 기권 비율 경보는 우리가 추가해야 함 | `signals/llm_agent.py:92-112`, `portfolio/construction.py:69-70` |
| 이중 검증(`validate_targets`) | 신호와 한도에서 목표를 독립 재계산해 사이징 버그를 주문 전에 차단 | `portfolio/validation.py:16-80` |
| 결정 T → 체결 T+1 세션 분리 + 해시체인 ledger | 같은 종가로 판단·체결하는 낙관 편향 제거, 감사 가능한 기록. 코인은 24h라 "세션" 정의(일봉 마감 시각 등)만 바꾸면 된다 | `pipeline/session.py:11-23`, `paper/ledger.py:1-122` |
| 멱등 tick + 자동 halt + 장부 대조 | 외부 cron이 호출해도 안전. 실패 시 거래 정지 | `paper/tick.py:1-15`, `session.py:185-198` |
| PIT 데이터 계약("fail loud") | 인프라 실패를 "데이터 없음"과 구분해 백테스트 오염 방지 | `data/protocol.py:33-45`, `data/client.py:253-303` |
| blind 렌더 + 사후지식 차단 지침 | LLM이 종목을 기억해서 백테스트가 부풀려지는 문제를 줄이는 실용적 장치(완전하지는 않음) | `features/snapshot.py:95-175`, `run.py:190-194` |
| 프롬프트/응답 디스크 캐시(키=프롬프트 텍스트) | 비용 절감 + 감사. 날짜를 프롬프트에서 빼서 같은 데이터면 재호출 방지 | `llm/cache.py:1-48`, `snapshot.py:9-13` |
| YAML mandate(전략=모델 조합+블렌드 정책) | 코드 변경 없이 전략 조합 | `fund/spec.py:34-107`, `strategies/*.yaml` |

### 버릴 것 / 그대로 쓰기 어려운 것

| 요소 | 이유(의견) | 코드 사실 위치 |
|---|---|---|
| 유명 투자자 페르소나 5명 | 우리 시장(코인, 국내 주식 단기/스윙)과 데이터(공시 재무)에 맞지 않고, "스타일화된 근사"일 뿐이다(`VISION.md:65-66`도 실존 인물과 무관하며 보증이 아니라고 기록). 프롬프트 구조(체크리스트·신호 정의·확신도 척도·JSON 스키마)만 참고 | `signals/buffett.py:1-6`, `VISION.md:65-66` |
| 펀더멘털 단일 스냅샷 | 가격·수급·뉴스·거시·코인 파생 데이터가 없어 단기 판단에 부적합. LLM이 현재가도 못 본다 | `features/snapshot.py:109-136`, `druckenmiller.py:60-61` |
| 상대 사이징(확신도의 절대 크기 무시) | 종목 1개면 확신도가 낮아도 gross_target 전액 배정 후 종목 상한으로 자름. 우리는 확신도 임계값(예: 일정 미만이면 비중 0)과 절대 크기를 반영하도록 바꿔야 함 | `construction.py:96-102`, `construction.py:47` |
| SimBroker 체결 모델 | 슬리피지·수수료·호가·부분 체결 없음. 업비트/키움에는 부적합 | `brokers/sim.py:1-12` |
| 사후 채점/메모리 | 없음. 가져갈 것이 아니라 **우리가 추가할 것** | `llm_agent.py:72-73` |
| 리스크 한도 | 종목/총노출 2종뿐. 일일 손실 한도, 최대 낙폭, 변동성 연동, 거래 횟수 제한 필요 | `risk/limits.py:21-31` |

### 업비트·키움 데이터로 대체할 항목 (의견)

| 이 레포의 입력 | 우리 대체 | 비고 |
|---|---|---|
| FD `/prices/` 일봉 종가 → mark | 업비트 캔들/체결가, 키움 REST 일봉(국내·해외) | 거래일 그리드는 벤치마크 일봉으로 만드는 방식이라 코인은 24h 마감 기준 정의 필요 |
| FD `/financial-metrics/` ttm 14개 필드 | 국내 주식: DART 재무제표/공시일 기준 PIT. 해외 주식: 키움이 제공하는 재무 TR 또는 별도 공급자. 코인: 해당 없음 | 공시일(`filing_date`) 필터 원칙은 반드시 유지 |
| 수급 | 키움 `ka10059`(투자자별 매매) 등을 스냅샷 컬럼으로 추가 | 이 레포에는 없음. `DataClient` Protocol에 메서드를 추가하고 `LLMAgent.build_snapshot()`을 오버라이드하는 확장 지점이 문서화돼 있음(`llm_agent.py:125-137`) |
| PEAD(EPS 서프라이즈) | 국내는 DART 잠정실적 공시 + 컨센서스 필요(공급원 별도). 코인은 해당 없음 | |
| 코인 파생 데이터(펀딩비, OI, 공포탐욕지수) | 별도 소스 필요 | 이 레포에 없음 |
| 뉴스/감성 | 별도 수집기 필요 | 이 레포에 없음(`04-research.md`) |
| 포트폴리오 보유 | 업비트/키움 잔고 조회로 `Broker.positions()/cash()` 구현 | 브로커 내부 구현은 이 조사 범위 밖 |

### 라이선스

- MIT(`LICENSE:1-3`, `pyproject.toml:6`). 저작권 고지를 유지하면 코드 재사용이 가능하다. (`코드 확인`)
- 다만 `hedge_fund/llm/api_models.json` 모델 목록, Jev(TypeSafe) 어댑터 같은 외부 서비스 의존 부분은 우리에게 불필요하며, FD API 사용 약관은 별도(`미확인`).
- 권장(의견): `portfolio/construction.py`, `risk/limits.py`, `portfolio/validation.py`, `paper/ledger.py`, `paper/tick.py`처럼 순수 로직 모듈은 코드 재사용, 페르소나 프롬프트와 FD 의존부는 아이디어만 참고.
