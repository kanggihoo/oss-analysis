---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
sources:
  - plugins/codex-security/skills/finding-discovery/SKILL.md
  - plugins/codex-security/skills/finding-discovery/agents/openai.yaml
  - plugins/codex-security/skills/security-diff-scan/SKILL.md
  - plugins/codex-security/references/artifact-storage.md
  - plugins/codex-security/references/scan-artifacts.md
  - plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts
  - plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts
  - plugins/codex-security/mcp-app/src/artifact-discovery.ts
  - plugins/codex-security/mcp-app/src/artifact-inventory.ts
  - plugins/codex-security/mcp-app/src/artifact-io.ts
  - plugins/codex-security/mcp-app/src/artifact-context.ts
  - plugins/codex-security/mcp-app/src/artifact-contracts.ts
  - plugins/codex-security/mcp-app/src/discovery-location-roles.ts
  - plugins/codex-security/mcp-app/src/record.ts
  - plugins/codex-security/mcp-app/src/workbench-arguments.ts
  - plugins/codex-security/mcp-app/src/helpers/normalize-candidates.ts
  - plugins/codex-security/mcp-app/src/helpers/resolve-security-md.ts
  - plugins/codex-security/mcp-app/src/deep-scan/artifact-contracts.ts
  - plugins/codex-security/mcp-app/helpers-main.ts
  - plugins/codex-security/mcp-app/server.ts
  - plugins/codex-security/mcp-app/package.json
  - plugins/codex-security/scripts/workbench_target.py
  - plugins/codex-security/scripts/workbench_db.py
  - plugins/codex-security/scripts/deep_scan_workbench.py
  - plugins/codex-security/scripts/workbench_saved_results.py
  - plugins/codex-security/schemas/definitions/discovery-candidate.schema.json
  - plugins/codex-security/schemas/definitions/artifact-common.schema.json
  - plugins/codex-security/schemas/tools/discovery-candidates.schema.json
  - plugins/codex-security/schemas/tools/review-items.schema.json
depends:
  - ./caller-modes.md
status: draft
---

# 후보 발견·정규화와 후보 ledger

> `finding-discovery` skill(지침)과 MCP 도구가 범위 안 소스에서 찾은 후보를 받아, 위치를 검증하고 병합해 안정적인 `candidate_id`를 붙인 뒤 scan 디렉터리의 후보 ledger(JSONL)에 쌓는다. 이 스펙이 공유 계약 S1(후보 ledger: 검증·공격 경로 단계가 같은 행에 필드를 덧붙이고 전체 행을 교체하는 계약)을 소유한다.

<!--
이 레포에는 정적 분석 코드가 없다. 후보를 "찾는" 판단은 모델이 SKILL.md를 따라 한다. R-ID 앞의 [지침]은 모델에게 주는 규칙(코드 확인 = 지침 문장을 읽었다)이고, [강제]는 코드가 검사하거나 만든다는 뜻이다. 모델이 지침을 따르는지는 R-23이 미확인으로 따로 묶는다.
용어: "후보"는 `candidate_ledger.jsonl`의 한 행. "compact diff"는 workbench가 소유한 diff scan에서 위 도구들을 쓰는 경로다(호출자 모드는 caller-modes.md).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 workbench가 소유한 diff scan(compact diff)이다. 순서는 이 순서다.

1. 부모 모델이 `prepare_codex_security_review_items`를 부른다. 서버가 helper `generate-in-scope-files`를 실행해 `artifacts/02_discovery/in_scope_files.txt`(변경 파일 목록)를 만들고 줄 수를 돌려준다(R-08).
2. 모델이 `list_codex_security_review_items`로 목록을 페이지 단위로 읽고, 각 파일을 `finding-discovery` 지침대로 검토해 후보를 모은다(R-01~R-06, R-09). 독립 검토는 worker에 나눌 수 있다(R-05).
3. 모델이 후보 전체를 `record_codex_security_discovery_candidates({ scanId, candidates })` 한 번으로 보낸다(R-10).
4. 서버가 scan context를 정하고, 목록 파일과 diff의 변경 파일 정보를 읽어 worker thread에서 후보를 정규화한다. 위치를 검사하고, 같은 (CWE, 위치, instance) 후보를 병합하고, `candidate-<해시 16자>` ID를 붙이고, 정렬한다(R-11~R-13).
5. 서버가 `artifacts/02_discovery/candidate_ledger.jsonl` 전체를 정규화된 행으로 교체하고 `{ operation: "replace", candidatesRecorded }`를 돌려준다. 중간에 실패하면 기존 ledger는 그대로다(R-14, R-15).
6. 모델이 `list_codex_security_candidates`로 읽어 후보 ID를 확인한다(R-16). 이후 [candidate-validation.md](./candidate-validation.md)가 각 행에 `validation`을, [attack-path-severity.md](./attack-path-severity.md)가 `attack_path`를 덧붙이며 매번 파일 전체를 교체한다(S1, R-18~R-22).

### 1.2 범위·통합 지점 [필수]
- 제공: (a) 후보를 만드는 모델 지침(증거 기준, 위치 역할, 병합 기준, 후보 필드), (b) 후보 정규화·병합·ID 부여·저장 도구와 읽기 도구, (c) S1 후보 ledger 계약(파일 위치, 행 스키마, 읽기·교체 규칙, 단계별 필드 소유), (d) 변경 파일 목록을 만드는 도구의 호출 계약(`prepare`·`list review items`).
- 이 skill이 쓰이는 곳: `finding-discovery`는 Standard scan과 Deep worker가 부르지 않는다(SKILL.md가 "coordinator의 자체 prompt를 쓴다"고 적었다, R-01). 쓰이는 곳은 세 가지다. 1) compact diff(이 스펙의 본문 경로, R-07~R-22). 2) 구형 standalone diff(compact 목록 없이, 파일 기반 worklist·receipt). 3) standalone 저장소 발견(후보와 coverage 한계를 반환만 한다). 호출자 모드와 diff scan 전체 순서는 [caller-modes.md](./caller-modes.md)와 diff 감사 스펙 몫이다.
- 제외(이유):
  - 후보 검증과 공격 경로·severity 판정: 후보 행에 덧붙는 필드의 쓰기 규칙은 각각 [candidate-validation.md](./candidate-validation.md)와 [attack-path-severity.md](./attack-path-severity.md)(행 5·6)가 정의한다. 이 스펙은 S1 공통 규칙까지만 쓴다.
  - 구형 standalone diff 경로(`skills/security-scan/references/scan-artifacts-and-ledger.md`의 `rank_input.jsonl`·`work_ledger.jsonl`·후보별 `candidate_ledger.jsonl` receipt 등): 이 SHA에서 compact diff와 별개의 파일 기반 흐름이고 이번 범위(검증 skill의 도구 경로)가 아니다. 경계만 R-01에 적었다. 이 경로의 receipt 파일은 같은 이름 `candidate_ledger.jsonl`이어도 `<findings_dir>/<candidate_id>/` 아래의 다른 파일이다(코드가 읽지 않는다).
  - 변경 파일 목록을 만드는 helper `generate-in-scope-files`(`generate-inventory.ts`)의 본문과 `make-diff-rank-input`(행 10): 호출 계약만 R-08에 쓴다.
  - Deep scan의 ledger 생산: Deep는 dedup reducer worker가 같은 경로의 `candidate_ledger.jsonl`을 게시한다(`deep_scan_workbench.py`의 `canonical_discovery_artifacts`·`recover_candidate_ledger_publication`). 그 생산·복구 규칙은 행 7 몫이다. 이 스펙의 읽기 규칙(R-16, R-19, R-20)은 Deep ledger에도 같은 코드로 적용된다.
  - 스캔 초안·확정(행 9). 후보 ledger를 최종 finding으로 옮기는 일은 모델이 `record_codex_security_scan_draft`로 한다. 예외는 Deep 비용 한도 소진 마무리로, 이때는 Python이 ledger를 읽어 coverage를 만든다(R-23).
  - `SECURITY.md` 해석(`resolve-security-md`), threat model(행 8), 호출자 모드(행 1).
