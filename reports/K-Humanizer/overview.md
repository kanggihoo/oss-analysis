---
sha: "916a0e1cd5f4a84de4ec7e485386c7d9941d7e00"
created: 2026-11-10
updated: 2026-11-10
sources:
  - README.md
  - LICENSE
  - CHANGELOG.md
  - plugin.json
  - .claude-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - .agents/plugins/marketplace.json
  - skills/k-humanizer/SKILL.md
  - skills/k-humanizer/agents/openai.yaml
  - skills/k-humanizer/references/business-korean.md
  - skills/k-humanizer/references/native-writing.md
  - skills/k-humanizer/references/patterns.md
  - skills/k-humanizer/references/evaluation.md
  - skills/k-humanizer-resume/SKILL.md
  - skills/k-humanizer-resume/agents/openai.yaml
  - skills/k-humanizer-resume/references/resume.md
  - skills/k-humanizer-resume/references/resume-workflow.md
  - skills/k-humanizer-resume/references/resume-roles.md
  - skills/k-humanizer-resume/references/application.md
  - skills/k-humanizer-resume/references/evaluation.md
  - docs/validation-plan.md
  - scripts/validate_business_set.py
  - scripts/validate_golden_set.py
  - scripts/validate_model_baseline.py
  - scripts/check_public_hygiene.py
  - .github/workflows/validate.yml
  - evals/fixtures/business_korean.v1.jsonl
  - evals/reports/2026-11-07-business-korean/business-review.md
  - evals/reports/2026-08-25/model-baseline.md
---

# K-Humanizer Analysis Overview

## 1. 기본 정보 (Code Baseline)

- **Repo URL**: `https://github.com/evergreentree97/K-Humanizer` (branch `main`, 44 commits 전체 clone)
- **작업트리 상태**: Clean
- **분석 목적**: 기본 목적(기능 스펙화). 사용자가 목적을 지정하지 않았다. 이 레포는 실행 코드가 아니라 **LLM이 읽고 따르는 지침 문서**가 본체라서, 스펙은 "이 지침이 에이전트에게 요구하는 판단 규칙"을 구현자(다른 스킬 작성자)가 다시 쓸 수 있는 수준으로 정리하는 일이 된다. 재구현, 한국어 글쓰기 스킬 설계 참고, 도입 검토 중 무엇이 목적인지 확인이 필요하다(`handoff.md`)
- **라이선스**: MIT License (LICENSE 파일에 적힌 그대로, Copyright (c) 2026 K-Humanizer contributors) — `LICENSE`. 하위 디렉터리 LICENSE는 `git ls-files`에 없다(코드 확인)
- **분석 대상 제품**: Agent Skill 2개와 그 주변. (1) `skills/k-humanizer/`(한국 고객용 한국어 작성·번역·편집, SKILL.md + references 4개), (2) `skills/k-humanizer-resume/`(이력서·지원서, SKILL.md + references 5개), (3) 배포: Claude Code·Codex 플러그인 매니페스트 3종, (4) 평가: `evals/`(fixture 3개·기록), `scripts/`(검증 스크립트 4개·테스트 3개), `.github/workflows/validate.yml`, `docs/validation-plan.md`. 서버·결제·호스팅 없음. 버전 0.5.0(`plugin.json`)
- **스펙 범위**: 2026-11-10 1차 승인(권장안대로): 행 1~7, 9와 공유 계약 S1·S2·S3·S4의 소유 부분. 같은 날 2차 승인(사용자가 "이력서 스킬 10~13, 일반 글쓰기 8, 평가 도구 15·16"을 선택): 행 8, 10~13, 15, 16. 3차 승인("14만 진행"): 행 14. 제외 행은 없다. 분석 목적은 여전히 미확인이라 기본 목적(기능 스펙화)으로 쓴다
- **검증 방식**: 지침·검증 스크립트·매니페스트는 소스를 읽어 확인했다(정적 읽기). 검증 스크립트와 unittest는 실행하지 않았다(실행 시도가 권한 설정으로 거부돼 우회하지 않았다). LLM에 스킬을 먹여 실제 출력이 어떤지는 확인하지 않았다. 그래서 "동작한다"가 아니라 "지침이 이렇게 쓰여 있다" 수준이다

---

## 2. 프로젝트 개요

한국어가 모국어가 아닌 사람이 한국 고객에게 보낼 글(영업 메일, 광고, 제품 페이지, 지원 답변, 서비스 공지, 앱 문구)을 쓸 때, LLM이 번역투 없이 자연스러운 한국어를 내되 **가격·날짜·정책·플레이스홀더를 바꾸지 않게** 하는 스킬이다(코드 확인: `README.md`, `skills/k-humanizer/SKILL.md:1-11`). 두 스킬로 나뉜다.

