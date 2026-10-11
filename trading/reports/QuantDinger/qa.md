# QuantDinger — 질문·답변 검증 기록

- 분석 SHA: `ba8cd667acca3e934bbc1cb354922eff413393dc`
- 질문자: Opus 5.5 / 답변자: Sonnet 5.5
- 진행 라운드: 1
- 상태: 완료

## 질문 현황

| ID | 질문 요약 | GUIDE 항목 | 상태 | 확정 라운드 |
|---|---|---|---|---|
| R1-Q1 | CN/FX/선물/MOEX 분석에서 전문 보고서가 예외로 빠져 게이트·리스크플랜이 생략되는가 | Q1, Q4-6 | 해소 | R1 |
| R1-Q2 | 뉴스 `sentiment` 라벨을 수집기가 어느 키에서 읽는가(Finnhub 뉴스) | Q1 | 해소 | R1 |
| R1-Q3 | 홍콩 리서치 캐시(`hk_research:{코드}`)의 실제 TTL 값 | Q2 | 해소 | R1 |
| R1-Q4 | 매크로·뉴스 실패가 `failed_items`에 기록되어 품질 배수 감점이 발동할 수 있는 경로가 있는가 | Q2, Q4-3 | 해소 | R1 |
| R1-Q5 | `call_llm_api`의 재시도·폴백 모델·대체 제공자 순서 | Q2, Q4-6 | 해소 | R1 |
| R1-Q6 | 6시간 캐시된 매크로 관측의 `as_of`가 무엇으로 찍히는가(신선도 판정) | Q3 | 해소 | R1 |
| R1-Q7 | LLM 완전 실패 시 합의만으로 BUY/SELL이 최종 결정까지 살아남는가 | Q4-6, Q4-5 | 해소 | R1 |
| R1-Q8 | LLM이 dict가 아닌 JSON을 반환하면 분석 전체가 `error`가 되는가 | Q4-6 | 해소 | R1 |
| R1-Q9 | 덮어쓰기 문턱(15)과 합의 결정 임계(±20, 보정값)의 실제 관계 | Q4-3, Q4-5 | 해소 | R1 |
| R1-Q10 | 앙상블에서 실패 모델의 기본 HOLD가 투표에 포함되는지와 최종 필드의 출처 모델 | Q4-2, Q4-5 | 해소 | R1 |
| R1-Q11 | 사용자 피드백(`user_feedback`)이 점수·프롬프트·보정에 쓰이는가 | Q4-7 | 없음 확정 | R1 |
| R1-Q12 | `agent_v1/research.py`·`mcp_server/`가 fast_analysis 또는 research_agent를 노출하는가 | Q5, Q6 | 없음 확정 | R1 |

---

## Round 1

### 질문 (질문자)

#### R1-Q1. 비지원 시장(CN/FX/선물/MOEX)에서 전문 보고서 게이트가 생략되는가
- GUIDE 항목: Q1(시장별 차이), Q4-6
- 왜 묻는가: `01-data.md` Q1-3 표의 CNStock·Forex/Futures/MOEX 행과 `03-decision.md` 4-6 "지원 안 하는 시장" 행이 `추론`이다. `contracts.py:19`의 `Market` 리터럴에 해당 시장이 없다는 사실만으로 "`professional_report_error` → 품질 게이트·리스크플랜 미적용(fail-open)"을 결론냈고, `next.md` 3절 (a)도 미확인으로 남겼다. 빌더가 리터럴 검증 이전에 시장을 정규화·매핑하거나 다른 분기로 보내는지 확인되지 않았다.
- 질문: `market="CNStock"`(및 Forex/Futures/MOEX)로 `FastAnalysisService.analyze()`가 실행될 때, `professional_report` 빌드 경로가 스냅샷 계약 검증에서 예외를 던져 `fast_analysis.py:573-578`의 except 분기로 들어가는가, 아니면 그 전에 시장 매핑·조기 반환 등 다른 분기가 있는가?
- 답변 완료 조건: 시장 값이 `builder.py`에 들어가서 `contracts.py`의 검증에 닿기까지의 호출 순서(`파일:라인` 각 단계)와, 예외가 발생하는 지점의 원문 인용. 그 결과 최종 응답의 `decision`·`position_size_pct`가 어느 값으로 남는지까지.

#### R1-Q2. 뉴스 감성 라벨은 수집기가 어디에서 읽는가
- GUIDE 항목: Q1(감성)
- 왜 묻는가: `03-decision.md` 4-3 객관 점수표 "감성 라벨의 출처" 행이 `추론`이다. "Finnhub 뉴스에 감성 필드가 없는 것으로 알고 있어(외부 API 스키마 기억)"라는 근거로 "감성 점수 ≈ 지정학 정규식 패널티"라고 결론냈다. 감성 가중치 25%의 실효성을 좌우하는 주장이다.
- 질문: `market_data_collector.py`의 Finnhub `company_news`/`general_news` 결과 변환 코드(약 `:2469-2569`)는 각 뉴스의 `sentiment`를 어느 키에서 어떤 기본값으로 채우는가? 그 외에 코드가 헤드라인 텍스트로 감성을 계산하는 경로가 있는가?
- 답변 완료 조건: `sentiment`를 대입하는 라인의 원문 인용(읽는 키와 기본값), 감성 점수 함수(`fast_analysis_scoring.py:557-625`)가 그 값을 읽는 라인. 텍스트 기반 감성 계산이 없다면 grep 패턴(`sentiment`, `positive`, `negative`, `bullish`, `polarity` 등)과 조사 범위. Finnhub 응답 스키마 자체는 정적 확인 불가로 분리해 적을 것.

#### R1-Q3. 홍콩 리서치 캐시의 실제 TTL
- GUIDE 항목: Q2(캐시)
- 왜 묻는가: `01-data.md` Q2-3 캐시 표 "홍콩 리서치" 행이 `미확인`("값 미확인")이고 `next.md` 3절 체크리스트에도 남아 있다.
- 질문: `hk_research.py:226-229`에서 키 `hk_research:{코드}`로 쓰는 캐시의 만료 시간은 몇 초인가?
- 답변 완료 조건: 쓰기 호출부의 원문 인용과, TTL이 결정되는 곳(`data_providers/__init__.py`의 TTL 테이블 키·기본값 등)의 `파일:라인`과 숫자.

#### R1-Q4. 매크로·뉴스 실패가 품질 배수 감점으로 이어지는 경로가 있는가
- GUIDE 항목: Q2(실패 처리), Q4-3
- 왜 묻는가: `01-data.md` Q2-5 "`failed_items` 한계" 행이 `추론`이다. 헬퍼가 예외를 삼켜 `failed_items`에 `macro`/`news`가 거의 들어가지 않으므로 0.85/0.8 감점이 사실상 발동하지 않는다고 했다. `03-decision.md` 4-3 "품질 배수" 행은 이 감점을 정상 동작처럼 적어 두어 두 문서의 무게가 다르다.
- 질문: `collect_all()`에서 `failed_items`에 `"macro"` 또는 `"news"`를 추가하는 코드 라인이 존재하는가? 존재한다면 그 라인에 도달하는 조건(어떤 예외/어떤 반환값)은 무엇인가?
- 답변 완료 조건: `failed_items`에 append/add 하는 모든 라인 목록(원문 인용)과, 매크로·뉴스 헬퍼(`:2329-2466`, `:2469-2569`)가 예외를 밖으로 던지는지 여부를 보여 주는 try/except 원문. 도달 경로가 없다면 "없음 확정"과 grep 범위.

#### R1-Q5. `call_llm_api`의 재시도·폴백 순서
- GUIDE 항목: Q2(호출 제한과 실패 처리), Q4-6
- 왜 묻는가: `01-data.md` Q2-5 "재시도·백오프" 행이 "`call_llm_api` 내부 재시도 세부는 미확인"이고, `next.md` 3절·4절 1번에도 남아 있다. R1-Q7(LLM 실패 시 동작)의 전제다.
- 질문: `LLMService.call_llm_api`(`llm.py:1097-1330` 부근)는 한 요청이 실패했을 때 몇 번, 어떤 모델·제공자 순서로 재시도하며, 모든 시도가 실패하면 예외를 던지는가 빈 값을 돌려주는가?
- 답변 완료 조건: 재시도 루프와 폴백 모델 목록이 결정되는 라인의 원문 인용(기본 폴백 `openai/gpt-4o-mini` 포함 여부), 최종 실패 시 동작(raise/return)의 라인, 그리고 `safe_call_llm`(`:1403-1445`)이 그 결과를 어떻게 받는지.

#### R1-Q6. 캐시된 매크로 관측의 `as_of`
- GUIDE 항목: Q3(데이터 신선도)
- 왜 묻는가: `01-data.md` Q2-2 "as_of 폴백" 행이 "해석은 추론: 매크로가 6시간 캐시여도 fresh로 표기됨"이다. `02-schedule.md` Q3-4 "시세·지표·매크로" 행은 같은 내용을 `코드 확인`으로 적어 검증 수준이 서로 다르다.
- 질문: 증거 스냅샷이 매크로 관측(`macro.*`)을 만들 때 `as_of`에 넣는 값은 무엇인가? 매크로 dict에 캐시 저장 시각이나 데이터 시각 필드가 있다면 스냅샷이 그것을 쓰는가 무시하는가?
- 답변 완료 조건: `snapshot.py`에서 매크로 관측을 생성하는 라인과 `as_of`/`retrieved_at` 대입 라인의 원문 인용, 수집기가 반환하는 매크로 dict의 키 목록(`market_data_collector.py:2329-2466`에서 시각 필드 존재 여부).

#### R1-Q7. LLM 완전 실패 시 합의만으로 나온 BUY/SELL이 최종까지 살아남는가
- GUIDE 항목: Q4-6, Q4-5
- 왜 묻는가: `00-overview.md` 핵심 발견 3과 `03-decision.md` 4-6이 "LLM 없이 BUY/SELL 산출 가능"을 핵심 주장으로 내세우지만 "논리 추적, 실행 재현 없음"이고 `next.md` 3절 (b)에 미확인으로 남아 있다. 덮어쓰기 이후의 지표 충돌 가드·저확신도 가드·전문 보고서 게이트가 폴백 응답(요약 "Analysis failed", `_llm_contract` 경고)을 감지해 HOLD로 내리는지는 추적되지 않았다.
- 질문: `safe_call_llm`이 `default_struct`를 반환한 경우, 그 이후 `fast_analysis.py`(`:970-1150`)와 `professional_report/builder.py`·`quality.py` 어디에서도 LLM 실패(폴백 여부, `report` 키, `unknown_llm_field:report` 경고, "Analysis failed" 요약)를 근거로 결정을 HOLD로 바꾸거나 분석을 중단하는 분기가 없는가?
- 답변 완료 조건: 폴백 구조가 만들어지는 라인부터 최종 `decision`이 확정되는 라인까지의 호출 순서(`파일:라인`). LLM 실패를 검사하는 분기가 있으면 그 원문, 없으면 grep 패턴(`Analysis failed`, `_llm_contract`, `valid`, `unknown_llm_field`, `fallback`, `llm_failed` 등)과 조사 범위를 포함한 "없음 확정".

