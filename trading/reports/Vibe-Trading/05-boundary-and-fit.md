# Vibe-Trading — 판단→주문 경계, 우리 시스템 적용 의견

- 분석 SHA: `e532650b527ba3fb146ef00d533f6fc5040d5d2d` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: Q6, Q7
- 검증 수준 요약: 코드 확인 28 / 추론 0 / 미확인 0

> 범위 메모: 브로커 내부 주문 구현은 조사하지 않았다. 업비트·KIS는 **조회 경로와 주문 가드 경계**만 다룬다.

<a id="q6"></a>
## Q6. 경계 기록

### 6-1. 판단 → 주문

| 질문 | 답 | 근거 | 검증 |
|---|---|---|---|
| 판단 결과를 주문으로 바꾸는 코드가 있는가 | **있다. 단 변환 코드가 아니라 "LLM이 직접 부르는 주문 도구"다.** 도구 `trading_place_order`(symbol, side, quantity 또는 notional, order_type, limit_price, time_in_force)를 에이전트가 호출한다. 판단 객체(등급·점수)를 받아 비중을 계산해 주문으로 바꾸는 결정적 코드는 없다 | `agent/src/tools/trading_connector_tool.py:730-803`, `agent/src/trading/service.py:697-761` | 코드 확인 |
| 비중을 정하는 코드 | 메인·swarm 경로에서는 없음(LLM과 CRO 프롬프트가 정함). 백테스트에서는 신호 [-1,1]을 `sum(abs(w)) <= 1`로 정규화하는 코드가 있음 | `agent/backtest/engines/base.py:247-248`, `investment_committee.yaml:147,176` | 코드 확인 |
| 사람 승인 단계 | **주문 건별 승인은 없다.** 사람이 개입하는 곳은 한 번, mandate 커밋(`POST /mandate/commit`)이다. 에이전트는 mandate를 쓸 코드 경로가 없고, 제안 도구(`propose_mandate_profiles`)는 "제안"만 저장한다. 기본 만료 30일 | `agent/src/live/mandate/commit.py:1-25,419`, `agent/src/tools/propose_mandate_tool.py:1-20` | 코드 확인 |
| 기본값 | 선택 프로필 기본값은 `ibkr-paper-local`(**페이퍼**). 프로필 선택 파일이 없으면 이 값 | `agent/src/trading/profiles.py:30,95-107` | 코드 확인 |
| 페이퍼 주문 | 가드 없이 커넥터 `place_order`로 직행(페이퍼 계좌) | `agent/src/trading/service.py:736-737` | 코드 확인 |
| 라이브 주문 | `execute_live_order`(SDK 커넥터) 또는 `LiveOrderGuardTool`(MCP, Robinhood) 게이트 경유 | `agent/src/trading/service.py:739-761`, `agent/src/live/sdk_order_gate.py:1-22` | 코드 확인 |
| 자율 라이브 러너 | 틱마다 에이전트에 mandate 전문을 프롬프트로 박아 "한도 안에서 자유롭게 거래하라"고 지시. 한도는 하드 백스톱 | `agent/src/live/runtime/runner.py:219-263` | 코드 확인 |

### 6-2. 하드 리스크 한도 (코드가 집행)

