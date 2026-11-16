---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
sources:
  - plugins/codex-security/skills/fix-finding/SKILL.md
  - plugins/codex-security/skills/fix-finding/agents/openai.yaml
  - plugins/codex-security/skills/verify-fix/SKILL.md
  - plugins/codex-security/skills/verify-fix/agents/openai.yaml
  - plugins/codex-security/skills/README.md
  - plugins/codex-security/references/static-finding-assessment.md
  - plugins/codex-security/references/scan-artifacts.md
  - plugins/codex-security/references/artifact-storage.md
  - plugins/codex-security/schemas/findings.schema.json
  - plugins/codex-security/shared/workbench-migrations.json
  - plugins/codex-security/mcp-app/server.ts
  - plugins/codex-security/mcp-app/src/workbench-client.ts
  - plugins/codex-security/scripts/workbench_remediation.py
  - plugins/codex-security/scripts/workbench_db.py
  - plugins/codex-security/scripts/workbench_cli.py
  - plugins/codex-security/scripts/workbench_constants.py
  - plugins/codex-security/scripts/workbench_target.py
  - sdk/typescript/src/remediation.ts
  - sdk/typescript/src/api.ts
  - sdk/typescript/src/finding-prompt.ts
  - sdk/typescript/src/codex-prompt.ts
  - sdk/typescript/src/cli.ts
  - sdk/typescript/src/patch-publication.ts
depends:
  - ./caller-modes.md
status: draft
---

# 수정과 수정 검증 (`fix-finding`, `verify-fix`)

> 이미 보고된 보안 finding을 입력으로 받아, 최소 변경으로 패치하고(`fix-finding` skill, workbench의 Generate·Apply·Verify 단계, SDK `patch`, `cs patch`) 기존 수정이 취약점을 막는지 읽기 전용으로 판정하는(`verify-fix` skill, `cs verify-fix`) 지침과, 그 결과를 workbench의 remediation 상태 기계와 SDK·CLI 결과 형식으로 받아 기록하는 코드를 정의한다.

<!--
이 레포에는 정적 분석 코드가 없다. 무엇이 안전한 패치인지, 취약점이 막혔는지는 SKILL.md를 읽은 모델이 정한다. R-ID 앞의 [지침]은 모델에게 주는 규칙(코드 확인 = 지침 문장을 읽었다)이고, [강제]는 코드가 검사하거나 만든다는 뜻이다. [강제 없음]은 코드가 같은 것을 보장하지 않는다는 부재 주장이다. 모델이 지침을 따르는지는 R-34가 미확인으로 묶는다.
이 기능에는 입구가 둘이고 서로 상태를 공유하지 않는다. (가) workbench 경로: Codex 데스크톱이 요청을 만들고 모델이 `fix-finding` skill의 Generate·Apply·Verify 단계를 따라 MCP 도구 `set_codex_security_finding_remediation`으로 SQLite 상태를 갱신한다. (나) SDK·CLI 경로: `CodexSecurity.patch`, `cs patch`, `cs verify-fix`가 plugin을 끈 Codex를 띄워 skill 문서를 prompt로 읽히고 결과 JSON을 받는다. 둘 다 같은 skill 문서를 쓰지만 결과 형식과 기록 위치가 다르다(R-32).
용어: "assigned finding"은 workbench가 한 remediation 요청에 묶어 모델에게 넘기는 finding 하나이고, "attempt"는 `finding_remediation_attempts`의 한 행(요청 하나의 생애)이다.
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

흐름 A는 workbench(Codex 데스크톱) 경로, 흐름 B는 CLI 경로다. 순서가 있는 것은 각 흐름 안에서만이다.

**흐름 A. workbench 단계별 수정**

1. 완료된 scan(`status = complete`)에서 사용자가 finding의 수정을 요청하면 앱이 `request_codex_security_finding_remediation`(app 전용)으로 attempt를 만든다. attempt는 `requested` 상태, version 1, 대기 작업 `generate`, 요청 때의 checkout `base_revision`과 `base_content_digest`를 갖는다(R-14, R-20).
2. 앱이 모델에게 `scanId`, `occurrenceId`, `requestId`, `actionToken`, 기대 version을 담은 요청을 보낸다(요청 본문은 레포 밖, U-01). 모델은 `get_codex_security_scan_context`에 이 값을 넘겨 assigned finding과 현재 `remediationState`를 읽는다(R-13).
3. Generate 단계: 모델이 격리된 작업 복사본에서 패치를 개발하고 검증한 뒤 `set_codex_security_finding_remediation({ state:"generated", patch, … })`로 unified diff를 보낸다. 서버가 patch를 검사해 scan 디렉터리에 저장하고 digest와 함께 attempt를 `generated`로 올린다(R-09, R-15~R-17).
4. 사용자가 적용을 승인하면 앱이 `request_codex_security_finding_remediation_action`으로 `apply`를 요청하고, 모델이 Apply 단계에서 정확히 그 patch를 선택된 작업 트리에 적용한 뒤 `state:"applied"`를 보낸다. 서버는 checkout이 "기준 + 이 patch"와 정확히 같은지 확인한다(R-10, R-18).
5. 사용자가 검증을 요청하면 `verify` 요청이 만들어지고, 모델이 소스를 바꾸지 않고 검증 gate를 수행해 `verifying`을 거쳐 `verified`(또는 `failed`)를 보낸다. `verified`에는 검증 요약이 필수다(R-11, R-19).
6. 어느 단계든 실패하면 모델이 `failed`와 실패한 단계·오류를 `summary`에 담아 보낸다(R-12, R-16).

**흐름 B. CLI 수정과 검증**

1. `cs patch --scan <id|latest> [--severity L]`이 저장된 scan에서 open finding을 골라 하나씩 `fix-finding` skill을 돌리고 finding마다 `{occurrenceId, status, files, verification, reason}`을 받아 해석한다(R-28). 직접 입력(`cs patch <text|file>`)은 skill의 자연어 보고서를 그대로 출력하고 작업 트리 변경 여부로 성공을 판정한다.
2. `cs verify-fix --scan …` 또는 직접 입력은 `verify-fix` skill 본문과 `static-finding-assessment.md`를 prompt에 인라인해 읽기 전용 sandbox에서 돌리고 `{results:[{id,status,evidence}]}`를 받는다(R-29~R-31).
3. SDK의 `CodexSecurity.patch({ repositoryPath, finding })`은 finding 하나를 받아 `{status, changedFiles, verificationReport|reason}`를 돌려준다(R-26, R-27).
4. `cs patch --create-pr`는 검증된 patch만 branch로 commit해 draft PR/MR을 만든다. 이 스펙은 그 경계 한 줄만 다룬다(R-33).

### 1.2 범위·통합 지점 [필수]

- 제공: `fix-finding`·`verify-fix` skill의 절차와 제약(작업 복사본 규칙, 신뢰 도구 선택, 오프라인·권한 경계, 검증 gate), 입력 finding과 원본 evidence의 형식, 결과 형식, MCP 도구 `set_codex_security_finding_remediation`과 workbench `finding_remediation_attempts` 상태 기계(`workbench_remediation.py`와 `workbench_db.py`의 remediation 함수), SDK가 이 skill을 prompt로 지시하고 결과를 받는 부분(`sdk/typescript/src/remediation.ts`, `api.ts`의 `patch`, `cli.ts`의 `patch`·`verify-fix`·`runSkill`).
- 제외(이유):
  - patch를 만드는 모델의 코드 변경 내용 자체(이 스펙은 입출력과 제약만 다룬다).
  - GitHub/GitLab draft PR 생성 상세(`sdk/typescript/src/patch-publication.ts`와 `cli.ts`의 `publishPatchBranch`, 사용자 요청: 계약 한 줄만, R-33). hosted remediation 프로토콜(`sdk/typescript/src/hosted-remediation.ts`, `--host` 옵션, 이번 범위 밖). Linear 연동(`--linear-*`, 범위 밖). 패치 위험 평가(`--assess-patch-risk`, `assess-patch-risk` skill은 행 13).
  - workbench 저장소 전체 스키마와 finding triage(행 12, S4): remediation attempt 행과 triage가 remediation에 미치는 영향만 다룬다.
  - 이 레포에 없는 Codex 데스크톱 앱의 요청 UI와 continuation 지시문(U-01).
  - 같은 SDK 경로의 `cs scan`, `cs validate`(행 5·15).
- 외부 의존·선행 계약: 입력 finding은 완료된 scan의 sealed `findings.json`(S2, 행 9가 소유)에서 온다. 이 스펙은 finding의 필드 형식을 `schemas/findings.schema.json`으로 가리키고 내용은 소유 스펙에 맡긴다. scan context 조회와 소유 증명의 일반 규칙은 [caller-modes.md](./caller-modes.md)(R-27 (a)가 remediation 인자 분기를 설명한다)다. 후보 ledger(S1, 행 4~6)는 이 기능이 읽지 않는다(선행 판단은 2.1 부재 주장 1). Codex 프로세스는 SDK가 준 sandbox·network 설정을 따른다고 가정한다(확인 한계). workbench는 Python + SQLite, 신뢰 Git 실행 파일(`trusted_git_executable`)이 필요하다.
- 소유 상태·부작용:
  - workbench DB `finding_remediation_attempts`(요청 하나당 한 행, 수명은 occurrence의 수명) 행과 이 attempt가 가리키는 scan 디렉터리 안의 patch 파일 `artifacts/remediation/<occurrenceId>/<requestId>/<actionToken>.patch`.
  - 대상 저장소의 작업 트리(Apply 단계, SDK `patch`, `cs patch`가 수정한다). Generate 단계는 격리된 복사본만 수정한다.
  - fix 보고서 경로 `<artifacts_dir>/fix_report.md`는 문서에만 있고 코드가 읽거나 쓰지 않는다(2.1 부재 주장 2).

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 입력 finding과 원본 evidence 형식