#### R1-Q8. LLM이 dict가 아닌 JSON을 반환할 때의 동작
- GUIDE 항목: Q4-6
- 왜 묻는가: `03-decision.md` 4-6 "LLM이 JSON이 아닌 형태" 행이 `추론`이다. 리스트 등이 오면 `dict(payload or {})`에서 예외가 나 분석 전체가 `error`가 된다고 판단했으나, 그 사이 `safe_call_llm`이나 `validate_llm_analysis`에 타입 검사가 있는지 확인되지 않았다.
- 질문: `safe_call_llm`의 `json.loads` 결과가 list·str·number일 때, 그 값이 `validate_llm_analysis`에 도달하기 전에 dict 여부를 검사하거나 `default_struct`로 바꾸는 코드가 있는가? 없다면 예외는 어느 `except`에서 잡혀 응답이 어떻게 되는가?
- 답변 완료 조건: `llm.py:1403-1445`의 파싱·반환 라인과 `llm_contract.py:56-83`의 입력 처리 라인 원문, 예외를 잡는 상위 `except`(`fast_analysis.py:1146-1149` 등)의 원문과 반환 형태.

#### R1-Q9. 덮어쓰기 문턱 15와 합의 결정 임계 ±20의 관계
- GUIDE 항목: Q4-3, Q4-5
- 왜 묻는가: `03-decision.md` 4-3 "덮어쓰기 문턱" 행은 "기본 임계 ±20이 이미 15보다 커서 15는 사실상 무의미"라고 했고, `next.md` 5절 첫 질문도 같은 의문을 남겼다. 그런데 합의 결정(`consensus_decision`)이 보정 임계값(후보 10~30)을 쓰는지, 고정 ±20을 쓰는지, `consensus_abs`가 합의 점수의 절댓값과 같은지가 명시되지 않아 "무의미" 판단의 전제가 확인되지 않았다.
- 질문: `consensus_decision`을 정하는 라인은 어떤 임계값(보정 DB 값 또는 고정값)으로 점수를 BUY/SELL/HOLD로 바꾸며, `consensus_abs`는 무엇으로 계산되는가? 그 결과 "합의가 방향성인데 `consensus_abs < min_abs_override`"인 경우가 코드상 가능한가?
- 답변 완료 조건: `consensus_decision`·`consensus_abs`·`min_abs_override` 각각의 대입 라인 원문(`fast_analysis.py:719-801,956-968` 부근)과 `_score_to_decision`이 임계값을 고르는 라인(`:1494-1521`). 가능/불가능 결론과 그 조건(예: 보정 임계 < 15일 때만).

#### R1-Q10. 앙상블 투표에서 실패 모델의 HOLD 포함 여부와 최종 필드 출처
- GUIDE 항목: Q4-2, Q4-5
- 왜 묻는가: `03-decision.md` 4-2 "앙상블" 행은 "동률이면 첫 모델"이라는 규칙을 "Python 동작 기반 추론"으로 적었고, 다수결 이후 `confidence`·`entry_price`·`position_size_pct` 등이 어느 모델의 값인지는 적지 않았다. 또 `safe_call_llm`이 실패 시 HOLD 기본 구조를 돌려주므로 실패한 모델이 HOLD 한 표로 집계될 수 있는데 보고서에 언급이 없다.
- 질문: `fast_analysis.py:506-526`에서 (a) 호출에 실패해 `default_struct`를 받은 모델의 `HOLD`도 `decisions`에 그대로 집계되는가, (b) 최종 결과의 `decision` 외 필드(확신도·가격·포지션·evidence_claims)는 어느 모델의 응답에서 오는가, (c) 동률일 때 선택 규칙은 무엇인가?
- 답변 완료 조건: 해당 구간 원문 인용(투표 집계, `most_common`, `decisions.index(vote)`, `.copy()`·`update`)과 각 (a)(b)(c)에 대한 확정 답. 실패 응답을 걸러 내는 코드가 있으면 그 라인, 없으면 없음 확정.

#### R1-Q11. `user_feedback`의 사용처
- GUIDE 항목: Q4-7
- 왜 묻는가: `03-decision.md` 4-7 "사용자 피드백" 행이 `미확인(사용처)`이고 `next.md` 3절 체크리스트에도 있다. 사후 채점·보정·메모리 주입 외에 사람 피드백이 판단에 들어가는 경로가 있는지가 메모리 구조 이해에 필요하다.
- 질문: `/feedback`로 저장된 `user_feedback` 컬럼(또는 필드)을 읽는 코드가 메모리 조회(`analysis_memory.py:557-639`), 보정(`ai_calibration.py`), 확신도 보정(`:848-916`), 프롬프트 조립 중 어디라도 있는가?
- 답변 완료 조건: 읽는 곳이 있으면 `파일:라인`과 원문, 그 값이 결정에 미치는 효과. 없으면 grep 패턴(`user_feedback`, `feedback`, `thumbs`, `rating` 등)과 레포 전체(`backend_api_python/`, `mcp_server/`) 조사 범위를 포함한 없음 확정.

#### R1-Q12. 에이전트 API·MCP 서버가 분석·리서치를 노출하는가
- GUIDE 항목: Q5, Q6
- 왜 묻는가: `04-research.md` Q5-1은 "`research_agent`의 호출처는 `ai_chat.py` 하나뿐"이라 하고, `05-boundary-and-fit.md` Q6-1은 fast_analysis 사용처를 라우트·모니터·Celery 래퍼로 한정했다. 그러나 `next.md` 3절에서 `routes/agent_v1/research.py`와 `mcp_server/`는 미확인으로 남아 있다. 외부 에이전트가 분석 결과를 받아 주문(`agent_v1/quick_trade.py`)으로 잇는 경로가 있다면 Q6 경계 서술이 바뀐다.
- 질문: `BE/routes/agent_v1/research.py`와 `mcp_server/src/quantdinger_mcp/`는 `FastAnalysisService`/`get_fast_analysis_service` 또는 `research_agent`(`execute_research` 등)를 직접 호출하거나, 그것을 감싼 HTTP 엔드포인트를 도구로 노출하는가? 노출한다면 그 결과가 같은 경로 안에서 주문 생성으로 이어지는가?
- 답변 완료 조건: 노출하면 엔드포인트·도구 이름과 호출 라인의 `파일:라인` 원문, 주문으로 이어지는지 여부의 근거. 노출하지 않으면 두 디렉터리 전체에 대한 grep 패턴(`fast_analysis`, `fast-analysis`, `analyze`, `research_agent`, `execute_research`, `ai_chat`)과 결과를 포함한 없음 확정.

### 답변 (답변자)

경로 약칭: `BE/` = `repos/QuantDinger/backend_api_python/app/`, `PR/` = `BE/professional_report/`, `SV/` = `BE/services/`.

#### R1-Q1 답변
- 결론: **확정**. CNStock/Forex/Futures/MOEX는 `build_professional_report` 안에서 예외가 난다. 다만 보고서가 든 이유("계약 `Market` 리터럴")는 맞지만 경로가 다르다. 예외 지점은 `_quality()`의 폴백 `EvidenceSnapshotV1.model_validate`이고, 이 예외는 `builder.py` 끝의 자체 try/except(`:744-748`)에 닿기 **전에** 발생해 `fast_analysis.py:573`의 except로 전파된다. 그 결과 전문 보고서(품질 게이트, 리스크플랜)는 적용되지 않고 레거시 결정이 그대로 남는다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/fast_analysis.py:1137` | `analyze()` | `self._attach_professional_report(result, data, market, symbol)` (시장 값 매핑·검사 없이 그대로 전달) | 코드 확인 |
  | `BE/routes/fast_analysis.py:88-96` | `analyze()` 라우트 | `if not market or not symbol:` 만 검사. `_resolve_analysis_instrument`(`:29-33`)는 `if str(market or '').strip() != 'Crypto' or not str(exchange_id...)` 이면 `return market, symbol` | 코드 확인 |
  | `SV/fast_analysis.py:529-541` | `_attach_professional_report` | `report = build_professional_report(data, result, data_tier=..., account_risk_budget_pct=...)` 가 `try:` 안에 있음 | 코드 확인 |
  | `PR/builder.py:553` | `build_professional_report` | `snapshot = build_evidence_snapshot(collector_payload)` — 시장 검사 없음 | 코드 확인 |
  | `PR/snapshot.py:12-16`, `:100-126` | `_MARKET_DEFAULTS`, `_instrument` | `_MARKET_DEFAULTS = {"USStock": ..., "HKStock": ..., "Crypto": ...}`, `"market": market`(= `"CNStock"` 그대로), `"asset_type": defaults.get("asset_type") or market.lower()`. 모르는 시장은 예외 없이 dict로 통과 | 코드 확인 |
  | `PR/snapshot.py:215-234`(반환 dict) | `build_evidence_snapshot` | 반환값은 `dict` (`"version": "evidence_snapshot_v1", "instrument": _instrument(payload), ...`) | 코드 확인 |
  | `PR/builder.py:556`, `:60-72` | `_quality` | `result = assess_snapshot_quality(snapshot)` 를 `try`로 호출하고 `except Exception:` 에서 `result = assess_snapshot_quality(EvidenceSnapshotV1.model_validate(snapshot))` | 코드 확인 |
  | `PR/quality.py:64-66` | `assess_snapshot_quality` | `for observation in snapshot.observations:` — 인자가 `dict`이면 `AttributeError`. 즉 레거시 경로에서는 **항상** 폴백 `model_validate`로 넘어감 | 코드 확인 |
  | `PR/contracts.py:19`, `:38` | `Market`, `InstrumentIdentity.market` | `Market = Literal["USStock", "HKStock", "Crypto"]`, `market: Market` (`:52-61` 별칭은 `us_equity/hk_equity/crypto`만) | 코드 확인 |
  | `SV/fast_analysis.py:573-578` | except 분기 | `logger.error("Professional report build failed for %s:%s: %s", ...)` / `result["professional_report_error"] = str(exc)` | 코드 확인 |

- 동작 설명 (호출 순서):
  1. 라우트는 `market`이 비어 있지 않은지만 본다(`routes/fast_analysis.py:88`). 시장 화이트리스트가 없고 `CNStock`도 그대로 `service.analyze()`로 간다. 수집기는 `CNStock`을 지원한다(`SV/market_data_collector.py:177` `if market in ('USStock', 'CNStock', 'HKStock')`).
  2. `analyze()`가 결정을 만들고(합의 오버라이드 `:970-978`, 지표 충돌 가드 `_validate_and_constrain` `:1288`, 포지션 보정 `:1048-1052`) `:1137`에서 `_attach_professional_report`를 부른다.
  3. `build_professional_report`(`builder.py:553`)는 스냅샷을 dict로 만든다. 이 단계는 시장 값을 검증하지 않는다.
  4. `builder.py:556` `_quality(snapshot)` → `assess_snapshot_quality(dict)`가 `AttributeError` → `EvidenceSnapshotV1.model_validate(dict)` → 중첩 `instrument.market: Market` 검증에서 `"CNStock"`이 리터럴에 없어 `pydantic.ValidationError`. 이 예외는 `_quality`의 `except` 블록 안에서 발생하므로 밖으로 전파된다.
  5. 예외는 `build_professional_report`를 탈출한다(`builder.py:744`의 try/except는 `:556`보다 한참 뒤라 거치지 않는다). `fast_analysis.py:573`에서 잡혀 `result["professional_report_error"]`만 채워지고 `result["professional_report"]`는 없다.
  6. 최종 응답: `decision`은 `:977`/`:1022`+지표 가드까지 거친 레거시 값, `trading_plan.position_size_pct`는 `:1048-1052`의 값(`HOLD`면 0, 아니면 `max(1, min(100, round(ps * quality_multiplier * agreement_scale)))`)이 그대로 남는다. 품질 게이트(`_apply_gate`, `builder.py:581`)와 리스크플랜(`build_risk_plan`, `:592`)에 도달하지 못하므로 `recommended_position_pct` 상한도 적용되지 않는다 = fail-open.
  7. 부수 사실: `builder.py:626-`의 `else: market_features = {"market": market, "warnings": ["unsupported_professional_report_market"]}` 분기는 4단계에서 먼저 예외가 나므로 도달 불가(죽은 코드). `response_contract='professional_report_v1'`로 호출하면 `routes/fast_analysis.py:231`에서 `'error': 'professional_report_v1 generation failed'`로 500이 되고, 기본(legacy) 계약이면 `code: 1` 정상 응답에 `professional_report_error`만 실린다.
- 조사 범위: `PR/builder.py`, `PR/contracts.py`, `PR/snapshot.py`, `PR/quality.py` 전체 읽기. `SV/fast_analysis.py:529-600,1137-1150`, `BE/routes/fast_analysis.py:29-52,73-135,226-260`. grep: `CNStock|Forex|Futures|MOEX|unsupported` (`fast_analysis.py`, `professional_report/`). 보고서 정정 필요(경미): 예외가 "스냅샷 계약 검증"이라는 점은 맞으나 정확한 발생 지점은 `builder.py:556`→`:71`이며, `contract_validation` 필드(`:744-750`)와는 무관하다. `unsupported_professional_report_market` 경고는 실제로 응답에 나오지 않는다.

#### R1-Q2 답변
- 결론: **확정**. Finnhub 뉴스 변환은 `item.get('sentiment', 'neutral')`로 `sentiment`를 채우고, 헤드라인 텍스트로 감성을 계산하는 코드는 없다. 점수 함수는 라벨이 정확히 `"positive"`/`"negative"`일 때만 센다. Finnhub 응답에 `sentiment` 키가 실제로 있는지는 **정적 확인 불가**(외부 API 스키마)이며 아래에 분리해 적는다. 추가 발견: 대체 경로인 Alpha Vantage 뉴스는 라벨을 소문자로만 바꿔(`"bullish"`, `"somewhat-bullish"` 등) 넘기므로 `"positive"`/`"negative"`와 절대 일치하지 않아 중립으로 집계된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/market_data_collector.py:2509-2522` | `_get_news` (Finnhub) | `"sentiment": item.get('sentiment', 'neutral'),` (`company_news`/`general_news('crypto'/'general')` 결과 `raw_news[:10]` 변환) | 코드 확인 |
  | `SV/market_data_collector.py:2599-2606` | `_get_news_from_search` | `"sentiment": result.sentiment,` | 코드 확인 |
  | `SV/search_models.py:22` | `SearchResult` | `sentiment: str = "neutral"` (기본값) | 코드 확인 |
  | `SV/search.py:590` | `AlphaVantageNewsProvider` | `sentiment = str(item.get("overall_sentiment_label") or "neutral").lower()` | 코드 확인 |
  | `SV/market_data_collector.py:2662` | `_get_global_major_events` | `"sentiment": "negative" if any(kw in text for kw in ["war", "conflict", "attack", "战争", "冲突", "袭击"]) else "neutral",` (유일한 키워드 기반 라벨. `FAST_ANALYSIS_INCLUDE_GLOBAL_NEWS=true`일 때만 `:2552-2558`에서 추가, 기본 false) | 코드 확인 |
  | `SV/fast_analysis_scoring.py:575`, `:601-606` | `_calculate_sentiment_score` | `sentiment = item.get("sentiment", "neutral")` / `if sentiment == "positive": positive_count += 1 / elif sentiment == "negative": negative_count += 1 / else: neutral_count += 1` | 코드 확인 |
  | `SV/fast_analysis_scoring.py:608-616` | 동일 | `net_sentiment = (positive_count - negative_count) / total` / `base_score = net_sentiment * 60` | 코드 확인 |
  | `SV/fast_analysis_scoring.py:47` | 호출 | `sentiment_score = self._calculate_sentiment_score(news)` | 코드 확인 |

