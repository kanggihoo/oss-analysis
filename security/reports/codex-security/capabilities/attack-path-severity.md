---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
sources:
  - plugins/codex-security/skills/attack-path-analysis/SKILL.md
  - plugins/codex-security/skills/attack-path-analysis/references/severity-policy.md
  - plugins/codex-security/skills/attack-path-analysis/references/attack-path-facts.md
  - plugins/codex-security/skills/security-diff-scan/SKILL.md
  - plugins/codex-security/references/default-severity-rubric.md
  - plugins/codex-security/references/scan-artifacts.md
  - plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts
  - plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts
  - plugins/codex-security/mcp-app/src/artifact-contracts.ts
  - plugins/codex-security/mcp-app/src/finding-detail-schemas.ts
  - plugins/codex-security/mcp-app/src/record.ts
  - plugins/codex-security/scripts/workbench_saved_results.py
  - plugins/codex-security/schemas/tools/candidate-attack-paths.schema.json
  - sdk/typescript/src/custom-validation-prompt.ts
depends:
  - ./candidate-discovery.md
  - ./candidate-validation.md
status: draft
---

# 공격 경로·severity 판정

> 검증을 통과한 후보(`validation.disposition`이 `reportable`·`deferred`)마다 공격자에서 영향까지의 경로, 통제·전제, 영향·가능성, 최종 severity와 보고 여부(`reportable`/`deferred`/`ignore`)를 정하고, `record_candidate_attack_paths`로 대상 후보 전부의 `attack_path` 객체를 한 번에 후보 ledger에 기록한다.

<!--
공격 경로를 따지고 severity를 매기는 기준은 코드가 아니라 skill·reference 지침이고 모델이 따른다. [지침]은 문장을 읽었다는 뜻의 `코드 확인`이고 모델 준수는 R-20이 미확인으로 묶는다. [강제]는 코드가 검사한다.
같은 지침을 두 번 쓰지 않으려고 지침 원문은 C-ID로 넘기고, R-ID에는 지침이 모델에게 요구하는 동작과 코드가 강제하는 것만 요약했다. 지침 문서 셋(`severity-policy.md`, `attack-path-facts.md`, `default-severity-rubric.md`)은 합쳐서 82줄이라 글로 옮기는 것보다 C-ID가 짧고 정확하다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 workbench가 소유한 diff scan(compact diff)에서 `$attack-path-analysis`를 한 번 부르는 경우다.

1. `security-diff-scan` skill이 후보가 있으면 `$validation`을 마친 뒤 `reportable`·`deferred`인 후보에 `$attack-path-analysis`를 한 번 돌린다(R-01).
2. 모델이 per-scan threat model과 후보 전체를 `list_codex_security_candidates`로 읽는다. 처리 대상은 `validation.disposition`이 `reportable`·`deferred`인 후보다(R-02).
3. 모델이 후보마다 공격자, 진입점, 통제하는 입력, 보안 경계, 민감 연산을 저장소 증거로 따라가고 통제와 가장 강한 반증을 확인한다(R-03, R-04).
4. 모델이 영향과 가능성을 평가하고 정책(R-05~R-07)과 rubric(R-08)으로 severity와 결정(`reportable`/`deferred`/`ignore`)을 정한다. 사실, severity 보정, 최종 정책 결정을 구분해서 적는다(R-04, R-11).
5. 모델이 대상 후보 전부의 결정을 `record_candidate_attack_paths({ scanId, attackPaths: [{ candidateId, attackPath }] })` 한 번에 보낸다. 대상이 없으면 `attackPaths: []`를 보낸다(R-02).
6. 서버가 대상(적격) 후보를 정확히 한 번씩 담았는지 확인하고 `attack_path` 스키마를 검사한 뒤, 대상 행에 `attack_path`를 대입하고 행 순서를 보존해 ledger를 전체 교체한다(R-12~R-16).
7. 이후 모델이 이 결정을 근거로 `record_codex_security_scan_draft`에 finding을 쓴다. 이 연결은 코드가 아니라 모델이 한다(R-18).

### 1.2 범위·통합 지점 [필수]
- 제공: (a) 공격 경로·severity 판정 지침(사실 정리, 보고 여부 규칙, 가능성 가중, 등급 기준, priority 매핑), (b) 대상 후보 전부에 `attack_path`를 쓰는 MCP 도구와 ledger 쓰기 규칙.
- 이 skill이 쓰이는 곳: Standard scan과 Deep worker는 이 phase skill을 부르지 않고 자기 흐름 안에서 공격 경로를 평가한다(SKILL.md의 "Scan integration"). 쓰이는 곳은 세 가지다. 1) compact diff(이 스펙 본문 경로). 2) 구형 phase 스캔(파일 기반 `attack_path_analysis_report.md`·receipt). 3) 단독 분석. 호출자 모드는 [caller-modes.md](./caller-modes.md)다.
- 제외(이유):
  - 후보 발견과 ledger 공통 규칙: [candidate-discovery.md](./candidate-discovery.md)(S1). 검증과 `validation` 쓰기: [candidate-validation.md](./candidate-validation.md).
  - 구형 phase 스캔의 파일 기반 결과(`attack_path_analysis_report.md`, 후보별 receipt, closure row 처리): 이번 범위 밖(이유: compact 도구 경로와 별개의 파일 흐름, `SKILL.md:38-42` 존재만 확인).
  - severity 재분류 CLI(`classify-severity`)와 SDK 쪽 finding 분류: 이번 범위 밖(이유: 사용자 제외, SDK 부속).
  - 저장된 finding의 최종 보고 형식(`record_codex_security_scan_draft`의 `severity`·`attackPath` 필드, `report.md`, SARIF)과 후보 ledger를 finding으로 옮기는 규칙: 스캔 초안·확정(행 9)과 diff 감사(행 3) 몫이다. 이 스펙은 두 스키마가 다르다는 사실만 R-18에 쓴다.
  - 외부 import 이슈 처리의 나머지(`codex-security import` 등): 행 14, 이번 범위 밖. R-10은 skill 문장만 적었다.