1. **k-humanizer**: `SKILL.md`가 5단계(입력 모드 판별 → 상황 파악 → 작성·편집 → 사실·약속 보호 → 멈춤 기준)와 응답 형식을 정하고, 필요할 때만 references를 읽게 한다. 번역투 진단표(`patterns.md`), 5개 비즈니스 채널 기본값과 사례 17개(`business-korean.md`), 일반 글쓰기 장르 7개(`native-writing.md`), 채점 루브릭(`evaluation.md`)이 있다.
2. **k-humanizer-resume**: 이력서·경력기술·포트폴리오·지원서. 증거 밖의 주장을 만들지 않고 개인/팀 기여, 계획/완료, 지표의 측정 조건을 구분한다.

핵심 설계는 두 가지다(코드 확인). (a) 입력 모드 3종(한국어만 / 영어 원문+한국어 초안 / 영어만)에 따라 "무엇을 원문으로 보고 얼마나 고칠지"가 달라진다. 영어와 한국어 초안이 가격·날짜·정책에서 충돌할 때는 조용히 고르지 않고, 사용자가 정한 쪽을 따르거나 명백한 오역을 고치고 한 줄로 알리거나 질문 하나를 하거나 해당 문장을 미해결로 표시한다. (b) 자연스러운 글은 그대로 돌려주고, 고치려면 "범위 안의 구체적 문제"를 말할 수 있어야 한다. 사전적으로 금지한 단어는 없다.

### Feature map

<!-- 한 행 = 스펙 하나의 작업 단위. 이 레포는 코드가 아니라 지침이므로 "진입점"은 파일과 절(heading) 이름이고, 줄 번호는 기준 SHA의 줄이다. -->