- 외부 의존·선행 계약: [caller-modes.md](./caller-modes.md)의 scan 등록·소유 증명(R-28·R-29). 서버는 도구 호출마다 workbench `get-scan`으로 scan을 다시 읽는다(R-07). 후보 정규화는 MCP 빌드 산출물 `mcp/helpers.mjs`를 worker thread로 실행한다(레포에 추적되지 않는 생성물, 확인 한계). 후보 위치 검증에는 diff의 변경 파일 정보(Python `workbench_target.candidate_source_lines`)와 git이 필요하다.
- 소유 상태·부작용: `<scanDir>/artifacts/02_discovery/in_scope_files.txt`(prepare가 씀), `<scanDir>/artifacts/02_discovery/candidate_ledger.jsonl`(record가 전체 교체, 이후 단계도 전체 교체). 임시 파일 `.<uuid>.tmp`는 같은 디렉터리에서 만들었다가 rename 또는 삭제된다. `artifacts`·`02_discovery` 디렉터리가 없으면 mode `0700`으로 만든다.

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 MCP 도구

외부 계약이라 이름과 필드는 원문 그대로다. 입력 스키마의 원본은 TypeScript zod 정의(C-01, C-02)이고, `plugins/codex-security/schemas/`의 JSON 파일은 그 정의에서 생성한 호환용 내보내기다(`artifact-contracts.ts` 주석, R-10). 모든 도구는 model 전용(`_meta.ui.visibility = ["model"]`)이다.

| 도구 | 입력 | 결과 | 허용 scan |
|---|---|---|---|
| `prepare_codex_security_review_items` | `{ scanId(uuid), handoffClaimToken? }` | `{ reviewItemsTotal }` | diff만 |
| `list_codex_security_review_items` | `{ scanId(uuid), handoffClaimToken?, cursor?, limit? }` | `{ items: [{ path }], nextCursor? }` | diff 또는 Deep |
| `record_codex_security_discovery_candidates` | `{ scanId(비어 있지 않은 문자열), candidates: RawCandidate[] }` | `{ operation: "replace", candidatesRecorded }` | diff만 |
| `list_codex_security_candidates` | `{ scanId(비어 있지 않은 문자열), cursor?, limit? }` | `{ rows: LedgerRow[], nextCursor? }` | diff 또는 Deep |

- `cursor`는 `^(0|[1-9][0-9]*)$` 문자열, `limit`은 1~1000 정수이고 생략하면 200이다(C-18). 위 입력은 모두 strict 객체라 모르는 키를 거부한다. `handoffClaimToken`은 `prepare`와 `list review items`의 스키마에만 있다(R-07).
- `RawCandidate`(모델이 내는 후보): `cwe_ids`(문자열 배열, 빈 배열 가능), `locations`(1개 이상), `summary`, `evidence`, `context?`, `instance?`. `locations[]`는 `path`·`start_line`·`end_line?`·`role`이고 `role`은 7가지(`entrypoint`, `entrypoint/wrapper`, `source`, `root_control`, `sink`, `concrete_implementation`, `evidence`, C-03) 중 하나다. 텍스트 필드는 공백이 아닌 글자가 하나 이상 있어야 한다. 정확한 정의는 C-01.
- `LedgerRow`: 정규화된 후보 필드(아래 1.3.2)에 이후 단계 필드가 붙은 객체. 읽기 스키마는 후보 필드만 검사하고 나머지 키는 그대로 돌려준다(R-16).

#### 1.3.2 S1 후보 ledger 계약

| 항목 | 내용 |
|---|---|
| 위치 | `<scanDir>/artifacts/02_discovery/candidate_ledger.jsonl`. 고정 구성요소 `["artifacts","02_discovery","candidate_ledger.jsonl"]`(모델 입력으로 바꿀 수 없다) |
| 형식 | JSONL. 한 줄이 JSON 객체 하나(한 후보). 행 순서에 의미가 있고 모든 단계가 보존한다 |
| 행 키 | `candidate_id`(scan 안에서 유일, 아래 R-13) |
| 1단계 필드(이 스펙, record) | `candidate_id`, `cwe_ids`(`CWE-<n>` 문자열 배열), `locations`(`path`, `start_line`, `end_line`, `role`), `summary`, `evidence`, `context?`, `instance?` |
| 2단계 필드([candidate-validation.md](./candidate-validation.md)) | `validation` 객체. 모든 행에 정확히 하나 |
| 3단계 필드([attack-path-severity.md](./attack-path-severity.md)) | `attack_path` 객체. `validation.disposition`이 `reportable`·`deferred`인 행만 대상 |
| 쓰기 방식 | 각 단계는 파일 전체를 읽고, 행에 자기 필드를 덧붙이고, 전체 행을 임시 파일에 쓴 뒤 rename으로 교체한다. 부분 추가·append는 없다(R-21) |
| 읽기 방식 | JSONL을 줄 단위로 JSON 파싱하고 행 스키마를 검사한다. 오류는 행 번호와 함께 던진다(R-19, R-20) |

#### 1.3.3 입력 목록 파일

`in_scope_files.txt`는 한 줄에 저장소 상대 경로 하나이고 줄 구분은 `\n` 또는 `\r\n`이다. `prepare`가 만들고 `list review items`와 후보 정규화가 읽는다. 생성 규칙은 행 10(helper)이고 이 스펙은 형식과 소비 규칙(R-09, R-12)만 쓴다.

### 1.4 행동 규칙과 남은 질문 [필수]