- 외부 의존·선행 계약: [candidate-discovery.md](./candidate-discovery.md)의 ledger 계약(S1)과 도구 접근 규칙(R-07), [candidate-validation.md](./candidate-validation.md)가 쓴 `validation.disposition`. per-scan threat model(`scan.threatModel`의 읽기는 행 8, 행 9). "scan이 준 severity rubric"을 모델이 받는 경로는 이 SHA에서 compact diff 쪽 도구에서 찾지 못했다(U-03).
- 소유 상태·부작용: 후보 ledger 각 적격 행의 `attack_path` 필드(이 도구만 쓴다). ledger 파일 전체가 교체된다. 다른 부작용은 없다.

### 1.3 인터페이스와 데이터 의미 [필수]

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `record_candidate_attack_paths` | 입력 `{ scanId: uuid, attackPaths: [{ candidateId, attackPath }] }`, 결과 `{ kind: "candidate_attack_paths", operation: "replace", rowsWritten }` | model 전용 도구. `diff` 또는 Deep scan에서 `running`일 때만 쓸 수 있다([candidate-discovery.md](./candidate-discovery.md) R-07). 입력은 strict 객체. `rowsWritten`은 **기록한 attack path 수**(입력 항목 수)이고 ledger 전체 행 수가 아니다(검증 도구와 다르다) |
| `attackPath` 공통 필드 | `dataflow`, `reachability`, `counterevidence`, `severity_rationale`, `change_conditions`(공백 아닌 글자가 있는 문자열), `impact`, `likelihood`(`high`\|`medium`\|`low`\|`ignore`\|`unknown`) | 알 수 없는 추가 키는 보존된다(C-01) |
| `attackPath` 변형 셋 | `decision: "reportable"` → `severity`는 `critical`\|`high`\|`medium`\|`low`. `decision: "ignore"` → `severity`는 `ignore`. `decision: "deferred"` → `severity`는 `critical`\|`high`\|`medium`\|`low`\|`unknown`이고 `proof_gap`(문자열)이 필수 | 정확히 한 변형에 맞아야 한다. 정확한 정의는 C-01 |
| ledger 행의 `attack_path` | `attackPath` 객체 하나(필드 병합 없이 통째로 대입) | 적격 행에만 쓴다. 적격 = `validation.disposition`이 `reportable` 또는 `deferred`(R-12) |
| priority | `critical`→`P0`, `high`→`P1`, `medium`→`P2`, `low`→`P3`. `ignore`는 priority 없음 | ledger의 `attack_path`에 priority 필드는 없다. 지침이 최종 finding에서 쓰는 매핑이다(R-09, R-18) |

### 1.4 행동 규칙과 남은 질문 [필수]

