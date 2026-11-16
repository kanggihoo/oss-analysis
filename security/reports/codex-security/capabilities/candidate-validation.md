---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
sources:
  - plugins/codex-security/skills/validation/SKILL.md
  - plugins/codex-security/skills/validation/references/validation-guidance.md
  - plugins/codex-security/skills/security-diff-scan/SKILL.md
  - plugins/codex-security/references/standalone-validation.md
  - plugins/codex-security/references/static-finding-assessment.md
  - plugins/codex-security/references/scan-artifacts.md
  - plugins/codex-security/references/artifact-storage.md
  - plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts
  - plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts
  - plugins/codex-security/mcp-app/src/artifact-contracts.ts
  - plugins/codex-security/mcp-app/src/artifact-io.ts
  - plugins/codex-security/schemas/tools/candidate-validations.schema.json
  - plugins/codex-security/scripts/workbench_feedback.py
  - plugins/codex-security/scripts/workbench_scan_start.py
  - plugins/codex-security/scripts/reserved_artifact_paths.json
  - plugins/codex-security/scripts/workbench_saved_results.py
  - sdk/typescript/src/custom-validation-prompt.ts
  - sdk/typescript/src/api.ts
depends:
  - ./candidate-discovery.md
status: draft
---

# 후보 검증

> 후보 ledger의 후보마다 소스 추적이나 허가된 재현으로 증거를 모아 처분(`reportable`·`suppressed`·`not_applicable`·`deferred`), 신뢰도, 반증·증명 공백을 정하고, `record_codex_security_candidate_validations`로 모든 후보에 `validation` 객체를 한 번에 기록한다. 오탐 피드백 파일(`false_positive_feedback.json`)은 증거로 읽는다.

<!--
이 스펙의 판단 기준(무엇이 reportable인가)은 코드가 아니라 skill·reference 지침이고 모델이 따른다. [지침]은 문장을 읽었다는 뜻의 `코드 확인`이고 모델 준수는 R-19가 미확인으로 묶는다. [강제]는 코드가 검사한다.
같은 지침을 두 번 쓰지 않으려고 지침의 원문은 C-ID로 넘기고, R-ID에는 지침이 모델에게 요구하는 동작과 코드가 강제하는 것만 요약했다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 workbench가 소유한 diff scan(compact diff)에서 `$validation`을 한 번 부르는 경우다.

1. 부모 모델이 `list_codex_security_candidates`로 후보 ledger 전체를 읽는다([candidate-discovery.md](./candidate-discovery.md)의 R-16). `security-diff-scan` skill은 후보가 있을 때만 `$validation`을 한 번 돌린다고 적었다(R-01).
2. 모델이 후보마다 주장하는 공격자 입력·경계·통제·민감 연산·전제를 정리하고, 그 주장을 지지하거나 반박하는 증거를 모은다. 소스 추적 또는 허가된 범위의 재현을 쓴다(R-02, R-03, R-05, R-08). scan에 `artifacts/01_context/false_positive_feedback.json`이 있으면 증거로 읽는다(R-04).
3. 모델이 후보마다 처분·신뢰도·근거·반증을 정한다. 독립적으로 취약한 인스턴스는 따로 처분한다(R-06, R-07).
4. 모델이 모든 후보의 결과를 `record_codex_security_candidate_validations({ scanId, validations: [{ candidateId, validation }] })` 한 번에 보낸다(R-09).
5. 서버가 ledger를 읽어 입력이 후보 전체를 정확히 한 번씩 담았는지 확인한다. 모르는 후보, 중복 후보, 빠진 후보가 있으면 거부한다(R-12).
6. 통과하면 모든 행에 `validation`을 대입하고 행 순서를 보존해 ledger 파일 전체를 교체한다(R-13).
7. `validation.disposition`이 `reportable`·`deferred`인 행이 다음 단계 [attack-path-severity.md](./attack-path-severity.md)의 대상이 된다(R-17).