- 동작 설명: `collect_all`(`:296-301`)이 `_get_news`를 부르고, Finnhub 항목은 `item.get('sentiment','neutral')`, 검색 보충 항목(`len(news_list) < 5`일 때, `:2540-2542`)은 `SearchResult.sentiment`를 그대로 담는다. `_calculate_sentiment_score`는 최대 15개 중 `asset_relevance`가 `direct/material`인 것만 보고(`:578-584`), 지정학 정규식(`geopolitical_match_level`)으로 패널티를 따로 누적(기본 하한 `SENTIMENT_GEO_PENALTY_CAP=-55`)한 뒤, 라벨이 정확히 `"positive"`/`"negative"`인 항목만 `±60` 스케일의 기본 점수로 환산한다. 따라서 (1) Finnhub 항목에 `sentiment` 키가 없으면 전부 중립, (2) Alpha Vantage 항목은 라벨 값이 어떻든 `"positive"`/`"negative"`가 아니므로 전부 중립이다. 텍스트 기반 감성 계산이 없으므로 "감성 점수 ≈ 지정학 패널티"라는 보고서 서술은 **라벨이 정확히 positive/negative로 들어올 때만 예외가 생긴다**는 조건으로 맞다.
- 정적 확인 불가 부분: Finnhub `company_news`/`general_news` 응답 JSON에 `sentiment` 키가 존재하는지, 존재한다면 값이 `positive/negative` 형태인지는 외부 API 응답에 달려 있어 코드로 알 수 없다. 갈리는 지점은 `market_data_collector.py:2521`이고, (a) 키 없음 → `'neutral'`, (b) 키가 `"positive"`/`"negative"` → 그대로 집계, (c) 다른 문자열 → 중립으로 집계. Alpha Vantage 라벨이 실제로 `Bullish/Somewhat-Bullish/...` 형태인지도 외부 스키마지만, 어떤 값이든 `"positive"`가 아닌 이상 결과는 같다.
- 조사 범위: `SV/market_data_collector.py` 전체 grep `sentiment`(`:150,298,2340-2388,2481-2568,2605,2662`), `SV/search.py`·`SV/search_models.py` grep `sentiment`, `BE/` 전체 grep `def .*sentiment`(점수 함수는 `fast_analysis_scoring.py:557` 하나; 나머지는 시장 심리/Adanos 라우트), `SV/fast_analysis*.py`·`market_data_collector.py`·`search.py`에서 `polarity|textblob|vader|bullish_words|positive_words|negative_words|"positive"|'positive'` grep — 라벨 비교는 `fast_analysis_scoring.py:601` 한 곳뿐.

#### R1-Q3 답변
- 결론: **확정**. 홍콩 리서치 캐시 TTL은 **21,600초(6시간)**. 다만 보고서가 `hk_research.py:226-229`를 "쓰기"로 지칭한 것은 부정확하다(`:226-229`는 읽기). 쓰기는 `:271`. 보고서 정정 필요(경미).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `BE/data_providers/hk_research.py:25` | `_CACHE_TTL_SECONDS` | `_CACHE_TTL_SECONDS = 21_600` | 코드 확인 |
  | `BE/data_providers/hk_research.py:226-229` | `collect_hk_research` (읽기) | `cache_key = f"hk_research:{code}"` / `cached = get_cached(cache_key)` / `if isinstance(cached, dict): return cached` | 코드 확인 |
  | `BE/data_providers/hk_research.py:269-271` | 쓰기 | `# Cache only useful results. A total outage should be retried on the next report.` / `if any(result.get(key) for key in jobs):` / `set_cached(cache_key, result, _CACHE_TTL_SECONDS)` | 코드 확인 |
  | `BE/data_providers/__init__.py:177-186` | `set_cached` | `effective_ttl = ttl or CACHE_TTL.get(key, _DEFAULT_TTL)` / `envelope = _wrap_envelope(data, effective_ttl)` / `backend_ttl = effective_ttl * SWR_MULTIPLIER` | 코드 확인 |
  | `BE/data_providers/__init__.py:122-135`, `:138-151` | `_wrap_envelope`, `_unwrap_envelope` | `"hard_until": now + max(1, int(hard_ttl))` / `return value, time.time() < hard_until` | 코드 확인 |
  | `BE/data_providers/__init__.py:76`, `:159-174` | `SWR_MULTIPLIER`, `get_cached` | `SWR_MULTIPLIER = 5`, `if not is_fresh: return None` | 코드 확인 |

- 동작 설명: `_get_hk_research`(`SV/market_data_collector.py:330-332`)가 `collect_hk_research(symbol)`을 부른다. 캐시 히트면 즉시 반환, 미스면 4개 소스(프로필·남향자금·애널리스트 기대·HKMA HIBOR)를 최대 12초 기한으로 병렬 수집한다. 소스가 하나라도 값을 줘야 캐시에 쓴다(전부 실패하면 저장하지 않아 다음 요청에서 재시도). 명시 TTL 21,600이 `CACHE_TTL` 테이블(`hk_research:{코드}` 키는 테이블에 없음)보다 우선한다. `hard_until`이 지나면 `get_cached`는 `None`을 돌려주므로 실질적 신선 구간은 6시간이다. 백엔드(Redis/MemoryCache)에는 `21600*5 = 108000`초로 저장되지만 이 값은 `get_cached`로는 읽히지 않는다.
- 조사 범위: `BE/data_providers/hk_research.py:1-280`, `BE/data_providers/__init__.py:40-230`, 호출처 grep `collect_hk_research`(`market_data_collector.py:330-332` 하나뿐).