#### 모델 지침 (attack-path-analysis skill)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [지침] 사용 경계 | "이미 attack-path 단계에 있거나 사용자가 finding의 source-to-sink 추적과 severity 보정을 명시적으로 요청한 경우"에 쓰고, 전체 스캔의 주된 trigger로 쓰지 않는다. Standard scan과 Deep worker는 이 skill을 부르지 않는다. compact workbench diff는 위 도구로 기록하고, `security-diff-scan`은 후보가 있으면 `$validation` 뒤에 `reportable`·`deferred` 후보에 `$attack-path-analysis`를 한 번 돌린다 | 코드 확인 (지침 문장) |
| R-02 | [지침] 입력과 준비 | scan phase는 per-scan threat model과 후보 집합을 쓰고 공급된 입력 경로를 유지하며, 필요한 scan artifact가 없으면 누락된 입력을 보고한다. compact diff는 `list_codex_security_candidates`로 threat model과 모든 검증된 후보를 읽고, `reportable`·`deferred` 검증 후보 전부를 분석하고, 후보 정체성과 기존 discovery·validation 필드를 보존한다. 대상이 없으면 `attackPaths: []`를 보낸다. 단독 분석은 공급된 finding·저장소·threat model 또는 정책·맥락을 쓰고 per-scan artifact가 필요 없으며, 중요한 가정을 밝히고 의미 있는 평가를 막을 때만 맥락을 묻는다 | 코드 확인 (지침 문장) |
| R-03 | [지침] 경로 구성 절차 | (1) 범위 안 공격자, 영향받는 제품 표면, 진입점, 통제하는 입력, 보안 경계, 민감 연산을 정하고 각 단계를 저장소 증거와 공급된 관찰로 따라간다. (2) 관련 통제와 가장 강한 반증을 찾아 그것이 무엇을 성립시키는지, 어떤 전제가 남는지, 주장한 경계를 정확히 넘는지 설명한다. (3) 그 사실에서 영향과 가능성을 평가하고 severity 정책(R-05~R-09)으로 최종 결정한다. 사실, severity 보정, 최종 정책 결정을 구분해서 남긴다. (4) 대상 후보마다 `ignore`·`deferred` 포함 명시적 결정을 낸다. 지지되는 인스턴스를 이웃 finding으로 바꾸거나 root-control 위치를 잃지 않는다. 공급된 artifact는 증거이고, 네트워크는 사용자가 명시적으로 허가했을 때만 쓰며(offline scan은 쓰지 않음), 지원되지 않는 공격 체인을 만들지 않는다. 배포·공개 ingress 증거가 없는 것은 신뢰도를 낮출 수 있으나 지지되는 finding을 무효화하지 않는다 | 코드 확인 (지침 문장) |
| R-04 | [지침] 사실 필드 | 경로와 보고 여부 결정을 설명하는 항목: 범위·맥락(영향받는 구성 요소, threat model 경계, self-only인지 의미 있는 경계를 넘는지), 공격 경로(공격자 제어 입력, 번호 붙인 공격 단계, 민감 연산), 노출과 벡터(`public`/`internal`/`admin-only`, `remote`·`local_network`·`localhost`·`none`·`unknown`), 신원과 전제(유효 권한, 필요한 위치·능력, 전제의 현실성), 영향(취약점 범주, 영향받는 표면, 도달 범위, 관련 비밀 유형), 통제와 반증, 불확실성(신뢰도, 빠진 사실, 평가를 바꿀 조건), 결정(영향·가능성 이유, 보정된 severity, 최종 정책 결정). 알 수 없는 것은 중요하면 명시한다. 사실은 severity·억제 결정과 구분해 남기고 검증이 준 정확한 위치와 식별자를 보존한다. 출력 항목은 R-11 | 코드 확인 (지침 문장) |
| R-05 | [지침] 보고 여부 규칙 | `ignore`는 반증된 finding이나 의미 있는 보안 영향이 없는 버그에 쓴다. 실제이고 보고할 finding을 영향이나 가능성이 낮다는 이유만으로 버리지 않고 낮은 severity를 준다. self-only 영향이나 달성 불가·매우 비현실적인 전제는 강하게 억제한다. 권한 있는 주체만(privileged, operator, developer, physical-access, 보호된 쓰기 경로) 필요한 경로는 권한 상승 delta가 쟁점이 아니면 `ignore`다. 저장소·검증 증거로 현실적인 낮은 권한 범위 안 공격자 경로를 성립시킬 수 없으면 `ignore`다. 내부·비공개 노출만으로는 실제 제품·운영 흐름의 인가·신원·신뢰 경계·보안 통제 실패를 억제하지 않는다. 배포·ingress 증거가 없는 것은 신뢰도를 낮추거나 사실을 `unknown`으로 둘 뿐 지지되는 finding을 무효화하지 않는다 | 코드 확인 (지침 문장) |
| R-06 | [지침] 가능성 가중 | 성립한 공격자 위치와 노출로 가중한다. `remote`는 현실적이고 범위 안이면 보통 높은 가능성, `local_network`는 다른 증거가 없으면 보통 중간, `localhost`는 낮은 권한 공격자가 listener에 현실적으로 닿는 경우가 아니면 보통 낮음, `none`은 노출로 가능성을 높이지 않는다 | 코드 확인 (지침 문장) |
| R-07 | [지침] 취약점 유형별 보정 | SSRF: 문서화된 outbound 요청 기능이나 선택적 운영자 필터는 증명된 목적지 통제 우회를 무효화하지 않는다. CSRF: 브라우저 credential 부착, cookie 정책, preflight, 요청 파싱, 실제 통제를 평가하고 method나 JSON content type만으로 범주적 방어로 보지 않는다. XSS: self-only 영향과 피해자 영향을 구분하고 `alert` 재현은 스크립트 실행만 증명하지 severity를 단독으로 정하지 않는다 | 코드 확인 (지침 문장) |
| R-08 | [지침] severity 기준과 rubric | 공격 경로·범위·반증을 정립한 뒤 정책을 적용한다. 후보의 severity 가설(hypothesis)에서 시작해 저장소와 검증 증거가 지지하는 영향·가능성·전제·완화로 조정하고 보정 중에 discovery를 다시 열지 않는다. 보고할 finding은 scan이 공급한 rubric으로, 없으면 기본 rubric(C-07)으로 등급을 매긴다. 공급된 rubric이 있어도 보안 영향이 없는 후보는 `ignore`로 둔다. 기본 rubric: `Critical`은 접근(인터넷의 미인증 공격자 또는 일반 외부 사용자 등)·영향(중요한 경계를 넘어 결과가 큰 접근, 권한 있는 동작, 의미 있는 코드 실행, workload 탈출 등)·증거(실증 또는 강한 소스 기반 검증으로 경로 전체 성립) 셋을 모두 만족할 때만, `High`는 낮은 신뢰 주체의 접근·상당한 새 capability·현실적 경로를, `Medium`은 구체적으로 한정된 영향의 신뢰할 만한 취약점을, `Low`는 추가 피해가 작고 범위·민감도·기간이 검증된 한계로 제한된 지원되는 약점을, `Informational`은 추가 무권한 capability가 성립하지 않는 hardening 관찰을 뜻한다. 증명 부재만으로 더 넓은 공격이 불가능하다고 보지 않고, 시연되지 않았다는 이유만으로 downgrade하지 않으며, 신뢰도는 severity와 분리해 쓰고, 결론을 바꿀 빠진 사실을 밝힌다 | 코드 확인 (지침 문장). `Informational`의 ledger 표현은 U-01, 가설의 출처는 U-02, rubric 공급은 U-03 |
| R-09 | [지침] priority 매핑 | 최종 보고 severity를 priority로 바꾼다: `critical`→`P0`, `high`→`P1`, `medium`→`P2`, `low`→`P3`. `ignore`된 finding은 `ignore` 결정과 severity를 갖고 priority는 없다. 데스크톱 결과의 `::code-comment` 줄의 `[P<n>]`과 `priority=<0~3>`이 이 매핑을 쓴다([caller-modes.md](./caller-modes.md) R-44) | 코드 확인 (지침 문장) |
| R-10 | [지침] 외부 import 이슈의 증거 | AWS Continuum에서 가져온 이슈이면 finding 증거의 `source_data.evidence_artifacts`를 읽는다. `VALIDATION_EVIDENCE` artifact의 `body.validationEvidence`는 저장소가 보일 수 없는 단계를 성립시킬 수 있고, 테스트된 대상·공격자 권한·관찰된 효과를 주장한 경로와 맞춘다. 묶음 이슈는 `perFindingResults`·`flowVerdicts`로 해당 finding·flow를 찾는다. HTTP `exploitArtifact`는 시험한 위치에서의 도달 가능성을, `executedProof`는 그 시험 환경에서 실행된 것을 성립시키고, `sourceAnalysis`는 정적 추론이며, `exploitable` 판정만으로 배포 환경의 도달 가능성을 입증하지 않는다. artifact ID와 단계를 지지·반박하는 관찰을 인용한다 | 코드 확인 (지침 문장) |
| R-11 | [지침] 출력 | 단독 분석은 호출자 형식이 있으면 따르고 없으면 finding별 간결한 평가를 낸다. scan phase는 compact 도구(R-12~R-16)가 출력 계약이다. 담을 내용: 제목과 후보·instance·ledger 식별자, 정확한 위치와 공격자에서 영향까지의 단계, 사실(R-04), 통제·반증·전제·중대한 증명 공백, 영향·가능성·보정된 severity·최종 정책 결정과 이유. 살아남은 finding과 억제된 finding을 모두 설명할 증거를 남기고, discovery를 다시 열거나 다른 공격 이야기로 바꾸지 않는다 | 코드 확인 (지침 문장) |