| 한도 | 값의 출처 | 동작 | 근거 | 검증 |
|---|---|---|---|---|
| 1회 주문 금액 상한 `max_order_notional_usd` | 사용자 mandate | 초과 시 정량 위반 → 재승인 요구(`PAUSE_FOR_REAUTH`) | `agent/src/live/mandate/model.py:46-73`, `agent/src/live/enforcement.py:562-566` | 코드 확인 |
| 총 노출 상한 `max_total_exposure_usd` | 사용자 mandate | 주문 후 노출 계산해 초과 시 위반. 보유 중 가격 불명 포지션이 하나라도 있으면 **전체 fail-closed**(모든 주문 차단) | `agent/src/live/enforcement.py:293-310,371-420,580-590` | 코드 확인 |
| 레버리지 `max_leverage` | 사용자 mandate (1.0=현금만) | 초과 시 위반 | `agent/src/live/enforcement.py:595` | 코드 확인 |
| 허용 상품 `allowed_instruments` | 사용자 mandate, 비면 전부 거부 | 구조 위반 → 즉시 DENY(재승인으로도 불가) | `agent/src/live/mandate/model.py:62-73`, `agent/src/live/order_guard.py:229-231` | 코드 확인 |
| 유니버스(자산군·시총·거래대금·제외 종목) | 사용자 mandate | 구조 위반 DENY | `agent/src/live/mandate/model.py:76-96` | 코드 확인 |
| 일일 주문 수 `max_trades_per_day` | 사용자 mandate | 파일 락 + UTC 일자 카운터. 브로커 응답이 에러가 아닌 확정 ALLOW에서만 증가 | `agent/src/live/order_guard.py:23-26,205-221` | 코드 확인 |
| kill switch | 파일 센티넬 `<runtime_root>/live/HALT`(전역), 브로커별 `HALT` | **LLM 협조와 무관**하게 모든 주문 직전에 검사. 켜지면 주문 도구는 등록 목록에서도 빠짐 | `agent/src/live/halt.py:1-16`, `agent/src/live/registry.py:196-200`, `agent/src/live/order_guard.py:161-166` | 코드 확인 |
| 만료 | `consent.expires_at` 경과 시 DENY, 러너는 틱마다 선제 점검 | 코드 확인 | `agent/src/live/order_guard.py:153-159`, `agent/src/live/runtime/runner.py:5-14` | 코드 확인 |
| 가드 순서 | mandate 없음/버전 불일치 → 만료 → halt → 계좌 바인딩 → 주문 의도 파싱 → 수량 주문의 시세 환산(불가 시 DENY) → 포지션·잔고 조회 → `check_mandate` | 전부 fail-closed | `agent/src/live/order_guard.py:134-231` | 코드 확인 |
| 의도 파서 | 브로커별 `extract_order_intent`. 등록된 것은 **Robinhood 하나**(MCP 경로). 파싱 불가면 DENY | `agent/src/live/extractors/__init__.py:27-29` | 코드 확인 |
| 어드바이저리(관찰용) | 외부 리스크 검토는 **fail-open**, 기본 꺼짐, 주문을 막지 못함 | `agent/src/live/advisory/__init__.py:1-22`, `agent/src/live/order_guard.py:94-98` | 코드 확인 |
| 감사 | 모든 결정이 감사 이벤트로 기록. 해시 체인 JSONL 모드는 옵트인 | `agent/src/live/order_guard.py:27-30`, `agent/src/governance/ledger.py:1-30` | 코드 확인 |

### 6-3. 업비트·KIS 커넥터 (조회 경로와 가드 경계만)

| 항목 | Upbit | KIS | 근거 | 검증 |
|---|---|---|---|---|
| 프로필 | `upbit-paper-sdk`(읽기), `upbit-paper-trade`(로컬 시뮬 주문), `upbit-live-sdk-readonly` | `kis-paper-sdk`, `kis-paper-trade`(KIS 모의투자 서버에 **진짜 주문**), `kis-live-sdk-readonly` | `upbit/profiles.py:20-66`, `kis/profiles.py:22-67` | 코드 확인 |
| 라이브 주문 | **없음.** `is_paper`가 아니면 즉시 에러 | **없음.** 비페이퍼 설정은 즉시 에러 `_LIVE_ORDER_ERROR` | `upbit/sdk.py:407-411`, `kis/sdk.py:91-97,494-498` | 코드 확인 |
| 이유(코드 주석) | 업비트는 샌드박스·런타임 paper/live 구분 수단이 없어 키 한 쌍이 같은 계좌를 읽음 → 구조적으로 페이퍼 상한 | KIS는 호스트 분리로 라이브 가능하나 mandate에 `KR_EQUITY` 자산군이 없어 후속 과제로 남김 | `upbit/profiles.py:6-13`, `kis/profiles.py:10-15` | 코드 확인 |
| 조회 API | 계좌(KRW 잔고·locked), 포지션(비KRW 잔고, 평균단가), 미체결/체결, 티커, 캔들(분/일/주/월) | 잔고(TR `TTTC8434R`/`VTTC8434R`), 포지션, 일별 체결(`TTTC0081R`), 현재가, 일·주·월 차트 | `upbit/sdk.py:222-371`, `kis/sdk.py:58-66,272-465` | 코드 확인 |
| 조회 인증 | 시세는 무인증, 계좌·주문 조회는 JWT(access/secret) | OAuth 토큰(만료 120초 전 갱신, 토큰 캐시), 호스트가 paper/live 판별 | `upbit/sdk.py:574-611`, `kis/sdk.py:53-56,84-89` | 코드 확인 |
| 신뢰도 단서 | 429 처리·재시도 없음(HTTP≥400이면 에러 반환) | "KIS 계정 없이 작성해 TR_ID·필드명을 실계정으로 검증하지 못했다"고 파일 머리에 명시 | `upbit/sdk.py:602-605`, `kis/sdk.py:16-19` | 코드 확인 |
| 가드 경계 | 라이브 주문 경로가 없으므로 mandate 게이트에 닿지 않음. 분류표는 조회=READ, 주문·취소=WRITE, 미등록은 WRITE(fail-closed) | 동일 | `upbit/classification.py:13-23`, `kis/classification.py:13-23`, `agent/src/live/registry.py:51-70` | 코드 확인 |
| 한국 자산군 | mandate `AssetClass`는 us_equity, us_etf, hk_equity, cn_equity, in_equity, crypto, forex뿐. **KR 없음**, 한도 단위는 USD, 트리거 시장은 `us_equity`와 `crypto`만 | 동일 | `agent/src/live/mandate/model.py:34-43`, `agent/src/live/runtime/triggers.py:112-127` | 코드 확인 |