#### 모델 지침 (finding-discovery)

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [지침] 워크플로 선택 | Standard scan과 Deep worker는 이 skill이 아니라 coordinator의 자체 prompt를 쓴다. 실행 중인 compact diff는 `list_codex_security_review_items`로 받은 목록의 모든 변경 파일을 검토하고 후보를 `record_codex_security_discovery_candidates`로 한 번에 기록한다. 이때 ranked worklist, 후보별 ledger, receipt, discovery report를 만들지 않는다. compact 목록이 없는 standalone diff는 구형 문서(`scan-artifacts-and-ledger.md`)의 worklist·receipt 절차를 쓴다. standalone 저장소 발견은 증거 기준을 적용해 후보와 coverage 한계를 반환하고, scan을 시작하거나 diff worklist 파이프라인을 돌리지 않는다. diff는 삭제된 파일도 baseline revision에서 본다 | 코드 확인 (지침 문장) |
| R-02 | [지침] 추적·통제 | 공격자 입력(또는 권한 있는 연산)에서 가장 가까운 관련 통제를 거쳐 sink와 보안 영향까지 추적하고, 통제가 없거나 우회되거나 잘못된 값·경계에 적용된 이유를 설명한다. runtime 도달 가능성과 배포 가정을 확인하고, 유효한 guard와 containment는 counterevidence로 기록한다. 안전한 형제 구현은 이 후보 경로의 안전 증거가 아니다 | 코드 확인 (지침 문장) |
| R-03 | [지침] 위치·인스턴스·병합 | root-control 위치와 entrypoint, wrapper, concrete implementation, sink를 보존한다. 여러 구현을 아우르는 claim이면 구현을 각각 검사하고 "모두 영향받는다"고 단정하지 않는다. 독립적으로 도달 가능한 취약 인스턴스는 따로 남긴다. 같은 source·control·sink·impact의 중복 관찰은 병합하고, 병합하면 영향받는 모든 위치와 원래 후보 ID를 보존한다 | 코드 확인 (지침 문장). 코드가 후보를 병합하는 기준은 R-13이 따로 정한다 |
| R-04 | [지침] seed와 lead | 사용자·advisory seed는 정확한 source와 control까지 따라가 근거(지지·반증·미해결)를 기록한다. 같은 계열의 인근 이슈가 seed를 닫지 않는다. 승인된 자료만 쓰고 advisory 링크를 허락 없이 가져오지 않는다. crash·위험한 API·선택 기능·누락된 검사는 그 자체로 finding이 아니라 lead다. 실행 가능한 재현이 없어도 증명 공백을 명시한 그럴듯한 후보는 증거를 지어내거나 버리지 않고 validation으로 넘긴다 | 코드 확인 (지침 문장) |
| R-05 | [지침] 병렬·phase 경계 | 독립 검토 배정은 가용 worker에 나누고(target, scope, 정책·모델, 요구 결과 필드를 준다) 부모는 배정되지 않은 일을 검토하고 중복을 조정한다. discovery 안에서 validation이나 attack-path를 반복하지 않는다. 최종 severity는 정하지 않는다. 배정된 소스 검토와 구체적 후속 조사가 정리되면 끝내고 미완료는 솔직히 기록한다. 후보가 없으면 실제 검토 범위와 한계를 반환한다 | 코드 확인 (지침 문장) |
| R-06 | [지침] 후보 출력 | 후보마다 안정적인 ID·제목(seed·ledger ID와 advisory 참조 보존), 파일·줄 위치와 역할 라벨(`entrypoint/wrapper`, `root_control`, `sink`, `concrete_implementation`), 공격자 제어 source·가장 가까운 통제·sink·영향과 그 근거, counterevidence·배포 전제·미해결 질문·validation이 확인할 것, CWE ID(없으면 빈 목록)를 보존한다. repository·scoped-path 인스턴스는 호출자가 요구하면 instance key `<family>:<file>:<line>`을 쓰고, diff finding은 변경과 겹치는 곳만 `relevant_lines`를 쓴다. compact 도구가 실제로 받는 필드는 1.3.1이고, 지침 필드 중 도구에 대응 필드가 없는 것(안정 ID 입력, `relevant_lines`, counterevidence 등 전용 필드)은 R-10·R-12와 U-01이 다룬다 | 코드 확인 (지침 문장) |

