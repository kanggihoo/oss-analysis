---
sha: "916a0e1cd5f4a84de4ec7e485386c7d9941d7e00"
created: 2026-11-10
updated: 2026-11-10
sources:
  - scripts/validate_golden_set.py
  - scripts/validate_business_set.py
  - scripts/validate_model_baseline.py
  - scripts/check_public_hygiene.py
  - scripts/test_validate_golden_set.py
  - scripts/test_validate_business_set.py
  - scripts/test_validate_model_baseline.py
  - .github/workflows/validate.yml
  - evals/fixtures/business_korean.v1.jsonl
  - evals/fixtures/golden_set.v0.jsonl
  - docs/validation-plan.md
depends:
  - ./input-mode-and-authority.md
  - ./fact-protection.md
  - ./evaluation-rubric.md
status: ready
---

# 평가셋 스키마·검증 스크립트

> 평가 fixture(JSONL) 3종의 형식과 그것을 검사하는 스크립트 4개(골든셋, 비즈니스 보충셋, 점수 기록, 공개 위생)와 CI 단계를 정의한다. 검증기는 한국어 품질이 아니라 파일의 구조·커버리지를 본다.

<!-- 이 레포에서 실행 코드는 이 검증기들뿐이다. 스크립트는 짧고 자기완결적이라 C-ID로 넘기고 1부에는 검사 항목을 글로 둔다. 검증 수준 `코드 확인` = 코드를 직접 읽음(실행은 하지 않았다, 1.4 확인 한계). -->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 평가 케이스는 JSONL(한 줄 = JSON 객체 하나)로 둔다. 종류는 v0 골든셋(220건, 동결), 샘플(11건), 비즈니스 보충셋(32건)이다.
2. `validate_golden_set.py`, `validate_business_set.py`가 각 fixture의 스키마·도메인·건수·커버리지를 검사한다.
3. 모델 출력을 점수 매긴 기록(JSONL)은 `validate_model_baseline.py`가 fixture와 맞춰 본다(ID, 입력, 도메인, 점수 범위, 실패 유형).
4. `check_public_hygiene.py`가 공개 전 민감 패턴을 검사한다.
5. CI가 push·PR마다 위 단계를 순서대로 실행한다.

### 1.2 범위·통합 지점
- 제공: fixture 스키마, 검증 규칙, 오류 출력, 종료 코드, CI 순서, 레포가 가진 단위 테스트의 시나리오.
- 제외: 평가 절차와 기록 해석([eval-procedure-and-records](./eval-procedure-and-records.md)), 채점 기준([evaluation-rubric](./evaluation-rubric.md)), 한국어 품질 판정(검증기는 하지 않는다).
- 외부 의존·선행 계약: 모드 이름·보호 항목·점수 5축의 어휘(S1, S2, S3). 파이썬 표준 라이브러리만 쓴다. CI의 YAML 검사는 Ruby를 쓴다.
- 소유 상태·부작용: 읽기만 한다. 파일을 쓰지 않는다. 오류가 있으면 종료 코드 1.

### 1.3 인터페이스와 데이터 의미
**fixture 형식**

| fixture | 필수 필드 | 의미·제약 |
|---|---|---|
| `golden_set.v0.jsonl` (220건, 동결) | `id`, `domain`, `input`, `expected_traits`, `must_preserve`, `avoid` (+ 이력서 40건은 `resume_role`) | `domain`은 10개(`resume` 90, `application` 10, `document` 20, `product_copy` 10, `everyday` 20, `messenger` 20, `email` 20, `public_post` 10, `code_review` 10, `dialogue` 10). `resume_role`은 `operations`·`planning`·`qa`·`design`·`marketing_content`·`customer_service`·`research_data`·`people_education` 각 5건이고 `resume` 도메인에서만 허용 |
| `golden_set.sample.jsonl` (11건) | 같음 | 테스트용 작은 샘플. v0 건수 규칙은 파일 이름이 `golden_set.v0.jsonl`일 때만 적용 |
| `business_korean.v1.jsonl` (32건) | 최상위 `id`, `domain`, `mode`, `input`, `grading` 정확히 5개. `grading`은 `expected_behavior`, `expected_traits`, `must_preserve`, `avoid` | `domain`은 비즈니스 5개(`b2b_sales`, `marketing_ad`, `landing_page`, `support_notice`, `ui_notification`) 또는 회귀 3개(`resume`, `everyday`, `document`). `mode`는 `korean_edit`·`bilingual_edit`·`english_to_korean`. `expected_behavior`는 `produce_korean`·`keep_unchanged`·`ask_one_question`. 생성기는 `id`와 `input`만 본다 |
| 점수 기록 JSONL | `id`, `domain`, `input`, `output`, `generator_model`, `judge_model`, `skill_revision`, `scores`, `critical_failure`, `failure_types`, `review_notes` | `scores`는 5축(`meaning_fidelity`, `korean_naturalness`, `context_fit`, `edit_discipline`, `practical_usefulness`) 각각 1~5 정수. `failure_types`는 12개 허용 목록 |