| 경로 | 입력 | 형식·의미 |
|---|---|---|
| workbench 단계 | `get_codex_security_scan_context({ scanId, occurrenceId, requestId, actionToken })`가 돌려주는 assigned finding | `{ scan: { scanId, targetPath, targetRevision, scanDir, findings: [finding] } }`. `finding`은 workbench가 저장소(occurrence) 행에서 만든 객체이고 그 안의 `remediationState`가 현재 attempt를 보여 준다(1.3.4). 세 인자(`occurrenceId`, `requestId`, `actionToken`)가 모두 있어야 한다 |
| `cs patch --scan`, `cs verify-fix --scan` | 저장된 scan의 open finding(occurrence 또는 finding ID, `occ_`·`csf_` 접두) | sealed 산출물의 finding(`loadContract`로 읽은 `findings.json`)에 workbench의 live 필드(`createdAt`, `triage`, `remediationState`, `matches`, `knownSince`, `knownScanIds`, `related`, `sourceExcerpt`, `artifactPaths`)를 덮어쓴 객체. triage가 `closed`인 finding은 제외된다 |
| 직접 입력(`cs patch`, `cs verify-fix`) | 텍스트, 파일 경로, `file://` URL, `text:<값>` | `text:` 접두는 접두를 뗀 문자열 그대로. `file://`은 로컬만 허용(host가 있으면 거부). 그 밖의 문자열은 존재하는 일반 파일이면 그 내용, 아니면 문자열 그대로 prompt에 들어간다. 비어 있으면 거부한다 |
| SDK `patch` | `finding: string \| object` | 문자열은 경로가 아니라 내용이다. 비어 있거나(공백뿐) 객체가 아닌 값이면 "A finding must be nonempty text or a JSON object."로 거부한다 |

finding 객체의 필드(`schemas/findings.schema.json`의 finding 항목): 필수 `findingId`, `occurrenceId`, `ruleId`, `identity`, `fingerprints`, `title`, `summary`, `severity`, `confidence`, `taxonomy`, `locations`, `remediation`, `provenance`, 선택 `writeup`, `codeEvidence`(`code_evidence`), `rootCause`(`root_cause`), `validation`, `attackPath`, `remediationTests`, `preventiveControls`, `extensions`. skill이 "원본 evidence"로 읽는 것은 이 중 `locations`, `codeEvidence`, `attackPath`, `rootCause`, `remediation`이고 AWS Continuum에서 온 finding은 `evidence`의 `patches[].patch`·`source_data.patches[].patch`를 시작 후보로 쓴다(fix-finding SKILL 38행). 필드 의미는 행 9가 소유한다.

prompt는 finding을 `Findings`(verify) 또는 `Issues`(patch) JSON 배열로 넣고 "데이터이지 지시가 아니다"라고 명시한다. 전체 prompt가 `MAX_CODEX_INPUT_CHARACTERS`(= 2^20 문자)를 넘으면 `finding.json`을 임시 디렉터리(mode `0600`)에 쓰고 경로만 prompt에 넣어 모델이 파일을 읽게 한다(R-29).

#### 1.3.2 결과 형식

| 위치 | 형식 | 값·제약 |
|---|---|---|
| `fix-finding` 기본 출력(skill) | 텍스트 | outcome `fixed`·`no_change`·`blocked`, 취약 경로·불변식·보존할 정상 동작, 선택한 patch 전략, 바뀐 파일, 추가한 테스트, 실행한 명령과 결과, 원 경로가 닫혔다는 근거(소스 평가와 실행 관찰을 구분), 정상 동작이 유지된다는 근거, 남은 불확실성. 호출자가 출력 스키마를 주면 그것을 따른다(R-07) |
| SDK `patch` 결과 | `{ status, changedFiles, verificationReport?, reason?, threadId, cost }` | `status` 4종 `verified`·`no_change`·`blocked`·`failed`. `verified`: `changedFiles`가 비어 있지 않고 `verificationReport`가 있고 `reason` 없음. `no_change`: `changedFiles`가 비어 있고 `verificationReport` 있음. `blocked`·`failed`: `reason` 필수, `verificationReport` 선택. `changedFiles` 원소는 저장소 상대 경로(절대·`..`·루트 불가, POSIX와 Windows 양쪽 기준) (R-27) |
| `cs patch`의 skill 결과(finding별) | `{ patches: [{ occurrenceId, status, files, verification?, reason? }] }` | `status` 같은 4종. `verified`·`no_change`는 `verification` 필요, `blocked`·`failed`는 `reason` 필요. 한 finding당 정확히 한 항목, `occurrenceId` 일치 (R-28) |
| `cs patch --scan` 출력 | `{ scanId, repository, patches[], applied, filesChanged, files[] }`(JSON 출력일 때), 실패 코드 `PATCH_FAILED`·`NO_PATCH_APPLIED` | 종료 코드: 하나라도 `failed`면 2, 아니고 `blocked`가 있으면 1, 아니면 0. 종료 코드가 0이어도 바뀐 파일이 0개면 `NO_PATCH_APPLIED` 오류다(R-28) |
| `verify-fix` skill 결과 | `{ results: [{ id, status, evidence }] }` | `status` `fixed`·`still_vulnerable`·`inconclusive`. `evidence`는 비어 있지 않은 문자열. 사람이 읽는 대화에서는 Markdown(finding별 판정, 근거, 확인한 검사, 남은 증명 공백) (R-24) |
| `cs verify-fix` 출력 | `{ repository, scanId?, results[] }` 또는 실패 `VERIFICATION_FAILED`. 기본 출력은 `<STATUS> <id>: <evidence>` 줄 | 종료 코드: 하나라도 `inconclusive`면 2, 아니고 `still_vulnerable`이 있으면 1, 아니면 0. 실패·결과 개수나 ID 불일치도 2 (R-30) |

#### 1.3.3 MCP 도구

| 도구 | 노출 | 입력 | 효과 |
|---|---|---|---|
| `get_codex_security_scan_context` | model | `scanId`, `occurrenceId`, `requestId`, `actionToken`(셋이 함께) | assigned finding 문맥만 돌려준다(R-13) |
| `set_codex_security_finding_remediation` | model | `scanId` 없이 `occurrenceId`, `requestId`, `actionToken`(uuid), `expectedVersion`(양의 정수), `state`(`generated`·`applied`·`verifying`·`verified`·`failed`), `patch?`(UTF-8 문자열 또는 `{ encoding:"base64", content }`), `patchPath?`, `patchDigest?`(`sha256:<64 hex>`), `baseRevision?`(최대 512), `summary?`, `verificationSummary?`(각 최대 2400) | attempt 상태를 갱신한다. 서버가 `assignedFinding: true`로 호출해 결과는 assigned finding 문맥이다(R-15) |
| `request_codex_security_finding_remediation`, `request_codex_security_finding_remediation_action`, `claim_codex_security_finding_remediation_resend`, `release_codex_security_finding_remediation_claim`, `cancel_codex_security_finding_remediation_request`, `mark_codex_security_finding_remediation_delivered` | app | `occurrenceId`, `requestId`, `actionToken`(+ action 요청은 `action`·`expectedVersion`) | 앱이 쓰는 요청·소유권 도구. 이 스펙은 이름과 R-14의 효과만 다룬다 |

patch 입력에서 문자열 `patch`는 well-formed Unicode여야 하고(짝 없는 surrogate가 있으면 "원본 바이트를 base64로 보내라"며 거부), 비UTF-8 바이트는 `{ encoding:"base64", content }`로 보낸다. 서버는 이를 stdin 바이트로 workbench에 넘긴다(`patchStdin`).

#### 1.3.4 remediation 상태

attempt 행(`finding_remediation_attempts`)의 열: `request_id`(PK), `occurrence_id`, `state`(`idle`·`requested`·`generated`·`applied`·`verifying`·`verified`·`failed`·`superseded`), `version`(1부터 증가), `base_revision`, `base_content_digest`, `applied_content_digest`, `pending_action`(`generate`·`apply`·`verify`), `pending_action_claimed_at`, `pending_action_claim_token`, `pending_action_delivered_at`, `patch_path`, `patch_digest`, `summary`, `verification_summary`, `created_at`, `updated_at`. 모델이 보는 `remediationState`는 attempt가 없으면 `{ state: "idle" }`, 있으면 가장 최근 attempt의 `baseRevision`, `actionClaimedAt`, `actionClaimToken`, `actionDeliveredAt`, `pendingAction`, `patchDigest`, `patchPath`, `patch`(최대 16000바이트 미리보기, digest가 맞을 때만), `patchStats`(`additions`, `deletions`, `fileCount`, `previewTruncated`), `requestId`, `state`, `summary`, `updatedAt`, `verificationSummary`, `version`이다.

| 현재 → 허용되는 다음 상태(`set`) | 비고 |
|---|---|
| `requested` → `requested`, `generated`, `failed` | 대기 작업 `generate` |
| `generated` → `generated`, `applied`, `failed` | `applied`는 먼저 `apply` 요청이 있어야 한다 |
| `applied` → `applied`, `verifying`, `failed` | `verifying`은 먼저 `verify` 요청이 있어야 한다 |
| `verifying` → `verifying`, `verified`, `failed` | |
| `verified` → `verifying`, `verified` | 재검증 |
| `failed` → `generated`, `applied`, `verifying`, `verified`, `failed` | 재시도 |

(`require_transition`, R-16). `set`의 `state`에는 `requested`·`idle`·`superseded`가 없다. 이 셋은 서버가 만든다(`request-finding-remediation`이 `requested`, 새 요청이 이전 `generated`·`applied` attempt를 `superseded`로 바꾼다).

### 1.4 행동 규칙과 남은 질문 [필수]

