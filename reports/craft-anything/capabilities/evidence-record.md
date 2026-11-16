---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/evidence/src/lib.rs
  - crates/evidence/src/canonical.rs
  - crates/evidence/src/error.rs
  - crates/engine/src/lib.rs
  - crates/engine/src/tool.rs
  - crates/engine/src/session.rs
  - crates/engine/src/project.rs
  - crates/engine/src/tools/session_tools.rs
  - crates/platform/src/fs.rs
  - AGENTS.md
depends: []
status: ready
---

# 증거 레코드 (`Evidence`)

> 분석 도구가 돌려준 결과 하나를 "무엇을 봤고(subject), 무엇을 물었고(operation·params), 무엇이 나왔고(result), 얼마나 확실하고(confidence), 누구의 권위인지(authority), 어디까지 봤고(coverage) 무엇을 못 봤는지(limitations)"로 묶은 레코드로 만들고, 내용의 SHA-256으로 id를 붙여 세션 원장(ledger)과 프로젝트 저장소에 넣고 꺼낼 때 변조를 검사한다. 모든 도구가 공유하는 오류 계약 `ToolError`도 이 스펙이 정한다.

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 분석 도구가 `EvidenceBuilder::new(operation, subject, environment)`로 시작해 params·result·summary·confidence·authority·limitations·coverage·locations·links·`carries_target_content`를 채운다. 채우지 않은 칸은 기본값이 들어간다(R-04).
2. `build()`가 레코드를 JSON으로 바꾸고 표시 전용 칸 4개를 뺀 나머지를 정규 JSON(canonical JSON, 키 정렬·공백 없음)으로 쓴 뒤 SHA-256을 구해 `ev_<64 hex>` id를 붙인다(R-01~R-03, R-07).
3. 도구가 레코드를 `ToolOutput::Evidence`로 돌려주면 엔진(`Engine::call`)이 세션 원장에 넣는다. 프로젝트가 열려 있으면 먼저 `evidence/<접두사 ev_ 뒤 첫 hex 2자>/<id>.json`에 쓴다(R-15, R-16).
4. 다른 기능(finding, unknown 검증, 보고서)은 id로 레코드를 찾는다. 메모리 원장을 먼저 보고, 없으면 프로젝트 파일을 읽어 id를 다시 계산해 맞는지 확인한다(R-17).
5. 프로젝트를 다시 열 때와 증거 묶음(bundle)을 가져올 때도 id를 다시 계산해 맞지 않는 레코드는 버린다(R-18, R-20).

### 1.2 범위·통합 지점
- 제공: 레코드 타입과 직렬화 이름, id 계산(정규 JSON + SHA-256), 변조 검사(`verify`), 빌더 기본값, `Coverage` 쪽 나누기 계산, 요약 보기(`summary_view`), 세션 원장 기록·조회, 프로젝트 저장소의 증거 파일 읽기·쓰기, 증거 묶음 내보내기·가져오기, `ToolError` 오류 계약.
- 제외:
  - 각 분석 도구가 어떤 confidence·authority·coverage를 고르는지(행 15 분석 도구 본체). 이 스펙은 칸의 의미와 기본값만 정한다.
  - MCP의 `evidence://<id>` 참조, 결과 쪽 넘기기 도구(`core_evidence_browse`)(행 12).
  - 미해결 질문(`Unknown`)의 의미·수정 규칙(행 2 [unknown-ledger.md](unknown-ledger.md)). 이 스펙은 묶음 내보내기·가져오기에 unknown이 함께 실리는 경계만 다룬다.
  - 프로젝트 폴더(`.cany`) 생성·메타데이터·형식 마이그레이션(행 17).
- 외부 의존·선행 계약:
  - 원자적 파일 쓰기 `write_atomic(path, bytes)`: 성공하면 파일 전체가 새 내용, 실패하면 `ToolError`. 기존 파일이 있으면 권한을 유지한다(`crates/platform/src/fs.rs` 주석).
  - 크기 제한 읽기 `read_file_capped(path, max)`: 일반 파일만, `max` 초과면 `over_limit`.
  - SHA-256, 시스템 시계는 쓰지 않는다(id는 시각을 포함하지 않는다).