#### R1-Q4 답변
- 결론: **정적 확인 불가**(news 한정) / **macro는 없음 확정**. `collect_all()`에는 `failed_items.append("macro")`(`:288`)와 `failed_items.append("news")`(`:304`)가 존재하지만, (macro) `_get_macro_data`가 모든 예외를 삼켜 `{}`를 돌려주므로 `:288`에 도달할 수 있는 경로가 없고, (news) `_get_news`가 예외를 밖으로 던지는 유일한 지점은 정렬 `unique_news.sort(key=...)`(`:2564`)에서 `datetime` 값이 문자열이 아닌 항목이 섞였을 때의 `TypeError`뿐인데 이는 외부 검색 제공자의 JSON 타입에 달려 있다. 또 결과가 비어 있어도(빈 매크로, 빈 뉴스) 실패로 기록되지 않는다. 따라서 `0.85/0.8` 감점(`fast_analysis.py:794-797`)은 사실상 발동하지 않는다는 보고서 서술(01-data Q2-5)이 맞고, `03-decision.md` 4-3 "품질 배수" 행은 이 감점을 정상 동작처럼 적었으므로 무게를 맞춰 "사실상 미발동"으로 정정해야 한다(보고서 정정 필요).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/market_data_collector.py:279-288` | `collect_all` macro | `data["macro"] = self._get_macro_data(market, timeout=10)` / `if data["macro"]: data["_meta"]["success_items"].append("macro")` / `except Exception as e:` / `data["_meta"]["failed_items"].append("macro")` | 코드 확인 |
  | `SV/market_data_collector.py:290-304` | `collect_all` news | `news_result = self._get_news(market, symbol, company_name, timeout=8)` / `if data["news"]: ...append("news")` / `except Exception as e:` / `data["_meta"]["failed_items"].append("news")` | 코드 확인 |
  | `SV/market_data_collector.py:2338-2465` | `_get_macro_data` | 전체가 `try:`로 감싸이고 `except ImportError as e: ... return {}` / `except Exception as e: logger.error(f"_get_macro_data failed: {e}") return {}`. 내부 개별 지표 실패도 `except Exception as e: logger.debug(f"Macro indicator {key} fetch failed: {e}")`(`:2452`), `except TimeoutError: logger.warning("Macro data fetch timed out")` | 코드 확인 |
  | `SV/market_data_collector.py:2469-2569` | `_get_news` | Finnhub 블록 `except Exception as e: logger.debug(...)`(`:2524`), 소셜 블록 `except Exception`(`:2533`), 검색 `_get_news_from_search`는 자체 `try/except`(`:2608`), 글로벌 이벤트도 자체 `try/except`(`:2680`). try 밖 코드는 `:2548-2564`의 중복 제거와 `unique_news.sort(key=lambda x: x.get('datetime', ''), reverse=True)` | 코드 확인 |
  | `SV/search_models.py:15-23` | `SearchResult` | `published_date: Optional[str] = None` (타입 힌트는 str) | 코드 확인 |
  | `SV/market_data_collector.py:2600` | 검색 뉴스 변환 | `"datetime": result.published_date or datetime.now().strftime('%Y-%m-%d'),` | 코드 확인 |
  | `SV/market_data_collector.py:213-221,257-258,274,277` | 핵심 데이터·크립토 | 이 라인들이 `failed_items`에 넣는 키는 `price/kline/fundamental/company/us_research/hk_research`와 `crypto_factors`뿐 | 코드 확인 |
  | `SV/fast_analysis.py:99-100` | `_backfill_primary_enrichment` | `while key in failed_items: failed_items.remove(key)` (제거만 하고 추가하지 않음; 대상 키는 `fundamental`/`company`) | 코드 확인 |
  | `SV/fast_analysis.py:790-801` | 품질 배수 | `if "macro" in failed_items: quality_multiplier *= 0.85` / `if "news" in failed_items: quality_multiplier *= 0.8` / 지표 누락 시 `*= 0.65` | 코드 확인 |

- 동작 설명: `failed_items`를 쓰는 곳은 `market_data_collector.py` 전체에서 `:165-166(초기화), 216-221, 257-258, 274, 277, 288, 304`뿐이고 `fast_analysis.py`에서는 제거(`:99-100`)와 읽기(`:792`)만 한다. macro: `_get_macro_data`는 `Exception` 전부를 안에서 잡아 `{}`를 반환하므로 `:281`에서 예외가 나지 않고, 빈 dict이면 success에도 failed에도 기록되지 않는다(`:284`의 `if data["macro"]`). `:283`의 `data["macro"]["HKMA"] = data.pop("hk_macro")`도 `macro`가 dict라 실패하지 않는다. news: 모든 네트워크 호출이 try/except 안이라 도달 가능한 조건은 (1) `:2564` 정렬 시 `datetime`에 `str`과 비-`str`이 섞일 때. Finnhub 항목은 항상 ISO 문자열 또는 `""`(`:2503-2512`), 검색 항목은 `published_date or 현재시각 문자열`이므로 `published_date`가 JSON 숫자 등으로 오는 외부 응답일 때만 가능. 그 외에는 도달 경로가 없다. 지표 누락 배수 `0.65`(`:802-806`)는 `indicators`가 비면 실제로 발동한다.
- 조사 범위: `grep -rn "failed_items"` 전체 `BE/`(결과: `market_data_collector.py`, `fast_analysis.py:92,99,100,792`, `professional_report/snapshot.py:459`(읽기 전용)), `market_data_collector.py:100-320, 2325-2570, 2570-2690`, `search.py` `published_date=` 대입 9곳(`:62,120,195,256,338,388,438,523,597`), `fast_analysis.py:46-101,785-810`.

#### R1-Q5 답변
- 결론: **확정**. `call_llm_api`에는 같은 모델 재시도 루프도 백오프(sleep)도 없다. 시도 순서는 "모델 후보 목록을 한 번씩"(요청 모델 → 공급자 기본 모델 → 공급자 정적 폴백 모델, 중복 제거)이고, 마지막 후보가 402/403이면 대체 공급자를 우선순위대로 시도한다. 전부 실패하면 **예외를 던진다**(빈 값 반환 없음). `safe_call_llm`이 그 예외를 잡아 `default_structure`(+`report` 문자열)를 돌려준다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/llm.py:1193-1209` | 모델 후보 | `models_to_try = [model]` / `if use_fallback:` / `configured_default = self._normalize_model_for_provider(self.get_default_model(p), p)` / `static_fallback = ...PROVIDER_CONFIGS[p].get("fallback_model")` / `for candidate in (configured_default, static_fallback): if candidate and candidate not in models_to_try: models_to_try.append(candidate)` | 코드 확인 |
  | `SV/llm.py:107-155` | `PROVIDER_CONFIGS` | OpenRouter `"default_model": "openai/gpt-5.4"`, `"fallback_model": "openai/gpt-4o-mini"`; OpenAI `gpt-5.4`/`gpt-4o-mini`; Google·DeepSeek·Grok·Atlas는 기본=폴백; MiniMax `MiniMax-M2.7`/`MiniMax-M2.7-highspeed`; LiteLLM `openai/gpt-5.4`/`gpt-4o-mini` | 코드 확인 |
  | `SV/llm.py:1211-1229` | 시도 루프 | `for current_model in models_to_try:` 안에서 공급자별 `_call_litellm / _call_google_gemini / _call_openai_compatible`를 한 번 호출하고 `return` | 코드 확인 |
  | `SV/llm.py:1232-1281` | `except LLMAPIError` | 402/403이고 마지막 후보면 `return self._try_alternative_providers(...)`; `if not use_fallback: raise`; 마지막 후보면 시도가 2개 이상일 때 `raise LLMAPIError(f"All model calls failed for {p.value}. Attempts: ...")`, 아니면 `raise`; 아니면 `continue` | 코드 확인 |
  | `SV/llm.py:1283-1319` | `HTTPError`/`RequestException`/`ValueError` | 402/403/404/429면 `continue`, 마지막 후보면 `raise`. 비-`LLMAPIError` `ValueError`도 마지막 후보면 `raise` | 코드 확인 |
  | `SV/llm.py:1321-1330` | 루프 이후 | `error_msg = f"All model calls failed for {p.value}. Last error: {last_error}"` ... `raise Exception(error_msg)` | 코드 확인 |
  | `SV/llm.py:1360-1396` | `_try_alternative_providers` | `priority_order = [DEEPSEEK, ATLASCLOUD, GROK, MINIMAX, OPENAI, GOOGLE, OPENROUTER]`, 제외 공급자·키 없는 공급자 건너뜀, 각 호출은 `try_alternative_providers=False`, 전부 실패하면 `raise Exception("All LLM providers failed. Please check your API key configurations.")` | 코드 확인 |
  | `SV/llm.py:1156-1180` | 미설정 공급자 | 명시 공급자(`LLM_PROVIDER`)가 키 없으면 `ValueError`; 명시 안 했으면 위 우선순위 리스트에서 키 있는 첫 공급자로 교체, 없으면 `ValueError("API key not configured for provider: ...")` | 코드 확인 |
  | `SV/llm.py:63-90` | `LLMAPIError` | `retryable` 속성은 계산되지만 `grep "\.retryable"`로 `llm.py` 안에서 읽는 곳이 없다(제어 흐름에 미사용) | 코드 확인 |
  | `SV/llm.py:1403-1445` | `safe_call_llm` | `except Exception as e: logger.error(f"LLM call failed: {str(e)}")` / `default_structure['report'] = f"Analysis failed: {str(e)}"` / `return default_structure` | 코드 확인 |
  | `SV/fast_analysis.py:598-599`, `:499-501` | 호출 | `if not model: model = self.llm_service.get_default_model()` 로 모델을 채워 `safe_call_llm(..., default_structure=default_struct, model=model)` 호출. `use_fallback=True`, `try_alternative_providers=True` 기본값 사용 | 코드 확인 |

- 동작 설명: `analyze()`는 요청 모델이 없으면 공급자 기본 모델을 넣으므로 첫 후보와 `configured_default`가 같아 중복 제거된다. 예: OpenRouter 기본이면 `["openai/gpt-5.4", "openai/gpt-4o-mini"]` 두 번이 상한(한 번에 한 후보, 각 후보당 HTTP 1회, 재시도·sleep 없음; `llm.py`에 `sleep`/`time` 임포트 없음). 모든 후보가 실패하면 `LLMAPIError`(후보 2개 이상) 또는 원 예외가 올라가고, 마지막 후보가 402/403이면 그 전에 대체 공급자를 우선순위대로 한 번씩 시도한다. `_call_openai_compatible` 안에도 재시도 루프는 없다(`:368-520`에 `for/while` 재시도 구문 없음, HTTP 400 이상은 즉시 `LLMAPIError`). 마지막으로 `safe_call_llm`이 `Exception`을 잡아 `default_struct`에 `report="Analysis failed: ..."`를 넣어 반환한다. `LLMAPIError`는 `ValueError`의 하위 클래스이지만 `except LLMAPIError`가 먼저라 `ValueError` 분기로 새지 않는다.
- 조사 범위: `SV/llm.py:60-155, 245-262, 321-520, 1090-1462`, grep `time.sleep|import time|retry|backoff|\.retryable`(`llm.py`는 `retryable` 속성 정의만, 제어 흐름 사용 없음; `BE/` 전체에서 `.retryable`은 `data_sources/errors.py:34`(다른 클래스) 뿐).

#### R1-Q6 답변
- 결론: **확정**. 캐시된 매크로(6시간 캐시)든 방금 가져온 값이든 비-HKMA 매크로 관측의 `as_of`는 스냅샷의 `retrieved_at`(= 수집 완료 시각 `collected_at`)로 찍혀 항상 "나이 0초"이다. 수집기가 반환하는 매크로 dict에는 시각 필드가 없고, 캐시에 들어 있던 `timestamp`는 버려진다. 보고서 01-data의 "fresh로 표기됨" 해석은 맞고(02-schedule의 `코드 확인`과 일치하도록 `추론`→`코드 확인`으로 올려도 된다). 예외는 HKMA(`as_of`를 HKMA 값에서 가져옴).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `PR/snapshot.py:368-385` | `build_evidence_snapshot` 매크로 | `for metric, value in _flatten_numeric("macro", macro_payload):` ... `collector.add(metric, value, category="macro", source=source, source_url=..., as_of=(hkma_macro or {}).get("as_of") if source == "hkma_open_api" else None,)` | 코드 확인 |
  | `PR/snapshot.py:136`, `:162` | `_ObservationCollector` | `self.retrieved_at = _iso_timestamp(payload.get("collected_at"))` / `observed_at = _iso_timestamp(as_of or period_end, self.retrieved_at)` (`as_of`가 `None`이면 `retrieved_at`로 폴백) | 코드 확인 |
  | `PR/snapshot.py:170-180` | 신선도 한계 | `"macro": 604_800` (7일). 나이가 0이라 항상 통과 | 코드 확인 |
  | `SV/market_data_collector.py:2349-2352` | 캐시 읽기 | `MACRO_CACHE_TTL = 21600  # 6 hours` / `cached_sentiment = _get_cached("market_sentiment", MACRO_CACHE_TTL)` | 코드 확인 |
  | `SV/market_data_collector.py:2353-2394` | 캐시 → 매크로 dict | 각 지표를 `{'name', 'description', 'price', 'change', 'changePercent', 'level'}`(TNX는 `+ 'spread'`, FEAR_GREED는 `name/description/price/change/changePercent`)로만 변환. 시각 키 없음 | 코드 확인 |
  | `BE/services/global_market_data.py:105-109` | `compute_market_sentiment` | 캐시된 페이로드 최상위에 `"timestamp": int(time.time())`가 있으나, 수집기는 읽지 않는다 | 코드 확인 |
  | `BE/data_providers/sentiment.py:26-31` | `fetch_fear_greed_index` | 반환에 `"timestamp": int(item.get("timestamp", 0))`가 있으나 `:2444-2450`의 변환에서 제외됨 | 코드 확인 |
  | `SV/market_data_collector.py:306-308` | `collected_at` | `data["collected_at"] = datetime.now(timezone.utc).isoformat()...` (수집이 끝난 뒤 시각) | 코드 확인 |