### 6-4. 판단 근거를 보여주는 UI (3줄)

- 에이전트 화면: 도구 호출 타임라인과 grounding 진행 상태(수정 중/수치 삭제 릴리즈)를 이벤트로 표시 (`frontend/src/pages/Agent.tsx:782-790`).
- 스케줄 화면: 작업별 마지막 Verdict의 "심볼 상태" 목록, 직전 대비 결과 변화(델타), 기록 시각, 읽기 불가 시 "unreadable" (`frontend/src/pages/Scheduled.tsx:328-370`).
- 라이브 화면 `Runtime.tsx`는 **열어보지 않았다**(미확인).

<a id="q7"></a>
## Q7. 우리 시스템에 적용 (분석자 의견)

> 이 절은 코드 근거가 아니라 **분석자 의견**이다. 우리는 업비트(코인), 키움 REST(국내·미국 주식)를 쓴다.

### 라이선스

MIT (`LICENSE:1-3`, `pyproject.toml:6`). 코드 재사용 가능. 저작권 고지만 유지하면 된다. 의견: 코드를 통째로 가져오기보다 아래 **설계 아이디어**를 우리 코드로 다시 쓰는 편이 낫다. 레포가 크고(`agent/src` 하위 1단계 `.py` 합계 약 14만 줄, `wc -l` 기준) 중국·인도·이란 시장 코드가 대부분이다.

### 가져갈 것