| 기능 | 사용자 동작·경계 | 진입점·처음 읽을 코드 | 선행 | 구분 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|---|---|
| 1. 입력 모드 판별·원문 권위 해소 | 입력이 한국어만 / 영어+한국어 초안 / 영어만 중 무엇인지에 따라 작업(편집·대조 후 수정·번역)과 범위를 정한다. 영어와 한국어가 가격·날짜·한도·정책·약속에서 충돌하면 (사용자가 정함 → 따름 / 명백한 오역 → 고치고 한 줄 고지 / 불명확하고 상업 조건이 달라짐 → 질문 하나 또는 미해결 표시). 원화 가격·VAT 문구만으로는 한국어가 승인됐다고 보지 않는다. 포함 안 함: 한→영 번역(요청 시 충실하게, 이 스킬의 스타일 지침은 적용 안 함) | `skills/k-humanizer/SKILL.md` "1. Identify the input mode"(13-40) | 없음 | 핵심 | [input-mode-and-authority](./capabilities/input-mode-and-authority.md) · ready | 코드 확인 |
| 2. 상황 파악·기본값·누락 사실 질문 | 독자·채널·브랜드 어투(합쇼체/해요체/명사구)·목적을 요청과 기존 문구에서 추론하고, B2B 메일·계약·공지는 합쇼체, 소비자 앱은 해요체, 버튼·헤드라인·사양표는 명사구를 기본으로 한다. 기존 문구·브랜드 샘플이 기본값을 이긴다. 중요한 사실(가격·기간·버튼 동작)이 없으면 원문이 뒷받침하는 모든 것은 번역하고 필요한 필드만 중립 자리표시자로 둔 채, 독립적으로 빠진 사실마다 질문한다 | `SKILL.md` "2. Read the situation"(42-74) | 1 | 핵심 | [situation-defaults-and-questions](./capabilities/situation-defaults-and-questions.md) · ready | 코드 확인 |
| 3. 작성·편집과 멈춤 기준 | 의미(주체·행동·이유·조건·결과)를 먼저 읽고 번역투·과한 격식·영어 관용구·불필요한 대명사(`당신`·`그것`)·긴 명사화 문장·어투 혼용·번역된 명령형 CTA·AI 반복 문구를 본다. 고쳐도 되는 경우는 의미 오류, 문법 파탄, 한국 독자가 알아챌 번역투, 사용자나 맥락이 정한 어투·장르 불일치 중 하나를 "이름 붙일 수 있을 때"뿐이다. 유의어 교체·조사 다듬기·"고친 티"만 나는 수정은 원문 유지. 이미 자연스러우면 그대로 반환. 끝에 원문과 대조(주장·조건·숫자·플레이스홀더·책임·이유, 합친 절의 시점 한정). 포함 안 함: 진단표 내용(4), 보호 대상(5) | `SKILL.md` "3. Write or edit"(76-103), "5. Stop when the text works"(138-162) | 1, 4, 5 | 핵심 | [edit-and-stop-rule](./capabilities/edit-and-stop-rule.md) · ready | 코드 확인 |
| 4. 번역투·어미·흐름 진단표 | `patterns.md`의 표 7개(번역투 문법 / 어투와 어미 / 추상 명사·빈 무게 / 독자 관점의 구체성 / 영어·내부 용어 / 문장·단락 흐름 / 리듬과 문장부호). 각 행은 "원문에 X → 조건이 맞으면 Y → Z면 유지" 3칸이며 금지어가 아니다. 접속·연결어미는 인과·대조·순서가 원문에 있을 때만 쓰고 합친 문장의 사실별 시점을 보존한다 | `skills/k-humanizer/references/patterns.md` 전체(1-211) | 없음 | 핵심 | [pattern-diagnosis](./capabilities/pattern-diagnosis.md) · ready | 코드 확인 |
| 5. 사실·약속 보호 | 가격·통화·할인과 그 조건, 제품·플랜·브랜드·사람 이름, 숫자·통계와 비교·측정 조건, 계약·자격·한도, 날짜·시각·시간대·마감, 환불·교환·배송·해지, 보증 범위와 예외, 인용·코드·식별자는 조건째 유지. 부정·예외·`최대`·`약` 같은 한정어와 요청/제안/약속의 차이도 유지. 혜택·성능·후기·긴박감·사과·약속·판매 문구를 추가하지 않고 통화·시간대·단위를 바꾸지 않는다. 샘플·대안에도 같은 제한이 적용되고, 없는 항목은 `[보증 기간]` 같은 중립 자리표시자. UI는 자리표시자·변수·키·마크업을 그대로 두고 받침에 따라 틀릴 조사(`{name}과`)는 구조를 바꿔 피하며, 버튼은 실제 동작을, 문구는 영구 삭제·결제 같은 실제 결과를 말한다 | `SKILL.md` "4. Protect the facts and commitments"(105-136) | 없음 | 핵심 | [fact-protection](./capabilities/fact-protection.md) · ready | 코드 확인 |
| 6. 응답 형식·참조 선택 | 응답은 붙여넣기 가능한 한국어로 시작한다. 단순 편집·번역·이미 자연스러운 글은 한국어만(판정·수정 목록·확인 문구 없음), 오역 등 실질 차이를 고쳤으면 1~2문장, 사실 누락·미결정 버전이면 자리표시자를 남기고 질문(독립 사실마다 하나). 노트와 질문은 요청한 언어로 쓴다. 다른 톤·버전은 요청 없으면 내지 않는다. 용도별로 읽을 reference를 고른다(비즈니스 → 7, 일반 글쓰기 → 8, 평가 → 9, 이력서 → 별도 스킬) | `SKILL.md` "Use the relevant reference"(164-176), "Return the result"(178-199) | 1, 5 | 핵심 | [response-format](./capabilities/response-format.md) · ready | 코드 확인 |
| 7. 비즈니스 한국어 채널 규약 | 5개 채널(B2B 영업 메일, 마케팅·광고, 랜딩·제품 페이지, 고객 지원·서비스 공지, 앱 UI·알림)마다 기본 어투와 주의점, 입력 모드별 사례 17개(영어 원문·AI 번역·수정본·이유). 일부는 "수정하지 않음"이 정답이다. 포함 안 함: 사례의 정확한 문구(어느 쪽이든 사실·조건·어투·독자 행동이 같으면 통과) | `skills/k-humanizer/references/business-korean.md`(22-654) | 1, 2, 5 | 핵심 | [business-channel-rules](./capabilities/business-channel-rules.md) · ready | 코드 확인 |
| 8. 일반 한국어 글쓰기 장르 규약 | 문서·보고서, 개인·일상, 메신저, 동료 메일, 코드 리뷰 댓글, 공개 게시글, 대화문 7개 장르의 목표·규칙·전후 예시. 공개 글은 내부 경로·비공개 구현을 민감하게 다루고 허락이 불명확하면 지우지 말고 확인 요청 | `skills/k-humanizer/references/native-writing.md`(24-162) | 1, 5 | 핵심 | [native-writing-genres](./capabilities/native-writing-genres.md) · ready | 코드 확인 |
| 9. 평가 루브릭 (일반) | 출력 하나를 입력 모드별로 채점(의미 충실·한국어 자연스러움·맥락 적합·편집 절제·실용성 각 1~5), 도메인별 점검, 점수가 2 이하가 되는 Red Flags, 비즈니스 하드 페일(의미 충실을 1로 제한). AI 탐지 점수는 목표가 아님. 포함 안 함: 이력서 확장 루브릭(행 10으로 옮김) | `skills/k-humanizer/references/evaluation.md`(22-227) | 1, 5 | 핵심 | [evaluation-rubric](./capabilities/evaluation-rubric.md) · ready | 코드 확인 |
| 10. 이력서 증거 경계·재작성 | 재작성 전에 사실·행동·결과·숫자·기간, 개인/주도/공유/지원 구분, 측정됨/관찰됨/계획/미검증, 공개 가능 용어를 식별한다. 증거 없는 효과를 만들지 않고, 형용사 부풀리기·`저는` 시작·기여/고도화 같은 흐린 동사·숫자의 비교 조건 삭제·계획의 완료 표기·키워드 나열을 조건부 표로 처리한다. 읽는 순서는 문제·범위 → 판단·행동 → 확인된 결과. 선택·삭제·순서 변경은 사용자가 요청할 때만. 라우팅: 다른 한국어는 k-humanizer로 | `skills/k-humanizer-resume/SKILL.md`(1-60); `skills/k-humanizer-resume/references/resume.md`(22-152); 이력서 확장 루브릭 `skills/k-humanizer-resume/references/evaluation.md`(1-75) | S4, 9 | 핵심 | [resume-evidence-rewrite](./capabilities/resume-evidence-rewrite.md) · ready | 코드 확인 |
| 11. 이력서 작업 유형·섹션 역할·맞춤 | 입력 유형(완성 bullet / 전체 이력서 / 원자료 / 공고+경력)별 기본 응답, 증거 기록 8칸(문제·판단·행동·소유·상태·결과·측정·공개), 섹션별 역할(요약·경력·프로젝트·기술·학력·지원 글), 맞춤은 요청 시에만(직접/전이/미지원 증거 분류, 공백은 그대로 드러냄), 흔한 실패와 출력 패턴 | `skills/k-humanizer-resume/references/resume-workflow.md`(18-201) | 10 | 핵심 | [resume-workflow](./capabilities/resume-workflow.md) · ready | 코드 확인 |
| 12. 직무별 맥락 | 운영·기획·QA·디자인·마케팅·고객 응대·리서치·교육 8개 직무의 보존할 경력 세부, 도움이 되는 증거, 피할 표현, 직무 맞춤 전후 예시. 직무 키워드는 맥락일 뿐 경험의 증명이 아니다 | `skills/k-humanizer-resume/references/resume-roles.md`(18-126) | 10 | 핵심 | [resume-role-context](./capabilities/resume-role-context.md) · ready | 코드 확인 |
| 13. 지원 동기 | 검증된 경험 하나를 조직·직무의 구체적 일과 잇고, 믿을 수 있는 기여를 설명한다. 조직 이름을 바꿔도 문단이 성립하면 너무 일반적이라는 진단 검사. 회사 칭찬을 개인 증거로 쓰지 않는다 | `skills/k-humanizer-resume/references/application.md`(1-23); `resume-workflow.md` "Application writing" | 10 | 핵심 | [application-motivation](./capabilities/application-motivation.md) · ready | 코드 확인 |
| 14. 스킬 메타데이터·플러그인 배포 | 스킬 frontmatter(`name`, 호출 판단에 쓰이는 `description`), `agents/openai.yaml`(표시 이름·기본 프롬프트·암묵 호출 허용), Claude Code·Codex 마켓플레이스·플러그인 매니페스트, 설치 명령(README). 포함 안 함: 플러그인 로더의 실제 동작 | `plugin.json`; `.claude-plugin/plugin.json`; `.claude-plugin/marketplace.json`; `.agents/plugins/marketplace.json`; `skills/*/agents/openai.yaml` | S4 | 부속 | [plugin-packaging](./capabilities/plugin-packaging.md) · ready | 코드 확인(파일 내용), 설치 동작은 추론 |
| 15. 평가셋 스키마·검증 스크립트 | JSONL fixture 3종(v0 골든셋 220건·샘플·비즈니스 v1 32건)과 검증기 3개(스키마·도메인·모드·커버리지·ID 중복), 점수 기록 검증기(모든 fixture ID·입력 일치·점수 1~5·실패 유형 목록), 공개 위생 검사(키·토큰·이메일·전화번호 패턴), CI 단계 | `scripts/validate_business_set.py` `validate_file`; `scripts/validate_golden_set.py` `validate_file`; `scripts/validate_model_baseline.py` `validate_file`; `scripts/check_public_hygiene.py`; `.github/workflows/validate.yml` | S1, S2, S3 | 부속 | [eval-fixtures-and-validators](./capabilities/eval-fixtures-and-validators.md) · ready | 코드 확인(정적 읽기, 실행 안 함). 테스트 3개 미탐색 |
| 16. 평가 절차·실행 기록 | 비즈니스 forward test 절차(스킬 해시 기반 revision, 생성자는 `id`·`input`만 봄, 독립 리뷰, 보고), 2026-11-07 개발 점검 4회와 2026-08-25 v0 기준선의 수치·한계. 모두 모델 채점이고 사람 검토·held-out 아님 | `docs/validation-plan.md`(1-514); `evals/reports/2026-11-07-business-korean/business-review.md`; `evals/reports/2026-08-25/model-baseline.md` | 15 | 부속 | [eval-procedure-and-records](./capabilities/eval-procedure-and-records.md) · ready | 코드 확인(문서 읽음), 수치 재계산 안 함 |