#### `fix-finding` skill [지침]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [지침] 사용 경계와 목적 | 사용자가 검증됐거나 그럴듯한 보안 취약점의 수정과 검증을 명시적으로 요청할 때만 쓴다. 일반 버그 수정, 정확성·설계 리뷰 finding, 일반 검증, PR·commit·branch·patch·저장소 전체 scan에는 쓰지 않는다. 목적은 현재 finding을 최소한의 검증된 코드 변경으로 바꾸는 것이고, 코드가 이미 안전하면 그것을 증명하고 변경 없음으로 보고한다. 증거로 현재 상태를 분류하고, 깨진 보안 경계를 닫고, 정상 동작을 보존하고, 선택한 verification mode가 요구하는 검사를 통과한다. 저장소의 관례에 맞는 가장 작은 변경을 택한다 | 코드 확인 (지침 문장) |
| R-02 | [지침] verification mode | 기본은 `standard`이고 호출자가 `verificationMode: static`을 명시할 때만 `static`이다. 선택한 mode는 위임한 모든 agent와 workbench 단계에 전달한다. `static`은 소스와 diff 증거만 평가한다: 의존성 설치, 빌드, 테스트, reproducer, 애플리케이션 실행을 하지 않고(검증 지시가 요구해도 하지 않는다) 저장소 읽기 도구는 쓸 수 있다. 런타임 검사를 하지 않았다고 명시하고 통과로 세지 않는다. 런타임 도구 부재만으로는 `blocked`가 아니지만 소스 증거의 중대한 공백은 `blocked`다 | 코드 확인 (지침 문장) |
| R-03 | [지침] 패치 전 조사(patch contract) | 편집 전에 영향받는 구현, 직접 호출자, 근처 helper, 관련 기존 테스트를 읽고 다음을 저장소 증거로 확정한다: 공격자 제어 입력과 source-to-sink 경로 또는 깨진 통제, 보안 불변식과 가장 좁은 공유 강제 지점, 유지해야 할 정상 동작·API·오류 의미·호환성, 가장 가까운 기존 구현·검증·오류 처리 선례. finding을 이름 붙은 입력 예시가 아니라 data-flow와 경계 문제로 본다: 동등한 인코딩, parser 형태, alias, 호출자, sink, 보안 상태의 모든 표현·복사본을 확인하고 안전하지 않은 상태를 조용히 받아들이거나 자르거나 다른 도달 가능한 형태로 재해석하지 않는다 | 코드 확인 (지침 문장) |
| R-04 | [지침] 구현 절차 | (1) 보고된 경로를 따라 실제 공유 경계를 찾고, 증거가 이미 안전함을 보이면 투기적 변경 없이 `no_change`를 돌려준다. (2) `standard`에서 가능하면 그 경계를 지나는 가장 작은 고신호 재현 하나와 같은 경로의 정상 입력 하나를 돌린다. (3) 공유 경계에 저장소 관례의 가장 작은 수정을 적용하고 관련 없는 재설계·정리·형제 finding으로 넓히지 않는다. finding에 이 저장소용 patch 제안이 있으면 시작 후보로 쓰되 현재 checkout과 hunk를 비교해, 불변식을 지키는 hunk는 유지하고 우회를 남기거나 정상 동작을 깨는 hunk는 고치거나 바꾼다. (4) 검증 전에 patch를 방어하지 말고 도전한다: 바뀐 helper의 모든 직접 호출자와 바뀐 조건의 양쪽 결과를 보고, 여전히 취약 sink에 닿는 형제 경로·표현·복사본 하나와 patch가 새로 거부하거나 재해석하는 평범한 입력 하나를 찾아 있으면 수정한다. (5) `standard`의 검증: 최종 diff 검토와 가장 좁은 문법·import·빌드·타입 검사, 보안 trigger(또는 가장 강한 대체 검사)와 다른 악성 입력 한 종류의 재실행, 정상 동작·가장 가까운 기존 테스트·패키지의 필수 검사 재실행. `static`은 최종 diff 검토, 변경된 통제를 통한 원 exploit 경로와 대안 입력의 추적, 호출자와 기존 테스트를 소스로 읽어 정상 동작·호환성 확인이고 각 gate의 소스 증거를 인용하며 확립하지 못한 것을 밝힌다 | 코드 확인 (지침 문장) |
| R-05 | [지침] 수정 검토 | 남은 우회와 정상 동작 회귀를 찾아 patch에 도전한다. 복잡도·불확실성·보안 영향이 크면 독립 조사나 검토를 쓴다. 새로운 read-only 검토자에게는 finding, repository root, 허가된 범위, 저장소 정책, verification mode, 후보 diff를 주고 작성자의 논리와 주장한 테스트 결과는 주지 않는다. 위임이 안 되면 별도 pass로 직접 한다. 검토 의견은 소스(또는 `standard`의 집중 실행)로 확인한 뒤에만 patch를 바꾸고, 확인된 문제만 finding과 호환성 경계 안에서 고친 뒤 영향받은 gate를 다시 돌린다. 임시·무관한 변경이 남지 않게 한다 | 코드 확인 (지침 문장) |
| R-06 | [지침] `blocked`와 hard rules | 취약점이 실제일 수 있지만 필수 증거, 도구, 접근, 제품·호환성 결정이 없어 안전한 수정을 책임 있게 완료·검증할 수 없으면 `blocked`다. 선택한 mode의 모든 gate를 통과하기 전에는 `fixed`로 보고하지 않는다(저장소 증거가 무관함을 보이는 검사만 생략 가능하고, 필요한 검사를 못 하면 `blocked`다). `standard`에서 집중 테스트나 reproducer가 가능한데 코드 검토만으로 판단하지 않는다. 사용자 변경과 무관한 로컬 수정을 지우지 않고, 인증·인가·tenant 격리·입력 검증·sandbox·logging을 약화해 테스트를 통과시키지 않고, 증명 공백을 숨기지 않는다 | 코드 확인 (지침 문장) |
| R-07 | [지침] 출력과 보고서 경로 | 호출자의 출력 스키마가 있으면 따르고 없으면 1.3.2의 항목을 최종 응답에 담는다. scan artifact 디렉터리를 쓰면 `scan-artifacts.md`로 경로를 해석해 보이는 보고서를 `<artifacts_dir>/fix_report.md`에 쓰고, scan 디렉터리가 없으면 최종 채팅 요약으로 충분하다(사용자가 파일을 원하지 않는 한). 저장 위치 선택은 먼저 `artifact-storage.md`를 읽고 따른다 | 코드 확인 (지침 문장) |

#### workbench 단계(Generate·Apply·Verify) [지침]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-08 | [지침] 단계 공통: 컨텍스트와 신뢰 도구 | workbench 요청에 scan ID, occurrence ID, remediation request ID, action token, 기대 version이 있으면 assigned finding을 읽거나 새로 고칠 때 `get_codex_security_scan_context`에 `scanId`, `occurrenceId`, `requestId`, `actionToken`을 넘기고 요청된 단계만 따른다(단계 경계는 코드를 쓸 수 있는 때를 바꿀 뿐 검증 요구를 약하게 하지 않는다). 작업 복사본을 만들거나 들어가기 전에, 모든 checkout과 capture·rehearsal 작업 공간 밖의 통제된 빈 디렉터리에서 Python과 Git을 고르고 각 신뢰 도구의 절대 호출 경로, resolve된 상위 디렉터리, resolve된 실행 파일이 선택한 target, 그것을 포함하는 checkout, 모든 작업 공간 밖에 있는지 확인한다. Python은 host가 고른 `CODEX_SECURITY_PYTHON_COMMAND`(SDK 실행)이고 없으면 신뢰 절대 `PYTHON`, host 관리 런타임, 확인된 시스템 인터프리터이며 따옴표 친 절대 경로를 `-I`로 호출해 설치된 plugin의 scripts 디렉터리 helper를 import한다. 같은 디렉터리에서 `workbench_target.trusted_git_executable(target)`을 불러(`CODEX_SECURITY_GIT`을 존중하거나 Git을 찾는다) 반환된 절대 경로를 helper 프로세스의 `CODEX_SECURITY_GIT`에 고정해 하위 helper에 넘기고, 둘 중 하나라도 확인하지 못하면 멈춘다. Generate·Apply의 Git 명령은 `offline=True`와 실제 target으로 `workbench_target.git_command`를 부르고 `-C`로 작업 디렉터리를 주고 `-c core.hooksPath=<빈 private 디렉터리>`를 둔다. 원문은 C-01 | 코드 확인 (지침 문장) |
| R-09 | [지침] Generate 단계 | 수정을 개발·편집하기 전에 worker와 자식 프로세스의 파일시스템 쓰기를 격리된 worktree나 임시 작업 공간으로 한정한다(파일시스템 링크를 통해서도). 쓰기를 한정할 수 없으면 편집·저장소 명령 실행 전에 `failed`를 기록한다. 링크는 링크 항목으로 보존하고 referent 편집은 복사본 안의 검증된 경로로 한다. Git 작업 트리: 시스템·사용자 Git 설정이 닿지 않게 private 저장소를 `git init --template=`(target의 object format)로 만들고 요청의 working-tree baseline(로컬 편집, 의도된 untracked 포함)을 파일 mode·symlink·중첩 위치·저장소 안 `.gitattributes`와 함께 복사하고 source Git metadata·config·hook은 복사하지 않는다. 외부 Git filter는 `clean`·`smudge`·`process`를 지워 비활성화한다. private index를 target의 stage-zero blob 항목으로 채우고(`git ls-files --stage -z`, `LC_ALL=C`, `error:`·`fatal:` 진단이면 종료 코드와 무관하게 멈춤, blob은 `workbench_source_scopes.offline_git_bytes`로 읽고 하나라도 로컬에 없으면 멈춤) 의도한 기존 경로를 stage해 `git write-tree`를 `BASE`로 기록한다. 최종 diff는 의도한 경로만 `git add -A`로 stage한 뒤 `git diff-index --cached --binary --relative --no-ext-diff --no-textconv --no-renames --submodule=short --no-color --unified=3 --src-prefix=a/ --dst-prefix=b/ BASE -- .`을 바이트로 캡처한다. Git 밖 target은 baseline을 형제 디렉터리 `a`·`b`로 복사해 `git -c core.autocrlf=false diff --no-index --binary --no-prefix --no-renames --submodule=short --no-ext-diff --no-textconv --no-color --unified=3 -- a b`를 캡처한다(종료 코드 1이 차이 있음). 전체 diff를 의도한 변경과 대조하고, native 변환이 비Git 변경에 영향을 줄 수 있으면 등록 전에 별도 일회용 baseline에서 rehearsal(Apply 설정 아래 정방향 결과를 `b`와, 되돌린 결과를 `a`와 원시 바이트까지 비교)을 하고 재현하지 못하면 `failed`를 기록한다. 마지막에 정확한 unified diff를 `patch`로(UTF-8 문자열 또는 base64) 보내 `set_codex_security_finding_remediation`을 `state: "generated"`로 부른다. 이미 검토된 scan-local patch는 `patchPath`와 `patchDigest`만 보내고 `patch`는 생략하며 이미 reviewed patch가 있는 실패한 Generate 재시도는 기록된 경로와 digest를 재사용한다 | 코드 확인 (지침 문장) |
| R-10 | [지침] Apply 단계 | 기록된 base revision과 patch digest를 확인한 뒤 정확히 그 patch만 선택된 작업 트리에 무관한 편집 없이 적용하고 `applied` 또는 `failed`를 기록한다. 이 단계에서 finding을 검증하거나 닫지 않는다. 예시: 선택 디렉터리 `components/api`, 단일 hunk가 기존 추적 일반 파일 `handler.py`를 제자리 편집, `core.autocrlf=false`, 변환 속성 없음이면, 현재 파일 바이트가 검토된 preimage와 맞는지 확인하고 `root, prefix = git_worktree_context(target)`로 `git_command(target, "-C", str(root), "-c", f"core.hooksPath={empty_hooks}", "apply", "--no-index", "--check", "--whitespace=nowarn", f"--directory={prefix}", "-", input_data=patch_bytes, text=False, offline=True)`가 성공하면 `--check` 없이 같은 digest 검증 바이트로 다시 호출하고 결과 파일이 정확히 검토된 결과인지 확인한다(`components/api` 안에서 실행하면 성공하면서 변경을 건너뛸 수 있다). 동등한 승인 Apply는 선택된 checkout에서 root와 prefix를 얻고 등록된 scan-local 파일을 `workbench_db.open_scan_local_file`로 한 번 읽어 SHA-256을 기록된 digest와 맞추고 모든 바이트를 제자리 diff의 검토된 전후 내용과 대조하며 실제 target 경로와 Git 설정이 예시 조건을 만족하는지 확인한 뒤 두 Git 명령을 실행한다. 안전한 적용 방법을 정할 수 없으면 쓰기 전에 `failed`를 기록한다 | 코드 확인 (지침 문장) |
| R-11 | [지침] Verify 단계와 `static`의 추가 규칙 | 소스를 수정하지 않는다. 선택한 mode의 검증 gate를 기록된 patch에 적용한다. 증거가 원 취약 경로가 닫혔고 정상 동작이 유지되고 필요한 검사를 통과했음을 확립할 때만 `verified`를 기록하고 정확한 증거와 실행한 명령을 검증 요약에 보존한다. 아니면 `failed`와 실패한 gate나 증명 공백을 적고 finding을 닫지 않는다. `static` mode에서 workbench setter의 checkout snapshot과 reverse check도 소스 전용 검증을 지켜야 하므로, 그런 작업을 요청하기 전에 적용 대상 작업 트리·index 속성(검토된 patch의 속성 변경 포함)에서 실행 가능한 filter가 없음을 확인하고, 확인하지 못하면 작업 전에 멈춘다 | 코드 확인 (지침 문장) |
| R-12 | [지침] 단계 실패와 위임 | 단계가 실패하면 `failed`를 기록하고 실패한 단계와 오류를 `summary`에 넣는다(등록이 실패하면 setter의 오류 포함). 부모 thread가 단계를 위임하면 worker가 그 단계의 terminal workbench 갱신까지 소유하고, 부모는 orchestrator로서 worker의 편집을 반복하거나 채팅 응답을 완료로 취급하지 않는다 | 코드 확인 (지침 문장) |

