# OpenAlice — 경계 기록과 적용 의견

- 분석 SHA: `87bc415260aaac92a072d89a1c6440268a3efdf1` (repos.lock.tsv와 일치해야 함)
- 분석일: 2026-10-09
- 관련 공통 항목: Q6, Q7
- 검증 수준 요약: 코드 확인 15 / 추론 1 / 미확인 0 (표의 검증 열 기준 집계)

> 범위 안내(GUIDE §0): 브로커 연동과 주문 실행의 내부 구현(어댑터, 정밀도, FX 등)은 조사하지 않았다. 아래는 **판단 결과가 주문으로 넘어가는 경계**와 **판단 근거를 보여주는 UI**만 짧게 기록한 것이다. Q7은 코드 근거가 아니라 **분석자 의견**이다.

## Q6. 경계 기록 {#q6}

### 6.1 판단 → 주문 경계

| 질문 | 답 | 위치 | 검증 |
|---|---|---|---|
| 판단 결과를 주문으로 바꾸는 코드가 있는가 | **있다, 단 변환이 아니라 "에이전트가 주문 도구를 직접 호출"하는 구조.** `placeOrder`/`modifyOrder`/`closePosition`/`cancelOrder`는 **stage**만 하고 실제 실행은 push. 코드가 thesis를 주문으로 해석하는 로직은 없음 | `src/tool/trading.ts:671-777` | 코드 확인 |
| 결정 형식 | 주문 필드(`aliceId`, `action`, `orderType`, `totalQuantity`/`cashQty`, 가격 필드, `takeProfit`/`stopLoss`) + 사유 문자열 `commitMessage`. 비중(%)이 아니라 **수량 또는 금액**을 에이전트가 정함 | `trading.ts:684-710`, 스키마 상세 `03-decision.md` 4-4 | 코드 확인 |
| 비중을 정하는 코드 | **없음.** 유일한 비중 관련 코드는 선택적 `max-position-size` 가드(검사만, 산정 아님) | `guards/max-position-size.ts:5-48` | 코드 확인 |
| 흐름 | stage → commit(해시 생성, 사유 기록) → push. 대기 커밋이 있으면 추가 stage 거부, push/reject는 `expectedPendingHash` 일치 필요 | `TradingGit.ts:77-127`, `:241-250` | 코드 확인 |
| 사람 승인 단계 | **기본은 있음.** `allowAiTrading` 기본 `false` → AI의 `tradingPush`는 대기 목록만 돌려주고 "사용자가 Web UI에서 승인하라"고 응답. 사람은 Trading as Git 화면에서 push/reject | `core/config.ts:249`, `trading.ts:824-832`, `routes-trading.ts:502-527`, `ui/src/components/PushApprovalPanel.tsx:413-443` | 코드 확인 |
| 승인 면제 조건 | `allowAiTrading=true`면 AI가 직접 push. 설정은 실행 중 즉시 반영(재시작 불필요), UI에서 위험 경고+이중 확인 뒤에만 켜짐 | `main.ts:249-256`, `config.ts:244-249`(주석), `ui/src/i18n/locales/en.ts:1214`(문구) | 코드 확인(코드·주석) / 이중 확인 UI 동작은 `추론`(주석 근거) |
| 하드 리스크 한도(종목당 상한) | **opt-in 가드.** `max-position-size` 기본 25%, **계정 설정 `guards` 기본값은 빈 배열**이라 켜지 않으면 없음 | `guards/max-position-size.ts:5`, `config.ts:288-291`, `:454` | 코드 확인 |
| 하드 리스크 한도(일일 한도) | **없음.** `daily loss`, `max daily`, `kill switch`, `emergency`, `circuit` 검색 결과 중 매매 관련 항목 없음(hit는 프로세스 kill, hub 브레이커) | `src`, `services` 검색 | 코드 확인(없음) |
| 킬스위치 | 전용 기능 없음. 대용: `allowAiTrading=false`(즉시 반영), 계정 `readOnly`, 트레이딩 모드 `readonly`/`lite`(환경변수 `OPENALICE_TRADING_MODE`가 설정보다 우선) | `trading-mode.ts:24-51`, `config.ts:466-473` | 코드 확인 |
| 쿨다운/화이트리스트 | opt-in 가드 | `guards/cooldown.ts`, `symbol-whitelist.ts` | 코드 확인 |
| 가드 fail-open 지점 | (1) 알 수 없는 가드 타입은 **경고 후 건너뜀**, (2) 신규 심볼+수량 주문은 가치 추정 불가여서 **통과** | `guards/registry.ts:26-31`, `max-position-size.ts:35-37` | 코드 확인 |
| 에이전트 권한 | 매니지드 실행은 도구 승인 프롬프트·샌드박스를 끈다(`--dangerously-skip-permissions`) → 안전장치는 UTA 쪽(승인, 가드)에만 있음. 워크스페이스에서 `alice-uta` CLI 그룹을 끄는 정책은 있음(`.alice/alice-harness-config.json`의 `cli.<binary>.enabled/groups`) | `claude.ts:80`, `:274`, `alice-harness-policy.ts:10-19`, `:37-41` | 코드 확인 |
| 스케줄 실행과 주문 | 헤드리스 실행도 같은 도구 표면을 쓴다. 문서는 "timer never moves money on its own"이라고 하지만 `allowAiTrading=true`면 헤드리스에서도 push가 가능 | `self-scheduling/SKILL.md:300-302`, `trading.ts:833-845` | 코드 확인 (README/스킬과 코드 차이 기록) |
| 모드 기본값 | UTA 계정 설정이 있으면 `pro`, 없으면 `lite`(UTA 연결 안 함). 계정별 `readOnly` 기본 `false` | `trading-mode.ts:50`, `config.ts:473` | 코드 확인 |
| README 경고 | "Trading execution is beta. Start with simulator, paper, demo, or testnet accounts." | `README.md:103-107` | 코드 확인 |

