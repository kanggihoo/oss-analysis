---
sha: "8374ad71544f2cc44698ea74ef990aa31600bac6"
created: 2026-11-14
updated: 2026-11-14
sources:
  - crates/analysis/src/js_ledger.rs
  - crates/analysis/src/js_app.rs
  - crates/js/src/model.rs
  - crates/js/src/facts.rs
  - crates/js/src/fallback.rs
  - crates/js/src/util.rs
  - crates/engine/src/tools/application_tools.rs
  - crates/engine/src/tools/compare_tools.rs
  - crates/engine/src/tools/js_tools.rs
  - crates/engine/src/tools/artifact_tools.rs
  - crates/engine/src/tools/mod.rs
  - crates/engine/src/session.rs
  - crates/engine/src/lib.rs
  - crates/engine/src/tool.rs
  - crates/engine/src/clean_room.rs
  - crates/evidence/src/lib.rs
  - crates/evidence/src/canonical.rs
  - crates/evidence/src/error.rs
  - crates/mcp/src/prompts.rs
  - docs/pitfalls.md
depends:
  - ../capabilities/evidence-record.md
status: ready
---

# 재구성 원장·증명 강도 (`app_ledger_build`·`app_coverage_evaluate`·`app_rebuild_claim_check`)

> JavaScript/Electron 앱 그래프에서 재구현이 해야 할 기대 동작(expectation) 목록을 고정 규칙으로 뽑고, 호출자가 낸 매니페스트(기대 동작마다 담당 위치·사례별 증거·검사 결과)를 받아 기대 동작마다 `proven`부터 `no-owner`까지 상태 하나를 매기고 원장 전체 상태와 증명 비율을 증거 레코드로 남긴다. 별도 도구 `app_rebuild_claim_check`는 원장과 상관없이 "서술 + 증거 id" 목록의 증거가 존재하고 변조되지 않았는지만 본다.

용어
- **기대 동작(expectation)**: 재구현이 원본처럼 해야 하는 일 하나. 예: "IPC 채널 `export-notes`를 main 프로세스가 처리한다".
- **사례 종류(case kind)**: 기대 동작이 보여야 하는 상황. `works`(정상), `refuses`(거부), `bad-input`(잘못된 입력), `cancel`, `shutdown`.
- **증명 강도(strength)**: 증거가 어느 수준의 실행에서 나왔는지를 나타내는 문자열. 8단계 사다리 `STRENGTH`에서 순위(0~7)로 비교한다.
- **binding**: 매니페스트의 한 항목. 기대 동작 id 하나에 담당 위치(owner), parser 타입, 사례 목록, 검사(verifier)를 묶는다.
- **verifier**: 기대 동작을 확인한 검사 하나(명령, 강도, pass/fail, 결과 증거 id, 이 검사가 다룬 기대 동작 id 목록).
- **증거가 유효하다**: 세션이 그 id의 증거 레코드를 찾을 수 있고, 레코드의 id가 내용 해시와 일치한다(선행 스펙 `evidence-record`의 `verify`). 레코드의 내용이나 종류는 보지 않는다(R-10).

## 1부. 동작 설명

### 1.1 한눈에 보는 흐름
1. 호출자(사람·코딩 에이전트·MCP 클라이언트)가 Deep 모드에서 `app_ledger_build`를 부른다. 입력은 앱 그래프(`js_app_map` 증거 또는 분석할 절대 경로), 매니페스트(`bindings`), 검토 결정(`reviewed_expectations`)이다. Clean room 모드면 실행 전에 거부된다(R-01).
2. 앱 그래프에서 후보 기대 동작을 만든다. 그래프 항목 종류마다 층(layer)·요구 사례·최소 강도·parser 타입 필요 여부가 고정되어 있다(R-04, C-02). 호출자가 기대 동작을 추가하는 입력은 없다.
3. 기대 동작마다 순서대로 판정한다. 검토 결정이 `skipped`/`waiting`이면 그 값이 상태다. 아니면 binding 수와 owner 수를 보고, binding이 하나로 정해지면 owner 필드 → parser 타입 → 사례별 증거와 강도 → verifier를 검사해 부족한 점(`missing`)을 모은다. 마지막에 우선순위 규칙으로 상태 하나를 고른다(R-06~R-13).
4. 상태 개수로 원장 상태(`failing` > `unclear` > `ready` > `open`)를 정하고, 그래프 id와 상태 목록에서 `ledger_id`를, 증명된 행에서 `closed_hash`를 계산한다(R-14, R-15). 결과는 증거 레코드 하나로 세션에 기록된다(R-17).
5. `app_coverage_evaluate`가 그 원장 증거를 받아 행의 상태를 다시 판정하지 않고 세기만 해서 증명 비율·층별 개수·빈칸 목록을 낸다(R-18, R-19).
6. 별도 경로: `app_rebuild_claim_check`는 원장·앱 그래프를 쓰지 않는다. `goal`과 "서술 + 증거 id 목록" 형태의 기대 동작들을 받아, 각 기대 동작의 증거가 모두 유효한지만 보고 `verified`를 낸다(R-20).

### 1.2 범위·통합 지점
- 제공: 후보 기대 동작 생성 규칙, 매니페스트 판정과 상태 어휘, 원장 상태·id, 커버리지 계산, 증거 존재 확인 도구, 세 도구의 입력 검증과 출력 증거.
- 제외:
  - 앱 그래프를 만드는 분석(`js_app_map`, `analyze_to_graph`). feature map 행 15(분석 도구 본체)에 속한다. 이 스펙은 그래프에서 읽는 필드만 경계로 정의한다(아래).
  - 증거 레코드의 id 계산·정규화 JSON 상세. 선행 스펙 `evidence-record` 소유다. 이 스펙은 아래 경계만 쓴다.
  - verifier `command` 실행. 원본은 명령을 실행하지 않고 문자열로 받기만 한다(R-12).
  - 리빌드 루프(행 7)와 검사 계약(행 9). 원본에서 리빌드 루프는 이 원장을 부르지 않는다(R-21).