- 동작 설명: `collect_all`이 매크로를 `data["macro"]`에 담는다(`:281`). 스냅샷은 `_flatten_numeric`으로 숫자·문자열 리프를 `macro.VIX.price` 같은 관측으로 펼치고(`snapshot.py:205-214`), HKMA가 아니면 `as_of=None`을 넘겨 `retrieved_at`을 쓴다. 따라서 6시간 전 값이든 방금 값이든 품질 평가의 신선도(`quality.py:_is_fresh`)는 항상 통과다. 보조 사실: 수집기는 `_set_cached`를 임포트(`:2339`)만 하고 호출하지 않는다(`grep _set_cached` → `:2339` 한 줄). 즉 `market_sentiment` 캐시는 글로벌 마켓 라우트(`BE/routes/global_market.py:149-150`의 `cached_or_compute`)가 채울 때만 존재하고, 캐시가 없으면 실시간 조회하지만 저장하지 않는다. 또 `compute_market_sentiment`의 실패 기본값(`vix: {"value": 0, "level": "unknown"}`)도 truthy라 `result['VIX']`가 `price 0`으로 생긴다(`:2353-2354`).
- 조사 범위: `PR/snapshot.py` 전체, `SV/market_data_collector.py:2325-2468`, `BE/services/global_market_data.py:73-110`, `BE/data_providers/sentiment.py:1-45`, grep `market_sentiment`, `_set_cached`.

#### R1-Q7 답변
- 결론: **확정**. 이후 경로 어디에도 LLM 실패(폴백 구조, `report` 문자열, `Analysis failed` 요약, `_llm_contract` 경고)를 근거로 결정을 `HOLD`로 바꾸거나 분석을 중단하는 분기가 **없다**. 따라서 LLM이 완전히 실패해도 다중 타임프레임 합의가 방향성(BUY/SELL)이고 `|합의점수| >= min_abs_override`이면 합의 결정이 최종 `decision`으로 나가고, 지표 충돌 가드·(지원 시장) 품질 게이트만 통과하면 살아남는다. 보고서 핵심 발견 3은 맞다. 단서: 폴백 응답은 `_llm_contract.valid == True`(경고만 `unknown_llm_field:report`)이다(보고서에 없던 사실).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/fast_analysis.py:851-868` | `default_struct` | `"decision": "HOLD", "confidence": 50, "summary": "Analysis failed", ... "position_size_pct": 10, ... "key_reasons": ["Unable to analyze"], "risks": ["Analysis error"]` | 코드 확인 |
  | `SV/llm.py:1426-1445` | `safe_call_llm` | JSON 실패 → `default_structure['report'] = f"Failed to parse analysis result JSON. ..."`, 예외 → `default_structure['report'] = f"Analysis failed: {str(e)}"`, 둘 다 `return default_structure` | 코드 확인 |
  | `SV/fast_analysis.py:499-505` | `_call_analysis_models` | `raw = self.llm_service.safe_call_llm(...)` / `return validate_llm_analysis(raw, default_struct, known_evidence_ids=evidence_ids)` | 코드 확인 |
  | `PR/llm_contract.py:68-81`, `:96-100` | `validate_llm_analysis` | `source = dict(payload or {})` / `warnings = [f"unknown_llm_field:{key}" ...]`(`report` 키는 허용 필드에 없음) / `model = FastAnalysisNarrative.model_validate(clean)` / `valid = True` / `result["_llm_contract"] = {"valid": valid, ..., "warnings": sorted(set(warnings))}`. 기본 구조는 스키마를 통과하므로 `valid=True`이고 `report` 필드는 결과에서 제거됨 | 코드 확인 |
  | `SV/fast_analysis.py:892` | LLM 결정 읽기 | `llm_decision = str(analysis.get("decision", "HOLD") or "HOLD").upper()` (폴백이면 `HOLD`) | 코드 확인 |
  | `SV/fast_analysis.py:970-978` | 합의 덮어쓰기 | `if should_override_with_consensus(consensus_decision, consensus_abs, min_abs_override): final_decision = consensus_decision ... analysis["decision"] = final_decision` / `analysis["confidence"] = consensus_conf` (LLM 실패 검사 없음) | 코드 확인 |
  | `SV/fast_analysis.py:1000-1002` | 비덮어쓰기 분기 | `if quality_multiplier < quality_hold_thr: analysis["decision"] = "HOLD"` (데이터 품질 기준이지 LLM 실패 기준이 아님) | 코드 확인 |
  | `SV/fast_analysis.py:1016`, `:1033` | 합의 정보 기록·검증 | `analysis["consensus"] = {...}` 후 `analysis = self._validate_and_constrain(...)` | 코드 확인 |
  | `SV/fast_analysis.py:1397-1410`, `:1413-1483` | `_validate_decision_against_indicators` | `confidence < 60`이면 `direction_supported_by_consensus`가 아닐 때만 HOLD(합의가 지지하면 유지). BUY는 RSI>70·MACD bearish·강한 하락추세 충돌 시, SELL은 과매수 추세 등 충돌 시 HOLD. 모두 지표/뉴스 기준이며 LLM 실패 필드를 보지 않음 | 코드 확인 |
  | `SV/fast_analysis.py:1137`, `PR/builder.py:556-583` | 전문 보고서 | `_apply_gate(raw_decision, raw_confidence, quality)` — `quality`는 `assess_snapshot_quality`(커버리지·신선도·충돌) 결과뿐 | 코드 확인 |
  | `PR/builder.py:683-688` | 경고 | `_warning_codes((analysis_result.get("llm_contract") or {}).get("warnings") or [])` — `warnings` 목록에 코드로만 합쳐짐, 결정에 영향 없음 | 코드 확인 |
  | `SV/fast_analysis.py:1111` | 결과 | `"llm_contract": analysis.get("_llm_contract", {}),` (응답에 노출만) | 코드 확인 |

- 동작 설명 (호출 순서): ① `safe_call_llm`이 `default_struct` 반환(`llm.py:1445`) → ② `validate_llm_analysis`가 그대로 통과시켜 `decision=HOLD, confidence=50, summary="Analysis failed", position_size_pct=10`, `_llm_contract.valid=True` 생성(`llm_contract.py:68-100`) → ③ `fast_analysis.py:892`에서 `llm_decision="HOLD"` → ④ `:970`에서 합의가 방향성이고 `consensus_abs >= min_abs_override`면 `analysis["decision"]`을 합의로 교체하고 요약에 `[多周期客观共识 ...]` 메모를 덧붙인다(요약 앞부분은 `"Analysis failed"` 그대로) → ⑤ `_validate_and_constrain`(지표 충돌 가드, `:1288`) → ⑥ `:1048-1052` 포지션 보정(`default_struct`의 10을 `quality_multiplier * agreement_scale`로 스케일) → ⑦ `result.update`(`:1082`) → ⑧ `_attach_professional_report`(`:1137`): US/HK/Crypto면 품질 게이트·리스크플랜을 적용하되 LLM 실패 여부는 보지 않는다. LLM 키가 전혀 없어 `ValueError`가 나도 `safe_call_llm`의 `except Exception`이 같은 폴백을 돌려주므로 동일하게 진행된다. 합의가 HOLD이거나 약하면 폴백 `HOLD`가 유지되고 신뢰도는 `50 × quality_multiplier`(`:999`).
- 조사 범위: `SV/fast_analysis.py:480-600, 780-1160, 1288-1485`, `PR/llm_contract.py`, `PR/builder.py:540-754`, `PR/quality.py`, `SV/llm.py:1403-1445`. grep(`BE/` 전체, `*.py`): `_llm_contract|llm_contract|Analysis failed|Unable to analyze|unknown_llm_field|invalid_llm_field|llm_failed|llm_fallback|analysis_failed` → `fast_analysis.py:22,856,863,1111`, `builder.py:686`, `llm.py:1444`, 그 외 `ai_chat.py:658,4542`·`strategy_review.py:863,1263`(이 둘은 `report` 문자열을 검사하지만 `fast_analysis` 경로가 아니라 AI 챗·전략 리뷰 경로)·`portfolio_monitor.py`(결과의 `error` 표시)·`analysis_memory.py:546`(실패 작업 기록). `fast_analysis` 경로에서 폴백을 검사하는 곳은 없음.

#### R1-Q8 답변
- 결론: **확정**. `safe_call_llm`과 `validate_llm_analysis` 어디에도 dict 타입 검사가 없다. `json.loads` 결과가 list/str/number이면 그대로 반환되어 `dict(payload or {})`(`llm_contract.py:68`)에서 평가된다. 비어 있지 않은 str/숫자/True나 비-쌍 원소 list는 `ValueError`/`TypeError`가 나고, 이 예외는 `analyze()`의 `except Exception as e`(`fast_analysis.py:1146-1148`)에서 잡혀 `result["error"] = str(e)`가 되며 `decision` 등 결과 필드는 없다(라우트는 500). 반면 빈 값(`[]`, `""`, `0`, `null`, `false`)은 `payload or {}` 때문에 `{}`가 되어 **오류 없이** 기본 모델(`HOLD`, 50, `position_size_pct=0`, `_llm_contract.valid=True`)로 진행한다. 보고서 4-6 "LLM이 JSON이 아닌 형태" 행은 부분적으로만 맞다(빈 값 경우 보완 필요).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/llm.py:1423-1425` | `safe_call_llm` | `result = json.loads(clean_text)` / `return result` (타입 검사 없음) | 코드 확인 |
  | `SV/llm.py:1432-1436` | 부분 JSON 폴백 | `result = json.loads(response_text[start:end])` / `return result` (`{`~`}` 구간이라 dict만 가능) | 코드 확인 |
  | `PR/llm_contract.py:68` | `validate_llm_analysis` | `source = dict(payload or {})` | 코드 확인 |
  | `SV/fast_analysis.py:499-505`, `:508-517` | `_call_analysis_models` | `raw = ...safe_call_llm(...)` 직후 `validate_llm_analysis(raw, ...)`; `try/except` 없음(앙상블도 동일) | 코드 확인 |
  | `SV/fast_analysis.py:1146-1149` | `analyze` | `except Exception as e:` / `logger.error(f"Fast analysis failed: {e}", exc_info=True)` / `result["error"] = str(e)` / `return result` | 코드 확인 |
  | `BE/routes/fast_analysis.py:237-251` | 라우트 | `if result.get('error'):` → 크레딧 환불 시도 후 `jsonify({'code': 0, 'msg': result['error'], 'data': result}), 500` | 코드 확인 |

- 동작 설명 (Python 3 `dict()` 동작을 직접 확인): `[1,2]`·`5`·`True` → `TypeError: object is not iterable`, `['a','b']`·`'abc'`·`[{'a':1}]` → `ValueError: dictionary update sequence element #0 has length 1; 2 is required`, `[]`·`''`·`0`·`None` → `{}`로 정상 진행. 특이 케이스로 `['ab']`는 `{'a': 'b'}`, 키 2개짜리 dict 한 개가 든 list는 키 쌍이 dict가 되어(`allowed` 필드가 아니므로 `clean`에서 제거) 마찬가지로 빈 입력처럼 진행한다. 예외 케이스의 흐름: `safe_call_llm` 반환(list 등) → `validate_llm_analysis` `:68`에서 예외 → `_call_analysis_models` 탈출 → `analyze()` except `:1146` → `result = {market, symbol, language, model, timeframe, analysis_time_ms, error: "<예외 메시지>"}` 반환(`result` 초기 구조 `:602-610`) → 라우트 500. 빈 값 케이스는 `validate_llm_analysis`가 `unknown_llm_field` 경고 없이 `FastAnalysisNarrative()` 기본값을 반환하고 `valid=True`이며 이후는 R1-Q7과 같은 흐름이다.
- 조사 범위: `SV/llm.py:1403-1445`, `PR/llm_contract.py:56-104`, `SV/fast_analysis.py:480-526, 1137-1150`, `BE/routes/fast_analysis.py:225-260`. `isinstance(` 검사 grep: `llm_contract.py`에는 없음(`validate_llm_analysis` 입력 타입은 `Mapping[str, Any] | None` 힌트만 있음).

