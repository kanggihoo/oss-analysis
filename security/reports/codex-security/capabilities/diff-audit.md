---
sha: "173483d7c658be7a512c93d9559bf01a05d5b196"
created: 2026-11-16
updated: 2026-11-16
sources:
  - plugins/codex-security/skills/security-diff-scan/SKILL.md
  - plugins/codex-security/skills/security-diff-scan/agents/openai.yaml
  - plugins/codex-security/skills/finding-discovery/SKILL.md
  - plugins/codex-security/skills/security-scan/references/scan-artifacts-and-ledger.md
  - plugins/codex-security/references/artifact-storage.md
  - plugins/codex-security/references/scan-runtime.md
  - plugins/codex-security/references/investigation-time-budget.md
  - plugins/codex-security/references/scan-artifacts.md
  - plugins/codex-security/references/final-report.md
  - plugins/codex-security/references/access-advisory.md
  - plugins/codex-security/mcp-app/server.ts
  - plugins/codex-security/mcp-app/helpers-main.ts
  - plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts
  - plugins/codex-security/mcp-app/src/artifact-inventory.ts
  - plugins/codex-security/mcp-app/src/artifact-context.ts
  - plugins/codex-security/mcp-app/src/artifact-scan-draft.ts
  - plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts
  - plugins/codex-security/mcp-app/src/helpers/inventory-git.ts
  - plugins/codex-security/mcp-app/src/helpers/inventory-paths.ts
  - plugins/codex-security/mcp-app/src/helpers/source-preview.ts
  - plugins/codex-security/mcp-app/src/helpers/rank-worklists.ts
  - plugins/codex-security/scripts/launch_codex_security_mcp
  - plugins/codex-security/scripts/workbench_setup.py
  - plugins/codex-security/scripts/workbench_target.py
  - plugins/codex-security/scripts/workbench_db.py
  - plugins/codex-security/scripts/workbench_scan_start.py
  - plugins/codex-security/scripts/workbench_constants.py
  - plugins/codex-security/scripts/workbench_source_scopes.py
  - plugins/codex-security/scripts/review_state.py
  - sdk/typescript/src/targets.ts
  - sdk/typescript/src/api.ts
  - sdk/typescript/src/scan-time-budget.ts
depends:
  - ./caller-modes.md
  - ./candidate-discovery.md
  - ./candidate-validation.md
  - ./attack-path-severity.md
status: draft
---

# Diff 감사 (PR·commit·branch·working tree 변경 스캔)

> PR, commit, branch 범위(두 revision 사이) 또는 working tree 변경을 `diffTarget`으로 고정하고, 변경된 텍스트 파일 목록(삭제 파일은 baseline 내용)을 검토 단위로 삼아, 발견, 검증, 공격 경로 판정을 단계별 compact 도구에 기록한 뒤 초안을 확정하는 `security-diff-scan` skill의 전체 순서와, 그 순서가 의존하는 diff 대상 해석 및 변경 파일 인벤토리 계약을 정의한다.

<!--
이 레포에는 정적 분석 코드가 없다. 무엇이 취약점인지, 어느 변경 줄을 어떻게 읽는지는 SKILL.md를 읽은 모델이 정한다. R-ID 앞의 [지침]은 모델에게 주는 규칙(코드 확인 = 지침 문장을 읽었다)이고, [강제]는 코드가 검사하거나 만든다는 뜻이다. [강제 없음]은 코드가 같은 것을 보장하지 않는다는 부재 주장이다. 모델이 지침을 따르는지는 R-35가 미확인으로 묶는다.
git과 코드가 정하는 것은 "변경 파일 목록"과 "baseline revision"이다. 변경 줄(hunk)을 모델에게 건네는 코드는 이 SHA에서 찾지 못했다(R-34).
용어: "diff 인벤토리"는 `artifacts/02_discovery/in_scope_files.txt`(변경 파일 경로 목록). "workbench-owned diff"는 모델이 `start_codex_security_prompt_only_scan(mode:"diff")`으로 시작한 scan, "SDK-owned diff"는 `cs scan`이 `DiffTarget`으로 등록한 scan이다(호출자 모드는 caller-modes.md).
-->

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름 [필수]

대표 흐름은 모델이 직접 시작하는 workbench-owned diff scan이다. 순서는 SKILL.md의 번호와 같다.

1. 모델이 사용자가 말한 PR, commit, branch 비교 범위, 또는 작업 트리 변경을 정확한 Git 범위로 해석해 고정하고, 이미 scan이 있으면 `get_codex_security_scan_context`로 이어 가고 없으면 `start_codex_security_prompt_only_scan({ mode:"diff", targetPath, scope:".", diffTarget, userContext? })`를 한 번 부른다(R-20, R-21).
2. 서버가 `diffTarget`을 로컬 commit SHA와 content digest로 해석하고(`working_tree`는 base=head=현재 HEAD), 해석한 값을 scan에 저장해 scan을 `running`으로 만든다(R-01~R-07). 이 값이 이후 모든 단계가 따르는 변경 집합의 기준이다.
3. 모델이 시간 예산(요청이 있을 때만)과 context 규칙을 적용하고(R-22~R-24), `$threat-model`을 한 번 돌려 모델을 만든 뒤 `complete:false` 초안으로 즉시 저장한다(R-25).
4. 모델이 `prepare_codex_security_review_items`를 불러 변경 파일 인벤토리를 만들고 `list_codex_security_review_items`로 전 페이지를 읽는다. 서버가 helper `generate-in-scope-files`를 `--diff-base/--diff-head/--diff-mode`로 실행하고, helper는 `git diff --raw`로 정한 변경 목록에서 일반 텍스트 파일만 남긴다(R-11~R-19, 도구 래퍼는 [candidate-discovery.md](./candidate-discovery.md) R-08·R-09).
5. 모델이 `$finding-discovery`를 compact diff 모드로 인벤토리 전체에 돌려 후보를 `record_codex_security_discovery_candidates`로 한 번에 기록한다([candidate-discovery.md](./candidate-discovery.md) R-01~R-16). 후보가 있으면 `$validation`을 한 번([candidate-validation.md](./candidate-validation.md)), 이어 `reportable`·`deferred` 후보에 `$attack-path-analysis`를 한 번([attack-path-severity.md](./attack-path-severity.md)) 돌린다(R-27, R-28).
6. 모델이 결정이 나오는 대로 `record_codex_security_scan_draft`에 `complete:false` checkpoint를 저장하고, ledger 결과를 finding·`reviewState`로 옮기는 순서(R-29)대로 정리해 `complete:true`로 최종 초안을 낸다(R-29).
7. 모델이 `complete_codex_security_scan`을 한 번 부르고 `get_codex_security_completed_scan`으로 읽는다. SDK가 완료를 소유하면 이 단계를 하지 않고 SDK가 마무리한다(R-30, [caller-modes.md](./caller-modes.md) R-20·R-32). finalization이 `report.md`와 SARIF를 만든다.

SDK-owned diff(`cs scan` + `DiffTarget`)는 2번이 다르다. SDK가 `normalizeTarget`으로 refs를 SHA로 바꾸고 workbench `register-cli-scan`이 scan을 등록한다(R-08, R-09). 3번 이후의 변경 파일 인벤토리와 skill 순서는 같다.

### 1.2 범위·통합 지점 [필수]

- 제공:
  - `security-diff-scan` skill의 단계 순서와 각 단계 규칙(시작과 재개, 시간 예산, context 갱신, threat model 단계, review item 준비와 읽기, 단계별 위임, checkpoint, 완료·실패·취소, "모든 변경 파일과 후보를 설명한다"는 책임).
  - diff 대상 해석 계약: MCP `diffTarget`, workbench의 해석과 검증, SDK `DiffTarget`·`NormalizedTarget`·`normalizeTarget`, diff scan에 묶이는 target 식별(`git_diff`, snapshot digest, coverage mode).
  - 변경 파일 인벤토리 계약: helper `generate-in-scope-files`의 diff 모드 입력, 출력, 선택 규칙, 실패.
  - "git·코드가 정하는 것"과 "모델이 하는 것"의 경계(R-33, R-34).
- 제외(이유):
  - 호출자 모드와 scan 등록, claim token, 환경 변수, SDK prompt 조립: [caller-modes.md](./caller-modes.md)(행 1)가 소유한다. 이 스펙은 diff와 관련된 사실만 R-ID로 참조한다.
  - 후보 발견·정규화·ledger(S1)와 `prepare`·`list review items` 도구의 입력 검사: [candidate-discovery.md](./candidate-discovery.md). 검증: [candidate-validation.md](./candidate-validation.md). 공격 경로와 severity: [attack-path-severity.md](./attack-path-severity.md).
  - threat model 내용, 재사용·cache 규칙, `threatmodel.md` 투영(행 8): 이 스펙은 diff skill이 `$threat-model`을 부르는 순서와 복사 규칙 한 줄만 쓴다. 초안·확정 검증, 봉인, 보고서(행 9, S2): 최종 draft를 모델이 낸다는 경계와 diff 전용 매핑 규칙(R-29)만 쓴다.
  - helper 소스 전체와 다른 helper(`resolve-security-md`, `make-repo-scope-input` 등, 행 10): diff 인벤토리 계약(R-11~R-19)만 쓴다. `make-diff-rank-input`은 구형 standalone diff 경로의 helper이고 이 skill이 부르지 않는다(R-19).
  - SDK `cs scan --diff` CLI 옵션 해석과 비용·재개(행 15·16). `DiffTarget`·`normalizeTarget`은 diff 대상 계약이라 포함한다(R-08).
  - 구형 standalone diff 경로(`security-scan/references/scan-artifacts-and-ledger.md`의 `rank_input.jsonl`·worklist·receipt). 이유와 경계는 [candidate-discovery.md](./candidate-discovery.md) 1.2.