- 외부 의존·선행 계약:
  - **증거 레코드(선행 `evidence-record`)**: 이 기능이 쓰는 것은 다섯 가지다. (a) id 형식 `ev_` + 소문자 hex 64자(`is_evidence_id`). (b) `verify()`: 레코드에서 `id`·`summary`·`carries_target_content`·`subject.name`을 뺀 나머지를 정규화 JSON으로 만들어 SHA-256을 구하고, `ev_`를 붙인 값이 저장된 `id`와 같으면 참. (c) 세션 조회 `resolve_evidence(id)`(선행 스펙 R-17): 메모리 원장 → 열린 프로젝트 저장소 순서로 찾는다. 메모리에 있으면 다시 검사하지 않고, 저장소에서 읽은 것은 `verify`가 참이고 id가 같을 때만 준다. 없음·파싱 실패·변조는 모두 같은 `BadInput` 오류(`details.reason = "missing"`)라 호출자가 구분할 수 없다. 이 기능은 조회 뒤 `verify`를 한 번 더 부른다(R-10). (d) 증거 입력 해석 `resolve_evidence_input`: 문자열이면 id로 조회, `{"kind":"saved","evidence_id":…}`면 그 id로 조회, 그 밖의 객체는 증거 레코드로 역직렬화한 뒤 `verify` 실패 시 `EvidenceHashMismatch` 오류. 그다음 레코드의 `operation`이 기대값 목록에 없으면 `BadInput`. (e) `EvidenceBuilder`로 결과 레코드를 만들고, 도구 호출부(`Engine::call`)가 반환된 증거를 세션 원장에 기록한다.
  - **정규화 JSON·SHA-256**: `canonical_json`(키 정렬, 공백 없음)과 `sha256_hex`(소문자 hex). 선행 스펙과 같은 함수다.
  - **앱 그래프 입력(행 15 경계)**: `graph_id`(string, `ag_` 접두), `label`(string), `entry_points.main`(optional string), `ipc`(list of {`channel`, `handlers`(list), `main_listeners`(list)}), `exposed`(list of {`key`, `members`: list of {`name`}}), `windows`(list of {`module`, `line`}), `endpoints`(list of {`api`, `method`(optional), `url`}), `routes`(list of {`path`}), `storage`·`effects`(list of {`api`, `arg`(optional)}), `native_modules`(list of {`name`}). 목록 순서가 기대 동작 순서가 된다. 이 기능이 기대는 그래프 쪽 성질은 R-22에 쓴 것뿐이다: `ipc`는 채널 이름당 항목 하나, `windows`·`exposed`는 생성·노출 호출마다 항목 하나(합치지 않음), 창 위치는 모듈과 줄 번호, `storage` 목록에는 `fs.` 이름이 없음. 그 밖의 분류 규칙(어떤 호출이 effect인지 등)과 목록 상한(각 10,000)은 그래프 분석기 소관이다.
- 소유 상태·부작용: 세 도구 모두 입력만 읽는 계산이다. 파일을 쓰지 않는다. 각 도구의 결과 증거 하나가 세션 원장에 추가된다(`Effects::EVIDENCE` = 세션 변경 + 멱등). 매니페스트 원문은 결과에 남지 않고 개수만 남는다(R-17).

### 1.3 인터페이스와 데이터 의미

**상수**

| 데이터 | 값 | 의미·제약 |
|---|---|---|
| `STRENGTH` | `unit-test`, `module-test`, `network-test`, `page-test`, `built-app`, `native-call`, `live-run`, `outside-check` | 약한 것부터 순서. 순위는 목록 위치(0~7). 목록에 없는 문자열은 순위가 없고, 그런 값은 어떤 비교도 통과하지 못한다. |
| `CASE_KINDS` | `works`, `refuses`, `bad-input`, `cancel`, `shutdown` | 정의만 있고 판정 코드에서 쓰이지 않는다. 후보 생성 규칙은 `cancel`·`shutdown`을 요구하지 않는다(R-04). |

**`app_ledger_build` 입력** (모든 객체 `deny_unknown_fields`: 모르는 키가 있으면 `BadInput` "invalid params at …")

| 필드 | 타입 | 의미·제약 |
|---|---|---|
| `application` | string 또는 object, 필수 | 증거 id가 아닌 문자열이면 분석할 경로로 보고 그 자리에서 분석한다. 증거 id·`{"kind":"saved",…}`·인라인 증거면 `operation`이 `js_app_map`이어야 한다(R-02). |
| `manifest.bindings[]` | list, 기본 빈 목록 | binding 목록. 순서는 R-09(첫 binding 사용)에 영향을 준다. |
| `…expectation_id` | string, 필수 | 원장 기대 동작 id(`ex_…`). 원장에 없는 id는 `stray_bindings`로만 보고된다. |
| `…owner.module_path`, `…owner.symbol` | string, 둘 다 필수 키 | 빈 문자열도 파싱은 통과한다. 판정에서 공백 제거 후 비면 부족으로 친다. |
| `…owner.impl_sha256` | optional string | 받기만 하고 판정·출력에 쓰지 않는다. |
| `…parser_type` | optional string | 기대 동작의 `needs_parser_type`이 참일 때만 검사한다. |
| `…cases[]` | list of {`kind`, `evidence_id`, `strength`}, 기본 빈 목록 | 세 필드 모두 필수 키. 값 검증 없음(목록 밖 `kind`·`strength`도 받는다). |
| `…verifier` | optional {`command`, `strength`, `status`, `result_evidence`, `expectation_ids`, `nondeterminism`?} | `nondeterminism`만 선택. `command`·`nondeterminism`은 판정에 쓰지 않는다. `status`는 `pass`/`fail` 이외 값도 받는다. |
| `reviewed_expectations[]` | list of {`expectation_id`, `decision`, `reason`?} | `decision`은 `required`/`skipped`/`waiting` 중 하나여야 한다. 아니면 `BadInput` "decision \"…\" must be required, skipped or waiting". 원장에 없는 id는 조용히 무시된다. |

**`app_ledger_build` 결과(`result`) = 원장**

| 필드 | 타입 | 의미 |
|---|---|---|
| `ledger_id` | string | `lg_` + SHA-256 hex 64자(R-15). |
| `closed_hash` | string | 접두 없는 SHA-256 hex 64자(R-15). |
| `graph_id` | string | 입력 그래프의 id. |
| `status` | string | `failing` / `unclear` / `ready` / `open`(R-14). |
| `counts` | map status→int | 실제로 나온 상태만 키로 있다(0인 상태는 키 없음). 키는 사전순. |
| `expectations` | list of row | 후보 기대 동작 순서 그대로. row = `expectation_id`, `layer`, `target`, `title`, `must_cover`(list), `min_strength`, `needs_parser_type`, `source_node`, `status`, `missing`(list of string, 찾은 순서), `review`(null 또는 {`decision`, `reason`}). |
| `stray_bindings` | list of string | 원장에 없는 `expectation_id`를 가진 binding의 id, 매니페스트 순서, 중복 제거 없음. |
| `strength_ladder` | list of string | `STRENGTH` 그대로. |

기대 동작 상태 값은 8개다: `skipped`, `waiting`, `no-owner`, `disproved`, `proven`, `unclear`, `built`, `described`.

**`app_coverage_evaluate`**