#### compact diff 도구 [강제]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-07 | [강제] 네 도구의 scan context | 서버는 호출마다 workbench `get-scan`(scanId와 호출 thread ID)으로 scan을 읽는다. thread ID를 못 얻으면 빈 문자열을 넘긴다. scan이 `running`이 아니면 "…is not running; its artifacts cannot be modified."로 거부한다. claim token은 caller-modes R-28과 같은 규칙(입력 token ?? 서버 캐시 token)이다. 이 네 도구 중 입력 스키마에 `handoffClaimToken`이 있는 것은 `prepare`·`list review items`뿐이라, `record`·`list candidates`는 서버 캐시의 token만 쓴다. scan mode가 `diff`·`deep`이 아니면 "This operation is only available for Deep or diff scans.", `prepare`·`record`는 mode가 `diff`가 아니면 "This operation is only available for diff scans."로 거부한다. owner 검사는 caller-modes R-29(`get-scan` 안)가 한다. 결과 객체는 JSON 텍스트와 구조화 결과로 돌려주고, 문자열에 짝 없는 surrogate가 있으면 텍스트만 돌려준다 | 코드 확인. token 캐시가 비는 서버 재시작 뒤 claim token이 있는 scan에서 `record`·`list candidates`를 못 쓴다는 점은 추론 |
| R-08 | [강제] `prepare_codex_security_review_items` | 컨텍스트 layout이 `scan`이어야 하고("only a parent scan can prepare its shared inventory."), plugin 루트가 묶여 있어야 한다. 서버는 helper `generate-in-scope-files`를 `--repo=<repoRoot> --scope=<scope, 없으면 "."> --out=<in_scope_files.txt 경로>`로 실행한다. diff scan이면 scan context의 `diffTarget`이 필요하다(없으면 "the diff scan has no authoritative change set."). `diffTarget.kind`가 `working_tree`·`commit`·`range`이고 `baseRevision`·`headRevision`이 비어 있지 않은 문자열이어야 하며(아니면 "invalid authoritative change set."), `--diff-base --diff-head`와 `--diff-mode=local-patch`(`working_tree`) 또는 `revisions`(`commit`, `range`)를 붙인다. 인자에 NUL이 있으면 거부한다. helper가 0이 아닌 코드로 끝나면 stderr(없으면 종료 상태)를 담아 "review_items: the scan inventory helper failed: …"를 던진다. 성공하면 만든 파일을 다시 읽어 검증한 뒤 줄 수를 `reviewItemsTotal`로 돌려준다. helper가 목록에 무엇을 넣는지(변경 파일, 삭제 파일, 무시 규칙)는 행 10이다 | 코드 확인 (helper 본문은 열지 않음) |
| R-09 | [강제] `list_codex_security_review_items` | 목록 파일을 `\r?\n`으로 나누고, 빈 줄을 건너뛰고, 각 줄을 `{ path }`로 검사한다. 경로는 상대 경로(`./` 접두는 허용)여야 하고 절대 경로·드라이브·역슬래시·`.`/`..` 구성요소·`//`·제어 문자·끝 `/`가 있거나 4096자를 넘으면 "review_items: inventory row N has an unsafe repository path…"로 거부한다(N은 빈 줄을 포함한 1부터의 줄 번호). 결과는 `{ items, nextCursor? }`다. 파일이 없으면 "review_items: the requested artifact is unavailable."이다. cursor가 행 수보다 크면 "review_items: cursor is outside the available rows."이다 | 코드 확인 |
| R-10 | [강제] `record_codex_security_discovery_candidates` 입력 | 도구 등록부가 입력을 strict zod 스키마로 먼저 검사한다. 후보 키는 `cwe_ids`·`locations`·`summary`·`evidence`·`context`·`instance`뿐이고 그 밖의 키는 `candidate_id`·`relevant_lines` 포함 거부된다. `cwe_ids` 원소는 `^\s*CWE-0*[1-9][0-9]*\s*$`(대소문자 무시) 문자열이고, `locations`는 1개 이상이다. `candidates: []`도 허용된다 | 코드 확인 (거부 메시지의 형식은 MCP 등록부 몫이라 열지 않음) |
| R-11 | [강제] `record` 전처리와 diff 소스 | 순서: (1) context(R-07). (2) `in_scope_files.txt`가 있어야 한다("discovery review inventory: the requested artifact is unavailable."), 즉 `prepare`가 먼저 실행돼야 한다. (3) 후보 ledger 경로를 정한다(없는 상위 디렉터리는 만든다). (4) diff scan이면 변경 파일 소스 맵을 만든다. `diffTarget`이 R-08과 같은 조건이 아니면 "discovery candidates: the diff scan has no authoritative change set."이다. 목록 파일 경로들과 후보 위치 경로들을 Python `candidate_source_lines`에 넘겨 경로별 소스(C-11)를 받는다. 후보 위치 경로가 안전한 상대 경로가 아니면 "candidate input row N: …"로 거부한다. (5) 정규화를 worker thread에서 실행한다(MCP 요청을 막지 않으려는 것이 코드 주석의 이유) | 코드 확인 |
| R-12 | [강제] 후보 정규화 규칙(후보 하나) | 순서와 오류는 C-05~C-09. 요약: 허용 필드 밖 키는 "unsupported fields …"이다. `cwe_ids`는 `CWE-<양의 정수>`로 정규화(앞의 0 제거), 중복 제거, 숫자 순 정렬. `summary`·`evidence`는 앞뒤 공백을 자른 비어 있지 않은 문자열, `context`·`instance`는 있으면 같은 규칙. `locations`는 비어 있지 않은 배열이고 각 항목은 알려진 키만, `path`는 저장소 상대 경로(절대·`..`·NUL 불가)이며 일반 파일이어야 한다. `end_line` 생략은 `start_line`과 같다. 줄 범위는 파일 줄 수 안이어야 한다("line range a-b exceeds <path>:<count>"). `role`은 7가지 중 하나다. 완전히 같은 위치 항목은 하나로 합치고 (role 순서, path, start_line, end_line)으로 정렬한다. 적어도 한 위치가 목록 파일(in-scope)에 있어야 한다("locations: expected at least one in-scope file"). 다른 위치는 저장소 안의 일반 파일이면 목록 밖이어도 된다. 경로는 실제 경로로 해석한 결과가 저장소 루트 안이어야 한다(symlink가 밖을 가리키면 거부, 추론). 목록 파일 해석(`\r` 처리 포함)은 C-07이다. diff scan은 목록에 없는 삭제 파일 같은 누락(ENOENT)을 허용하되 저장소 밖으로 나가는 경로는 거부한다. 소스 읽기는 변경 파일 소스 맵(R-11)이 정한 revision(삭제된 파일은 base, `working_tree`가 아닌 diff의 나머지는 head, `working_tree`에서 삭제되지 않은 파일은 변경 여부와 관계없이 작업 트리에서 읽는다. `workbench_target.py:628-630`이 `local and not deleted`인 파일 전부를 소스 맵에서 건너뛰어 revision 대신 작업 트리를 쓰게 한다. diff-audit 작성자 지적, 2026-11-16 메인이 해당 줄을 열어 확인)을 쓴다 | 코드 확인. 경로 해석 helper(`resolvedPath`, Windows 파일 API)는 열지 않음(추론) |
| R-13 | [강제] 병합·ID·정렬 | 정규화된 후보를 키 `stableJson({ cwe_ids, locations, instance: instance ?? null })`로 묶는다. 같은 키의 후보는 한 행이 된다. 키가 다르면(CWE, 위치 집합, instance 중 하나라도 다르면) 병합하지 않는다. 행의 `candidate_id`는 `candidate-` + 키 문자열의 SHA-256 앞 16자리 16진수다. `summary`·`evidence`·`context`는 묶음 안 고유 값을 문자열 순서(UTF-16 코드 단위)로 정렬해 `\n`으로 이은 것이고, `context`는 결과가 빈 문자열이면 넣지 않는다. 그 밖의 필드는 묶음 첫 후보(입력 순서)의 값이다. 행은 키 문자열의 사전 순으로 정렬한다(입력 순서가 아니다). 같은 입력이면 같은 ID가 나온다 | 코드 확인 |
| R-14 | [강제] 저장과 재호출 | 정규화 결과를 `stableJson(행)` + `\n`을 이은 문자열로 ledger에 전체 교체한다(후보가 0개면 빈 파일). 필드 순서는 알파벳순이고 아는 필드만 남는다(C-05). `record`는 기존 ledger를 읽지 않으므로, 이미 `validation`·`attack_path`가 붙은 ledger에 다시 `record`를 부르면 모든 행이 1단계 필드만 가진 새 행으로 바뀐다(이전 단계 결과가 지워진다). 같은 후보 입력이면 같은 `candidate_id`가 다시 나온다. 결과 `candidatesRecorded`는 병합 후 행 수다 | 코드 확인. "기존 ledger를 읽지 않는다"는 2.1 부재 주장 1 |
| R-15 | [강제] 실패 시 상태 | 후보 하나라도 정규화에 실패하면 "discovery candidates: candidate input row N: <오류>"를 던지고(N은 입력 배열의 1부터의 위치) ledger는 바뀌지 않는다. worker가 오류를 내면 그 오류를, 메시지 없이 끝나면 "Candidate normalizer exited with code N."을 던진다. 임시 파일 쓰기·rename이 실패하면 임시 파일을 지우고 오류를 던지며 기존 ledger는 그대로다 | 코드 확인 |
| R-16 | [강제] `list_codex_security_candidates` | ledger를 읽어 `{ rows, nextCursor? }`로 돌려준다(`cursor`는 행 인덱스 문자열, 기본 `limit` 200). 행은 후보 필드가 스키마(`candidate_id` 형식, `cwe_ids` `CWE-<n>`, `locations` 1개 이상과 `end_line` 필수 등)에 맞아야 하고, 그 밖의 키(`validation`, `attack_path`)는 보존해서 돌려준다. ledger가 없으면 "discovery candidates: the requested artifact is unavailable."이고, 줄 오류는 R-19, cursor가 행 수보다 크면 "discovery candidates: cursor is outside the available rows."이다. scan이 `running`일 때만 읽을 수 있다(R-07) | 코드 확인 |
| R-17 | [강제] helper `normalize-candidates`(CLI) | `launch_codex_security_mcp --helper normalize-candidates --input PATH [PATH ...] --out PATH --repo-root PATH --in-scope-files PATH [--allow-missing-in-scope]`. 입력 JSONL 파일들을 경로 기준으로 중복 제거·정렬해 줄마다 JSON을 읽어 R-12·R-13의 같은 정규화기(`sources` 없음)에 넣고, `--out`에 임시 파일 + rename으로 쓴다. `--out`이 입력이나 `--in-scope-files`와 같으면 거부한다. 성공은 종료 코드 0과 "Combined N candidate rows into M rows in <out>", 실패는 stderr `normalize_candidates: <메시지>`와 종료 코드 2다. 이 SHA에서 skill·reference·SDK 문서는 이 helper를 부르지 않는다(구형 흐름이 남긴 CLI로 읽힌다, 추론) | 코드 확인 (호출처 없음은 2.1 부재 주장 2) |