- 외부 의존·선행 계약: scan 시작과 소유 증명(claim token, owner thread, `running` 요구)은 [caller-modes.md](./caller-modes.md) R-24·R-28·R-29·R-31·R-32다. 도구 접근 규칙은 [candidate-discovery.md](./candidate-discovery.md) R-07이다. 이 SHA에서 diff 인벤토리를 만드는 코드는 빌드 산출물 `mcp/helpers.mjs`로 실행되고 이 파일은 레포에 추적되지 않는다(확인 한계). Git 실행 파일(diff 인벤토리는 ripgrep을 쓰지 않고 Git만 쓴다).
- 소유 상태·부작용:
  - workbench DB의 scan 행에 저장되는 diff 식별(`diff_target_kind`, `diff_base_revision`, `diff_head_revision`, `diff_content_digest`)과 workspace의 같은 열. 전체 스키마는 S4(행 12) 몫이다.
  - `<scanDir>/artifacts/02_discovery/in_scope_files.txt`(인벤토리). 쓰는 쪽은 `prepare`이고 이후 읽기 규칙은 [candidate-discovery.md](./candidate-discovery.md) 1.3.3이다. 같은 이름의 임시 파일 `.<random>.tmp`가 같은 디렉터리에 생겼다가 rename된다.
  - 이 스펙이 만드는 다른 영속 상태는 없다. 후보 ledger는 S1, 초안과 확정은 S2다.

### 1.3 인터페이스와 데이터 의미 [필수]

#### 1.3.1 skill 단계와 호출 대상

| 단계 | skill이 지시하는 일 | 호출 대상 | 코드가 강제하는 것 | 상세 |
|---|---|---|---|---|
| setup | Git 범위 해석·고정, 시작 또는 이어받기 | `start_codex_security_prompt_only_scan`, `get_codex_security_scan_context` | 입력 스키마, `diffTarget` 해석과 저장(R-01~R-07), 소유 증명 | R-20, R-21 |
| 런타임 | 위임 도구 확인, `SECURITY.md`, access advisory, 시간 예산 | `scan-runtime.md`, `access-advisory.md`, `investigation-time-budget.md` 문서 | 없음(문서 지침) | R-22, R-23 |
| context | 요청 시 `update_codex_security_scan_context`, 단계 전환마다 `update_codex_security_scan_progress` | 같은 이름의 도구 | phase 순서·값 검사([caller-modes.md](./caller-modes.md) R-31) | R-24 |
| 1 | `$threat-model` 한 번, `complete:false` 초안 | `record_codex_security_scan_draft` | 초안 스키마(행 9) | R-25 |
| 2 | 변경 파일 목록 준비와 전 페이지 읽기 | `prepare_codex_security_review_items`, `list_codex_security_review_items` | 인벤토리 생성·검사(R-11~R-19), 경로 안전 검사 | R-26 |
| 3 | `$finding-discovery` compact diff | `record_codex_security_discovery_candidates` | 후보 정규화·ledger | R-27 |
| 4 | `$validation` 한 번, `$attack-path-analysis` 한 번 | `record_codex_security_candidate_validations`, `record_candidate_attack_paths` | 입력 대 ledger 검사 | R-28 |
| 5 | checkpoint와 최종 초안 | `record_codex_security_scan_draft` | 초안 스키마(행 9) | R-29 |
| 6 | 완료 | `complete_codex_security_scan`, `get_codex_security_completed_scan` | 소유·claim·`running`([caller-modes.md](./caller-modes.md) R-32) | R-30 |

#### 1.3.2 MCP `diffTarget`과 서버 해석

외부 계약이므로 필드 이름은 원문이다. 서버가 쓰는 도구는 `start_codex_security_prompt_only_scan`(`mode:"diff"`)이다.

| kind | 모델이 주는 필드 | 서버가 해석해 저장하는 값 | 거부 조건 |
|---|---|---|---|
| `working_tree` | `baseRevision?`(기본 `HEAD`), `headRevision?`(기본 현재 HEAD), `contentDigest?` | `baseRevision`=`headRevision`=현재 HEAD의 commit SHA, `contentDigest`=현재 작업 트리 digest | base나 head가 현재 HEAD와 다르면 거부. `contentDigest`를 줬는데 현재 digest와 다르면 거부(R-03) |
| `commit` | `headRevision`(필수), `baseRevision?` | `headRevision`=`<head>^{commit}` SHA, `baseRevision`=그 commit의 첫 `parent` SHA. 부모가 없으면 빈 tree 객체 ID | `baseRevision`을 줬는데 부모와 다르면 거부(R-04) |
| `range` | `baseRevision`, `headRevision`(둘 다 필수) | 각각 `^{commit}`으로 해석한 SHA | 둘이 같은 commit이면 거부(R-05) |

공통: 각 revision 문자열은 최대 512자이고, 모든 입력은 strict 객체다(R-01). 해석 결과는 workspace와 scan 행에 `kind`, base, head, `contentDigest`로 저장되고(R-06), 이후 scan context의 `contract.diffTarget`으로 돌아온다. `targetSummary`가 비어 있으면 서버가 `Uncommitted changes`, `Commit <head 7자>`, `<base 7자>…<head 7자>` 중 하나로 채운다(R-06).

#### 1.3.3 SDK `DiffTarget`과 `NormalizedTarget`

| 연산·타입 | 입력·출력 | 의미·제약 |
|---|---|---|
| `DiffTarget.refs({ base, head = "HEAD" })` | `DiffTarget { kind:"refs", base, head }` | `base`·`head`는 비어 있지 않은 문자열이어야 한다. 객체는 동결된다(R-08) |
| `DiffTarget.workingTree({ base = "HEAD" })` | `DiffTarget { kind:"working_tree", base }` | `head`를 지정하면 거부한다(R-08) |
| `normalizeTarget(repository, target)` | `NormalizedTarget { kind:"refs"\|"working_tree", paths:[], base, head, baseRef, headRef }` | `base`·`head`는 `git rev-parse --verify <ref>^{commit}`이 돌려준 SHA, `baseRef`·`headRef`는 사용자가 준 ref 문자열이다. `working_tree`의 `head`는 항상 `HEAD`를 해석한 값이다. merge-base는 계산하지 않는다(R-08) |
| scan recipe의 `target` | `{ kind, paths:[], base, head, baseRef, headRef }` | workbench `register-cli-scan`이 받는다. diff이면 `base`·`head` 문자열이 필수다(R-09) |

#### 1.3.4 diff 인벤토리 helper 계약

- 호출: `launch_codex_security_mcp --helper generate-in-scope-files --repo=<repoRoot> --scope=<scope> --out=<in_scope_files.txt> --diff-base=<base> --diff-head=<head> --diff-mode=<local-patch|revisions>`. `--repo`, `--out`, `--scope`는 필수이고 `--diff-base`가 있으면 diff 인벤토리다. `--diff-head`의 기본값은 `HEAD`, `--diff-mode`의 기본값은 `revisions`, 허용값은 `revisions`·`local-patch` 둘이다. MCP `prepare`는 항상 세 값을 다 준다(R-11).
- 출력: 한 줄에 저장소 상대 경로 하나. 경로는 Git이 준 바이트 그대로이고 `./` 접두가 없다. 중복은 제거하고 (줄 끝 개행 문자까지 포함한) 바이트 순서로 정렬한다. 줄 구분은 LF다. 변경이 없으면 빈 파일이다(R-15).
- 성공: stdout에 `Recorded N in-scope files.`, 종료 코드 0. 실패: stderr에 메시지, 종료 코드 2(R-16).
- 선택 규칙은 모드별로 R-12(revisions), R-13(local-patch)이고, 파일 내용 검사(텍스트 판정)는 R-14다.

#### 1.3.5 같은 규칙의 Python 미러

Python(`workbench_target.git_changed_paths`)에 같은 선택 규칙이 한 번 더 구현돼 있다. 용도는 둘이다. `diff_scope_file_count`는 scan 시작 때 progress의 파일 총수 추정값(`scopeFileCount`)을 만들고, `candidate_source_lines`는 후보 위치를 검사할 때 변경 파일의 revision과 줄 수를 정한다([candidate-discovery.md](./candidate-discovery.md) R-11·R-12). 두 구현이 같은 결과를 내는지는 이 스펙이 보증하지 않는다(R-18).

### 1.4 행동 규칙과 남은 질문 [필수]