#### 공격 경로 기록 도구 [강제]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-12 | [강제] 적격 판정과 입력 대 ledger 검사 | 후보가 적격이려면 행의 `validation`이 객체이고 `validation.disposition`이 `reportable` 또는 `deferred`여야 한다(`validation`이 없거나 `suppressed`·`not_applicable`이면 부적격). 검사 순서: (1) scan context의 layout이 `scan`이 아니면 "Candidate attack-path analysis requires a scan-bound artifact context."(S1 R-22). (2) 입력 항목을 입력 순서로 보며 같은 `candidateId`가 이미 있으면 "Candidate attack-path update repeats candidate X."(ledger를 읽기 전에 던진다). (3) ledger를 읽는다(없으면 "Compact candidate ledger: the requested artifact is unavailable.", 줄·스키마 오류는 S1 R-19·R-20, ledger 안 중복은 "Candidate ledger repeats candidate X."). (4) 입력의 각 ID를 입력 순서로 확인한다. ledger에 없으면 "Candidate attack-path update refers to unknown candidate X.", 부적격이면 "Candidate X must have a reportable or deferred validation before attack-path analysis."를 던진다(첫 위반에서 멈춤). (5) 입력에 없는 적격 후보가 있으면 ledger 순서로 나열한 "Attack-path analysis must include every reportable or deferred candidate; missing a, b."를 던진다. 어느 오류도 ledger를 바꾸지 않는다. 즉 입력 ID 집합은 적격 후보 집합과 정확히 같아야 하고 순서는 상관없다 | 코드 확인 |
| R-13 | [강제] 도구 등록과 scan context | `diff` 또는 Deep scan이어야 하고 `running`이어야 하며 claim·owner 규칙은 [candidate-discovery.md](./candidate-discovery.md) R-07과 같다(`phaseScanContext`, requiredMode 없음). 입력 스키마에는 `handoffClaimToken`이 없어 서버가 캐시한 token만 쓴다. mode `standard`는 "This operation is only available for Deep or diff scans."로 거부된다 | 코드 확인 |
| R-14 | [강제] `attackPath` 스키마 | 도구 등록부가 코드 실행 전에 입력을 검사한다: 입력 strict(`scanId` UUID, `attackPaths` 배열이고 빈 배열 가능), 항목 strict(`candidateId`, `attackPath`), `attackPath`는 1.3의 세 변형 중 정확히 하나. `decision: "reportable"`에 `severity: "ignore"`·`"unknown"`, `decision: "ignore"`에 `ignore` 아닌 severity, `decision: "deferred"`에 `proof_gap` 누락은 거부된다. 텍스트 필드는 공백 아닌 글자가 있어야 한다. `impact`·`likelihood`는 5개 enum 값 중 하나이고 결정·severity와의 일관성은 검사하지 않는다(R-17) | 코드 확인 (거부 메시지 형식은 열지 않음) |
| R-15 | [강제] 쓰기 | 검사를 통과하면 ledger의 모든 행을 읽은 순서대로, 입력에 있는 후보는 `{ ...행, attack_path: 입력의 그 attackPath }`로, 없는 후보는 원래 행 그대로 만들어 전체 교체한다([candidate-discovery.md](./candidate-discovery.md) R-21). 대상 행의 기존 `attack_path`는 통째로 덮어쓴다(필드 병합 없음). 다른 필드(1·2단계)는 그대로다. 결과는 `{ kind: "candidate_attack_paths", operation: "replace", rowsWritten: 입력 항목 수 }`다 | 코드 확인 |
| R-16 | [강제] 빈 입력과 재호출 | ledger가 존재하고 적격 후보가 0개이면 `attackPaths: []`는 통과해 파일을 같은 내용으로 다시 쓰고 `rowsWritten: 0`이다. 적격 후보가 있으면 `attackPaths: []`는 R-12 (5)의 누락 오류다. 같은 후보에 이미 `attack_path`가 있어도 오류 없이 덮어쓴다. 앞 단계를 다시 해서 후보가 부적격이 돼도 이전 `attack_path`는 지워지지 않는다(그 후보를 입력에 넣으면 (4)의 부적격 오류이고, 입력에 넣지 않으면 그대로 남는다) | 코드 확인 |
| R-17 | [강제 없음] 코드가 검사하지 않는 것 | 도구는 (a) `decision`과 `validation.disposition`의 일치(`deferred` 검증 후보에 `reportable` 결정, `reportable` 검증 후보에 `ignore` 결정을 모두 받는다), (b) `impact`·`likelihood`·`severity`의 관계(rubric 규칙, 가능성 가중, `ignore` 규칙), (c) `severity`와 후보·validation 필드의 일치(ledger에 severity 가설 필드가 없다), (d) `dataflow`·`reachability`의 내용이 후보 위치와 맞는지, (e) priority 매핑, (f) rubric 사용을 검사하지 않는다. 형식(필수 필드, enum, 변형별 severity 제한, `proof_gap`)과 후보 집합만 강제한다 | 코드 확인 (부재 주장은 2.1 1번) |
| R-18 | [강제 없음] ledger와 최종 finding의 연결 | 이 SHA에서 ledger 행의 `attack_path`를 읽는 코드는 Deep 비용 한도 소진 마무리(R-21)뿐이다(attack-path 도구의 적격 판정은 `validation`을 읽는다). 최종 `record_codex_security_scan_draft`의 finding은 별도 스키마(camelCase `attackPath`, `severity.level`에 `informational` 포함, `validation`도 별개 구조)를 쓰고 코드는 ledger와 대조하지 않는다. 어떤 후보가 finding이 되고 `severity`가 어떻게 옮겨지는지, `ignore`·`deferred` 결정이 `reviewState`에 어떻게 반영되는지는 모델 몫이다([candidate-discovery.md](./candidate-discovery.md) R-23) | 코드 확인 (ledger 소비자 없음) / 모델의 이행은 미확인 |
| R-19 | [강제 없음] Standard·Deep에서의 사용 | `record_candidate_attack_paths`의 설명과 주석은 "diff or Deep"이라 Deep scan context도 받는다. 그러나 plugin의 비테스트 코드와 prompt 템플릿에서 이 도구를 부르는 곳은 찾지 못했다. SDK의 custom validation이 이 도구를 `disabled_tools`에 넣는다([candidate-validation.md](./candidate-validation.md) R-18) | 코드 확인 (호출처 부재는 2.1 2번) |
| R-20 | 모델이 [지침] R-01~R-11을 따르는가(대상 후보마다 결정을 내는가, rubric과 정책을 적용하는가, 사실과 결정을 구분하는가, `attackPaths`를 한 번에 보내는가) | 실행하지 않았다. 서버는 R-12~R-16이 정한 검사만 한다 | 미확인 |
| R-21 | [강제] Deep 비용 한도 소진 마무리가 `attack_path.decision`을 읽는 규칙 | SDK 소유 Deep scan이 비용 한도를 넘겨 `complete-budget-exhausted-scan`으로 닫힐 때, Python이 ledger의 후보 중 초안에 아직 없는 것마다 coverage surface를 만든다. `attack_path.decision`(객체일 때만)이 `deferred`이면 `needs_follow_up`, `ignore`이면 `rejected`로 영향을 준다. 우선순위는 `validation.disposition == "deferred"` 또는 `decision == "deferred"` → `needs_follow_up`, 그다음 `validation.disposition == "not_applicable"` → `not_applicable`, 그다음 `suppressed` 또는 `decision == "ignore"` → `rejected`, 그 밖(`reportable` 검증, `reportable` 결정, 필드 없음)은 `needs_follow_up`이다. 전체 규칙과 ledger 검사는 [candidate-discovery.md](./candidate-discovery.md) R-23 | 코드 확인 |