**공유 계약** (여러 기능이 실제로 같이 쓰는 어휘·계약. 기능 개수에 넣지 않음)

| 계약 | 쓰는 기능 | 진입점·처음 읽을 코드 | 스펙·상태 | 검증 수준 |
|---|---|---|---|---|
| S1. 입력 모드 3종 어휘 | 1(소유), 3, 7, 9, 15 | `SKILL.md:15-19`(Korean only / English source with a Korean draft / English only), `scripts/validate_business_set.py:28-32`(`korean_edit`·`bilingual_edit`·`english_to_korean`), `evaluation.md:22-37` | [input-mode-and-authority](./capabilities/input-mode-and-authority.md) 1.3 · ready | 코드 확인 |
| S2. 보호 항목·하드 페일 | 5(소유), 3, 7, 9, 15 | `SKILL.md:105-136`, `evaluation.md:181-211`, fixture `grading.must_preserve`·`avoid` | [fact-protection](./capabilities/fact-protection.md) 1.3 · ready | 코드 확인 |
| S3. 평가 5축 점수 | 9(소유), 15, 16 | `evaluation.md:39-135`, `scripts/validate_model_baseline.py:12-18`(`SCORE_FIELDS`) | [evaluation-rubric](./capabilities/evaluation-rubric.md) 1.3 · ready | 코드 확인 |
| S4. 스킬 간 위임 | 6(소유), 10, 14 | `SKILL.md:171-172`(이력서는 `k-humanizer-resume`로), `skills/k-humanizer-resume/SKILL.md:52`(k-humanizer가 설치돼 있으면 그 `patterns.md`로 진단), 두 `description` | [response-format](./capabilities/response-format.md) 1.3 · ready | 코드 확인 |