| 항목 | 타입 | 의미 |
|---|---|---|
| 입력 `ledger` | string 또는 object, 필수 | `app_ledger_build` 증거(id, saved 참조, 인라인). 다른 `operation`이면 `BadInput`. |
| 결과 | object | `ledger_id`, `ledger_status`, `expectations`(행 수), `in_scope`(`skipped`가 아닌 행 수), `proven`, `proven_percent`(소수 1자리, R-18), `by_layer`(layer→status→int), `gaps`(최대 500행, 각 {`expectation_id`, `layer`, `target`, `status`, `missing`}), `ready`(bool). |

**`app_rebuild_claim_check`**

| 항목 | 타입 | 의미 |
|---|---|---|
| 입력 `specification.goal` | string, 필수 | 공백 제거 후 비면 `BadInput` "goal is empty". |
| 입력 `specification.expectations[]` | list of {`description`: string, `evidence_ids`: list, 기본 빈 목록}, 필수 | 빈 목록이면 `BadInput` "a specification needs at least one expectation". 원장의 `Expectation`과 다른 타입이다. |
| 결과 | object | `verified`(bool), `satisfied`(int), `total`(int), `expectations`(list of {`description`, `evidence_ids`, `satisfied`, `problems`}). |

### 1.4 행동 규칙과 남은 질문