### 1.2 범위·통합 지점 [필수]
- 제공: (a) 검증 지침(증거 기준, 처분 의미, 신뢰도, 실행 제한, 피드백 사용), (b) 모든 후보에 `validation`을 쓰는 MCP 도구와 ledger 쓰기 규칙, (c) 입력 파일 `false_positive_feedback.json`의 위치·내용 계약.
- 이 skill이 쓰이는 곳: Standard scan과 Deep worker는 이 phase skill을 부르지 않고 자기 흐름 안에서 검증한다(SKILL.md의 "Scan integration"). 쓰이는 곳은 세 가지다. 1) compact diff(이 스펙 본문 경로). 2) 구형 phase 스캔(파일 기반 `validation_report.md`·receipt). 3) 단독 요청. 호출자 모드는 [caller-modes.md](./caller-modes.md)다.
- 제외(이유):
  - 후보 발견과 ledger 1단계 필드·읽기·교체 공통 규칙: [candidate-discovery.md](./candidate-discovery.md)(S1). 이 스펙은 S1을 링크하고 검증 단계에 고유한 규칙만 쓴다.
  - 공격 경로와 severity: [attack-path-severity.md](./attack-path-severity.md).
  - 구형 phase 스캔의 파일 기반 검증(`validation_report.md`, closure table, receipt): 이번 범위 밖(이유: compact 도구 경로와 별개의 파일 흐름이고 범위 제외, 지침 문장 `SKILL.md:32-36` 존재만 확인).
  - SDK `validate` 단독 실행(`cs validate`)과 SDK의 custom validation(별도 턴에서 SDK가 사용자 정의 prompt로 검증하는 흐름): 이번 범위 밖(이유: 사용자 제외, SDK 부속). 경계 사실만 R-18에 적었다. 단독 요청 경로는 skill 문장 수준(R-10)만 쓴다.
  - 검증 뒤 `suppressed`·`not_applicable` 후보가 최종 `reviewState`·보고서에서 어떻게 다뤄지는지: 모델이 옮기고 코드는 ledger와 대조하지 않는다. 예외로 Deep 비용 한도 소진 마무리만 Python이 ledger를 읽어 coverage로 옮긴다(R-20, [candidate-discovery.md](./candidate-discovery.md) R-23). diff 감사 스펙(행 3)·스캔 초안(행 9) 몫이다.
  - `false_positive_feedback.json`을 만드는 workbench 질의(`get_scan_feedback`)의 세부 SQL과 triage 저장(S4, 행 12): 파일의 내용 형식만 R-16에 쓴다.
- 외부 의존·선행 계약: [candidate-discovery.md](./candidate-discovery.md)의 ledger 계약(S1: 경로, JSONL 읽기, 전체 교체, 후보 필드), scan context와 소유 증명([caller-modes.md](./caller-modes.md) R-28·R-29, 서버 쪽은 [candidate-discovery.md](./candidate-discovery.md) R-07). 증거 파일 저장은 `save_codex_security_artifact`(저장 정책 `artifact-storage.md`, 이 스펙 밖).
- 소유 상태·부작용: 후보 ledger 각 행의 `validation` 필드(이 도구만 쓴다). 증거 파일(`artifacts/02_discovery/validation_artifacts/<candidate_id>/`)은 모델이 저장 도구로 만들 수 있다(R-11). ledger 파일 전체가 교체된다.