**대조한 범위와 미탐색 영역**
- 대조: `git ls-files` 64개 전체 이름, README 기능 설명·설치 명령, 두 `SKILL.md` 전문, references 9개 전문, 매니페스트 4개와 `openai.yaml` 2개, 검증 스크립트 4개 전문, CI 워크플로, `docs/validation-plan.md` 전문, `CHANGELOG.md` 앞부분(0.3.0~Unreleased), 비즈니스 fixture 첫 행과 도메인·모드·행동 분포, 2026-11-07 보고서 앞부분(실행 표·귀속), 2026-08-25 기준선 앞부분.
- 문서와 구현의 차이:
  - `skills/k-humanizer/references/evaluation.md:219-221`은 비즈니스 fixture를 "30건(비즈니스 25 + 회귀 5)"이라 쓰지만, 파일은 32줄이다(비즈니스 `b2b_sales` 5·`marketing_ad` 5·`landing_page` 6·`support_notice` 6·`ui_notification` 5 = 27, 회귀 5, `grep`·`wc`로 셈). `docs/validation-plan.md`는 32건으로 맞게 쓴다. 30건은 2026-11-07 첫 점검의 fixture(`business-review.md` "Initial: 30, original fixture")다 → 갱신 누락(코드 확인).
  - `CHANGELOG.md` 0.5.0 항목은 `use-cases.md`를 말하지만 현재 파일은 `business-korean.md`다. Unreleased 항목에 "split business and native-writing references"가 있어 이름 변경은 설명되지만 0.5.0 문장은 옛 이름이다(코드 확인).
  - README는 "영어로 요청하면 설명도 영어"라는 지시가 SKILL.md에 있어도 기본 상태 점검 3건은 모두 한국어로 답했다고 스스로 적는다(`README.md` 버전 기록 아래 문단, `CHANGELOG.md` 0.5.0의 "Still open" 항목. `business-review.md`의 열린 문제 절은 읽지 않았다). 즉 행 6의 "요청한 언어로 쓴다" 규칙은 지침으로는 있고 관측으로는 지켜지지 않았다.
  - 플러그인 매니페스트는 스킬 경로를 나열하지 않는다. README의 "플러그인으로 두 스킬을 함께 설치"는 `source: "./"`와 루트 `skills/` 자동 탐색에 기대는 것으로 보이며 로더 동작은 확인하지 않았다(추론).