### 6.2 판단 근거를 보여주는 UI (3줄 이내)

- **Trading as Git** (`ui/src/pages/TradingAsGitPage.tsx` → `PushApprovalPanel.tsx`): 대기 중인 커밋 메시지(`pendingMessage` = 에이전트가 쓴 매매 사유), 스테이지된 주문 목록, 과거 커밋 이력을 보여주고 push/reject 버튼 제공(`PushApprovalPanel.tsx:259-261`, `:344-347`, `:413-443`).
- **Inbox** (`ui/src/pages/InboxPage.tsx`): 에이전트가 보낸 마크다운 리포트와 첨부 파일, 발신 세션/Issue 출처(`origin`), 발신 세션에 답장하는 스레드(`InboxPage.tsx:1-30`, `:270-283`).
- **Issues 보드 · Tracked · 섹터 로테이션 페이지**: 예약 작업·실행 상태, `[[name]]` 링크로 묶인 종목·테마 그래프, 로테이션 표(5분 폴링, `MarketRotationPage.tsx:18`, `:66`). 모든 항목 검증: 코드 확인(페이지 파일 존재와 위 라인).

---

## Q7. 우리 시스템에 적용 (분석자 의견) {#q7}

> **이 절 전체가 분석자 의견이다.** 코드 근거가 필요한 부분은 위 문서의 `파일:라인`을 가리킨다.

### 7.1 라이선스: 아이디어만 참고

- 이 레포는 **AGPL-3.0-only**다(`LICENSE`, `package.json:103`, `README.md:185`). 의견: **코드 복사·번역·포팅은 모두 파생물 위험이 있으므로 하지 않고, 설계 아이디어와 개념(아래 목록)만 참고하는 것이 안전하다.** 네트워크 서비스로 제공하면 소스 공개 의무가 생기는 강한 카피레프트이므로, 설령 개인용이라도 나중에 외부 공개·서비스화 가능성이 있다면 더더욱 코드는 가져오지 않는다.
- 스킬 마크다운은 데이터이지만 같은 저장소 안의 저작물이다. 문장을 그대로 옮기지 말고 **구조(절차, 반증 신호 의무, 신선도 게이트)만** 우리 말로 새로 쓴다.
- 라이선스 가능 여부 요약: `코드 재사용 불가 / 아이디어 참고 가능`.

### 7.2 가져갈 것 (아이디어 단위)