- 불변식:
  - 도구가 성공하면 ledger의 모든 적격 후보에 `attack_path`가 정확히 하나 있고(이번 호출이 쓴 것), 행 순서와 다른 단계의 필드는 바뀌지 않는다(R-15).
  - 도구는 부분 입력을 받지 않는다. 일부 적격 후보만 담은 호출은 없고, 실패한 호출은 ledger를 바꾸지 않는다(R-12).
  - 이 도구가 성공한 직후에는 모든 적격 후보의 `attack_path`가 이번 호출 것이지만, 앞 단계를 다시 하면 이 성질은 깨질 수 있다(R-16).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-08, R-14, R-18 | 기본 rubric의 `Informational`(hardening 관찰) 후보를 ledger에서는 어떻게 표현하는가. `attack_path.severity`에는 `informational`이 없고(`ignore`와 `unknown`이 있다), 최종 finding의 `severity.level`에는 `informational`이 있다. 지침은 "의미 있는 보안 영향이 없으면 `ignore`"라고도 한다 | 구현자는 `Informational` 후보를 `ignore`로 보낼지, `deferred`로 보낼지, 낮은 `reportable`로 올릴지 정해야 한다 | 실제 scan 산출물이나 세션 기록. 두 문서(`severity-policy.md`와 `default-severity-rubric.md`)에 연결 문장이 없다 |