| ID | 조건·입력 | 반드시 관찰될 결과·사후 상태 | 검증 수준 |
|---|---|---|---|
| R-01 | 세션이 Clean room 모드(기본값)일 때 세 도구 중 하나를 호출 | 도구 본문이 실행되기 전에 `FeatureMissing` 오류, `details` = {`reason`: `clean_room`, `tool`: <id>}. 세 도구 모두 Clean room 허용 목록에 없다. Deep 모드에서만 실행된다. | 코드 확인 |
| R-02 | `application` 해석 | 증거 id 형식이 아닌 문자열 → 경로로 분석해 그래프를 만들고 그래프 증거 id는 없음. 그 밖 → 증거로 해석(1.2 (d)), `operation`이 `js_app_map`이 아니면 `BadInput` "evidence … came from …, but this needs js_app_map". 결과가 그래프로 역직렬화되지 않으면 `BadInput`. 증거의 `modules` 수가 `modules_total`보다 적으면(페이징된 기록) 기록된 `params.input_path`를 다시 분석해 전체 그래프를 쓰고, 다시 만든 `graph_id`가 다르면 `FileChanged` 오류. | 코드 확인 |
| R-03 | 매개변수 검증 | 키 누락·모르는 키·타입 오류 → `BadInput` "invalid params at \"<경로>\": …". `decision` 값 검사(1.3)는 그래프를 읽은 뒤, 판정 전에 한다. `kind`·`strength`·`status`·`expectation_ids`의 값은 검증하지 않는다. | 코드 확인 |
| R-04 | 그래프에서 후보 생성 | 다음 순서로 기대 동작을 만든다(세부는 C-02). ① `entry_points.main`이 있으면 `install` 층 1개(`works`, `built-app`). ② `ipc` 중 `handlers` 또는 `main_listeners`가 비지 않은 채널마다 `shell`(`works`·`refuses`·`bad-input`, `module-test`, parser 필요). ③ `exposed`의 멤버마다 `shell`(`works`·`refuses`, `page-test`). ④ `windows`마다 `shell`(`works`, `built-app`). ⑤ `api`가 `literal`이 아닌 `endpoints`마다 `network`(`works`·`refuses`·`bad-input`, `network-test`, parser 필요). ⑥ `routes`마다 `page`(`works`, `page-test`). ⑦ `storage` 전부와, `effects` 중 `api`가 `fs.write`·`fs.append`·`fs.mkdir`·`fs.rm`·`fs.unlink`·`child_process.`·`shell.`로 시작하는 것마다 `works`·`refuses`, `module-test`. 층은 `api`가 `fs.`로 시작하면 `storage`, 아니면 원래 목록 기준(`storage` / `system`)이고, parser 필요 여부는 층이 `storage`인지와 같다. ⑧ `native_modules`마다 `native`(`works`, `native-call`). 중복 제거는 ⑤~⑧에만 하고(공유 집합 `seen`), ①~④는 그래프 항목 수만큼 만든다. | 코드 확인 |
| R-05 | 기대 동작 id | `ex_` + SHA-256(`<layer>` + U+0000 + `<target>`) hex의 앞 16자. 같은 층·target이면 같은 id다. 같은 id의 행이 실제로 두 번 생기는 조건과 생기지 않는 종류는 R-22. | 코드 확인 |
| R-06 | 기대 동작에 검토 결정이 있음 | 같은 id의 검토 중 **마지막** 것을 쓴다. `skipped`·`waiting`이면 상태가 그 값이고 `missing`은 빈 목록이며 binding은 보지 않는다. `required`는 검토가 없는 것과 같다. 행의 `review`에는 쓴 검토가 들어간다. | 코드 확인 |
| R-07 | 그 id의 binding이 0개 | 상태 `no-owner`, `missing` = ["no owner in the rebuild"]. | 코드 확인 |
| R-08 | 그 id의 binding들이 서로 다른 (`module_path`, `symbol`) 쌍을 2개 이상 가짐 | 상태 `disproved`, `missing` = ["<쌍 수> different owners claim it"]. 다른 필드는 검사하지 않는다. 원장 상태는 `failing`이 된다(R-14). | 코드 확인 |
| R-09 | binding이 1개 이상이고 owner 쌍이 1개 | 매니페스트 순서상 **첫 binding만** 검사한다. 같은 owner의 두 번째 이후 binding에 있는 사례·verifier는 무시된다. | 코드 확인 |
| R-10 | 사례·verifier의 증거 유효성 | 유효성 = `resolve_evidence(id)` 성공 그리고 `verify()` 참. 증거의 `operation`·내용·신뢰도는 보지 않는다. 그래서 `js_app_map` 분석 증거처럼 검사 실행과 무관한 증거도 사례 증거와 verifier 결과로 인정된다(원본 엔진 테스트가 그렇게 `proven`을 만든다). 강도는 호출자가 문자열로 선언한 값을 그대로 믿는다. | 코드 확인 |
| R-11 | 첫 binding 검사: owner·parser·사례 | ⓐ `module_path` 또는 `symbol`이 공백 제거 후 비면 "owner needs module_path and symbol". ⓑ 기대 동작이 parser 필요이고 `parser_type`이 없거나 공백뿐이면 "parser_type is required for this layer". ⓒ `must_cover`의 각 종류마다, 같은 `kind`이면서 증거가 유효하고 `strength` 순위 ≥ `min_strength` 순위인 사례가 하나라도 있으면 충족. 없으면 "<kind> case with <min_strength> (or stronger) evidence"를 추가하고 사례 충족 플래그를 거짓으로 한다. 같은 `kind`의 사례 중 증거가 무효인 것이 하나라도 검사되면 "불명" 플래그를 켠다(다른 사례가 그 종류를 충족해도 켜질 수 있다. 검사 순서상 충족 사례보다 앞에 있으면 켜진다). `must_cover`에 없는 `kind`의 사례는 무시한다. | 코드 확인 |
| R-12 | 첫 binding 검사: verifier | ⓐ 없음 → "no verifier". ⓑ `status == "fail"` → 다른 검사 없이 "실패"로 표시(이 기대 동작을 `expectation_ids`에 넣지 않았거나 강도가 낮아도 마찬가지). ⓒ 그 밖 → `status`가 `pass`가 아니면 "verifier status is \"<값>\"", `strength` 순위가 없거나 `min_strength`보다 낮으면 "check strength \"<값>\" is below <min_strength>", `expectation_ids`에 이 id가 없으면 "verifier does not list this expectation", `result_evidence`가 무효면 "verifier result evidence is missing or tampered"와 "불명" 플래그. verifier 강도는 사례 강도가 아니라 기대 동작의 `min_strength`와 비교한다. `command`는 실행하지 않는다. | 코드 확인 |
| R-13 | 첫 binding의 상태 결정 | 다음 순서에서 처음 맞는 것. ① verifier 실패 → `missing`에 "verifier failed"를 더하고 `disproved`. ② `missing`이 비었음 → `proven`, (id, `result_evidence`)를 증명 목록에 추가. ③ "불명" 플래그 → `unclear`. ④ 사례 충족 플래그가 참이고 `symbol`이 빈 문자열이 아님(공백 제거 안 함) → `built`. ⑤ 그 밖 → `described`. 따라서 `built`는 verifier 없음·parser 누락·`module_path` 빈 값이어도 나올 수 있다. | 코드 확인 |
| R-14 | 원장 상태 | `disproved` ≥ 1 → `failing`. 아니고 `unclear` ≥ 1 → `unclear`. 아니고 `proven` + `skipped` = 기대 동작 수 → `ready`(기대 동작이 0개여도 `ready`). 그 밖 → `open`. `waiting`이 하나라도 있으면 `ready`가 될 수 없다. | 코드 확인 |
| R-15 | 원장 id와 증명 해시 | `ledger_id` = `lg_` + SHA-256(canonical_json({"graph": graph_id, "statuses": [[id, status], …]})), 상태 목록은 행 순서. 매니페스트 내용·증거 id는 상태를 통해서만 영향을 준다. `closed_hash` = SHA-256(canonical_json([[id, result_evidence], …])), `proven` 행만, (id, 증거) 쌍 사전순 정렬. 증명된 행이 없으면 `[]`의 해시다. | 코드 확인 |
| R-16 | 원장에 없는 id의 binding | `stray_bindings`에 id를 넣는다. 어떤 행의 상태나 원장 상태에도 영향이 없고 오류도 아니다. | 코드 확인 |
| R-17 | `app_ledger_build` 출력 증거 | `operation` `app_ledger_build`, `subject` {kind `js-app`, sha256 없음, name = 그래프 `label`}, `params` {`graph_id`, `bindings`: 개수, `reviews`: 개수}, `result` = 원장, `confidence` `derived`, `limitations` = [`candidate_expectations`: "Expectations are derived from what static analysis found; behaviour it could not see needs expectations added by review."], `links` = 모든 사례 `evidence_id`와 verifier `result_evidence`(binding 순서, 무효 id 포함, 중복 포함) 뒤에 그래프 증거 id(경로 입력이면 없음). `summary` = "Ledger <ledger_id>: <n> expectation(s), status <status> (<개수> <상태>, …)." 매니페스트 원문은 저장되지 않는다. | 코드 확인 |
| R-18 | `app_coverage_evaluate` 계산 | 입력 원장의 행 상태를 다시 판정하지 않는다. `in_scope` = `skipped`가 아닌 행 수(`waiting` 포함), `proven_percent` = round(proven × 1000 / in_scope) / 10, `in_scope`가 0이면 100.0. `gaps`는 `proven`·`skipped`가 아닌 행을 원장 순서로 최대 500개 담고, 잘렸다는 표시는 없다. `ready`는 원장 `status`가 `ready`일 때만 참. 행에 `layer`·`status`가 없으면 `"?"`로 센다. | 코드 확인 |
| R-19 | `app_coverage_evaluate` 출력 증거 | `operation` `app_coverage_evaluate`, `subject`는 원장 증거의 것, `params` {`ledger_id`}, `confidence` `derived`, `links` = [원장 증거 id], 한계 없음. `summary` = "<proven_percent>% of <in_scope> in-scope expectation(s) proven; ledger <status>." | 코드 확인 |
| R-20 | `app_rebuild_claim_check` | 기대 동작마다 `evidence_ids`가 비면 "cites no evidence", 각 id에 대해 조회 실패면 "<id> not found", `verify` 실패면 "<id> failed its integrity check". 문제가 없으면 `satisfied`. `verified` = 모두 `satisfied`. 출력 증거: `operation` `app_rebuild_claim_check`, `subject` {kind `reconstruction`, name = goal}, `environment` 내장 엔진 + 현재 clean_room 값, `confidence` `derived`, `coverage` complete(total), `links` = 유효했던 id(중복 포함). `summary` = "\"<goal>\": <satisfied> of <total> expectations satisfied[, verified]." 원장·강도·사례·재구현 코드는 보지 않는다. | 코드 확인 |
| R-22 | 같은 id의 기대 동작 행 | **중복이 생기는 종류는 두 가지다.** ⓐ 창(④): 그래프 분석기는 `new BrowserWindow`·`new BrowserView`·`new WebContentsView` 호출마다 창 하나를 남기고 위치는 모듈 경로와 1부터 세는 **줄 번호**뿐이다. 같은 모듈의 같은 줄에 생성 호출이 둘 이상이면(압축된 번들의 한 줄, `a = new BrowserWindow(…), b = new BrowserWindow(…)`) target `window:<모듈>@<줄>`이 같아 같은 id의 행이 그 수만큼 생긴다. ⓑ 브리지 멤버(③): `contextBridge.exposeInMainWorld`/`exposeInIsolatedWorld` 호출마다 항목 하나가 남고 같은 key끼리 합치지 않는다. 그래서 (1) 같은 key를 노출하는 호출이 둘 이상이고(여러 preload, 한 preload 안의 반복 호출, 다른 world 번호로 같은 key) 같은 이름의 멤버를 가질 때, (2) 노출 객체 리터럴에 같은 속성 이름이 두 번 있을 때, (3) key가 문자열 리터럴이 아니어서 모두 `?`가 된 호출들이 같은 이름의 멤버를 가질 때 같은 target `bridge:<key>.<name>`이 반복된다. **중복이 생기지 않는 종류:** ① entry(그래프에 main 진입점이 하나뿐), ② IPC(분석기가 채널 이름을 키로 한 map에 모아 채널당 항목 하나), ⑤~⑧(`seen` 중복 제거). ⑦에서 `storage` 목록에는 `fs.`로 시작하는 API가 들어가지 않으므로 `storage`·`effects` 양쪽에서 같은 `storage` 층 id가 나오는 경우도 없다(`storage` 목록은 `localStorage.`·`sessionStorage.`·`indexedDB.open`·`caches.open`·`safeStorage.`·`keytar.` 이름이거나 `better-sqlite3`·`sqlite3`·`electron-store`·`keytar`·`level`·`lowdb` 모듈에서 온 호출이고, 모듈에서 온 호출의 이름은 `<모듈>.…` 또는 `new <모듈>.…`로 만들어진다). **중복 행의 의미:** 두 행은 기대 동작 필드가 모두 같고 binding·검토도 id로 찾으므로 항상 같은 상태를 받는다. `counts`·`by_layer`·`in_scope`·`proven`에 각각 따로 세고, `ledger_id`의 상태 목록과 `closed_hash`의 증명 목록에도 같은 쌍이 두 번 들어간다. 서로 다른 창(또는 멤버)을 서로 다른 담당 위치에 묶을 수 없다. 두 owner로 binding하면 R-08에 따라 두 행 모두 `disproved`다. | 코드 확인 |
| R-21 | 다른 기능과의 연결 | `js_ledger`·`app_ledger_build`·`app_coverage_evaluate`·`app_rebuild_claim_check`를 `crates/`·`apps/`·`docs/` 전체에서 검색한 결과, 호출부는 엔진 도구 등록(`tools/mod.rs`)과 도구 본문뿐이다. 리빌드 루프(`crates/ai`)는 원장을 부르지 않는다. 그 밖에는 MCP 가이드 프롬프트 이름 `app_rebuild_claim_check`(도구 호출 없는 절차 문구)와 CLI 도움말 테스트가 이름을 언급한다. | 코드 확인(문자열 검색, 검색 범위 위와 같음) |