**점수 기록의 허용 `failure_types`**: `completion_state_change`, `context_mismatch`, `evidence_type_mixup`, `factual_drift`, `generic_organization_fit`, `not_ready`, `number_drift`, `other`, `over_editing`, `ownership_inflation`, `under_editing`, `unnatural_korean`.

**공개 위생 검사**: 금지 문자열 8개(`BEGIN PRIVATE KEY`, `BEGIN OPENSSH PRIVATE KEY`, `api_key`, `apikey`, `access_token`, `refresh_token`, `client_secret`, `password`, 대소문자 무시)와 정규식 4개(GitHub 토큰, OpenAI 키 형태, 이메일(`users.noreply.github.com` 제외), 한국 휴대전화 번호).

**CI 순서**(`.github/workflows/validate.yml`): 골든셋 검증 → 비즈니스 보충셋 검증 → 세 검증기의 unittest → 2026-08-25 기준선 검증 → 공개 위생 → `.github`·`skills`의 YAML 파싱(Ruby). 트리거는 `main`에 대한 push와 PR, 러너 `ubuntu-latest`, Python 3.12.

### 1.4 행동 규칙과 남은 질문
| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 골든셋 검증 | 빈 줄은 건너뛴다. 각 줄이 JSON이어야 하고, 필수 6필드, 비어 있지 않은 문자열 `id`(중복 금지), 허용된 `domain`, 길이 10자(공백 제거 후) 이상의 `input`, 세 목록 필드가 비어 있지 않은 문자열 목록이어야 한다. `resume_role`은 `resume` 도메인에서만, 알려진 값만 허용 | 코드 확인 |
| R-02 | 파일 이름이 `golden_set.v0.jsonl` | 도메인별 건수(90·10·20·10·20·20·20·10·10·10)와 직무별 5건이 정확히 맞아야 한다. 맞지 않으면 `expected N <domain> items, found M` 형식의 오류 | 코드 확인 |
| R-03 | 비즈니스 보충셋 검증 | 최상위와 `grading`의 필드가 정확히 정해진 집합이어야 하고(알 수 없는 필드는 "평가자 요구는 `grading` 아래"라는 안내와 함께 오류) 도메인·모드·기대 행동이 허용값이어야 한다. 회귀 도메인은 `korean_edit`만 허용 | 코드 확인 |
| R-04 | 비즈니스 보충셋 커버리지 | 비즈니스 도메인 5개, 회귀 도메인 3개, 비즈니스의 모드 3개, 비즈니스 도메인×모드 15쌍, 기대 행동 3개가 모두 있어야 하고, `keep_unchanged`와 `ask_one_question`은 비즈니스 케이스 자체에도 있어야 한다(회귀 케이스가 대신하지 못한다). 오류는 `ERROR:` 접두사로 출력 | 코드 확인 |
| R-05 | 점수 기록 검증 | 모든 fixture ID가 정확히 한 번 있어야 하고 `input`·`domain`이 fixture와 같아야 하며, `output`이 비어 있지 않고, `generator_model`·`judge_model`·`skill_revision`은 비어 있지 않고 파일 안에서 각각 하나의 값이어야 한다. 점수는 bool이 아닌 1~5 정수, `critical_failure`는 bool, `failure_types`는 중복·미지 유형이 없는 목록이며 치명 실패면 유형이 하나 이상, 유형이 있으면 `review_notes`가 비어 있지 않아야 한다 | 코드 확인 |
| R-06 | 점수 기록이 모두 통과 | 평균 5축 점수, 치명 실패 수, 도메인별 건수를 출력한다. 점수가 릴리스 기준에 못 미쳐도 실패시키지 않는다(실패한 케이스를 보이게 두기 위해) | 코드 확인 (`validation-plan.md`의 설명과 일치) |
| R-07 | 공개 위생 검사 | 대상 확장자(`.md`, `.jsonl`, `.py`, `.yaml`, `.yml`, `.gitignore`, 확장자 없음)의 각 줄에서 금지 문자열과 정규식을 찾아 `path:line` 형식의 발견 목록을 출력하고 하나라도 있으면 종료 코드 1. `evals/datasets`와 `.git` 등은 건너뛴다(경로가 그 접두로 시작할 때만 건너뛰므로 루트를 `.`로 줄 때 동작한다) | 코드 확인 |
| R-08 | 검증 성공·실패 | 성공은 종료 코드 0과 `OK: <path> (N items/cases/scored outputs)`와 분포 출력, 실패는 오류를 모두 모아 출력하고 종료 코드 1 | 코드 확인 |

