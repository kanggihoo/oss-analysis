---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/evidence/src/unknown.rs
  - crates/engine/src/tools/session_tools.rs
  - crates/engine/src/session.rs
  - crates/engine/src/project.rs
  - crates/engine/src/clean_room.rs
  - crates/engine/src/tools/report_tools.rs
  - crates/ai/src/rebuild/self_check.rs
  - crates/ai/src/rebuild/brief.rs
depends:
  - ./evidence-record.md
status: ready
---

# 미해결 질문 원장 (`Unknown`)

> 아직 답하지 못한 질문을 중요도·영역·확인 방법(probes)·찬반 증거 id와 함께 기록하고, 개정 번호(revision)로 낡은 수정을 거부하며 상태를 바꾸고, 해결됐다고 표시한 질문이 해결 설명과 실제로 존재하는 증거를 갖췄는지 따로 검사한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 호출자(사람·에이전트)가 `core_unknown_add`로 질문을 기록한다. 질문과 영역(domain)에서 id `unk_<16 hex>`가 정해지고 revision 1, 상태 `open`으로 시작한다(R-01, R-02).
2. 세션 메모리에 넣고, 프로젝트가 열려 있으면 `unknowns/<id>.json`에도 쓴다(R-03, R-12).
3. 조사하면서 `core_unknown_edit`로 상태·중요도·probes·증거 id·해결 설명을 바꾼다. 호출자는 읽었던 revision을 `based_on_revision`으로 보내야 하고, 다르면 거부된다(R-05, R-06).
4. 수정 시점에는 "해결됨"에 근거가 있는지 거의 검사하지 않는다(R-07, R-08). 검사는 읽기 전용 도구 `core_unknown_verify`가 따로 한다(R-11).
5. `core_unknowns_show`로 상태·중요도·영역별로 걸러 본다(R-04). 보고서(행 4)와 리빌드 자체 검사(행 7)가 `resolved`가 아닌 질문을 "열린 질문"으로 읽는다(1.2).

### 1.2 범위·통합 지점
- 제공: `Unknown` 레코드와 id 규칙, 도구 4개(`core_unknowns_show`·`core_unknown_add`·`core_unknown_edit`·`core_unknown_verify`)의 입력·출력·오류, revision 검사, 해결 검사, 프로젝트 파일 저장·로드.
- 제외:
  - 보고서의 "Open questions" 절 렌더(행 4 [investigation-report.md](investigation-report.md)).
  - 리빌드 루프가 열린 질문을 읽어 에이전트에 돌려주는 흐름(행 7)과 빌더 브리프의 지시 문구(행 8). 경계만 아래에 적는다.
  - 증거 묶음 형식(선행 [evidence-record.md](evidence-record.md) R-19·R-20). unknown은 그 묶음에 함께 실린다.
- 외부 의존·선행 계약:
  - 선행 evidence-record: `canonical_json`·`sha256_hex`(id 계산), `resolve_evidence`·`verify`(R-11), `ToolError`·`parse_params`(오류), 원자적 쓰기.
  - 소비자 경계(이 스펙이 정하지 않음): 보고서는 `status != resolved`인 unknown을 열린 질문으로 쓴다(`report_tools.rs:297`). 리빌드 자체 검사 `open_questions`는 작업 공간의 조사 폴더를 프로젝트로 열어 `load_unknowns()`로 디스크에서 직접 읽고, `status != resolved`만 남겨 severity 내림차순·question 오름차순으로 정렬한다(`self_check.rs:59-71`). 빌더 브리프는 "답 못 한 질문은 `core_unknown_add`로 기록하고, 나중에 답하면 `core_unknown_edit`(status resolved, resolution, 증거 id)로 닫으라"고 지시한다(`brief.rs:29`).