| U-02 | R-08 | 정책이 "후보의 severity 가설에서 시작하라"고 하는데, compact diff의 ledger 행에는 severity 필드가 없고(후보 필드·`validation`에 모두 없다) 가설이 어디서 오는지 문서에 없다 | 구현자는 가설을 `summary`·`context` 텍스트에서 읽는지, 모델이 직접 정하는지 정해야 한다 | 실제 scan 산출물이나 세션 기록. 스키마와 skill 문장에서 연결을 찾지 못했다 |
| U-03 | R-08 | "scan이 공급한 severity rubric"이 compact diff(workbench 소유)에서 모델에게 어떻게 전달되는가. SDK 경로는 `scanPrompt`가 rubric 문단을 넣고(caller-modes R-13), Deep은 `severityRubric.markdown`을 worker 템플릿에 넣는다. diff 도구 응답(`get_codex_security_scan_context` 등)에서 rubric을 주는 코드는 찾지 못했다 | rubric을 쓰는 diff scan을 구현하려면 전달 경로를 정해야 한다 | 호출자(데스크톱 앱, SDK)가 diff scan에 주는 입력. 앱 코드는 레포에 없다(U-01 of caller-modes) |
| U-04 | R-05, R-08 | `impact`·`likelihood` 값 `ignore`와 `unknown`은 언제 쓰는가, 그리고 영향·가능성이 최종 severity를 어떻게 정하는가. 지침은 가능성 가중(R-06)과 등급 기준(R-08)만 주고 두 값을 합치는 규칙이 없다 | 구현자는 두 enum의 의미와 severity 결정식을 정해야 한다(모델 판단 몫이라면 prompt에 기준을 넣어야 한다) | 실제 scan 산출물. 코드는 이 값을 읽지 않는다(R-17) |

- 확인 한계:
  - 실행하지 않았다(MCP, workbench). 오류 문구는 소스에서 옮겼다. 입력 스키마 위반 시 MCP 등록부가 내는 메시지는 확인하지 못했다.
  - 판단 기준은 모델이 따르는 문장이라 실행 없이는 어느 쪽 severity가 나오는지 알 수 없다(R-20).
  - SDK의 severity 재분류(`classify-severity`)와 `sdk/typescript/docs/*`의 rubric 문서는 이번 범위 밖이라 열지 않았다. 기본 rubric 파일을 SDK가 다른 목적(저장된 finding 분류)에도 쓴다는 것은 문서 검색 결과에서만 보았다.

### 1.5 필수 코드 참조 [필수]