- 불변식: 검증기는 한국어 품질을 판정하지 않는다(`validation-plan.md`). 비즈니스 출력·리뷰 파일을 위한 검증기는 없다(`validation-plan.md:272`).
- 미결정: 없음.
- 확인 한계: 스크립트와 unittest는 실행하지 않았다(권한 설정으로 거부돼 우회하지 않았다). 아래 규칙과 사례는 코드와 테스트를 읽은 결과다. 레포의 개발 보고서는 29개 unittest 통과와 32건 fixture 통과를 기록하지만(`business-review.md`의 Mechanical checks) 재현하지 않았다. 레포 스스로 인정한 미시험 항목은 읽을 수 없는 경로(없는 파일, 디렉터리, UTF-8 아님)다(`business-review.md`의 L9).

### 1.5 필수 코드 참조
| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `scripts/validate_golden_set.py:12-57` | 필수 필드, 허용 도메인, v0 건수표, 직무 건수표 | R-01, R-02 |
| C-02 | `scripts/validate_golden_set.py:59-143` `validate_file` | 골든셋 검사 본문과 출력 형식 | R-01, R-02, R-08 |
| C-03 | `scripts/validate_business_set.py:12-51` | 도메인·모드·기대 행동·필드 집합 상수 | R-03, R-04 |
| C-04 | `scripts/validate_business_set.py:58-181` `validate_file` | 보충셋 검사 본문, 커버리지 규칙, 출력 형식 | R-03, R-04, R-08 |
| C-05 | `scripts/validate_model_baseline.py:12-48` | 점수 필드, 허용 실패 유형, 필수 필드 | R-05 |
| C-06 | `scripts/validate_model_baseline.py:50-222` `load_fixture`, `validate_file` | fixture 로드와 점수 기록 검증, 평균 출력 | R-05, R-06 |
| C-07 | `scripts/check_public_hygiene.py:11-81` | 금지 문자열, 정규식, 건너뛰기, 대상 확장자, 출력 | R-07 |
| C-08 | `.github/workflows/validate.yml:1-37` | CI 단계 순서 | 1.3 |