#### diff 대상 해석 [강제]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | [강제] `start_codex_security_prompt_only_scan` 입력 | `mode`는 `diff`·`standard`, `scope`와 `targetPath`는 필수다. `diffTarget`은 zod discriminated union(`working_tree`: base·head·digest 선택, `commit`: head 필수·base 선택, `range`: base·head 필수)이고 strict다. `mode:"diff"`인데 `diffTarget`이 없으면 "Review changes prompt-only scans require diffTarget.", `mode:"standard"`에 `diffTarget`이 있으면 "Standard prompt-only scans must omit diffTarget."이다. `mode:"diff"`의 `scope`는 `.`(생략 포함)이거나 `targetPath` 자신이어야 하고 아니면 "Review changes prompt-only scans require the whole target; use scope '.'."이다. 호출 thread ID가 없으면 오류다([caller-modes.md](./caller-modes.md) R-24). 서버는 `diffTarget`의 `kind`, base, head, `contentDigest`(`working_tree`만)를 workbench에 인자로 넘긴다 | 코드 확인 |
| R-02 | [강제] 해석 전 공통 검사(`inspect_setup_values`) | `targetPath`는 절대 경로이고 존재하는 디렉터리여야 한다. bare 저장소가 아닌 checkout된 Git worktree이어야 하고("Codex Security requires a checked-out worktree, not a bare Git repository."), HEAD가 resolve돼야 한다("Review changes requires a non-bare Git worktree with a resolvable HEAD."). `git rev-parse --show-toplevel`이 `targetPath`와 같은 디렉터리여야 한다(하위 디렉터리를 target으로 줄 수 없다, "Review changes requires the checked-out Git repository root as the target."). `scope`는 정규화한 결과가 `.`이어야 한다("Review changes requires the whole target; use scope '.'."). `mode`가 `diff`가 아니면서 diff 인자가 하나라도 있으면 "A Git diff target requires Review changes mode."다 | 코드 확인 |
| R-03 | [강제] `kind:"working_tree"` 해석 | `baseRevision`(기본 `HEAD`)과 `headRevision`(기본 현재 HEAD)을 `<rev>^{commit}`으로 해석한다. 둘 중 하나라도 현재 HEAD와 다르면 "Repository HEAD changed after these working-tree changes were selected. Select Uncommitted changes again."로 거부한다. 현재 작업 트리 digest(`worktree_content_digest`, submodule worktree가 clean이어야 한다)를 계산하고, 모델이 `contentDigest`를 줬는데 다르면 "Working-tree contents changed after they were selected. Select Uncommitted changes again."로 거부한다. 결과는 `{ kind, baseRevision: 현재 HEAD, headRevision: 현재 HEAD, contentDigest: 현재 digest }`다. 즉 이 경로의 working tree diff는 항상 `HEAD` 대비다 | 코드 확인 |
| R-04 | [강제] `kind:"commit"` 해석 | `headRevision`(필수)을 `^{commit}`으로 해석하고, 그 commit 객체의 첫 `parent` 줄을 base로 쓴다. 부모 줄이 없으면(root commit) base는 저장소 객체 형식의 빈 tree ID다(`sha1`: `4b825dc642cb6eb9a060e54bf8d69288fbee4904`, `sha256`: `6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321`). 모델이 `baseRevision`을 줬고 부모와 다르면(빈 tree ID 문자열이면 비교만, 아니면 `^{commit}`으로 해석해 비교) "Commit base revision must match the selected commit's parent."다. merge commit은 첫 부모 대비다 | 코드 확인 |
| R-05 | [강제] `kind:"range"` 해석 | `baseRevision`·`headRevision`을 각각 `^{commit}`으로 해석한다. 해석할 수 없으면 "<라벨> does not resolve to a local Git commit: <값>", 두 SHA가 같으면 "Base and head revisions must identify different commits."다. 해석 결과의 변경 집합은 R-12의 `<base>..<head>` 직접 비교이고 merge-base를 쓰지 않는다. 사용자가 PR의 merge-base 비교를 원하면 모델이 merge-base를 base로 골라야 한다(코드는 대신 계산하지 않는다) | 코드 확인 (merge-base 부재는 2.1 부재 주장 1) |
| R-06 | [강제] 해석 결과의 저장과 재사용 | `start-prompt-only-scan`은 R-02~R-05를 거친 값으로 scan을 만든다. workspace와 scan 행에 `diff_target_kind`, `diff_base_revision`, `diff_head_revision`, `diff_content_digest`를 저장하고(digest는 `working_tree`일 때만 값이 있다), scan 등록용 target identity는 (head revision, digest 없음, 디렉터리의 device, inode)다(`scan_target_identity`가 diff이면 head revision을 쓰고 digest를 계산하지 않는다). `target_summary`가 비어 있으면 `Uncommitted changes`(working_tree), `Commit <head 7자>`(commit), `<base 7자>…<head 7자>`(range)로 채운다. 시작 때 `scopeFileCount`(progress 총수 추정)를 Python 미러로 계산하고, 부분 clone처럼 계산할 수 없으면 NULL이다. scan context의 `contract.diffTarget`과 `diffTarget`은 이 저장값에서 `kind`, `baseRevision`, `headRevision`, `contentDigest`(있을 때)를 다시 만든 것이다. 같은 thread가 같은 diff identity로 다시 시작하면 새 scan 대신 기존 scan을 `joined`로 돌려준다([caller-modes.md](./caller-modes.md) R-26) | 코드 확인 |
| R-07 | [강제] 시작 경합 검사 | 해석과 digest 계산이 끝난 뒤 쓰기 잠금 전에 `require_diff_target`과 target identity를 다시 계산해, 이전 값과 하나라도 다르면 "The selected scan target changed while the scan was starting. Try again."로 거부한다. `working_tree`는 시작 직전에도 HEAD와 digest를 다시 확인한다. scan이 시작된 뒤 작업 트리가 바뀌어도 이를 감시하거나 거부하는 workbench 코드는 찾지 못했다(prepare 시점에도 재검사하지 않는다) | 코드 확인 (시작 후 감시 부재는 2.1 부재 주장 2) |
| R-08 | [강제] SDK `DiffTarget`·`normalizeTarget`·검사 | `DiffTarget`은 `kind`가 `refs`·`working_tree`가 아니면 "Unsupported diff target kind: …", `base`가 비었으면 "The diff base ref must be non-empty.", `refs`에 `head`가 없으면 "Git diff refs must include a non-empty head ref.", `working_tree`에 `head`가 있으면 "Working-tree targets cannot specify a head ref."로 거부한다. `normalizeTarget`은 저장소가 Git worktree 루트여야 하고("Diff target repository must be the Git worktree root: …") 각 ref를 `git rev-parse --verify --end-of-options <ref>^{commit}`으로 해석한다(실패 시 "unknown Git ref: <ref>. …"). `refs`는 `head`를 그대로, `working_tree`는 `HEAD`를 head로 해석한다. `refs`이면 실행 전에 `validateCommittedDiffCheckout`이 (a) checkout의 HEAD가 해석한 head와 같아야 하고, (b) `git status --porcelain=v1 --untracked-files=all`이 비어 있어야 하고(clean checkout), (c) sparse checkout 항목(`S `·`s `)이 없어야 하고, (d) assume-unchanged 항목(`h `)이 있으면 `update-index --really-refresh`를 private index 복사본으로 돌려 변경이 없음을 확인해야 한다. `working_tree`에는 이 검사가 없다. mode가 `deep`이면 diff target을 거부한다([caller-modes.md](./caller-modes.md) R-03) | 코드 확인 |
| R-09 | [강제] SDK-owned diff의 workbench 등록(`register-cli-scan`) | recipe의 `target.kind`가 `refs`·`working_tree`이면 `base`·`head` 문자열이 있어야 하고, 저장소는 R-02와 같은 worktree 루트 조건(`require_review_changes_target`)을 만족해야 한다. `base`·`head`를 다시 commit으로 해석하고, workbench의 diff kind는 `refs`→`range`, `working_tree`→`working_tree`다. `working_tree`는 `head`가 현재 HEAD와 같아야 하고 digest를 계산해 저장한다. 이 경로는 base가 HEAD여야 한다는 검사가 없고(R-03과 다름), `range`의 base와 head가 같아도 거부하지 않는다. scan mode는 항상 `diff`다. 시작 직전에 `working_tree`는 HEAD와 digest를 다시 확인한다("The selected scan target changed while the scan was starting. Try again.") | 코드 확인 (base=head 비거부는 2.1 부재 주장 3) |
| R-10 | [강제] diff scan의 target 식별 | diff scan의 manifest target 종류는 `git_diff` 하나다(`expected_target_kinds`). 서버가 초안을 만들 때 target에 `baseRevision`·`headRevision`을 넣고 `snapshotDigest`는 `working_tree`이면 저장된 `contentDigest`, `commit`·`range`이면 SHA-256(`"codex-security-diff/v1\0" + kind + "\0" + base + "\0" + head`)의 16진수 앞에 `codex-security-snapshot/v1:sha256:`을 붙인 값이다. coverage mode는 `range`이면 `branch_diff`, 아니면 `working_tree`·`commit` 그대로이고, `inventoryStrategy`는 `diff`다. `working_tree` target의 manifest digest가 저장된 `contentDigest`와 다르면 manifest 검증이 거부한다. 이 값들을 검증하는 전체 규칙은 행 9 몫이다 | 코드 확인 |

