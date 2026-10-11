# ai-hedge-fund — 다음 단계

- 분석 SHA: `78b779c1389e2d1452dc29606d2c4126d859b964` (repos.lock.tsv와 일치)
- 분석일: 2026-10-09
- 관련 공통 항목: 전체
- 검증 수준 요약: 코드 주장 없음(범위·질문 문서). 미확인 항목은 아래 체크리스트 참조

## 확인한 범위

- 전부 열어 읽음: `hedge_fund/` 의 `run.py`, `models.py`, `paths.py`, `data/{client,cached,protocol,sessions}.py`, `features/{snapshot,breakpoints}.py`, `signals/*.py`(6개 + base, llm_agent, __init__), `fund/{spec.py,example.yaml}`, `strategies/*.yaml`, `portfolio/{construction,validation}.py`, `risk/limits.py`, `pipeline/{session,stages,execution,models}.py`, `paper/{tick,ledger,deployed}.py`, `brokers/*.py`, `llm/{client,contract,cache,registry}.py`, `backtesting/fund.py`, 루트 `README.md`, `hedge_fund/README.md`, `.env.example`, `pyproject.toml`.
- 부분만 읽음: `data/models.py`(필드 목록), `backtesting/engine.py`(머리 docstring과 클래스 시그니처), `llm/watch.py`(머리), `tui/app.py`(승인·실행·보고서 화면, warm 로직 위주. 총 3206줄), `ROADMAP.md`/`VISION.md`(grep + 일부).
- 열지 않음: `event_study/*`, `tui/{shared,keys}.py` 대부분, `*/test_*.py` 전체, `poetry.lock`, `assets/`.
- 실행은 하지 않았다(읽기 전용 규칙). 모든 결론은 정적 코드 읽기 기반.

## 미확인 항목 체크리스트

- [ ] FD API 응답의 실제 필드 값/단위(예: `revenue_growth`가 비율인지 %인지, `market_cap`이 공시일 기준 시총인지). 모델 정의만 확인함
- [ ] FD가 `filing_date`를 모르는 행을 서버에서 제외한다는 문서화(`data/client.py:107-113`)의 실제 동작
- [ ] 장기 paper 운영 시 `company_facts`/`earnings_history` 캐시가 TTL 없이 오래된 값을 반환하는지(`data/cached.py:94-104`, 추론으로 표기)
- [ ] 실제 LLM 호출 1회당 입력/출력 토큰 수와 비용(실행 없이 계산 불가)
- [ ] 백테스트의 기권(abstain) 비율, 캐시 적중률, 신호 분포(실행 결과 필요)
- [ ] blind 프롬프트가 실제로 종목 식별을 얼마나 막는지(`snapshot.py:102-105`가 한계를 인정)
- [ ] TUI 화면의 실제 렌더링(코드 확인만 함)
- [ ] `tui/app.py`의 빌더(`BuilderScreen`)·백테스트 화면 세부, `event_study` 모듈
- [ ] FD API 이용 약관(코드 재사용과 별개)

## 다음에 볼 파일과 함수

| 파일 | 함수/클래스 | 이유 |
|---|---|---|
| `hedge_fund/tui/app.py` | `_report_detail`, `_session_nav`, `BuilderScreen` | 판단 근거 UI 표시 항목 상세 확인 |
| `hedge_fund/data/models.py` | `FinancialMetrics`, `EarningsData` | 필드 단위·의미(우리 DART/키움 매핑 설계용) |
| `hedge_fund/backtesting/engine.py` | `BacktestEngine.run_alpha` | 단일 모델 연구 하네스(PEAD 검증)가 펀드 경로와 어떻게 다른지 |
| `hedge_fund/event_study/engine.py` | CAR 계산 | PEAD 근거 연구 방식 |
| `hedge_fund/pipeline/test_*.py`, `portfolio/test_construction.py` | 테스트 케이스 | 경계 조건(숏 권한, flat_reason, 리프레시 평가) 의도 확인 |
| `VISION.md`, `ROADMAP.md` | 전체 | 향후(라이브 브로커, 승인 게이트, 전략 생성기) 설계 방향 |

## 분석 중 생긴 질문

1. 종목 1개 + 낮은 확신도에도 gross_target 전액을 배정하는 상대 사이징은 의도된 설계인가? (`portfolio/construction.py:47`의 docstring은 "does not calibrate conviction"이라고 인정)
2. paper(unblind)와 backtest(blind)의 프롬프트 차이가 성과 기대치에 얼마나 영향을 주는가?
3. 기권이 누적될 때(모델 장애) 경보/중단 조건이 필요하지 않은가? 현재는 조용히 중립으로 진행된다.
4. 같은 의견이 반복되면 캐시로 같은 결과를 내므로 "의견 안정성"이 높다. 이 장점을 우리 시스템에서 유지하면서 가격·뉴스 같은 빠르게 변하는 입력을 넣을 수 있는가?
5. 뉴스(`get_news`)가 Protocol에 이미 있는데 소비자가 없다. 작성자의 다음 단계는 어떤 페르소나일까?