#### R1-Q9 답변
- 결론: **확정**. 합의 결정은 **보정 DB 값**(`buy_threshold`/`sell_threshold`)을 쓰며(기본 ±20, 보정 후보 10~30), `consensus_abs = abs(consensus_score)`이다. 따라서 "방향성 합의인데 `consensus_abs < min_abs_override`"는 **가능하다**. 기본값(±20, 오버라이드 15)에서는 불가능하다(방향성이면 `consensus_abs >= 20 > 15`). 가능해지는 조건은 (a) 오프라인 보정이 `buy_threshold`를 14 이하(후보 10/12/14)로 정한 시장 — 추세장 문턱 15 미만, 또는 16/18이 선택되고 `regime == "ranging"`일 때 문턱이 `15×1.2=18`이 되는 경우, (b) 하락·패닉 맥락에서 BUY 합의 vs LLM SELL/HOLD일 때 문턱이 40/55로 상향되는 경우(`:965-968`)이다. 이 두 번째 경우가 기본값에서 `min_abs_override`가 실제로 작동하는 유일한 지점이다. 보고서의 "15는 사실상 무의미"는 기본 설정 한정으로만 맞다(보고서 보완 필요).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/fast_analysis.py:781-783` | 합의 계산 | `consensus_score = weighted_score_sum / weighted_score_w_sum if weighted_score_w_sum > 0 else 0.0` / `consensus_decision = self._score_to_decision(consensus_score, market=market)` / `consensus_abs = abs(consensus_score)` | 코드 확인 |
  | `SV/fast_analysis.py:1494-1521` | `_score_to_decision` | `cfg = self._get_ai_calibration(market=market)` / `buy_thr = float(cfg.get("buy_threshold") or 20.0)` / `sell_thr = float(cfg.get("sell_threshold") or -20.0)` / `if score >= buy_thr: return "BUY" elif score <= sell_thr: return "SELL"` | 코드 확인 |
  | `SV/fast_analysis.py:956-968` | 오버라이드 문턱 | `min_abs_override = float(cfg.get("min_consensus_abs_override") or 15.0)` / `if regime == "ranging": min_abs_override *= 1.2` / `consensus_decision == "BUY" and llm_decision in ("SELL", "HOLD") and (panic_breakdown or bearish_context)` 이면 `min_abs_override = max(min_abs_override, 55.0 if risk_context.get("panic_breakdown") else 40.0)` | 코드 확인 |
  | `SV/fast_analysis_policy.py:6-13` | `should_override_with_consensus` | `return decision in ("BUY", "SELL") and float(consensus_abs) >= float(min_abs_override)` | 코드 확인 |
  | `SV/fast_analysis_scoring.py:122-148` | `_get_ai_calibration` | 5분 캐시(`AI_CALIBRATION_CACHE_TTL_SEC` 기본 300), 실패 시 `cfg = {}` (→ 호출부의 `or 20.0`/`or 15.0` 기본값 사용) | 코드 확인 |
  | `SV/ai_calibration.py:37-42`, `:91-130` | `DEFAULTS`, `get_latest` | `"buy_threshold": 20.0, "sell_threshold": -20.0, "min_consensus_abs_override": 15.0, "quality_hold_threshold": 0.7`; 행이 없으면 `DEFAULTS` 반환 | 코드 확인 |
  | `SV/ai_calibration.py:132-145` | 후보 격자 | `return [10, 12, 14, 16, 18, 20, 22, 25, 30]` (`AI_CALIBRATION_CANDIDATE_ABS_THRESHOLDS`로 변경 가능) | 코드 확인 |
  | `SV/ai_calibration.py:268-273` | `calibrate_market` | `buy_threshold = float(best_abs_thr)` / `sell_threshold = float(-best_abs_thr)` / `min_consensus_abs_override = float(cfg.get("min_consensus_abs_override") or DEFAULTS[...])` (이전 값을 복사만 함, 보정 대상 아님) | 코드 확인 |
  | `SV/ai_calibration.py:313-340`, `BE/startup.py:282-284` | 보정 워커 | `ENABLE_OFFLINE_AI_CALIBRATION` 기본 `"true"`, 시작 시 한 번, `AI_CALIBRATION_MARKET` 기본 `"Crypto"` 한 시장만 | 코드 확인 |

- 동작 설명: `_score_to_decision`이 "방향성(BUY/SELL)"의 기준을 정하고(보정 DB가 있으면 그 `buy_threshold`, 없으면 20), 오버라이드 여부는 별도의 `min_abs_override`(기본 15, 추세 없음이면 ×1.2=18, 하락 맥락 BUY면 40/55)와 비교한다. 두 문턱은 독립이므로 `buy_threshold < min_abs_override`인 조합에서 "방향성 합의지만 오버라이드 안 함"이 생기고, 그때는 LLM 결정이 유지되고 신뢰도만 `× quality_multiplier`로 줄어든다(`:999-1002`). 기본값 경로: 방향성 ⇒ `consensus_abs >= 20` ⇒ 추세장(15)·횡보장(18) 모두 통과 ⇒ 15와 18은 무의미, 40/55 상향만 의미 있음. 보정은 기본 활성이고 한 시장(기본 Crypto)만 건드리므로, 다른 시장은 `get_latest`가 `DEFAULTS`를 돌려준다.
- 조사 범위: `SV/fast_analysis.py:719-1002, 1494-1521`, `SV/fast_analysis_policy.py`, `SV/fast_analysis_scoring.py:122-148`, `SV/ai_calibration.py:1-340`, `BE/startup.py:275-290`. 보정이 DB에 실제로 어떤 값으로 쓰여 있는지는 런타임 데이터라 정적으로 알 수 없으나, 위 조건식은 값에 대해 닫혀 있다.

#### R1-Q10 답변
- 결론: **확정**. (a) 호출이 실패해 `default_struct`를 받은 모델의 `HOLD`도 **그대로 투표에 집계**된다(걸러내는 코드 없음). (b) `decision` 외 모든 필드(확신도·가격·포지션·점수·`evidence_claims`·요약·`_llm_contract`)는 **투표 승자 결정과 같은 결정을 낸, `ensemble_models` 순서상 첫 번째 모델**의 검증된 응답에서 온다. (c) 동률이면 `Counter` 삽입 순서상 먼저 나온 결정(= 모델 순서상 앞선 모델의 결정)이 이긴다. 보고서 4-2의 "동률이면 첫 모델" 서술은 맞다(추론 → 코드 확인으로 상향 가능).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `SV/fast_analysis.py:491-497` | 앙상블 조건 | `if os.getenv("ENABLE_AI_ENSEMBLE", "false").lower() == "true":` 이때 `AI_ENSEMBLE_MODELS` 콤마 목록 `[:3]`; `if len(ensemble_models) < 2:`면 단일 호출(`:498-505`) | 코드 확인 |
  | `SV/fast_analysis.py:508-517` | 모델별 호출 | `analyses = [validate_llm_analysis(self.llm_service.safe_call_llm(system_prompt, user_prompt, default_structure=default_struct, model=item), default_struct, known_evidence_ids=evidence_ids) for item in ensemble_models]` (실패 필터 없음, 순차 실행) | 코드 확인 |
  | `SV/fast_analysis.py:518-520` | 집계 | `decisions = [str(item.get("decision") or "HOLD").upper() for item in analyses]` / `vote = Counter(decisions).most_common(1)[0][0]` / `selected = analyses[decisions.index(vote)].copy()` | 코드 확인 |
  | `SV/fast_analysis.py:521-526` | 덮어쓰기 | `selected.update({"decision": vote, "_ensemble_vote": dict(Counter(decisions)), "_ensemble_models": ensemble_models,})` / `return selected` | 코드 확인 |
  | `SV/llm.py:1442-1445` | 실패 응답 | `default_structure['report'] = ...; return default_structure` (`decision: "HOLD"`) | 코드 확인 |

- 동작 설명: 각 모델 응답은 검증을 거쳐 `decision`이 `BUY/SELL/HOLD`로 정규화된다. 실패한 모델은 `default_struct`(`HOLD`, 50)가 되어 `decisions`에 `"HOLD"`로 들어간다. `Counter.most_common(1)`은 동률일 때 삽입 순서(첫 등장 순)를 유지한다(Python으로 `Counter(['HOLD','BUY']).most_common(1)` → `[('HOLD', 1)]`, `Counter(['BUY','SELL','HOLD'])` → `BUY` 확인). `decisions.index(vote)`는 그 결정을 낸 첫 모델의 인덱스를 준다. 예: 2개 모델 `[A 실패→HOLD, B→BUY]`는 `HOLD` 1:1 동률로 A의 폴백이 최종 응답이 되고(`confidence 50`, `Analysis failed`), `[A→BUY, B 실패→HOLD]`면 A가 이긴다. 3개 모델에서 실패 1개와 성공 2개가 같은 결정이면 실패 표가 영향 없이 성공 모델의 응답이 선택된다(첫 일치 모델). 앙상블에서는 호출자의 `model` 인자가 무시되고 `ensemble_models`만 쓰인다(`:508-517`). 선택된 `decision`은 이후 합의 오버라이드(`:970`)와 지표 가드를 다시 거친다.
- 조사 범위: `SV/fast_analysis.py:476-527`, `SV/llm.py:1403-1445`, `PR/llm_contract.py`. 실패 응답을 걸러내는 코드(`_llm_contract`/`valid` 참조) grep 결과 `fast_analysis.py`에는 `:1111`(응답 노출)뿐이며 앙상블 구간에는 없다.

#### R1-Q11 답변
- 결론: **없음 확정**. `/feedback`로 저장된 `user_feedback`은 **판단(점수·확신도 보정·메모리 조회·프롬프트·합의 보정)에 쓰이지 않는다**. 읽는 곳은 통계 집계 둘뿐이고(성능 통계 `user_satisfaction_pct`, 관리자 사용자 요약), 둘 다 표시용이다. 값은 `helpful`/`not_helpful`/`accurate`/`inaccurate` 중 하나가 컬럼 `user_feedback`에 저장된다.
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `BE/routes/fast_analysis.py:467-505` | `/feedback` 라우트 | `valid_feedback = ['helpful', 'not_helpful', 'accurate', 'inaccurate']` / `success = memory.record_feedback(memory_id, feedback, user_id=...)` | 코드 확인 |
  | `SV/analysis_memory.py:641-669` | `record_feedback` | `SET user_feedback = %s, feedback_at = NOW()` (쓰기) | 코드 확인 |
  | `SV/analysis_memory.py:954-956` | `get_performance_stats` | `SUM(CASE WHEN user_feedback = 'helpful' THEN 1 ELSE 0 END) as helpful_count, SUM(CASE WHEN user_feedback IS NOT NULL THEN 1 ELSE 0 END) as feedback_count` | 코드 확인 |
  | `SV/analysis_memory.py:994-998` | 동일 | `"user_satisfaction_pct": round((row['helpful_count'] / row['feedback_count'] * 100) if ... else 0, 2)` | 코드 확인 |
  | `BE/routes/fast_analysis.py:520-540` | 호출처 | `/performance` 라우트에서만 `memory.get_performance_stats(market, symbol, days)` 호출, 결과는 그대로 JSON 응답. `grep get_performance_stats` 호출처는 이 한 곳 | 코드 확인 |
  | `BE/routes/user.py:2265-2266`, `:2355-2356` | 관리자 요약 | `SUM(CASE WHEN user_feedback = 'helpful' ...) AS helpful_count`, `... 'not_helpful' ... AS not_helpful_count` (관리자 대시보드 집계) | 코드 확인 |
  | `SV/analysis_memory.py:298-310`, `:585-598` | `get_recent`, `get_similar_patterns` | SELECT 컬럼에 `user_feedback` 없음 (`id, decision, confidence, price_at_analysis, summary, reasons, scores, ...`/`..., indicators_snapshot, ..., was_correct, actual_return_pct`) | 코드 확인 |
  | `SV/analysis_memory.py:892-916` | `get_adjusted_confidence` | 버킷별 `was_correct` 정확도만 사용(`get_confidence_accuracy_by_bucket`) | 코드 확인 |

- 동작 설명: 메모리 프롬프트 주입(`get_recent`/`get_similar_patterns`)은 `user_feedback`을 SELECT하지 않고, 확신도 보정은 사후 채점 `was_correct`만 쓰며, `ai_calibration.py`는 `actual_return_pct`/점수로 문턱을 정한다. `user_feedback`을 읽는 두 곳(`analysis_memory.py:955-956` → `/performance` 응답의 만족도 퍼센트, `user.py` 관리자 통계)은 모두 결정 경로 밖이다.
- 조사 범위: `grep -rniE "user_feedback|feedback|thumbs|rating"` — `BE/app`(py), `repos/QuantDinger/mcp_server`, `migrations/init.sql`; `grep -rn "user_feedback"` 레포 전체(`node_modules`, `.git` 제외): `migrations/init.sql:2329`(컬럼 정의), `analysis_memory.py:116,660,955,956`, `routes/user.py:2265,2266,2355,2356`뿐. `ai_calibration.py`, `fast_analysis*.py`, `ai_decision*.py`에는 `feedback` 문자열이 없다(`rating`은 애널리스트 등급·커뮤니티 별점으로 무관). 프롬프트 조립은 `SV/fast_analysis.py`의 `_build_analysis_prompt`에서 `get_recent`/`get_similar_patterns` 경유(위 SELECT 컬럼 확인).

#### R1-Q12 답변
- 결론: **없음 확정**. `BE/routes/agent_v1/research.py`와 `mcp_server/src/quantdinger_mcp/` 어디에도 `FastAnalysisService`/`get_fast_analysis_service`/`research_agent`/`execute_research`/`ai_chat`을 호출하거나 노출하는 코드가 없다. 에이전트 API의 "research"는 유니버스·팩터·워치리스트 CRUD일 뿐 AI 분석이 아니다. 따라서 외부 에이전트가 분석 결과를 받아 주문으로 잇는 경로는 이 두 디렉터리에는 없다(보고서 Q5-1·Q6-1 서술 유지).
- 근거:

  | 위치 | 식별자 | 내용 (원문 인용) | 검증 |
  |---|---|---|---|
  | `BE/routes/agent_v1/research.py:1-16` | 모듈 | `"""Research workspace endpoints: universes, factors, and watchlists."""` / 임포트는 `app.services.factors`, `app.services.market.watchlist`, `app.services.universe`, `app.utils.agent_auth`뿐 | 코드 확인 |
  | `BE/routes/agent_v1/research.py:22-117` | 라우트 | `/research/universes`, `/research/universes/<id>`, `/research/universes/<id>/members`, `/research/factors`, `/research/factors/<factor_id>`, `/research/watchlist`(GET/POST/DELETE) 가 전부 | 코드 확인 |
  | `mcp_server/src/quantdinger_mcp/server.py:281-1071` | MCP 도구 | 등록 도구: `whoami, check_health, list_markets, search_symbols, get_klines, get_price, list_strategies, get_strategy, runtime_overview, stop_strategy, place_quick_order, emergency_stop_trading, get_job, cancel_job, list_jobs, wait_for_job, stream_job_until_done, indicator/strategy 작성·저장·컴파일, submit_backtest, list_portfolio_positions, list_paper_orders, cancel_open_paper_orders, list_universes, get_universe, list_universe_members, list_factors, get_factor, list_watchlist, add_watchlist, remove_watchlist, list_trading_accounts, get_account_snapshot, list_account_positions, 전략 포지션/거래/대기주문, list_agent_quick_trades, signal alert CRUD` | 코드 확인 |
  | `mcp_server/src/quantdinger_mcp/server.py` 호출 경로 | `_get`/`_post` 인수 | 호출하는 경로는 전부 `/api/agent/v1/...` (`backtest/run, indicators, jobs, klines, markets, portfolio/..., price, quick-trade/orders, research/factors·universes, runtime/overview, strategies, strategy-sources, trading/..., whoami`). `/api/fast-analysis`나 `/api/ai/...` 경로 없음 | 코드 확인 |
  | `BE/` 전체 | 호출처 | `grep -rln "get_fast_analysis_service\|FastAnalysisService"`(tests 제외): `routes/fast_analysis.py`, `services/fast_analysis_tasks.py`, `services/__init__.py`, `services/ai_calibration.py`, `services/portfolio_monitor.py`, `services/analysis_memory.py`, `services/fast_analysis.py`. `execute_research`는 `routes/ai_chat.py`(`:81` 임포트, `:2535`, `:2947` 호출)뿐 | 코드 확인 |

- 동작 설명: 에이전트 API(`agent_v1`)는 토큰 스코프(`SCOPE_R`/`SCOPE_W`)로 보호되는 별도 블루프린트이며, 주문 관련은 `quick_trade.py`(MCP `place_quick_order`)에 있다. 이 주문 입력은 호출자가 직접 지정하는 값이고 `fast_analysis`의 결정을 읽지 않는다. MCP 서버는 위 HTTP 엔드포인트를 감싸는 얇은 클라이언트이며 분석 도구가 없다.
- 조사 범위: `grep -rniE "fast_analysis|fast-analysis|analyze|research_agent|execute_research|ai_chat|FastAnalysis|professional_report"` → `BE/routes/agent_v1/`, `mcp_server/src/` 결과 없음; `grep -rniE "analysis|\bai_|llm|\bagent_chat|copilot"` → `agent_v1/jobs.py:6`의 주석(`LLMs that want to react to partial results`)뿐. 디렉터리: `agent_v1/` 17개 파일 전체 목록 확인, `mcp_server/src/quantdinger_mcp/` 4개 파일(`server.py, security.py, tool_contract.py, __init__.py`). `jobs.py`가 잡 종류별로 분석을 실행하는지도 확인(`kind` 필터만 있고 분석 잡 없음).

### 판정 (질문자)

| ID | 판정 | 이유 |
|---|---|---|
| R1-Q1 | 해소 | `builder.py:553-556`(`build_evidence_snapshot` → `_quality`), `:60-72`(`except Exception:` 안에서 `EvidenceSnapshotV1.model_validate(snapshot)`), `quality.py:76`(`for observation in snapshot.observations:` — dict면 AttributeError), `contracts.py:19`(`Literal["USStock", "HKStock", "Crypto"]`), `fast_analysis.py:573-578`을 직접 열어 확인. 예외가 `builder.py:744`의 try보다 앞에서 나서 서비스 except로 전파되는 순서와 최종 `decision`·`position_size_pct`가 남는 값까지 완료 조건 충족. 인용 라인 `quality.py:64-66`은 실제로 `:64` 함수 정의, 루프는 `:76`(경미한 라인 차이, 내용은 맞음) |
| R1-Q2 | 해소 | `market_data_collector.py:2521` `"sentiment": item.get('sentiment', 'neutral'),`, `fast_analysis_scoring.py:575,601-606`, `search.py:590` `overall_sentiment_label ... .lower()`를 직접 확인. 코드 쪽(읽는 키, 기본값, 정확 일치 비교, 텍스트 기반 감성 없음, grep 범위)은 완전히 확정됐고, 남은 부분(Finnhub 응답에 `sentiment` 키가 있는지)은 외부 API 스키마에만 의존하며 갈림 지점·경우의 수가 적혀 있어 허용 |
| R1-Q3 | 해소 | `hk_research.py:25` `_CACHE_TTL_SECONDS = 21_600`, `:226-229`(읽기), `:269-271`(조건부 쓰기), `data_providers/__init__.py:159-186`(`effective_ttl = ttl or ...`, hard-expired면 `None`)을 확인. TTL 21,600초(6시간) 확정 |
| R1-Q4 | 해소 | `market_data_collector.py:279-304`(append 라인 `:288`, `:304`), `:2452-2466`(`_get_macro_data`가 `except Exception` → `return {}`), `:2469-2566`(try 밖은 중복 제거와 `:2564` 정렬뿐), `grep failed_items`로 append 라인 전체 목록을 직접 대조. macro는 도달 경로 없음 확정, news는 검색 제공자의 `published_date` 타입(외부 응답)에만 의존하는 한 경로뿐이라는 점까지 정적으로 닫혀 있음 |
| R1-Q5 | 해소 | `llm.py:1193-1209`(후보 목록), `:1321-1330`(`raise Exception(error_msg)`), `:1360-1366`(대체 공급자 우선순위), `:1423-1445`(`safe_call_llm` 폴백)를 확인. `grep sleep|import time|num_retries|max_retries|Retry|HTTPAdapter` 결과 레포 코드에 재시도·백오프 없음. 단 LiteLLM 공급자 경로의 `litellm.completion`(`:757`) 내부 재시도는 외부 라이브러리 동작이라 범위 밖 |
| R1-Q6 | 해소 | `snapshot.py:368-385`(비-HKMA면 `as_of=None`), `:136`·`:162`(`retrieved_at` 폴백), `market_data_collector.py:2339`(`_set_cached`는 임포트만), `:2349` `MACRO_CACHE_TTL = 21600`을 확인. 매크로 관측 나이 항상 0 확정 |
| R1-Q7 | 해소 | `fast_analysis.py:853-868`(`default_struct`), `:892`, `:956-1002`(오버라이드에 LLM 실패 검사 없음, 비오버라이드 분기의 HOLD는 품질 기준), `llm.py:1441-1445`, `llm_contract.py:68-100`을 확인. 폴백 구조가 `valid=True`로 통과하는 것도 `:70-73`에서 확인. grep 범위도 충분 |
| R1-Q8 | 해소 | `llm.py:1423-1425`(타입 검사 없이 `return result`), `llm_contract.py:68` `source = dict(payload or {})`, `fast_analysis.py:499-505`(try 없음), `:1146-1149`를 확인. 빈 값이 `FastAnalysisNarrative` 기본값(`position_size_pct` 기본 0, `llm_contract.py:38`)으로 진행한다는 것도 확인 |
| R1-Q9 | 해소 | `fast_analysis.py:781-783`(`consensus_abs = abs(consensus_score)`), `:1494-1521`(`buy_thr = float(cfg.get("buy_threshold") or 20.0)`), `:956-968`(×1.2, 40/55 상향), `ai_calibration.py:132-145` 후보 `[10, ..., 30]`을 확인. 가능 조건이 값에 대해 닫힌 형태로 제시됨 |
| R1-Q10 | 해소 | `fast_analysis.py:491-526`을 직접 열어 실패 필터 없음, `most_common(1)`, `decisions.index(vote)`, `.copy()`·`update` 확인. (a)(b)(c) 모두 확정 |
| R1-Q11 | 없음 확정 | 레포 전체 `grep -rn user_feedback`(node_modules·.git 제외)을 직접 재실행: `init.sql:2329`, `analysis_memory.py:116,660,955,956`, `user.py:2265,2266,2355,2356`뿐으로 답변과 일치. `analysis_memory.py`·`fast_analysis*.py`·`ai_calibration.py`에 `SELECT *`가 없어 암묵적 읽기도 없음 |
| R1-Q12 | 없음 확정 | `agent_v1/research.py:1` docstring(`universes, factors, and watchlists`) 확인, `grep -rniE "fast_analysis|fast-analysis|research_agent|execute_research|ai_chat|FastAnalysis|professional_report"`을 `routes/agent_v1`·`mcp_server/src`에 재실행해 결과 0건. `mcp_server/src/quantdinger_mcp/` 파일 4개 확인 |

새 질문 없음. 모든 질문이 해소 또는 없음 확정이므로 Round 1로 종료한다.

---

## 최종 정리 (질문자)

- 총 라운드: 1 / 총 질문: 12 / 해소 10 · 없음 확정 2 · 정적 확인 불가 0
- (R1-Q2의 Finnhub 응답 스키마, R1-Q4의 검색 제공자 `published_date` 타입은 질문 안의 하위 항목으로만 정적 확인 불가가 남는다.)

이 레포를 이해하는 데 핵심인 확정 사실:

1. **LLM이 완전히 실패해도 BUY/SELL이 나간다.** `safe_call_llm`은 예외를 삼켜 `default_struct`(HOLD, 50, "Analysis failed")를 돌려주고(`llm.py:1441-1445`), 계약 검증은 이를 `valid=True`로 통과시킨다(`llm_contract.py:70-73`). 이후 합의 덮어쓰기(`fast_analysis.py:970-978`), 지표 가드, 품질 게이트 어디에서도 LLM 실패를 확인하지 않는다. (R1-Q7)
2. **CN/FX/선물/MOEX에서는 전문 보고서가 열리지 않은 채(fail-open) 진행된다.** `builder.py:556` → `_quality`의 `EvidenceSnapshotV1.model_validate`(`:71`)가 `Market` 리터럴(`contracts.py:19`)에서 실패하고, `fast_analysis.py:573`에서 `professional_report_error`만 남는다. 그래서 품질 게이트와 리스크플랜 상한이 적용되지 않는다. `unsupported_professional_report_market` 분기는 도달할 수 없는 코드다. (R1-Q1)
3. **합의 결정 임계(보정값, 기본 ±20)와 덮어쓰기 문턱(기본 15, 횡보장 ×1.2, 하락 맥락 BUY는 40/55)은 서로 독립이다.** 기본값에서 의미가 있는 것은 40/55 상향뿐이고, 보정이 14 이하를 고른 시장에서만 15가 작동한다. (R1-Q9)
4. **`call_llm_api`에는 재시도도 백오프도 없다.** 모델 후보(요청 → 기본 → 정적 폴백)를 한 번씩 시도하고, 마지막 후보가 402/403일 때만 대체 공급자를 시도한다. 전부 실패하면 raise한다(`llm.py:1193-1330`). (R1-Q5)
5. **뉴스 감성 점수는 라벨이 정확히 `positive`/`negative`일 때만 움직인다.** Finnhub은 `item.get('sentiment','neutral')`(`market_data_collector.py:2521`)이고, Alpha Vantage 라벨은 소문자 `bullish` 등이라 항상 중립으로 잡힌다. 텍스트로 감성을 계산하는 코드는 없다. (R1-Q2)
6. **매크로·뉴스 실패 감점(0.85/0.8)은 사실상 발동하지 않는다.** 헬퍼가 예외를 삼켜 `{}`나 빈 목록을 돌려주기 때문이다(`market_data_collector.py:2460-2466`). (R1-Q4)
7. **매크로 관측의 `as_of`는 항상 수집 시각이다.** 6시간 캐시 값이어도 신선도 검사를 통과한다(`snapshot.py:384`, `:162`). 수집기는 매크로 캐시를 쓰지 않고 읽기만 한다. (R1-Q6)
8. **앙상블(기본 off)에서는 실패한 모델도 HOLD 한 표로 집계된다.** 동률이면 앞 모델의 결정이 이기고, 최종 필드는 승리한 결정을 낸 첫 모델의 응답에서 온다(`fast_analysis.py:518-526`). (R1-Q10)
9. **LLM이 dict가 아닌 JSON을 반환할 때는 값에 따라 결과가 갈린다.** 비어 있지 않은 list·str·number는 `dict()` 예외로 분석 전체가 `error`(500)가 되고, 빈 값은 기본 HOLD(포지션 0)로 진행한다(`llm_contract.py:68`). (R1-Q8)
10. **사용자 피드백과 에이전트 API·MCP는 판단 경로에 들어가지 않는다.** `user_feedback`은 표시용 통계에만 쓰인다. 에이전트 API·MCP는 분석이나 리서치를 노출하지 않는다. (R1-Q11, R1-Q12)

## 보고서 반영 목록

| 보고서 위치 | 현재 내용 | 고쳐야 할 내용 | 근거 질문 |
|---|---|---|---|
| `01-data.md` Q1-3 표 CNStock·Forex/Futures/MOEX 행, `03-decision.md` 4-6 "지원 안 하는 시장" 행, `next.md` 3절 (a) | `contracts.py:19` 리터럴 기반의 `추론`, 미확인 | `코드 확인`으로 올린다. 예외 지점은 `builder.py:556` → `_quality`의 `EvidenceSnapshotV1.model_validate`(`:71`)다. `fast_analysis.py:573`에서 `professional_report_error`만 남고, 결정과 포지션은 레거시 값 그대로다(fail-open). `unsupported_professional_report_market` 분기(`builder.py:626`)는 도달할 수 없다. `response_contract=professional_report_v1`로 요청하면 500이 된다. next.md 체크 해제 | R1-Q1 |
| `03-decision.md` 4-3 "감성 라벨의 출처" 행 | 외부 API 스키마 기억에 근거한 `추론` | 코드 확인: Finnhub `item.get('sentiment','neutral')`(`market_data_collector.py:2521`), 점수는 정확히 `positive`/`negative`만 집계(`fast_analysis_scoring.py:601-606`), 텍스트 기반 감성 없음. Alpha Vantage 라벨(`search.py:590`, 소문자 bullish 등)은 항상 중립. Finnhub 응답에 `sentiment` 키가 있는지만 정적 확인 불가로 남긴다 | R1-Q2 |
| `01-data.md` Q2-3 캐시 표 "홍콩 리서치" 행, `next.md` 3절 | "값 미확인", 쓰기 위치 `hk_research.py:226-229` | TTL 21,600초(6시간, `hk_research.py:25`). `:226-229`는 읽기이고 쓰기는 `:271`이다. 소스가 하나라도 값을 줄 때만 저장한다 | R1-Q3 |
| `03-decision.md` 4-3 "품질 배수" 행, `01-data.md` Q2-5 "`failed_items` 한계" 행 | 03은 0.85/0.8 감점을 정상 동작처럼 적었고, 01은 `추론` | 두 문서 모두 "macro 감점은 도달 경로 없음, news 감점은 검색 제공자의 `published_date` 타입이 섞일 때만 가능 → 사실상 미발동"(`market_data_collector.py:279-304`, `:2460-2466`, `:2564`)으로 맞추고 `코드 확인`으로 올린다. 빈 결과도 실패로 기록되지 않는다 | R1-Q4 |
| `01-data.md` Q2-5 "재시도·백오프" 행, `next.md` 3절·4절 1번 | `call_llm_api` 내부 재시도 미확인 | 재시도·백오프 없음. 후보 모델(요청 → 공급자 기본 → 정적 폴백, 중복 제거)을 1회씩 시도하고, 마지막 후보가 402/403이면 대체 공급자(DeepSeek > AtlasCloud > Grok > MiniMax > OpenAI > Google > OpenRouter)를 시도한다. 전부 실패하면 raise하고, `safe_call_llm`이 폴백 구조로 바꾼다(`llm.py:1193-1330, 1360-1396, 1441-1445`) | R1-Q5 |
| `01-data.md` Q2-2 "as_of 폴백" 행 | 해석이 `추론` | `코드 확인`으로 올린다(02-schedule Q3-4와 맞춤). 비-HKMA 매크로는 `as_of=None` → `retrieved_at`(`snapshot.py:384`, `:162`). 보충: 수집기는 `market_sentiment` 캐시를 쓰지 않는다(`_set_cached`는 임포트만, `:2339`) | R1-Q6 |
| `00-overview.md` 핵심 발견 3, `03-decision.md` 4-6, `next.md` 3절 (b) | "논리 추적, 실행 재현 없음", 미확인 | 코드 확인: 폴백 구조 이후 어디에도 LLM 실패를 검사하는 분기가 없다. 폴백 응답은 `_llm_contract.valid=True`이고 경고는 `unknown_llm_field:report`뿐이다(`llm_contract.py:70-100`) | R1-Q7 |
| `03-decision.md` 4-6 "LLM이 JSON이 아닌 형태" 행 | 리스트 등이 오면 분석 전체가 `error`(`추론`) | 코드 확인 후 보완: 비어 있지 않은 list·str·number는 `dict(payload or {})`(`llm_contract.py:68`) 예외로 `result["error"]`가 되고 라우트는 500이다. 빈 값(`[]`, `""`, `0`, `null`)은 오류 없이 `FastAnalysisNarrative` 기본값(HOLD, 포지션 0, valid=True)으로 진행한다 | R1-Q8 |
| `03-decision.md` 4-3 "덮어쓰기 문턱" 행, `next.md` 5절 첫 질문 | "기본 임계 ±20이 이미 15보다 커서 15는 사실상 무의미" | "기본 설정에서만" 무의미하다. 합의 결정은 보정 `buy_threshold`(후보 10~30)를 쓰고 `consensus_abs = abs(consensus_score)`다. 보정값이 15 미만(횡보장은 18 미만)이면 15·18 문턱이 작동하고, 하락 맥락 BUY의 40/55 상향은 기본값에서도 작동한다(`fast_analysis.py:781-783, 956-968, 1494-1521`) | R1-Q9 |
| `03-decision.md` 4-2 "앙상블" 행 | "동률이면 첫 모델"(`추론`), 실패 모델과 필드 출처 언급 없음 | `코드 확인`으로 올린다. 실패 모델의 폴백 HOLD도 집계된다. `decision` 외 필드는 승리한 결정을 낸 첫 모델의 응답에서 온다. 동률은 `Counter` 첫 등장 순이다. 앙상블에서는 `model` 인자가 무시된다(`fast_analysis.py:491-526`) | R1-Q10 |
| `03-decision.md` 4-7 "사용자 피드백" 행, `next.md` 3절 | `미확인(사용처)` | 없음 확정: `user_feedback`은 `/performance`의 `user_satisfaction_pct`와 관리자 통계(`user.py:2265-2356`)에서만 읽힌다. 메모리 조회·확신도 보정·AI 보정·프롬프트에는 쓰이지 않는다 | R1-Q11 |
| `next.md` 3절 `routes/agent_v1/research.py`·`mcp_server/` 항목 | 미확인 | 없음 확정으로 체크 해제한다. agent_v1 research는 유니버스·팩터·워치리스트 CRUD이고, MCP 도구에는 분석·리서치가 없다. Q5-1·Q6-1 서술은 그대로 둔다 | R1-Q12 |