#### S1 후보 ledger 공통 규칙

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-18 | [강제] ledger 경로 해석 | 읽기는 scan 루트에서 시작해 각 구성요소를 `lstat`으로 확인한다(중간은 디렉터리, 마지막은 일반 파일, symlink는 통과하지 못한다). 없으면 "<label>: the requested artifact is unavailable.", 형식이 다르면 "…is not a safe regular file.", 실제 경로가 scan 루트 밖이면 "…escaped its bound context."다. 쓰기 대상은 중간 디렉터리를 mode `0700`으로 만들고 기존 대상이 일반 파일이 아니면 거부한다. 구성요소는 코드 상수이고 `/`·`\`·NUL·`.`·`..`을 가질 수 없다 | 코드 확인 |
| R-19 | [강제] JSONL 읽기 | 파일을 UTF-8로 읽고 `\r?\n`으로 나눈다. 공백뿐인 줄은 건너뛴다. 줄이 JSON이 아니면 "<label>: row N is not valid JSON.", JSON이 객체가 아니면(배열·null 포함) "<label>: row N must be a JSON object.", 행 스키마에 안 맞으면 "<label>: row N does not match its artifact schema: <첫 이슈 경로: 메시지>"를 던진다. N은 빈 줄을 포함한 1부터의 줄 번호다. 한 줄이라도 오류면 읽기 전체가 실패한다(부분 결과 없음) | 코드 확인 |
| R-20 | [강제] 이후 단계가 읽는 ledger | 검증·공격 경로 도구는 ledger를 `candidateSchemaV1`을 `passthrough`한 스키마(C-04)로 읽는다. 후보 필드는 엄격하게(`candidate_id` 형식, `cwe_ids` `^CWE-[1-9]\d*$`, `locations` 1개 이상의 4필드와 `end_line >= start_line`, `summary`·`evidence` 비어 있지 않음) 검사하고 추가 키는 통과시킨다(zod 4의 `passthrough`는 strict를 풀어 추가 키를 허용한다, 추론). 같은 `candidate_id`가 두 행이면 "<라벨> repeats candidate X."(라벨은 검증 "Compact candidate ledger", 공격 경로 "Candidate ledger")로 거부한다. `candidate_id` 순서는 파일 행 순서로 보존한다 | 코드 확인 (`passthrough` 의미는 라이브러리 지식이라 추론) |
| R-21 | [강제] 전체 교체 쓰기 | 쓰기는 같은 디렉터리의 `.<uuid>.tmp`를 mode `0600`으로 `wx` 생성해 내용을 쓰고, rename으로 대상을 교체한다. Windows에서 rename이 EPERM·EBUSY·EACCES로 실패하면 10·25·50·100·200·400ms 간격으로 같은 rename을 재시도한다. 쓰기·rename이 실패하면 임시 파일을 지우고 오류를 던지며 이전 파일은 보이는 채로 남는다. 후속 단계(`replaceArtifactJsonl`)는 행을 `JSON.stringify` + `\n`으로 쓰고 행이 0개면 빈 파일이다. 즉 읽는 쪽이 보는 파일은 항상 이전 완전본 또는 새 완전본이다. 이 코드 안에는 ledger를 읽고 쓰는 구간의 잠금이 없다(두 도구를 동시에 부르면 한쪽 변경이 덮일 수 있다, 추론) | 코드 확인. 동시 호출은 추론(확인 한계) |
| R-22 | [강제] 단계 쓰기의 공통 규칙 | 검증·공격 경로 도구는 (1) scan 컨텍스트의 layout이 `scan`이어야 하고("…requires a scan-bound artifact context."), (2) ledger를 읽고, (3) 입력의 후보 ID를 검사하고, (4) 행마다 자기 필드 객체를 통째로 대입(필드 병합 없음)하고, (5) 행 순서를 그대로 둔 채 전체 행을 교체한다. 다른 단계의 필드는 지우지도 검사하지도 않는다. 단계별 입력 검사(누락·중복·모르는 후보·대상 행)와 결과는 R-ID가 각각 [candidate-validation.md](./candidate-validation.md), [attack-path-severity.md](./attack-path-severity.md)에 있다. layout `worker`는 `get-scan` 기반 컨텍스트(layout은 항상 `scan`)에서 만들어지지 않으므로 이 검사에 걸리는 경로는 이 SHA의 도구에서 찾지 못했다 | 코드 확인 (layout 부재 주장은 2.1 부재 주장 3) |
| R-23 | [강제] ledger의 다른 소비자 / [강제 없음] 최종 결과와의 연결 / 모델 준수 | 이 SHA에서 ledger 파일을 읽는 코드는 위 TypeScript 도구들, Deep dedup 게시 복구(`recover_candidate_ledger_publication`), 그리고 Deep 비용 한도 소진 마무리(`complete-budget-exhausted-scan`)뿐이다. 마지막은 Python이 ledger를 따로 읽고(TypeScript 스키마를 쓰지 않는다) 행이 객체이고, `candidate_id`가 유효·유일하고, `summary`·`evidence`가 비어 있지 않고, `locations`가 비어 있지 않으며 경로가 저장소 상대 POSIX 경로이고, 적어도 한 위치가 `in_scope_files.txt`(앞의 `./` 제거) 안에 있는지 확인한다(아니면 "Canonical Deep Scan candidate ledger contains an invalid candidate." 등으로 거부). 그리고 이미 초안의 finding·`deferred`에 없는 후보마다 coverage surface(`candidate-<id>`)를 만든다. surface의 `disposition`은 `validation.disposition`이나 `attack_path.decision`이 `deferred`면 `needs_follow_up`, 아니면 `validation.disposition`이 `not_applicable`이면 `not_applicable`, 아니면 `validation.disposition`이 `suppressed`이거나 `attack_path.decision`이 `ignore`면 `rejected`, 그 밖에는 `needs_follow_up`이다. `needs_follow_up` 후보는 `reviewState.deferred`에도 넣는다. 초안(`record_codex_security_scan_draft`)·일반 확정 코드는 ledger 파일을 읽지 않는다. 후보가 최종 finding·`reviewState`로 옮겨졌는지, 지침 R-01~R-06을 모델이 따랐는지는 코드가 검사하지 않고 실행하지 않아 미확인이다 | 코드 확인(소비자 목록과 Python 매핑, 2.1 부재 주장 4) / 미확인(모델 준수). 이 매핑의 본문은 이 마무리 경로에서만 읽었고 호출 조건(SDK 소유 Deep, 비용 초과)은 caller-modes R-21 |

- 불변식:
  - `record`가 성공하면 ledger 모든 행의 `candidate_id`는 유일하고 행의 후보 필드는 정규화 결과다(R-13, R-14).
  - 어떤 단계의 쓰기가 성공하면 파일은 이전 완전본 아니면 새 완전본이다(R-21).
  - `validation`·`attack_path`가 있는 행은 `record`를 다시 부르지 않는 한 행 순서와 1단계 필드가 바뀌지 않는다(R-22).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-06, R-10, R-12 | 지침이 요구하는 후보 내용 중 compact 도구에 전용 필드가 없는 것(counterevidence, 배포 전제, 미해결 질문, validation이 확인할 것, source·control·sink 분해, 입력으로 지정하는 안정 ID, `relevant_lines`)을 모델이 `summary`·`evidence`·`context` 중 어디에 어떻게 담는가. 코드는 `relevant_lines`·`candidate_id` 입력을 거부한다 | 이 지침을 따르는 prompt를 재구현하면 필드 매핑을 정해야 한다. 코드 계약(1.3.1)은 이 점에서 지침과 어긋난다 | 실제 scan 산출물 `candidate_ledger.jsonl`이나 세션 기록. 레포의 `evals/`·테스트 fixture를 열면 예시가 있을 수 있으나 열지 않았다 |
| U-02 | R-01, R-06 | standalone 저장소 발견이 "caller의 structured candidate contract"로 반환할 형식은 무엇인가. SKILL.md는 호출자 몫으로만 둔다 | standalone 경로를 구현하면 반환 형식을 정해야 한다 | standalone 호출자(사용자 prompt 또는 SDK) 문서. 이 레포에서 호출 지점을 찾지 못했다 |

- 확인 한계:
  - 실행하지 않았다(MCP 서버, helper, Python, git). 오류 문구는 소스에서 옮겼고 실제 출력은 보지 않았다. MCP 등록부가 입력 스키마 위반을 내는 메시지 형식은 외부 라이브러리 몫이다.
  - 후보 정규화는 빌드 산출물 `mcp/helpers.mjs`로 실행된다. 이 파일은 레포에 추적되지 않아 열지 않았고, 소스 `helpers-main.ts`가 `workerData`로 `normalizeCandidateBatch`를 부르는 것까지만 확인했다.
  - `generate-inventory.ts`(목록 생성), `git_changed_paths`(Python), 경로 해석 helper(`resolve-security-md.ts`의 `resolvedPath`·`windowsFiles`·`windowsRelativePath`, `posix-path.ts`, `native/windows-files.mjs`) 본문은 열지 않았다. 이 때문에 "무엇이 변경 파일인가"와 symlink·Windows 경로 해석의 세부는 행 10과 미확인이다.
  - 동시에 두 도구를 부를 때의 동작은 코드에서 잠금을 못 찾은 것이 전부다. MCP 서버가 요청을 직렬화하는지는 확인하지 않았다.

### 1.5 필수 코드 참조 [필수]

기준은 frontmatter SHA다. 라이선스는 Apache-2.0(overview 1절)이라 인용을 막지 않는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `plugins/codex-security/mcp-app/src/artifact-contracts.ts:41-93` `candidateId`·`page`·`cweId`·`locationRole`·`rawDiscoveryLocation`·`normalizedDiscoveryLocation`·`rawDiscoveryCandidate`·`discoveryCandidate`·`recordDiscoveryCandidatesInput` | 후보 입력·정규화 결과·읽기용 후보의 zod 스키마(필드, 정규식, 필수·선택, strict와 loose) | R-10, R-16 |
| C-02 | `plugins/codex-security/mcp-app/src/artifact-contracts.ts:409-419, 449-455` `artifactSchemaDocuments` | 도구 입력 스키마(`scanId` 형식, `candidates`, 페이지) | R-09, R-10 |
| C-03 | `plugins/codex-security/mcp-app/src/discovery-location-roles.ts:1-9` `discoveryLocationRoles` | 위치 역할 7가지와 정렬에 쓰는 순서 | R-12 |
| C-04 | `plugins/codex-security/mcp-app/src/deep-scan/artifact-contracts.ts:1-34` `candidateSchemaV1` | ledger 행의 엄격한 후보 스키마(이후 단계가 `passthrough`로 읽는다) | R-20 |
| C-05 | `plugins/codex-security/mcp-app/src/helpers/normalize-candidates.ts:30-47` `jsonFields`·`stableJson` | 행·키 직렬화의 키 허용 목록과 알파벳 순서 | R-13, R-14 |
| C-06 | `plugins/codex-security/mcp-app/src/helpers/normalize-candidates.ts:84-122` `candidateRelativePath`·`relativeFile` | 후보 경로 검사와 소스 맵 사용(삭제·누락·not_file 오류) | R-12 |
| C-07 | `plugins/codex-security/mcp-app/src/helpers/normalize-candidates.ts:124-211` `readScope` | 목록 파일 해석: `\r` 줄 끝 모호성 판정과 누락 허용 | R-12 |
| C-08 | `plugins/codex-security/mcp-app/src/helpers/normalize-candidates.ts:213-365` `textField`·`cweIds`·`positiveLine`·`normalizeLocations`·`normalizeCandidate`·`combine` | 필드 정규화, 위치 정렬, 후보 병합, ID 부여 | R-12, R-13 |
| C-09 | `plugins/codex-security/mcp-app/src/helpers/normalize-candidates.ts:367-428` `createCandidateNormalizer`·`normalizeCandidateBatch` | 묶음 키, 입력 위치 번호를 단 오류 | R-13, R-15 |
| C-10 | `plugins/codex-security/mcp-app/src/helpers/normalize-candidates.ts:430-562` `argumentsFor`·`normalizeCandidatesCommand` | helper CLI의 옵션·종료 코드·임시 파일 교체 | R-17 |
| C-11 | `plugins/codex-security/scripts/workbench_target.py:588-664` `candidate_source_lines` | diff의 경로별 소스 결정(삭제 파일은 base, 그 외 head, `working_tree`는 건너뜀)과 줄 수 계산, 대소문자 무시 별칭 | R-11, R-12 |
| C-12 | `plugins/codex-security/mcp-app/src/artifact-discovery.ts:56-178` `recordCodexSecurityDiscoveryCandidates`·`diffCandidateSources` | `record` 흐름 전체(목록 파일, worker, 교체)와 diff 소스 맵 호출 | R-11, R-14, R-15 |
| C-13 | `plugins/codex-security/mcp-app/src/artifact-inventory.ts:30-168` `prepareCodexSecurityReviewItems`·`listCodexSecurityReviewItems`·`readReviewItems` | `prepare`의 helper 인자 조립과 목록 읽기·검증 | R-08, R-09 |
| C-14 | `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:353-384` `scanContext`·`phaseScanContext` | scan context 요구(running, claim, 허용 mode) | R-07 |
| C-15 | `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:161-199` `readCandidateLedger`·`replaceCandidateLedger` | ledger 경로 상수, 읽기 스키마, 중복 검사, 교체 | R-18, R-20, R-21 |
| C-16 | `plugins/codex-security/mcp-app/src/artifact-io.ts:82-112, 132-167, 191-232` `artifactSourcePath`·`readArtifactJsonl`·`artifactDestination` | 경로 안전 검사와 JSONL 읽기 오류 형식 | R-18, R-19 |
| C-17 | `plugins/codex-security/mcp-app/src/artifact-io.ts:236-304` `publishArtifact`·`replaceArtifactText`·`replaceArtifactJsonl` | 임시 파일 + rename 교체, Windows 재시도, 빈 파일 | R-21 |
| C-18 | `plugins/codex-security/mcp-app/src/artifact-io.ts:169-186` `paginateArtifactRows` | cursor·limit 규칙과 오류 | R-09, R-16 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 사례는 실행하지 않았다. 해시 값은 계산하지 않고 조건으로 적는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-10~R-14 | running diff scan, 목록에 `src/a.ts`(10줄). `candidates`에 (cwe `["cwe-0079"]`, locations `[{path:"src/a.ts", start_line:3, role:"sink"}]`, instance 없음) 후보 둘을 summary만 다르게(`"B"`, `"A"`) 보낸다 | ledger는 한 행이다. `cwe_ids: ["CWE-79"]`, 위치 `end_line: 3`, `summary: "A\nB"`, `candidate_id`는 `candidate-` + 16자리 16진수. 응답은 `{ operation: "replace", candidatesRecorded: 1 }`. 같은 입력을 다시 보내면 같은 `candidate_id`다 |
| T-02 | R-10, R-14, R-16 | `candidates: []`를 보낸다 | ledger가 빈 파일이 되고 `candidatesRecorded: 0`. `list_codex_security_candidates`는 `rows: []`다 |
| T-03 | R-10 | 후보에 `relevant_lines: [3]` 또는 `candidate_id`를 넣는다 | 도구 입력 검증에서 거부되고 ledger는 바뀌지 않는다 |
| T-04 | R-12, R-15 | 후보의 모든 위치가 목록에 없는 파일이다 | "discovery candidates: candidate input row 1: locations: expected at least one in-scope file"으로 거부, ledger 불변 |
| T-05 | R-12 | 길이 10줄 파일에 `start_line: 5, end_line: 12`, 또는 `role: "foo"` | 앞은 "line range 5-12 exceeds src/a.ts:10", 뒤는 "role: unsupported value foo"(둘 다 "candidate input row N: " 접두) |
| T-06 | R-13 | CWE·위치·instance가 같고 `context`가 `"y"`·`"x"`인 두 후보와, instance만 다른 후보 하나 | 앞의 둘은 한 행(`context: "x\ny"`), instance가 다른 후보는 별도 행이다. 행 순서는 묶음 키 문자열 순이다 |
| T-07 | R-14, R-22 | 모든 행에 `validation`이 붙은 ledger가 있고 `record`를 다시 부른다 | `validation`이 모두 사라진 새 ledger가 된다. 같은 후보 입력이면 `candidate_id`는 같다 |
| T-08 | R-16, R-19 | ledger 3행, `limit: 2` → 다음 `cursor: "2"`. `cursor: "5"` | 첫 호출은 `rows` 2개와 `nextCursor: "2"`, 둘째는 행 1개와 `nextCursor` 없음, `"5"`는 "discovery candidates: cursor is outside the available rows." |
| T-09 | R-19 | ledger 2번째 줄이 `{` 로 깨졌다(빈 줄이 하나 앞에 있어 실제 줄 번호는 3) | 읽기가 "<라벨>: row 3 is not valid JSON."으로 실패한다 |
| T-10 | R-07 | Standard scan(mode `standard`)에 `record`를 부른다. Deep scan에 `record`를, Deep scan에 `list_codex_security_candidates`를 부른다 | 앞은 "This operation is only available for Deep or diff scans.", 둘째는 "…only available for diff scans.", 셋째는 허용된다 |
| T-11 | R-08, R-11 | `prepare`를 부르지 않고 `record`를 부른다 | "discovery review inventory: the requested artifact is unavailable."로 거부 |
| T-12 | R-11, R-12 | revision diff에서 삭제된 파일(`old.ts`, base에서 20줄)을 위치로 가진 후보 | 목록이 그 경로를 담고 있으면 base revision의 줄 수(20)로 검사해 통과한다. 목록에 없으면 그 위치는 in-scope가 아니다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

경로는 모두 `173483d7c658be7a512c93d9559bf01a05d5b196` 기준이다. 부재 주장의 검색 범위는 이 표 아래에 모았다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `plugins/codex-security/skills/finding-discovery/SKILL.md:12-20` | 지침 문장. 구형 경로의 문서 `plugins/codex-security/skills/security-scan/references/scan-artifacts-and-ledger.md:1-30`을 훑어 "compact diff는 쓰지 않는다"는 첫 문장만 확인했다 |
| R-02 | `plugins/codex-security/skills/finding-discovery/SKILL.md:24-25` | |
| R-03 | `plugins/codex-security/skills/finding-discovery/SKILL.md:26-27` | |
| R-04 | `plugins/codex-security/skills/finding-discovery/SKILL.md:28-29` | |
| R-05 | `plugins/codex-security/skills/finding-discovery/SKILL.md:8, 31, 45` | |
| R-06 | `plugins/codex-security/skills/finding-discovery/SKILL.md:35-43` | `relevant_lines`·`candidate_id` 입력 거부는 R-10·R-12. 부재 주장 2 |
| R-07 | C-14, `plugins/codex-security/mcp-app/src/artifact-context.ts:26-104` `createScanArtifactContext`, `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:305-351` `registerCompactTool`, `plugins/codex-security/mcp-app/server.ts:1842-1852`(`resolveHandoffClaimToken`), `plugins/codex-security/mcp-app/src/workbench-arguments.ts:7-24`, `plugins/codex-security/scripts/workbench_db.py:2686-2692` | 빈 문자열 thread ID가 `--model-thread-id ""`로 넘어가는 것은 `workbenchArgs`가 `""`를 건너뛰지 않는 코드에서 읽었다(건너뛰는 값은 `undefined`·`false`). workbench의 owner 검사는 `None`일 때만 건너뛴다(`plugins/codex-security/scripts/workbench/handoff.py:22-33`)는 점은 [caller-modes.md](./caller-modes.md) R-29. 스키마별 `handoffClaimToken` 유무는 C-02와 `plugins/codex-security/mcp-app/src/artifact-contracts.ts:166-173`. 서버 재시작 뒤 실패는 caller-modes R-28(캐시가 사라진다)과 이 스키마 차이에서 추론했다 |
| R-08 | C-13, `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:80-92` | 인자 조립만 읽었다. helper 본문 미열람 |
| R-09 | C-13(`readReviewItems`), C-18, `plugins/codex-security/mcp-app/src/artifact-contracts.ts:36-39, 171-173` | 경로 정규식은 `repositoryPath` 정의에서 읽었다 |
| R-10 | C-01, C-02, `plugins/codex-security/mcp-app/src/artifact-contracts.ts:388-419` | `strictObject`라 모르는 키를 거부한다는 것은 zod 4 동작에 대한 지식이다. JSON 내보내기에서도 `additionalProperties: false`(`plugins/codex-security/schemas/tools/discovery-candidates.schema.json`, `plugins/codex-security/schemas/definitions/discovery-candidate.schema.json`)로 같다 |
| R-11 | C-12, C-11, `plugins/codex-security/mcp-app/helpers-main.ts:44-50` | worker가 `normalizeCandidateBatch(workerData)`를 부르는 것(`isMainThread`가 아닐 때)까지 확인. `git_changed_paths`(`plugins/codex-security/scripts/workbench_target.py:498-`)는 시그니처만 봤다 |
| R-12 | C-05~C-09, C-11, `plugins/codex-security/mcp-app/src/helpers/resolve-security-md.ts:65-69` | symlink 거부는 `inside()`가 해석된 경로로 저장소 루트 안을 검사하는 코드(C-06의 `relativeFile`)에서 추론했다 |
| R-13 | C-05, C-08, C-09 | `combine`·`createCandidateNormalizer`의 코드에서 도출. 해시 값은 실행하지 않았다 |
| R-14 | C-12(`replaceArtifactText(destination, rows.map(...))`), C-05 | "기존 ledger를 읽지 않는다"는 부재 주장 1 |
| R-15 | C-09(`normalizeCandidateBatch`의 `try/catch`), C-12(worker 이벤트), C-17 | |
| R-16 | `plugins/codex-security/mcp-app/src/artifact-discovery.ts:180-193` `listCodexSecurityCandidates`, C-01(`discoveryCandidate`는 `looseObject`), C-16, C-18 | 스키마의 `looseObject`가 추가 키를 보존한다는 것은 zod 4 동작에 대한 지식(추론). 코드 주석(`:180`)도 "later shared phases 포함"이라 적었다 |
| R-17 | C-10, `plugins/codex-security/mcp-app/helpers-main.ts:120-121` | 부재 주장 2 |
| R-18 | C-15, C-16 | |
| R-19 | C-16(`readArtifactJsonl`) | |
| R-20 | C-04, C-15, `plugins/codex-security/mcp-app/package.json:18`(`zod ^4.6.7`) | `passthrough`가 strict를 해제한다는 것은 zod 4 라이브러리 지식이라 `추론`이다 |
| R-21 | C-17, `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:189-199` | 잠금 부재는 부재 주장 5 |
| R-22 | `plugins/codex-security/mcp-app/src/artifact-candidate-ledger.ts:24-77, 91-154` | 검증·공격 경로 함수 본문에서 공통 부분만 뽑았다. 세부는 두 스펙 |
| R-23 | 부재 주장 4, `plugins/codex-security/scripts/workbench_db.py:1147-1199` `complete_budget_exhausted_scan`, `plugins/codex-security/scripts/workbench_db.py:1209-1280` `budget_exhausted_candidates`, `plugins/codex-security/scripts/workbench_saved_results.py:1442-1598` `budget_exhausted_draft`, `plugins/codex-security/scripts/deep_scan_workbench.py:288-298, 1092-1130` | 위 Python 소비자는 후보 검사와 `disposition` 매핑 부분을 읽었다(`budget_exhausted_draft` 뒷부분의 manifest 쓰기는 훑음). 실행하지 않음(모델 준수는 미확인) |
| T-01~T-12 | 해당 R-ID의 근거 | 모두 코드 읽기로 기대값을 도출했다. 실행·원본 테스트 열람 없음. 테스트 파일 이름만 확인했다(`plugins/codex-security/mcp-app/tests/test_normalize_candidates.ts`, `sdk/typescript/tests-ts/candidate-normalizer.test.ts`) |

**부재 주장의 검색 범위**
1. R-14 (`record`가 기존 ledger를 읽지 않는다). `recordCodexSecurityDiscoveryCandidates`(`plugins/codex-security/mcp-app/src/artifact-discovery.ts:56-101`) 함수 본문을 전부 읽었고 `readArtifactJsonl`·`readCandidateLedger` 호출이 없다. `candidate_ledger.jsonl`을 여는 쓰기 호출은 `artifactDestination`뿐이다. 놓칠 수 있는 것: `replaceArtifactText` 호출 전에 다른 계층(MCP 등록부)이 파일을 보존·병합하는 동작. 등록부 `registerCompactTool`(`compact-artifact-tools.ts:317-351`)에는 그런 호출이 없다.
2. R-06·R-10·R-17 (`relevant_lines`가 문서에만 있다, helper `normalize-candidates` 호출처 없음). 기준 SHA에서 `git grep -n "relevant_lines" -- .`는 `plugins/codex-security/skills/finding-discovery/SKILL.md:43` 한 건이고, `git grep -n -i "relevantLines\|relevant-lines" -- .`는 0건이다. `git grep -n "normalize-candidates\|normalize_candidates" -- . ':!*test*' ':!*.test.*'`는 `.github/workflows/node-ci.yml`(CI 테스트 실행), `helpers-main.ts`, `normalize-candidates.ts` 자기 자신, `plugins/codex-security/native/examples/windows-wide-launcher.rs`(예제의 명령 이름 목록)만 나왔고 `skills/`·`references/`·`scripts/`·`sdk/typescript/src/`에는 없다. 놓칠 수 있는 것: 빌드 산출물(`mcp/*.mjs`, 추적 안 됨), 문자열을 조합해 부르는 호출, 사용자 정의 prompt.
3. R-22 (layout `worker`로 이 도구들에 도달하는 경로가 없다). `createScanArtifactContext`(`artifact-context.ts:82-103`)는 항상 `layout: "scan"`을 반환한다. `registerCompactWorkerArtifactTools`(`compact-artifact-tools.ts:263-303`)가 등록하는 도구는 `post_deep_scan_peer_note`·`read_deep_scan_peer_notes`·`record_codex_security_scan_draft`뿐이다. 놓칠 수 있는 것: 다른 서버 진입점(`artifact-writer-main.ts`)이 ledger 도구를 따로 등록하는 경우. `git grep -n "record_codex_security_candidate_validations\|record_candidate_attack_paths\|record_codex_security_discovery_candidates" -- plugins/codex-security/mcp-app sdk/typescript/src ':!*test*'`는 `compact-artifact-tools.ts` 등록과 `sdk/typescript/src/custom-validation-prompt.ts`(비활성 목록)만 나왔다.
4. R-23 (ledger를 읽는 코드는 이 도구들과 Deep 경로뿐이다). `git grep -n -i "candidate_ledger\|candidateLedger" -- plugins sdk github-action docker ':!*test*' ':!*.md'`는 `artifact-discovery.ts`, `artifact-candidate-ledger.ts`(경로 상수), `deep_scan_workbench.py`, `workbench_db.py`, `reserved_artifact_paths.json`만 나왔다. 별도로 후보 행의 `validation`·`attack_path`를 읽는 코드를 찾으려고 `git grep -n "attack_path" -- plugins sdk ':!*test*' ':!*.md'`를 봤고, ledger 행으로 읽는 곳은 `workbench_saved_results.py:1526`(`budget_exhausted_draft`)뿐이었다(나머지는 phase 이름 문자열 `attack_path`와 finding의 camelCase `attackPath`). `git grep -n -i "ledger" -- plugins/codex-security/mcp-app/src/artifact-scan-draft.ts plugins/codex-security/mcp-app/src/finding-normalization.ts plugins/codex-security/mcp-app/src/sealed-contract.ts plugins/codex-security/mcp-app/server.ts plugins/codex-security/scripts/finalize_scan_contract.py plugins/codex-security/scripts/validate_scan_contract.py`는 `ledgerRowId`(finding의 출처 필드 이름) 몇 줄만 나왔고 ledger 파일 읽기는 없다. 놓칠 수 있는 것: 파일 이름을 조합해 여는 코드, Deep worker가 별도 경로로 읽는 것(`worker-runner.ts`·`artifact-writer-main.ts` 등은 이 검색에 `candidate_ledger` 문자열이 없어 잡히지 않는다).
5. R-21 (잠금 없음). `artifact-candidate-ledger.ts`와 `artifact-io.ts`에서 `lock`·`mutex`·`flock`·`AsyncLock`을 찾지 못했다(`Grep` 범위는 두 파일). 서버(`server.ts`)에는 Deep 시작용 `AsyncLock`이 있으나(`:522` 부근) ledger 도구와 관련 없다. 놓칠 수 있는 것: MCP 프로토콜 계층의 요청 직렬화.

차이: 문서(SKILL.md)와 구현이 다른 곳은 세 가지다. (a) 지침은 `relevant_lines`와 입력으로 지정하는 안정 ID를 요구하지만 compact 도구는 둘 다 거부하고 ID를 해시로 만든다(R-06, R-10, U-01). (b) 지침 "병합하면 원래 후보 ID를 보존"은 compact 경로에서 입력 ID가 없어 코드가 보존하지 않는다(R-03, R-13). (c) `scan-artifacts.md`(43행)의 "writer가 CWE ids·위치·optional instance가 같은 행을 병합하고 deterministic ID를 부여한다"는 R-13과 일치한다.

### 2.2 코드 읽는 순서 [선택]
`compact-artifact-tools.ts`의 도구 등록(81-165)과 `scanContext`·`phaseScanContext`(353-384)로 입구와 게이트를 본다. 이어 `artifact-inventory.ts`(`prepare`·`list`), `artifact-discovery.ts`의 `recordCodexSecurityDiscoveryCandidates`(56-101)와 `diffCandidateSources`(103-178), 그 안에서 부르는 `normalize-candidates.ts`의 `normalizeCandidateBatch`(410)를 따라간다. 정규화의 세부는 `normalizeCandidate`(312) → `normalizeLocations`(251) → `readScope`(124) → `combine`(341) 순이다. ledger 계약은 `artifact-candidate-ledger.ts` 하단(161-199)과 `artifact-io.ts`(132-167, 296-304)다. 스키마는 `artifact-contracts.ts`(41-93, 409-419).

### 2.3 비교·재사용 출처 [선택]
다른 레포에 같은 기능 스펙은 없다. 원본 코드를 복사하지 않았다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 세션 기본 점검(2026-11-16). `python scripts/check.py codex-security`로 인용 줄의 존재를 확인하고(형식·위치 확인일 뿐), 고위험 R-ID 표본을 인용 줄과 검색으로 대조했다.  행 3·7·11이 `depends`로 의존하는 스펙이라 독립 검토가 남아 있고, 미결정도 있어 `draft`로 둔다.
- 대조한 R-ID: R-14(`MCP/src/artifact-discovery.ts` `recordCodexSecurityDiscoveryCandidates`가 기존 ledger를 읽지 않고 정규화한 새 행으로 `candidate_ledger.jsonl`을 교체하므로 재호출하면 `validation`·`attack_path`가 사라진다는 서술과 일치), R-10(`git grep relevant_lines|relevantLines`가 `finding-discovery/SKILL.md:43` 한 줄만 반환해 "코드·스키마에 없다"가 맞다)
- 대조하지 않은 R-ID: 위 2개를 제외한 전부. 특히 R-07(token 처리 `추론`), R-12(symlink 거부 `추론`), R-13(병합 키·ID 규칙), R-17·R-23(부재·전칭 주장), R-20·R-21(`추론`)은 독립 검토 대상이다.
- 재구현: 미수행