- 소유 상태·부작용: 세션의 `unknowns` 맵(id → Unknown, 세션 수명), 프로젝트 폴더의 `unknowns/*.json`. unknown은 증거 레코드가 아니어서(`ToolOutput::Value`로 반환) 원장에 들어가지 않고 해시 id도 없다. 조사 작업 기억(행 3)의 상태와도 연결 필드가 없다.

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `Unknown` | map `{id, revision, question, severity, domain, status, probes, evidence_for, evidence_against, resolution?}` | JSON 칸 이름은 그대로. `resolution`은 None이면 빠진다. `probes`·`evidence_*`는 없으면 빈 목록으로 읽는다. 형식 버전 칸은 없다. |
| `id` | string | `unk_` + R-01의 hex 16자. 처음 기록할 때 정해지고 바뀌지 않는다. |
| `revision` | u64 | 1부터 시작, 수정이 받아들여질 때마다 1 증가(포화 덧셈). |
| `severity` | enum `low` < `medium` < `high` < `critical` | 기본 `medium`. 순서 비교가 가능하다(소비자의 정렬에 쓰임). |
| `status` | enum `open` / `investigating` / `blocked` / `contradicted` / `resolved` | 기본 `open`. 상태 사이 전이 제한은 없다(R-10). 각 상태의 뜻은 이름 외에 코드에 정의가 없다. |
| `domain` | string | 영역(`native`, `network`, `ui`, `storage` 등 자유 문자열). 기본 `"general"`. |
| `probes` | list of string | 무엇이 질문을 풀지(도구, 확인할 사실). 자유 문자열. |
| `evidence_for` / `evidence_against` | list of string | 찬반 증거 id. 기록·수정 시 존재 여부를 검사하지 않는다. |
| `core_unknowns_show` | in `{status?, severity?, domain?}` → `{items: [Unknown], total}` | 읽기 전용. |
| `core_unknown_add` | in `{question, domain="general", severity?, probes=[], evidence_for=[], evidence_against=[]}` → `{"result": Unknown}` | 세션 변경. |
| `core_unknown_edit` | in `{unknown_id, based_on_revision, status?, severity?, probes?, evidence_for?, evidence_against?, resolution?}` → `{"result": Unknown}` | 세션 변경. 질문·영역은 바꿀 수 없다. |
| `core_unknown_verify` | in `{unknown_id}` → `{valid: bool, problems: [string], unknown: Unknown}` | 읽기 전용. |
| 저장 파일 | `<project>/unknowns/<id에서 [A-Za-z0-9_]만 남긴 것>.json` | pretty JSON, 원자적 쓰기. |