| 아이디어 | OpenAlice 근거 | 우리 시스템에서의 형태(의견) | 대체 데이터(의견) |
|---|---|---|---|
| **소스 정체성(`barId`) + 소스별 능력 표기** — 같은 자산도 소스별로 다른 ID, 자동 교체 금지, 라벨에 `delayed/realtime` 노출 | `bars/types.ts:3-20`, `bar-service.ts:34-39`, `:340-350`, `:386-401` | 업비트와 키움을 서로 다른 소스로 구분하고, 결과마다 "지연 가능"을 구조화 필드로 남김 | 업비트 캔들 REST, 키움 REST 차트 조회 계열(구체 TR은 별도 확인) |
| **신선도 계약** — `asOf`, `isLatestActual`, `staleTradingDays`, "기록 나이≠피드 지연" | `bar-service.ts:152-182`, `freshness.ts:21-46` | 한국 거래일 캘린더(KRX 휴장일)를 반영해 `staleTradingDays`를 정확히 계산(OpenAlice는 주말만 제외) | KRX 휴장일 목록(출처 별도 확보) |
| **as-of 스냅샷 + 상한 후처리** — 벤더가 `end_date`를 무시해도 한 번 더 필터 | `bar-service.ts:219-244`, `snapshot.ts:101-109` | 백테스트·회고 분석의 look-ahead 방어를 응답 경계에 한 번 더 둠 | 동일 |
| **섹터 로테이션 점수** — z-score 평균 + 거래대금 점유율 변화, 방법론 문자열에 "대리 지표" 한계 명시 | `sector-rotation.ts:41`, `:132-262` | 코스피/코스닥 섹터 ETF 11~N개 유니버스로 재구현(공식은 새로 작성) | 키움 ETF 일봉 + 거래대금, 또는 지수 구성 ETF 목록 |
| **스킬 절차 문서화** — thesis의 좌/우 2면, 반증 신호 의무, priced-in 점검, 회고의 신선도 게이트 | `build-thesis/SKILL.md:26-84`, `retrospective/SKILL.md:29-44` | 프롬프트/체크리스트 템플릿으로 재작성. 반증 신호를 모니터링 훅으로 저장 | DART 재무(좌), 키움 수급 `ka10059`·가격 모멘텀(우) |
| **파일 기반 연구 서류철** — `notes/<TICKER>.md`에 claim/what-must-be-true/반증 신호를 쌓고 다음 세션이 읽음 | `build-thesis/SKILL.md:75-84`, `scan-value-chain/SKILL.md:49-65` | DB 또는 Git 저장소의 종목별 thesis 문서 | — |
| **Issue 파일 스케줄(`when` + 본문 프롬프트)** — 스케줄 선언이 작업 정의와 같은 파일, 스캐너는 해석하지 않음, 마커는 성공 후에만 기록 | `scanner.ts:259-403`, `marker-store.ts:2-18` | 단순한 정기 실행기로 차용. **거래일 캘린더와 장 시각 게이트는 코드로 앞단에 추가**(OpenAlice는 프롬프트 조건에 맡김, `docs/workspace-issues-and-scheduling.md:218-221`) | KRX 휴장일, 업비트는 24/7 |
| **stage → commit(사유) → 해시 고정 승인** — 승인 대상이 바뀌면 거부, 대기 커밋 1개 제한 | `TradingGit.ts:77-127`, `:241-250`, `routes-trading.ts:508-515` | 우리 주문 계층 앞단에 "제안 큐+사유 기록+해시 승인" | 키움/업비트 주문 API(구현은 우리 몫) |
| **마스터 스위치 기본 OFF + 실시간 토글** | `config.ts:249`, `main.ts:249-256` | 자동 주문 허용을 기본 OFF로, 재시작 없이 끌 수 있게 | — |
| **구조화 오류 + 다음 행동 제안** — `{error:{kind,message,suggestion}}`, "데이터 소스 오류는 스크립트가 아니라 소스를 바꿔라" | `calc-v2/evaluator.ts:201-204`, `tool/quant.ts:76-81` | LLM 도구 반환 규약으로 차용 | — |
| **보드 캐시: TTL + stale-while-error + `meta.origin/stale`** | `reference/cache.ts:19-53`, `hub.ts:20-77` | 저빈도 데이터(거시, 재무)를 캐시하면서 stale 여부를 응답에 표기 | DART, 한국은행 ECOS(의견: 이 레포 밖의 후보) |
| **도구 설명문의 커버리지 고지** — "빈 결과≠아무 일 없음" | `archive.ts:197-200` | 우리 뉴스/공시 도구 설명에 동일 취지 문장 | — |
| **의도적으로 코드 계산 vs LLM 해석 분리** — 지표는 코드, 해석은 에이전트 | `evaluator.ts:305-326`, `alice-analysis/SKILL.md:158-161` | 지표·점수는 결정적 코드, 서술은 LLM | — |

### 7.3 버릴 것(그대로 쓰지 않을 것)