#### workbench 코드: 요청·소유권·상태 기록 [강제]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-13 | [강제] assigned finding 읽기 | `get_codex_security_scan_context`에 `requestId` 또는 `actionToken`이 있으면 `occurrenceId`·`requestId`·`actionToken`이 모두 있어야 하고 아니면 "Remediation context requires occurrenceId, requestId and actionToken."를 던진다. 서버는 `get-scan`을 이 셋으로 부르고, workbench는 그 occurrence에 대해 `request_id`가 같고 `pending_action_claim_token`이 이 token이며 `pending_action`이 NULL이 아닌 attempt가 있어야 한다("This remediation action is no longer owned by the supplied request and action token."). 통과하면 이 finding 하나만 `{ scan: { scanId, targetPath, targetRevision, scanDir, findings: [finding] } }`로 돌려준다. 이 경로는 모델 thread의 owner·claim 검사를 하지 않고 위 token 소유만 본다 | 코드 확인 |
| R-14 | [강제] 요청·소유권 도구(app 전용) | `request-finding-remediation`은 occurrence의 triage가 `closed`가 아니어야 하고("Reopen this finding before requesting remediation.") scan이 `complete`여야 하며(R-20) 현재 checkout이 scan 때의 revision이어야 한다(`remediation_checkout_snapshot`, 아니면 "Repository HEAD changed. Regenerate the remediation patch against the current checkout."). 같은 `request_id`가 이미 있으면 같은 occurrence일 때만 기존 결과를 돌려준다. 진행 중 attempt(대기 작업이 있거나 `requested`·`verifying`)가 있으면 그것이 `failed`이면서 claim이 만료된 경우가 아니면 "Finish or retry the active remediation operation before regenerating."로 거부한다. 이전 attempt가 `generated`·`applied`이면 `superseded`로 바꾼다. 새 attempt는 `requested`, version 1, `pending_action = generate`, claim token = `actionToken`이다. `request-finding-remediation-action`(`apply`·`verify`)은 `expectedVersion`이 맞아야 하고(다르면 "This remediation request changed. Refresh it before recording an update."), 현재 상태가 `apply`는 `generated`, `verify`는 `applied`여야 하며, patch 경로·digest가 있어야 하고 digest가 파일과 맞아야 하며(`apply`는 기준 내용, `verify`는 적용된 내용과 checkout이 같아야 한다, R-19의 같은 검사), 대기 작업이 NULL일 때만 대기 작업과 claim token을 설정하고 version을 올린다. 같은 action·token의 재요청은 그대로 돌려주고 다른 대기 작업이 있으면 "Another remediation operation is already pending."이다. `claim-…-resend`는 token이 같으면 그대로이고, 아니면 이전 claim이 없거나 만료됐을 때만 새 token으로 바꾼다(미전달 claim 120초, 전달된 claim 900초 lease). `mark-…-delivered`는 token이 일치하는 대기 요청의 전달 시각을 기록하고, `release-…-claim`은 token이 일치하는 claim을 비운다. `cancel-…-request`는 `requested`의 generate만 attempt를 삭제하고(이전 `superseded`는 `applied` 내용이 있었는지에 따라 `applied`·`generated`로 복원), 다른 대기 작업은 대기 필드를 비우며 `verifying`이던 verify는 `applied`로 되돌린다 | 코드 확인 (신규·취소 경로의 claim 만료 분기는 코드 읽기) |
| R-15 | [강제] `set_codex_security_finding_remediation` 검사 순서 | (1) `set-finding-remediation`은 scan이 `complete`여야 하고, occurrence가 열려 있어야 하고, `request_id`가 그 occurrence의 것이어야 한다. (2) `expectedVersion`이 현재 version과 다르면 "This remediation request changed. Refresh it before recording an update.". (3) 소유 claim token이 없으면 "This remediation attempt does not have an owned pending host request.", 다르면 "This remediation host request is owned by a different action token.". (4) 상태 전이(R-16)와 대기 작업 일치를 확인한다. (5) `patch`가 있으면 stdin 바이트로 읽는다. patch 메타데이터(R-17)를 정한다. (6) `generated`·`applied`·`verifying`·`verified`는 patch 경로와 digest가 있어야 한다("Generated remediation states require a scan-local patch path and digest."). `patch`가 없고 경로·digest만 있으면 파일의 digest가 맞아야 한다. (7) 상태별 추가 검사(R-17~R-19). (8) 통과하면 `state`, `version + 1`, patch 경로·digest, `applied_content_digest`를 갱신하고 `generated`·`applied`·`verified` 때는 대기 작업과 claim을 비우고 `verifying`일 때는 대기 작업과 claim을 유지하며 `failed`일 때는 대기 작업을 남기되 claim과 전달 시각을 비운다. `summary`는 `failed`에서 다른 상태로 재시도할 때 새 값으로 교체되고(없으면 비워짐) 그 외에는 값이 있을 때만 바꾼다. `verification_summary`는 값이 있을 때만 바꾼다. (9) 결과는 assigned finding 문맥이거나, 그새 다음 작업이 시작됐으면 `{ occurrenceId, requestId, version }`이다. 어떤 검사든 실패하면 attempt는 바뀌지 않는다 | 코드 확인 |
| R-16 | [강제] 상태 전이와 대기 작업 결합 | 허용 전이는 1.3.4의 표다(`require_transition`). 대기 작업이 있으면 `generate`는 `generated`·`failed`, `apply`는 `applied`·`failed`, `verify`는 `verifying`·`verified`·`failed`만 기록할 수 있다. 대기 작업이 없을 때 (`requested`→`generated`), (`generated`→`applied`), (`applied`→`verifying`)은 각각 `generate`·`apply`·`verify` 요청이 먼저 있어야 한다("Request apply before recording remediation state applied." 형식). 위반하면 "Finding remediation cannot move from <현재> to <요청>." 또는 "Pending remediation action <작업> cannot record state <요청>."이다 | 코드 확인 |
| R-17 | [강제] patch의 검증·저장 | `patch`는 `generated` 상태에서만, `patchPath`·`patchDigest` 없이 줄 수 있다(아니면 "Supply patch only for generation, without a patch path or digest."). 새 patch의 경로는 이미 있으면 그것, 없으면 `artifacts/remediation/<occurrenceId>/<requestId>/<actionToken>.patch`이고 digest는 `sha256:<hex>`다. 한 attempt는 patch 경로나 digest를 바꿀 수 없다("A remediation attempt cannot replace its reviewed patch path/digest."). 참조 patch의 `patchPath`는 구분자 `/`의 scan 상대 경로여야 하고(절대·`..`·`\\` 불가) scan 디렉터리 안의 일반 파일이며 `patchDigest`는 `sha256:<소문자 64 hex>`다. 새 patch는 `generated`일 때 `require_valid_patch`로 검사한다: 모든 file section의 헤더와 hunk를 파싱하고 Git이 `apply --check`로 받아들이고 `--numstat -z` 파일 수가 section 수와 같아야 한다. hunk 없는 section은 빈 파일 추가·삭제나 blob이 같은 mode 변경·rename일 때만 허용하고 그 외는 "The remediation patch omits file content. Generate a complete binary diff with Git's --binary option."이다. binary patch는 `index` 줄에 target object format 길이의 전체 object ID가 있어야 한다. 저장은 sealed scan의 manifest digest와 scan 디렉터리 identity가 변하지 않는 동안 scan-local 파일을 배타적으로 만들고 fsync한 뒤 SQLite에 경로를 커밋하며, 같은 경로에 이미 파일이 있으면 digest가 맞는지 확인하고 아니면 실패한다. 저장 중 오류는 "Could not save the remediation patch: …"이다 | 코드 확인 |
| R-18 | [강제] `applied` 기록 검사 | `baseRevision`이 attempt의 `base_revision`과 같아야 한다("The remediation base revision changed. Regenerate the patch before applying it."). 그리고 `require_reviewed_patch_applied`가 checkout의 현재 revision이 base이고 현재 내용 digest가 `base_content_digest`와 다른지 확인한다("The selected checkout is unchanged; apply the reviewed patch before recording it as applied."). 이어 현재 작업 트리를 임시 디렉터리에 복사해(scan 디렉터리와 submodule 제외) 검토된 patch를 `git apply --reverse`로 되돌린 결과의 내용 digest가 `base_content_digest`와 같아야 한다. 다르면 "The selected checkout contains changes outside the reviewed patch. Remove them before recording the patch as applied."다. 되돌리기 실패는 "The selected checkout does not contain the reviewed remediation patch. Apply exactly that patch before recording it as applied."이다. 통과하면 현재 내용 digest를 `applied_content_digest`로 저장한다 | 코드 확인 |
| R-19 | [강제] `generated`·`verifying`·`verified` 기록 검사 | `generated`는 checkout이 요청 때의 revision과 `base_content_digest`와 같아야 한다("Working-tree contents changed. Regenerate the remediation patch against the current checkout."). `verifying`·`verified`는 `baseRevision`이 `base_revision`과 같아야 하고 checkout의 내용 digest가 `applied_content_digest`와 같아야 한다(같은 문구). `verified`는 검증 요약이 필요하다("Verified remediation requires a verification summary."). `failed`는 이 내용 검사가 없다 | 코드 확인 |
| R-20 | [강제] 가용성과 triage 상호작용 | remediation 명령은 대상 occurrence의 scan이 `complete`일 때만 쓸 수 있다("Remediation is available only for successfully completed scans."). scan context의 `remediationAvailable`은 scan이 `complete`이고 현재 checkout의 HEAD가 scan의 `target_revision`일 때만 true이고 아니면 이유 문구(`remediationUnavailableReason`)를 준다. finding triage를 `closed`로 바꿀 때 활성 remediation 대기 작업이 있으면(`failed`이면서 claim이 만료된 경우 제외) "Wait for the pending remediation operation to finish before closing this finding."이고, 닫는 이유가 `already_fixed`이면서 attempt가 `verified`이면 checkout이 `applied_content_digest`와 같아야 한다. remediation 도구는 모두 occurrence가 열려 있어야 한다 | 코드 확인 |