모든 도구는 알 수 없는 입력 칸을 거부한다(`deny_unknown_fields`). enum 값이 틀리거나 타입이 틀리면 선행 스펙 R-25의 `bad_input`이 된다.

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | `core_unknown_add` | `question`을 trim하고 비면 `bad_input` "question is empty". id는 `sha256_hex(canonical_json({"question": <trim한 질문>, "domain": <domain>}))`의 앞 16자에 `unk_`를 붙인 것. `domain`은 trim하지 않고 빈 문자열도 받는다. severity 생략 시 medium. probes·evidence 목록은 받은 그대로 저장하며 증거 id의 형식·존재를 검사하지 않는다. revision 1, status open, resolution 없음. | 코드 확인 |
| R-02 | 같은 (trim한 질문, domain) 조합이 이미 있음 | `bad_input` "<id> is already recorded", remediation "Use core_unknown_edit to change it." 기존 질문이 resolved여도 같다. 새 기록은 생기지 않는다. | 코드 확인 |
| R-03 | 기록·수정 결과 저장(`put_unknown`) | 프로젝트가 열려 있으면 파일을 먼저 쓰고, 실패하면 그 오류를 돌려주며 메모리 맵은 바꾸지 않는다. 성공하면 메모리 맵에 넣는다(같은 id면 교체). 프로젝트가 없으면 메모리에만 있다. | 코드 확인 |
| R-04 | `core_unknowns_show` | 주어진 조건을 모두 만족하는 것만(status·severity는 enum 일치, domain은 문자열 완전 일치). 순서는 id 오름차순. 쪽 나누기 없음. `total`은 걸러낸 개수. | 코드 확인 |
| R-05 | `core_unknown_edit`의 대상 | 메모리 맵에 그 id가 없으면 `bad_input` "No unknown <id>"(`not_found`가 아님). 있으면 현재 레코드를 복사해 다음 값을 만든다: 준 칸만 바꾸고, 목록 칸(`probes`·`evidence_for`·`evidence_against`)은 준 목록으로 통째로 교체한다(빈 목록을 주면 비워짐, 추가가 아님). `resolution`을 주면 그 문자열로 바꾼다(빈 문자열도 그대로). 한 번 생긴 resolution을 없음으로 되돌리는 입력은 없다. | 코드 확인 |
| R-06 | revision 검사 | `based_on_revision`(필수)이 현재 revision과 다르면 `stale_revision` "<id> is at revision <R>, not <B>", remediation "Read the unknown again and retry with its current revision."(범주 input, retryable true). 같으면 id를 유지하고 revision을 1 올려 교체한다. revision 검사가 R-07보다 먼저다. | 코드 확인 |
| R-07 | 해결 상태의 쓰기 시점 검사 | 거부하는 경우는 하나뿐이다: 현재 상태가 resolved이고 다음 상태도 resolved인데 다음 값의 resolution이 없을 때 `bad_input` "A resolved unknown needs a resolution." 그 밖에는 resolved로 바꿀 때 resolution도 증거도 요구하지 않는다. `Unknown::resolution_is_valid`(resolution이 공백이 아니고 `evidence_for`가 1개 이상)는 정의만 있고 레포 안 호출처가 없다. | 코드 확인 |
| R-08 | 수정 시 증거 id | `evidence_for`·`evidence_against`에 넣는 id를 원장에서 찾지 않는다. 없는 id도 저장된다. | 코드 확인 |
| R-09 | 수정 저장 순서 | 메모리의 레코드를 먼저 교체(revision 증가)한 뒤 R-03 저장을 한다. 파일 쓰기가 실패하면 오류를 돌려주지만 메모리에는 이미 새 revision이 들어가 있고 디스크는 이전 값이다. | 코드 확인 |
| R-10 | 상태 전이 | 다섯 상태 사이 어떤 전이도 허용된다(예: resolved → open). 상태를 바꿔도 resolution과 증거 목록은 그대로 남는다. | 코드 확인 |
| R-11 | `core_unknown_verify` | 대상이 없으면 `bad_input` "No unknown <id>". 있으면 다음 순서로 문제를 모은다: 상태가 resolved가 아니면 "not marked resolved", resolution이 없거나 공백이면 "no resolution text", `evidence_for`가 비면 "cites no evidence", 그리고 `evidence_for`의 각 id를 선행 스펙 `resolve_evidence`로 찾아 실패하면 "<id> not found", 찾았지만 `verify()`가 false면 "<id> failed its integrity check". `evidence_against`는 보지 않는다. 문제가 없으면 `valid` true. 아무것도 바꾸지 않는다. | 코드 확인 |
| R-12 | 프로젝트 저장·로드 | 저장: R-03, 파일명은 id에서 영숫자와 `_`만 남긴 것. 로드(프로젝트 열 때): `unknowns/` 폴더가 없으면 빈 목록, 읽기 실패한 파일은 조용히 건너뛰고, 파싱 실패는 경고 로그 후 건너뛴다. 읽은 것은 메모리 맵에 넣는다(같은 id는 디스크 값으로 교체). | 코드 확인 |
| R-13 | 다른 프로세스가 같은 프로젝트의 unknown을 수정 | 수정은 디스크를 다시 읽지 않고 자기 세션 메모리의 revision만 비교하므로, 두 프로세스가 각자 revision 1에서 수정하면 둘 다 받아들여지고 디스크에는 나중에 쓴 쪽이 남는다. 파일 잠금이 없다(조사 작업 기억은 잠금이 있다, [investigation-memory.md](investigation-memory.md) R-14). | 코드 확인(디스크를 다시 읽지 않음) · 추론(경합 결과) |
| R-14 | 모드·효과 | 네 도구 모두 Core 툴셋, Clean room에서도 허용된다. show·verify는 읽기 전용, add·edit는 세션 변경으로 선언한다. | 코드 확인 |
| R-15 | 증거 묶음 가져오기의 unknown | 같은 id가 없을 때만 그대로 추가하고 revision·상태를 검사하지 않는다(선행 스펙 R-20). | 코드 확인 |