| 항목 | 이유(의견) | 근거 |
|---|---|---|
| **외부 CLI 에이전트 하네스 전체**(권한 프롬프트·샌드박스 해제 상태로 코딩 에이전트에 셸을 줌) | 주문 경로와 같은 호스트에서 무제한 셸을 가진 에이전트를 돌리면 키 유출·오주문 표면이 커진다. 우리는 판단 전용 샌드박스와 주문 계층을 분리하는 편이 낫다 | `claude.ts:80`, `:274` |
| **LLM이 수량/금액을 직접 지정**하는 주문 스키마 | 한도 위반 가능. 의견: 에이전트는 방향·확신·근거까지만 내고 **수량은 결정적 코드(예: 위험 기반 사이징)**가 정하게 한다 | `trading.ts:690-691` |
| **가드 기본 OFF + 알 수 없는 가드 타입 건너뜀 + 신규 심볼 통과** | 전부 fail-open. 우리는 한도를 기본 ON, 설정 오류는 fail-closed(거래 불가)로 | `config.ts:454`, `registry.ts:26-31`, `max-position-size.ts:35-37` |
| **일일 손실 한도/킬스위치 부재** | 직접 구현 필요(일일 한도, 전체 정지 플래그) | 6.1절 |
| **미국 중심 데이터 소스**(SEC 심볼, FRED/FMP/OECD, 섹터 ETF 11개) | 한국 시장에는 직접 적용 불가. 구조만 재사용 | `aggregate-search.ts`, `reference/macro.ts:25-46` |
| **비공식 Yahoo(yfinance) 의존을 기본 가격원으로 삼는 것** | Yahoo는 비공식 클라이언트를 IP·지문으로 차단(429/crumb)하고 OpenAlice는 자동 재시도·폴백이 없어 에이전트에게 오류만 설명한다. 우리는 공식 API(업비트·키움)를 기본으로 하고 폴백 정책을 코드로 가짐 | `errors.ts:54-93`, `bar-service.ts:34-39` |
| **RSS 28개 영문 피드** | 한국어 소스 없음. 발행시각 누락 시 수집시각 대체는 look-ahead 위험 | `news/config.ts:34-268`, `rss.ts:120` |
| **거래일 캘린더를 프롬프트에 위임** | 휴장일 오발사를 LLM의 조용한 종료에 의존 | `docs/workspace-issues-and-scheduling.md:218-221` |
| **사후 채점 부재** | 우리는 판단 로그를 N거래일 뒤 수익률로 채점하는 장치를 직접 추가해야 함 (이 레포에는 참고 구현이 없음) | `03-decision.md` 4-7 |
| 낡은/불일치 문서·설정 잔재(`agent.maxSteps`, 도구 설명의 `calculateIndicator` 언급 등) | 참고 가치 없음 | `config.ts:242-269`, `tool/market.ts:27` |

### 7.4 업비트·키움 데이터로 대체할 항목 (의견)

| OpenAlice 항목 | 한국 시스템 후보(의견) | 비고 |
|---|---|---|
| yfinance 봉 / 브로커 봉 | 업비트 캔들, 키움 REST 일·분봉 | 소스 능력(realtime/delayed)과 신선도 필드를 우리 계약으로 정의 |
| FMP 재무비율/재무제표 | DART 재무제표(공식 공시) | 시점(공시일) 기준 as-of 필터를 코드로 강제(OpenAlice는 펀더멘털 as-of 없음) |
| 공매도/수급(yfinance 공유통계 등) | 키움 `ka10059`(투자자별 수급) | GUIDE 예시값. 응답 필드는 별도 확인 필요 |
| 내부자 거래(Form 4) | DART 임원·주요주주 특정증권 소유상황보고 | 의견, 구체 API는 별도 확인 |
| 섹터 ETF 로테이션 | 한국 섹터 ETF 거래대금·수익률 | 공식은 새로 구현 |
| FRED/OECD 거시 | 한국은행 ECOS, 통계청 등 + OECD `south_korea`(OpenAlice도 지원) | 의견 |
| RSS 뉴스 | 한국 언론사 RSS, DART 공시 목록 | `windowRss` 식 날짜 창 조회 설계 참고 |
| Deribit 기간구조/옵션 | 업비트에는 파생 없음 → 필요 시 별도 소스(바이낸스 공개 API 등) | 의견 |
| 코인 전용(펀딩비·OI·공포탐욕지수) | OpenAlice도 미제공(CCXT 계정 전용 `getFundingRate` 제외) | 직접 수집 필요 |

### 7.5 종합 판단 (의견)

OpenAlice에서 가장 배울 만한 것은 "AI가 똑똑한 판단을 한다"가 아니라 **(a) 데이터 계약(소스 정체성, 신선도, as-of), (b) 스킬 문서로 판단 절차를 외부화하는 방식, (c) 주문 직전의 승인 경계 설계**다. 반대로 우리 요구(업비트·키움, 한국 장 운영, 결정적 리스크 한도)에는 **판단→주문 연결부를 결정적 코드로 더 두껍게** 만들어야 한다. 이 레포는 그 부분을 사람 승인에 의존한다.
