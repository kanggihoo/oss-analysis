---
sha: "ce364e457aab288863a5707e7b3df79786ad07f2"
created: 2026-11-11
updated: 2026-11-11
sources:
  - src/market_analyzer.py
  - src/services/screening/pipeline.py
  - src/services/screening/LICENSE
  - src/core/backtest_engine.py
  - src/services/portfolio_risk_service.py
---

# Q1. 시장 복기·스크리닝·백테스트·보유 위험과 코드 규모

## 기능의 의미

- 시장 복기: 시장 지수·상승/하락 업종·테마·뉴스를 모아 시장 전체 상황을 설명하는 보고서. `_build_review_prompt`는 지수 가격/등락률, 업종·테마 순위, 뉴스 최대 6건을 조립한다. `generate_market_review`는 LLM 보고서 생성 입구다. 과거 추천의 정답률 평가와 구분한다. 근거 `src/market_analyzer.py:779-790, 1652-1690`, 코드 확인.
- 스크리닝: 분석할 종목을 먼저 골라내는 과정. `screen`은 시장 snapshot에 hard filter를 적용하고 점수를 계산한 뒤 선택적으로 LLM ranking을 수행한다. `market` 허용값은 구현상 cn/us다(docstring의 cn only와 다름). 전체 종목 각각에 상세 LLM 보고서를 만드는 것과 경계가 다르다. 근거 `src/services/screening/pipeline.py:51-136, 202-232, 329, 414`, 코드 확인. 거래량·가격 등 어떤 조건을 적용할지는 전략별 후속 조사 필요.
- 백테스트: 이 레포의 `evaluate_single`은 이미 작성한 과거 분석과 이후 일봉을 대조하는 사후 평가다. 시작가 대비 기간 말 수익률, 방향 적중, 손절·익절 도달과 가상 청산을 계산한다. 같은 일봉에서 손절·익절 모두 도달하면 순서를 알 수 없어 ambiguous로 기록하고 시뮬레이션은 손절 우선으로 처리한다. 근거 `src/core/backtest_engine.py:158-240`, 코드 확인. 전체 과거 시점에서 LLM을 다시 실행하는 기능이라고 확대 해석하지 않는다.
- 보유 위험: `get_risk_report`가 보유 포트폴리오 snapshot을 받아 종목 집중도, 업종 집중도, 자산 낙폭, 손실 경고, decision signal 위험을 반환한다. 근거 `src/services/portfolio_risk_service.py:39-101`, 코드 확인. 여기서 본 코드는 보고서 생성이며 자동 매도 실행은 확인하지 않았다.

## 보유 위험의 구체 계산

- 종목 집중도: 종목 평가액 / 총 보유 평가액 ×100. 같은 종목의 계좌별 보유액을 합친다. `portfolio_risk_service.py:282-320`, 코드 확인.
- 낙폭: 일별 총자산 snapshot에서 이전 최고액 대비 하락률을 계산한다. 현재·최대 낙폭을 반환하고 최대 낙폭으로 경고한다. `portfolio_risk_service.py:465-525`, 코드 확인.
- 손실 경고: 평균 매입가 대비 현재가 하락률. 설정 속성이 없을 때 fallback은 손실 10%, 접근 비율 0.8이므로 8%부터 접근 경고, 10%부터 triggered다. 종목 집중도 35%, 낙폭 15%, 관측 기간 180일도 이 메서드의 fallback이며 전체 설정 기본값은 별도 확인이 필요하다. `portfolio_risk_service.py:56-62, 524-560`, 코드 확인.

설명용 가상 예: 시장 복기는 “오늘 반도체 업종이 강했다”, 스크리닝은 “그중 조건을 충족한 후보 10개”, 백테스트는 “지난 매수 판단 이후 실제 상승·손절 여부”, 보유 위험은 “현재 자산이 한 종목에 50% 집중”이라는 서로 다른 질문을 다룬다. 예시는 실제 실행 결과가 아니다.

## 소스 규모

기준 SHA의 git 추적 파일 중 런타임 디렉터리 src/data_provider/api/bot/apps/templates와 루트의 py/js/jsx/ts/tsx/css/html/mjs/cjs를 집계했다. tests/test/__tests__, test_*, *.test.*, *.spec.*, docs/evals/scripts는 제외했다. Markdown·JSON·YAML·lockfile·이미지도 제외한다. 물리 줄수에는 주석·docstring·프롬프트가 포함되므로 실행문 수나 주석을 제외한 SLOC와 같지 않다. 원본 코드는 실행하지 않았다. 집계 검증 수준: 코드 확인(고정 SHA 파일 목록과 파일 내용 계수).

| 범위 | 파일 | 물리 줄수 | 빈 줄 제외 |
|---|---:|---:|---:|
| src | 246 | 147,451 | 131,089 |
| data_provider | 21 | 18,068 | 15,649 |
| api | 41 | 11,990 | 10,372 |
| bot | 22 | 5,502 | 4,506 |
| 루트 진입점 | 3 | 2,060 | 1,759 |
| apps | 204 | 56,098 | 51,914 |
| 합계 | 537 | 241,169 | 215,289 |

원자료: [source-lines.json](../../../artifacts/daily_stock_analysis/source-lines.json). 백엔드 쪽 합계는 185,071줄, 앱은 56,098줄이다.

규모 분류는 분석자 의견이다. 이 답변에서만 사용하는 편의 기준으로 소형 <1만 줄, 중형 1만~10만 줄, 대형 ≥10만 줄을 두면 이 레포는 대형이다. 보편 표준이나 복잡도 평가가 아니며, 기능 결합·의존성·테스트 품질은 줄수로 판단할 수 없다.

## 후속 범위와 라이선스 보정

행 8의 시장 복기·스크리닝과 행 9의 평가·보유 위험은 목적과 경계가 달라 스펙 작성 시 분리하는 것이 적절하다(분석자 의견). 이번 질문은 범위 승인으로 간주하지 않는다. 시장 복기·스크리닝·과거 분석 평가·보유 위험 보고서는 기능 스펙 후보로 기록한다.

추가로 screening은 AlphaSift 파생 코드이며 `src/services/screening/LICENSE:1-4`는 Apache-2.0이다. 루트 MIT만으로 전체 코드를 설명할 수 없으므로 overview 라이선스 정보를 보정한다(코드 확인).