- 불변식: 한 세션 안에서 같은 id의 unknown은 하나다. id는 처음 기록한 (질문, 영역)에서 정해지고, 질문과 영역을 바꾸는 입력이 없으므로 id와 질문은 항상 맞는다(전제: 파일을 손으로 고치지 않음).
- 미결정: 없음.
- 확인 한계: 정적 읽기만 했다. R-11의 "failed its integrity check"는 메모리 원장 레코드가 검증에 실패할 때만 나오는데, 메모리 원장에는 빌더나 검증을 거친 레코드만 들어가므로 실제로는 나오지 않는다고 본다(추론). 디스크에서 변조된 레코드는 `resolve_evidence`가 실패시켜 "not found"로 나온다(코드 확인).

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/evidence/src/unknown.rs:6-90` `UnknownStatus`·`Severity`·`Unknown`·`Unknown::new`·`apply_update`·`resolution_is_valid` | 칸·기본값·id 계산·revision·resolved 거부 조건 | R-01, R-06, R-07 |
| C-02 | `crates/engine/src/tools/session_tools.rs:437-615` 파라미터 구조체·`core_unknowns_show`·`core_unknown_add`·`core_unknown_edit`·`core_unknown_verify` | 입력 칸, 기본값, 오류 문구, 검사 순서 | R-01~R-11 |
| C-03 | `crates/engine/src/session.rs:291-311` `unknowns`·`unknown`·`put_unknown`·`unknown_mut` | 저장 순서 | R-03, R-09 |
| C-04 | `crates/engine/src/project.rs:173-191` `store_unknown`·`load_unknowns` | 파일 이름, 로드 시 건너뛰기 | R-12 |

### 1.6 수락 사례
출처: 사례별 표기

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-06 | `Unknown::new("Where is the % rule implemented?", "native", High)` 후 상태만 investigating으로 바꿔 `apply_update(1, …)`, 같은 값으로 다시 `apply_update(1, …)` (원본 테스트) | id가 `unk_`로 시작, 첫 수정 후 revision 2, 두 번째는 `stale_revision` |
| T-02 | R-05, R-06, R-07, R-11 | `core_unknown_add {question: "Where is the key derived?", severity: "high"}` → `core_unknown_edit {based_on_revision: 1, status: "resolved", resolution: "In kdf()"}` → 같은 edit를 revision 1로 다시 → `core_unknown_verify` (원본 테스트) | 첫 edit 성공(revision 2, 증거 없이 resolved 허용), 두 번째 `stale_revision`, verify `valid: false`(cites no evidence) |
| T-03 | R-01 | `core_unknown_add {question: ["Where is the loop?"]}`를 Agent·MCP·CLI 호출자로 (원본 테스트) | 셋 다 `bad_input`, details.parameter_path `/question`, 메시지에 "expected a string", unknown 0개. 문자열로 다시 보내면 1개 |
| T-04 | R-15 | unknown 1개를 묶음으로 내보내고 새 세션에서 가져오기 (원본 테스트) | `unknowns_added` 1 |
| T-05 | R-02 | `{question: "  q  "}` 추가 후 `{question: "q"}` 추가 (구현에서 도출) | 두 번째는 `bad_input` "… is already recorded" (trim 후 같은 id) |
| T-06 | R-02 | `{question: "q", domain: "ui"}`와 `{question: "q"}` (구현에서 도출) | 둘 다 기록됨(domain이 달라 id가 다름) |
| T-07 | R-07 | `{status: "resolved"}`만 주어 resolution 없이 resolved로 만든 뒤(revision 2), `{based_on_revision: 2, severity: "low"}` 수정 (구현에서 도출) | 두 번째 수정은 `bad_input` "A resolved unknown needs a resolution."; `resolution`을 같이 주면 성공 |
| T-08 | R-08, R-11 | `evidence_for: ["ev_missing"]`로 add 후 resolved·resolution 설정, verify (구현에서 도출) | add·edit 성공. verify `valid: false`, problems에 "ev_missing not found" |
| T-09 | R-05 | probes가 `["a","b"]`인 unknown을 `probes: []`로 수정 (구현에서 도출) | probes가 빈 목록 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-02 | `session_tools.rs:503-538` `RecordUnknownParams`·`default_domain`·`core_unknown_add`, `unknown.rs:51-69` `Unknown::new` | |
| R-03 | `session.rs:301-307` `put_unknown` | |
| R-04 | `session_tools.rs:491-501` `core_unknowns_show`, `session.rs:79` `unknowns: BTreeMap` | |
| R-05 | `session_tools.rs:540-586` `UpdateUnknownParams`·`core_unknown_edit` | |
| R-06, R-07 | `unknown.rs:71-84` `apply_update` | 문서 차이: overview feature map 2행은 "resolved는 해결 설명과 증거 1개 이상 필요"라고 적었으나 쓰기 시점에 강제되지 않는다. `resolution_is_valid`(`unknown.rs:86-89`)는 `grep -rn resolution_is_valid crates apps` 결과 정의 파일 밖 0건 |
| R-08 | `session_tools.rs:569-577` | 증거 id를 보는 코드 없음 |
| R-09 | `session_tools.rs:581-584` | `unknown_mut` → `apply_update` → `put_unknown` 순서 |
| R-10 | `unknown.rs:71-84` | 전이 표가 없음 |
| R-11 | `session_tools.rs:594-615` `core_unknown_verify`, 선행 스펙 R-17 | |
| R-12 | C-04, `session.rs:319-321` `open_project` | |
| R-13 | `session_tools.rs:559-586`, C-04 | edit 경로에 디스크 읽기·파일 잠금 없음을 읽음. 두 프로세스 실행은 하지 않았다 |
| R-14 | `session_tools.rs:116-159` `specs`, `clean_room.rs:24-27` `TOOLS` | |
| R-15 | `session_tools.rs:421-429` | |
| T-01 | `unknown.rs:96-106` `optimistic_concurrency` | 원본 테스트 열람 |
| T-02~T-04 | `session_tools.rs:689-725` `unknown_lifecycle`·`an_unknown_can_be_recorded_after_correcting_its_parameter_type`, `:761-772` `bundle_export_import` | 원본 테스트 열람 |

### 2.2 코드 읽는 순서
`unknown.rs` 전체 → `session_tools.rs` `specs`의 unknown 4개 → 파라미터 구조체와 도구 함수 4개 → `session.rs` unknowns 절 → `project.rs` `store_unknown`·`load_unknowns`. 소비 쪽은 `report_tools.rs:297`, `:452`와 `crates/ai/src/rebuild/self_check.rs:59-71`.

## 적용 메모

overview 2절 "우리 절차와 맞대어 볼 후보" 3행(스펙의 미결정 → 상태·확인 방법·중요도가 있는 목록, 해결 시 근거 요구)에 대한 의견이다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| 1.3 `Unknown` 칸, R-04 | **후보 확정(형식).** 스펙 1.4 "미결정"을 자유 문장 대신 항목마다 `상태 · 중요도 · 확인 방법(probes) · 관련 R-ID`를 갖는 목록으로 쓴다. 상태는 원본의 5개 중 `open / blocked / resolved` 세 개면 충분하다(우리 쪽은 investigating·contradicted를 구분해 쓰는 흐름이 없음, 추론). | 원본은 "무엇이 이 질문을 풀지(probes)"를 질문과 함께 적어, 다음 사람이 바로 확인 작업을 시작할 수 있게 한다. 우리 미결정은 "구현에 미치는 영향"은 적지만 "어떻게 확인할지"를 적는 칸이 없다. | `capability-spec-template.md` 1.4 미결정 줄을 `- 미결정: <없음 \| U-ID · 질문 · 확인 방법 · 영향>` 형식으로. `next.md`의 "남은 질문"도 같은 형식으로 옮길 수 있다 |
| R-07, R-11 | **후보 수정.** "해결 시 근거 요구"는 쓰기 시점에 막지 말고 점검 단계에서 검사한다. 원본도 쓰기는 거의 막지 않고(R-07), `core_unknown_verify`가 "resolved인데 근거가 없음 / 근거 id가 없음"을 따로 보고한다. 우리 쪽 대응은 `scripts/check.py`에 "미결정에서 해소로 옮긴 항목에 R-ID나 `파일:줄`이 붙었는가"를 검사하는 것이다. | 쓰기 시점에 막으면 조사 중간 기록이 어려워진다는 점을 원본 구조가 보여 준다(추론). 반대로 검사 도구를 따로 두면 사람이 언제 돌리느냐에 기대게 되므로, 우리는 4장 6번에서 이미 돌리는 `check.py`에 넣는 편이 맞다. | 해소된 미결정을 지우지 않고 `resolved · 근거` 형태로 남기는 규칙이 필요해진다. 지금은 해소되면 1부로 옮기고 지우므로 기록이 남지 않는다 |
| R-13 | 채택하지 않음: revision 번호 | 원본은 같은 질문을 여러 에이전트가 동시에 고치는 상황을 막으려 revision을 둔다. 그래도 프로세스 사이에서는 막지 못한다(R-13). 우리 쪽은 4장 1번에서 "작업자는 자기 스펙만 쓰고 공용 파일은 메인 세션이 고친다"로 쓰기 주체를 나눠 같은 문제를 이미 피한다. | 없음 |
| R-02 | 참고: 질문 텍스트 해시 id | 같은 질문을 두 번 적는 것을 막지만, 문장이 조금만 달라도 다른 질문이 된다. 우리 쪽 U-ID는 순번이 맞다(추론). | 없음 |