기준은 frontmatter SHA다. 라이선스는 Apache-2.0(overview 1절)이라 인용을 막지 않는다. 지침 원문은 합쳐서 90여 줄이라 글로 다시 쓰는 대신 아래 줄 범위를 가져가면 된다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `plugins/codex-security/mcp-app/src/artifact-contracts.ts:95-133` `attackPath_*`, `:421-436` | `attack_path` zod 정의(필드, enum, 변형별 severity, `proof_gap`, loose, xor)와 도구 입력 | R-12~R-15 |
| C-02 | `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:79-159` `recordCodexSecurityCandidateAttackPaths`·`isAttackPathEligible` | 검사 순서, 오류 문구, 적격 판정, 쓰기 | R-12, R-15, R-16 |
| C-03 | `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:161-199` `readCandidateLedger`·`replaceCandidateLedger` | ledger 읽기·교체(S1, [candidate-discovery.md](./candidate-discovery.md) C-15) | R-12, R-15 |
| C-04 | `plugins/codex-security/skills/attack-path-analysis/SKILL.md:6-54` | 모델에게 주는 공격 경로 지침 원문 | R-01~R-03, R-10, R-11 |
| C-05 | `plugins/codex-security/skills/attack-path-analysis/references/severity-policy.md:1-35` | 보고 여부 규칙, 가능성 가중, priority 매핑 원문 | R-05~R-09 |
| C-06 | `plugins/codex-security/skills/attack-path-analysis/references/attack-path-facts.md:1-14` | 사실 필드 원문 | R-04 |
| C-07 | `plugins/codex-security/references/default-severity-rubric.md:1-33` | 기본 severity rubric 원문(Critical~Informational) | R-08 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 사례는 실행하지 않았다. 아래 `P_R`·`P_I`·`P_D`는 각각 `decision`이 `reportable`·`ignore`·`deferred`인 유효한 `attackPath` 객체다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-12~R-15 | running diff scan, ledger 행 A(`validation.disposition: "reportable"`), B(`"suppressed"`), C(`"deferred"`). `attackPaths: [{C, P_D}, {A, P_R}]` | 성공. A와 C에 `attack_path`가 붙고 B는 그대로다. 행 순서는 A, B, C이고 결과는 `{ kind: "candidate_attack_paths", operation: "replace", rowsWritten: 2 }` |
| T-02 | R-12 | 같은 ledger에 `attackPaths: [{A, P_R}, {B, P_I}, {C, P_D}]` | "Candidate B must have a reportable or deferred validation before attack-path analysis."로 거부, ledger 불변 |
| T-03 | R-12 | `attackPaths: [{A, P_R}]` | "Attack-path analysis must include every reportable or deferred candidate; missing C."로 거부 |
| T-04 | R-12 | `attackPaths: [{A, P_R}, {X, P_R}, {C, P_D}]`(X는 ledger에 없음). 별도로 `[{A, P_R}, {A, P_R}]` | 앞은 "…refers to unknown candidate X."로 거부(A는 통과하고 X에서 멈춤). 뒤는 ledger를 읽기도 전에 "Candidate attack-path update repeats candidate A." |
| T-05 | R-16 | 적격 후보가 0개인 ledger에 `attackPaths: []`. 적격 후보가 있는 ledger에 같은 입력 | 앞은 성공, `rowsWritten: 0`(파일은 같은 내용으로 다시 써진다). 뒤는 R-12 (5)의 누락 오류 |
| T-06 | R-14 | `{ decision: "reportable", severity: "unknown", … }`, `{ decision: "ignore", severity: "low", … }`, `{ decision: "deferred", … }`(`proof_gap` 없음) | 셋 모두 도구 입력 검증에서 거부. `{ decision: "deferred", severity: "unknown", proof_gap: "…", … }`는 통과 |
| T-07 | R-17 | `validation.disposition`이 `deferred`인 후보에 `P_R`, `reportable`인 후보에 `P_I` | 둘 다 받아들여져 저장된다(일치를 검사하지 않는다) |
| T-08 | R-16 | A에 `attack_path`가 있고 이후 검증을 다시 해 A를 `suppressed`로 바꿨다. `attackPaths: []`(적격 후보가 없다고 하자) 호출. 이어서 `attackPaths: [{A, P_R}]` | 앞 호출은 성공하고 A의 이전 `attack_path`가 그대로 남는다. 뒤 호출은 "Candidate A must have a reportable or deferred validation…"으로 거부 |
| T-09 | R-13 | mode `standard` scan, 또는 `running`이 아닌 scan | 앞은 "This operation is only available for Deep or diff scans.", 뒤는 "Codex Security scan <scanId> is not running; its artifacts cannot be modified." |
| T-10 | R-12 | 후보 ledger 파일이 없다 | "Compact candidate ledger: the requested artifact is unavailable." |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

경로는 모두 `173483d7c658be7a512c93d9559bf01a05d5b196` 기준이다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `plugins/codex-security/skills/attack-path-analysis/SKILL.md:3, 27, 29-36`, `plugins/codex-security/skills/security-diff-scan/SKILL.md:31` | 지침 문장 |
| R-02 | `plugins/codex-security/skills/attack-path-analysis/SKILL.md:12-14, 33-36`, `plugins/codex-security/references/scan-artifacts.md:44-45` | |
| R-03 | `plugins/codex-security/skills/attack-path-analysis/SKILL.md:16-19, 23` | |
| R-04 | `plugins/codex-security/skills/attack-path-analysis/references/attack-path-facts.md:3-14`, `plugins/codex-security/skills/attack-path-analysis/SKILL.md:44-54` | |
| R-05 | `plugins/codex-security/skills/attack-path-analysis/references/severity-policy.md:3-17` | |
| R-06 | `plugins/codex-security/skills/attack-path-analysis/references/severity-policy.md:19-24` | |
| R-07 | `plugins/codex-security/skills/attack-path-analysis/references/severity-policy.md:7` | |
| R-08 | `plugins/codex-security/skills/attack-path-analysis/references/severity-policy.md:3-5`, `plugins/codex-security/skills/attack-path-analysis/SKILL.md:18`, `plugins/codex-security/references/default-severity-rubric.md:1-33` | rubric 요약은 문서의 핵심 문장에서 가져왔고 정확한 기준은 C-07을 본다 |
| R-09 | `plugins/codex-security/skills/attack-path-analysis/references/severity-policy.md:26-35` | 데스크톱 `::code-comment` 줄은 caller-modes R-44의 근거(`plugins/codex-security/skills/security-scan/references/desktop-scan.md`) |
| R-10 | `plugins/codex-security/skills/attack-path-analysis/SKILL.md:21-23` | 이 문장이 가리키는 import 데이터의 코드는 열지 않았다(행 14) |
| R-11 | `plugins/codex-security/skills/attack-path-analysis/SKILL.md:44-54` | |
| R-12 | C-02(`:91-141, 156-159`) | `asRecord`는 객체가 아니거나 배열이면 `undefined`(`plugins/codex-security/mcp-app/src/record.ts:5-11`)라 `validation`이 배열·null이면 부적격이다 |
| R-13 | `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:152-165, 370-384` | `recordCodexSecurityCandidateAttackPaths(await phaseScanContext(input, options, requestContext), input)`에 requiredMode 인자가 없다(`:160-163`) |
| R-14 | C-01, `plugins/codex-security/schemas/tools/candidate-attack-paths.schema.json:1-189` | `z.xor`는 정확히 하나만 맞아야 한다는 것을 zod 4 동작 지식으로 읽었다. JSON 내보내기에서는 `oneOf`(`:37`)로 같다 |
| R-15 | C-02(`:143-154`), C-03 | `rowsWritten: updates.size`가 입력 항목 수라는 것은 `:152` |
| R-16 | C-02(`:119-141, 143-154`) | |
| R-17 | C-02 전체 | 부재 주장 1 |
| R-18 | `plugins/codex-security/mcp-app/src/finding-detail-schemas.ts:61-77, 83-90`, `plugins/codex-security/mcp-app/src/artifact-contracts.ts:216-285`(`draft_finding`), [candidate-discovery.md](./candidate-discovery.md) R-23과 2.1 4번 | 두 스키마의 필드 차이만 읽었다. 초안 코드의 검증(행 9)은 열지 않았다 |
| R-19 | `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:152-165`, `sdk/typescript/src/custom-validation-prompt.ts:27-34` | 부재 주장 2 |
| R-20 | 실행하지 않음 | |
| R-21 | `plugins/codex-security/scripts/workbench_saved_results.py:1442-1598` `budget_exhausted_draft`(특히 `:1520-1545`), `plugins/codex-security/scripts/workbench_db.py:1147-1199` | 매핑 부분만 정독. 호출 조건은 caller-modes R-21 |
| T-01~T-10 | 해당 R-ID의 근거 | 모두 코드 읽기로 기대값 도출. 실행·원본 테스트 열람 없음 |