### 1.6 수락 사례
출처: 원본 테스트 열람(`scripts/test_validate_*.py`)의 시나리오. 테스트는 실행하지 않았다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-02 | 골든셋에서 `public_001`을 뺀 파일(`test_missing_public_post_is_rejected`) | 종료 코드 1, `expected 10 public_post items, found 9` |
| T-02 | R-01 | 골든셋의 `id`를 중복(`test_duplicate_id_is_rejected`) | 종료 코드 1, `duplicate id` |
| T-03 | R-01, R-08 | 실제 골든셋과 11건 샘플(`test_real_fixture_passes`, `test_sample_fixture_passes`) | 종료 코드 0, 출력에 `(220 items)`, `(11 items)` |
| T-04 | R-04 | 비즈니스 도메인의 `keep_unchanged` 케이스를 모두 `produce_korean`으로 바꾸고 회귀 도메인(`resume`·`everyday`·`document`)의 `keep_unchanged`는 남김(`test_native_no_op_cases_do_not_satisfy_business_no_op_coverage`) | 종료 코드 1, `missing business behavior coverage: keep_unchanged`만 나오고 전체 `missing expected_behavior coverage`·도메인·모드 누락 오류는 나오지 않는다 |
| T-05 | R-05 | 점수 5축 중 `meaning_fidelity`를 6으로(`test_invalid_score_is_rejected`) | 종료 코드 1, `meaning_fidelity score must be an integer from 1 to 5` |
| T-06 | R-05 | `critical_failure`가 참인데 `failure_types`가 비어 있음(`test_critical_failure_requires_type`) | 종료 코드 1, `must name at least one failure type` |
| T-07 | R-05 | 기록의 `input`이 fixture와 다름(`test_source_input_drift_is_rejected`) | 종료 코드 1, `input differs from fixture` |
| T-08 | R-03, R-04 | 비즈니스 fixture의 4번째 줄을 잘라 JSON이 아니게 함(`test_malformed_json_is_rejected`), 빈 파일(`test_empty_file_is_rejected`), 회귀 케이스(`resume`)의 모드를 `english_to_korean`으로(`test_regression_case_must_be_korean_edit`) | 각각 종료 코드 1이며 `:4: invalid JSON`, `missing business domain coverage`, `native regression cases must use korean_edit` |
| T-09 | R-04 | `support_notice`×`bilingual_edit` 한 쌍만 제거(`test_missing_business_domain_mode_pair_is_rejected`) | 종료 코드 1, `missing business domain/mode coverage: support_notice/bilingual_edit` 한 건만. 도메인 단독·모드 단독 누락 오류는 나오지 않는다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map
| R-ID / T-ID | 근거 (repo@916a0e1) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02, 1.3 골든셋 | `scripts/validate_golden_set.py:12-143`, `evals/fixtures/golden_set.v0.jsonl`(필드·도메인 건수는 직접 셈) | 코드 전문과 fixture 건수를 확인. 건수 220은 `Counter`로 셈 |
| R-03, R-04, 1.3 보충셋 | `scripts/validate_business_set.py:12-181`, `evals/fixtures/business_korean.v1.jsonl` | 코드 전문 확인. 32건·도메인·모드·기대 행동 분포를 직접 셈(27+5, 15/7/10, 22/7/3) |
| R-05, R-06 | `scripts/validate_model_baseline.py:12-222` | 코드 전문 확인 |
| R-07 | `scripts/check_public_hygiene.py:11-81` | 코드 전문 확인. 건너뛰기 조건은 코드 읽기에서 도출 |
| R-08 | 세 검증기의 `main`·`validate_file` | 코드 전문 확인. 골든셋 오류는 접두사 없이, 보충셋 오류는 `ERROR:` 접두사로 출력한다 |
| 1.3 CI | `.github/workflows/validate.yml:1-37` | 직접 읽음 |
| 1.4 불변식 | `docs/validation-plan.md:272` | 직접 읽음 |
| T-01~T-09 | `scripts/test_validate_golden_set.py`, `test_validate_model_baseline.py`, `test_validate_business_set.py:46-203`(테스트 17개) | 골든셋·점수 기록 테스트 전문과 보충셋 테스트의 1-60, 137-210줄 본문을 읽었다. 보충셋 테스트 60-137줄(타입·빈 항목·중복·모드 오류 등)은 이름만 확인 |

### 2.2 코드 읽는 순서
`validate_business_set.py`(가장 새롭고 규칙이 많다) → `validate_golden_set.py` → `validate_model_baseline.py` → CI 워크플로. 보충셋 포맷의 의도는 `docs/validation-plan.md:154-221`.

## 적용 메모
| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| — | 없음 | — | — |