#### `verify-fix` skill [지침]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-21 | [지침] 사용 경계와 read-only | 보안 수정이 보고된 취약점을 고치는지 검증하라는 명시적 요청(직접 `$verify-fix` 포함)에만 쓴다. 수정 구현 요청이나 그 테스트 실행 요청만으로는 쓰지 않는다. 일반 작업은 사용자가 요청한 workflow를 따른다. 비보안 수정, 후보 finding 검증, 전체 scan에는 쓰지 않는다. 독립 검증 전용 모드로서 저장소 파일을 만들거나 수정하거나 지우지 않고, patch를 적용하지 않고, commit하지 않고, artifact를 쓰지 않고, issue tracker를 수정하지 않는다 | 코드 확인 (지침 문장) |
| R-22 | [지침] 평가 방법과 mode | `static-finding-assessment.md`로 원래 공격자 제어 source, 보안 통제, 민감 sink, 도달 경로, 신뢰 경계, 반증, 증명 공백을 식별한다(호출자가 prompt에 이 reference를 줬으면 다시 읽지 않는다). `standard`가 기본이고 `static`은 현재 소스와 diff, 원 exploit 경로와 그럴듯한 우회, 호출자와 기존 테스트를 소스로 읽은 정상 동작만 평가하며 설치·빌드·테스트·reproducer·앱 실행을 하지 않는다. evidence에 정적 평가이고 런타임 검사를 하지 않았음을 명시하며 통과로 세지 않는다. 런타임 도구 부재만으로 `inconclusive`가 되지 않고 소스 증거의 중대한 공백은 `inconclusive`다 | 코드 확인 (지침 문장) |
| R-23 | [지침] 검증 절차 | (1) 원 취약점, 전제, 영향받는 보안 경계, 계속 동작해야 할 정상 동작을 세운다. (2) 현재 checkout에 영향받는 구성요소가 있는지 확인하고 파일 누락·줄 삭제·함수 이름 변경을 수정의 증거로 보지 않고 옮겨지거나 리팩터링된 코드를 따라간다. (3) 원 exploit 경로를 현재 구현으로 따라가며 가장 가까운 통제, 동등한 경로, 그럴듯한 우회를 본다. (4) `standard`에서 저장소를 수정하지 않고 돌릴 수 있을 때만 원 reproducer, 집중 회귀 검사, 정상 동작 검사를 돌리고 런타임 검사가 안 되면 정확한 정적 증거를 보존한다. (5) 지정된 순서로 supplied finding마다 결과를 하나씩 낸다. 닫힌 ticket, 무관한 통과 테스트, 새 scan finding의 부재는 증명으로 충분하지 않다 | 코드 확인 (지침 문장) |
| R-24 | [지침] 결과 계약과 판정 | 대화에서는 읽기 쉬운 Markdown(finding별 판정, 근거와 소스 참조, 관련 검사와 남은 증명 공백)이다. 호출자가 JSON이나 자동화 결과 계약을 요청하면(CLI 검증은 명시적으로 요청한다) 정확히 한 JSON 객체 `{ "results": [{ "id", "status": "fixed\|still_vulnerable\|inconclusive", "evidence" }] }`를 낸다. `fixed`는 증거가 원 보안 경계가 닫혔고 정상 동작이 유지됨을 증명할 때만, `still_vulnerable`은 원 취약 경로가 여전히 도달 가능함을 증명할 때만, `inconclusive`는 repository 불일치, 원 문맥 부재, 선택한 mode가 요구하는 검사를 못 함, 증명되지 않은 정당한 통제, 그 밖의 중대한 증명 공백일 때다. read-only 경계를 약하게 하거나 다른 취약점으로 바꾸거나 누락한 증거를 숨겨서 더 강한 판정을 추론하지 않는다 | 코드 확인 (지침 문장) |