| 우선 | 항목 | 이유 | 우리 데이터로 대체할 부분 |
|---|---|---|---|
| 1 | **주문 직전 결정적 게이트의 순서와 fail-closed 원칙** (`order_guard.py:134-231`): mandate → 만료 → halt 파일 → 의도 파싱 → 시세 환산 불가 시 DENY → 포지션·잔고 조회 → 한도 검사 | LLM이 주문 도구를 직접 호출하는 구조에서 "LLM 협조와 무관한" 최후 방어선의 모범 | 한도 단위를 USD가 아니라 KRW·코인 수량으로. 한국 자산군(코스피·코스닥·원화 코인)과 KRX 장 시간(09:00–15:30 KST) 추가가 필요(원본에는 없음) |
| 1 | **kill switch를 파일 센티넬로** (`halt.py:1-16`) | 에이전트 루프가 멈춰도 동작 | 그대로 |
| 1 | **Verdict 엄격 파서 + 상태 어휘 선언** (`verdict.py:103-138`) | 자유 서술 브리핑 끝에 기계가 읽는 상태 줄만 두고, 형식이 틀리면 추측 없이 폐기 | 한국 플레이북용 상태 어휘(예: `HOT/QUIET`) |
| 2 | **grounding 아이디어**: "수치는 이번 세션 도구 결과의 어느 호출에서 왔는가"를 선언·검증, 위반은 삭제 후 릴리즈 (`context.py:41-72`, `ledger.py:321-398`) | LLM 환각 수치 차단. 7천 줄 규모라 전부 이식은 과함 | 의견: 우리 도구 결과에 `call_id`를 붙이고, 최종 답변의 수치 선언만 대조하는 최소판을 새로 작성 |
| 2 | **swarm DAG의 의존성 게이트** (`runtime.py:920-960`) | 리스크 담당이 실패하면 PM을 실행하지 않음(거부권 우회 방지) | 그대로 개념 사용 |
| 2 | **한국 엔진 규칙** (`korea_equity.py:61-136,157-228`): 호가 단위표, ±30% 상하한 계산 절차, 롱온리, 직전 종가 기준 판정, 비용 스택 | 백테스트 현실성. 틱 그리드·상하한은 키움 데이터로 검증 가능 | 세율·수수료는 코드 주석이 "주기적으로 개정되니 확인하라"고 명시 → 우리가 현행 값으로 다시 채워야 함 |
| 3 | **소스별 조정주가 caliber 라벨링과 혼합 경고** (`registry.py:260-304,392-446`) | 소스 교체 시 단위·조정 불일치 사고 방지 | 키움 일봉 수정주가 여부를 같은 라벨로 기록 |
| 3 | **조회 전용 커넥터 구조**: 조회=READ, 주문=WRITE, 미등록=WRITE (`classification.py`) | 새 브로커 도구가 기본값으로 차단됨 | 키움 REST 조회·주문 함수에 같은 분류표 |
| 3 | 업비트 캔들 매핑(분 1/3/5/15/30/60/240, 일·주·월, 1회 200개 한도)과 포지션 정규화(심볼, 평균단가, `unit_currency`) (`upbit/sdk.py:296-371,241-273`) | 우리도 업비트를 쓴다 | 업비트 API 문서와 대조 후 사용. 원본은 429 처리가 없으므로 호출 제한 처리를 추가 |

### 버릴 것

- 중국·인도·이란 소스 22종과 Eastmoney 기반 수급·뉴스 도구 전부(한국 종목 미지원).
- LLM이 매번 쓰는 `bash` 스크립트로 리스크 수치를 계산하는 방식(재현성 없음). 우리는 계산을 고정 코드로 두는 편이 맞다.
- swarm PM이 방향·비중·손절을 **자유 서술로 결정**하는 구조. 우리는 LLM 의견을 구조화 JSON으로 받고 비중은 결정적 코드가 정해야 한다(원본 ai-hedge-fund 계열 구조가 더 가깝다).
- "분석만, 조언 금지" 원칙. 우리는 매매 판단이 목적이라 원칙 4는 해당 없음. 대신 원칙 1–3(수치는 도구 출처, as-of 표기, 도구가 안 준 것은 채우지 않음)은 유지할 가치가 크다.
- 사후 채점이 없다(Q4-7). 가져갈 게 없다. 우리가 직접 만들어야 한다.

### 업비트·키움 데이터로 대체할 항목

| 원본 항목 | 대체 의견 | 비고 |
|---|---|---|
| 한국 가격(pykrx, Naver 기반 수정주가) | 키움 REST 일봉 | 원본 pykrx는 선택 의존성이라 조용히 yahoo로 강등됨(`registry.py:220`). 우리는 소스 강등 시 명시 에러가 낫다 |
| 수급(원본엔 한국용 없음) | 키움 `ka10059`(투자자별 수급) | GUIDE의 예시 TR. 원본에서 가져올 코드 없음 |
| 재무(원본엔 한국용 없음) | DART | 원본 `get_fundamentals`는 SEC 전용 |
| 한국 뉴스(원본 미지원) | 별도 한국 뉴스 소스 필요 | 원본에서 가져올 것 없음 |
| 코인 시세·캔들 | 업비트 REST 직접 | 원본 백테스트 체인엔 업비트가 없어 OKX·Binance로 대체됨. 원화 마켓은 직접 연결 필요 |
| 공포탐욕지수 | alternative.me 그대로 | `sentiment_tool.py:1-9`. 크립토 전용 |
| 거시 | FRED(키 필요) 유지 가능, 한국 거시는 별도 | `fred_macro_tool.py:1-17` |

### 한 줄 평가 (의견)

판단 로직 자체는 참고할 것이 적고(LLM이 자유롭게 결정), **"LLM이 주문 도구를 가졌을 때 코드로 어떻게 막는가"와 "LLM 답변의 수치를 어떻게 검증하는가"** 두 가지가 가치가 크다.