**부재 주장의 검색 범위**
1. R-17 (코드가 검사하지 않는 것). `recordCodexSecurityCandidateAttackPaths`(`plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:91-154`)와 `isAttackPathEligible`(`:156-159`) 전체를 읽었다. `git grep -n "attack_path" -- plugins sdk ':!*test*' ':!*.md'` 결과에서 ledger 행의 키로 쓰는 비테스트 코드는 `artifact-candidate-ledger.ts`(쓰기)와 `workbench_saved_results.py:1526`(R-21, 읽기)뿐이다. 나머지는 phase 이름 문자열 `"attack_path"`(`server.ts:346`, `workbench_constants.py:7`, `sdk/typescript/src/worker-progress.ts`), SQL 마이그레이션 문자열, finding의 camelCase `attackPath`(초안·보고서 코드)다. 놓칠 수 있는 것: 키를 문자열 조합으로 읽는 코드, 빌드 산출물.
2. R-19 (Deep·Standard에서 이 도구를 부르는 곳이 없다). `git grep -n "record_candidate_attack_paths\|record_codex_security_candidate_validations" -- plugins/codex-security/mcp-app plugins/codex-security/scripts plugins/codex-security/skills plugins/codex-security/references sdk/typescript/src ':!*test*'` 결과는 등록(`compact-artifact-tools.ts:139, 154`), skill 문장(`skills/validation/SKILL.md:28`, `skills/attack-path-analysis/SKILL.md:35`), `references/scan-artifacts.md:45`, SDK의 비활성 목록(`custom-validation-prompt.ts:32-33`)이다. Deep worker prompt 템플릿(`plugins/codex-security/mcp-app/templates/deep-scan/`)에서 이 도구 이름은 찾지 못했다(위 검색 범위에 이 디렉터리가 들어 있다). 놓칠 수 있는 것: 이름을 조합해 prompt를 만드는 코드, 빌드 산출물.

차이: 문서와 구현이 다른 곳은 두 가지다. (a) 정책 문서가 요구하는 "후보의 severity 가설에서 시작"은 compact ledger에 대응 필드가 없다(U-02). (b) 기본 rubric의 `Informational`은 ledger `attack_path.severity` 열거에 없다(U-01). `scan-artifacts.md:44`의 attack-path 필드 설명(`decision`, `severity` 조합, `proof_gap`)은 R-14와 일치한다.

### 2.2 코드 읽는 순서 [선택]
`compact-artifact-tools.ts`의 등록(152-165)과 `phaseScanContext`(370-384)로 입구를 본다. 이어 `artifact-candidate-ledger.ts`의 `recordCodexSecurityCandidateAttackPaths`(91-154)와 `isAttackPathEligible`(156-159), ledger 읽기·교체(161-199)를 본다. 입력 스키마는 `artifact-contracts.ts`(95-133, 421-436). 지침은 `skills/attack-path-analysis/SKILL.md` → `references/attack-path-facts.md` → `references/severity-policy.md` → `references/default-severity-rubric.md` 순이다.

### 2.3 비교·재사용 출처 [선택]
다른 레포에 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 세션 기본 점검(2026-11-16). `python scripts/check.py codex-security`로 인용 줄의 존재를 확인하고(형식·위치 확인일 뿐), 고위험 R-ID 표본을 인용 줄과 검색으로 대조했다.  행 3·7·11이 `depends`로 의존하는 스펙이라 독립 검토가 남아 있고, 미결정도 있어 `draft`로 둔다.
- 대조한 R-ID: R-15(`recordCodexSecurityCandidateAttackPaths`가 `rowsWritten: updates.size`, 즉 입력 항목 수를 반환하고 검증 도구의 행 수와 다르다는 서술과 일치)
- 대조하지 않은 R-ID: R-15를 제외한 전부. 특히 R-12·R-14(적격 판정·`decision`별 severity 제한), R-17·R-18·R-19(부재·전칭 주장), R-21은 독립 검토 대상이다.
- 재구현: 미수행