- 미탐색: `README.en.md`(번역본), `CONTRIBUTING.md`·`SECURITY.md`·`CODE_OF_CONDUCT.md`·이슈/PR 템플릿(규칙상 열지 않음), `scripts/test_validate_business_set.py` 60-137줄, `evals/fixtures/golden_set.v0.jsonl`·`golden_set.sample.jsonl` 본문(검증기가 정하는 스키마·건수와 `Counter`로 센 분포만 확인), `evals/reports/` 아래 `.jsonl` 원자료(`metrics.jsonl`·`runs.jsonl` 앞부분만), 외부 공개 데이터셋 후보(사용 안 함). 스킬이 실제 LLM에서 어떻게 동작하는지(출력 품질)는 확인하지 않았다.

### 권장 범위 (2026-11-10 승인됨, 이후 2차로 8·10~13·15·16 추가 승인)

목적이 정해지지 않아 "스킬을 다시 쓸 수 있는 규칙"을 기준으로 잡았다.

- **권장 행 1~7, 9**: 1~6은 `SKILL.md` 한 파일의 구조 그대로이고 행동 규칙(모드별 처리, 충돌 해소, 편집 수락 조건, 응답 모양)이 모여 있다. 4는 진단표라 표 자체가 스펙의 본문이다. 7은 채널별 기본값이 있는 곳이다. 9는 어떤 출력이 합격인지 정하는 기준이라 1~7을 검증하는 짝이다.
- **보류 8, 10~13**: 8은 사례 중심의 짧은 규칙이라 목적이 한국어 글쓰기 설계일 때만 필요하다. 10~13은 별도 스킬(이력서)이므로 이력서가 목적일 때만 쓴다. 이 경우 S4와 9의 이력서 확장 부분이 같이 필요하다.
- **제외 14~16(부속)**: 배포·평가 도구와 기록은 지침의 행동 규칙이 아니다. 단 15는 이 레포에서 유일한 실행 코드라 "평가셋을 같은 형식으로 만들고 싶다"면 넣는다.

### 통합 검토 (2026-11-10, 승인 범위 8개)

1. 빠진 행 없음: 1차 승인 8개(1~7, 9), 2차 7개(8, 10~13, 15, 16), 3차 1개(14)로 16행 모두 스펙이 있다. 쓰는 도중 feature map을 두 군데 고쳤다. 9번에서 이력서 확장 루브릭을 행 10으로 옮기고 선행에서 10을 뺐다(승인 범위 밖 스펙에 의존하면 `ready`가 될 수 없다). 행 3의 선행에서 2를, 행 6의 선행에서 2~4를 뺐다(스펙이 실제로 쓰는 계약만 `depends`에 둠).
2. 경계·공유 정의: S1(모드 이름 `Korean only` / `English source with a Korean draft` / `English only`와 fixture 값 `korean_edit` / `bilingual_edit` / `english_to_korean`)은 행 1에서만 정의하고 나머지는 링크한다. S2(보호 항목)는 행 5에서 정의하고 행 9의 하드 페일과 대응표로 맞췄다. S3은 행 9, S4는 행 6에 있다. 스펙 1.2의 "제외"가 서로 가리키는 경계(편집 판단 = 3, 진단 = 4, 어투 = 2, 출력 = 6)가 겹치지 않는다.
3. 선행·C-ID: 8개 스펙의 `depends`는 비순환이다(1, 5, 4는 선행 없음 → 2 → 3, 6, 7, 9). 줄 범위 C-ID는 스크립트로 파일 길이 안에 있는지 확인했고 모두 안에 있다. 사례의 입출력은 줄 범위로만 가리키고 문구는 복사하지 않았다.
4. 대표 흐름 하나(fixture `bk_support_006`: 고객 지원 답변): 입력은 영어 답변과 팀원이 번역한 한국어이고 어느 쪽이 승인됐다는 말이 없다 → **모드 B**로 판별(행 1 R-02, 영어가 기본 원문 R-10) → 독자는 고객, 채널은 지원 답변, 어투는 정중한 합쇼체(행 2 R-01·R-02, 행 7 R-06) → 한국어가 "환불 대상인지 검토"를 `전액 환불해 드리겠습니다`로 바꿨으므로 권위 표시가 없어 한국어를 고친다(행 1 R-06, 행 5 R-02·R-03: 약속 강화·추가 금지) → 영수증 요청과 검토 후 안내는 원문대로 유지하고 다른 곳은 건드리지 않는다(행 3 R-07·R-08) → 응답은 고친 한국어로 시작하고 "환불 약속을 검토 요청으로 고쳤다"는 노트 한 줄(행 6 R-01·R-03), 어느 버전이 승인됐는지는 묻지 않는다(행 1 R-10). 이 흐름은 평가에서 하드 페일 판정을 피한다(행 9 R-10).