#### SDK·CLI 코드 [강제]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-25 | [강제] `remediationPrompt`(CLI·hosted 공용)의 prompt 구성 | `operation:"verify"`: "Follow the bundled `$codex-security:verify-fix` instructions…"에 이어 `verify-fix/SKILL.md` 본문과 `static-finding-assessment.md` 본문을 읽어 prompt에 그대로 넣고("Do not reload these instruction files."), 기대 결과 ID JSON 배열과 "ID마다 같은 순서로 정확히 한 결과" 지시를 붙인다. `operation:"patch"`: "Use the bundled `$codex-security:fix-finding` skill at <절대 경로>."이고, `structuredPatch`이면 finding마다 `{"occurrenceId","status","files","verification","reason"}` 한 객체를 `patches` 배열에 담은 JSON 하나만 내라는 지시(상태별 필수 필드, `static`이면 "원 공격 경로가 닫혔고 정상 동작이 보존됨을 정적 증거가 확립할 때만 verified")와 `blocked` 결과에 쓸 `reason` 서술 지침을 붙인다. 공통: 사용자 finding별 지시(occurrence ID를 키로 한 JSON), 저장소 지시(JSON 문자열), 검증 지시를 모드·operation에 맞는 안내 문장과 함께 붙이고, `static`이면 `STATIC_VERIFICATION_INSTRUCTIONS`를 붙이고, 마지막에 finding 배열을 붙인다. 문장 원문은 C-07이다 | 코드 확인 |
| R-26 | [강제] SDK `patch()`의 Codex 실행 구성 | 저장소 경로를 해석하고 임시 디렉터리가 저장소 밖임을 확인한다. Codex 세션은 `features.plugins = false`(plugin 비활성)이고 환경은 `CODEX_SECURITY_REPOSITORY`, `CODEX_SECURITY_PLUGIN_ROOT`, `CODEX_SECURITY_SURFACE`만 더한다([caller-modes.md](./caller-modes.md) C-04). 추가 설정으로 scan 권한 profile의 network를 끄고(`permissions.codex_security_scan.network.enabled=false`), `project_root_markers=[]`, 저장소 프로젝트를 `untrusted`로 고정해 저장소 MCP 서버가 로드되지 않게 한다. thread는 source `remediation`, `workingDirectory`=저장소, `skipGitRepoCheck`, 승인 정책 `never`, web search 비활성이고 `outputSchema`로 `patchResponseSchema`의 JSON Schema를 준다. prompt는 fix-finding SKILL.md의 절대 경로를 가리키고 "저장소 작업 공간은 의도적으로 mutable이니 무관한 변경을 보존하고 그 밖에는 쓰지 말라", "commit·push·publish·PR·원격 상태 갱신·검증(또는 `static`의 정적 평가) 없는 verified 주장 금지", 4개 키 JSON 규칙을 담는다. 취소·중단은 "Codex Security patch was interrupted; the workspace may contain partial changes at <repo>."의 `ScanInterruptedError`이고 부분 변경은 되돌리지 않는다 | 코드 확인 (Codex가 이 설정을 실제로 따르는 것은 확인 한계) |
| R-27 | [강제] SDK `patch()` 결과 검증 | turn 상태가 `completed`가 아니면 "Finding patch did not complete."이다. 최종 응답은 strict JSON `{status, changedFiles, verificationReport, reason}`(`verificationReport`·`reason`은 `null` 가능, 문자열은 trim 후 비어 있지 않음)이어야 하고 `changedFiles` 원소는 비어 있지 않은 저장소 상대 경로(POSIX·Windows 양쪽에서 절대·루트·`.`·`..`·`../` 시작 불가)다. 상태별 규칙: `verified`는 `changedFiles`가 비어 있지 않고 `verificationReport`가 있고 `reason`이 `null`이어야 한다. `no_change`는 `changedFiles`가 비고 `verificationReport`가 있고 `reason`이 `null`이다. `blocked`·`failed`는 `reason`이 있어야 한다. 파싱·검증 오류는 모두 "Finding patch returned an invalid result."로 바뀐다. SDK는 `changedFiles`를 실제 변경과 대조하지 않는다. 결과에 `threadId`와 추정 비용이 붙는다 | 코드 확인 (실제 변경과의 비대조는 2.1 부재 주장 3) |
| R-28 | [강제] `cs patch`의 finding 선택과 결과 해석 | finding 입력이 모두 `occ_`·`csf_` 식별자이거나 `--scan`이 있으면 저장된 finding 경로다(Linear와 함께 쓸 수 없고 `--resume-pr`는 다른 옵션과 함께 쓸 수 없다). `--scan latest`는 이 저장소의 `status: complete` scan 목록 첫 항목이고, scan 없이 식별자만 주면 open finding 전역 목록에서 찾으며 한 scan에 속해야 한다("Select findings from one saved scan at a time."). scan이 `findingsTruncated`이면 open finding 페이지를 모두 읽는다. 선택 대상: triage가 `closed`가 아닌 것 중 식별자가 주어지면 일치하는 것, `--severity`가 있으면 그 이상인 것. 요청한 식별자가 scan에 없으면 "The requested finding does not belong to the selected scan."이다. 그 뒤 sealed `findings.json`(`loadContract`)과 합쳐 finding을 하이드레이트하고 빠진 것이 있으면 "Finding <id> is missing from the saved scan artifacts."이다. 대상이 없으면 "No matching open findings to patch."이다. 각 finding은 순차로 따로 `fix-finding`을 돌리고(finding별 `structuredPatch` prompt, 사용자 finding별 지시 선택) 응답 JSON에서 `occurrenceId`가 일치하는 항목이 정확히 하나여야 하며 아니면 `failed("No complete patch result was returned for this finding.")`이다. 종료 코드가 0이 아니면 `failed("Patch command exited with status N.")`, JSON이 아니면 `failed("Patch results were not valid JSON.")`, `verified`·`no_change`인데 `verification`이 비어 있으면 `failed("Patch verification was not reported.", files)`, `verified`인데 작업 트리가 실제로 바뀌지 않았으면 `failed("No patch was applied; 0 files changed.")`이다. 종료 코드는 1.3.2 표와 같다(`failed`가 있으면 2, 아니고 `blocked`가 있으면 1, 그 밖 0). 모든 finding을 처리한 뒤 종료 코드가 0이 아니면 `PATCH_FAILED`, 0인데 바뀐 파일이 0개면 `NO_PATCH_APPLIED` 오류다. 직접 입력 경로는 `runSkill("fix-finding")` 한 번으로 skill의 자연어 응답을 출력하고 바뀐 파일이 0개면 `NO_PATCH_APPLIED`, skill 종료 코드가 0이 아니면 `PATCH_FAILED`다 | 코드 확인 |
| R-29 | [강제] 입력 크기와 finding 파일 | prompt 전체 길이가 2^20 문자를 넘으면 finding 전체를 임시 디렉터리 `codex-security-finding-*`의 `finding.json`(mode `0600`)에 쓰고 prompt에는 "The finding evidence is in this file: <경로>"를 넣어 모델이 데이터로 읽게 한다. 턴이 끝나면 디렉터리를 지운다(정리 실패는 무시). `cs verify-fix`는 finding을 prompt 크기 한도로 배치로 나눈다(각 배치의 overhead는 빈 prompt 길이, 한 finding이 한도를 넘으면 그 finding만 파일 기반 배치) | 코드 확인 |
| R-30 | [강제] `cs verify-fix` 실행과 결과 | 입력은 `FINDING...`(텍스트·파일·`file://`·식별자), `--scan ID [--severity LEVEL]`(저장된 open finding, `--severity`는 저장된 finding에만), Linear, `--host`(단독)다. 식별자는 저장된 경우 occurrence ID, 직접 입력은 `finding-1`, `finding-2`, …, Linear는 issue ID이고 중복이면 "Verification inputs must have unique finding or issue identifiers."다. 저장된 scan이면 그 scan의 `targetPath`가 작업 디렉터리이고 직접 입력이면 현재 디렉터리다. 배치마다 `runSkill("verify-fix")`를 돌리고 응답을 `parseFindingVerifications`로 해석한다: JSON이어야 하고("Verification results were not valid JSON."), `results` 개수와 ID 순서가 기대와 정확히 같고 각 항목이 `{ id, status, evidence(비어 있지 않음) }`여야 하며 아니면 "Codex did not return an evidence-backed verification result for every finding."이다. 종료 코드는 `inconclusive`가 있으면 2, 아니고 `still_vulnerable`이 있으면 1, 아니면 0이고 오류는 `VERIFICATION_FAILED`(종료 코드 2)이다. SDK `CodexSecurity`에는 `verify-fix` 메서드가 없다(CLI 전용) | 코드 확인 (SDK 메서드 부재는 2.1 부재 주장 4) |
| R-31 | [강제] `runSkill`의 Codex 실행 구성(patch·verify) | 둘 다 `codex app-server`를 `--disable plugins`로 띄운다(plugin MCP 없이 skill 문서는 prompt에 넣거나 절대 경로로 읽힌다). `verify-fix`: 스레드 source `validation`, 승인 정책 `on-request`이고 승인 검토자는 `auto_review`, sandbox `read-only`, 작업 디렉터리가 있어야 하며 없으면 "Codex did not receive the repository directory required for read-only verification."이다. 시작 전에 `config/read`로 설정 layer를 읽어 repository-local(project layer)의 MCP 서버를 모두 `enabled=false`로 끄고, 그 이름이 사용자가 구성한 MCP 서버 이름과 겹치면 "Repository-local MCP server "<이름>" overrides a configured integration; remove the repository override before verifying fixes."로 중단한다. `fix-finding`: 스레드 source `remediation`, 승인 정책 `never`, sandbox `workspace-write`(`--external-sandbox`이면 `externalSandbox` 정책에 network `enabled`로 바꾸고 경고를 출력), 시작 전에 `command/exec`로 `node -e ""`를 같은 sandbox에서 한 번 실행해 실패하면 "The patch sandbox could not start. Check the runner's sandbox permissions and retry. No patch was applied; 0 files changed."이다. 결과는 마지막 비-commentary `agentMessage` 텍스트이고 turn이 `completed`가 아니면 오류다. 지원하지 않는 client 요청에는 `-32601`로 답한다. 허용 설정 override는 model, reasoning effort, provider, daybreak, analytics.enabled뿐이다 | 코드 확인 (Codex 쪽 sandbox·network 기본값은 확인 한계) |
| R-32 | [강제 없음] SDK·CLI 경로가 workbench remediation 상태를 쓰는가 | `set-finding-remediation`, `request-finding-remediation`, `remediation_state` 계열 호출을 `sdk/typescript/src`에서 검색했고 `cli.ts:9606`의 저장 finding 하이드레이트 때 `remediationState` 키를 복사하는 한 줄만 있다. 즉 `cs patch`·`cs verify-fix`·SDK `patch`는 workbench `finding_remediation_attempts`를 만들거나 갱신하지 않는다. 이 상태는 workbench 경로(흐름 A)가 MCP 도구로만 바꾼다. `cs verify-fix`의 판정도 triage나 remediation 상태에 기록되지 않는다 | 코드 확인 (부재 주장은 2.1 부재 주장 5) |
| R-33 | [강제] `--create-pr`의 경계(상세는 범위 밖) | `cs patch --create-pr`는 검증된 patch만 branch `codex-security/patch-<id>`로 commit(메시지 `fix: patch verified security findings`)해 draft 형태의 PR/MR로 게시하는 흐름이다(옵션 설명은 "Create a draft GitHub pull request or GitLab merge request after verified patches."). 저장된 scan 경로는 시작 전에 HEAD tree와 현재 작업 트리·index의 변경, ignored·untracked 경로를 기록하고, 각 `verified` finding의 보고된 파일이 사전 변경·ignored·이전 미검증 변경과 겹치거나 보고되지 않은 경로를 바꾸면 그 finding을 `failed`로 돌리고 로컬 편집은 검토용으로 남긴다. 직접 입력 경로는 깨끗한 작업 트리(`HEAD^{tree}`와 같은 snapshot)를 요구한다. 게시 provider 호출(`publishPatchBranch`, `patch-publication.ts`)은 열지 않았다 | 코드 확인 (finding별 게이트는 `prepareSavedPatchPublication`의 `record`와 `requireCleanPatchPullRequestBase`) / 게시 동작은 미확인 |
| R-34 | 모델이 [지침] R-01~R-12, R-21~R-24를 따르는가: 최소 변경, 검증 gate 통과 전 `fixed` 보고 금지, 격리 작업 복사본, 신뢰 도구 선택, 단계 경계, `verify-fix`의 read-only 준수, 증명 공백 보고 | 실행하지 않았다. 코드가 검사하는 것은 R-13~R-20(상태 기계와 checkout digest), R-26~R-31의 형식과 sandbox 설정, R-28의 "verified인데 변경이 없으면 failed"뿐이다. 모델이 실제로 patch가 취약점을 막는지, 정상 동작이 보존되는지, 격리를 지켰는지는 코드가 판단하지 않는다 | 미확인 |

- 불변식:
  - attempt의 `version`은 갱신마다 1씩 증가하고, 호출자가 아는 `expectedVersion`과 다르면 어떤 갱신도 적용되지 않는다(R-15).
  - attempt의 patch 경로와 digest는 한 번 정해지면 바뀌지 않고(R-17), 저장된 patch 파일의 SHA-256은 digest와 같아야 단계가 진행된다.
  - `applied`가 기록된 attempt는 `applied_content_digest`를 갖고, 이후 `verifying`·`verified`는 checkout이 그 digest와 같을 때만 기록된다(R-18, R-19). 따라서 `verified`는 "검증 시점의 작업 트리가 patch를 적용한 직후와 같다"를 뜻한다.
  - SDK `patch`의 `verified`는 `changedFiles`가 비어 있지 않다는 것까지만 보장하고(R-27) 실제 diff와 일치함은 보장하지 않는다. `cs patch --scan`의 `verified`는 작업 트리가 실제로 바뀐 것이 확인된 경우만이다(R-28).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-08, R-13, R-14 | Codex 데스크톱이 Generate·Apply·Verify 요청을 모델에게 보내는 본문은 무엇인가. skill은 "scan ID, occurrence ID, remediation request ID, action token, 기대 version이 요청에 있다"고만 한다. 모델이 `set`에 넘길 `expectedVersion`과 `baseRevision`을 어디서 얻는지(assigned finding의 `remediationState.version`·`baseRevision`으로 추정)도 명시되지 않았다 | 이 흐름을 처음부터 재구현하는 사람이 모델에게 줄 요청 prompt를 정해야 한다 | Codex 데스크톱 앱 소스(레포 밖) 또는 실제 세션 기록 |