- 불변식:
  - `proven`인 행의 `missing`은 항상 빈 목록이고, `proven`이 아닌 판정 행(`skipped`·`waiting` 제외)은 `missing`이 비지 않는다.
  - 같은 그래프·같은 상태 목록이면 매니페스트가 달라도 `ledger_id`가 같다. 증명에 쓴 결과 증거가 바뀌면 `closed_hash`만 바뀐다.
  - 원장 판정은 입력(그래프, 매니페스트, 검토, 세션의 증거 집합)에 대해 결정적이다. 시각·난수를 쓰지 않는다.
  - `min_strength`로 쓰이는 값은 `module-test`, `network-test`, `page-test`, `built-app`, `native-call` 다섯 개뿐이다. 그래서 `unit-test` 강도의 사례·verifier는 어떤 기대 동작도 증명하지 못하고, `live-run`·`outside-check`는 모든 기대 동작의 강도 조건을 넘는다.
- 미결정: 없음. (이전 U-1 "같은 id 행이 생길 수 있는가"는 그래프 분석기의 해당 부분을 읽어 R-22로 닫았다.)
- 확인 한계:
  - 실행·빌드·테스트를 하지 않았다. 모든 규칙은 기준 SHA의 코드를 읽어 정했다.
  - 1.2의 증거 경계는 `crates/evidence/src/lib.rs`·`canonical.rs`·`crates/engine/src/session.rs`를 직접 읽어 정의했고, 작성 끝에 선행 스펙 `evidence-record`(같은 SHA, `ready`)의 R-01·R-06·R-17과 대조해 맞췄다. 프로젝트 저장소 읽기(`project.rs` `load_evidence`)의 검증 동작은 선행 스펙의 서술을 따랐다.

### 1.5 필수 코드 참조

| C-ID | 파일:줄 범위 · 심볼 | 가져올 규칙 | 관련 R-ID |
|---|---|---|---|
| C-01 | `crates/analysis/src/js_ledger.rs:15-22` `STRENGTH`, `strength_rank`, `CASE_KINDS` | 강도 사다리 순서와 순위 함수, 사례 종류 목록 | R-11, R-12, R-14 |
| C-02 | `crates/analysis/src/js_ledger.rs:87-217` `expectation_key`, `expectation`, `candidate_expectations` | 기대 동작 id 공식, 그래프 항목별 target·title 문구·층·사례·강도·parser 표, `seen` 중복 제거 키, `effects` 필터 접두어 | R-04, R-05, R-22 |
| C-03 | `crates/analysis/src/js_ledger.rs:219-341` `build_ledger` | 판정 분기 순서, `missing` 문구 원문, 상태 결정, 원장 상태, `ledger_id`·`closed_hash`, 출력 키 | R-06~R-16 |
| C-04 | `crates/analysis/src/js_ledger.rs:343-372` `evaluate_coverage` | 층별 집계, `gaps` 500 상한, 비율 반올림, `ready` | R-18 |
| C-05 | `crates/analysis/src/js_ledger.rs:24-85` `Expectation`, `Owner`, `Case`, `Verifier`, `Binding`, `Review` | 라이브러리 내부 타입과 serde 기본값 | R-09~R-12 |
| C-06 | `crates/engine/src/tools/application_tools.rs:83-98, 598-766` 도구 등록, `OwnerParam`~`LedgerParams`, `app_ledger_build`, `CoverageParams`, `app_coverage_evaluate` (+ `:127-136` `with_links`, `app_subject`) | 도구 입력 스키마(필수·선택·`deny_unknown_fields`), `decision` 검증, 증거 유효성 클로저, 출력 증거 구성과 `summary` 형식 | R-02, R-03, R-10, R-17, R-19 |
| C-07 | `crates/engine/src/tools/compare_tools.rs:88-98, 769-839` `VerifyParams`, `Specification`, `Expectation`, `app_rebuild_claim_check` | 증거 존재 확인 도구 전체 | R-20 |
| C-08 | `crates/engine/src/tools/js_tools.rs:486-507` `load_graph`; `crates/engine/src/tools/artifact_tools.rs:390-416` `resolve_evidence_input`, `is_path_input` | 경로/증거 입력 판별, 페이징 기록 재분석, `operation` 검사 | R-02, R-18 |
| C-09 | `crates/engine/src/session.rs:257-268` `resolve_evidence`; `crates/evidence/src/lib.rs:239-259, 429-431` `compute_id`, `verify`, `is_evidence_id`; `crates/evidence/src/canonical.rs:12-22` `canonical_json`, `sha256_hex` | 증거 조회 순서와 무결성 판정(선행 스펙 경계, 상세는 선행 스펙) | R-10, R-15 |
| C-10 | `crates/engine/src/clean_room.rs:136-151` `allows`, `refusal`; `crates/engine/src/lib.rs:257-259` | Clean room 거부 위치와 오류 형태 | R-01 |