#### 변경 파일 인벤토리 [강제]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-11 | [강제] `prepare` 호출 → helper 인자 | 도구 래퍼의 검사(layout `scan`, plugin 루트, `diffTarget` 형식)는 [candidate-discovery.md](./candidate-discovery.md) R-08이다. 인자의 diff 부분은 `--diff-base=<baseRevision> --diff-head=<headRevision> --diff-mode=<working_tree이면 local-patch, 아니면 revisions>`이고 `--scope`는 scan scope(생략 시 `.`)다. helper는 diff 인벤토리일 때 `--scope`가 저장소 루트(`.`, `./`, 또는 루트의 절대 경로)가 아니면 "--scope: diff scans must use the repository root"로 실패한다. POSIX에서는 인자를 NUL로 이은 문자열의 16진수를 stdin으로 넘기고(경로 바이트 보존), Windows에서는 argv로 넘긴다 | 코드 확인 |
| R-12 | [강제] `revisions` 모드(commit, range)의 변경 후보와 선택 | Git 질의는 `git diff --ignore-submodules=all --raw -z --diff-filter=ACMRDT <base>..<head> --`이다(`GIT_LITERAL_PATHSPECS=1`). 출력의 각 항목에서 선택한 쪽의 mode가 `100`으로 시작하는 일반 파일만 남긴다. 삭제(`D`)는 이전 mode, 그 밖은 새 mode를 본다. 따라서 symlink(`120000`)와 submodule(`160000`)은 빠지고, 형식 변경(`T`)은 새 쪽이 일반 파일일 때만 남는다. 이름 변경(`R`)은 새 경로만, 복사(`C`)도 새 경로만 목록에 올라가고 이름 변경의 이전 경로는 따로 올라가지 않는다. rename 감지를 강제하는 옵션(`-M`)도 끄는 옵션(`--no-renames`)도 주지 않으므로 Git 설정(`diff.renames`)이 감지 여부를 정한다 | 코드 확인 (rename 감지가 설정에 달렸다는 점은 Git 동작이라 추론) |
| R-13 | [강제] `local-patch` 모드(working_tree)의 변경 후보와 선택 | 후보는 (a) `git diff … <base>`(작업 트리 대비)와 `git diff … --cached <base>`(index 대비)의 합집합(같은 경로는 앞의 것이 우선, 즉 작업 트리 쪽), (b) `git ls-files --others --exclude-standard -z`로 얻은 추적되지 않고 무시되지 않는 파일(경로가 `/`로 끝나지 않는 것, 상태 `A`)이다. 추적 중인 파일의 변경은 ignore 규칙과 상관없이 후보다. 각 후보에 대해: 경로 구성요소에 `.git`·`.svn`이 있으면 제외. 상태 `D`는 그대로 남기고 작업 트리를 보지 않는다. 상태 `M`·`R`이고 경로의 상위 디렉터리에 symlink가 있으면 `M`은 `D`로 바꾸고 `R`은 제외한다. 그 밖에는 작업 트리에서 일반 파일일 때만 남기고, 없거나 일반 파일이 아니면 제외한다(없음 외의 파일시스템 오류는 던진다). `R`인데 새 경로가 제외되고 이전 경로가 아직 선택되지 않았다면 이전 경로를 `D`로 올린다. 결과: 새 경로가 정상인 이름 변경은 새 경로만 올라간다 | 코드 확인 (staged에만 남은 변경도 후보라는 점은 위 합집합 코드에서 읽은 것이다) |
| R-14 | [강제] 텍스트 판정과 내용 읽기 | 후보마다 내용 전체에 NUL 바이트가 있으면 binary로 보고 목록에서 뺀다(UTF-16 BOM `FF FE`·`FE FF`로 시작하면 UTF-16으로 풀어 NUL 문자를 본다). 확인 대상은 `revisions`에서는 모든 후보의 blob(삭제는 `<base>:<path>`, 그 밖은 `<head>:<path>`), `local-patch`에서는 삭제만 `<base>:<path>` blob이고 나머지는 작업 트리의 실제 파일이다. 작업 트리 파일은 일반 파일이어야 하고 실제 경로가 저장소 안이어야 하며(밖이면 제외), 읽다가 실패하면 binary로 취급해 제외한다. blob을 읽지 못하면(객체 없음, 형식 불일치) "Unable to read committed diff blob: <rev>:<path>"로 실패한다. 파일 크기나 개수 제한은 이 코드에 없다 | 코드 확인 (제한 부재는 2.1 부재 주장 4) |
| R-15 | [강제] 인벤토리 출력 | 줄에 CR 또는 LF가 든 경로가 하나라도 있으면 전체가 실패한다("Git changes contain a path that cannot fit in the file inventory"). 그 밖에는 경로 바이트(Windows에서는 짝 없는 surrogate 보존 인코딩)에 `\n`을 붙이고 같은 바이트의 중복을 하나로 합쳐 (줄 끝 개행 문자까지 포함한) 바이트 순서로 정렬한다. 같은 디렉터리의 임시 파일에 쓰고 rename으로 교체한다. `--out`은 symlink이거나 일반 파일이 아닌 기존 대상이면 거부한다. 변경이 없으면 빈 파일이고 `Recorded 0 in-scope files.`다. `revisions`에서는 `.git`·`.svn` 경로를 거르지 않고, `local-patch`에서만 거른다 | 코드 확인 |
| R-16 | [강제] 인벤토리 실패 | 모든 실패는 종료 코드 2다. Git이 비정상이고 stderr가 있으면 "could not resolve the selected Git changes: Git diff failed with …: <stderr>"(제어 문자는 `\uXXXX`로 바꾼다). 필수 옵션 누락, 모르는 모드, `--out` 규칙 위반은 사용법과 `generate-in-scope-files: error: …`다. MCP `prepare`는 종료 코드가 0이 아니면 stderr(없으면 종료 상태·signal)를 담아 "review_items: the scan inventory helper failed: …"를 던진다. 실패하면 기존 `in_scope_files.txt`는 바뀌지 않는다(임시 파일이 정리되고 rename은 마지막이다) | 코드 확인 |
| R-17 | [강제] helper의 Git 실행 환경 | 저장소를 가리키는 Git 환경 변수(`GIT_DIR`, `GIT_WORK_TREE` 등 `repositoryEnvironment`)를 지우고, `GIT_LITERAL_PATHSPECS=1`, `GIT_NO_LAZY_FETCH=1`, `GIT_ALLOW_PROTOCOL=""`, `-c core.fsmonitor=false`, `-c i18n.logOutputEncoding=UTF-8`, `-C <repo>`로 실행한다. 신뢰할 Git 실행 파일을 고르는 규칙(`trustedTools`)과 Windows 경로 해석은 행 10과 확인 한계다. Git을 찾지 못하면 diff 인벤토리는 질의 실패로 끝난다 | 코드 확인 (신뢰 실행 파일 선택은 열지 않음) |
| R-18 | [강제 없음] 같은 규칙의 두 구현이 같은 결과를 내는지 | 인벤토리(TypeScript)와 progress 추정·후보 위치 검사(Python)가 각자 `git diff --raw` 파싱, 일반 파일 모드 필터, local-patch 후처리, NUL 기반 binary 판정을 구현한다. 줄 단위로 대응하는 로직임은 읽었지만 같은 입력에서 같은 결과를 낸다는 점은 실행하지 않아 확인하지 못했다(예: 두 구현의 UTF-16 처리와 오류 취급이 다르다). 어긋나면 `scopeFileCount`가 인벤토리 줄 수와 다를 뿐이고 인벤토리 자체가 바뀌지는 않는다. 후보 위치 검사는 인벤토리 목록에 든 경로를 in-scope로 보므로 어긋남이 후보 거부로 나타날 수 있다 | 코드 확인 (대응) / 추론 (결과 동일성 미확인) |
| R-19 | [강제 없음] `make-diff-rank-input`을 누가 부르는가 | `make-diff-rank-input`은 `generate-inventory.ts`의 `inventoryCommand`가 구현하고(`rank-worklists.ts`는 행 파서 등 공용 유틸이다) 같은 diff 선택 규칙(R-12~R-14)으로 `{path, area, preview}` JSONL 행(경로 코드 포인트 순, 기본 area `diff`, 삭제 파일은 빈 preview)을 `--out`에 쓴다. `security-diff-scan` SKILL.md는 "ranked worklist를 만들지 말라"고 하고 이 helper를 부르지 않는다. 이 SHA에서 호출처는 `security-scan/references/scan-artifacts-and-ledger.md`(compact 인벤토리 없는 standalone·구형 diff, `finding-discovery/SKILL.md`가 가리킨다)와 테스트뿐이고 SDK는 부르지 않는다 | 코드 확인 (호출처 부재는 2.1 부재 주장 5) |