- 확인 한계:
  - 실행하지 않았다(`cs`, SDK, MCP, Python, Git, Codex). 오류 문구는 소스에서 옮겼고 실제 출력은 보지 않았다.
  - Codex가 SDK·CLI가 준 `features.plugins=false`, network 비활성, sandbox 정책을 실제로 어떻게 적용하는지, `workspace-write` sandbox의 network 기본값은 Codex 쪽 동작이라 확인하지 못했다. 코드는 "SDK가 그렇게 요청했다"는 증거다.
  - `fix-finding`이 요구하는 Git filter 비활성·격리 절차는 모델이 따르는 지침이다. workbench 쪽 코드(`require_reviewed_patch_applied`, `remediation_checkout_snapshot`, `git_command`)가 filter와 hook을 어떻게 다루는지는 일부만 읽었다(`copy_git_worktree_files`, `git_command` 본문은 열지 않음).
  - `workbench_remediation.py`의 `save_patch`, `reverse_reviewed_patch`의 Windows 분기(짧은 GIT_DIR 재생), `prepare_replay_gitfile`은 구조만 읽었다.
  - 게시(`publishPatchBranch`, `patch-publication.ts`)와 `--assess-patch-risk`, hosted·Linear 경로는 열지 않았다.
  - 입력 finding의 필드 의미(`severity`, `attackPath`, `codeEvidence` 등)는 행 9(S2)가 소유한다.

### 1.5 필수 코드 참조 [필수]

기준은 frontmatter SHA다. 라이선스는 Apache-2.0(overview 1절)이라 인용을 막지 않는다. skill 원문은 105줄·52줄이라 글로 다시 풀지 않고 줄 범위를 가져가는 쪽이 짧고 정확하다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `plugins/codex-security/skills/fix-finding/SKILL.md:6-105` | `fix-finding` 지침 원문 전체(mode, patch contract, 구현 절차, 검토, workbench 단계 Generate·Apply·Verify, 출력, hard rules) | R-01~R-12 |
| C-02 | `plugins/codex-security/skills/verify-fix/SKILL.md:6-52` | `verify-fix` 지침 원문과 결과 JSON 계약 | R-21~R-24 |
| C-03 | `plugins/codex-security/references/static-finding-assessment.md:1-75` | 평가 tuple, 증거 탐색 순서, 표면 분류, 정적 신뢰도(`verify-fix`가 링크, `remediation.ts`가 prompt에 인라인) | R-22, R-25 |
| C-04 | `plugins/codex-security/mcp-app/server.ts:418-458` `findingRemediationSchema`·`findingRemediationActionRequestSchema`·`findingRemediationClaimSchema`, `:1675-1796` 도구 등록 | 입력 스키마와 app·model 노출, `set` 호출의 `assignedFinding`·`patchStdin` | R-14, R-15 |
| C-05 | `plugins/codex-security/scripts/workbench_remediation.py:713-747` `require_transition`·`require_pending_action`, `:694-710` `remediation_claim_is_active`, `plugins/codex-security/scripts/workbench_constants.py:19, 27-29` | 상태 전이표, 대기 작업 결합, claim lease(120초, 전달 900초) | R-14, R-16 |
| C-06 | `plugins/codex-security/scripts/workbench_db.py:1991-2076, 2079-2143, 2146-2214, 2217-2259, 2262-2402` | 요청·action 요청·resend·delivered·release·`set` 구현 | R-14~R-16, R-19 |
| C-07 | `sdk/typescript/src/remediation.ts:1-208` | 결과 스키마, 정적 mode 지시문, `remediationPrompt`, `parseFindingVerifications`, `parseFindingPatch`, `verificationBatches` | R-25, R-28~R-30 |
| C-08 | `sdk/typescript/src/api.ts:526-643` `PatchOptions`·`PatchResult`·`patchResponseSchema`·`patchOutcomeFromResponse`, `:1514-1721` `patch`·`#patch` | SDK `patch`의 입출력, Codex 구성, prompt, 결과 검증 | R-26, R-27 |
| C-09 | `plugins/codex-security/scripts/workbench_remediation.py:397-481` `require_valid_patch`, `:484-517` `patch_metadata` | patch 완전성 검사와 경로·digest 결정 | R-17 |
| C-10 | `plugins/codex-security/scripts/workbench_db.py:2451-2541` `require_reviewed_patch_applied`, `:2544-2564` `require_remediation_checkout_unchanged` | applied·verified 기록 시 checkout 검사 | R-18, R-19 |
| C-11 | `sdk/typescript/src/cli.ts:7210-7458` `verify-fix` 명령, `:7460-7817` `patch` 명령, `:9410-9446` `resolveRemediationInputs`, `:9470-9620` `selectSavedFindings`, `:9638-9641` `patchExitCode`, `:10342-10488` `runFindingPatches` | CLI 입력 선택, per-finding 실행, 결과 해석, 종료 코드 | R-28, R-30 |
| C-12 | `sdk/typescript/src/cli.ts:10503-10900` `runSkill`, `:10992-11011, 11164-11202` app-server thread 시작·sandbox 점검 | Codex 실행 구성(sandbox, 승인, plugin 비활성, 저장소 MCP 끄기) | R-31 |
| C-13 | `plugins/codex-security/scripts/workbench_db.py:3218-3259` `finding_remediation_result`, `:2405-2448` `assigned_remediation_context`, `:2731-2752` `get-scan` remediation 분기, `:2950-2967` `remediation_availability` | 모델이 보는 상태, assigned finding 문맥, 가용성 | R-13, R-20 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 사례는 실행하지 않았다. 해시와 ID는 조건으로 적는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-14, R-15, R-17 | `complete` scan, checkout이 scan의 revision, 열린 finding(occurrence `O`). 앱이 `request`(requestId `R`, actionToken `T`)를 만들고, 모델이 `set`(`expectedVersion:1`, `state:"generated"`, `patch:<완전한 unified diff>`)을 보낸다 | attempt가 `generated`, version 2, `pending_action`·claim 없음, `patch_path = artifacts/remediation/O/R/T.patch`, `patch_digest = sha256:<patch 바이트의 해시>`. scan 디렉터리에 patch 파일이 생기고 결과는 assigned finding 문맥이다 |
| T-02 | R-17 | T-01의 patch에 `GIT binary patch` 없이 binary 파일 변경 section(hunk 없음, 내용이 다른 blob ID)이 있다 | "The remediation patch omits file content. Generate a complete binary diff with Git's --binary option."로 거부, attempt와 파일 불변 |
| T-03 | R-16 | attempt가 `requested`인데 모델이 `state:"applied"`를 보낸다 | "Finding remediation cannot move from requested to applied."로 거부 |
| T-04 | R-16 | attempt가 `generated`이고 대기 작업이 없는데 `state:"applied"` | "Request apply before recording remediation state applied."로 거부 |
| T-05 | R-15 | `expectedVersion`이 현재 version보다 작다 | "This remediation request changed. Refresh it before recording an update."로 거부 |
| T-06 | R-15 | 다른 `actionToken`으로 `set` | "This remediation host request is owned by a different action token."로 거부 |
| T-07 | R-18 | `generated` attempt에서 `apply` 요청을 받았지만 작업 트리를 건드리지 않고 `state:"applied"`, `baseRevision:<base>` | "The selected checkout is unchanged; apply the reviewed patch before recording it as applied."로 거부 |
| T-08 | R-18 | patch를 적용한 뒤 patch 밖의 파일도 수정하고 `state:"applied"` | 복사본에서 patch를 되돌려도 `base_content_digest`와 다르므로 "The selected checkout contains changes outside the reviewed patch. Remove them before recording the patch as applied."로 거부 |
| T-09 | R-19 | `applied` 기록 후 작업 트리를 더 수정하고 `verify` 요청 → 모델이 `state:"verifying"` | "Working-tree contents changed. Regenerate the remediation patch against the current checkout."로 거부(이 검사는 `verify` 요청 시점에도 한 번 한다) |
| T-10 | R-19 | `verifying` attempt에서 `state:"verified"`에 `verificationSummary`가 없다 | "Verified remediation requires a verification summary."로 거부 |
| T-11 | R-20 | scan이 `failed`이거나 checkout의 HEAD가 scan 때의 revision이 아니다 | scan이 `failed`면 모든 remediation 명령이 "Remediation is available only for successfully completed scans."로 거부, HEAD가 다르면 context의 `remediationAvailable:false`와 이유 문구, `request`는 "Repository HEAD changed. Regenerate the remediation patch against the current checkout." |
| T-12 | R-20 | attempt가 `verified`이고 대기 작업이 없는 finding을 `already_fixed`로 닫는데 그 사이 작업 트리가 patch 적용 상태에서 바뀌었다 | triage 변경이 거부된다("Working-tree contents changed…"). 같은 finding을 `wont_fix`로 닫는 것은 이 digest 검사 대상이 아니다 |
| T-13 | R-27 | SDK `patch`에서 모델이 `{"status":"verified","changedFiles":[],"verificationReport":"ok","reason":null}`을 낸다 | "Finding patch returned an invalid result."(`verified`는 `changedFiles`가 비어 있을 수 없다) |
| T-14 | R-27 | 같은 호출에서 `{"status":"no_change","changedFiles":[],"verificationReport":"already validated by X","reason":null}` | `{ status:"no_change", changedFiles:[], verificationReport:"…", threadId, cost }`를 돌려준다. 저장소는 바뀌지 않았는지 코드는 확인하지 않는다 |
| T-15 | R-28 | `cs patch --scan latest`에서 모델이 finding `O1`에 `{"patches":[{"occurrenceId":"O1","status":"verified","files":["a.ts"],"verification":"tests pass"}]}`를 냈지만 작업 트리가 바뀌지 않았다 | 그 finding의 결과가 `failed("No patch was applied; 0 files changed.")`, 종료 코드 2 |
| T-16 | R-28 | 같은 명령에서 한 finding은 `verified`(파일 변경 있음), 다른 하나는 `blocked`(reason 있음) | `patches`에 둘이 그대로 담기고 종료 코드 1, `files`는 바뀐 파일 목록, `applied: true` |
| T-17 | R-30 | `cs verify-fix --scan S`에서 열린 finding 2개(`O1`, `O2`), 모델이 `{"results":[{"id":"O1","status":"fixed","evidence":"…"}]}`만 낸다 | "Codex did not return an evidence-backed verification result for every finding."로 실패, 종료 코드 2 |
| T-18 | R-30 | 결과가 `[{O1 fixed}, {O2 still_vulnerable}]` / `[{O1 fixed}, {O2 inconclusive}]` | 앞은 종료 코드 1, 뒤는 2. 기본 출력은 `FIXED O1: …`, `STILL_VULNERABLE O2: …` 줄이다 |
| T-19 | R-31 | `cs verify-fix`를 실행하는 저장소에 사용자가 구성한 MCP 서버 `x`와 같은 이름의 저장소 로컬 MCP 서버 `x`가 있다 | "Repository-local MCP server "x" overrides a configured integration; remove the repository override before verifying fixes."로 중단, 검증하지 않음 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