### 1.6 수락 사례
출처: T-01~T-06은 원본 테스트 열람(`js_ledger.rs` `ledger_proves_only_with_strong_enough_evidence`), T-13·T-14는 원본 엔진 테스트 열람(`application_tools.rs` `versions_exports_and_ledger`, `compare_tools.rs` `verify_reconstruction_checks_evidence`), 나머지는 구현에서 도출. 모두 실행하지 않았다.

공통 전제(T-01~T-09): 그래프에 IPC 채널 `export-notes`(handler 있음)가 있고 그 기대 동작 E의 `min_strength`는 `module-test`, `must_cover`는 `works`·`refuses`·`bad-input`, parser 필요. 기본 binding B = owner (`src/ipc.rs`, `export_notes`), `parser_type` `NotesPayload`, 세 종류 사례 모두 `module-test`·유효 증거, verifier {`strength` `module-test`, `status` `pass`, 유효 결과 증거, `expectation_ids` [E]}. 그래프에는 E 말고도 기대 동작이 여럿 있다.

| T-ID | 관련 R-ID | 사전 상태·입력·동작 | 출력·사후 상태 |
|---|---|---|---|
| T-01 | R-13, R-14 | 매니페스트 [B] | E는 `proven`, `missing` []. 다른 행은 `no-owner`라 원장 `open`. |
| T-02 | R-12, R-13 | B의 verifier `strength`만 `unit-test` | E는 `built`, `missing` = ["check strength \"unit-test\" is below module-test"]. |
| T-03 | R-12, R-13, R-14 | B의 verifier `status`만 `fail` | E는 `disproved`, `missing` = ["verifier failed"]. 원장 `failing`. |
| T-04 | R-10, R-13, R-14 | B 그대로, 세션의 어떤 증거도 유효하지 않음 | E는 `unclear`(사례 3개 부족 문구 + "verifier result evidence is missing or tampered"). 원장 `unclear`. |
| T-05 | R-06, R-14, R-18 | 바인딩 없음, 모든 기대 동작에 `skipped` 검토 | 원장 `ready`. 커버리지 `in_scope` 0, `proven_percent` 100.0, `ready` true. |
| T-06 | R-18 | T-01 원장으로 커버리지 계산 | `proven` 1, `gaps`는 3행 이상. |
| T-07 | R-11, R-13 | B의 `bad-input` 사례 강도만 `unit-test` | E는 `described`, `missing` = ["bad-input case with module-test (or stronger) evidence"]. 사례 충족이 거짓이라 `built`가 아니다. |
| T-08 | R-12, R-13 | B에서 verifier 제거 | E는 `built`, `missing` = ["no verifier"]. |
| T-09 | R-12 | B의 verifier `status` `fail`, `expectation_ids` [] | E는 `disproved`. 목록에 없어도 실패가 우선한다. |
| T-10 | R-08, R-14 | [B, B'] B'는 owner (`src/other.rs`, `export_notes`) | E는 `disproved`, `missing` = ["2 different owners claim it"]. 원장 `failing`. |
| T-11 | R-09 | [B'', B] B''는 B와 같은 owner이고 사례·verifier가 없음 | 첫 binding B''만 검사되어 E는 `described`, `missing` = 사례 부족 문구 3개 + "no verifier". B의 사례·verifier는 무시된다. |
| T-12 | R-03 | `reviewed_expectations` [{`expectation_id`: "x", `decision`: "maybe"}] | `BadInput` 오류, 증거 기록 없음. |
| T-13 | R-10, R-02, R-18 | `js_app_map` 증거 하나를 E의 세 사례와 verifier 결과 증거로 모두 지정(강도 `module-test`, `bad-input`만 `network-test`), 그 증거 id로 원장 생성 → 원장 증거를 커버리지에 전달. 그리고 `js_app_map` 증거를 커버리지 입력으로 전달 | 원장 `counts.proven` 1, 커버리지 `proven` 1. 마지막 호출은 `BadInput`(종류가 다름). |
| T-14 | R-20 | 존재하는 증거 id 하나를 인용한 기대 동작 1개 / `ev_` + "0"×64를 인용한 기대 동작 1개 | 첫째 `verified` true. 둘째 `verified` false, `problems` = ["ev_000…0 not found"]. |
| T-15 | R-20 | `expectations` [] 또는 `goal` "  " | 각각 `BadInput`("a specification needs at least one expectation" / "goal is empty"). |
| T-16 | R-18 | 행 상태가 `proven` 1, `no-owner` 2, `skipped` 1인 원장 | `in_scope` 3, `proven_percent` 33.3, `gaps` 2행. |
| T-17 | R-01 | Clean room 세션에서 `app_ledger_build` 호출 | `FeatureMissing`, `details.reason` `clean_room`. |
| T-18 | R-16 | binding의 `expectation_id`가 원장에 없는 "ex_nope" | `stray_bindings` ["ex_nope"], 상태 변화 없음. |
| T-19 | R-22 | 그래프 `windows`에 {`module` "main.js", `line` 1}이 두 개(압축된 main.js 한 줄에 `new BrowserWindow` 두 번), 매니페스트 없음 | 같은 `expectation_id`의 `shell` 행 두 개, 둘 다 `no-owner`. `counts.no-owner`에 2가 더해진다. |
| T-20 | R-22, R-08 | T-19의 그 id에 owner가 다른 binding 두 개 | 두 행 모두 `disproved`("2 different owners claim it"), 원장 `failing`. |
| T-21 | R-22 | 그래프 `exposed`에 {`key` "api", `members` [{`name` "save"}]}가 두 개(preload 두 개), 그 id에 B 수준 binding 하나 | `bridge:api.save` 행 두 개가 같은 상태를 받는다. `proven`이면 커버리지 `proven` 2, `closed_hash` 입력에 같은 쌍이 두 번. |
| T-22 | R-22 | 그래프 `ipc`에 `export-notes` 하나(handler가 두 모듈에 있음) | IPC 행은 하나뿐이다. |

## 2부. 근거

### 2.1 요구사항별 근거 feature map

| R-ID / T-ID | 근거 (repo@8374ad7 `파일:줄` `심볼`) | 확인 방법·한계 |
|---|---|---|
| R-01, T-17 | C-10, `crates/engine/src/clean_room.rs` `TOOLS`(세 id 없음) | `TOOLS`에 `app_` 접두 id가 하나도 없음을 검색으로 확인 |
| R-02 | C-08, `application_tools.rs:678` | 코드 읽기 |
| R-03, T-12, T-15 | `crates/engine/src/tool.rs:311-319` `parse_params`, `application_tools.rs:679-683`, C-07 | 코드 읽기. `ToolError::invalid` = `ErrorCode::BadInput`(`crates/evidence/src/error.rs:115-117`) |
| R-04, R-05 | C-02, 입력 필드 모양 `crates/analysis/src/js_app.rs:136-152, 181-220, 756-811, 924-927`, `crates/js/src/model.rs:158-169` `ApiUse` | 코드 읽기 |
| R-22, T-19~T-22 | IPC: `crates/analysis/src/js_app.rs:602, 667-710, 934`(`channels: BTreeMap<String, IpcChannel>`, `channels.entry(ch)`). 브리지: `js_app.rs:711-728, 909-928`(호출마다 `exposed_keys.push`, 항목별 `g.exposed.push`), `crates/js/src/facts.rs:730-771` `on_expose`(속성마다 `members.push`, key 비리터럴이면 `?`), `crates/js/src/fallback.rs:66-67`(토큰 경로는 멤버 없는 항목만). 창: `js_app.rs:730-759`(fact마다 `g.windows.push`), `facts.rs:773-800` `on_new`(생성 호출마다 `windows.push`, `line`), `crates/js/src/util.rs:22-25`(1부터 세는 줄 번호). storage: `facts.rs:633-650`(storage 조건과 `is_effect`), `:717-728` `add_api`, `:815-830`(`new` 경로), `:1075-1100` `is_effect`, 이름 생성 `facts.rs:84-115` `render`·`render_full` | 코드 읽기. `storage`·`effects`를 채우는 곳이 `add_api` 하나뿐임을 `crates/js/src`·`crates/analysis/src`에서 검색해 확인했다. 실제 앱 번들로 실행해 보지 않았다 |
| R-06~R-16 | C-03 | 코드 읽기 |
| R-10, T-13 | `application_tools.rs:716-717`, `:889-897`(테스트) | 테스트 본문 열람: `js_app_map` 증거 id를 사례·verifier 증거로 넣어 `proven` 1을 단언 |
| R-17 | C-06(`:719-743`) | 코드 읽기. 기록 위치 `crates/engine/src/lib.rs:297-298` |
| R-18, R-19 | C-04, C-06(`:753-766`) | 코드 읽기 |
| R-20, T-14 | C-07, `compare_tools.rs:918-937` | 코드 읽기 + 테스트 열람 |
| R-21 | `crates/engine/src/tools/mod.rs:136, 161`, `crates/mcp/src/prompts.rs:81-95`, `apps/craft-anything-cli/src/tool_args.rs:334` | `grep -rn` 범위: `crates/`, `apps/`, `docs/`, `xtask/`. 검색어 4개 |
| T-01~T-06 | `js_ledger.rs:379-418` | 테스트 본문 열람 |
| T-07~T-11, T-16, T-18 | C-03, C-04 | 구현에서 도출 |

문서와 구현의 차이:
- **기대 동작 추가 경로가 없다.** 출력 한계 문구는 "behaviour it could not see needs expectations added by review"라고 하지만, `reviewed_expectations`는 기존 id의 결정(`required`/`skipped`/`waiting`)만 받고, 원장에 없는 id의 binding은 `stray_bindings`로 빠진다(R-06, R-16). 원장의 기대 동작은 항상 그래프에서 자동 생성한 것뿐이다.
- **`cancel`·`shutdown`은 요구되지 않는다.** `CASE_KINDS`와 도구 스키마 설명은 다섯 종류를 나열하지만 후보 생성 규칙(C-02)은 `works`·`refuses`·`bad-input`만 요구하고, `CASE_KINDS` 상수는 코드 어디서도 참조되지 않는다(검색 확인). overview feature map 6행의 "커버할 사례(works/refuses/bad-input/cancel/shutdown)"는 정의 목록이고 실제 요구 목록이 아니다.
- **"정적 사실은 런타임 사실을 증명하지 못한다"(머리 주석 `js_ledger.rs:4-7`)는 선언된 강도 비교로만 지켜진다.** 증거의 `operation`이나 내용을 보지 않으므로(R-10), 정적 분석 증거에 `module-test` 강도를 붙여도 통과한다. 원본 엔진 테스트가 실제로 그렇게 한다(T-13).
- **verifier `command`·`nondeterminism`, owner `impl_sha256`는 받기만 한다.** 판정에도 출력에도 쓰이지 않는다(R-12, R-17). 원장 결과에는 매니페스트가 남지 않아, 나중에 원장 증거만으로 어떤 binding이 `proven`을 만들었는지 되짚을 수 없다(`links`에 증거 id만 남는다).
- **`gaps` 상한 500에 잘림 표시가 없다.** 원본 `docs/pitfalls.md` Design 절은 상한으로 자른 목록에 `rows_capped`·한계를 붙이라고 규칙을 두지만 `evaluate_coverage`는 표시 없이 자른다(R-18). 총수는 `by_layer`로 알 수 있다.
- **도구 위치.** overview feature map 6행은 `app_ledger_build`·`app_coverage_evaluate`를 `compare_tools.rs`에 있다고 적었지만 실제 위치는 `crates/engine/src/tools/application_tools.rs`다. `compare_tools.rs`에는 `app_rebuild_claim_check`만 있고, 그 도구는 원장과 연결되지 않은 별도 검사다(R-20).
- **MCP 가이드 프롬프트 `app_rebuild_claim_check`(`prompts.rs:81-95`)** 는 "기대 동작마다 재구현에 대해 met / not met / not yet testable로 표시하라"는 3상태 절차를 말하지만, 같은 이름의 도구는 증거 존재·무결성만 보는 2상태(`satisfied` 참/거짓)다. 프롬프트는 도구를 직접 부르라고 하지 않는다.
- **Clean room과의 관계(추론).** 머리 주석은 "clean-room rebuild"가 지켜야 할 것을 다룬다고 하지만 세 도구는 Deep 모드에서만 실행된다. 원본 내부(앱 번들)를 읽어 기대 동작을 뽑으므로 분석 쪽은 Deep, 재구현 쪽이 clean room이라는 뜻으로 읽힌다. 의도를 밝힌 문서는 찾지 못했다.

### 2.2 코드 읽는 순서
`application_tools.rs` `app_ledger_build`(676) → `js_ledger.rs` `candidate_expectations`(106) → `build_ledger`(220) → `evaluate_coverage`(344) → `app_coverage_evaluate`(753). 별도로 `compare_tools.rs` `app_rebuild_claim_check`(792). 원본 구현 전략: 판정 함수는 증거 조회를 클로저(`evidence_ok`)로 받아 L2(analysis)에 두고, 세션 접근은 L4(engine) 도구가 넣는다. 그래서 판정 로직은 세션 없이 테스트된다(`js_ledger.rs` 테스트는 `id.starts_with("ev_good")` 클로저를 쓴다).

### 2.3 비교·재사용 출처
같은 기능을 다른 레포에서 스펙으로 쓴 것은 없다. 코드를 복사하지 않았다. 라이선스는 `MIT OR Apache-2.0`(overview 1절).

## 적용 메모
원본과 다르게 할 점은 이 기능을 재구현할 때가 아니라 **우리 절차(`OSS_ANALYSIS_WORKFLOW.md`)의 재구현 검증**에 가져올 때를 기준으로 쓴다. 우리 쪽 대응물은 스펙의 R-ID(기대 동작), T-ID(사례), 재구현 결과물이다.

| 관련 R-ID | 원본과 다르게 할 점 | 이유 | 바뀌는 인터페이스·흐름·사례 |
|---|---|---|---|
| R-04, R-11 | 사례 종류를 R-ID별로 스펙 작성자가 정한다. 원본처럼 층별 고정표로 자동 생성하지 않는다. 1.6 T-ID에 `사례 종류`(정상/거부/잘못된 입력/취소·종료) 열을 두고, R-ID마다 필요한 종류가 T-ID로 하나씩 덮였는지 본다. | 우리 기대 동작의 원천은 정적 그래프가 아니라 사람이 쓴 R-ID다. 원본도 자동 생성이 놓친 동작을 추가할 경로가 없다(2.1 첫 항목). | 템플릿 1.6에 열 하나. T-ID 없는 R-ID·종류가 "빈칸"으로 드러난다. |
| R-11, R-12, 불변식 | 강도를 문자열 선언으로 받지 않고 **근거물의 종류로 정한다.** 우리에 맞는 사다리는 3단계면 충분하다: `읽기 대조`(재구현 코드를 스펙과 눈으로 대조) < `재구현 단독 실행`(T-ID 입력으로 재구현만 실행) < `원본 대조 실행`(같은 입력을 원본과 재구현에 넣고 출력 비교). R-ID마다 최소 강도를 적고, 실행 기록 경로(`artifacts/<repo>/…`)가 없으면 `읽기 대조`로 본다. | 원본은 강도를 호출자가 선언하고 증거의 존재·무결성만 보므로, 정적 분석 증거로도 `proven`이 된다(R-10, T-13). 우리는 사람이 검증하므로 선언만으로는 같은 구멍이 생긴다. 원본의 8단계는 Electron 앱 층(네트워크·페이지·네이티브)에 맞춘 것이라 라이브러리·CLI 스펙에는 과하다. | 재구현 검증 결과 표에 `강도`·`근거물` 열. R-ID 표에 `최소 강도` 열(기본 `재구현 단독 실행`, 외부 형식·출력 비교가 핵심인 규칙은 `원본 대조 실행`). |
| R-07, R-08, R-13 | 재구현 검증 결과를 R-ID별 **충족 표**로 남기고 원본의 상태 어휘를 그대로 쓴다: `no-owner`(재구현에 담당 위치 없음), `described`(위치만 있음, 사례 부족), `built`(사례는 있으나 검사 부족·약함), `proven`, `disproved`(검사 실패 또는 담당 위치 2곳 이상), `unclear`(근거물이 없거나 깨짐), `skipped`(범위 밖, 사유 필수), `waiting`(사용자 결정 대기). | 지금 우리 4장 6번의 "재현 준비 완료"는 스펙 `status`와 통합 검토 같은 **문서 상태**로만 판정하고, 재구현을 실제로 돌린 결과를 R-ID 단위로 남기는 칸이 없다. 원본의 `disproved`/`unclear` 구분은 "재구현(또는 스펙)이 틀렸다"와 "판단할 근거가 없다"를 나눠 준다. | 4장에 선택 단계 "재구현 검증"과 표 형식 추가. 예: `R-11 | owner: ledger.py:build | T-07(거부) 원본 대조 실행 | proven`. |
| R-08 | R-ID 하나에 재구현 담당 위치가 둘 이상 필요하면 `disproved`로 끝내지 말고 **스펙 분할 신호**로 기록한다. | 원본에서 담당 위치가 둘이면 바로 반증이다. 우리 스펙에서 그런 R-ID는 두 규칙이 한 줄에 섞였다는 뜻일 가능성이 높다(추론). | 충족 표의 `missing`에 "담당 2곳 → R-ID 분할 검토". |
| R-12 | 실패한 검사는 R-ID 목록에 없어도 그 기대 동작을 반증한다는 원본 규칙은 가져오지 않는다. 검사 결과는 그 검사가 명시한 R-ID에만 적용한다. | 원본은 binding에 붙은 verifier가 `fail`이면 목록 여부와 상관없이 `disproved`다(T-09). 우리 쪽에서는 한 테스트 묶음 실패가 무관한 R-ID까지 반증하는 오판이 된다. | 없음(규칙 차이만). |
| R-14, R-18 | 원장 상태 우선순위(`failing` > `unclear` > `ready` > `open`)와 비율(`proven` / (`skipped` 제외 수))을 "재현 준비 완료" 보고에 함께 쓴다. `waiting`이 있으면 완료가 아니다. 빈칸 목록을 자르면 잘린 수를 같이 적는다. | 지금 보고 형식은 `ready M / draft K / 미작성 N`(스펙 단위)뿐이다. R-ID 단위 비율이 있어야 "어느 규칙이 아직 증명되지 않았는가"가 보인다. 원본은 `gaps`를 표시 없이 자른다(R-18). | 4장 6번 보고에 `proven P / in_scope S (x%)`, 상태 하나. |
| R-17 | 검증 결과에 **매니페스트 원문(어느 재구현 위치·어느 근거물로 판정했는지)** 을 남긴다. | 원본 원장 증거는 매니페스트 개수만 저장해 나중에 판정을 되짚을 수 없다. | 충족 표 자체가 그 기록이다(파일로 남김). |
| R-20 | `app_rebuild_claim_check` 수준의 "인용한 근거가 존재하고 깨지지 않았나" 검사는 `scripts/check.py`로 자동화할 수 있다(스펙의 `파일:줄`이 기준 SHA에 존재하는지). 하지만 그것은 근거 존재 확인일 뿐 재구현 검증이 아니라고 구분해 쓴다. | 원본도 두 도구를 분리했고, 존재 확인 도구의 이름("rebuild claim check")과 가이드 프롬프트가 실제보다 강한 검증처럼 읽힌다(2.1). | `check.py` 점검 항목 후보(overview 후보 표의 근거 행 3과 같은 항목). |