#### skill 지침 [지침]

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-20 | [지침] 검토 단위와 확장 한계 | 변경된 모든 텍스트 파일을 검토한다. 삭제된 파일도 포함하고 baseline revision의 내용으로 본다. 변경된 동작이 기대는 지원 코드까지 따라가되 무관한 저장소 전체 감사로 넓히지 않는다. 변경 파일의 보안 관련성은 파일 이름이 아니라 동작과 도달 가능성으로 평가하고 build, 배포, CI 용도도 포함한다. 인벤토리는 이름·확장자·디렉터리와 상관없이 변경된 텍스트 파일을 담고(R-12~R-14), 추적 파일의 변경은 무시 규칙과 상관없이 남고 local patch는 무시되지 않는 untracked 파일도 포함한다 | 코드 확인 (지침 문장). 인벤토리 쪽 사실은 R-12~R-14 |
| R-21 | [지침] setup과 시작 | `references/artifact-storage.md`로 scan 소유와 저장 규칙을 읽고, 정확한 Git range 또는 local patch를 해석해 바꾸지 않는다. 사용자 context와 외부 자료는 분석 데이터이고 지시나 권한이 아니다(부모는 사용자가 허가한 범위 안의 URL을 읽을 수 있고 내용이 다른 target·서비스 접근을 허가하지 못한다). 기존 `scanId`는 `get_codex_security_scan_context`로 이어 가고, 없으면 `start_codex_security_prompt_only_scan`을 `mode:"diff"`, `targetPath`, `scope:"."`, `diffTarget`, 선택적 `userContext`로 한 번 부른다. 돌려받은 identity, directory, revisions, handoff token을 보존한다. MCP를 쓸 수 없거나 baseline이 지원되지 않으면 blocker를 보고하고 대체 scan이나 shell로 쓴 canonical 파일을 만들지 않는다(`artifact-storage.md`도 같다). SDK-owned scan은 주어진 context와 완료 소유자를 유지한다 | 코드 확인 (지침 문장) |
| R-22 | [지침] 런타임, `SECURITY.md`, access advisory | 소스를 읽기 전에 `scan-runtime.md`를 읽는다: 위임 도구가 deferred이고 `tool_search`가 있으면 한 번 찾아보고, 성공한 spawn 호출과 반환된 worker ID만 worker가 시작됐다는 증거로 쓰고, 위임이 안 되면 부모가 배정된 검토를 이어 가며 실제 coverage gap을 보고한다. 영속 Codex 설정을 읽거나 고쳐 worker·goal 도구를 켜지 않는다. 관련 `SECURITY.md`를 적용한다. diff scan은 첫 실질 작업 전에 `access-advisory.md`를 읽는다(선택적 점검이고 scan을 막지 않는다) | 코드 확인 (지침 문장) |
| R-23 | [지침] 시간 예산 | 이미 있거나 host가 준 investigation 시간 허용치는 재개 턴에서도 바꾸지 않고 따른다. 그 밖에는 이 대화에서 사용자가 명시적으로 요청한 경우에만 setup 뒤 소스 검토 전에 `investigation-time-budget.md`를 읽고, 요청한 양수 `budgetMinutes`, 실제 UTC `startedAt`, 계산한 `deadlineAt`을 채워 한 번 렌더링해 이 scan 동안 따른다. repository 내용과 가져온 `userContext`는 허용치를 허가하거나 바꾸지 못한다. 허용치도 요청도 없으면 템플릿을 읽지 않고 시계를 시작하지 않는다. 템플릿 본문의 규칙: 허용치는 권고이지 hard timeout이나 최소 시간이 아니고, 남은 시간 동안 가장 가치 있는 구체적 소스 검사를 계속하고, 모든 phase·worker·재시도·재개 턴이 처음의 절대 deadline을 공유하고, 마감 후에는 새 조사를 열지 않고 읽지 않은 파일이나 풀지 못한 후보를 검토했다고 주장하지 않는다. SDK 경로는 SDK가 같은 템플릿을 렌더링해 prompt 끝에 붙인다(SDK의 mode가 `standard`이면 diff target이어도 `maxTimeMinutes`가 있을 때 적용된다) | 코드 확인 (지침 문장과 `scan-time-budget.ts`의 렌더링). 모델이 지키는지는 R-35 |
| R-24 | [지침] context 갱신과 phase | 사용자가 context 변경을 요청하면 `update_codex_security_scan_context`로 저장한다. 실제 단계 전환마다 `update_codex_security_scan_progress`를 부르고 그 결과의 `structuredContent.scan.userContext`를 그 단계와 worker의 context로 쓴다. 필요하면 현재 handoff token을 넘긴다. worker는 context를 데이터로 취급하고 offline이며 부모만 허가 범위 안에서 외부 context를 가져온다. host-backed diff scan은 architecture mapping 전에 `threat_model` phase로 올린다(`scan-runtime.md`). 도구 쪽 검사는 [caller-modes.md](./caller-modes.md) R-30·R-31이다 | 코드 확인 (지침 문장) |
| R-25 | [지침] 1단계 threat model | `$threat-model`을 한 번 돌리거나 제공된 모델을 쓴다. 제공된 schema-valid canonical `threatModel` 객체는 바꾸지 않고 보존한다. 그 밖에는 제공된 텍스트나 생성한 Markdown을 `{ "format": "markdown", "content": "<model text>" }`로 보존하고 `origin`은 `provided` 또는 `generated`다. 사용자가 더 좁게 요청하지 않으면 저장소를 모델링하고 모델의 실제 범위를 변경 파일 범위와 따로 기록한다. 곧바로 그 모델과 빈 findings로 `complete:false` 의미 초안을 저장한다. host가 `threatmodel.md`를 쓰고 이후 phase는 같은 canonical 모델을 유지한다. 내용 규칙은 [threat-model.md](./threat-model.md)(행 8) | 코드 확인 (지침 문장) |
| R-26 | [지침] 2단계 review item | `prepare_codex_security_review_items`로 변경 파일 목록을 준비하고 `list_codex_security_review_items`의 모든 페이지를 읽는다. 변경 동작을 설명하는 데 필요한 만큼만 변경되지 않은 지원 파일을 검토한다 | 코드 확인 (지침 문장). 도구 동작은 R-11~R-16, [candidate-discovery.md](./candidate-discovery.md) R-08·R-09 |
| R-27 | [지침] 3단계 발견 | `$finding-discovery`를 compact diff 모드로 인벤토리 전체에 돌린다. 독립 배정은 가용 worker에 나누고 배정되지 않은 파일은 부모가 직접 검토한다. 독립적으로 취약한 instance는 따로 다룰 수 있게 두고 후보 전체를 `record_codex_security_discovery_candidates`로 한 번 기록한다. ranked worklist, finding별 ledger, discovery report를 만들지 않는다 | 코드 확인 (지침 문장). 기록 쪽은 [candidate-discovery.md](./candidate-discovery.md) R-01·R-05·R-10 |
| R-28 | [지침] 4단계 검증과 공격 경로 | 후보가 있으면 `$validation`을 한 번 돌리고, 이어 `reportable` 또는 `deferred`로 표시된 후보에 `$attack-path-analysis`를 한 번 돌린다. 위치, 증거, 영향받는 instance, 풀리지 않은 질문을 보존한다. `$validation`은 "후보가 있으면"이라는 조건이 붙고, 후보가 없을 때 두 skill을 돌리지 않는다는 점은 이 조건에서 읽은 것이다(후보 없는 경우의 `validations: []` 호출 여부는 지침에 없다) | 코드 확인 (지침 문장). 각 도구의 입력 검사는 [candidate-validation.md](./candidate-validation.md) R-12, [attack-path-severity.md](./attack-path-severity.md) R-12 |
| R-29 | [지침] 5단계 checkpoint와 ledger → draft 매핑 | `references/final-report.md`를 읽고 finding, review state, 완료 계약을 따른다. 결정이 나올 때마다 `record_codex_security_scan_draft`로 `complete:false` 의미 checkpoint를 저장하고, 풀리지 않은 후보와 원래 증거는 `reviewState.deferred`에 남긴다. 검토가 정리되면 보존한 모델, findings, review state로 `complete:true`를 낸다. 저장된 surface ID를 재사용하고, 끝난 generic task는 `reviewState.resolvedDeferred: [{ id, reason }]`로 닫는다. 자세한 write-up과 hardening 계획은 요청 시의 선택 산출물이다. compact diff 후보의 결과는 다음 순서로 옮긴다: (1) validation `reportable`이고 attack-path `reportable`이면 finding(고유 instance와 모든 관련 위치), (2) 어느 단계든 `deferred`이면 `needs_follow_up` surface와 증명 공백이 든 deferred 작업, (3) validation `not_applicable`이면 `not_applicable` coverage, (4) validation `suppressed` 또는 attack-path `ignore`이면 `rejected` coverage. 필요한 단계 기록이 없으면 그 후보는 가진 증거와 함께 미해결로 남기고 추가 조정 pass나 중복 receipt를 만들지 않는다 | 코드 확인 (지침 문장). 이 매핑을 코드가 검사하지 않는 점은 [candidate-discovery.md](./candidate-discovery.md) R-23 |
| R-30 | [지침] 6단계 완료 | SDK가 완료를 소유하는 경우를 뺀 나머지는 `complete_codex_security_scan`을 한 번 부른 뒤 `get_codex_security_completed_scan`으로 읽는다. finalization이 `report.md`와 SARIF를 만든다. 생성된 보고서, 실제 coverage 한계, 측정된 token 사용량(있을 때), 확인된 finding의 Codex review comment를 돌려준다. `cancel_codex_security_scan`은 사용자가 명시적으로 취소할 때만, `fail_codex_security_scan`은 확정된 복구 불가 blocker에만 쓰고 복구가 가능한 동안 durable scan을 보존한다 | 코드 확인 (지침 문장). 도구 쪽은 [caller-modes.md](./caller-modes.md) R-32·R-43 |
| R-31 | [지침] 완전성 책임과 no-findings 금지 | 모든 변경 파일과 모든 후보는 reviewed, resolved, 명시적 unfinished 중 하나로 설명돼야 한다. 불완전한 검토를 no-findings 주장으로 바꾸지 않는다(`final-report.md`는 중지된 scan이 finding 0개여도 clean scan 결론이 아니라고 한다) | 코드 확인 (지침 문장) |

#### 코드가 하지 않는 것과 모델 준수

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-32 | [강제 없음] 변경 파일 검토 여부 | 인벤토리 파일을 읽는 코드는 목록 조회와 후보 위치 검사(in-scope 판정)뿐이다. 초안(`record_codex_security_scan_draft`)과 확정이 "변경 파일마다 reviewed·resolved·unfinished 설명이 있는지"를 인벤토리와 대조하는 코드는 찾지 못했다. `reviewItemsCompleted`·`reviewItemsTotal` 같은 진행 수치도 모델이 보고하는 값이다 | 코드 확인 (부재 주장은 2.1 부재 주장 6) |
| R-33 | [강제 없음] 후보가 diff와 겹치는지 | 후보 위치는 파일이 인벤토리(in-scope)에 있는지와 줄 범위가 파일 줄 수 안인지만 검사한다. 위치가 변경된 줄(hunk)과 겹치는지, 변경으로 새로 생긴 취약점인지를 검사하는 코드는 찾지 못했다. 도구는 `relevant_lines`를 입력에서 거부한다([candidate-discovery.md](./candidate-discovery.md) R-10, U-01). "변경과 겹치는 곳만 `relevant_lines`를 쓴다"는 지침이 도구에 대응 필드가 없는 점은 같은 문서의 U-01이다 | 코드 확인 (부재 주장은 2.1 부재 주장 7) |
| R-34 | [강제 없음] 모델이 변경 줄을 어떻게 보는가 | helper는 `git diff --raw`(path와 status)만 쓴다. 이 SHA의 helper, 도구, skill 어디에도 hunk 본문(`git diff -U`, `--patch`)을 만들어 모델에게 전달하는 코드는 없다. `git diff` 나 `git show`를 실행해 변경 줄과 baseline 내용을 읽는 일은 모델이 shell로 하는 일이고, 어떤 명령을 쓰는지 skill도 지정하지 않는다. 그래서 "삭제 파일은 baseline revision 내용으로 본다"(R-20)는 지침은 모델이 `<baseRevision>:<path>`를 읽는다는 가정이고 코드가 보장하지 않는다 | 코드 확인 (부재 주장은 2.1 부재 주장 7) / 모델의 실제 방식은 미확인 |
| R-35 | 모델이 [지침] R-20~R-31을 따르는가: scan 정체 유지, 인벤토리 전체 읽기, 단계 한 번씩, checkpoint 시점, 완료 호출, no-findings 금지 | 실행하지 않았다. 서버가 하는 것은 R-01~R-17과 candidate·validation·attack-path 도구 검사, 소유·claim 검사뿐이다 | 미확인 |