경로는 모두 `173483d7c658be7a512c93d9559bf01a05d5b196` 기준이다. 부재 주장의 검색 범위는 이 표 아래에 모았다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01~R-07 | C-01 `plugins/codex-security/skills/fix-finding/SKILL.md`: 목적 10-14, mode 16-20, contract 22-31, 구현 33-47, 검토 49-53, 출력 82-96, hard rules 98-105, 저장 8 | 지침 문장. `plugins/codex-security/references/scan-artifacts.md:114-117`(Fix Finding Paths) |
| R-08 | `plugins/codex-security/skills/fix-finding/SKILL.md:55-63`, `plugins/codex-security/scripts/workbench_target.py:249-256` `trusted_git_executable` | 지침 문장. 함수 존재만 확인 |
| R-09 | `plugins/codex-security/skills/fix-finding/SKILL.md:65-72` | 지침 문장 |
| R-10 | `plugins/codex-security/skills/fix-finding/SKILL.md:73-75` | 지침 문장 |
| R-11 | `plugins/codex-security/skills/fix-finding/SKILL.md:63, 76` | 지침 문장 |
| R-12 | `plugins/codex-security/skills/fix-finding/SKILL.md:78-80` | 지침 문장 |
| R-13 | `plugins/codex-security/mcp-app/server.ts:1348-1377`, `plugins/codex-security/scripts/workbench_db.py:2731-2752, 2405-2448` | `get_codex_security_scan_context`와 `get-scan`을 읽음. 이 분기가 owner·claim 검사를 건너뛴다는 점은 같은 분기 이후(2753)에 일반 경로가 따로 있는 구조에서 읽음 |
| R-14 | `plugins/codex-security/scripts/workbench_db.py:1982-2259`, `plugins/codex-security/scripts/workbench_remediation.py:694-710, 750-832`, `plugins/codex-security/mcp-app/server.ts:1675-1773` | `cancel_finding_remediation_request`의 분기는 코드 읽기. lease 상수는 `workbench_constants.py:27-29` |
| R-15 | `plugins/codex-security/scripts/workbench_db.py:2262-2402`, `plugins/codex-security/scripts/workbench_cli.py:418-431`, `plugins/codex-security/mcp-app/server.ts:418-446, 1775-1796` | SQL의 `CASE` 분기를 읽고 요약 |
| R-16 | `plugins/codex-security/scripts/workbench_remediation.py:713-747` | |
| R-17 | `plugins/codex-security/scripts/workbench_remediation.py:397-517, 575-691`, `plugins/codex-security/scripts/workbench_db.py:2567-2597` | `save_patch`의 Windows 재시도·archive 경합 분기는 구조만 읽음 |
| R-18 | `plugins/codex-security/scripts/workbench_db.py:2451-2541`, `plugins/codex-security/scripts/workbench_remediation.py:103-166` | `copy_git_worktree_files`, `directory_content_digest` 본문은 열지 않음 |
| R-19 | `plugins/codex-security/scripts/workbench_db.py:2290-2314, 2544-2564`, `plugins/codex-security/scripts/workbench_target.py:808-828` `remediation_checkout_snapshot` | |
| R-20 | `plugins/codex-security/scripts/workbench_remediation.py:50, 189-195`, `plugins/codex-security/scripts/workbench_db.py:3405, 2950-2967, 1907-1945, 1982-1988` | `remediation_state.require_available` 호출은 3405행에서 확인 |
| R-21~R-24 | C-02 `plugins/codex-security/skills/verify-fix/SKILL.md:8-52` | 지침 문장 |
| R-25 | `sdk/typescript/src/remediation.ts:26-143` | `static-finding-assessment.md`를 inline하는 점은 85-93행 |
| R-26 | `sdk/typescript/src/api.ts:1514-1721`, `sdk/typescript/src/api.ts:796` `SCAN_PERMISSION_PROFILE` | `#createSessionCodex`·`#prepareSession` 본문은 열지 않음 |
| R-27 | `sdk/typescript/src/api.ts:526-643, 1685-1694, 7795-7816`, `sdk/typescript/src/finding-prompt.ts:11-44` | |
| R-28 | `sdk/typescript/src/cli.ts:9410-9446, 9470-9641, 10342-10488, 7568-7678, 7679-7795` | 직접 입력 경로(7679-7795)는 `runSkill` 한 번과 파일 변경 검사 |
| R-29 | `sdk/typescript/src/finding-prompt.ts:11-44`, `sdk/typescript/src/codex-prompt.ts:3`, `sdk/typescript/src/remediation.ts:43-72` | |
| R-30 | `sdk/typescript/src/cli.ts:7210-7458`, `sdk/typescript/src/remediation.ts:145-168` | `FindingProgressPresenter`, Linear 가져오기, `--host`는 열지 않음 |
| R-31 | `sdk/typescript/src/cli.ts:10503-10900, 10905-11270` | `runCodex` 본문(프로세스 실행)은 열지 않음 |
| R-32 | 부재 주장 5 | 아래 검색 |
| R-33 | `sdk/typescript/src/cli.ts:575-580, 9725-10002, 10004-10019`, `sdk/typescript/src/patch-publication.ts:1-60` | `publishPatchBranch`(9676~)와 provider 본문은 열지 않음 |
| R-34 | 실행하지 않음 | |
| T-01~T-19 | 구현에서 도출. 각각 R-ID의 근거 줄 | |

부재 주장의 검색 범위(모두 기준 SHA):

1. "이 기능은 후보 ledger(S1)와 행 4~6의 도구를 읽지 않는다": `candidate_ledger`, `candidate-ledger`, `record_codex_security_candidate`, `record_candidate_attack_paths`, `list_codex_security_candidates`를 `plugins/codex-security/skills/fix-finding`, `plugins/codex-security/skills/verify-fix`, `plugins/codex-security/scripts/workbench_remediation.py`, `plugins/codex-security/scripts/workbench_db.py`의 remediation 함수, `sdk/typescript/src/remediation.ts`, `sdk/typescript/src/finding-prompt.ts`에서 검색했을 때 `fix-finding`·`verify-fix` 경로에는 없다. `workbench_db.py`에는 Deep 비용 한도 마무리용 ledger 읽기가 있지만 remediation 함수 밖이다. feature map 표는 선행을 4~6으로 제안했으나 이 기능의 입력은 완료 scan의 finding(S2)이다. 이 스펙이 `depends`에 [caller-modes.md](./caller-modes.md) 하나만 둔 이유다. 놓칠 가능성: 모델이 `fix-finding` 중 ledger 파일을 직접 읽는 것은 코드가 아니라 모델 행동이다(skill은 scan ledger를 언급하지 않는다).
2. "`fix_report.md`를 읽거나 쓰는 코드 없음": `fix_report`를 확장자 `ts`·`py`·`md`·`json`·`mts` 파일에서 검색했고(`node_modules`와 테스트 제외) `references/scan-artifacts.md:116` 한 곳뿐이다. 동적으로 조립된 경로는 놓칠 수 있다.
3. "SDK `patch`가 `changedFiles`를 실제 변경과 대조하지 않는다": `#patch`(`api.ts:1522-1721`)에 `git diff`·snapshot 호출이나 `changedFiles` 비교가 없고 결과를 그대로 `PatchResult`로 돌려준다. `cs patch`는 별도로 `changedPatchFiles`로 대조한다(R-28).
4. "SDK에 `verify-fix` 메서드가 없다": `verify-fix`·`verifyFix`·`verify_fix`를 `sdk/typescript/src`에서 검색했고 `cli.ts`, `cli-help.ts`, `operation-telemetry.ts`, `skill-authentication.ts`, `remediation.ts`, `hosted-remediation.ts`에만 나오며 `api.ts`의 `CodexSecurity` 클래스에는 `patch`와 `validate`만 있다(`fix-finding`은 1637행 한 곳). `package.json` `exports`는 열지 않았다.
5. "SDK·CLI가 workbench remediation 상태를 쓰지 않는다": `set-finding-remediation`, `request-finding-remediation`, `remediation_state`, `remediationState`를 `sdk/typescript/src`와 `plugins/codex-security/mcp-app`(비테스트 소스)에서 검색했다. SDK는 `cli.ts:9606` 한 곳(하이드레이트 키 목록), MCP는 `server.ts`의 도구 등록과 `workbench-client.ts:87-91`의 명령 허용 목록뿐이다. SDK가 workbench를 `runWorkbench`로 부르는 다른 명령 이름은 모두 열지 않았다.

### 2.2 코드 읽는 순서 [선택]

CLI 경로는 `cli.ts`의 `patch`(7460) → `runFindingPatches`(10342) → `runSkill`(10503) → `remediation.ts`의 `remediationPrompt` 순이고, `verify-fix`는 7210 → `verificationBatches` → `parseFindingVerifications`다. SDK API는 `api.ts`의 `#patch`(1522)에서 prompt와 `patchResponseSchema`를 본다. workbench 경로는 skill(`fix-finding/SKILL.md` 55-80) → `server.ts`의 `set_codex_security_finding_remediation` → `workbench_db.py`의 `set_finding_remediation`(2262) → `workbench_remediation.py`의 `require_transition`·`require_valid_patch` 순이다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 세션 기본 점검(2026-11-16). `python scripts/check.py codex-security`로 인용 줄의 존재를 확인하고(형식·위치 확인일 뿐), 고위험 R-ID 표본을 인용 줄과 검색으로 대조했다. 다른 스펙이 `depends`로 의존하지 않아 독립 검토 조건에는 해당하지 않으나, 미결정 U-01이 남아 `draft`로 둔다.
- 대조한 R-ID: R-32 및 부재 주장 4·5(`git grep`으로 `sdk/typescript/src/api.ts`에 `verifyFix`·`async verify` 메서드가 없고 SDK 소스에 `set-finding-remediation`·`finding_remediation` 문자열이 없음을 확인)
- 대조하지 않은 R-ID: 위를 제외한 전부. 특히 R-13~R-20(owner·claim, 전이표, patch 완전성·reverse apply digest), R-27·R-28·R-30(종료 코드·`verified` 거부), R-33(열지 않음)은 독립 검토 대상이다.
- 재구현: 미수행