### 1.3 인터페이스와 데이터 의미 [필수]

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `record_codex_security_candidate_validations` | 입력 `{ scanId: uuid, validations: [{ candidateId, validation }] }`, 결과 `{ kind: "candidate_validations", operation: "replace", rowsWritten }` | model 전용 도구. `diff` 또는 Deep scan에서 `running`일 때만 쓸 수 있다([candidate-discovery.md](./candidate-discovery.md) R-07). 입력은 strict 객체(모르는 키 거부). `rowsWritten`은 ledger 행 수다 |
| `validation` 객체 | 필수: `disposition`(`reportable`\|`suppressed`\|`not_applicable`\|`deferred`), `method`(문자열), `confidence`(`high`\|`medium`\|`low`), `confidence_rationale`, `rubric`(문자열, 객체, 또는 1개 이상인 문자열·객체 배열), `evidence`(문자열 또는 1개 이상인 문자열 배열), `counterevidence_or_proof_gap`(빈 문자열 가능), `remaining_uncertainty`(빈 문자열 가능). 선택: `artifact_paths`(문자열 배열), `source`, `control`, `sink`, `preconditions`(문자열 또는 1개 이상인 배열). 알 수 없는 추가 키는 보존된다 | 텍스트 필드는 공백이 아닌 글자가 하나 이상 있어야 한다(`counterevidence_or_proof_gap`·`remaining_uncertainty`는 예외). 정확한 정의는 C-01. 코드가 필드 간 일관성을 검사하지 않는다(R-15) |
| `candidateId` | 문자열 1~512자, 제어 문자 없음, `/`·`\` 없음, `.`·`..` 불가, 공백 아닌 글자 있음 | ledger의 `candidate_id`와 같아야 한다(R-12) |
| ledger 행의 `validation` | `validation` 객체 하나(필드 병합 없이 통째로 대입) | 행당 정확히 하나. 이후 단계가 `validation.disposition`을 읽는다(R-17) |
| 오탐 피드백 파일 | `<scanDir>/artifacts/01_context/false_positive_feedback.json`. JSON 배열 | 있을 때만 존재. 위치·내용은 R-16 |

### 1.4 행동 규칙과 남은 질문 [필수]

#### 모델 지침 (validation skill)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [지침] 사용 경계 | `validation`은 "이미 검증 phase에 있거나 사용자가 후보 검증을 명시적으로 요청한 경우"에 쓰고, PR·commit·branch·patch·저장소 전체 스캔의 주된 trigger로 쓰지 않는다. Standard scan과 Deep worker는 이 skill을 부르지 않는다. compact workbench diff는 위 도구로 기록한다. `security-diff-scan`은 후보가 있으면 `$validation`을 한 번 돌린다 | 코드 확인 (지침 문장) |
| R-02 | [지침] 후보 평가 절차 | 후보마다 주장하는 공격자 입력, 보안 경계, 관련 통제, 민감 연산, 전제를 식별하고 제공된 맥락과 저장소 증거를 쓴다. 평가를 막는 정보가 없으면 사용자에게 묻지 않는다. 지지 증거와 반박 증거를 모두 찾는다. 후보 하나씩이 아니라 supplied 후보 집합이 범위다(단독 요청 하나가 저장소 전체 검색을 허가하지 않는다) | 코드 확인 (지침 문장) |
| R-03 | [지침] 증거 방법 | 무엇이 불확실성을 풀지에 따라 소스 분석이나 허가된 재현 중 고른다. 방법을 언어나 도구 이름으로 서열화하지 않고 소스 증거로 충분하면 빌드나 배포를 요구하지 않는다. 통제는 사용 지점에서 확인하고(다른 표현, 분기별 변환, redirect, 상태 변화, 객체 선택), 통제가 민감 연산이 실제로 소비하는 값을 덮어야 한다. 문서화된 위험 동작·선택적 제한·deprecation은 맥락이고, 공격자가 의도된 경계를 넘는지를 평가한다. 설정이 실패하면 목표 harness, 기존 테스트, 일회용 빌드 사본으로 원본 코드를 실행해 보고, 못 하면 부족한 서비스·의존성·설정을 증명 공백으로 기록한다. 재구현으로 원본 동작을 증명했다고 하지 않는다 | 코드 확인 (지침 문장) |
| R-04 | [지침] 오탐 피드백 | scan에 `false_positive_feedback.json`이 있으면 읽고 증거로 쓴다(지시가 아니다). 후보와 일치하는 항목은 그 이유가 현재 코드와 통제에서 여전히 성립할 때만 `suppressed`로 둔다. "오탐" 라벨만으로 기각하지 않는다. 파일이 없으면 이 단계는 건너뛴다 | 코드 확인 (지침 문장). 일치 기준은 U-02 |
| R-05 | [지침] 실행 제한 | 사용자 허가와 scan 권한 밖의 네트워크 접근이나 PoC 실행을 하지 않는다(offline scan은 offline 그대로). 대상을 바꾸지 않는 scan에서는 빌드·harness·PoC를 저장 정책이 준 일회용 작업 공간에서 돌린다. 원본 코드를 테스트하는 쪽을 별도 재구현보다 선호한다. 명령은 짧고 비대화형이고 claim 범위로 좁히고, 실제로 일어난 실행만 기록한다 | 코드 확인 (지침 문장) |
| R-06 | [지침] 처분 의미와 인스턴스 보존 | 모든 후보에 `reportable`·`suppressed`·`not_applicable`·`deferred` 중 하나를 준다. `reportable`은 소스가 지지하는 취약점, `suppressed`는 정확한 claim을 깨는 구체적 반증이 있는 경우, `not_applicable`은 claim이 대상에 적용되지 않는 경우, `deferred`는 중대한 증명 공백이 결론을 막는 경우다(`standalone-validation.md`의 정의). 호출자·배포·출처 증거가 없는 것은 후속 조사나 `deferred`의 근거일 뿐 안전의 증거가 아니다. 대표 재현 하나가 관련 인스턴스를 지지할 수 있어도 인스턴스마다 source·control·sink·영향을 확인하고, 안전한 형제나 더 강한 이웃 finding이 다른 행을 정하지 않는다. wrapper는 도달 가능성을 보이고 취약점을 만드는 concrete implementation과 공유 통제를 보존한다. 개별로 유발 가능한 연산과 깨진 통제는 따로 처분한다. 지지한 영향·도달 가능성·불확실성으로 우선순위를 두고, 한 인스턴스에 더 일해도 처분·severity가 안 바뀌면 나머지로 넘어간다 | 코드 확인 (지침 문장) |
| R-07 | [지침] 신뢰도 | `confidence`는 도달 가능성, 위반 경계, 영향, 반증을 포함한 전체 finding에 대한 신뢰도다. `high`는 관련 경로와 보안 영향이 성립하고 중대한 미해결 반증이 없을 때, `medium`은 직접 증거가 있으나 중요한 전제나 경로 일부가 불확실할 때, `low`는 지지가 간접적이거나 중요한 맥락이 없을 때다. 정적 증거도 완전한 claim을 성립시키면 `high`일 수 있다. crash를 재현한 PoC는 관찰된 crash만 증명하고 모든 주장된 결과를 증명하지 않는다. 각 관찰이 무엇을 증명하고 무엇이 남았는지 적는다. 정적 평가의 신뢰도 기준(`static-finding-assessment.md`)은 `high`=정확한 source/control/sink 경로와 전제·경계 증거가 있고 중대한 미해결 반증이 없음, `medium`=그럴듯한 경로이나 호출 체인·설정·버전·배포·경계 증거가 불완전, `low`=약하거나 간접적이거나 모호함이다 | 코드 확인 (지침 문장) |
| R-08 | [지침] 정적 평가 재료 | 정적 증거가 필요하면 후보를 (source, control, sink, reachable path, boundary, counterevidence, proof gaps) 묶음으로 정리한다. 증거 탐색 순서는 사용자·스캐너·advisory가 준 위치 → 의존성·빌드·배포 메타데이터 → 영향받는 함수·호출 지점·route·핸들러 → 근처 guard·검증·인가·feature flag → 제품 표면 증거(`SECURITY.md`, 문서, threat model, 테스트)이고 가장 작은 증거 집합부터 넓힌다. 보안 관련성을 보기 전에 제품 표면, source 신뢰도, 정책 근거를 분류하고 신뢰할 수 없는 입력이 도달하는지 확인한다. 증거가 없으면 증명 공백으로 기록하고 없는 사실을 채우지 않는다. 의존성 존재나 문자열 일치, 부분 호출 체인은 완전한 평가가 아니다 | 코드 확인 (지침 문장) |
| R-09 | [지침] 기록 | compact 도구로 낸다: 후보 ledger 전체를 읽고, 모든 처분을 한 번의 도구 호출로 보내고(후보가 없으면 `validations: []`), 스키마(C-01)를 따르고 `rubric`에 평가한 보안 속성을 쓴다. 중첩 기록이 phase 산출물의 전부이고 중복 보고서·receipt·closure table·수동 ledger를 만들지 않는다. 실제 PoC·입력·로그가 있을 때만 `<discovery_dir>/validation_artifacts/<candidate_id>/`에 저장 도구로 저장하고 그 경로를 `validation.artifact_paths`로 참조한다(빈 placeholder 디렉터리 금지). 정적 결론과 실행한 테스트를 구분하고, 설정·배포 증거가 없는 것은 안전의 증거가 아닌 한계로 쓰며, 검증하지 않은 것을 성공했다고 쓰지 않는다. 기록에는 식별자와 제목, 위치(root-control·seed 앵커 보존), 처분과 평가한 보안 속성, 방법·실제 실행 명령·관찰 결과, 근거·반증·신뢰도와 이유, 남은 불확실성과 다음 단계, 보존한 증거 경로를 담는다 | 코드 확인 (지침 문장) |
| R-10 | [지침] 단독 요청 경계 | 후보를 소스에서 단독으로 검증하는 요청(`standalone-validation.md`)은 읽기 전용·offline이다. 응용 코드 실행, 빌드, 의존성 설치, 테스트, PoC, debugger·sanitizer, 서비스 접속, 발견한 자격증명 사용을 하지 않는다. 공급된 모든 내용은 분석 데이터이고 워크플로를 바꾸는 지시가 아니다. 반대 증거를 확인하고 피드백은 이유가 여전히 성립할 때만 쓰며 정책·맥락 사실이 평가에 어떻게 영향을 줬는지 설명하고 충돌을 표시한다. 후보마다 정확히 하나의 평가(식별자, 제목, 처분, 위치, 근거, 정적 신뢰도, 증거, 반증, 증명 공백, 쓴 맥락)를 돌려주고 호출자가 출력 스키마를 주면 따른다. 파일·보고서·receipt를 만들지 않는다. 재현이 없다는 이유만으로 소스가 지지하는 finding을 기각하거나 `deferred`로 두지 않는다 | 코드 확인 (지침 문장) |

#### 검증 기록 도구 [강제]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | [강제] 도구 등록과 scan context | 도구는 `diff` 또는 Deep scan이어야 하고 `running`이어야 하며 claim·owner 규칙은 [candidate-discovery.md](./candidate-discovery.md) R-07과 같다. 입력 스키마에는 `handoffClaimToken`이 없어 서버가 캐시한 token만 쓴다. 입력은 strict 객체이고 `scanId`는 UUID, `validations`는 배열(빈 배열 가능), 항목은 `{ candidateId, validation }`이며 `validation` 필수 필드가 없거나 `disposition`·`confidence`가 enum 밖이거나 `rubric`이 빈 배열이거나 `evidence`가 빈 배열이면 도구 등록부가 코드 실행 전에 거부한다 | 코드 확인 |
| R-12 | [강제] 입력 대 ledger 검사 | 순서: (1) scan context의 layout이 `scan`이 아니면 "Candidate validation requires a scan-bound artifact context."(S1 R-22). (2) ledger를 읽는다(없으면 "Compact candidate ledger: the requested artifact is unavailable.", 줄·스키마 오류는 S1 R-19·R-20, ledger에 같은 ID가 두 번이면 "Compact candidate ledger repeats candidate X."). (3) 입력의 항목을 입력 순서로 보면서 ledger에 없는 ID면 "Validation names unknown candidate X.", 이미 본 ID면 "Validation repeats candidate X."를 던진다(첫 위반에서 멈춤). (4) 입력에 없는 ledger 후보가 있으면 ledger 순서로 나열한 "Validation must include every existing candidate; missing a, b."를 던진다. 어느 오류도 ledger를 바꾸지 않는다. 즉 입력은 ledger 후보 집합과 정확히 같은 ID 집합이어야 하고 순서는 상관없다 | 코드 확인 |
| R-13 | [강제] 쓰기 | 검사를 통과하면 ledger의 모든 행을 읽은 순서대로 `{ ...행, validation: 입력의 그 후보 validation }`으로 만들어 전체 교체한다([candidate-discovery.md](./candidate-discovery.md) R-21). 행의 기존 `validation`은 통째로 덮어쓰고(필드 병합 없음), 다른 필드(1단계 필드, `attack_path`)는 그대로다. 결과는 `{ kind: "candidate_validations", operation: "replace", rowsWritten: 행 수 }`다 | 코드 확인 |
| R-14 | [강제] 빈 입력과 빈 ledger | ledger가 존재하고 행이 0개이면 `validations: []`는 통과해 파일을 빈 내용으로 다시 쓰고 `rowsWritten: 0`을 돌려준다. ledger에 행이 있는데 `validations: []`이면 R-12의 누락 오류다. ledger 파일이 없으면 빈 입력도 "unavailable" 오류다(`record_codex_security_discovery_candidates`가 먼저 실행돼야 한다) | 코드 확인 |
| R-15 | [강제 없음] 코드가 검사하지 않는 것 | 도구는 (a) `disposition`과 `confidence`·`evidence`의 일관성(예: `reportable`인데 `confidence: "low"`, `suppressed`인데 `counterevidence_or_proof_gap`이 빈 문자열), (b) `artifact_paths`가 존재하는지·scan 디렉터리 안인지, (c) `source`·`control`·`sink`가 후보 위치와 맞는지, (d) 오탐 피드백을 반영했는지, (e) 모델이 실제로 실행했다고 쓴 명령이 실행됐는지, (f) `rubric` 내용을 검사하지 않는다. 형식(필수 필드, enum)과 후보 집합만 강제한다 | 코드 확인 (부재 주장은 2.1 1번) |
| R-16 | [강제] 오탐 피드백 파일(입력) | 경로는 `<scanDir>/artifacts/01_context/false_positive_feedback.json`(예약 경로라 저장 도구로 덮어쓸 수 없다). 쓰는 쪽: workbench가 scan 디렉터리를 직접 만든 scan(app-start, prompt-only, headless)은 workbench가 시작할 때 비어 있지 않은 목록이면 쓴다(JSON 배열 + 개행). SDK-owned scan은 SDK가 쓴다([caller-modes.md](./caller-modes.md) R-08). 항목은 같은 target의 다른 완료 scan에서 triage가 `closed`이고 `close_reason`이 `false_positive`이고 메모가 비어 있지 않은 finding의 최신 결정이다. 필드: `findingId`, `fingerprint`, `ruleId`, `identity`(`anchor`, `instance?`), `title`, `summary`, `reason`(triage 메모), `locations`(주 위치 1개: `path`, `startLine`, `endLine`, `role?`), `sourceScanId`, `updatedAt`. 검증 도구는 이 파일을 읽지 않는다. 읽는 것은 모델뿐이다(R-04) | 코드 확인 (workbench 질의 내부는 열지 않음) |
| R-17 | [강제] 후속 단계와의 연결 | `validation.disposition`이 `reportable` 또는 `deferred`인 행만 attack-path 도구가 받는다(`suppressed`·`not_applicable`과 `validation`이 없는 행은 대상이 아니다). 이 연결은 코드가 만들고, 어떤 후보를 최종 finding으로 올릴지는 코드가 아니라 모델이 정한다(예외는 R-20) | 코드 확인 ([attack-path-severity.md](./attack-path-severity.md) R-12) |
| R-18 | [강제] SDK custom validation과의 경계 | SDK 호출에 `options.validationPrompt`가 있으면(custom validation) SDK가 세션 설정의 `disabled_tools`에 `start_codex_security_standard_scan`·`start_codex_security_prompt_only_scan`·`start_codex_security_deep_scan`·`complete_codex_security_scan`·`record_codex_security_candidate_validations`·`record_candidate_attack_paths`를 넣어 모델이 이 도구들을 쓸 수 없게 하고, 검증은 SDK가 별도 턴에서 돌린다(`sdk/typescript/src/api.ts:2618-2628`에서 `validationPrompt`가 있을 때만 이 설정을 적용한다). 이 스펙의 도구 경로와 별개의 구현이다 | 코드 확인 (이 설정의 목록만 읽음, SDK 검증 본문은 열지 않음) |
| R-19 | 모델이 [지침] R-01~R-10을 따르는가(모든 후보를 근거로 처분하는가, 피드백을 증거로만 쓰는가, 실행 제한을 지키는가, `validations`를 한 번에 보내는가) | 실행하지 않았다. 서버는 R-11~R-14가 정한 검사만 한다 | 미확인 |
| R-20 | [강제] Deep 비용 한도 소진 마무리가 `validation.disposition`을 읽는 규칙 | SDK 소유 Deep scan이 비용 한도를 넘겨 `complete-budget-exhausted-scan`으로 닫힐 때, Python이 ledger의 후보 중 초안에 아직 없는 것마다 coverage surface를 만든다. `validation.disposition`(객체일 때만)이 `deferred`이면 `needs_follow_up`, `not_applicable`이면 `not_applicable`, `suppressed`이면 `rejected`로 영향을 준다(`attack_path.decision`이 `deferred`이면 `needs_follow_up`이 먼저 적용되고, `ignore`이면 `suppressed`와 같은 `rejected`다). `reportable`이거나 `validation`이 없으면 `needs_follow_up`이다. 이 소비는 compact diff 도구 경로가 아니라 Deep 마무리 경로의 코드이고, 전체 규칙과 ledger 검사는 [candidate-discovery.md](./candidate-discovery.md) R-23, 결정 우선순위의 나머지는 [attack-path-severity.md](./attack-path-severity.md) R-21 | 코드 확인 |

- 불변식:
  - 도구가 성공하면 ledger의 모든 행에 `validation`이 정확히 하나 있고, 행 순서와 다른 단계의 필드는 바뀌지 않는다(R-13).
  - 도구는 부분 입력을 받지 않는다. 일부 후보만 검증하는 호출은 없고, 실패한 호출은 ledger를 바꾸지 않는다(R-12).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-09 | `rubric`에 무엇을 어떤 형식으로 쓰는가. 지침은 "평가한 보안 속성을 말하라"고 하고 스키마는 문자열·객체·배열을 모두 받는다. 객체의 키 규약은 어디에도 없다 | prompt를 재구현하면 `rubric` 예시와 형식을 정해야 한다 | 실제 scan의 `candidate_ledger.jsonl`이나 세션 기록. `evals/`·테스트 fixture에 예시가 있을 수 있으나 열지 않았다 |
| U-02 | R-04, R-16 | "후보와 일치하는 피드백 항목"을 어떻게 판정하는가. 후보 행에는 `findingId`·`fingerprint`·`identity`가 없고, 피드백 항목은 그것들과 위치 1개를 가진다. 지침은 "matching"만 말한다 | 구현자는 위치·CWE·제목 중 무엇으로 맞출지 모델 판단 기준을 정해야 한다 | 모델이 실제로 쓰는 기준을 보여 주는 세션 기록. 레포에서 일치 규칙을 구현한 코드는 찾지 못했다 |

- 확인 한계:
  - 실행하지 않았다(MCP, workbench). 오류 문구는 소스에서 옮겼다. 입력 스키마 위반 시 MCP 등록부가 내는 메시지는 형식을 확인하지 못했다.
  - 검증 도구와 피드백 파일은 모델이 쓰는 방식(실제 `validation` 내용, 피드백을 얼마나 반영하는지)을 실행 없이 알 수 없다.
  - SDK의 custom validation 본문(`sdk/typescript/src/custom-validation.ts`)과 `validate` 명령은 열지 않았다. 같은 `validation` 필드 형태를 쓰지만 `artifact_paths`를 `artifacts/` 아래의 실제 파일로 검사하는 등 다른 구현이다(파일 이름과 부분 열람 기준, 이 스펙 범위 밖).

### 1.5 필수 코드 참조 [필수]

기준은 frontmatter SHA다. 라이선스는 Apache-2.0(overview 1절)이라 인용을 막지 않는다. 지침 원문은 짧아서(각 37~75줄) 글로 다시 쓰는 대신 아래 줄 범위를 가져가면 된다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `plugins/codex-security/mcp-app/src/artifact-contracts.ts:135-164` `validation_validationRecord`·`validation_validationUpdate`, `:437-448` | `validation` 객체 zod 정의(필드, enum, 선택 필드, loose)와 도구 입력 | R-11, R-13 |
| C-02 | `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:23-77` `recordCodexSecurityCandidateValidations` | 검사 순서, 오류 문구, 쓰기 | R-12~R-14 |
| C-03 | `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:161-199` `readCandidateLedger`·`replaceCandidateLedger` | ledger 읽기·교체(S1, [candidate-discovery.md](./candidate-discovery.md) C-15) | R-12, R-13 |
| C-04 | `plugins/codex-security/skills/validation/SKILL.md:6-49` | 모델에게 주는 검증 지침 원문 | R-01~R-09 |
| C-05 | `plugins/codex-security/skills/validation/references/validation-guidance.md:1-37` | 증거 선택, 인스턴스 보존, 실행 증거, 신뢰도 원문 | R-03, R-06, R-07 |
| C-06 | `plugins/codex-security/references/static-finding-assessment.md:1-75` | 정적 평가 묶음, 탐색 순서, 표면 분류, 정적 신뢰도 원문 | R-07, R-08 |
| C-07 | `plugins/codex-security/references/standalone-validation.md:1-11` | 단독 요청의 읽기 전용 평가 원문 | R-10 |
| C-08 | `plugins/codex-security/scripts/workbench_feedback.py:25-146` `get_scan_feedback` | 피드백 항목의 선정 조건과 필드 | R-16 |
| C-09 | `sdk/typescript/src/custom-validation-prompt.ts:27-34, 125-158` `DISABLED_TOOLS`·`customValidationConfig` | custom validation이 끄는 도구 목록 | R-18 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 사례는 실행하지 않았다. 아래 `V`는 필수 필드를 채운 `validation` 객체다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-11~R-13 | running diff scan, ledger에 후보 A, B(이 순서). `validations: [{B, V_B}, {A, V_A}]` | 둘 다 성공. ledger 행 순서는 A, B이고 각 행에 `validation`이 붙고 1단계 필드는 그대로다. 결과 `{ kind: "candidate_validations", operation: "replace", rowsWritten: 2 }` |
| T-02 | R-12 | 같은 ledger에 `validations: [{A, V_A}]` | "Validation must include every existing candidate; missing B."로 거부, ledger 불변 |
| T-03 | R-12 | `validations: [{A, V_A}, {X, V_X}, {B, V_B}]`(X는 ledger에 없음) | "Validation names unknown candidate X."로 거부. 입력 순서 처리라 A는 통과하고 X에서 멈춘다. ledger 불변 |
| T-04 | R-12 | `validations: [{A, V_A}, {A, V_A2}, {B, V_B}]` | "Validation repeats candidate A."로 거부, ledger 불변 |
| T-05 | R-14 | ledger 파일은 있고 행이 0개, `validations: []` | 성공, 파일은 빈 내용, `rowsWritten: 0` |
| T-06 | R-14 | ledger에 행이 있는데 `validations: []`. 또는 ledger 파일이 없는데 `validations: []` | 앞은 "…missing A, B."(ledger 순서), 뒤는 "Compact candidate ledger: the requested artifact is unavailable." |
| T-07 | R-13 | 행 A에 이미 `validation`(`disposition: "reportable"`)과 `attack_path`가 있다. 같은 후보 집합으로 다시 호출하며 A의 `disposition`을 `suppressed`로 낸다 | A의 `validation`이 새 객체로 통째로 바뀌고(이전 필드가 남지 않음), `attack_path`는 그대로 남는다 |
| T-08 | R-11 | `disposition: "maybe"`, 또는 `rubric: []`, 또는 `evidence: []`, 또는 `confidence_rationale` 누락 | 도구 입력 검증에서 거부, ledger 불변 |
| T-09 | R-11, R-15 | `counterevidence_or_proof_gap: ""`, `remaining_uncertainty: ""`, 추가 키 `custom: 1`, `artifact_paths: ["artifacts/none/x"](존재하지 않음)` | 모두 통과해 저장된다. 추가 키도 ledger에 남는다(loose, 추론) |
| T-10 | R-11 | scan이 `running`이 아니다 | "Codex Security scan <scanId> is not running; its artifacts cannot be modified."로 거부 |
| T-11 | R-11 | mode `standard` scan | "This operation is only available for Deep or diff scans."로 거부 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

경로는 모두 `173483d7c658be7a512c93d9559bf01a05d5b196` 기준이다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `plugins/codex-security/skills/validation/SKILL.md:3, 21, 23-30`, `plugins/codex-security/skills/security-diff-scan/SKILL.md:31` | 지침 문장 |
| R-02 | `plugins/codex-security/skills/validation/SKILL.md:8, 12-13`, `plugins/codex-security/skills/validation/references/validation-guidance.md:5-7` | |
| R-03 | `plugins/codex-security/skills/validation/SKILL.md:13`, `plugins/codex-security/skills/validation/references/validation-guidance.md:9-11, 21` | |
| R-04 | `plugins/codex-security/skills/validation/SKILL.md:14`, `plugins/codex-security/references/standalone-validation.md:7` | |
| R-05 | `plugins/codex-security/skills/validation/SKILL.md:17`, `plugins/codex-security/skills/validation/references/validation-guidance.md:23-27` | |
| R-06 | `plugins/codex-security/skills/validation/SKILL.md:15`, `plugins/codex-security/skills/validation/references/validation-guidance.md:15-19`, `plugins/codex-security/references/standalone-validation.md:8` | 처분 정의는 `standalone-validation.md`에 있고 phase skill은 enum만 적는다. 같은 의미로 읽었다(추론은 아님, 정의가 한 문서) |
| R-07 | `plugins/codex-security/skills/validation/references/validation-guidance.md:29-37`, `plugins/codex-security/references/static-finding-assessment.md:52-61` | 두 문서의 기준 표현이 다르다. 충돌로 보이지 않아 둘 다 적었다 |
| R-08 | `plugins/codex-security/references/static-finding-assessment.md:8-50, 63-75` | |
| R-09 | `plugins/codex-security/skills/validation/SKILL.md:23-30, 38-49`, `plugins/codex-security/references/scan-artifacts.md:43, 46`, `plugins/codex-security/references/artifact-storage.md:34` | 저장 도구 호출 형식 예는 `artifact-storage.md:34`. 스키마 파일은 C-01과 일치한다(`plugins/codex-security/schemas/tools/candidate-validations.schema.json`) |
| R-10 | `plugins/codex-security/references/standalone-validation.md:3-11` | SDK `validate` 호출 경로는 열지 않음 |
| R-11 | `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:137-150, 370-384`, C-01, `plugins/codex-security/mcp-app/src/artifact-contracts.ts:41-49, 161-164` | `phaseScanContext`는 requiredMode 없이 호출돼 diff·Deep 모두 허용(`:144-149`). 입력 거부 메시지는 열지 않음 |
| R-12 | C-02(`:32-65`) | |
| R-13 | C-02(`:67-77`), C-03 | `{ ...row, validation }`이라 다른 키가 남는다는 것은 코드의 객체 전개에서 읽음 |
| R-14 | C-02, C-03, `plugins/codex-security/mcp-app/src/artifact-io.ts:296-304` | 빈 파일은 `replaceArtifactJsonl`이 행이 0개면 빈 문자열을 쓰는 코드(`:300-302`) |
| R-15 | C-02 전체 | 부재 주장 1 |
| R-16 | C-08, `plugins/codex-security/scripts/workbench_scan_start.py:421, 427-431, 492-500`, `plugins/codex-security/scripts/reserved_artifact_paths.json:1-5`, [caller-modes.md](./caller-modes.md) R-08 | `native_scan = scan_dir is None`이라 workbench가 디렉터리를 직접 만드는 경로(app-start·prompt-only·headless)에서만 쓴다는 것은 `insert_running_scan`의 이 분기에서 읽었다. 이 함수를 부르는 호출 지점 세 곳(`workbench_db.py`의 `start_scan`·prompt-driven 시작·`register_cli_scan`)은 호출 인자만 봤다. 질의 본문(`:56-125`)은 조건 절만 읽었다 |
| R-17 | `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:156-159` `isAttackPathEligible` | |
| R-18 | C-09 | `customValidationConfig` 호출 지점은 `sdk/typescript/src/api.ts:2618-2628`(`options.validationPrompt` 조건) |
| R-19 | 실행하지 않음 | |
| R-20 | `plugins/codex-security/scripts/workbench_saved_results.py:1442-1598` `budget_exhausted_draft`(특히 `:1520-1545`), `plugins/codex-security/scripts/workbench_db.py:1147-1199` | 매핑 부분만 정독. 호출 조건은 caller-modes R-21 |
| T-01~T-11 | 해당 R-ID의 근거 | 모두 코드 읽기로 기대값 도출. 실행·원본 테스트 열람 없음 |

**부재 주장의 검색 범위**
1. R-15 (코드가 검사하지 않는 것). `recordCodexSecurityCandidateValidations`(`plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:24-77`) 본문 전체를 읽었다. `git grep -n "artifact_paths\|validation_artifacts" -- plugins sdk ':!*test*' ':!*.md'`에서 `artifact_paths`를 읽는 비테스트 코드는 스키마(`artifact-contracts.ts:152`, JSON 내보내기)와 SDK custom validation(`sdk/typescript/src/custom-validation.ts:405` 등, 이 스펙 밖)뿐이고 plugin의 TypeScript·Python에서 `validation_artifacts` 경로를 여는 코드는 없다. `git grep -n "false_positive_feedback" -- plugins sdk ':!*test*' ':!*.md'`는 `workbench_scan_start.py:498`(쓰기), `reserved_artifact_paths.json`, `deep-scan/worker-runner.ts:95`(Deep worker가 파일 존재를 확인해 prompt에 넣음), `sdk/typescript/src/api.ts:3501-3512`(SDK 쓰기·prompt)만 나왔다. 검증 도구가 파일을 읽는 코드는 없다. 놓칠 수 있는 것: 동적으로 조합한 경로, 빌드 산출물(`mcp/*.mjs`), MCP 등록부 계층의 후처리.

### 2.2 코드 읽는 순서 [선택]
`compact-artifact-tools.ts`의 등록(137-150)과 `phaseScanContext`(370-384)로 입구를 본다. 이어 `artifact-candidate-ledger.ts`의 `recordCodexSecurityCandidateValidations`(24-77)와 ledger 읽기·교체(161-199)를 본다. 입력 스키마는 `artifact-contracts.ts`(135-164, 437-448). 지침은 `skills/validation/SKILL.md` → `references/validation-guidance.md` → `references/static-finding-assessment.md` 순이다.

### 2.3 비교·재사용 출처 [선택]
다른 레포에 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 세션 기본 점검(2026-11-16). `python scripts/check.py codex-security`로 인용 줄의 존재를 확인하고(형식·위치 확인일 뿐), 고위험 R-ID 표본을 인용 줄과 검색으로 대조했다.  행 3·7·11이 `depends`로 의존하는 스펙이라 독립 검토가 남아 있고, 미결정도 있어 `draft`로 둔다.
- 대조한 R-ID: R-12(`artifact-candidate-ledger.ts`의 `recordCodexSecurityCandidateValidations`가 입력 항목마다 unknown → duplicate를 검사하고 루프 뒤 missing을 검사하는 순서, 오류 문구 일치)
- 대조하지 않은 R-ID: R-12를 제외한 전부. 특히 R-13·R-14(덮어쓰기·빈 입력), R-15(부재 주장), R-16(오탐 피드백 작성 주체, 호출 지점 3곳은 인자만 확인), R-18, R-20은 독립 검토 대상이다.
- 재구현: 미수행