- 소유 상태·부작용: 세션의 메모리 원장(`ledger` 맵 + 삽입 순서 `order`), 프로젝트를 다시 열 때 메모리에 올리지 않은 레코드 수(`unloaded_evidence`), 프로젝트 폴더의 `evidence/` 아래 파일. 원장은 세션 수명 동안 남고, 지우는 공개 경로(`clear_ledger`)는 정의만 있고 호출하는 곳이 없다(R-24).

### 1.3 인터페이스와 데이터 의미

| 연산·데이터 | 입력·출력 / 타입 | 의미·제약 |
|---|---|---|
| `Evidence.id` | string | `ev_` + 소문자 hex 64자. R-01로 계산한 값. |
| `subject` | map `{kind: string, sha256?: string, name?: string}` | `kind`는 대상 종류(`native`, `electron`, `apk`, `website` 등 자유 문자열). `sha256`은 파일일 때 대상 바이트의 해시. `name`은 표시용이라 id에 들어가지 않는다. |
| `operation` | string | 레코드를 만든 도구 id(예: `native_function_pseudocode`). |
| `params`, `result` | 임의 JSON | 도구 입력과 결과. 빌더 기본값은 둘 다 `null`. |
| `summary` | string | 사람용 한두 문장. 표시 전용, id 밖. 없으면 `""`. |
| `confidence` | enum `observed` / `derived` / `inferred` | observed = 대상에서 직접 읽음(바이트·헤더·잡은 요청). derived = 관찰에서 결정적 함수로 계산(CFG, 호출 그래프). inferred = 휴리스틱·이름·모델 해석에 의한 추측. 사람용 이름은 R-13. |
| `authority` | enum `original-files` / `our-run` / `earlier-record` / `outside-service` / `reasoning` | 원본 프로그램·파일 자체 / 우리가 통제한 실행(프로세스 캡처, 브라우저 진행) / 과거 기록(HAR, 크래시 덤프) / 외부 서비스(원격 기기, 엔진 DB) / 사람·모델의 해석. |
| `environment` | map `{clean_room: bool, engine: string, engine_version?: string, host: string, language_id?: string}` | 관찰 조건. `clean_room`은 내장 엔진만 돌았는지, `engine`은 `builtin`·`ghidra`·`jadx`·`adb`·`cdp` 등, `host`는 `<os>-<arch>`, `language_id`는 Deep 엔진에 강제한 프로세서 id. `Environment::builtin(clean_room)`은 engine=`builtin`, engine_version=이 crate의 버전, host=현재 호스트로 채운다. |
| `limitations` | list of `{code: string, message: string}` | 분석이 확정하지 못했거나 일부러 뺀 것. `code`는 기계용(`stripped_binary`, `truncated` 등), `message`는 사람용. 순서 유지. |
| `coverage` | map `{status: complete/partial/unknown, examined?: u64, total?: u64, next_offset?: u64}` | 전체 공간 중 본 양. 기본값은 `{status: unknown}`. 계산은 R-09. |
| `locations` | list of `{kind: string, value: string, label?: string}` | 대상 안의 위치(`address`, `file_offset`, `path`, `url`, `line` 등). `Location::address(n)`은 `0x` 소문자 hex. |
| `links` | list of string | 이 레코드를 도출한 다른 증거 id. 존재 여부를 검사하지 않는다. |
| `carries_target_content` | bool, 기본 false | 결과에 대상에서 가져온 바이트·문자열·디컴파일 텍스트가 들어 있다는 표시. 읽는 쪽은 그 내용을 지시가 아니라 데이터로 다뤄야 한다. 표시 전용, id 밖. false면 직렬화에서 빠진다. |
| `compute_id()` | → string 또는 `ToolError(internal)` | R-01. |
| `verify()` | → bool | 저장된 id와 다시 계산한 id가 같으면 true(R-06). |
| `summary_view()` | → map | R-10. |
| `is_evidence_id(s)` | string → bool | `ev_` 다음 정확히 64자, 각 글자가 `0-9a-f`. |
| `ToolOutput` | `Evidence(레코드)` 또는 `Value(JSON)` | 도구 반환값. 에이전트가 보는 JSON은 레코드면 레코드 그대로, 값이면 `{"result": 값}`. 원장에 들어가는 것은 `Evidence`뿐이다. |
| `ToolError` | map `{code, category, message, retryable, remediation?, details?}` | 모든 도구·CLI·MCP의 오류. 필드 규칙은 R-21~R-23. |
| 증거 파일 | `<project>/evidence/<id[3..5]>/<id>.json` | 레코드의 pretty JSON. 처음 쓴 내용이 남는다(R-15). |
| 증거 묶음 | JSON 파일 `{"format": "craft-anything-evidence-bundle", "version": 1, "records": [...], "unknowns": [...]}` | 내보내기·가져오기 형식(R-19, R-20). |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | id 계산 | 레코드를 JSON 객체로 직렬화한 뒤 최상위 `id`·`summary`·`carries_target_content`와 `subject.name`을 지우고, 남은 값의 정규 JSON(C-02) UTF-8 바이트에 SHA-256을 걸어 `ev_` + 소문자 hex로 쓴다. 나머지 칸은 모두 id에 들어간다: `subject.kind`·`subject.sha256`, `operation`, `params`, `result`, `confidence`, `authority`, `environment` 전체, `limitations`, `coverage`, `locations`, `links`. 목록 칸은 순서까지 id에 영향을 준다. | 코드 확인 |
| R-02 | 선택 칸이 비어 있음 | `Option`이 None인 칸(`subject.sha256`, `engine_version`, `language_id`, `coverage`의 숫자들, `location.label`)과 false인 `carries_target_content`는 직렬화에서 빠진다. 그래서 칸이 없던 시절에 저장된 레코드도 같은 id로 읽힌다. | 코드 확인 |
| R-03 | 같은 도구·같은 대상·같은 결과지만 실행 환경이 다름 | `environment`가 id에 들어가므로 `host`, `engine_version`(내장 엔진은 앱 버전), `clean_room`, `engine`이 다르면 id가 다르다. 머리 주석의 "같은 관찰은 항상 같은 id"는 환경까지 같을 때만 성립한다. | 코드 확인 |
| R-04 | 빌더에서 칸을 채우지 않음 | 기본값: params·result `null`, summary `""`, confidence `observed`, authority `original-files`, limitations·locations·links 빈 목록, coverage `{status: unknown}`, `carries_target_content` false. 기본값이 가장 강한 확실성·권위다. 정직한 값을 고르는 것은 도구 작성자의 규칙(`AGENTS.md` Golden rule 3)이고 코드가 강제하지 않는다. | 코드 확인 |
| R-05 | 빌더 누적 | `limitation`·`location`·`link`는 호출 순서대로 뒤에 붙고, `limitations`·`locations`는 여러 개를 이어 붙인다. 나머지 setter는 덮어쓴다. `build()`의 유일한 실패는 직렬화 실패(`internal`)다. | 코드 확인 |
| R-06 | `verify()` | `compute_id()`가 성공하고 그 값이 `id`와 같으면 true, 아니면 false. 표시 전용 칸(summary, subject.name, carries_target_content)을 바꿔도 true가 유지되고, 그 밖의 칸을 바꾸면 false가 된다. | 코드 확인 |
| R-07 | 정규 JSON | 객체 키는 UTF-16 코드 단위 순으로 정렬, 불필요한 공백 없음, 문자열은 최소 escape(`"` `\` `\b` `\f` `\n` `\r` `\t`, 그 밖의 U+0000~U+001F는 `\u00xx` 소문자 hex, 나머지는 그대로), 숫자는 `serde_json`의 `Number` 문자열 표현. 세부는 C-02. | 코드 확인 |
| R-08 | 512단계보다 깊게 중첩된 값 | 그 값은 `null`로 쓴다. 깊이 512를 넘는 부분만 다른 두 레코드는 같은 id를 갖는다. | 코드 확인 |
| R-09 | `Coverage::complete(n)` / `Coverage::page(examined, total, offset)` | complete: status complete, examined=total=n. page: `end = offset + examined`(포화 덧셈)이 `total` 이상이면 complete·next_offset 없음, 아니면 partial·`next_offset = end`. `offset` 자체는 저장하지 않는다. | 코드 확인 |
| R-10 | `summary_view()` | `evidence_id`, `operation`, `summary`, `confidence`, `limitations`, `coverage`, `subject`(name 포함), `carries_target_content`(false여도 포함)를 담고 `result`는 뺀다. result 안에 목록이 있으면 `lists`(이름 → 길이)를 더하고, 없으면 `lists` 키 자체가 없다. `params`, `authority`, `environment`, `locations`, `links`는 들어가지 않는다. 목록 이름 규칙은 C-04. | 코드 확인 |
| R-11 | 결과 안의 이름 찾기 `find_result_key(v, key)` | 최상위 키를 먼저 보고, 없으면 하위 객체를 깊이 우선으로 최대 4단계 아래까지 찾아 처음 만난 값을 준다. 배열 안은 찾지 않는다. | 코드 확인 |
| R-12 | `is_evidence_id` | R-01 형식(`ev_` + 소문자 hex 64자)만 true. 대문자 hex는 false. | 코드 확인 |
| R-13 | `Confidence::plain_label` | observed → "Seen it", derived → "Worked it out", inferred → "Best guess". | 코드 확인 |
| R-14 | 직렬화 이름 | confidence·coverage status는 snake_case(`observed`, `partial`), authority는 kebab-case(`original-files`, `our-run`, `earlier-record`, `outside-service`, `reasoning`), ErrorCode·ErrorCategory는 snake_case. | 코드 확인 |
| R-15 | 도구가 `ToolOutput::Evidence`를 반환 | 도구 함수가 성공한 뒤 엔진이 `session.record`를 부른다. 프로젝트가 열려 있으면 파일 저장을 먼저 하고, 저장이 실패하면 그 `ToolError`가 호출자에게 가며 메모리 원장은 바뀌지 않는다(도구 자체는 이미 실행됐다). 같은 id 파일이 이미 있으면 다시 쓰지 않는다(디스크는 처음 쓴 내용이 남음). 메모리 원장은 같은 id면 새 레코드로 값을 바꾸되 순서 위치는 처음 넣은 자리를 유지한다. 그래서 같은 id인데 표시 칸만 다른 두 레코드는 메모리에는 나중 것, 디스크에는 처음 것이 남는다. `ToolOutput::Value`는 원장에 들어가지 않는다. | 코드 확인 |
| R-16 | 증거 파일 경로 | id가 R-12 형식이 아니면 `bad_input`("not an evidence id: …"). 형식이 맞으면 `evidence/<id의 3~4번째 바이트(접두사 뒤 첫 hex 2자)>/<id>.json`. | 코드 확인 |
| R-17 | id로 레코드 찾기 `resolve_evidence(id)` | 메모리 원장에 있으면 그 복사본을 다시 검사하지 않고 준다. 없고 프로젝트가 열려 있으면 파일을 읽어 파싱하고, `verify()`가 true이고 `id`가 요청과 같을 때만 준다. 그 밖의 모든 경우(프로젝트 없음, 파일 없음, 파싱 실패, 변조)는 같은 오류: `bad_input` "Unknown evidence id <id>", `details = {"reason": "missing", "evidence_id": <id>}`. 변조와 부재를 호출자가 구분할 수 없다. | 코드 확인 |
| R-18 | 프로젝트 열기 | 저장된 증거 파일을 수정 시각 내림차순(같으면 id 오름차순)으로 보며, 이미 올린 수가 5,000개이거나 이 파일을 더하면 누적 크기가 64 MiB를 넘는 첫 지점에서 멈추고 남은 파일 수(그 파일 포함)를 `unloaded_evidence`로 기록한다. 읽기·검증에 실패한 파일은 경고 로그만 남기고 건너뛴다(크기·개수에 넣지 않음). 올린 레코드는 오래된 것부터 원장에 넣어 `ledger()`(최신 먼저)가 쓴 순서와 맞게 한다. 올리지 않은 레코드도 R-17로 찾을 수 있다. | 코드 확인 |
| R-19 | 묶음 내보내기 `core_evidence_export {path, overwrite=false}` | path가 절대 경로가 아니면 `bad_input`. 파일이 있고 overwrite가 false면 `bad_input`(remediation: overwrite=true나 다른 이름). 메모리 원장 전체(최신 먼저)와 unknown 전체를 1.3 형식의 pretty JSON으로 원자적으로 쓴다. 메모리에 올리지 않은 프로젝트 레코드는 묶음에 들어가지 않고 그 수만 `not_loaded`로 알린다. 반환: `{path, bytes, records, unknowns, not_loaded}`. | 코드 확인 |
| R-20 | 묶음 가져오기 `core_evidence_import {path}` | 512 MiB까지 읽는다. JSON이 아니면 `bad_input` "not a bundle: …", `format`이 다르면 `bad_input`. `version`은 보지 않는다. `records`의 각 항목: 파싱되고 `verify()`가 true면 R-15로 기록, 파싱 실패면 `"unparseable"`, 검증 실패면 그 id를 `rejected`에 넣는다. 기록 중 프로젝트 저장이 실패하면 그 자리에서 오류로 끝나고 앞서 기록한 것은 남는다. `unknowns`의 각 항목: 파싱되고 같은 id가 없을 때만 추가한다(검증 없음, 파싱 실패는 조용히 건너뜀). 끝에 `rejected`가 있고 하나도 기록하지 못했으면 `evidence_hash_mismatch`("<N> records failed their integrity check", details `{rejected}`)를 돌려준다. 이때도 이미 추가한 unknown은 남는다. 그 밖에는 `{imported, rejected, unknowns_added, total}`. | 코드 확인 |
| R-21 | `ToolError::new(code, message)` | `category`와 `retryable`은 code에서 정해진다(C-05). remediation·details는 None으로 시작하고 None이면 JSON에서 빠진다. 편의 생성자: `invalid`→bad_input, `unsupported`→not_supported, `unavailable`→feature_missing, `internal`, `cancelled`("The operation was cancelled."), `target_required`(not_found + "Open a file, app or folder first (core_target_open)."). | 코드 확인 |
| R-22 | `ToolError::io(context, e)` | OS 오류 종류가 NotFound면 `not_found`, PermissionDenied면 `no_permission`, 그 밖은 `file_error`. 메시지는 `"<context>: <e>"`. | 코드 확인 |
| R-23 | `for_people()` | message와 remediation을 각각 trim하고, remediation이 없거나 비면 message만, 있으면 message가 `. ! ? :`로 끝나지 않을 때 `.`을 붙이고 공백 하나 뒤에 remediation을 잇는다. | 코드 확인 |
| R-24 | 정의만 있고 쓰이지 않는 것 | `EvidenceRef`(`{kind: "saved", evidence_id}`)와 `Session::clear_ledger`는 레포 안 호출처가 없다(`grep -rn` 결과 정의 파일 밖 0건). | 코드 확인 |
| R-25 | 도구 파라미터 파싱 실패 | `parse_params`는 `null`을 빈 객체로 보고, 역직렬화 실패를 `bad_input` "invalid params at \"<JSON pointer>\": <원인>", remediation "Correct the parameter to match the tool's input schema, then call the tool again.", details `{"parameter_path": <pointer 또는 null>}`로 바꾼다. 이 스펙과 뒤 스펙들의 모든 도구가 같은 경로를 탄다. | 코드 확인 |

- 불변식: 원장(메모리)에 있는 레코드는 빌더나 `verify()`를 거쳐 들어왔으므로 id와 내용이 맞는다(전제: 메모리 원장을 직접 고치는 코드가 없음, 추론). 디스크에서 읽어 쓰는 레코드는 항상 R-17·R-18에서 다시 검사된다.
- 미결정: 없음.
- 확인 한계: 실행하지 않고 정적 읽기만 했다. 실수(float) 정규화는 `serde_json`의 최단 왕복 표현에 기대며, 소스 주석은 "증거가 담는 값(개수·오프셋·비율)에 대해 ECMAScript와 같다"고만 주장한다(RFC 8785 완전 일치는 확인하지 않음). `serde_json`의 `Map`이 키 정렬 맵인지(= `preserve_order` 꺼짐)는 `Cargo.lock`의 `serde_json` 의존에 `indexmap`이 없다는 점으로 판단했다(추론). 이 판단은 R-01에는 영향이 없고(정규화가 직접 정렬), C-04에서 목록 이름이 64개를 넘을 때 어느 64개가 남는지에만 영향을 준다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/evidence/src/lib.rs:24-233` `Confidence`·`Authority`·`Subject`·`Environment`·`Limitation`·`CoverageStatus`·`Coverage`·`Location`·`Evidence` | 칸 이름, serde 속성(rename_all, skip_serializing_if, default), 기본값 | R-01, R-02, R-13, R-14 |
| C-02 | `crates/evidence/src/canonical.rs:12-85` `canonical_json`·`sha256_hex`·`MAX_DEPTH`·`write_value`·`write_string` | 정규 JSON 문법 전체와 깊이 상한 | R-07, R-08 |
| C-03 | `crates/evidence/src/lib.rs:240-258` `compute_id`·`verify` | id에서 빼는 칸 4개와 형식 | R-01, R-06 |
| C-04 | `crates/evidence/src/lib.rs:263-323` `summary_view`·`RESULT_KEY_DEPTH`·`MAX_LISTED`·`find_result_key`·`result_lists` | 요약 보기 칸과 목록 이름 규칙(깊이 4, 최대 64개, 같은 이름이 먼저 목록 아닌 값에 닿으면 제외) | R-10, R-11 |
| C-05 | `crates/evidence/src/error.rs:6-108` `ErrorCode`·`ErrorCategory`·`category`·`retryable`·`ToolError` | 오류 코드 22종, 코드 → 범주 표, 재시도 가능 코드(timed_out, cancelled, over_limit, stale_revision) | R-21 |
| C-06 | `crates/evidence/src/lib.rs:160-174` `Coverage::complete`·`Coverage::page` | 쪽 나누기 계산 | R-09 |
| C-07 | `crates/engine/src/session.rs:241-268`, `:313-351` `record`·`resolve_evidence`·`open_project` | 원장 기록 순서, 조회 순서, 프로젝트 로드 예산(`MAX_LOADED_EVIDENCE` 5,000, `MAX_LOADED_EVIDENCE_BYTES` 64 MiB, `:63-67`) | R-15, R-17, R-18 |
| C-08 | `crates/engine/src/project.rs:118-170` `evidence_path`·`store_evidence`·`load_evidence`·`evidence_files` | 파일 경로, 처음 쓴 것 유지, 읽을 때 검증 | R-15, R-16, R-18 |
| C-09 | `crates/engine/src/tools/session_tools.rs:357-435` `BUNDLE_FORMAT`·`core_evidence_export`·`MAX_BUNDLE_BYTES`·`core_evidence_import` | 묶음 형식과 가져오기 분기 | R-19, R-20 |

### 1.6 수락 사례
출처: 사례별 표기

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-01, R-06, R-12 | 같은 입력으로 빌더를 두 번 실행 (원본 테스트) | 두 id가 같고 `is_evidence_id`가 true, `verify()` true |
| T-02 | R-01, R-06 | 레코드의 summary와 subject.name만 바꾸고 `compute_id()` (원본 테스트) | 원래 id와 같다 |
| T-03 | R-06 | result를 `{"functions": 12}`에서 13으로 바꿈 (원본 테스트) | `verify()` false |
| T-04 | R-02 | `target_content(true)`로 만든 레코드와 같은 내용의 기본 레코드 비교, false 레코드를 직렬화 (원본 테스트) | 두 id가 같다. false 레코드 JSON에 `carries_target_content` 문자열이 없다. 그 JSON을 다시 읽어도 같은 id, `verify()` true |
| T-05 | R-09 | `page(10, 25, 10)`, `page(5, 25, 20)`, `page(0, 0, u64::MAX)` (원본 테스트) | partial·next_offset 20 / complete / complete |
| T-06 | R-07 | `{"b": [1, {"z": null, "a": true}], "a": "x\ny"}` 정규화 (원본 테스트) | `{"a":"x\ny","b":[1,{"a":true,"z":null}]}` |
| T-07 | R-07 | 키 U+1F600과 U+FB01 (원본 테스트) | U+1F600 키가 먼저(UTF-16 대리쌍 0xD83D < 0xFB01) |
| T-08 | R-08 | 배열로 2,000번 감싼 값 정규화 (원본 테스트) | 실패 없이 끝나고 결과에 `null` 포함 |
| T-09 | R-18 | 프로젝트에 레코드 둘을 저장하고 하나의 파일에서 `"result": 2`를 3으로 고친 뒤 새 세션에서 프로젝트 열기 (원본 테스트) | 원장 레코드 1개(고치지 않은 것), `core_session_show`의 `evidence_records` 1 |
| T-10 | R-19 | 같은 경로로 overwrite 없이 두 번 내보내기 (원본 테스트) | 두 번째는 오류 |
| T-11 | R-10 | result `{"counts": {"changed": 2}, "changed": 2, "pairs": [..2개..], "groups": {"ambiguous": [], "deeper": {"changed": [1]}}, "text": "x"}` (원본 테스트) | `lists` = `{"ambiguous": 0, "pairs": 2}`. result에 목록이 없으면 `lists` 키 없음 |
| T-12 | R-20 | 레코드 2개가 모두 변조됐고 unknown 1개가 있는 묶음 가져오기 (구현에서 도출) | `evidence_hash_mismatch`, details.rejected에 두 id. 세션에 unknown 1개가 추가돼 있다 |
| T-13 | R-17 | 프로젝트에만 있는 레코드 파일을 변조한 뒤 그 id로 `resolve_evidence` (구현에서 도출) | `bad_input`, details `{"reason": "missing", ...}` (변조라고 말하지 않음) |
| T-14 | R-03 | 다른 모든 칸이 같고 `environment.host`만 `linux-x86_64`와 `macos-aarch64`로 다른 두 레코드 (구현에서 도출) | id가 다르다 |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, R-06 | C-03, C-01 `Evidence` `:201-233` | 직렬화 후 지우는 키 4개를 읽음 |
| R-02 | C-01 `skip_serializing_if`, `is_false` `:235-237` | 테스트 `target_content_flag_round_trips_and_leaves_id_unchanged` `lib.rs:516-553`이 같은 보장을 검사 |
| R-03 | `lib.rs:94-104` `Environment::builtin`·`host_triple`, C-03 | environment를 빼는 코드가 없음을 확인. 문서 차이: 머리 주석 `lib.rs:6-7` "the same observation always has the same id"는 환경이 같다는 전제를 말하지 않는다 |
| R-04, R-05 | `lib.rs:325-419` `EvidenceBuilder` | 기본값과 setter를 읽음. `AGENTS.md` Golden rule 3 "honest confidence"는 문서 규칙이고 강제 코드는 찾지 못함(`build()`가 검사하지 않음) |
| R-07, R-08 | C-02 | 머리 주석 `canonical.rs:1-6`이 RFC 8785 "style"이라고 밝힘 |
| R-09 | C-06 | |
| R-10, R-11 | C-04 | |
| R-12 | `lib.rs:428-431` `is_evidence_id` | |
| R-13 | `lib.rs:36-45` `plain_label` | |
| R-14 | C-01, `error.rs:7-8`, `:53-54` | |
| R-15 | `crates/engine/src/lib.rs:297-299` `call_inner`, C-07 `record`, C-08 `store_evidence` | `Engine::call`의 저널 기록(`lib.rs:213-229`)은 행 3에서 다룬다 |
| R-16 | C-08 `evidence_path` | |
| R-17 | C-07 `resolve_evidence`, C-08 `load_evidence` `:135-143` | `if let Ok(e)`로 오류 종류가 버려짐을 읽음 |
| R-18 | C-07 `open_project`, C-08 `evidence_files` | |
| R-19, R-20 | C-09 | `version` 필드를 읽는 코드 없음 |
| R-21~R-23 | `error.rs:110-165` | |
| R-24 | `grep -rn "EvidenceRef" crates apps`, `grep -rn "clear_ledger" crates apps` | 정의 파일 밖 결과 0건. 동적 호출은 Rust에서 불가하므로 검색으로 충분하다고 판단 |
| R-25 | `crates/engine/src/tool.rs:311-320` `parse_params` | |
| T-01~T-04, T-11 | `lib.rs:459-553` `summary_view_names_the_lists_a_name_reaches`·`id_is_stable_and_well_formed`·`display_fields_do_not_change_the_id`·`content_change_is_detected`·`target_content_flag_round_trips_and_leaves_id_unchanged` | 원본 테스트 열람 |
| T-05 | `lib.rs:555-564` `coverage_page_math` | 원본 테스트 열람 |
| T-06~T-08 | `canonical.rs:92-114` | 원본 테스트 열람 |
| T-09, T-10 | `session_tools.rs:727-772` `project_evidence_is_loaded_in_a_new_session`·`bundle_export_import` | 원본 테스트 열람 |

### 2.2 코드 읽는 순서
`crates/evidence/src/lib.rs`(타입 → `compute_id` → 빌더) → `canonical.rs` → `error.rs` → `crates/engine/src/lib.rs` `call_inner` 끝(기록 지점) → `session.rs` evidence 절 → `project.rs` evidence 절 → `session_tools.rs` export/import. `verify()`를 부르는 다른 곳: `compare_tools.rs:406`, `:810`(행 6), `artifact_tools.rs:401`(행 15), `session_tools.rs:609`(행 2).

## 적용 메모

우리 절차(`OSS_ANALYSIS_WORKFLOW.md` 7장)와 비교한 결과. overview 2절 "우리 절차와 맞대어 볼 후보" 1행(검증 수준 3단계)에 대한 의견이다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-01, R-04, 1.3 confidence·authority·coverage | **후보 수정 후 채택 제안.** 우리 검증 수준 3단계는 "얼마나 확실한가"와 "무엇에 근거했나"를 한 칸에 섞는다. 이 레포는 확실성(`confidence`: 직접 읽음 / 결정적 계산 / 추측), 권위(`authority`: 원본 파일 / 우리가 한 실행 / 과거 기록 / 외부 서비스 / 해석), 본 범위(`coverage`), 못 본 것(`limitations`)을 따로 둔다. 우리에게 바로 필요한 것은 두 가지다. (1) `코드 확인`을 "직접 읽음"과 "도구로 계산·검색함(grep 결과 0건 등)"으로 나누는 것(이 레포의 observed/derived 구분). 이 스펙의 R-24처럼 "호출처 없음"은 읽은 것이 아니라 검색 결과다. (2) 부재·전수 주장에는 검색 범위(명령과 대상 경로)를 근거 칸에 적는 것. `coverage`는 쪽 나누기 숫자(examined/total)라서 "어디를 검색했는가"까지 담지 않으므로, 우리 쪽은 숫자가 아니라 검색 명령을 적는 편이 맞다(추론). | 원본은 칸을 나눠 기계가 걸러낼 수 있게 했다. 우리 문서는 사람이 읽으므로 칸을 늘리기보다 2.1 "확인 방법·한계"에 형식을 정하는 정도가 비용 대비 낫다(추론). | `capability-spec-template.md` 2.1 주석에 "부재·전수 주장은 검색 명령과 범위를 적는다", 7장 검증 수준 정의에 "`코드 확인`에는 직접 읽은 것과 검색·도구 결과가 있고 후자는 명령을 남긴다" 한 줄 |
| R-04 | 기본값을 가장 강한 수준으로 두지 않는다 | 원본 빌더는 아무것도 지정하지 않으면 observed·original-files가 된다. 정직성은 문서 규칙에만 기대고 코드가 막지 않는다. 우리 템플릿도 검증 수준 칸에 기본값을 두지 않는 현재 방식을 유지하는 것이 맞다. | 없음(현행 유지 근거) |
| R-01, R-06, R-17 | 채택하지 않음: 주장별 내용 해시 id | 이 레포는 레코드를 파일로 주고받고 변조를 의심해야 해서 해시 id가 필요하다. 우리 스펙은 frontmatter `sha` 하나로 원본 시점을 고정하고 근거는 `파일:줄`이므로, 주장마다 해시를 둘 이유가 없다. 다만 "근거가 실제로 있는가"를 기계로 검사하는 쪽은 행 3(finding의 id 검사)에서 다룬다. | 없음 |
| R-03 | 참고: 환경을 id에 넣은 결과 | 같은 결과라도 호스트·앱 버전이 다르면 다른 레코드가 된다. 우리 쪽에 대응시키면 "어떤 SHA에서 확인했는가"가 근거의 일부라는 현행 규칙(7장)과 같은 생각이다. | 없음 |