- 불변식:
  - 도구 경로의 diff scan은 시작 시점에 고정된 base·head(그리고 `working_tree`의 digest)에 묶이고, 그 값은 모델 입력으로 바뀌지 않는다(R-06). 인벤토리는 `prepare` 호출 시점의 Git 상태에서 다시 계산한다(R-12, R-13).
  - `commit`·`range`의 인벤토리는 Git 객체(`<base>..<head>`)로만 정해지므로 작업 트리 상태와 무관하다. `working_tree`의 인벤토리는 호출 시점의 작업 트리를 읽는다(R-13, R-14).
  - 인벤토리 파일은 항상 이전 완전본 또는 새 완전본이다(R-15, R-16).
- 미결정:

| U-ID | 관련 R-ID | 질문 | 구현 영향 | 확인 방법 |
|---|---|---|---|---|
| U-01 | R-34, R-20 | 모델이 변경 줄(hunk)과 삭제 파일의 baseline 내용을 어떤 명령과 형식으로 읽는가. 코드와 skill 어디에도 지정이 없다 | 재구현하려면 모델에게 `git diff`·`git show <base>:<path>` 같은 읽는 방법을 prompt에 줄지 정해야 한다. 이 스펙은 그 방법을 규정하지 않는다 | 실제 diff scan의 Codex 세션 기록(어떤 shell 명령을 썼는지) 또는 `evals/`의 diff 사례. 열지 않았다 |
| U-02 | R-05, R-21 | "PR"을 모델이 `range`로 바꿀 때 base를 PR 대상 branch의 tip으로 둘지 merge-base로 둘지, 그리고 그 판단이 어디에 정해져 있는가. 코드는 직접 비교(`<base>..<head>`)만 하고 skill은 "정확한 Git range를 해석한다"고만 한다 | PR 변경이 대상 branch의 최신 변경을 포함해 보일 수 있다. 재구현은 PR → range 변환 규칙(merge-base 사용 여부)을 정해야 한다 | GitHub Action(`github-action/src/main.ts`)이 `cs scan`에 넘기는 base 값(행 17, 이번 범위 밖), 또는 Codex 데스크톱이 diffTarget을 만드는 방식(레포 밖) |
| U-03 | R-09 | SDK-owned `working_tree`(`DiffTarget.workingTree({ base })`)에서 base가 HEAD가 아닐 때 인벤토리와 progress가 의도대로 동작하는가. workbench 등록은 base를 HEAD로 제한하지 않지만 도구 경로(R-03)는 제한한다 | 같은 `working_tree`가 호출자에 따라 허용 base가 다르다. SDK의 `refs`처럼 임의 base를 쓰는 것이 의도인지 알 수 없다 | `register-cli-scan`의 working_tree 후속 코드와 원본 테스트(`sdk/typescript/tests-ts/` 중 working tree 사례). 열지 않았다 |

- 확인 한계:
  - 실행하지 않았다(`cs`, MCP, helper, Python, Git). 오류 문구는 소스에서 옮겼고 실제 출력은 보지 않았다.
  - helper는 빌드 산출물 `mcp/helpers.mjs`로 실행되고 이 파일은 레포에 추적되지 않는다. 소스(`helpers-main.ts` → `generate-inventory.ts`)와 같다고 가정했다.
  - Git 동작(rename 감지 기본값, `ls-files --others --exclude-standard`, `git diff <base>`와 `--cached`의 의미)은 Git의 문서화된 동작을 전제로 한 읽기이고 이 레포 코드가 정하지 않는다. 신뢰 Git 실행 파일 선택(`trustedTools`)과 Windows 경로 해석은 열지 않았다.
  - SDK-owned diff에서 모델이 `record_codex_security_scan_draft`를 쓸 수 없을 때 직접 쓴 manifest의 target 필드(특히 `commit`·`range`의 `snapshotDigest`, SDK는 `contentDigest`가 있는 `working_tree`만 환경 변수로 넘긴다)가 finalizer에서 어떻게 채워지는지는 행 9 범위라 열지 않았다.

### 1.5 필수 코드 참조 [필수]