**2차 통합 검토 (같은 날, 행 8·10~13·15·16 추가)**

1. 경계: 이력서 확장 루브릭(하드 페일·전용 채점 점검)은 행 10(`resume-evidence-rewrite` R-10·R-11), 직무별 채점 점검은 행 12(R-06), 일반 루브릭은 행 9로 나눴고 서로 중복하지 않는다. 행 10(증거·재작성 문장) / 11(작업 유형·섹션·맞춤) / 12(직무 표) / 13(지원 동기)은 각 스펙 1.2의 "제외"가 서로를 가리킨다. 행 15(스키마·검증기)와 16(절차·기록)도 같다. S3 필드 이름은 행 9가 정의하고 행 15가 `SCORE_FIELDS`의 원문 위치를 C-ID로 가진다.
2. 문서 차이 기록: 평가 문서의 비즈니스 fixture "30건"(실제 32건)을 행 9와 16의 2.1에 적었다. 행 12의 `resume_role` 값(`marketing_content` 등)과 직무 표 이름의 표기 차이를 행 12 확인 한계에 적었다.
3. 선행: `depends`는 비순환이다(8 → 1·5, 10 → 6·9, 11·12·13 → 10, 15 → 1·5·9, 16 → 15). 줄 범위 C-ID는 스크립트로 파일 길이 안에 있는지 확인했다.
4. 대표 흐름(이력서): 사용자가 한국어 이력서와 채용 공고를 주며 맞춤을 요청 → `k-humanizer`가 이력서·지원서는 다루지 않고 `k-humanizer-resume`으로 넘김(행 6 R-07, S4) → 작업 유형이 "공고+기존 경력"이고 맞춤이 요청됐으므로 구조·맞춤 허용(행 11 R-02·R-03·R-06) → 각 경력에서 증거 4항목·8칸을 뽑고 소유·상태·측정 조건을 확인(행 10 R-02, 행 11 R-04) → 직무 맥락으로 용어를 이해하고 공고 책임을 경험으로 복사하지 않으며 공백은 그대로 보임(행 12 R-02) → 조건부 표와 읽는 순서로 재작성(행 10 R-04·R-08·R-09) → 지원 동기 글이 있으면 경험 하나와 조직의 구체적 일을 잇는다(행 13 R-02·R-03) → 수정본이 앞, `근거 보완:`이 뒤인 응답(행 11 R-08) → 평가는 이력서 하드 페일로 판정(행 10 R-10).

**남은 한계**: 8개 스펙의 모든 R-ID는 `코드 확인`이지만 "지침 문장을 읽었다"는 뜻이다. 스킬을 LLM에 실제로 먹여 이 흐름이 재현되는지는 확인하지 않았다. 재구현 검증(4장 6번)은 사용자가 요청할 때만 한다.

---

## 3. 핵심 아키텍처 feature map (archify Diagrams)

| 다이어그램 | 원본 JSON | 시각화 HTML | 설명 |
|---|---|---|---|
| 전체 모듈 구조도 | [structure.json](./diagrams/structure.json) | [structure.html](./diagrams/structure.html) | 호스트 에이전트가 읽는 지침 파일 구조와 평가 도구 |

검증: archify `finalize`(validate·deliver·check·browser-check) 통과. 첫 결과에서 `main → patterns`와 `main → native`가 교차한다는 권고가 나와 노드 위치만 바꿔 다시 돌렸고(`diagrams/review-2/`) 권고 없이 통과했다. 시각 검토(이미지로 보기)는 하지 않았다.

### 그림 해설