기준은 frontmatter SHA다. 라이선스는 Apache-2.0(overview 1절)이라 인용을 막지 않는다.

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:6-35` | skill 지침 원문(35줄) | R-20~R-31 |
| C-02 | `plugins/codex-security/mcp-app/server.ts:103-120` `diffTargetSchema`, `:162-179` `startPromptOnlyScanSchema`, `:637-679` 도구 등록, `:1993-1999` `wholeTargetScope`, `:2266-2277` `diffTargetFields` | `diffTarget` 입력 스키마와 `mode`·`scope` 검사, workbench 인자 변환 | R-01 |
| C-03 | `plugins/codex-security/scripts/workbench_setup.py:44-130` `resolve_git_commit`·`require_diff_target`, `:133-173` `inspect_setup_values`, `:176-184` `require_review_changes_target`, `:198-220` `require_scope` | `diffTarget` 해석·검증 전체(R-02~R-05) | R-02~R-05 |
| C-04 | `plugins/codex-security/scripts/workbench_constants.py:6` `DIFF_TARGET_KINDS`, `:68-72` `EMPTY_GIT_TREE(S)` | diff kind 목록과 빈 tree ID | R-04 |
| C-05 | `plugins/codex-security/scripts/workbench_db.py:843-1023` `_start_prompt_driven_scan`, `:706-716` `require_working_tree_unchanged`, `:2600-2606` `diff_target_summary` | 도구 경로 scan 생성, 시작 경합 검사, 요약 문구 | R-06, R-07 |
| C-06 | `plugins/codex-security/scripts/workbench_db.py:1631-1660` `register-cli-scan`의 diff 처리, `:1885-1887` `parse_scan_recipe`의 diff 검사 | SDK-owned diff 해석 | R-09 |
| C-07 | `plugins/codex-security/scripts/workbench_scan_start.py:63-90` `scan_target_identity`, `:112-137` `scan_diff_identity`·`stored_diff_target` | diff scan의 revision·digest 저장 형태와 context 복원 | R-06 |
| C-08 | `plugins/codex-security/scripts/workbench_target.py:44-70` `committed_diff_snapshot_digest`·`diff_snapshot_digest`, `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:3090-3128` | `snapshotDigest` 계산식 | R-10 |
| C-09 | `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:3362-3366` `coverageMode`, `:3378-3383` `inventoryStrategy`, `plugins/codex-security/scripts/workbench_source_scopes.py:28-38` `expected_target_kinds` | coverage mode와 target kind | R-10 |
| C-10 | `sdk/typescript/src/targets.ts:57-119` `DiffTarget`, `:121-132` `NormalizedTarget`, `:565-595` `normalizeTarget`, `:678-714` `validateCommittedDiffCheckout`, `:789-835` `requireGitRepository`·`resolveGitRef` | SDK diff 대상 정규화와 clean checkout 검사 | R-08 |
| C-11 | `sdk/typescript/src/api.ts:6566-6570` `skillNameFor`, `:6631-6634` `targetInstruction`의 diff 분기, `:6637-6683` `scanRecipe` | skill 선택, diff 대상 prompt 문구, recipe 형태 | R-08, R-09 |
| C-12 | `plugins/codex-security/mcp-app/src/artifact-inventory.ts:29-119` `prepareCodexSecurityReviewItems` | helper 호출 인자 조립 | R-11, R-16 |
| C-13 | `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:267-285, 359-426, 446-454` `generateInventory`의 diff 분기와 출력, `:203-234` `inventoryOutput`·`replaceInventory`, `:492-594` `inventoryCommand` | 인벤토리 helper의 입력, 선택 후 내용 확인, 출력, 종료 코드 | R-11, R-14~R-16, R-19 |
| C-14 | `plugins/codex-security/mcp-app/src/helpers/inventory-git.ts:820-848` `gitProcess`, `:1117-1158` `changed`, `:1159-1201` `changedPaths`, `:1204-1271` `blobSamples` | Git 질의, 일반 파일 모드 필터, local-patch 합성, blob 읽기 | R-12, R-13, R-17 |
| C-15 | `plugins/codex-security/mcp-app/src/helpers/source-preview.ts:26-30, 94-127` `isBinarySample`·`createSourceSampler`, `plugins/codex-security/mcp-app/src/helpers/inventory-paths.ts:94-108` `linkedParent`·`sourceMetadata` | 텍스트 판정, symlink 상위 검사, 제외 디렉터리 | R-13, R-14 |
| C-16 | `plugins/codex-security/scripts/workbench_target.py:462-548` `run_git_changed_paths`·`git_changed_paths`, `:551-585` `diff_scope_file_count`, `:588-664` `candidate_source_lines` | Python 미러 | R-18 |
| C-17 | `plugins/codex-security/references/final-report.md:42-49` | compact diff 후보 → finding·coverage 매핑 원문 | R-29 |
| C-18 | `plugins/codex-security/references/investigation-time-budget.md:1-11`, `sdk/typescript/src/scan-time-budget.ts:1-36` | 시간 예산 템플릿과 SDK 렌더링 | R-23 |
| C-19 | `plugins/codex-security/references/scan-runtime.md:1-13` | 위임·fallback·diff phase 지침 원문 | R-22, R-24 |

### 1.6 수락 사례 [필수]
출처: 모두 구현에서 도출(원본 테스트는 열지 않았다). 사례는 실행하지 않았다. SHA와 digest 값은 조건으로 적는다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-04, R-06 | Git worktree 루트 `/r`에서 HEAD commit `C`가 부모 `P`를 하나 가진다. `diffTarget:{kind:"commit", headRevision:"HEAD"}`, `scope:"."` | scan이 `running`으로 생성되고 diff 식별은 `{kind:"commit", baseRevision:P의 SHA, headRevision:C의 SHA}`다. `targetSummary`가 비어 있었다면 `Commit <C 앞 7자>`다. `snapshotDigest`는 `codex-security-snapshot/v1:sha256:`으로 시작하고 `commit`·P·C로 정해진다 |
| T-02 | R-04 | root commit `C`(부모 없음), sha1 저장소. `kind:"commit"`, `headRevision:C` | `baseRevision`은 `4b825dc642cb6eb9a060e54bf8d69288fbee4904`(빈 tree)다. 이때 base는 commit이 아니라 tree ID다 |
| T-03 | R-04 | T-01의 `C`에 `baseRevision`으로 `P`가 아닌 다른 commit을 준다 | "Commit base revision must match the selected commit's parent."로 거부, scan 생성 없음 |
| T-04 | R-05 | `kind:"range"`, `baseRevision`과 `headRevision`이 같은 commit | "Base and head revisions must identify different commits."로 거부 |
| T-05 | R-03 | `kind:"working_tree"`를 준 뒤 다른 commit을 checkout해 HEAD가 바뀌었다고 가정하고 `baseRevision`에 이전 HEAD를 준다. 또는 `baseRevision`을 HEAD가 아닌 branch로 준다 | "Repository HEAD changed after these working-tree changes were selected. Select Uncommitted changes again."로 거부 |
| T-06 | R-01 | `mode:"diff"`, `scope:"src"` | "Review changes prompt-only scans require the whole target; use scope '.'."로 거부(`workbench`를 부르기 전). 같은 호출에 `diffTarget`이 없으면 "Review changes prompt-only scans require diffTarget." |
| T-07 | R-02 | `targetPath`가 Git 저장소의 하위 디렉터리 `/r/pkg` | "Review changes requires the checked-out Git repository root as the target."로 거부 |
| T-08 | R-12, R-14, R-15 | `commit` diff. 변경: 텍스트 파일 `b.ts` 추가, `a.ts` 수정, `old.ts` 삭제, NUL이 든 `logo.png` 추가, `link`(symlink) 추가, `x.ts`→`y.ts` 이름 변경(rename 감지 켜짐), submodule 포인터 변경 | `in_scope_files.txt`는 `a.ts`, `b.ts`, `old.ts`, `y.ts`를 바이트 순으로 한 줄씩 담는다. `logo.png`, `link`, submodule 경로, `x.ts`는 없다. `old.ts`의 내용은 base blob에서 읽은 것이다. stdout은 `Recorded 4 in-scope files.` |
| T-09 | R-13, R-14 | `working_tree` diff. 추적 중이지만 `.gitignore`에도 든 `build/out.js`를 수정, 추적되지 않고 무시되지 않는 `notes.md` 추가, 추적되지 않고 무시되는 `dist/x.js`, 추적 파일 `gone.ts` 삭제 | 목록은 `build/out.js`, `notes.md`, `gone.ts`다. `dist/x.js`는 없다. `gone.ts`는 base blob으로 NUL 검사를 한다. 작업 트리의 `notes.md`가 binary면 빠진다 |
| T-10 | R-15, R-16 | 변경된 경로에 줄바꿈이 든 파일명이 하나 있다 | helper가 "Git changes contain a path that cannot fit in the file inventory"로 종료 코드 2, `prepare`는 "review_items: the scan inventory helper failed: …"를 던지고 기존 `in_scope_files.txt`는 그대로다 |
| T-11 | R-15 | `base`와 `head`의 tree가 같다(range) | `in_scope_files.txt`가 빈 파일이고 `prepare`는 `{ reviewItemsTotal: 0 }`을 돌려준다. 코드는 이를 거부하지 않는다 |
| T-12 | R-08 | SDK에서 `DiffTarget.refs({ base:"main", head:"HEAD" })`, 작업 트리에 미커밋 변경이 있다 | `InvalidTargetError`("Committed-diff scans require a clean repository checkout. Commit, stash, or remove local changes and retry. …"), scan 등록 전에 중단 |
| T-13 | R-08, R-09 | SDK `DiffTarget.workingTree()`와 `mode:"deep"` | `validateMode`가 "Deep mode supports repository and path targets only."로 거부([caller-modes.md](./caller-modes.md) R-03). `DiffTarget.workingTree()` 자체는 `head`를 받지 않는다 |
| T-14 | R-29 | compact diff 후보 3개: A(validation `reportable`, attack-path `reportable`), B(validation `suppressed`), C(validation `reportable`, attack-path `deferred`) | skill 지침대로면 A는 finding, B는 `rejected` coverage, C는 `needs_follow_up` surface와 deferred 작업(증명 공백 포함)이다. 코드는 이 대응을 검사하지 않으므로 모델이 틀려도 도구는 막지 않는다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map [필수]

경로는 모두 `173483d7c658be7a512c93d9559bf01a05d5b196` 기준이다. 부재 주장의 검색 범위는 이 표 아래에 모았다.

| R-ID / T-ID | 근거 (repo@SHA `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01 | `plugins/codex-security/mcp-app/server.ts:103-120, 162-179, 637-679, 1993-1999, 2266-2277` | 도구 등록부를 읽음. strict 위반 메시지 형식은 MCP SDK 몫이라 열지 않음 |
| R-02 | `plugins/codex-security/scripts/workbench_setup.py:24-32, 133-173, 176-184, 187-220`, `plugins/codex-security/scripts/workbench_target.py:1793-1797` `require_git_worktree_head` | `git_target_metadata`(isGit, isWorktree, hasHead)의 내부는 열지 않음 |
| R-03 | `plugins/codex-security/scripts/workbench_setup.py:76-95`, `plugins/codex-security/scripts/workbench_target.py:799-805` `worktree_content_digest` | digest 계산 본문(`_git_content_digest`, 929 이후)은 열지 않음. 제출된 digest가 있고 다르면 거부한다는 비교만 확인 |
| R-04 | `plugins/codex-security/scripts/workbench_setup.py:96-125`, `plugins/codex-security/scripts/workbench_constants.py:68-72` | 첫 `parent` 줄만 본다(다중 부모의 나머지는 무시)는 코드 읽기. 실제 merge commit에서의 결과는 실행하지 않음 |
| R-05 | `plugins/codex-security/scripts/workbench_setup.py:44-58, 126-130`, `plugins/codex-security/scripts/workbench_target.py:498-504` | `A..B`가 `git diff`에서 두 tree의 직접 비교라는 것은 Git 문서 동작(추론) |
| R-06 | `plugins/codex-security/scripts/workbench_db.py:843-1023, 2600-2606`, `plugins/codex-security/scripts/workbench_scan_start.py:63-90, 112-137`, `plugins/codex-security/scripts/workbench_db.py:360-390, 2923` | `insert_running_scan`(INSERT 본문)은 열지 않음. 저장 열 이름은 workspace INSERT(957-964)에서 확인 |
| R-07 | `plugins/codex-security/scripts/workbench_db.py:706-716, 743-772, 877-901, 1660` | "감시 코드 부재"는 2.1 부재 주장 2 |
| R-08 | `sdk/typescript/src/targets.ts:57-119, 565-595, 678-714, 759-771, 789-835`, `sdk/typescript/src/api.ts:5783-5808` | `gitOutput`의 신뢰 Git 선택은 열지 않음 |
| R-09 | `plugins/codex-security/scripts/workbench_db.py:1605-1660, 1855-1888`, `sdk/typescript/src/api.ts:3030-3072, 6637-6683` | base=head 비거부는 2.1 부재 주장 3. `scan.mode`가 `diff`라는 점은 1645행 `mode = "diff" if diff_target is not None` |
| R-10 | `plugins/codex-security/mcp-app/src/artifact-scan-draft.ts:3085-3128, 3362-3366, 3378-3383`, `plugins/codex-security/scripts/workbench_source_scopes.py:28-38`, `plugins/codex-security/scripts/workbench_db.py:396-420, 455-487`, `plugins/codex-security/scripts/review_state.py:40-52` | 초안 구성과 manifest 검증 중 diff 관련 줄만 읽음. 그 밖은 행 9 |
| R-11 | `plugins/codex-security/mcp-app/src/artifact-inventory.ts:29-119`, `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:359-368, 492-523`, `plugins/codex-security/mcp-app/helpers-main.ts:107-117` | POSIX stdin 전달 형식은 `artifact-inventory.ts:82-102`에서 읽음. 받는 쪽(`helpers-main.ts` 이전 구간)은 열지 않음 |
| R-12 | `plugins/codex-security/mcp-app/src/helpers/inventory-git.ts:1117-1158, 1159-1165`, `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:369-389` | 모드 필터(`100` 접두)는 1152-1155행. 실제 `--raw` 출력 형식은 Git 동작 |
| R-13 | `plugins/codex-security/mcp-app/src/helpers/inventory-git.ts:1159-1201`, `plugins/codex-security/mcp-app/src/helpers/inventory-paths.ts:94-108`, `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:381-426` | 후보 합성과 `localStatus`는 코드 읽기. Git의 `--cached`와 작업 트리 의미는 Git 동작 |
| R-14 | `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:381-426`, `plugins/codex-security/mcp-app/src/helpers/inventory-git.ts:1204-1271`, `plugins/codex-security/mcp-app/src/helpers/source-preview.ts:26-30, 94-141` | `createSourceSampler`는 모든 바이트를 검사하고 BOM 구분을 한다. 읽기 오류를 binary로 취급하는 것은 `sampleFile`의 catch(138-140). 제한 부재는 2.1 부재 주장 4 |
| R-15 | `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:203-234, 417-424, 446-454, 584-588` | |
| R-16 | `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:372-380, 590-593`, `plugins/codex-security/mcp-app/src/helpers/inventory-git.ts:1122-1143`, `plugins/codex-security/mcp-app/src/helpers/rank-worklists.ts:151-164` `reportCommandError`, `plugins/codex-security/mcp-app/src/artifact-inventory.ts:95-116` | `inventoryCommand`가 inventory면 종료 코드를 2로 고정함(592) |
| R-17 | `plugins/codex-security/mcp-app/src/helpers/inventory-git.ts:820-848, 959-970` | `repositoryEnvironment` 목록의 내용은 열지 않음 |
| R-18 | `plugins/codex-security/scripts/workbench_target.py:462-585, 588-664`와 R-12~R-14의 TS 코드 | 두 구현을 줄 단위로 대조해 구조가 같음을 확인했고 실행 비교는 없음 |
| R-19 | `plugins/codex-security/mcp-app/src/helpers/generate-inventory.ts:47-51, 277-285, 455-490`, `plugins/codex-security/mcp-app/src/helpers/rank-worklists.ts:14-18, 81-90`, `plugins/codex-security/mcp-app/helpers-main.ts:107-117`, `plugins/codex-security/skills/security-scan/references/scan-artifacts-and-ledger.md:1-30`, `plugins/codex-security/skills/finding-discovery/SKILL.md:17` | 부재 주장 5 |
| R-20 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:8, 24` | |
| R-21 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:12-14`, `plugins/codex-security/references/artifact-storage.md:3-9` | |
| R-22 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:16`, `plugins/codex-security/references/scan-runtime.md:1-13`, `plugins/codex-security/references/access-advisory.md:1-11` | |
| R-23 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:18`, `plugins/codex-security/references/investigation-time-budget.md:1-11`, `sdk/typescript/src/scan-time-budget.ts:1-36`, `sdk/typescript/src/api.ts:3663-3676` | SDK mode가 `standard`이면 diff target에도 적용된다는 것은 `validateMode`(targets.ts 759-771)가 `standard`·`deep`만 받고 diff target + `deep`을 거부하는 점에서 읽음 |
| R-24 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:20`, `plugins/codex-security/references/scan-runtime.md:7` | |
| R-25 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:28`, `plugins/codex-security/references/artifact-storage.md:49` | |
| R-26 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:29`, `plugins/codex-security/mcp-app/src/server/compact-artifact-tools.ts:81-106` | |
| R-27 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:30`, `plugins/codex-security/references/scan-artifacts.md:33-49` | |
| R-28 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:31`, `plugins/codex-security/references/scan-artifacts.md:41-45` | |
| R-29 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:32`, `plugins/codex-security/references/final-report.md:30-49` | 코드가 매핑을 검사하지 않는 근거는 [candidate-discovery.md](./candidate-discovery.md) R-23 |
| R-30 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:26, 33`, `plugins/codex-security/references/final-report.md:55-61` | |
| R-31 | `plugins/codex-security/skills/security-diff-scan/SKILL.md:35`, `plugins/codex-security/references/final-report.md:61` | |
| R-32 | 부재 주장 6 | 아래 검색 |
| R-33 | 부재 주장 7 | 아래 검색 |
| R-34 | 부재 주장 7 | 아래 검색 |
| R-35 | 실행하지 않음 | |
| T-01~T-14 | 구현에서 도출. 각각 R-ID의 근거 줄 | |

부재 주장의 검색 범위(모두 기준 SHA, 원본 clone `plugins/codex-security`와 `sdk/typescript`에서 비테스트 소스):

1. "merge-base를 계산하지 않는다": `merge-base`, `merge_base`를 `plugins/codex-security/scripts`, `plugins/codex-security/mcp-app/src`, `plugins/codex-security/mcp-app/server.ts`, `sdk/typescript/src/targets.ts`에서 검색했고 diff 대상 해석 코드에는 나오지 않았다(다른 곳의 사용은 이 스펙 범위 밖이라 확인하지 않음). 동적 인자 조립으로 만들어지는 `merge-base` 호출은 문자열 검색으로 놓칠 수 있다.
2. "시작 후 작업 트리 변경을 감시·거부하는 코드 없음": `require_working_tree_unchanged`와 `require_scan_target_unchanged`의 호출 지점을 `plugins/codex-security/scripts/*.py`에서 검색했다. 앞의 것은 시작 경로(`workbench_db.py:772, 1660`)에서만, 뒤의 것은 `get-scan --check-target`(3472-3473)에서만 호출된다. `--check-target`을 넘기는 곳은 SDK의 `validate` 구간(`sdk/typescript/src/api.ts:1113-1128, 1318, 1473`, `sdk/typescript/src/cli.ts:12256-12338`)이고 diff 스캔과 prepare는 넘기지 않는다. SDK의 head drift monitor(`api.ts:3299-3319`)는 경고만 한다. 놓칠 가능성: 이 SHA에서 `get-scan`을 다른 별칭으로 부르는 호출.
3. "range의 base=head를 SDK 경로가 거부하지 않는다": `different commits`, `must identify`를 레포 전체(테스트 제외)에서 검색했고 `workbench_setup.py:129`(도구 경로) 하나만 나왔다. `register-cli-scan`(`workbench_db.py:1632-1640`)과 `normalizeTarget`에는 같은 검사가 없다.
4. "인벤토리 크기·개수 제한이 없다": `generate-inventory.ts`, `inventory-git.ts`의 diff 경로에서 상한 상수(`limit`, `max`, `MAX`)를 읽었고 diff 선택 경로에서 쓰이는 상한은 보지 못했다(`PREVIEW_READ_BYTES`는 미리보기 용도이고 binary 판정은 전체 바이트). 프로세스 출력 크기 제한(`collect`의 버퍼)은 열지 않았다.
5. "`make-diff-rank-input` 호출처": 레포 전체에서 `make-diff-rank-input`을 검색했다(테스트 제외). 결과는 `helpers-main.ts`(디스패치), `generate-inventory.ts`(구현), `security-scan/references/scan-artifacts-and-ledger.md`(문서의 명령 예시 4곳)뿐이다. `plugins/codex-security/skills/security-diff-scan/`, `sdk/typescript/src/`에는 없다. 쉘 문자열이 변수로 조립되는 호출은 놓칠 수 있다. 같은 검색에서 `generate_rank_input.py`는 `git ls-files`에 없다(SDK `targetInstruction`이 있으면 쓰는 구형 생성기이고 이 SHA에서는 파일이 없어 쓰이지 않는다, `api.ts:6587-6595`).
6. "변경 파일 coverage를 인벤토리와 대조하는 코드 없음": `in_scope_files`를 `plugins/codex-security`(테스트 제외)에서 검색했다. 결과는 `artifact-inventory.ts`, `artifact-discovery.ts`, `deep_scan_workbench.py`(Deep), `reserved_artifact_paths.json`, 문서뿐이고 `artifact-scan-draft.ts`, `finalize_scan_contract.py`, `validate_scan_contract.py`에는 없다. 초안 쪽은 `inventoryStrategy`(diff)와 coverage mode만 만든다. 다른 이름(`reviewItems`)으로 같은 파일을 읽는 코드는 `artifact-inventory.ts` 외에 찾지 못했다.
7. "변경 줄(hunk)을 만들어 모델에 전달하는 코드 없음, 후보와 변경 줄의 겹침 검사 없음": `git diff` 계열 호출을 `plugins/codex-security/scripts`와 `mcp-app/src`에서 검색했다. 결과는 `--raw` 기반 변경 목록(`inventory-git.ts`, `workbench_target.py`)과 patch를 검증하는 remediation 쪽(`workbench_remediation.py`)뿐이다. `relevant_lines`는 도구 입력에서 거부된다([candidate-discovery.md](./candidate-discovery.md) T-03). 놓칠 가능성: 모델이 shell로 실행하는 `git diff`는 코드가 아니므로 이 검색 대상이 아니다.

### 2.2 코드 읽는 순서 [선택]

skill(`SKILL.md` 35줄)을 먼저 읽고, 도구 쪽은 `server.ts`의 `start_codex_security_prompt_only_scan` → `workbench_setup.py`의 `require_diff_target`(해석) → `artifact-inventory.ts`의 `prepare` → `generate-inventory.ts`의 diff 분기 → `inventory-git.ts`의 `changed`·`changedPaths` 순으로 따라간다. SDK 경로는 `targets.ts`의 `normalizeTarget` → `api.ts`의 `scanRecipe`와 `targetInstruction` → `workbench_db.py`의 `register-cli-scan` 순이다.

### 2.4 검토 기록 [필수, ready 스펙]
- 방식: 메인 세션 기본 점검(2026-11-16). `python scripts/check.py codex-security`로 인용 줄의 존재를 확인하고(형식·위치 확인일 뿐), 고위험 R-ID 표본을 인용 줄과 검색으로 대조했다. 다른 스펙이 `depends`로 의존하지 않아 독립 검토 조건에는 해당하지 않으나, 미결정 U-01~U-03이 남아 `draft`로 둔다.
- 대조한 R-ID: R-03(`workbench_setup.py` `require_diff_target`가 `working_tree`에서 base·head가 현재 HEAD와 다르면 거부), R-19(`make-diff-rank-input`은 `generate-inventory.ts`의 `inventoryCommand`가 구현하고 호출처는 `security-scan/references/scan-artifacts-and-ledger.md`뿐이라 `security-diff-scan` skill은 부르지 않음. `git grep`으로 재확인)
- 대조하지 않은 R-ID: 위 2개를 제외한 전부. 특히 R-04·R-05·R-07~R-10(상태·거부 규칙, 부재 주장), R-12~R-16(인벤토리 선택·실패, `추론` 포함), R-18(TS·Python 두 구현의 결과 동일성 미확인), R-32~R-34(부재 주장)는 독립 검토 대상이다.
- 재구현: 미수행