**읽는 순서**
1. 글 쓰는 사람 → 호스트 에이전트: 사용자가 초안을 주면 호스트(Claude Code, Codex, Cursor 등)가 스킬을 읽는다. 웹 채팅·API에서는 README가 파일 내용을 직접 붙여 넣으라고 안내한다(`README.md` "사용 환경").
2. 호스트 → `k-humanizer SKILL.md`: 호스트는 frontmatter의 `description`을 보고 스킬을 고른다. `SKILL.md`가 모드 판별 → 상황 파악 → 작성 → 보호 → 멈춤 → 응답 순서를 정한다.
3. `SKILL.md` → references: 용도에 따라 `business-korean.md`(채널 규약), `patterns.md`(문구 진단), `native-writing.md`(일반 장르)를 읽고, 검토 요청이 오면 `evaluation.md`를 읽는다. 이력서·지원서는 `k-humanizer-resume`으로 넘긴다.
4. 평가 쪽: `evaluation.md`의 기준을 fixture와 검증 스크립트가 같은 어휘(모드·보호 항목·점수 축)로 쓴다.

**구조도: 모듈별 역할**

| 모듈 | 맡은 일 | 주고받는 것 | 근거 (`파일:심볼`) | 검증 수준 |
|---|---|---|---|---|
| 호스트 에이전트(외부) | 스킬 `description`으로 호출 여부 판단, 파일 읽기. `allow_implicit_invocation: true` | 사용자 요청 ↔ 스킬 지침 | `skills/k-humanizer/agents/openai.yaml:5-7`, `SKILL.md:1-4` | 코드 확인(메타데이터), 호스트의 실제 로딩 동작은 추론 |
| 플러그인 매니페스트 | Claude Code·Codex 마켓플레이스에 `k-humanizer` 하나를 `source: "./"`로 등록 | 설치 명령 → 호스트가 레포 루트를 플러그인으로 취급 | `.claude-plugin/marketplace.json`, `plugin.json`, `.agents/plugins/marketplace.json` | 코드 확인(파일 내용), 로더 동작은 추론 |
| `k-humanizer` SKILL.md | 5단계 규칙과 응답 형식. 비즈니스·일반·평가·이력서 중 읽을 곳 지정 | 사용자 텍스트 → 붙여넣기용 한국어 + 필요시 노트·질문 | `skills/k-humanizer/SKILL.md:13-199` | 코드 확인 |
| `patterns.md` | 진단표 7개. 금지어가 아니라 조건부 교체 | SKILL.md가 "어색한 이유를 진단할 때" 참조 | `skills/k-humanizer/references/patterns.md:1-24` | 코드 확인 |
| `business-korean.md` | 5개 채널 기본값과 사례 17개 | 채널·입력 모드별 기대 행동 | `skills/k-humanizer/references/business-korean.md:22-43` | 코드 확인 |
| `native-writing.md` | 일반 글쓰기 7개 장르의 규칙·예시 | 장르별 목표와 금지 | `skills/k-humanizer/references/native-writing.md:24-40` | 코드 확인 |
| `evaluation.md` | 모드별 채점, Red Flags, 비즈니스 하드 페일 | 출력 → 점수·합격 판정 | `skills/k-humanizer/references/evaluation.md:22-37,181-211` | 코드 확인 |
| `k-humanizer-resume` SKILL.md | 이력서 규칙, 읽을 reference 지정, 응답 형식 | 이력서 텍스트 → 증거 안의 한국어 + 필요시 질문 | `skills/k-humanizer-resume/SKILL.md:1-60` | 코드 확인 |
| 이력서 참조 5개 | 증거·워크플로·직무·지원동기·평가 | 직무·작업 유형별 규칙 | `skills/k-humanizer-resume/references/resume.md:22-68`, `resume-workflow.md:18-48`, `resume-roles.md:31-42` | 코드 확인 |
| 평가셋·검증 스크립트 | fixture 형식 검사, 점수 기록 검사, 공개 위생 검사, CI | fixture·점수 JSONL → OK/ERROR | `scripts/validate_business_set.py:58-183`, `.github/workflows/validate.yml:1-37` | 코드 확인(정적 읽기, 실행 안 함) |

**미확인 영역**
- 스킬을 LLM에 실제로 먹였을 때의 출력과 호스트별 로딩 방식.
- `scripts/test_*.py`의 시나리오, v0 골든셋 본문, 평가 원자료 `.jsonl`.
- 그림에서 `resume` → `patterns.md`(설치 시 참조) 선은 생략했다.

---

## 4. 질문 (Questions)

아직 없음.

---

## 5. 다음 작업 및 연계 링크

- **다음 세션 계획**: [next.md](./next.md)
- **기능 스펙**: 2절 feature map의 "스펙·상태" 칸 (16개 모두 ready)
